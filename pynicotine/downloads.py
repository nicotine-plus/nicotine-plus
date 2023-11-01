# COPYRIGHT (C) 2020-2023 Nicotine+ Contributors
#
# GNU GENERAL PUBLIC LICENSE
#    Version 3, 29 June 2007
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import os.path
import re
import shutil
import time

from collections import defaultdict
from locale import strxfrm

from pynicotine import slskmessages
from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.logfacility import log
from pynicotine.transfers import Transfer
from pynicotine.transfers import Transfers
from pynicotine.utils import execute_command
from pynicotine.utils import clean_file
from pynicotine.utils import clean_path
from pynicotine.utils import encode_path
from pynicotine.utils import truncate_string_byte


class Downloads(Transfers):

    def __init__(self):

        super().__init__(transfers_file_path=os.path.join(config.data_folder_path, "downloads.json"))

        self.requested_folders = defaultdict(dict)
        self.requested_folder_token = 0

        self._download_queue_timer_id = None
        self._retry_connection_downloads_timer_id = None
        self._retry_io_downloads_timer_id = None
        self._retry_limited_downloads_timer_id = None

        for event_name, callback in (
            ("download-connection-closed", self._download_connection_closed),
            ("download-file-error", self._download_file_error),
            ("file-download-init", self._file_download_init),
            ("file-download-progress", self._file_download_progress),
            ("folder-contents-response", self._folder_contents_response),
            ("peer-connection-error", self._peer_connection_error),
            ("place-in-queue-response", self._place_in_queue_response),
            ("set-connection-stats", self._set_connection_stats),
            ("transfer-request", self._transfer_request),
            ("upload-denied", self._upload_denied),
            ("upload-failed", self._upload_failed),
            ("user-status", self._user_status)
        ):
            events.connect(event_name, callback)

    def _start(self):
        super()._start()
        self.update_download_filters()

    def _quit(self):

        super()._quit()

        self.requested_folder_token = 0

    def _server_login(self, msg):

        if not msg.success:
            return

        super()._server_login(msg)

        self.requested_folders.clear()

        # Request queue position of queued downloads and retry failed downloads every 3 minutes
        self._download_queue_timer_id = events.schedule(delay=180, callback=self._check_download_queue, repeat=True)

        # Retry downloads failed due to connection issues every 3 minutes
        self._retry_connection_downloads_timer_id = events.schedule(
            delay=180, callback=self._retry_failed_connection_downloads, repeat=True)

        # Retry downloads failed due to file I/O errors every 15 minutes
        self._retry_io_downloads_timer_id = events.schedule(
            delay=900, callback=self._retry_failed_io_downloads, repeat=True)

        # Re-queue limited downloads every 12 minutes
        self._retry_limited_downloads_timer_id = events.schedule(
            delay=720, callback=self._retry_limited_downloads, repeat=True)

    def _server_disconnect(self, msg):

        for timer_id in (
            self._download_queue_timer_id,
            self._retry_connection_downloads_timer_id,
            self._retry_io_downloads_timer_id,
            self._retry_limited_downloads_timer_id
        ):
            events.cancel_scheduled(timer_id)

        super()._server_disconnect(msg)

        events.emit("update-downloads")
        self.requested_folders.clear()

    # Load Transfers #

    def get_transfer_list_file_path(self):

        downloads_file_1_4_2 = os.path.join(config.data_folder_path, "config.transfers.pickle")
        downloads_file_1_4_1 = os.path.join(config.data_folder_path, "transfers.pickle")

        if os.path.exists(encode_path(self.transfers_file_path)):
            # New file format
            return self.transfers_file_path

        if os.path.exists(encode_path(downloads_file_1_4_2)):
            # Nicotine+ 1.4.2+
            return downloads_file_1_4_2

        if os.path.exists(encode_path(downloads_file_1_4_1)):
            # Nicotine <=1.4.1
            return downloads_file_1_4_1

        # Fall back to new file format
        return self.transfers_file_path

    def load_transfers(self):

        load_func = self.load_transfers_file
        transfers_file_path = self.get_transfer_list_file_path()

        if transfers_file_path != self.transfers_file_path:
            load_func = self.load_legacy_transfers_file

        for transfer in self.get_stored_transfers(transfers_file_path, load_func):
            if transfer.status == "User logged off":
                # Mark transfer as failed in order to resume it when connected
                self._fail_transfer(transfer)

            self._append_transfer(transfer)

    # Limits #

    def update_transfer_limits(self):

        events.emit("update-download-limits")

        if core.user_status == slskmessages.UserStatus.OFFLINE:
            return

        use_speed_limit = config.sections["transfers"]["use_download_speed_limit"]

        if use_speed_limit == "primary":
            speed_limit = config.sections["transfers"]["downloadlimit"]

        elif use_speed_limit == "alternative":
            speed_limit = config.sections["transfers"]["downloadlimitalt"]

        else:
            speed_limit = 0

        core.send_message_to_network_thread(slskmessages.SetDownloadLimit(speed_limit))

    # Events #

    def _user_status(self, msg):
        """Server code 7.

        We get a status of a user and if he's online, we request a file
        from him
        """

        update = False
        username = msg.user

        if msg.status == slskmessages.UserStatus.OFFLINE:
            for users in (self.queued_users, self.failed_users):
                for download in users.get(username, {}).copy().values():
                    self._abort_transfer(download, abort_reason="User logged off")
                    update = True

            for download in self.active_users.get(username, {}).copy().values():
                if download.status != "Transferring":
                    self._abort_transfer(download, abort_reason="User logged off")
                    update = True
        else:
            for download in self.failed_users.get(username, {}).copy().values():
                self.get_file(username, download.virtual_path, transfer=download, ui_callback=False)
                update = True

        if update:
            events.emit("update-downloads")

    def _set_connection_stats(self, download_bandwidth=0, **_unused):
        self.total_bandwidth = download_bandwidth

    def _peer_connection_error(self, username, msgs=None, is_offline=False):

        if msgs is None:
            return

        for msg in msgs:
            if msg.__class__ is slskmessages.QueueUpload:
                self._cant_connect_queue_file(username, msg.file, is_offline)

    def _cant_connect_queue_file(self, username, virtual_path, is_offline):
        """We can't connect to the user, either way (QueueUpload)."""

        download = self.queued_users.get(username, {}).get(virtual_path)

        if download is None:
            return

        log.add_transfer("Download attempt for file %(filename)s from user %(user)s timed out", {
            "filename": virtual_path,
            "user": username
        })

        self._abort_transfer(download, abort_reason="User logged off" if is_offline else "Connection timeout")

    def _folder_contents_response(self, msg, check_num_files=True):
        """Peer code 37."""

        username = msg.init.target_user

        if username not in self.requested_folders:
            return

        for folder_path, files in msg.list.items():
            if folder_path not in self.requested_folders[username]:
                continue

            log.add_transfer("Received response for folder content request from user %s", username)

            num_files = len(files)

            if check_num_files and num_files > 100:
                events.emit("download-large-folder", username, folder_path, num_files, msg)
                return

            destination_folder_path = self.get_folder_destination(username, folder_path)
            del self.requested_folders[username][folder_path]

            if num_files > 1:
                files.sort(key=lambda x: strxfrm(x[1]))

            log.add_transfer(("Attempting to download files in folder %(folder)s for user %(user)s. "
                              "Destination path: %(destination)s"), {
                "folder": folder_path,
                "user": username,
                "destination": destination_folder_path
            })

            for _code, basename, file_size, _ext, file_attributes, *_unused in files:
                virtual_path = folder_path.rstrip("\\") + "\\" + basename

                self.get_file(
                    username, virtual_path, folder_path=destination_folder_path, size=file_size,
                    file_attributes=file_attributes)

    def _transfer_request(self, msg):
        """Peer code 40."""

        username = msg.init.target_user

        if msg.direction != slskmessages.TransferDirection.UPLOAD:
            return

        response = self._transfer_request_downloads(msg)

        log.add_transfer(("Responding to download request with token %(token)s for file %(filename)s "
                          "from user: %(user)s, allowed: %(allowed)s, reason: %(reason)s"), {
            "token": response.token, "filename": msg.file, "user": username,
            "allowed": response.allowed, "reason": response.reason
        })

        core.send_message_to_peer(username, response)

    def _transfer_request_downloads(self, msg):

        username = msg.init.target_user
        virtual_path = msg.file
        size = msg.filesize
        token = msg.token

        log.add_transfer("Received download request with token %(token)s for file %(filename)s from user %(user)s", {
            "token": token,
            "filename": virtual_path,
            "user": username
        })

        cancel_reason = "Cancelled"
        accepted = True
        download = self.transfers.get(username + virtual_path)

        if download is not None:
            status = download.status

            if status == "Finished":
                # SoulseekQt sends "Complete" as the reason for rejecting the download if it exists
                cancel_reason = "Complete"
                accepted = False

            elif status in {"Paused", "Filtered"}:
                accepted = False

            else:
                # Remote peer is signaling a transfer is ready, attempting to download it

                # If the file is larger than 2GB, the SoulseekQt client seems to
                # send a malformed file size (0 bytes) in the TransferRequest response.
                # In that case, we rely on the cached, correct file size we received when
                # we initially added the download.

                if size > 0:
                    if download.size != size:
                        # The remote user's file contents have changed since we queued the download
                        download.size_changed = True

                    download.size = size

                self._activate_transfer(download, token)
                self._update_transfer(download)

                return slskmessages.TransferResponse(allowed=True, token=token)

        if accepted and self.can_upload(username):
            if self.get_complete_download_file_path(username, virtual_path, size):
                # Check if download exists in our default download folder
                cancel_reason = "Complete"
            else:
                # If this file is not in your download queue, then it must be
                # a remotely initiated download and someone is manually uploading to you
                parent_folder_path = virtual_path.replace("/", "\\").split("\\")[-2]
                folder_path = os.path.join(
                    os.path.normpath(config.sections["transfers"]["uploaddir"]), username, parent_folder_path)

                transfer = Transfer(
                    username=username, virtual_path=virtual_path, folder_path=folder_path, size=size)

                self._activate_transfer(transfer, token)
                self._append_transfer(transfer)
                self._update_transfer(transfer)

                return slskmessages.TransferResponse(allowed=True, token=token)

        log.add_transfer("Denied file request: User %(user)s, %(msg)s", {
            "user": username,
            "msg": msg
        })

        return slskmessages.TransferResponse(allowed=False, reason=cancel_reason, token=token)

    def _transfer_timeout(self, transfer):

        log.add_transfer("Download %(filename)s with token %(token)s for user %(user)s timed out", {
            "filename": transfer.virtual_path,
            "token": transfer.token,
            "user": transfer.username
        })

        self._abort_transfer(transfer, abort_reason="Connection timeout")

    def _download_file_error(self, username, token, error):
        """Networking thread encountered a local file error for download."""

        download = self.active_users.get(username, {}).get(token)

        if download is None:
            return

        self._abort_transfer(download, abort_reason="Local file error")
        log.add(_("Download I/O error: %s"), error)

    def _file_download_init(self, msg):
        """A peer is requesting to start uploading a file to us."""

        username = msg.init.target_user
        token = msg.token
        download = self.active_users.get(username, {}).get(token)

        if download is None:
            # Support legacy transfer system (clients: old Nicotine+ versions, slskd)
            # The user who requested the download initiates the file upload connection
            # in this case, but we always assume an incoming file init message is
            # FileDownloadInit

            log.add_transfer(("Received unknown file download init message with token %s, checking if peer "
                              "requested us to upload a file instead"), token)
            events.emit("file-upload-init", msg)
            return

        virtual_path = download.virtual_path

        log.add_transfer(("Received file download init with token %(token)s for file %(filename)s "
                          "from user %(user)s"), {
            "token": token,
            "filename": virtual_path,
            "user": username
        })

        if download.sock is not None:
            log.add_transfer("Download already has an existing file connection, ignoring init message")
            core.send_message_to_network_thread(slskmessages.CloseConnection(msg.init.sock))
            return

        incomplete_folder_path = os.path.normpath(config.sections["transfers"]["incompletedir"])
        need_update = True
        download.sock = msg.init.sock

        try:
            incomplete_folder_path_encoded = encode_path(incomplete_folder_path)

            if not os.path.isdir(incomplete_folder_path_encoded):
                os.makedirs(incomplete_folder_path_encoded)

            incomplete_file_path = self.get_incomplete_download_file_path(username, virtual_path)
            file_handle = open(encode_path(incomplete_file_path), "ab+")  # pylint: disable=consider-using-with

            try:
                import fcntl
                try:
                    fcntl.lockf(file_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except OSError as error:
                    log.add(_("Can't get an exclusive lock on file - I/O error: %s"), error)
            except ImportError:
                pass

            if download.size_changed:
                # Remote user sent a different file size than we originally requested,
                # wipe any existing data in the incomplete file to avoid corruption
                file_handle.truncate(0)

            # Seek to the end of the file for resuming the download
            offset = file_handle.seek(0, os.SEEK_END)

        except OSError as error:
            log.add(_("Cannot save file in %(folder_path)s: %(error)s"), {
                "folder_path": incomplete_folder_path,
                "error": error
            })
            self._abort_transfer(download, abort_reason="Download folder error")
            core.notifications.show_download_notification(
                str(error), title=_("Download Folder Error"), high_priority=True)
            need_update = False

        else:
            download.file_handle = file_handle
            download.last_byte_offset = offset
            download.last_update = time.monotonic()
            download.start_time = download.last_update - download.time_elapsed

            core.statistics.append_stat_value("started_downloads", 1)
            core.pluginhandler.download_started_notification(username, virtual_path, incomplete_file_path)

            log.add_download(
                _("Download started: user %(user)s, file %(file)s"), {
                    "user": username,
                    "file": file_handle.name.decode("utf-8", "replace")
                }
            )

            if download.size > offset:
                download.status = "Transferring"
                core.send_message_to_network_thread(slskmessages.DownloadFile(
                    init=msg.init, token=token, file=file_handle, leftbytes=(download.size - offset)
                ))
                core.send_message_to_network_thread(slskmessages.FileOffset(init=msg.init, offset=offset))

            else:
                self._finish_transfer(download)
                need_update = False

        events.emit("download-notification")

        if need_update:
            self._update_transfer(download)

    def _upload_denied(self, msg):
        """Peer code 50."""

        username = msg.init.target_user
        virtual_path = msg.file
        reason = msg.reason
        download = self.queued_users.get(username, {}).get(virtual_path)

        if download is None:
            return

        if reason in {"Getting status", "Transferring", "Paused", "Filtered", "User logged off", "Finished"}:
            # Don't allow internal statuses as reason
            reason = "Cancelled"

        if reason == "File not shared." and not download.legacy_attempt:
            # The peer is possibly using an old client that doesn't support Unicode
            # (Soulseek NS). Attempt to request file name encoded as latin-1 once.

            log.add_transfer("User %(user)s responded with reason '%(reason)s' for download request %(filename)s. "
                             "Attempting to request file as latin-1.", {
                                 "user": username,
                                 "reason": reason,
                                 "filename": virtual_path
                             })

            self._abort_transfer(download, abort_reason=None)
            download.legacy_attempt = True
            self.get_file(username, virtual_path, transfer=download)
            return

        self._abort_transfer(download, abort_reason=reason)
        self._update_transfer(download)

        log.add_transfer("Download request denied by user %(user)s for file %(filename)s. Reason: %(reason)s", {
            "user": username,
            "filename": virtual_path,
            "reason": msg.reason
        })

    def _upload_failed(self, msg):
        """Peer code 46."""

        username = msg.init.target_user
        virtual_path = msg.file
        download = self.transfers.get(username + virtual_path)

        if download is None:
            return

        if download.token not in self.active_users.get(username, {}):
            return

        should_retry = not download.legacy_attempt

        if should_retry:
            # Attempt to request file name encoded as latin-1 once

            self._abort_transfer(download, abort_reason=None)
            download.legacy_attempt = True
            self.get_file(username, virtual_path, transfer=download)
            return

        # Already failed once previously, give up
        self._abort_transfer(download, abort_reason="Connection closed")

        log.add_transfer("Upload attempt by user %(user)s for file %(filename)s failed. Reason: %(reason)s", {
            "filename": virtual_path,
            "user": username,
            "reason": download.status
        })

    def _file_download_progress(self, username, token, bytes_left):
        """A file download is in progress."""

        download = self.active_users.get(username, {}).get(token)

        if download is None:
            return

        if download in self.transfer_request_times:
            del self.transfer_request_times[download]

        current_time = time.monotonic()
        size = download.size

        download.status = "Transferring"
        download.time_elapsed = current_time - download.start_time
        download.current_byte_offset = current_byte_offset = (size - bytes_left)
        byte_difference = current_byte_offset - download.last_byte_offset

        if byte_difference:
            core.statistics.append_stat_value("downloaded_size", byte_difference)

            if size > current_byte_offset or download.speed is None:
                download.speed = int(max(0, byte_difference // max(0.1, current_time - download.last_update)))
                download.time_left = (size - current_byte_offset) // download.speed if download.speed else 0
            else:
                download.time_left = 0

        download.last_byte_offset = current_byte_offset
        download.last_update = current_time

        self._update_transfer(download)

    def _download_connection_closed(self, username, token):
        """A file download connection has closed for any reason."""

        download = self.active_users.get(username, {}).get(token)

        if download is None:
            return

        if download.current_byte_offset is not None and download.current_byte_offset >= download.size:
            self._finish_transfer(download)
            return

        status = None

        if core.user_statuses.get(download.username) == slskmessages.UserStatus.OFFLINE:
            status = "User logged off"
        else:
            status = "Cancelled"

        self._abort_transfer(download, abort_reason=status)

    def _place_in_queue_response(self, msg):
        """Peer code 44.

        The peer tells us our place in queue for a particular transfer
        """

        username = msg.init.target_user
        virtual_path = msg.filename
        download = self.queued_users.get(username, {}).get(virtual_path)

        if download is None:
            return

        download.queue_position = msg.place
        self._update_transfer(download, update_parent=False)

    # Transfer Actions #

    def _append_transfer(self, transfer):
        self.transfers[transfer.username + transfer.virtual_path] = transfer

    def _update_transfer(self, transfer, update_parent=True):
        events.emit("update-download", transfer, update_parent)

    def _auto_clear_transfer(self, transfer):

        if config.sections["transfers"]["autoclear_downloads"]:
            self._clear_transfer(transfer)
            return True

        return False

    def get_folder(self, username, folder_path, download_folder_path=None):

        self.requested_folders[username][folder_path] = download_folder_path
        self.requested_folder_token = slskmessages.increment_token(self.requested_folder_token)

        core.send_message_to_peer(
            username, slskmessages.FolderContentsRequest(directory=folder_path, token=self.requested_folder_token))

    def get_file(self, username, virtual_path, folder_path=None, transfer=None, size=0, file_attributes=None,
                 bypass_filter=False, ui_callback=True):

        is_new_download = False

        if folder_path:
            folder_path = clean_path(folder_path)
        else:
            folder_path = self.get_default_download_folder(username)

        if transfer is None:
            download = self.transfers.get(username + virtual_path)

            if download is not None and download.folder_path != folder_path and download.status == "Finished":
                # Only one user + virtual path transfer possible at a time, remove the old one
                self._clear_transfer(download, update_parent=False)
                download = None

            if download is None:
                transfer = Transfer(
                    username=username, virtual_path=virtual_path, folder_path=folder_path,
                    size=size, file_attributes=file_attributes
                )
                is_new_download = True
            else:
                # Duplicate download found, stop here
                return
        else:
            transfer.virtual_path = virtual_path

        if not bypass_filter and config.sections["transfers"]["enablefilters"]:
            try:
                downloadregexp = re.compile(config.sections["transfers"]["downloadregexp"], flags=re.IGNORECASE)

                if downloadregexp.search(virtual_path) is not None:
                    log.add_transfer("Filtering: %s", virtual_path)

                    if self._auto_clear_transfer(transfer):
                        return

                    self._abort_transfer(transfer, abort_reason="Filtered")

            except re.error:
                pass

        if slskmessages.UserStatus.OFFLINE in (core.user_status, core.user_statuses.get(username)):
            # Either we are offline or the user we want to download from is
            self._abort_transfer(transfer, abort_reason="User logged off")

        elif transfer.status != "Filtered":
            download_path = self.get_complete_download_file_path(username, virtual_path, size, transfer.folder_path)

            if download_path:
                transfer.status = "Finished"
                transfer.size = transfer.current_byte_offset = size

                log.add_transfer("File %s is already downloaded", download_path)

            else:
                log.add_transfer("Adding file %(filename)s from user %(user)s to download queue", {
                    "filename": virtual_path,
                    "user": username
                })
                self._enqueue_transfer(transfer)
                core.send_message_to_peer(
                    username, slskmessages.QueueUpload(file=virtual_path, legacy_client=transfer.legacy_attempt))

        if is_new_download:
            self._append_transfer(transfer)

        if ui_callback:
            self._update_transfer(transfer)

    def can_upload(self, username):

        transfers = config.sections["transfers"]

        if not transfers["remotedownloads"]:
            return False

        if transfers["uploadallowed"] == 1:
            # Everyone
            return True

        if transfers["uploadallowed"] == 2 and username in core.userlist.buddies:
            # Buddies
            return True

        if transfers["uploadallowed"] == 3:
            # Trusted buddies
            user_data = core.userlist.buddies.get(username)

            if user_data and user_data.is_trusted:
                return True

        return False

    def get_folder_destination(self, username, folder_path, root_folder_path=None, download_folder_path=None):

        # Remove parent folders of the requested folder from path
        parent_folder_path = root_folder_path if root_folder_path else folder_path
        removed_parent_folders = parent_folder_path.rsplit("\\", 1)[0] if "\\" in parent_folder_path else ""
        target_folders = folder_path.replace(removed_parent_folders, "").lstrip("\\").replace("\\", os.sep)

        # Check if a custom download location was specified
        if not download_folder_path:
            if (username in self.requested_folders and folder_path in self.requested_folders[username]
                    and self.requested_folders[username][folder_path]):
                download_folder_path = self.requested_folders[username][folder_path]
            else:
                download_folder_path = self.get_default_download_folder(username)

        # Merge download path with target folder name
        return os.path.join(download_folder_path, target_folders)

    def get_default_download_folder(self, username=None):

        download_folder_path = os.path.normpath(config.sections["transfers"]["downloaddir"])

        # Check if username subfolders should be created for downloads
        if username and config.sections["transfers"]["usernamesubfolders"]:
            download_folder_path = os.path.join(download_folder_path, clean_file(username))

        return download_folder_path

    def get_basename_byte_limit(self, folder_path):

        try:
            max_bytes = os.statvfs(encode_path(folder_path)).f_namemax

        except (AttributeError, OSError):
            max_bytes = 255

        return max_bytes

    def get_download_basename(self, virtual_path, download_folder_path, avoid_conflict=False):
        """Returns the download basename for a virtual file path."""

        max_bytes = self.get_basename_byte_limit(download_folder_path)

        basename = clean_file(virtual_path.replace("/", "\\").split("\\")[-1])
        basename_no_extension, extension = os.path.splitext(basename)
        basename_limit = max_bytes - len(extension.encode("utf-8"))
        basename_no_extension = truncate_string_byte(basename_no_extension, max(0, basename_limit))

        if basename_limit < 0:
            extension = truncate_string_byte(extension, max_bytes)

        corrected_basename = basename_no_extension + extension

        if not avoid_conflict:
            return corrected_basename

        counter = 1

        while os.path.exists(encode_path(os.path.join(download_folder_path, corrected_basename))):
            corrected_basename = f"{basename_no_extension} ({counter}){extension}"
            counter += 1

        return corrected_basename

    def get_complete_download_file_path(self, username, virtual_path, size, download_folder_path=None):
        """Returns the download path of a complete download, if available."""

        if not download_folder_path:
            download_folder_path = self.get_default_download_folder(username)

        basename = self.get_download_basename(virtual_path, download_folder_path)
        basename_no_extension, extension = os.path.splitext(basename)
        download_file_path = os.path.join(download_folder_path, basename)
        counter = 1

        while os.path.isfile(encode_path(download_file_path)):
            if os.stat(encode_path(download_file_path)).st_size == size:
                # Found a previous download with a matching file size
                return download_file_path

            basename = f"{basename_no_extension} ({counter}){extension}"
            download_file_path = os.path.join(download_folder_path, basename)
            counter += 1

        return None

    def get_incomplete_download_file_path(self, username, virtual_path):
        """Returns the path to store a download while it's still
        transferring."""

        from hashlib import md5
        md5sum = md5()
        md5sum.update((virtual_path + username).encode("utf-8"))
        prefix = f"INCOMPLETE{md5sum.hexdigest()}"

        # Ensure file name length doesn't exceed file system limit
        incomplete_folder_path = os.path.normpath(config.sections["transfers"]["incompletedir"])
        max_bytes = self.get_basename_byte_limit(incomplete_folder_path)

        basename = clean_file(virtual_path.replace("/", "\\").split("\\")[-1])
        basename_no_extension, extension = os.path.splitext(basename)
        basename_limit = max_bytes - len(prefix) - len(extension.encode("utf-8"))
        basename_no_extension = truncate_string_byte(basename_no_extension, max(0, basename_limit))

        if basename_limit < 0:
            extension = truncate_string_byte(extension, max_bytes - len(prefix))

        return os.path.join(incomplete_folder_path, prefix + basename_no_extension + extension)

    def get_current_download_file_path(self, username, virtual_path, download_folder_path, size):
        """Returns the current file path of a download."""

        return (self.get_complete_download_file_path(username, virtual_path, size, download_folder_path)
                or self.get_incomplete_download_file_path(username, virtual_path))

    def _file_downloaded_actions(self, username, file_path):

        if config.sections["notifications"]["notification_popup_file"]:
            core.notifications.show_download_notification(
                _("%(file)s downloaded from %(user)s") % {
                    "user": username,
                    "file": os.path.basename(file_path)
                },
                title=_("File Downloaded")
            )

        if config.sections["transfers"]["afterfinish"]:
            try:
                execute_command(config.sections["transfers"]["afterfinish"], file_path)
                log.add(_("Executed: %s"), config.sections["transfers"]["afterfinish"])

            except Exception:
                log.add(_("Trouble executing '%s'"), config.sections["transfers"]["afterfinish"])

    def _folder_downloaded_actions(self, username, folder_path):

        if not folder_path:
            return

        for downloads in (
            self.queued_users.get(username, {}),
            self.active_users.get(username, {}),
            self.failed_users.get(username, {})
        ):
            for download in downloads.values():
                if download.folder_path == folder_path:
                    return

        if config.sections["notifications"]["notification_popup_folder"]:
            core.notifications.show_download_notification(
                _("%(folder)s downloaded from %(user)s") % {
                    "user": username,
                    "folder": folder_path
                },
                title=_("Folder Downloaded")
            )

        if config.sections["transfers"]["afterfolder"]:
            try:
                execute_command(config.sections["transfers"]["afterfolder"], folder_path)
                log.add(_("Executed on folder: %s"), config.sections["transfers"]["afterfolder"])

            except Exception:
                log.add(_("Trouble executing on folder: %s"), config.sections["transfers"]["afterfolder"])

    def _finish_transfer(self, transfer):

        download_folder_path = transfer.folder_path or self.get_default_download_folder(transfer.username)
        download_folder_path_encoded = encode_path(download_folder_path)

        download_basename = self.get_download_basename(transfer.virtual_path, download_folder_path, avoid_conflict=True)
        download_file_path = os.path.join(download_folder_path, download_basename)
        incomplete_file_path_encoded = transfer.file_handle.name

        self._deactivate_transfer(transfer)
        self._close_file(transfer)

        try:
            if not os.path.isdir(download_folder_path_encoded):
                os.makedirs(download_folder_path_encoded)

            shutil.move(incomplete_file_path_encoded, encode_path(download_file_path))

        except OSError as error:
            log.add(
                _("Couldn't move '%(tempfile)s' to '%(file)s': %(error)s"), {
                    "tempfile": incomplete_file_path_encoded.decode("utf-8", "replace"),
                    "file": download_file_path,
                    "error": error
                }
            )
            self._abort_transfer(transfer, abort_reason="Download folder error")
            core.notifications.show_download_notification(
                str(error), title=_("Download Folder Error"), high_priority=True
            )
            return

        transfer.status = "Finished"
        transfer.current_byte_offset = transfer.size
        transfer.sock = None

        core.statistics.append_stat_value("completed_downloads", 1)

        # Attempt to show notification and execute commands
        self._file_downloaded_actions(transfer.username, download_file_path)
        self._folder_downloaded_actions(transfer.username, transfer.folder_path)

        finished = True
        events.emit("download-notification", finished)

        # Attempt to autoclear this download, if configured
        if not self._auto_clear_transfer(transfer):
            self._update_transfer(transfer)

        core.pluginhandler.download_finished_notification(transfer.username, transfer.virtual_path, download_file_path)

        log.add_download(
            _("Download finished: user %(user)s, file %(file)s"), {
                "user": transfer.username,
                "file": transfer.virtual_path
            }
        )

    def _check_download_queue(self):

        for download in self.queued_transfers:
            core.send_message_to_peer(
                download.username,
                slskmessages.PlaceInQueueRequest(file=download.virtual_path, legacy_client=download.legacy_attempt)
            )

    def retry_download(self, transfer, bypass_filter=False):

        username = transfer.username
        active_downloads = self.active_users.get(username, {}).values()

        if transfer in active_downloads or transfer.status == "Finished":
            # Don't retry active or finished downloads
            return

        self._abort_transfer(transfer, abort_reason=None)
        self.get_file(username, transfer.virtual_path, transfer=transfer, bypass_filter=bypass_filter)

    def retry_downloads(self, downloads):

        num_downloads = len(downloads)

        for download in downloads:
            # Provide a way to bypass download filters in case the user actually wants a file.
            # To avoid accidentally bypassing filters, ensure that only a single file is selected,
            # and it has the "Filtered" status.

            bypass_filter = (num_downloads == 1 and download.status == "Filtered")
            self.retry_download(download, bypass_filter)

    def _retry_failed_connection_downloads(self):

        statuses = {"Connection closed", "Connection timeout", "Pending shutdown."}

        for failed_downloads in self.failed_users.copy().values():
            for download in failed_downloads.copy().values():
                if download.status not in statuses:
                    continue

                self._abort_transfer(download, abort_reason=None)
                self.get_file(download.username, download.virtual_path, transfer=download)

    def _retry_failed_io_downloads(self):

        statuses = {"Download folder error", "File read error.", "Local file error"}

        for failed_downloads in self.failed_users.copy().values():
            for download in failed_downloads.copy().values():
                if download.status not in statuses:
                    continue

                self._abort_transfer(download, abort_reason=None)
                self.get_file(download.username, download.virtual_path, transfer=download)

    def _retry_limited_downloads(self):

        statuses = {"Too many files", "Too many megabytes"}

        for failed_downloads in self.failed_users.copy().values():
            for download in failed_downloads.copy().values():
                if download.status not in statuses and not download.status.startswith("User limit of"):
                    continue

                log.add_transfer("Re-queuing file %(filename)s from user %(user)s in download queue", {
                    "filename": download.virtual_path,
                    "user": download.username
                })

                self._abort_transfer(download, abort_reason=None)
                self.get_file(download.username, download.virtual_path, transfer=download)

    def _abort_transfer(self, transfer, denied_message=None, abort_reason="Paused", update_parent=True):

        log.add_transfer(('Aborting download, user "%(user)s", filename "%(filename)s", token "%(token)s", '
                          'status "%(status)s"'), {
            "user": transfer.username,
            "filename": transfer.virtual_path,
            "token": transfer.token,
            "status": transfer.status
        })

        transfer.legacy_attempt = False
        transfer.size_changed = False

        if transfer.sock is not None:
            core.send_message_to_network_thread(slskmessages.CloseConnection(transfer.sock))
            transfer.sock = None

        if transfer.file_handle is not None:
            self._close_file(transfer)

            log.add_download(
                _("Download aborted, user %(user)s file %(file)s"), {
                    "user": transfer.username,
                    "file": transfer.virtual_path
                }
            )

        self._deactivate_transfer(transfer)
        self._dequeue_transfer(transfer)
        self._unfail_transfer(transfer)

        if abort_reason:
            transfer.status = abort_reason

            if abort_reason not in {"Finished", "Filtered", "Paused"}:
                self._fail_transfer(transfer)

        events.emit("abort-download", transfer, abort_reason, update_parent)

    def abort_downloads(self, downloads, abort_reason="Paused"):

        ignored_statuses = {abort_reason, "Finished"}

        for download in downloads:
            if download.status not in ignored_statuses:
                self._abort_transfer(download, abort_reason=abort_reason, update_parent=False)

        events.emit("abort-downloads", downloads, abort_reason)

    def _clear_transfer(self, transfer, update_parent=True):

        self._abort_transfer(transfer, abort_reason=None)
        self._remove_transfer(transfer)

        events.emit("clear-download", transfer, update_parent)

    def clear_downloads(self, downloads=None, statuses=None, clear_deleted=False):

        if downloads is None:
            # Clear all downloads
            downloads = self.transfers.copy().values()
        else:
            downloads = downloads.copy()

        for download in downloads:
            if statuses and download.status not in statuses:
                continue

            if clear_deleted:
                if download.status != "Finished":
                    continue

                if self.get_complete_download_file_path(
                        download.username, download.virtual_path, download.size, download.folder_path):
                    continue

            self._clear_transfer(download, update_parent=False)

        events.emit("clear-downloads", downloads, statuses, clear_deleted)

    # Filters #

    def update_download_filters(self):

        failed = {}
        outfilter = "(\\\\("
        download_filters = sorted(config.sections["transfers"]["downloadfilters"])
        # Get Filters from config file and check their escaped status
        # Test if they are valid regular expressions and save error messages

        for item in download_filters:
            dfilter, escaped = item
            if escaped:
                dfilter = re.escape(dfilter)
                dfilter = dfilter.replace("\\*", ".*")

            try:
                re.compile(f"({dfilter})")
                outfilter += dfilter

                if item is not download_filters[-1]:
                    outfilter += "|"

            except re.error as error:
                failed[dfilter] = error

        outfilter += ")$)"

        try:
            re.compile(outfilter)

        except re.error as error:
            # Strange that individual filters _and_ the composite filter both fail
            log.add(_("Error: Download Filter failed! Verify your filters. Reason: %s"), error)
            config.sections["transfers"]["downloadregexp"] = ""
            return

        config.sections["transfers"]["downloadregexp"] = outfilter

        # Send error messages for each failed filter to log window
        if not failed:
            return

        errors = ""

        for dfilter, error in failed.items():
            errors += f"Filter: {dfilter} Error: {error} "

        log.add(_("Error: %(num)d Download filters failed! %(error)s "), {"num": len(failed), "error": errors})
