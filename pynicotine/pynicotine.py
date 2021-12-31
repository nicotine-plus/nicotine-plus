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
import signal
import threading
import time

from collections import deque

from pynicotine import slskmessages
from pynicotine import slskproto
from pynicotine.chatrooms import ChatRooms
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
from pynicotine.transfers import Transfers
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
        self.chatrooms = None
        self.pluginhandler = None
        self.now_playing = None
        self.protothread = None
        self.geoip = None
        self.notifications = None

        self.shutdown = False

        # Handle Ctrl+C and "kill" exit gracefully
        for signal_type in (signal.SIGINT, signal.SIGTERM):
            signal.signal(signal_type, self.quit)

        # Tell threads when we're disconnecting
        self.exit = threading.Event()

        self.bindip = bindip
        self.port = port

        self.peerconns = []
        self.watched_users = set()
        self.ip_requested = set()
        self.users = {}
        self.out_indirect_conn_request_times = {}

        self.queue = deque()

        self.away = False
        self.logged_in = False
        self.user_ip_address = None
        self.privileges_left = None
        self.manual_disconnect = False

        self.server_conn = None
        self.server_address = None
        self.server_timer = None
        self.server_timeout_value = -1

        self.parent_conn = None
        self.potential_parents = {}
        self.distrib_parent_min_speed = 0
        self.distrib_parent_speed_ratio = 1
        self.max_distrib_children = 10

        self.upnp_timer = None
        self.ban_message = "You are banned from downloading my shared files. Ban message: \"%s\""

        self.requested_info_times = {}
        self.requested_share_times = {}
        self.token = 100

        # Callback handlers for messages
        self.events = {
            slskmessages.ConnectError: self.connect_error,
            slskmessages.InitServerConn: self.init_server_conn,
            slskmessages.InitPeerConn: self.init_peer_conn,
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
            slskmessages.UserInfoReply: self.user_info_reply,
            slskmessages.UserInfoRequest: self.user_info_request,
            slskmessages.PierceFireWall: self.pierce_fire_wall,
            slskmessages.CantConnectToPeer: self.cant_connect_to_peer,
            slskmessages.MessageProgress: self.message_progress,
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
            slskmessages.ParentMinSpeed: self.parent_min_speed,
            slskmessages.ParentSpeedRatio: self.parent_speed_ratio,
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
            slskmessages.UploadQueueNotification: self.dummy_message,
            slskmessages.EmbeddedMessage: self.embedded_message,
            slskmessages.FileSearch: self.search_request,
            slskmessages.RoomSearch: self.search_request,
            slskmessages.UserSearch: self.search_request,
            slskmessages.RelatedSearch: self.dummy_message,
            slskmessages.PossibleParents: self.possible_parents,
            slskmessages.DistribAlive: self.dummy_message,
            slskmessages.DistribSearch: self.distrib_search,
            slskmessages.DistribEmbeddedMessage: self.embedded_message,
            slskmessages.ResetDistributed: self.reset_distributed,
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

        log.add("Loading Nicotine+ %(nic_version)s" % {"nic_version": config.version})
        log.add("Using Python %(py_version)s" % {"py_version": config.python_version})

        self.ui_callback = ui_callback
        self.network_callback = network_callback if network_callback else self.network_event

        script_dir = os.path.dirname(__file__)
        self.geoip = GeoIP(os.path.join(script_dir, "geoip/ipcountrydb.bin"))

        self.notifications = Notifications(config, ui_callback)
        self.network_filter = NetworkFilter(self, config, self.users, self.queue, self.geoip)
        self.now_playing = NowPlaying(config)
        self.statistics = Statistics(config, ui_callback)

        self.shares = Shares(self, config, self.queue, ui_callback=ui_callback)
        self.search = Search(self, config, self.queue, self.shares.share_dbs, self.geoip, ui_callback)
        self.transfers = Transfers(self, config, self.queue, self.network_callback, ui_callback)
        self.interests = Interests(self, config, self.queue, ui_callback)
        self.userbrowse = UserBrowse(self, config, ui_callback)
        self.userinfo = UserInfo(self, config, self.queue, ui_callback)
        self.userlist = UserList(self, config, self.queue, ui_callback)
        self.privatechats = PrivateChats(self, config, self.queue, ui_callback)
        self.chatrooms = ChatRooms(self, config, self.queue, ui_callback)

        self.transfers.init_transfers()
        self.privatechats.load_users()

        port_range = config.sections["server"]["portrange"]
        interface = config.sections["server"]["interface"]
        self.protothread = slskproto.SlskProtoThread(
            self.network_callback, self.queue, self.bindip, interface, self.port, port_range, self.network_filter, self)

        self.add_upnp_portmapping()
        self.pluginhandler = PluginHandler(self, config)

        connect_ready = not config.need_config()

        if not connect_ready:
            log.add(_("You need to specify a username and password before connecting…"))

        return connect_ready

    def quit(self, signal_type=None, _frame=None):

        log.add(_("Quitting Nicotine+ %(version)s, %(status)s…"), {
            "version": config.version,
            "status": _("terminating") if signal_type == signal.SIGTERM else _("application closing")
        })

        # Indicate that a shutdown has started, to prevent UI callbacks from networking thread
        self.shutdown = True
        self.manual_disconnect = True

        # Notify plugins
        self.pluginhandler.shutdown_notification()

        # Disable plugins
        for plugin in self.pluginhandler.list_installed_plugins():
            self.pluginhandler.disable_plugin(plugin)

        # Shut down networking thread
        self.server_disconnect()
        self.protothread.abort()

        if self.server_timer is not None:
            self.server_timer.cancel()

        # Save download/upload list to file
        self.transfers.abort_transfers()

        # Closing up all shelves db
        self.shares.quit()

        if self.ui_callback:
            self.ui_callback.quit()

        log.add(_("Quit Nicotine+ %(version)s, %(status)s!"), {
            "version": config.version,
            "status": _("terminated") if signal_type == signal.SIGTERM else _("done")
        })

    def connect(self):

        if not self.protothread.server_disconnected:
            return True

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

        self.protothread.server_connect()

        # Clear any potential messages queued up while offline
        self.queue.clear()
        self.peerconns.clear()

        server = config.sections["server"]["server"]
        log.add(_("Connecting to %(host)s:%(port)s"), {'host': server[0], 'port': server[1]})
        self.queue.append(slskmessages.InitServerConn(None, server))

        if self.server_timer is not None:
            self.server_timer.cancel()
            self.server_timer = None

        return True

    def disconnect(self):
        self.manual_disconnect = True
        self.queue.append(slskmessages.ConnClose(self.server_conn))

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
            current_time = time.time()

            if self.out_indirect_conn_request_times:
                for conn, request_time in self.out_indirect_conn_request_times.copy().items():
                    if (current_time - request_time) >= 20:
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

        if user == config.sections["server"]["login"]:
            # Bypass public IP address request if we connect to ourselves
            addr = (self.protothread.bindip or '127.0.0.1', self.protothread.listenport)

        elif user in self.users:
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
            self.connect_to_peer_direct(user, addr, message_type, init)

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

        self.queue.append(slskmessages.InitPeerConn(None, addr, init))

        log.add_conn("Attempting direct connection of type %(type)s to user %(user)s %(addr)s", {
            'type': message_type,
            'user': user,
            'addr': addr
        })

    def connect_to_peer_indirect(self, conn, error):

        """ Send a message to the server to ask the peer to connect to us instead (indirect connection) """

        conn.token = self.get_new_token()
        self.queue.append(slskmessages.ConnectToPeer(conn.token, conn.username, conn.conn_type))
        self.out_indirect_conn_request_times[conn] = time.time()

        log.add_conn(("Direct connection of type %(type)s to user %(user)s failed, attempting indirect connection. "
                      "Error: %(error)s"), {
            "type": conn.conn_type,
            "user": conn.username,
            "error": error
        })

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

        self.chatrooms.set_user_country(user, country_code)
        self.userinfo.set_user_country(user, country_code)
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
            log.add(_("Cannot retrieve the IP of user %s, since this user is offline"), user)
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
            j.conn = conn
            self.queue.append(j)

        peerconn.msgs = []

    @staticmethod
    def inc_conn(msg):
        log.add_msg_contents(msg)

    def init_peer_conn(self, msg):

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

                log.add_conn("Established connection with user %(user)s. List of outgoing messages: %(messages)s", {
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

    def show_connection_error_message(self, conn):

        """ Request UI to show error messages related to connectivity """

        for i in conn.msgs:
            if i.__class__ in (slskmessages.FileRequest, slskmessages.TransferRequest):
                self.transfers.get_cant_connect_request(i.token)

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
                log.add_conn("Cannot connect to user %s neither directly nor indirectly, giving up", i.username)
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

    def init_server_conn(self, msg):

        log.add_msg_contents(msg)

        log.add(
            _("Connected to server %(host)s:%(port)s, logging in…"), {
                'host': msg.addr[0],
                'port': msg.addr[1]
            }
        )

        self.server_conn = msg.conn
        self.server_address = msg.addr
        self.server_timeout_value = -1

        self.queue.append(
            slskmessages.Login(
                config.sections["server"]["login"],
                config.sections["server"]["passw"],

                # Soulseek client version
                # NS and SoulseekQt use 157
                # We use a custom version number for Nicotine+
                160,

                # Soulseek client minor version
                # 17 stands for 157 ns 13c, 19 for 157 ns 13e
                # SoulseekQt seems to go higher than this
                # We use a custom minor version for Nicotine+
                1,
            )
        )
        if self.protothread.listenport is not None:
            self.queue.append(slskmessages.SetWaitPort(self.protothread.listenport))

    def server_disconnect(self):

        if self.server_conn is None:
            return

        host, port = self.server_address

        log.add(
            _("Disconnected from server %(host)s:%(port)s"), {
                'host': host,
                'port': port
            })

        # Inform threads we've disconnected
        self.exit.set()

        if not self.manual_disconnect:
            self.set_server_timer()
        else:
            self.manual_disconnect = False

        self.server_conn = None
        self.server_address = None
        self.logged_in = False

        # Clean up connections
        self.peerconns.clear()
        self.out_indirect_conn_request_times.clear()
        self.watched_users.clear()
        self.users.clear()

        self.pluginhandler.server_disconnect_notification(self.manual_disconnect)

        self.transfers.server_disconnect()
        self.search.server_disconnect()
        self.userlist.server_disconnect()
        self.chatrooms.server_disconnect()
        self.privatechats.server_disconnect()
        self.userinfo.server_disconnect()
        self.userbrowse.server_disconnect()

        if self.ui_callback:
            self.ui_callback.server_disconnect()

    def conn_close(self, msg):

        log.add_msg_contents(msg)

        conn = msg.conn
        addr = msg.addr

        if conn == self.server_conn:
            self.server_disconnect()

        else:
            """ A peer connection has died, remove it """

            for i in self.peerconns:
                if i.conn == conn:
                    log.add_conn("Closed connection of type %(type)s to user %(user)s %(addr)s",
                                 {'type': i.init.conn_type, 'user': i.username, 'addr': addr})

                    if i in self.out_indirect_conn_request_times:
                        del self.out_indirect_conn_request_times[i]

                    if i.init.conn_type == 'F':
                        self.transfers.conn_close(conn)

                    if i.conn == self.parent_conn:
                        self.send_have_no_parent()

                    self.peerconns.remove(i)
                    return

    def connect_error(self, msg):

        log.add_msg_contents(msg)

        if msg.connobj.__class__ is slskmessages.InitServerConn:

            log.add(
                _("Cannot connect to server %(host)s:%(port)s: %(error)s"), {
                    'host': msg.connobj.addr[0],
                    'port': msg.connobj.addr[1],
                    'error': msg.err
                }
            )

            self.set_server_timer()
            self.server_conn = None
            self.server_address = None

        elif msg.connobj.__class__ is slskmessages.InitPeerConn:

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
                            "Cannot respond to indirect connection request from user %(user)s. Error: %(error)s", {
                                'user': i.username,
                                'error': msg.err
                            })

                        self.peerconns.remove(i)

                    break

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

        from pynicotine.upnp import UPnPPortMapping
        upnp = UPnPPortMapping()
        upnp.update_port_mapping(self.protothread.listenport)

    def set_away_mode(self, is_away, save_state=False):

        if save_state:
            config.sections["server"]["away"] = is_away

        self.away = is_away
        self.request_set_status(is_away and 1 or 2)

        if self.ui_callback:
            self.ui_callback.set_away_mode(is_away)

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

    def get_user_country(self, user):
        """ Retrieve a user's country code if previously cached, otherwise request
        user's IP address to determine country """

        user_address = self.users.get(user)

        if user_address and isinstance(user_address.addr, tuple):
            ip_address, _port = user_address.addr
            country_code = self.geoip.get_country_code(ip_address)
            return country_code

        if user not in self.ip_requested:
            self.queue.append(slskmessages.GetPeerAddress(user))

        return None

    def watch_user(self, user, force_update=False):
        """ Tell the server we want to be notified of status/stat updates
        for a user """

        if not isinstance(user, str):
            return

        if not force_update and user in self.watched_users:
            # Already being watched, and we don't need to re-fetch the status/stats
            return

        self.queue.append(slskmessages.AddUser(user))

        # Get privilege status
        self.queue.append(slskmessages.GetUserStatus(user))

    def connect_to_server(self, msg):
        log.add_msg_contents(msg)
        self.connect()

    @staticmethod
    def dummy_message(msg):
        log.add_msg_contents(msg)

    def ignore(self, msg):
        # Ignore received message
        pass

    def message_progress(self, msg):

        if msg.msg_type is slskmessages.SharedFileList:
            self.userbrowse.message_progress(msg)

        elif msg.msg_type is slskmessages.UserInfoReply:
            self.userinfo.message_progress(msg)

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

            self.logged_in = True
            self.set_away_mode(config.sections["server"]["away"])
            self.watch_user(config.sections["server"]["login"])

            if msg.ip_address is not None:
                self.user_ip_address = msg.ip_address

            self.transfers.server_login()
            self.userbrowse.server_login()
            self.userinfo.server_login()
            self.userlist.server_login()
            self.privatechats.server_login()
            self.chatrooms.server_login()

            if self.ui_callback:
                self.ui_callback.server_login()

            if msg.banner:
                log.add(msg.banner)

            self.interests.server_login()

            self.queue.append(slskmessages.CheckPrivileges())

            # Ask for a list of parents to connect to (distributed network)
            self.send_have_no_parent()

            """ TODO: We can currently receive search requests from a parent connection, but
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
            self.manual_disconnect = True
            self.queue.append(slskmessages.ConnClose(self.server_conn))

            if msg.reason == "INVALIDPASS":
                self.ui_callback.invalid_password()
                return

            log.add_important_error(_("Unable to connect to the server. Reason: %s"), msg.reason)

    def add_user(self, msg):
        """ Server code: 5 """

        log.add_msg_contents(msg)

        self.watched_users.add(msg.user)

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
        self.chatrooms.get_user_status(msg)

        self.pluginhandler.user_status_notification(msg.user, msg.status, bool(msg.privileged))

    def say_chat_room(self, msg):
        """ Server code: 13 """

        log.add_msg_contents(msg)
        log.add_chat(_("Chat message from user '%(user)s' in room '%(room)s': %(message)s"), {
            "user": msg.user,
            "room": msg.room,
            "message": msg.msg
        })

        self.chatrooms.say_chat_room(msg)

    def join_room(self, msg):
        """ Server code: 14 """

        log.add_msg_contents(msg)
        self.chatrooms.join_room(msg)

    def leave_room(self, msg):
        """ Server code: 15 """

        log.add_msg_contents(msg)
        self.chatrooms.leave_room(msg)

    def user_joined_room(self, msg):
        """ Server code: 16 """

        log.add_msg_contents(msg)
        self.chatrooms.user_joined_room(msg)

    def user_left_room(self, msg):
        """ Server code: 17 """

        log.add_msg_contents(msg)
        self.chatrooms.user_left_room(msg)

    def message_user(self, msg):
        """ Server code: 22 """

        log.add_msg_contents(msg)
        log.add_chat(_("Private message from user '%(user)s': %(message)s"), {
            "user": msg.user,
            "message": msg.msg
        })

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
            self.max_distrib_children = msg.avgspeed // self.distrib_parent_speed_ratio

        self.interests.get_user_stats(msg)
        self.userinfo.get_user_stats(msg)
        self.userlist.get_user_stats(msg)
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

        log.add_important_info(_("Someone logged in to your Soulseek account elsewhere"))
        self.manual_disconnect = True

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
        self.chatrooms.room_list(msg)

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
            peermsg.tunneledtoken = msg.token
            peermsg.tunneledaddr = msg.addr
            self.network_callback([peermsg])
        else:
            log.add_msg_contents("Unknown tunneled message: %s", log.contents(msg))

    def privileged_users(self, msg):
        """ Server code: 69 """

        log.add_msg_contents(msg)
        self.transfers.set_privileged_users(msg.users)
        log.add(_("%i privileged users"), (len(msg.users)))

    def parent_min_speed(self, msg):
        """ Server code: 83 """

        log.add_msg_contents(msg)
        self.distrib_parent_min_speed = msg.speed

    def parent_speed_ratio(self, msg):
        """ Server code: 84 """

        log.add_msg_contents(msg)
        self.distrib_parent_speed_ratio = msg.ratio

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
                _("You have no privileges. Privileges are not required, but allow your downloads "
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

        self.potential_parents = msg.list
        log.add_conn("Server sent us a list of %s possible parents", len(msg.list))

        if self.parent_conn is None and self.potential_parents:

            for user in self.potential_parents:
                addr = self.potential_parents[user]

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
        self.chatrooms.ticker_set(msg)

    def room_ticker_add(self, msg):
        """ Server code: 114 """

        log.add_msg_contents(msg)
        self.chatrooms.ticker_add(msg)

    def room_ticker_remove(self, msg):
        """ Server code: 115 """

        log.add_msg_contents(msg)
        self.chatrooms.ticker_remove(msg)

    def reset_distributed(self, msg):
        """ Server code: 130 """

        log.add_msg_contents(msg)
        log.add_conn("Received a reset request for distributed network")

        if self.parent_conn is not None:
            self.queue.append(slskmessages.ConnClose(self.parent_conn))

        self.send_have_no_parent()

    def private_room_users(self, msg):
        """ Server code: 133 """

        log.add_msg_contents(msg)
        self.chatrooms.private_room_users(msg)

    def private_room_add_user(self, msg):
        """ Server code: 134 """

        log.add_msg_contents(msg)
        self.chatrooms.private_room_add_user(msg)

    def private_room_remove_user(self, msg):
        """ Server code: 135 """

        log.add_msg_contents(msg)
        self.chatrooms.private_room_remove_user(msg)

    def private_room_disown(self, msg):
        """ Server code: 137 """

        log.add_msg_contents(msg)
        self.chatrooms.private_room_disown(msg)

    def private_room_added(self, msg):
        """ Server code: 139 """

        log.add_msg_contents(msg)
        self.chatrooms.private_room_added(msg)

    def private_room_removed(self, msg):
        """ Server code: 140 """

        log.add_msg_contents(msg)
        self.chatrooms.private_room_removed(msg)

    def private_room_toggle(self, msg):
        """ Server code: 141 """

        log.add_msg_contents(msg)
        self.chatrooms.private_room_toggle(msg)

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
        self.chatrooms.private_room_add_operator(msg)

    def private_room_remove_operator(self, msg):
        """ Server code: 144 """

        log.add_msg_contents(msg)
        self.chatrooms.private_room_remove_operator(msg)

    def private_room_operator_added(self, msg):
        """ Server code: 145 """

        log.add_msg_contents(msg)
        self.chatrooms.private_room_operator_added(msg)

    def private_room_operator_removed(self, msg):
        """ Server code: 146 """

        log.add_msg_contents(msg)
        self.chatrooms.private_room_operator_removed(msg)

    def private_room_owned(self, msg):
        """ Server code: 148 """

        log.add_msg_contents(msg)
        self.chatrooms.private_room_owned(msg)

    def public_room_message(self, msg):
        """ Server code: 152 """

        log.add_msg_contents(msg)
        self.chatrooms.public_room_message(msg)

    """
    Incoming Peer Messages
    """

    def get_shared_file_list(self, msg):
        """ Peer code: 4 """

        log.add_msg_contents(msg)

        user = msg.conn.init.target_user
        conn = msg.conn.conn
        request_time = time.time()

        if user in self.requested_share_times and request_time < self.requested_share_times[user] + 0.4:
            # Ignoring request, because it's less than half a second since the
            # last one by this user
            return

        self.requested_share_times[user] = request_time

        log.add(_("User %(user)s is browsing your list of shared files"), {'user': user})

        ip_address, _port = msg.conn.addr
        checkuser, reason = self.network_filter.check_user(user, ip_address)

        if not checkuser:
            message = self.ban_message % reason
            self.privatechats.send_automatic_message(user, message)

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
        self.userbrowse.shared_file_list(username, msg)

    def file_search_result(self, msg):
        """ Peer message: 9 """

        log.add_msg_contents(msg)
        self.search.file_search_result(msg)

    def user_info_request(self, msg):
        """ Peer code: 15 """

        log.add_msg_contents(msg)

        user = msg.conn.init.target_user
        login_user = config.sections["server"]["login"]
        conn = msg.conn.conn
        addr = msg.conn.addr
        request_time = time.time()

        if user in self.requested_info_times and request_time < self.requested_info_times[user] + 0.4:
            # Ignoring request, because it's less than half a second since the
            # last one by this user
            return

        self.requested_info_times[user] = request_time

        if login_user != user:
            log.add(_("User %(user)s is reading your user info"), {'user': user})

        status, reason = self.network_filter.check_user(user, addr[0])

        if not status:
            pic = None
            descr = self.ban_message % reason
            descr += "\n\n--------------------------------------------------------\n\n"
            descr += unescape(config.sections["userinfo"]["descr"])

        else:
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

    def user_info_reply(self, msg):
        """ Peer code: 16 """

        log.add_msg_contents(msg)

        username = msg.conn.init.target_user
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
            message = self.ban_message % reason
            self.privatechats.send_automatic_message(username, message)

        normalshares = self.shares.share_dbs.get("streams")
        buddyshares = self.shares.share_dbs.get("buddystreams")

        if checkuser == 1 and normalshares is not None:
            shares = normalshares

        elif checkuser == 2 and buddyshares is not None:
            shares = buddyshares

        else:
            shares = {}

        if checkuser:
            try:
                if msg.dir in shares:
                    self.queue.append(slskmessages.FolderContentsResponse(conn, msg.dir, shares[msg.dir]))
                    return

                if msg.dir.rstrip('\\') in shares:
                    self.queue.append(slskmessages.FolderContentsResponse(conn, msg.dir, shares[msg.dir.rstrip('\\')]))
                    return

            except Exception as error:
                log.add(_("Failed to fetch the shared folder %(folder)s: %(error)s"),
                        {"folder": msg.dir, "error": error})

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

    def send_have_no_parent(self):
        """ Inform the server we have no parent. The server should either send
        us a PossibleParents message, or start sending us search requests. """

        self.parent_conn = None
        log.add_conn("We have no parent, requesting a new one")

        self.queue.append(slskmessages.HaveNoParent(1))
        self.queue.append(slskmessages.BranchRoot(config.sections["server"]["login"]))
        self.queue.append(slskmessages.BranchLevel(0))

    def distrib_branch_level(self, msg):
        """ Distrib code: 4 """

        """ This message is received when we have a successful connection with a potential
        parent. Tell the server who our parent is, and stop requesting new potential parents. """

        log.add_msg_contents(msg)
        conn = msg.conn.conn
        username = msg.conn.init.target_user

        if msg.value < 0:
            # There are rare cases of parents sending a branch level value of -1, presumably buggy clients
            log.add_conn("Received an invalid branch level value %(level)s from user %(user)s. Closing connection." %
                         {"level": msg.value, "user": username})
            self.queue.append(slskmessages.ConnClose(conn))
            return

        if self.parent_conn is None and username in self.potential_parents:
            self.parent_conn = conn

            self.queue.append(slskmessages.HaveNoParent(0))
            self.queue.append(slskmessages.BranchLevel(msg.value + 1))

            log.add_conn("Adopting user %s as parent", username)
            log.add_conn("Our branch level is %s", msg.value + 1)
            return

        if conn != self.parent_conn:
            # Unwanted connection, close it
            self.queue.append(slskmessages.ConnClose(conn))
            return

        # Inform the server of our new branch level
        self.queue.append(slskmessages.BranchLevel(msg.value + 1))
        log.add_conn("Received a branch level update from our parent. Our new branch level is %s", msg.value + 1)

    def distrib_branch_root(self, msg):
        """ Distrib code: 5 """

        log.add_msg_contents(msg)
        conn = msg.conn.conn

        if conn != self.parent_conn:
            # Unwanted connection, close it
            self.queue.append(slskmessages.ConnClose(conn))
            return

        # Inform the server of our branch root
        self.queue.append(slskmessages.BranchRoot(msg.user))
        log.add_conn("Our branch root is user %s", msg.user)
