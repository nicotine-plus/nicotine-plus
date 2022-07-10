# COPYRIGHT (C) 2020-2022 Nicotine+ Contributors
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2016 Mutnick <muhing@yahoo.com>
# COPYRIGHT (C) 2013 eL_vErDe <gandalf@le-vert.net>
# COPYRIGHT (C) 2008-2012 Quinox <quinox@users.sf.net>
# COPYRIGHT (C) 2009 Hedonist <ak@sensi.org>
# COPYRIGHT (C) 2006-2009 Daelstorm <daelstorm@gmail.com>
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

""" This module contains classes that deal with file transfers:
the transfer manager.
"""

import json
import os
import os.path
import re
import stat
import threading
import time

from collections import defaultdict
from collections import deque
from collections import OrderedDict

from pynicotine import slskmessages
from pynicotine.logfacility import log
from pynicotine.slskmessages import increment_token
from pynicotine.utils import execute_command
from pynicotine.utils import clean_file
from pynicotine.utils import clean_path
from pynicotine.utils import encode_path
from pynicotine.utils import get_result_bitrate_length
from pynicotine.utils import human_speed
from pynicotine.utils import load_file
from pynicotine.utils import truncate_string_byte
from pynicotine.utils import write_file_and_backup


class Transfer:
    """ This class holds information about a single transfer """

    __slots__ = ("sock", "user", "filename",
                 "path", "token", "size", "file", "start_time", "last_update",
                 "current_byte_offset", "last_byte_offset", "speed", "time_elapsed",
                 "time_left", "modifier", "queue_position", "bitrate", "length",
                 "iterator", "status", "legacy_attempt", "size_changed")

    def __init__(self, user=None, filename=None, path=None, status=None, token=None, size=0,
                 current_byte_offset=None, bitrate=None, length=None):
        self.user = user
        self.filename = filename
        self.path = path
        self.size = size
        self.status = status
        self.token = token
        self.current_byte_offset = current_byte_offset
        self.bitrate = bitrate
        self.length = length

        self.sock = None
        self.file = None
        self.queue_position = 0
        self.modifier = None
        self.start_time = None
        self.last_update = None
        self.last_byte_offset = None
        self.speed = None
        self.time_elapsed = 0
        self.time_left = None
        self.iterator = None
        self.legacy_attempt = False
        self.size_changed = False


