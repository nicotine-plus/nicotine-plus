# COPYRIGHT (C) 2020-2022 Nicotine+ Team
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
from pynicotine.utils import get_result_bitrate_length
from pynicotine.utils import human_length
from pynicotine.utils import load_file
from pynicotine.utils import write_file_and_backup


class Transfer:
    """ This class holds information about a single transfer """

    __slots__ = ("sock", "user", "filename",
                 "path", "token", "size", "file", "start_time", "last_update",
                 "current_byte_offset", "last_byte_offset", "speed", "time_elapsed",
                 "time_left", "modifier", "queue_position", "bitrate", "length",
                 "iterator", "status", "legacy_attempt")

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
        self.time_elapsed = None
        self.time_left = None
        self.iterator = None
        self.legacy_attempt = False


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
        self.last_save_times = {"downloads": 0, "uploads": 0}
        self.transfer_request_times = {}
        self.upload_speed = 0
        self.token = 0

        self.user_update_counter = 0
        self.user_update_counters = {}

        self.downloads_file_name = os.path.join(self.config.data_dir, 'downloads.json')
        self.uploads_file_name = os.path.join(self.config.data_dir, 'uploads.json')

        self.network_callback = network_callback
        self.download_queue_timer_count = -1
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

        if os.path.exists(downloads_file_json):
            # New file format
            return downloads_file_json

        if os.path.exists(downloads_file_1_4_2):
            # Nicotine+ 1.4.2+
            return downloads_file_1_4_2

        if os.path.exists(downloads_file_1_4_1):
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

        if not os.path.isfile(transfers_file):
            return None

        with open(transfers_file, encoding="utf-8") as handle:
            return json.load(handle)

    @staticmethod
    def load_legacy_transfers_file(transfers_file):
        """ Loads a download queue file in pickle format (legacy) """

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

        for i in transfers:
            loaded_status = current_byte_offset = bitrate = length = None
            size = 0

            try:
                loaded_status = str(i[3])
            except Exception:
                pass

            try:
                size = int(i[4])
            except Exception:
                pass

            try:
                current_byte_offset = int(i[5])
            except Exception:
                pass

            try:
                loaded_bitrate = i[6]

                if loaded_bitrate is not None:
                    bitrate = str(loaded_bitrate)
            except Exception:
                pass

            try:
                loaded_length = i[7]

                if loaded_length is not None:
                    length = str(loaded_length)
            except Exception:
                pass

            if loaded_status in ("Aborted", "Paused"):
                status = "Paused"

            elif loaded_status in ("Filtered", "Finished"):
                status = loaded_status

            elif current_byte_offset is not None and current_byte_offset >= size:
                status = "Finished"

            else:
                status = "User logged off"

            if transfer_type == "uploads" and status != "Finished":
                # Only finished uploads are supposed to be restored
                continue

            transfer_list.appendleft(
                Transfer(
                    user=i[0], filename=i[1], path=i[2], status=status,
                    size=size, current_byte_offset=current_byte_offset, bitrate=bitrate,
                    length=length
                )
            )

    def watch_stored_downloads(self):
        """ When logging in, we request to watch the status of our downloads """

        users = set()

        for i in self.downloads:
            users.add(i.user)

            if i.status in ("Aborted", "Paused"):
                i.status = "Paused"

            elif i.status in ("Filtered", "Finished"):
                continue

            else:
                i.status = "Getting status"

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
            size = os.path.getsize(filename)
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
                "filename": file_handle.name,
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

        queue_size_limit = self.config.sections["transfers"]["queuelimit"] * 1024 * 1024

        if not queue_size_limit:
            return False

        queue_size = 0

        for i in self.uploads:
            if i.user == user and i.status == "Queued":
                queue_size += i.size

                if queue_size >= queue_size_limit:
                    return True

        return False

    def file_limit_reached(self, user):

        file_limit = self.config.sections["transfers"]["filelimit"]

        if not file_limit:
            return False

        num_files = 0

        for i in self.uploads:
            if i.user == user and i.status == "Queued":
                num_files += 1

                if num_files >= file_limit:
                    return True

        return False

    def slot_limit_reached(self):

        upload_slot_limit = self.config.sections["transfers"]["uploadslots"]

        if upload_slot_limit <= 0:
            upload_slot_limit = 1

        num_in_progress = 0
        active_statuses = ("Getting status", "Establishing connection", "Transferring")

        for i in self.uploads:
            if i.status in active_statuses:
                num_in_progress += 1

                if num_in_progress >= upload_slot_limit:
                    return True

        return False

    def bandwidth_limit_reached(self):

        bandwidth_limit = self.config.sections["transfers"]["uploadbandwidth"] * 1024

        if not bandwidth_limit:
            return False

        bandwidth_sum = 0

        for i in self.uploads:
            if i.speed is not None and i.sock is not None:
                bandwidth_sum += i.speed

                if bandwidth_sum >= bandwidth_limit:
                    return True

        return False

    def allow_new_uploads(self):

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

        statuses = ("Queued", "Getting status", "Establishing connection", "Transferring")

        for i in self.uploads:
            if i.user == user and i.filename == filename and i.status in statuses:
                return True

        return False

    """ Network Events """

    def get_user_status(self, msg):
        """ We get a status of a user and if he's online, we request a file from him """

        download_statuses = ("Queued", "Getting status", "Establishing connection", "Too many files",
                             "Too many megabytes", "Pending shutdown.", "User logged off", "Connection closed by peer",
                             "Cannot connect", "Remote file error")

        upload_statuses = ("Getting status", "Establishing connection", "Disallowed extension",
                           "User logged off", "Cannot connect", "Cancelled")

        for i in reversed(self.downloads.copy()):
            if msg.user == i.user and (i.status in download_statuses or i.status.startswith("User limit of")):
                if msg.status <= 0:
                    i.status = "User logged off"
                    self.abort_transfer(i)
                    self.update_download(i)

                elif i.status in ("Getting status", "User logged off", "Connection closed by peer", "Cannot connect"):
                    self.get_file(i.user, i.filename, i.path, i)

        # We need a copy due to upload auto-clearing modifying the deque during iteration
        for i in reversed(self.uploads.copy()):
            if msg.user == i.user and i.status in upload_statuses:
                if msg.status <= 0:
                    i.status = "User logged off"
                    self.abort_transfer(i)

                    if not self.auto_clear_upload(i):
                        self.update_upload(i)

                elif i.status == "User logged off":
                    i.status = "Cancelled"

                    if not self.auto_clear_upload(i):
                        self.update_upload(i)

    def get_cant_connect_request(self, token):
        """ We can't connect to the user, either way (FileRequest, TransferRequest). """

        for i in self.downloads:
            if i.token == token:
                self._get_cant_connect_download(i)
                break

        for i in self.uploads:
            if i.token == token:
                self._get_cant_connect_upload(i)
                break

    def get_cant_connect_queue_file(self, username, filename):
        """ We can't connect to the user, either way (QueueUpload). """

        for i in self.downloads:
            if i.user == username and i.filename == filename:
                self._get_cant_connect_download(i)
                break

    def _get_cant_connect_download(self, i):

        i.status = "Cannot connect"
        i.token = None

        self.update_download(i)
        self.core.watch_user(i.user)

    def _get_cant_connect_upload(self, i):

        i.status = "Cannot connect"
        i.token = None
        i.queue_position = 0

        self.update_user_counter(i.user)
        self.update_upload(i)

        self.core.watch_user(i.user)
        self.check_upload_queue()

    def folder_contents_response(self, msg):
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
                destination = self.get_folder_destination(username, directory)

                if self.config.sections["transfers"]["reverseorder"]:
                    files.sort(key=lambda x: x[1], reverse=True)

                log.add_transfer(
                    "Attempting to download files in folder %(folder)s for user %(user)s. "
                    + "Destination path: %(destination)s", {
                        "folder": directory,
                        "user": username,
                        "destination": destination
                    }
                )

                for file in files:
                    virtualpath = directory.rstrip('\\') + '\\' + file[1]
                    size = file[2]
                    h_bitrate, _bitrate, h_length, _length = get_result_bitrate_length(size, file[4])

                    self.get_file(
                        username, virtualpath, destination,
                        size=size, bitrate=h_bitrate, length=h_length)

                if directory in self.requested_folders.get(username, []):
                    del self.requested_folders[username][directory]

    def queue_upload(self, msg):
        """ Peer remotely queued a download (upload here). This is the modern replacement to
        a TransferRequest with direction 0 (download request). We will initiate the upload of
        the queued file later. """

        user = msg.init.target_user
        real_path = self.core.shares.virtual2real(msg.file)

        if not self.file_is_upload_queued(user, msg.file):

            limits = True

            if self.config.sections["transfers"]["friendsnolimits"]:
                friend = user in (i[0] for i in self.config.sections["server"]["userlist"])

                if friend:
                    limits = False

            ip_address, _port = msg.init.addr
            checkuser, reason = self.core.network_filter.check_user(user, ip_address)

            if not checkuser:
                self.queue.append(
                    slskmessages.UploadDenied(msg.init, msg.file, reason)
                )

            elif limits and self.queue_limit_reached(user):
                self.queue.append(
                    slskmessages.UploadDenied(msg.init, msg.file, "Too many megabytes")
                )

            elif limits and self.file_limit_reached(user):
                self.queue.append(
                    slskmessages.UploadDenied(msg.init, msg.file, "Too many files")
                )

            elif self.core.shares.file_is_shared(user, msg.file, real_path):
                newupload = Transfer(
                    user=user, filename=msg.file,
                    path=os.path.dirname(real_path), status="Queued",
                    size=self.get_file_size(real_path)
                )
                self.append_upload(user, msg.file, newupload)
                self.update_upload(newupload)

                self.core.pluginhandler.upload_queued_notification(user, msg.file, real_path)
                self.check_upload_queue()

            else:
                self.queue.append(
                    slskmessages.UploadDenied(msg.init, msg.file, "File not shared.")
                )

        log.add_transfer("QueueUpload request: User %(user)s, %(msg)s", {
            'user': user,
            'msg': str(vars(msg))
        })

    def transfer_request(self, msg):

        user = msg.init.target_user
        response = None

        if msg.direction == 1:
            log.add_transfer("Received upload request %(request)s for file %(filename)s from user %(user)s", {
                "request": msg.token,
                "filename": msg.file,
                "user": user
            })

            response = self.transfer_request_downloads(msg)

            log.add_transfer("Sending response to upload request %(request)s for file %(filename)s "
                             + "from user %(user)s: %(allowed)s", {
                                 "request": response.token,
                                 "filename": msg.file,
                                 "user": user,
                                 "allowed": response.allowed
                             })

        else:
            log.add_transfer("Received download request %(request)s for file %(filename)s from user %(user)s", {
                "request": msg.token,
                "filename": msg.file,
                "user": user
            })

            response = self.transfer_request_uploads(msg)

            log.add_transfer("Sending response to download request %(request)s for file %(filename)s "
                             + "from user %(user)s: %(allowed)s", {
                                 "request": response.token,
                                 "filename": msg.file,
                                 "user": user,
                                 "allowed": response.allowed
                             })

        self.core.send_message_to_peer(user, response)

    def transfer_request_downloads(self, msg):

        user = msg.init.target_user
        filename = msg.file
        size = msg.filesize

        cancel_reason = "Cancelled"
        accepted = True

        for i in self.downloads:
            if i.filename == filename and user == i.user:
                status = i.status

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

                if msg.filesize > 0:
                    i.size = size

                i.token = msg.token
                i.status = "Getting status"
                self.transfer_request_times[i] = time.time()

                self.update_download(i)
                response = slskmessages.TransferResponse(None, 1, token=i.token)
                return response

        # Check if download exists in our default download folder
        if self.get_existing_download_path(user, filename, "", size):
            cancel_reason = "Complete"
            accepted = False

        # If this file is not in your download queue, then it must be
        # a remotely initiated download and someone is manually uploading to you
        if accepted and self.can_upload(user):
            path = ""
            if self.config.sections["transfers"]["uploadsinsubdirs"]:
                parentdir = msg.file.replace('/', '\\').split('\\')[-2]
                path = os.path.join(self.config.sections["transfers"]["uploaddir"], user, parentdir)

            transfer = Transfer(
                user=user, filename=msg.file, path=path,
                status="Queued", size=msg.filesize, token=msg.token
            )
            self.downloads.appendleft(transfer)
            self.core.watch_user(user)

            response = slskmessages.TransferResponse(None, 0, reason="Queued", token=transfer.token)
            self.update_download(transfer)

        else:
            response = slskmessages.TransferResponse(None, 0, reason=cancel_reason, token=msg.token)
            log.add_transfer("Denied file request: User %(user)s, %(msg)s", {
                'user': user,
                'msg': str(vars(msg))
            })

        return response

    def transfer_request_uploads(self, msg):
        """ Remote peer is requesting to download a file through your upload queue.
        Note that the QueueUpload peer message has replaced this method of requesting
        a download in most clients. """

        response = self._transfer_request_uploads(msg)
        log.add_transfer("Legacy TransferRequest upload request: %(req)s Response: %(resp)s", {
            'req': str(vars(msg)),
            'resp': response
        })
        return response

    def _transfer_request_uploads(self, msg):

        # Is user allowed to download?
        user = msg.init.target_user
        ip_address, _port = msg.init.addr
        checkuser, reason = self.core.network_filter.check_user(user, ip_address)

        if not checkuser:
            return slskmessages.TransferResponse(None, 0, reason=reason, token=msg.token)

        # Do we actually share that file with the world?
        real_path = self.core.shares.virtual2real(msg.file)

        if not self.core.shares.file_is_shared(user, msg.file, real_path):
            return slskmessages.TransferResponse(None, 0, reason="File not shared.", token=msg.token)

        # Is that file already in the queue?
        if self.file_is_upload_queued(user, msg.file):
            return slskmessages.TransferResponse(None, 0, reason="Queued", token=msg.token)

        # Has user hit queue limit?
        limits = True

        if self.config.sections["transfers"]["friendsnolimits"]:
            friend = user in (i[0] for i in self.config.sections["server"]["userlist"])

            if friend:
                limits = False

        if limits and self.queue_limit_reached(user):
            return slskmessages.TransferResponse(None, 0, reason="Too many megabytes", token=msg.token)

        if limits and self.file_limit_reached(user):
            return slskmessages.TransferResponse(None, 0, reason="Too many files", token=msg.token)

        # All checks passed, user can queue file!
        self.core.pluginhandler.upload_queued_notification(user, msg.file, real_path)

        # Is user already downloading/negotiating a download?
        already_downloading = False
        active_statuses = ("Getting status", "Establishing connection", "Transferring")

        for i in self.uploads:
            if i.user != user:
                continue

            if i.status in active_statuses:
                already_downloading = True
                break

        if not self.allow_new_uploads() or already_downloading:

            response = slskmessages.TransferResponse(None, 0, reason="Queued", token=msg.token)
            newupload = Transfer(
                user=user, filename=msg.file,
                path=os.path.dirname(real_path), status="Queued",
                size=self.get_file_size(real_path)
            )
            self.append_upload(user, msg.file, newupload)
            self.update_upload(newupload)
            return response

        # All checks passed, starting a new upload.
        size = self.get_file_size(real_path)
        response = slskmessages.TransferResponse(None, 1, token=msg.token, filesize=size)

        transferobj = Transfer(
            user=user, filename=msg.file,
            path=os.path.dirname(real_path), status="Getting status",
            token=msg.token, size=size
        )

        self.transfer_request_times[transferobj] = time.time()
        self.append_upload(user, msg.file, transferobj)
        self.update_upload(transferobj)
        return response

    def transfer_response(self, msg):
        """ Received a response to the file request from the peer """

        log.add_transfer("Received response for transfer request %(request)s. Allowed: %(allowed)s. "
                         + "Reason: %(reason)s. Filesize: %(size)s", {
                             "request": msg.token,
                             "allowed": msg.allowed,
                             "reason": msg.reason,
                             "size": msg.filesize
                         })

        if msg.reason is not None:

            for i in self.uploads:
                if i.token != msg.token:
                    continue

                i.status = msg.reason
                i.token = None
                i.queue_position = 0

                self.update_upload(i)

                if i in self.transfer_request_times:
                    del self.transfer_request_times[i]

                self.update_user_counter(i.user)

                if msg.reason == "Complete":
                    # A complete download of this file already exists on the user's end
                    self.upload_finished(i)

                elif msg.reason in ("Cancelled", "Disallowed extension"):
                    self.auto_clear_upload(i)

                self.check_upload_queue()
                break

        else:
            for i in self.uploads:
                if i.token != msg.token:
                    continue

                i.status = "Establishing connection"
                self.core.send_message_to_peer(i.user, slskmessages.FileRequest(None, msg.token))
                self.update_upload(i)
                self.check_upload_queue()
                break
            else:
                log.add_transfer("Got unknown transfer response: %s", str(vars(msg)))

    def transfer_timeout(self, msg):

        transfer = msg.transfer

        if transfer.status == "Transferring":
            # Check if the transfer has started since the timeout callback was initiated
            return

        log.add_transfer("Transfer %(filename)s with request %(request)s for user %(user)s timed out", {
            "filename": transfer.filename,
            "request": transfer.token,
            "user": transfer.user
        })

        transfer.status = "Cannot connect"
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

    def file_error(self, msg):
        """ Networking thread encountered a local file error """

        for i in self.downloads + self.uploads:

            if i.sock != msg.sock:
                continue

            self.abort_transfer(i)
            i.status = "Local file error"

            log.add(_("I/O error: %s"), msg.strerror)

            if i in self.downloads:
                self.update_download(i)

            elif i in self.uploads:
                self.update_upload(i)
                self.check_upload_queue()

    def file_request(self, msg):
        """ Got an incoming file request. Could be an upload request or a
        request to get the file that was previously queued """

        token = msg.token

        log.add_transfer("Received file request %(request)s", {
            "request": token
        })

        for i in self.downloads:
            if token == i.token:
                self._file_request_download(msg, i)
                return

        for i in self.uploads:
            if token == i.token:
                self._file_request_upload(msg, i)
                return

        self.queue.append(slskmessages.FileConnClose(msg.init.sock))

    def _file_request_download(self, msg, i):

        log.add_transfer("Received file upload request %(request)s for file %(filename)s from user %(user)s", {
            "request": msg.token,
            "filename": i.filename,
            "user": i.user
        })

        incompletedir = self.config.sections["transfers"]["incompletedir"]
        needupdate = True

        if i.sock is None:
            i.sock = msg.init.sock
            i.token = None

            if i in self.transfer_request_times:
                del self.transfer_request_times[i]

            if not incompletedir:
                if i.path:
                    incompletedir = i.path
                else:
                    incompletedir = self.get_default_download_folder(i.user)

            try:
                if not os.access(incompletedir, os.F_OK):
                    os.makedirs(incompletedir)
                if not os.access(incompletedir, os.R_OK | os.W_OK | os.X_OK):
                    raise OSError("Download directory %s Permissions error.\nDir Permissions: %s" %
                                  (incompletedir, oct(os.stat(incompletedir)[stat.ST_MODE] & 0o777)))

            except OSError as error:
                log.add(_("OS error: %s"), error)
                self.download_folder_error(i, error)

            else:
                file_handle = None
                try:
                    from hashlib import md5
                    md5sum = md5()
                    md5sum.update((i.filename + i.user).encode('utf-8'))

                    base_name, extension = os.path.splitext(clean_file(i.filename.replace('/', '\\').split('\\')[-1]))
                    prefix = "INCOMPLETE" + md5sum.hexdigest()

                    # Ensure file name doesn't exceed 255 characters in length
                    incomplete_name = os.path.join(
                        incompletedir, prefix + base_name[:255 - len(prefix) - len(extension)] + extension)
                    file_handle = open(incomplete_name, 'ab+')

                    if self.config.sections["transfers"]["lock"]:
                        try:
                            import fcntl
                            try:
                                fcntl.lockf(file_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                            except OSError as error:
                                log.add(_("Can't get an exclusive lock on file - I/O error: %s"), error)
                        except ImportError:
                            pass

                    file_handle.seek(0, 2)
                    offset = file_handle.tell()

                except OSError as error:
                    log.add(_("Download I/O error: %s"), error)

                    self.abort_transfer(i)
                    i.status = "Local file error"

                else:
                    i.file = file_handle
                    i.last_byte_offset = offset
                    i.queue_position = 0

                    self.core.statistics.append_stat_value("started_downloads", 1)
                    self.core.pluginhandler.download_started_notification(i.user, i.filename, incomplete_name)

                    if i.size > offset:
                        i.status = "Transferring"
                        i.legacy_attempt = False
                        self.queue.append(slskmessages.DownloadFile(i.sock, file_handle))
                        self.queue.append(slskmessages.FileOffset(msg.init, i.size, offset))

                        log.add_download(
                            _("Download started: user %(user)s, file %(file)s"), {
                                "user": i.user,
                                "file": "%s" % file_handle.name
                            }
                        )
                    else:
                        self.download_finished(file_handle, i)
                        needupdate = False

            if self.downloadsview:
                self.downloadsview.new_transfer_notification()

            if needupdate:
                self.update_download(i)

        else:
            log.add_transfer("Download error formally known as 'Unknown file request': %(req)s (%(user)s: %(file)s)", {
                'req': str(vars(msg)),
                'user': i.user,
                'file': i.filename
            })

            self.queue.append(slskmessages.FileConnClose(msg.init.sock))

    def _file_request_upload(self, msg, i):

        log.add_transfer("Received file download request %(request)s for file %(filename)s from user %(user)s", {
            "request": msg.token,
            "filename": i.filename,
            "user": i.user
        })
        needupdate = True

        if i.sock is None:
            i.sock = msg.init.sock
            i.token = None
            file_handle = None

            if i in self.transfer_request_times:
                del self.transfer_request_times[i]

            try:
                # Open File
                real_path = self.core.shares.virtual2real(i.filename)
                file_handle = open(real_path, "rb")
                offset = file_handle.tell()

            except OSError as error:
                log.add(_("Upload I/O error: %s"), error)

                self.abort_transfer(i)
                i.status = "Local file error"
                self.check_upload_queue()

            else:
                i.file = file_handle
                i.last_byte_offset = offset
                i.queue_position = 0

                self.core.statistics.append_stat_value("started_uploads", 1)
                self.core.pluginhandler.upload_started_notification(i.user, i.filename, real_path)

                if i.size > offset:
                    i.status = "Transferring"
                    self.queue.append(slskmessages.UploadFile(i.sock, file=file_handle, size=i.size))

                    log.add_upload(
                        _("Upload started: user %(user)s, IP address %(ip)s, file %(file)s"), {
                            "user": i.user,
                            "ip": self.core.protothread.user_addresses.get(i.user),
                            "file": i.filename
                        }
                    )
                else:
                    self.upload_finished(i, file_handle=file_handle)
                    needupdate = False

            if self.uploadsview:
                self.uploadsview.new_transfer_notification()

            if needupdate:
                self.update_upload(i)

        else:
            log.add_transfer("Upload error formally known as 'Unknown file request': %(req)s (%(user)s: %(file)s)", {
                'req': str(vars(msg)),
                'user': i.user,
                'file': i.filename
            })

            self.queue.append(slskmessages.FileConnClose(msg.init.sock))

    def upload_denied(self, msg):

        user = msg.init.target_user

        for i in self.downloads:
            if i.user != user or i.filename != msg.file:
                continue

            if i.status in ("Finished", "Paused"):
                # SoulseekQt also sends this message for finished downloads when unsharing files, ignore
                continue

            if msg.reason in ("File not shared.", "File not shared", "Remote file error") and not i.legacy_attempt:
                # The peer is possibly using an old client that doesn't support Unicode
                # (Soulseek NS). Attempt to request file name encoded as latin-1 once.

                log.add_transfer("User %(user)s responded with reason '%(reason)s' for download request %(filename)s. "
                                 "Attempting to request file as latin-1.", {
                                     "user": user,
                                     "reason": msg.reason,
                                     "filename": i.filename
                                 })

                self.abort_transfer(i)
                i.legacy_attempt = True
                self.get_file(i.user, i.filename, i.path, i)
                break

            if i.status == "Transferring":
                self.abort_transfer(i, reason=msg.reason)

            i.status = msg.reason
            self.update_download(i)

            log.add_transfer("Download request denied by user %(user)s for file %(filename)s. Reason: %(reason)s", {
                "user": user,
                "filename": i.filename,
                "reason": msg.reason
            })
            break

    def upload_failed(self, msg):

        user = msg.init.target_user

        for i in self.downloads:
            if i.user != user or i.filename != msg.file:
                continue

            if i.status in ("Finished", "Paused", "Download folder error", "Local file error", "User logged off"):
                # Check if there are more transfers with the same virtual path
                continue

            if not i.legacy_attempt:
                # Attempt to request file name encoded as latin-1 once

                self.abort_transfer(i)
                i.legacy_attempt = True
                self.get_file(i.user, i.filename, i.path, i)
                break

            # Already failed once previously, give up
            i.status = "Remote file error"
            self.update_download(i)

            log.add_transfer("Upload attempt by user %(user)s for file %(filename)s failed. Reason: %(reason)s", {
                "filename": i.filename,
                "user": user,
                "reason": "Remote file error"
            })
            break

    def file_download(self, msg):
        """ A file download is in progress """

        needupdate = True

        for i in self.downloads:

            if i.sock != msg.sock:
                continue

            try:
                if i in self.transfer_request_times:
                    del self.transfer_request_times[i]

                current_time = time.time()
                i.current_byte_offset = msg.file.tell()

                if i.start_time is None:
                    i.start_time = current_time

                i.status = "Transferring"
                oldelapsed = i.time_elapsed
                i.time_elapsed = current_time - i.start_time
                byte_difference = i.current_byte_offset - i.last_byte_offset

                if byte_difference:
                    self.core.statistics.append_stat_value("downloaded_size", byte_difference)

                if i.size > i.current_byte_offset:
                    if current_time > i.start_time and i.current_byte_offset > i.last_byte_offset:
                        i.speed = int(max(0, byte_difference // max(1, current_time - i.last_update)))

                        if i.speed <= 0:
                            i.time_left = "∞"
                        else:
                            i.time_left = human_length((i.size - i.current_byte_offset) / i.speed)

                    if oldelapsed == i.time_elapsed:
                        needupdate = False
                else:
                    self.download_finished(msg.file, i)
                    needupdate = False

                i.last_byte_offset = i.current_byte_offset
                i.last_update = current_time

            except OSError as error:
                log.add(_("Download I/O error: %s"), error)

                self.abort_transfer(i)
                i.status = "Local file error"

            if needupdate:
                self.update_download(i)

            break

    def file_upload(self, msg):
        """ A file upload is in progress """

        needupdate = True

        for i in self.uploads:

            if i.sock != msg.sock:
                continue

            if i in self.transfer_request_times:
                del self.transfer_request_times[i]

            current_time = time.time()
            i.current_byte_offset = msg.offset + msg.sentbytes

            if i.start_time is None:
                i.start_time = current_time

            i.status = "Transferring"
            oldelapsed = i.time_elapsed
            i.time_elapsed = current_time - i.start_time
            byte_difference = i.current_byte_offset - i.last_byte_offset

            if byte_difference:
                self.core.statistics.append_stat_value("uploaded_size", byte_difference)

            if i.size > i.current_byte_offset:
                if current_time > i.start_time and i.current_byte_offset > i.last_byte_offset:
                    i.speed = int(max(0, byte_difference // max(1, current_time - i.last_update)))

                    if i.speed <= 0:
                        i.time_left = "∞"
                    else:
                        i.time_left = human_length((i.size - i.current_byte_offset) / i.speed)

                if oldelapsed == i.time_elapsed:
                    needupdate = False

            elif i.speed is not None:
                # Inform the server about the last upload speed for this transfer
                self.upload_speed = i.speed
                self.queue.append(slskmessages.SendUploadSpeed(i.speed))

                i.speed = None
                i.time_left = ""

            i.last_byte_offset = i.current_byte_offset
            i.last_update = current_time

            if needupdate:
                self.update_upload(i)

            break

    def file_conn_close(self, sock):
        """ The remote peer has closed a file transfer connection """

        for i in self.downloads:
            if i.sock == sock:
                self._file_conn_close(i, "download")
                return

        # We need a copy due to upload auto-clearing modifying the deque during iteration
        for i in self.uploads.copy():
            if i.sock == sock:
                self._file_conn_close(i, "upload")
                return

    def _file_conn_close(self, i, transfer_type):

        if transfer_type == "download":
            self.abort_transfer(i)

            if i.status != "Finished":
                if self.user_logged_out(i.user):
                    i.status = "User logged off"
                else:
                    i.status = "Connection closed by peer"

            self.update_download(i)

        elif transfer_type == "upload":
            if i.current_byte_offset is not None and i.current_byte_offset >= i.size:
                # We finish the upload here in case the downloading peer has a slow/limited download
                # speed and finishes later than us
                self.upload_finished(i, file_handle=i.file)
                return

            if i.status == "Finished":
                return

            self.abort_transfer(i)

            if self.user_logged_out(i.user):
                i.status = "User logged off"
            else:
                i.status = "Cancelled"

                # Transfer ended abruptly. Tell the peer to re-queue the file. If the transfer was
                # intentionally cancelled, the peer should ignore this message.
                self.core.send_message_to_peer(i.user, slskmessages.UploadFailed(None, i.filename))

            if not self.auto_clear_upload(i):
                self.update_upload(i)

            self.check_upload_queue()

    def place_in_queue_request(self, msg):

        user = msg.init.target_user
        privileged_user = self.is_privileged(user)
        queue_position = 0
        transfer = None

        if self.config.sections["transfers"]["fifoqueue"]:
            for i in reversed(self.uploads):
                # Ignore non-queued files
                if i.status != "Queued":
                    continue

                if not privileged_user or self.is_privileged(i.user):
                    queue_position += 1

                # Stop counting on the matching file
                if i.user == user and i.filename == msg.file:
                    transfer = i
                    break

        else:
            num_queued_users = len(self.user_update_counters)

            for i in reversed(self.uploads):
                if i.user != user:
                    continue

                # Ignore non-queued files
                if i.status != "Queued":
                    continue

                queue_position += num_queued_users

                # Stop counting on the matching file
                if i.filename == msg.file:
                    transfer = i
                    break

        if queue_position > 0:
            self.queue.append(slskmessages.PlaceInQueue(msg.init, msg.file, queue_position))

        if transfer is None:
            return

        # Update queue position in our list of uploads
        transfer.queue_position = queue_position
        self.update_upload(transfer)

    def place_in_queue(self, msg):
        """ The peer tells us our place in queue for a particular transfer """

        username = msg.init.target_user
        filename = msg.filename

        for i in self.downloads:
            if i.user == username and i.filename == filename and i.status not in ("Finished", "Paused", "Filtered"):
                i.queue_position = msg.place
                self.update_download(i)
                return

    """ Transfer Actions """

    def get_folder(self, user, folder):
        self.core.send_message_to_peer(user, slskmessages.FolderContentsRequest(None, folder))

    def get_file(self, user, filename, path="", transfer=None, size=0, bitrate=None, length=None):

        path = clean_path(path, absolute=True)

        if transfer is None:
            for i in self.downloads:
                if i.user == user and i.filename == filename and i.path == path:
                    if i.status == "Finished":
                        # Duplicate finished download found, verify that it's still present on disk later
                        transfer = i
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
                    user, slskmessages.QueueUpload(None, filename, transfer.legacy_attempt))

        self.update_download(transfer)

    def push_file(self, user, filename, size, path="", transfer=None, bitrate=None, length=None, locally_queued=False):

        if not self.core.logged_in:
            return

        real_path = self.core.shares.virtual2real(filename)
        size_attempt = self.get_file_size(real_path)

        if size_attempt > 0:
            size = size_attempt

        if transfer is None:
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

        log.add_transfer(
            "Initializing upload request for file %(file)s to user %(user)s", {
                'file': filename,
                'user': user
            }
        )

        self.core.watch_user(user)

        if self.user_logged_out(user):
            transfer.status = "User logged off"

        elif not locally_queued:
            self.token = increment_token(self.token)
            transfer.token = self.token
            transfer.status = "Getting status"
            self.transfer_request_times[transfer] = time.time()

            log.add_transfer("Requesting to upload file %(filename)s with transfer "
                             + "request %(request)s to user %(user)s", {
                                 "filename": filename,
                                 "request": transfer.token,
                                 "user": user
                             })

            self.core.send_message_to_peer(
                user, slskmessages.TransferRequest(None, 1, transfer.token, filename, size, real_path))

        self.update_upload(transfer)

    def append_upload(self, user, filename, transferobj):

        previously_queued = False
        old_index = 0

        if self.is_privileged(user):
            transferobj.modifier = "privileged" if user in self.privileged_users else "prioritized"

        for i in self.uploads:
            if i.user == user and i.filename == filename:
                if i.status == "Queued":
                    # This upload was queued previously
                    # Use the previous queue position and time
                    transferobj.queue_position = i.queue_position
                    previously_queued = True

                if i in self.transfer_request_times:
                    del self.transfer_request_times[i]

                self.uploads.remove(i)

                if self.uploadsview:
                    self.uploadsview.remove_specific(i, True)

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
                    and user in (i[0] for i in self.config.sections["server"]["userlist"])):
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

    def get_folder_destination(self, user, directory):

        # Check if a custom download location was specified
        if (user in self.requested_folders and directory in self.requested_folders[user]
                and self.requested_folders[user][directory]):
            download_location = self.requested_folders[user][directory]

        else:
            download_location = self.get_default_download_folder(user)

        # Get the last folder in directory path
        target_name = directory.rstrip('\\').split('\\')[-1]

        # Merge download path with target folder name
        destination = os.path.join(download_location, target_name)

        return destination

    def get_total_uploads_allowed(self):

        if self.config.sections["transfers"]["useupslots"]:
            maxupslots = self.config.sections["transfers"]["uploadslots"]

            if maxupslots <= 0:
                maxupslots = 1

            return maxupslots

        lstlen = sum(1 for i in self.uploads if i.sock is not None)

        if self.allow_new_uploads():
            return lstlen + 1

        return lstlen

    def get_upload_queue_size(self, username=None):

        if self.is_privileged(username):
            queue_size = 0

            for i in self.uploads:
                if i.status == "Queued" and self.is_privileged(i.user):
                    queue_size += 1

            return queue_size

        return sum(1 for i in self.uploads if i.status == "Queued")

    def get_default_download_folder(self, user):

        downloaddir = self.config.sections["transfers"]["downloaddir"]

        # Check if username subfolders should be created for downloads
        if self.config.sections["transfers"]["usernamesubfolders"]:
            try:
                downloaddir = os.path.join(downloaddir, clean_file(user))

                if not os.path.isdir(downloaddir):
                    os.makedirs(downloaddir)

            except Exception as error:
                log.add(_("Unable to save download to username subfolder, falling back "
                          "to default download folder. Error: %s") % error)

        return downloaddir

    def get_download_destination(self, user, virtual_path, target_path):
        """ Returns the download destination of a virtual file path """

        folder_path = target_path if target_path else self.get_default_download_folder(user)
        basename = clean_file(virtual_path.replace('/', '\\').split('\\')[-1])

        return folder_path, basename

    def get_existing_download_path(self, user, virtual_path, target_path, size):
        """ Returns the download path of a previous download, if available """

        folder, basename = self.get_download_destination(user, virtual_path, target_path)
        basename_root, extension = os.path.splitext(basename)
        download_path = os.path.join(folder, basename)
        counter = 1

        while os.path.isfile(download_path):
            if os.stat(download_path).st_size == size:
                # Found a previous download with a matching file size
                return download_path

            basename = basename_root + " (" + str(counter) + ")" + extension
            download_path = os.path.join(folder, basename)
            counter += 1

        return None

    @staticmethod
    def get_renamed(name):
        """ When a transfer is finished, we remove INCOMPLETE~ or INCOMPLETE
        prefix from the file's name.

        Checks if a file with the same name already exists, and adds a number
        to the file name if that's the case. """

        filename, extension = os.path.splitext(name)
        counter = 1

        while os.path.exists(name):
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
            if not execute_command(config["transfers"]["afterfinish"], filepath):
                log.add(_("Trouble executing '%s'"), config["transfers"]["afterfinish"])
            else:
                log.add(_("Executed: %s"), config["transfers"]["afterfinish"])

    def folder_downloaded_actions(self, user, folderpath):

        # walk through downloads and break if any file in the same folder exists, else execute
        for i in self.downloads:
            if i.status not in ("Finished", "Paused", "Filtered") and i.path == folderpath:
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
            if not execute_command(config["transfers"]["afterfolder"], folderpath):
                log.add(_("Trouble executing on folder: %s"), config["transfers"]["afterfolder"])
            else:
                log.add(_("Executed on folder: %s"), config["transfers"]["afterfolder"])

    def download_folder_error(self, transfer, error):

        self.abort_transfer(transfer)
        transfer.status = "Download folder error"

        self.core.notifications.new_text_notification(
            _("OS error: %s") % error, title=_("Download folder error"))

    def download_finished(self, file, i):

        self.close_file(file, i)

        folder, basename = self.get_download_destination(i.user, i.filename, i.path)
        newname = self.get_renamed(os.path.join(folder, basename))

        try:
            if not os.access(folder, os.F_OK):
                os.makedirs(folder)

            import shutil
            shutil.move(file.name, newname)

        except OSError as inst:
            log.add(
                _("Couldn't move '%(tempfile)s' to '%(file)s': %(error)s"), {
                    'tempfile': "%s" % file.name,
                    'file': newname,
                    'error': inst
                }
            )
            self.download_folder_error(i, inst)
            self.update_download(i)
            return

        i.status = "Finished"
        i.current_byte_offset = i.size
        i.speed = None
        i.time_left = ""
        i.sock = None

        self.core.statistics.append_stat_value("completed_downloads", 1)

        # Attempt to show notification and execute commands
        self.file_downloaded_actions(i.user, newname)
        self.folder_downloaded_actions(i.user, i.path)

        if self.downloadsview:
            # Main tab highlight (bright)
            self.downloadsview.new_transfer_notification(finished=True)

        # Attempt to autoclear this download, if configured
        if not self.auto_clear_download(i, force_save=True):
            self.update_download(i, force_save=True)

        self.core.pluginhandler.download_finished_notification(i.user, i.filename, newname)

        log.add_download(
            _("Download finished: user %(user)s, file %(file)s"), {
                'user': i.user,
                'file': i.filename
            }
        )

    def upload_finished(self, i, file_handle=None):

        self.close_file(file_handle, i)

        i.status = "Finished"
        i.current_byte_offset = i.size
        i.speed = None
        i.time_left = ""
        i.sock = None

        self.update_user_counter(i.user)

        log.add_upload(
            _("Upload finished: user %(user)s, IP address %(ip)s, file %(file)s"), {
                'user': i.user,
                'ip': self.core.protothread.user_addresses.get(i.user),
                'file': i.filename
            }
        )

        self.core.statistics.append_stat_value("completed_uploads", 1)

        # Autoclear this upload
        if not self.auto_clear_upload(i, force_save=True):
            self.update_upload(i, force_save=True)

        real_path = self.core.shares.virtual2real(i.filename)
        self.core.pluginhandler.upload_finished_notification(i.user, i.filename, real_path)

        self.check_upload_queue()

    def auto_clear_download(self, transfer, force_save=False):

        if self.config.sections["transfers"]["autoclear_downloads"]:
            self.downloads.remove(transfer)
            self.save_transfers("downloads", force_save)

            if self.downloadsview:
                self.downloadsview.remove_specific(transfer, True)

            return True

        return False

    def auto_clear_upload(self, transfer, force_save=False):

        if self.config.sections["transfers"]["autoclear_uploads"]:
            self.uploads.remove(transfer)
            self.save_transfers("uploads", force_save)

            if self.uploadsview:
                self.uploadsview.remove_specific(transfer, True)

            return True

        return False

    def update_download(self, transfer, force_save=False):

        self.save_transfers("downloads", force_save)

        if self.downloadsview:
            self.downloadsview.update(transfer)

    def update_upload(self, transfer, force_save=False):

        self.save_transfers("uploads", force_save)

        if self.uploadsview:
            self.uploadsview.update(transfer)

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

        while True:
            self.network_callback([slskmessages.CheckUploadQueue()])

            if self.core.protothread.exit.wait(10):
                # Event set, we're exiting
                return

    def _check_download_queue_timer(self):

        self.download_queue_timer_count = -1

        while True:
            self.download_queue_timer_count += 1
            self.network_callback([slskmessages.CheckDownloadQueue()])

            if self.core.protothread.exit.wait(180):
                # Event set, we're exiting
                return

    # Find failed or stuck downloads and attempt to queue them.
    # Also ask for the queue position of downloads.
    def check_download_queue(self):

        statuslist_failed = ("Cannot connect", "Connection closed by peer", "Local file error", "Remote file error")
        statuslist_limited = ("Too many files", "Too many megabytes")
        reset_count = False

        for transfer in reversed(self.downloads):
            status = transfer.status

            if (self.download_queue_timer_count >= 4
                    and (status in statuslist_limited or status.startswith("User limit of"))):
                # Re-queue limited downloads every 12 minutes

                log.add_transfer("Re-queuing file %(filename)s from user %(user)s in download queue", {
                    "filename": transfer.filename,
                    "user": transfer.user
                })
                reset_count = True

                self.abort_transfer(transfer)
                self.get_file(transfer.user, transfer.filename, transfer.path, transfer)

            if status in statuslist_failed:
                # Retry failed downloads every 3 minutes

                self.abort_transfer(transfer)
                self.get_file(transfer.user, transfer.filename, transfer.path, transfer)

            if status == "Queued":
                # Request queue position every 3 minutes

                self.core.send_message_to_peer(
                    transfer.user,
                    slskmessages.PlaceInQueueRequest(None, transfer.filename, transfer.legacy_attempt)
                )

        if reset_count:
            self.download_queue_timer_count = 0

    def get_upload_candidate(self):
        """ Retrieve a suitable queued transfer for uploading.
        Round Robin: Get the first queued item from the oldest user
        FIFO: Get the first queued item in the list """

        round_robin_queue = not self.config.sections["transfers"]["fifoqueue"]
        active_statuses = ("Getting status", "Establishing connection", "Transferring")
        privileged_queue = False

        first_queued_transfers = OrderedDict()
        queued_users = {}
        uploading_users = set()

        for i in reversed(self.uploads):
            if i.status == "Queued":
                user = i.user

                if user not in first_queued_transfers and user not in uploading_users:
                    first_queued_transfers[user] = i

                if user in queued_users:
                    continue

                privileged = self.is_privileged(user)
                queued_users[user] = privileged

                if privileged:
                    privileged_queue = True

            elif i.status in active_statuses:
                # We're currently uploading a file to the user
                user = i.user

                uploading_users.add(user)

                if user in first_queued_transfers:
                    del first_queued_transfers[user]

        oldest_time = None
        target_user = None

        if not round_robin_queue:
            # skip the looping below (except the cleanup) and get the first
            # user of the highest priority we saw above
            for user in first_queued_transfers:
                if privileged_queue and not queued_users[user]:
                    continue

                target_user = user
                break

        for user, update_time in list(self.user_update_counters.items()):
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

        while True:
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

            if self.user_logged_out(user):
                upload_candidate.status = "User logged off"
                self.abort_transfer(upload_candidate)

                if not self.auto_clear_upload(upload_candidate):
                    self.update_upload(upload_candidate)

                # Check queue again
                continue

            self.push_file(
                user=user, filename=upload_candidate.filename, size=upload_candidate.size, transfer=upload_candidate
            )
            return

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

        if self.user_logged_out(user):
            transfer.status = "User logged off"
            self.abort_transfer(transfer)
            self.update_download(transfer)
            return

        self.abort_transfer(transfer)
        self.get_file(user, transfer.filename, transfer.path, transfer)

    def retry_upload(self, transfer):

        active_statuses = ["Getting status", "Establishing connection", "Transferring"]

        if transfer.status in active_statuses + ["Finished"]:
            # Don't retry active or finished uploads
            return

        user = transfer.user

        for i in self.uploads:
            if i.user != user:
                continue

            if i.status in active_statuses:
                # User already has an active upload, queue the retry attempt
                if transfer.status != "Queued":
                    transfer.status = "Queued"
                    self.update_upload(transfer)
                return

        if self.user_logged_out(user):
            transfer.status = "User logged off"
            self.abort_transfer(transfer)

            if not self.auto_clear_upload(transfer):
                self.update_upload(transfer)
            return

        self.push_file(user, transfer.filename, transfer.size, transfer.path, transfer=transfer)

    def abort_transfer(self, transfer, reason="Cancelled", send_fail_message=False):

        transfer.legacy_attempt = False
        transfer.token = None
        transfer.speed = None
        transfer.queue_position = 0
        transfer.time_left = ""

        if transfer.sock is not None:
            self.queue.append(slskmessages.FileConnClose(transfer.sock))
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
                transfer.user, slskmessages.UploadDenied(None, file=transfer.filename, reason=reason))

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

        for i in self.downloads:
            if i.status not in ("Finished", "Filtered", "Paused"):
                self.abort_transfer(i)
                i.status = "User logged off"
                self.update_download(i)

        for i in self.uploads.copy():
            if i.status != "Finished":
                self.uploads.remove(i)

                if self.uploadsview:
                    self.uploadsview.remove_specific(i, True)

        self.privileged_users.clear()
        self.requested_folders.clear()
        self.transfer_request_times.clear()
        self.user_update_counters.clear()

    def get_downloads(self):
        """ Get a list of downloads """
        return [[i.user, i.filename, i.path, i.status, i.size, i.current_byte_offset, i.bitrate, i.length]
                for i in reversed(self.downloads)]

    def get_uploads(self):
        """ Get a list of finished uploads """
        return [[i.user, i.filename, i.path, i.status, i.size, i.current_byte_offset, i.bitrate, i.length]
                for i in reversed(self.uploads) if i.status == "Finished"]

    def save_downloads_callback(self, filename):
        json.dump(self.get_downloads(), filename, ensure_ascii=False)

    def save_uploads_callback(self, filename):
        json.dump(self.get_uploads(), filename, ensure_ascii=False)

    def save_transfers(self, transfer_type, force_save=False):
        """ Save list of transfers """

        if not self.allow_saving_transfers:
            # Don't save if transfers didn't load properly!
            return

        self.config.create_data_folder()
        current_time = time.time()

        if not force_save and (current_time - self.last_save_times[transfer_type]) < 15:
            # Save list of transfers to file every 15 seconds
            return

        if transfer_type == "uploads":
            transfers_file = self.uploads_file_name
            callback = self.save_uploads_callback
        else:
            transfers_file = self.downloads_file_name
            callback = self.save_downloads_callback

        write_file_and_backup(transfers_file, callback)
        self.last_save_times[transfer_type] = current_time

    def server_disconnect(self):

        self.abort_transfers()

        if self.downloadsview:
            self.downloadsview.server_disconnect()

        if self.uploadsview:
            self.uploadsview.server_disconnect()

    def quit(self):

        self.save_transfers("downloads", force_save=True)
        self.save_transfers("uploads", force_save=True)


class Statistics:

    def __init__(self, config, ui_callback=None):

        self.config = config
        self.ui_callback = ui_callback
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
