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

import os
import os.path
import re
import stat
import threading
import time

from collections import defaultdict
from collections import deque
from time import sleep

from pynicotine import slskmessages
from pynicotine.logfacility import log
from pynicotine.slskmessages import new_id
from pynicotine.utils import execute_command
from pynicotine.utils import clean_file
from pynicotine.utils import clean_path
from pynicotine.utils import get_result_bitrate_length
from pynicotine.utils import write_file_and_backup


class Transfer(object):
    """ This class holds information about a single transfer. """

    __slots__ = "conn", "user", "filename", \
                "path", "req", "size", "file", "starttime", "lasttime", \
                "offset", "currentbytes", "lastbytes", "speed", "timeelapsed", \
                "timeleft", "timequeued", \
                "modifier", "place", "bitrate", "length", "iter", "_status", \
                "laststatuschange", "legacy_attempt"

    def __init__(
        self, conn=None, user=None, filename=None,
        path=None, status=None, req=None, size=None, file=None, starttime=None,
        offset=None, currentbytes=None, speed=None, timeelapsed=None,
        timeleft=None, timequeued=None, requestconn=None,
        modifier=None, place=0, bitrate=None, length=None, iter=None, legacy_attempt=False
    ):
        self.user = user
        self.filename = filename
        self.conn = conn
        self.path = path  # Used for ???
        self.modifier = modifier
        self.req = req
        self.size = size
        self.file = file
        self.starttime = starttime
        self.lasttime = starttime
        self.offset = offset
        self.currentbytes = currentbytes
        self.lastbytes = currentbytes
        self.speed = speed
        self.timeelapsed = timeelapsed
        self.timeleft = timeleft
        self.timequeued = timequeued
        self.place = place  # Queue position
        self.bitrate = bitrate
        self.length = length
        self.iter = iter
        self.legacy_attempt = legacy_attempt
        self.setstatus(status)

    def setstatus(self, status):
        self._status = status
        self.laststatuschange = time.time()

    def getstatus(self):
        return self._status
    status = property(getstatus, setstatus)


class TransferTimeout:

    __slots__ = "transfer"

    def __init__(self, transfer):
        self.transfer = transfer


