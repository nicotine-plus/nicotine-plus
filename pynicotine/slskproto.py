# Copyright (C) 2007 daelstorm. All rights reserved.
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
#
# Previous copyright below
# Copyright (c) 2003-2004 Hyriand. All rights reserved.
#
# Based on code from PySoulSeek, original copyright note:
# Copyright (c) 2001-2003 Alexander Kanavin. All rights reserved.

"""
This module implements SoulSeek networking protocol.
"""

import select
import socket
import struct
import sys
import threading
import time
from errno import EINTR
from gettext import gettext as _
from math import floor

from pynicotine.logfacility import log
from pynicotine.slskmessages import AcceptChildren
from pynicotine.slskmessages import AckNotifyPrivileges
from pynicotine.slskmessages import AddThingIHate
from pynicotine.slskmessages import AddThingILike
from pynicotine.slskmessages import AddToPrivileged
from pynicotine.slskmessages import AddUser
from pynicotine.slskmessages import AdminMessage
from pynicotine.slskmessages import BranchLevel
from pynicotine.slskmessages import BranchRoot
from pynicotine.slskmessages import CantConnectToPeer
from pynicotine.slskmessages import ChangePassword
from pynicotine.slskmessages import CheckPrivileges
from pynicotine.slskmessages import ChildDepth
from pynicotine.slskmessages import ConnClose
from pynicotine.slskmessages import ConnectError
from pynicotine.slskmessages import ConnectToPeer
from pynicotine.slskmessages import DistribAlive
from pynicotine.slskmessages import DistribAliveInterval
from pynicotine.slskmessages import DistribBranchLevel
from pynicotine.slskmessages import DistribBranchRoot
from pynicotine.slskmessages import DistribChildDepth
from pynicotine.slskmessages import DistribMessage9
from pynicotine.slskmessages import DistribSearch
from pynicotine.slskmessages import DownloadFile
from pynicotine.slskmessages import ExactFileSearch
from pynicotine.slskmessages import FileError
from pynicotine.slskmessages import FileRequest
from pynicotine.slskmessages import FileSearch
from pynicotine.slskmessages import FileSearchRequest
from pynicotine.slskmessages import FileSearchResult
from pynicotine.slskmessages import FolderContentsRequest
from pynicotine.slskmessages import FolderContentsResponse
from pynicotine.slskmessages import GetPeerAddress
from pynicotine.slskmessages import GetSharedFileList
from pynicotine.slskmessages import GetUserStats
from pynicotine.slskmessages import GetUserStatus
from pynicotine.slskmessages import GivePrivileges
from pynicotine.slskmessages import GlobalRecommendations
from pynicotine.slskmessages import GlobalUserList
from pynicotine.slskmessages import HaveNoParent
from pynicotine.slskmessages import IncConn
from pynicotine.slskmessages import IncPort
from pynicotine.slskmessages import InternalData
from pynicotine.slskmessages import InternalMessage
from pynicotine.slskmessages import ItemRecommendations
from pynicotine.slskmessages import ItemSimilarUsers
from pynicotine.slskmessages import JoinPublicRoom
from pynicotine.slskmessages import JoinRoom
from pynicotine.slskmessages import LeavePublicRoom
from pynicotine.slskmessages import LeaveRoom
from pynicotine.slskmessages import Login
from pynicotine.slskmessages import MessageAcked
from pynicotine.slskmessages import MessageUser
from pynicotine.slskmessages import MinParentsInCache
from pynicotine.slskmessages import Msg85
from pynicotine.slskmessages import Msg89
from pynicotine.slskmessages import Msg12547
from pynicotine.slskmessages import NetInfo
from pynicotine.slskmessages import NotifyPrivileges
from pynicotine.slskmessages import OutConn
from pynicotine.slskmessages import ParentInactivityTimeout
from pynicotine.slskmessages import ParentMinSpeed
from pynicotine.slskmessages import ParentSpeedRatio
from pynicotine.slskmessages import PeerInit
from pynicotine.slskmessages import PeerMessage
from pynicotine.slskmessages import PeerTransfer
from pynicotine.slskmessages import PierceFireWall
from pynicotine.slskmessages import PlaceholdUpload
from pynicotine.slskmessages import PlaceInLineResponse
from pynicotine.slskmessages import PlaceInQueue
from pynicotine.slskmessages import PlaceInQueueRequest
from pynicotine.slskmessages import PMessageUser
from pynicotine.slskmessages import PopupMessage
from pynicotine.slskmessages import PrivateRoomAdded
from pynicotine.slskmessages import PrivateRoomAddOperator
from pynicotine.slskmessages import PrivateRoomAddUser
from pynicotine.slskmessages import PrivateRoomDismember
from pynicotine.slskmessages import PrivateRoomDisown
from pynicotine.slskmessages import PrivateRoomOperatorAdded
from pynicotine.slskmessages import PrivateRoomOperatorRemoved
from pynicotine.slskmessages import PrivateRoomOwned
from pynicotine.slskmessages import PrivateRoomRemoved
from pynicotine.slskmessages import PrivateRoomRemoveOperator
from pynicotine.slskmessages import PrivateRoomRemoveUser
from pynicotine.slskmessages import PrivateRoomSomething
from pynicotine.slskmessages import PrivateRoomToggle
from pynicotine.slskmessages import PrivateRoomUsers
from pynicotine.slskmessages import PrivilegedUsers
from pynicotine.slskmessages import PublicRoomMessage
from pynicotine.slskmessages import QueuedDownloads
from pynicotine.slskmessages import QueueFailed
from pynicotine.slskmessages import QueueUpload
from pynicotine.slskmessages import Recommendations
from pynicotine.slskmessages import Relogged
from pynicotine.slskmessages import RemoveThingIHate
from pynicotine.slskmessages import RemoveThingILike
from pynicotine.slskmessages import RoomAdded
from pynicotine.slskmessages import RoomList
from pynicotine.slskmessages import RoomRemoved
from pynicotine.slskmessages import RoomSearch
from pynicotine.slskmessages import RoomTickerAdd
from pynicotine.slskmessages import RoomTickerRemove
from pynicotine.slskmessages import RoomTickerSet
from pynicotine.slskmessages import RoomTickerState
from pynicotine.slskmessages import SayChatroom
from pynicotine.slskmessages import SearchInactivityTimeout
from pynicotine.slskmessages import SearchParent
from pynicotine.slskmessages import SearchRequest
from pynicotine.slskmessages import SendSpeed
from pynicotine.slskmessages import SendUploadSpeed
from pynicotine.slskmessages import ServerConn
from pynicotine.slskmessages import ServerMessage
from pynicotine.slskmessages import ServerPing
from pynicotine.slskmessages import SetDownloadLimit
from pynicotine.slskmessages import SetGeoBlock
from pynicotine.slskmessages import SetStatus
from pynicotine.slskmessages import SetUploadLimit
from pynicotine.slskmessages import SetWaitPort
from pynicotine.slskmessages import SharedFileList
from pynicotine.slskmessages import SharedFoldersFiles
from pynicotine.slskmessages import SimilarUsers
from pynicotine.slskmessages import TransferRequest
from pynicotine.slskmessages import TransferResponse
from pynicotine.slskmessages import TunneledMessage
from pynicotine.slskmessages import Unknown6
from pynicotine.slskmessages import UploadFailed
from pynicotine.slskmessages import UploadFile
from pynicotine.slskmessages import UploadQueueNotification
from pynicotine.slskmessages import UserInfoReply
from pynicotine.slskmessages import UserInfoRequest
from pynicotine.slskmessages import UserInterests
from pynicotine.slskmessages import UserJoinedRoom
from pynicotine.slskmessages import UserLeftRoom
from pynicotine.slskmessages import UserPrivileged
from pynicotine.slskmessages import UserSearch
from pynicotine.slskmessages import WishlistInterval
from pynicotine.slskmessages import WishlistSearch
from pynicotine.utils import win32

