# COPYRIGHT (C) 2020-2021 Nicotine+ Team
# COPYRIGHT (C) 2020 Mathias <mail@mathias.is>
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

"""
This is the actual client code. Actual GUI classes are in the separate modules
"""

import os
import threading
import time

from collections import deque

from pynicotine import slskmessages
from pynicotine import slskproto
from pynicotine import transfers
from pynicotine.config import config
from pynicotine.geoip.geoip import GeoIP
from pynicotine.interests import Interests
from pynicotine.logfacility import log
from pynicotine.networkfilter import NetworkFilter
from pynicotine.notifications import Notifications
from pynicotine.nowplaying import NowPlaying
from pynicotine.pluginsystem import PluginHandler
from pynicotine.privatechat import PrivateChats
from pynicotine.search import Search
from pynicotine.shares import Shares
from pynicotine.transfers import Statistics
from pynicotine.userbrowse import UserBrowse
from pynicotine.userinfo import UserInfo
from pynicotine.userlist import UserList
from pynicotine.utils import unescape


class PeerConnection:
    """
    Holds information about a peer connection. Not every field may be set
    to something. addr is (ip, port) address, conn is a socket object, msgs is
    a list of outgoing pending messages, token is a reverse-handshake
    number (protocol feature), init is a PeerInit protocol message. (read
    slskmessages docstrings for explanation of these)
    """

    __slots__ = ("addr", "username", "conn", "msgs", "token", "init", "conn_type", "tryaddr")

    def __init__(self, addr=None, username=None, conn=None, msgs=None, token=None, init=None, tryaddr=None):
        self.addr = addr
        self.username = username
        self.conn = conn
        self.msgs = msgs
        self.token = token
        self.init = init
        self.conn_type = init.conn_type
        self.tryaddr = tryaddr


class UserAddr:

    __slots__ = ("addr", "status")

    def __init__(self, addr=None, status=None):
        self.addr = addr
        self.status = status