class Transfers:
    """ This is the transfers manager """

    def __init__(self, core, config, queue, network_callback, ui_callback=None):

        self.core = core
        self.config = config
        self.queue = queue
        self.allow_saving_transfers = False
        self.downloads = deque()
        self.uploads = deque()
        self.privileged_users = set()
        self.requested_folders = defaultdict(dict)
        self.transfer_request_times = {}
        self.upload_speed = 0
        self.token = 0

        self.user_update_counter = 0
        self.user_update_counters = {}

        self.downloads_file_name = os.path.join(self.config.data_dir, 'downloads.json')
        self.uploads_file_name = os.path.join(self.config.data_dir, 'uploads.json')

        self.network_callback = network_callback
        self.download_queue_timer_count = -1
        self.upload_queue_timer_count = -1
        self.downloadsview = None
        self.uploadsview = None

        if hasattr(ui_callback, "downloads"):
            self.downloadsview = ui_callback.downloads

        if hasattr(ui_callback, "uploads"):
            self.uploadsview = ui_callback.uploads

        self.update_download_filters()

    def init_transfers(self):

        self.add_stored_transfers("downloads")
        self.add_stored_transfers("uploads")

        if self.downloadsview:
            self.downloadsview.init_transfers(self.downloads)

        if self.uploadsview:
            self.uploadsview.init_transfers(self.uploads)

        self.allow_saving_transfers = True

    def server_login(self):

        self.requested_folders.clear()
        self.update_limits()
        self.watch_stored_downloads()

        # Check for transfer timeouts
        thread = threading.Thread(target=self._check_transfer_timeouts)
        thread.name = "TransferTimeoutTimer"
        thread.daemon = True
        thread.start()

        # Check for failed downloads (1 min delay)
        thread = threading.Thread(target=self._check_download_queue_timer)
        thread.name = "DownloadQueueTimer"
        thread.daemon = True
        thread.start()

        # Check if queued uploads can be started
        thread = threading.Thread(target=self._check_upload_queue_timer)
        thread.name = "UploadQueueTimer"
        thread.daemon = True
        thread.start()

        if self.downloadsview:
            self.downloadsview.server_login()

        if self.uploadsview:
            self.uploadsview.server_login()

    """ Load Transfers """

    def get_download_queue_file_name(self):

        data_dir = self.config.data_dir
        downloads_file_json = os.path.join(data_dir, 'downloads.json')
        downloads_file_1_4_2 = os.path.join(data_dir, 'config.transfers.pickle')
        downloads_file_1_4_1 = os.path.join(data_dir, 'transfers.pickle')

        if os.path.exists(encode_path(downloads_file_json)):
            # New file format
            return downloads_file_json

        if os.path.exists(encode_path(downloads_file_1_4_2)):
            # Nicotine+ 1.4.2+
            return downloads_file_1_4_2

        if os.path.exists(encode_path(downloads_file_1_4_1)):
            # Nicotine <=1.4.1
            return downloads_file_1_4_1

        # Fall back to new file format
        return downloads_file_json

    def get_upload_list_file_name(self):

        data_dir = self.config.data_dir
        uploads_file_json = os.path.join(data_dir, 'uploads.json')

        return uploads_file_json

    @staticmethod
    def load_transfers_file(transfers_file):
        """ Loads a file of transfers in json format """

        transfers_file = encode_path(transfers_file)

        if not os.path.isfile(transfers_file):
            return None

        with open(transfers_file, encoding="utf-8") as handle:
            return json.load(handle)

    @staticmethod
    def load_legacy_transfers_file(transfers_file):
        """ Loads a download queue file in pickle format (legacy) """

        transfers_file = encode_path(transfers_file)

        if not os.path.isfile(transfers_file):
            return None

        with open(transfers_file, "rb") as handle:
            from pynicotine.utils import RestrictedUnpickler
            return RestrictedUnpickler(handle, encoding="utf-8").load()

    def load_transfers(self, transfer_type):

        load_func = self.load_transfers_file

        if transfer_type == "uploads":
            transfers_file = self.get_upload_list_file_name()
        else:
            transfers_file = self.get_download_queue_file_name()

        if transfer_type == "downloads" and not transfers_file.endswith("downloads.json"):
            load_func = self.load_legacy_transfers_file

        return load_file(transfers_file, load_func)

    def add_stored_transfers(self, transfer_type):

        transfers = self.load_transfers(transfer_type)

        if not transfers:
            return

        if transfer_type == "uploads":
            transfer_list = self.uploads
        else:
            transfer_list = self.downloads

        for transfer_row in transfers:
            # User / filename / path

            if len(transfer_row) < 3:
                continue

            user = transfer_row[0]

            if not isinstance(user, str):
                continue

            filename = transfer_row[1]

            if not isinstance(filename, str):
                continue

            path = transfer_row[2]

            if not isinstance(path, str):
                continue

            # Status

            try:
                loaded_status = str(transfer_row[3])
            except IndexError:
                loaded_status = None

            if transfer_type == "uploads" and loaded_status != "Finished":
                # Only finished uploads are supposed to be restored
                continue

            if loaded_status in ("Aborted", "Paused"):
                status = "Paused"

            elif loaded_status in ("Filtered", "Finished"):
                status = loaded_status

            else:
                status = "User logged off"

            # Size / offset

            try:
                size = int(transfer_row[4])
            except Exception:
                size = 0

            try:
                current_byte_offset = int(transfer_row[5])
            except Exception:
                current_byte_offset = None

            # Bitrate / length

            bitrate = length = None

            try:
                loaded_bitrate = transfer_row[6]

                if loaded_bitrate is not None:
                    bitrate = str(loaded_bitrate)
            except IndexError:
                pass

            try:
                loaded_length = transfer_row[7]

                if loaded_length is not None:
                    length = str(loaded_length)
            except IndexError:
                pass

            transfer_list.appendleft(
                Transfer(
                    user=user, filename=filename, path=path, status=status, size=size,
                    current_byte_offset=current_byte_offset, bitrate=bitrate, length=length
                )
            )

    def watch_stored_downloads(self):
        """ When logging in, we request to watch the status of our downloads """

        users = set()

        for download in self.downloads:
            if download.status in ("Filtered", "Finished"):
                continue

            users.add(download.user)

        for user in users:
            self.core.watch_user(user)

    """ Privileges """

    def set_privileged_users(self, user_list):
        for user in user_list:
            self.add_to_privileged(user)

    def add_to_privileged(self, user):
        self.privileged_users.add(user)

    def remove_from_privileged(self, user):
        if user in self.privileged_users:
            self.privileged_users.remove(user)

    def is_privileged(self, user):

        if not user:
            return False

        if user in self.privileged_users:
            return True

        return self.is_buddy_prioritized(user)

    def is_buddy_prioritized(self, user):

        if not user:
            return False

        for row in self.config.sections["server"]["userlist"]:
            if not row or not isinstance(row, list):
                continue

            if user == str(row[0]):
                # All users
                if self.config.sections["transfers"]["preferfriends"]:
                    return True

                # Only explicitly prioritized users
                try:
                    return bool(row[3])  # Prioritized column
                except IndexError:
                    return False

        return False

    """ File Actions """

    @staticmethod
    def get_file_size(filename):

        try:
            size = os.path.getsize(encode_path(filename))
        except Exception:
            # file doesn't exist (remote files are always this)
            size = 0

        return size

    @staticmethod
    def close_file(file_handle, transfer):

        transfer.file = None

        if file_handle is None:
            return

        try:
            file_handle.close()

        except Exception as error:
            log.add_transfer("Failed to close file %(filename)s: %(error)s", {
                "filename": file_handle.name.decode("utf-8", "replace"),
                "error": error
            })

    """ Limits """

    def _update_regular_limits(self):
        """ Sends the regular speed limits to the networking thread """

        uselimit = self.config.sections["transfers"]["uselimit"]
        uploadlimit = self.config.sections["transfers"]["uploadlimit"]
        limitby = self.config.sections["transfers"]["limitby"]

        self.queue.append(slskmessages.SetUploadLimit(uselimit, uploadlimit, limitby))
        self.queue.append(slskmessages.SetDownloadLimit(self.config.sections["transfers"]["downloadlimit"]))

    def _update_alt_limits(self):
        """ Sends the alternative speed limits to the networking thread """

        uselimit = True
        uploadlimit = self.config.sections["transfers"]["uploadlimitalt"]
        limitby = self.config.sections["transfers"]["limitby"]

        self.queue.append(slskmessages.SetUploadLimit(uselimit, uploadlimit, limitby))
        self.queue.append(slskmessages.SetDownloadLimit(self.config.sections["transfers"]["downloadlimitalt"]))

    def update_limits(self):

        if self.config.sections["transfers"]["usealtlimits"]:
            self._update_alt_limits()
            return

        self._update_regular_limits()

    def queue_limit_reached(self, user):

        file_limit = self.config.sections["transfers"]["filelimit"]
        queue_size_limit = self.config.sections["transfers"]["queuelimit"] * 1024 * 1024

        if not file_limit and not queue_size_limit:
            return False, None

        num_files = 0
        queue_size = 0

        for upload in self.uploads:
            if upload.user != user or upload.status != "Queued":
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

        upload_slot_limit = self.config.sections["transfers"]["uploadslots"]

        if upload_slot_limit <= 0:
            upload_slot_limit = 1

        num_in_progress = 0
        active_statuses = ("Getting status", "Transferring")

        for upload in self.uploads:
            if upload.status in active_statuses:
                num_in_progress += 1

                if num_in_progress >= upload_slot_limit:
                    return True

        return False

    def bandwidth_limit_reached(self):

        bandwidth_limit = self.config.sections["transfers"]["uploadbandwidth"] * 1024

        if not bandwidth_limit:
            return False

        bandwidth_sum = 0

        for upload in self.uploads:
            if upload.sock is not None and upload.speed is not None:
                bandwidth_sum += upload.speed

                if bandwidth_sum >= bandwidth_limit:
                    return True

        return False

    def allow_new_uploads(self):

        if self.core.shares.rescanning:
            return False

        if self.config.sections["transfers"]["useupslots"]:
            # Limit by upload slots
            if self.slot_limit_reached():
                return False

        else:
            # Limit by maximum bandwidth
            if self.bandwidth_limit_reached():
                return False

        # No limits
        return True

    def file_is_upload_queued(self, user, filename):

        statuses = ("Queued", "Getting status", "Transferring")

        return next(
            (upload.filename == filename and upload.status in statuses and upload.user == user
             for upload in self.uploads), False
        )

    @staticmethod
    def file_is_readable(filename, real_path):

        try:
            if os.access(encode_path(real_path), os.R_OK):
                return True

            log.add_transfer("Cannot access file, not sharing: %(virtual_name)s with real path %(path)s", {
                "virtual_name": filename,
                "path": real_path
            })

        except Exception:
            log.add_transfer(("Requested file path contains invalid characters or other errors, not sharing: "
                              "%(virtual_name)s with real path %(path)s"), {
                "virtual_name": filename,
                "path": real_path
            })

        return False

    """ Network Events """

    def get_user_status(self, msg):
        """ Server code: 7 """
        """ We get a status of a user and if he's online, we request a file from him """

        update = False
        username = msg.user
        user_offline = (msg.status <= 0)
        download_statuses = ("Queued", "Getting status", "Too many files", "Too many megabytes", "Pending shutdown.",
                             "User logged off", "Connection timeout", "Remote file error", "Cancelled")
        upload_statuses = ("Getting status", "Disallowed extension", "User logged off", "Connection timeout",
                           "Cancelled")

        for download in reversed(self.downloads.copy()):
            if (download.user == username
                    and (download.status in download_statuses or download.status.startswith("User limit of"))):
                if user_offline:
                    download.status = "User logged off"
                    self.abort_transfer(download)
                    update = True

                elif download.status == "User logged off":
                    self.get_file(username, download.filename, path=download.path, transfer=download, ui_callback=False)
                    update = True

        if self.downloadsview and update:
            self.downloadsview.update_model()

        update = False

        # We need a copy due to upload auto-clearing modifying the deque during iteration
        for upload in reversed(self.uploads.copy()):
            if upload.user == username and upload.status in upload_statuses:
                if user_offline:
                    upload.status = "User logged off"
                    self.abort_transfer(upload)
                    self.auto_clear_upload(upload)
                    update = True

                elif upload.status == "User logged off":
                    upload.status = "Cancelled"
                    self.auto_clear_upload(upload)
                    update = True

        if self.uploadsview and update:
            self.uploadsview.update_model()

    def get_cant_connect_queue_file(self, username, filename):
        """ We can't connect to the user, either way (QueueUpload). """

        for download in self.downloads:
            if download.filename != filename or download.user != username:
                continue

            download.status = "Connection timeout"
            download.token = None

            self.update_download(download)
            self.core.watch_user(username)
            break

    def get_cant_connect_upload(self, token):
        """ We can't connect to the user, either way (TransferRequest, FileUploadInit). """

        for upload in self.uploads:
            if upload.token != token:
                continue

            upload.status = "Connection timeout"
            upload.token = None
            upload.queue_position = 0

            self.update_user_counter(upload.user)
            self.update_upload(upload)

            self.core.watch_user(upload.user)
            self.check_upload_queue()
            return

    def folder_contents_response(self, msg, check_num_files=True):
        """ Peer code: 37 """
        """ When we got a contents of a folder, get all the files in it, but
        skip the files in subfolders """

        username = msg.init.target_user
        file_list = msg.list

        log.add_transfer("Received response for folder content request from user %s", username)

        for i in file_list:
            for directory in file_list[i]:
                if os.path.commonprefix([i, directory]) != directory:
                    continue

                files = file_list[i][directory][:]
                num_files = len(files)

                if check_num_files and num_files > 100 and self.downloadsview:
                    self.downloadsview.download_large_folder(username, directory, num_files, msg)
                    return

                destination = self.get_folder_destination(username, directory)

                if self.config.sections["transfers"]["reverseorder"]:
                    files.sort(key=lambda x: x[1], reverse=True)

                log.add_transfer(("Attempting to download files in folder %(folder)s for user %(user)s. "
                                  "Destination path: %(destination)s"), {
                    "folder": directory,
                    "user": username,
                    "destination": destination
                })

                for file in files:
                    virtualpath = directory.rstrip('\\') + '\\' + file[1]
                    size = file[2]
                    h_bitrate, _bitrate, h_length, _length = get_result_bitrate_length(size, file[4])

                    self.get_file(
                        username, virtualpath, path=destination,
                        size=size, bitrate=h_bitrate, length=h_length)

                if directory in self.requested_folders.get(username, []):
                    del self.requested_folders[username][directory]

    def queue_upload(self, msg):
        """ Peer code: 43 """
        """ Peer remotely queued a download (upload here). This is the modern replacement to
        a TransferRequest with direction 0 (download request). We will initiate the upload of
        the queued file later. """

        log.add_msg_contents(msg)

        user = msg.init.target_user
        filename = msg.file

        log.add_transfer("Received upload request for file %(filename)s from user %(user)s", {
            "user": user,
            "filename": filename,
        })

        real_path = self.core.shares.virtual2real(filename)
        allowed, reason = self.check_queue_upload_allowed(user, msg.init.addr, filename, real_path, msg)

        log.add_transfer(("Upload request for file %(filename)s from user %(user)s: "
                          "allowed: %(allowed)s, reason: %(reason)s"), {
            "filename": filename,
            "user": user,
            "allowed": allowed,
            "reason": reason
        })

        if not allowed:
            if reason and reason != "Queued":
                self.core.send_message_to_peer(user, slskmessages.UploadDenied(file=filename, reason=reason))

            return

        transfer = Transfer(user=user, filename=filename, path=os.path.dirname(real_path),
                            status="Queued", size=self.get_file_size(real_path))
        self.append_upload(user, filename, transfer)
        self.update_upload(transfer)

        self.core.pluginhandler.upload_queued_notification(user, filename, real_path)
        self.check_upload_queue()

    def transfer_request(self, msg):
        """ Peer code: 40 """

        log.add_msg_contents(msg)

        user = msg.init.target_user
        response = None

        if msg.direction == 1:
            response = self.transfer_request_downloads(msg)

            log.add_transfer(("Responding to download request %(token)s for file %(filename)s "
                              "from user %(user)s: allowed: %(allowed)s, reason: %(reason)s"), {
                "token": response.token, "filename": msg.file, "user": user,
                "allowed": response.allowed, "reason": response.reason
            })

        else:
            response = self.transfer_request_uploads(msg)

            if response is None:
                return

            log.add_transfer(("Responding to legacy upload request %(token)s for file %(filename)s "
                              "from user %(user)s: allowed: %(allowed)s, reason: %(reason)s"), {
                "token": response.token, "filename": msg.file, "user": user,
                "allowed": response.allowed, "reason": response.reason
            })

        self.core.send_message_to_peer(user, response)

    def transfer_request_downloads(self, msg):

        user = msg.init.target_user
        filename = msg.file
        size = msg.filesize
        token = msg.token

        log.add_transfer("Received download request %(token)s for file %(filename)s from user %(user)s", {
            "token": token,
            "filename": filename,
            "user": user
        })

        cancel_reason = "Cancelled"
        accepted = True

        for download in self.downloads:
            if download.filename != filename or download.user != user:
                continue

            status = download.status

            if status == "Finished":
                # SoulseekQt sends "Complete" as the reason for rejecting the download if it exists
                cancel_reason = "Complete"
                accepted = False
                break

            if status in ("Paused", "Filtered"):
                accepted = False
                break

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

            download.token = token
            download.status = "Getting status"
            self.transfer_request_times[download] = time.time()

            self.update_download(download)
            return slskmessages.TransferResponse(allowed=True, token=token)

        # Check if download exists in our default download folder
        if self.get_existing_download_path(user, filename, "", size):
            cancel_reason = "Complete"
            accepted = False

        # If this file is not in your download queue, then it must be
        # a remotely initiated download and someone is manually uploading to you
        if accepted and self.can_upload(user):
            path = ""
            if self.config.sections["transfers"]["uploadsinsubdirs"]:
                parentdir = filename.replace('/', '\\').split('\\')[-2]
                path = os.path.join(self.config.sections["transfers"]["uploaddir"], user, parentdir)

            transfer = Transfer(user=user, filename=filename, path=path, status="Queued",
                                size=size, token=msg.token)
            self.downloads.appendleft(transfer)
            self.update_download(transfer)
            self.core.watch_user(user)

            return slskmessages.TransferResponse(allowed=False, reason="Queued", token=transfer.token)

        log.add_transfer("Denied file request: User %(user)s, %(msg)s", {
            'user': user,
            'msg': str(vars(msg))
        })

        return slskmessages.TransferResponse(allowed=False, reason=cancel_reason, token=msg.token)

    def transfer_request_uploads(self, msg):
        """ Remote peer is requesting to download a file through your upload queue.
        Note that the QueueUpload peer message has replaced this method of requesting
        a download in most clients. """

        user = msg.init.target_user
        filename = msg.file

        log.add_transfer("Received legacy upload request %(token)s for file %(filename)s from user %(user)s", {
            "token": msg.token,
            "filename": filename,
            "user": user
        })

        # Is user allowed to download?
        real_path = self.core.shares.virtual2real(filename)
        allowed, reason = self.check_queue_upload_allowed(user, msg.init.addr, filename, real_path, msg)

        if not allowed:
            if reason:
                return slskmessages.TransferResponse(allowed=False, reason=reason, token=msg.token)

            return None

        # All checks passed, user can queue file!
        self.core.pluginhandler.upload_queued_notification(user, filename, real_path)

        # Is user already downloading/negotiating a download?
        already_downloading = False
        active_statuses = ("Getting status", "Transferring")

        for upload in self.uploads:
            if upload.status not in active_statuses or upload.user != user:
                continue

            already_downloading = True
            break

        if not self.allow_new_uploads() or already_downloading:
            transfer = Transfer(user=user, filename=filename, path=os.path.dirname(real_path),
                                status="Queued", size=self.get_file_size(real_path))
            self.append_upload(user, filename, transfer)
            self.update_upload(transfer)

            return slskmessages.TransferResponse(allowed=False, reason="Queued", token=msg.token)

        # All checks passed, starting a new upload.
        size = self.get_file_size(real_path)
        transfer = Transfer(user=user, filename=filename, path=os.path.dirname(real_path),
                            status="Getting status", token=msg.token, size=size)

        self.transfer_request_times[transfer] = time.time()
        self.append_upload(user, filename, transfer)
        self.update_upload(transfer)

        return slskmessages.TransferResponse(allowed=True, token=msg.token, filesize=size)

    def transfer_response(self, msg):
        """ Peer code: 41 """
        """ Received a response to the file request from the peer """

        token = msg.token
        reason = msg.reason

        log.add_msg_contents(msg)
        log.add_transfer(("Received response for upload request %(token)s: allowed: %(allowed)s, "
                          "reason: %(reason)s, file size: %(size)s"), {
            "token": token,
            "allowed": msg.allowed,
            "reason": reason,
            "size": msg.filesize
        })

        if reason is not None:
            if reason in ("Getting status", "Transferring", "Paused", "Filtered", "User logged off"):
                # Don't allow internal statuses as reason
                reason = "Cancelled"

            for upload in self.uploads:
                if upload.token != token:
                    continue

                upload.status = reason
                upload.token = None
                upload.queue_position = 0

                self.update_upload(upload)

                if upload in self.transfer_request_times:
                    del self.transfer_request_times[upload]

                self.update_user_counter(upload.user)

                if reason in ("Complete", "Finished"):
                    # A complete download of this file already exists on the user's end
                    self.upload_finished(upload)

                elif reason in ("Cancelled", "Disallowed extension"):
                    self.auto_clear_upload(upload)

                self.check_upload_queue()
                return

            return

        for upload in self.uploads:
            if upload.token != token:
                continue

            self.core.send_message_to_peer(upload.user, slskmessages.FileUploadInit(None, token=token))
            self.check_upload_queue()
            return

        log.add_transfer("Received unknown upload response: %s", str(vars(msg)))

    def transfer_timeout(self, msg):

        transfer = msg.transfer

        if transfer.status == "Transferring":
            # Check if the transfer has started since the timeout callback was initiated
            return

        log.add_transfer("Transfer %(filename)s with token %(token)s for user %(user)s timed out", {
            "filename": transfer.filename,
            "token": transfer.token,
            "user": transfer.user
        })

        transfer.status = "Connection timeout"
        transfer.token = None

        self.core.watch_user(transfer.user)

        if transfer in self.downloads:
            self.update_download(transfer)

        elif transfer in self.uploads:
            transfer.queue_position = 0
            self.update_user_counter(transfer.user)
            self.update_upload(transfer)

        if transfer in self.transfer_request_times:
            del self.transfer_request_times[transfer]

        self.check_upload_queue()

    def download_file_error(self, msg):
        """ Networking thread encountered a local file error for download """

        log.add_msg_contents(msg)

        sock = msg.sock

        for download in self.downloads:
            if download.sock != sock:
                continue

            self.abort_transfer(download)
            download.status = "Local file error"

            log.add(_("I/O error: %s"), msg.error)
            self.update_download(download)
            return

    def upload_file_error(self, msg):
        """ Networking thread encountered a local file error for upload """

        log.add_msg_contents(msg)

        sock = msg.sock

        for upload in self.uploads:
            if upload.sock != sock:
                continue

            self.abort_transfer(upload)
            upload.status = "Local file error"

            log.add(_("I/O error: %s"), msg.error)
            self.update_upload(upload)
            self.check_upload_queue()
            return

    def file_download_init(self, msg):
        """ A peer is requesting to start uploading a file to us """

        log.add_msg_contents(msg)

        token = msg.token

        for download in self.downloads:
            if download.token != token:
                continue

            username = download.user
            filename = download.filename

            log.add_transfer(("Received file download init with token %(token)s for file %(filename)s "
                              "from user %(user)s"), {
                "token": token,
                "filename": filename,
                "user": username
            })

            if download.sock is not None:
                log.add_transfer("Download already has an existing file connection, ignoring init message")
                self.queue.append(slskmessages.ConnClose(msg.init.sock))
                return

            incomplete_folder = self.config.sections["transfers"]["incompletedir"]
            need_update = True
            download.sock = msg.init.sock
            download.token = None

            if download in self.transfer_request_times:
                del self.transfer_request_times[download]

            if not incomplete_folder:
                if download.path:
                    incomplete_folder = download.path
                else:
                    incomplete_folder = self.get_default_download_folder(username)

            try:
                incomplete_folder_encoded = encode_path(incomplete_folder)

                if not os.path.isdir(incomplete_folder_encoded):
                    os.makedirs(incomplete_folder_encoded)

                if not os.access(incomplete_folder_encoded, os.R_OK | os.W_OK | os.X_OK):
                    raise OSError("Download directory %s Permissions error.\nDir Permissions: %s" %
                                  (incomplete_folder, oct(os.stat(incomplete_folder_encoded)[stat.ST_MODE] & 0o777)))

            except OSError as error:
                log.add(_("OS error: %s"), error)
                self.download_folder_error(download, error)

            else:
                file_handle = None
                try:
                    incomplete_path = self.get_incomplete_file_path(incomplete_folder, username, filename)
                    file_handle = open(encode_path(incomplete_path), 'ab+')  # pylint: disable=consider-using-with

                    if self.config.sections["transfers"]["lock"]:
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
                    log.add(_("Download I/O error: %s"), error)

                    self.abort_transfer(download)
                    download.status = "Local file error"

                else:
                    download.file = file_handle
                    download.last_byte_offset = offset
                    download.queue_position = 0
                    download.last_update = time.time()
                    download.start_time = download.last_update - download.time_elapsed

                    self.core.statistics.append_stat_value("started_downloads", 1)
                    self.core.pluginhandler.download_started_notification(username, filename, incomplete_path)

                    log.add_download(
                        _("Download started: user %(user)s, file %(file)s"), {
                            "user": username,
                            "file": file_handle.name.decode("utf-8", "replace")
                        }
                    )

                    if download.size > offset:
                        download.status = "Transferring"
                        self.queue.append(slskmessages.DownloadFile(
                            sock=download.sock, file=file_handle, leftbytes=(download.size - offset)
                        ))
                        self.queue.append(slskmessages.FileOffset(init=msg.init, offset=offset))

                    else:
                        self.download_finished(download, file_handle=file_handle)
                        need_update = False

            if self.downloadsview:
                self.downloadsview.new_transfer_notification()

            if need_update:
                self.update_download(download)

            return

        # Support legacy transfer system (clients: old Nicotine+ versions, slskd)
        log.add_transfer(("Received unknown file download init message with token %s, checking if peer "
                          "requested us to upload a file instead"), token)
        self.file_upload_init(msg)

    def file_upload_init(self, msg):
        """ We are requesting to start uploading a file to a peer """

        log.add_msg_contents(msg)

        token = msg.token

        for upload in self.uploads:
            if upload.token != token:
                continue

            username = upload.user
            filename = upload.filename

            log.add_transfer("Initializing upload with token %(token)s for file %(filename)s to user %(user)s", {
                "token": token,
                "filename": filename,
                "user": username
            })

            if upload.sock is not None:
                log.add_transfer("Upload already has an existing file connection, ignoring init message")
                self.queue.append(slskmessages.ConnClose(msg.init.sock))
                return

            need_update = True
            upload.sock = msg.init.sock
            upload.token = None
            file_handle = None

            if upload in self.transfer_request_times:
                del self.transfer_request_times[upload]

            real_path = self.core.shares.virtual2real(filename)

            if not self.core.shares.file_is_shared(username, filename, real_path):
                upload.status = "File not shared."

                self.abort_transfer(upload)
                self.update_upload(upload)
                self.check_upload_queue()
                return

            try:
                # Open File
                file_handle = open(encode_path(real_path), "rb")  # pylint: disable=consider-using-with

            except OSError as error:
                log.add(_("Upload I/O error: %s"), error)
                upload.status = "Local file error"

                self.abort_transfer(upload)
                self.check_upload_queue()

            else:
                upload.file = file_handle
                upload.last_byte_offset = 0
                upload.queue_position = 0
                upload.last_update = time.time()
                upload.start_time = upload.last_update - upload.time_elapsed

                self.core.statistics.append_stat_value("started_uploads", 1)
                self.core.pluginhandler.upload_started_notification(username, filename, real_path)

                log.add_upload(
                    _("Upload started: user %(user)s, IP address %(ip)s, file %(file)s"), {
                        "user": username,
                        "ip": self.core.protothread.user_addresses.get(username),
                        "file": filename
                    }
                )

                if upload.size > 0:
                    upload.status = "Transferring"
                    self.queue.append(slskmessages.UploadFile(upload.sock, file=file_handle, size=upload.size))

                else:
                    self.upload_finished(upload, file_handle=file_handle)
                    need_update = False

            if self.uploadsview:
                self.uploadsview.new_transfer_notification()

            if need_update:
                self.update_upload(upload)

            return

        log.add_transfer("Unknown file upload init message with token %s", token)
        self.queue.append(slskmessages.ConnClose(msg.init.sock))

    def upload_denied(self, msg):
        """ Peer code: 50 """

        log.add_msg_contents(msg)

        user = msg.init.target_user
        filename = msg.file
        reason = msg.reason

        if reason in ("Getting status", "Transferring", "Paused", "Filtered", "User logged off", "Finished"):
            # Don't allow internal statuses as reason
            reason = "Cancelled"

        for download in self.downloads:
            if download.filename != filename or download.user != user:
                continue

            if download.status in ("Finished", "Paused"):
                # SoulseekQt also sends this message for finished downloads when unsharing files, ignore
                continue

            if reason in ("File not shared.", "File not shared", "Remote file error") and not download.legacy_attempt:
                # The peer is possibly using an old client that doesn't support Unicode
                # (Soulseek NS). Attempt to request file name encoded as latin-1 once.

                log.add_transfer("User %(user)s responded with reason '%(reason)s' for download request %(filename)s. "
                                 "Attempting to request file as latin-1.", {
                                     "user": user,
                                     "reason": reason,
                                     "filename": filename
                                 })

                self.abort_transfer(download)
                download.legacy_attempt = True
                self.get_file(user, filename, path=download.path, transfer=download)
                break

            if download.status == "Transferring":
                self.abort_transfer(download, reason=reason)

            download.status = reason
            self.update_download(download)

            log.add_transfer("Download request denied by user %(user)s for file %(filename)s. Reason: %(reason)s", {
                "user": user,
                "filename": filename,
                "reason": msg.reason
            })
            return

    def upload_failed(self, msg):
        """ Peer code: 46 """

        log.add_msg_contents(msg)

        user = msg.init.target_user
        filename = msg.file

        for download in self.downloads:
            if download.filename != filename or download.user != user:
                continue

            if download.status in ("Finished", "Paused", "Download folder error", "Local file error",
                                   "User logged off"):
                # Check if there are more transfers with the same virtual path
                continue

            should_retry = not download.legacy_attempt
            self.abort_transfer(download)

            if should_retry:
                # Attempt to request file name encoded as latin-1 once

                download.legacy_attempt = True
                self.get_file(user, filename, path=download.path, transfer=download)
                break

            # Already failed once previously, give up
            download.status = "Remote file error"
            self.update_download(download)

            log.add_transfer("Upload attempt by user %(user)s for file %(filename)s failed. Reason: %(reason)s", {
                "filename": filename,
                "user": user,
                "reason": download.status
            })
            return

    def file_download(self, msg):
        """ A file download is in progress """

        log.add_msg_contents(msg)

        sock = msg.sock
        need_update = True

        for download in self.downloads:
            if download.sock != sock:
                continue

            try:
                if download in self.transfer_request_times:
                    del self.transfer_request_times[download]

                current_time = time.time()
                download.current_byte_offset = current_byte_offset = (download.size - msg.leftbytes)

                download.status = "Transferring"
                old_elapsed = download.time_elapsed
                download.time_elapsed = current_time - download.start_time
                byte_difference = current_byte_offset - download.last_byte_offset

                if byte_difference:
                    self.core.statistics.append_stat_value("downloaded_size", byte_difference)

                if download.size > current_byte_offset or download.speed is None:
                    if current_byte_offset > download.last_byte_offset:
                        download.speed = int(max(0, byte_difference // max(1, current_time - download.last_update)))

                        if download.speed <= 0:
                            download.time_left = 0
                        else:
                            download.time_left = (download.size - download.current_byte_offset) / download.speed

                    if old_elapsed == download.time_elapsed:
                        need_update = False

                download.last_byte_offset = current_byte_offset
                download.last_update = current_time

            except OSError as error:
                log.add(_("Download I/O error: %s"), error)

                self.abort_transfer(download)
                download.status = "Local file error"

            if need_update:
                self.update_download(download)

            return

    def file_upload(self, msg):
        """ A file upload is in progress """

        log.add_msg_contents(msg)

        sock = msg.sock
        need_update = True

        for upload in self.uploads:
            if upload.sock != sock:
                continue

            if upload in self.transfer_request_times:
                del self.transfer_request_times[upload]

            current_time = time.time()
            upload.current_byte_offset = current_byte_offset = (msg.offset + msg.sentbytes)

            upload.status = "Transferring"
            old_elapsed = upload.time_elapsed
            upload.time_elapsed = current_time - upload.start_time
            byte_difference = current_byte_offset - upload.last_byte_offset

            if byte_difference:
                self.core.statistics.append_stat_value("uploaded_size", byte_difference)

            if upload.size > current_byte_offset or upload.speed is None:
                if current_byte_offset > upload.last_byte_offset:
                    upload.speed = int(max(0, byte_difference // max(1, current_time - upload.last_update)))

                    if upload.speed <= 0:
                        upload.time_left = 0
                    else:
                        upload.time_left = (upload.size - current_byte_offset) / upload.speed

                if old_elapsed == upload.time_elapsed:
                    need_update = False

            upload.last_byte_offset = current_byte_offset
            upload.last_update = current_time

            if need_update:
                self.update_upload(upload)

            return

    def download_conn_close(self, msg):
        """ The remote peer has closed a file transfer connection """

        log.add_msg_contents(msg)

        sock = msg.sock

        for download in self.downloads:
            if download.sock != sock:
                continue

            if download.current_byte_offset is not None and download.current_byte_offset >= download.size:
                self.download_finished(download, file_handle=download.file)
                return

            self.abort_transfer(download)

            if download.status != "Finished":
                if self.user_logged_out(download.user):
                    download.status = "User logged off"
                else:
                    download.status = "Cancelled"

            self.update_download(download)
            return

    def upload_conn_close(self, msg):
        """ The remote peer has closed a file transfer connection """

        log.add_msg_contents(msg)

        sock = msg.sock

        # We need a copy due to upload auto-clearing modifying the deque during iteration
        for upload in self.uploads.copy():
            if upload.sock != sock:
                continue

            if upload.current_byte_offset is not None and upload.current_byte_offset >= upload.size:
                # We finish the upload here in case the downloading peer has a slow/limited download
                # speed and finishes later than us

                if upload.speed is not None:
                    # Inform the server about the last upload speed for this transfer
                    log.add_transfer("Sending upload speed %s to the server", human_speed(upload.speed))
                    self.queue.append(slskmessages.SendUploadSpeed(upload.speed))

                self.upload_finished(upload, file_handle=upload.file)
                return

            if upload.status == "Finished":
                return

            self.abort_transfer(upload)

            if self.user_logged_out(upload.user):
                upload.status = "User logged off"
            else:
                upload.status = "Cancelled"

                # Transfer ended abruptly. Tell the peer to re-queue the file. If the transfer was
                # intentionally cancelled, the peer should ignore this message.
                self.core.send_message_to_peer(upload.user, slskmessages.UploadFailed(file=upload.filename))

            if not self.auto_clear_upload(upload):
                self.update_upload(upload)

            self.check_upload_queue()
            return

    def place_in_queue_request(self, msg):
        """ Peer code: 51 """

        log.add_msg_contents(msg)

        user = msg.init.target_user
        filename = msg.file
        privileged_user = self.is_privileged(user)
        queue_position = 0
        transfer = None

        if self.config.sections["transfers"]["fifoqueue"]:
            for upload in reversed(self.uploads):
                # Ignore non-queued files
                if upload.status != "Queued":
                    continue

                if not privileged_user or self.is_privileged(upload.user):
                    queue_position += 1

                # Stop counting on the matching file
                if upload.filename == filename and upload.user == user:
                    transfer = upload
                    break

        else:
            num_queued_users = len(self.user_update_counters)

            for upload in reversed(self.uploads):
                if upload.user != user:
                    continue

                # Ignore non-queued files
                if upload.status != "Queued":
                    continue

                queue_position += num_queued_users

                # Stop counting on the matching file
                if upload.filename == filename:
                    transfer = upload
                    break

        if queue_position > 0:
            self.queue.append(slskmessages.PlaceInQueue(init=msg.init, filename=filename, place=queue_position))

        if transfer is None:
            return

        # Update queue position in our list of uploads
        transfer.queue_position = queue_position
        self.update_upload(transfer, update_parent=False)

    def place_in_queue(self, msg):
        """ Peer code: 44 """
        """ The peer tells us our place in queue for a particular transfer """

        log.add_msg_contents(msg)

        username = msg.init.target_user
        filename = msg.filename

        for download in self.downloads:
            if download.filename == filename and download.status == "Queued" and download.user == username:
                download.queue_position = msg.place
                self.update_download(download, update_parent=False)
                return

    """ Transfer Actions """

    def get_folder(self, user, folder):
        self.core.send_message_to_peer(user, slskmessages.FolderContentsRequest(directory=folder))

    def get_file(self, user, filename, path="", transfer=None, size=0, bitrate=None, length=None, ui_callback=True):

        path = clean_path(path, absolute=True)

        if transfer is None:
            for download in self.downloads:
                if download.filename == filename and download.path == path and download.user == user:
                    if download.status == "Finished":
                        # Duplicate finished download found, verify that it's still present on disk later
                        transfer = download
                        break

                    # Duplicate active/cancelled download found, stop here
                    return

            else:
                transfer = Transfer(
                    user=user, filename=filename, path=path,
                    status="Queued", size=size, bitrate=bitrate,
                    length=length
                )
                self.downloads.appendleft(transfer)
        else:
            transfer.filename = filename
            transfer.status = "Queued"

        self.core.watch_user(user)

        if self.config.sections["transfers"]["enablefilters"]:
            try:
                downloadregexp = re.compile(self.config.sections["transfers"]["downloadregexp"], re.I)

                if downloadregexp.search(filename) is not None:
                    log.add_transfer("Filtering: %s", filename)
                    self.abort_transfer(transfer)
                    # The string to be displayed on the GUI
                    transfer.status = "Filtered"

                    if self.auto_clear_download(transfer):
                        return

            except Exception:
                pass

        if self.user_logged_out(user):
            transfer.status = "User logged off"

        elif transfer.status != "Filtered":
            download_path = self.get_existing_download_path(user, filename, path, size)

            if download_path:
                transfer.status = "Finished"
                transfer.size = transfer.current_byte_offset = size

                log.add_transfer("File %s is already downloaded", download_path)

            else:
                log.add_transfer("Adding file %(filename)s from user %(user)s to download queue", {
                    "filename": filename,
                    "user": user
                })
                self.core.send_message_to_peer(
                    user, slskmessages.QueueUpload(file=filename, legacy_client=transfer.legacy_attempt))

        if ui_callback:
            self.update_download(transfer)

    def push_file(self, user, filename, size, path="", transfer=None, bitrate=None, length=None, locally_queued=False):

        if not self.core.logged_in:
            return

        real_path = self.core.shares.virtual2real(filename)
        size_attempt = self.get_file_size(real_path)

        if size_attempt > 0:
            size = size_attempt

        if transfer is None:
            if not path:
                path = os.path.dirname(real_path)

            transfer = Transfer(
                user=user, filename=filename, path=path,
                status="Queued", size=size, bitrate=bitrate,
                length=length
            )
            self.append_upload(user, filename, transfer)
        else:
            transfer.filename = filename
            transfer.size = size
            transfer.status = "Queued"

        log.add_transfer("Initializing upload request for file %(file)s to user %(user)s", {
            'file': filename,
            'user': user
        })

        self.core.watch_user(user)

        if self.user_logged_out(user):
            transfer.status = "User logged off"

            if not self.auto_clear_upload(transfer):
                self.update_upload(transfer)
            return

        if not locally_queued:
            self.token = increment_token(self.token)
            transfer.token = self.token
            transfer.status = "Getting status"
            self.transfer_request_times[transfer] = time.time()

            log.add_transfer(("Requesting to upload file %(filename)s with token %(token)s to user %(user)s"), {
                "filename": filename,
                "token": transfer.token,
                "user": user
            })

            self.core.send_message_to_peer(
                user, slskmessages.TransferRequest(
                    direction=1, token=transfer.token, file=filename, filesize=size, realfile=real_path))

        self.update_upload(transfer)

    def append_upload(self, user, filename, transferobj):

        previously_queued = False
        old_index = 0

        if self.is_privileged(user):
            transferobj.modifier = "privileged" if user in self.privileged_users else "prioritized"

        for upload in self.uploads:
            if upload.filename == filename and upload.user == user:
                if upload.status == "Queued":
                    # This upload was queued previously
                    # Use the previous queue position
                    transferobj.queue_position = upload.queue_position
                    previously_queued = True

                if upload.status != "Finished":
                    transferobj.current_byte_offset = upload.current_byte_offset
                    transferobj.time_elapsed = upload.time_elapsed

                if upload in self.transfer_request_times:
                    del self.transfer_request_times[upload]

                self.uploads.remove(upload)

                if self.uploadsview:
                    self.uploadsview.remove_specific(upload, True)

                break

            old_index += 1

        if previously_queued:
            self.uploads.insert(old_index, transferobj)
            return

        if user not in self.user_update_counters:
            self.update_user_counter(user)

        self.uploads.appendleft(transferobj)

    def can_upload(self, user):

        transfers = self.config.sections["transfers"]

        if transfers["remotedownloads"]:

            if transfers["uploadallowed"] == 0:
                # No One can sent files to you
                return False

            if transfers["uploadallowed"] == 1:
                # Everyone can sent files to you
                return True

            if (transfers["uploadallowed"] == 2
                    and user in (x[0] for x in self.config.sections["server"]["userlist"])):
                # Users in userlist
                return True

            if transfers["uploadallowed"] == 3:
                # Trusted buddies
                for row in self.config.sections["server"]["userlist"]:
                    if row[0] == user and row[4]:
                        return True

        return False

    def user_logged_out(self, user):
        """ Check if a user who previously queued a file has logged out since """

        if not self.core.logged_in:
            return True

        try:
            return self.core.user_statuses[user] <= 0

        except (KeyError, TypeError):
            return False

    def get_folder_destination(self, user, directory, remove_prefix=""):

        if not remove_prefix and '\\' in directory:
            remove_prefix = directory.rsplit('\\', 1)[0]

        # Get the last folders in directory path, excluding remove_prefix
        target_folders = directory.replace(remove_prefix, "").lstrip('\\').replace('\\', os.sep)

        # Check if a custom download location was specified
        if (user in self.requested_folders and directory in self.requested_folders[user]
                and self.requested_folders[user][directory]):
            download_location = self.requested_folders[user].pop(directory)
        else:
            download_location = self.get_default_download_folder(user)

        # Merge download path with target folder name
        return os.path.join(download_location, target_folders)

    def get_total_uploads_allowed(self):

        if self.config.sections["transfers"]["useupslots"]:
            maxupslots = self.config.sections["transfers"]["uploadslots"]

            if maxupslots <= 0:
                maxupslots = 1

            return maxupslots

        lstlen = sum(1 for upload in self.uploads if upload.sock is not None)

        if self.allow_new_uploads():
            return lstlen + 1

        return lstlen or 1

    def get_upload_queue_size(self, username=None):

        if self.is_privileged(username):
            queue_size = 0

            for upload in self.uploads:
                if upload.status == "Queued" and self.is_privileged(upload.user):
                    queue_size += 1

            return queue_size

        return sum(1 for upload in self.uploads if upload.status == "Queued")

    def get_default_download_folder(self, user):

        downloaddir = self.config.sections["transfers"]["downloaddir"]

        # Check if username subfolders should be created for downloads
        if self.config.sections["transfers"]["usernamesubfolders"]:
            try:
                downloaddir = os.path.join(downloaddir, clean_file(user))
                downloaddir_encoded = encode_path(downloaddir)

                if not os.path.isdir(downloaddir_encoded):
                    os.makedirs(downloaddir_encoded)

            except Exception as error:
                log.add(_("Unable to save download to username subfolder, falling back "
                          "to default download folder. Error: %s") % error)

        return downloaddir

    def get_download_destination(self, user, virtual_path, target_path):
        """ Returns the download destination of a virtual file path """

        folder_path = target_path if target_path else self.get_default_download_folder(user)
        basename = clean_file(virtual_path.replace('/', '\\').split('\\')[-1])

        return folder_path, basename

    def get_existing_download_path(self, user, virtual_path, target_path, size, always_return=False):
        """ Returns the download path of a previous download, if available """

        folder, basename = self.get_download_destination(user, virtual_path, target_path)
        basename_root, extension = os.path.splitext(basename)
        download_path = os.path.join(folder, basename)
        counter = 1

        while os.path.isfile(encode_path(download_path)):
            if os.stat(encode_path(download_path)).st_size == size:
                # Found a previous download with a matching file size
                return download_path

            basename = basename_root + " (" + str(counter) + ")" + extension
            download_path = os.path.join(folder, basename)
            counter += 1

        if always_return:
            # Get a download path even if it doesn't exist anymore
            return download_path

        return None

    @staticmethod
    def get_incomplete_file_path(incomplete_folder, username, virtual_path):
        """ Returns the path to store a download while it's still transferring """

        from hashlib import md5
        md5sum = md5()
        md5sum.update((virtual_path + username).encode('utf-8'))
        prefix = "INCOMPLETE" + md5sum.hexdigest()

        # Ensure file name doesn't exceed 255 bytes in length
        base_name, extension = os.path.splitext(clean_file(virtual_path.replace('/', '\\').split('\\')[-1]))
        base_name_limit = 255 - len(prefix) - len(extension.encode('utf-8'))
        base_name = truncate_string_byte(base_name, base_name_limit)

        if base_name_limit < 0:
            extension = truncate_string_byte(extension, 255 - len(prefix))

        return os.path.join(incomplete_folder, prefix + base_name + extension)

    @staticmethod
    def get_renamed(name):
        """ When a transfer is finished, we remove INCOMPLETE~ or INCOMPLETE
        prefix from the file's name.

        Checks if a file with the same name already exists, and adds a number
        to the file name if that's the case. """

        filename, extension = os.path.splitext(name)
        counter = 1

        while os.path.exists(encode_path(name)):
            name = filename + " (" + str(counter) + ")" + extension
            counter += 1

        return name

    def file_downloaded_actions(self, user, filepath):

        config = self.config.sections

        if config["notifications"]["notification_popup_file"]:
            self.core.notifications.new_text_notification(
                _("%(file)s downloaded from %(user)s") % {
                    'user': user,
                    'file': filepath.rsplit(os.sep, 1)[1]
                },
                title=_("File downloaded")
            )

        if config["transfers"]["afterfinish"]:
            try:
                execute_command(config["transfers"]["afterfinish"], filepath)
                log.add(_("Executed: %s"), config["transfers"]["afterfinish"])

            except Exception:
                log.add(_("Trouble executing '%s'"), config["transfers"]["afterfinish"])

    def folder_downloaded_actions(self, user, folderpath):

        # walk through downloads and break if any file in the same folder exists, else execute
        statuses = ("Finished", "Paused", "Filtered")

        for download in self.downloads:
            if download.path == folderpath and download.status not in statuses:
                return

        config = self.config.sections

        if not folderpath:
            return

        if config["notifications"]["notification_popup_folder"]:
            self.core.notifications.new_text_notification(
                _("%(folder)s downloaded from %(user)s") % {
                    'user': user,
                    'folder': folderpath
                },
                title=_("Folder downloaded")
            )

        if config["transfers"]["afterfolder"]:
            try:
                execute_command(config["transfers"]["afterfolder"], folderpath)
                log.add(_("Executed on folder: %s"), config["transfers"]["afterfolder"])

            except Exception:
                log.add(_("Trouble executing on folder: %s"), config["transfers"]["afterfolder"])

    def download_folder_error(self, transfer, error):

        self.abort_transfer(transfer)
        transfer.status = "Download folder error"

        self.core.notifications.new_text_notification(
            _("OS error: %s") % error, title=_("Download folder error"))

    def download_finished(self, transfer, file_handle=None):

        self.close_file(file_handle, transfer)

        folder, basename = self.get_download_destination(transfer.user, transfer.filename, transfer.path)
        folder_encoded = encode_path(folder)
        newname = self.get_renamed(os.path.join(folder, basename))

        try:
            if not os.path.isdir(folder_encoded):
                os.makedirs(folder_encoded)

            import shutil
            shutil.move(file_handle.name, encode_path(newname))

        except OSError as error:
            log.add(
                _("Couldn't move '%(tempfile)s' to '%(file)s': %(error)s"), {
                    'tempfile': file_handle.name.decode("utf-8", "replace"),
                    'file': newname,
                    'error': error
                }
            )
            self.download_folder_error(transfer, error)
            self.update_download(transfer)
            return

        transfer.status = "Finished"
        transfer.current_byte_offset = transfer.size
        transfer.time_left = 0
        transfer.sock = None

        self.core.statistics.append_stat_value("completed_downloads", 1)

        # Attempt to show notification and execute commands
        self.file_downloaded_actions(transfer.user, newname)
        self.folder_downloaded_actions(transfer.user, transfer.path)

        if self.downloadsview:
            # Main tab highlight (bright)
            self.downloadsview.new_transfer_notification(finished=True)

        # Attempt to autoclear this download, if configured
        if not self.auto_clear_download(transfer):
            self.update_download(transfer)

        self.core.pluginhandler.download_finished_notification(transfer.user, transfer.filename, newname)

        log.add_download(
            _("Download finished: user %(user)s, file %(file)s"), {
                'user': transfer.user,
                'file': transfer.filename
            }
        )

    def upload_finished(self, transfer, file_handle=None):

        self.close_file(file_handle, transfer)

        transfer.status = "Finished"
        transfer.current_byte_offset = transfer.size
        transfer.time_left = 0
        transfer.sock = None

        self.update_user_counter(transfer.user)

        log.add_upload(
            _("Upload finished: user %(user)s, IP address %(ip)s, file %(file)s"), {
                'user': transfer.user,
                'ip': self.core.protothread.user_addresses.get(transfer.user),
                'file': transfer.filename
            }
        )

        self.core.statistics.append_stat_value("completed_uploads", 1)

        # Autoclear this upload
        if not self.auto_clear_upload(transfer):
            self.update_upload(transfer)

        real_path = self.core.shares.virtual2real(transfer.filename)
        self.core.pluginhandler.upload_finished_notification(transfer.user, transfer.filename, real_path)

        self.check_upload_queue()

    def auto_clear_download(self, transfer):

        if self.config.sections["transfers"]["autoclear_downloads"]:
            self.downloads.remove(transfer)

            if self.downloadsview:
                self.downloadsview.remove_specific(transfer, True)

            return True

        return False

    def auto_clear_upload(self, transfer):

        if self.config.sections["transfers"]["autoclear_uploads"]:
            self.uploads.remove(transfer)

            if self.uploadsview:
                self.uploadsview.remove_specific(transfer, True)

            return True

        return False

    def update_download(self, transfer, update_parent=True):

        if self.downloadsview:
            self.downloadsview.update_model(transfer, update_parent=update_parent)

    def update_upload(self, transfer, update_parent=True):

        if self.uploadsview:
            self.uploadsview.update_model(transfer, update_parent=update_parent)

    def _check_transfer_timeouts(self):

        while True:
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
                        self.network_callback([slskmessages.TransferTimeout(transfer)])

            if self.core.protothread.exit.wait(1):
                # Event set, we're exiting
                return

    def _check_upload_queue_timer(self):

        self.upload_queue_timer_count = -1

        while True:
            self.upload_queue_timer_count += 1
            self.network_callback([slskmessages.CheckUploadQueue()])

            if self.core.protothread.exit.wait(10):
                # Event set, we're exiting
                return

    def _check_download_queue_timer(self):

        self.download_queue_timer_count = -1

        while True:
            self.download_queue_timer_count += 1
            self.network_callback([slskmessages.CheckDownloadQueue()])

            if self.core.protothread.exit.wait(60):
                # Event set, we're exiting
                return

    def check_queue_upload_allowed(self, user, addr, filename, real_path, msg):

        # Is user allowed to download?
        ip_address, _port = addr
        checkuser, reason = self.core.network_filter.check_user(user, ip_address)

        if not checkuser:
            return False, reason

        if self.core.shares.rescanning:
            self.core.shares.pending_network_msgs.append(msg)
            return False, None

        # Is that file already in the queue?
        if self.file_is_upload_queued(user, filename):
            return False, "Queued"

        # Has user hit queue limit?
        enable_limits = True

        if self.config.sections["transfers"]["friendsnolimits"]:
            friend = user in (x[0] for x in self.config.sections["server"]["userlist"])

            if friend:
                enable_limits = False

        if enable_limits:
            limit_reached, reason = self.queue_limit_reached(user)

            if limit_reached:
                return False, reason

        # Do we actually share that file with the world?
        if (not self.core.shares.file_is_shared(user, filename, real_path)
                or not self.file_is_readable(filename, real_path)):
            return False, "File not shared."

        return True, None

    def check_download_queue_callback(self, _msg):
        """ Find failed or stuck downloads and attempt to queue them. Also ask for the queue
        position of downloads. """

        statuslist_failed = ("Connection timeout", "Local file error", "Remote file error")
        statuslist_limited = ("Too many files", "Too many megabytes")
        reset_count = False

        for download in reversed(self.downloads):
            status = download.status

            if (self.download_queue_timer_count >= 12
                    and (status in statuslist_limited or status.startswith("User limit of"))):
                # Re-queue limited downloads every 12 minutes

                log.add_transfer("Re-queuing file %(filename)s from user %(user)s in download queue", {
                    "filename": download.filename,
                    "user": download.user
                })
                reset_count = True

                self.abort_transfer(download)
                self.get_file(download.user, download.filename, path=download.path, transfer=download)

            if self.download_queue_timer_count % 3 == 0:
                if status in statuslist_failed:
                    # Retry failed downloads every 3 minutes

                    self.abort_transfer(download)
                    self.get_file(download.user, download.filename, path=download.path, transfer=download)

                if status == "Queued":
                    # Request queue position every 3 minutes

                    self.core.send_message_to_peer(
                        download.user,
                        slskmessages.PlaceInQueueRequest(file=download.filename, legacy_client=download.legacy_attempt)
                    )

        # Save list of downloads to file every one minute
        self.save_transfers("downloads")

        if reset_count:
            self.download_queue_timer_count = 0

    def get_upload_candidate(self):
        """ Retrieve a suitable queued transfer for uploading.
        Round Robin: Get the first queued item from the oldest user
        FIFO: Get the first queued item in the list """

        round_robin_queue = not self.config.sections["transfers"]["fifoqueue"]
        active_statuses = ("Getting status", "Transferring")
        privileged_queue = False

        first_queued_transfers = OrderedDict()
        queued_users = {}
        uploading_users = set()

        for upload in reversed(self.uploads):
            if upload.status == "Queued":
                user = upload.user

                if user not in first_queued_transfers and user not in uploading_users:
                    first_queued_transfers[user] = upload

                if user in queued_users:
                    continue

                privileged = self.is_privileged(user)
                queued_users[user] = privileged

            elif upload.status in active_statuses:
                # We're currently uploading a file to the user
                user = upload.user

                if user in uploading_users:
                    continue

                uploading_users.add(user)

                if user in first_queued_transfers:
                    del first_queued_transfers[user]

        oldest_time = None
        target_user = None

        for user, privileged in queued_users.items():
            if privileged and user not in uploading_users:
                privileged_queue = True
                break

        if not round_robin_queue:
            # skip the looping below (except the cleanup) and get the first
            # user of the highest priority we saw above
            for user in first_queued_transfers:
                if privileged_queue and not queued_users[user]:
                    continue

                target_user = user
                break

        for user, update_time in self.user_update_counters.copy().items():
            if user not in queued_users:
                del self.user_update_counters[user]
                continue

            if not round_robin_queue or user in uploading_users:
                continue

            if privileged_queue and not queued_users[user]:
                continue

            if not oldest_time:
                oldest_time = update_time + 1

            if update_time < oldest_time:
                target_user = user
                oldest_time = update_time

        if not target_user:
            return None

        return first_queued_transfers[target_user]

    def check_upload_queue(self):
        """ Find next file to upload """

        if not self.uploads:
            # No uploads exist
            return

        if not self.allow_new_uploads():
            return

        upload_candidate = self.get_upload_candidate()

        if upload_candidate is None:
            return

        user = upload_candidate.user

        log.add_transfer(
            "Checked upload queue, attempting to upload file %(file)s to user %(user)s", {
                'file': upload_candidate.filename,
                'user': user
            }
        )

        self.push_file(
            user=user, filename=upload_candidate.filename, size=upload_candidate.size, transfer=upload_candidate
        )

    def check_upload_queue_callback(self, _msg):

        if self.upload_queue_timer_count % 6 == 0:
            # Save list of uploads to file every one minute
            self.save_transfers("uploads")

        if self.upload_queue_timer_count >= 18:
            # Re-queue timed out uploads every 3 minutes
            for upload in reversed(self.uploads):
                if upload.status == "Connection timeout":
                    upload.status = "Queued"
                    self.update_upload(upload)

            self.upload_queue_timer_count = 0

        self.check_upload_queue()

    def update_user_counter(self, user):
        """ Called when an upload associated with a user has changed. The user update counter
        is used by the Round Robin queue system to determine which user has waited the longest
        since their last download. """

        self.user_update_counter += 1
        self.user_update_counters[user] = self.user_update_counter

    def ban_user(self, user, ban_message=None):
        """ Ban a user, cancel all the user's uploads, send a 'Banned'
        message via the transfers, and clear the transfers from the
        uploads list. """

        if ban_message:
            banmsg = "Banned (%s)" % ban_message
        elif self.config.sections["transfers"]["usecustomban"]:
            banmsg = "Banned (%s)" % self.config.sections["transfers"]["customban"]
        else:
            banmsg = "Banned"

        for upload in self.uploads.copy():
            if upload.user != user:
                continue

            self.abort_transfer(upload, reason=banmsg, send_fail_message=True)

            if self.uploadsview:
                self.uploadsview.remove_specific(upload)

        self.core.network_filter.ban_user(user)

    def retry_download(self, transfer):

        if transfer.status in ("Transferring", "Finished"):
            return

        user = transfer.user

        self.abort_transfer(transfer)
        self.get_file(user, transfer.filename, path=transfer.path, transfer=transfer)

    def retry_upload(self, transfer):

        active_statuses = ["Getting status", "Transferring"]

        if transfer.status in active_statuses + ["Finished"]:
            # Don't retry active or finished uploads
            return

        user = transfer.user

        for upload in self.uploads:
            if upload.user != user:
                continue

            if upload.status in active_statuses:
                # User already has an active upload, queue the retry attempt
                if transfer.status != "Queued":
                    transfer.status = "Queued"
                    self.update_upload(transfer)
                return

        self.push_file(user, transfer.filename, transfer.size, transfer.path, transfer=transfer)

    def abort_transfer(self, transfer, reason="Cancelled", send_fail_message=False):

        transfer.legacy_attempt = False
        transfer.size_changed = False
        transfer.token = None
        transfer.queue_position = 0

        if transfer.sock is not None:
            self.queue.append(slskmessages.ConnClose(transfer.sock))
            transfer.sock = None

        if transfer in self.transfer_request_times:
            del self.transfer_request_times[transfer]

        if transfer.file is not None:
            self.close_file(transfer.file, transfer)

            if transfer in self.uploads:
                self.update_user_counter(transfer.user)
                self.check_upload_queue()
                log.add_upload(
                    _("Upload aborted, user %(user)s file %(file)s"), {
                        "user": transfer.user,
                        "file": transfer.filename
                    }
                )
            else:
                log.add_download(
                    _("Download aborted, user %(user)s file %(file)s"), {
                        "user": transfer.user,
                        "file": transfer.filename
                    }
                )

        elif send_fail_message and transfer in self.uploads and transfer.status == "Queued":
            self.core.send_message_to_peer(
                transfer.user, slskmessages.UploadDenied(file=transfer.filename, reason=reason))

    """ Filters """

    def update_download_filters(self):

        proccessedfilters = []
        outfilter = "(\\\\("
        failed = {}
        download_filters = sorted(self.config.sections["transfers"]["downloadfilters"])
        # Get Filters from config file and check their escaped status
        # Test if they are valid regular expressions and save error messages

        for item in download_filters:
            dfilter, escaped = item
            if escaped:
                dfilter = re.escape(dfilter)
                dfilter = dfilter.replace("\\*", ".*")
            else:
                # Avoid "Nothing to repeat" error
                dfilter = dfilter.replace("*", "\\*").replace("+", "\\+")

            try:
                re.compile("(" + dfilter + ")")
                outfilter += dfilter
                proccessedfilters.append(dfilter)

            except Exception as error:
                failed[dfilter] = error

            proccessedfilters.append(dfilter)

            if item is not download_filters[-1]:
                outfilter += "|"

        # Crop trailing pipes
        while outfilter[-1] == "|":
            outfilter = outfilter[:-1]

        outfilter += ")$)"
        try:
            re.compile(outfilter)
            self.config.sections["transfers"]["downloadregexp"] = outfilter
            # Send error messages for each failed filter to log window
            if failed:
                errors = ""

                for dfilter, error in failed.items():
                    errors += "Filter: %s Error: %s " % (dfilter, error)

                log.add(_("Error: %(num)d Download filters failed! %(error)s "), {'num': len(failed), 'error': errors})

        except Exception as error:
            # Strange that individual filters _and_ the composite filter both fail
            log.add(_("Error: Download Filter failed! Verify your filters. Reason: %s"), error)
            self.config.sections["transfers"]["downloadregexp"] = ""

    """ Exit """

    def abort_transfers(self):
        """ Stop all transfers on disconnect/shutdown """

        need_update = False

        for download in self.downloads:
            if download.status not in ("Finished", "Filtered", "Paused"):
                self.abort_transfer(download)
                download.status = "User logged off"
                need_update = True

        if self.downloadsview and need_update:
            self.downloadsview.update_model()

        need_update = False

        for upload in self.uploads.copy():
            if upload.status != "Finished":
                self.uploads.remove(upload)
                need_update = True

                if self.uploadsview:
                    self.uploadsview.remove_specific(upload, True, update_parent=False)

        if self.uploadsview and need_update:
            self.uploadsview.update_model()

        self.privileged_users.clear()
        self.requested_folders.clear()
        self.transfer_request_times.clear()
        self.user_update_counters.clear()

    def get_downloads(self):
        """ Get a list of downloads """
        return [
            [download.user, download.filename, download.path, download.status, download.size,
             download.current_byte_offset, download.bitrate, download.length]
            for download in reversed(self.downloads)
        ]

    def get_uploads(self):
        """ Get a list of finished uploads """
        return [
            [upload.user, upload.filename, upload.path, upload.status, upload.size, upload.current_byte_offset,
             upload.bitrate, upload.length]
            for upload in reversed(self.uploads) if upload.status == "Finished"
        ]

    def save_downloads_callback(self, filename):
        json.dump(self.get_downloads(), filename, ensure_ascii=False)

    def save_uploads_callback(self, filename):
        json.dump(self.get_uploads(), filename, ensure_ascii=False)

    def save_transfers(self, transfer_type):
        """ Save list of transfers """

        if not self.allow_saving_transfers:
            # Don't save if transfers didn't load properly!
            return

        if transfer_type == "uploads":
            transfers_file = self.uploads_file_name
            callback = self.save_uploads_callback
        else:
            transfers_file = self.downloads_file_name
            callback = self.save_downloads_callback

        self.config.create_data_folder()
        write_file_and_backup(transfers_file, callback)

    def server_disconnect(self):

        self.abort_transfers()

        if self.downloadsview:
            self.downloadsview.server_disconnect()

        if self.uploadsview:
            self.uploadsview.server_disconnect()

    def quit(self):

        self.save_transfers("downloads")
        self.save_transfers("uploads")


class Statistics:

    def __init__(self, config, ui_callback=None):

        self.config = config
        self.ui_callback = None
        self.session_stats = {}

        if hasattr(ui_callback, "statistics"):
            self.ui_callback = ui_callback.statistics

        for stat_id in self.config.defaults["statistics"]:
            self.session_stats[stat_id] = 0

    def append_stat_value(self, stat_id, stat_value):

        self.session_stats[stat_id] += stat_value
        self.config.sections["statistics"][stat_id] += stat_value
        self.update_ui(stat_id)

    def update_ui(self, stat_id):

        if self.ui_callback:
            stat_value = self.session_stats[stat_id]
            self.ui_callback.update_stat_value(stat_id, stat_value)

    def reset_stats(self):

        for stat_id in self.config.defaults["statistics"]:
            self.session_stats[stat_id] = 0
            self.config.sections["statistics"][stat_id] = 0

            self.update_ui(stat_id)