if sys.platform == "win32":
    from pynicotine.multiselect import multiselect


MAXFILELIMIT = -1
if win32:
    import ctypes
    ctypes.cdll.msvcrt._setmaxstdio(2048)
    MAXFILELIMIT = ctypes.cdll.msvcrt._getmaxstdio()
else:
    try:
        import resource
        try:
            (soft, MAXFILELIMIT) = resource.getrlimit(resource.RLIMIT_NOFILE)
        except AttributeError:
            pass
    except ImportError:
        pass

# OSX reports INFINITE as hard limit, but supports up to 10240
# Solaris supposedly reports 65535 and actually supports this
# Linux usually reports 1024 and supports this.
if MAXFILELIMIT > 65535:
    MAXFILELIMIT = 2048
if MAXFILELIMIT > 0:
    # Bumping soft limit
    try:
        resource.setrlimit(resource.RLIMIT_NOFILE, (MAXFILELIMIT, MAXFILELIMIT))
    except Exception:
        pass

# Since most people have a limit of 1024 or higher we can
# set it to 90% of the max limit and still get a workable amount of
# connections. We cannot set it to 100% because our connection count
# doesn't agree with with the OS connection count (at least on Linux),
# maybe because closed connections aren't closed on the spot.
MAXFILELIMIT = max(int(floor(MAXFILELIMIT * 0.9)), 100)


class Connection:
    """
    Holds data about a connection. conn is a socket object,
    addr is (ip, port) pair, ibuf and obuf are input and output msgBuffer,
    init is a PeerInit object (see slskmessages docstrings).
    """
    def __init__(self, conn=None, addr=None, ibuf=b"", obuf=b""):
        if not isinstance(ibuf, bytes):
            raise ValueError(f'ibuf is of type {type(ibuf).__name__}: {ibuf}')
        if not isinstance(obuf, bytes):
            raise ValueError(f'obuf is of type {type(obuf).__name__}: {obuf}')
        self.conn = conn
        self.addr = addr
        self.ibuf: bytes = ibuf
        self.obuf: bytes = obuf
        self.init = None
        self.lastreadlength = 100 * 1024


class ServerConnection(Connection):
    """
    Server socket
    """
    def __init__(self, conn=None, addr=None, ibuf=b"", obuf=b""):
        Connection.__init__(self, conn, addr, ibuf, obuf)
        self.lastping = time.time()


class PeerConnection(Connection):
    def __init__(self, conn=None, addr=None, ibuf=b"", obuf=b"", init=None):
        Connection.__init__(self, conn, addr, ibuf, obuf)
        self.filereq = None
        self.filedown = None
        self.fileupl = None
        self.filereadbytes = 0
        self.bytestoread = 0
        self.init = init
        self.piercefw = None
        self.lastactive = time.time()

        self.starttime = None  # Used for upload bandwidth management
        self.sentbytes2 = 0
        self.readbytes2 = 0


class PeerConnectionInProgress:
    """ As all p2p connect()s are non-blocking, this class is used to
    hold data about a connection that is not yet established. msgObj is
    a message to be sent after the connection has been established.
    """
    def __init__(self, conn=None, msgObj=None):
        self.conn = conn
        self.msgObj = msgObj
        self.lastactive = time.time()


