# COPYRIGHT (C) 2020-2024 Nicotine+ Contributors
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2016 Mutnick <muhing@yahoo.com>
# COPYRIGHT (C) 2013 eLvErDe <gandalf@le-vert.net>
# COPYRIGHT (C) 2008-2012 quinox <quinox@users.sf.net>
# COPYRIGHT (C) 2009 hedonist <ak@sensi.org>
# COPYRIGHT (C) 2006-2009 daelstorm <daelstorm@gmail.com>
# COPYRIGHT (C) 2003-2004 Hyriand <hyriand@thegraveyard.org>
# COPYRIGHT (C) 2001-2003 Alexander Kanavin
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
import re
import shutil
import time

try:
    # Try faster module import first, if available
    from _md5 import md5  # pylint: disable=import-private-name
except ImportError:
    from hashlib import md5

from collections import defaultdict

from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.logfacility import log
from pynicotine.slskmessages import ConnectionType
from pynicotine.slskmessages import DownloadFile
from pynicotine.slskmessages import FileOffset
from pynicotine.slskmessages import FolderContentsRequest
from pynicotine.slskmessages import increment_token
from pynicotine.slskmessages import initial_token
from pynicotine.slskmessages import PlaceInQueueRequest
from pynicotine.slskmessages import QueueUpload
from pynicotine.slskmessages import SetDownloadLimit
from pynicotine.slskmessages import TransferDirection
from pynicotine.slskmessages import TransferRejectReason
from pynicotine.slskmessages import TransferResponse
from pynicotine.slskmessages import UserStatus
from pynicotine.transfers import Transfer
from pynicotine.transfers import Transfers
from pynicotine.transfers import TransferStatus
from pynicotine.utils import execute_command
from pynicotine.utils import clean_file
from pynicotine.utils import clean_path
from pynicotine.utils import encode_path
from pynicotine.utils import truncate_string_byte


class RequestedFolder:
    __slots__ = ("username", "folder_path", "download_folder_path", "request_timer_id", "has_retried",
                 "legacy_attempt")

    def __init__(self, username, folder_path, download_folder_path):
        self.username = username
        self.folder_path = folder_path
        self.download_folder_path = download_folder_path
        self.request_timer_id = None
        self.has_retried = False
        self.legacy_attempt = False