class NicotineCore:
    """ NicotineCore contains handlers for various messages from the networking thread.
    This class links the networking thread and user interface. """

    def __init__(self, bindip, port):

        self.ui_callback = None
        self.network_callback = None
        self.network_filter = None
        self.statistics = None
        self.shares = None
        self.search = None
        self.transfers = None
        self.interests = None
        self.userbrowse = None
        self.userinfo = None
        self.userlist = None
        self.privatechats = None
        self.pluginhandler = None
        self.now_playing = None
        self.protothread = None
        self.geoip = None
        self.notifications = None

        self.chatrooms = None

        self.shutdown = False
        self.manualdisconnect = False

        # Tell threads when we're disconnecting
        self.exit = threading.Event()

        self.bindip = bindip
        self.port = port

        self.peerconns = []
        self.watchedusers = set()
        self.ip_requested = set()
        self.users = {}
        self.out_indirect_conn_request_times = {}

        self.queue = deque()

        self.away = False
        self.active_server_conn = None
        self.waitport = None
        self.ipaddress = None
        self.privileges_left = None
        self.servertimer = None
        self.upnp_timer = None
        self.server_timeout_value = -1

        self.has_parent = False

        self.requested_info_times = {}
        self.requested_share_times = {}
        self.token = 100

        # Callback handlers for messages
        self.events = {
            slskmessages.ConnectError: self.connect_error,
            slskmessages.IncPort: self.inc_port,
            slskmessages.ServerConn: self.server_conn,
            slskmessages.ConnClose: self.conn_close,
            slskmessages.Login: self.login,
            slskmessages.ChangePassword: self.change_password,
            slskmessages.MessageUser: self.message_user,
            slskmessages.PMessageUser: self.p_message_user,
            slskmessages.ExactFileSearch: self.dummy_message,
            slskmessages.RoomAdded: self.dummy_message,
            slskmessages.RoomRemoved: self.dummy_message,
            slskmessages.UserJoinedRoom: self.user_joined_room,
            slskmessages.SayChatroom: self.say_chat_room,
            slskmessages.JoinRoom: self.join_room,
            slskmessages.UserLeftRoom: self.user_left_room,
            slskmessages.CantCreateRoom: self.dummy_message,
            slskmessages.QueuedDownloads: self.dummy_message,
            slskmessages.GetPeerAddress: self.get_peer_address,
            slskmessages.PeerConn: self.peer_conn,
            slskmessages.UserInfoReply: self.user_info_reply,
            slskmessages.UserInfoRequest: self.user_info_request,
            slskmessages.PierceFireWall: self.pierce_fire_wall,
            slskmessages.CantConnectToPeer: self.cant_connect_to_peer,
            slskmessages.PeerTransfer: self.peer_transfer,
            slskmessages.SharedFileList: self.shared_file_list,
            slskmessages.GetSharedFileList: self.get_shared_file_list,
            slskmessages.FileSearchRequest: self.dummy_message,
            slskmessages.FileSearchResult: self.file_search_result,
            slskmessages.ConnectToPeer: self.connect_to_peer_request,
            slskmessages.GetUserStatus: self.get_user_status,
            slskmessages.GetUserStats: self.get_user_stats,
            slskmessages.Relogged: self.relogged,
            slskmessages.PeerInit: self.peer_init,
            slskmessages.CheckDownloadQueue: self.check_download_queue,
            slskmessages.CheckUploadQueue: self.check_upload_queue,
            slskmessages.DownloadFile: self.file_download,
            slskmessages.UploadFile: self.file_upload,
            slskmessages.FileRequest: self.file_request,
            slskmessages.TransferRequest: self.transfer_request,
            slskmessages.TransferResponse: self.transfer_response,
            slskmessages.QueueUpload: self.queue_upload,
            slskmessages.UploadDenied: self.upload_denied,
            slskmessages.UploadFailed: self.upload_failed,
            slskmessages.PlaceInQueue: self.place_in_queue,
            slskmessages.FileError: self.file_error,
            slskmessages.FolderContentsResponse: self.folder_contents_response,
            slskmessages.FolderContentsRequest: self.folder_contents_request,
            slskmessages.RoomList: self.room_list,
            slskmessages.LeaveRoom: self.leave_room,
            slskmessages.GlobalUserList: self.dummy_message,
            slskmessages.AddUser: self.add_user,
            slskmessages.PrivilegedUsers: self.privileged_users,
            slskmessages.AddToPrivileged: self.add_to_privileged,
            slskmessages.CheckPrivileges: self.check_privileges,
            slskmessages.ServerPing: self.dummy_message,
            slskmessages.ParentMinSpeed: self.dummy_message,
            slskmessages.ParentSpeedRatio: self.dummy_message,
            slskmessages.ParentInactivityTimeout: self.dummy_message,
            slskmessages.SearchInactivityTimeout: self.dummy_message,
            slskmessages.MinParentsInCache: self.dummy_message,
            slskmessages.WishlistInterval: self.wishlist_interval,
            slskmessages.DistribAliveInterval: self.dummy_message,
            slskmessages.DistribChildDepth: self.dummy_message,
            slskmessages.DistribBranchLevel: self.distrib_branch_level,
            slskmessages.DistribBranchRoot: self.distrib_branch_root,
            slskmessages.AdminMessage: self.admin_message,
            slskmessages.TunneledMessage: self.tunneled_message,
            slskmessages.IncConn: self.inc_conn,
            slskmessages.PlaceholdUpload: self.dummy_message,
            slskmessages.PlaceInQueueRequest: self.place_in_queue_request,
            slskmessages.UploadQueueNotification: self.upload_queue_notification,
            slskmessages.EmbeddedMessage: self.embedded_message,
            slskmessages.FileSearch: self.search_request,
            slskmessages.RoomSearch: self.search_request,
            slskmessages.UserSearch: self.search_request,
            slskmessages.RelatedSearch: self.dummy_message,
            slskmessages.PossibleParents: self.possible_parents,
            slskmessages.DistribAlive: self.dummy_message,
            slskmessages.DistribSearch: self.distrib_search,
            slskmessages.DistribEmbeddedMessage: self.embedded_message,
            slskmessages.ConnectToPeerTimeout: self.connect_to_peer_timeout,
            slskmessages.TransferTimeout: self.transfer_timeout,
            slskmessages.SetCurrentConnectionCount: self.set_current_connection_count,
            slskmessages.GlobalRecommendations: self.global_recommendations,
            slskmessages.Recommendations: self.recommendations,
            slskmessages.ItemRecommendations: self.item_recommendations,
            slskmessages.SimilarUsers: self.similar_users,
            slskmessages.ItemSimilarUsers: self.similar_users,
            slskmessages.UserInterests: self.user_interests,
            slskmessages.RoomTickerState: self.room_ticker_state,
            slskmessages.RoomTickerAdd: self.room_ticker_add,
            slskmessages.RoomTickerRemove: self.room_ticker_remove,
            slskmessages.UserPrivileged: self.dummy_message,
            slskmessages.AckNotifyPrivileges: self.dummy_message,
            slskmessages.NotifyPrivileges: self.dummy_message,
            slskmessages.PrivateRoomUsers: self.private_room_users,
            slskmessages.PrivateRoomOwned: self.private_room_owned,
            slskmessages.PrivateRoomAddUser: self.private_room_add_user,
            slskmessages.PrivateRoomRemoveUser: self.private_room_remove_user,
            slskmessages.PrivateRoomAdded: self.private_room_added,
            slskmessages.PrivateRoomRemoved: self.private_room_removed,
            slskmessages.PrivateRoomDisown: self.private_room_disown,
            slskmessages.PrivateRoomToggle: self.private_room_toggle,
            slskmessages.PrivateRoomSomething: self.dummy_message,
            slskmessages.PrivateRoomOperatorAdded: self.private_room_operator_added,
            slskmessages.PrivateRoomOperatorRemoved: self.private_room_operator_removed,
            slskmessages.PrivateRoomAddOperator: self.private_room_add_operator,
            slskmessages.PrivateRoomRemoveOperator: self.private_room_remove_operator,
            slskmessages.PublicRoomMessage: self.public_room_message,
            slskmessages.UnknownPeerMessage: self.ignore
        }

    def start(self, ui_callback=None, network_callback=None):

        self.ui_callback = ui_callback
        self.network_callback = network_callback if network_callback else self.network_event

        script_dir = os.path.dirname(__file__)
        self.geoip = GeoIP(os.path.join(script_dir, "geoip/ipcountrydb.bin"))

        self.notifications = Notifications(config, ui_callback)
        self.network_filter = NetworkFilter(self, config, self.users, self.queue, self.geoip)
        self.now_playing = NowPlaying(config)
        self.statistics = Statistics(config, ui_callback)

        self.shares = Shares(self, config, self.queue, ui_callback)
        self.search = Search(self, config, self.queue, self.shares.share_dbs, ui_callback)
        self.transfers = transfers.Transfers(self, config, self.queue, self.users, self.network_callback, ui_callback)
        self.interests = Interests(self, config, self.queue, ui_callback)
        self.userbrowse = UserBrowse(self, config, ui_callback)
        self.userinfo = UserInfo(self, config, self.queue, ui_callback)
        self.userlist = UserList(self, config, self.queue, ui_callback)
        self.privatechats = PrivateChats(self, config, self.queue, ui_callback)

        self.add_upnp_portmapping()

        port_range = config.sections["server"]["portrange"]
        interface = config.sections["server"]["interface"]
        self.protothread = slskproto.SlskProtoThread(
            self.network_callback, self.queue, self.bindip, interface, self.port, port_range, self.network_filter, self)

        self.pluginhandler = PluginHandler(self, config)

        connect_ready = not config.need_config()

        if not connect_ready:
            log.add(_("You need to specify a username and password before connecting..."))

        return connect_ready

    def quit(self, *_args):

        # Indicate that a shutdown has started, to prevent UI callbacks from networking thread
        self.shutdown = True
        self.manualdisconnect = True

        # Notify plugins
        self.pluginhandler.shutdown_notification()

        # Disable plugins
        for plugin in self.pluginhandler.list_installed_plugins():
            self.pluginhandler.disable_plugin(plugin)

        # Shut down networking thread
        server_conn = self.active_server_conn

        if server_conn:
            self.closed_connection(server_conn, server_conn.getsockname())

        self.protothread.abort()
        self.stop_timers()

        # Closing up all shelves db
        self.shares.close_shares("normal")
        self.shares.close_shares("buddy")

    def connect(self):

        self.protothread.server_connect()

        if self.active_server_conn is not None:
            return True

        # Clear any potential messages queued up to this point (should not happen)
        while self.queue:
            self.queue.popleft()

        valid_network_interface = self.protothread.validate_network_interface()

        if not valid_network_interface:
            message = _(
                "The network interface you specified, '%s', does not exist. Change or remove the specified "
                "network interface and restart Nicotine+."
            )
            log.add_important_error(message, self.protothread.interface)
            return False

        valid_listen_port = self.protothread.validate_listen_port()

        if not valid_listen_port:
            message = _(
                "The range you specified for client connection ports was "
                "{}-{}, but none of these were usable. Increase and/or ".format(self.protothread.portrange[0],
                                                                                self.protothread.portrange[1])
                + "move the range and restart Nicotine+."
            )
            if self.protothread.portrange[0] < 1024:
                message += "\n\n" + _(
                    "Note that part of your range lies below 1024, this is usually not allowed on"
                    " most operating systems with the exception of Windows."
                )
            log.add_important_error(message)
            return False

        server = config.sections["server"]["server"]
        log.add(_("Connecting to %(host)s:%(port)s"), {'host': server[0], 'port': server[1]})
        self.queue.append(slskmessages.ServerConn(None, server))

        if self.servertimer is not None:
            self.servertimer.cancel()
            self.servertimer = None

        return True

    def disconnect(self):
        self.manualdisconnect = True
        self.queue.append(slskmessages.ConnClose(self.active_server_conn))

    def network_event(self, msgs):

        for i in msgs:
            if self.shutdown:
                return

            if i.__class__ in self.events:
                self.events[i.__class__](i)

            else:
                log.add("No handler for class %s %s", (i.__class__, dir(i)))

    def get_new_token(self):
        self.token += 1
        return self.token

    def _check_indirect_connection_timeouts(self):

        while True:
            curtime = time.time()

            if self.out_indirect_conn_request_times:
                for conn, request_time in self.out_indirect_conn_request_times.copy().items():
                    if (curtime - request_time) >= 20:
                        self.network_callback([slskmessages.ConnectToPeerTimeout(conn)])

            if self.exit.wait(1):
                # Event set, we're exiting
                return

    def peer_init(self, msg):

        """ Peer wants to connect to us, remember them """

        log.add_msg_contents(msg)

        user = msg.init_user
        addr = msg.conn.addr
        conn = msg.conn.conn
        conn_type = msg.conn_type
        found_conn = False

        # We need two connections in our name if we're downloading from ourselves
        if user != config.sections["server"]["login"] and conn_type != 'F':
            for i in self.peerconns:
                if i.username == user and i.conn_type == conn_type:
                    i.addr = addr
                    i.conn = conn
                    i.token = None
                    i.init = msg

                    if i in self.out_indirect_conn_request_times:
                        del self.out_indirect_conn_request_times[i]

                    found_conn = True

                    # Deliver our messages to the peer
                    self.process_conn_messages(i, conn)
                    break

        if not found_conn:
            """ No previous connection exists for user """

            self.peerconns.append(
                PeerConnection(
                    addr=addr,
                    username=user,
                    conn=conn,
                    init=msg,
                    msgs=[]
                )
            )

        log.add_conn("Received incoming direct connection of type %(type)s from user %(user)s", {
            'type': conn_type,
            'user': user
        })

    def send_message_to_peer(self, user, message, address=None):

        """ Sends message to a peer. Used primarily when we know the username of a peer,
        but don't have an active connection. """

        conn = None

        if message.__class__ is not slskmessages.FileRequest:
            """ Check if there's already a connection object for the specified username """

            for i in self.peerconns:
                if i.username == user and i.conn_type == 'P':
                    conn = i
                    log.add_conn("Found existing connection of type %(type)s for user %(user)s, using it.", {
                        'type': i.conn_type,
                        'user': user
                    })
                    break

        if conn is not None and conn.conn is not None:
            """ We have initiated a connection previously, and it's ready """

            conn.msgs.append(message)
            self.process_conn_messages(conn, conn.conn)

        elif conn is not None:
            """ Connection exists but is not ready yet, add new messages to it """

            conn.msgs.append(message)

        else:
            """ This is a new peer, initiate a connection """

            self.initiate_connection_to_peer(user, message, address)

        log.add_conn("Sending message of type %(type)s to user %(user)s", {
            'type': message.__class__,
            'user': user
        })

    def initiate_connection_to_peer(self, user, message, address=None):

        """ Prepare to initiate a connection with a peer """

        if message.__class__ is slskmessages.FileRequest:
            message_type = 'F'

        elif message.__class__ is slskmessages.DistribRequest:
            message_type = 'D'

        else:
            message_type = 'P'

        init = slskmessages.PeerInit(
            init_user=config.sections["server"]["login"], target_user=user, conn_type=message_type, token=0)
        addr = None

        if user in self.users:
            addr = self.users[user].addr

        elif address is not None:
            self.users[user] = UserAddr(status=-1, addr=address)
            addr = address

        if addr is None:
            self.queue.append(slskmessages.GetPeerAddress(user))

            log.add_conn("Requesting address for user %(user)s", {
                'user': user
            })

        else:
            self.connect_to_peer_direct(user, addr, message_type)

        self.peerconns.append(
            PeerConnection(
                addr=addr,
                username=user,
                msgs=[message],
                init=init
            )
        )

    def connect_to_peer_direct(self, user, addr, message_type, init=None):

        """ Initiate a connection with a peer directly """

        self.queue.append(slskmessages.PeerConn(None, addr, init))

        log.add_conn("Initialising direct connection of type %(type)s to user %(user)s", {
            'type': message_type,
            'user': user
        })

    def connect_to_peer_indirect(self, conn, error):

        """ Send a message to the server to ask the peer to connect to us instead (indirect connection) """

        conn.token = self.get_new_token()
        self.queue.append(slskmessages.ConnectToPeer(conn.token, conn.username, conn.conn_type))
        self.out_indirect_conn_request_times[conn] = time.time()

        log.add_conn(
            """Direct connection of type %(type)s to user %(user)s failed, attempting indirect connection.
Error: %(error)s""", {
                "type": conn.conn_type,
                "user": conn.username,
                "error": error
            }
        )

    def connect_to_peer_request(self, msg):

        """ Peer sent us an indirect connection request via the server, attempt to
        connect to them """

        log.add_msg_contents(msg)

        user = msg.user
        addr = (msg.ip_address, msg.port)
        token = msg.token
        conn_type = msg.conn_type
        found_conn = False
        should_connect = True

        init = slskmessages.PeerInit(init_user=user, target_user=user, conn_type=conn_type, token=0)

        if user != config.sections["server"]["login"] and conn_type != 'F':
            for i in self.peerconns:
                if i.username == user and i.conn_type == conn_type:
                    """ Only update existing connection if it hasn't been established yet,
                    otherwise ignore indirect connection request. """

                    found_conn = True

                    if i.conn is None:
                        i.addr = addr
                        i.token = token
                        i.init = init
                        break

                    if i in self.out_indirect_conn_request_times:
                        del self.out_indirect_conn_request_times[i]

                    should_connect = False
                    break

        if should_connect:
            self.connect_to_peer_direct(user, addr, conn_type, init)

        if not found_conn:
            """ No previous connection exists for user """

            self.peerconns.append(
                PeerConnection(
                    addr=addr,
                    username=user,
                    msgs=[],
                    token=token,
                    init=init
                )
            )

    def get_peer_address(self, msg):

        """ Server responds with the IP address and port of the user we requested """

        log.add_msg_contents(msg)

        user = msg.user

        for i in self.peerconns:
            if i.username == user and i.addr is None:
                if msg.port != 0 or i.tryaddr == 10:

                    """ We now have the IP address for a user we previously didn't know,
                    attempt a direct connection to the peer/user """

                    if i.tryaddr == 10:
                        log.add_conn(
                            "Server reported port 0 for the 10th time for user %(user)s, giving up", {
                                'user': user
                            }
                        )

                    elif i.tryaddr is not None:
                        log.add_conn(
                            "Server reported non-zero port for user %(user)s after %(tries)i retries", {
                                'user': user,
                                'tries': i.tryaddr
                            }
                        )

                    i.addr = (msg.ip_address, msg.port)
                    i.tryaddr = None

                    self.connect_to_peer_direct(user, i.addr, i.conn_type)

                else:

                    """ Server responded with an incorrect port, request peer address again """

                    if i.tryaddr is None:
                        i.tryaddr = 1
                        log.add_conn(
                            "Server reported port 0 for user %(user)s, retrying", {
                                'user': user
                            }
                        )
                    else:
                        i.tryaddr += 1

                    self.queue.append(slskmessages.GetPeerAddress(user))
                    return

        if user in self.users:
            self.users[user].addr = (msg.ip_address, msg.port)
        else:
            self.users[user] = UserAddr(addr=(msg.ip_address, msg.port))

        # User seems to be offline, don't update IP
        if msg.ip_address != "0.0.0.0":

            # If the IP address changed, make sure our IP block/ignore list reflects this
            self.network_filter.update_saved_user_ip_filters(user)

            if self.network_filter.block_unblock_user_ip_callback(user):
                return

            if self.network_filter.ignore_unignore_user_ip_callback(user):
                return

        country_code = self.geoip.get_country_code(msg.ip_address)

        if country_code == "-":
            country_code = ""

        if self.chatrooms is not None:
            self.chatrooms.set_user_flag(user, country_code)

        self.userlist.set_user_country(user, country_code)

        # From this point on all paths should call
        # self.pluginhandler.user_resolve_notification precisely once
        self.privatechats.private_message_queue_process(user)

        if user not in self.ip_requested:
            self.pluginhandler.user_resolve_notification(user, msg.ip_address, msg.port)
            return

        self.ip_requested.remove(user)
        self.pluginhandler.user_resolve_notification(user, msg.ip_address, msg.port, country_code)

        if country_code:
            country = " (%(cc)s / %(country)s)" % {
                'cc': country_code, 'country': self.geoip.country_code_to_name(country_code)}
        else:
            country = ""

        if msg.ip_address == "0.0.0.0":
            log.add(_("IP address of user %s is unknown, since user is offline"), user)
            return

        log.add(_("IP address of user %(user)s is %(ip)s, port %(port)i%(country)s"), {
            'user': user,
            'ip': msg.ip_address,
            'port': msg.port,
            'country': country
        })

    def process_conn_messages(self, peerconn, conn):

        """ A connection is established with the peer, time to queue up our peer
        messages for delivery """

        for j in peerconn.msgs:

            if j.__class__ is slskmessages.UserInfoRequest:
                self.userinfo.set_conn(peerconn.username, conn)

            elif j.__class__ is slskmessages.GetSharedFileList:
                self.userbrowse.set_conn(peerconn.username, conn)

            j.conn = conn
            self.queue.append(j)

        peerconn.msgs = []

    @staticmethod
    def inc_conn(msg):
        log.add_msg_contents(msg)

    def peer_conn(self, msg):

        """ Networking thread told us that the connection to the peer was successful.
        If we connected directly to the peer, send a PeerInit message. If we connected
        as a result of an indirect connect request by the peer, send a PierceFirewall
        message. Queue up any messages we want to deliver to the peer. """

        log.add_msg_contents(msg)

        addr = msg.addr

        for i in self.peerconns:
            if i.addr == addr and i.conn is None:
                conn = msg.conn

                if i.token is None:
                    i.init.conn = conn
                    self.queue.append(i.init)

                else:
                    self.queue.append(slskmessages.PierceFireWall(conn, i.token))

                i.conn = conn

                log.add_conn("Connection established with user %(user)s. List of outgoing messages: %(messages)s", {
                    'user': i.username,
                    'messages': i.msgs
                })

                # Deliver our messages to the peer
                self.process_conn_messages(i, conn)

                break

    def pierce_fire_wall(self, msg):

        """ We received a response to our indirect connection request. Since a
        connection is now established with the peer, re-send our original peer
        messages. """

        log.add_msg_contents(msg)

        # Sometimes a token is seemingly not sent by the peer, check if the
        # IP address matches in that case

        for i in self.peerconns:
            if i.token is None or i.conn is not None:
                continue

            if (msg.token is None and i.addr == msg.conn.addr) or i.token == msg.token:
                conn = msg.conn.conn

                if i in self.out_indirect_conn_request_times:
                    del self.out_indirect_conn_request_times[i]

                i.init.conn = conn
                self.queue.append(i.init)
                i.conn = conn

                log.add_conn("User %(user)s managed to connect to us indirectly, connection is established. "
                             + "List of outgoing messages: %(messages)s", {
                                 'user': i.username,
                                 'messages': i.msgs
                             })

                # Deliver our messages to the peer
                self.process_conn_messages(i, conn)

                break

    def close_peer_connection(self, conn):

        """ Forcibly close a peer connection. Only used after receiving a search result,
        as we need to get rid of connections before they pile up """

        if conn is None:
            return

        if not self.protothread.socket_still_active(conn.conn):
            self.queue.append(slskmessages.ConnClose(conn.conn))

    def show_connection_error_message(self, conn):

        """ Request UI to show error messages related to connectivity """

        for i in conn.msgs:
            if i.__class__ in (slskmessages.FileRequest, slskmessages.TransferRequest):
                self.transfers.get_cant_connect_request(i.req)

            elif i.__class__ is slskmessages.QueueUpload:
                self.transfers.get_cant_connect_queue_file(conn.username, i.file)

            elif i.__class__ is slskmessages.GetSharedFileList:
                self.userbrowse.show_connection_error(conn.username)

            elif i.__class__ is slskmessages.UserInfoRequest:
                self.userinfo.show_connection_error(conn.username)

    def cant_connect_to_peer(self, msg):

        """ Peer informs us via the server that an indirect connection has failed.
        Game over. """

        log.add_msg_contents(msg)

        token = msg.token

        for i in self.peerconns:
            if i.token == token:

                if i in self.out_indirect_conn_request_times:
                    del self.out_indirect_conn_request_times[i]

                self.peerconns.remove(i)

                self.show_connection_error_message(i)
                log.add_conn("Can't connect to user %s neither directly nor indirectly, giving up", i.username)
                break

    def connect_to_peer_timeout(self, msg):

        """ Peer was not able to repond to our indirect connection request """

        conn = msg.conn

        if conn.conn is not None:
            # Connection has succeeded since the timeout callback was initiated
            return

        log.add_msg_contents(msg)

        try:
            self.peerconns.remove(conn)
        except ValueError:
            pass

        if conn in self.out_indirect_conn_request_times:
            del self.out_indirect_conn_request_times[conn]

        self.show_connection_error_message(conn)
        log.add_conn(
            "Indirect connect request of type %(type)s to user %(user)s expired, giving up", {
                'type': conn.conn_type,
                'user': conn.username
            }
        )

    def server_conn(self, msg):

        log.add_msg_contents(msg)

        log.add(
            _("Connected to server %(host)s:%(port)s, logging in..."), {
                'host': msg.addr[0],
                'port': msg.addr[1]
            }
        )

        self.active_server_conn = msg.conn
        self.server_timeout_value = -1
        self.users.clear()
        self.queue.append(
            slskmessages.Login(
                config.sections["server"]["login"],
                config.sections["server"]["passw"],

                # Soulseek client version; 155, 156, 157
                # SoulseekQt seems to be using 157
                # We use a custom version number for Nicotine+
                160,

                # Soulseek client minor version
                # 17 stands for 157 ns 13c, 19 for 157 ns 13e
                # SoulseekQt seems to go higher than this
                # We use a custom minor version for Nicotine+
                1,
            )
        )
        if self.waitport is not None:
            self.queue.append(slskmessages.SetWaitPort(self.waitport))

    def server_disconnect(self, addr):

        log.add(
            _("Disconnected from server %(host)s:%(port)s"), {
                'host': addr[0],
                'port': addr[1]
            })
        userchoice = self.manualdisconnect

        # Inform threads we've disconnected
        self.exit.set()

        if not self.manualdisconnect:
            self.set_server_timer()
        else:
            self.manualdisconnect = False

        self.active_server_conn = None

        # Clean up connections
        self.peerconns.clear()
        self.out_indirect_conn_request_times.clear()

        self.watchedusers.clear()
        self.shares.set_connected(False)

        self.transfers.server_disconnect()

        self.chatrooms = None
        self.pluginhandler.server_disconnect_notification(userchoice)

        if self.ui_callback:
            self.ui_callback.server_disconnect()

    def closed_connection(self, conn, addr, error=None):

        if conn == self.active_server_conn:
            self.server_disconnect(addr)

        else:
            """ A peer connection has died, remove it """

            for i in self.peerconns:
                if i.conn == conn:
                    log.add_conn("Connection closed by peer: %(peer)s. Error: %(error)s",
                                 {'peer': log.contents(i), 'error': error})

                    if i in self.out_indirect_conn_request_times:
                        del self.out_indirect_conn_request_times[i]

                    self.transfers.conn_close(conn, i.username, error)

                    if i.conn_type == 'D':
                        self.send_have_no_parent()

                    self.peerconns.remove(i)
                    return

    def conn_close(self, msg):

        log.add_msg_contents(msg)

        self.closed_connection(msg.conn, msg.addr)

    def connect_error(self, msg):

        log.add_msg_contents(msg)

        if msg.connobj.__class__ is slskmessages.ServerConn:

            log.add(
                _("Can't connect to server %(host)s:%(port)s: %(error)s"), {
                    'host': msg.connobj.addr[0],
                    'port': msg.connobj.addr[1],
                    'error': msg.err
                }
            )

            self.set_server_timer()

            if self.active_server_conn is not None:
                self.active_server_conn = None

            if self.ui_callback:
                self.ui_callback.server_connect_error()

        elif msg.connobj.__class__ is slskmessages.PeerConn:

            addr = msg.connobj.addr

            for i in self.peerconns:
                if i.addr == addr and i.conn is None:
                    if i.token is None:

                        """ We can't correct to peer directly, request indirect connection """

                        self.connect_to_peer_indirect(i, msg.err)

                    elif i not in self.out_indirect_conn_request_times:

                        """ Peer sent us an indirect connection request, and we weren't able to
                        connect to them. """

                        log.add_conn(
                            "Can't respond to indirect connection request from user %(user)s. Error: %(error)s", {
                                'user': i.username,
                                'error': msg.err
                            })

                        self.peerconns.remove(i)

                    break

        else:
            self.closed_connection(msg.connobj.conn, msg.connobj.addr, msg.err)

    def start_upnp_timer(self):
        """ Port mapping entries last 24 hours, we need to regularly renew them """
        """ The default interval is 4 hours """

        if self.upnp_timer:
            self.upnp_timer.cancel()

        upnp_interval = config.sections["server"]["upnp_interval"]

        if upnp_interval < 1:
            return

        upnp_interval_seconds = upnp_interval * 60 * 60

        self.upnp_timer = threading.Timer(upnp_interval_seconds, self.add_upnp_portmapping)
        self.upnp_timer.name = "UPnPTimer"
        self.upnp_timer.daemon = True
        self.upnp_timer.start()

    def add_upnp_portmapping(self):

        # Test if we want to do a port mapping
        if not config.sections["server"]["upnp"]:
            return

        # Do the port mapping
        thread = threading.Thread(target=self._add_upnp_portmapping)
        thread.name = "UPnPAddPortmapping"
        thread.daemon = True
        thread.start()

        # Repeat
        self.start_upnp_timer()

    def _add_upnp_portmapping(self):

        from pynicotine.upnp.portmapper import UPnPPortMapping
        upnp = UPnPPortMapping()
        upnp.add_port_mapping(self)

    def set_server_timer(self):

        if self.server_timeout_value == -1:
            self.server_timeout_value = 15

        elif 0 < self.server_timeout_value < 600:
            self.server_timeout_value = self.server_timeout_value * 2

        self.servertimer = threading.Timer(self.server_timeout_value, self.server_timeout)
        self.servertimer.name = "ServerTimer"
        self.servertimer.daemon = True
        self.servertimer.start()

        log.add(_("The server seems to be down or not responding, retrying in %i seconds"),
                self.server_timeout_value)

    def server_timeout(self):
        if not config.need_config():
            self.connect()

    def transfer_timeout(self, msg):

        log.add_msg_contents(msg)
        self.transfers.transfer_timeout(msg)

    def request_change_password(self, password):
        self.queue.append(slskmessages.ChangePassword(password))

    def request_check_privileges(self):
        self.queue.append(slskmessages.CheckPrivileges())

    def request_give_privileges(self, user, days):
        self.queue.append(slskmessages.GivePrivileges(user, days))

    def request_ip_address(self, username):
        self.ip_requested.add(username)
        self.queue.append(slskmessages.GetPeerAddress(username))

    def request_set_status(self, status):
        self.queue.append(slskmessages.SetStatus(status))

    def watch_user(self, user, force_update=False):
        """ Tell the server we want to be notified of status/stat updates
        for a user """

        if not isinstance(user, str):
            return

        if not force_update and user in self.watchedusers:
            # Already being watched, and we don't need to re-fetch the status/stats
            return

        self.queue.append(slskmessages.AddUser(user))

        # Get privilege status
        self.queue.append(slskmessages.GetUserStatus(user))

    def stop_timers(self):
        if self.servertimer is not None:
            self.servertimer.cancel()

    def connect_to_server(self, msg):
        log.add_msg_contents(msg)
        self.connect()

    @staticmethod
    def dummy_message(msg):
        log.add_msg_contents(msg)

    def ignore(self, msg):
        # Ignore received message
        pass

    def inc_port(self, msg):
        self.waitport = msg.port
        log.add(_("Listening on port %i"), msg.port)

    def peer_transfer(self, msg):

        if msg.msg is slskmessages.UserInfoReply:
            self.userinfo.update_gauge(msg)

        if msg.msg is slskmessages.SharedFileList:
            self.userbrowse.update_gauge(msg)

    def check_download_queue(self, msg):
        log.add_msg_contents(msg)
        self.transfers.check_download_queue()

    def check_upload_queue(self, _msg):
        self.transfers.check_upload_queue()

    def file_download(self, msg):
        log.add_msg_contents(msg)
        self.transfers.file_download(msg)

    def file_upload(self, msg):
        log.add_msg_contents(msg)
        self.transfers.file_upload(msg)

    def file_error(self, msg):
        log.add_msg_contents(msg)
        self.transfers.file_error(msg)

    def set_current_connection_count(self, msg):
        if self.ui_callback:
            self.ui_callback.set_socket_status(msg.msg)

    """
    Incoming Server Messages
    """

    def login(self, msg):
        """ Server code: 1 """

        log.add_msg_contents(msg)

        if msg.success:
            # Check for indirect connection timeouts
            self.exit.clear()
            thread = threading.Thread(target=self._check_indirect_connection_timeouts)
            thread.name = "IndirectConnectionTimeoutTimer"
            thread.daemon = True
            thread.start()

            self.away = config.sections["server"]["away"]
            self.queue.append(slskmessages.SetStatus((not self.away) + 1))
            self.watch_user(config.sections["server"]["login"])

            self.transfers.server_login()
            self.shares.set_connected(True)

            if msg.ip_address is not None:
                self.ipaddress = msg.ip_address

            self.userbrowse.server_login()
            self.userinfo.server_login()
            self.userlist.server_login()
            self.privatechats.server_login()

            if self.ui_callback:
                self.chatrooms = self.ui_callback.server_login()

            if msg.banner:
                log.add(msg.banner)

            self.interests.server_login()

            self.queue.append(slskmessages.CheckPrivileges())

            # Ask for a list of parents to connect to (distributed network)
            self.send_have_no_parent()

            """ TODO: Nicotine+ can currently receive search requests from a parent connection, but
            redirecting results to children is not implemented yet. Tell the server we don't accept
            children for now. """
            self.queue.append(slskmessages.AcceptChildren(0))

            self.shares.send_num_shared_folders_files()

            """ Request a complete room list. A limited room list not including blacklisted rooms and
            rooms with few users is automatically sent when logging in, but subsequent room list
            requests contain all rooms. """
            self.queue.append(slskmessages.RoomList())

            self.queue.append(slskmessages.PrivateRoomToggle(config.sections["server"]["private_chatrooms"]))
            self.pluginhandler.server_connect_notification()

        else:
            self.manualdisconnect = True
            self.queue.append(slskmessages.ConnClose(self.active_server_conn))

            log.add_important_error(_("Can not log in. Reason: %s"), msg.reason)

    def add_user(self, msg):
        """ Server code: 5 """

        log.add_msg_contents(msg)

        self.watchedusers.add(msg.user)

        if msg.userexists and msg.status is None:
            # Legacy support (Soulfind server)
            self.queue.append(slskmessages.GetUserStatus(msg.user))

        if msg.files is not None:
            self.get_user_stats(msg, log_contents=False)

    def get_user_status(self, msg, log_contents=True):
        """ Server code: 7 """

        if log_contents:
            log.add_msg_contents(msg)

        if msg.status is None:
            msg.status = -1

        if msg.user in self.users:
            if msg.status <= 0:
                # User went offline, reset stored IP address
                self.users[msg.user] = UserAddr(status=msg.status)
            else:
                self.users[msg.user].status = msg.status
        else:
            self.users[msg.user] = UserAddr(status=msg.status)

        if msg.privileged == 1:
            self.transfers.add_to_privileged(msg.user)

        elif msg.privileged == 0:
            self.transfers.remove_from_privileged(msg.user)

        self.interests.get_user_status(msg)
        self.transfers.get_user_status(msg)
        self.userbrowse.get_user_status(msg)
        self.userinfo.get_user_status(msg)
        self.userlist.get_user_status(msg)
        self.privatechats.get_user_status(msg)

        if self.chatrooms is not None:
            self.chatrooms.get_user_status(msg)

    def say_chat_room(self, msg):
        """ Server code: 13 """

        log.add_msg_contents(msg)
        log.add_chat(msg)

        event = self.pluginhandler.incoming_public_chat_event(msg.room, msg.user, msg.msg)

        if event is not None:
            _room, _user, msg.msg = event

            if self.chatrooms is not None:
                self.chatrooms.say_chat_room(msg, msg.msg)

            self.pluginhandler.incoming_public_chat_notification(msg.room, msg.user, msg.msg)

    def join_room(self, msg):
        """ Server code: 14 """

        log.add_msg_contents(msg)

        if self.chatrooms is not None:
            self.chatrooms.join_room(msg)

    def leave_room(self, msg):
        """ Server code: 15 """

        log.add_msg_contents(msg)

        if self.chatrooms is not None:
            self.chatrooms.leave_room(msg)

    def user_joined_room(self, msg):
        """ Server code: 16 """

        log.add_msg_contents(msg)

        if self.chatrooms is not None:
            self.chatrooms.user_joined_room(msg)

        self.pluginhandler.user_join_chatroom_notification(msg.room, msg.userdata.username)

    def user_left_room(self, msg):
        """ Server code: 17 """

        log.add_msg_contents(msg)

        if self.chatrooms is not None:
            self.chatrooms.user_left_room(msg)

        self.pluginhandler.user_leave_chatroom_notification(msg.room, msg.username)

    def message_user(self, msg):
        """ Server code: 22 """

        log.add_msg_contents(msg)
        log.add_chat(msg)

        self.privatechats.message_user(msg)

    def search_request(self, msg):
        """ Server code: 26, 42 and 120 """

        log.add_msg_contents(msg)

        self.search.process_search_request(msg.searchterm, msg.user, msg.searchid, direct=True)
        self.pluginhandler.search_request_notification(msg.searchterm, msg.user, msg.searchid)

    def get_user_stats(self, msg, log_contents=True):
        """ Server code: 36 """

        if log_contents:
            log.add_msg_contents(msg)

        if msg.user == config.sections["server"]["login"]:
            self.transfers.upload_speed = msg.avgspeed

        self.interests.get_user_stats(msg)
        self.userinfo.get_user_stats(msg)
        self.userlist.get_user_stats(msg)

        if self.chatrooms is not None:
            self.chatrooms.get_user_stats(msg)

        stats = {
            'avgspeed': msg.avgspeed,
            'uploadnum': msg.uploadnum,
            'files': msg.files,
            'dirs': msg.dirs,
        }

        self.pluginhandler.user_stats_notification(msg.user, stats)

    def relogged(self, _msg):
        """ Server code: 41 """

        log.add(_("Someone else is logging in with the same nickname, server is going to disconnect us"))
        self.manualdisconnect = True
        self.pluginhandler.server_disconnect_notification(False)

    def recommendations(self, msg):
        """ Server code: 54 """

        log.add_msg_contents(msg)
        self.interests.recommendations(msg)

    def global_recommendations(self, msg):
        """ Server code: 56 """

        log.add_msg_contents(msg)
        self.interests.global_recommendations(msg)

    def user_interests(self, msg):
        """ Server code: 57 """

        log.add_msg_contents(msg)
        self.userinfo.user_interests(msg)

    def room_list(self, msg):
        """ Server code: 64 """

        log.add_msg_contents(msg)

        if self.chatrooms is not None:
            self.chatrooms.set_room_list(msg)

    @staticmethod
    def admin_message(msg):
        """ Server code: 66 """

        log.add_important_info(msg.msg)

    def tunneled_message(self, msg):
        """ Server code: 68 """
        """ DEPRECATED """

        if msg.code in self.protothread.peerclasses:
            peermsg = self.protothread.peerclasses[msg.code](None)
            peermsg.parse_network_message(msg.msg)
            peermsg.tunneleduser = msg.user
            peermsg.tunneledreq = msg.req
            peermsg.tunneledaddr = msg.addr
            self.network_callback([peermsg])
        else:
            log.add_msg_contents("Unknown tunneled message: %s", log.contents(msg))

    def privileged_users(self, msg):
        """ Server code: 69 """

        log.add_msg_contents(msg)
        self.transfers.set_privileged_users(msg.users)
        log.add(_("%i privileged users"), (len(msg.users)))

    def add_to_privileged(self, msg):
        """ Server code: 91 """
        """ DEPRECATED """

        log.add_msg_contents(msg)
        self.transfers.add_to_privileged(msg.user)

    def check_privileges(self, msg):
        """ Server code: 92 """

        log.add_msg_contents(msg)

        mins = msg.seconds // 60
        hours = mins // 60
        days = hours // 24

        if msg.seconds == 0:
            log.add(
                _("You have no privileges left. They are not necessary, but allow your downloads "
                  "to be queued ahead of non-privileged users.")
            )
        else:
            log.add(
                _("%(days)i days, %(hours)i hours, %(minutes)i minutes, %(seconds)i seconds of "
                  "download privileges left."), {
                    'days': days,
                    'hours': hours % 24,
                    'minutes': mins % 60,
                    'seconds': msg.seconds % 60
                }
            )

        self.privileges_left = msg.seconds

    def embedded_message(self, msg):
        """ Server/distrib code: 93 """
        """ This message embeds a distributed message. We unpack the distributed message and
        process it. """

        # Verbose: log.add_msg_contents(msg)

        if msg.distrib_code in self.protothread.distribclasses:
            distrib_class = self.protothread.distribclasses[msg.distrib_code]
            distrib_msg = distrib_class(None)
            distrib_msg.parse_network_message(msg.distrib_message)

            # Process the distributed message
            self.events[distrib_class](distrib_msg)

    def possible_parents(self, msg):
        """ Server code: 102 """

        """ Server sent a list of 10 potential parents, whose purpose is to forward us search requests.
        We attempt to connect to them all at once, since connection errors are fairly common. """

        log.add_msg_contents(msg)

        potential_parents = msg.list
        log.add_conn("Server sent us a list of %s possible parents", len(msg.list))

        if not self.has_parent and potential_parents:

            for user in potential_parents:
                addr = potential_parents[user]

                self.send_message_to_peer(user, slskmessages.DistribRequest(), address=addr)
                log.add_conn("Attempting parent connection to user %s", user)

    def wishlist_interval(self, msg):
        """ Server code: 104 """

        log.add_msg_contents(msg)
        self.search.set_wishlist_interval(msg)

    def similar_users(self, msg):
        """ Server code: 110 and 112 """

        log.add_msg_contents(msg)
        self.interests.similar_users(msg)

    def item_recommendations(self, msg):
        """ Server code: 111 """

        log.add_msg_contents(msg)
        self.interests.item_recommendations(msg)

    def room_ticker_state(self, msg):
        """ Server code: 113 """

        log.add_msg_contents(msg)

        if self.chatrooms is not None:
            self.chatrooms.ticker_set(msg)

    def room_ticker_add(self, msg):
        """ Server code: 114 """

        log.add_msg_contents(msg)

        if self.chatrooms is not None:
            self.chatrooms.ticker_add(msg)

    def room_ticker_remove(self, msg):
        """ Server code: 115 """

        log.add_msg_contents(msg)

        if self.chatrooms is not None:
            self.chatrooms.ticker_remove(msg)

    def private_room_users(self, msg):
        """ Server code: 133 """

        log.add_msg_contents(msg)

        if self.chatrooms is not None:
            self.chatrooms.private_room_users(msg)

    def private_room_add_user(self, msg):
        """ Server code: 134 """

        log.add_msg_contents(msg)

        if self.chatrooms is not None:
            self.chatrooms.private_room_add_user(msg)

    def private_room_remove_user(self, msg):
        """ Server code: 135 """

        log.add_msg_contents(msg)

        if self.chatrooms is not None:
            self.chatrooms.private_room_remove_user(msg)

    def private_room_disown(self, msg):
        """ Server code: 137 """

        log.add_msg_contents(msg)

        if self.chatrooms is not None:
            self.chatrooms.private_room_disown(msg)

    def private_room_added(self, msg):
        """ Server code: 139 """

        log.add_msg_contents(msg)

        if self.chatrooms is not None:
            self.chatrooms.private_room_added(msg)

    def private_room_removed(self, msg):
        """ Server code: 140 """

        log.add_msg_contents(msg)

        if self.chatrooms is not None:
            self.chatrooms.private_room_removed(msg)

    def private_room_toggle(self, msg):
        """ Server code: 141 """

        log.add_msg_contents(msg)

        if self.chatrooms is not None:
            self.chatrooms.toggle_private_rooms(msg.enabled)

    @staticmethod
    def change_password(msg):
        """ Server code: 142 """

        log.add_msg_contents(msg)

        password = msg.password
        config.sections["server"]["passw"] = password
        config.write_configuration()

        log.add_important_info(
            _("Your password has been changed. Password is %s"), password)

    def private_room_add_operator(self, msg):
        """ Server code: 143 """

        log.add_msg_contents(msg)

        if self.chatrooms is not None:
            self.chatrooms.private_room_add_operator(msg)

    def private_room_remove_operator(self, msg):
        """ Server code: 144 """

        log.add_msg_contents(msg)

        if self.chatrooms is not None:
            self.chatrooms.private_room_remove_operator(msg)

    def private_room_operator_added(self, msg):
        """ Server code: 145 """

        log.add_msg_contents(msg)

        if self.chatrooms is not None:
            self.chatrooms.private_room_operator_added(msg)

    def private_room_operator_removed(self, msg):
        """ Server code: 146 """

        log.add_msg_contents(msg)

        if self.chatrooms is not None:
            self.chatrooms.private_room_operator_removed(msg)

    def private_room_owned(self, msg):
        """ Server code: 148 """

        log.add_msg_contents(msg)

        if self.chatrooms is not None:
            self.chatrooms.private_room_owned(msg)

    def public_room_message(self, msg):
        """ Server code: 152 """

        log.add_msg_contents(msg)

        if self.chatrooms is not None:
            self.chatrooms.public_room_message(msg, msg.msg)
            self.pluginhandler.public_room_message_notification(msg.room, msg.user, msg.msg)

    """
    Incoming Peer Messages
    """

    def get_shared_file_list(self, msg):
        """ Peer code: 4 """

        log.add_msg_contents(msg)

        user = msg.conn.init.target_user
        ip_address = port = msg.conn.addr
        conn = msg.conn.conn
        request_time = time.time()

        if user in self.requested_share_times and request_time < self.requested_share_times[user] + 0.4:
            # Ignoring request, because it's less than half a second since the
            # last one by this user
            return

        self.requested_share_times[user] = request_time

        # Check address is spoofed, if possible
        if user == config.sections["server"]["login"]:
            if ip_address is not None and port is not None:
                log.add(
                    _("%(user)s is making a BrowseShares request, blocking possible spoofing attempt "
                      "from IP %(ip)s port %(port)s"), {
                        'user': user,
                        'ip': ip_address,
                        'port': port
                    })
            else:
                log.add(
                    _("%(user)s is making a BrowseShares request, blocking possible spoofing attempt "
                      "from an unknown IP & port"), {
                        'user': user
                    })

            if conn is not None:
                self.queue.append(slskmessages.ConnClose(conn))
            return

        log.add(_("%(user)s is making a BrowseShares request"), {
            'user': user
        })

        ip_address, port = msg.conn.addr
        checkuser, reason = self.network_filter.check_user(user, ip_address)

        if not checkuser:
            self.privatechats.send_automatic_message(user, reason)

        shares_list = None

        if checkuser == 1:
            # Send Normal Shares
            shares_list = self.shares.get_compressed_shares_message("normal")

        elif checkuser == 2:
            # Send Buddy Shares
            shares_list = self.shares.get_compressed_shares_message("buddy")

        if not shares_list:
            # Nyah, Nyah
            shares_list = slskmessages.SharedFileList(conn, {})

        shares_list.conn = conn
        self.queue.append(shares_list)

    def shared_file_list(self, msg):
        """ Peer code: 5 """

        username = msg.conn.init.target_user

        if username != config.sections["server"]["login"]:
            self.userbrowse.shared_file_list(username, msg)

    def file_search_result(self, msg):
        """ Peer message: 9 """

        log.add_msg_contents(msg)

        conn = msg.conn
        addr = conn.addr

        if addr:
            country = self.geoip.get_country_code(addr[0])
        else:
            country = ""

        if country == "-":
            country = ""

        self.search.show_search_result(msg, msg.user, country)

        # Close peer connection immediately, otherwise we exhaust our connection limit
        self.close_peer_connection(conn)

    def user_info_request(self, msg):
        """ Peer code: 15 """

        log.add_msg_contents(msg)

        user = msg.conn.init.target_user
        ip_address = port = msg.conn.addr
        conn = msg.conn.conn
        request_time = time.time()

        if user in self.requested_info_times and request_time < self.requested_info_times[user] + 0.4:
            # Ignoring request, because it's less than half a second since the
            # last one by this user
            return

        self.requested_info_times[user] = request_time

        # Check address is spoofed, if possible
        if user == config.sections["server"]["login"]:

            if ip_address is not None and port is not None:
                log.add(
                    _("Blocking %(user)s from making a UserInfo request, possible spoofing attempt "
                      "from IP %(ip)s port %(port)s"), {
                        'user': user,
                        'ip': ip_address,
                        'port': port
                    }
                )
            else:
                log.add(_("Blocking %s from making a UserInfo request, possible spoofing attempt from "
                          "an unknown IP & port"), user)

            if conn is not None:
                self.queue.append(slskmessages.ConnClose(conn))

            return

        if self.network_filter.is_user_banned(user):
            log.add(
                _("%(user)s is banned, but is making a UserInfo request"), {
                    'user': user
                }
            )
            log.add_msg_contents(msg)
            return

        try:
            userpic = config.sections["userinfo"]["pic"]

            with open(userpic, 'rb') as file_handle:
                pic = file_handle.read()

        except Exception:
            pic = None

        descr = unescape(config.sections["userinfo"]["descr"])
        totalupl = self.transfers.get_total_uploads_allowed()
        queuesize = self.transfers.get_upload_queue_size()
        slotsavail = self.transfers.allow_new_uploads()

        if config.sections["transfers"]["remotedownloads"]:
            uploadallowed = config.sections["transfers"]["uploadallowed"]
        else:
            uploadallowed = 0

        self.queue.append(
            slskmessages.UserInfoReply(conn, descr, pic, totalupl, queuesize, slotsavail, uploadallowed))

        log.add(
            _("%(user)s is making a UserInfo request"), {
                'user': user
            }
        )

    def user_info_reply(self, msg):
        """ Peer code: 16 """

        log.add_msg_contents(msg)

        username = msg.conn.init.target_user

        if username != config.sections["server"]["login"]:
            self.userinfo.user_info_reply(username, msg)

    def p_message_user(self, msg):
        """ Peer code: 22 """

        log.add_msg_contents(msg)

        username = msg.conn.init.target_user

        if username != msg.user:
            msg.msg = _("(Warning: %(realuser)s is attempting to spoof %(fakeuser)s) ") % {
                "realuser": username, "fakeuser": msg.user} + msg.msg
            msg.user = username

        self.privatechats.message_user(msg)

    def folder_contents_request(self, msg):
        """ Peer code: 36 """

        log.add_msg_contents(msg)

        conn = msg.conn.conn
        ip_address, _port = msg.conn.addr
        username = msg.conn.init.target_user
        checkuser, reason = self.network_filter.check_user(username, ip_address)

        if not checkuser:
            self.privatechats.send_automatic_message(username, reason)

        normalshares = self.shares.share_dbs.get("streams")
        buddyshares = self.shares.share_dbs.get("buddystreams")

        if checkuser == 1 and normalshares is not None:
            shares = normalshares

        elif checkuser == 2 and buddyshares is not None:
            shares = buddyshares

        else:
            shares = {}

        if checkuser:
            if msg.dir in shares:
                self.queue.append(slskmessages.FolderContentsResponse(conn, msg.dir, shares[msg.dir]))

            elif msg.dir.rstrip('\\') in shares:
                self.queue.append(slskmessages.FolderContentsResponse(conn, msg.dir, shares[msg.dir.rstrip('\\')]))

            else:
                self.queue.append(slskmessages.FolderContentsResponse(conn, msg.dir, None))

    def folder_contents_response(self, msg):
        """ Peer code: 37 """

        file_list = msg.list

        # Check for a large number of files
        many = False
        folder = ""

        for i in file_list:
            for j in file_list[i]:
                if os.path.commonprefix([i, j]) == j:
                    numfiles = len(file_list[i][j])
                    if numfiles > 100:
                        many = True
                        folder = j

        if many:
            username = msg.conn.init.target_user
            self.transfers.downloadsview.download_large_folder(username, folder, numfiles, msg)
        else:
            self.transfers.folder_contents_response(msg)

    def transfer_request(self, msg):
        """ Peer code: 40 """

        log.add_msg_contents(msg)
        self.transfers.transfer_request(msg)

    def transfer_response(self, msg):
        """ Peer code: 41 """

        log.add_msg_contents(msg)
        self.transfers.transfer_response(msg)

    def queue_upload(self, msg):
        """ Peer code: 43 """

        log.add_msg_contents(msg)
        self.transfers.queue_upload(msg)

    def place_in_queue(self, msg):
        """ Peer code: 44 """

        log.add_msg_contents(msg)
        self.transfers.place_in_queue(msg)

    def upload_failed(self, msg):
        """ Peer code: 46 """

        log.add_msg_contents(msg)
        self.transfers.upload_failed(msg)

    def upload_denied(self, msg):
        """ Peer code: 50 """

        log.add_msg_contents(msg)
        self.transfers.upload_denied(msg)

    def place_in_queue_request(self, msg):
        """ Peer code: 51 """

        log.add_msg_contents(msg)
        self.transfers.place_in_queue_request(msg)

    def upload_queue_notification(self, msg):
        """ Peer code: 52 """

        log.add_msg_contents(msg)
        self.transfers.upload_queue_notification(msg)

    def file_request(self, msg):

        log.add_msg_contents(msg)
        self.transfers.file_request(msg)

    """
    Incoming Distributed Messages
    """

    def distrib_search(self, msg):
        """ Distrib code: 3 """

        # Verbose: log.add_msg_contents(msg)

        self.search.process_search_request(msg.searchterm, msg.user, msg.searchid, direct=False)
        self.pluginhandler.distrib_search_notification(msg.searchterm, msg.user, msg.searchid)

    def get_parent_conn(self):

        for i in self.peerconns:
            if i.conn_type == 'D':
                return i

        return None

    def send_have_no_parent(self):
        """ Inform the server we have no parent. The server should either send
        us a PossibleParents message, or start sending us search requests. """

        self.has_parent = False
        log.add_conn("We have no parent, requesting a new one")

        self.queue.append(slskmessages.HaveNoParent(1))
        self.queue.append(slskmessages.BranchRoot(config.sections["server"]["login"]))
        self.queue.append(slskmessages.BranchLevel(0))

    def distrib_branch_level(self, msg):
        """ Distrib code: 4 """

        """ This message is received when we have a successful connection with a potential
        parent. Tell the server who our parent is, and stop requesting new potential parents. """

        log.add_msg_contents(msg)

        if not self.has_parent:
            for i in self.peerconns[:]:
                if i.conn_type == 'D':
                    """ We previously attempted to connect to all potential parents. Since we now
                    have a parent, stop connecting to the others. """

                    if i.conn != msg.conn.conn:
                        if i.conn is not None:
                            self.queue.append(slskmessages.ConnClose(i.conn, callback=False))

                        if i in self.out_indirect_conn_request_times:
                            del self.out_indirect_conn_request_times[i]

                        self.peerconns.remove(i)

            parent = self.get_parent_conn()

            if parent:
                self.queue.append(slskmessages.HaveNoParent(0))
                self.queue.append(slskmessages.BranchLevel(msg.value + 1))
                self.has_parent = True

                log.add_conn("Adopting user %s as parent", parent.username)
                log.add_conn("Our branch level is %s", msg.value + 1)
            else:
                self.send_have_no_parent()

            return

        parent = self.get_parent_conn()

        if parent and msg.conn.conn == parent.conn:
            # Only accept messages by our current parent
            # Inform the server of our new branch level

            self.queue.append(slskmessages.BranchLevel(msg.value + 1))
            log.add_conn("Received a branch level update from our parent. Our new branch level is %s", msg.value + 1)

    def distrib_branch_root(self, msg):
        """ Distrib code: 5 """

        log.add_msg_contents(msg)

        parent = self.get_parent_conn()

        if parent and msg.conn.conn == parent.conn:
            # Only accept messages by our current parent
            # Inform the server of our branch root

            self.queue.append(slskmessages.BranchRoot(msg.user))
            log.add_conn("Our branch root is user %s", msg.user)