class SlskProtoThread(threading.Thread):
    """ This is a networking thread that actually does all the communication.
    It sends data to the UI thread via a callback function and receives data
    via a Queue object.
    """

    """ Server and peers send each other small binary messages, that start
    with length and message code followed by the actual message data.
    These are the codes."""

    servercodes = {
        Login: 1,
        SetWaitPort: 2,
        GetPeerAddress: 3,
        AddUser: 5,
        Unknown6: 6,
        GetUserStatus: 7,
        SayChatroom: 13,
        JoinRoom: 14,
        LeaveRoom: 15,
        UserJoinedRoom: 16,
        UserLeftRoom: 17,
        ConnectToPeer: 18,
        MessageUser: 22,
        MessageAcked: 23,
        FileSearch: 26,
        SetStatus: 28,
        ServerPing: 32,
        SendSpeed: 34,
        SharedFoldersFiles: 35,
        GetUserStats: 36,
        QueuedDownloads: 40,
        Relogged: 41,
        UserSearch: 42,
        AddThingILike: 51,
        RemoveThingILike: 52,
        Recommendations: 54,
        GlobalRecommendations: 56,
        UserInterests: 57,
        PlaceInLineResponse: 60,  # Depreciated?
        RoomAdded: 62,
        RoomRemoved: 63,
        RoomList: 64,
        ExactFileSearch: 65,
        AdminMessage: 66,
        GlobalUserList: 67,  # Depreciated?
        TunneledMessage: 68,  # Depreciated?
        PrivilegedUsers: 69,
        HaveNoParent: 71,
        SearchParent: 73,
        ParentMinSpeed: 83,
        ParentSpeedRatio: 84,
        Msg85: 85,
        ParentInactivityTimeout: 86,
        SearchInactivityTimeout: 87,
        MinParentsInCache: 88,
        Msg89: 89,
        DistribAliveInterval: 90,
        AddToPrivileged: 91,
        CheckPrivileges: 92,
        SearchRequest: 93,
        AcceptChildren: 100,
        NetInfo: 102,
        WishlistSearch: 103,
        WishlistInterval: 104,
        SimilarUsers: 110,
        ItemRecommendations: 111,
        ItemSimilarUsers: 112,
        RoomTickerState: 113,
        RoomTickerAdd: 114,
        RoomTickerRemove: 115,
        RoomTickerSet: 116,
        AddThingIHate: 117,
        RemoveThingIHate: 118,
        RoomSearch: 120,
        SendUploadSpeed: 121,
        UserPrivileged: 122,
        GivePrivileges: 123,
        NotifyPrivileges: 124,
        AckNotifyPrivileges: 125,
        BranchLevel: 126,
        BranchRoot: 127,
        ChildDepth: 129,
        # AnotherStatus: 10,
        PrivateRoomUsers: 133,
        PrivateRoomAddUser: 134,
        PrivateRoomRemoveUser: 135,
        PrivateRoomDismember: 136,
        PrivateRoomDisown: 137,
        PrivateRoomSomething: 138,
        PrivateRoomAdded: 139,
        PrivateRoomRemoved: 140,
        PrivateRoomToggle: 141,
        ChangePassword: 142,
        PrivateRoomAddOperator: 143,
        PrivateRoomRemoveOperator: 144,
        PrivateRoomOperatorAdded: 145,
        PrivateRoomOperatorRemoved: 146,
        PrivateRoomOwned: 148,
        JoinPublicRoom: 150,
        LeavePublicRoom: 151,
        PublicRoomMessage: 152,
        CantConnectToPeer: 1001,
    }

    peercodes = {
        GetSharedFileList: 4,
        SharedFileList: 5,
        FileSearchRequest: 8,
        FileSearchResult: 9,
        UserInfoRequest: 15,
        UserInfoReply: 16,
        PMessageUser: 22,
        FolderContentsRequest: 36,
        FolderContentsResponse: 37,
        TransferRequest: 40,
        TransferResponse: 41,
        PlaceholdUpload: 42,
        QueueUpload: 43,
        PlaceInQueue: 44,
        UploadFailed: 46,
        QueueFailed: 50,
        PlaceInQueueRequest: 51,
        UploadQueueNotification: 52,
        Msg12547: 12547
    }

    distribclasses = {
        0: DistribAlive,
        3: DistribSearch,
        4: DistribBranchLevel,
        5: DistribBranchRoot,
        7: DistribChildDepth,
        9: DistribMessage9
    }

    IN_PROGRESS_STALE_AFTER = 30
    # The value of 30 was pulled out of thin air. When we let the OS handle this:
    # - Linux seems okay, stale in progress conns get killed after a minute or two
    # - With Windows, based on #473, it would seem these connections are never removed
    CONNECTION_MAX_IDLE = 60

    def __init__(self, ui_callback, queue, bindip, port, config, eventprocessor):
        """ ui_callback is a UI callback function to be called with messages
        list as a parameter. queue is Queue object that holds messages from UI
        thread.
        """
        threading.Thread.__init__(self)
        self._ui_callback = ui_callback
        self._queue = queue
        self._want_abort = 0
        self._stopped = 0
        self._bindip = bindip
        self._config = config
        self._eventprocessor = eventprocessor
        portrange = (port, port) if port else config.sections["server"]["portrange"]
        self.serverclasses = {}
        for i in list(self.servercodes.keys()):
            self.serverclasses[self.servercodes[i]] = i
        self.peerclasses = {}
        for i in list(self.peercodes.keys()):
            self.peerclasses[self.peercodes[i]] = i
        self._p = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._p.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._conns = {}
        self._connsinprogress = {}
        self._uploadlimit = (self._calcLimitNone, 0)
        self._downloadlimit = (self._calcDLimitByTotal, self._config.sections["transfers"]["downloadlimit"])
        self._limits = {}
        self._dlimits = {}
        # GeoIP Config
        self._geoip = None
        # GeoIP Module
        self.geoip = self._eventprocessor.geoip
        listenport = None
        self.lastsocketwarning = 0

        for listenport in range(int(portrange[0]), int(portrange[1]) + 1):
            try:
                self._p.bind((bindip or '', listenport))
            except socket.error:
                listenport = None
            else:
                self._p.listen(1)
                self._ui_callback([IncPort(listenport)])
                break
        if listenport is not None:
            self.start()
        else:
            short_message = _("Could not bind to a local port, aborting connection")
            long_message = _(
                f"The range you specified for client connection ports was "
                f"{portrange[0]}-{portrange[1]}, but none of these were usable. Increase and/or "
                f"move the range and restart Nicotine+."
            )
            if portrange[0] < 1024:
                long_message += "\n\n" + _(
                    "Note that part of your range lies below 1024, this is usually not allowed on"
                    " most operating systems with the exception of Windows."
                )
            self._ui_callback([PopupMessage(short_message, long_message)])

    def _isUpload(self, conn):
        return conn.__class__ is PeerConnection and conn.fileupl is not None

    def _isDownload(self, conn):
        return conn.__class__ is PeerConnection and conn.filedown is not None

    def _calcUploadSpeed(self, i):
        curtime = time.time()
        if i.starttime is None:
            i.starttime = curtime
        elapsed = curtime - i.starttime
        if elapsed == 0:
            return 0
        else:
            return i.sentbytes2 / elapsed

    def _calcLimitByTransfer(self, conns, i):
        max = self._uploadlimit[1] * 1024.0
        limit = max - self._calcUploadSpeed(i) + 1024
        if limit < 1024.0:
            return int(0)
        return int(limit)

    def _calcLimitByTotal(self, conns, i):
        max = self._uploadlimit[1] * 1024.0
        bw = 0.0
        for j in list(conns.values()):
            if self._isUpload(j):
                bw += self._calcUploadSpeed(j)
        limit = max - bw + 1024
        if limit < 1024.0:
            return int(0)
        return int(limit)

    def _calcDownloadSpeed(self, i):
        curtime = time.time()
        if i.starttime is None:
            i.starttime = curtime
        elapsed = curtime - i.starttime
        if elapsed == 0:
            return 0
        else:
            return i.readbytes2 / elapsed

    def _calcDLimitByTotal(self, conns, i):
        max = self._downloadlimit[1] * 1024.0
        bw = 0.0
        for j in conns:
            if self._isDownload(j):
                bw += self._calcDownloadSpeed(j)
        limit = max - bw + 1023
        if limit < 1024.0:
            return int(0)
        return int(limit)

    def _calcLimitNone(self, conns, i):
        return None

    def run(self):
        """ Actual networking loop is here."""
        # @var p Peer / Listen Port
        p = self._p
        # @var s Server Port
        self._server_socket = server_socket = None
        conns = self._conns
        connsinprogress = self._connsinprogress
        queue = self._queue

        while not self._want_abort:
            if not queue.empty():
                conns, connsinprogress, server_socket = self.process_queue(queue, conns, connsinprogress, server_socket)
                self._server_socket = server_socket
            for i in list(conns.keys())[:]:
                if conns[i].__class__ is ServerConnection and i is not server_socket:
                    del conns[i]
            outsocks = [i for i in list(conns.keys()) if len(conns[i].obuf) > 0 or (i is not server_socket and conns[i].fileupl is not None and conns[i].fileupl.offset is not None)]
            outsock = []
            self._limits = {}
            self._dlimits = {}
            for i in outsocks:
                if self._isUpload(conns[i]):
                    limit = self._uploadlimit[0](conns, conns[i])
                    if limit is None or limit > 0:
                        self._limits[i] = limit
                        outsock.append(i)

                else:
                    outsock.append(i)
            try:
                # Select Networking Input and Output sockets
                if sys.platform == "win32":
                    input, output, exc = multiselect(list(conns.keys()) + list(connsinprogress.keys()) + [p], list(connsinprogress.keys()) + outsock, [], 0.5)
                else:
                    input, output, exc = select.select(list(conns.keys()) + list(connsinprogress.keys()) + [p], list(connsinprogress.keys()) + outsock, [], 0.5)
                numsockets = 0
                if p is not None:
                    numsockets += 1
                numsockets += len(conns) + len(connsinprogress)

                self._ui_callback([InternalData(numsockets)])
            # print "Sockets open: %s = %s + %s + %s (+1)" % (len(conns.keys()+connsinprogress.keys()+[p]+outsock), len(conns.keys()),  len(connsinprogress.keys()), len(outsock))
            except select.error as error:
                if len(error.args) == 2 and error.args[0] == EINTR:
                    # Error recieved; but we don't care :)
                    continue
                # Error recieved; terminate networking loop
                print(time.strftime("%H:%M:%S"), "select.error", error)
                self._want_abort = 1
                message = _("Major Socket Error: Networking terminated! %s" % str(error))
                log.addwarning(message)
            except ValueError as error:
                # Possibly opened too many sockets
                print(time.strftime("%H:%M:%S"), "select ValueError:", error)
                if not self.killOverflowConnection(connsinprogress):
                    self.killOverflowConnection(conns)
                continue
            # Write Output
            for (key, value) in conns.items():
                if key in output:
                    try:
                        self.writeData(server_socket, conns, key)
                    except socket.error as err:
                        self._ui_callback([ConnectError(value, err)])
            # Listen / Peer Port
            if p in input[:]:
                print(f"reading from {p}")
                try:
                    incconn, incaddr = p.accept()
                except Exception:
                    time.sleep(0.01)
                else:
                    ip, port = self.getIpPort(incaddr)
                    if self.ipBlocked(ip):
                        message = _("Ignoring connection request from blocked IP Address %(ip)s:%(port)s" % {
                            'ip': ip,
                            'port': port
                        })
                        log.add(message, 3)
                    else:
                        conns[incconn] = PeerConnection(incconn, incaddr, b"", b"")
                        self._ui_callback([IncConn(incconn, incaddr)])

            # Manage Connections
            curtime = time.time()
            for connection_in_progress in list(connsinprogress.keys())[:]:
                if (curtime - connsinprogress[connection_in_progress].lastactive) > self.IN_PROGRESS_STALE_AFTER:
                    connection_in_progress.close()
                    del connsinprogress[connection_in_progress]
                    continue
                try:
                    msgObj = connsinprogress[connection_in_progress].msgObj
                    if connection_in_progress in input:
                        connection_in_progress.recv(0)
                except socket.error as err:
                    self._ui_callback([ConnectError(msgObj, err)])
                    connection_in_progress.close()
                    del connsinprogress[connection_in_progress]
                else:
                    if connection_in_progress in output:
                        if connection_in_progress is server_socket:
                            conns[server_socket] = ServerConnection(server_socket, msgObj.addr, b"", b"")
                            self._ui_callback([ServerConn(server_socket, msgObj.addr)])
                        else:
                            ip, port = self.getIpPort(msgObj.addr)
                            if self.ipBlocked(ip):
                                message = "Blocking peer connection in progress to IP: %(ip)s Port: %(port)s" % {"ip": ip, "port": port}
                                log.add(message, 3)
                                connection_in_progress.close()
                            else:
                                conns[connection_in_progress] = PeerConnection(connection_in_progress, msgObj.addr, b"", b"", msgObj.init)
                                self._ui_callback([OutConn(connection_in_progress, msgObj.addr)])
                        del connsinprogress[connection_in_progress]
            # Process Data
            for connection in list(conns.keys())[:]:
                ip, port = self.getIpPort(conns[connection].addr)
                # print(f"ip: {ip}:{port}  p: {p}, conn: {connection}")
                if self.ipBlocked(ip) and connection is not self._server_socket:
                    message = "Blocking peer connection to IP: %(ip)s Port: %(port)s" % {"ip": ip, "port": port}
                    log.add(message, 3)
                    connection.close()
                    del conns[connection]
                    continue

                if connection in input:
                    if self._isDownload(conns[connection]):
                        limit = self._downloadlimit[0](conns, connection)
                        if limit is None or limit > 0:
                            self._dlimits[connection] = limit
                        # if connection in self._dlimits:
                        # FIXME: Fix this Ugly download limit hack (sleep)
                        # time.sleep(1.0)

                        try:
                            self.readData(conns, connection)
                        except socket.error as err:
                            self._ui_callback([ConnectError(conns[connection], err)])
                    else:
                        try:
                            self.readData(conns, connection)
                        except socket.error as err:
                            self._ui_callback([ConnectError(conns[connection], err)])
                if connection in conns and len(conns[connection].ibuf) > 0:
                    if connection is server_socket:
                        msgs, conns[server_socket].ibuf = self.process_server_input(conns[server_socket].ibuf)
                        self._ui_callback(msgs)
                    else:
                        if conns[connection].init is None or conns[connection].init.type not in ['F', 'D']:
                            msgs, conns[connection] = self.process_peer_input(conns[connection], conns[connection].ibuf)
                            self._ui_callback(msgs)
                        if conns[connection].init is not None and conns[connection].init.type == 'F':
                            msgs, conns[connection] = self.process_file_input(conns[connection], conns[connection].ibuf)
                            self._ui_callback(msgs)
                        if conns[connection].init is not None and conns[connection].init.type == 'D':
                            msgs, conns[connection] = self.process_distrib_input(conns[connection], conns[connection].ibuf)
                            self._ui_callback(msgs)
                        if conns[connection].conn is None:
                            del conns[connection]

            # ---------------------------
            # Server Pings used to get us banned
            # ---------------------------
            # Timeout Connections
            curtime = time.time()
            connsockets = len(list(conns.keys()))  # noqa: F841
            for connection in list(conns.keys())[:]:
                if connection is not server_socket and connection is not p:
                    if curtime - conns[connection].lastactive > self.CONNECTION_MAX_IDLE:
                        self._ui_callback([ConnClose(connection, conns[connection].addr)])
                        connection.close()
                        # print "Closed_run", conns[i].addr
                        del conns[connection]
                #  Was 30 seconds
            if server_socket in conns:
                if curtime - conns[server_socket].lastping > 120:
                    conns[server_socket].lastping = curtime
                    queue.put(ServerPing())

            self._ui_callback([])
            if self._downloadlimit[1] and self._downloadlimit[1] > 0:
                time.sleep(0.1)

        # Close Server Port
        if server_socket is not None:
            server_socket.close()
        # print "Networking thread aborted"
        self._stopped = 1

    # randomly selects a safe connection to kill and closes the socket--
    # Will not kill upload, download, or server connections
    def killOverflowConnection(self, conns):
        victim_conn = None
        for (k, v) in conns.items():
            if self._isUpload(v):
                continue
            if self._isDownload(v):
                continue
            if k is self._server_socket:
                continue
            victim_conn = k
            break

        if victim_conn is None:
            return False

        del conns[victim_conn]
        # if endpoint is not connected, will get an exception on sockets...
        try:
            pn = victim_conn.getpeername()
            print('Killing overflow connection ', pn)
            victim_conn.shutdown(socket.SHUT_RDWR)
            victim_conn.close()
        except Exception:
            return False
        return True

    def socketStillActive(self, conn):
        try:
            connection = self._conns[conn]
        except KeyError:
            return False
        return len(connection.obuf) > 0 or len(connection.ibuf) > 0

    def ipBlocked(self, address):
        if address is None:
            return True
        ips = self._config.sections["server"]["ipblocklist"]
        s_address = address.split(".")
        for ip in ips:
            # No Wildcard in IP
            if "*" not in ip:
                if address == ip:
                    return True
                continue
            # Wildcard in IP
            parts = ip.split(".")
            seg = 0
            for part in parts:
                # Stop if there's no wildcard or matching string number
                if part not in (s_address[seg], "*"):
                    break

                seg += 1
                # Last time around
                if seg == 4:
                    # Wildcard blocked
                    return True
        # Not blocked
        return False

    def getIpPort(self, address):
        ip = port = None
        if type(address) is tuple:
            ip, port = address

        return ip, port

    def writeData(self, server_socket, conns, i):
        if i in self._limits:
            limit = self._limits[i]
        else:
            limit = None

        conns[i].lastactive = time.time()
        i.setblocking(0)
        if limit is None:
            bytes_send = i.send(conns[i].obuf)
        else:
            bytes_send = i.send(conns[i].obuf[:limit])

        i.setblocking(1)
        conns[i].obuf = conns[i].obuf[bytes_send:]
        if i is not server_socket:
            if conns[i].fileupl is not None and conns[i].fileupl.offset is not None:
                conns[i].fileupl.sentbytes += bytes_send
                conns[i].sentbytes2 += bytes_send
                try:
                    if conns[i].fileupl.offset + conns[i].fileupl.sentbytes + len(conns[i].obuf) < conns[i].fileupl.size:
                        bytestoread = bytes_send * 2 - len(conns[i].obuf) + 10 * 1024
                        if bytestoread > 0:
                            read = conns[i].fileupl.file.read(bytestoread)
                            conns[i].obuf = conns[i].obuf + read
                except IOError as strerror:
                    self._ui_callback([FileError(conns[i], conns[i].fileupl.file, strerror)])
                except ValueError:
                    pass

                if bytes_send > 0:
                    self._ui_callback([conns[i].fileupl])

    def readData(self, conns, i):
        # Check for a download limit
        if i in self._dlimits:
            limit = self._dlimits[i]
        else:
            limit = None
        conns[i].lastactive = time.time()
        if limit is None:
            # Unlimited download data
            data = i.recv(conns[i].lastreadlength)
            conns[i].ibuf = conns[i].ibuf + data
            if len(data) >= conns[i].lastreadlength // 2:
                conns[i].lastreadlength = conns[i].lastreadlength * 2
        else:
            # Speed Limited Download data (transfers)
            data = i.recv(conns[i].lastreadlength)
            conns[i].ibuf += data
            conns[i].lastreadlength = limit
            conns[i].readbytes2 += len(data)

        if not data:
            self._ui_callback([ConnClose(i, conns[i].addr)])
            i.close()
            # print "Closed", conns[i].addr
            del conns[i]

    def process_server_input(self, msgBuffer: bytes):
        """ Server has sent us something, this function retrieves messages
        from the msgBuffer, creates message objects and returns them and the rest
        of the msgBuffer.
        """
        msgs = []
        # Server messages are 8 bytes or greater in length
        while len(msgBuffer) >= 8:
            msgsize, msgtype = struct.unpack("<ii", msgBuffer[:8])
            if msgsize + 4 > len(msgBuffer):
                break
            elif msgtype in self.serverclasses:
                msg = self.serverclasses[msgtype]()
                msg.parseNetworkMessage(msgBuffer[8:msgsize + 4])
                msgs.append(msg)
            else:
                msgs.append(_("Server message type %(type)i size %(size)i contents %(msgBuffer)s unknown") % {'type': msgtype, 'size': msgsize - 4, 'msgBuffer': msgBuffer[8:msgsize + 4].__repr__()})
            msgBuffer = msgBuffer[msgsize + 4:]
        return msgs, msgBuffer

    def parseFileReq(self, conn, msgBuffer):
        msg = None
        # File Request messages are 4 bytes or greater in length
        if len(msgBuffer) >= 4:
            reqnum = struct.unpack("<i", msgBuffer[:4])[0]
            msg = FileRequest(conn.conn, reqnum)
            msgBuffer = msgBuffer[4:]
        return msg, msgBuffer

    def parseOffset(self, conn, msgBuffer):
        offset = None
        if len(msgBuffer) >= 8:
            offset = struct.unpack("<i", msgBuffer[:4])[0]
            msgBuffer = msgBuffer[8:]
        return offset, msgBuffer

    def process_file_input(self, conn, msgBuffer):
        """ We have a "F" connection (filetransfer) , peer has sent us
        something, this function retrieves messages
        from the msgBuffer, creates message objects and returns them
        and the rest of the msgBuffer.
        """
        msgs = []
        if conn.filereq is None:
            filereq, msgBuffer = self.parseFileReq(conn, msgBuffer)
            if filereq is not None:
                msgs.append(filereq)
                conn.filereq = filereq
        elif conn.filedown is not None:
            leftbytes = conn.bytestoread - conn.filereadbytes
            if leftbytes > 0:
                try:
                    conn.filedown.file.write(msgBuffer[:leftbytes])
                except IOError as strerror:
                    self._ui_callback([FileError(conn, conn.filedown.file, strerror)])
                except ValueError:
                    pass
                self._ui_callback([DownloadFile(conn.conn, len(msgBuffer[:leftbytes]), conn.filedown.file)])
            conn.filereadbytes = conn.filereadbytes + len(msgBuffer[:leftbytes])
            msgBuffer = msgBuffer[leftbytes:]
        elif conn.fileupl is not None:
            if conn.fileupl.offset is None:
                offset, msgBuffer = self.parseOffset(conn, msgBuffer)
                if offset is not None:
                    try:
                        conn.fileupl.file.seek(offset)
                    except IOError as strerror:
                        self._ui_callback([FileError(conn, conn.fileupl.file, strerror)])
                    except ValueError:
                        pass
                    conn.fileupl.offset = offset
                    self._ui_callback([conn.fileupl])

        conn.ibuf = msgBuffer
        return msgs, conn

    def process_peer_input(self, conn, msgBuffer):
        """ We have a "P" connection (p2p exchange) , peer has sent us
        something, this function retrieves messages
        from the msgBuffer, creates message objects and returns them
        and the rest of the msgBuffer.
        """
        msgs = []
        while (conn.init is None or conn.init.type not in ['F', 'D']) and len(msgBuffer) >= 8:
            msgsize = struct.unpack("<i", msgBuffer[:4])[0]
            if len(msgBuffer) >= 8:
                msgtype = struct.unpack("<i", msgBuffer[4:8])[0]
                self._ui_callback([PeerTransfer(conn, msgsize, len(msgBuffer) - 4, self.peerclasses.get(msgtype, None))])
            if msgsize + 4 > len(msgBuffer):
                break
            elif conn.init is None:
                # Unpack Peer Connections
                if msgBuffer[4] == 0:
                    msg = PierceFireWall(conn)
                    try:
                        msg.parseNetworkMessage(msgBuffer[5:msgsize + 4])
                    except Exception as error:
                        print(error)
                    else:
                        conn.piercefw = msg
                        msgs.append(msg)
                elif msgBuffer[4] == 1:
                    msg = PeerInit(conn)
                    try:
                        msg.parseNetworkMessage(msgBuffer[5:msgsize + 4])
                    except Exception as error:
                        print(error)
                    else:
                        conn.init = msg
                        msgs.append(msg)
                elif conn.piercefw is None:
                    msgs.append(_(
                        f"Unknown peer init code: {msgBuffer[4]}, message contents "
                        f"{ msgBuffer[5:msgsize + 4].__repr__()}"
                    ))
                    conn.conn.close()
                    self._ui_callback([ConnClose(conn.conn, conn.addr)])
                    conn.conn = None
                    break
                else:
                    break
            elif conn.init.type == 'P':
                # Unpack Peer Messages
                msgtype = struct.unpack("<i", msgBuffer[4:8])[0]
                if msgtype in self.peerclasses:
                    try:
                        msg = self.peerclasses[msgtype](conn)
                        # Parse Peer Message and handle exceptions
                        try:
                            msg.parseNetworkMessage(msgBuffer[8:msgsize + 4])
                        except Exception as error:
                            host = port = _("unknown")
                            msgname = str(self.peerclasses[msgtype]).split(".")[-1]
                            print("Error parsing %s:" % msgname, error)
                            import traceback
                            for line in traceback.format_tb(error.__traceback__):
                                print(line)
                            if "addr" in conn.__dict__:
                                if conn.addr is not None:
                                    host = conn.addr[0]
                                    port = conn.addr[1]
                            debugmessage = _("There was an error while unpacking Peer message type %(type)s size %(size)i contents %(msgBuffer)s from user: %(user)s, %(host)s:%(port)s") % {'type': msgname, 'size': msgsize - 4, 'msgBuffer': msgBuffer[8:msgsize + 4].__repr__(), 'user': conn.init.user, 'host': host, 'port': port}
                            msgs.append(debugmessage)
                            del msg
                        else:
                            msgs.append(msg)
                    except Exception as error:
                        debugmessage = "Error in message function:", error, msgtype, conn
                        msgs.append(debugmessage)

                else:
                    host = port = _("unknown")
                    if conn.init.conn is not None and conn.addr is not None:
                        host = conn.addr[0]
                        port = conn.addr[1]
                    # Unknown Peer Message
                    x = 0
                    newbuf = ""
                    # massive speedup in the status log with the newline
                    # wrapping is incredibly slow
                    for char in msgBuffer[8:msgsize + 4].__repr__():
                        if x % 80 == 0:
                            newbuf += "\n"
                        newbuf += char
                        x += 1
                    debugmessage = _("Peer message type %(type)s size %(size)i contents %(msgBuffer)s unknown, from user: %(user)s, %(host)s:%(port)s") % {'type': msgtype, 'size': msgsize - 4, 'msgBuffer': newbuf, 'user': conn.init.user, 'host': host, 'port': port}
                    msgs.append(debugmessage)

            else:
                # Unknown Message type
                msgs.append(_("Can't handle connection type %s") % (conn.init.type))
            if msgsize >= 0:
                msgBuffer = msgBuffer[msgsize + 4:]
            else:
                msgBuffer = b""
        conn.ibuf = msgBuffer
        return msgs, conn

    def process_distrib_input(self, conn, msgBuffer):
        """ We have a distributed network connection, parent has sent us
        something, this function retrieves messages
        from the msgBuffer, creates message objects and returns them
        and the rest of the msgBuffer.
        """
        msgs = []
        while len(msgBuffer) >= 5:
            msgsize = struct.unpack("<i", msgBuffer[:4])[0]
            if msgsize + 4 > len(msgBuffer):
                break
            msgtype = msgBuffer[4]
            if msgtype in self.distribclasses:
                msg = self.distribclasses[msgtype](conn)
                msg.parseNetworkMessage(msgBuffer[5:msgsize + 4])
                msgs.append(msg)
            else:
                msgs.append(_("Distrib message type %(type)i size %(size)i contents %(msgBuffer)s unknown") % {'type': msgtype, 'size': msgsize - 1, 'msgBuffer': msgBuffer[5:msgsize + 4].__repr__()})
                conn.conn.close()
                self._ui_callback([ConnClose(conn.conn, conn.addr)])
                conn.conn = None
                break
            if msgsize >= 0:
                msgBuffer = msgBuffer[msgsize + 4:]
            else:
                msgBuffer = b""
        conn.ibuf = msgBuffer
        return msgs, conn

    def _resetCounters(self, conns):
        curtime = time.time()
        for i in list(conns.values()):
            if self._isUpload(i):
                i.starttime = curtime
                i.sentbytes2 = 0
            if self._isDownload(i):
                i.starttime = curtime
                i.sentbytes2 = 0

    def process_queue(self, queue, conns, connsinprogress, server_socket, maxsockets=MAXFILELIMIT):
        """ Processes messages sent by UI thread. server_socket is a server connection
        socket object, queue holds the messages, conns and connsinprogress
        are dictionaries holding Connection and PeerConnectionInProgress
        messages."""
        msgList = []
        needsleep = False
        numsockets = 0
        if server_socket is not None:
            numsockets += 1
        numsockets += len(conns) + len(connsinprogress)
        while not queue.empty():
            msgList.append(queue.get())

        for msgObj in msgList:
            if issubclass(msgObj.__class__, ServerMessage):
                try:
                    msg = msgObj.makeNetworkMessage()
                    if msg == '' or msg is None:
                        msg = b''
                    if server_socket in conns:

                        conns[server_socket].obuf += \
                            struct.pack("<ii", len(msg) + 4, self.servercodes[msgObj.__class__]) + \
                            msg
                    else:
                        queue.put(msgObj)
                        needsleep = True
                except Exception as error:
                    print(_("Error packaging message: %(type)s %(msg_obj)s, %(error)s") % {'type': msgObj.__class__, 'msg_obj': vars(msgObj), 'error': str(error)})
                    self._ui_callback([_("Error packaging message: %(type)s %(msg_obj)s, %(error)s") % {'type': msgObj.__class__, 'msg_obj': vars(msgObj), 'error': str(error)}])
            elif issubclass(msgObj.__class__, PeerMessage):
                if msgObj.conn in conns:
                    # Pack Peer and File and Search Messages
                    if msgObj.__class__ is PierceFireWall:
                        conns[msgObj.conn].piercefw = msgObj
                        msg = msgObj.makeNetworkMessage()
                        conns[msgObj.conn].obuf += struct.pack("<i", len(msg) + 1) + \
                            bytes(chr(0), 'ascii') + \
                            msg
                    elif msgObj.__class__ is PeerInit:
                        conns[msgObj.conn].init = msgObj
                        msg = msgObj.makeNetworkMessage()
                        if conns[msgObj.conn].piercefw is None:
                            conns[msgObj.conn].obuf += struct.pack("<i", len(msg) + 1) + \
                                bytes(chr(1), 'ascii') + \
                                msg

                    elif msgObj.__class__ is FileRequest:
                        conns[msgObj.conn].filereq = msgObj
                        msg = msgObj.makeNetworkMessage()
                        conns[msgObj.conn].obuf += msg
                        self._ui_callback([msgObj])
                    else:
                        checkuser = 1
                        if msgObj.__class__ is FileSearchResult and msgObj.geoip and self.geoip and self._geoip:
                            cc = self.geoip.country_code_by_addr(conns[msgObj.conn].addr[0])
                            if not cc and self._geoip[0]:
                                checkuser = 0
                            elif cc and self._geoip[1][0].find(cc) >= 0:
                                checkuser = 0
                        if checkuser:
                            msg = msgObj.makeNetworkMessage()
                            conns[msgObj.conn].obuf += struct.pack("<ii", len(msg) + 4, self.peercodes[msgObj.__class__]) + \
                                msg
                else:
                    if msgObj.__class__ not in [PeerInit, PierceFireWall, FileSearchResult]:
                        message = _("Can't send the message over the closed connection: %(type)s %(msg_obj)s") % {'type': msgObj.__class__, 'msg_obj': vars(msgObj)}
                        log.add(message, 3)
            elif issubclass(msgObj.__class__, InternalMessage):
                socketwarning = False
                if msgObj.__class__ is ServerConn:
                    if maxsockets == -1 or numsockets < maxsockets:
                        try:
                            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            if self._bindip:
                                server_socket.bind((self._bindip, 0))
                            server_socket.setblocking(0)
                            server_socket.connect_ex(msgObj.addr)
                            server_socket.setblocking(1)
                            connsinprogress[server_socket] = PeerConnectionInProgress(server_socket, msgObj)
                            numsockets += 1
                        except socket.error as err:
                            self._ui_callback([ConnectError(msgObj, err)])
                    else:
                        socketwarning = True
                elif msgObj.__class__ is ConnClose and msgObj.conn in conns:
                    msgObj.conn.close()
                    # print "Close3", conns[msgObj.conn].addr
                    self._ui_callback([ConnClose(msgObj.conn, conns[msgObj.conn].addr)])
                    del conns[msgObj.conn]
                elif msgObj.__class__ is OutConn:
                    if msgObj.addr[1] == 0:
                        self._ui_callback([ConnectError(msgObj, (0, "Port cannot be zero"))])
                    elif maxsockets == -1 or numsockets < maxsockets:
                        try:
                            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            conn.setblocking(0)
                            if self._bindip:
                                conn.bind((self._bindip, 0))
                            conn.connect_ex(msgObj.addr)
                            conn.setblocking(1)
                            connsinprogress[conn] = PeerConnectionInProgress(conn, msgObj)
                            numsockets += 1
                        except socket.error as xxx_todo_changeme:
                            (errnum, strerror) = xxx_todo_changeme.args
                            import errno
                            if errno.errorcode.get(errnum, "") == 'EMFILE':
                                queue.put(msgObj)
                                needsleep = True
                            else:
                                self._ui_callback([ConnectError(msgObj, (errnum, strerror))])
                    else:
                        socketwarning = True
                elif msgObj.__class__ is DownloadFile and msgObj.conn in conns:
                    conns[msgObj.conn].filedown = msgObj
                    conns[msgObj.conn].obuf = conns[msgObj.conn].obuf + struct.pack("<i", msgObj.offset) + struct.pack("<i", 0)
                    conns[msgObj.conn].bytestoread = msgObj.filesize - msgObj.offset
                    self._ui_callback([DownloadFile(msgObj.conn, 0, msgObj.file)])
                elif msgObj.__class__ is UploadFile and msgObj.conn in conns:
                    conns[msgObj.conn].fileupl = msgObj
                    self._resetCounters(conns)
                elif msgObj.__class__ is SetGeoBlock:
                    self._geoip = msgObj.config
                elif msgObj.__class__ is SetUploadLimit:
                    if msgObj.uselimit:
                        if msgObj.limitby:
                            cb = self._calcLimitByTotal
                        else:
                            cb = self._calcLimitByTransfer
                    else:
                        cb = self._calcLimitNone
                    self._resetCounters(conns)
                    self._uploadlimit = (cb, msgObj.limit)
                elif msgObj.__class__ is SetDownloadLimit:
                    self._downloadlimit = (self._calcDLimitByTotal, msgObj.limit)
                if socketwarning and time.time() - self.lastsocketwarning > 60:
                    self.lastsocketwarning = time.time()
                    log.addwarning(_("You have just hit your connection limit of %(limit)s. Nicotine+ will drop connections for your protection. If you get this message often you should search for less generic terms, or increase your per-process file descriptor limit.") % {'limit': maxsockets})
        if needsleep:
            time.sleep(1)

        return conns, connsinprogress, server_socket

    def abort(self):
        """ Call this to abort the thread"""
        self._want_abort = 1

    def stopped(self):
        """ returns true if thread has stopped """
        return self._stopped
