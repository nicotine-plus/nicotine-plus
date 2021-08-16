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
from pynicotine.slskmessages import DistribMessage
from pynicotine.slskmessages import DistribSearch
from pynicotine.slskmessages import DownloadFile
from pynicotine.slskmessages import EmbeddedMessage
from pynicotine.slskmessages import ExactFileSearch
from pynicotine.slskmessages import FileError
from pynicotine.slskmessages import FileMessage
from pynicotine.slskmessages import FileOffset
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
from pynicotine.slskmessages import ItemRecommendations
from pynicotine.slskmessages import ItemSimilarUsers
from pynicotine.slskmessages import JoinPublicRoom
from pynicotine.slskmessages import JoinRoom
from pynicotine.slskmessages import LeavePublicRoom
from pynicotine.slskmessages import LeaveRoom
from pynicotine.slskmessages import Login
from pynicotine.slskmessages import MessageAcked
from pynicotine.slskmessages import MessageUser
from pynicotine.slskmessages import MessageUsers
from pynicotine.slskmessages import MinParentsInCache
from pynicotine.slskmessages import PossibleParents
from pynicotine.slskmessages import NotifyPrivileges
from pynicotine.slskmessages import ParentInactivityTimeout
from pynicotine.slskmessages import ParentMinSpeed
from pynicotine.slskmessages import ParentSpeedRatio
from pynicotine.slskmessages import PeerConn
from pynicotine.slskmessages import PeerInit
from pynicotine.slskmessages import PeerInitMessage
from pynicotine.slskmessages import PeerMessage
from pynicotine.slskmessages import PeerTransfer
from pynicotine.slskmessages import PierceFireWall
from pynicotine.slskmessages import PlaceholdUpload
from pynicotine.slskmessages import PlaceInLineResponse
from pynicotine.slskmessages import PlaceInQueue
from pynicotine.slskmessages import PlaceInQueueRequest
from pynicotine.slskmessages import PMessageUser
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

    except Exception as rlimit_error:
        log.add("Failed to set RLIMIT_NOFILE: %s", rlimit_error)

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
                 "lastcallback")

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
    It sends data to the NicotineCore via a callback function and receives
    data via a deque object. """

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
        MessageUsers: 149,
        JoinPublicRoom: 150,
        LeavePublicRoom: 151,
        PublicRoomMessage: 152,
        RelatedSearch: 153,           # Deprecated
        CantConnectToPeer: 1001,      # Deprecated
        CantCreateRoom: 1003
    }

    peerinitcodes = {
        PierceFireWall: 0,
        PeerInit: 1
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

    distribcodes = {
        DistribAlive: 0,
        DistribSearch: 3,
        DistribBranchLevel: 4,
        DistribBranchRoot: 5,
        DistribChildDepth: 7,
        DistribEmbeddedMessage: 93
    }

    IN_PROGRESS_STALE_AFTER = 2
    CONNECTION_MAX_IDLE = 60
    CONNCOUNT_CALLBACK_INTERVAL = 0.5

    def __init__(self, core_callback, queue, bindip, interface, port, port_range, network_filter, eventprocessor):
        """ core_callback is a NicotineCore callback function to be called with messages
        list as a parameter. queue is deque object that holds network messages from
        NicotineCore. """

        threading.Thread.__init__(self)

        self.name = "NetworkThread"

        if sys.platform not in ("linux", "darwin"):
            # TODO: support custom network interface for other systems than Linux and macOS
            interface = None

        self._core_callback = core_callback
        self._queue = queue
        self._want_abort = False
        self.server_disconnected = True
        self.bindip = bindip
        self.listenport = None
        self.portrange = (port, port) if port else port_range
        self.interface = interface
        self._network_filter = network_filter
        self._eventprocessor = eventprocessor

        self.serverclasses = {}
        for code_class, code_id in self.servercodes.items():
            self.serverclasses[code_id] = code_class

        self.peerinitclasses = {}
        for code_class, code_id in self.peerinitcodes.items():
            self.peerinitclasses[code_id] = code_class

        self.peerclasses = {}
        for code_class, code_id in self.peercodes.items():
            self.peerclasses[code_id] = code_class

        self.distribclasses = {}
        for code_class, code_id in self.distribcodes.items():
            self.distribclasses[code_id] = code_class

        # Select Networking Input and Output sockets
        self.selector = selectors.DefaultSelector()

        self.listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.server_socket = None
        self._numsockets = 1

        self._conns = {}
        self._connsinprogress = {}
        self._uploadlimit = (self._calc_upload_limit_none, 0)
        self._downloadlimit = (self._calc_download_limit, 0)
        self._ulimits = {}
        self._dlimits = {}
        self.total_uploads = 0
        self.total_downloads = 0
        self.last_conncount_callback = time.time()
        self.last_cycle_time = time.time()
        self.current_cycle_loop_count = 0
        self.last_cycle_loop_count = 0
        self.loops_per_second = 0

        self.bind_listen_port()

        self.daemon = True
        self.start()

    """ General """

    def validate_listen_port(self):

        if self.listenport is not None:
            return True

        return False

    def validate_network_interface(self):

        try:
            if self.interface and self.interface not in (name for _i, name in socket.if_nameindex()):
                return False

        except AttributeError:
            pass

        return True

    @staticmethod
    def bind_to_network_interface(sock, if_name):

        if sys.platform == "linux":
            sock.setsockopt(socket.SOL_SOCKET, 25, if_name.encode())

        if sys.platform == "darwin":
            sock.setsockopt(socket.IPPROTO_IP, 25, socket.if_nametoindex(if_name))

    def bind_listen_port(self):

        if not self.validate_network_interface():
            return

        ip_address = self.bindip or ''

        if self.interface:
            self.bind_to_network_interface(self.listen_socket, self.interface)
            ip_address = ''

        for listenport in range(int(self.portrange[0]), int(self.portrange[1]) + 1):
            try:
                self.listen_socket.bind((ip_address, listenport))
                self.listen_socket.listen()
                self._core_callback([IncPort(listenport)])
                self.listenport = listenport
                break

            except socket.error:
                continue

    def server_connect(self):
        """ We've connected to the server """
        self.server_disconnected = False

    def server_disconnect(self):
        """ We've disconnected from the server, clean up """

        self.server_disconnected = True
        self.server_socket = None

        for connection in self._conns.copy():
            self.close_connection(self._conns, connection)

        for connection in self._connsinprogress.copy():
            self.close_connection(self._connsinprogress, connection)

        self._queue.clear()

        if not self._want_abort:
            self._core_callback([SetCurrentConnectionCount(0)])

    def abort(self):
        """ Call this to abort the thread """
        self._want_abort = True
        self.server_disconnect()

    """ File Transfers """

    @staticmethod
    def _is_upload(conn):
        return conn.__class__ is PeerConnection and conn.fileupl is not None

    @staticmethod
    def _is_download(conn):
        return conn.__class__ is PeerConnection and conn.filedown is not None

    def _calc_upload_limit(self, limit_disabled=False, limit_per_transfer=False):

        limit = self._uploadlimit[1] * 1024.0
        self.total_uploads = sum(1 for connection in self._conns.values() if self._is_upload(connection))

        if limit_disabled:
            return 0

        if not limit_per_transfer and self.total_uploads > 1:
            limit = limit / self.total_uploads

        return int(max(1024, limit))  # 1 KB/s is the minimum upload speed per transfer

    def _calc_upload_limit_by_transfer(self):
        return self._calc_upload_limit(limit_per_transfer=True)

    def _calc_upload_limit_none(self):
        return self._calc_upload_limit(limit_disabled=True)

    def _calc_download_limit(self):

        limit = self._downloadlimit[1] * 1024.0
        self.total_downloads = sum(1 for connection in self._conns.values() if self._is_download(connection))

        if limit == 0:
            # Download limit disabled
            return limit

        if self.total_downloads > 1:
            limit = limit / self.total_downloads

        return int(max(1024, limit))  # 1 KB/s is the minimum download speed per transfer

    def _calc_loops_per_second(self):
        """ Calculate number of loops per second. This value is used to split the
        per-second transfer speed limit evenly for each loop. """

        curtime = time.time()

        if curtime - self.last_cycle_time >= 1:
            self.loops_per_second = (self.last_cycle_loop_count + self.current_cycle_loop_count) // 2

            self.last_cycle_loop_count = self.current_cycle_loop_count
            self.last_cycle_time = curtime
            self.current_cycle_loop_count = 0
        else:
            self.current_cycle_loop_count = self.current_cycle_loop_count + 1

    def set_conn_speed_limit(self, connection, limit_callback, limits):

        limit = limit_callback() // max(1, self.loops_per_second)

        if limit > 0:
            limits[connection] = limit

    """ Connections """

    def socket_still_active(self, conn):

        try:
            connection = self._conns[conn]

        except KeyError:
            return False

        return len(connection.obuf) > 0 or len(connection.ibuf) > 0

    @staticmethod
    def pack_network_message(msg_obj):

        try:
            return msg_obj.make_network_message()

        except Exception:
            from traceback import format_exc
            log.add(("Unable to pack message type %(msg_type)s. %(error)s"),
                    {'msg_type': msg_obj.__class__, 'error': format_exc()})

        return None

    @staticmethod
    def unpack_network_message(msg_class, msg_buffer, msg_size, conn_type, conn=None):

        try:
            if conn is not None:
                msg = msg_class(conn)
            else:
                msg = msg_class()

            msg.parse_network_message(msg_buffer)
            return msg

        except Exception as error:
            log.add(("Unable to parse %(conn_type)s message type %(msg_type)s size %(size)i "
                    "contents %(msg_buffer)s: %(error)s"),
                    {'conn_type': conn_type, 'msg_type': msg_class, 'size': msg_size,
                     'msg_buffer': msg_buffer, 'error': error})

        return None

    def close_connection(self, connection_list, connection):

        if connection not in connection_list:
            # Already removed
            return

        self.selector.unregister(connection)
        connection.close()
        del connection_list[connection]
        self._numsockets -= 1

        if connection is self.server_socket:
            # Disconnected from server, clean up connections and queue
            self.server_disconnect()

    """ Server Connection """

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

    def init_server_conn(self, msg_obj):

        try:
            self.server_socket = server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            # Detect if our connection to the server is still alive
            self.set_server_socket_keepalive(server_socket)

            if self.interface:
                self.bind_to_network_interface(server_socket, self.interface)

            elif self.bindip:
                server_socket.bind((self.bindip, 0))

            server_socket.setblocking(0)
            server_socket.connect_ex(msg_obj.addr)
            server_socket.setblocking(1)

            self.selector.register(server_socket, selectors.EVENT_READ | selectors.EVENT_WRITE)
            self._connsinprogress[server_socket] = PeerConnectionInProgress(server_socket, msg_obj)
            self._numsockets += 1

        except socket.error as err:
            self._core_callback([ConnectError(msg_obj, err)])
            server_socket.close()
            self.server_disconnect()

    def process_server_input(self, msg_buffer):
        """ Server has sent us something, this function retrieves messages
        from the msg_buffer, creates message objects and returns them and the rest
        of the msg_buffer.
        """
        msgs = []

        # Server messages are 8 bytes or greater in length
        while len(msg_buffer) >= 8:
            msgsize, msgtype = struct.unpack("<II", msg_buffer[:8])

            if msgsize < 0 or msgsize + 4 > len(msg_buffer):
                # Invalid message size or buffer is being filled
                break

            # Unpack server messages
            if msgtype in self.serverclasses:
                msg = self.unpack_network_message(
                    self.serverclasses[msgtype], msg_buffer[8:msgsize + 4], msgsize - 4, "server")

                if msg is not None:
                    msgs.append(msg)

            else:
                log.add("Server message type %(type)i size %(size)i contents %(msg_buffer)s unknown",
                        {'type': msgtype, 'size': msgsize - 4, 'msg_buffer': msg_buffer[8:msgsize + 4]})

            msg_buffer = msg_buffer[msgsize + 4:]

        return msgs, msg_buffer

    def process_server_output(self, msg_obj):

        if self.server_socket not in self._conns:
            log.add_conn("Can't send the message over the closed connection: %(type)s %(msg_obj)s", {
                'type': msg_obj.__class__,
                'msg_obj': vars(msg_obj)
            })
            return

        msg = self.pack_network_message(msg_obj)

        if msg is None:
            return

        conn_obj = self._conns[self.server_socket]
        conn_obj.obuf.extend(struct.pack("<I", len(msg) + 4))
        conn_obj.obuf.extend(struct.pack("<I", self.servercodes[msg_obj.__class__]))
        conn_obj.obuf.extend(msg)

    """ Peer Init """

    def process_peer_init_input(self, conn, msg_buffer):

        msgs = []

        # Peer init messages are 8 bytes or greater in length
        while conn.init is None and len(msg_buffer) >= 8:
            msgsize = struct.unpack("<I", msg_buffer[:4])[0]

            if msgsize < 0 or msgsize + 4 > len(msg_buffer):
                # Invalid message size or buffer is being filled
                break

            msgtype = msg_buffer[4]

            # Unpack peer init messages
            if msgtype in self.peerinitclasses:
                msg = self.unpack_network_message(
                    self.peerinitclasses[msgtype], msg_buffer[5:msgsize + 4], msgsize - 1, "peer init", conn)

                if msg is not None:
                    if self.peerinitclasses[msgtype] is PierceFireWall:
                        conn.piercefw = msg

                    elif self.peerinitclasses[msgtype] is PeerInit:
                        conn.init = msg

                    msgs.append(msg)

            else:
                if conn.piercefw is None:
                    log.add("Peer init message type %(type)i size %(size)i contents %(msg_buffer)s unknown",
                            {'type': msgtype, 'size': msgsize - 1, 'msg_buffer': msg_buffer[5:msgsize + 4]})

                    self._core_callback([ConnClose(conn.conn, conn.addr)])
                    self.close_connection(self._conns, conn)

                break

            msg_buffer = msg_buffer[msgsize + 4:]

        conn.ibuf = msg_buffer
        return msgs

    def process_peer_init_output(self, msg_obj):

        if msg_obj.conn not in self._conns:
            log.add_conn("Can't send the message over the closed connection: %(type)s %(msg_obj)s", {
                'type': msg_obj.__class__,
                'msg_obj': vars(msg_obj)
            })
            return

        # Pack peer init messages
        if msg_obj.__class__ is PierceFireWall:
            conn_obj = self._conns[msg_obj.conn]
            msg = self.pack_network_message(msg_obj)

            if msg is None:
                return

            conn_obj.piercefw = msg_obj

            conn_obj.obuf.extend(struct.pack("<I", len(msg) + 1))
            conn_obj.obuf.extend(bytes([self.peerinitcodes[msg_obj.__class__]]))
            conn_obj.obuf.extend(msg)

        elif msg_obj.__class__ is PeerInit:
            conn_obj = self._conns[msg_obj.conn]
            msg = self.pack_network_message(msg_obj)

            if msg is None:
                return

            conn_obj.init = msg_obj

            if conn_obj.piercefw is None:
                conn_obj.obuf.extend(struct.pack("<I", len(msg) + 1))
                conn_obj.obuf.extend(bytes([self.peerinitcodes[msg_obj.__class__]]))
                conn_obj.obuf.extend(msg)

    """ Peer Connection """

    def init_peer_conn(self, msg_obj):

        try:
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            if self.interface:
                self.bind_to_network_interface(conn, self.interface)

            elif self.bindip:
                conn.bind((self.bindip, 0))

            conn.setblocking(0)
            conn.connect_ex(msg_obj.addr)
            conn.setblocking(1)

            self.selector.register(conn, selectors.EVENT_READ | selectors.EVENT_WRITE)
            self._connsinprogress[conn] = PeerConnectionInProgress(conn, msg_obj)
            self._numsockets += 1

        except socket.error as err:
            self._core_callback([ConnectError(msg_obj, err)])
            conn.close()

    def process_peer_input(self, conn, msg_buffer):
        """ We have a "P" connection (p2p exchange), peer has sent us
        something, this function retrieves messages
        from the msg_buffer, creates message objects and returns them
        and the rest of the msg_buffer.
        """
        msgs = []
        search_result_received = False

        # Peer messages are 8 bytes or greater in length
        while len(msg_buffer) >= 8:
            msgsize, msgtype = struct.unpack("<II", msg_buffer[:8])
            peer_class = self.peerclasses.get(msgtype, None)

            if peer_class and peer_class in (SharedFileList, UserInfoReply):
                # Send progress to the main thread
                self._core_callback(
                    [PeerTransfer(conn, msgsize, len(msg_buffer) - 4, peer_class)])

            if msgsize < 0 or msgsize + 4 > len(msg_buffer):
                # Invalid message size or buffer is being filled
                break

            # Unpack peer messages
            if msgtype in self.peerclasses:
                msg = self.unpack_network_message(
                    self.peerclasses[msgtype], msg_buffer[8:msgsize + 4], msgsize - 4, "peer", conn)

                if msg.__class__ is FileSearchResult:
                    search_result_received = True

                if msg is not None:
                    msgs.append(msg)

            else:
                host = port = "unknown"

                if conn.init.conn is not None and conn.addr is not None:
                    host = conn.addr[0]
                    port = conn.addr[1]

                log.add(("Peer message type %(type)s size %(size)i contents %(msg_buffer)s unknown, "
                         "from user: %(user)s, %(host)s:%(port)s"),
                        {'type': msgtype, 'size': msgsize - 4, 'msg_buffer': msg_buffer[8:msgsize + 4],
                         'user': conn.init.target_user, 'host': host, 'port': port})

            msg_buffer = msg_buffer[msgsize + 4:]

        conn.ibuf = msg_buffer

        if search_result_received and not self.socket_still_active(conn.conn):
            # Forcibly close peer connection. Only used after receiving a search result,
            # as we need to get rid of peer connections before they pile up.

            self._core_callback([ConnClose(conn.conn, conn.addr)])
            self.close_connection(self._conns, conn.conn)

        return msgs

    def process_peer_output(self, msg_obj):

        if msg_obj.conn not in self._conns:
            log.add_conn("Can't send the message over the closed connection: %(type)s %(msg_obj)s", {
                'type': msg_obj.__class__,
                'msg_obj': vars(msg_obj)
            })
            return

        # Pack peer messages
        msg = self.pack_network_message(msg_obj)

        if msg is None:
            return

        conn_obj = self._conns[msg_obj.conn]
        conn_obj.obuf.extend(struct.pack("<I", len(msg) + 4))
        conn_obj.obuf.extend(struct.pack("<I", self.peercodes[msg_obj.__class__]))
        conn_obj.obuf.extend(msg)

    """ File Connection """

    def process_file_input(self, conn, msg_buffer):
        """ We have a "F" connection (filetransfer), peer has sent us
        something, this function retrieves messages
        from the msg_buffer, creates message objects and returns them
        and the rest of the msg_buffer.
        """
        msgs = []

        if conn.filereq is None:
            msgsize = 4
            msg = self.unpack_network_message(FileRequest, msg_buffer[:msgsize], msgsize, "file", conn.conn)

            if msg is not None and msg.req is not None:
                msgs.append(msg)
                conn.filereq = msg

            msg_buffer = msg_buffer[msgsize:]

        elif conn.filedown is not None:
            leftbytes = conn.bytestoread - conn.filereadbytes
            addedbytes = msg_buffer[:leftbytes]

            if leftbytes > 0:
                try:
                    conn.filedown.file.write(addedbytes)

                except IOError as strerror:
                    self._core_callback([FileError(conn, conn.filedown.file, strerror)])
                    self._core_callback([ConnClose(conn.conn, conn.addr)])
                    self.close_connection(self._conns, conn.conn)

                except ValueError:
                    pass

            addedbyteslen = len(addedbytes)

            curtime = time.time()

            """ Depending on the number of active downloads, the cooldown for callbacks
            can be up to 15 seconds per transfer. We use a bit of randomness to give the
            illusion that downloads are updated often. """

            finished = ((leftbytes - addedbyteslen) == 0)
            cooldown = max(1.0, min(self.total_downloads * uniform(0.8, 1.0), 15))

            if finished or (curtime - conn.lastcallback) > cooldown:

                """ We save resources by not sending data back to the NicotineCore
                every time a part of a file is downloaded """

                self._core_callback([DownloadFile(conn.conn, conn.filedown.file)])
                conn.lastcallback = curtime

            if finished:
                self._core_callback([ConnClose(conn.conn, conn.addr)])
                self.close_connection(self._conns, conn.conn)

            conn.filereadbytes += addedbyteslen
            msg_buffer = msg_buffer[leftbytes:]

        elif conn.fileupl is not None and conn.fileupl.offset is None:
            msgsize = 8
            msg = self.unpack_network_message(FileOffset, msg_buffer[:msgsize], msgsize, "file", conn)

            if msg is not None and msg.offset is not None:
                try:
                    conn.fileupl.file.seek(msg.offset)

                except IOError as strerror:
                    self._core_callback([FileError(conn, conn.fileupl.file, strerror)])
                    self._core_callback([ConnClose(conn.conn, conn.addr)])
                    self.close_connection(self._conns, conn.conn)

                except ValueError:
                    pass

                conn.fileupl.offset = msg.offset
                self._core_callback([conn.fileupl])

            msg_buffer = msg_buffer[msgsize:]

        conn.ibuf = msg_buffer
        return msgs

    def process_file_output(self, msg_obj):

        if msg_obj.conn not in self._conns:
            log.add_conn("Can't send the message over the closed connection: %(type)s %(msg_obj)s", {
                'type': msg_obj.__class__,
                'msg_obj': vars(msg_obj)
            })
            return

        # Pack file messages
        if msg_obj.__class__ is FileRequest:
            msg = self.pack_network_message(msg_obj)

            if msg is None:
                return

            conn_obj = self._conns[msg_obj.conn]
            conn_obj.filereq = msg_obj
            conn_obj.obuf.extend(msg)

            self._core_callback([msg_obj])

        elif msg_obj.__class__ is FileOffset:
            msg = self.pack_network_message(msg_obj)

            if msg is None:
                return

            conn_obj = self._conns[msg_obj.conn]
            conn_obj.bytestoread = msg_obj.filesize - msg_obj.offset
            conn_obj.obuf.extend(msg)

    """ Distributed Connection """

    def process_distrib_input(self, conn, msg_buffer):
        """ We have a distributed network connection, parent has sent us
        something, this function retrieves messages
        from the msg_buffer, creates message objects and returns them
        and the rest of the msg_buffer.
        """
        msgs = []

        # Distributed messages are 5 bytes or greater in length
        while len(msg_buffer) >= 5:
            msgsize = struct.unpack("<I", msg_buffer[:4])[0]

            if msgsize < 0 or msgsize + 4 > len(msg_buffer):
                # Invalid message size or buffer is being filled
                break

            msgtype = msg_buffer[4]

            # Unpack distributed messages
            if msgtype in self.distribclasses:
                msg = self.unpack_network_message(
                    self.distribclasses[msgtype], msg_buffer[5:msgsize + 4], msgsize - 1, "distrib", conn)

                if msg is not None:
                    msgs.append(msg)

            else:
                log.add("Distrib message type %(type)i size %(size)i contents %(msg_buffer)s unknown",
                        {'type': msgtype, 'size': msgsize - 1, 'msg_buffer': msg_buffer[5:msgsize + 4]})
                self._core_callback([ConnClose(conn.conn, conn.addr)])
                self.close_connection(self._conns, conn)
                break

            msg_buffer = msg_buffer[msgsize + 4:]

        conn.ibuf = msg_buffer
        return msgs

    def process_distrib_output(self, msg_obj):

        if msg_obj.conn not in self._conns:
            log.add_conn("Can't send the message over the closed connection: %(type)s %(msg_obj)s", {
                'type': msg_obj.__class__,
                'msg_obj': vars(msg_obj)
            })
            return

        # Pack distributed messages
        msg = self.pack_network_message(msg_obj)

        if msg is None:
            return

        conn_obj = self._conns[msg_obj.conn]
        conn_obj.obuf.extend(struct.pack("<I", len(msg) + 1))
        conn_obj.obuf.extend(bytes([self.distribcodes[msg_obj.__class__]]))
        conn_obj.obuf.extend(msg)

    """ Connection I/O """

    def process_conn_input(self, connection, conn_obj):

        if connection is self.server_socket:
            msgs, conn_obj.ibuf = self.process_server_input(conn_obj.ibuf)
            self._core_callback(msgs)

        elif conn_obj.init is None:
            msgs = self.process_peer_init_input(conn_obj, conn_obj.ibuf)
            self._core_callback(msgs)

        elif conn_obj.init is not None and conn_obj.init.conn_type == 'P':
            msgs = self.process_peer_input(conn_obj, conn_obj.ibuf)
            self._core_callback(msgs)

        elif conn_obj.init is not None and conn_obj.init.conn_type == 'F':
            msgs = self.process_file_input(conn_obj, conn_obj.ibuf)
            self._core_callback(msgs)

        elif conn_obj.init is not None and conn_obj.init.conn_type == 'D':
            msgs = self.process_distrib_input(conn_obj, conn_obj.ibuf)
            self._core_callback(msgs)

        else:
            # Unknown message type
            log.add("Can't handle connection type %s", conn_obj.init.conn_type)

    def process_conn_output(self):
        """ Processes messages sent by the main thread. queue holds the messages,
        conns and connsinprogress are dictionaries holding Connection and
        PeerConnectionInProgress messages. """

        msg_list = self._queue.copy()
        self._queue.clear()

        for msg_obj in msg_list:
            if self.server_disconnected:
                # Disconnected from server, stop processing queue
                return

            msg_class = msg_obj.__class__

            if issubclass(msg_class, PeerInitMessage):
                self.process_peer_init_output(msg_obj)

            elif issubclass(msg_class, PeerMessage):
                self.process_peer_output(msg_obj)

            elif msg_class is PeerConn:
                if self._numsockets < MAXSOCKETS:
                    self.init_peer_conn(msg_obj)
                else:
                    # Connection limit reached, re-queue
                    self._queue.append(msg_obj)

            elif issubclass(msg_class, DistribMessage):
                self.process_distrib_output(msg_obj)

            elif issubclass(msg_class, FileMessage):
                self.process_file_output(msg_obj)

            elif issubclass(msg_class, ServerMessage):
                self.process_server_output(msg_obj)

            elif msg_class is ConnClose and msg_obj.conn in self._conns:
                conn = msg_obj.conn

                self._core_callback([ConnClose(conn, self._conns[conn].addr)])
                self.close_connection(self._conns, conn)

            elif msg_class is ServerConn:
                if self._numsockets < MAXSOCKETS:
                    self.init_server_conn(msg_obj)

            elif msg_class is DownloadFile and msg_obj.conn in self._conns:
                self._conns[msg_obj.conn].filedown = msg_obj

            elif msg_class is UploadFile and msg_obj.conn in self._conns:
                self._conns[msg_obj.conn].fileupl = msg_obj

            elif msg_class is SetDownloadLimit:
                self._downloadlimit = (self._calc_download_limit, msg_obj.limit)

            elif msg_class is SetUploadLimit:
                if msg_obj.uselimit:
                    if msg_obj.limitby:
                        callback = self._calc_upload_limit
                    else:
                        callback = self._calc_upload_limit_by_transfer

                else:
                    callback = self._calc_upload_limit_none

                self._uploadlimit = (callback, msg_obj.limit)

    def read_data(self, conn_obj):

        connection = conn_obj.conn

        # Check for a download limit
        if connection in self._dlimits:
            limit = self._dlimits[connection]
        else:
            limit = None

        conn_obj.lastactive = time.time()
        data = connection.recv(conn_obj.lastreadlength)
        conn_obj.ibuf.extend(data)

        if limit is None:
            # Unlimited download data
            if len(data) >= conn_obj.lastreadlength // 2:
                conn_obj.lastreadlength = conn_obj.lastreadlength * 2

        else:
            # Speed Limited Download data (transfers)
            conn_obj.lastreadlength = limit

        if not data:
            return False

        return True

    def write_data(self, conn_obj):

        connection = conn_obj.conn

        if connection in self._ulimits:
            limit = self._ulimits[connection]
        else:
            limit = None

        conn_obj.lastactive = time.time()

        if conn_obj.obuf:
            connection.setblocking(0)

            if limit is None:
                bytes_send = connection.send(conn_obj.obuf)
            else:
                bytes_send = connection.send(conn_obj.obuf[:limit])

            connection.setblocking(1)
            conn_obj.obuf = conn_obj.obuf[bytes_send:]
        else:
            bytes_send = 0

        if connection is self.server_socket:
            return

        if conn_obj.fileupl is not None and conn_obj.fileupl.offset is not None:
            conn_obj.fileupl.sentbytes += bytes_send

            totalsentbytes = conn_obj.fileupl.offset + conn_obj.fileupl.sentbytes + len(conn_obj.obuf)

            try:
                size = conn_obj.fileupl.size

                if totalsentbytes < size:
                    bytestoread = bytes_send * 2 - len(conn_obj.obuf) + 10 * 4024

                    if bytestoread > 0:
                        read = conn_obj.fileupl.file.read(bytestoread)
                        conn_obj.obuf.extend(read)

            except IOError as strerror:
                self._core_callback([FileError(conn_obj, conn_obj.fileupl.file, strerror)])
                self._core_callback([ConnClose(connection, conn_obj.addr)])
                self.close_connection(self._conns, connection)

            except ValueError:
                pass

            if bytes_send <= 0:
                return

            curtime = time.time()

            """ Depending on the number of active uploads, the cooldown for callbacks
            can be up to 15 seconds per transfer. We use a bit of randomness to give the
            illusion that uploads are updated often. """

            finished = (conn_obj.fileupl.offset + conn_obj.fileupl.sentbytes == size)
            cooldown = max(1.0, min(self.total_uploads * uniform(0.8, 1.0), 15))

            if finished or (curtime - conn_obj.lastcallback) > cooldown:

                """ We save resources by not sending data back to the NicotineCore
                every time a part of a file is uploaded """

                self._core_callback([conn_obj.fileupl])
                conn_obj.lastcallback = curtime

    """ Networking Loop """

    def run(self):

        # Listen socket needs to be registered for selection here instead of __init__,
        # otherwise connections break on certain systems (OpenBSD confirmed)
        self.selector.register(self.listen_socket, selectors.EVENT_READ)

        while not self._want_abort:

            if self.server_disconnected:
                # We're not connected to the server at the moment
                time.sleep(0.1)
                continue

            self._ulimits = {}
            self._dlimits = {}
            self._calc_loops_per_second()

            curtime = time.time()

            # Send updated connection count to NicotineCore. Avoid sending too many
            # updates at once,if there are a lot of connections
            if (curtime - self.last_conncount_callback) > self.CONNCOUNT_CALLBACK_INTERVAL:
                self._core_callback([SetCurrentConnectionCount(self._numsockets)])
                self.last_conncount_callback = curtime

            if self._queue:
                self.process_conn_output()

            try:
                for connection, conn_obj in self._conns.items():
                    event_masks = selectors.EVENT_READ

                    if (conn_obj.obuf or (connection is not self.server_socket
                                          and conn_obj.fileupl is not None and conn_obj.fileupl.offset is not None)):
                        event_masks |= selectors.EVENT_WRITE

                    self.selector.modify(connection, event_masks)

                key_events = self.selector.select(timeout=-1)
                input_list = set(key.fileobj for key, event in key_events if event & selectors.EVENT_READ)
                output_list = set(key.fileobj for key, event in key_events if event & selectors.EVENT_WRITE)

            except OSError as error:
                # Error recieved; terminate networking loop

                self._want_abort = True
                log.add("Major Socket Error: Networking terminated! %s", error)

            except ValueError as error:
                # Possibly opened too many sockets

                log.add("select ValueError: %s", error)
                time.sleep(0.1)
                continue

            # Listen / Peer Port
            if self._numsockets < MAXSOCKETS and not self.server_disconnected and self.listen_socket in input_list:
                try:
                    incconn, incaddr = self.listen_socket.accept()
                except Exception:
                    time.sleep(0.01)
                else:
                    if self._network_filter.is_ip_blocked(incaddr[0]):
                        log.add_conn(_("Ignoring connection request from blocked IP Address %(ip)s:%(port)s"), {
                            'ip': incaddr[0],
                            'port': incaddr[1]
                        })
                        incconn.close()

                    else:
                        self._conns[incconn] = PeerConnection(conn=incconn, addr=incaddr)
                        self._numsockets += 1
                        self._core_callback([IncConn(incconn, incaddr)])

                        # Event flags are modified to include 'write' in subsequent loops, if necessary.
                        # Don't do it here, otherwise connections may break.
                        self.selector.register(incconn, selectors.EVENT_READ)

            # Manage Connections
            curtime = time.time()

            for connection_in_progress in self._connsinprogress.copy():
                conn_obj = self._connsinprogress.get(connection_in_progress)

                if not conn_obj:
                    # Connection was removed, possibly disconnecting from the server
                    continue

                msg_obj = conn_obj.msg_obj

                if (curtime - conn_obj.lastactive) > self.IN_PROGRESS_STALE_AFTER:

                    self._core_callback([ConnectError(msg_obj, "Timed out")])
                    self.close_connection(self._connsinprogress, connection_in_progress)
                    continue

                try:
                    if connection_in_progress in input_list:
                        # Check if the socket has any data for us
                        connection_in_progress.setblocking(0)
                        connection_in_progress.recv(1, socket.MSG_PEEK)
                        connection_in_progress.setblocking(1)

                except socket.error as err:

                    self._core_callback([ConnectError(msg_obj, err)])
                    self.close_connection(self._connsinprogress, connection_in_progress)

                else:
                    if connection_in_progress in output_list:
                        addr = msg_obj.addr

                        if connection_in_progress is self.server_socket:
                            self._conns[self.server_socket] = Connection(conn=self.server_socket, addr=addr)

                            self._core_callback([ServerConn(self.server_socket, addr)])

                        else:
                            self._conns[connection_in_progress] = PeerConnection(
                                conn=connection_in_progress, addr=addr, init=msg_obj.init)

                            self._core_callback([PeerConn(connection_in_progress, addr)])

                        del self._connsinprogress[connection_in_progress]

            # Process Data
            curtime = time.time()

            for connection in self._conns.copy():
                conn_obj = self._conns.get(connection)

                if not conn_obj:
                    # Connection was removed, possibly disconnecting from the server
                    continue

                if connection is not self.server_socket:
                    addr = conn_obj.addr

                    # Timeout Connections

                    if curtime - conn_obj.lastactive > self.CONNECTION_MAX_IDLE:
                        self._core_callback([ConnClose(connection, addr)])
                        self.close_connection(self._conns, connection)
                        continue

                    if self._network_filter.is_ip_blocked(addr[0]):
                        log.add_conn("Blocking peer connection to IP: %(ip)s Port: %(port)s", {
                            "ip": addr[0],
                            "port": addr[1]
                        })
                        self._core_callback([ConnClose(connection, addr)])
                        self.close_connection(self._conns, connection)
                        continue

                if connection in input_list:
                    if self._is_download(conn_obj):
                        self.set_conn_speed_limit(connection, self._downloadlimit[0], self._dlimits)

                    try:
                        if not self.read_data(conn_obj):
                            # No data received, socket was likely closed remotely
                            self._core_callback([ConnClose(connection, conn_obj.addr)])
                            self.close_connection(self._conns, connection)
                            continue

                    except socket.error as err:
                        self._core_callback([ConnectError(conn_obj, err)])
                        self.close_connection(self._conns, connection)
                        continue

                if conn_obj.ibuf:
                    self.process_conn_input(connection, conn_obj)

                if connection in output_list:
                    if self._is_upload(conn_obj):
                        self.set_conn_speed_limit(connection, self._uploadlimit[0], self._ulimits)

                    try:
                        self.write_data(conn_obj)

                    except socket.error as err:
                        self._core_callback([ConnectError(conn_obj, err)])
                        self.close_connection(self._conns, connection)
                        continue

            # Don't exhaust the CPU
            time.sleep(0.005)

        # Networking thread aborted
