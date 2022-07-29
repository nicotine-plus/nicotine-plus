# COPYRIGHT (C) 2020-2022 Nicotine+ Contributors
# COPYRIGHT (C) 2008-2012 Quinox <quinox@users.sf.net>
# COPYRIGHT (C) 2007-2009 Daelstorm <daelstorm@gmail.com>
# COPYRIGHT (C) 2003-2004 Hyriand <hyriand@thegraveyard.org>
# COPYRIGHT (C) 2001-2003 Alexander Kanavin
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

import copy
import selectors
import socket
import struct
import sys
import threading
import time

from pynicotine.logfacility import log
from pynicotine.slskmessages import DISTRIBUTED_MESSAGE_CLASSES
from pynicotine.slskmessages import DISTRIBUTED_MESSAGE_CODES
from pynicotine.slskmessages import PEER_MESSAGE_CLASSES
from pynicotine.slskmessages import PEER_MESSAGE_CODES
from pynicotine.slskmessages import PEER_INIT_MESSAGE_CLASSES
from pynicotine.slskmessages import PEER_INIT_MESSAGE_CODES
from pynicotine.slskmessages import SERVER_MESSAGE_CLASSES
from pynicotine.slskmessages import SERVER_MESSAGE_CODES
from pynicotine.slskmessages import AcceptChildren
from pynicotine.slskmessages import BranchLevel
from pynicotine.slskmessages import BranchRoot
from pynicotine.slskmessages import CheckPrivileges
from pynicotine.slskmessages import ConnClose
from pynicotine.slskmessages import ConnCloseIP
from pynicotine.slskmessages import ConnectionType
from pynicotine.slskmessages import ConnectToPeer
from pynicotine.slskmessages import DistribBranchLevel
from pynicotine.slskmessages import DistribBranchRoot
from pynicotine.slskmessages import DistribEmbeddedMessage
from pynicotine.slskmessages import DistribSearch
from pynicotine.slskmessages import DownloadConnClose
from pynicotine.slskmessages import DownloadFile
from pynicotine.slskmessages import DownloadFileError
from pynicotine.slskmessages import EmbeddedMessage
from pynicotine.slskmessages import FileOffset
from pynicotine.slskmessages import FileDownloadInit
from pynicotine.slskmessages import FileUploadInit
from pynicotine.slskmessages import FileSearchResult
from pynicotine.slskmessages import GetPeerAddress
from pynicotine.slskmessages import GetUserStats
from pynicotine.slskmessages import GetUserStatus
from pynicotine.slskmessages import HaveNoParent
from pynicotine.slskmessages import InitPeerConn
from pynicotine.slskmessages import Login
from pynicotine.slskmessages import MessageProgress
from pynicotine.slskmessages import MessageType
from pynicotine.slskmessages import PossibleParents
from pynicotine.slskmessages import ParentMinSpeed
from pynicotine.slskmessages import ParentSpeedRatio
from pynicotine.slskmessages import PeerInit
from pynicotine.slskmessages import PierceFireWall
from pynicotine.slskmessages import Relogged
from pynicotine.slskmessages import ResetDistributed
from pynicotine.slskmessages import RoomList
from pynicotine.slskmessages import SendNetworkMessage
from pynicotine.slskmessages import ServerConnect
from pynicotine.slskmessages import ServerDisconnect
from pynicotine.slskmessages import ServerTimeout
from pynicotine.slskmessages import SetConnectionStats
from pynicotine.slskmessages import SetDownloadLimit
from pynicotine.slskmessages import SetUploadLimit
from pynicotine.slskmessages import SetWaitPort
from pynicotine.slskmessages import SharedFileList
from pynicotine.slskmessages import ShowConnectionErrorMessage
from pynicotine.slskmessages import UploadConnClose
from pynicotine.slskmessages import UploadFile
from pynicotine.slskmessages import UploadFileError
from pynicotine.slskmessages import UserInfoReply
from pynicotine.slskmessages import UserStatus
from pynicotine.slskmessages import increment_token


# Set the maximum number of open files to the hard limit reported by the OS.
# Our MAXSOCKETS value needs to be lower than the file limit, otherwise our open
# sockets in combination with other file activity can exceed the file limit,
# effectively halting the program.

if sys.platform == "win32":
    # For Windows, FD_SETSIZE is set to 512 in the Python source.
    # This limit is hardcoded, so we'll have to live with it for now.

    MAXSOCKETS = 512
else:
    import resource  # pylint: disable=import-error

    if sys.platform == "darwin":
        # Maximum number of files a process can open is 10240 on macOS.
        # macOS reports INFINITE as hard limit, so we need this special case.

        MAXFILELIMIT = 10240
    else:
        _SOFTLIMIT, MAXFILELIMIT = resource.getrlimit(resource.RLIMIT_NOFILE)     # pylint: disable=no-member

    try:
        resource.setrlimit(resource.RLIMIT_NOFILE, (MAXFILELIMIT, MAXFILELIMIT))  # pylint: disable=no-member

    except Exception as rlimit_error:
        log.add("Failed to set RLIMIT_NOFILE: %s", rlimit_error)

    # Set the maximum number of open sockets to a lower value than the hard limit,
    # otherwise we just waste resources.
    # The maximum is 3072, but can be lower if the file limit is too low.

    MAXSOCKETS = min(max(int(MAXFILELIMIT * 0.75), 50), 3072)

UINT_UNPACK = struct.Struct("<I").unpack
DOUBLE_UINT_UNPACK = struct.Struct("<II").unpack


class Connection:
    """ Holds data about a connection. sock is a socket object,
    addr is (ip, port) pair, ibuf and obuf are input and output msgBuffer,
    init is a PeerInit object (see slskmessages docstrings). """

    __slots__ = ("sock", "addr", "events", "ibuf", "obuf", "lastactive", "lastreadlength")

    def __init__(self, sock=None, addr=None, events=None):

        self.sock = sock
        self.addr = addr
        self.events = events
        self.ibuf = bytearray()
        self.obuf = bytearray()
        self.lastactive = time.time()
        self.lastreadlength = 100 * 1024


class ServerConnection(Connection):

    __slots__ = ("login",)

    def __init__(self, sock=None, addr=None, events=None, login=None):

        super().__init__(sock, addr, events)

        self.login = login


class PeerConnection(Connection):

    __slots__ = ("init", "indirect", "fileinit", "filedown", "fileupl", "lastcallback")

    def __init__(self, sock=None, addr=None, events=None, init=None, indirect=False):

        super().__init__(sock, addr, events)

        self.init = init
        self.indirect = indirect
        self.fileinit = None
        self.filedown = None
        self.fileupl = None
        self.lastcallback = time.time()


