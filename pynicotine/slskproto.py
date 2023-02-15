# COPYRIGHT (C) 2020-2022 Nicotine+ Contributors
# COPYRIGHT (C) 2008-2012 quinox <quinox@users.sf.net>
# COPYRIGHT (C) 2007-2009 daelstorm <daelstorm@gmail.com>
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

import errno
import selectors
import socket
import struct
import sys
import time

from threading import Thread

from pynicotine.events import events
from pynicotine.logfacility import log
from pynicotine.slskmessages import DISTRIBUTED_MESSAGE_CLASSES
from pynicotine.slskmessages import DISTRIBUTED_MESSAGE_CODES
from pynicotine.slskmessages import NETWORK_MESSAGE_EVENTS
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
from pynicotine.slskmessages import CloseConnection
from pynicotine.slskmessages import CloseConnectionIP
from pynicotine.slskmessages import ConnectionType
from pynicotine.slskmessages import ConnectToPeer
from pynicotine.slskmessages import DistribBranchLevel
from pynicotine.slskmessages import DistribBranchRoot
from pynicotine.slskmessages import DistribEmbeddedMessage
from pynicotine.slskmessages import DistribSearch
from pynicotine.slskmessages import DownloadFile
from pynicotine.slskmessages import EmbeddedMessage
from pynicotine.slskmessages import FileOffset
from pynicotine.slskmessages import FileDownloadInit
from pynicotine.slskmessages import FileUploadInit
from pynicotine.slskmessages import FileSearchResponse
from pynicotine.slskmessages import GetPeerAddress
from pynicotine.slskmessages import GetUserStats
from pynicotine.slskmessages import GetUserStatus
from pynicotine.slskmessages import HaveNoParent
from pynicotine.slskmessages import InitPeerConnection
from pynicotine.slskmessages import Login
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
from pynicotine.slskmessages import SetDownloadLimit
from pynicotine.slskmessages import SetUploadLimit
from pynicotine.slskmessages import SetWaitPort
from pynicotine.slskmessages import SharedFileListResponse
from pynicotine.slskmessages import UploadFile
from pynicotine.slskmessages import UserInfoResponse
from pynicotine.slskmessages import UserStatus
from pynicotine.slskmessages import increment_token
from pynicotine.upnp import UPnP


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

SIOCGIFADDR = 0x8915 if sys.platform == "linux" else 0xc0206921  # 0xc0206921 for *BSD, macOS
UINT_UNPACK = struct.Struct("<I").unpack
DOUBLE_UINT_UNPACK = struct.Struct("<II").unpack


class Connection:
    """ Holds data about a connection. sock is a socket object,
    addr is (ip, port) pair, ibuf and obuf are input and output msgBuffer,
    init is a PeerInit object (see slskmessages docstrings). """

    __slots__ = ("sock", "addr", "selector_events", "ibuf", "obuf", "lastactive", "lastreadlength")

    def __init__(self, sock=None, addr=None, selector_events=None):

        self.sock = sock
        self.addr = addr
        self.selector_events = selector_events
        self.ibuf = bytearray()
        self.obuf = bytearray()
        self.lastactive = time.time()
        self.lastreadlength = 100 * 1024


class ServerConnection(Connection):

    __slots__ = ("login",)

    def __init__(self, sock=None, addr=None, selector_events=None, login=None):

        super().__init__(sock, addr, selector_events)

        self.login = login


class PeerConnection(Connection):

    __slots__ = ("init", "fileinit", "filedown", "fileupl", "has_post_init_activity", "lastcallback")

    def __init__(self, sock=None, addr=None, selector_events=None, init=None):

        super().__init__(sock, addr, selector_events)

        self.init = init
        self.fileinit = None
        self.filedown = None
        self.fileupl = None
        self.has_post_init_activity = False
        self.lastcallback = time.time()


