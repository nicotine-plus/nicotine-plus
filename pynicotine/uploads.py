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
import time

from pynicotine import slskmessages
from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.logfacility import log
from pynicotine.transfers import Transfer
from pynicotine.transfers import Transfers
from pynicotine.utils import encode_path
from pynicotine.utils import human_speed


class Uploads(Transfers):

    def __init__(self):

        super().__init__(transfers_file_path=os.path.join(config.data_folder_path, "uploads.json"))

        self.pending_shutdown = False
        self.privileged_users = set()
        self.upload_speed = 0
        self.token = 0

        self.user_update_counter = 0
        self.user_update_counters = {}

        self._upload_queue_timer_id = None
        self._retry_failed_uploads_timer_id = None

        for event_name, callback in (
            ("add-privileged-user", self._add_to_privileged),
            ("file-upload-init", self._file_upload_init),
            ("file-upload-progress", self._file_upload_progress),
            ("peer-connection-error", self._peer_connection_error),
            ("place-in-queue-request", self._place_in_queue_request),
            ("queue-upload", self._queue_upload),
            ("remove-privileged-user", self._remove_from_privileged),
            ("schedule-quit", self._schedule_quit),
            ("transfer-request", self._transfer_request),
            ("transfer-response", self._transfer_response),
            ("upload-connection-closed", self._upload_connection_closed),
            ("upload-file-error", self._upload_file_error),
            ("user-stats", self._user_stats),
            ("user-status", self._user_status)
        ):
            events.connect(event_name, callback)

    def _schedule_quit(self, should_finish_uploads):

        if not should_finish_uploads:
            return

        self.pending_shutdown = True
        self.check_upload_queue()

    def _quit(self):

        super()._quit()

        self.upload_speed = 0
        self.token = 0

    def _server_login(self, msg):

        if not msg.success:
            return

        super()._server_login(msg)

        # Check if queued uploads can be started every 10 seconds
        self._upload_queue_timer_id = events.schedule(delay=10, callback=self.check_upload_queue, repeat=True)

        # Re-queue timed out uploads every 3 minutes
        self._retry_failed_uploads_timer_id = events.schedule(
            delay=180, callback=self.retry_failed_uploads, repeat=True)

    def _server_disconnect(self, msg):

        super()._server_disconnect(msg)

        for timer_id in (self._upload_queue_timer_id, self._retry_failed_uploads_timer_id):
            events.cancel_scheduled(timer_id)

        need_update = False

        for upload in self.transfers.copy():
            if upload.status != "Finished":
                need_update = True
                self.clear_upload(upload, update_parent=False)

        if need_update:
            events.emit("update-uploads")

        self.privileged_users.clear()
        self.user_update_counters.clear()
        self.user_update_counter = 0

        # Quit in case we were waiting for uploads to finish
        self.check_upload_queue()

    # Load Transfers #

    def load_transfers(self):
        self.add_stored_transfers(self.transfers_file_path, self.load_transfers_file, load_only_finished=True)

    # Privileges #

    def _add_to_privileged(self, username):
        self.privileged_users.add(username)

    def _remove_from_privileged(self, username):
        if username in self.privileged_users:
            self.privileged_users.remove(username)

    def is_privileged(self, username):

        if not username:
            return False

        if username in self.privileged_users:
            return True

        return self.is_buddy_prioritized(username)

    def is_buddy_prioritized(self, username):

        if not username:
            return False

        user_data = core.userlist.buddies.get(username)

        if user_data:
            # All users
            if config.sections["transfers"]["preferfriends"]:
                return True

            # Only explicitly prioritized users
            return bool(user_data.is_prioritized)

        return False

    # File Actions #

    @staticmethod
    def get_file_size(file_path):

        try:
            size = os.path.getsize(encode_path(file_path))
        except Exception:
            # file doesn't exist (remote files are always this)
            size = 0

        return size

    # Limits #

    def update_transfer_limits(self):

        events.emit("update-upload-limits")

        if core.user_status == slskmessages.UserStatus.OFFLINE:
            return

        use_speed_limit = config.sections["transfers"]["use_upload_speed_limit"]
        limit_by = config.sections["transfers"]["limitby"]

        if use_speed_limit == "primary":
            speed_limit = config.sections["transfers"]["uploadlimit"]

        elif use_speed_limit == "alternative":
            speed_limit = config.sections["transfers"]["uploadlimitalt"]

        else:
            speed_limit = 0

        core.send_message_to_network_thread(slskmessages.SetUploadLimit(speed_limit, limit_by))

    def queue_limit_reached(self, username):

        file_limit = config.sections["transfers"]["filelimit"]
        queue_size_limit = config.sections["transfers"]["queuelimit"] * 1024 * 1024

        if not file_limit and not queue_size_limit:
            return False, None

        num_files = 0
        queue_size = 0

        for upload in self.transfers:
            if upload.username != username or upload.status != "Queued":
                continue

            if file_limit:
                num_files += 1

                if num_files >= file_limit:
                    return True, "Too many files"

            if queue_size_limit:
                queue_size += upload.size

                if queue_size >= queue_size_limit:
                    return True, "Too many megabytes"

        return False, None

    def slot_limit_reached(self):

        upload_slot_limit = config.sections["transfers"]["uploadslots"]

        if upload_slot_limit <= 0:
            upload_slot_limit = 1

        num_in_progress = 0
        active_statuses = {"Getting status", "Transferring"}

        for upload in self.transfers:
            if upload.status in active_statuses:
                num_in_progress += 1

                if num_in_progress >= upload_slot_limit:
                    return True

        return False

    def bandwidth_limit_reached(self):

        bandwidth_limit = config.sections["transfers"]["uploadbandwidth"] * 1024

        if not bandwidth_limit:
            return False

        bandwidth_sum = 0

        for upload in self.transfers:
            if upload.sock is not None and upload.speed is not None:
                bandwidth_sum += upload.speed

                if bandwidth_sum >= bandwidth_limit:
                    return True

        return False

    def allow_new_uploads(self):

        if core.shares.rescanning:
            return False

        if config.sections["transfers"]["useupslots"]:
            # Limit by upload slots
            if self.slot_limit_reached():
                return False

        elif self.bandwidth_limit_reached():
            # Limit by maximum bandwidth
            return False

        # No limits
        return True

    def has_active_uploads(self):

        statuses = {"Queued", "Getting status", "Transferring"}

        return bool(next(
            (upload for upload in self.transfers if upload.status in statuses), None
        ))

    def file_is_upload_queued(self, username, virtual_path):

        statuses = {"Queued", "Getting status", "Transferring"}

        return bool(next(
            (upload for upload in self.transfers
             if upload.virtual_path == virtual_path and upload.status in statuses and upload.username == username), None
        ))

    @staticmethod
    def file_is_readable(virtual_path, real_path):

        try:
            if os.access(encode_path(real_path), os.R_OK):
                return True

            log.add_transfer("Cannot access file, not sharing: %(virtual_name)s with real path %(path)s", {
                "virtual_name": virtual_path,
                "path": real_path
            })

        except Exception:
            log.add_transfer(("Requested file path contains invalid characters or other errors, not sharing: "
                              "%(virtual_name)s with real path %(path)s"), {
                "virtual_name": virtual_path,
                "path": real_path
            })

        return False

    # Events #

    def _user_status(self, msg):
        """Server code 7.

        We get a status of a user and if he's online, we request a file
        from him
        """

        update = False
        username = msg.user
        privileged = msg.privileged
        user_offline = (msg.status == slskmessages.UserStatus.OFFLINE)
        upload_statuses = {"Getting status", "User logged off", "Connection timeout"}

        if privileged is not None:
            if privileged:
                events.emit("add-privileged-user", username)
            else:
                events.emit("remove-privileged-user", username)

        # We need a copy due to upload auto-clearing modifying the deque during iteration
        for upload in reversed(self.transfers.copy()):
            if upload.username == username and upload.status in upload_statuses:
                if user_offline:
                    if not self.auto_clear_upload(upload):
                        upload.status = "User logged off"
                        self.abort_upload(upload, abort_reason=None)

                    update = True

                elif upload.status == "User logged off":
                    if not self.auto_clear_upload(upload):
                        upload.status = "Cancelled"

                    update = True

        if update:
            events.emit("update-uploads")

    def _connect_to_peer(self, msg):
        """Server code 18."""

        if msg.privileged is None:
            return

        if msg.privileged:
            events.emit("add-privileged-user", msg.user)
        else:
            events.emit("remove-privileged-user", msg.user)

    def _user_stats(self, msg):
        """Server code 36."""

        if msg.user == core.login_username:
            self.upload_speed = msg.avgspeed

    def _peer_connection_error(self, username, msgs=None, is_offline=False):

        if msgs is None:
            return

        for msg in msgs:
            if msg.__class__ in (slskmessages.TransferRequest, slskmessages.FileUploadInit):
                self._cant_connect_upload(username, msg.token, is_offline)

    def _cant_connect_upload(self, username, token, is_offline):
        """We can't connect to the user, either way (TransferRequest,
        FileUploadInit)."""

        for upload in self.transfers:
            if upload.token != token or upload.username != username:
                continue

            log.add_transfer("Upload attempt for file %(filename)s with token %(token)s to user %(user)s timed out", {
                "filename": upload.virtual_path,
                "token": token,
                "user": username
            })

            if upload.sock is not None:
                log.add_transfer("Existing file connection for upload with token %s already exists?", token)
                return

            upload_cleared = is_offline and self.auto_clear_upload(upload)

            if not upload_cleared:
                self.abort_upload(upload, abort_reason="User logged off" if is_offline else "Connection timeout")

            core.watch_user(username)
            self.check_upload_queue()
            return

    def _queue_upload(self, msg):
        """Peer code 43.

        Peer remotely queued a download (upload here). This is the
        modern replacement to a TransferRequest with direction 0
        (download request). We will initiate the upload of the queued
        file later.
        """

        username = msg.init.target_user
        virtual_path = msg.file

        log.add_transfer("Received upload request for file %(filename)s from user %(user)s", {
            "user": username,
            "filename": virtual_path,
        })

        real_path = core.shares.virtual2real(virtual_path)
        allowed, reason = self.check_queue_upload_allowed(username, msg.init.addr, virtual_path, real_path, msg)

        log.add_transfer(("Upload request for file %(filename)s from user: %(user)s, "
                          "allowed: %(allowed)s, reason: %(reason)s"), {
            "filename": virtual_path,
            "user": username,
            "allowed": allowed,
            "reason": reason
        })

        if not allowed:
            if reason and reason != "Queued":
                core.send_message_to_peer(username, slskmessages.UploadDenied(file=virtual_path, reason=reason))

            return

        transfer = Transfer(username=username, virtual_path=virtual_path, folder_path=os.path.dirname(real_path),
                            status="Queued", size=self.get_file_size(real_path))
        self.append_upload(username, virtual_path, transfer)
        self.update_upload(transfer)

        core.pluginhandler.upload_queued_notification(username, virtual_path, real_path)
        self.check_upload_queue()

    def _transfer_request(self, msg):
        """Peer code 40."""

        username = msg.init.target_user

        if msg.direction != slskmessages.TransferDirection.DOWNLOAD:
            return

        response = self._transfer_request_uploads(msg)

        if response is None:
            return

        log.add_transfer(("Responding to legacy upload request %(token)s for file %(filename)s "
                          "from user %(user)s, allowed: %(allowed)s, reason: %(reason)s"), {
            "token": response.token, "filename": msg.file, "user": username,
            "allowed": response.allowed, "reason": response.reason
        })

        core.send_message_to_peer(username, response)

    def _transfer_request_uploads(self, msg):
        """Remote peer is requesting to download a file through your upload
        queue.

        Note that the QueueUpload peer message has replaced this method
        of requesting a download in most clients.
        """

        username = msg.init.target_user
        virtual_path = msg.file
        token = msg.token

        log.add_transfer("Received legacy upload request %(token)s for file %(filename)s from user %(user)s", {
            "token": token,
            "filename": virtual_path,
            "user": username
        })

        # Is user allowed to download?
        real_path = core.shares.virtual2real(virtual_path)
        allowed, reason = self.check_queue_upload_allowed(username, msg.init.addr, virtual_path, real_path, msg)

        if not allowed:
            if reason:
                return slskmessages.TransferResponse(allowed=False, reason=reason, token=token)

            return None

        # All checks passed, user can queue file!
        core.pluginhandler.upload_queued_notification(username, virtual_path, real_path)

        # Is user already downloading/negotiating a download?
        already_downloading = False
        active_statuses = {"Getting status", "Transferring"}

        for upload in self.transfers:
            if upload.status not in active_statuses or upload.username != username:
                continue

            already_downloading = True
            break

        if not self.allow_new_uploads() or already_downloading:
            transfer = Transfer(username=username, virtual_path=virtual_path, folder_path=os.path.dirname(real_path),
                                status="Queued", size=self.get_file_size(real_path))
            self.append_upload(username, virtual_path, transfer)
            self.update_upload(transfer)

            return slskmessages.TransferResponse(allowed=False, reason="Queued", token=token)

        # All checks passed, starting a new upload.
        size = self.get_file_size(real_path)
        transfer = Transfer(username=username, virtual_path=virtual_path, folder_path=os.path.dirname(real_path),
                            status="Getting status", token=token, size=size)

        self.transfer_request_times[transfer] = time.time()
        self.append_upload(username, virtual_path, transfer)
        self.update_upload(transfer)

        return slskmessages.TransferResponse(allowed=True, token=token, filesize=size)

    def _transfer_response(self, msg):
        """Peer code 41.

        Received a response to the file request from the peer
        """

        username = msg.init.target_user
        token = msg.token
        reason = msg.reason

        log.add_transfer(("Received response for upload with token: %(token)s, allowed: %(allowed)s, "
                          "reason: %(reason)s, file size: %(size)s"), {
            "token": token,
            "allowed": msg.allowed,
            "reason": reason,
            "size": msg.filesize
        })

        if reason is not None:
            if reason in {"Queued", "Getting status", "Transferring", "Paused", "Filtered", "User logged off"}:
                # Don't allow internal statuses as reason
                reason = "Cancelled"

            for upload in self.transfers:
                if upload.token != token or upload.username != username:
                    continue

                if upload.sock is not None:
                    log.add_transfer("Upload with token %s already has an existing file connection", token)
                    return

                self.abort_upload(upload, abort_reason=reason)

                if reason in {"Complete", "Finished"}:
                    # A complete download of this file already exists on the user's end
                    self.upload_finished(upload)

                elif reason in {"Cancelled", "Disallowed extension"}:
                    self.auto_clear_upload(upload)

                self.check_upload_queue()
                return

            return

        for upload in self.transfers:
            if upload.token != token or upload.username != username:
                continue

            if upload.sock is not None:
                log.add_transfer("Upload with token %s already has an existing file connection", token)
                return

            core.send_message_to_peer(upload.username, slskmessages.FileUploadInit(None, token=token))
            self.check_upload_queue()
            return

        log.add_transfer("Received unknown upload response: %s", msg)

    def _transfer_timeout(self, transfer):

        log.add_transfer("Upload %(filename)s with token %(token)s for user %(user)s timed out", {
            "filename": transfer.virtual_path,
            "token": transfer.token,
            "user": transfer.username
        })

        status = "Connection timeout"
        core.watch_user(transfer.username)

        self.abort_upload(transfer, abort_reason=status)

        if transfer in self.transfer_request_times:
            del self.transfer_request_times[transfer]

        self.check_upload_queue()

    def _upload_file_error(self, username, token, error):
        """Networking thread encountered a local file error for upload."""

        for upload in self.transfers:
            if upload.token != token or upload.username != username:
                continue

            self.abort_upload(upload, abort_reason="Local file error")

            log.add(_("Upload I/O error: %s"), error)
            self.check_upload_queue()
            return

    def _file_upload_init(self, msg):
        """We are requesting to start uploading a file to a peer."""

        username = msg.init.target_user
        token = msg.token

        for upload in self.transfers:
            if upload.token != token or upload.username != username:
                continue

            virtual_path = upload.virtual_path

            log.add_transfer("Initializing upload with token %(token)s for file %(filename)s to user %(user)s", {
                "token": token,
                "filename": virtual_path,
                "user": username
            })

            if upload.sock is not None:
                log.add_transfer("Upload already has an existing file connection, ignoring init message")
                core.send_message_to_network_thread(slskmessages.CloseConnection(msg.init.sock))
                return

            need_update = True
            upload.sock = msg.init.sock

            real_path = core.shares.virtual2real(virtual_path)

            if not core.shares.file_is_shared(username, virtual_path, real_path):
                self.abort_upload(upload, abort_reason="File not shared.")
                self.check_upload_queue()
                return

            try:
                # Open File
                file_handle = open(encode_path(real_path), "rb")  # pylint: disable=consider-using-with

            except OSError as error:
                log.add(_("Upload I/O error: %s"), error)
                self.abort_upload(upload, abort_reason="Local file error")
                self.check_upload_queue()

            else:
                upload.file_handle = file_handle
                upload.queue_position = 0
                upload.last_update = time.time()
                upload.start_time = upload.last_update - upload.time_elapsed

                core.statistics.append_stat_value("started_uploads", 1)
                core.pluginhandler.upload_started_notification(username, virtual_path, real_path)

                log.add_upload(
                    _("Upload started: user %(user)s, IP address %(ip)s, file %(file)s"), {
                        "user": username,
                        "ip": core.user_addresses.get(username),
                        "file": virtual_path
                    }
                )

                if upload.size > 0:
                    upload.status = "Transferring"
                    core.send_message_to_network_thread(slskmessages.UploadFile(
                        init=msg.init, token=token, file=file_handle, size=upload.size
                    ))

                else:
                    self.upload_finished(upload)
                    need_update = False

            events.emit("upload-notification")

            if need_update:
                self.update_upload(upload)

            return

        log.add_transfer("Unknown file upload init message with token %s", token)
        core.send_message_to_network_thread(slskmessages.CloseConnection(msg.init.sock))

    def _file_upload_progress(self, username, token, offset, bytes_sent):
        """A file upload is in progress."""

        for upload in self.transfers:
            if upload.token != token or upload.username != username:
                continue

            if upload in self.transfer_request_times:
                del self.transfer_request_times[upload]

            current_time = time.time()
            size = upload.size

            if not upload.last_byte_offset:
                upload.last_byte_offset = offset

            upload.status = "Transferring"
            upload.time_elapsed = current_time - upload.start_time
            upload.current_byte_offset = current_byte_offset = (offset + bytes_sent)
            byte_difference = current_byte_offset - upload.last_byte_offset

            if byte_difference:
                core.statistics.append_stat_value("uploaded_size", byte_difference)

                if size > current_byte_offset or upload.speed is None:
                    upload.speed = int(max(0, byte_difference // max(1, current_time - upload.last_update)))
                    upload.time_left = (size - current_byte_offset) // upload.speed if upload.speed else 0
                else:
                    upload.time_left = 0

            upload.last_byte_offset = current_byte_offset
            upload.last_update = current_time

            self.update_upload(upload)
            return

    def _upload_connection_closed(self, username, token, timed_out):
        """A file upload connection has closed for any reason."""

        # We need a copy due to upload auto-clearing modifying the deque during iteration
        for upload in self.transfers.copy():
            if upload.token != token or upload.username != username:
                continue

            if not timed_out and upload.current_byte_offset is not None and upload.current_byte_offset >= upload.size:
                # We finish the upload here in case the downloading peer has a slow/limited download
                # speed and finishes later than us

                if upload.speed is not None:
                    # Inform the server about the last upload speed for this transfer
                    log.add_transfer("Sending upload speed %s to the server", human_speed(upload.speed))
                    core.send_message_to_server(slskmessages.SendUploadSpeed(upload.speed))

                self.upload_finished(upload)
                return

            if upload.status == "Finished":
                return

            status = None

            if core.user_statuses.get(upload.username) == slskmessages.UserStatus.OFFLINE:
                status = "User logged off"
            else:
                status = "Cancelled"

                # Transfer ended abruptly. Tell the peer to re-queue the file. If the transfer was
                # intentionally cancelled, the peer should ignore this message.
                core.send_message_to_peer(upload.username, slskmessages.UploadFailed(file=upload.virtual_path))

            if not self.auto_clear_upload(upload):
                self.abort_upload(upload, abort_reason=status)

            self.check_upload_queue()
            return

    def _place_in_queue_request(self, msg):
        """Peer code 51."""

        username = msg.init.target_user
        virtual_path = msg.file
        privileged_user = self.is_privileged(username)
        queue_position = 0
        transfer = None

        if config.sections["transfers"]["fifoqueue"]:
            for upload in reversed(self.transfers):
                # Ignore non-queued files
                if upload.status != "Queued":
                    continue

                if not privileged_user or self.is_privileged(upload.username):
                    queue_position += 1

                # Stop counting on the matching file
                if upload.virtual_path == virtual_path and upload.username == username:
                    transfer = upload
                    break

        else:
            num_queued_users = len(self.user_update_counters)

            for upload in reversed(self.transfers):
                if upload.username != username:
                    continue

                # Ignore non-queued files
                if upload.status != "Queued":
                    continue

                queue_position += num_queued_users

                # Stop counting on the matching file
                if upload.virtual_path == virtual_path:
                    transfer = upload
                    break

        if queue_position > 0:
            core.send_message_to_peer(
                username, slskmessages.PlaceInQueueResponse(filename=virtual_path, place=queue_position))

        if transfer is None:
            return

        # Update queue position in our list of uploads
        transfer.queue_position = queue_position
        self.update_upload(transfer, update_parent=False)

    # Transfer Actions #

    def push_file(self, username, virtual_path, size, folder_path=None, transfer=None, locally_queued=False):

        real_path = core.shares.virtual2real(virtual_path)
        size_attempt = self.get_file_size(real_path)

        if folder_path:
            folder_path = os.path.normpath(folder_path)

        if size_attempt > 0:
            size = size_attempt

        if transfer is None:
            if not folder_path:
                folder_path = os.path.dirname(real_path)

            transfer = Transfer(
                username=username, virtual_path=virtual_path, folder_path=folder_path, status="Queued",
                size=size
            )
            self.append_upload(username, virtual_path, transfer)
        else:
            transfer.virtual_path = virtual_path
            transfer.size = size
            transfer.status = "Queued"
            transfer.token = None

        log.add_transfer("Initializing upload request for file %(file)s to user %(user)s", {
            "file": virtual_path,
            "user": username
        })

        core.watch_user(username)

        if slskmessages.UserStatus.OFFLINE in (core.user_status, core.user_statuses.get(username)):
            # Either we are offline or the user we want to upload to is
            transfer.status = "User logged off"

            if not self.auto_clear_upload(transfer):
                self.update_upload(transfer)
            return

        if not locally_queued:
            self.token = slskmessages.increment_token(self.token)
            transfer.token = self.token
            transfer.status = "Getting status"
            self.transfer_request_times[transfer] = time.time()

            log.add_transfer("Requesting to upload file %(filename)s with token %(token)s to user %(user)s", {
                "filename": virtual_path,
                "token": transfer.token,
                "user": username
            })

            core.send_message_to_peer(
                username, slskmessages.TransferRequest(
                    direction=slskmessages.TransferDirection.UPLOAD, token=transfer.token, file=virtual_path,
                    filesize=size, realfile=real_path))

        self.update_upload(transfer)

    def append_upload(self, username, virtual_path, transfer):

        previously_queued = False
        old_index = 0

        if self.is_privileged(username):
            transfer.modifier = "privileged" if username in self.privileged_users else "prioritized"

        for upload in self.transfers:
            if upload.virtual_path == virtual_path and upload.username == username:
                if upload.status == "Queued":
                    # This upload was queued previously
                    # Use the previous queue position
                    transfer.queue_position = upload.queue_position
                    previously_queued = True

                if upload.status != "Finished":
                    transfer.current_byte_offset = upload.current_byte_offset
                    transfer.time_elapsed = upload.time_elapsed
                    transfer.time_left = upload.time_left
                    transfer.speed = upload.speed

                if upload in self.transfer_request_times:
                    del self.transfer_request_times[upload]

                self.clear_upload(upload)
                break

            old_index += 1

        if previously_queued:
            self.transfers.insert(old_index, transfer)
            return

        self.transfers.appendleft(transfer)

    def get_total_uploads_allowed(self):

        if config.sections["transfers"]["useupslots"]:
            maxupslots = config.sections["transfers"]["uploadslots"]

            if maxupslots <= 0:
                maxupslots = 1

            return maxupslots

        lstlen = sum(1 for upload in self.transfers if upload.sock is not None)

        if self.allow_new_uploads():
            return lstlen + 1

        return lstlen or 1

    def get_upload_queue_size(self, username=None):

        if self.is_privileged(username):
            queue_size = 0

            for upload in self.transfers:
                if upload.status == "Queued" and self.is_privileged(upload.username):
                    queue_size += 1

            return queue_size

        return sum(1 for upload in self.transfers if upload.status == "Queued")

    def get_downloading_users(self):

        statuses = {"Queued", "Getting status", "Transferring"}
        users = set()

        for upload in self.transfers:
            if upload.status in statuses:
                users.add(upload.username)

        return users

    def upload_finished(self, transfer):

        self.close_file(transfer)

        if transfer in self.transfer_request_times:
            del self.transfer_request_times[transfer]

        transfer.status = "Finished"
        transfer.current_byte_offset = transfer.size
        transfer.sock = None
        transfer.token = None

        log.add_upload(
            _("Upload finished: user %(user)s, IP address %(ip)s, file %(file)s"), {
                "user": transfer.username,
                "ip": core.user_addresses.get(transfer.username),
                "file": transfer.virtual_path
            }
        )

        core.statistics.append_stat_value("completed_uploads", 1)

        # Autoclear this upload
        if not self.auto_clear_upload(transfer):
            self.update_upload(transfer)

        real_path = core.shares.virtual2real(transfer.virtual_path)
        core.pluginhandler.upload_finished_notification(transfer.username, transfer.virtual_path, real_path)

        self.check_upload_queue()

    def auto_clear_upload(self, upload):

        if config.sections["transfers"]["autoclear_uploads"]:
            self.update_user_counter(upload.username)
            self.clear_upload(upload)
            return True

        return False

    def update_upload(self, transfer, update_parent=True):

        username = transfer.username
        status = transfer.status

        events.emit("update-upload", transfer, update_parent)

        if status == "Queued" and username in self.user_update_counters:
            # Don't update existing user counter for queued uploads
            # We don't want to push the user back in the queue if they enqueued new files
            return

        if status == "Transferring":
            # Avoid unnecessary updates while transferring
            return

        self.update_user_counter(username)

    def _check_transfer_timeouts(self):

        current_time = time.time()

        if self.transfer_request_times:
            for transfer, start_time in self.transfer_request_times.copy().items():
                # When our port is closed, certain clients can take up to ~30 seconds before they
                # initiate a 'F' connection, since they only send an indirect connection request after
                # attempting to connect to our port for a certain time period.
                # Known clients: Nicotine+ 2.2.0 - 3.2.0, 2 s; Soulseek NS, ~20 s; soulseeX, ~30 s.
                # To account for potential delays while initializing the connection, add 15 seconds
                # to the timeout value.

                if (current_time - start_time) >= 45:
                    self._transfer_timeout(transfer)

    def check_queue_upload_allowed(self, username, addr, virtual_path, real_path, msg):

        # Is user allowed to download?
        ip_address, _port = addr
        permission_level, reject_reason = core.network_filter.check_user_permission(username, ip_address)

        if permission_level == "banned":
            return False, reject_reason

        if core.shares.rescanning:
            core.shares.pending_network_msgs.append(msg)
            return False, None

        # Is that file already in the queue?
        if self.file_is_upload_queued(username, virtual_path):
            return False, "Queued"

        # Are we waiting for existing uploads to finish?
        if self.pending_shutdown:
            return False, "Pending shutdown."

        # Has user hit queue limit?
        enable_limits = True

        if config.sections["transfers"]["friendsnolimits"]:
            if username in core.userlist.buddies:
                enable_limits = False

        if enable_limits:
            limit_reached, reason = self.queue_limit_reached(username)

            if limit_reached:
                return False, reason

        # Do we actually share that file with the world?
        if not core.shares.file_is_shared(username, virtual_path, real_path):
            return False, "File not shared."

        if not self.file_is_readable(virtual_path, real_path):
            return False, "File read error."

        return True, None

    def get_upload_candidate(self):
        """Retrieve a suitable queued transfer for uploading.

        Round Robin: Get the first queued item from the oldest user
        FIFO: Get the first queued item in the list
        """

        round_robin_queue = not config.sections["transfers"]["fifoqueue"]
        active_statuses = {"Getting status", "Transferring"}
        privileged_queue = False

        first_queued_transfers = {}
        queued_users = {}
        uploading_users = set()

        for upload in reversed(self.transfers):
            if upload.status == "Queued":
                username = upload.username

                if username not in first_queued_transfers and username not in uploading_users:
                    first_queued_transfers[username] = upload

                if username in queued_users:
                    continue

                privileged = self.is_privileged(username)
                queued_users[username] = privileged

            elif upload.status in active_statuses:
                # We're currently uploading a file to the user
                username = upload.username

                if username in uploading_users:
                    continue

                uploading_users.add(username)

                if username in first_queued_transfers:
                    del first_queued_transfers[username]

        has_active_uploads = bool(uploading_users)
        oldest_time = None
        target_username = None

        for username, privileged in queued_users.items():
            if privileged and username not in uploading_users:
                privileged_queue = True
                break

        if not round_robin_queue:
            # skip the looping below (except the cleanup) and get the first
            # user of the highest priority we saw above
            for username in first_queued_transfers:
                if privileged_queue and not queued_users[username]:
                    continue

                target_username = username
                break

        for username, update_time in self.user_update_counters.copy().items():
            if username not in queued_users:
                del self.user_update_counters[username]
                continue

            if not round_robin_queue or username in uploading_users:
                continue

            if privileged_queue and not queued_users[username]:
                continue

            if not oldest_time:
                oldest_time = update_time + 1

            if update_time < oldest_time:
                target_username = username
                oldest_time = update_time

        return first_queued_transfers.get(target_username), has_active_uploads

    def check_upload_queue(self):
        """Find next file to upload."""

        if not self.allow_new_uploads():
            return

        upload_candidate, has_active_uploads = self.get_upload_candidate()

        if upload_candidate is None:
            if not has_active_uploads and self.pending_shutdown:
                self.pending_shutdown = False
                core.quit()
            return

        username = upload_candidate.username

        log.add_transfer(
            "Checked upload queue, attempting to upload file %(file)s to user %(user)s", {
                "file": upload_candidate.virtual_path,
                "user": username
            }
        )

        self.push_file(
            username=username, virtual_path=upload_candidate.virtual_path, size=upload_candidate.size,
            transfer=upload_candidate
        )

    def update_user_counter(self, username):
        """Called when an upload associated with a user has changed.

        The user update counter is used by the Round Robin queue system
        to determine which user has waited the longest since their last
        download.
        """

        self.user_update_counter += 1
        self.user_update_counters[username] = self.user_update_counter

    def ban_users(self, users, ban_message=None):
        """Ban a user, cancel all the user's uploads, send a 'Banned' message
        via the transfers, and clear the transfers from the uploads list."""

        if not ban_message and config.sections["transfers"]["usecustomban"]:
            ban_message = config.sections["transfers"]["customban"]

        if ban_message:
            banmsg = f"Banned ({ban_message})"
        else:
            banmsg = "Banned"

        for upload in self.transfers.copy():
            if upload.username not in users:
                continue

            self.clear_upload(upload, denied_message=banmsg)

        for username in users:
            core.network_filter.ban_user(username)

        self.check_upload_queue()

    def retry_upload(self, transfer):

        active_statuses = {"Getting status", "Transferring"}

        if transfer.status in active_statuses.union({"Finished"}):
            # Don't retry active or finished uploads
            return

        username = transfer.username

        for upload in self.transfers:
            if upload.username != username:
                continue

            if upload.status in active_statuses:
                # User already has an active upload, queue the retry attempt
                if transfer.status != "Queued":
                    transfer.status = "Queued"
                    self.update_upload(transfer)
                return

        self.push_file(username, transfer.virtual_path, transfer.size, transfer=transfer)

    def retry_uploads(self, uploads):
        for upload in uploads:
            self.retry_upload(upload)

    def retry_failed_uploads(self):

        for upload in reversed(self.transfers):
            if upload.status == "Connection timeout":
                upload.status = "Queued"
                self.update_upload(upload)

    def abort_upload(self, upload, denied_message=None, abort_reason="Cancelled", update_parent=True):

        log.add_transfer(('Aborting upload, user "%(user)s", filename "%(filename)s", token "%(token)s", '
                          'status "%(status)s"'), {
            "user": upload.username,
            "filename": upload.virtual_path,
            "token": upload.token,
            "status": upload.status
        })

        upload.token = None
        upload.queue_position = 0

        if upload in self.transfer_request_times:
            del self.transfer_request_times[upload]

        if upload.sock is not None:
            core.send_message_to_network_thread(slskmessages.CloseConnection(upload.sock))
            upload.sock = None

        if upload.file_handle is not None:
            self.close_file(upload)

            log.add_upload(
                _("Upload aborted, user %(user)s file %(file)s"), {
                    "user": upload.username,
                    "file": upload.virtual_path
                }
            )

        elif denied_message and upload.status == "Queued":
            core.send_message_to_peer(
                upload.username, slskmessages.UploadDenied(file=upload.virtual_path, reason=denied_message))

        if abort_reason:
            upload.status = abort_reason

        events.emit("abort-upload", upload, abort_reason, update_parent)

    def abort_uploads(self, uploads, denied_message=None, abort_reason="Cancelled"):

        ignored_statuses = {abort_reason, "Finished"}

        for upload in uploads:
            if upload.status not in ignored_statuses:
                self.abort_upload(
                    upload, denied_message=denied_message, abort_reason=abort_reason, update_parent=False)

        events.emit("abort-uploads", uploads, abort_reason)

    def clear_upload(self, upload, denied_message=None, update_parent=True):

        self.abort_upload(upload, denied_message=denied_message, abort_reason=None)
        self.transfers.remove(upload)

        events.emit("clear-upload", upload, update_parent)

    def clear_uploads(self, uploads=None, statuses=None):

        if uploads is None:
            # Clear all uploads
            uploads = self.transfers

        for upload in uploads.copy():
            if statuses and upload.status not in statuses:
                continue

            self.clear_upload(upload, update_parent=False)

        events.emit("clear-uploads", uploads, statuses)
