# COPYRIGHT (C) 2020-2024 Nicotine+ Contributors
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

import errno
import random
import selectors
import socket
import struct
import sys
import time

from collections import defaultdict
from collections import deque
from os import strerror
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
from pynicotine.slskmessages import DOUBLE_UINT32_UNPACK
from pynicotine.slskmessages import UINT32_UNPACK
from pynicotine.slskmessages import AcceptChildren
from pynicotine.slskmessages import BranchLevel
from pynicotine.slskmessages import BranchRoot
from pynicotine.slskmessages import CantConnectToPeer
from pynicotine.slskmessages import CloseConnection
from pynicotine.slskmessages import ConnectionType
from pynicotine.slskmessages import ConnectToPeer
from pynicotine.slskmessages import DistribBranchLevel
from pynicotine.slskmessages import DistribBranchRoot
from pynicotine.slskmessages import DistribEmbeddedMessage
from pynicotine.slskmessages import DistribSearch
from pynicotine.slskmessages import DownloadFile
from pynicotine.slskmessages import EmbeddedMessage
from pynicotine.slskmessages import EmitNetworkMessageEvents
from pynicotine.slskmessages import FileOffset
from pynicotine.slskmessages import FileSearchResponse
from pynicotine.slskmessages import FileTransferInit
from pynicotine.slskmessages import GetPeerAddress
from pynicotine.slskmessages import GetUserStats
from pynicotine.slskmessages import GetUserStatus
from pynicotine.slskmessages import HaveNoParent
from pynicotine.slskmessages import Login
from pynicotine.slskmessages import MessageType
from pynicotine.slskmessages import PossibleParents
from pynicotine.slskmessages import ParentMinSpeed
from pynicotine.slskmessages import ParentSpeedRatio
from pynicotine.slskmessages import PeerInit
from pynicotine.slskmessages import PierceFireWall
from pynicotine.slskmessages import Relogged
from pynicotine.slskmessages import ResetDistributed
from pynicotine.slskmessages import ServerConnect
from pynicotine.slskmessages import ServerDisconnect
from pynicotine.slskmessages import ServerReconnect
from pynicotine.slskmessages import SetDownloadLimit
from pynicotine.slskmessages import SetUploadLimit
from pynicotine.slskmessages import SetWaitPort
from pynicotine.slskmessages import SharedFileListResponse
from pynicotine.slskmessages import UnwatchUser
from pynicotine.slskmessages import UploadFile
from pynicotine.slskmessages import UserInfoResponse
from pynicotine.slskmessages import UserStatus
from pynicotine.slskmessages import WatchUser
from pynicotine.slskmessages import increment_token
from pynicotine.slskmessages import initial_token
from pynicotine.utils import human_speed


class Connection:
    __slots__ = ("sock", "addr", "io_events", "is_established", "in_buffer", "out_buffer",
                 "last_active", "recv_size")

    def __init__(self, sock=None, addr=None, io_events=None):

        self.sock = sock
        self.addr = addr
        self.io_events = io_events
        self.in_buffer = bytearray()
        self.out_buffer = bytearray()
        self.last_active = time.monotonic()
        self.recv_size = 51200
        self.is_established = False


class ServerConnection(Connection):
    __slots__ = ("login",)

    def __init__(self, *args, login=None, **kwargs):
        Connection.__init__(self, *args, **kwargs)
        self.login = login


class PeerConnection(Connection):
    __slots__ = ("init", "request_token", "response_token", "has_post_init_activity")

    def __init__(self, *args, init=None, request_token=None, response_token=None, **kwargs):

        Connection.__init__(self, *args, **kwargs)

        self.init = init
        self.request_token = request_token    # Requesting indirect connection to user
        self.response_token = response_token  # Responding to indirect connection request from user
        self.has_post_init_activity = False


class NetworkInterfaces:

    IP_BIND_ADDRESS_NO_PORT = SO_BINDTODEVICE = None

    if sys.platform == "win32":
        from ctypes import POINTER, Structure, wintypes

        AF_INET = 2

        GAA_FLAG_SKIP_ANYCAST = 2
        GAA_FLAG_SKIP_MULTICAST = 4
        GAA_FLAG_SKIP_DNS_SERVER = 8

        ERROR_BUFFER_OVERFLOW = 111

        class SockaddrIn(Structure):
            pass

        class SocketAddress(Structure):
            pass

        class IpAdapterUnicastAddress(Structure):
            pass

        class IpAdapterAddresses(Structure):
            pass

        SockaddrIn._fields_ = [  # pylint: disable=protected-access
            ("sin_family", wintypes.USHORT),
            ("sin_port", wintypes.USHORT),
            ("sin_addr", wintypes.BYTE * 4),
            ("sin_zero", wintypes.CHAR * 8)
        ]

        SocketAddress._fields_ = [  # pylint: disable=protected-access
            ("lp_sockaddr", POINTER(SockaddrIn)),
            ("i_sockaddr_length", wintypes.INT)
        ]

        IpAdapterUnicastAddress._fields_ = [  # pylint: disable=protected-access
            ("length", wintypes.ULONG),
            ("flags", wintypes.DWORD),
            ("next", POINTER(IpAdapterUnicastAddress)),
            ("address", SocketAddress)
        ]

        IpAdapterAddresses._fields_ = [  # pylint: disable=protected-access
            ("length", wintypes.ULONG),
            ("if_index", wintypes.DWORD),
            ("next", POINTER(IpAdapterAddresses)),
            ("adapter_name", wintypes.LPSTR),
            ("first_unicast_address", POINTER(IpAdapterUnicastAddress)),
            ("first_anycast_address", wintypes.LPVOID),
            ("first_multicast_address", wintypes.LPVOID),
            ("first_dns_server_address", wintypes.LPVOID),
            ("dns_suffix", wintypes.LPWSTR),
            ("description", wintypes.LPWSTR),
            ("friendly_name", wintypes.LPWSTR)
        ]

    elif sys.platform == "linux":
        IP_BIND_ADDRESS_NO_PORT = 24
        SIOCGIFADDR = 0x8915
        SO_BINDTODEVICE = 25

    elif sys.platform.startswith("sunos"):
        SIOCGIFADDR = -0x3fdf96f3  # Solaris

    else:
        SIOCGIFADDR = 0xc0206921   # macOS, *BSD

    @classmethod
    def _get_interface_addresses_win32(cls):
        """Returns a dictionary of network interface names and IP addresses (Win32).

        https://learn.microsoft.com/en-us/windows/win32/api/iphlpapi/nf-iphlpapi-getadaptersaddresses
        """

        # pylint: disable=invalid-name

        from ctypes import POINTER, byref, cast, create_string_buffer, windll, wintypes

        interface_addresses = {}
        adapter_addresses_size = wintypes.ULONG()
        return_value = cls.ERROR_BUFFER_OVERFLOW

        while return_value == cls.ERROR_BUFFER_OVERFLOW:
            p_adapter_addresses = cast(
                create_string_buffer(adapter_addresses_size.value), POINTER(cls.IpAdapterAddresses)
            )
            return_value = windll.Iphlpapi.GetAdaptersAddresses(
                cls.AF_INET,
                (cls.GAA_FLAG_SKIP_ANYCAST | cls.GAA_FLAG_SKIP_MULTICAST | cls.GAA_FLAG_SKIP_DNS_SERVER),
                None,
                p_adapter_addresses,
                byref(adapter_addresses_size),
            )

        if return_value:
            log.add_debug("Failed to get list of network interfaces. Error code %s", return_value)
            return interface_addresses

        while p_adapter_addresses:
            adapter_addresses = p_adapter_addresses.contents

            if adapter_addresses.first_unicast_address:
                interface_name = adapter_addresses.friendly_name
                socket_address = adapter_addresses.first_unicast_address[0].address
                interface_addresses[interface_name] = socket.inet_ntoa(socket_address.lp_sockaddr[0].sin_addr)

            p_adapter_addresses = adapter_addresses.next

        return interface_addresses

    @classmethod
    def _get_interface_addresses_posix(cls):
        """Returns a dictionary of network interface names and IP addresses
        (POSIX)"""

        interface_addresses = {}

        try:
            interface_name_index = socket.if_nameindex()

        except (AttributeError, OSError) as error:
            log.add_debug("Failed to get list of network interfaces: %s", error)
            return interface_addresses

        for _i, interface_name in interface_name_index:
            try:
                import fcntl

                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                    ip_interface = fcntl.ioctl(sock.fileno(),
                                               cls.SIOCGIFADDR,
                                               struct.pack("256s", interface_name.encode()[:15]))

                    ip_address = socket.inet_ntoa(ip_interface[20:24])
                    interface_addresses[interface_name] = ip_address

            except (ImportError, OSError) as error:
                log.add_debug("Failed to get IP address for network interface %s: %s", (interface_name, error))
                continue

        return interface_addresses

    @classmethod
    def get_interface_addresses(cls):
        """Returns a dictionary of network interface names and IP addresses."""

        if sys.platform == "win32":
            return cls._get_interface_addresses_win32()

        return cls._get_interface_addresses_posix()

    @classmethod
    def get_interface_address(cls, interface_name):
        """Returns the IP address of a specific network interface."""

        if not interface_name:
            return None

        return cls.get_interface_addresses().get(interface_name)

    @classmethod
    def bind_to_interface(cls, sock, interface_name, address):
        """Bind socket to the specified network interface name, if required on
        the current platform. Otherwise bind to the IP address of the network
        interface, retrieved from get_interface_addresses().
        """

        if cls.SO_BINDTODEVICE:
            try:
                # We need to use SO_BINDTODEVICE on Linux, since socket.bind() has no
                # effect on routing (weak host model).
                sock.setsockopt(socket.SOL_SOCKET, cls.SO_BINDTODEVICE, interface_name.encode())
                return

            except PermissionError as error:
                log.add_debug("Failed to bind socket to network interface with SO_BINDTODEVICE. "
                              "Falling back to socket.bind(). Error: %s", error)

                # We only need to bind to the interface address, not a port.
                # Set IP_BIND_ADDRESS_NO_PORT to avoid reserving an ephemeral port in bind(),
                # and let connect() select one instead later.
                sock.setsockopt(socket.SOL_IP, cls.IP_BIND_ADDRESS_NO_PORT, 1)

        sock.bind((address, 0))