class Downloads(Transfers):
    __slots__ = ("_requested_folders", "_requested_folder_token", "_folder_basename_byte_limits",
                 "_pending_queue_messages", "_download_queue_timer_id", "_retry_connection_downloads_timer_id",
                 "_retry_io_downloads_timer_id")

    def __init__(self):

        super().__init__(name="downloads")

        self._requested_folders = defaultdict(dict)
        self._requested_folder_token = initial_token()

        self._folder_basename_byte_limits = {}
        self._pending_queue_messages = {}

        self._download_queue_timer_id = None
        self._retry_connection_downloads_timer_id = None
        self._retry_io_downloads_timer_id = None

        for event_name, callback in (
            ("download-file-error", self._download_file_error),
            ("file-connection-closed", self._file_connection_closed),
            ("file-transfer-init", self._file_transfer_init),
            ("file-download-progress", self._file_download_progress),
            ("folder-contents-response", self._folder_contents_response),
            ("peer-connection-closed", self._peer_connection_closed),
            ("peer-connection-error", self._peer_connection_error),
            ("place-in-queue-response", self._place_in_queue_response),
            ("set-connection-stats", self._set_connection_stats),
            ("shares-ready", self._shares_ready),
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

        self._delete_stale_incomplete_downloads()

        super()._quit()

        self._folder_basename_byte_limits.clear()

    def _server_login(self, msg):

        if not msg.success:
            return

        super()._server_login(msg)

        # Request queue position of queued downloads every 5 minutes
        self._download_queue_timer_id = events.schedule(
            delay=300, callback=self._request_queue_positions, repeat=True)

        # Retry downloads failed due to connection issues every 3 minutes
        self._retry_connection_downloads_timer_id = events.schedule(
            delay=180, callback=self._retry_failed_connection_downloads, repeat=True)

        # Retry downloads failed due to file I/O errors every 15 minutes
        self._retry_io_downloads_timer_id = events.schedule(
            delay=900, callback=self._retry_failed_io_downloads, repeat=True)

    def _server_disconnect(self, msg):

        super()._server_disconnect(msg)

        for timer_id in (
            self._download_queue_timer_id,
            self._retry_connection_downloads_timer_id,
            self._retry_io_downloads_timer_id
        ):
            events.cancel_scheduled(timer_id)

        for user_requested_folders in self._requested_folders.values():
            for requested_folder in user_requested_folders.values():
                if requested_folder.request_timer_id is None:
                    continue

                events.cancel_scheduled(requested_folder.request_timer_id)
                requested_folder.request_timer_id = None

        self._requested_folders.clear()

    # Load Transfers #

    def _get_transfer_list_file_path(self):

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

    def _load_transfers(self):

        load_func = self._load_transfers_file
        transfers_file_path = self._get_transfer_list_file_path()

        if transfers_file_path != self.transfers_file_path:
            load_func = self._load_legacy_transfers_file

        for transfer in self._get_stored_transfers(transfers_file_path, load_func):
            self._append_transfer(transfer)

            if transfer.status == TransferStatus.USER_LOGGED_OFF:
                # Mark transfer as failed in order to resume it when connected
                self._fail_transfer(transfer)

    # Filters/Limits #

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

    def update_transfer_limits(self):

        events.emit("update-download-limits")

        use_speed_limit = config.sections["transfers"]["use_download_speed_limit"]

        if use_speed_limit == "primary":
            speed_limit = config.sections["transfers"]["downloadlimit"]

        elif use_speed_limit == "alternative":
            speed_limit = config.sections["transfers"]["downloadlimitalt"]

        else:
            speed_limit = 0

        core.send_message_to_network_thread(SetDownloadLimit(speed_limit))

    # Transfer Actions #

    def _update_transfer(self, transfer, update_parent=True):
        events.emit("update-download", transfer, update_parent)

    def _enqueue_transfer(self, transfer, bypass_filter=False):

        username = transfer.username
        virtual_path = transfer.virtual_path
        size = transfer.size

        if not bypass_filter and config.sections["transfers"]["enablefilters"]:
            try:
                downloadregexp = re.compile(config.sections["transfers"]["downloadregexp"], flags=re.IGNORECASE)

                if downloadregexp.search(virtual_path) is not None:
                    log.add_transfer("Filtering: %s", virtual_path)

                    if not self._auto_clear_transfer(transfer):
                        self._abort_transfer(transfer, status=TransferStatus.FILTERED)

                    return False

            except re.error:
                pass

        if UserStatus.OFFLINE in (core.users.login_status, core.users.statuses.get(username)):
            # Either we are offline or the user we want to download from is
            self._abort_transfer(transfer, status=TransferStatus.USER_LOGGED_OFF)
            return False

        log.add_transfer("Adding file %s from user %s to download queue", (virtual_path, username))

        _file_path, file_exists = self.get_complete_download_file_path(
            username, virtual_path, size, transfer.folder_path)

        if file_exists:
            self._finish_transfer(transfer)
            return False

        super()._enqueue_transfer(transfer)

        msg = QueueUpload(virtual_path, transfer.legacy_attempt)

        if not core.shares.initialized:
            # Remain queued locally until our shares have initialized, to prevent invalid
            # messages about not sharing any files
            self._pending_queue_messages[transfer] = msg
        else:
            core.send_message_to_peer(username, msg)

        return True

    def _enqueue_limited_transfers(self, username):

        num_limited_transfers = 0
        queue_size_limit = self._user_queue_limits.get(username)

        if queue_size_limit is None:
            return

        for download in self.failed_users.get(username, {}).copy().values():
            if download.status != TransferRejectReason.QUEUED:
                continue

            if num_limited_transfers >= queue_size_limit:
                # Only enqueue a small number of downloads at a time
                return

            self._unfail_transfer(download)

            if self._enqueue_transfer(download):
                self._update_transfer(download)

            num_limited_transfers += 1

        # No more limited downloads
        del self._user_queue_limits[username]

    def _dequeue_transfer(self, transfer):

        super()._dequeue_transfer(transfer)

        if transfer in self._pending_queue_messages:
            del self._pending_queue_messages[transfer]

    def _file_downloaded_actions(self, username, file_path):

        if config.sections["notifications"]["notification_popup_file"]:
            core.notifications.show_download_notification(
                _("%(file)s downloaded from %(user)s") % {
                    "user": username,
                    "file": os.path.basename(file_path)
                },
                title=_("File Downloaded")
            )

        command = config.sections["transfers"]["afterfinish"]

        if command:
            try:
                execute_command(command, file_path, hidden=True)
                log.add(_("Executed: %s"), command)

            except Exception as error:
                log.add(_("Executing '%(command)s' failed: %(error)s"), {
                    "command": command,
                    "error": error
                })

    def _folder_downloaded_actions(self, username, folder_path):

        if not folder_path:
            return

        if folder_path == self.get_default_download_folder(username):
            return

        for downloads in (
            self.queued_users.get(username, {}),
            self.active_users.get(username, {}),
            self.failed_users.get(username, {})
        ):
            for download in downloads.values():
                if download.folder_path == folder_path:
                    return

        events.emit("folder-download-finished", folder_path)

        if config.sections["notifications"]["notification_popup_folder"]:
            core.notifications.show_download_notification(
                _("%(folder)s downloaded from %(user)s") % {
                    "user": username,
                    "folder": folder_path
                },
                title=_("Folder Downloaded")
            )

        command = config.sections["transfers"]["afterfolder"]

        if command:
            try:
                execute_command(command, folder_path, hidden=True)
                log.add(_("Executed on folder: %s"), command)

            except Exception as error:
                log.add(_("Executing '%(command)s' failed: %(error)s"), {
                    "command": command,
                    "error": error
                })

    def _move_finished_transfer(self, transfer, incomplete_file_path):

        download_folder_path = transfer.folder_path or self.get_default_download_folder(transfer.username)
        download_folder_path_encoded = encode_path(download_folder_path)

        download_basename = self.get_download_basename(transfer.virtual_path, download_folder_path, avoid_conflict=True)
        download_file_path = os.path.join(download_folder_path, download_basename)

        try:
            if not os.path.isdir(download_folder_path_encoded):
                os.makedirs(download_folder_path_encoded)

            shutil.move(incomplete_file_path, encode_path(download_file_path))

        except OSError as error:
            log.add(
                _("Couldn't move '%(tempfile)s' to '%(file)s': %(error)s"), {
                    "tempfile": incomplete_file_path.decode("utf-8", "replace"),
                    "file": download_file_path,
                    "error": error
                }
            )
            self._abort_transfer(transfer, status=TransferStatus.DOWNLOAD_FOLDER_ERROR)
            core.notifications.show_download_notification(
                str(error), title=_("Download Folder Error"), high_priority=True
            )
            return None

        return download_file_path

    def _finish_transfer(self, transfer):

        username = transfer.username
        virtual_path = transfer.virtual_path
        already_exists = transfer.file_handle is None
        incomplete_file_path = transfer.file_handle.name if not already_exists else None

        super()._finish_transfer(transfer)

        if not already_exists:
            download_file_path = self._move_finished_transfer(transfer, incomplete_file_path)

            if download_file_path is None:
                # Download was not moved successfully
                return

        if not self._auto_clear_transfer(transfer):
            self._update_transfer(transfer)

        if already_exists:
            log.add_transfer("File %s is already downloaded", virtual_path)
            return

        core.statistics.append_stat_value("completed_downloads", 1)

        # Attempt to show notification and execute commands
        self._file_downloaded_actions(username, download_file_path)
        self._folder_downloaded_actions(username, transfer.folder_path)

        core.pluginhandler.download_finished_notification(username, virtual_path, download_file_path)

        log.add_download(
            _("Download finished: user %(user)s, file %(file)s"), {
                "user": username,
                "file": virtual_path
            }
        )

    def _abort_transfer(self, transfer, status=None, denied_message=None, update_parent=True):

        if transfer.file_handle is not None:
            log.add_download(
                _("Download aborted, user %(user)s file %(file)s"), {
                    "user": transfer.username,
                    "file": transfer.virtual_path
                }
            )

        super()._abort_transfer(transfer, status=status, denied_message=denied_message)

        if status:
            events.emit("abort-download", transfer, status, update_parent)

    def _clear_transfer(self, transfer, denied_message=None, update_parent=True):

        virtual_path = transfer.virtual_path
        username = transfer.username

        log.add_transfer("Clearing download %s from user %s", (virtual_path, username))

        try:
            super()._clear_transfer(transfer, denied_message=denied_message)

        except KeyError:
            log.add("FIXME: failed to remove download %s from user %s, not present in list",
                    (virtual_path, username))

        events.emit("clear-download", transfer, update_parent)

    def _delete_stale_incomplete_downloads(self):

        if not self._allow_saving_transfers:
            return

        incomplete_download_folder_path = self.get_incomplete_download_folder()
        allowed_incomplete_file_paths = {
            encode_path(self.get_incomplete_download_file_path(transfer.username, transfer.virtual_path))
            for transfer in self.transfers.values()
            if transfer.current_byte_offset and transfer.status != TransferStatus.FINISHED
        }
        prefix = b"INCOMPLETE"
        prefix_len = len(prefix)
        md5_len = 32
        md5_regex = re.compile(b"[0-9a-f]{32}", re.IGNORECASE)

        try:
            with os.scandir(encode_path(incomplete_download_folder_path)) as entries:
                for entry in entries:
                    if entry.is_dir():
                        continue

                    if entry.path in allowed_incomplete_file_paths:
                        continue

                    basename = entry.name

                    # Skip files that are not incomplete downloads
                    if (not basename.startswith(prefix)
                            or len(basename) <= (prefix_len + md5_len)
                            or not md5_regex.match(basename[prefix_len:prefix_len + md5_len])):
                        continue

                    # Incomplete file no longer has a download associated with it. Delete it.
                    try:
                        os.remove(entry.path)
                        log.add_transfer("Deleted stale incomplete download %s", entry.path)

                    except OSError as error:
                        log.add_transfer("Cannot delete incomplete download %s: %s", (entry.path, error))

        except OSError as error:
            log.add_transfer("Cannot read incomplete download folder: %s", error)

    def _request_queue_positions(self):

        for download in self.queued_transfers:
            core.send_message_to_peer(
                download.username,
                PlaceInQueueRequest(download.virtual_path, download.legacy_attempt)
            )

    def _retry_failed_connection_downloads(self):

        statuses = {
            TransferStatus.CONNECTION_CLOSED, TransferStatus.CONNECTION_TIMEOUT, TransferRejectReason.PENDING_SHUTDOWN}

        for failed_downloads in self.failed_users.copy().values():
            for download in failed_downloads.copy().values():
                if download.status not in statuses:
                    continue

                self._unfail_transfer(download)

                if self._enqueue_transfer(download):
                    self._update_transfer(download)

    def _retry_failed_io_downloads(self):

        statuses = {
            TransferStatus.DOWNLOAD_FOLDER_ERROR, TransferStatus.LOCAL_FILE_ERROR, TransferRejectReason.FILE_READ_ERROR}

        for failed_downloads in self.failed_users.copy().values():
            for download in failed_downloads.copy().values():
                if download.status not in statuses:
                    continue

                self._unfail_transfer(download)

                if self._enqueue_transfer(download):
                    self._update_transfer(download)

    def can_upload(self, username):

        transfers = config.sections["transfers"]

        if not transfers["remotedownloads"]:
            return False

        if transfers["uploadallowed"] == 1:
            # Everyone
            return True

        if transfers["uploadallowed"] == 2 and username in core.buddies.users:
            # Buddies
            return True

        if transfers["uploadallowed"] == 3:
            # Trusted buddies
            user_data = core.buddies.users.get(username)

            if user_data and user_data.is_trusted:
                return True

        return False

    def get_folder_destination(self, username, folder_path, root_folder_path=None, download_folder_path=None):

        # Remove parent folders of the requested folder from path
        parent_folder_path = root_folder_path if root_folder_path else folder_path
        removed_parent_folders = parent_folder_path.rpartition("\\")[0]
        target_folders = folder_path.replace(removed_parent_folders, "", 1).lstrip("\\").replace("\\", os.sep)

        # Check if a custom download location was specified
        if not download_folder_path:
            requested_folder = self._requested_folders.get(username, {}).get(folder_path)

            if requested_folder is not None and requested_folder.download_folder_path:
                download_folder_path = requested_folder.download_folder_path
            else:
                download_folder_path = self.get_default_download_folder(username)

        # Merge download path with target folder name
        return os.path.join(download_folder_path, target_folders)

    def get_default_download_folder(self, username=None):

        download_folder_path = os.path.normpath(os.path.expandvars(config.sections["transfers"]["downloaddir"]))

        # Check if username subfolders should be created for downloads
        if username and config.sections["transfers"]["usernamesubfolders"]:
            download_folder_path = os.path.join(download_folder_path, clean_file(username))

        return download_folder_path

    def get_incomplete_download_folder(self):
        return os.path.normpath(os.path.expandvars(config.sections["transfers"]["incompletedir"]))

    def get_basename_byte_limit(self, folder_path):

        max_bytes = self._folder_basename_byte_limits.get(folder_path)

        if max_bytes is None:
            try:
                max_bytes = os.statvfs(encode_path(folder_path)).f_namemax

            except (AttributeError, OSError):
                max_bytes = 255

            self._folder_basename_byte_limits[folder_path] = max_bytes

        return max_bytes

    def get_download_basename(self, virtual_path, download_folder_path, avoid_conflict=False):
        """Returns the download basename for a virtual file path."""

        max_bytes = self.get_basename_byte_limit(download_folder_path)

        basename = clean_file(virtual_path.rpartition("\\")[-1])
        basename_no_extension, separator, extension = basename.rpartition(".")
        extension = separator + extension
        basename_limit = max_bytes - len(extension.encode())
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
        basename_no_extension, separator, extension = basename.rpartition(".")
        extension = separator + extension
        download_file_path = os.path.join(download_folder_path, basename)
        file_exists = False
        counter = 1

        while os.path.exists(encode_path(download_file_path)):
            if os.stat(encode_path(download_file_path)).st_size == size:
                # Found a previous download with a matching file size
                file_exists = True
                break

            basename = f"{basename_no_extension} ({counter}){extension}"
            download_file_path = os.path.join(download_folder_path, basename)
            counter += 1

        return download_file_path, file_exists

    def get_incomplete_download_file_path(self, username, virtual_path):
        """Returns the path to store a download while it's still
        transferring."""

        md5sum = md5()
        md5sum.update((virtual_path + username).encode())
        prefix = f"INCOMPLETE{md5sum.hexdigest()}"

        # Ensure file name length doesn't exceed file system limit
        incomplete_folder_path = self.get_incomplete_download_folder()
        max_bytes = self.get_basename_byte_limit(incomplete_folder_path)

        basename = clean_file(virtual_path.rpartition("\\")[-1])
        basename_no_extension, separator, extension = basename.rpartition(".")
        extension = separator + extension
        basename_limit = max_bytes - len(prefix) - len(extension.encode())
        basename_no_extension = truncate_string_byte(basename_no_extension, max(0, basename_limit))

        if basename_limit < 0:
            extension = truncate_string_byte(extension, max_bytes - len(prefix))

        return os.path.join(incomplete_folder_path, prefix + basename_no_extension + extension)

    def get_current_download_file_path(self, transfer):
        """Returns the current file path of a download."""

        file_path, file_exists = self.get_complete_download_file_path(
            transfer.username, transfer.virtual_path, transfer.size, transfer.folder_path)

        if file_exists or transfer.status == TransferStatus.FINISHED:
            return file_path

        return self.get_incomplete_download_file_path(transfer.username, transfer.virtual_path)

    def enqueue_folder(self, username, folder_path, download_folder_path=None):

        requested_folder = self._requested_folders.get(username, {}).get(folder_path)

        if requested_folder is None:
            self._requested_folders[username][folder_path] = requested_folder = RequestedFolder(
                username, folder_path, download_folder_path
            )

        # First timeout is shorter to get a response sooner in case the first request
        # failed. Second timeout is longer in case the response is delayed.
        timeout = 60 if requested_folder.has_retried else 15

        if requested_folder.request_timer_id is not None:
            events.cancel_scheduled(requested_folder.request_timer_id)
            requested_folder.request_timer_id = None

        requested_folder.request_timer_id = events.schedule(
            delay=timeout, callback=self._requested_folder_timeout, callback_args=(requested_folder,)
        )

        log.add_transfer("Requesting contents of folder %s from user %s", (folder_path, username))

        self._requested_folder_token = increment_token(self._requested_folder_token)

        core.send_message_to_peer(
            username, FolderContentsRequest(
                folder_path, self._requested_folder_token, legacy_client=requested_folder.legacy_attempt
            )
        )

    def enqueue_download(self, username, virtual_path, folder_path=None, size=0, file_attributes=None,
                         bypass_filter=False):

        transfer = self.transfers.get(username + virtual_path)

        if folder_path:
            folder_path = clean_path(folder_path)
        else:
            folder_path = self.get_default_download_folder(username)

        if transfer is not None and transfer.folder_path != folder_path and transfer.status == TransferStatus.FINISHED:
            # Only one user + virtual path transfer possible at a time, remove the old one
            self._clear_transfer(transfer, update_parent=False)
            transfer = None

        if transfer is not None:
            # Duplicate download found, stop here
            return

        transfer = Transfer(username, virtual_path, folder_path, size, file_attributes)

        self._append_transfer(transfer)

        if self._enqueue_transfer(transfer, bypass_filter=bypass_filter):
            self._update_transfer(transfer)

    def retry_download(self, transfer, bypass_filter=False):

        username = transfer.username
        active_downloads = self.active_users.get(username, {}).values()

        if transfer in active_downloads or transfer.status == TransferStatus.FINISHED:
            # Don't retry active or finished downloads
            return

        self._dequeue_transfer(transfer)
        self._unfail_transfer(transfer)

        if self._enqueue_transfer(transfer, bypass_filter=bypass_filter):
            self._update_transfer(transfer)

    def retry_downloads(self, downloads):

        num_downloads = len(downloads)

        for download in downloads:
            # Provide a way to bypass download filters in case the user actually wants a file.
            # To avoid accidentally bypassing filters, ensure that only a single file is selected,
            # and it has the "Filtered" status.

            bypass_filter = (num_downloads == 1 and download.status == TransferStatus.FILTERED)
            self.retry_download(download, bypass_filter)

    def abort_downloads(self, downloads, status=TransferStatus.PAUSED):

        ignored_statuses = {status, TransferStatus.FINISHED}

        for download in downloads:
            if download.status not in ignored_statuses:
                self._abort_transfer(download, status=status, update_parent=False)

        events.emit("abort-downloads", downloads, status)

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
                if download.status != TransferStatus.FINISHED:
                    continue

                _file_path, file_exists = self.get_complete_download_file_path(
                    download.username, download.virtual_path, download.size, download.folder_path)

                if file_exists:
                    continue

            self._clear_transfer(download, update_parent=False)

        events.emit("clear-downloads", downloads, statuses, clear_deleted)

    # Events #

    def _shares_ready(self, _successful):
        """Send any QueueUpload messages we delayed while our shares were
        initializing.
        """

        for transfer, msg in self._pending_queue_messages.items():
            core.send_message_to_peer(transfer.username, msg)

        self._pending_queue_messages.clear()

    def _user_status(self, msg):
        """Server code 7."""

        username = msg.user

        if username not in core.users.watched:
            # Skip redundant status updates from users in joined rooms
            return

        if msg.status == UserStatus.OFFLINE:
            for users in (self.queued_users, self.failed_users):
                for download in users.get(username, {}).copy().values():
                    self._abort_transfer(download, status=TransferStatus.USER_LOGGED_OFF)

            for download in self.active_users.get(username, {}).copy().values():
                if download.status != TransferStatus.TRANSFERRING:
                    self._abort_transfer(download, status=TransferStatus.USER_LOGGED_OFF)

            self._online_users.discard(username)
            return

        # No need to check transfers on away status change
        if username in self._online_users:
            return

        # User logged in, resume "User logged off" transfers
        for download in self.failed_users.get(username, {}).copy().values():
            self._unfail_transfer(download)

            if self._enqueue_transfer(download):
                self._update_transfer(download)

        self._online_users.add(username)

    def _set_connection_stats(self, download_bandwidth=0, **_unused):
        self.total_bandwidth = download_bandwidth

    def _peer_connection_error(self, username, conn_type, msgs, is_offline=False, is_timeout=True):

        if not msgs:
            return

        if conn_type not in {ConnectionType.FILE, ConnectionType.PEER}:
            return

        failed_msg_types = {QueueUpload, PlaceInQueueRequest}

        for msg in msgs:
            if msg.__class__ in failed_msg_types:
                self._cant_connect_queue_file(username, msg.file, is_offline, is_timeout)

    def _peer_connection_closed(self, username, conn_type, msgs=None):
        self._peer_connection_error(username, conn_type, msgs, is_timeout=False)

    def _cant_connect_queue_file(self, username, virtual_path, is_offline, is_timeout):
        """We can't connect to the user, either way (QueueUpload, PlaceInQueueRequest)."""

        download = self.queued_users.get(username, {}).get(virtual_path)

        if download is None:
            return

        if is_offline:
            status = TransferStatus.USER_LOGGED_OFF

        elif is_timeout:
            status = TransferStatus.CONNECTION_TIMEOUT

        else:
            status = TransferStatus.CONNECTION_CLOSED

        log.add_transfer("Download attempt for file %s from user %s failed with status %s",
                         (virtual_path, username, status))
        self._abort_transfer(download, status=status)

    def _requested_folder_timeout(self, requested_folder):

        if requested_folder.request_timer_id is None:
            return

        requested_folder.request_timer_id = None
        username = requested_folder.username
        folder_path = requested_folder.folder_path

        if requested_folder.has_retried:
            log.add_transfer("Folder content request for folder %s from user %s timed out, "
                             "giving up", (folder_path, username))
            del self._requested_folders[username][folder_path]
            return

        log.add_transfer("Folder content request for folder %s from user %s timed out, "
                         "retrying", (folder_path, username))

        requested_folder.has_retried = True
        self.enqueue_folder(username, folder_path, requested_folder.download_folder_path)

    def _folder_contents_response(self, msg, check_num_files=True):
        """Peer code 37."""

        username = msg.username
        folder_path = msg.dir

        if username not in self._requested_folders:
            return

        requested_folder = self._requested_folders[username].get(msg.dir)

        if requested_folder is None:
            return

        log.add_transfer("Received response for folder content request for folder %s "
                         "from user %s", (folder_path, username))

        if requested_folder.request_timer_id is not None:
            events.cancel_scheduled(requested_folder.request_timer_id)
            requested_folder.request_timer_id = None

        if not msg.list and not requested_folder.legacy_attempt:
            log.add_transfer("Folder content response is empty. Trying legacy latin-1 request.")
            requested_folder.legacy_attempt = True
            self.enqueue_folder(username, folder_path, requested_folder.download_folder_path)
            return

        for i_folder_path, files in msg.list.items():
            if i_folder_path != folder_path:
                continue

            num_files = len(files)

            if check_num_files and num_files > 100:
                check_num_files = False
                events.emit(
                    "download-large-folder", username, folder_path, num_files,
                    self._folder_contents_response, (msg, check_num_files)
                )
                return

            destination_folder_path = self.get_folder_destination(username, folder_path)

            log.add_transfer("Attempting to download files in folder %s for user %s. "
                             "Destination path: %s", (folder_path, username, destination_folder_path))

            for _code, basename, file_size, _ext, file_attributes, *_unused in files:
                virtual_path = folder_path.rstrip("\\") + "\\" + basename

                self.enqueue_download(
                    username, virtual_path, folder_path=destination_folder_path, size=file_size,
                    file_attributes=file_attributes)

        del self._requested_folders[username][folder_path]

    def _transfer_request(self, msg):
        """Peer code 40."""

        if msg.direction != TransferDirection.UPLOAD:
            return

        username = msg.username
        response = self._transfer_request_downloads(msg)

        log.add_transfer("Responding to download request with token %s for file %s "
                         "from user: %s, allowed: %s, reason: %s",
                         (response.token, msg.file, username, response.allowed, response.reason))

        core.send_message_to_peer(username, response)

    def _transfer_request_downloads(self, msg):

        username = msg.username
        virtual_path = msg.file
        size = msg.filesize
        token = msg.token

        log.add_transfer("Received download request with token %s for file %s from user %s",
                         (token, virtual_path, username))

        download = (self.queued_users.get(username, {}).get(virtual_path)
                    or self.failed_users.get(username, {}).get(virtual_path))

        if download is not None:
            # Remote peer is signaling a transfer is ready, attempting to download it

            # If the file is larger than 2GB, the SoulseekQt client seems to
            # send a malformed file size (0 bytes) in the TransferRequest response.
            # In that case, we rely on the cached, correct file size we received when
            # we initially added the download.

            self._unfail_transfer(download)
            self._dequeue_transfer(download)

            if size > 0:
                if download.size != size:
                    # The remote user's file contents have changed since we queued the download
                    download.size_changed = True

                download.size = size

            self._activate_transfer(download, token)
            self._update_transfer(download)

            return TransferResponse(allowed=True, token=token)

        download = self.transfers.get(username + virtual_path)
        cancel_reason = TransferRejectReason.CANCELLED

        if download is not None:
            if download.status == TransferStatus.FINISHED:
                # SoulseekQt sends "Complete" as the reason for rejecting the download if it exists
                cancel_reason = TransferRejectReason.COMPLETE

        elif self.can_upload(username):
            # Check if download exists in our default download folder
            _file_path, file_exists = self.get_complete_download_file_path(username, virtual_path, size)

            if file_exists:
                cancel_reason = TransferRejectReason.COMPLETE
            else:
                # If this file is not in your download queue, then it must be
                # a remotely initiated download and someone is manually uploading to you
                parent_folder_path = virtual_path.replace("/", "\\").split("\\")[-2]
                received_folder_path = os.path.normpath(os.path.expandvars(config.sections["transfers"]["uploaddir"]))
                folder_path = os.path.join(received_folder_path, username, parent_folder_path)

                transfer = Transfer(username, virtual_path, folder_path, size)

                self._append_transfer(transfer)
                self._activate_transfer(transfer, token)
                self._update_transfer(transfer)

                return TransferResponse(allowed=True, token=token)

        log.add_transfer("Denied file request: user %s, message %s", (username, msg))
        return TransferResponse(allowed=False, reason=cancel_reason, token=token)

    def _transfer_timeout(self, transfer):

        if transfer.request_timer_id is None:
            return

        log.add_transfer("Download %s with token %s for user %s timed out",
                         (transfer.virtual_path, transfer.token, transfer.username))

        super()._transfer_timeout(transfer)

    def _download_file_error(self, username, token, error):
        """Networking thread encountered a local file error for download."""

        download = self.active_users.get(username, {}).get(token)

        if download is None:
            return

        self._abort_transfer(download, status=TransferStatus.LOCAL_FILE_ERROR)
        log.add(_("Download I/O error: %s"), error)

    def _file_transfer_init(self, msg):
        """A peer is requesting to start uploading a file to us."""

        if msg.is_outgoing:
            # Upload init message sent to ourselves, ignore
            return

        username = msg.username
        token = msg.token
        download = self.active_users.get(username, {}).get(token)

        if download is None or download.sock is not None:
            return

        virtual_path = download.virtual_path
        incomplete_folder_path = self.get_incomplete_download_folder()
        sock = download.sock = msg.sock
        need_update = True
        download_started = False

        log.add_transfer("Received file download init with token %s for file %s from user %s",
                         (token, virtual_path, username))

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
            self._abort_transfer(download, status=TransferStatus.DOWNLOAD_FOLDER_ERROR)
            core.notifications.show_download_notification(
                str(error), title=_("Download Folder Error"), high_priority=True)
            need_update = False

        else:
            download.file_handle = file_handle
            download.last_byte_offset = offset
            download.start_time = time.monotonic() - download.time_elapsed
            download.retry_attempt = False

            core.statistics.append_stat_value("started_downloads", 1)
            download_started = True

            log.add_download(
                _("Download started: user %(user)s, file %(file)s"), {
                    "user": username,
                    "file": file_handle.name.decode("utf-8", "replace")
                }
            )

            if download.size > offset:
                download.status = TransferStatus.TRANSFERRING
                core.send_message_to_network_thread(DownloadFile(
                    sock=sock, token=token, file=file_handle, leftbytes=(download.size - offset)
                ))
                core.send_message_to_peer(username, FileOffset(sock, offset))

            else:
                self._finish_transfer(download)
                need_update = False

        if need_update:
            self._update_transfer(download)

        if download_started:
            # Must be emitted after the final update to prevent inconsistent state
            core.pluginhandler.download_started_notification(username, virtual_path, incomplete_file_path)

    def _upload_denied(self, msg):
        """Peer code 50."""

        username = msg.username
        virtual_path = msg.file
        reason = msg.reason
        queued_downloads = self.queued_users.get(username, {})
        download = queued_downloads.get(virtual_path)

        if download is None:
            return

        if reason in TransferStatus.__dict__.values():
            # Don't allow internal statuses as reason
            reason = TransferRejectReason.CANCELLED

        if reason == TransferRejectReason.FILE_NOT_SHARED and not download.legacy_attempt:
            # The peer is possibly using an old client that doesn't support Unicode
            # (Soulseek NS). Attempt to request file name encoded as latin-1 once.

            log.add_transfer("User %s responded with reason '%s' for download request %s. "
                             "Attempting to request file as latin-1.", (username, reason, virtual_path))

            self._dequeue_transfer(download)
            download.legacy_attempt = True

            if self._enqueue_transfer(download):
                self._update_transfer(download)

            return

        if (reason in {TransferRejectReason.TOO_MANY_FILES, TransferRejectReason.TOO_MANY_MEGABYTES}
                or reason.startswith("User limit of")):
            # Make limited downloads appear as queued, and automatically resume them later
            reason = TransferRejectReason.QUEUED
            self._user_queue_limits[username] = max(5, len(queued_downloads) - 1)

        self._abort_transfer(download, status=reason)
        self._update_transfer(download)

        log.add_transfer("Download request denied by user %s for file %s. Reason: %s",
                         (username, virtual_path, msg.reason))

    def _upload_failed(self, msg):
        """Peer code 46."""

        username = msg.username
        virtual_path = msg.file
        download = self.transfers.get(username + virtual_path)

        if download is None:
            return

        if (download.token not in self.active_users.get(username, {})
                and virtual_path not in self.failed_users.get(username, {})
                and virtual_path not in self.queued_users.get(username, {})):
            return

        if download.status in {TransferStatus.DOWNLOAD_FOLDER_ERROR, TransferStatus.LOCAL_FILE_ERROR}:
            # Local error, no need to retry
            return

        if not download.retry_attempt:
            # Attempt to request file name encoded as latin-1 once

            # We mark download as failed when aborting it, to avoid a redundant request
            # to unwatch the user. Need to call _unfail_transfer() to undo this.
            self._abort_transfer(download, status=TransferStatus.CONNECTION_CLOSED)
            self._unfail_transfer(download)

            download.legacy_attempt = download.retry_attempt = True

            if self._enqueue_transfer(download):
                self._update_transfer(download)

            return

        # Already failed once previously, give up
        self._abort_transfer(download, status=TransferStatus.CONNECTION_CLOSED)
        download.retry_attempt = False

        log.add_transfer("Upload attempt by user %s for file %s failed. Reason: %s",
                         (virtual_path, username, download.status))

    def _file_download_progress(self, username, token, bytes_left, speed=None):
        """A file download is in progress."""

        download = self.active_users.get(username, {}).get(token)

        if download is None:
            return

        if download.request_timer_id is not None:
            events.cancel_scheduled(download.request_timer_id)
            download.request_timer_id = None

        self._update_transfer_progress(
            download, stat_id="downloaded_size",
            current_byte_offset=(download.size - bytes_left), speed=speed
        )
        self._update_transfer(download)

    def _file_connection_closed(self, username, token, sock, **_unused):
        """A file download connection has closed for any reason."""

        download = self.active_users.get(username, {}).get(token)

        if download is None:
            return

        if download.sock != sock:
            return

        if download.current_byte_offset is not None and download.current_byte_offset >= download.size:
            self._finish_transfer(download)
            return

        if core.users.statuses.get(download.username) == UserStatus.OFFLINE:
            status = TransferStatus.USER_LOGGED_OFF
        else:
            status = TransferStatus.CANCELLED

        self._abort_transfer(download, status=status)

    def _place_in_queue_response(self, msg):
        """Peer code 44.

        The peer tells us our place in queue for a particular transfer
        """

        username = msg.username
        virtual_path = msg.filename
        download = self.queued_users.get(username, {}).get(virtual_path)

        if download is None:
            return

        download.queue_position = msg.place
        self._update_transfer(download, update_parent=False)
