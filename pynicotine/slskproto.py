# Copyright (C) 2020-2021 Nicotine+ Team
# Copyright (C) 2007 daelstorm. All rights reserved.
# Copyright (c) 2003-2004 Hyriand. All rights reserved.
#
# Based on code from PySoulSeek, original copyright note:
# Copyright (c) 2001-2003 Alexander Kanavin. All rights reserved.
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

"""
This module implements Soulseek networking protocol.
"""

import selectors
import socket
import struct
import sys
import threading
import time

from errno import EINTR
from itertools import islice
from random import uniform

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
from pynicotine.slskmessages import CantCreateRoom
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
from pynicotine.slskmessages import DistribEmbeddedMessage
from pynicotine.slskmessages import DistribSearch
from pynicotine.slskmessages import DownloadFile
from pynicotine.slskmessages import EmbeddedMessage
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
from pynicotine.slskmessages import PossibleParents
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
from pynicotine.slskmessages import UploadDenied
from pynicotine.slskmessages import QueueUpload
from pynicotine.slskmessages import Recommendations
from pynicotine.slskmessages import RelatedSearch
from pynicotine.slskmessages import Relogged
from pynicotine.slskmessages import RemoveThingIHate
from pynicotine.slskmessages import RemoveThingILike
from pynicotine.slskmessages import RemoveUser
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
from pynicotine.slskmessages import SendConnectToken
from pynicotine.slskmessages import SendDownloadSpeed
from pynicotine.slskmessages import SendUploadSpeed
from pynicotine.slskmessages import ServerConn
from pynicotine.slskmessages import ServerMessage
from pynicotine.slskmessages import ServerPing
from pynicotine.slskmessages import SetCurrentConnectionCount
from pynicotine.slskmessages import SetDownloadLimit
from pynicotine.slskmessages import SetStatus
from pynicotine.slskmessages import SetUploadLimit
from pynicotine.slskmessages import SetWaitPort
from pynicotine.slskmessages import SharedFileList
from pynicotine.slskmessages import SharedFoldersFiles
from pynicotine.slskmessages import SimilarUsers
from pynicotine.slskmessages import TransferRequest
from pynicotine.slskmessages import TransferResponse
from pynicotine.slskmessages import TunneledMessage
from pynicotine.slskmessages import UnknownPeerMessage
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


""" Set the maximum number of open files to the hard limit reported by the OS.
Our MAXSOCKETS value needs to be lower than the file limit, otherwise our open
sockets in combination with other file activity can exceed the file limit,
effectively halting the program. """

if sys.platform == "win32":

    """ For Windows, FD_SETSIZE is set to 512 in the Python source.
    This limit is hardcoded, so we'll have to live with it for now. """

    MAXSOCKETS = 512
else:
    import resource

    if sys.platform == "darwin":

        """ Maximum number of files a process can open is 10240 on macOS.
        macOS reports INFINITE as hard limit, so we need this special case. """

        MAXFILELIMIT = 10240
    else:
        _SOFTLIMIT, MAXFILELIMIT = resource.getrlimit(resource.RLIMIT_NOFILE)

    try:
        resource.setrlimit(resource.RLIMIT_NOFILE, (MAXFILELIMIT, MAXFILELIMIT))

    except Exception as error:
        log.add("Failed to set RLIMIT_NOFILE: %s", error)

    """ Set the maximum number of open sockets to a lower value than the hard limit,
    otherwise we just waste resources.
    The maximum is 1024, but can be lower if the file limit is too low. """

    MAXSOCKETS = min(max(int(MAXFILELIMIT * 0.75), 50), 1024)


class Connection:
    """
    Holds data about a connection. conn is a socket object,
    addr is (ip, port) pair, ibuf and obuf are input and output msgBuffer,
    init is a PeerInit object (see slskmessages docstrings).
    """

    __slots__ = "conn", "addr", "ibuf", "obuf", "init", "lastactive", "lastreadlength"

    def __init__(self, conn=None, addr=None):
        self.conn = conn
        self.addr = addr
        self.ibuf = bytearray()
        self.obuf = bytearray()
        self.init = None
        self.lastactive = time.time()
        self.lastreadlength = 100 * 1024


class PeerConnection(Connection):

    __slots__ = ("filereq", "filedown", "fileupl", "filereadbytes", "bytestoread", "piercefw",
                 "lastcallback", "starttime", "sentbytes2", "readbytes2")

    def __init__(self, conn=None, addr=None, init=None):
        Connection.__init__(self, conn, addr)
        self.filereq = None
        self.filedown = None
        self.fileupl = None
        self.filereadbytes = 0
        self.bytestoread = 0
        self.init = init
        self.piercefw = None
        self.lastactive = time.time()
        self.lastcallback = time.time()

        self.starttime = None  # Used for upload bandwidth management
        self.sentbytes2 = 0
        self.readbytes2 = 0