class NetworkThread(Thread):
    """This is the networking thread that does all the communication with the
    Soulseek server and peers. Communication with the core is done through
    events.

    The server and peers send each other small binary messages that
    start with length and message code followed by the actual message
    data.
    """

    __slots__ = ("pending_shutdown", "upload_speed", "token", "_pending_network_msgs",
                 "_user_update_counter", "_user_update_counters", "_upload_queue_timer_id",
                 "_retry_failed_uploads_timer_id")

    IN_PROGRESS_STALE_AFTER = 2
    INDIRECT_REQUEST_TIMEOUT = 20
    CONNECTION_MAX_IDLE = 60
    CONNECTION_MAX_IDLE_GHOST = 10
    CONNECTION_BACKLOG_LENGTH = 65535      # OS limit can be lower
    MAX_INCOMING_MESSAGE_SIZE = 469762048  # 448 MiB, to leave headroom for large shares
    ALLOWED_PEER_CONN_TYPES = {
        ConnectionType.PEER,
        ConnectionType.FILE,
        ConnectionType.DISTRIBUTED
    }
    ERROR_NOT_CONNECTED = OSError(errno.ENOTCONN, strerror(errno.ENOTCONN))
    ERROR_TIMED_OUT = OSError(errno.ETIMEDOUT, strerror(errno.ETIMEDOUT))

    # Looping max ~240 times per second (SLEEP_MIN_IDLE) on high activity
    # ~20 (SLEEP_MAX_IDLE + SLEEP_MIN_IDLE) by default
    SLEEP_MAX_IDLE = 0.04584
    SLEEP_MIN_IDLE = 0.00416

    try:
        import resource

        # Increase the process file limit to a maximum of 10240 (macOS limit), to provide
        # breathing room for opening both peer sockets and regular files (file transfers,
        # log files etc.)

        _SOFT_FILE_LIMIT, HARD_FILE_LIMIT = resource.getrlimit(resource.RLIMIT_NOFILE)    # pylint: disable=no-member
        MAX_FILE_LIMIT = min(HARD_FILE_LIMIT, 10240)

        resource.setrlimit(resource.RLIMIT_NOFILE, (MAX_FILE_LIMIT, MAX_FILE_LIMIT))  # pylint: disable=no-member

        # Reserve 2/3 of the file limit for sockets, but always limit the maximum number
        # of sockets to 3072 to improve performance.

        MAX_SOCKETS = min(int(MAX_FILE_LIMIT * (2 / 3)), 3072)

    except ImportError:
        # For Windows, FD_SETSIZE is set to 512 in CPython.
        # This limit is hardcoded, so we'll have to live with it for now.
        # https://github.com/python/cpython/issues/72894

        MAX_SOCKETS = 512

    def __init__(self):

        super().__init__(name="NetworkThread")

        self._message_queue = deque()
        self._pending_peer_conns = {}
        self._pending_init_msgs = defaultdict(list)
        self._token_init_msgs = {}
        self._username_init_msgs = {}
        self._user_addresses = {}
        self._should_process_queue = False
        self._want_abort = False

        self._selector = None
        self._listen_socket = None
        self._listen_port = None
        self._interface_name = None
        self._interface_address = None
        self._portmapper = None
        self._local_ip_address = ""

        self._server_conn = None
        self._server_address = None
        self._server_username = None
        self._server_timeout_time = None
        self._server_timeout_value = -1
        self._manual_server_disconnect = False
        self._manual_server_reconnect = False
        self._server_relogged = False

        self._parent_conn = None
        self._potential_parents = {}
        self._child_peers = {}
        self._branch_level = 0
        self._branch_root = None
        self._is_server_parent = False
        self._distrib_parent_min_speed = 0
        self._distrib_parent_speed_ratio = 1
        self._max_distrib_children = 0
        self._upload_speed = 0

        self._num_sockets = 0
        self._last_cycle_time = 0

        self._conns = {}
        self._token = initial_token()

        self._file_init_msgs = {}
        self._file_download_msgs = {}
        self._file_upload_msgs = {}
        self._conns_downloaded = defaultdict(int)
        self._conns_uploaded = defaultdict(int)
        self._calc_upload_limit_function = self._calc_upload_limit_none
        self._upload_limit = 0
        self._download_limit = 0
        self._upload_limit_split = 0
        self._download_limit_split = 0
        self._total_uploads = 0
        self._total_downloads = 0
        self._total_download_bandwidth = 0
        self._total_upload_bandwidth = 0

        for event_name, callback in (
            ("enable-message-queue", self._enable_message_queue),
            ("queue-network-message", self._queue_network_message),
            ("schedule-quit", self._schedule_quit),
            ("start", self.start)
        ):
            events.connect(event_name, callback)

    def _enable_message_queue(self):
        self._should_process_queue = True

    def _queue_network_message(self, msg):
        if self._should_process_queue:
            self._message_queue.append(msg)

    def _schedule_quit(self):
        self._want_abort = True

    # Listening Socket #

    def _create_listen_socket(self):

        self._listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._listen_socket.setblocking(False)
        self._num_sockets += 1

        # On platforms other than Windows, SO_REUSEADDR is necessary to allow binding
        # to the same port immediately after reconnecting. This option behaves differently
        # on Windows, allowing other programs to hijack the port, so don't set it there.

        if sys.platform != "win32":
            self._listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        if not self._bind_listen_port():
            self._close_listen_socket()
            return False

        self._selector.register(self._listen_socket, selectors.EVENT_READ)
        return True

    def _close_listen_socket(self):

        if self._listen_socket is None:
            return

        try:
            self._selector.unregister(self._listen_socket)

        except KeyError:
            # Socket was not registered
            pass

        self._close_socket(self._listen_socket)
        self._listen_socket = None
        self._listen_port = None
        self._num_sockets -= 1

    def _bind_listen_port(self):

        if not self._bind_socket_interface(self._listen_socket):
            self._set_server_timer(use_fixed_timeout=True)
            log.add(_("Specified network interface '%s' is not available"), self._interface_name)
            return False

        try:
            ip_address = self._interface_address or self._find_local_ip_address()

            self._listen_socket.bind((ip_address, self._listen_port))
            self._listen_socket.listen(self.CONNECTION_BACKLOG_LENGTH)

        except OSError as error:
            self._set_server_timer(use_fixed_timeout=True)
            log.add(_("Cannot listen on port %(port)s. Ensure no other application uses it, or choose a "
                      "different port. Error: %(error)s"), {"port": self._listen_port, "error": error})
            self._listen_port = None
            return False

        self._local_ip_address = ip_address

        if self._interface_name:
            log.add_debug("Network interface: %s", self._interface_name)

        log.add_debug("Local IP address: %s", ip_address)
        log.add_debug("Maximum number of concurrent connections (sockets): %s", self.MAX_SOCKETS)
        log.add(_("Listening on port: %i"), self._listen_port)
        return True

    # Connections #

    def _indirect_request_error(self, token, init):

        username = init.target_user
        conn_type = init.conn_type

        log.add_conn("Indirect connect request of type %s to user %s with "
                     "token %s failed", (conn_type, username, token))

        if init.sock is not None:
            return

        # No direct connection was established, give up
        events.emit_main_thread(
            "peer-connection-error", username=username, conn_type=conn_type,
            msgs=init.outgoing_msgs[:]
        )
        init.outgoing_msgs.clear()
        self._username_init_msgs.pop(username + conn_type, None)

    def _check_indirect_request_timeouts(self, current_time=None, expire_all=False):

        if not self._token_init_msgs:
            return

        timed_out_requests = set()

        for token, (init, request_time) in self._token_init_msgs.items():
            if not expire_all and (current_time - request_time) < self.INDIRECT_REQUEST_TIMEOUT:
                continue

            self._indirect_request_error(token, init)
            timed_out_requests.add(token)

        if not timed_out_requests:
            return

        for token in timed_out_requests:
            del self._token_init_msgs[token]

        timed_out_requests.clear()

    def _is_connection_still_active(self, conn):

        init = conn.init

        if init is not None and (init.conn_type != "P" or init.target_user == self._server_username):
            # Distributed and file connections, as well as connections to ourselves,
            # are critical. Always assume they are active.
            return True

        return len(conn.out_buffer) > 0 or len(conn.in_buffer) > 0

    def _bind_socket_interface(self, sock):
        """Attempt to bind socket to an IP address, if provided with the
        --bindip CLI argument. Otherwise retrieve the IP address of the
        requested interface name, cache it for later, and bind to it.
        """

        if self._interface_address:
            if sock is not self._listen_socket:
                NetworkInterfaces.bind_to_interface(sock, self._interface_name, self._interface_address)

            return True

        if not self._interface_name:
            return True

        return False

    def _find_local_ip_address(self):

        # Create a UDP socket
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as local_socket:

            # Send a broadcast packet on a local address (doesn't need to be reachable,
            # but MacOS requires port to be non-zero)
            local_socket.connect_ex(("10.255.255.255", 1))

            # This returns the "primary" IP on the local box, even if that IP is a NAT/private/internal IP
            ip_address = local_socket.getsockname()[0]

        return ip_address

    def _add_init_message(self, init):

        conn_type = init.conn_type

        if conn_type == ConnectionType.FILE:
            # File transfer connections are not unique or reused later
            return True

        init_key = init.target_user + conn_type

        if init_key not in self._username_init_msgs:
            self._username_init_msgs[init_key] = init
            return True

        return False

    @staticmethod
    def _pack_network_message(msg):

        try:
            return msg.make_network_message()

        except Exception:
            from traceback import format_exc
            log.add("Unable to pack message type %s: %s", (msg.__class__, format_exc()))

        return None

    @staticmethod
    def _unpack_network_message(msg_class, msg_content, msg_size, conn_type, sock=None, addr=None, username=None):

        try:
            msg = msg_class()

            if sock is not None:
                msg.sock = sock

            if addr is not None:
                msg.addr = addr

            if username is not None:
                msg.username = username

            msg.parse_network_message(msg_content)
            return msg

        except Exception as error:
            log.add_debug("Unable to parse %s message type %s, size %s, contents %s. Error: %s",
                          (conn_type, msg_class, msg_size, msg_content, error))

        return None

    @staticmethod
    def _unpack_embedded_message(msg):
        """This message embeds a distributed message.

        We unpack the distributed message and process it.
        """

        msg_type = msg.distrib_code

        if msg_type not in DISTRIBUTED_MESSAGE_CLASSES:
            log.add_debug("Embedded distrib message type %s unknown", msg_type)
            return None

        distrib_class = DISTRIBUTED_MESSAGE_CLASSES[msg_type]
        unpacked_msg = distrib_class()
        unpacked_msg.parse_network_message(memoryview(msg.distrib_message))

        return unpacked_msg

    def _emit_network_message_event(self, msg):

        if msg is None:
            return

        msg_class = msg.__class__
        log.add_msg_contents(msg)

        if msg_class in NETWORK_MESSAGE_EVENTS:
            event_name = NETWORK_MESSAGE_EVENTS[msg_class]
            events.emit_main_thread(event_name, msg)

    def _modify_connection_events(self, conn, io_events):

        if conn.io_events != io_events:
            self._selector.modify(conn.sock, io_events)
            conn.io_events = io_events

    def _process_conn_messages(self, init):
        """A connection is established with the peer, time to queue up our peer
        messages for delivery."""

        username = init.target_user
        sock = init.sock
        msgs = init.outgoing_msgs

        for j in msgs:
            j.username = username
            j.sock = sock

        self._process_outgoing_messages(msgs)
        msgs.clear()

    def _send_message_to_peer(self, username, msg):

        conn_type = msg.msg_type

        if conn_type not in self.ALLOWED_PEER_CONN_TYPES:
            log.add_conn("Unknown connection type %s", conn_type)
            return

        init = None
        init_key = username + conn_type

        # Check if there's already a connection for the specified username
        if init_key in self._username_init_msgs:
            init = self._username_init_msgs[init_key]

        if init is None and conn_type != ConnectionType.FILE and username in self._pending_init_msgs:
            # Check if we have a pending PeerInit message (currently requesting user IP address)
            for pending_init in self._pending_init_msgs[username]:
                if pending_init.conn_type == conn_type:
                    init = pending_init
                    break

        if init is not None:
            log.add_conn("Sending message of type %s to user %s on existing connection",
                         (msg.__class__, username))

            init.outgoing_msgs.append(msg)

            if init.sock is not None and self._conns[init.sock].is_established:
                # We have initiated a connection previously, and it's ready
                self._process_conn_messages(init)

        else:
            log.add_conn("Sending message of type %s to user %s on new connection",
                         (msg.__class__, username))

            # This is a new peer, initiate a connection
            self._initiate_connection_to_peer(username, conn_type, msg)

    def _initiate_connection_to_peer(self, username, conn_type, msg=None, in_address=None):
        """Prepare to initiate a connection with a peer."""

        init = PeerInit(init_user=self._server_username, target_user=username, conn_type=conn_type)
        user_address = self._user_addresses.get(username)

        if in_address is not None:
            user_address = in_address

        elif user_address is not None:
            _ip_address, port = user_address

            if not port:
                # Port 0 means the user is likely bugged, ask the server for a new address
                user_address = None

        if msg is not None:
            init.outgoing_msgs.append(msg)

        if user_address is None:
            self._pending_init_msgs[username].append(init)
            self._send_message_to_server(GetPeerAddress(username))

            log.add_conn("Requesting address for user %s", username)
        else:
            self._connect_to_peer(username, user_address, init)

    def _connect_to_peer(self, username, addr, init, response_token=None):
        """Initiate a connection with a peer."""

        conn_type = init.conn_type

        if conn_type not in self.ALLOWED_PEER_CONN_TYPES:
            log.add_conn("Unknown connection type %s", conn_type)
            return

        if not self._add_init_message(init):
            log.add_conn("Direct connection of type %s to user %s (%s) requested, "
                         "but existing connection already exists", (conn_type, username, addr))
            return

        log.add_conn("Attempting direct connection of type %s to user %s, address %s",
                     (conn_type, username, addr))
        self._init_peer_connection(addr, init, response_token=response_token)

    def _connect_error(self, error, conn):

        if conn.__class__ is ServerConnection:
            server_address, port = conn.addr

            log.add(
                _("Cannot connect to server %(host)s:%(port)s: %(error)s"), {
                    "host": server_address,
                    "port": port,
                    "error": error
                }
            )
            self._set_server_timer()
            return

        conn_type = conn.init.conn_type
        username = conn.init.target_user
        response_token = conn.response_token

        if response_token is not None:
            log.add_conn("Cannot respond to indirect connection request of type %s from user %s, "
                         "token %s: %s", (conn_type, username, response_token, error))
            self._send_message_to_server(CantConnectToPeer(response_token, username))
            return

        log.add_conn("Direct connection of type %s to user %s failed: %s",
                     (conn_type, username, error))

    def _connect_to_peer_indirect(self, init):
        """Send a message to the server to ask the peer to connect to us
        (indirect connection)"""

        username = init.target_user
        conn_type = init.conn_type
        token = self._token = increment_token(self._token)
        request_time = time.monotonic()

        self._token_init_msgs[token] = (init, request_time)
        self._send_message_to_server(ConnectToPeer(token, username, conn_type))

        log.add_conn("Requesting indirect connection to user %s with token %s", (username, token))
        return token

    def _establish_outgoing_peer_connection(self, conn):

        conn.is_established = True
        init = conn.init
        sock = init.sock = conn.sock
        response_token = conn.response_token
        username = init.target_user
        conn_type = init.conn_type

        log.add_conn("Established outgoing connection of type %s with user %s. List of "
                     "outgoing messages: %s", (conn_type, username, init.outgoing_msgs))

        if response_token is not None:
            log.add_conn("Responding to indirect connection request of type %s from "
                         "user %s, token %s", (conn_type, username, response_token))
            self._process_outgoing_messages([PierceFireWall(sock, response_token)])
            self._accept_child_peer_connection(conn)
        else:
            log.add_conn("Sending peer init message of type %s to user %s", (conn_type, username))
            self._process_outgoing_messages([init])

        self._process_conn_messages(init)

    def _replace_existing_connection(self, init):

        username = init.target_user
        conn_type = init.conn_type

        if username == self._server_username:
            return

        prev_init = self._username_init_msgs.pop(username + conn_type, None)

        if prev_init is None or prev_init.sock is None:
            return

        log.add_conn("Discarding existing connection of type %s to user %s", (init.conn_type, username))

        init.outgoing_msgs = prev_init.outgoing_msgs
        prev_init.outgoing_msgs = []

        self._close_connection(self._conns[prev_init.sock])

    @staticmethod
    def _close_socket(sock):

        try:
            log.add_conn("Shutting down socket %s", sock)
            sock.shutdown(socket.SHUT_RDWR)

        except OSError as error:
            # Can't call shutdown if connection wasn't established, ignore error
            if error.errno != errno.ENOTCONN:
                log.add_conn("Failed to shut down socket %s: %s", (sock, error))

        log.add_conn("Closing socket %s", sock)
        sock.close()

    def _close_connection(self, conn):

        if conn is None:
            return

        sock = conn.sock
        del self._conns[sock]

        if conn is self._server_conn:
            # Disconnecting from server, clean up connections and queue
            self._server_disconnect()

        self._selector.unregister(sock)
        self._close_socket(sock)
        self._num_sockets -= 1

        conn.sock = None
        conn.in_buffer.clear()
        conn.out_buffer.clear()

        if conn.__class__ is not PeerConnection:
            return

        init = conn.init

        if init is None:
            # No peer init message present, nothing to do
            return

        conn_type = init.conn_type
        username = init.target_user
        addr = conn.addr
        is_connection_replaced = (init.sock is not sock)

        log.add_conn("Removed connection of type %s to user %s, address %s", (conn_type, username, addr))

        if not is_connection_replaced:
            init.sock = None

        if conn_type == ConnectionType.DISTRIBUTED:
            child_conn = self._child_peers.get(username)

            if child_conn is conn:
                self._remove_child_peer_connection(username)

            elif conn is self._parent_conn:
                self._send_have_no_parent()

        elif conn in self._file_init_msgs:
            file_init = self._file_init_msgs.pop(conn)

            if self._should_process_queue:
                timed_out = (time.monotonic() - conn.last_active) > self.CONNECTION_MAX_IDLE
                events.emit_main_thread(
                    "file-connection-closed", username=username, token=file_init.token,
                    sock=sock, timed_out=timed_out
                )

        if conn in self._file_download_msgs:
            del self._file_download_msgs[conn]
            self._total_downloads -= 1

            if not self._total_downloads:
                self._total_download_bandwidth = 0

            self._calc_download_limit()

        elif conn in self._file_upload_msgs:
            del self._file_upload_msgs[conn]
            self._total_uploads -= 1

            if not self._total_uploads:
                self._total_upload_bandwidth = 0

            self._calc_upload_limit_function()

        init_key = username + conn_type

        if init_key not in self._username_init_msgs:
            return

        log.add_conn("Removing peer init message of type %s for user %s, address %s",
                     (conn_type, username, addr))

        if is_connection_replaced or init is not self._username_init_msgs[init_key]:
            # Don't remove init message if connection has been superseded
            log.add_conn("Cannot remove peer init message, since the connection has been superseded")
            return

        if conn.request_token in self._token_init_msgs:
            # Indirect connection attempt in progress, remove init message later on timeout
            log.add_conn("Cannot remove peer init message, since an indirect connection attempt "
                         "is still in progress")
            return

        event_name = "peer-connection-closed" if conn.is_established else "peer-connection-error"
        events.emit_main_thread(
            event_name, username=username, conn_type=conn_type, msgs=init.outgoing_msgs[:])

        del self._username_init_msgs[init_key]

    def _is_connection_inactive(self, conn, current_time, num_sockets):

        if conn is self._server_conn:
            return False

        if num_sockets >= self.MAX_SOCKETS and not self._is_connection_still_active(conn):
            # Connection limit reached, close connection if inactive
            return True

        time_diff = (current_time - conn.last_active)

        if not conn.has_post_init_activity and time_diff > self.CONNECTION_MAX_IDLE_GHOST:
            # "Ghost" connections can appear when an indirect connection is established,
            # search results arrive, we close the connection, and the direct connection attempt
            # succeeds afterwrds. Since the peer already sent a search result message, this connection
            # idles without any messages ever being sent beyond PeerInit. Close it sooner than regular
            # idling connections to prevent connections from piling up.
            return True

        if time_diff > self.CONNECTION_MAX_IDLE:
            # No recent activity, peer connection is stale
            return True

        return False

    def _check_connections(self, current_time):

        num_sockets = self._num_sockets
        inactive_conns = set()
        stale_conns = set()

        for conn in self._conns.values():
            if not conn.is_established:
                if (current_time - conn.last_active) > self.IN_PROGRESS_STALE_AFTER:
                    stale_conns.add(conn)

            elif self._is_connection_inactive(conn, current_time, num_sockets):
                inactive_conns.add(conn)

            elif conn in self._file_download_msgs:
                file_download = self._file_download_msgs[conn]

                events.emit_main_thread(
                    "file-download-progress",
                    username=conn.init.target_user, token=file_download.token,
                    bytes_left=file_download.leftbytes, speed=file_download.speed
                )
                file_download.speed = 0

            elif conn in self._file_upload_msgs:
                file_upload = self._file_upload_msgs[conn]

                events.emit_main_thread(
                    "file-upload-progress",
                    username=conn.init.target_user, token=file_upload.token,
                    offset=file_upload.offset, bytes_sent=file_upload.sentbytes,
                    speed=file_upload.speed
                )
                file_upload.speed = 0

        if inactive_conns:
            for conn in inactive_conns:
                self._close_connection(conn)

            inactive_conns.clear()

        if stale_conns:
            for conn in stale_conns:
                self._connect_error(self.ERROR_TIMED_OUT, conn)
                self._close_connection(conn)

            stale_conns.clear()

        if self._pending_peer_conns:
            for addr, init in self._pending_peer_conns.copy().items():
                self._init_peer_connection(addr, init)

    # Server Connection #

    def _set_server_timer(self, use_fixed_timeout=False):

        if use_fixed_timeout:
            self._server_timeout_value = 5

        elif self._server_timeout_value == -1:
            # Add jitter to spread out connection attempts from Nicotine+ clients
            # in case server goes down
            self._server_timeout_value = random.randint(5, 15)

        elif 0 < self._server_timeout_value < 300:
            # Exponential backoff, max 5 minute wait
            self._server_timeout_value *= 2

        self._server_timeout_time = time.monotonic() + self._server_timeout_value
        log.add(_("Reconnecting to server in %s seconds"), self._server_timeout_value)

    @staticmethod
    def _set_server_socket_keepalive(sock, idle=10, interval=2):
        """Ensure we are disconnected from the server in case of connectivity
        issues, by sending TCP keepalive pings.

        Assuming default values are used, once we reach 10 seconds of
        idle time, we start sending keepalive pings once every 2
        seconds. If 10 failed pings have been sent in a row (20
        seconds), the connection is presumed dead.
        """

        count = 10
        timeout_seconds = (idle + (interval * count))

        if hasattr(socket, "SO_KEEPALIVE"):
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)  # pylint: disable=no-member

        if hasattr(socket, "TCP_KEEPINTVL"):
            sock.setsockopt(socket.IPPROTO_TCP,
                            socket.TCP_KEEPINTVL, interval)  # pylint: disable=no-member

        if hasattr(socket, "TCP_KEEPCNT"):
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, count)  # pylint: disable=no-member

        if hasattr(socket, "TCP_KEEPIDLE"):
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, idle)  # pylint: disable=no-member

        elif hasattr(socket, "TCP_KEEPALIVE"):
            # macOS fallback

            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPALIVE, idle)  # pylint: disable=no-member

        elif hasattr(socket, "SIO_KEEPALIVE_VALS"):
            # Windows fallback
            # Probe count is set to 10 on a system level, and can't be modified.
            # https://docs.microsoft.com/en-us/windows/win32/winsock/so-keepalive

            sock.ioctl(
                socket.SIO_KEEPALIVE_VALS,  # pylint: disable=no-member
                (
                    1,
                    idle * 1000,
                    interval * 1000
                )
            )

        if hasattr(socket, "TCP_USER_TIMEOUT"):
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_USER_TIMEOUT, timeout_seconds * 1000)

    def _server_connect(self, msg):
        """We're connecting to the server."""

        if self._server_conn is not None:
            return

        self._interface_name = msg.interface_name
        self._interface_address = (
            msg.interface_address or NetworkInterfaces.get_interface_address(self._interface_name)
        )
        self._listen_port = msg.listen_port

        if not self._create_listen_socket():
            self._should_process_queue = False
            events.emit_main_thread("set-connection-stats")  # Reset connection stats
            return

        self._portmapper = msg.portmapper

        self._manual_server_disconnect = False
        self._manual_server_reconnect = False
        self._server_timeout_time = None

        ip_address, port = msg.addr
        log.add(_("Connecting to %(host)s:%(port)s"), {"host": ip_address, "port": port})

        self._init_server_conn(msg)

    def _init_server_conn(self, msg):

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        io_events = selectors.EVENT_READ | selectors.EVENT_WRITE
        conn = ServerConnection(
            sock=sock, addr=msg.addr, io_events=io_events, login=msg.login
        )

        sock.setblocking(False)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

        # Detect if our connection to the server is still alive
        self._set_server_socket_keepalive(sock)

        try:
            self._bind_socket_interface(sock)
            sock.connect_ex(msg.addr)

        except OSError as error:
            self._connect_error(error, conn)
            self._close_socket(sock)
            self._server_disconnect()
            return

        self._server_conn = self._conns[sock] = conn
        self._selector.register(sock, io_events)
        self._num_sockets += 1

    def _establish_outgoing_server_connection(self, conn):

        conn.is_established = True
        server_hostname, server_port = conn.addr

        log.add(
            _("Connected to server %(host)s:%(port)s, logging in…"), {
                "host": server_hostname,
                "port": server_port
            }
        )

        login, password = conn.login
        self._user_addresses[login] = (self._local_ip_address, self._listen_port)
        conn.login = True

        self._server_address = conn.addr
        self._server_username = self._branch_root = login
        self._server_timeout_value = -1

        self._send_message_to_server(
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
                2
            )
        )

        self._send_message_to_server(SetWaitPort(self._listen_port))

    def _process_server_message(self, msg_type, msg_size, in_buffer, start_offset, end_offset):

        msg_class = SERVER_MESSAGE_CLASSES[msg_type]
        msg = self._unpack_network_message(
            msg_class,
            memoryview(in_buffer)[start_offset:end_offset],
            msg_size,
            conn_type="server"
        )

        if msg is None:
            # Ignore unknown message and keep connection open
            return True

        if msg_class is EmbeddedMessage:
            self._distribute_embedded_message(msg)
            msg = self._unpack_embedded_message(msg)

        elif msg_class is Login:
            if msg.success:
                # Ensure listening port is open
                msg.local_address = self._user_addresses[self._server_username]
                local_ip_address, port = msg.local_address
                self._portmapper.set_port(port, local_ip_address)
                self._portmapper.add_port_mapping(blocking=True)

                msg.username = self._server_username
                msg.server_address = self._server_address

                # Ask for a list of parents to connect to (distributed network)
                self._send_have_no_parent()
            else:
                # Emit event and close connection
                self._emit_network_message_event(msg)
                return False

        elif msg_class is ConnectToPeer:
            username = msg.user
            addr = (msg.ip_address, msg.port)
            conn_type = msg.conn_type
            token = msg.token
            init = PeerInit(init_user=username, target_user=username, conn_type=conn_type)

            log.add_conn("Received indirect connection request of type %s from user %s, "
                         "token %s, address %s", (conn_type, username, token, addr))

            self._connect_to_peer(username, addr, init, response_token=token)

        elif msg_class is CantConnectToPeer:
            token = msg.token

            if token in self._token_init_msgs:
                init, _request_time = self._token_init_msgs.pop(token)
                self._indirect_request_error(token, init)

        elif msg_class is GetUserStatus:
            if msg.status == UserStatus.OFFLINE and msg.user in self._user_addresses:
                # User went offline, reset stored IP address
                self._user_addresses[msg.user] = None

        elif msg_class is GetPeerAddress:
            username = msg.user
            pending_init_msgs = self._pending_init_msgs.pop(msg.user, [])

            if not msg.port:
                log.add_conn("Server reported port 0 for user %s", username)

            addr = (msg.ip_address, msg.port)
            user_offline = (msg.ip_address == "0.0.0.0")

            for init in pending_init_msgs:
                # We now have the IP address for a user we previously didn't know,
                # attempt a connection with the peer/user
                if user_offline:
                    events.emit_main_thread(
                        "peer-connection-error", username=username, conn_type=init.conn_type,
                        msgs=init.outgoing_msgs[:], is_offline=True)
                else:
                    self._connect_to_peer(username, addr, init)

            # We already store a local IP address for our username
            if username != self._server_username and username in self._user_addresses:
                if user_offline or not msg.port:
                    addr = None

                self._user_addresses[username] = addr

        elif msg_class in (WatchUser, GetUserStats):
            if msg.user == self._server_username:
                if msg.avgspeed is not None:
                    self._upload_speed = msg.avgspeed
                    log.add_conn("Server reported our upload speed as %s", human_speed(msg.avgspeed))
                    self._update_maximum_distributed_children()

            elif msg_class is WatchUser and not msg.userexists:
                self._user_addresses.pop(msg.user, None)

        elif msg_class is Relogged:
            self._manual_server_disconnect = True
            self._server_relogged = True

        elif msg_class is PossibleParents:
            # Server sent a list of 10 potential parents, whose purpose is to forward us search requests.
            # We attempt to connect to them all at once, since connection errors are fairly common.

            self._potential_parents = msg.list
            log.add_conn("Server sent us a list of %s possible parents", len(msg.list))

            if self._parent_conn is None and self._potential_parents:
                for username, addr in self._potential_parents.items():
                    log.add_conn("Attempting parent connection to user %s", username)
                    self._initiate_connection_to_peer(username, ConnectionType.DISTRIBUTED, in_address=addr)

        elif msg_class is ParentMinSpeed:
            self._distrib_parent_min_speed = msg.speed
            log.add_conn("Received minimum distributed parent speed %s from the server", msg.speed)
            self._update_maximum_distributed_children()

        elif msg_class is ParentSpeedRatio:
            self._distrib_parent_speed_ratio = msg.ratio
            log.add_conn("Received distributed parent speed ratio %s from the server", msg.ratio)
            self._update_maximum_distributed_children()

        elif msg_class is ResetDistributed:
            log.add_conn("Received a reset request for distributed network")

            if self._parent_conn is not None:
                self._close_connection(self._parent_conn)

            for child_conn in self._child_peers.copy().values():
                self._close_connection(child_conn)

            self._send_have_no_parent()

        self._emit_network_message_event(msg)
        return True

    def _process_server_input(self, conn):
        """Reads messages from the input buffer of a server connection."""

        in_buffer = conn.in_buffer
        buffer_len = len(in_buffer)
        msg_content_offset = 8
        idx = 0

        # Server messages are 8 bytes or greater in length
        while buffer_len >= msg_content_offset:
            msg_size, msg_type = DOUBLE_UINT32_UNPACK(in_buffer, idx)

            if msg_size > self.MAX_INCOMING_MESSAGE_SIZE:
                log.add_conn("Received message larger than maximum size %s from server. "
                             "Closing connection.", self.MAX_INCOMING_MESSAGE_SIZE)
                self._manual_server_disconnect = True
                self._close_connection(conn)
                return

            msg_size_total = msg_size + 4

            if msg_size_total > buffer_len:
                # Buffer is being filled
                break

            # Unpack server messages
            if msg_type in SERVER_MESSAGE_CLASSES:
                if not self._process_server_message(
                    msg_type, msg_size, in_buffer, idx + msg_content_offset, idx + msg_size_total
                ):
                    self._manual_server_disconnect = True
                    self._close_connection(conn)
                    return
            else:
                msg_content = in_buffer[idx + msg_content_offset:idx + min(50, msg_size_total)]
                log.add_debug("Server message type %s size %s contents %s unknown",
                              (msg_type, msg_size, msg_content))

            idx += msg_size_total
            buffer_len -= msg_size_total

        if idx:
            del in_buffer[:idx]

    def _process_server_output(self, msg):

        msg_content = self._pack_network_message(msg)

        if msg_content is None:
            return

        msg_class = msg.__class__

        if msg_class is WatchUser and msg.user not in self._user_addresses:
            # Only cache IP address of watched users, otherwise we won't know if
            # a user reconnects and changes their IP address.
            self._user_addresses[msg.user] = None

        elif msg_class is UnwatchUser and msg.user != self._server_username:
            self._user_addresses.pop(msg.user, None)

        conn = self._server_conn
        out_buffer = conn.out_buffer

        out_buffer += msg.pack_uint32(len(msg_content) + 4)
        out_buffer += msg.pack_uint32(SERVER_MESSAGE_CODES[msg_class])
        out_buffer += msg_content

        self._modify_connection_events(conn, selectors.EVENT_READ | selectors.EVENT_WRITE)

    def _server_disconnect(self):
        """We're disconnecting from the server, clean up."""

        self._server_conn = None
        self._should_process_queue = False
        self._interface_name = self._interface_address = None
        self._local_ip_address = ""

        self._close_listen_socket()

        if self._portmapper is not None:
            self._portmapper.remove_port_mapping(blocking=True)
            self._portmapper.set_port(port=None, local_ip_address=None)
            self._portmapper = None

        self._parent_conn = None
        self._potential_parents.clear()
        self._branch_level = 0
        self._branch_root = None
        self._is_server_parent = False
        self._distrib_parent_min_speed = 0
        self._distrib_parent_speed_ratio = 1
        self._max_distrib_children = 0
        self._upload_speed = 0
        self._user_addresses.clear()

        self._check_indirect_request_timeouts(expire_all=True)

        for conn in self._conns.copy().values():
            self._close_connection(conn)

        self._message_queue.clear()
        self._pending_peer_conns.clear()
        self._pending_init_msgs.clear()
        self._username_init_msgs.clear()

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
            self._set_server_timer(use_fixed_timeout=self._manual_server_reconnect)

        self._server_address = None
        self._server_username = None

        events.emit_main_thread(
            "server-disconnect",
            ServerDisconnect(manual_disconnect=self._manual_server_disconnect)
        )

    def _send_message_to_server(self, msg):
        self._process_outgoing_messages([msg])

    # Peer Init #

    def _process_peer_init_message(self, conn, msg_type, msg_size, in_buffer, start_offset, end_offset):

        msg_class = PEER_INIT_MESSAGE_CLASSES[msg_type]
        msg = self._unpack_network_message(
            msg_class,
            memoryview(in_buffer)[start_offset:end_offset],
            msg_size,
            conn_type="peer init",
            sock=conn.sock
        )

        if msg is None:
            return None

        if msg_class is PierceFireWall:
            token = msg.token
            log.add_conn("Received indirect connection response (PierceFireWall) with token "
                         "%s, address %s", (token, conn.addr))

            log.add_conn("Number of stored peer init message tokens: %s", len(self._token_init_msgs))

            if token not in self._token_init_msgs:
                log.add_conn("Indirect connection attempt with token %s previously expired, "
                             "closing connection", token)
                return None

            init, _request_time = self._token_init_msgs.pop(token)
            previous_sock = init.sock
            is_direct_conn_in_progress = (
                previous_sock is not None and not self._conns[previous_sock].is_established
            )

            log.add_conn("Indirect connection to user %s with token %s established",
                         (init.target_user, token))

            if previous_sock is None or is_direct_conn_in_progress:
                init.sock = conn.sock
                log.add_conn("Using as primary connection, since no direct connection is established")
            else:
                # We already have a direct connection, but some clients may send a message over
                # the indirect connection. Keep it open.
                log.add_conn("Direct connection was already established, keeping it as primary connection")

            if is_direct_conn_in_progress:
                log.add_conn("Stopping direct connection attempt to user %s", init.target_user)
                self._close_connection(self._conns[previous_sock])

        elif msg_class is PeerInit:
            username = msg.target_user
            conn_type = msg.conn_type
            addr = conn.addr

            log.add_conn("Received incoming direct connection of type %s from user "
                         "%s, address %s", (conn_type, username, addr))

            if conn_type not in self.ALLOWED_PEER_CONN_TYPES:
                log.add_conn("Unknown connection type %s", conn_type)
                return None

            init = msg
            self._replace_existing_connection(init)

        self._emit_network_message_event(msg)
        return init

    def _process_peer_init_input(self, conn):
        """Reads peer init messages from the input buffer of a peer connection."""

        init = None
        in_buffer = conn.in_buffer
        buffer_len = len(in_buffer)
        msg_content_offset = 5
        idx = 0

        # Peer init messages are 5 bytes or greater in length
        while buffer_len >= msg_content_offset and init is None:
            msg_size, = UINT32_UNPACK(in_buffer, idx)

            if msg_size > self.MAX_INCOMING_MESSAGE_SIZE:
                log.add_conn("Received message larger than maximum size %s from peer %s. "
                             "Closing connection.", (self.MAX_INCOMING_MESSAGE_SIZE, conn.addr))
                break

            msg_size_total = msg_size + 4

            if msg_size_total > buffer_len:
                # Buffer is being filled
                conn.has_post_init_activity = True
                break

            # Unpack peer init messages
            msg_type = in_buffer[idx + 4]

            if msg_type in PEER_INIT_MESSAGE_CLASSES:
                init = self._process_peer_init_message(
                    conn, msg_type, msg_size, in_buffer, idx + msg_content_offset, idx + msg_size_total)
            else:
                msg_content = in_buffer[idx + msg_content_offset:idx + min(50, msg_size_total)]
                log.add_debug("Peer init message type %s size %s contents %s unknown",
                              (msg_type, msg_size, msg_content))

            if init is None:
                break

            idx += msg_size_total
            buffer_len -= msg_size_total

        if init is None:
            self._close_connection(conn)
            return None

        if idx:
            del in_buffer[:idx]

        conn.init = init

        self._add_init_message(init)
        self._process_conn_messages(init)
        self._accept_child_peer_connection(conn)
        return init

    def _process_peer_init_output(self, msg):

        # Pack peer init messages
        conn = self._conns[msg.sock]
        msg_content = self._pack_network_message(msg)

        if msg_content is None:
            return

        out_buffer = conn.out_buffer

        out_buffer += msg.pack_uint32(len(msg_content) + 1)
        out_buffer += msg.pack_uint8(PEER_INIT_MESSAGE_CODES[msg.__class__])
        out_buffer += msg_content

        self._modify_connection_events(conn, selectors.EVENT_READ | selectors.EVENT_WRITE)

    # Peer Connection #

    def _accept_incoming_peer_connections(self):

        while self._num_sockets < self.MAX_SOCKETS:
            incoming_sock = None

            try:
                incoming_sock, incoming_addr = self._listen_socket.accept()
                incoming_sock.setblocking(False)
                incoming_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

            except OSError as error:
                if error.errno == errno.EWOULDBLOCK:
                    # No more incoming connections
                    break

                log.add_conn("Incoming connection failed: %s", error)

                if incoming_sock is not None:
                    self._close_socket(incoming_sock)

                continue

            io_events = selectors.EVENT_READ

            conn = self._conns[incoming_sock] = PeerConnection(
                sock=incoming_sock, addr=incoming_addr, io_events=io_events
            )
            self._num_sockets += 1

            # Event flags are modified to include 'write' in subsequent loops, if necessary.
            # Don't do it here, otherwise connections may break.
            self._selector.register(incoming_sock, io_events)
            conn.is_established = True

            log.add_conn("Incoming connection from address %s", (incoming_addr,))

    def _init_peer_connection(self, addr, init, response_token=None):

        if self._num_sockets >= self.MAX_SOCKETS:
            # Connection limit reached, re-queue
            self._pending_peer_conns[addr] = init
            return

        request_token = None
        _ip_address, port = addr
        self._pending_peer_conns.pop(addr, None)

        if response_token is None:
            # No token provided, we're not responding to an indirect connection request.
            # Request indirect connection from our end in case the user's port is closed.
            request_token = self._connect_to_peer_indirect(init)

        if port <= 0 or port > 65535:
            log.add_conn("Skipping direct connection attempt of type %s to user %s "
                         "due to invalid address %s", (init.conn_type, init.target_user, addr))
            return

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        io_events = selectors.EVENT_READ | selectors.EVENT_WRITE
        conn = PeerConnection(
            sock=sock, addr=addr, io_events=io_events,
            init=init, request_token=request_token, response_token=response_token
        )

        sock.setblocking(False)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

        try:
            self._bind_socket_interface(sock)
            sock.connect_ex(addr)

        except OSError as error:
            self._connect_error(error, conn)
            self._close_socket(sock)
            return

        init.sock = sock
        self._conns[sock] = conn
        self._selector.register(sock, io_events)
        self._num_sockets += 1

    def _process_peer_input(self, conn):
        """Reads messages from the input buffer of a 'P' connection."""

        in_buffer = conn.in_buffer
        buffer_len = len(in_buffer)
        msg_content_offset = 8
        idx = 0
        search_result_received = False

        # Peer messages are 8 bytes or greater in length
        while buffer_len >= msg_content_offset:
            msg_size, msg_type = DOUBLE_UINT32_UNPACK(in_buffer, idx)

            if msg_size > self.MAX_INCOMING_MESSAGE_SIZE:
                log.add_conn("Received message larger than maximum size %s from user %s. "
                             "Closing connection.", (self.MAX_INCOMING_MESSAGE_SIZE, conn.init.target_user))
                self._close_connection(conn)
                return

            msg_size_total = msg_size + 4
            msg_class = None

            if msg_type in PEER_MESSAGE_CLASSES:
                msg_class = PEER_MESSAGE_CLASSES[msg_type]

            # Send progress to the main thread
            if msg_class is SharedFileListResponse:
                events.emit_main_thread(
                    "shared-file-list-progress", conn.init.target_user, conn.sock, buffer_len, msg_size_total)

            elif msg_class is UserInfoResponse:
                events.emit_main_thread(
                    "user-info-progress", conn.init.target_user, conn.sock, buffer_len, msg_size_total)

            if msg_size_total > buffer_len:
                # Buffer is being filled
                break

            # Unpack peer messages
            if msg_class:
                msg = self._unpack_network_message(
                    msg_class,
                    memoryview(in_buffer)[idx + msg_content_offset:idx + msg_size_total],
                    msg_size,
                    conn_type="peer",
                    sock=conn.sock,
                    addr=conn.addr,
                    username=conn.init.target_user
                )

                if msg_class is FileSearchResponse:
                    search_result_received = True

                self._emit_network_message_event(msg)
            else:
                msg_content = in_buffer[idx + msg_content_offset:idx + min(50, msg_size_total)]
                log.add_debug("Peer message type %s size %s contents %s unknown, from user: %s, address %s",
                              (msg_type, msg_size, msg_content, conn.init.target_user, conn.addr))

            idx += msg_size_total
            buffer_len -= msg_size_total

        if idx:
            del in_buffer[:idx]
            conn.has_post_init_activity = True

        if search_result_received and not self._is_connection_still_active(conn):
            # Forcibly close peer connection. Only used after receiving a search result,
            # as we need to get rid of peer connections before they pile up.

            self._close_connection(conn)

    def _process_peer_output(self, msg):

        # Pack peer messages
        msg_content = self._pack_network_message(msg)

        if msg_content is None:
            return

        conn = self._conns[msg.sock]
        out_buffer = conn.out_buffer

        out_buffer += msg.pack_uint32(len(msg_content) + 4)
        out_buffer += msg.pack_uint32(PEER_MESSAGE_CODES[msg.__class__])
        out_buffer += msg_content

        conn.has_post_init_activity = True
        self._modify_connection_events(conn, selectors.EVENT_READ | selectors.EVENT_WRITE)

    # File Connection #

    def _calc_upload_limit(self, limit_disabled=False, limit_per_transfer=False):

        limit = self._upload_limit
        loop_limit = 1024  # 1 KB/s is the minimum upload speed per transfer

        if limit_disabled or limit < loop_limit:
            self._upload_limit_split = 0
            return

        if not limit_per_transfer and self._total_uploads > 1:
            limit //= self._total_uploads

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
            limit //= self._total_downloads

        self._download_limit_split = int(limit)

    def _process_file_init_message(self, conn, in_buffer):

        msg_size = idx = 4
        msg = self._unpack_network_message(
            FileTransferInit,
            memoryview(in_buffer)[:msg_size],
            msg_size,
            conn_type="file",
            sock=conn.sock,
            username=conn.init.target_user
        )

        if msg is not None and msg.token is not None:
            self._file_init_msgs[conn] = msg
            self._emit_network_message_event(msg)

        return idx

    def _process_file_offset_message(self, conn, in_buffer):

        file_upload = self._file_upload_msgs[conn]

        if file_upload.offset is not None:
            # No more incoming messages on this connection after receiving the
            # file offset. If peer sends something anyway, clear it.
            return len(in_buffer)

        msg_size = idx = 8
        msg = self._unpack_network_message(
            FileOffset,
            memoryview(in_buffer)[:msg_size],
            msg_size,
            conn_type="file",
            sock=conn.sock,
            username=conn.init.target_user
        )

        if msg is None or msg.offset is None:
            return idx

        file_upload.offset = msg.offset

        events.emit_main_thread(
            "file-upload-progress",
            username=conn.init.target_user, token=file_upload.token,
            offset=file_upload.offset, bytes_sent=file_upload.sentbytes
        )

        try:
            file_upload.file.seek(msg.offset)
            self._modify_connection_events(conn, selectors.EVENT_READ | selectors.EVENT_WRITE)

        except (OSError, ValueError) as error:
            events.emit_main_thread(
                "upload-file-error",
                username=conn.init.target_user, token=file_upload.token, error=error
            )
            self._close_connection(conn)
            return None

        return idx

    def _write_download_file(self, file_download, data, data_len):

        try:
            if not data:
                return

            file_download.speed += data_len
            self._total_download_bandwidth += data_len

            file_download.file.write(data)
            file_download.leftbytes -= data_len

        finally:
            # Release memoryview in case of critical error
            data = None

    def _process_download(self, conn, data, data_len):

        file_download = self._file_download_msgs[conn]
        idx = file_download.leftbytes

        try:
            if data_len > idx:
                self._write_download_file(file_download, memoryview(data)[:idx], idx)
            else:
                self._write_download_file(file_download, data, data_len)

        except (OSError, ValueError) as error:
            events.emit_main_thread(
                "download-file-error",
                username=conn.init.target_user, token=file_download.token, error=error
            )
            return False  # Close the connection

        # Download finished
        if file_download.leftbytes <= 0:
            events.emit_main_thread(
                "file-download-progress",
                username=conn.init.target_user, token=file_download.token,
                bytes_left=file_download.leftbytes
            )
            return False  # Close the connection

        return True

    def _process_upload(self, conn, num_sent_bytes, current_time):

        file_upload = self._file_upload_msgs[conn]

        if file_upload.offset is None:
            return True

        out_buffer = conn.out_buffer
        out_buffer_len = len(out_buffer)
        file_upload.sentbytes += num_sent_bytes
        total_read_bytes = file_upload.offset + file_upload.sentbytes + out_buffer_len
        size = file_upload.size

        try:
            if total_read_bytes < size:
                num_bytes_to_read = int(
                    (max(4096, num_sent_bytes * 1.25) / max(1, current_time - conn.last_active))
                    - out_buffer_len
                )
                if num_bytes_to_read > 0:
                    out_buffer += file_upload.file.read(num_bytes_to_read)
                    self._modify_connection_events(conn, selectors.EVENT_READ | selectors.EVENT_WRITE)

        except (OSError, ValueError) as error:
            events.emit_main_thread(
                "upload-file-error",
                username=conn.init.target_user, token=file_upload.token, error=error
            )
            return False  # Close the connection

        file_upload.speed += num_sent_bytes
        self._total_upload_bandwidth += num_sent_bytes

        # Upload finished
        if file_upload.offset + file_upload.sentbytes == size:
            events.emit_main_thread(
                "file-upload-progress",
                username=conn.init.target_user, token=file_upload.token,
                offset=file_upload.offset, bytes_sent=file_upload.sentbytes
            )
        return True

    def _process_file_input(self, conn):
        """Reads file messages from the input buffer of a 'F' connection."""

        in_buffer = conn.in_buffer
        idx = 0

        if conn not in self._file_init_msgs:
            idx = self._process_file_init_message(conn, in_buffer)

        elif conn in self._file_upload_msgs:
            idx = self._process_file_offset_message(conn, in_buffer)

        if idx:
            del in_buffer[:idx]
            conn.has_post_init_activity = True

    def _process_file_output(self, msg):

        msg_class = msg.__class__

        # Pack file messages
        if msg_class is FileTransferInit:
            msg_content = self._pack_network_message(msg)

            if msg_content is None:
                return

            conn = self._conns[msg.sock]
            self._file_init_msgs[conn] = msg
            conn.out_buffer += msg_content

            self._emit_network_message_event(msg)

        elif msg_class is FileOffset:
            msg_content = self._pack_network_message(msg)

            if msg_content is None:
                return

            conn = self._conns[msg.sock]
            conn.out_buffer += msg_content

        conn.has_post_init_activity = True
        self._modify_connection_events(conn, selectors.EVENT_READ | selectors.EVENT_WRITE)

    # Distributed Connection #

    def _accept_child_peer_connection(self, conn):

        if conn.init.conn_type != ConnectionType.DISTRIBUTED:
            return

        username = conn.init.target_user

        if username == self._server_username:
            # We can't connect to ourselves
            return

        if username in self._potential_parents:
            # This is not a child peer, ignore
            return

        if self._parent_conn is None and not self._is_server_parent:
            # We have no parent user and the server hasn't sent search requests, no point
            # in accepting child peers
            log.add_conn("Rejecting distributed child peer connection from user %s, since we have no parent", username)
            self._close_connection(conn)
            return

        if username in self._child_peers:
            log.add_conn("Rejecting distributed child peer connection from user %s, since an existing connection "
                         "already exists", username)
            self._close_connection(conn)
            return

        if len(self._child_peers) >= self._max_distrib_children:
            log.add_conn("Rejecting distributed child peer connection from user %s, since child peer limit "
                         "of %s was reached", (username, self._max_distrib_children))
            self._close_connection(conn)
            return

        self._child_peers[username] = conn
        self._send_message_to_peer(username, DistribBranchLevel(self._branch_level))

        if self._parent_conn is not None:
            # Only sent when we're not the branch root
            self._send_message_to_peer(username, DistribBranchRoot(self._branch_root))

        log.add_conn("Adopting user %s as distributed child peer. Number of current child peers: %s",
                     (username, len(self._child_peers)))

        if len(self._child_peers) >= self._max_distrib_children:
            log.add_conn("Maximum number of distributed child peers reached (%s), "
                         "no longer accepting new connections", self._max_distrib_children)
            self._send_message_to_server(AcceptChildren(False))

    def _remove_child_peer_connection(self, username):

        self._child_peers.pop(username, None)

        if not self._should_process_queue:
            return

        if len(self._child_peers) == self._max_distrib_children - 1:
            log.add_conn("Available to accept a new distributed child peer")
            self._send_message_to_server(AcceptChildren(True))

        log.add_conn("Number of current child peers: %s", len(self._child_peers))

    def _send_message_to_child_peers(self, msg):

        msg_class = msg.__class__
        msg_attrs = [getattr(msg, s) for s in msg.__slots__]
        msgs = []

        for conn in self._child_peers.values():
            msg_child = msg_class(*msg_attrs)
            msg_child.sock = conn.sock
            msgs.append(msg_child)

        self._process_outgoing_messages(msgs)

    def _distribute_embedded_message(self, msg):
        """Distributes an embedded message from the server to our child
        peers."""

        if self._parent_conn is not None:
            # The server shouldn't send embedded messages while it's not our parent, but let's be safe
            return

        self._send_message_to_child_peers(DistribEmbeddedMessage(msg.distrib_code, msg.distrib_message))

        if self._is_server_parent:
            return

        self._is_server_parent = True

        if len(self._child_peers) < self._max_distrib_children:
            self._send_message_to_server(AcceptChildren(True))

        log.add_conn("Server is our parent, ready to distribute search requests as a branch root")

    def _verify_parent_connection(self, conn, msg_class):
        """Verify that a connection is our current parent connection."""

        if conn is not self._parent_conn:
            log.add_conn("Received a distributed message %s from user %s, who is not our parent. "
                         "Closing connection.", (msg_class, conn.init.target_user))
            return False

        return True

    def _send_have_no_parent(self):
        """Inform the server we have no parent.

        The server should either send us a PossibleParents message, or
        start sending us search requests.
        """

        if not self._should_process_queue:
            return

        # Note that we don't clear the previous list of possible parents here, since
        # it's possible the parent connection was closed immediately or superseded by
        # an indirect connection
        self._parent_conn = None
        self._branch_level = 0
        self._branch_root = self._server_username

        log.add_conn("We have no parent, requesting a new one")

        self._send_message_to_server(HaveNoParent(True))
        self._send_message_to_server(BranchRoot(self._branch_root))
        self._send_message_to_server(BranchLevel(self._branch_level))
        self._send_message_to_server(AcceptChildren(False))

    def _set_branch_root(self, username):
        """Inform the server and child peers of our branch root."""

        if not username:
            return

        if username == self._branch_root:
            return

        self._branch_root = username
        self._send_message_to_server(BranchRoot(username))
        self._send_message_to_child_peers(DistribBranchRoot(username))

        log.add_conn("Our branch root is user %s", username)

    def _update_maximum_distributed_children(self):

        prev_max_distrib_children = self._max_distrib_children
        num_child_peers = len(self._child_peers)

        if self._upload_speed >= self._distrib_parent_min_speed and self._distrib_parent_speed_ratio > 0:
            # Limit maximum distributed child peers to 10 for now due to socket limit concerns
            self._max_distrib_children = min(self._upload_speed // self._distrib_parent_speed_ratio // 100, 10)
        else:
            # Server does not allow us to accept distributed child peers
            self._max_distrib_children = 0

        log.add_conn("Distributed child peer limit updated, maximum connections: %s", self._max_distrib_children)

        if self._max_distrib_children <= num_child_peers < prev_max_distrib_children:
            log.add_conn("Our current number of distributed child peers (%s) reached the new limit, no longer "
                         "accepting new connections", num_child_peers)
            self._send_message_to_server(AcceptChildren(False))

    def _process_distrib_message(self, conn, msg_type, msg_size, in_buffer, start_offset, end_offset):

        msg_class = DISTRIBUTED_MESSAGE_CLASSES[msg_type]
        msg = self._unpack_network_message(
            msg_class,
            memoryview(in_buffer)[start_offset:end_offset],
            msg_size,
            conn_type="distrib",
            sock=conn.sock,
            username=conn.init.target_user
        )

        if msg is None:
            # Ignore unknown message and keep connection open
            return True

        if msg_class is DistribSearch:
            if not self._verify_parent_connection(conn, msg_class):
                return False

            self._send_message_to_child_peers(msg)

        elif msg_class is DistribEmbeddedMessage:
            if not self._verify_parent_connection(conn, msg_class):
                return False

            msg = self._unpack_embedded_message(msg)

            if msg is not None:
                self._send_message_to_child_peers(msg)

        elif msg_class is DistribBranchLevel:
            if msg.level < 0:
                # There are rare cases of parents sending a branch level value of -1,
                # presumably buggy clients
                log.add_conn("Received an invalid branch level value %s from user %s. "
                             "Closing connection.", (msg.level, msg.username))
                return False

            if self._parent_conn is None and msg.username in self._potential_parents:
                # We have a successful connection with a potential parent. Tell the server who
                # our parent is, and stop requesting new potential parents.
                self._parent_conn = conn
                self._branch_level = msg.level + 1
                self._is_server_parent = False

                self._send_message_to_server(HaveNoParent(False))
                self._send_message_to_server(BranchLevel(self._branch_level))

                if len(self._child_peers) < self._max_distrib_children:
                    self._send_message_to_server(AcceptChildren(True))

                self._send_message_to_child_peers(DistribBranchLevel(self._branch_level))
                self._child_peers.pop(msg.username, None)

                log.add_conn("Adopting user %s as parent", msg.username)
                log.add_conn("Our branch level is %s", self._branch_level)

                if self._branch_level == 1:
                    # Our current branch level is 1, our parent is a branch root
                    self._set_branch_root(msg.username)

            elif not self._verify_parent_connection(conn, msg_class):
                return False

            else:
                # Inform the server and child peers of our new branch level
                self._branch_level = msg.level + 1
                self._send_message_to_server(BranchLevel(self._branch_level))
                self._send_message_to_child_peers(DistribBranchLevel(self._branch_level))

                log.add_conn("Received a branch level update from our parent. Our new branch level is %s",
                             self._branch_level)

        elif msg_class is DistribBranchRoot:
            if not self._verify_parent_connection(conn, msg_class):
                return False

            self._set_branch_root(msg.root_username)

        self._emit_network_message_event(msg)
        return True

    def _process_distrib_input(self, conn):
        """Reads messages from the input buffer of a 'D' connection."""

        in_buffer = conn.in_buffer
        buffer_len = len(in_buffer)
        msg_content_offset = 5
        idx = 0

        # Distributed messages are 5 bytes or greater in length
        while buffer_len >= msg_content_offset:
            msg_size, = UINT32_UNPACK(in_buffer, idx)

            if msg_size > self.MAX_INCOMING_MESSAGE_SIZE:
                log.add_conn("Received message larger than maximum size %s from user %s. "
                             "Closing connection.", (self.MAX_INCOMING_MESSAGE_SIZE, conn.init.target_user))
                self._close_connection(conn)
                break

            msg_size_total = msg_size + 4

            if msg_size_total > buffer_len:
                # Buffer is being filled
                conn.has_post_init_activity = True
                break

            # Unpack distributed messages
            msg_type = in_buffer[idx + 4]

            if msg_type in DISTRIBUTED_MESSAGE_CLASSES:
                if not self._process_distrib_message(
                    conn, msg_type, msg_size, in_buffer, idx + msg_content_offset, idx + msg_size_total
                ):
                    self._close_connection(conn)
                    return
            else:
                msg_content = in_buffer[idx + msg_content_offset:idx + min(50, msg_size_total)]
                log.add_debug("Distrib message type %s size %s contents %s unknown",
                              (msg_type, msg_size, msg_content))

            idx += msg_size_total
            buffer_len -= msg_size_total

        if idx:
            del in_buffer[:idx]
            conn.has_post_init_activity = True

    def _process_distrib_output(self, msg):

        # Pack distributed messages
        msg_content = self._pack_network_message(msg)

        if msg_content is None:
            return

        conn = self._conns[msg.sock]
        out_buffer = conn.out_buffer

        out_buffer += msg.pack_uint32(len(msg_content) + 1)
        out_buffer += msg.pack_uint8(DISTRIBUTED_MESSAGE_CODES[msg.__class__])
        out_buffer += msg_content

        conn.has_post_init_activity = True
        self._modify_connection_events(conn, selectors.EVENT_READ | selectors.EVENT_WRITE)

    # Internal Messages #

    def _process_internal_messages(self, msg):

        msg_class = msg.__class__

        if msg_class is CloseConnection:
            self._close_connection(self._conns.get(msg.sock))

        elif msg_class is ServerConnect:
            self._server_connect(msg)

        elif msg_class is ServerDisconnect:
            self._manual_server_disconnect = True
            self._close_connection(self._server_conn)

        elif msg_class is ServerReconnect:
            self._manual_server_reconnect = True
            self._close_connection(self._server_conn)

        elif msg_class is DownloadFile:
            conn = self._conns.get(msg.sock)

            if conn is not None:
                self._file_download_msgs[conn] = msg

                self._total_downloads += 1
                self._calc_download_limit()
                self._process_conn_incoming_messages(conn)

        elif msg_class is UploadFile:
            conn = self._conns.get(msg.sock)

            if conn is not None:
                self._file_upload_msgs[conn] = msg

                self._total_uploads += 1
                self._calc_upload_limit_function()
                self._process_conn_incoming_messages(conn)

        elif msg_class is SetDownloadLimit:
            self._download_limit = msg.limit * 1024
            self._calc_download_limit()

        elif msg_class is SetUploadLimit:
            if msg.limit > 0:
                if msg.limitby:
                    self._calc_upload_limit_function = self._calc_upload_limit
                else:
                    self._calc_upload_limit_function = self._calc_upload_limit_by_transfer
            else:
                self._calc_upload_limit_function = self._calc_upload_limit_none

            self._upload_limit = msg.limit * 1024
            self._calc_upload_limit_function()

        elif msg_class is EmitNetworkMessageEvents:
            for network_msg in msg.msgs:
                self._emit_network_message_event(network_msg)

    # Input/Output #

    def _process_ready_input_socket(self, sock, current_time):

        if sock in self._conns:
            conn = self._conns[sock]
        else:
            # Unknown connection
            return

        if (self._download_limit_split
                and conn in self._conns_downloaded
                and self._conns_downloaded[conn] >= self._download_limit_split):
            return

        conn_error = None

        try:
            if self._read_data(conn, current_time):
                self._process_conn_incoming_messages(conn)
                return

        except OSError as error:
            log.add_conn("Cannot read data from connection %s, closing connection. "
                         "Error: %s", (conn.addr, error))
            conn_error = error

        if not conn.is_established:
            if conn_error is None:
                # No error when connection shuts down gracefully (recv() returns
                # 0 bytes), but we need to display one anyway. Is this is the best fit?
                conn_error = self.ERROR_NOT_CONNECTED

            self._connect_error(conn_error, conn)

        self._close_connection(conn)

    def _process_ready_output_socket(self, sock, current_time):

        if sock in self._conns:
            conn = self._conns[sock]
        else:
            # Unknown connection
            return

        if not conn.is_established:
            if conn is self._server_conn:
                self._establish_outgoing_server_connection(conn)
            else:
                self._establish_outgoing_peer_connection(conn)

            if sock not in self._conns:
                # Connection was closed while being established
                return

        if (self._upload_limit_split
                and conn in self._conns_uploaded
                and self._conns_uploaded[conn] >= self._upload_limit_split):
            return

        try:
            if self._write_data(conn, current_time):
                return

        except (OSError, ValueError) as error:
            log.add_conn("Cannot write data to connection %s, closing connection. Error: %s",
                         (conn.addr, error))

        self._close_connection(conn)

    def _process_ready_sockets(self, current_time):

        if self._listen_socket is None:
            # We can't call select() when no sockets are registered (WinError 10022)
            return

        for key, io_events in self._selector.select(timeout=self.SLEEP_MAX_IDLE):
            sock = key.fileobj

            if io_events & selectors.EVENT_READ:
                if sock is self._listen_socket:
                    self._accept_incoming_peer_connections()
                    continue

                self._process_ready_input_socket(sock, current_time)

            if io_events & selectors.EVENT_WRITE:
                self._process_ready_output_socket(sock, current_time)

    def _process_conn_incoming_messages(self, conn):

        if not conn.in_buffer:
            return

        if conn is self._server_conn:
            self._process_server_input(conn)
            return

        init = conn.init

        if init is None:
            conn.init = init = self._process_peer_init_input(conn)

            if init is None or not conn.in_buffer:
                return

        if init.conn_type == ConnectionType.PEER:
            self._process_peer_input(conn)

        elif init.conn_type == ConnectionType.FILE:
            self._process_file_input(conn)

        elif init.conn_type == ConnectionType.DISTRIBUTED:
            self._process_distrib_input(conn)

        if conn.sock is not None and init.sock is not conn.sock:
            log.add_conn("Received message on secondary connection of type %s to user %s, "
                         "promoting to primary connection", (init.conn_type, init.target_user))
            init.sock = conn.sock

    def _process_outgoing_messages(self, msgs):

        for msg in msgs:
            if not self._should_process_queue:
                return

            msg_type = msg.msg_type
            process_func = None

            if msg_type == MessageType.INIT:
                process_func = self._process_peer_init_output
                sock = msg.sock

            elif msg_type == MessageType.INTERNAL:
                process_func = self._process_internal_messages
                sock = None

            elif msg_type == MessageType.PEER:
                process_func = self._process_peer_output
                sock = msg.sock

                if sock is None:
                    self._send_message_to_peer(msg.username, msg)
                    continue

            elif msg_type == MessageType.DISTRIBUTED:
                process_func = self._process_distrib_output
                sock = msg.sock

            elif msg_type == MessageType.FILE:
                process_func = self._process_file_output
                sock = msg.sock

                if sock is None:
                    self._send_message_to_peer(msg.username, msg)
                    continue

            elif msg_type == MessageType.SERVER:
                process_func = self._process_server_output
                sock = self._server_conn.sock

            log.add_msg_contents(msg, is_outgoing=True)

            if sock is not None and sock not in self._conns:
                log.add_conn("Cannot send the message over the closed connection: %s %s",
                             (msg.__class__, msg))
                continue

            if process_func is not None:
                process_func(msg)

    def _process_queue_messages(self):

        if not self._message_queue:
            return

        msgs = []

        while self._message_queue:
            msgs.append(self._message_queue.popleft())

        self._process_outgoing_messages(msgs)

    def _read_data(self, conn, current_time):

        sock = conn.sock
        current_recv_size = conn.recv_size
        is_file_download = (conn in self._file_download_msgs)
        use_download_limit = (self._download_limit_split and is_file_download)

        if use_download_limit:
            download_limit = (self._download_limit_split - self._conns_downloaded[conn])

            if current_recv_size > download_limit:  # pylint: disable=consider-using-min-builtin
                current_recv_size = download_limit

        data = sock.recv(current_recv_size)
        data_len = len(data)

        if not data:
            return False  # Close the connection

        # An intermediate buffer is useless when downloading a file. Write to the
        # file immediately, and let the OS handle buffering when necessary.
        if not is_file_download:
            conn.in_buffer += data

        elif not self._process_download(conn, data, data_len):
            return False  # Close the connection

        if use_download_limit:
            self._conns_downloaded[conn] += data_len

        # Grow or shrink recv buffer depending on how much data we're receiving
        elif data_len >= current_recv_size // 2:
            conn.recv_size *= 2

        elif data_len <= current_recv_size // 6:
            conn.recv_size //= 2

        conn.last_active = current_time
        return True

    def _write_data(self, conn, current_time):

        sock = conn.sock
        out_buffer = conn.out_buffer
        is_file_upload = (conn in self._file_upload_msgs)

        if is_file_upload and self._upload_limit_split:
            limit = (self._upload_limit_split - self._conns_uploaded[conn])

            if len(out_buffer) > limit:
                num_bytes_sent = sock.send(memoryview(out_buffer)[:limit])
            else:
                num_bytes_sent = sock.send(out_buffer)

            self._conns_uploaded[conn] += num_bytes_sent
        else:
            num_bytes_sent = sock.send(out_buffer)

        del out_buffer[:num_bytes_sent]

        if is_file_upload and not self._process_upload(conn, num_bytes_sent, current_time):
            return False  # Close the connection

        if not out_buffer:
            # Nothing else to send, stop watching connection for writes
            self._modify_connection_events(conn, selectors.EVENT_READ)

        conn.last_active = current_time
        return True

    # Networking Loop #

    def _loop(self):

        while not self._want_abort:
            current_time = time.monotonic()

            if (current_time - self._last_cycle_time) >= 1:
                self._check_connections(current_time)
                self._check_indirect_request_timeouts(current_time)

                events.emit_main_thread(
                    "set-connection-stats",
                    total_conns=self._num_sockets,
                    download_bandwidth=self._total_download_bandwidth,
                    upload_bandwidth=self._total_upload_bandwidth
                )

                self._conns_downloaded.clear()
                self._conns_uploaded.clear()

                self._total_download_bandwidth = 0
                self._total_upload_bandwidth = 0

                self._last_cycle_time = current_time

            if not self._should_process_queue:
                if self._server_timeout_time and (self._server_timeout_time - current_time) <= 0:
                    self._server_timeout_time = None
                    events.emit_main_thread(
                        "server-reconnect",
                        ServerReconnect(manual_reconnect=self._manual_server_reconnect)
                    )

                time.sleep(self.SLEEP_MAX_IDLE + self.SLEEP_MIN_IDLE)
                continue

            # Process queue messages
            self._process_queue_messages()

            # Check which connections are ready to send/receive data
            self._process_ready_sockets(current_time)

            # Don't exhaust the CPU
            time.sleep(self.SLEEP_MIN_IDLE)

    def run(self):

        events.emit_main_thread("set-connection-stats")

        # Watch sockets for I/0 readiness with the selectors module. Only call register() after a socket
        # is bound, otherwise watching the socket not guaranteed to work (breaks on OpenBSD at least)
        self._selector = selectors.DefaultSelector()

        try:
            self._loop()

        finally:
            # Networking thread aborted
            self._manual_server_disconnect = True
            self._close_connection(self._server_conn)
            self._selector.close()

            # We're ready to quit
            events.emit_main_thread("quit")