class SoulseekNetworkThread(Thread):
    """ This is a networking thread that actually does all the communication.
    It sends data to the core via a callback function and receives data via a deque object. """

    """ The server and peers send each other small binary messages that start
    with length and message code followed by the actual message data. """

    IN_PROGRESS_STALE_AFTER = 2
    CONNECTION_MAX_IDLE = 60
    CONNECTION_MAX_IDLE_GHOST = 10
    CONNECTION_BACKLOG_LENGTH = 4096
    SOCKET_READ_BUFFER_SIZE = 1048576
    SOCKET_WRITE_BUFFER_SIZE = 1048576
    SLEEP_MIN_IDLE = 0.016  # ~60 times per second

    def __init__(self, queue, user_addresses):
        """ queue is deque object that holds network messages from Core. """

        super().__init__(name="SoulseekNetworkThread")

        self.listenport = None
        self.upnp = None

        self._queue = queue
        self._user_addresses = user_addresses
        self._pending_init_msgs = {}
        self._token_init_msgs = {}
        self._username_init_msgs = {}
        self._should_process_queue = False
        self._want_abort = False

        self._selector = None
        self._listen_socket = None
        self._listen_port_range = None
        self._bound_ip = None
        self._interface = None

        self._server_socket = None
        self._server_address = None
        self._server_username = None
        self._server_timer = None
        self._server_timeout_value = -1
        self._manual_server_disconnect = False
        self._server_relogged = False

        self._parent_socket = None
        self._potential_parents = {}
        self._distrib_parent_min_speed = 0
        self._distrib_parent_speed_ratio = 1
        self._max_distrib_children = 10

        self._numsockets = 1
        self._last_conn_stat_time = 0

        self._conns = {}
        self._connsinprogress = {}
        self._out_indirect_conn_request_times = {}
        self._conn_timeouts_timer_id = None
        self._token = 0

        self._calc_upload_limit_function = self._calc_upload_limit_none
        self._upload_limit = 0
        self._download_limit = 0
        self._upload_limit_split = 0
        self._download_limit_split = 0
        self._ulimits = {}
        self._dlimits = {}
        self._total_uploads = 0
        self._total_downloads = 0
        self._total_download_bandwidth = 0
        self._total_upload_bandwidth = 0
        self._last_cycle_time = 0
        self._current_cycle_loop_count = 0
        self._last_cycle_loop_count = 0
        self._loops_per_second = 0

        for event_name, callback in (
            ("enable-message-queue", self._enable_message_queue),
            ("quit", self._quit),
            ("start", self.start)
        ):
            events.connect(event_name, callback)

    def _enable_message_queue(self):
        self._queue.clear()
        self._should_process_queue = True

    def _quit(self):
        self._want_abort = True

    """ General """

    def _create_listen_socket(self):

        self._listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, self.SOCKET_READ_BUFFER_SIZE)
        self._listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, self.SOCKET_WRITE_BUFFER_SIZE)
        self._listen_socket.setblocking(False)

        if not self._bind_listen_port():
            return False

        self._selector.register(self._listen_socket, selectors.EVENT_READ)
        return True

    def _close_listen_socket(self):

        if self._listen_socket is None:
            return

        self._selector.unregister(self._listen_socket)
        self._close_socket(self._listen_socket, shutdown=False)
        self._listen_socket = None
        self.listenport = None

    def _bind_listen_port(self):

        if self._interface and not self._bound_ip:
            try:
                self._bind_to_network_interface(self._listen_socket, self._interface)

            except OSError:
                log.add(_("Specified network interface '%s' is not available"), self._interface,
                        title=_("Unknown Network Interface"))
                return False

        ip_address = self._bound_ip or "0.0.0.0"

        for listenport in range(int(self._listen_port_range[0]), int(self._listen_port_range[1]) + 1):
            try:
                self._listen_socket.bind((ip_address, listenport))
                self._listen_socket.listen(self.CONNECTION_BACKLOG_LENGTH)
                self.listenport = listenport
                log.add(_("Listening on port: %i"), listenport)
                log.add_debug("Maximum number of concurrent connections (sockets): %i", MAXSOCKETS)
                return True

            except OSError as error:
                log.add_debug("Cannot listen on port %(port)s: %(error)s", {"port": listenport, "error": error})
                continue

        log.add(_("No listening port is available in the specified port range %s–%s"), self._listen_port_range,
                title=_("Listening Port Unavailable"))
        return False

    @staticmethod
    def _get_interface_ip_address(if_name):

        try:
            import fcntl
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            ip_if = fcntl.ioctl(sock.fileno(),
                                SIOCGIFADDR,
                                struct.pack("256s", if_name.encode()[:15]))

            ip_address = socket.inet_ntoa(ip_if[20:24])

        except ImportError:
            ip_address = None

        return ip_address

    def _bind_to_network_interface(self, sock, if_name):

        try:
            if sys.platform == "linux":
                sock.setsockopt(socket.SOL_SOCKET, 25, if_name.encode())
                self._bound_ip = None
                return

            if sys.platform == "darwin":
                sock.setsockopt(socket.IPPROTO_IP, 25, socket.if_nametoindex(if_name))
                self._bound_ip = None
                return

        except PermissionError:
            pass

        # System does not support changing the network interface
        # Retrieve the IP address of the interface, and bind to it instead
        self._bound_ip = self._get_interface_ip_address(if_name)

    def _find_local_ip_address(self):

        # Create a UDP socket
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as local_socket:

            # Use the interface we have selected
            if self._bound_ip:
                local_socket.bind((self._bound_ip, 0))

            elif self._interface:
                self._bind_to_network_interface(local_socket, self._interface)

            try:
                # Send a broadcast packet on a local address (doesn't need to be reachable,
                # but MacOS requires port to be non-zero)
                local_socket.connect(("10.255.255.255", 1))

                # This returns the "primary" IP on the local box, even if that IP is a NAT/private/internal IP
                ip_address = local_socket.getsockname()[0]

            except OSError:
                # Fall back to localhost
                ip_address = "127.0.0.1"

        return ip_address

    def _server_connect(self, msg_obj):
        """ We're connecting to the server """

        if self._server_socket:
            return

        if sys.platform == "win32":
            # TODO: support custom network interface on Windows
            self._interface = None
        else:
            self._interface = msg_obj.interface

        self._bound_ip = msg_obj.bound_ip
        self._listen_port_range = msg_obj.listen_port_range

        if not self._create_listen_socket():
            self._should_process_queue = False
            return

        self._manual_server_disconnect = False
        events.cancel_scheduled(self._server_timer)

        ip_address, port = msg_obj.addr
        log.add(_("Connecting to %(host)s:%(port)s"), {"host": ip_address, "port": port})

        self._init_server_conn(msg_obj)

    def _server_disconnect(self):
        """ We're disconnecting from the server, clean up """

        self._should_process_queue = False
        self._bound_ip = self._interface = self._listen_port_range = self._server_socket = None

        self._close_listen_socket()
        self.upnp.cancel_timer()

        for sock in self._conns.copy():
            self._close_connection(self._conns, sock, callback=False)

        for sock in self._connsinprogress.copy():
            self._close_connection(self._connsinprogress, sock, callback=False)

        self._queue.clear()
        self._pending_init_msgs.clear()
        self._token_init_msgs.clear()
        self._username_init_msgs.clear()

        events.cancel_scheduled(self._conn_timeouts_timer_id)
        self._out_indirect_conn_request_times.clear()

        if self._want_abort:
            return

        # Reset connection stats
        events.emit_main_thread("set-connection-stats")

        if not self._server_address:
            # We didn't successfully establish a connection to the server
            return

        ip_address, port = self._server_address

        log.add(
            _("Disconnected from server %(host)s:%(port)s"), {
                "host": ip_address,
                "port": port
            })

        if self._server_relogged:
            log.add(_("Someone logged in to your Soulseek account elsewhere"))
            self._server_relogged = False

        if not self._manual_server_disconnect:
            self._set_server_timer()

        self._server_address = None
        self._server_username = None
        events.emit_main_thread("server-disconnect", self._manual_server_disconnect)

    def _server_timeout(self):
        events.emit_main_thread("server-timeout")

    def _set_server_timer(self):

        if self._server_timeout_value == -1:
            self._server_timeout_value = 15

        elif 0 < self._server_timeout_value < 600:
            self._server_timeout_value = self._server_timeout_value * 2

        self._server_timer = events.schedule(delay=self._server_timeout_value, callback=self._server_timeout)

        log.add(_("The server seems to be down or not responding, retrying in %i seconds"),
                self._server_timeout_value)

    """ File Transfers """

    @staticmethod
    def _is_upload(conn_obj):
        return conn_obj.__class__ is PeerConnection and conn_obj.fileupl is not None

    @staticmethod
    def _is_download(conn_obj):
        return conn_obj.__class__ is PeerConnection and conn_obj.filedown is not None

    def _calc_upload_limit(self, limit_disabled=False, limit_per_transfer=False):

        limit = self._upload_limit
        loop_limit = 1024  # 1 KB/s is the minimum upload speed per transfer

        if limit_disabled or limit < loop_limit:
            self._upload_limit_split = 0
            return

        if not limit_per_transfer and self._total_uploads > 1:
            limit = limit // self._total_uploads

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

        if self._total_downloads > 1:
            limit = limit // self._total_downloads

        self._download_limit_split = int(limit)

    def _calc_loops_per_second(self, current_time):
        """ Calculate number of loops per second. This value is used to split the
        per-second transfer speed limit evenly for each loop. """

        if current_time - self._last_cycle_time >= 1:
            self._loops_per_second = (self._last_cycle_loop_count + self._current_cycle_loop_count) // 2

            self._last_cycle_loop_count = self._current_cycle_loop_count
            self._last_cycle_time = current_time
            self._current_cycle_loop_count = 0
        else:
            self._current_cycle_loop_count += 1

    def _set_conn_speed_limit(self, sock, limit, limits):

        limit = limit // (self._loops_per_second or 1)

        if limit > 0:
            limits[sock] = limit

    """ Connections """

    def _check_indirect_connection_timeouts(self):

        curtime = time.time()

        if self._out_indirect_conn_request_times:
            for init, request_time in self._out_indirect_conn_request_times.copy().items():
                username = init.target_user
                conn_type = init.conn_type

                if (curtime - request_time) >= 20 and self._out_indirect_conn_request_times.pop(init, None):
                    log.add_conn(("Indirect connect request of type %(type)s to user %(user)s with "
                                  "token %(token)s expired, giving up"), {
                        "type": conn_type,
                        "user": username,
                        "token": init.token
                    })

                    events.emit_main_thread("peer-connection-error", username, init.outgoing_msgs)

                    self._token_init_msgs.pop(init.token, None)
                    init.outgoing_msgs.clear()

    @staticmethod
    def _connection_still_active(conn_obj):

        init = conn_obj.init

        if init is not None and init.conn_type != "P":
            # Distributed and file connections are critical, always assume they are active
            return True

        return len(conn_obj.obuf) > 0 or len(conn_obj.ibuf) > 0

    def _has_existing_user_socket(self, user, conn_type):

        prev_init = self._username_init_msgs.get(user + conn_type)

        if prev_init is not None and prev_init.sock is not None:
            return True

        return False

    def _add_init_message(self, init):

        conn_type = init.conn_type

        if conn_type == ConnectionType.FILE:
            # File transfer connections are not unique or reused later
            return

        self._username_init_msgs[init.target_user + conn_type] = init

    @staticmethod
    def _pack_network_message(msg_obj):

        try:
            return msg_obj.make_network_message()

        except Exception:
            from traceback import format_exc
            log.add("Unable to pack message type %(msg_type)s. %(error)s",
                    {"msg_type": msg_obj.__class__, "error": format_exc()})

        return None

    @staticmethod
    def _unpack_network_message(msg_class, msg_buffer, msg_size, conn_type, conn=None):

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
                "conn_type": conn_type,
                "msg_type": msg_class,
                "size": msg_size,
                "msg_buffer": msg_buffer,
                "error": error
            })

        return None

    @staticmethod
    def _unpack_embedded_message(msg):
        """ This message embeds a distributed message. We unpack the distributed message and process it. """

        if msg.distrib_code not in DISTRIBUTED_MESSAGE_CLASSES:
            return None

        distrib_class = DISTRIBUTED_MESSAGE_CLASSES[msg.distrib_code]
        distrib_msg = distrib_class()
        distrib_msg.parse_network_message(msg.distrib_message)

        return distrib_msg

    def emit_network_message_event(self, msg):

        if msg is None:
            return

        log.add_msg_contents(msg)
        event_name = NETWORK_MESSAGE_EVENTS.get(msg.__class__)

        if event_name:
            events.emit_main_thread(event_name, msg)

    def _modify_connection_events(self, conn_obj, selector_events):

        if conn_obj.selector_events != selector_events:
            log.add_conn("Modifying selector events for connection to %(addr)s: %(events)s", {
                "addr": conn_obj.addr,
                "events": selector_events
            })
            self._selector.modify(conn_obj.sock, selector_events)
            conn_obj.selector_events = selector_events

    def _process_conn_messages(self, init):
        """ A connection is established with the peer, time to queue up our peer
        messages for delivery """

        msgs = init.outgoing_msgs

        for j in msgs:
            j.init = init
            self._queue.append(j)

        msgs.clear()

    @staticmethod
    def _verify_peer_connection_type(conn_type):

        if conn_type not in (ConnectionType.PEER, ConnectionType.FILE, ConnectionType.DISTRIBUTED):
            log.add_conn("Unknown connection type %s", str(conn_type))
            return False

        return True

    def _send_message_to_peer(self, user, message):

        conn_type = message.msgtype

        if not self._verify_peer_connection_type(conn_type):
            return

        # Check if there's already a connection for the specified username
        init = self._username_init_msgs.get(user + conn_type)

        if init is None and conn_type != ConnectionType.FILE:
            # Check if we have a pending PeerInit message (currently requesting user IP address)
            pending_init_msgs = self._pending_init_msgs.get(user, [])

            for msg in pending_init_msgs:
                if msg.conn_type == conn_type:
                    init = msg
                    break

        log.add_conn("Sending message of type %(type)s to user %(user)s", {
            "type": message.__class__,
            "user": user
        })

        if init is not None:
            log.add_conn("Found existing connection of type %(type)s for user %(user)s, using it.", {
                "type": conn_type,
                "user": user
            })

            init.outgoing_msgs.append(message)

            if init.sock is not None:
                # We have initiated a connection previously, and it's ready
                self._process_conn_messages(init)

        else:
            # This is a new peer, initiate a connection
            self._initiate_connection_to_peer(user, conn_type, message)

    def _initiate_connection_to_peer(self, user, conn_type, message=None, in_address=None):
        """ Prepare to initiate a connection with a peer """

        init = PeerInit(init_user=self._server_username, target_user=user, conn_type=conn_type)
        user_address = self._user_addresses.get(user)

        if in_address is not None:
            user_address = in_address

        elif user_address is not None:
            _ip_address, port = user_address

            if port == 0:
                # Port 0 means the user is likely bugged, ask the server for a new address
                user_address = None

        if message is not None:
            init.outgoing_msgs.append(message)

        if user_address is None:
            if user not in self._pending_init_msgs:
                self._pending_init_msgs[user] = []

            self._pending_init_msgs[user].append(init)
            self._queue.append(GetPeerAddress(user))

            log.add_conn("Requesting address for user %(user)s", {
                "user": user
            })

        else:
            init.addr = user_address
            self._connect_to_peer(user, user_address, init)

    def _connect_to_peer(self, user, addr, init):
        """ Initiate a connection with a peer """

        conn_type = init.conn_type

        if not self._verify_peer_connection_type(conn_type):
            return

        if self._has_existing_user_socket(user, conn_type):
            log.add_conn(("Direct connection of type %(type)s to user %(user)s %(addr)s requested, "
                          "but existing connection already exists"), {
                "type": conn_type,
                "user": user,
                "addr": addr
            })
            return

        if not init.indirect:
            # Also request indirect connection in case the user's port is closed
            self._connect_to_peer_indirect(init)

        self._add_init_message(init)
        self._queue.append(InitPeerConnection(addr, init))

        log.add_conn("Attempting direct connection of type %(type)s to user %(user)s %(addr)s", {
            "type": conn_type,
            "user": user,
            "addr": addr
        })

    def _connect_error(self, error, conn_obj):

        if conn_obj.sock is self._server_socket:
            server_address, port = conn_obj.addr

            log.add(
                _("Cannot connect to server %(host)s:%(port)s: %(error)s"), {
                    "host": server_address,
                    "port": port,
                    "error": error
                }
            )
            self._set_server_timer()
            return

        if not conn_obj.init.indirect:
            log.add_conn("Direct connection of type %(type)s to user %(user)s failed. Error: %(error)s", {
                "type": conn_obj.init.conn_type,
                "user": conn_obj.init.target_user,
                "error": error
            })
            return

        if conn_obj.init in self._out_indirect_conn_request_times:
            return

        log.add_conn(
            "Cannot respond to indirect connection request from user %(user)s. Error: %(error)s", {
                "user": conn_obj.init.target_user,
                "error": error
            })

    def _connect_to_peer_indirect(self, init):
        """ Send a message to the server to ask the peer to connect to us (indirect connection) """

        self._token = increment_token(self._token)

        username = init.target_user
        conn_type = init.conn_type
        init.token = self._token

        self._token_init_msgs[self._token] = init
        self._out_indirect_conn_request_times[init] = time.time()
        self._queue.append(ConnectToPeer(self._token, username, conn_type))

        log.add_conn("Attempting indirect connection to user %(user)s with token %(token)s", {
            "user": username,
            "token": self._token
        })

    def _establish_outgoing_peer_connection(self, conn_obj):

        sock = conn_obj.sock
        self._conns[sock] = conn_obj

        init = conn_obj.init
        user = init.target_user
        conn_type = init.conn_type
        token = init.token
        init.sock = sock

        log.add_conn(("Established outgoing connection of type %(type)s with user %(user)s. List of "
                      "outgoing messages: %(messages)s"), {
            "type": conn_type,
            "user": user,
            "messages": init.outgoing_msgs
        })

        if init.indirect:
            log.add_conn(("Responding to indirect connection request of type %(type)s from "
                          "user %(user)s, token %(token)s"), {
                "type": conn_type,
                "user": user,
                "token": token
            })
            self._queue.append(PierceFireWall(sock, token))

        else:
            # Direct connection established
            log.add_conn("Sending PeerInit message of type %(type)s to user %(user)s", {
                "type": conn_type,
                "user": user
            })
            self._queue.append(init)

            # Direct and indirect connections are attempted at the same time, clean up
            self._token_init_msgs.pop(token, None)

            if self._out_indirect_conn_request_times.pop(init, None):
                log.add_conn(("Stopping indirect connection attempt of type %(type)s to user "
                              "%(user)s"), {
                    "type": conn_type,
                    "user": user
                })

        self._process_conn_messages(init)

    def _establish_outgoing_server_connection(self, conn_obj):

        self._conns[self._server_socket] = conn_obj
        addr = conn_obj.addr

        log.add(
            _("Connected to server %(host)s:%(port)s, logging in…"), {
                "host": addr[0],
                "port": addr[1]
            }
        )

        login, password = conn_obj.login
        self._user_addresses[login] = (self._find_local_ip_address(), self.listenport)
        conn_obj.login = True

        self._server_address = addr
        self._server_username = login
        self._server_timeout_value = -1

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

        self._queue.append(SetWaitPort(self.listenport))

    def _replace_existing_connection(self, init):

        user = init.target_user
        conn_type = init.conn_type

        if user == self._server_username or not self._has_existing_user_socket(user, conn_type):
            return

        log.add_conn("Discarding existing connection of type %(type)s to user %(user)s", {
            "type": init.conn_type,
            "user": user
        })

        prev_init = self._username_init_msgs[user + conn_type]
        init.outgoing_msgs = prev_init.outgoing_msgs
        prev_init.outgoing_msgs = []

        self._close_connection(self._conns, prev_init.sock, callback=False)

    @staticmethod
    def _close_socket(sock, shutdown=True):

        # In certain cases, a shutdown isn't possible, e.g. if a connection wasn't established
        if shutdown:
            try:
                log.add_conn("Shutting down socket %s", sock)
                sock.shutdown(socket.SHUT_RDWR)

            except OSError as error:
                log.add_conn("Failed to shut down socket %(sock)s: %(error)s", {
                    "sock": sock,
                    "error": error
                })

        try:
            log.add_conn("Closing socket %s", sock)
            sock.close()

        except OSError as error:
            log.add_conn("Failed to close socket %(sock)s: %(error)s", {
                "sock": sock,
                "error": error
            })

    def _close_connection(self, connection_list, sock, callback=True):

        conn_obj = connection_list.pop(sock, None)

        if conn_obj is None:
            # Already removed
            return

        self._selector.unregister(sock)
        self._close_socket(sock, shutdown=(connection_list != self._connsinprogress))
        self._numsockets -= 1

        if conn_obj.__class__ is ServerConnection:
            # Disconnected from server, clean up connections and queue
            self._server_disconnect()
            return

        init = conn_obj.init

        if sock is self._parent_socket and self._should_process_queue:
            self._send_have_no_parent()

        elif self._is_download(conn_obj):
            self._total_downloads -= 1

            if not self._total_downloads:
                self._total_download_bandwidth = 0

            if callback:
                events.emit_main_thread("download-connection-closed", init.target_user, conn_obj.filedown.token)

            self._calc_download_limit()

        elif self._is_upload(conn_obj):
            self._total_uploads -= 1

            if not self._total_uploads:
                self._total_upload_bandwidth = 0

            if callback:
                timed_out = (time.time() - conn_obj.lastactive) > self.CONNECTION_MAX_IDLE
                events.emit_main_thread("upload-connection-closed", init.target_user, conn_obj.fileupl.token, timed_out)

            self._calc_upload_limit_function()

        elif init is not None:
            if callback:
                events.emit_main_thread("peer-connection-closed", init.target_user)

        else:
            # No peer init message present, nothing to do
            return

        conn_type = init.conn_type
        user = init.target_user

        log.add_conn("Removed connection of type %(type)s to user %(user)s %(addr)s", {
            "type": conn_type,
            "user": user,
            "addr": conn_obj.addr
        })

        init_key = user + conn_type
        user_init = self._username_init_msgs.get(init_key)

        if user_init is None:
            return

        log.add_conn("Removing PeerInit message of type %(type)s for user %(user)s %(addr)s", {
            "type": conn_type,
            "user": user,
            "addr": conn_obj.addr
        })

        if init is not user_init:
            # Don't remove init message if connection has been superseded
            log.add_conn("Cannot remove PeerInit message, since the connection has been superseded")
            return

        if connection_list is self._connsinprogress and user_init.sock is not None:
            # Outgoing connection failed, but an indirect connection was already established
            log.add_conn("Cannot remove PeerInit message, an indirect connection was already established previously")
            return

        del self._username_init_msgs[init_key]

    def _close_conn_in_progress_if_stale(self, conn_obj, sock, current_time):

        if (current_time - conn_obj.lastactive) > self.IN_PROGRESS_STALE_AFTER:
            # Connection failed
            self._connect_error("Timed out", conn_obj)
            self._close_connection(self._connsinprogress, sock, callback=False)

    def _close_connection_if_inactive(self, conn_obj, sock, current_time, num_sockets):

        if sock is self._server_socket:
            return

        if num_sockets >= MAXSOCKETS and not self._connection_still_active(conn_obj):
            # Connection limit reached, close connection if inactive
            self._close_connection(self._conns, sock)
            return

        time_diff = (current_time - conn_obj.lastactive)

        if not conn_obj.has_post_init_activity and time_diff > self.CONNECTION_MAX_IDLE_GHOST:
            # "Ghost" connections can appear when an indirect connection is established,
            # search results arrive, we close the connection, and the direct connection attempt
            # succeeds afterwrds. Since the peer already sent a search result message, this connection
            # idles without any messages ever being sent beyond PeerInit. Close it sooner than regular
            # idling connections to prevent connections from piling up.
            self._close_connection(self._conns, sock)

        elif time_diff > self.CONNECTION_MAX_IDLE:
            # No recent activity, peer connection is stale
            self._close_connection(self._conns, sock)

    def _close_connection_by_ip(self, ip_address):

        for sock, conn_obj in self._conns.copy().items():
            if conn_obj is None or sock is self._server_socket:
                continue

            addr = conn_obj.addr

            if ip_address == addr[0]:
                log.add_conn("Blocking peer connection to IP address %(ip)s:%(port)s", {
                    "ip": addr[0],
                    "port": addr[1]
                })
                self._close_connection(self._conns, sock)

    """ Server Connection """

    @staticmethod
    def _set_server_socket_keepalive(server_socket, idle=10, interval=2):
        """ Ensure we are disconnected from the server in case of connectivity issues,
        by sending TCP keepalive pings. Assuming default values are used, once we reach
        10 seconds of idle time, we start sending keepalive pings once every 2 seconds.
        If 10 failed pings have been sent in a row (20 seconds), the connection is presumed
        dead. """

        count = 10
        timeout_seconds = (idle + (interval * count))

        if hasattr(socket, "SO_KEEPALIVE"):
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)  # pylint: disable=no-member

        if hasattr(socket, "TCP_KEEPINTVL"):
            server_socket.setsockopt(socket.IPPROTO_TCP,
                                     socket.TCP_KEEPINTVL, interval)  # pylint: disable=no-member

        if hasattr(socket, "TCP_KEEPCNT"):
            server_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, count)  # pylint: disable=no-member

        if hasattr(socket, "TCP_KEEPIDLE"):
            server_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, idle)  # pylint: disable=no-member

        elif hasattr(socket, "TCP_KEEPALIVE"):
            # macOS fallback

            server_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPALIVE, idle)  # pylint: disable=no-member

        elif hasattr(socket, "SIO_KEEPALIVE_VALS"):
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

        if hasattr(socket, "TCP_USER_TIMEOUT"):
            server_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_USER_TIMEOUT, timeout_seconds * 1000)

    def _init_server_conn(self, msg_obj):

        try:
            self._server_socket = server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            selector_events = selectors.EVENT_READ | selectors.EVENT_WRITE
            conn_obj = ServerConnection(
                sock=server_socket, addr=msg_obj.addr, selector_events=selector_events, login=msg_obj.login)

            server_socket.setblocking(False)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, self.SOCKET_READ_BUFFER_SIZE)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, self.SOCKET_WRITE_BUFFER_SIZE)

            # Detect if our connection to the server is still alive
            self._set_server_socket_keepalive(server_socket)

            if self._bound_ip:
                server_socket.bind((self._bound_ip, 0))

            elif self._interface:
                self._bind_to_network_interface(server_socket, self._interface)

            server_socket.connect_ex(msg_obj.addr)

            self._selector.register(server_socket, selector_events)
            self._connsinprogress[server_socket] = conn_obj
            self._numsockets += 1

        except OSError as error:
            self._connect_error(error, conn_obj)
            self._close_socket(server_socket, shutdown=False)
            self._server_disconnect()

    def _process_server_input(self, conn_obj, msg_buffer):
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
                msg = self._unpack_network_message(
                    msg_class, msg_buffer_mem[idx + 8:idx + msgsize_total], msgsize - 4, "server")

                if msg is not None:
                    if msg_class is EmbeddedMessage:
                        msg = self._unpack_embedded_message(msg)

                    elif msg_class is Login:
                        if msg.success:
                            # Ensure listening port is open
                            self.upnp.local_ip_address, self.upnp.port = self._user_addresses[self._server_username]
                            self.upnp.add_port_mapping(blocking=True)

                            # Check for indirect connection timeouts
                            self._conn_timeouts_timer_id = events.schedule(
                                delay=1, callback=self._check_indirect_connection_timeouts, repeat=True
                            )

                            msg.username = self._server_username
                            self._queue.append(CheckPrivileges())

                            # Ask for a list of parents to connect to (distributed network)
                            self._send_have_no_parent()

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
                        self._connect_to_peer(user, addr, init)

                    elif msg_class is GetUserStatus:
                        if msg.status == UserStatus.OFFLINE:
                            # User went offline, reset stored IP address
                            if msg.user in self._user_addresses:
                                del self._user_addresses[msg.user]

                    elif msg_class is GetUserStats:
                        if msg.user == self._server_username:
                            self._max_distrib_children = msg.avgspeed // self._distrib_parent_speed_ratio

                    elif msg_class is GetPeerAddress:
                        user = msg.user
                        pending_init_msgs = self._pending_init_msgs.pop(msg.user, [])

                        if msg.port == 0:
                            log.add_conn(
                                "Server reported port 0 for user %(user)s", {
                                    "user": user
                                }
                            )

                        addr = (msg.ip_address, msg.port)
                        user_offline = (addr == ("0.0.0.0", 0))

                        for init in pending_init_msgs:
                            # We now have the IP address for a user we previously didn't know,
                            # attempt a direct connection to the peer/user
                            if user_offline:
                                events.emit_main_thread(
                                    "peer-connection-error", user, init.outgoing_msgs[:], is_offline=True)
                            else:
                                init.addr = addr
                                self._connect_to_peer(user, addr, init)

                        # We already store a local IP address for our username
                        if user != self._server_username and not user_offline:
                            self._user_addresses[msg.user] = addr

                    elif msg_class is Relogged:
                        self._manual_server_disconnect = True
                        self._server_relogged = True

                    elif msg_class is PossibleParents:
                        # Server sent a list of 10 potential parents, whose purpose is to forward us search requests.
                        # We attempt to connect to them all at once, since connection errors are fairly common.

                        self._potential_parents = msg.list
                        log.add_conn("Server sent us a list of %s possible parents", len(msg.list))

                        if self._parent_socket is None and self._potential_parents:
                            for user in self._potential_parents:
                                addr = self._potential_parents[user]

                                log.add_conn("Attempting parent connection to user %s", user)
                                self._initiate_connection_to_peer(user, ConnectionType.DISTRIBUTED, in_address=addr)

                    elif msg_class is ParentMinSpeed:
                        self._distrib_parent_min_speed = msg.speed

                    elif msg_class is ParentSpeedRatio:
                        self._distrib_parent_speed_ratio = msg.ratio

                    elif msg_class is ResetDistributed:
                        log.add_conn("Received a reset request for distributed network")

                        if self._parent_socket is not None:
                            self._close_connection(self._conns, self._parent_socket)

                        self._send_have_no_parent()

                    self.emit_network_message_event(msg)

            else:
                log.add_debug("Server message type %(type)i size %(size)i contents %(msg_buffer)s unknown", {
                    "type": msgtype,
                    "size": msgsize - 4,
                    "msg_buffer": msg_buffer[idx + 8:idx + msgsize_total]
                })

            idx += msgsize_total
            buffer_len -= msgsize_total

        if idx:
            conn_obj.ibuf = msg_buffer[idx:]

    def _process_server_output(self, msg_obj):

        msg_class = msg_obj.__class__

        if self._server_socket not in self._conns:
            log.add_conn("Cannot send the message over the closed connection: %(type)s %(msg_obj)s", {
                "type": msg_class,
                "msg_obj": msg_obj
            })
            return

        msg = self._pack_network_message(msg_obj)

        if msg is None:
            return

        conn_obj = self._conns[self._server_socket]
        conn_obj.obuf.extend(msg_obj.pack_uint32(len(msg) + 4))
        conn_obj.obuf.extend(msg_obj.pack_uint32(SERVER_MESSAGE_CODES[msg_class]))
        conn_obj.obuf.extend(msg)

        self._modify_connection_events(conn_obj, selectors.EVENT_READ | selectors.EVENT_WRITE)

    """ Peer Init """

    def _process_peer_init_input(self, conn_obj, msg_buffer):

        init = None
        msg_buffer_mem = memoryview(msg_buffer)
        buffer_len = len(msg_buffer_mem)
        idx = 0

        # Peer init messages are 8 bytes or greater in length
        while buffer_len >= 8 and init is None:
            msgsize = UINT_UNPACK(msg_buffer_mem[idx:idx + 4])[0]
            msgsize_total = msgsize + 4

            if msgsize_total > buffer_len or msgsize < 0:
                # Invalid message size or buffer is being filled
                conn_obj.has_post_init_activity = True
                break

            msgtype = msg_buffer_mem[idx + 4]

            # Unpack peer init messages
            if msgtype in PEER_INIT_MESSAGE_CLASSES:
                msg_class = PEER_INIT_MESSAGE_CLASSES[msgtype]
                msg = self._unpack_network_message(
                    msg_class, msg_buffer_mem[idx + 5:idx + msgsize_total], msgsize - 1, "peer init", conn_obj.sock)

                if msg is not None:
                    if msg_class is PierceFireWall:
                        log.add_conn(("Received indirect connection response (PierceFireWall) with token "
                                      "%(token)s, address %(addr)s"), {
                            "token": msg.token,
                            "addr": conn_obj.addr
                        })

                        log.add_conn("List of stored PeerInit messages: %s", str(self._token_init_msgs))
                        log.add_conn("Attempting to fetch PeerInit message for token %s", msg.token)

                        init = self._token_init_msgs.pop(msg.token, None)

                        if init is None:
                            log.add_conn(("Indirect connection attempt with token %s previously expired, "
                                          "closing connection"), msg.token)
                            conn_obj.ibuf = bytearray()
                            self._close_connection(self._conns, conn_obj.sock)
                            return None

                        self._add_init_message(init)

                        init.sock = conn_obj.sock
                        self._out_indirect_conn_request_times.pop(init, None)

                        log.add_conn("Indirect connection to user %(user)s with token %(token)s established", {
                            "user": init.target_user,
                            "token": msg.token
                        })

                        self._process_conn_messages(init)

                    elif msg_class is PeerInit:
                        user = msg.target_user
                        conn_type = msg.conn_type
                        addr = conn_obj.addr

                        log.add_conn(("Received incoming direct connection of type %(type)s from user "
                                      "%(user)s %(addr)s"), {
                            "type": conn_type,
                            "user": user,
                            "addr": addr
                        })

                        if not self._verify_peer_connection_type(conn_type):
                            conn_obj.ibuf = bytearray()
                            self._close_connection(self._conns, conn_obj.sock)
                            return None

                        self._replace_existing_connection(msg)

                        init = msg
                        init.addr = addr

                        self._add_init_message(msg)
                        self._process_conn_messages(msg)

                    self.emit_network_message_event(msg)

            else:
                log.add_debug("Peer init message type %(type)i size %(size)i contents %(msg_buffer)s unknown", {
                    "type": msgtype,
                    "size": msgsize - 1,
                    "msg_buffer": msg_buffer[idx + 5:idx + msgsize_total]
                })

                conn_obj.ibuf = bytearray()
                self._close_connection(self._conns, conn_obj.sock)
                return None

            idx += msgsize_total
            buffer_len -= msgsize_total

        if idx:
            conn_obj.ibuf = msg_buffer[idx:]

        return init

    def _process_peer_init_output(self, msg_obj):

        msg_class = msg_obj.__class__

        if msg_obj.sock not in self._conns:
            log.add_conn("Cannot send the message over the closed connection: %(type)s %(msg_obj)s", {
                "type": msg_class,
                "msg_obj": msg_obj
            })
            return

        # Pack peer init messages
        conn_obj = self._conns[msg_obj.sock]
        msg = self._pack_network_message(msg_obj)

        if msg is None:
            return

        conn_obj.obuf.extend(msg_obj.pack_uint32(len(msg) + 1))
        conn_obj.obuf.extend(msg_obj.pack_uint8(PEER_INIT_MESSAGE_CODES[msg_class]))
        conn_obj.obuf.extend(msg)

        self._modify_connection_events(conn_obj, selectors.EVENT_READ | selectors.EVENT_WRITE)

    """ Peer Connection """

    def _init_peer_connection(self, msg_obj):

        conn_obj = None

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            selector_events = selectors.EVENT_READ | selectors.EVENT_WRITE
            conn_obj = PeerConnection(sock=sock, addr=msg_obj.addr, selector_events=selector_events, init=msg_obj.init)

            sock.setblocking(False)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, self.SOCKET_READ_BUFFER_SIZE)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, self.SOCKET_WRITE_BUFFER_SIZE)

            if self._bound_ip:
                sock.bind((self._bound_ip, 0))

            elif self._interface:
                self._bind_to_network_interface(sock, self._interface)

            sock.connect_ex(msg_obj.addr)

            self._selector.register(sock, selector_events)
            self._connsinprogress[sock] = conn_obj
            self._numsockets += 1

        except OSError as error:
            self._connect_error(error, conn_obj)
            self._close_socket(sock, shutdown=False)

    def _process_peer_input(self, conn_obj, msg_buffer):
        """ We have a "P" connection (p2p exchange), peer has sent us
        something, this function retrieves messages
        from the msg_buffer, creates message objects and returns them
        and the rest of the msg_buffer. """

        msg_buffer_mem = memoryview(msg_buffer)
        buffer_len = len(msg_buffer_mem)
        idx = 0
        search_result_received = False

        # Peer messages are 8 bytes or greater in length
        while buffer_len >= 8:
            msgsize, msgtype = DOUBLE_UINT_UNPACK(msg_buffer_mem[idx:idx + 8])
            msgsize_total = msgsize + 4

            try:
                # Send progress to the main thread
                peer_class = PEER_MESSAGE_CLASSES[msgtype]

                if peer_class is SharedFileListResponse:
                    events.emit_main_thread(
                        "shared-file-list-progress", conn_obj.init.target_user, buffer_len, msgsize_total)

                elif peer_class is UserInfoResponse:
                    events.emit_main_thread(
                        "user-info-progress", conn_obj.init.target_user, buffer_len, msgsize_total)

            except KeyError:
                pass

            if msgsize_total > buffer_len or msgsize < 0:
                # Invalid message size or buffer is being filled
                break

            # Unpack peer messages
            if msgtype in PEER_MESSAGE_CLASSES:
                msg_class = PEER_MESSAGE_CLASSES[msgtype]
                msg = self._unpack_network_message(
                    msg_class, msg_buffer_mem[idx + 8:idx + msgsize_total], msgsize - 4, "peer", conn_obj.init)

                if msg_class is FileSearchResponse:
                    search_result_received = True

                self.emit_network_message_event(msg)

            else:
                host, port = conn_obj.addr
                log.add_debug(("Peer message type %(type)s size %(size)i contents %(msg_buffer)s unknown, "
                               "from user: %(user)s, %(host)s:%(port)s"), {
                    "type": msgtype,
                    "size": msgsize - 4,
                    "msg_buffer": msg_buffer[idx + 8:idx + msgsize_total],
                    "user": conn_obj.init.target_user,
                    "host": host,
                    "port": port
                })

            idx += msgsize_total
            buffer_len -= msgsize_total

        if idx:
            conn_obj.ibuf = msg_buffer[idx:]
            conn_obj.has_post_init_activity = True

        if search_result_received and not self._connection_still_active(conn_obj):
            # Forcibly close peer connection. Only used after receiving a search result,
            # as we need to get rid of peer connections before they pile up.

            self._close_connection(self._conns, conn_obj.sock)

    def _process_peer_output(self, msg_obj):

        msg_class = msg_obj.__class__

        if msg_obj.init.sock not in self._conns:
            log.add_conn("Cannot send the message over the closed connection: %(type)s %(msg_obj)s", {
                "type": msg_class,
                "msg_obj": msg_obj
            })
            return

        # Pack peer messages
        msg = self._pack_network_message(msg_obj)

        if msg is None:
            return

        conn_obj = self._conns[msg_obj.init.sock]
        conn_obj.obuf.extend(msg_obj.pack_uint32(len(msg) + 4))
        conn_obj.obuf.extend(msg_obj.pack_uint32(PEER_MESSAGE_CODES[msg_class]))
        conn_obj.obuf.extend(msg)

        conn_obj.has_post_init_activity = True
        self._modify_connection_events(conn_obj, selectors.EVENT_READ | selectors.EVENT_WRITE)

    """ File Connection """

    def _process_file_input(self, conn_obj, msg_buffer):
        """ We have a "F" connection (filetransfer), peer has sent us
        something, this function retrieves messages
        from the msg_buffer, creates message objects and returns them
        and the rest of the msg_buffer. """

        msg_buffer_mem = memoryview(msg_buffer)
        idx = 0

        if conn_obj.fileinit is None:
            # Note that this would technically be a FileUploadInit message if the remote user
            # uses the legacy file transfer system, where file upload connections are initiated
            # by the user that requested a download. We have no easy way of determining this.
            # Hence, we always assume that any incoming file init message is a
            # FileDownloadInit message. Do NOT use these messages to determine if the
            # transfer is a download or upload!

            msgsize = idx = 4
            msg = self._unpack_network_message(
                FileDownloadInit, msg_buffer_mem[:msgsize], msgsize, "file", conn_obj.init)

            if msg is not None and msg.token is not None:
                self.emit_network_message_event(msg)
                conn_obj.fileinit = msg

        elif conn_obj.filedown is not None:
            idx = conn_obj.filedown.leftbytes
            added_bytes = msg_buffer_mem[:idx]

            if added_bytes:
                try:
                    conn_obj.filedown.file.write(added_bytes)

                except (OSError, ValueError) as error:
                    events.emit_main_thread(
                        "download-file-error", conn_obj.filedown.token, conn_obj.filedown.file, error)
                    self._close_connection(self._conns, conn_obj.sock)

                added_bytes_len = len(added_bytes)
                self._total_download_bandwidth += added_bytes_len
                conn_obj.filedown.leftbytes -= added_bytes_len

            current_time = time.time()
            finished = (conn_obj.filedown.leftbytes == 0)

            if finished or (current_time - conn_obj.lastcallback) > 1:
                # We save resources by not sending data back to core
                # every time a part of a file is downloaded

                events.emit_main_thread("file-download-progress", conn_obj.filedown.init.target_user,
                                        conn_obj.filedown.token, conn_obj.filedown.leftbytes)
                conn_obj.lastcallback = current_time

            if finished:
                self._close_connection(self._conns, conn_obj.sock)

        elif conn_obj.fileupl is not None and conn_obj.fileupl.offset is None:
            msgsize = idx = 8
            msg = self._unpack_network_message(FileOffset, msg_buffer_mem[:msgsize], msgsize, "file", conn_obj.init)

            if msg is not None and msg.offset is not None:
                self.emit_network_message_event(msg)
                conn_obj.fileupl.offset = msg.offset

                try:
                    conn_obj.fileupl.file.seek(msg.offset)
                    self._modify_connection_events(conn_obj, selectors.EVENT_READ | selectors.EVENT_WRITE)

                except (OSError, ValueError) as error:
                    events.emit_main_thread("upload-file-error", conn_obj.fileupl.token, conn_obj.fileupl.file, error)
                    self._close_connection(self._conns, conn_obj.sock)

        if idx:
            conn_obj.ibuf = msg_buffer[idx:]
            conn_obj.has_post_init_activity = True

    def _process_file_output(self, msg_obj):

        msg_class = msg_obj.__class__

        if msg_obj.init.sock not in self._conns:
            log.add_conn("Cannot send the message over the closed connection: %(type)s %(msg_obj)s", {
                "type": msg_class,
                "msg_obj": msg_obj
            })
            return

        # Pack file messages
        if msg_class is FileUploadInit:
            msg = self._pack_network_message(msg_obj)

            if msg is None:
                return

            conn_obj = self._conns[msg_obj.init.sock]
            conn_obj.fileinit = msg_obj
            conn_obj.obuf.extend(msg)

            self.emit_network_message_event(msg_obj)

        elif msg_class is FileOffset:
            msg = self._pack_network_message(msg_obj)

            if msg is None:
                return

            conn_obj = self._conns[msg_obj.init.sock]
            conn_obj.obuf.extend(msg)

        conn_obj.has_post_init_activity = True
        self._modify_connection_events(conn_obj, selectors.EVENT_READ | selectors.EVENT_WRITE)

    """ Distributed Connection """

    def _verify_parent_connection(self, conn_obj):
        """ Verify that a connection is our current parent connection """

        if self._parent_socket is not None and conn_obj.sock != self._parent_socket:
            log.add_conn("Received a distributed message from user %s, who is not our parent. Closing connection.",
                         conn_obj.init.target_user)
            conn_obj.ibuf = bytearray()
            self._close_connection(self._conns, conn_obj.sock)
            return False

        return True

    def _send_have_no_parent(self):
        """ Inform the server we have no parent. The server should either send
        us a PossibleParents message, or start sending us search requests. """

        self._parent_socket = None
        log.add_conn("We have no parent, requesting a new one")

        self._queue.append(HaveNoParent(True))
        self._queue.append(BranchRoot(self._server_username))
        self._queue.append(BranchLevel(0))

    def _process_distrib_input(self, conn_obj, msg_buffer):
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
                conn_obj.has_post_init_activity = True
                break

            msgtype = msg_buffer_mem[idx + 4]

            # Unpack distributed messages
            if msgtype in DISTRIBUTED_MESSAGE_CLASSES:
                msg_class = DISTRIBUTED_MESSAGE_CLASSES[msgtype]
                msg = self._unpack_network_message(
                    msg_class, msg_buffer_mem[idx + 5:idx + msgsize_total], msgsize - 1, "distrib", conn_obj.init)

                if msg is not None:
                    if msg_class is DistribSearch and not self._verify_parent_connection(conn_obj):
                        return

                    if msg_class is DistribEmbeddedMessage:
                        if not self._verify_parent_connection(conn_obj):
                            return

                        msg = self._unpack_embedded_message(msg)

                    elif msg_class is DistribBranchLevel:
                        if msg.value < 0:
                            # There are rare cases of parents sending a branch level value of -1,
                            # presumably buggy clients
                            log.add_conn(("Received an invalid branch level value %(level)s from user %(user)s. "
                                          "Closing connection."), {"level": msg.value, "user": msg.init.target_user})
                            conn_obj.ibuf = bytearray()
                            self._close_connection(self._conns, conn_obj.sock)
                            return

                        if self._parent_socket is None and msg.init.target_user in self._potential_parents:
                            # We have a successful connection with a potential parent. Tell the server who
                            # our parent is, and stop requesting new potential parents.
                            self._parent_socket = conn_obj.sock

                            self._queue.append(HaveNoParent(False))
                            self._queue.append(BranchLevel(msg.value + 1))

                            log.add_conn("Adopting user %s as parent", msg.init.target_user)
                            log.add_conn("Our branch level is %s", msg.value + 1)

                        elif conn_obj.sock != self._parent_socket:
                            # Unwanted connection, close it
                            conn_obj.ibuf = bytearray()
                            self._close_connection(self._conns, conn_obj.sock)
                            return

                        else:
                            # Inform the server of our new branch level
                            self._queue.append(BranchLevel(msg.value + 1))
                            log.add_conn("Received a branch level update from our parent. Our new branch level is %s",
                                         msg.value + 1)

                    elif msg_class is DistribBranchRoot:
                        if not self._verify_parent_connection(conn_obj):
                            return

                        # Inform the server of our branch root
                        self._queue.append(BranchRoot(msg.user))
                        log.add_conn("Our branch root is user %s", msg.user)

                    self.emit_network_message_event(msg)

            else:
                log.add_debug("Distrib message type %(type)i size %(size)i contents %(msg_buffer)s unknown", {
                    "type": msgtype,
                    "size": msgsize - 1,
                    "msg_buffer": msg_buffer[idx + 5:idx + msgsize_total]
                })

                conn_obj.ibuf = bytearray()
                self._close_connection(self._conns, conn_obj.sock)
                return

            idx += msgsize_total
            buffer_len -= msgsize_total

        if idx:
            conn_obj.ibuf = msg_buffer[idx:]
            conn_obj.has_post_init_activity = True

    def _process_distrib_output(self, msg_obj):

        msg_class = msg_obj.__class__

        if msg_obj.init.sock not in self._conns:
            log.add_conn("Cannot send the message over the closed connection: %(type)s %(msg_obj)s", {
                "type": msg_class,
                "msg_obj": msg_obj
            })
            return

        # Pack distributed messages
        msg = self._pack_network_message(msg_obj)

        if msg is None:
            return

        conn_obj = self._conns[msg_obj.init.sock]
        conn_obj.obuf.extend(msg_obj.pack_uint32(len(msg) + 1))
        conn_obj.obuf.extend(msg_obj.pack_uint8(DISTRIBUTED_MESSAGE_CODES[msg_class]))
        conn_obj.obuf.extend(msg)

        conn_obj.has_post_init_activity = True
        self._modify_connection_events(conn_obj, selectors.EVENT_READ | selectors.EVENT_WRITE)

    """ Internal Messages """

    def _process_internal_messages(self, msg_obj):

        msg_class = msg_obj.__class__

        if msg_class is InitPeerConnection:
            if self._numsockets < MAXSOCKETS:
                self._init_peer_connection(msg_obj)
            else:
                # Connection limit reached, re-queue
                self._queue.append(msg_obj)

        elif msg_class is CloseConnection and msg_obj.sock in self._conns:
            sock = msg_obj.sock
            self._close_connection(self._conns, sock)

        elif msg_class is CloseConnectionIP:
            self._close_connection_by_ip(msg_obj.addr)

        elif msg_class is ServerConnect:
            self._server_connect(msg_obj)

        elif msg_class is ServerDisconnect:
            self._manual_server_disconnect = True
            self._server_disconnect()

        elif msg_class is DownloadFile:
            conn_obj = self._conns.get(msg_obj.init.sock)

            if conn_obj is not None:
                conn_obj.filedown = msg_obj

                self._total_downloads += 1
                self._calc_download_limit()
                self._process_conn_incoming_messages(conn_obj)

        elif msg_class is UploadFile:
            conn_obj = self._conns.get(msg_obj.init.sock)

            if conn_obj is not None:
                conn_obj.fileupl = msg_obj

                self._total_uploads += 1
                self._calc_upload_limit_function()
                self._process_conn_incoming_messages(conn_obj)

        elif msg_class is SetDownloadLimit:
            self._download_limit = msg_obj.limit * 1024
            self._calc_download_limit()

        elif msg_class is SetUploadLimit:
            if msg_obj.limit > 0:
                if msg_obj.limitby:
                    self._calc_upload_limit_function = self._calc_upload_limit
                else:
                    self._calc_upload_limit_function = self._calc_upload_limit_by_transfer
            else:
                self._calc_upload_limit_function = self._calc_upload_limit_none

            self._upload_limit = msg_obj.limit * 1024
            self._calc_upload_limit_function()

        elif msg_class is SendNetworkMessage:
            self._send_message_to_peer(msg_obj.user, msg_obj.message)

    """ Input/Output """

    def _process_ready_input_socket(self, sock, current_time):

        if sock is self._listen_socket:
            # Manage incoming connections to listening socket
            while self._numsockets < MAXSOCKETS:
                try:
                    incoming_sock, incoming_addr = sock.accept()

                except OSError as error:
                    if error.errno == errno.EAGAIN:
                        # No more incoming connections
                        break

                    log.add_conn("Incoming connection failed: %s", error)
                    break

                selector_events = selectors.EVENT_READ
                incoming_sock.setblocking(False)

                self._conns[incoming_sock] = PeerConnection(
                    sock=incoming_sock, addr=incoming_addr, selector_events=selector_events
                )
                self._numsockets += 1
                log.add_conn("Incoming connection from %s", str(incoming_addr))

                # Event flags are modified to include 'write' in subsequent loops, if necessary.
                # Don't do it here, otherwise connections may break.
                self._selector.register(incoming_sock, selector_events)

            return

        conn_obj_in_progress = self._connsinprogress.get(sock)

        if conn_obj_in_progress is not None:
            try:
                # Check if the socket has any data for us
                sock.recv(1, socket.MSG_PEEK)

            except OSError as error:
                self._connect_error(error, conn_obj_in_progress)
                self._close_connection(self._connsinprogress, sock, callback=False)

            return

        conn_obj_established = self._conns.get(sock)

        if conn_obj_established is not None:
            if self._is_download(conn_obj_established):
                self._set_conn_speed_limit(sock, self._download_limit_split, self._dlimits)

            try:
                if not self._read_data(conn_obj_established, current_time):
                    # No data received, socket was likely closed remotely
                    self._close_connection(self._conns, sock)
                    return

            except OSError as error:
                log.add_conn(("Cannot read data from connection %(addr)s, closing connection. "
                              "Error: %(error)s"), {
                    "addr": conn_obj_established.addr,
                    "error": error
                })
                self._close_connection(self._conns, sock)
                return

            self._process_conn_incoming_messages(conn_obj_established)

    def _process_ready_output_socket(self, sock, current_time):

        conn_obj_in_progress = self._connsinprogress.get(sock)

        if conn_obj_in_progress is not None:
            try:
                # Connection has been established
                conn_obj_in_progress.lastactive = current_time

                if sock is self._server_socket:
                    self._establish_outgoing_server_connection(conn_obj_in_progress)
                else:
                    self._establish_outgoing_peer_connection(conn_obj_in_progress)

                del self._connsinprogress[sock]

            except OSError as error:
                self._connect_error(error, conn_obj_in_progress)
                self._close_connection(self._connsinprogress, sock, callback=False)

            return

        conn_obj_established = self._conns.get(sock)

        if conn_obj_established is not None:
            if self._is_upload(conn_obj_established):
                self._set_conn_speed_limit(sock, self._upload_limit_split, self._ulimits)

            try:
                self._write_data(conn_obj_established, current_time)

            except OSError as error:
                log.add_conn("Cannot write data to connection %(addr)s, closing connection. Error: %(error)s", {
                    "addr": conn_obj_established.addr,
                    "error": error
                })
                self._close_connection(self._conns, sock)

    def _process_ready_sockets(self, current_time):

        if self._listen_socket is None:
            # We can't call select() when no sockets are registered (WinError 10022)
            return

        for selector_key, selector_events in self._selector.select(timeout=-1):
            sock = selector_key.fileobj

            if selector_events & selectors.EVENT_READ:
                self._process_ready_input_socket(sock, current_time)

            if selector_events & selectors.EVENT_WRITE:
                self._process_ready_output_socket(sock, current_time)

    def _process_conn_incoming_messages(self, conn_obj):

        if not conn_obj.ibuf:
            return

        if conn_obj.sock is self._server_socket:
            self._process_server_input(conn_obj, conn_obj.ibuf)
            return

        init = conn_obj.init

        if init is None:
            conn_obj.init = init = self._process_peer_init_input(conn_obj, conn_obj.ibuf)

            if init is None or not conn_obj.ibuf:
                return

        if init.conn_type == ConnectionType.PEER:
            self._process_peer_input(conn_obj, conn_obj.ibuf)

        elif init.conn_type == ConnectionType.FILE:
            self._process_file_input(conn_obj, conn_obj.ibuf)

        elif init.conn_type == ConnectionType.DISTRIBUTED:
            self._process_distrib_input(conn_obj, conn_obj.ibuf)

    def _process_queue_messages(self):

        msgs = []

        while self._queue:
            msgs.append(self._queue.popleft())

        for msg_obj in msgs:
            if not self._should_process_queue:
                return

            msg_type = msg_obj.msgtype
            log.add_msg_contents(msg_obj, is_outgoing=True)

            if msg_type == MessageType.INIT:
                self._process_peer_init_output(msg_obj)

            elif msg_type == MessageType.INTERNAL:
                self._process_internal_messages(msg_obj)

            elif msg_type == MessageType.PEER:
                self._process_peer_output(msg_obj)

            elif msg_type == MessageType.DISTRIBUTED:
                self._process_distrib_output(msg_obj)

            elif msg_type == MessageType.FILE:
                self._process_file_output(msg_obj)

            elif msg_type == MessageType.SERVER:
                self._process_server_output(msg_obj)

    def _read_data(self, conn_obj, current_time):

        sock = conn_obj.sock
        limit = self._dlimits.get(sock)
        conn_obj.lastactive = current_time

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

    def _write_data(self, conn_obj, current_time):

        sock = conn_obj.sock
        limit = self._ulimits.get(sock)
        prev_active = conn_obj.lastactive
        conn_obj.lastactive = current_time

        if limit is None:
            bytes_send = sock.send(conn_obj.obuf)
        else:
            bytes_send = sock.send(conn_obj.obuf[:limit])

        conn_obj.obuf = conn_obj.obuf[bytes_send:]

        if self._is_upload(conn_obj) and conn_obj.fileupl.offset is not None:
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

                        self._modify_connection_events(conn_obj, selectors.EVENT_READ | selectors.EVENT_WRITE)

            except (OSError, ValueError) as error:
                events.emit_main_thread("upload-file-error", conn_obj.fileupl.token, conn_obj.fileupl.file, error)
                self._close_connection(self._conns, sock)

            # bytes_send can be zero if the offset equals the file size, check finished status here
            finished = (conn_obj.fileupl.offset + conn_obj.fileupl.sentbytes == size)

            if finished or bytes_send > 0:
                self._total_upload_bandwidth += bytes_send

                if finished or (current_time - conn_obj.lastcallback) > 1:
                    # We save resources by not sending data back to core
                    # every time a part of a file is uploaded

                    events.emit_main_thread("file-upload-progress", conn_obj.fileupl.init.target_user,
                                            conn_obj.fileupl.token, conn_obj.fileupl.offset, conn_obj.fileupl.sentbytes)
                    conn_obj.lastcallback = current_time

        if not conn_obj.obuf:
            # Nothing else to send, stop watching connection for writes
            self._modify_connection_events(conn_obj, selectors.EVENT_READ)

    """ Networking Loop """

    def run(self):

        events.emit_main_thread("set-connection-stats")
        self.upnp = UPnP()

        # Watch sockets for I/0 readiness with the selectors module. Only call register() after a socket
        # is bound, otherwise watching the socket not guaranteed to work (breaks on OpenBSD at least)
        self._selector = selectors.DefaultSelector()

        while not self._want_abort:

            if not self._should_process_queue:
                time.sleep(0.1)
                continue

            current_time = time.time()

            # Send updated connection count to core. Avoid sending too many
            # updates at once, if there are a lot of connections.
            if (current_time - self._last_conn_stat_time) >= 1:
                num_sockets = self._numsockets

                events.emit_main_thread("set-connection-stats", num_sockets, self._total_downloads,
                                        self._total_download_bandwidth, self._total_uploads,
                                        self._total_upload_bandwidth)

                # Close stale outgoing connection attempts
                for sock, conn_obj in self._connsinprogress.copy().items():
                    self._close_conn_in_progress_if_stale(conn_obj, sock, current_time)

                # Close inactive connections
                for sock, conn_obj in self._conns.copy().items():
                    self._close_connection_if_inactive(conn_obj, sock, current_time, num_sockets)

                self._total_download_bandwidth = 0
                self._total_upload_bandwidth = 0
                self._last_conn_stat_time = current_time

            # Process queue messages
            self._process_queue_messages()

            # Check which connections are ready to send/receive data
            self._process_ready_sockets(current_time)

            # Reset transfer speed limits
            self._ulimits = {}
            self._dlimits = {}

            self._calc_loops_per_second(current_time)

            # Don't exhaust the CPU
            time.sleep(self.SLEEP_MIN_IDLE)

        # Networking thread aborted
        self._manual_server_disconnect = True
        self._server_disconnect()
        self._selector.close()
