# COPYRIGHT (C) 2020-2021 Nicotine+ Team
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

from pynicotine import slskmessages
from pynicotine import utils
from pynicotine.logfacility import log
from pynicotine.utils import execute_command
from pynicotine.utils import clean_file
from pynicotine.utils import clean_path
from pynicotine.utils import get_result_bitrate_length
from pynicotine.utils import human_length
from pynicotine.utils import load_file
from pynicotine.utils import write_file_and_backup


class Transfer:
    """ This class holds information about a single transfer. """

    __slots__ = ("conn", "user", "filename",
                 "path", "req", "size", "file", "starttime", "lasttime",
                 "currentbytes", "lastbytes", "speed", "timeelapsed",
                 "timeleft", "timequeued", "modifier", "place", "bitrate", "length",
                 "iterator", "_status", "laststatuschange", "legacy_attempt")

    def __init__(self, user=None, filename=None, path=None, status=None, req=None, size=None,
                 file=None, currentbytes=None, timequeued=None, place=0, bitrate=None, length=None):
        self.user = user
        self.filename = filename
        self.path = path
        self.req = req
        self.size = size
        self.file = file
        self.currentbytes = currentbytes
        self.timequeued = timequeued
        self.place = place
        self.bitrate = bitrate
        self.length = length

        self.conn = None
        self.modifier = None
        self.starttime = None
        self.lasttime = None
        self.lastbytes = None
        self.speed = None
        self.timeelapsed = None
        self.timeleft = None
        self.iterator = None
        self.legacy_attempt = False
        self.setstatus(status)

    def setstatus(self, status):
        self._status = status
        self.laststatuschange = time.time()

    def getstatus(self):
        return self._status
    status = property(getstatus, setstatus)


