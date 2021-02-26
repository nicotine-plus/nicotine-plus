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

from hashlib import md5
from time import sleep

from pynicotine import slskmessages
from pynicotine.logfacility import log
from pynicotine.slskmessages import new_id
from pynicotine.utils import execute_command
from pynicotine.utils import clean_file
from pynicotine.utils import clean_path
from pynicotine.utils import get_result_bitrate_length
from pynicotine.utils import write_log


class Transfer(object):
    """ This class holds information about a single transfer. """

    __slots__ = "conn", "user", "realfilename", "filename", \
                "path", "req", "size", "file", "starttime", "lasttime", \
                "offset", "currentbytes", "lastbytes", "speed", "timeelapsed", \
                "timeleft", "timequeued", "transfertimer", "requestconn", \
                "modifier", "place", "bitrate", "length", "iter", "_status", \
                "laststatuschange", "legacy_attempt"

    def __init__(
        self, conn=None, user=None, realfilename=None, filename=None,
        path=None, status=None, req=None, size=None, file=None, starttime=None,
        offset=None, currentbytes=None, speed=None, timeelapsed=None,
        timeleft=None, timequeued=None, transfertimer=None, requestconn=None,
        modifier=None, place=0, bitrate=None, length=None, iter=None, legacy_attempt=False
    ):
        self.user = user
        self.realfilename = realfilename  # Sent as is to the user announcing what file we're sending
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
        self.transfertimer = transfertimer
        self.requestconn = None
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

    __slots__ = "req", "callback"

    def __init__(self, req, callback):
        self.req = req
        self.callback = callback

    def timeout(self):
        self.callback([self])