class Transfers:
    """ This is the transfers manager """

    def __init__(self, config, peerconns, queue, eventprocessor, users, ui_callback, notifications=None, pluginhandler=None):

        self.config = config
        self.peerconns = peerconns
        self.queue = queue
        self.eventprocessor = eventprocessor
        self.downloads = deque()
        self.uploads = deque()
        self.privilegedusers = set()
        self.requested_folders = defaultdict(dict)
        userstatus = set()

        self.update_limits()

        for i in self.load_download_queue():
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
                status = "Aborted"
            elif len(i) >= 4 and i[3] == "Filtered":
                status = "Filtered"
            else:
                status = "Getting status"

            self.downloads.appendleft(
                Transfer(
                    user=i[0], filename=i[1], path=i[2], status=status,
                    size=size, currentbytes=currentbytes, bitrate=bitrate,
                    length=length
                )
            )
            userstatus.add(i[0])

        for user in userstatus:
            self.eventprocessor.watch_user(user)

        self.users = users
        self.ui_callback = ui_callback
        self.notifications = notifications
        self.pluginhandler = pluginhandler
        self.downloadsview = None
        self.uploadsview = None

        self.geoip = self.eventprocessor.geoip

        # Check for transfer timeouts
        self.transfer_request_times = {}

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

    def set_transfer_views(self, downloads, uploads):
        self.downloadsview = downloads
        self.uploadsview = uploads

    """ Load Downloads """

    def get_download_queue_file_name(self):

        data_dir = self.config.data_dir
        downloads_file_json = os.path.join(data_dir, 'downloads.json')
        downloads_file_1_4_2 = os.path.join(data_dir, 'config.transfers.pickle')
        downloads_file_1_4_1 = os.path.join(data_dir, 'transfers.pickle')

        if os.path.exists(downloads_file_json):
            # New file format
            return downloads_file_json

        elif os.path.exists(downloads_file_1_4_2):
            # Nicotine+ 1.4.2+
            return downloads_file_1_4_2

        elif os.path.exists(downloads_file_1_4_1):
            # Nicotine <=1.4.1
            return downloads_file_1_4_1

        return None

    def load_current_queue_format(self, downloads_file):
        """ Loads a download queue file in json format """

        download_queue = []

        try:
            with open(downloads_file, encoding="utf-8") as handle:
                import json
                download_queue = json.load(handle)

        except Exception as inst:
            log.add(_("Something went wrong while reading your transfer list: %(error)s"), {'error': str(inst)})

        return download_queue

    def load_legacy_queue_format(self, downloads_file):
        """ Loads a download queue file in pickle format (legacy) """

        download_queue = []

        try:
            with open(downloads_file, "rb") as handle:
                from pynicotine.utils import RestrictedUnpickler
                download_queue = RestrictedUnpickler(handle, encoding='utf-8').load()

        except Exception as inst:
            log.add(_("Something went wrong while reading your transfer list: %(error)s"), {'error': str(inst)})

        return download_queue

    def load_download_queue(self):

        downloads_file = self.get_download_queue_file_name()

        if not downloads_file:
            return []

        if not downloads_file.endswith("downloads.json"):
            return self.load_legacy_queue_format(downloads_file)

        return self.load_current_queue_format(downloads_file)

    """ Privileges """

    def set_privileged_users(self, list):
        for i in list:
            self.add_to_privileged(i)

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

    def get_file_size(self, filename):

        try:
            size = os.path.getsize(filename)
        except Exception:
            # file doesn't exist (remote files are always this)
            size = 0

        return size

    def close_file(self, file, transfer):

        transfer.file = None

        if file is None:
            return

        try:
            file.close()

        except Exception as e:
            log.add_transfer("Failed to close file %(filename)s: %(error)s", {
                "filename": file.name,
                "error": e
            })

    """ Limits """

    def update_limits(self):
        """ Sends the updated speed limits to the networking thread """

        uselimit = self.config.sections["transfers"]["uselimit"]
        uploadlimit = self.config.sections["transfers"]["uploadlimit"]
        limitby = self.config.sections["transfers"]["limitby"]

        self.queue.append(slskmessages.SetUploadLimit(uselimit, uploadlimit, limitby))
        self.queue.append(slskmessages.SetDownloadLimit(self.config.sections["transfers"]["downloadlimit"]))

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
        in_progress_count = 0
        now = time.time()

        for i in self.uploads:
            if i.conn is not None and i.speed is not None:
                # Currently transferring
                in_progress_count += 1

            elif (now - i.laststatuschange) < 30:
                # Transfer initiating, changed within last 30 seconds

                if i.req is not None:
                    in_progress_count += 1

                elif i.conn is not None and i.speed is None:
                    in_progress_count += 1

                elif i.status == "Getting status":
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

        for i in self.downloads:
            if msg.user == i.user and i.status in ("Queued", "Getting status", "Establishing connection", "User logged off", "Connection closed by peer", "Cannot connect"):
                if msg.status <= 0:
                    i.status = "User logged off"
                    self.abort_transfer(i)
                    self.downloadsview.update(i)

                elif i.status in ("Getting status", "User logged off", "Connection closed by peer", "Cannot connect"):
                    self.get_file(i.user, i.filename, i.path, i)

        # We need a copy due to upload auto-clearing modifying the deque during iteration
        for i in self.uploads.copy():
            if msg.user == i.user and i.status in ("Getting status", "Establishing connection", "User logged off", "Cannot connect", "Cancelled"):
                if msg.status <= 0:
                    i.status = "User logged off"
                    self.abort_transfer(i)

                    if not self.auto_clear_upload(i):
                        self.uploadsview.update(i)

                elif i.status == "User logged off":
                    i.status = "Cancelled"

                    if not self.auto_clear_upload(i):
                        self.uploadsview.update(i)

    def got_cant_connect(self, req):
        """ We can't connect to the user, either way. """

        for i in self.downloads:
            if i.req == req:
                self._get_cant_connect_download(i)
                break

        for i in self.uploads:
            if i.req == req:
                self._get_cant_connect_upload(i)
                break

    def _get_cant_connect_download(self, i):

        i.status = "Cannot connect"
        i.req = None
        self.downloadsview.update(i)

        self.eventprocessor.watch_user(i.user)

    def _get_cant_connect_upload(self, i):

        i.status = "Cannot connect"
        i.req = None
        curtime = time.time()

        for j in self.uploads:
            if j.user == i.user:
                j.timequeued = curtime

        self.uploadsview.update(i)

        self.eventprocessor.watch_user(i.user)
        self.check_upload_queue()

    def folder_contents_response(self, conn, file_list):
        """ When we got a contents of a folder, get all the files in it, but
        skip the files in subfolders"""

        username = None
        for i in self.peerconns:
            if i.conn is conn:
                username = i.username
                break

        if username is None:
            return

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
                        h_bitrate, bitrate, h_length, length = get_result_bitrate_length(size, file[4])

                        self.get_file(
                            username, virtualpath, destination,
                            size=size, bitrate=h_bitrate, length=h_length, checkduplicate=True
                        )

                    log.add_transfer(
                        "Attempting to download files in folder %(folder)s for user %(user)s. Destination path: %(destination)s", {
                            "folder": directory,
                            "user": username,
                            "destination": destination
                        }
                    )

    def queue_upload(self, msg):
        """ Peer remotely queued a download (upload here). This is the modern replacement to
        a TransferRequest with direction 0 (download request). We will initiate the upload of
        the queued file later. """

        user = None
        for i in self.peerconns:
            if i.conn is msg.conn.conn:
                user = i.username
                break

        if user is None:
            return

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
        realpath = self.eventprocessor.shares.virtual2real(filename_utf8)

        if not self.file_is_upload_queued(user, msg.file):

            limits = True

            if self.config.sections["transfers"]["friendsnolimits"]:
                friend = user in (i[0] for i in self.config.sections["server"]["userlist"])

                if friend:
                    limits = False

            checkuser, reason = self.eventprocessor.network_filter.check_user(user, addr)

            if not checkuser:
                self.queue.append(
                    slskmessages.UploadDenied(conn=msg.conn.conn, file=msg.file, reason=reason)
                )

            elif limits and self.queue_limit_reached(user):
                uploadslimit = self.config.sections["transfers"]["queuelimit"]
                limitmsg = "User limit of %i megabytes exceeded" % (uploadslimit)
                self.queue.append(
                    slskmessages.UploadDenied(conn=msg.conn.conn, file=msg.file, reason=limitmsg)
                )

            elif limits and self.file_limit_reached(user):
                filelimit = self.config.sections["transfers"]["filelimit"]
                limitmsg = "User limit of %i files exceeded" % (filelimit)
                self.queue.append(
                    slskmessages.UploadDenied(conn=msg.conn.conn, file=msg.file, reason=limitmsg)
                )

            elif self.eventprocessor.shares.file_is_shared(user, filename_utf8, realpath):
                newupload = Transfer(
                    user=user, filename=msg.file,
                    path=os.path.dirname(realpath), status="Queued",
                    timequeued=time.time(), size=self.get_file_size(realpath), place=len(self.uploads)
                )
                self._append_upload(user, msg.file, newupload)
                self.uploadsview.update(newupload)

                if self.pluginhandler:
                    self.pluginhandler.upload_queued_notification(user, msg.file, realpath)

                self.check_upload_queue()

            else:
                self.queue.append(
                    slskmessages.UploadDenied(conn=msg.conn.conn, file=msg.file, reason="File not shared")
                )

        log.add_transfer("QueueUpload request: User %(user)s, %(msg)s", {
            'user': user,
            'msg': str(vars(msg))
        })

    def transfer_request(self, msg):

        user = response = None

        if msg.conn is not None:
            for i in self.peerconns:
                if i.conn is msg.conn.conn:
                    user = i.username
                    addr = msg.conn.addr[0]
                    break

        elif msg.tunneleduser is not None:  # Deprecated
            user = msg.tunneleduser
            addr = "127.0.0.1"

        if user is None:
            log.add_transfer("Got transfer request %s but cannot determine requestor", vars(msg))
            return

        if msg.direction == 1:
            log.add_transfer("Received upload request %(request)s for file %(filename)s from user %(user)s", {
                "request": msg.req,
                "filename": msg.file,
                "user": user
            })

            response = self.transfer_request_downloads(msg, user)

            log.add_transfer("Sending response to upload request %(request)s for file %(filename)s from user %(user)s: %(allowed)s", {
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

            log.add_transfer("Sending response to download request %(request)s for file %(filename)s from user %(user)s: %(allowed)s", {
                "request": response.req,
                "filename": msg.file,
                "user": user,
                "allowed": response.allowed
            })

        self.eventprocessor.send_message_to_peer(user, response)

    def transfer_request_downloads(self, msg, user):

        for i in self.downloads:
            if i.filename == msg.file and user == i.user and i.status not in ("Finished", "Aborted", "Filtered"):

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

                response = slskmessages.TransferResponse(None, 1, req=i.req)
                self.downloadsview.update(i)

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

            self.eventprocessor.watch_user(user)

            response = slskmessages.TransferResponse(None, 0, reason="Queued", req=transfer.req)
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
        checkuser, reason = self.eventprocessor.network_filter.check_user(user, addr)

        if not checkuser:
            return slskmessages.TransferResponse(None, 0, reason=reason, req=msg.req)

        # Do we actually share that file with the world?
        realpath = self.eventprocessor.shares.virtual2real(msg.file)

        if not self.eventprocessor.shares.file_is_shared(user, msg.file, realpath):
            return slskmessages.TransferResponse(None, 0, reason="File not shared", req=msg.req)

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
            uploadslimit = self.config.sections["transfers"]["queuelimit"]
            return slskmessages.TransferResponse(None, 0, reason="User limit of %i megabytes exceeded" % (uploadslimit), req=msg.req)

        if limits and self.file_limit_reached(user):
            filelimit = self.config.sections["transfers"]["filelimit"]
            limitmsg = "User limit of %i files exceeded" % (filelimit)
            return slskmessages.TransferResponse(None, 0, reason=limitmsg, req=msg.req)

        # All checks passed, user can queue file!
        if self.pluginhandler:
            self.pluginhandler.upload_queued_notification(user, msg.file, realpath)

        # Is user already downloading/negotiating a download?
        already_downloading = False

        for i in self.uploads:
            if i.user == user:
                if i.req is not None or i.conn is not None or i.status == "Getting status":
                    already_downloading = True

        if not self.allow_new_uploads() or already_downloading:

            response = slskmessages.TransferResponse(None, 0, reason="Queued", req=msg.req)
            newupload = Transfer(
                user=user, filename=msg.file,
                path=os.path.dirname(realpath), status="Queued",
                timequeued=time.time(), size=self.get_file_size(realpath),
                place=len(self.uploads)
            )
            self._append_upload(user, msg.file, newupload)
            self.uploadsview.update(newupload)
            return response

        # All checks passed, starting a new upload.
        size = self.get_file_size(realpath)
        response = slskmessages.TransferResponse(None, 1, req=msg.req, filesize=size)

        transferobj = Transfer(
            user=user, filename=msg.file,
            path=os.path.dirname(realpath), status="Getting status",
            req=msg.req, size=size, place=len(self.uploads)
        )

        self.transfer_request_times[transferobj] = time.time()
        self._append_upload(user, msg.file, transferobj)

        self.uploadsview.update(transferobj)
        return response

    def transfer_response(self, msg):

        """ Got a response to the file request from the peer."""

        log.add_transfer("Received response for transfer request %(request)s. Allowed: %(allowed)s. Reason: %(reason)s. Filesize: %(size)s", {
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

                elif msg.reason == "Cancelled":

                    self.auto_clear_upload(i)

                self.check_upload_queue()
                break

        else:
            for i in self.uploads:

                if i.req != msg.req:
                    continue

                i.status = "Establishing connection"
                self.eventprocessor.send_message_to_peer(i.user, slskmessages.FileRequest(None, msg.req))
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

        self.eventprocessor.watch_user(transfer.user)

        if transfer in self.downloads:
            self.downloadsview.update(transfer)

        elif transfer in self.uploads:
            curtime = time.time()

            for j in self.uploads:
                if j.user == transfer.user:
                    j.timequeued = curtime

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

            if i in self.downloads:
                self.downloadsview.update(i)

            elif i in self.uploads:
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

        downloaddir = self.config.sections["transfers"]["downloaddir"]
        incompletedir = self.config.sections["transfers"]["incompletedir"]
        needupdate = True

        if i.conn is None and i.size is not None:
            i.conn = msg.conn
            i.req = None

            if i in self.transfer_request_times:
                del self.transfer_request_times[i]

            if not incompletedir:
                if i.path and i.path[0] == '/':
                    incompletedir = i.path
                else:
                    incompletedir = os.path.join(downloaddir, i.path)

            try:
                if not os.access(incompletedir, os.F_OK):
                    os.makedirs(incompletedir)
                if not os.access(incompletedir, os.R_OK | os.W_OK | os.X_OK):
                    raise OSError("Download directory %s Permissions error.\nDir Permissions: %s" % (incompletedir, oct(os.stat(incompletedir)[stat.ST_MODE] & 0o777)))

            except OSError as strerror:
                log.add(_("OS error: %s"), strerror)

                self.abort_transfer(i)
                i.status = "Download directory error"

                if self.notifications:
                    self.notifications.new_notification(_("OS error: %s") % strerror, title=_("Folder download error"))

            else:
                f = None
                try:
                    from hashlib import md5
                    m = md5()
                    m.update((i.filename + i.user).encode('utf-8'))

                    basename = clean_file(i.filename.replace('/', '\\').split('\\')[-1])
                    fname = os.path.join(incompletedir, "INCOMPLETE" + m.hexdigest() + basename)
                    f = open(fname, 'ab+')

                    if self.config.sections["transfers"]["lock"]:
                        try:
                            import fcntl
                            try:
                                fcntl.lockf(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                            except IOError as strerror:
                                log.add(_("Can't get an exclusive lock on file - I/O error: %s"), strerror)
                        except ImportError:
                            pass

                    f.seek(0, 2)
                    size = f.tell()

                except IOError as strerror:
                    log.add(_("Download I/O error: %s"), strerror)

                    self.abort_transfer(i)
                    i.status = "Local file error"

                else:
                    i.currentbytes = size
                    i.file = f
                    i.place = 0
                    i.offset = size
                    i.starttime = time.time()

                    self.eventprocessor.statistics.append_stat_value("started_downloads", 1)

                    if i.size > size:
                        i.status = "Transferring"
                        i.legacy_attempt = False
                        self.queue.append(slskmessages.DownloadFile(i.conn, size, f, i.size))
                        log.add_download(
                            _("Download started: user %(user)s, file %(file)s"), {
                                "user": i.user,
                                "file": "%s" % f.name
                            }
                        )
                    else:
                        self.download_finished(f, i)
                        needupdate = False

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

        if i.conn is None:
            i.conn = msg.conn
            i.req = None
            f = None

            if i in self.transfer_request_times:
                del self.transfer_request_times[i]

            try:
                # Open File
                realpath = self.eventprocessor.shares.virtual2real(i.filename)
                f = open(realpath, "rb")

            except IOError as strerror:
                log.add(_("Upload I/O error: %s"), strerror)

                self.abort_transfer(i)
                i.status = "Local file error"

            else:
                self.queue.append(slskmessages.UploadFile(i.conn, file=f, size=i.size))
                i.status = "Transferring"
                i.file = f

                if self.is_privileged(i.user):
                    i.modifier = _("privileged")

                self.eventprocessor.statistics.append_stat_value("started_uploads", 1)

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

            self.uploadsview.new_transfer_notification()
            self.uploadsview.update(i)

            if i.size == 0:
                # If filesize is 0, we will not receive a UploadFile message later. Finish now.
                i.conn = None
                i.lasttime = time.time()
                self.upload_finished(i, file=f)

        else:
            log.add_transfer("Upload error formally known as 'Unknown file request': %(req)s (%(user)s: %(file)s)", {
                'req': str(vars(msg)),
                'user': i.user,
                'file': i.filename
            })

            self.queue.append(slskmessages.ConnClose(msg.conn))

    def upload_denied(self, msg):

        user = None
        for i in self.peerconns:
            if i.conn is msg.conn.conn:
                user = i.username
                break

        if user is None:
            return

        for i in self.downloads:
            if i.user != user or i.filename != msg.file:
                continue

            if msg.reason in ("File not shared.", "File not shared", "Remote file error") and \
                    not i.legacy_attempt:
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

            elif i.status != "Aborted":
                if i.status == "Transferring":
                    self.abort_transfer(i, reason=msg.reason)

                i.status = msg.reason
                self.downloadsview.update(i)

                log.add_transfer("Download request denied by user %(user)s for file %(filename)s. Reason: %(reason)s", {
                    "user": user,
                    "filename": i.filename,
                    "reason": msg.reason
                })
                break

    def upload_failed(self, msg):

        user = None
        for i in self.peerconns:
            if i.conn is msg.conn.conn:
                user = i.username
                break

        if user is None:
            return

        for i in self.downloads:
            if i.user != user or i.filename != msg.file:
                continue

            if i.status in ("Aborted", "Local file error", "User logged off"):
                continue

            if not i.legacy_attempt:
                """ Attempt to request file name encoded as latin-1 once. """

                self.abort_transfer(i)
                i.legacy_attempt = True
                self.get_file(i.user, i.filename, i.path, i)
                break

            else:
                """ Already failed once previously, give up """

                i.status = "Remote file error"
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

                if i.lastbytes is None:
                    i.lastbytes = i.currentbytes
                if i.starttime is None:
                    i.starttime = curtime
                if i.lasttime is None:
                    i.lasttime = curtime - 1

                i.status = "Transferring"
                oldelapsed = i.timeelapsed
                i.timeelapsed = curtime - i.starttime

                if curtime > i.starttime and \
                        i.currentbytes > i.lastbytes:

                    bytesdifference = (i.currentbytes - i.lastbytes)
                    self.eventprocessor.statistics.append_stat_value("downloaded_size", bytesdifference)

                    try:
                        i.speed = max(0, bytesdifference / (curtime - i.lasttime))
                    except ZeroDivisionError:
                        i.speed = None

                    if i.speed <= 0.0:
                        i.speed = None

                    if i.speed is None:
                        i.timeleft = "∞"
                    else:
                        i.timeleft = self.get_time((i.size - i.currentbytes) / i.speed)

                i.lastbytes = i.currentbytes
                i.lasttime = curtime

                if i.size > i.currentbytes:
                    if oldelapsed == i.timeelapsed:
                        needupdate = False
                else:
                    self.download_finished(msg.file, i)
                    needupdate = False

            except IOError as strerror:
                log.add(_("Download I/O error: %s"), strerror)

                self.abort_transfer(i)
                i.status = "Local file error"

            if needupdate:
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
            if i.starttime is None:
                i.starttime = curtime
                i.offset = msg.offset

            lastspeed = None
            if i.speed is not None:
                lastspeed = i.speed

            i.currentbytes = msg.offset + msg.sentbytes
            oldelapsed = i.timeelapsed
            i.timeelapsed = curtime - i.starttime

            if curtime > i.starttime and \
                    i.currentbytes > i.lastbytes:

                bytesdifference = (i.currentbytes - i.lastbytes)
                self.eventprocessor.statistics.append_stat_value("uploaded_size", bytesdifference)

                try:
                    i.speed = max(0, bytesdifference / (curtime - i.lasttime))
                except ZeroDivisionError:
                    i.speed = lastspeed  # too fast!

                if i.speed <= 0.0:
                    i.speed = None

                if i.speed is None:
                    i.timeleft = "∞"
                else:
                    i.timeleft = self.get_time((i.size - i.currentbytes) / i.speed)

            i.lastbytes = i.currentbytes
            i.lasttime = curtime

            if i.size > i.currentbytes:
                if oldelapsed == i.timeelapsed:
                    needupdate = False
                i.status = "Transferring"

            elif i.size is None:
                # Failed?
                self.check_upload_queue()
                sleep(0.01)
            else:
                self.upload_finished(i, file=msg.file)
                needupdate = False

            if needupdate:
                self.uploadsview.update(i)

            break

    def conn_close(self, conn, addr, user, error):
        """ The remote user has closed the connection either because
        he logged off, or because there's a network problem. """

        for i in self.downloads:
            if i.conn == conn:
                self._conn_close(conn, addr, i, "download")

        # We need a copy due to upload auto-clearing modifying the deque during iteration
        for i in self.uploads.copy():
            if not isinstance(error, ConnectionRefusedError) and i.conn != conn:
                continue

            if i.user != user:
                continue

            self._conn_close(conn, addr, i, "upload")

    def _conn_close(self, conn, addr, i, type):

        self.abort_transfer(i)
        auto_clear = False

        if i.status != "Finished":
            if type == "download":
                if self.user_logged_out(i.user):
                    i.status = "User logged off"
                else:
                    i.status = "Connection closed by peer"

            elif type == "upload":
                if self.user_logged_out(i.user):
                    i.status = "User logged off"
                else:
                    i.status = "Cancelled"

                    """ Transfer ended abruptly. Tell the peer to re-queue the file. If the transfer was
                    intentionally cancelled, the peer should ignore this message. """
                    self.eventprocessor.send_message_to_peer(i.user, slskmessages.UploadFailed(None, i.filename, i.legacy_attempt))

                auto_clear = True

        if type == "download":
            self.downloadsview.update(i)

        elif type == "upload":
            curtime = time.time()
            for j in self.uploads:
                if j.user == i.user:
                    j.timequeued = curtime

            if auto_clear and self.auto_clear_upload(i):
                # Upload cleared
                pass
            else:
                self.uploadsview.update(i)

            self.check_upload_queue()

    def place_in_queue_request(self, msg):

        user = None
        for i in self.peerconns:
            if i.conn is msg.conn.conn:
                user = i.username
                break

        if user is None:
            return

        privileged_user = self.is_privileged(user)
        place = 0

        if self.config.sections["transfers"]["fifoqueue"]:
            for i in reversed(self.uploads):
                # Ignore non-queued files
                if i.status != "Queued":
                    continue

                if not privileged_user or self.is_privileged(i.user):
                    place += 1

                # Stop counting on the matching file
                if i.user == user and i.filename == msg.file:
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

        self.queue.append(slskmessages.PlaceInQueue(msg.conn.conn, msg.file, place))

    def place_in_queue(self, msg):
        """ The server tells us our place in queue for a particular transfer."""

        username = None
        for i in self.peerconns:
            if i.conn is msg.conn.conn:
                username = i.username
                break
        else:
            return

        filename = msg.filename

        for i in self.downloads:
            if i.user == username and i.filename == filename and i.status not in ("Finished", "Aborted", "Filtered"):
                i.place = msg.place
                self.downloadsview.update(i)
                return

    def upload_queue_notification(self, msg):

        username = None

        for i in self.peerconns:
            if i.conn is msg.conn.conn:
                username = i.username
                break

        if username is None:
            return

        if self.can_upload(username):
            log.add(_("Your buddy, %s, is attempting to upload file(s) to you."), username)

        else:
            self.eventprocessor.send_automatic_message(username, "You are not allowed to send me files.")
            log.add(_("%s is not allowed to send you file(s), but is attempting to, anyway. Warning Sent."), username)

    """ Transfer Actions """

    def get_file(self, user, filename, path="", transfer=None, size=None, bitrate=None, length=None, checkduplicate=False):

        path = clean_path(path, absolute=True)

        if checkduplicate:
            for i in self.downloads:
                if i.user == user and i.filename == filename and i.path == path:
                    # Don't add duplicate downloads
                    return

        self.transfer_file(0, user, filename, path, transfer, size, bitrate, length)

    def push_file(self, user, filename, path="", transfer=None, size=None, bitrate=None, length=None, locally_queued=False):
        self.transfer_file(1, user, filename, path, transfer, size, bitrate, length, locally_queued)

    def transfer_file(self, direction, user, filename, path="", transfer=None, size=None, bitrate=None, length=None, locally_queued=False):

        """ Get a single file. path is a local path. if transfer object is
        not None, update it, otherwise create a new one."""

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

        if not direction and self.config.sections["transfers"]["enablefilters"]:
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
            self.eventprocessor.watch_user(user)

        elif self.user_logged_out(user):
            transfer.status = "User logged off"

        if transfer.status not in ("Filtered", "User logged off"):
            if direction == 0:
                log.add_transfer("Adding file %(filename)s from user %(user)s to download queue", {
                    "filename": filename,
                    "user": user
                })
                self.eventprocessor.send_message_to_peer(user, slskmessages.QueueUpload(None, filename, transfer.legacy_attempt))

            elif not locally_queued:
                log.add_transfer("Requesting to upload file %(filename)s with transfer request %(request)s to user %(user)s", {
                    "filename": filename,
                    "request": transfer.req,
                    "user": user
                })
                transfer.req = new_id()
                transfer.status = "Getting status"
                self.transfer_request_times[transfer] = time.time()

                realpath = self.eventprocessor.shares.virtual2real(filename)
                self.eventprocessor.send_message_to_peer(user, slskmessages.TransferRequest(None, direction, transfer.req, filename, self.get_file_size(realpath), realpath))

        if shouldupdate:
            if direction == 0:
                self.downloadsview.update(transfer)
            else:
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

            # Remote Uploads only for users in list
            if transfers["uploadallowed"] == 2:
                # Users in userlist
                if user not in (i[0] for i in self.config.sections["server"]["userlist"]):
                    # Not a buddy
                    return False

            if transfers["uploadallowed"] == 0:
                # No One can sent files to you
                return False

            if transfers["uploadallowed"] == 1:
                # Everyone can sent files to you
                return True

            if transfers["uploadallowed"] == 3:
                # Trusted buddies
                userlist = [i[0] for i in self.config.sections["server"]["userlist"]]

                if user not in userlist:
                    # Not a buddy
                    return False
                if not self.config.sections["server"]["userlist"][userlist.index(user)][4]:
                    # Not Trusted
                    return False

            return True

        return False

    def user_logged_out(self, user):
        """ Check if a user who previously queued a file has logged out since """

        try:
            return (self.users[user].status <= 0)

        except (KeyError, TypeError):
            return False

    def get_folder_destination(self, user, directory):

        # Check if a custom download location was specified
        if user in self.requested_folders and directory in self.requested_folders[user] and self.requested_folders[user][directory]:
            download_location = self.requested_folders[user][directory]

        else:
            download_location = self.config.sections["transfers"]["downloaddir"]

        # Get the last folder in directory path
        target_name = directory.rstrip('\\').split('\\')[-1]

        # Merge download path with target folder name
        destination = os.path.join(download_location, target_name)

        # Make sure the target folder doesn't exist
        # If it exists, append a number to the folder name
        orig_destination = destination
        counter = 1

        while os.path.exists(destination):
            destination = orig_destination + " (" + str(counter) + ")"
            counter += 1

        return destination

    def get_total_uploads_allowed(self):

        if self.config.sections["transfers"]["useupslots"]:
            maxupslots = self.config.sections["transfers"]["uploadslots"]
            return maxupslots
        else:
            lstlen = sum(1 for i in self.uploads if i.conn is not None)

            if self.allow_new_uploads():
                return lstlen + 1
            else:
                return lstlen

    def get_time(self, seconds):

        sec = int(seconds % 60)
        minutes = int(seconds / 60 % 60)
        hours = int(seconds / 3600 % 24)
        days = int(seconds / 86400)

        time_string = "%02d:%02d:%02d" % (hours, minutes, sec)
        if days > 0:
            time_string = str(days) + "." + time_string

        return time_string

    def get_upload_queue_size(self, username=None):

        if self.is_privileged(username):
            queue_size = 0

            for i in self.uploads:
                if i.status == "Queued" and self.is_privileged(i.user):
                    queue_size += 1

            return queue_size

        return sum(1 for i in self.uploads if i.status == "Queued")

    def get_renamed(self, name):
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

        if self.notifications and config["notifications"]["notification_popup_file"]:
            self.notifications.new_notification(
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

    def folder_downloaded_actions(self, user, filepath, folderpath):

        # walk through downloads and break if any file in the same folder exists, else execute
        for i in self.downloads:
            if i.status not in ("Finished", "Aborted", "Filtered") and i.path == folderpath:
                return

        config = self.config.sections

        if config["transfers"]["sharedownloaddir"]:
            """ Folder downloaded and shared. Notify the server of new stats. The
            reason we don't send this message after each download is to reduce traffic from
            the server to room users, since every stat update is relayed by the server. """
            self.eventprocessor.shares.send_num_shared_folders_files()

        if not folderpath:
            return

        if self.notifications and config["notifications"]["notification_popup_folder"]:
            self.notifications.new_notification(
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

    def download_finished(self, file, i):

        self.close_file(file, i)

        downloaddir = self.config.sections["transfers"]["downloaddir"]
        basename = clean_file(i.filename.replace('/', '\\').split('\\')[-1])

        if i.path and i.path[0] == '/':
            folder = i.path
        else:
            folder = os.path.join(downloaddir, i.path)

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

        i.status = "Finished"
        i.currentbytes = i.size
        i.speed = None
        i.timeleft = ""
        i.conn = None

        self.eventprocessor.shares.add_file_to_shared(newname)
        self.eventprocessor.shares.add_file_to_buddy_shared(newname)
        self.eventprocessor.statistics.append_stat_value("completed_downloads", 1)

        # Attempt to show notification and execute commands
        self.file_downloaded_actions(i.user, newname)
        self.folder_downloaded_actions(i.user, newname, i.path)

        # Attempt to autoclear this download, if configured
        if not self.auto_clear_download(i):
            self.downloadsview.update(i)

        self.save_downloads()

        log.add_download(
            _("Download finished: user %(user)s, file %(file)s"), {
                'user': i.user,
                'file': i.filename
            }
        )

    def upload_finished(self, i, file=None):

        if i.speed is not None:
            speedbytes = int(i.speed)
            self.eventprocessor.speed = speedbytes
            self.queue.append(slskmessages.SendUploadSpeed(speedbytes))

        self.close_file(file, i)

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

        self.eventprocessor.statistics.append_stat_value("completed_uploads", 1)

        # Autoclear this upload
        if not self.auto_clear_upload(i):
            self.uploadsview.update(i)

        self.check_upload_queue()

    def auto_clear_download(self, transfer):
        if self.config.sections["transfers"]["autoclear_downloads"]:
            self.downloads.remove(transfer)
            self.downloadsview.remove_specific(transfer, True)
            return True

        return False

    def auto_clear_upload(self, transfer):
        if self.config.sections["transfers"]["autoclear_uploads"]:
            self.uploads.remove(transfer)
            self.uploadsview.remove_specific(transfer, True)
            return True

        return False

    def _check_transfer_timeouts(self):

        while True:
            curtime = time.time()

            if self.transfer_request_times:
                for transfer, start_time in self.transfer_request_times.copy().items():
                    if (curtime - start_time) >= 30:
                        self.ui_callback([TransferTimeout(transfer)])

            if self.eventprocessor.exit.wait(1):
                # Event set, we're exiting
                return

    def _check_upload_queue_timer(self):

        while True:
            self.ui_callback([slskmessages.CheckUploadQueue()])

            if self.eventprocessor.exit.wait(10):
                # Event set, we're exiting
                return

    def _check_download_queue_timer(self):

        while True:
            self.ui_callback([slskmessages.CheckDownloadQueue()])

            if self.eventprocessor.exit.wait(180):
                # Event set, we're exiting
                return

    # Find failed or stuck downloads and attempt to queue them.
    # Also ask for the queue position of downloads.
    def check_download_queue(self):

        statuslist = ("Cannot connect", "Connection closed by peer", "Local file error", "Remote file error")

        for transfer in self.downloads:
            if transfer.status in statuslist:
                self.abort_transfer(transfer)
                self.get_file(transfer.user, transfer.filename, transfer.path, transfer)

            elif transfer.status == "Queued":
                self.eventprocessor.send_message_to_peer(
                    transfer.user,
                    slskmessages.PlaceInQueueRequest(None, transfer.filename, transfer.legacy_attempt)
                )

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
        for i in self.uploads:
            if i.req is not None or i.conn is not None or i.status == "Getting status":  # some file is being transferred
                if i.user not in uploading_users:
                    uploading_users.add(i.user)

            elif i.user not in queued_users:
                queued_users[i.user] = self.is_privileged(i.user)

        # Check queued uploads
        for i in self.uploads:
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
            if not len(self.uploads):
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

                if not self.auto_clear_upload(upload_candidate):
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
            banmsg = _("Banned (%s)") % ban_message
        elif self.config.sections["transfers"]["usecustomban"]:
            banmsg = _("Banned (%s)") % self.config.sections["transfers"]["customban"]
        else:
            banmsg = _("Banned")

        for upload in self.uploads.copy():
            if upload.user != user:
                continue

            self.abort_transfer(upload, reason=banmsg, send_fail_message=True)
            self.uploadsview.remove_specific(upload)

        self.eventprocessor.network_filter.ban_user(user)

    def retry_download(self, transfer):

        if transfer.status in ("Finished", "Old"):
            return

        user = transfer.user

        if self.user_logged_out(user):
            transfer.status = "User logged off"
            self.abort_transfer(transfer)
            self.downloadsview.update(transfer)
            return

        self.abort_transfer(transfer)
        self.get_file(user, transfer.filename, transfer.path, transfer)

    def retry_upload(self, transfer):

        if transfer.status in ("Finished", "Old"):
            return

        user = transfer.user

        for i in self.uploads:
            if i.user == user:
                if i.req is not None or i.conn is not None or i.status == "Getting status":
                    return

        if self.user_logged_out(user):
            transfer.status = "User logged off"
            self.abort_transfer(transfer)

            if not self.auto_clear_upload(transfer):
                self.uploadsview.update(transfer)
            return

        self.push_file(user, transfer.filename, transfer.path, transfer=transfer)

    def abort_transfer(self, transfer, reason="Cancelled", send_fail_message=False):

        transfer.legacy_attempt = False
        transfer.req = None
        transfer.speed = None
        transfer.place = None
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
            self.eventprocessor.send_message_to_peer(transfer.user, slskmessages.UploadDenied(None, file=transfer.filename, reason=reason))

    """ Exit """

    def abort_transfers(self):
        """ Stop all transfers on disconnect/shutdown """

        for i in self.downloads + self.uploads:
            if i.status == "Aborted":
                self.abort_transfer(i)
                i.status = "Paused"

            elif i.status != "Finished":
                self.abort_transfer(i)
                i.status = "Old"

    def get_downloads(self):
        """ Get a list of incomplete and not aborted downloads """
        return [[i.user, i.filename, i.path, i.status, i.size, i.currentbytes, i.bitrate, i.length] for i in self.downloads if i.status != "Finished"]

    def save_downloads_callback(self, f):
        import json
        json.dump(self.get_downloads(), f, ensure_ascii=False)

    def save_downloads(self):
        """ Save list of files to be downloaded """

        self.config.create_data_folder()
        downloads_file = os.path.join(self.config.data_dir, 'downloads.json')

        write_file_and_backup(downloads_file, self.save_downloads_callback)

    def disconnect(self):
        self.abort_transfers()
        self.save_downloads()


class Statistics:

    def __init__(self, config, ui_callback=None):

        self.config = config
        self.ui_callback = ui_callback
        self.session_stats = {}

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