class Transfers:
    """ This is the transfers manager """

    def __init__(self, core, config, queue, users, network_callback, ui_callback=None):

        self.core = core
        self.config = config
        self.queue = queue
        self.downloads = deque()
        self.uploads = deque()
        self.privilegedusers = set()
        self.requested_folders = defaultdict(dict)
        self.transfer_request_times = {}
        self.upload_speed = 0

        self.downloads_file_name = os.path.join(self.config.data_dir, 'downloads.json')
        self.uploads_file_name = os.path.join(self.config.data_dir, 'uploads.json')

        self.add_stored_transfers("downloads")
        self.add_stored_transfers("uploads")

        self.users = users
        self.network_callback = network_callback
        self.download_queue_timer_count = -1
        self.downloadsview = None
        self.uploadsview = None
        utils.OPEN_SOULSEEK_URL = self.open_soulseek_url

        if hasattr(ui_callback, "downloads"):
            self.downloadsview = ui_callback.downloads

        if hasattr(ui_callback, "uploads"):
            self.uploadsview = ui_callback.uploads

        self.update_download_filters()

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
            size = currentbytes = bitrate = length = None

            try:
                size = int(i[4])
            except Exception:
                pass

            try:
                currentbytes = int(i[5])
            except Exception:
                pass

            try:
                bitrate = i[6]
            except Exception:
                pass

            try:
                length = i[7]
            except Exception:
                pass

            if len(i) >= 4 and i[3] in ("Aborted", "Paused"):
                status = "Paused"
            elif len(i) >= 4 and i[3] in ("Filtered", "Finished"):
                status = i[3]
            else:
                status = "Getting status"

            if transfer_type == "uploads" and status != "Finished":
                # Only finished uploads are supposed to be restored
                continue

            transfer_list.appendleft(
                Transfer(
                    user=i[0], filename=i[1], path=i[2], status=status,
                    size=size, currentbytes=currentbytes, bitrate=bitrate,
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
        self.privilegedusers.add(user)

    def remove_from_privileged(self, user):
        if user in self.privilegedusers:
            self.privilegedusers.remove(user)

    def is_privileged(self, user):

        if not user:
            return False

        if user in self.privilegedusers:
            return True

        return self.is_buddy_privileged(user)

    def is_buddy_privileged(self, user):

        if not user:
            return False

        for row in self.config.sections["server"]["userlist"]:
            if not row or not isinstance(row, list):
                continue

            if user == str(row[0]):
                # All users
                if self.config.sections["transfers"]["preferfriends"]:
                    return True

                # Only privileged users
                try:
                    return bool(row[3])  # Privileged column
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

        uploadslimit = self.config.sections["transfers"]["queuelimit"] * 1024 * 1024

        if not uploadslimit:
            return False

        size = sum(i.size for i in self.uploads if i.user == user and i.status == "Queued")

        return size >= uploadslimit

    def file_limit_reached(self, user):

        filelimit = self.config.sections["transfers"]["filelimit"]

        if not filelimit:
            return False

        numfiles = sum(1 for i in self.uploads if i.user == user and i.status == "Queued")

        return numfiles >= filelimit

    def slot_limit_reached(self):

        maxupslots = self.config.sections["transfers"]["uploadslots"]

        if maxupslots <= 0:
            maxupslots = 1

        in_progress_count = 0
        now = time.time()

        for i in self.uploads:
            if i.conn is not None and i.speed is not None:
                # Currently transferring
                in_progress_count += 1

            elif (now - i.laststatuschange) < 30:
                # Transfer initiating, changed within last 30 seconds

                if (i.req is not None
                        or i.conn is not None and i.speed is None
                        or i.status == "Getting status"):
                    in_progress_count += 1

        return in_progress_count >= maxupslots

    def bandwidth_limit_reached(self):

        bandwidthlimit = self.config.sections["transfers"]["uploadbandwidth"] * 1024

        if not bandwidthlimit:
            return False

        bandwidth_sum = sum(i.speed for i in self.uploads if i.conn is not None and i.speed is not None)

        return bandwidth_sum >= bandwidthlimit

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

        for i in self.uploads:
            if i.user == user and i.filename == filename and i.status in ("Queued", "Transferring"):
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

                    if self.downloadsview:
                        self.downloadsview.update(i)

                elif i.status in ("Getting status", "User logged off", "Connection closed by peer", "Cannot connect"):
                    self.get_file(i.user, i.filename, i.path, i)

        # We need a copy due to upload auto-clearing modifying the deque during iteration
        for i in reversed(self.uploads.copy()):
            if msg.user == i.user and i.status in upload_statuses:
                if msg.status <= 0:
                    i.status = "User logged off"
                    self.abort_transfer(i)

                    if not self.auto_clear_upload(i) and self.uploadsview:
                        self.uploadsview.update(i)

                elif i.status == "User logged off":
                    i.status = "Cancelled"

                    if not self.auto_clear_upload(i) and self.uploadsview:
                        self.uploadsview.update(i)

    def get_cant_connect_request(self, req):
        """ We can't connect to the user, either way (FileRequest, TransferRequest). """

        for i in self.downloads:
            if i.req == req:
                self._get_cant_connect_download(i)
                break

        for i in self.uploads:
            if i.req == req:
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
        i.req = None

        if self.downloadsview:
            self.downloadsview.update(i)

        self.core.watch_user(i.user)

    def _get_cant_connect_upload(self, i):

        i.status = "Cannot connect"
        i.req = None
        curtime = time.time()

        for j in self.uploads:
            if j.user == i.user:
                j.timequeued = curtime

        if self.uploadsview:
            self.uploadsview.update(i)

        self.core.watch_user(i.user)
        self.check_upload_queue()

    def folder_contents_response(self, msg):
        """ When we got a contents of a folder, get all the files in it, but
        skip the files in subfolders"""

        username = msg.conn.init.target_user
        file_list = msg.list

        log.add_transfer("Received response for folder content request from user %s", username)

        for i in file_list:
            for directory in file_list[i]:

                if os.path.commonprefix([i, directory]) == directory:
                    files = file_list[i][directory][:]
                    destination = self.get_folder_destination(username, directory)

                    if self.config.sections["transfers"]["reverseorder"]:
                        files.sort(key=lambda x: x[1], reverse=True)

                    for file in files:
                        virtualpath = directory.rstrip('\\') + '\\' + file[1]
                        size = file[2]
                        h_bitrate, _bitrate, h_length, _length = get_result_bitrate_length(size, file[4])

                        self.get_file(
                            username, virtualpath, destination,
                            size=size, bitrate=h_bitrate, length=h_length)

                    log.add_transfer(
                        "Attempting to download files in folder %(folder)s for user %(user)s. "
                        + "Destination path: %(destination)s", {
                            "folder": directory,
                            "user": username,
                            "destination": destination
                        }
                    )

    def queue_upload(self, msg):
        """ Peer remotely queued a download (upload here). This is the modern replacement to
        a TransferRequest with direction 0 (download request). We will initiate the upload of
        the queued file later. """

        user = msg.conn.init.target_user
        addr = msg.conn.addr[0]

        """ Under certain conditions, SoulseekQt will send a file name/path containing both
        mojibake (utf-8 incorrectly decoded as latin-1) and correct utf-8. This was observed
        when a file name contains special characters, and is downloaded directly from
        a user share. In this case, the folder path is garbled, while the file name is correct.
        Downloading from search results results in no such issue.

        Decode the incorrect parts as utf-8, if necessary, otherwise Nicotine+ thinks the file
        isn't shared. """

        filename_parts = msg.file.replace('/', '\\').split('\\')

        for i, part in enumerate(filename_parts):
            try:
                filename_parts[i] = part.encode('latin-1').decode('utf-8')

            except Exception:
                # Already utf-8
                pass

        filename_utf8 = '\\'.join(filename_parts)
        real_path = self.core.shares.virtual2real(filename_utf8)

        if not self.file_is_upload_queued(user, msg.file):

            limits = True

            if self.config.sections["transfers"]["friendsnolimits"]:
                friend = user in (i[0] for i in self.config.sections["server"]["userlist"])

                if friend:
                    limits = False

            checkuser, reason = self.core.network_filter.check_user(user, addr)

            if not checkuser:
                self.queue.append(
                    slskmessages.UploadDenied(conn=msg.conn.conn, file=msg.file, reason=reason)
                )

            elif limits and self.queue_limit_reached(user):
                self.queue.append(
                    slskmessages.UploadDenied(conn=msg.conn.conn, file=msg.file, reason="Too many megabytes")
                )

            elif limits and self.file_limit_reached(user):
                self.queue.append(
                    slskmessages.UploadDenied(conn=msg.conn.conn, file=msg.file, reason="Too many files")
                )

            elif self.core.shares.file_is_shared(user, filename_utf8, real_path):
                newupload = Transfer(
                    user=user, filename=msg.file,
                    path=os.path.dirname(real_path), status="Queued",
                    timequeued=time.time(), size=self.get_file_size(real_path)
                )
                self._append_upload(user, msg.file, newupload)

                if self.uploadsview:
                    self.uploadsview.update(newupload)

                self.core.pluginhandler.upload_queued_notification(user, msg.file, real_path)
                self.check_upload_queue()

            else:
                self.queue.append(
                    slskmessages.UploadDenied(conn=msg.conn.conn, file=msg.file, reason="File not shared.")
                )

        log.add_transfer("QueueUpload request: User %(user)s, %(msg)s", {
            'user': user,
            'msg': str(vars(msg))
        })

    def transfer_request(self, msg):

        user = msg.conn.init.target_user
        addr = msg.conn.addr[0]
        response = None

        if msg.direction == 1:
            log.add_transfer("Received upload request %(request)s for file %(filename)s from user %(user)s", {
                "request": msg.req,
                "filename": msg.file,
                "user": user
            })

            response = self.transfer_request_downloads(msg, user)

            log.add_transfer("Sending response to upload request %(request)s for file %(filename)s "
                             + "from user %(user)s: %(allowed)s", {
                                 "request": response.req,
                                 "filename": msg.file,
                                 "user": user,
                                 "allowed": response.allowed
                             })

        else:
            log.add_transfer("Received download request %(request)s for file %(filename)s from user %(user)s", {
                "request": msg.req,
                "filename": msg.file,
                "user": user
            })

            response = self.transfer_request_uploads(msg, user, addr)

            log.add_transfer("Sending response to download request %(request)s for file %(filename)s "
                             + "from user %(user)s: %(allowed)s", {
                                 "request": response.req,
                                 "filename": msg.file,
                                 "user": user,
                                 "allowed": response.allowed
                             })

        self.core.send_message_to_peer(user, response)

    def transfer_request_downloads(self, msg, user):

        for i in self.downloads:
            if i.filename == msg.file and user == i.user and i.status not in ("Finished", "Paused", "Filtered"):

                # Remote peer is signalling a tranfer is ready, attempting to download it

                """ If the file is larger than 2GB, the SoulseekQt client seems to
                send a malformed file size (0 bytes) in the TransferRequest response.
                In that case, we rely on the cached, correct file size we received when
                we initially added the download. """

                if msg.filesize > 0:
                    i.size = msg.filesize

                i.req = msg.req
                i.status = "Getting status"
                self.transfer_request_times[i] = time.time()

                if self.downloadsview:
                    self.downloadsview.update(i)

                response = slskmessages.TransferResponse(None, 1, req=i.req)
                return response

        # If this file is not in your download queue, then it must be
        # a remotely initated download and someone is manually uploading to you
        if self.can_upload(user):
            path = ""
            if self.config.sections["transfers"]["uploadsinsubdirs"]:
                parentdir = msg.file.replace('/', '\\').split('\\')[-2]
                path = os.path.join(self.config.sections["transfers"]["uploaddir"], user, parentdir)

            transfer = Transfer(
                user=user, filename=msg.file, path=path,
                status="Queued", size=msg.filesize, req=msg.req
            )
            self.downloads.appendleft(transfer)

            self.core.watch_user(user)

            response = slskmessages.TransferResponse(None, 0, reason="Queued", req=transfer.req)

            if self.downloadsview:
                self.downloadsview.update(transfer)

        else:
            response = slskmessages.TransferResponse(None, 0, reason="Cancelled", req=msg.req)
            log.add_transfer("Denied file request: User %(user)s, %(msg)s", {
                'user': user,
                'msg': str(vars(msg))
            })

        return response

    def transfer_request_uploads(self, msg, user, addr):
        """ Remote peer is requesting to download a file through your upload queue.
        Note that the QueueUpload peer message has replaced this method of requesting
        a download in most clients. """

        response = self._transfer_request_uploads(msg, user, addr)
        log.add_transfer("Legacy TransferRequest upload request: %(req)s Response: %(resp)s", {
            'req': str(vars(msg)),
            'resp': response
        })
        return response

    def _transfer_request_uploads(self, msg, user, addr):

        # Is user allowed to download?
        checkuser, reason = self.core.network_filter.check_user(user, addr)

        if not checkuser:
            return slskmessages.TransferResponse(None, 0, reason=reason, req=msg.req)

        # Do we actually share that file with the world?
        real_path = self.core.shares.virtual2real(msg.file)

        if not self.core.shares.file_is_shared(user, msg.file, real_path):
            return slskmessages.TransferResponse(None, 0, reason="File not shared.", req=msg.req)

        # Is that file already in the queue?
        if self.file_is_upload_queued(user, msg.file):
            return slskmessages.TransferResponse(None, 0, reason="Queued", req=msg.req)

        # Has user hit queue limit?
        limits = True

        if self.config.sections["transfers"]["friendsnolimits"]:
            friend = user in (i[0] for i in self.config.sections["server"]["userlist"])

            if friend:
                limits = False

        if limits and self.queue_limit_reached(user):
            return slskmessages.TransferResponse(None, 0, reason="Too many megabytes", req=msg.req)

        if limits and self.file_limit_reached(user):
            return slskmessages.TransferResponse(None, 0, reason="Too many files", req=msg.req)

        # All checks passed, user can queue file!
        self.core.pluginhandler.upload_queued_notification(user, msg.file, real_path)

        # Is user already downloading/negotiating a download?
        already_downloading = False

        for i in self.uploads:
            if i.user != user:
                continue

            if i.req is not None or i.conn is not None or i.status == "Getting status":
                already_downloading = True

        if not self.allow_new_uploads() or already_downloading:

            response = slskmessages.TransferResponse(None, 0, reason="Queued", req=msg.req)
            newupload = Transfer(
                user=user, filename=msg.file,
                path=os.path.dirname(real_path), status="Queued",
                timequeued=time.time(), size=self.get_file_size(real_path)
            )
            self._append_upload(user, msg.file, newupload)

            if self.uploadsview:
                self.uploadsview.update(newupload)

            return response

        # All checks passed, starting a new upload.
        size = self.get_file_size(real_path)
        response = slskmessages.TransferResponse(None, 1, req=msg.req, filesize=size)

        transferobj = Transfer(
            user=user, filename=msg.file,
            path=os.path.dirname(real_path), status="Getting status",
            req=msg.req, size=size
        )

        self.transfer_request_times[transferobj] = time.time()
        self._append_upload(user, msg.file, transferobj)

        if self.uploadsview:
            self.uploadsview.update(transferobj)

        return response

    def transfer_response(self, msg):

        """ Got a response to the file request from the peer."""

        log.add_transfer("Received response for transfer request %(request)s. Allowed: %(allowed)s. "
                         + "Reason: %(reason)s. Filesize: %(size)s", {
                             "request": msg.req,
                             "allowed": msg.allowed,
                             "reason": msg.reason,
                             "size": msg.filesize
                         })

        if msg.reason is not None:

            for i in self.uploads:

                if i.req != msg.req:
                    continue

                i.status = msg.reason
                i.req = None

                if self.uploadsview:
                    self.uploadsview.update(i)

                if i in self.transfer_request_times:
                    del self.transfer_request_times[i]

                curtime = time.time()

                for j in self.uploads:
                    if j.user == i.user:
                        j.timequeued = curtime

                if msg.reason == "Complete":

                    """ Edge case. There are rare cases where a "Complete" status is sent to us by
                    SoulseekQt, even though it shouldn't be (?) """

                    self.upload_finished(i)

                elif msg.reason in ("Cancelled", "Disallowed extension"):

                    self.auto_clear_upload(i)

                self.check_upload_queue()
                break

        else:
            for i in self.uploads:

                if i.req != msg.req:
                    continue

                i.status = "Establishing connection"
                self.core.send_message_to_peer(i.user, slskmessages.FileRequest(None, msg.req))

                if self.uploadsview:
                    self.uploadsview.update(i)

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
            "request": transfer.req,
            "user": transfer.user
        })

        transfer.status = "Cannot connect"
        transfer.req = None

        self.core.watch_user(transfer.user)

        if transfer in self.downloads and self.downloadsview:
            self.downloadsview.update(transfer)

        elif transfer in self.uploads:
            curtime = time.time()

            for j in self.uploads:
                if j.user == transfer.user:
                    j.timequeued = curtime

            if self.uploadsview:
                self.uploadsview.update(transfer)

        if transfer in self.transfer_request_times:
            del self.transfer_request_times[transfer]

        self.check_upload_queue()

    def file_error(self, msg):
        """ Networking thread encountered a local file error """

        for i in self.downloads + self.uploads:

            if i.conn != msg.conn.conn:
                continue

            self.abort_transfer(i)
            i.status = "Local file error"

            log.add(_("I/O error: %s"), msg.strerror)

            if i in self.downloads and self.downloadsview:
                self.downloadsview.update(i)

            elif i in self.uploads:
                if self.uploadsview:
                    self.uploadsview.update(i)

                self.check_upload_queue()

    def file_request(self, msg):
        """ Got an incoming file request. Could be an upload request or a
        request to get the file that was previously queued """

        log.add_transfer("Received file request %(request)s", {
            "request": msg.req
        })

        for i in self.downloads:
            if msg.req == i.req:
                self._file_request_download(msg, i)
                return

        for i in self.uploads:
            if msg.req == i.req:
                self._file_request_upload(msg, i)
                return

        self.queue.append(slskmessages.ConnClose(msg.conn))

    def _file_request_download(self, msg, i):

        log.add_transfer("Received file upload request %(request)s for file %(filename)s from user %(user)s", {
            "request": msg.req,
            "filename": i.filename,
            "user": i.user
        })

        incompletedir = self.config.sections["transfers"]["incompletedir"]
        needupdate = True

        if i.conn is None and i.size is not None:
            i.conn = msg.conn
            i.req = None

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

                    base_name = clean_file(i.filename.replace('/', '\\').split('\\')[-1])
                    incomplete_name = os.path.join(incompletedir, "INCOMPLETE" + md5sum.hexdigest() + base_name)
                    file_handle = open(incomplete_name, 'ab+')

                    if self.config.sections["transfers"]["lock"]:
                        try:
                            import fcntl
                            try:
                                fcntl.lockf(file_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                            except IOError as error:
                                log.add(_("Can't get an exclusive lock on file - I/O error: %s"), error)
                        except ImportError:
                            pass

                    file_handle.seek(0, 2)
                    offset = file_handle.tell()

                except IOError as error:
                    log.add(_("Download I/O error: %s"), error)

                    self.abort_transfer(i)
                    i.status = "Local file error"

                else:
                    i.file = file_handle
                    i.lastbytes = offset
                    i.place = 0

                    self.core.statistics.append_stat_value("started_downloads", 1)
                    self.core.pluginhandler.download_started_notification(i.user, i.filename, incomplete_name)

                    if i.size > offset:
                        i.status = "Transferring"
                        i.legacy_attempt = False
                        self.queue.append(slskmessages.DownloadFile(i.conn, file_handle))
                        self.queue.append(slskmessages.FileOffset(i.conn, i.size, offset))

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
                    self.downloadsview.update(i)

        else:
            log.add_transfer("Download error formally known as 'Unknown file request': %(req)s (%(user)s: %(file)s)", {
                'req': str(vars(msg)),
                'user': i.user,
                'file': i.filename
            })

            self.queue.append(slskmessages.ConnClose(msg.conn))

    def _file_request_upload(self, msg, i):

        log.add_transfer("Received file download request %(request)s for file %(filename)s from user %(user)s", {
            "request": msg.req,
            "filename": i.filename,
            "user": i.user
        })
        needupdate = True

        if i.conn is None:
            i.conn = msg.conn
            i.req = None
            file_handle = None

            if i in self.transfer_request_times:
                del self.transfer_request_times[i]

            try:
                # Open File
                real_path = self.core.shares.virtual2real(i.filename)
                file_handle = open(real_path, "rb")
                offset = file_handle.tell()

            except IOError as error:
                log.add(_("Upload I/O error: %s"), error)

                self.abort_transfer(i)
                i.status = "Local file error"

            else:
                i.file = file_handle
                i.lastbytes = offset
                i.place = 0

                if self.is_privileged(i.user):
                    i.modifier = _("privileged")

                self.core.statistics.append_stat_value("started_uploads", 1)
                self.core.pluginhandler.upload_started_notification(i.user, i.filename, real_path)

                if i.size > offset:
                    i.status = "Transferring"
                    self.queue.append(slskmessages.UploadFile(i.conn, file=file_handle, size=i.size))

                    ip_address = None
                    if i.conn is not None:
                        try:
                            ip_address = i.conn.getpeername()
                        except OSError:
                            # Connection already closed
                            pass

                    log.add_upload(
                        _("Upload started: user %(user)s, IP address %(ip)s, file %(file)s"), {
                            "user": i.user,
                            "ip": ip_address,
                            "file": i.filename
                        }
                    )
                else:
                    i.lasttime = time.time()
                    self.upload_finished(i, file_handle=file_handle)
                    needupdate = False

            if self.uploadsview:
                self.uploadsview.new_transfer_notification()

                if needupdate:
                    self.uploadsview.update(i)

        else:
            log.add_transfer("Upload error formally known as 'Unknown file request': %(req)s (%(user)s: %(file)s)", {
                'req': str(vars(msg)),
                'user': i.user,
                'file': i.filename
            })

            self.queue.append(slskmessages.ConnClose(msg.conn))

    def upload_denied(self, msg):

        user = msg.conn.init.target_user

        for i in self.downloads:
            if i.user != user or i.filename != msg.file:
                continue

            if msg.reason in ("File not shared.", "File not shared", "Remote file error") and not i.legacy_attempt:
                """ The peer is possibly using an old client that doesn't support Unicode
                (Soulseek NS). Attempt to request file name encoded as latin-1 once. """

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

            if i.status != "Paused":
                if i.status == "Transferring":
                    self.abort_transfer(i, reason=msg.reason)

                i.status = msg.reason

                if self.downloadsview:
                    self.downloadsview.update(i)

                log.add_transfer("Download request denied by user %(user)s for file %(filename)s. Reason: %(reason)s", {
                    "user": user,
                    "filename": i.filename,
                    "reason": msg.reason
                })
                break

    def upload_failed(self, msg):

        user = msg.conn.init.target_user

        for i in self.downloads:
            if i.user != user or i.filename != msg.file:
                continue

            if i.status in ("Paused", "Download folder error", "Local file error", "User logged off"):
                continue

            if not i.legacy_attempt:
                """ Attempt to request file name encoded as latin-1 once. """

                self.abort_transfer(i)
                i.legacy_attempt = True
                self.get_file(i.user, i.filename, i.path, i)
                break

            """ Already failed once previously, give up """

            i.status = "Remote file error"

            if self.downloadsview:
                self.downloadsview.update(i)

            log.add_transfer("Upload attempt by user %(user)s for file %(filename)s failed. Reason: %(reason)s", {
                "filename": i.filename,
                "user": user,
                "reason": "Remote file error"
            })

    def file_download(self, msg):
        """ A file download is in progress"""

        needupdate = True

        for i in self.downloads:

            if i.conn != msg.conn:
                continue

            try:
                if i in self.transfer_request_times:
                    del self.transfer_request_times[i]

                curtime = time.time()
                i.currentbytes = msg.file.tell()

                if i.starttime is None:
                    i.starttime = curtime

                i.status = "Transferring"
                oldelapsed = i.timeelapsed
                i.timeelapsed = curtime - i.starttime
                bytesdifference = i.currentbytes - i.lastbytes

                if bytesdifference:
                    self.core.statistics.append_stat_value("downloaded_size", bytesdifference)

                if i.size > i.currentbytes:
                    if curtime > i.starttime and i.currentbytes > i.lastbytes:
                        i.speed = max(0, bytesdifference / max(1, curtime - i.lasttime))

                        if i.speed <= 0:
                            i.timeleft = "∞"
                        else:
                            i.timeleft = human_length((i.size - i.currentbytes) / i.speed)

                    if oldelapsed == i.timeelapsed:
                        needupdate = False
                else:
                    self.download_finished(msg.file, i)
                    needupdate = False

                i.lastbytes = i.currentbytes
                i.lasttime = curtime

            except IOError as error:
                log.add(_("Download I/O error: %s"), error)

                self.abort_transfer(i)
                i.status = "Local file error"

            if needupdate and self.downloadsview:
                self.downloadsview.update(i)

            break

    def file_upload(self, msg):
        """ A file upload is in progress """

        needupdate = True

        for i in self.uploads:

            if i.conn != msg.conn:
                continue

            if i in self.transfer_request_times:
                del self.transfer_request_times[i]

            curtime = time.time()
            i.currentbytes = msg.offset + msg.sentbytes

            if i.starttime is None:
                i.starttime = curtime

            i.status = "Transferring"
            oldelapsed = i.timeelapsed
            i.timeelapsed = curtime - i.starttime
            bytesdifference = i.currentbytes - i.lastbytes

            if bytesdifference:
                self.core.statistics.append_stat_value("uploaded_size", bytesdifference)

            if i.size > i.currentbytes:
                if curtime > i.starttime and i.currentbytes > i.lastbytes:
                    i.speed = max(0, bytesdifference / max(1, curtime - i.lasttime))

                    if i.speed <= 0:
                        i.timeleft = "∞"
                    else:
                        i.timeleft = human_length((i.size - i.currentbytes) / i.speed)

                if oldelapsed == i.timeelapsed:
                    needupdate = False
            else:
                self.upload_finished(i, file_handle=msg.file)
                needupdate = False

            i.lastbytes = i.currentbytes
            i.lasttime = curtime

            if needupdate and self.uploadsview:
                self.uploadsview.update(i)

            break

    def conn_close(self, conn):
        """ The remote user has closed the connection either because
        he logged off, or because there's a network problem. """

        for i in self.downloads:
            if i.conn == conn:
                self._conn_close(i, "download")
                return

        # We need a copy due to upload auto-clearing modifying the deque during iteration
        for i in self.uploads.copy():
            if i.conn == conn:
                self._conn_close(i, "upload")
                return

    def _conn_close(self, i, transfer_type):

        self.abort_transfer(i)
        auto_clear = False

        if i.status != "Finished":
            if transfer_type == "download":
                if self.user_logged_out(i.user):
                    i.status = "User logged off"
                else:
                    i.status = "Connection closed by peer"

            elif transfer_type == "upload":
                if self.user_logged_out(i.user):
                    i.status = "User logged off"
                else:
                    i.status = "Cancelled"

                    """ Transfer ended abruptly. Tell the peer to re-queue the file. If the transfer was
                    intentionally cancelled, the peer should ignore this message. """
                    self.core.send_message_to_peer(
                        i.user, slskmessages.UploadFailed(None, i.filename, i.legacy_attempt))

                auto_clear = True

        if transfer_type == "download" and self.downloadsview:
            self.downloadsview.update(i)

        elif transfer_type == "upload":
            curtime = time.time()
            for j in self.uploads:
                if j.user == i.user:
                    j.timequeued = curtime

            if auto_clear and self.auto_clear_upload(i):
                # Upload cleared
                pass
            elif self.uploadsview:
                self.uploadsview.update(i)

            self.check_upload_queue()

    def place_in_queue_request(self, msg):

        user = msg.conn.init.target_user
        privileged_user = self.is_privileged(user)
        place = 0
        transfer = None

        if self.config.sections["transfers"]["fifoqueue"]:
            for i in reversed(self.uploads):
                # Ignore non-queued files
                if i.status != "Queued":
                    continue

                if not privileged_user or self.is_privileged(i.user):
                    place += 1

                # Stop counting on the matching file
                if i.user == user and i.filename == msg.file:
                    transfer = i
                    break

        else:
            # TODO: more accurate calculation, if possible
            should_count = True
            queued_users = set()
            uploading_users = set()

            for i in reversed(self.uploads):

                # Ignore non-queued files
                if i.status != "Queued":
                    continue

                if i.user == user:
                    if not should_count:
                        continue

                    # Count all transfers for requesting user
                    place += 1

                    # Stop counting on the matching file
                    if i.filename == msg.file:
                        should_count = False
                        transfer = i

                    continue

                if i.user not in queued_users or i.user not in uploading_users:
                    user_uploading = (i.req is not None or i.conn is not None or i.status == "Getting status")

                    if user_uploading:
                        uploading_users.add(i.user)
                        continue

                    # Each unique user in the queue adds one to the placement
                    queued_users.add(i.user)

                    if not privileged_user or self.is_privileged(i.user):
                        place += 1

        if place > 0:
            self.queue.append(slskmessages.PlaceInQueue(msg.conn.conn, msg.file, place))

        if transfer is None:
            return

        # Update queue position in our list of uploads
        transfer.place = place

        if self.uploadsview:
            self.uploadsview.update(transfer)

    def place_in_queue(self, msg):
        """ The server tells us our place in queue for a particular transfer."""

        username = msg.conn.init.target_user
        filename = msg.filename

        for i in self.downloads:
            if i.user == username and i.filename == filename and i.status not in ("Finished", "Paused", "Filtered"):
                i.place = msg.place

                if self.downloadsview:
                    self.downloadsview.update(i)

                return

    def upload_queue_notification(self, msg):

        username = msg.conn.init.target_user

        if self.can_upload(username):
            log.add(_("Your buddy, %s, is attempting to upload file(s) to you."), username)

        else:
            self.core.privatechats.send_automatic_message(username, "You are not allowed to send me files.")
            log.add(_("%s is not allowed to send you file(s), but is attempting to, anyway. Warning Sent."), username)

    """ Transfer Actions """

    def get_file(self, user, filename, path="", transfer=None, size=None, bitrate=None, length=None):

        path = clean_path(path, absolute=True)

        if transfer is None:
            for i in self.downloads:
                if i.user == user and i.filename == filename and i.path == path:
                    if i.status == "Finished":
                        # Duplicate finished download found, verify that it's still present on disk in transfer_file
                        transfer = i
                        break

                    # Duplicate active/cancelled download found, stop here
                    return

        self.transfer_file(0, user, filename, path, transfer, size, bitrate, length)

    def get_folder(self, user, folder):
        self.core.send_message_to_peer(user, slskmessages.FolderContentsRequest(None, folder))

    def push_file(self, user, filename, path="", transfer=None, size=None, bitrate=None,
                  length=None, locally_queued=False):
        self.transfer_file(1, user, filename, path, transfer, size, bitrate, length, locally_queued)

    def transfer_file(self, direction, user, filename, path="", transfer=None, size=None,
                      bitrate=None, length=None, locally_queued=False):

        """ Get a single file. path is a local path. if transfer object is
        not None, update it, otherwise create a new one."""

        if not self.core.logged_in:
            return

        if transfer is None:
            transfer = Transfer(
                user=user, filename=filename, path=path,
                status="Queued", size=size, bitrate=bitrate,
                length=length
            )

            if direction == 0:
                self.downloads.appendleft(transfer)
            else:
                self._append_upload(user, filename, transfer)
        else:
            transfer.status = "Queued"

        if direction == 1:
            log.add_transfer(
                "Initializing upload request for file %(file)s to user %(user)s", {
                    'file': filename,
                    'user': user
                }
            )

        try:
            status = self.users[user].status
        except KeyError:
            status = None

        shouldupdate = True

        if direction == 0 and self.config.sections["transfers"]["enablefilters"]:
            # Only filter downloads, never uploads!
            try:
                downloadregexp = re.compile(self.config.sections["transfers"]["downloadregexp"], re.I)
                if downloadregexp.search(filename) is not None:
                    log.add_transfer("Filtering: %s", filename)
                    self.abort_transfer(transfer)
                    # The string to be displayed on the GUI
                    transfer.status = "Filtered"

                    shouldupdate = not self.auto_clear_download(transfer)
            except Exception:
                pass

        if status is None:
            self.core.watch_user(user)

        elif self.user_logged_out(user):
            transfer.status = "User logged off"

        if transfer.status not in ("Filtered", "User logged off"):
            if direction == 0:
                download_path = self.get_existing_download_path(user, filename, path, size)

                if download_path:
                    transfer.status = "Finished"
                    transfer.size = transfer.currentbytes = size

                    log.add_transfer("File %s is already downloaded", download_path)

                else:
                    log.add_transfer("Adding file %(filename)s from user %(user)s to download queue", {
                        "filename": filename,
                        "user": user
                    })
                    self.core.send_message_to_peer(
                        user, slskmessages.QueueUpload(None, filename, transfer.legacy_attempt))

            elif not locally_queued:
                log.add_transfer("Requesting to upload file %(filename)s with transfer "
                                 + "request %(request)s to user %(user)s", {
                                     "filename": filename,
                                     "request": transfer.req,
                                     "user": user
                                 })
                transfer.req = self.core.get_new_token()
                transfer.status = "Getting status"
                self.transfer_request_times[transfer] = time.time()

                real_path = self.core.shares.virtual2real(filename)
                self.core.send_message_to_peer(
                    user, slskmessages.TransferRequest(None, direction, transfer.req, filename,
                                                       self.get_file_size(real_path), real_path))

        if shouldupdate:
            if direction == 0 and self.downloadsview:
                self.downloadsview.update(transfer)

            elif self.uploadsview:
                self.uploadsview.update(transfer)

    def _append_upload(self, user, filename, transferobj):

        previously_queued = False
        old_index = 0

        for i in self.uploads:
            if i.user == user and i.filename == filename:
                if i.status == "Queued":
                    # This upload was queued previously
                    # Use the previous queue position and time
                    transferobj.place = i.place
                    transferobj.timequeued = i.timequeued
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
        else:
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

        try:
            return self.users[user].status <= 0

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

        lstlen = sum(1 for i in self.uploads if i.conn is not None)

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
                downloaddir = os.path.join(downloaddir, user)

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

        if config["transfers"]["sharedownloaddir"]:
            """ Folder downloaded and shared. Notify the server of new stats. The
            reason we don't send this message after each download is to reduce traffic from
            the server to room users, since every stat update is relayed by the server. """
            self.core.shares.send_num_shared_folders_files()

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

        except (IOError, OSError) as inst:
            log.add(
                _("Couldn't move '%(tempfile)s' to '%(file)s': %(error)s"), {
                    'tempfile': "%s" % file.name,
                    'file': newname,
                    'error': inst
                }
            )
            self.download_folder_error(i, inst)

            if self.downloadsview:
                self.downloadsview.update(i)

            return

        i.status = "Finished"
        i.currentbytes = i.size
        i.speed = None
        i.timeleft = ""
        i.conn = None

        self.core.shares.add_file_to_shared(newname)
        self.core.shares.add_file_to_buddy_shared(newname)
        self.core.statistics.append_stat_value("completed_downloads", 1)
        self.core.pluginhandler.download_finished_notification(i.user, i.filename, newname)

        # Attempt to show notification and execute commands
        self.file_downloaded_actions(i.user, newname)
        self.folder_downloaded_actions(i.user, i.path)

        # Attempt to autoclear this download, if configured
        if not self.auto_clear_download(i) and self.downloadsview:
            self.downloadsview.update(i)

        self.save_transfers("downloads")

        log.add_download(
            _("Download finished: user %(user)s, file %(file)s"), {
                'user': i.user,
                'file': i.filename
            }
        )

    def upload_finished(self, i, file_handle=None):

        if i.speed is not None:
            # Inform the server about the last upload speed for this transfer
            speed = int(i.speed)
            self.upload_speed = speed
            self.queue.append(slskmessages.SendUploadSpeed(speed))

        self.close_file(file_handle, i)

        ip_address = None
        if i.conn is not None:
            try:
                ip_address = i.conn.getpeername()
            except OSError:
                # Connection already closed
                pass

        i.status = "Finished"
        i.currentbytes = i.size
        i.speed = None
        i.timeleft = ""
        i.conn = None

        for j in self.uploads:
            if j.user == i.user:
                j.timequeued = i.lasttime

        log.add_upload(
            _("Upload finished: user %(user)s, IP address %(ip)s, file %(file)s"), {
                'user': i.user,
                'ip': ip_address,
                'file': i.filename
            }
        )

        self.core.statistics.append_stat_value("completed_uploads", 1)
        real_path = self.core.shares.virtual2real(i.filename)
        self.core.pluginhandler.upload_finished_notification(i.user, i.filename, real_path)

        # Autoclear this upload
        if not self.auto_clear_upload(i) and self.uploadsview:
            self.uploadsview.update(i)

        self.save_transfers("uploads")
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

    def _check_transfer_timeouts(self):

        while True:
            curtime = time.time()

            if self.transfer_request_times:
                for transfer, start_time in self.transfer_request_times.copy().items():
                    if (curtime - start_time) >= 30:
                        self.network_callback([slskmessages.TransferTimeout(transfer)])

            if self.core.exit.wait(1):
                # Event set, we're exiting
                return

    def _check_upload_queue_timer(self):

        while True:
            self.network_callback([slskmessages.CheckUploadQueue()])

            if self.core.exit.wait(10):
                # Event set, we're exiting
                return

    def _check_download_queue_timer(self):

        self.download_queue_timer_count = -1

        while True:
            self.download_queue_timer_count += 1
            self.network_callback([slskmessages.CheckDownloadQueue()])

            if self.core.exit.wait(180):
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

    def get_queued_uploads(self):

        # List of transfer instances of users who are not currently transferring
        list_queued = []

        # Sublist of privileged users transfers
        list_privileged = []
        use_privileged_queue = False

        # List of users
        uploading_users = set()
        queued_users = {}

        # Check users
        for i in reversed(self.uploads):
            # some file is being transferred
            if i.req is not None or i.conn is not None or i.status == "Getting status":
                if i.user not in uploading_users:
                    uploading_users.add(i.user)

            elif i.user not in queued_users:
                queued_users[i.user] = self.is_privileged(i.user)

        # Check queued uploads
        for i in reversed(self.uploads):
            if i.status == "Queued" and i.user not in uploading_users:
                if queued_users[i.user]:  # check if user is privileged
                    list_privileged.append(i)
                    use_privileged_queue = True

                elif not use_privileged_queue:
                    list_queued.append(i)

        if use_privileged_queue:
            # Upload to a privileged user
            # Only Privileged users' files will get selected
            return list_privileged

        return list_queued

    def get_upload_candidate(self, queued_uploads):

        if not queued_uploads:
            return None

        if self.config.sections["transfers"]["fifoqueue"]:
            # FIFO
            # Get the first item in the list
            upload_candidate = queued_uploads[0]

        else:
            # Round Robin
            # Get first transfer that was queued less than one second from now
            upload_candidate = None
            mintimequeued = time.time() + 1

            for i in queued_uploads:
                if i.timequeued is not None and i.timequeued < mintimequeued:
                    upload_candidate = i
                    # Break loop
                    mintimequeued = i.timequeued

        return upload_candidate

    # Find next file to upload
    def check_upload_queue(self):

        while True:
            # Check if any uploads exist
            if not self.uploads:
                return

            if not self.allow_new_uploads():
                return

            queued_uploads = self.get_queued_uploads()
            upload_candidate = self.get_upload_candidate(queued_uploads)

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

                if not self.auto_clear_upload(upload_candidate) and self.uploadsview:
                    self.uploadsview.update(upload_candidate)

                # Check queue again
                continue

            self.push_file(
                user=user, filename=upload_candidate.filename, transfer=upload_candidate
            )
            return

    def ban_user(self, user, ban_message=None):
        """
        Ban a user, cancel all the user's uploads, send a 'Banned'
        message via the transfers, and clear the transfers from the
        uploads list.
        """

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

        if transfer.status in ("Finished", "Old"):
            return

        user = transfer.user

        if self.user_logged_out(user):
            transfer.status = "User logged off"
            self.abort_transfer(transfer)

            if self.downloadsview:
                self.downloadsview.update(transfer)

            return

        self.abort_transfer(transfer)
        self.get_file(user, transfer.filename, transfer.path, transfer)

    def retry_upload(self, transfer):

        if transfer.status in ("Finished", "Old"):
            return

        user = transfer.user

        for i in self.uploads:
            if i.user != user:
                continue

            if i.req is not None or i.conn is not None or i.status == "Getting status":
                return

        if self.user_logged_out(user):
            transfer.status = "User logged off"
            self.abort_transfer(transfer)

            if not self.auto_clear_upload(transfer) and self.uploadsview:
                self.uploadsview.update(transfer)
            return

        self.push_file(user, transfer.filename, transfer.path, transfer=transfer)

    def abort_transfer(self, transfer, reason="Cancelled", send_fail_message=False):

        transfer.legacy_attempt = False
        transfer.req = None
        transfer.speed = None
        transfer.place = 0
        transfer.timeleft = ""

        if transfer.conn is not None:
            self.queue.append(slskmessages.ConnClose(transfer.conn))
            transfer.conn = None

        if transfer in self.transfer_request_times:
            del self.transfer_request_times[transfer]

        if transfer.file is not None:
            self.close_file(transfer.file, transfer)

            if transfer in self.uploads:
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

    def open_soulseek_url(self, url):

        import urllib.parse

        try:
            user, file_path = urllib.parse.unquote(url[7:]).split("/", 1)

            if file_path[-1] == "/":
                self.get_folder(user, file_path[:-1].replace("/", "\\"))
            else:
                self.get_file(user, file_path.replace("/", "\\"))

            self.downloadsview.switch_tab()

        except Exception:
            log.add(_("Invalid Soulseek URL: %s"), url)

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

        for i in self.downloads + self.uploads:
            if i.status not in ("Finished", "Paused"):
                self.abort_transfer(i)
                i.status = "Old"

    def get_downloads(self):
        """ Get a list of downloads """
        return [[i.user, i.filename, i.path, i.status, i.size, i.currentbytes, i.bitrate, i.length]
                for i in reversed(self.downloads)]

    def get_uploads(self):
        """ Get a list of finished uploads """
        return [[i.user, i.filename, i.path, i.status, i.size, i.currentbytes, i.bitrate, i.length]
                for i in reversed(self.uploads) if i.status == "Finished"]

    def save_downloads_callback(self, filename):
        json.dump(self.get_downloads(), filename, ensure_ascii=False)

    def save_uploads_callback(self, filename):
        json.dump(self.get_uploads(), filename, ensure_ascii=False)

    def save_transfers(self, transfer_type):
        """ Save list of transfers """

        self.config.create_data_folder()

        if transfer_type == "uploads":
            transfers_file = self.uploads_file_name
            callback = self.save_uploads_callback
        else:
            transfers_file = self.downloads_file_name
            callback = self.save_downloads_callback

        write_file_and_backup(transfers_file, callback)

    def server_disconnect(self):

        self.abort_transfers()
        self.save_transfers("downloads")
        self.save_transfers("uploads")

        for i in self.uploads.copy():
            if i.status != "Finished":
                self.uploads.remove(i)

        self.privilegedusers.clear()
        self.requested_folders.clear()
        self.transfer_request_times.clear()

        if self.downloadsview:
            self.downloadsview.server_disconnect()

        if self.uploadsview:
            self.uploadsview.server_disconnect()


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