class Transfers:
    """ This is the transfers manager"""
    FAILED_TRANSFERS = ["Cannot connect", "Connection closed by peer", "Local file error", "Remote file error"]
    COMPLETED_TRANSFERS = ["Finished", "Filtered", "Aborted", "Cancelled"]
    PRE_TRANSFER = ["Queued"]
    TRANSFER = ["Requesting file", "Initializing transfer", "Transferring"]

    def __init__(self, peerconns, queue, eventprocessor, users, ui_callback, notifications=None, pluginhandler=None):

        self.peerconns = peerconns
        self.queue = queue
        self.eventprocessor = eventprocessor
        self.downloads = []
        self.uploads = []
        self.privilegedusers = set()
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
                status = "Paused"
            elif len(i) >= 4 and i[3] == "Filtered":
                status = "Filtered"
            else:
                status = "Getting status"

            self.downloads.append(
                Transfer(
                    user=i[0], filename=i[1], path=i[2], status=status,
                    size=size, currentbytes=currentbytes, bitrate=bitrate,
                    length=length
                )
            )
            userstatus.add(i[0])

        for i in userstatus:
            if i not in self.eventprocessor.watchedusers:
                self.queue.put(slskmessages.AddUser(i))

        self.users = users
        self.ui_callback = ui_callback
        self.notifications = notifications
        self.pluginhandler = pluginhandler
        self.downloadsview = None
        self.uploadsview = None

        # queue sizes
        self.privcount = 0
        self.usersqueued = {}
        self.privusersqueued = {}
        self.geoip = self.eventprocessor.geoip

        # Check for failed downloads if option is enabled (1 min delay)
        self.start_check_download_queue_timer()

    def get_download_queue_file_name(self):

        data_dir = self.eventprocessor.config.data_dir
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

    def set_transfer_views(self, downloads, uploads):
        self.downloadsview = downloads
        self.uploadsview = uploads

    def set_privileged_users(self, list):
        for i in list:
            self.add_to_privileged(i)

    def add_to_privileged(self, user):

        self.privilegedusers.add(user)

        if user in self.usersqueued:
            self.privusersqueued.setdefault(user, 0)
            self.privusersqueued[user] += self.usersqueued[user]
            self.privcount += self.usersqueued[user]
            del self.usersqueued[user]

    def update_limits(self):
        """ Sends the updated speed limits to the networking thread """

        uselimit = self.eventprocessor.config.sections["transfers"]["uselimit"]
        uploadlimit = self.eventprocessor.config.sections["transfers"]["uploadlimit"]
        limitby = self.eventprocessor.config.sections["transfers"]["limitby"]

        self.queue.put(slskmessages.SetUploadLimit(uselimit, uploadlimit, limitby))
        self.queue.put(slskmessages.SetDownloadLimit(self.eventprocessor.config.sections["transfers"]["downloadlimit"]))

    def user_logged_out(self, user):
        """ Check if a user who previously queued a file has logged out since """

        try:
            return (self.users[user].status <= 0)

        except (KeyError, TypeError):
            return False

    def get_user_status(self, msg):
        """ We get a status of a user and if he's online, we request a file from him """

        for i in self.downloads:
            if msg.user == i.user and i.status in ("Queued", "Getting status", "Establishing connection", "User logged off", "Connection closed by peer", "Aborted", "Cannot connect", "Paused"):
                if msg.status > 0:
                    if i.status not in ("Queued", "Aborted", "Cannot connect", "Paused"):
                        self.get_file(i.user, i.filename, i.path, i)
                else:
                    if i.status not in ("Aborted", "Filtered"):
                        i.status = "User logged off"
                        self.abort_transfer(i, send_fail_message=False)
                        self.downloadsview.update(i)

        for i in self.uploads:
            if msg.user == i.user and i.status in ("Getting status", "Establishing connection", "Initializing transfer", "Connection closed by peer", "Cannot connect"):
                if msg.status <= 0:
                    i.status = "User logged off"
                    self.abort_transfer(i, send_fail_message=False)
                    self.uploadsview.update(i)

        if msg.status <= 0:
            self.check_upload_queue()

    def get_file(self, user, filename, path="", transfer=None, size=None, bitrate=None, length=None, checkduplicate=False):
        path = clean_path(path, absolute=True)

        if checkduplicate:
            for i in self.downloads:
                if i.user == user and i.filename == filename and i.path == path:
                    # Don't add duplicate downloads
                    return

        self.transfer_file(0, user, filename, path, transfer, size, bitrate, length)

    def push_file(self, user, filename, realfilename, path="", transfer=None, size=None, bitrate=None, length=None):
        if size is None:
            size = self.get_file_size(realfilename)

        self.transfer_file(1, user, filename, path, transfer, size, bitrate, length, realfilename)

    def transfer_file(self, direction, user, filename, path="", transfer=None, size=None, bitrate=None, length=None, realfilename=None):

        """ Get a single file. path is a local path. if transfer object is
        not None, update it, otherwise create a new one."""

        if transfer is None:
            transfer = Transfer(
                user=user, filename=filename, realfilename=realfilename, path=path,
                status="Getting status", size=size, bitrate=bitrate,
                length=length
            )

            if direction == 0:
                self.downloads.append(transfer)
            else:
                self._append_upload(user, filename, transfer)
        else:
            transfer.status = "Getting status"

        log.add_transfer(
            "Initializing transfer request for file %(file)s to user %(user)s, direction: %(direction)s", {
                'file': filename,
                'user': user,
                'direction': direction
            }
        )

        try:
            status = self.users[user].status
        except KeyError:
            status = None

        shouldupdate = True

        if not direction and self.eventprocessor.config.sections["transfers"]["enablefilters"]:
            # Only filter downloads, never uploads!
            try:
                downloadregexp = re.compile(self.eventprocessor.config.sections["transfers"]["downloadregexp"], re.I)
                if downloadregexp.search(filename) is not None:
                    log.add_transfer("Filtering: %s", filename)
                    self.abort_transfer(transfer)
                    # The string to be displayed on the GUI
                    transfer.status = "Filtered"

                    shouldupdate = not self.auto_clear_download(transfer)
            except Exception:
                pass

        if status is None:
            if user not in self.eventprocessor.watchedusers:
                self.queue.put(slskmessages.AddUser(user))

        if transfer.status != "Filtered":
            transfer.req = new_id()
            realpath = self.eventprocessor.shares.virtual2real(filename)
            request = slskmessages.TransferRequest(None, direction, transfer.req, filename, self.get_file_size(realpath), realpath)
            self.eventprocessor.send_message_to_peer(user, request)

            if direction == 0:
                log.add_transfer("Requesting to download file %(filename)s with transfer request %(request)s from user %(user)s", {
                    "filename": filename,
                    "request": transfer.req,
                    "user": user
                })
            else:
                log.add_transfer("Requesting to upload file %(filename)s with transfer request %(request)s to user %(user)s", {
                    "filename": filename,
                    "request": transfer.req,
                    "user": user
                })

        if shouldupdate:
            if direction == 0:
                self.downloadsview.update(transfer)
            else:
                self.uploadsview.update(transfer)

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

    def upload_failed(self, msg):

        for i in self.peerconns:
            if i.conn is msg.conn.conn:
                user = i.username
                break
        else:
            return

        for i in self.downloads:
            if i.user == user and i.filename == msg.file and (i.conn is not None or i.status in ["Connection closed by peer", "Establishing connection", "Waiting for download"]):
                self.abort_transfer(i)
                self.get_file(i.user, i.filename, i.path, i)
                self.log_transfer(
                    _("Retrying failed download: user %(user)s, file %(file)s") % {
                        'user': i.user,
                        'file': i.filename
                    },
                    show_ui=1
                )
                break

    def getting_address(self, req, direction):

        if direction == 0:
            for i in self.downloads:
                if i.req == req:
                    i.status = "Getting address"
                    self.downloadsview.update(i)
                    break

        elif direction == 1:

            for i in self.uploads:
                if i.req == req:
                    i.status = "Getting address"
                    self.uploadsview.update(i)
                    break

    def got_address(self, req, direction):
        """ A connection is in progress, we got the address for a user we need
        to connect to."""

        if direction == 0:
            for i in self.downloads:
                if i.req == req:
                    i.status = "Connecting"
                    self.downloadsview.update(i)
                    break

        elif direction == 1:

            for i in self.uploads:
                if i.req == req:
                    i.status = "Connecting"
                    self.uploadsview.update(i)
                    break

    def got_connect_error(self, req, direction):
        """ We couldn't connect to the user, now we are waitng for him to
        connect to us. Note that all this logic is handled by the network
        event processor, we just provide a visual feedback to the user."""

        if direction == 0:
            for i in self.downloads:
                if i.req == req:
                    i.status = "Waiting for peer to connect"
                    self.downloadsview.update(i)
                    break

        elif direction == 1:

            for i in self.uploads:
                if i.req == req:
                    i.status = "Waiting for peer to connect"
                    self.uploadsview.update(i)
                    break

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

        if i.user not in self.eventprocessor.watchedusers:
            self.queue.put(slskmessages.AddUser(i.user))

    def _get_cant_connect_upload(self, i):

        i.status = "Cannot connect"
        i.req = None
        curtime = time.time()

        for j in self.uploads:
            if j.user == i.user:
                j.timequeued = curtime

        self.uploadsview.update(i)

        if i.user not in self.eventprocessor.watchedusers:
            self.queue.put(slskmessages.AddUser(i.user))

        self.check_upload_queue()

    def got_file_connect(self, req, conn):
        """ A transfer connection has been established,
        now exchange initialisation messages."""

        for i in self.downloads:
            if i.req == req:
                i.status = "Initializing transfer"
                self.downloadsview.update(i)
                break

        for i in self.uploads:
            if i.req == req:
                i.status = "Initializing transfer"
                self.uploadsview.update(i)
                break

    def got_connect(self, req, conn, direction):
        """ A connection has been established, now exchange initialisation
        messages."""

        if direction == 0:
            for i in self.downloads:
                if i.req == req:
                    i.status = "Requesting file"
                    i.requestconn = conn
                    self.downloadsview.update(i)
                    break

        elif direction == 1:

            for i in self.uploads:
                if i.req == req:
                    i.status = "Requesting file"
                    i.requestconn = conn
                    self.uploadsview.update(i)
                    break

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
            if i.filename == msg.file and user == i.user and i.status not in ["Aborted", "Paused"]:
                # Remote peer is signalling a tranfer is ready, attempting to download it

                """ If the file is larger than 2GB, the SoulseekQt client seems to
                send a malformed file size (0 bytes) in the TransferRequest response.
                In that case, we rely on the cached, correct file size we received when
                we initially added the download. """

                if msg.filesize > 0:
                    i.size = msg.filesize

                i.req = msg.req
                i.status = "Waiting for download"
                transfertimeout = TransferTimeout(i.req, self.ui_callback)

                if i.transfertimer is not None:
                    i.transfertimer.cancel()

                i.transfertimer = threading.Timer(30.0, transfertimeout.timeout)
                i.transfertimer.setName("TransferTimer")
                i.transfertimer.setDaemon(True)
                i.transfertimer.start()

                response = slskmessages.TransferResponse(None, 1, req=i.req)
                self.downloadsview.update(i)
                break
        else:
            # If this file is not in your download queue, then it must be
            # a remotely initated download and someone is manually uploading to you
            if self.can_upload(user):
                path = ""
                if self.eventprocessor.config.sections["transfers"]["uploadsinsubdirs"]:
                    parentdir = msg.file.replace('/', '\\').split('\\')[-2]
                    path = self.eventprocessor.config.sections["transfers"]["uploaddir"] + os.sep + user + os.sep + parentdir

                transfer = Transfer(
                    user=user, filename=msg.file, path=path,
                    status="Getting status", size=msg.filesize, req=msg.req
                )
                self.downloads.append(transfer)

                if user not in self.eventprocessor.watchedusers:
                    self.queue.put(slskmessages.AddUser(user))

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
        """
        Remote peer is requesting to download a file through
        your Upload queue
        """

        response = self._transfer_request_uploads(msg, user, addr)
        log.add_transfer("Upload request: %(req)s Response: %(resp)s", {
            'req': str(vars(msg)),
            'resp': response
        })
        return response

    def _transfer_request_uploads(self, msg, user, addr):

        # Is user allowed to download?
        checkuser, reason = self.eventprocessor.check_user(user, addr)

        if not checkuser:
            return slskmessages.TransferResponse(None, 0, reason=reason, req=msg.req)

        # Do we actually share that file with the world?
        realpath = self.eventprocessor.shares.virtual2real(msg.file)

        if not self.file_is_shared(user, msg.file, realpath):
            return slskmessages.TransferResponse(None, 0, reason="File not shared", req=msg.req)

        # Is that file already in the queue?
        if self.file_is_upload_queued(user, msg.file):
            return slskmessages.TransferResponse(None, 0, reason="Queued", req=msg.req)

        # Has user hit queue limit?
        limits = True

        if self.eventprocessor.config.sections["transfers"]["friendsnolimits"]:
            friend = user in (i[0] for i in self.eventprocessor.config.sections["server"]["userlist"])

            if friend:
                limits = False

        if limits and self.queue_limit_reached(user):
            uploadslimit = self.eventprocessor.config.sections["transfers"]["queuelimit"]
            return slskmessages.TransferResponse(None, 0, reason="User limit of %i megabytes exceeded" % (uploadslimit), req=msg.req)

        if limits and self.file_limit_reached(user):
            filelimit = self.eventprocessor.config.sections["transfers"]["filelimit"]
            limitmsg = "User limit of %i files exceeded" % (filelimit)
            return slskmessages.TransferResponse(None, 0, reason=limitmsg, req=msg.req)

        # All checks passed, user can queue file!
        if self.pluginhandler:
            self.pluginhandler.upload_queued_notification(user, msg.file, realpath)

        # Is user already downloading/negotiating a download?
        if not self.allow_new_uploads() or user in self.get_transferring_users():

            response = slskmessages.TransferResponse(None, 0, reason="Queued", req=msg.req)
            newupload = Transfer(
                user=user, filename=msg.file, realfilename=realpath,
                path=os.path.dirname(realpath), status="Queued",
                timequeued=time.time(), size=self.get_file_size(realpath),
                place=len(self.uploads)
            )
            self._append_upload(user, msg.file, newupload)
            self.uploadsview.update(newupload)
            self.add_queued(user, realpath)
            return response

        # All checks passed, starting a new upload.
        size = self.get_file_size(realpath)
        response = slskmessages.TransferResponse(None, 1, req=msg.req, filesize=size)

        transfertimeout = TransferTimeout(msg.req, self.ui_callback)
        transferobj = Transfer(
            user=user, realfilename=realpath, filename=msg.file,
            path=os.path.dirname(realpath), status="Waiting for upload",
            req=msg.req, size=size, place=len(self.uploads)
        )

        self._append_upload(user, msg.file, transferobj)
        transferobj.transfertimer = threading.Timer(30.0, transfertimeout.timeout)
        transferobj.transfertimer.setName("TransferTimer")
        transferobj.transfertimer.setDaemon(True)
        transferobj.transfertimer.start()

        self.uploadsview.update(transferobj)
        return response

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

                self.uploads.remove(i)
                self.uploadsview.remove_specific(i, True)
                break

            old_index += 1

        if previously_queued:
            self.uploads.insert(old_index, transferobj)
        else:
            self.uploads.append(transferobj)

    def file_is_upload_queued(self, user, filename):

        for i in self.uploads:
            if i.user == user and i.filename == filename and i.status in self.PRE_TRANSFER + self.TRANSFER:
                return True

        return False

    def queue_limit_reached(self, user):

        uploadslimit = self.eventprocessor.config.sections["transfers"]["queuelimit"] * 1024 * 1024

        if not uploadslimit:
            return False

        size = sum(i.size for i in self.uploads if i.user == user and i.status == "Queued")

        return size >= uploadslimit

    def file_limit_reached(self, user):

        filelimit = self.eventprocessor.config.sections["transfers"]["filelimit"]

        if not filelimit:
            return False

        numfiles = sum(1 for i in self.uploads if i.user == user and i.status == "Queued")

        return numfiles >= filelimit

    def queue_upload(self, msg):
        """ Peer remotely(?) queued a download (upload here) """

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

            if self.eventprocessor.config.sections["transfers"]["friendsnolimits"]:
                friend = user in (i[0] for i in self.eventprocessor.config.sections["server"]["userlist"])

                if friend:
                    limits = False

            checkuser, reason = self.eventprocessor.check_user(user, addr)

            if not checkuser:
                self.queue.put(
                    slskmessages.QueueFailed(conn=msg.conn.conn, file=msg.file, reason=reason)
                )

            elif limits and self.queue_limit_reached(user):
                uploadslimit = self.eventprocessor.config.sections["transfers"]["queuelimit"]
                limitmsg = "User limit of %i megabytes exceeded" % (uploadslimit)
                self.queue.put(
                    slskmessages.QueueFailed(conn=msg.conn.conn, file=msg.file, reason=limitmsg)
                )

            elif limits and self.file_limit_reached(user):
                filelimit = self.eventprocessor.config.sections["transfers"]["filelimit"]
                limitmsg = "User limit of %i files exceeded" % (filelimit)
                self.queue.put(
                    slskmessages.QueueFailed(conn=msg.conn.conn, file=msg.file, reason=limitmsg)
                )

            elif self.file_is_shared(user, filename_utf8, realpath):
                newupload = Transfer(
                    user=user, filename=msg.file, realfilename=realpath,
                    path=os.path.dirname(realpath), status="Queued",
                    timequeued=time.time(), size=self.get_file_size(realpath), place=len(self.uploads)
                )
                self._append_upload(user, msg.file, newupload)
                self.uploadsview.update(newupload)
                self.add_queued(user, msg.file)

                if self.pluginhandler:
                    self.pluginhandler.upload_queued_notification(user, msg.file, realpath)

            else:
                self.queue.put(
                    slskmessages.QueueFailed(conn=msg.conn.conn, file=msg.file, reason="File not shared")
                )

        log.add_transfer("Queued upload request: User %(user)s, %(msg)s", {
            'user': user,
            'msg': str(vars(msg))
        })

        self.check_upload_queue()

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
            self.queue.put(
                slskmessages.MessageUser(username, _("[Automatic Message] ") + _("You are not allowed to send me files."))
            )
            log.add(_("%s is not allowed to send you file(s), but is attempting to, anyway. Warning Sent."), username)

    def can_upload(self, user):

        transfers = self.eventprocessor.config.sections["transfers"]

        if transfers["remotedownloads"]:

            # Remote Uploads only for users in list
            if transfers["uploadallowed"] == 2:
                # Users in userlist
                if user not in (i[0] for i in self.eventprocessor.config.sections["server"]["userlist"]):
                    # Not a buddy
                    return False

            if transfers["uploadallowed"] == 0:
                # No One can sent files to you
                return False

            if transfers["uploadallowed"] == 1:
                # Everyone can sent files to you
                return True

            if transfers["uploadallowed"] == 3:
                # Trusted Users
                userlist = [i[0] for i in self.eventprocessor.config.sections["server"]["userlist"]]

                if user not in userlist:
                    # Not a buddy
                    return False
                if not self.eventprocessor.config.sections["server"]["userlist"][userlist.index(user)][4]:
                    # Not Trusted
                    return False

            return True

        return False

    def queue_failed(self, msg):

        user = None
        for i in self.peerconns:
            if i.conn is msg.conn.conn:
                user = i.username
                break

        if user is None:
            return

        for i in self.downloads:
            if i.user == user and i.filename == msg.file and i.status not in ["Aborted", "Paused"]:
                if i.status in self.TRANSFER:
                    self.abort_transfer(i, reason=msg.reason)

                i.status = msg.reason
                self.downloadsview.update(i)

                break

    def file_is_shared(self, user, virtualfilename, realfilename):

        log.add_transfer("Checking if file %(virtual_name)s with real path %(path)s is shared", {
            "virtual_name": virtualfilename,
            "path": realfilename
        })

        if not os.access(realfilename, os.R_OK):
            log.add_transfer("Can't access file %(virtual_name)s with real path %(path)s, not sharing", {
                "virtual_name": virtualfilename,
                "path": realfilename
            })
            return False

        folder, sep, file = virtualfilename.rpartition('\\')

        if self.eventprocessor.config.sections["transfers"]["enablebuddyshares"]:
            if user in (i[0] for i in self.eventprocessor.config.sections["server"]["userlist"]):
                bshared = self.eventprocessor.shares.share_dbs["buddyfiles"]

                for i in bshared.get(str(folder), ''):
                    if file == i[0]:
                        return True

        shared = self.eventprocessor.shares.share_dbs["files"]

        for i in shared.get(str(folder), ''):
            if file == i[0]:
                return True

        log.add_transfer("Failed to share file %(virtual_name)s with real path %(path)s, since it wasn't found", {
            "virtual_name": virtualfilename,
            "path": realfilename
        })
        return False

    def get_transferring_users(self):
        return [i.user for i in self.uploads if i.req is not None or i.conn is not None or i.status == "Getting status"]  # some file is being transfered

    def transfer_negotiating(self):

        # some file is being negotiated
        now = time.time()
        count = 0

        for i in self.uploads:
            if (now - i.laststatuschange) < 30:  # if a status hasn't changed in the last 30 seconds the connection is probably never going to work, ignoring it.

                if i.req is not None:
                    count += 1
                if i.conn is not None and i.speed is None:
                    count += 1
                if i.status == "Getting status":
                    count += 1

        return count

    def allow_new_uploads(self):

        limit_upload_slots = self.eventprocessor.config.sections["transfers"]["useupslots"]
        limit_upload_speed = self.eventprocessor.config.sections["transfers"]["uselimit"]

        currently_negotiating = self.transfer_negotiating()

        if limit_upload_slots:
            maxupslots = self.eventprocessor.config.sections["transfers"]["uploadslots"]
            in_progress_count = sum(1 for i in self.uploads if i.conn is not None and i.speed is not None)

            if in_progress_count + currently_negotiating >= maxupslots:
                return False

        bandwidth_sum = sum(i.speed for i in self.uploads if i.conn is not None and i.speed is not None)

        if limit_upload_speed:
            max_upload_speed = self.eventprocessor.config.sections["transfers"]["uploadlimit"] * 1024

            if bandwidth_sum >= max_upload_speed:
                return False

            if currently_negotiating:
                return False

        maxbandwidth = self.eventprocessor.config.sections["transfers"]["uploadbandwidth"] * 1024
        if maxbandwidth:
            if bandwidth_sum >= maxbandwidth:
                return False

        return True

    def get_file_size(self, filename):

        try:
            size = os.path.getsize(filename)
        except Exception:
            # file doesn't exist (remote files are always this)
            size = 0

        return size

    def transfer_response(self, msg):

        """ Got a response to the file request from the peer."""

        log.add_transfer("Received response for transfer request %(request)s. Allowed: %(allowed)s. Reason: %(reason)s. Filesize: %(size)s", {
            "request": msg.req,
            "allowed": msg.allowed,
            "reason": msg.reason,
            "size": msg.filesize
        })

        if msg.reason is not None:

            for i in self.downloads:

                if i.req != msg.req:
                    continue

                if msg.reason in ("File not shared.", "File not shared", "Remote file error") and \
                        not i.legacy_attempt:
                    """ The peer is possibly using an old client that doesn't support Unicode
                    (Soulseek NS). Attempt to request file name encoded as latin-1 once. """

                    i.req = new_id()
                    realpath = self.eventprocessor.shares.virtual2real(i.filename)
                    request = slskmessages.TransferRequest(None, 0, i.req, i.filename, self.get_file_size(realpath), realpath, legacy_client=True)
                    self.eventprocessor.send_message_to_peer(i.user, request)
                    i.legacy_attempt = True

                    log.add_transfer("Peer responded with reason '%(reason)s' for download request %(request)s for file %(filename)s. "
                                     "Attempting to request file as latin-1.", {
                                         "reason": msg.reason,
                                         "request": msg.req,
                                         "filename": i.filename
                                     })
                    break

                i.status = msg.reason
                i.req = None
                self.downloadsview.update(i)

                if msg.reason == "Queued":

                    if i.user not in self.users or self.users[i.user].status is None:
                        if i.user not in self.eventprocessor.watchedusers:
                            self.queue.put(slskmessages.AddUser(i.user))

                    self.queue.put(
                        slskmessages.PlaceInQueueRequest(msg.conn.conn, i.filename, i.legacy_attempt)
                    )

                self.check_upload_queue()
                break

            for i in self.uploads:

                if i.req != msg.req:
                    continue

                i.status = msg.reason
                i.req = None
                self.uploadsview.update(i)

                if msg.reason == "Queued":

                    if i.user not in self.users or self.users[i.user].status is None:
                        if i.user not in self.eventprocessor.watchedusers:
                            self.queue.put(slskmessages.AddUser(i.user))

                    if i.transfertimer is not None:
                        i.transfertimer.cancel()

                    self.uploads.remove(i)
                    self.uploadsview.remove_specific(i, True)

                elif msg.reason == "Complete":

                    """ Edge case. There are rare cases where a "Complete" status is sent to us by
                    SoulseekQt, even though it shouldn't be (?) """

                    self.upload_finished(i)

                elif msg.reason == "Cancelled":

                    self.auto_clear_upload(i)

                self.check_upload_queue()
                break

        elif msg.filesize is not None:
            for i in self.downloads:

                if i.req != msg.req:
                    continue

                i.size = msg.filesize
                i.status = "Establishing connection"
                # Have to establish 'F' connection here
                self.eventprocessor.send_message_to_peer(i.user, slskmessages.FileRequest(None, msg.req))
                self.downloadsview.update(i)
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

        for i in (self.downloads + self.uploads):

            if i.req != msg.req:
                continue

            if i.status in ["Queued", "User logged off", "Paused"] + self.COMPLETED_TRANSFERS:
                continue

            log.add_transfer("Transfer %(filename)s with request %(request)s for user %(user)s timed out", {
                "filename": i.filename,
                "request": i.req,
                "user": i.user
            })

            i.status = "Cannot connect"
            i.req = None
            curtime = time.time()

            for j in self.uploads:
                if j.user == i.user:
                    j.timequeued = curtime

            if i.user not in self.eventprocessor.watchedusers:
                self.queue.put(slskmessages.AddUser(i.user))

            if i in self.downloads:
                self.downloadsview.update(i)
            elif i in self.uploads:
                self.uploadsview.update(i)

            break

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

        self.queue.put(slskmessages.ConnClose(msg.conn))

    def _file_request_download(self, msg, i):

        log.add_transfer("Received file upload request %(request)s for file %(filename)s from user %(user)s", {
            "request": msg.req,
            "filename": i.filename,
            "user": i.user
        })

        downloaddir = self.eventprocessor.config.sections["transfers"]["downloaddir"]
        incompletedir = self.eventprocessor.config.sections["transfers"]["incompletedir"]
        needupdate = True

        if i.conn is None and i.size is not None:
            i.conn = msg.conn
            i.req = None

            if i.transfertimer is not None:
                i.transfertimer.cancel()

            if not incompletedir:
                if i.path and i.path[0] == '/':
                    incompletedir = clean_path(i.path)
                else:
                    incompletedir = os.path.join(downloaddir, clean_path(i.path))

            try:
                if not os.access(incompletedir, os.F_OK):
                    os.makedirs(incompletedir)
                if not os.access(incompletedir, os.R_OK | os.W_OK | os.X_OK):
                    raise OSError("Download directory %s Permissions error.\nDir Permissions: %s" % (incompletedir, oct(os.stat(incompletedir)[stat.ST_MODE] & 0o777)))

            except OSError as strerror:
                log.add(_("OS error: %s"), strerror)
                i.status = "Download directory error"
                i.conn = None
                self.queue.put(slskmessages.ConnClose(msg.conn))

                if self.notifications:
                    self.notifications.new_notification(_("OS error: %s") % strerror, title=_("Folder download error"))

            else:
                # also check for a windows-style incomplete transfer
                basename = clean_file(i.filename.replace('/', '\\').split('\\')[-1])
                winfname = os.path.join(incompletedir, "INCOMPLETE~" + basename)
                pyfname = os.path.join(incompletedir, "INCOMPLETE" + basename)

                m = md5()
                m.update((i.filename + i.user).encode('utf-8'))

                f = None
                pynewfname = os.path.join(incompletedir, "INCOMPLETE" + m.hexdigest() + basename)
                try:
                    if os.access(winfname, os.F_OK):
                        fname = winfname
                    elif os.access(pyfname, os.F_OK):
                        fname = pyfname
                    else:
                        fname = pynewfname

                    f = open(fname, 'ab+')

                    if self.eventprocessor.config.sections["transfers"]["lock"]:
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

                    i.status = "Local file error"
                    self.close_file(f, i)

                    i.conn = None
                    self.queue.put(slskmessages.ConnClose(msg.conn))

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
                        self.queue.put(slskmessages.DownloadFile(i.conn, size, f, i.size))
                        log.add_transfer("Download started: %s", f.name)

                        self.log_transfer(_("Download started: user %(user)s, file %(file)s") % {'user': i.user, 'file': "%s" % f.name}, show_ui=1)
                    else:
                        self.download_finished(f, i)
                        needupdate = False

            self.downloadsview.new_transfer_notification()

            if needupdate:
                self.downloadsview.update(i)

        else:
            log.add_warning("Download error formally known as 'Unknown file request': %(req)s (%(user)s: %(file)s)", {
                'req': str(vars(msg)),
                'user': i.user,
                'file': i.filename
            })

            self.queue.put(slskmessages.ConnClose(msg.conn))

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

            if i.transfertimer is not None:
                i.transfertimer.cancel()

            try:
                # Open File
                f = open(i.realfilename, "rb")

            except IOError as strerror:
                log.add(_("Upload I/O error: %s"), strerror)

                i.status = "Local file error"
                self.close_file(f, i)

                i.conn = None
                self.queue.put(slskmessages.ConnClose(msg.conn))

            else:
                self.queue.put(slskmessages.UploadFile(i.conn, file=f, size=i.size))
                i.status = "Initializing transfer"
                i.file = f

                self.eventprocessor.statistics.append_stat_value("started_uploads", 1)

                ip_address = None
                if i.conn is not None:
                    try:
                        ip_address = i.conn.getpeername()
                    except OSError:
                        # Connection already closed
                        pass

                self.log_transfer(_("Upload started: user %(user)s, IP address %(ip)s, file %(file)s") % {
                    'user': i.user,
                    'ip': ip_address,
                    'file': i.filename
                })

            self.uploadsview.new_transfer_notification()
            self.uploadsview.update(i)

            if i.size == 0:
                # If filesize is 0, we will not receive a UploadFile message later. Finish now.
                self.upload_finished(i, file=f)

        else:
            log.add_warning("Upload error formally known as 'Unknown file request': %(req)s (%(user)s: %(file)s)", {
                'req': str(vars(msg)),
                'user': i.user,
                'file': i.filename
            })

            self.queue.put(slskmessages.ConnClose(msg.conn))

    def file_download(self, msg):
        """ A file download is in progress"""

        needupdate = True

        for i in self.downloads:

            if i.conn != msg.conn:
                continue

            try:

                if i.transfertimer is not None:
                    i.transfertimer.cancel()
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

                i.status = "Local file error"
                self.close_file(msg.file, i)

                i.conn = None
                self.queue.put(slskmessages.ConnClose(msg.conn))

            if needupdate:
                self.downloadsview.update(i)

            break

    def download_finished(self, file, i):

        self.close_file(file, i)

        basename = clean_file(i.filename.replace('/', '\\').split('\\')[-1])
        config = self.eventprocessor.config.sections
        downloaddir = config["transfers"]["downloaddir"]

        if i.path and i.path[0] == '/':
            folder = clean_path(i.path)
        else:
            folder = os.path.join(downloaddir, i.path)

        if not os.access(folder, os.F_OK):
            os.makedirs(folder)

        newname = self.get_renamed(os.path.join(folder, basename))

        try:
            import shutil
            shutil.move(file.name, newname)
        except (IOError, OSError) as inst:
            log.add_warning(
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

        log.add_transfer(
            "Download finished: %(file)s", {
                'file': newname
            }
        )

        self.log_transfer(
            _("Download finished: user %(user)s, file %(file)s") % {
                'user': i.user,
                'file': i.filename
            },
            show_ui=1
        )

        i.conn = None

        self.add_to_shared(newname)
        self.eventprocessor.shares.send_num_shared_folders_files()

        self.eventprocessor.statistics.append_stat_value("completed_downloads", 1)

        if self.notifications and config["notifications"]["notification_popup_file"]:
            self.notifications.new_notification(
                _("%(file)s downloaded from %(user)s") % {
                    'user': i.user,
                    'file': newname.rsplit(os.sep, 1)[1]
                },
                title=_("File downloaded")
            )

        self.save_downloads()

        # Attempt to autoclear this download, if configured
        if not self.auto_clear_download(i):
            self.downloadsview.update(i)

        if config["transfers"]["afterfinish"]:
            if not execute_command(config["transfers"]["afterfinish"], newname):
                log.add(_("Trouble executing '%s'"), config["transfers"]["afterfinish"])
            else:
                log.add(_("Executed: %s"), config["transfers"]["afterfinish"])

        if i.path and (config["notifications"]["notification_popup_folder"] or config["transfers"]["afterfolder"]):

            # walk through downloads and break if any file in the same folder exists, else execute
            for ia in self.downloads:
                if ia.status not in ["Finished", "Aborted", "Paused", "Filtered"] and ia.path and ia.path == i.path:
                    break
            else:
                if self.notifications and config["notifications"]["notification_popup_folder"]:
                    self.notifications.new_notification(
                        _("%(folder)s downloaded from %(user)s") % {
                            'user': i.user,
                            'folder': folder
                        },
                        title=_("Folder downloaded")
                    )
                if config["transfers"]["afterfolder"]:
                    if not execute_command(config["transfers"]["afterfolder"], folder):
                        log.add(_("Trouble executing on folder: %s"), config["transfers"]["afterfolder"])
                    else:
                        log.add(_("Executed on folder: %s"), config["transfers"]["afterfolder"])

    def add_to_shared(self, name):
        """ Add a file to the normal shares database """

        self.eventprocessor.shares.add_file_to_shared(name)

    def file_upload(self, msg):
        """ A file upload is in progress """

        needupdate = True

        for i in self.uploads:

            if i.conn != msg.conn:
                continue

            if i.transfertimer is not None:
                i.transfertimer.cancel()

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

                self.check_upload_queue()

            i.lastbytes = i.currentbytes
            i.lasttime = curtime

            if i.size > i.currentbytes:
                if oldelapsed == i.timeelapsed:
                    needupdate = False
                i.status = "Transferring"

                if i.user in self.privilegedusers:
                    i.modifier = _("(privileged)")
                elif self.user_list_privileged(i.user):
                    i.modifier = _("(friend)")
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

    def upload_finished(self, i, file=None):

        if i.speed is not None:
            speedbytes = int(i.speed)
            self.eventprocessor.speed = speedbytes
            self.queue.put(slskmessages.SendUploadSpeed(speedbytes))

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

        self.log_transfer(
            _("Upload finished: user %(user)s, IP address %(ip)s, file %(file)s") % {
                'user': i.user,
                'ip': ip_address,
                'file': i.filename
            }
        )

        self.eventprocessor.statistics.append_stat_value("completed_uploads", 1)

        self.check_upload_queue()
        self.uploadsview.update(i)

        # Autoclear this upload
        self.auto_clear_upload(i)

    def auto_clear_download(self, transfer):
        if self.eventprocessor.config.sections["transfers"]["autoclear_downloads"]:
            self.downloads.remove(transfer)
            self.downloadsview.remove_specific(transfer, True)
            return True

        return False

    def auto_clear_upload(self, transfer):
        if self.eventprocessor.config.sections["transfers"]["autoclear_uploads"]:
            self.uploads.remove(transfer)
            self.uploadsview.remove_specific(transfer, True)
            self.calc_upload_queue_sizes()
            self.check_upload_queue()

    def ban_user(self, user, ban_message=None):
        """
        Ban a user, cancel all the user's uploads, send a 'Banned'
        message via the transfers, and clear the transfers from the
        uploads list.
        """

        if ban_message:
            banmsg = _("Banned (%s)") % ban_message
        elif self.eventprocessor.config.sections["transfers"]["usecustomban"]:
            banmsg = _("Banned (%s)") % self.eventprocessor.config.sections["transfers"]["customban"]
        else:
            banmsg = _("Banned")

        for upload in self.uploads:
            if upload.user != user:
                continue

            if upload.status == "Queued":
                self.eventprocessor.send_message_to_peer(user, slskmessages.QueueFailed(None, file=upload.filename, reason=banmsg))
            else:
                self.abort_transfer(upload, reason=banmsg)

        if self.uploadsview is not None:
            self.uploadsview.clear_by_user(user)

        if user not in self.eventprocessor.config.sections["server"]["banlist"]:
            self.eventprocessor.config.sections["server"]["banlist"].append(user)
            self.eventprocessor.config.write_configuration()

    def start_check_download_queue_timer(self):

        self.download_queue_timer = threading.Timer(60.0, self.ui_callback, [[slskmessages.CheckDownloadQueue()]])
        self.download_queue_timer.setName("DownloadQueueTimer")
        self.download_queue_timer.setDaemon(True)
        self.download_queue_timer.start()

    # Find failed or stuck downloads and attempt to queue them.
    # Also ask for the queue position of downloads.
    def check_download_queue(self):

        statuslist = self.FAILED_TRANSFERS + \
            ["Getting status", "Getting address", "Connecting", "Waiting for peer to connect", "Requesting file", "Initializing transfer"]

        for transfer in self.downloads:
            if transfer.status in statuslist:
                self.abort_transfer(transfer)
                self.get_file(transfer.user, transfer.filename, transfer.path, transfer)

            elif transfer.status == "Queued":
                self.eventprocessor.send_message_to_peer(
                    transfer.user,
                    slskmessages.PlaceInQueueRequest(None, transfer.filename, transfer.legacy_attempt)
                )

        self.start_check_download_queue_timer()

    # Find next file to upload
    def check_upload_queue(self):

        if not self.allow_new_uploads():
            return

        transfercandidate = None
        trusers = self.get_transferring_users()

        # List of transfer instances of users who are not currently transferring
        list_queued = [i for i in self.uploads if i.user not in trusers and i.status == "Queued"]

        # Sublist of privileged users transfers
        list_privileged = [i for i in list_queued if self.is_privileged(i.user)]

        if len(list_privileged) > 0:
            # Upload to a privileged user
            # Only Privileged users' files will get selected
            list_queued = list_privileged

        if len(list_queued) == 0:
            return

        if self.eventprocessor.config.sections["transfers"]["fifoqueue"]:
            # FIFO
            # Get the first item in the list
            transfercandidate = list_queued[0]
        else:
            # Round Robin
            # Get first transfer that was queued less than one second from now
            mintimequeued = time.time() + 1
            for i in list_queued:
                if i.timequeued is not None and i.timequeued < mintimequeued:
                    transfercandidate = i
                    # Break loop
                    mintimequeued = i.timequeued

        if transfercandidate is not None:
            user = transfercandidate.user

            log.add_transfer(
                "Checked upload queue, attempting to upload file %(file)s to user %(user)s", {
                    'file': transfercandidate.filename,
                    'user': user
                }
            )

            if self.user_logged_out(user):
                transfercandidate.status = "User logged off"
                self.abort_transfer(transfercandidate, send_fail_message=False)
                self.uploadsview.update(transfercandidate)
                self.auto_clear_upload(transfercandidate)

                self.check_upload_queue()

            else:
                self.push_file(
                    user=transfercandidate.user, filename=transfercandidate.filename,
                    realfilename=transfercandidate.realfilename, transfer=transfercandidate
                )

            self.remove_queued(transfercandidate.user, transfercandidate.filename)

    def place_in_queue_request(self, msg):

        user = None
        for i in self.peerconns:
            if i.conn is msg.conn.conn:
                user = i.username
                break

        if user is None:
            return

        def list_users():
            users = set()
            for i in self.uploads:
                if i.user not in users:
                    users.add(i.user)
            return users

        if self.eventprocessor.config.sections["transfers"]["fifoqueue"]:

            # Number of transfers queued by non-privileged users
            count = 0

            # Number of transfers queued by privileged users
            countpriv = 0

            # Place in the queue for msg.file
            place = 0

            for i in self.uploads:
                # Ignore non-queued files
                if i.status == "Queued":
                    if self.is_privileged(i.user):
                        countpriv += 1
                    else:
                        count += 1

                    # Stop counting on the matching file
                    if i.user == user and i.filename == msg.file:
                        if self.is_privileged(user):
                            # User is privileged so we only
                            # count priv'd transfers
                            place = countpriv
                        else:
                            # Count all transfers
                            place = count + countpriv
                        break
        else:
            # Todo
            listpriv = {user: time.time()}
            countpriv = 0
            trusers = self.get_transferring_users()
            count = 0
            place = 0
            transfers = 0

            for i in self.uploads:
                # Ignore non-queued files
                if i.status == "Queued":
                    if i.user == user:
                        if self.is_privileged(user):
                            # User is privileged so we only
                            # count priv'd transfers
                            listpriv[i.user] = i.timequeued
                            place += 1
                        else:
                            # Count all transfers
                            place += 1
                        # Stop counting on the matching file
                        if i.filename == msg.file:
                            break

            upload_users = list_users()
            user_transfers = {}

            for username in upload_users:
                user_transfers[username] = sum(1 for i in self.uploads if i.status == "Queued" and i.user == username)
                if username is not user:
                    if user_transfers[username] >= place:
                        if username not in trusers:
                            transfers += place

            place += transfers

        self.queue.put(slskmessages.PlaceInQueue(msg.conn.conn, msg.file, place))

    def get_time(self, seconds):

        sec = int(seconds % 60)
        minutes = int(seconds / 60 % 60)
        hours = int(seconds / 3600 % 24)
        days = int(seconds / 86400)

        time_string = "%02d:%02d:%02d" % (hours, minutes, sec)
        if days > 0:
            time_string = str(days) + "." + time_string

        return time_string

    def calc_upload_queue_sizes(self):
        # queue sizes
        self.privcount = 0
        self.usersqueued = {}
        self.privusersqueued = {}

        for i in self.uploads:
            if i.status == "Queued":
                self.add_queued(i.user, i.filename)

    def get_upload_queue_sizes(self, username=None):

        if self.eventprocessor.config.sections["transfers"]["fifoqueue"]:
            count = 0
            for i in self.uploads:
                if i.status == "Queued":
                    count += 1
            return count, count
        else:
            if username is not None and self.is_privileged(username):
                return len(self.privusersqueued), len(self.privusersqueued)
            else:
                return len(self.usersqueued) + self.privcount, self.privcount

    def add_queued(self, user, filename):

        if user in self.privilegedusers:
            self.privusersqueued.setdefault(user, 0)
            self.privusersqueued[user] += 1
            self.privcount += 1
        else:
            self.usersqueued.setdefault(user, 0)
            self.usersqueued[user] += 1

    def remove_queued(self, user, filename):

        if user in self.privilegedusers:
            self.privusersqueued[user] -= 1
            self.privcount -= 1
            if self.privusersqueued[user] == 0:
                del self.privusersqueued[user]
        else:
            self.usersqueued[user] -= 1
            if self.usersqueued[user] == 0:
                del self.usersqueued[user]

    def get_total_uploads_allowed(self):

        if self.eventprocessor.config.sections["transfers"]["useupslots"]:
            maxupslots = self.eventprocessor.config.sections["transfers"]["uploadslots"]
            return maxupslots
        else:
            lstlen = sum(1 for i in self.uploads if i.conn is not None)

            if self.allow_new_uploads():
                return lstlen + 1
            else:
                return lstlen

    def user_list_privileged(self, user):

        for i in self.eventprocessor.config.sections["server"]["userlist"]:
            if user == i[0]:
                # All users
                if self.eventprocessor.config.sections["transfers"]["preferfriends"]:
                    return True

                # Only privileged users
                return i[3]  # Privileged column

        return False

    def is_privileged(self, user):

        if user in self.privilegedusers or self.user_list_privileged(user):
            return True
        else:
            return False

    def conn_close(self, conn, addr, user, error):
        """ The remote user has closed the connection either because
        he logged off, or because there's a network problem. """

        for i in self.downloads:
            if i.conn == conn:
                self._conn_close(conn, addr, i, "download")

        for i in self.uploads:
            if not isinstance(error, ConnectionRefusedError) and i.conn != conn:
                continue

            if i.user != user:
                continue

            self._conn_close(conn, addr, i, "upload")

    def _conn_close(self, conn, addr, i, type):

        if i.requestconn == conn and i.status == "Requesting file":
            # This code is probably not needed anymore?
            i.requestconn = None
            i.status = "Connection closed by peer"
            i.req = None

        self.abort_transfer(i, send_fail_message=False)  # Don't send "Aborted" message, let remote user recover

        if i.status != "Finished":
            if type == "download":
                if self.user_logged_out(i.user):
                    i.status = "User logged off"
                else:
                    i.status = "Connection closed by peer"

            elif type == "upload" and i.status != "Queued":
                """ Only cancel files being transferred, queued files will take care of
                themselves. We don't want to cancel all queued files at once, in case
                it's just a connectivity fluke. """

                if self.user_logged_out(i.user):
                    i.status = "User logged off"
                else:
                    i.status = "Cancelled"

                self.auto_clear_upload(i)

        curtime = time.time()
        for j in self.uploads:
            if j.user == i.user:
                j.timequeued = curtime

        if type == "download":
            self.downloadsview.update(i)
        elif type == "upload":
            self.uploadsview.update(i)

        self.check_upload_queue()

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
            if i.user == username and i.filename == filename:
                i.place = msg.place
                self.downloadsview.update(i)
                return

    def file_error(self, msg):
        """ Networking thread encountered a local file error"""

        for i in self.downloads + self.uploads:

            if i.conn != msg.conn.conn:
                continue

            i.status = "Local file error"
            self.close_file(msg.file, i)

            i.conn = None
            log.add(_("I/O error: %s"), msg.strerror)

            if i in self.downloads:
                self.downloadsview.update(i)
            elif i in self.uploads:
                self.uploadsview.update(i)

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

        for i in file_list:
            for directory in file_list[i]:

                if os.path.commonprefix([i, directory]) == directory:
                    files = file_list[i][directory][:]

                    if self.eventprocessor.config.sections["transfers"]["reverseorder"]:
                        files.sort(key=lambda x: x[1], reverse=True)

                    for file in files:
                        size = file[2]
                        h_bitrate, bitrate, h_length, length = get_result_bitrate_length(size, file[4])

                        if directory[-1] == '\\':
                            self.get_file(
                                username,
                                directory + file[1],
                                self.folder_destination(username, directory),
                                size=size,
                                bitrate=h_bitrate,
                                length=h_length,
                                checkduplicate=True
                            )
                        else:
                            self.get_file(
                                username,
                                directory + '\\' + file[1],
                                self.folder_destination(username, directory),
                                size=size,
                                bitrate=h_bitrate,
                                length=h_length,
                                checkduplicate=True
                            )

    def folder_destination(self, user, directory):

        destination = ""

        if user in self.eventprocessor.requested_folders:
            if directory in self.eventprocessor.requested_folders[user]:
                destination += self.eventprocessor.requested_folders[user][directory]

        if directory[-1] == '\\':
            parent = directory.split('\\')[-2]
        else:
            parent = directory.split('\\')[-1]

        destination = os.path.join(destination, parent)

        if destination[0] != '/':
            destination = os.path.join(
                self.eventprocessor.config.sections["transfers"]["downloaddir"],
                destination
            )

        """ Make sure the target folder doesn't exist
        If it exists, append a number to the folder name """

        orig_destination = destination
        counter = 1

        while os.path.exists(destination):
            destination = orig_destination + " (" + str(counter) + ")"
            counter += 1

        return destination

    def retry_download(self, transfer):

        if transfer.status in ("Finished", "Old"):
            return

        user = transfer.user

        if self.user_logged_out(user):
            transfer.status = "User logged off"
            self.abort_transfer(transfer, send_fail_message=False)
            self.downloadsview.update(transfer)
            return

        self.abort_transfer(transfer)
        self.get_file(user, transfer.filename, transfer.path, transfer)

    def retry_upload(self, transfer):

        user = transfer.user

        if user in self.get_transferring_users():
            return

        if self.user_logged_out(user):
            transfer.status = "User logged off"
            self.abort_transfer(transfer, send_fail_message=False)
            self.uploadsview.update(transfer)
            self.auto_clear_upload(transfer)
            return

        self.eventprocessor.send_message_to_peer(user, slskmessages.UploadQueueNotification(None))
        self.push_file(user, transfer.filename, transfer.path, transfer=transfer)

    def abort_transfers(self, send_fail_message=True):
        """ Stop all transfers """

        for i in self.downloads + self.uploads:
            if i.status in ("Aborted", "Paused"):
                self.abort_transfer(i, send_fail_message=send_fail_message)
                i.status = "Paused"
            elif i.status != "Finished":
                self.abort_transfer(i, send_fail_message=send_fail_message)
                i.status = "Old"

    def abort_transfer(self, transfer, reason="Aborted", send_fail_message=True):

        transfer.legacy_attempt = False
        transfer.req = None
        transfer.speed = None
        transfer.timeleft = ""

        if send_fail_message and transfer in self.uploads:
            self.eventprocessor.send_message_to_peer(transfer.user, slskmessages.QueueFailed(None, file=transfer.filename, reason=reason))

        if transfer.conn is not None:
            self.queue.put(slskmessages.ConnClose(transfer.conn))
            transfer.conn = None

        if transfer.transfertimer is not None:
            transfer.transfertimer.cancel()

        if transfer.file is not None:
            self.close_file(transfer.file, transfer)

            if transfer in self.uploads:
                self.log_transfer(
                    _("Upload aborted, user %(user)s file %(file)s") % {
                        'user': transfer.user,
                        'file': transfer.filename
                    }
                )
            else:
                self.log_transfer(
                    _("Download aborted, user %(user)s file %(file)s") % {
                        'user': transfer.user,
                        'file': transfer.filename
                    },
                    show_ui=1
                )

    def log_transfer(self, message, show_ui=0):

        if self.eventprocessor.config.sections["logging"]["transfers"]:
            timestamp_format = self.eventprocessor.config.sections["logging"]["log_timestamp"]
            write_log(self.eventprocessor.config.sections["logging"]["transferslogsdir"], "transfers", message, timestamp_format)

        if show_ui:
            log.add(message)

    def get_downloads(self):
        """ Get a list of incomplete and not aborted downloads """
        return [[i.user, i.filename, i.path, i.status, i.size, i.currentbytes, i.bitrate, i.length] for i in self.downloads if i.status != "Finished"]

    def save_downloads(self):
        """ Save list of files to be downloaded """

        self.eventprocessor.config.create_data_folder()
        downloads_file = os.path.join(self.eventprocessor.config.data_dir, 'downloads.json')

        try:
            with open(downloads_file, "w", encoding="utf-8") as handle:
                import json
                json.dump(self.get_downloads(), handle, ensure_ascii=False)

        except Exception as inst:
            log.add(_("Something went wrong while writing your transfer list: %(error)s"), {'error': str(inst)})

    def disconnect(self):

        if self.download_queue_timer is not None:
            self.download_queue_timer.cancel()

        self.abort_transfers(send_fail_message=False)
        self.save_downloads()


class Statistics:

    def __init__(self, config, ui_callback=None):

        self.config = config
        self.ui_callback = ui_callback

        self.init_stats()

    def init_stats(self):
        for stat_id in self.config.defaults["statistics"]:
            self.__dict__[stat_id] = 0

    def append_stat_value(self, stat_id, stat_value):

        self.__dict__[stat_id] += stat_value
        self.config.sections["statistics"][stat_id] += stat_value
        self.update_ui(stat_id)

    def update_ui(self, stat_id):

        if self.ui_callback:
            stat_value = self.__dict__[stat_id]
            self.ui_callback.update_stat_value(stat_id, stat_value)

    def reset_stats(self):

        for stat_id in self.config.defaults["statistics"]:
            self.__dict__[stat_id] = 0
            self.config.sections["statistics"][stat_id] = 0

            self.update_ui(stat_id)