class PeerConnectionInProgress:
    """ As all p2p connect()s are non-blocking, this class is used to
    hold data about a connection that is not yet established. msgObj is
    a message to be sent after the connection has been established.
    """
    __slots__ = "conn", "msg_obj", "lastactive"

    def __init__(self, conn=None, msg_obj=None):
        self.conn = conn
        self.msg_obj = msg_obj
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
        RemoveUser: 6,
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
        ServerPing: 32,               # Deprecated
        SendConnectToken: 33,         # Deprecated
        SendDownloadSpeed: 34,        # Deprecated
        SharedFoldersFiles: 35,
        GetUserStats: 36,
        QueuedDownloads: 40,          # Deprecated
        Relogged: 41,
        UserSearch: 42,
        AddThingILike: 51,
        RemoveThingILike: 52,
        Recommendations: 54,
        GlobalRecommendations: 56,
        UserInterests: 57,
        PlaceInLineResponse: 60,      # Deprecated
        RoomAdded: 62,                # Deprecated
        RoomRemoved: 63,              # Deprecated
        RoomList: 64,
        ExactFileSearch: 65,          # Deprecated
        AdminMessage: 66,
        GlobalUserList: 67,           # Deprecated
        TunneledMessage: 68,          # Deprecated
        PrivilegedUsers: 69,
        HaveNoParent: 71,
        SearchParent: 73,
        ParentMinSpeed: 83,           # Unused
        ParentSpeedRatio: 84,         # Unused
        ParentInactivityTimeout: 86,  # Deprecated
        SearchInactivityTimeout: 87,  # Deprecated
        MinParentsInCache: 88,        # Deprecated
        DistribAliveInterval: 90,     # Deprecated
        AddToPrivileged: 91,
        CheckPrivileges: 92,
        EmbeddedMessage: 93,
        AcceptChildren: 100,
        PossibleParents: 102,
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
        RelatedSearch: 153,           # Deprecated ?
        CantConnectToPeer: 1001,      # Deprecated
        CantCreateRoom: 1003
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
        PlaceholdUpload: 42,          # Deprecated
        QueueUpload: 43,
        PlaceInQueue: 44,
        UploadFailed: 46,
        UploadDenied: 50,
        PlaceInQueueRequest: 51,
        UploadQueueNotification: 52,
        UnknownPeerMessage: 12547
    }

    distribclasses = {
        0: DistribAlive,
        3: DistribSearch,
        4: DistribBranchLevel,
        5: DistribBranchRoot,
        7: DistribChildDepth,         # Unimplemented
        93: DistribEmbeddedMessage
    }

    IN_PROGRESS_STALE_AFTER = 2
    CONNECTION_MAX_IDLE = 60
    CONNCOUNT_UI_INTERVAL = 0.5

    def __init__(self, ui_callback, queue, bindip, port, port_range, network_filter, eventprocessor):
        """ ui_callback is a UI callback function to be called with messages
        list as a parameter. queue is Queue object that holds messages from UI
        thread.
        """
        threading.Thread.__init__(self)

        self.name = "NetworkThread"

        self._ui_callback = ui_callback
        self._queue = queue
        self._want_abort = False
        self._server_disconnect = True
        self._bindip = bindip
        self._network_filter = network_filter
        self._eventprocessor = eventprocessor

        self.serverclasses = {}
        for i in self.servercodes:
            self.serverclasses[self.servercodes[i]] = i

        self.peerclasses = {}
        for i in self.peercodes:
            self.peerclasses[self.peercodes[i]] = i

        # Select Networking Input and Output sockets
        self.selector = selectors.DefaultSelector()

        self.listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.selector.register(self.listen_socket, selectors.EVENT_READ)

        self.server_socket = None

        self._conns = {}
        self._connsinprogress = {}
        self._uploadlimit = (self._calc_upload_limit_none, 0)
        self._downloadlimit = (self._calc_download_limit_by_total, 0)
        self._ulimits = {}
        self._dlimits = {}
        self.total_uploads = 0
        self.total_downloads = 0

        self.last_conncount_ui_update = time.time()

        portrange = (port, port) if port else port_range
        listenport = None

        for listenport in range(int(portrange[0]), int(portrange[1]) + 1):
            try:
                self.listen_socket.bind((bindip or '', listenport))
            except socket.error:
                listenport = None
            else:
                self.listen_socket.listen(1)
                self._ui_callback([IncPort(listenport)])
                break

        if listenport is not None:
            self.daemon = True
            self.start()
        else:
            short_message = _("Could not bind to a local port, aborting connection")
            long_message = _(
                "The range you specified for client connection ports was "
                "{}-{}, but none of these were usable. Increase and/or ".format(portrange[0], portrange[1])
                + "move the range and restart Nicotine+."
            )
            if portrange[0] < 1024:
                long_message += "\n\n" + _(
                    "Note that part of your range lies below 1024, this is usually not allowed on"
                    " most operating systems with the exception of Windows."
                )
            self._ui_callback([PopupMessage(short_message, long_message)])

    @staticmethod
    def _is_upload(conn):
        return conn.__class__ is PeerConnection and conn.fileupl is not None

    @staticmethod
    def _is_download(conn):
        return conn.__class__ is PeerConnection and conn.filedown is not None

    def _calc_transfer_speed(self, i):
        curtime = time.time()

        if i.starttime is None:
            i.starttime = curtime

        elapsed = curtime - i.starttime

        if elapsed == 0:
            return 0

        if self._is_upload(i):
            return i.sentbytes2 / elapsed

        return i.readbytes2 / elapsed

    def _calc_upload_limit_by_transfer(self, conns):
        self.total_uploads = sum(1 for j in conns.values() if self._is_upload(j))

        return int(self._uploadlimit[1] * 1024.0)

    def _calc_upload_limit_by_total(self, conns):
        max_limit = self._uploadlimit[1] * 1024.0
        bandwidth = 0.0
        self.total_uploads = 1

        """ Skip first upload
        If we have 2 or more uploads, we start reducing their individual speeds to
        stay below the total limit """

        uploads = islice((j for j in conns.values() if self._is_upload(j)), 1, None)
        for j in uploads:
            bandwidth += self._calc_transfer_speed(j)
            self.total_uploads += 1

        limit = int(max(1024, max_limit - bandwidth))  # 1 KB/s is the minimum upload speed per transfer
        return limit

    def _calc_upload_limit_none(self, conns):
        self.total_uploads = sum(1 for j in conns.values() if self._is_upload(j))

    def _calc_download_limit_by_total(self, conns):
        max_limit = self._downloadlimit[1] * 1024.0
        bandwidth = 0.0
        self.total_downloads = 1

        """ Skip first download
        If we have 2 or more downloads, we start reducing their individual speeds to
        stay below the total limit """

        downloads = islice((j for j in conns.values() if self._is_download(j)), 1, None)
        for j in downloads:
            bandwidth += self._calc_transfer_speed(j)
            self.total_downloads += 1

        if max_limit == 0:
            # Download limit disabled
            limit = 0
        else:
            limit = int(max(1024, max_limit - bandwidth))  # 1 KB/s is the minimum download speed per transfer

        return limit

    def socket_still_active(self, conn):
        try:
            connection = self._conns[conn]
        except KeyError:
            return False

        return len(connection.obuf) > 0 or len(connection.ibuf) > 0

    def close_connection(self, connection_list, connection):

        if connection not in connection_list:
            # Already removed
            return

        self.selector.unregister(connection)
        connection.close()
        del connection_list[connection]

        if connection is self.server_socket:
            # Disconnected from server, clean up connections and queue
            self.server_disconnect()

    @staticmethod
    def parse_file_req(conn, msg_buffer):
        msg = None

        # File Request messages are 4 bytes or greater in length
        if len(msg_buffer) >= 4:
            reqnum = struct.unpack("<i", msg_buffer[:4])[0]
            msg = FileRequest(conn.conn, reqnum)
            msg_buffer = msg_buffer[4:]

        return msg, msg_buffer

    @staticmethod
    def parse_offset(msg_buffer):
        offset = None

        if len(msg_buffer) >= 8:
            offset = struct.unpack("<Q", msg_buffer[:8])[0]
            msg_buffer = msg_buffer[8:]

        return offset, msg_buffer

    def process_server_input(self, msg_buffer):
        """ Server has sent us something, this function retrieves messages
        from the msg_buffer, creates message objects and returns them and the rest
        of the msg_buffer.
        """
        msgs = []

        # Server messages are 8 bytes or greater in length
        while len(msg_buffer) >= 8:
            msgsize, msgtype = struct.unpack("<ii", msg_buffer[:8])

            if msgsize + 4 > len(msg_buffer):
                break

            if msgtype in self.serverclasses:
                msg = self.serverclasses[msgtype]()
                msg.parse_network_message(msg_buffer[8:msgsize + 4])
                msgs.append(msg)

            else:
                msgs.append("Server message type %(type)i size %(size)i contents %(msg_buffer)s unknown" %
                            {'type': msgtype, 'size': msgsize - 4, 'msg_buffer': msg_buffer[8:msgsize + 4].__repr__()})

            msg_buffer = msg_buffer[msgsize + 4:]

        return msgs, msg_buffer

    def process_file_input(self, conn, msg_buffer, conns):
        """ We have a "F" connection (filetransfer), peer has sent us
        something, this function retrieves messages
        from the msg_buffer, creates message objects and returns them
        and the rest of the msg_buffer.
        """
        msgs = []

        if conn.filereq is None:
            filereq, msg_buffer = self.parse_file_req(conn, msg_buffer)

            if filereq is not None:
                msgs.append(filereq)
                conn.filereq = filereq

        elif conn.filedown is not None:
            leftbytes = conn.bytestoread - conn.filereadbytes
            addedbytes = msg_buffer[:leftbytes]

            if leftbytes > 0:
                try:
                    conn.filedown.file.write(addedbytes)
                except IOError as strerror:
                    self._ui_callback([FileError(conn, conn.filedown.file, strerror)])
                    self._ui_callback([ConnClose(conn.conn, conn.addr)])
                    self.close_connection(conns, conn.conn)
                except ValueError:
                    pass

            addedbyteslen = len(addedbytes)
            curtime = time.time()

            """ Depending on the number of active downloads, the cooldown for UI callbacks
            can be up to 15 seconds per transfer. We use a bit of randomness to give the
            illusion that downloads are updated often. """
            finished = ((leftbytes - addedbyteslen) == 0)
            cooldown = max(1.0, min(self.total_downloads * uniform(0.8, 1.0), 15))

            if finished or (curtime - conn.lastcallback) > cooldown:

                """ We save resources by not sending data back to the UI every time
                a part of a file is downloaded """

                self._ui_callback([DownloadFile(conn.conn, addedbyteslen, conn.filedown.file)])
                conn.lastcallback = curtime

            if finished:
                self._ui_callback([ConnClose(conn.conn, conn.addr)])
                self.close_connection(conns, conn.conn)

            conn.filereadbytes += addedbyteslen
            msg_buffer = msg_buffer[leftbytes:]

        elif conn.fileupl is not None:
            if conn.fileupl.offset is None:
                offset, msg_buffer = self.parse_offset(msg_buffer)

                if offset is not None:
                    try:
                        conn.fileupl.file.seek(offset)
                    except IOError as strerror:
                        self._ui_callback([FileError(conn, conn.fileupl.file, strerror)])
                        self._ui_callback([ConnClose(conn.conn, conn.addr)])
                        self.close_connection(conns, conn.conn)
                    except ValueError:
                        pass

                    conn.fileupl.offset = offset
                    self._ui_callback([conn.fileupl])

        conn.ibuf = msg_buffer
        return msgs, conn

    def process_peer_input(self, conns, conn, msg_buffer):
        """ We have a "P" connection (p2p exchange), peer has sent us
        something, this function retrieves messages
        from the msg_buffer, creates message objects and returns them
        and the rest of the msg_buffer.
        """
        msgs = []

        while (conn.init is None or conn.init.conn_type not in ['F', 'D']) and len(msg_buffer) >= 8:
            msgsize = struct.unpack("<i", msg_buffer[:4])[0]

            if len(msg_buffer) >= 8:
                msgtype = struct.unpack("<i", msg_buffer[4:8])[0]
                self._ui_callback(
                    [PeerTransfer(conn, msgsize, len(msg_buffer) - 4, self.peerclasses.get(msgtype, None))])

            if msgsize + 4 > len(msg_buffer):
                break

            if conn.init is None:
                # Unpack Peer Connections
                if msg_buffer[4] == 0:
                    msg = PierceFireWall(conn)

                    try:
                        msg.parse_network_message(msg_buffer[5:msgsize + 4])
                    except Exception as error:
                        log.add("%s", error)
                    else:
                        conn.piercefw = msg
                        msgs.append(msg)

                elif msg_buffer[4] == 1:
                    msg = PeerInit(conn)

                    try:
                        msg.parse_network_message(msg_buffer[5:msgsize + 4])
                    except Exception as error:
                        log.add("%s", error)
                    else:
                        conn.init = msg
                        msgs.append(msg)

                elif conn.piercefw is None:
                    msgs.append(_(
                        "Unknown peer init code: {}, message contents ".format(msg_buffer[4])
                        + "{}".format(msg_buffer[5:msgsize + 4].__repr__())
                    ))

                    self._ui_callback([ConnClose(conn.conn, conn.addr)])
                    self.close_connection(conns, conn)
                    break

                else:
                    break

            elif conn.init.conn_type == 'P':
                # Unpack Peer Messages
                msgtype = struct.unpack("<i", msg_buffer[4:8])[0]

                if msgtype in self.peerclasses:
                    try:
                        msg = self.peerclasses[msgtype](conn)

                        # Parse Peer Message and handle exceptions
                        try:
                            msg.parse_network_message(msg_buffer[8:msgsize + 4])

                        except Exception as error:
                            host = port = "unknown"
                            msgname = str(self.peerclasses[msgtype]).split(".")[-1]
                            print("Error parsing %s:" % msgname, error)

                            import traceback
                            for line in traceback.format_tb(error.__traceback__):
                                print(line)

                            if "addr" in conn.__dict__:
                                if conn.addr is not None:
                                    host = conn.addr[0]
                                    port = conn.addr[1]

                            debugmessage = ("There was an error while unpacking Peer message type %(type)s size "
                                            "%(size)i contents %(msg_buffer)s from user: %(user)s, "
                                            "%(host)s:%(port)s") % {
                                'type': msgname, 'size': msgsize - 4,
                                'msg_buffer': msg_buffer[8:msgsize + 4].__repr__(), 'user': conn.init.user,
                                'host': host, 'port': port}
                            msgs.append(debugmessage)

                            del msg

                        else:
                            msgs.append(msg)

                    except Exception as error:
                        debugmessage = "Error in message function:", error, msgtype, conn
                        msgs.append(debugmessage)

                else:
                    host = port = "unknown"

                    if conn.init.conn is not None and conn.addr is not None:
                        host = conn.addr[0]
                        port = conn.addr[1]

                    debugmessage = ("Peer message type %(type)s size %(size)i contents %(msg_buffer)s unknown, "
                                    "from user: %(user)s, %(host)s:%(port)s") % {
                        'type': msgtype, 'size': msgsize - 4, 'msg_buffer': msg_buffer[8:msgsize + 4].__repr__(),
                        'user': conn.init.user, 'host': host, 'port': port}
                    msgs.append(debugmessage)

            else:
                # Unknown Message type
                msgs.append("Can't handle connection type %s" % (conn.init.conn_type))

            if msgsize >= 0:
                msg_buffer = msg_buffer[msgsize + 4:]
            else:
                msg_buffer = bytearray()

        conn.ibuf = msg_buffer
        return msgs, conn

    def process_distrib_input(self, conns, conn, msg_buffer):
        """ We have a distributed network connection, parent has sent us
        something, this function retrieves messages
        from the msg_buffer, creates message objects and returns them
        and the rest of the msg_buffer.
        """
        msgs = []

        while len(msg_buffer) >= 5:
            msgsize = struct.unpack("<i", msg_buffer[:4])[0]

            if msgsize + 4 > len(msg_buffer):
                break

            msgtype = msg_buffer[4]

            if msgtype in self.distribclasses:
                msg = self.distribclasses[msgtype](conn)
                msg.parse_network_message(msg_buffer[5:msgsize + 4])
                msgs.append(msg)

            else:
                msgs.append("Distrib message type %(type)i size %(size)i contents %(msg_buffer)s unknown" %
                            {'type': msgtype, 'size': msgsize - 1, 'msg_buffer': msg_buffer[5:msgsize + 4].__repr__()})
                self._ui_callback([ConnClose(conn.conn, conn.addr)])
                self.close_connection(conns, conn)
                break

            if msgsize >= 0:
                msg_buffer = msg_buffer[msgsize + 4:]
            else:
                msg_buffer = bytearray()

        conn.ibuf = msg_buffer
        return msgs, conn

    def _reset_counters(self, conns):
        curtime = time.time()

        for i in conns.values():
            if self._is_upload(i):
                i.starttime = curtime
                i.sentbytes2 = 0

            if self._is_download(i):
                i.starttime = curtime
                i.sentbytes2 = 0

    @staticmethod
    def set_server_socket_keepalive(server_socket, idle=10, interval=4, count=10):
        """ Ensure we are disconnected from the server in case of connectivity issues,
        by sending TCP keepalive pings. Assuming default values are used, once we reach
        10 seconds of idle time, we start sending keepalive pings once every 4 seconds.
        If 10 failed pings have been sent in a row (40 seconds), the connection is presumed
        dead. """

        if hasattr(socket, 'SO_KEEPALIVE'):
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)  # pylint: disable=maybe-no-member

        if hasattr(socket, 'TCP_KEEPINTVL'):
            server_socket.setsockopt(socket.IPPROTO_TCP,
                                     socket.TCP_KEEPINTVL, interval)  # pylint: disable=maybe-no-member

        if hasattr(socket, 'TCP_KEEPCNT'):
            server_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, count)  # pylint: disable=maybe-no-member

        if hasattr(socket, 'TCP_KEEPIDLE'):
            server_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, idle)  # pylint: disable=maybe-no-member

        elif hasattr(socket, 'TCP_KEEPALIVE'):
            # macOS fallback

            server_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPALIVE, idle)  # pylint: disable=maybe-no-member

        elif hasattr(socket, 'SIO_KEEPALIVE_VALS'):
            """ Windows fallback
            Probe count is set to 10 on a system level, and can't be modified.
            https://docs.microsoft.com/en-us/windows/win32/winsock/so-keepalive """

            server_socket.ioctl(
                socket.SIO_KEEPALIVE_VALS,  # pylint: disable=maybe-no-member
                (
                    1,
                    idle * 1000,
                    interval * 1000
                )
            )

    def process_queue(self, queue, conns, connsinprogress, server_socket, maxsockets=MAXSOCKETS):
        """ Processes messages sent by UI thread. server_socket is a server connection
        socket object, queue holds the messages, conns and connsinprogress
        are dictionaries holding Connection and PeerConnectionInProgress
        messages."""

        msg_list = []
        needsleep = False
        numsockets = 1 + len(conns) + len(connsinprogress)  # 1 = listen socket

        while queue:
            msg_list.append(queue.popleft())

        for msg_obj in msg_list:
            if issubclass(msg_obj.__class__, ServerMessage):
                try:
                    msg = msg_obj.make_network_message()

                    if server_socket in conns:
                        conns[server_socket].obuf.extend(
                            struct.pack("<ii", len(msg) + 4, self.servercodes[msg_obj.__class__]))
                        conns[server_socket].obuf.extend(msg)
                    else:
                        queue.append(msg_obj)
                        needsleep = True

                except Exception as error:
                    print("Error packaging message: %(type)s %(msg_obj)s, %(error)s" %
                          {'type': msg_obj.__class__, 'msg_obj': vars(msg_obj), 'error': str(error)})
                    self._ui_callback(["Error packaging message: %(type)s %(msg_obj)s, %(error)s" %
                                      {'type': msg_obj.__class__, 'msg_obj': vars(msg_obj), 'error': str(error)}])

            elif issubclass(msg_obj.__class__, PeerMessage):
                if msg_obj.conn in conns:

                    # Pack Peer and File and Search Messages
                    if msg_obj.__class__ is PierceFireWall:
                        conns[msg_obj.conn].piercefw = msg_obj

                        msg = msg_obj.make_network_message()

                        conns[msg_obj.conn].obuf.extend(struct.pack("<i", len(msg) + 1))
                        conns[msg_obj.conn].obuf.extend(bytes([0]))
                        conns[msg_obj.conn].obuf.extend(msg)

                    elif msg_obj.__class__ is PeerInit:
                        conns[msg_obj.conn].init = msg_obj
                        msg = msg_obj.make_network_message()

                        if conns[msg_obj.conn].piercefw is None:
                            conns[msg_obj.conn].obuf.extend(struct.pack("<i", len(msg) + 1))
                            conns[msg_obj.conn].obuf.extend(bytes([1]))
                            conns[msg_obj.conn].obuf.extend(msg)

                    elif msg_obj.__class__ is FileRequest:
                        conns[msg_obj.conn].filereq = msg_obj

                        msg = msg_obj.make_network_message()
                        conns[msg_obj.conn].obuf.extend(msg)

                        self._ui_callback([msg_obj])

                    else:
                        msg = msg_obj.make_network_message()
                        conns[msg_obj.conn].obuf.extend(
                            struct.pack("<ii", len(msg) + 4, self.peercodes[msg_obj.__class__]))
                        conns[msg_obj.conn].obuf.extend(msg)

                else:
                    if msg_obj.__class__ not in [PeerInit, PierceFireWall, FileSearchResult]:
                        log.add_conn("Can't send the message over the closed connection: %(type)s %(msg_obj)s", {
                            'type': msg_obj.__class__,
                            'msg_obj': vars(msg_obj)
                        })

            elif issubclass(msg_obj.__class__, InternalMessage):
                if msg_obj.__class__ is ServerConn:
                    if maxsockets == -1 or numsockets < maxsockets:
                        try:
                            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

                            # Detect if our connection to the server is still alive
                            self.set_server_socket_keepalive(server_socket)

                            if self._bindip:
                                server_socket.bind((self._bindip, 0))

                            server_socket.setblocking(0)
                            server_socket.connect_ex(msg_obj.addr)
                            server_socket.setblocking(1)

                            connsinprogress[server_socket] = PeerConnectionInProgress(server_socket, msg_obj)
                            self.selector.register(server_socket, selectors.EVENT_READ | selectors.EVENT_WRITE)

                            numsockets += 1

                        except socket.error as err:

                            self._ui_callback([ConnectError(msg_obj, err)])
                            server_socket.close()

                elif msg_obj.__class__ is ConnClose and msg_obj.conn in conns:
                    conn = msg_obj.conn

                    if msg_obj.callback:
                        self._ui_callback([ConnClose(conn, conns[conn].addr)])

                    self.close_connection(conns, conn)

                elif msg_obj.__class__ is OutConn:
                    if msg_obj.addr[1] == 0:
                        self._ui_callback([ConnectError(msg_obj, "Port cannot be zero")])

                    elif maxsockets == -1 or numsockets < maxsockets:
                        try:
                            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

                            if self._bindip:
                                conn.bind((self._bindip, 0))

                            conn.setblocking(0)
                            conn.connect_ex(msg_obj.addr)
                            conn.setblocking(1)

                            connsinprogress[conn] = PeerConnectionInProgress(conn, msg_obj)
                            self.selector.register(conn, selectors.EVENT_READ | selectors.EVENT_WRITE)

                            numsockets += 1

                        except socket.error as err:

                            self._ui_callback([ConnectError(msg_obj, err)])
                            conn.close()
                    else:
                        # Connection limit reached, re-queue
                        queue.append(msg_obj)

                elif msg_obj.__class__ is DownloadFile and msg_obj.conn in conns:
                    conns[msg_obj.conn].filedown = msg_obj

                    conns[msg_obj.conn].obuf.extend(struct.pack("<Q", msg_obj.offset))
                    conns[msg_obj.conn].obuf.extend(struct.pack("<i", 0))

                    conns[msg_obj.conn].bytestoread = msg_obj.filesize - msg_obj.offset

                    self._ui_callback([DownloadFile(msg_obj.conn, 0, msg_obj.file)])

                elif msg_obj.__class__ is UploadFile and msg_obj.conn in conns:
                    conns[msg_obj.conn].fileupl = msg_obj
                    self._reset_counters(conns)

                elif msg_obj.__class__ is SetUploadLimit:
                    if msg_obj.uselimit:
                        if msg_obj.limitby:
                            callback = self._calc_upload_limit_by_total
                        else:
                            callback = self._calc_upload_limit_by_transfer

                    else:
                        callback = self._calc_upload_limit_none

                    self._reset_counters(conns)
                    self._uploadlimit = (callback, msg_obj.limit)

                elif msg_obj.__class__ is SetDownloadLimit:
                    self._downloadlimit = (self._calc_download_limit_by_total, msg_obj.limit)

        if needsleep:
            time.sleep(1)

        return conns, connsinprogress, server_socket, numsockets

    def write_data(self, server_socket, conns, i):

        if i in self._ulimits:
            limit = self._ulimits[i]
        else:
            limit = None

        conn = conns[i]
        conn.lastactive = time.time()

        if conn.obuf:
            i.setblocking(0)

            if limit is None:
                bytes_send = i.send(conn.obuf)
            else:
                bytes_send = i.send(conn.obuf[:limit])

            i.setblocking(1)
            conn.obuf = conn.obuf[bytes_send:]
        else:
            bytes_send = 0

        if i is server_socket:
            return

        if conn.fileupl is not None and conn.fileupl.offset is not None:
            conn.fileupl.sentbytes += bytes_send
            conn.sentbytes2 += bytes_send

            totalsentbytes = conn.fileupl.offset + conn.fileupl.sentbytes + len(conn.obuf)

            try:
                size = conn.fileupl.size

                if totalsentbytes < size:
                    bytestoread = bytes_send * 2 - len(conn.obuf) + 10 * 4024

                    if bytestoread > 0:
                        read = conn.fileupl.file.read(bytestoread)
                        conn.obuf.extend(read)

            except IOError as strerror:
                self._ui_callback([FileError(conn, conn.fileupl.file, strerror)])
                self._ui_callback([ConnClose(i, conn.addr)])
                self.close_connection(conns, i)

            except ValueError:
                pass

            if bytes_send <= 0:
                return

            curtime = time.time()

            """ Depending on the number of active uploads, the cooldown for UI callbacks
            can be up to 15 seconds per transfer. We use a bit of randomness to give the
            illusion that uploads are updated often. """
            cooldown = max(1.0, min(self.total_uploads * uniform(0.8, 1.0), 15))

            if totalsentbytes == size or (curtime - conn.lastcallback) > cooldown:

                """ We save resources by not sending data back to the UI every time
                a part of a file is uploaded """

                self._ui_callback([conn.fileupl])
                conn.lastcallback = curtime

    def read_data(self, conns, i):
        # Check for a download limit
        if i in self._dlimits:
            limit = self._dlimits[i]
        else:
            limit = None

        conn = conns[i]

        conn.lastactive = time.time()

        if limit is None:
            # Unlimited download data
            data = i.recv(conn.lastreadlength)
            conn.ibuf.extend(data)

            if len(data) >= conn.lastreadlength // 2:
                conn.lastreadlength = conn.lastreadlength * 2

        else:
            # Speed Limited Download data (transfers)
            data = i.recv(conn.lastreadlength)
            conn.ibuf.extend(data)
            conn.lastreadlength = limit
            conn.readbytes2 += len(data)

        if not data and not conn.obuf:  # Make sure we don't have data to send on this connection
            self._ui_callback([ConnClose(i, conn.addr)])
            self.close_connection(conns, i)

    def run(self):
        """ Actual networking loop is here."""

        # @var p Peer / Listen Port
        listen_socket = self.listen_socket

        # @var s Server Port
        server_socket = self.server_socket

        conns = self._conns
        connsinprogress = self._connsinprogress
        queue = self._queue

        while not self._want_abort:

            if self._server_disconnect:
                # We're not connected to the server at the moment
                time.sleep(0.2)
                continue

            if queue:
                conns, connsinprogress, server_socket, numsockets = self.process_queue(
                    queue, conns, connsinprogress, server_socket)
                self.server_socket = server_socket

            self._ulimits = {}
            self._dlimits = {}

            try:
                for i in conns:
                    conn = conns[i]
                    event_masks = selectors.EVENT_READ

                    if (conn.obuf or (i is not server_socket
                                      and conn.fileupl is not None and conn.fileupl.offset is not None)):
                        event_masks |= selectors.EVENT_WRITE

                    try:
                        self.selector.modify(i, event_masks)

                    except KeyError:
                        self.selector.register(i, event_masks)

                timeout = -1
                key_events = self.selector.select(timeout)
                input_list = set(key.fileobj for key, event in key_events if event & selectors.EVENT_READ)
                output_list = set(key.fileobj for key, event in key_events if event & selectors.EVENT_WRITE)

            except OSError as error:
                if len(error.args) == 2 and error.args[0] == EINTR:
                    # Error recieved; but we don't care :)
                    time.sleep(0.2)
                    continue

                # Error recieved; terminate networking loop
                print(time.strftime("%H:%M:%S"), "select OSError:", error)
                self._want_abort = True

                log.add("Major Socket Error: Networking terminated! %s", str(error))

            except ValueError as error:
                # Possibly opened too many sockets
                print(time.strftime("%H:%M:%S"), "select ValueError:", error)
                time.sleep(0.2)
                continue

            # Update UI connection count
            curtime = time.time()

            if (curtime - self.last_conncount_ui_update) > self.CONNCOUNT_UI_INTERVAL:
                # Avoid sending too many updates to the UI at once, if there are a lot of connections

                self._ui_callback([SetCurrentConnectionCount(numsockets)])
                self.last_conncount_ui_update = curtime

            # Listen / Peer Port
            if listen_socket in input_list:
                try:
                    incconn, incaddr = listen_socket.accept()
                except Exception:
                    time.sleep(0.01)
                else:
                    if self._network_filter.is_ip_blocked(incaddr[0]):
                        log.add_conn(_("Ignoring connection request from blocked IP Address %(ip)s:%(port)s"), {
                            'ip': incaddr[0],
                            'port': incaddr[1]
                        })
                    else:
                        conns[incconn] = PeerConnection(conn=incconn, addr=incaddr)
                        self._ui_callback([IncConn(incconn, incaddr)])

            # Manage Connections
            curtime = time.time()

            for connection_in_progress in connsinprogress.copy():
                conn_obj = connsinprogress.get(connection_in_progress)

                if not conn_obj:
                    # Connection was removed, possibly disconnecting from the server
                    continue

                msg_obj = conn_obj.msg_obj

                if (curtime - conn_obj.lastactive) > self.IN_PROGRESS_STALE_AFTER:

                    self._ui_callback([ConnectError(msg_obj, "Timed out")])
                    self.close_connection(connsinprogress, connection_in_progress)
                    continue

                try:
                    if connection_in_progress in input_list:
                        # Check if the socket has any data for us
                        connection_in_progress.setblocking(0)
                        connection_in_progress.recv(1, socket.MSG_PEEK)
                        connection_in_progress.setblocking(1)

                except socket.error as err:

                    self._ui_callback([ConnectError(msg_obj, err)])
                    self.close_connection(connsinprogress, connection_in_progress)

                else:
                    if connection_in_progress in output_list:
                        addr = msg_obj.addr

                        if connection_in_progress is server_socket:
                            conns[server_socket] = Connection(conn=server_socket, addr=addr)

                            self._ui_callback([ServerConn(server_socket, addr)])

                        else:
                            conns[connection_in_progress] = PeerConnection(
                                conn=connection_in_progress, addr=addr, init=msg_obj.init)
                            self._ui_callback([OutConn(connection_in_progress, addr)])

                        del connsinprogress[connection_in_progress]

            # Process Data
            curtime = time.time()

            for connection in conns.copy():
                conn_obj = conns.get(connection)

                if not conn_obj:
                    # Connection was removed, possibly disconnecting from the server
                    continue

                if connection in output_list:
                    if self._is_upload(conn_obj):
                        limit = self._uploadlimit[0](conns)

                        if limit is not None:
                            limit = int(limit * 0.2)  # limit is per second, we loop 5 times a second

                        if limit is None or limit > 0:
                            self._ulimits[connection] = limit

                    try:
                        self.write_data(server_socket, conns, connection)

                    except socket.error as err:
                        self._ui_callback([ConnectError(conn_obj, err)])
                        self.close_connection(conns, connection)
                        continue

                if connection is not server_socket:
                    addr = conn_obj.addr

                    # Timeout Connections

                    if curtime - conn_obj.lastactive > self.CONNECTION_MAX_IDLE:
                        self._ui_callback([ConnClose(connection, addr)])
                        self.close_connection(conns, connection)
                        continue

                    if self._network_filter.is_ip_blocked(addr[0]):
                        log.add_conn("Blocking peer connection to IP: %(ip)s Port: %(port)s", {
                            "ip": addr[0],
                            "port": addr[1]
                        })
                        self.close_connection(conns, connection)
                        continue

                if connection in input_list:
                    if self._is_download(conn_obj):
                        limit = self._downloadlimit[0](conns)

                        if limit is not None:
                            limit = int(limit * 0.2)  # limit is per second, we loop 5 times a second

                        if limit is None or limit > 0:
                            self._dlimits[connection] = limit

                    try:
                        self.read_data(conns, connection)

                    except socket.error as err:
                        self._ui_callback([ConnectError(conn_obj, err)])
                        self.close_connection(conns, connection)
                        continue

                if conn_obj.ibuf:
                    if connection is server_socket:
                        msgs, conn_obj.ibuf = self.process_server_input(conn_obj.ibuf)
                        self._ui_callback(msgs)

                    else:
                        if conn_obj.init is None or conn_obj.init.conn_type not in ['F', 'D']:
                            msgs, conn_obj = self.process_peer_input(conns, conn_obj, conn_obj.ibuf)
                            self._ui_callback(msgs)

                        if conn_obj.init is not None and conn_obj.init.conn_type == 'F':
                            msgs, conn_obj = self.process_file_input(conn_obj, conn_obj.ibuf, conns)
                            self._ui_callback(msgs)

                        if conn_obj.init is not None and conn_obj.init.conn_type == 'D':
                            msgs, conn_obj = self.process_distrib_input(conns, conn_obj, conn_obj.ibuf)
                            self._ui_callback(msgs)

            # Don't exhaust the CPU
            time.sleep(0.2)

        # Networking thread aborted

    def server_connect(self):
        """ We've connected to the server """
        self._server_disconnect = False

    def server_disconnect(self):
        """ We've disconnected from the server, clean up """

        self._server_disconnect = True
        self.server_socket = None

        for i in self._conns.copy():
            self.close_connection(self._conns, i)

        for i in self._connsinprogress.copy():
            self.close_connection(self._conns, i)

        while self._queue:
            self._queue.popleft()

        if not self._want_abort:
            self._ui_callback([SetCurrentConnectionCount(0)])

    def abort(self):
        """ Call this to abort the thread """
        self._want_abort = True
        self.server_disconnect()