class SlskProtoThread(threading.Thread):
    """ This is a networking thread that actually does all the communication.
    It sends data to the NicotineCore via a callback function and receives
    data via a deque object. """

    """ The server and peers send each other small binary messages that start
    with length and message code followed by the actual message data. """

    IN_PROGRESS_STALE_AFTER = 2
    CONNECTION_MAX_IDLE = 60

    def __init__(self, core_callback, queue, bindip, interface, port, port_range):
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
        self._callback_msgs = []
        self._init_msgs = {}
        self._want_abort = False
        self.bindip = bindip
        self.listenport = None
        self.portrange = (port, port) if port else port_range
        self.interface = interface

        # Select Networking Input and Output sockets
        self.selector = selectors.DefaultSelector()

        self.listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.listen_socket.setblocking(False)

        self.server_disconnected = True
        self.manual_server_disconnect = False
        self._server_relogged = False

        self.server_socket = None
        self.server_address = None
        self.server_username = None
        self.server_timer = None
        self.server_timeout_value = -1

        self.parent_socket = None
        self.potential_parents = {}
        self.distrib_parent_min_speed = 0
        self.distrib_parent_speed_ratio = 1
        self.max_distrib_children = 10

        self._numsockets = 1
        self._last_conn_stat_time = 0

        self._conns = {}
        self._connsinprogress = {}
        self._out_indirect_conn_request_times = {}
        self._token = 0
        self.exit = threading.Event()
        self.user_addresses = {}

        self._calc_upload_limit_function = self._calc_upload_limit_none
        self._upload_limit = 0
        self._download_limit = 0
        self._upload_limit_split = 0
        self._download_limit_split = 0
        self._ulimits = {}
        self._dlimits = {}
        self.total_uploads = 0
        self.total_downloads = 0
        self.total_download_bandwidth = 0
        self.total_upload_bandwidth = 0
        self.last_cycle_time = time.time()
        self.current_cycle_loop_count = 0
        self.last_cycle_loop_count = 0
        self.loops_per_second = 0

        core_callback([SetConnectionStats()])
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
    def get_interface_ip_address(if_name):

        try:
            import fcntl
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            ip_if = fcntl.ioctl(sock.fileno(),
                                0x8915,  # SIOCGIFADDR
                                struct.pack('256s', if_name.encode()[:15]))

            ip_address = socket.inet_ntoa(ip_if[20:24])

        except ImportError:
            ip_address = None

        return ip_address

    def bind_to_network_interface(self, sock, if_name):

        try:
            if sys.platform == "linux":
                sock.setsockopt(socket.SOL_SOCKET, 25, if_name.encode())
                self.bindip = None
                return

            if sys.platform == "darwin":
                sock.setsockopt(socket.IPPROTO_IP, 25, socket.if_nametoindex(if_name))
                self.bindip = None
                return

        except PermissionError:
            pass

        # System does not support changing the network interface
        # Retrieve the IP address of the interface, and bind to it instead
        self.bindip = self.get_interface_ip_address(if_name)

    def bind_listen_port(self):

        if not self.validate_network_interface():
            return

        if self.interface and not self.bindip:
            self.bind_to_network_interface(self.listen_socket, self.interface)

        ip_address = self.bindip or ''

        for listenport in range(int(self.portrange[0]), int(self.portrange[1]) + 1):
            try:
                self.listen_socket.bind((ip_address, listenport))
                self.listen_socket.listen()
                self.listenport = listenport
                log.add(_("Listening on port: %i"), listenport)
                log.add_debug("Maximum number of concurrent connections (sockets): %i", MAXSOCKETS)
                break

            except OSError as error:
                log.add_debug("Cannot listen on port %(port)s: %(error)s", {"port": listenport, "error": error})
                continue

    def server_connect(self, msg_obj):
        """ We're connecting to the server """

        if self.server_socket:
            return

        self.server_disconnected = False
        self.manual_server_disconnect = False

        if self.server_timer is not None:
            self.server_timer.cancel()
            self.server_timer = None

        ip_address, port = msg_obj.addr
        log.add(_("Connecting to %(host)s:%(port)s"), {'host': ip_address, 'port': port})

        self.init_server_conn(msg_obj)

    def server_disconnect(self):
        """ We're disconnecting from the server, clean up """

        self.server_disconnected = True
        self.server_socket = None

        for sock in self._conns.copy():
            self.close_connection(self._conns, sock, callback=False)

        for sock in self._connsinprogress.copy():
            self.close_connection(self._connsinprogress, sock, callback=False)

        self._queue.clear()
        self._init_msgs.clear()

        # Inform threads we've disconnected
        self.exit.set()
        self._out_indirect_conn_request_times.clear()

        if self._want_abort:
            return

        # Reset connection stats
        self._callback_msgs.append(SetConnectionStats())

        if not self.server_address:
            # We didn't successfully establish a connection to the server
            return

        ip_address, port = self.server_address

        log.add(
            _("Disconnected from server %(host)s:%(port)s"), {
                'host': ip_address,
                'port': port
            })

        if self._server_relogged:
            log.add(_("Someone logged in to your Soulseek account elsewhere"))
            self._server_relogged = False

        if not self.manual_server_disconnect:
            self.set_server_timer()

        self.server_address = None
        self.server_username = None
        self._callback_msgs.append(ServerDisconnect(self.manual_server_disconnect))

    def server_timeout(self):
        self._core_callback([ServerTimeout()])

    def set_server_timer(self):

        if self.server_timeout_value == -1:
            self.server_timeout_value = 15

        elif 0 < self.server_timeout_value < 600:
            self.server_timeout_value = self.server_timeout_value * 2

        self.server_timer = threading.Timer(self.server_timeout_value, self.server_timeout)
        self.server_timer.name = "ServerTimer"
        self.server_timer.daemon = True
        self.server_timer.start()

        log.add(_("The server seems to be down or not responding, retrying in %i seconds"),
                self.server_timeout_value)

    def abort(self):
        """ Call this to abort the thread """
        self._want_abort = True

        self.close_socket(self.listen_socket)
        self.selector.close()
        self.server_disconnect()

    """ File Transfers """

    @staticmethod
    def _is_upload(conn_obj):
        return conn_obj.__class__ is PeerConnection and conn_obj.fileinit.__class__ is FileUploadInit

    @staticmethod
    def _is_download(conn_obj):
        return conn_obj.__class__ is PeerConnection and conn_obj.fileinit.__class__ is FileDownloadInit

    def _calc_upload_limit(self, limit_disabled=False, limit_per_transfer=False):

        limit = self._upload_limit
        loop_limit = 1024  # 1 KB/s is the minimum upload speed per transfer

        if limit_disabled or limit < loop_limit:
            self._upload_limit_split = 0
            return

        if not limit_per_transfer and self.total_uploads > 1:
            limit = limit // self.total_uploads

        self._upload_limit_split = int(limit)

    def _calc_upload_limit_by_transfer(self):
        return self._calc_upload_limit(limit_per_transfer=True)

    def _calc_upload_limit_none(self):
        return self._calc_upload_limit(limit_disabled=True)

    def _calc_download_limit(self):

        limit = self._download_limit
        loop_limit = 1024  # 1 KB/s is the minimum download speed per transfer

        if limit < loop_limit:
            # Download limit disabled
            self._download_limit_split = 0
            return

        if self.total_downloads > 1:
            limit = limit // self.total_downloads

        self._download_limit_split = int(limit)

    def _calc_loops_per_second(self):
        """ Calculate number of loops per second. This value is used to split the
        per-second transfer speed limit evenly for each loop. """

        current_time = time.time()

        if current_time - self.last_cycle_time >= 1:
            self.loops_per_second = (self.last_cycle_loop_count + self.current_cycle_loop_count) // 2

            self.last_cycle_loop_count = self.current_cycle_loop_count
            self.last_cycle_time = current_time
            self.current_cycle_loop_count = 0
        else:
            self.current_cycle_loop_count = self.current_cycle_loop_count + 1

    def set_conn_speed_limit(self, sock, limit, limits):

        limit = limit // (self.loops_per_second or 1)

        if limit > 0:
            limits[sock] = limit

    """ Connections """

    def _check_indirect_connection_timeouts(self):

        while True:
            curtime = time.time()

            if self._out_indirect_conn_request_times:
                for init, request_time in self._out_indirect_conn_request_times.copy().items():
                    username = init.target_user
                    conn_type = init.conn_type

                    if (curtime - request_time) >= 20:
                        log.add_conn(("Indirect connect request of type %(type)s to user %(user)s with "
                                      "token %(token)s expired, giving up"), {
                            'type': conn_type,
                            'user': username,
                            'token': init.token
                        })

                        self._callback_msgs.append(ShowConnectionErrorMessage(username, init.outgoing_msgs[:]))

                        self._init_msgs.pop(init.token, None)
                        init.outgoing_msgs.clear()
                        del self._out_indirect_conn_request_times[init]

            if self.exit.wait(1):
                # Event set, we're exiting
                return

    def socket_still_active(self, sock):

        try:
            conn_obj = self._conns[sock]

        except KeyError:
            return False

        return len(conn_obj.obuf) > 0 or len(conn_obj.ibuf) > 0

    def has_existing_user_socket(self, user, conn_type):

        prev_init = self._init_msgs.get(user + conn_type)

        if prev_init is not None and prev_init.sock is not None:
            return True

        return False

    def add_init_message(self, init):

        conn_type = init.conn_type

        if conn_type == ConnectionType.FILE:
            # File transfer connections are not unique or reused later
            return

        self._init_msgs[init.target_user + conn_type] = init

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
            log.add_debug(("Unable to parse %(conn_type)s message type %(msg_type)s size %(size)i "
                           "contents %(msg_buffer)s: %(error)s"), {
                'conn_type': conn_type,
                'msg_type': msg_class,
                'size': msg_size,
                'msg_buffer': msg_buffer,
                'error': error
            })

        return None

    @staticmethod
    def unpack_embedded_message(msg):
        """ This message embeds a distributed message. We unpack the distributed message and process it. """

        if msg.distrib_code not in DISTRIBUTED_MESSAGE_CLASSES:
            return None

        distrib_class = DISTRIBUTED_MESSAGE_CLASSES[msg.distrib_code]
        distrib_msg = distrib_class()
        distrib_msg.parse_network_message(msg.distrib_message)

        return distrib_msg

    def modify_connection_events(self, conn_obj, events):

        if conn_obj.events != events:
            self.selector.modify(conn_obj.sock, events)
            conn_obj.events = events

    def process_conn_messages(self, init):
        """ A connection is established with the peer, time to queue up our peer
        messages for delivery """

        msgs = init.outgoing_msgs

        for j in msgs:
            j.init = init
            self._queue.append(j)

        msgs.clear()

    def send_message_to_peer(self, user, message, address=None):

        init = None
        conn_type = message.msgtype

        if conn_type not in (ConnectionType.PEER, ConnectionType.FILE, ConnectionType.DISTRIBUTED):
            return

        # Check if there's already a connection for the specified username
        init = self._init_msgs.get(user + conn_type)

        if init is None and conn_type != ConnectionType.FILE:
            # Check if we have a pending PeerInit message (currently requesting user IP address)
            pending_init_msgs = self._init_msgs.get(user, [])

            for msg in pending_init_msgs:
                if msg.conn_type == conn_type:
                    init = msg
                    break

        log.add_conn("Sending message of type %(type)s to user %(user)s", {
            'type': message.__class__,
            'user': user
        })

        if init is not None:
            log.add_conn("Found existing connection of type %(type)s for user %(user)s, using it.", {
                'type': conn_type,
                'user': user
            })

            init.outgoing_msgs.append(message)

            if init.sock is not None:
                # We have initiated a connection previously, and it's ready
                self.process_conn_messages(init)

        else:
            # This is a new peer, initiate a connection
            self.initiate_connection_to_peer(user, conn_type, message, address)

    def initiate_connection_to_peer(self, user, conn_type, message=None, address=None):
        """ Prepare to initiate a connection with a peer """

        init = PeerInit(init_user=self.server_username, target_user=user, conn_type=conn_type)
        addr = None

        if message is not None:
            init.outgoing_msgs.append(message)

        if user in self.user_addresses:
            addr = self.user_addresses[user]

        elif address is not None:
            self.user_addresses[user] = addr = address

        if addr is None:
            if user not in self._init_msgs:
                self._init_msgs[user] = []

            self._init_msgs[user].append(init)
            self._queue.append(GetPeerAddress(user))

            log.add_conn("Requesting address for user %(user)s", {
                'user': user
            })

        else:
            init.addr = addr
            self.connect_to_peer(user, addr, init)

    def connect_to_peer(self, user, addr, init):
        """ Initiate a connection with a peer """

        if self.has_existing_user_socket(user, init.conn_type):
            log.add_conn(("Direct connection of type %(type)s to user %(user)s %(addr)s requested, "
                          "but existing connection already exists"), {
                'type': init.conn_type,
                'user': user,
                'addr': addr
            })
            return

        if not init.indirect:
            # Also request indirect connection in case the user's port is closed
            self.connect_to_peer_indirect(init)

        self.add_init_message(init)
        self._queue.append(InitPeerConn(addr, init))

        log.add_conn("Attempting direct connection of type %(type)s to user %(user)s %(addr)s", {
            'type': init.conn_type,
            'user': user,
            'addr': addr
        })

    def connect_error(self, error, conn_obj):

        if conn_obj.sock is self.server_socket:
            server_address, port = conn_obj.addr

            log.add(
                _("Cannot connect to server %(host)s:%(port)s: %(error)s"), {
                    'host': server_address,
                    'port': port,
                    'error': error
                }
            )
            self.set_server_timer()
            return

        if not conn_obj.init.indirect:
            log.add_conn(("Direct connection of type %(type)s to user %(user)s failed. Error: %(error)s"), {
                "type": conn_obj.init.conn_type,
                "user": conn_obj.init.target_user,
                "error": error
            })
            return

        if conn_obj.init in self._out_indirect_conn_request_times:
            return

        log.add_conn(
            "Cannot respond to indirect connection request from user %(user)s. Error: %(error)s", {
                'user': conn_obj.init.target_user,
                'error': error
            })

    def connect_to_peer_indirect(self, init):
        """ Send a message to the server to ask the peer to connect to us (indirect connection) """

        self._token = increment_token(self._token)

        username = init.target_user
        conn_type = init.conn_type
        init.token = self._token

        self._init_msgs[self._token] = init
        self._out_indirect_conn_request_times[init] = time.time()
        self._queue.append(ConnectToPeer(self._token, username, conn_type))

        log.add_conn(("Attempting indirect connection to user %(user)s with token %(token)s"), {
            "user": username,
            "token": self._token
        })

    def establish_outgoing_peer_connection(self, conn_obj):

        sock = conn_obj.sock
        self._conns[sock] = conn_obj

        init = conn_obj.init
        user = init.target_user
        conn_type = init.conn_type
        token = init.token
        init.sock = sock

        log.add_conn(("Established outgoing connection of type %(type)s with user %(user)s. List of "
                      "outgoing messages: %(messages)s"), {
            'type': conn_type,
            'user': user,
            'messages': init.outgoing_msgs
        })

        if init.indirect:
            log.add_conn(("Responding to indirect connection request of type %(type)s from "
                          "user %(user)s, token %(token)s"), {
                'type': conn_type,
                'user': user,
                'token': token
            })
            self._queue.append(PierceFireWall(sock, token))

        else:
            # Direct connection established
            log.add_conn("Sending PeerInit message of type %(type)s to user %(user)s", {
                'type': conn_type,
                'user': user
            })
            self._queue.append(init)

            # Direct and indirect connections are attempted at the same time, clean up
            self._init_msgs.pop(token, None)

            if self._out_indirect_conn_request_times.pop(init, None):
                log.add_conn(("Stopping indirect connection attempt of type %(type)s to user "
                              "%(user)s"), {
                    'type': conn_type,
                    'user': user
                })

        self.process_conn_messages(init)

    def establish_outgoing_server_connection(self, conn_obj):

        self._conns[self.server_socket] = conn_obj
        addr = conn_obj.addr

        log.add(
            _("Connected to server %(host)s:%(port)s, logging in…"), {
                'host': addr[0],
                'port': addr[1]
            }
        )

        login, password = conn_obj.login
        self.user_addresses[login] = (self.bindip or '127.0.0.1', self.listenport)
        conn_obj.login = True

        self.server_address = addr
        self.server_username = login
        self.server_timeout_value = -1

        self._queue.append(
            Login(
                login, password,
                # Soulseek client version
                # NS and SoulseekQt use 157
                # We use a custom version number for Nicotine+
                160,

                # Soulseek client minor version
                # 17 stands for 157 ns 13c, 19 for 157 ns 13e
                # SoulseekQt seems to go higher than this
                # We use a custom minor version for Nicotine+
                1
            )
        )

        if self.listenport is not None:
            self._queue.append(SetWaitPort(self.listenport))

    def replace_existing_connection(self, init):

        user = init.target_user
        conn_type = init.conn_type

        if user == self.server_username or not self.has_existing_user_socket(user, conn_type):
            return

        log.add_conn("Discarding existing connection of type %(type)s to user %(user)s", {
            "type": init.conn_type,
            "user": user
        })

        prev_init = self._init_msgs[user + conn_type]
        init.outgoing_msgs = prev_init.outgoing_msgs
        prev_init.outgoing_msgs = []

        self.close_connection(self._conns, prev_init.sock)

    def close_socket(self, sock):

        try:
            sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass

        try:
            sock.close()
        except OSError:
            pass

    def close_connection(self, connection_list, sock, callback=True):

        conn_obj = connection_list.pop(sock, None)

        if conn_obj is None:
            # Already removed
            return

        # If we're shutting down, we've already closed the selector in abort()
        if not self._want_abort:
            self.selector.unregister(sock)

        self.close_socket(sock)
        self._numsockets -= 1

        if sock is self.server_socket:
            # Disconnected from server, clean up connections and queue
            self.server_disconnect()

        elif sock is self.parent_socket and not self.server_disconnected:
            self.send_have_no_parent()

        elif self._is_download(conn_obj):
            self.total_downloads -= 1

            if not self.total_downloads:
                self.total_download_bandwidth = 0

            if callback:
                self._callback_msgs.append(DownloadConnClose(sock))

            self._calc_download_limit()

        elif self._is_upload(conn_obj):
            self.total_uploads -= 1

            if not self.total_uploads:
                self.total_upload_bandwidth = 0

            if callback:
                self._callback_msgs.append(UploadConnClose(sock))

            self._calc_upload_limit_function()

        if conn_obj.__class__ is ServerConnection or conn_obj.init is None:
            return

        conn_type = conn_obj.init.conn_type
        user = conn_obj.init.target_user

        log.add_conn("Removed connection of type %(type)s to user %(user)s %(addr)s", {
            'type': conn_type,
            'user': user,
            'addr': conn_obj.addr
        })

        init_key = user + conn_type
        init = self._init_msgs.get(init_key)

        if init is None:
            return

        log.add_conn("Removing PeerInit message of type %(type)s for user %(user)s %(addr)s", {
            'type': conn_type,
            'user': user,
            'addr': conn_obj.addr
        })

        if conn_obj.init is not init:
            # Don't remove init message if connection has been superseded
            log.add_conn("Cannot remove PeerInit message, since the connection has been superseded")
            return

        if connection_list is self._connsinprogress and init.sock is not None:
            # Outgoing connection failed, but an indirect connection was already established
            log.add_conn("Cannot remove PeerInit message, an indirect connection was already established previously")
            return

        del self._init_msgs[init_key]

    def close_connection_by_ip(self, ip_address):

        for sock, conn_obj in self._conns.copy().items():
            if conn_obj is None or sock is self.server_socket:
                continue

            addr = conn_obj.addr

            if ip_address == addr[0]:
                log.add_conn("Blocking peer connection to IP address %(ip)s:%(port)s", {
                    "ip": addr[0],
                    "port": addr[1]
                })
                self.close_connection(self._conns, sock)

    """ Server Connection """

    @staticmethod
    def set_server_socket_keepalive(server_socket, idle=10, interval=4, count=10):
        """ Ensure we are disconnected from the server in case of connectivity issues,
        by sending TCP keepalive pings. Assuming default values are used, once we reach
        10 seconds of idle time, we start sending keepalive pings once every 4 seconds.
        If 10 failed pings have been sent in a row (40 seconds), the connection is presumed
        dead. """

        if hasattr(socket, 'SO_KEEPALIVE'):
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)  # pylint: disable=no-member

        if hasattr(socket, 'TCP_KEEPINTVL'):
            server_socket.setsockopt(socket.IPPROTO_TCP,
                                     socket.TCP_KEEPINTVL, interval)  # pylint: disable=no-member

        if hasattr(socket, 'TCP_KEEPCNT'):
            server_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, count)  # pylint: disable=no-member

        if hasattr(socket, 'TCP_KEEPIDLE'):
            server_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, idle)  # pylint: disable=no-member

        elif hasattr(socket, 'TCP_KEEPALIVE'):
            # macOS fallback

            server_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPALIVE, idle)  # pylint: disable=no-member

        elif hasattr(socket, 'SIO_KEEPALIVE_VALS'):
            # Windows fallback
            # Probe count is set to 10 on a system level, and can't be modified.
            # https://docs.microsoft.com/en-us/windows/win32/winsock/so-keepalive

            server_socket.ioctl(
                socket.SIO_KEEPALIVE_VALS,  # pylint: disable=no-member
                (
                    1,
                    idle * 1000,
                    interval * 1000
                )
            )

    def init_server_conn(self, msg_obj):

        try:
            self.server_socket = server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            events = selectors.EVENT_READ | selectors.EVENT_WRITE
            conn_obj = ServerConnection(sock=server_socket, addr=msg_obj.addr, events=events, login=msg_obj.login)

            server_socket.setblocking(False)

            # Detect if our connection to the server is still alive
            self.set_server_socket_keepalive(server_socket)

            if self.bindip:
                server_socket.bind((self.bindip, 0))

            elif self.interface:
                self.bind_to_network_interface(server_socket, self.interface)

            server_socket.connect_ex(msg_obj.addr)

            self.selector.register(server_socket, events)
            self._connsinprogress[server_socket] = conn_obj
            self._numsockets += 1

        except OSError as error:
            self.connect_error(error, conn_obj)
            self.close_socket(server_socket)
            self.server_disconnect()

    def process_server_input(self, conn_obj, msg_buffer):
        """ Server has sent us something, this function retrieves messages
        from the msg_buffer, creates message objects and returns them and the rest
        of the msg_buffer. """

        msg_buffer_mem = memoryview(msg_buffer)
        buffer_len = len(msg_buffer_mem)
        idx = 0

        # Server messages are 8 bytes or greater in length
        while buffer_len >= 8:
            msgsize, msgtype = DOUBLE_UINT_UNPACK(msg_buffer_mem[idx:idx + 8])
            msgsize_total = msgsize + 4

            if msgsize_total > buffer_len or msgsize < 0:
                # Invalid message size or buffer is being filled
                break

            # Unpack server messages
            if msgtype in SERVER_MESSAGE_CLASSES:
                msg_class = SERVER_MESSAGE_CLASSES[msgtype]
                msg = self.unpack_network_message(
                    msg_class, msg_buffer_mem[idx + 8:idx + msgsize_total], msgsize - 4, "server")

                if msg is not None:
                    if msg_class is EmbeddedMessage:
                        msg = self.unpack_embedded_message(msg)

                    elif msg_class is Login:
                        if msg.success:
                            # Check for indirect connection timeouts
                            self.exit.clear()

                            thread = threading.Thread(target=self._check_indirect_connection_timeouts)
                            thread.name = "IndirectConnectionTimeoutTimer"
                            thread.daemon = True
                            thread.start()

                            msg.username = self.server_username
                            self._queue.append(CheckPrivileges())

                            # Ask for a list of parents to connect to (distributed network)
                            self.send_have_no_parent()

                            # TODO: We can currently receive search requests from a parent connection, but
                            # redirecting results to children is not implemented yet. Tell the server we don't accept
                            # children for now.
                            self._queue.append(AcceptChildren(False))

                            # Request a complete room list. A limited room list not including blacklisted rooms and
                            # rooms with few users is automatically sent when logging in, but subsequent room list
                            # requests contain all rooms.
                            self._queue.append(RoomList())

                        else:
                            self._queue.append(ServerDisconnect())

                    elif msg_class is ConnectToPeer:
                        user = msg.user
                        addr = (msg.ip_address, msg.port)
                        conn_type = msg.conn_type
                        token = msg.token

                        log.add_conn(("Received indirect connection request of type %(type)s from user %(user)s, "
                                      "token %(token)s, address %(addr)s"), {
                            "type": conn_type,
                            "user": user,
                            "token": token,
                            "addr": addr
                        })
                        init = PeerInit(addr=addr, init_user=user, target_user=user,
                                        conn_type=conn_type, indirect=True, token=token)
                        self.connect_to_peer(user, addr, init)

                    elif msg_class is GetUserStatus:
                        if msg.status == UserStatus.OFFLINE:
                            # User went offline, reset stored IP address
                            if msg.user in self.user_addresses:
                                del self.user_addresses[msg.user]

                    elif msg_class is GetUserStats:
                        if msg.user == self.server_username:
                            self.max_distrib_children = msg.avgspeed // self.distrib_parent_speed_ratio

                    elif msg_class is GetPeerAddress:
                        user = msg.user
                        pending_init_msgs = self._init_msgs.pop(msg.user, [])

                        if msg.port == 0:
                            log.add_conn(
                                "Server reported port 0 for user %(user)s", {
                                    'user': user
                                }
                            )

                        addr = (msg.ip_address, msg.port)
                        user_offline = (addr == ("0.0.0.0", 0))

                        for init in pending_init_msgs:
                            # We now have the IP address for a user we previously didn't know,
                            # attempt a direct connection to the peer/user
                            if user_offline:
                                self._callback_msgs.append(ShowConnectionErrorMessage(user, init.outgoing_msgs[:]))
                            else:
                                init.addr = addr
                                self.connect_to_peer(user, addr, init)

                        # We already store a local IP address for our username
                        # Port 0 means the user is offline or bugged, don't store address
                        if user != self.server_username and msg.port != 0:
                            self.user_addresses[msg.user] = addr

                    elif msg_class is Relogged:
                        self.manual_server_disconnect = True
                        self._server_relogged = True

                    elif msg_class is PossibleParents:
                        # Server sent a list of 10 potential parents, whose purpose is to forward us search requests.
                        # We attempt to connect to them all at once, since connection errors are fairly common.

                        self.potential_parents = msg.list
                        log.add_conn("Server sent us a list of %s possible parents", len(msg.list))

                        if self.parent_socket is None and self.potential_parents:
                            for user in self.potential_parents:
                                addr = self.potential_parents[user]

                                log.add_conn("Attempting parent connection to user %s", user)
                                self.initiate_connection_to_peer(user, ConnectionType.DISTRIBUTED, address=addr)

                    elif msg_class is ParentMinSpeed:
                        self.distrib_parent_min_speed = msg.speed

                    elif msg_class is ParentSpeedRatio:
                        self.distrib_parent_speed_ratio = msg.ratio

                    elif msg_class is ResetDistributed:
                        log.add_conn("Received a reset request for distributed network")

                        if self.parent_socket is not None:
                            self.close_connection(self._conns, self.parent_socket)

                        self.send_have_no_parent()

                    if msg is not None:
                        self._callback_msgs.append(msg)

            else:
                log.add_debug("Server message type %(type)i size %(size)i contents %(msg_buffer)s unknown", {
                    'type': msgtype,
                    'size': msgsize - 4,
                    'msg_buffer': msg_buffer[idx + 8:idx + msgsize_total]
                })

            idx += msgsize_total
            buffer_len -= msgsize_total

        if idx:
            conn_obj.ibuf = msg_buffer[idx:]

    def process_server_output(self, msg_obj):

        msg_class = msg_obj.__class__

        if self.server_socket not in self._conns:
            log.add_conn("Cannot send the message over the closed connection: %(type)s %(msg_obj)s", {
                'type': msg_class,
                'msg_obj': vars(msg_obj)
            })
            return

        msg = self.pack_network_message(msg_obj)

        if msg is None:
            return

        conn_obj = self._conns[self.server_socket]
        conn_obj.obuf.extend(msg_obj.pack_uint32(len(msg) + 4))
        conn_obj.obuf.extend(msg_obj.pack_uint32(SERVER_MESSAGE_CODES[msg_class]))
        conn_obj.obuf.extend(msg)

        self.modify_connection_events(conn_obj, selectors.EVENT_READ | selectors.EVENT_WRITE)

    """ Peer Init """

    def process_peer_init_input(self, conn_obj, msg_buffer):

        msg_buffer_mem = memoryview(msg_buffer)
        buffer_len = len(msg_buffer_mem)
        idx = 0

        # Peer init messages are 8 bytes or greater in length
        while buffer_len >= 8 and conn_obj.init is None:
            msgsize = UINT_UNPACK(msg_buffer_mem[idx:idx + 4])[0]
            msgsize_total = msgsize + 4

            if msgsize_total > buffer_len or msgsize < 0:
                # Invalid message size or buffer is being filled
                break

            msgtype = msg_buffer_mem[idx + 4]

            # Unpack peer init messages
            if msgtype in PEER_INIT_MESSAGE_CLASSES:
                msg_class = PEER_INIT_MESSAGE_CLASSES[msgtype]
                msg = self.unpack_network_message(
                    msg_class, msg_buffer_mem[idx + 5:idx + msgsize_total], msgsize - 1, "peer init", conn_obj.sock)

                if msg is not None:
                    if msg_class is PierceFireWall:
                        log.add_conn(("Received indirect connection response (PierceFireWall) with token "
                                      "%(token)s, address %(addr)s"), {
                            "token": msg.token,
                            "addr": conn_obj.addr
                        })

                        log.add_conn("List of stored PeerInit messages: %s", str(self._init_msgs))
                        log.add_conn("Attempting to fetch PeerInit message for token %s", msg.token)

                        conn_obj.init = init = self._init_msgs.pop(msg.token, None)

                        if init is None:
                            log.add_conn(("Indirect connection attempt with token %s previously expired, "
                                          "closing connection"), msg.token)
                            conn_obj.ibuf = bytearray()
                            self.close_connection(self._conns, conn_obj.sock)
                            return

                        self.add_init_message(init)

                        init.sock = conn_obj.sock
                        self._out_indirect_conn_request_times.pop(init, None)

                        log.add_conn("Indirect connection to user %(user)s with token %(token)s established", {
                            "user": init.target_user,
                            "token": msg.token
                        })

                        conn_obj.indirect = True
                        self.process_conn_messages(init)

                    elif msg_class is PeerInit:
                        user = msg.target_user
                        conn_type = msg.conn_type
                        addr = conn_obj.addr

                        log.add_conn(("Received incoming direct connection of type %(type)s from user "
                                      "%(user)s %(addr)s"), {
                            'type': conn_type,
                            'user': user,
                            'addr': addr
                        })

                        self.replace_existing_connection(msg)

                        conn_obj.init = msg
                        conn_obj.init.addr = addr

                        self.add_init_message(msg)
                        self.process_conn_messages(msg)

                    self._callback_msgs.append(msg)

            else:
                if not conn_obj.indirect:
                    log.add_debug("Peer init message type %(type)i size %(size)i contents %(msg_buffer)s unknown", {
                        'type': msgtype,
                        'size': msgsize - 1,
                        'msg_buffer': msg_buffer[idx + 5:idx + msgsize_total]
                    })

                    conn_obj.ibuf = bytearray()
                    self.close_connection(self._conns, conn_obj.sock)
                    return

                break

            idx += msgsize_total
            buffer_len -= msgsize_total

        if idx:
            conn_obj.ibuf = msg_buffer[idx:]

    def process_peer_init_output(self, msg_obj):

        msg_class = msg_obj.__class__

        if msg_obj.sock not in self._conns:
            log.add_conn("Cannot send the message over the closed connection: %(type)s %(msg_obj)s", {
                'type': msg_class,
                'msg_obj': vars(msg_obj)
            })
            return

        # Pack peer init messages
        if msg_class is PierceFireWall:
            conn_obj = self._conns[msg_obj.sock]
            msg = self.pack_network_message(msg_obj)

            if msg is None:
                return

            conn_obj.obuf.extend(msg_obj.pack_uint32(len(msg) + 1))
            conn_obj.obuf.extend(msg_obj.pack_uint8(PEER_INIT_MESSAGE_CODES[msg_class]))
            conn_obj.obuf.extend(msg)

        elif msg_class is PeerInit:
            conn_obj = self._conns[msg_obj.sock]
            msg = self.pack_network_message(msg_obj)

            if msg is None:
                return

            if conn_obj.indirect:
                return

            conn_obj.obuf.extend(msg_obj.pack_uint32(len(msg) + 1))
            conn_obj.obuf.extend(msg_obj.pack_uint8(PEER_INIT_MESSAGE_CODES[msg_class]))
            conn_obj.obuf.extend(msg)

        self.modify_connection_events(conn_obj, selectors.EVENT_READ | selectors.EVENT_WRITE)

    """ Peer Connection """

    def init_peer_conn(self, msg_obj):

        conn_obj = None

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            events = selectors.EVENT_READ | selectors.EVENT_WRITE
            conn_obj = PeerConnection(sock=sock, addr=msg_obj.addr, events=events, init=msg_obj.init)

            sock.setblocking(False)

            if self.bindip:
                sock.bind((self.bindip, 0))

            elif self.interface:
                self.bind_to_network_interface(sock, self.interface)

            sock.connect_ex(msg_obj.addr)

            self.selector.register(sock, events)
            self._connsinprogress[sock] = conn_obj
            self._numsockets += 1

        except OSError as error:
            self.connect_error(error, conn_obj)
            self.close_socket(sock)

    def process_peer_input(self, conn_obj, msg_buffer):
        """ We have a "P" connection (p2p exchange), peer has sent us
        something, this function retrieves messages
        from the msg_buffer, creates message objects and returns them
        and the rest of the msg_buffer. """

        msg_buffer_mem = memoryview(msg_buffer)
        buffer_len = len(msg_buffer_mem)
        idx = 0
        search_result_received = False
        sock = conn_obj.sock

        # Peer messages are 8 bytes or greater in length
        while buffer_len >= 8:
            msgsize, msgtype = DOUBLE_UINT_UNPACK(msg_buffer_mem[idx:idx + 8])
            msgsize_total = msgsize + 4

            try:
                peer_class = PEER_MESSAGE_CLASSES[msgtype]

                if peer_class in (SharedFileList, UserInfoReply):
                    # Send progress to the main thread
                    self._callback_msgs.append(
                        MessageProgress(conn_obj.init.target_user, peer_class, buffer_len, msgsize_total))

            except KeyError:
                pass

            if msgsize_total > buffer_len or msgsize < 0:
                # Invalid message size or buffer is being filled
                break

            # Unpack peer messages
            if msgtype in PEER_MESSAGE_CLASSES:
                msg_class = PEER_MESSAGE_CLASSES[msgtype]
                msg = self.unpack_network_message(
                    msg_class, msg_buffer_mem[idx + 8:idx + msgsize_total], msgsize - 4, "peer", conn_obj.init)

                if msg_class is FileSearchResult:
                    search_result_received = True

                if msg is not None:
                    self._callback_msgs.append(msg)

            else:
                host, port = conn_obj.addr
                log.add_debug(("Peer message type %(type)s size %(size)i contents %(msg_buffer)s unknown, "
                               "from user: %(user)s, %(host)s:%(port)s"), {
                    'type': msgtype,
                    'size': msgsize - 4,
                    'msg_buffer': msg_buffer[idx + 8:idx + msgsize_total],
                    'user': conn_obj.init.target_user,
                    'host': host,
                    'port': port
                })

            idx += msgsize_total
            buffer_len -= msgsize_total

        if idx:
            conn_obj.ibuf = msg_buffer[idx:]

        if search_result_received and not self.socket_still_active(sock):
            # Forcibly close peer connection. Only used after receiving a search result,
            # as we need to get rid of peer connections before they pile up.

            self.close_connection(self._conns, sock)

    def process_peer_output(self, msg_obj):

        msg_class = msg_obj.__class__

        if msg_obj.init.sock not in self._conns:
            log.add_conn("Cannot send the message over the closed connection: %(type)s %(msg_obj)s", {
                'type': msg_class,
                'msg_obj': vars(msg_obj)
            })
            return

        # Pack peer messages
        msg = self.pack_network_message(msg_obj)

        if msg is None:
            return

        conn_obj = self._conns[msg_obj.init.sock]
        conn_obj.obuf.extend(msg_obj.pack_uint32(len(msg) + 4))
        conn_obj.obuf.extend(msg_obj.pack_uint32(PEER_MESSAGE_CODES[msg_class]))
        conn_obj.obuf.extend(msg)

        self.modify_connection_events(conn_obj, selectors.EVENT_READ | selectors.EVENT_WRITE)

    """ File Connection """

    def process_file_input(self, conn_obj, msg_buffer):
        """ We have a "F" connection (filetransfer), peer has sent us
        something, this function retrieves messages
        from the msg_buffer, creates message objects and returns them
        and the rest of the msg_buffer. """

        msg_buffer_mem = memoryview(msg_buffer)
        idx = 0

        if conn_obj.fileinit is None:
            msgsize = idx = 4
            msg = self.unpack_network_message(
                FileDownloadInit, msg_buffer_mem[:msgsize], msgsize, "file", conn_obj.init)

            if msg is not None and msg.token is not None:
                self._callback_msgs.append(msg)
                conn_obj.fileinit = msg

                self.total_downloads += 1
                self._calc_download_limit()

        elif conn_obj.filedown is not None:
            idx = conn_obj.filedown.leftbytes
            added_bytes = msg_buffer_mem[:idx]

            if added_bytes:
                try:
                    conn_obj.filedown.file.write(added_bytes)

                except (OSError, ValueError) as error:
                    self._callback_msgs.append(DownloadFileError(conn_obj.sock, conn_obj.filedown.file, error))
                    self.close_connection(self._conns, conn_obj.sock)

                added_bytes_len = len(added_bytes)
                self.total_download_bandwidth += added_bytes_len
                conn_obj.filedown.leftbytes -= added_bytes_len

            current_time = time.time()
            finished = (conn_obj.filedown.leftbytes == 0)

            if finished or (current_time - conn_obj.lastcallback) > 1:
                # We save resources by not sending data back to the NicotineCore
                # every time a part of a file is downloaded

                self._callback_msgs.append(copy.copy(conn_obj.filedown))
                conn_obj.lastcallback = current_time

            if finished:
                self.close_connection(self._conns, conn_obj.sock)

        elif conn_obj.fileupl is not None and conn_obj.fileupl.offset is None:
            msgsize = idx = 8
            msg = self.unpack_network_message(FileOffset, msg_buffer_mem[:msgsize], msgsize, "file", conn_obj.init)

            if msg is not None and msg.offset is not None:
                try:
                    conn_obj.fileupl.file.seek(msg.offset)
                    self.modify_connection_events(conn_obj, selectors.EVENT_READ | selectors.EVENT_WRITE)

                except (OSError, ValueError) as error:
                    self._callback_msgs.append(UploadFileError(conn_obj.sock, conn_obj.fileupl.file, error))
                    self.close_connection(self._conns, conn_obj.sock)

                conn_obj.fileupl.offset = msg.offset

        if idx:
            conn_obj.ibuf = msg_buffer[idx:]

    def process_file_output(self, msg_obj):

        msg_class = msg_obj.__class__

        if msg_obj.init.sock not in self._conns:
            log.add_conn("Cannot send the message over the closed connection: %(type)s %(msg_obj)s", {
                'type': msg_class,
                'msg_obj': vars(msg_obj)
            })
            return

        # Pack file messages
        if msg_class is FileUploadInit:
            msg = self.pack_network_message(msg_obj)

            if msg is None:
                return

            conn_obj = self._conns[msg_obj.init.sock]
            conn_obj.fileinit = msg_obj
            conn_obj.obuf.extend(msg)

            self.total_uploads += 1
            self._calc_upload_limit_function()

            self._callback_msgs.append(msg_obj)

        elif msg_class is FileOffset:
            msg = self.pack_network_message(msg_obj)

            if msg is None:
                return

            conn_obj = self._conns[msg_obj.init.sock]
            conn_obj.obuf.extend(msg)

        self.modify_connection_events(conn_obj, selectors.EVENT_READ | selectors.EVENT_WRITE)

    """ Distributed Connection """

    def verify_parent_connection(self, conn_obj):
        """ Verify that a connection is our current parent connection """

        if self.parent_socket is not None and conn_obj.sock != self.parent_socket:
            log.add_conn("Received a distributed message from user %s, who is not our parent. Closing connection.",
                         conn_obj.init.target_user)
            conn_obj.ibuf = bytearray()
            self.close_connection(self._conns, conn_obj.sock)
            return False

        return True

    def send_have_no_parent(self):
        """ Inform the server we have no parent. The server should either send
        us a PossibleParents message, or start sending us search requests. """

        self.parent_socket = None
        log.add_conn("We have no parent, requesting a new one")

        self._queue.append(HaveNoParent(True))
        self._queue.append(BranchRoot(self.server_username))
        self._queue.append(BranchLevel(0))

    def process_distrib_input(self, conn_obj, msg_buffer):
        """ We have a distributed network connection, parent has sent us
        something, this function retrieves messages
        from the msg_buffer, creates message objects and returns them
        and the rest of the msg_buffer. """

        msg_buffer_mem = memoryview(msg_buffer)
        buffer_len = len(msg_buffer_mem)
        idx = 0

        # Distributed messages are 5 bytes or greater in length
        while buffer_len >= 5:
            msgsize = UINT_UNPACK(msg_buffer_mem[idx:idx + 4])[0]
            msgsize_total = msgsize + 4

            if msgsize_total > buffer_len or msgsize < 0:
                # Invalid message size or buffer is being filled
                break

            msgtype = msg_buffer_mem[idx + 4]

            # Unpack distributed messages
            if msgtype in DISTRIBUTED_MESSAGE_CLASSES:
                msg_class = DISTRIBUTED_MESSAGE_CLASSES[msgtype]
                msg = self.unpack_network_message(
                    msg_class, msg_buffer_mem[idx + 5:idx + msgsize_total], msgsize - 1, "distrib", conn_obj.init)

                if msg is not None:
                    if msg_class is DistribSearch and not self.verify_parent_connection(conn_obj):
                        return

                    if msg_class is DistribEmbeddedMessage:
                        if not self.verify_parent_connection(conn_obj):
                            return

                        msg = self.unpack_embedded_message(msg)

                    elif msg_class is DistribBranchLevel:
                        if msg.value < 0:
                            # There are rare cases of parents sending a branch level value of -1,
                            # presumably buggy clients
                            log.add_conn(("Received an invalid branch level value %(level)s from user %(user)s. "
                                          "Closing connection.") % {"level": msg.value, "user": msg.init.target_user})
                            conn_obj.ibuf = bytearray()
                            self.close_connection(self._conns, conn_obj.sock)
                            return

                        if self.parent_socket is None and msg.init.target_user in self.potential_parents:
                            # We have a successful connection with a potential parent. Tell the server who
                            # our parent is, and stop requesting new potential parents.
                            self.parent_socket = conn_obj.sock

                            self._queue.append(HaveNoParent(False))
                            self._queue.append(BranchLevel(msg.value + 1))

                            log.add_conn("Adopting user %s as parent", msg.init.target_user)
                            log.add_conn("Our branch level is %s", msg.value + 1)

                        elif conn_obj.sock != self.parent_socket:
                            # Unwanted connection, close it
                            conn_obj.ibuf = bytearray()
                            self.close_connection(self._conns, conn_obj.sock)
                            return

                        else:
                            # Inform the server of our new branch level
                            self._queue.append(BranchLevel(msg.value + 1))
                            log.add_conn("Received a branch level update from our parent. Our new branch level is %s",
                                         msg.value + 1)

                    elif msg_class is DistribBranchRoot:
                        if not self.verify_parent_connection(conn_obj):
                            return

                        # Inform the server of our branch root
                        self._queue.append(BranchRoot(msg.user))
                        log.add_conn("Our branch root is user %s", msg.user)

                    if msg is not None:
                        self._callback_msgs.append(msg)

            else:
                log.add_debug("Distrib message type %(type)i size %(size)i contents %(msg_buffer)s unknown", {
                    'type': msgtype,
                    'size': msgsize - 1,
                    'msg_buffer': msg_buffer[idx + 5:idx + msgsize_total]
                })

                conn_obj.ibuf = bytearray()
                self.close_connection(self._conns, conn_obj.sock)
                return

            idx += msgsize_total
            buffer_len -= msgsize_total

        if idx:
            conn_obj.ibuf = msg_buffer[idx:]

    def process_distrib_output(self, msg_obj):

        msg_class = msg_obj.__class__

        if msg_obj.init.sock not in self._conns:
            log.add_conn("Cannot send the message over the closed connection: %(type)s %(msg_obj)s", {
                'type': msg_class,
                'msg_obj': vars(msg_obj)
            })
            return

        # Pack distributed messages
        msg = self.pack_network_message(msg_obj)

        if msg is None:
            return

        conn_obj = self._conns[msg_obj.init.sock]
        conn_obj.obuf.extend(msg_obj.pack_uint32(len(msg) + 1))
        conn_obj.obuf.extend(msg_obj.pack_uint8(DISTRIBUTED_MESSAGE_CODES[msg_class]))
        conn_obj.obuf.extend(msg)

        self.modify_connection_events(conn_obj, selectors.EVENT_READ | selectors.EVENT_WRITE)

    """ Internal Messages """

    def process_internal_messages(self, msg_obj):

        msg_class = msg_obj.__class__

        if msg_class is InitPeerConn:
            if self._numsockets < MAXSOCKETS:
                self.init_peer_conn(msg_obj)
            else:
                # Connection limit reached, re-queue
                self._queue.append(msg_obj)

        elif msg_class is ConnClose and msg_obj.sock in self._conns:
            sock = msg_obj.sock
            self.close_connection(self._conns, sock)

        elif msg_class is ConnCloseIP:
            self.close_connection_by_ip(msg_obj.addr)

        elif msg_class is ServerConnect:
            self.server_connect(msg_obj)

        elif msg_class is ServerDisconnect:
            self.manual_server_disconnect = True
            self.server_disconnect()

        elif msg_class is DownloadFile and msg_obj.sock in self._conns:
            self._conns[msg_obj.sock].filedown = msg_obj

        elif msg_class is UploadFile and msg_obj.sock in self._conns:
            self._conns[msg_obj.sock].fileupl = msg_obj

        elif msg_class is SetDownloadLimit:
            self._download_limit = msg_obj.limit * 1024
            self._calc_download_limit()

        elif msg_class is SetUploadLimit:
            if msg_obj.uselimit:
                if msg_obj.limitby:
                    self._calc_upload_limit_function = self._calc_upload_limit
                else:
                    self._calc_upload_limit_function = self._calc_upload_limit_by_transfer

            else:
                self._calc_upload_limit_function = self._calc_upload_limit_none

            self._upload_limit = msg_obj.limit * 1024
            self._calc_upload_limit_function()

        elif msg_class is SendNetworkMessage:
            self.send_message_to_peer(msg_obj.user, msg_obj.message, msg_obj.addr)

    """ Input/Output """

    def process_conn_incoming_messages(self, conn_obj):

        if conn_obj.sock is self.server_socket:
            self.process_server_input(conn_obj, conn_obj.ibuf)
            return

        init = conn_obj.init

        if init is None:
            self.process_peer_init_input(conn_obj, conn_obj.ibuf)
            return

        if init.conn_type == ConnectionType.PEER:
            self.process_peer_input(conn_obj, conn_obj.ibuf)

        elif init.conn_type == ConnectionType.FILE:
            self.process_file_input(conn_obj, conn_obj.ibuf)

        elif init.conn_type == ConnectionType.DISTRIBUTED:
            self.process_distrib_input(conn_obj, conn_obj.ibuf)

    def process_queue_messages(self):

        msgs = []

        while self._queue:
            msgs.append(self._queue.popleft())

        for msg_obj in msgs:
            if self.server_disconnected:
                # Disconnected from server, stop processing queue
                return

            msg_type = msg_obj.msgtype

            if msg_type == MessageType.INIT:
                self.process_peer_init_output(msg_obj)

            elif msg_type == MessageType.INTERNAL:
                self.process_internal_messages(msg_obj)

            elif msg_type == MessageType.PEER:
                self.process_peer_output(msg_obj)

            elif msg_type == MessageType.DISTRIBUTED:
                self.process_distrib_output(msg_obj)

            elif msg_type == MessageType.FILE:
                self.process_file_output(msg_obj)

            elif msg_type == MessageType.SERVER:
                self.process_server_output(msg_obj)

    def read_data(self, conn_obj):

        sock = conn_obj.sock

        # Check for a download limit
        if sock in self._dlimits:
            limit = self._dlimits[sock]
        else:
            limit = None

        conn_obj.lastactive = time.time()
        data = sock.recv(conn_obj.lastreadlength)
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

        sock = conn_obj.sock

        if sock in self._ulimits:
            limit = self._ulimits[sock]
        else:
            limit = None

        prev_active = conn_obj.lastactive
        conn_obj.lastactive = time.time()

        if conn_obj.obuf:
            if limit is None:
                bytes_send = sock.send(conn_obj.obuf)
            else:
                bytes_send = sock.send(conn_obj.obuf[:limit])

            conn_obj.obuf = conn_obj.obuf[bytes_send:]
        else:
            bytes_send = 0

        if self._is_upload(conn_obj) and conn_obj.fileupl is not None and conn_obj.fileupl.offset is not None:
            conn_obj.fileupl.sentbytes += bytes_send
            totalsentbytes = conn_obj.fileupl.offset + conn_obj.fileupl.sentbytes + len(conn_obj.obuf)

            try:
                size = conn_obj.fileupl.size

                if totalsentbytes < size:
                    bytestoread = int(max(4096, bytes_send * 1.2) / max(1, conn_obj.lastactive - prev_active)
                                      - len(conn_obj.obuf))

                    if bytestoread > 0:
                        read = conn_obj.fileupl.file.read(bytestoread)
                        conn_obj.obuf.extend(read)

                        self.modify_connection_events(conn_obj, selectors.EVENT_READ | selectors.EVENT_WRITE)

            except (OSError, ValueError) as error:
                self._callback_msgs.append(UploadFileError(sock, conn_obj.fileupl.file, error))
                self.close_connection(self._conns, sock)

            if bytes_send > 0:
                self.total_upload_bandwidth += bytes_send
                current_time = time.time()
                finished = (conn_obj.fileupl.offset + conn_obj.fileupl.sentbytes == size)

                if finished or (current_time - conn_obj.lastcallback) > 1:
                    # We save resources by not sending data back to the NicotineCore
                    # every time a part of a file is uploaded

                    self._callback_msgs.append(copy.copy(conn_obj.fileupl))
                    conn_obj.lastcallback = current_time

        if not conn_obj.obuf:
            # Nothing else to send, stop watching connection for writes
            self.modify_connection_events(conn_obj, selectors.EVENT_READ)

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

            current_time = time.time()

            # Send updated connection count to NicotineCore. Avoid sending too many
            # updates at once, if there are a lot of connections.
            if (current_time - self._last_conn_stat_time) >= 1:
                self._callback_msgs.append(
                    SetConnectionStats(self._numsockets, self.total_downloads, self.total_download_bandwidth,
                                       self.total_uploads, self.total_upload_bandwidth))

                self.total_download_bandwidth = 0
                self.total_upload_bandwidth = 0
                self._last_conn_stat_time = current_time

            # Process queue messages
            if self._queue:
                self.process_queue_messages()

            # Check which connections are ready to send/receive data
            try:
                key_events = self.selector.select(timeout=-1)
                input_list = {key.fileobj for key, event in key_events if event & selectors.EVENT_READ}
                output_list = {key.fileobj for key, event in key_events if event & selectors.EVENT_WRITE}

            except OSError as error:
                # Error recieved; terminate networking loop

                log.add("Major Socket Error: Networking terminated! %s", error)
                self.abort()
                break

            except ValueError as error:
                # Possibly opened too many sockets

                log.add("select ValueError: %s", error)
                time.sleep(0.1)

                self._callback_msgs.clear()
                continue

            # Manage incoming connections to listen socket
            if self._numsockets < MAXSOCKETS and not self.server_disconnected and self.listen_socket in input_list:
                try:
                    incsock, incaddr = self.listen_socket.accept()
                except Exception:
                    time.sleep(0.01)
                else:
                    events = selectors.EVENT_READ
                    incsock.setblocking(False)

                    self._conns[incsock] = PeerConnection(sock=incsock, addr=incaddr, events=events)
                    self._numsockets += 1
                    log.add_conn("Incoming connection from %s", str(incaddr))

                    # Event flags are modified to include 'write' in subsequent loops, if necessary.
                    # Don't do it here, otherwise connections may break.
                    self.selector.register(incsock, events)

            # Manage outgoing connections in progress
            for sock_in_progress, conn_obj in self._connsinprogress.copy().items():
                if (current_time - conn_obj.lastactive) > self.IN_PROGRESS_STALE_AFTER:
                    # Connection failed

                    self.connect_error("Timed out", conn_obj)
                    self.close_connection(self._connsinprogress, sock_in_progress, callback=False)
                    continue

                try:
                    if sock_in_progress in input_list:
                        # Check if the socket has any data for us
                        sock_in_progress.recv(1, socket.MSG_PEEK)

                    if sock_in_progress in output_list:
                        # Connection has been established

                        conn_obj.lastactive = time.time()

                        if sock_in_progress is self.server_socket:
                            self.establish_outgoing_server_connection(conn_obj)
                        else:
                            self.establish_outgoing_peer_connection(conn_obj)

                        del self._connsinprogress[sock_in_progress]

                except OSError as error:
                    self.connect_error(error, conn_obj)
                    self.close_connection(self._connsinprogress, sock_in_progress, callback=False)

            # Process read/write for active connections
            for sock, conn_obj in self._conns.copy().items():
                if (sock is not self.server_socket
                        and (current_time - conn_obj.lastactive) > self.CONNECTION_MAX_IDLE):
                    # No recent activity, peer connection is stale
                    self.close_connection(self._conns, sock)
                    continue

                if sock in input_list:
                    if self._is_download(conn_obj):
                        self.set_conn_speed_limit(sock, self._download_limit_split, self._dlimits)

                    try:
                        if not self.read_data(conn_obj):
                            # No data received, socket was likely closed remotely
                            self.close_connection(self._conns, sock)
                            continue

                    except OSError as error:
                        log.add_conn(("Cannot read data from connection %(addr)s, closing connection. "
                                      "Error: %(error)s"), {
                            "addr": conn_obj.addr,
                            "error": error
                        })
                        self.close_connection(self._conns, sock)
                        continue

                if conn_obj.ibuf:
                    self.process_conn_incoming_messages(conn_obj)

                if sock in output_list:
                    if self._is_upload(conn_obj):
                        self.set_conn_speed_limit(sock, self._upload_limit_split, self._ulimits)

                    try:
                        self.write_data(conn_obj)

                    except Exception as err:
                        log.add_conn("Cannot write data to connection %(addr)s, closing connection. Error: %(error)s", {
                            "addr": conn_obj.addr,
                            "error": err
                        })
                        self.close_connection(self._conns, sock)
                        continue

            # Inform the main thread
            if self._callback_msgs:
                self._core_callback(self._callback_msgs)
                self._callback_msgs.clear()

            # Reset transfer speed limits
            self._ulimits = {}
            self._dlimits = {}

            self._calc_loops_per_second()

            # Don't exhaust the CPU
            time.sleep(1 / 60)

        # Networking thread aborted
