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
import queue
import threading
import time
import _thread

from pynicotine import slskmessages
from pynicotine import slskproto
from pynicotine import transfers
from pynicotine.config import Config
from pynicotine.geoip.ip2location import IP2Location
from pynicotine.logfacility import log
from pynicotine.nowplaying import NowPlaying
from pynicotine.shares import Shares
from pynicotine.slskmessages import new_id
from pynicotine.transfers import Statistics
from pynicotine.utils import clean_file
from pynicotine.utils import unescape


class UserAddr:

    __slots__ = "addr", "status"

    def __init__(self, addr=None, status=None):
        self.addr = addr
        self.status = status


class PeerConnection:
    """
    Holds information about a peer connection. Not every field may be set
    to something. addr is (ip, port) address, conn is a socket object, msgs is
    a list of outgoing pending messages, token is a reverse-handshake
    number (protocol feature), init is a PeerInit protocol message. (read
    slskmessages docstrings for explanation of these)
    """

    __slots__ = "addr", "username", "conn", "msgs", "token", "init", "type", "conntimer", "tryaddr"

    def __init__(self, addr=None, username=None, conn=None, msgs=None, token=None, init=None, conntimer=None, tryaddr=None):
        self.addr = addr
        self.username = username
        self.conn = conn
        self.msgs = msgs
        self.token = token
        self.init = init
        self.type = init.type
        self.conntimer = conntimer
        self.tryaddr = tryaddr


class Timeout:

    __slots__ = "callback"

    def __init__(self, callback):
        self.callback = callback

    def timeout(self):
        try:
            self.callback([self])
        except Exception as e:
            log.add_warning(_("Exception in callback %s: %s"), (self.callback, e))


class ConnectToPeerTimeout(Timeout):

    __slots__ = "conn"

    def __init__(self, conn, callback):
        self.conn = conn
        self.callback = callback


class NetworkEventProcessor:
    """ This class contains handlers for various messages from the networking thread """

    def __init__(self, ui_callback, network_callback, setstatus, bindip, port, data_dir, config):

        self.ui_callback = ui_callback
        self.network_callback = network_callback
        self.set_status = setstatus
        self.manualdisconnect = False

        try:
            self.config = Config(config, data_dir)

        except Exception:
            import shutil
            corruptfile = ".".join([config, clean_file(time.strftime("%Y-%m-%d_%H_%M_%S")), "corrupt"])
            shutil.move(config, corruptfile)
            short = _("Your config file is corrupt")
            long = _("We're sorry, but it seems your configuration file is corrupt. Please reconfigure Nicotine+.\n\nWe renamed your old configuration file to\n%(corrupt)s\nIf you open this file with a text editor you might be able to rescue some of your settings.") % {'corrupt': corruptfile}
            self.config = Config(config, data_dir)
            self.network_callback([slskmessages.PopupMessage(short, long)])

        self.bindip = bindip
        self.port = port

        log.set_log_levels(self.config.sections["logging"]["debugmodes"])

        self.peerconns = []
        self.watchedusers = set()
        self.ipblock_requested = {}
        self.ipignore_requested = {}
        self.ip_requested = set()
        self.private_message_queue = {}
        self.users = {}

        self.queue = queue.Queue(0)
        self.statistics = Statistics(self.config, self.ui_callback)
        self.shares = Shares(self, self.config, self.queue, self.ui_callback)
        self.pluginhandler = None  # Initialized when the GUI is ready
        self.now_playing = NowPlaying(self.config)

        script_dir = os.path.dirname(__file__)
        file_path = os.path.join(script_dir, "geoip/ipcountrydb.bin")
        self.geoip = IP2Location(file_path, "SHARED_MEMORY")

        # Give the logger information about log folder
        self.update_debug_log_options()

        self.protothread = slskproto.SlskProtoThread(self.network_callback, self.queue, self.bindip, self.port, self.config, self)

        # UPnP
        self.upnp_interval = self.config.sections["server"]["upnp_interval"]
        self.upnp_timer = None
        _thread.start_new_thread(self.add_upnp_portmapping, ())

        self.active_server_conn = None
        self.waitport = None
        self.chatrooms = None
        self.privatechat = None
        self.globallist = None
        self.userinfo = None
        self.userbrowse = None
        self.search = None
        self.transfers = None
        self.userlist = None
        self.ipaddress = None
        self.privileges_left = None
        self.servertimer = None
        self.server_timeout_value = -1

        self.has_parent = False

        self.requested_info = {}
        self.requested_folders = {}
        self.speed = 0

        # Callback handlers for messages
        self.events = {
            slskmessages.ConnectToServer: self.connect_to_server,
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
            slskmessages.OutConn: self.out_conn,
            slskmessages.UserInfoReply: self.user_info_reply,
            slskmessages.UserInfoRequest: self.user_info_request,
            slskmessages.PierceFireWall: self.pierce_fire_wall,
            slskmessages.CantConnectToPeer: self.cant_connect_to_peer,
            slskmessages.PeerTransfer: self.peer_transfer,
            slskmessages.SharedFileList: self.shared_file_list,
            slskmessages.GetSharedFileList: self.get_shared_file_list,
            slskmessages.FileSearchRequest: self.file_search_request,
            slskmessages.FileSearchResult: self.file_search_result,
            slskmessages.ConnectToPeer: self.connect_to_peer_request,
            slskmessages.GetUserStatus: self.get_user_status,
            slskmessages.GetUserStats: self.get_user_stats,
            slskmessages.Relogged: self.relogged,
            slskmessages.PeerInit: self.peer_init,
            slskmessages.CheckDownloadQueue: self.check_download_queue,
            slskmessages.DownloadFile: self.file_download,
            slskmessages.UploadFile: self.file_upload,
            slskmessages.FileRequest: self.file_request,
            slskmessages.TransferRequest: self.transfer_request,
            slskmessages.TransferResponse: self.transfer_response,
            slskmessages.QueueUpload: self.queue_upload,
            slskmessages.QueueFailed: self.queue_failed,
            slskmessages.UploadFailed: self.upload_failed,
            slskmessages.PlaceInQueue: self.place_in_queue,
            slskmessages.FileError: self.file_error,
            slskmessages.FolderContentsResponse: self.folder_contents_response,
            slskmessages.FolderContentsRequest: self.folder_contents_request,
            slskmessages.RoomList: self.room_list,
            slskmessages.LeaveRoom: self.leave_room,
            slskmessages.GlobalUserList: self.global_user_list,
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
            slskmessages.ChildDepth: self.child_depth,
            slskmessages.BranchLevel: self.branch_level,
            slskmessages.BranchRoot: self.branch_root,
            slskmessages.DistribChildDepth: self.distrib_child_depth,
            slskmessages.DistribBranchLevel: self.distrib_branch_level,
            slskmessages.DistribBranchRoot: self.distrib_branch_root,
            slskmessages.AdminMessage: self.admin_message,
            slskmessages.TunneledMessage: self.tunneled_message,
            slskmessages.IncConn: self.inc_conn,
            slskmessages.PlaceholdUpload: self.dummy_message,
            slskmessages.PlaceInQueueRequest: self.place_in_queue_request,
            slskmessages.UploadQueueNotification: self.upload_queue_notification,
            slskmessages.SearchRequest: self.search_request,
            slskmessages.FileSearch: self.search_request,
            slskmessages.RoomSearch: self.room_search_request,
            slskmessages.UserSearch: self.search_request,
            slskmessages.RelatedSearch: self.dummy_message,
            slskmessages.PossibleParents: self.possible_parents,
            slskmessages.DistribAlive: self.dummy_message,
            slskmessages.DistribSearch: self.distrib_search,
            slskmessages.DistribServerSearch: self.distrib_search,
            ConnectToPeerTimeout: self.connect_to_peer_timeout,
            transfers.TransferTimeout: self.transfer_timeout,
            str: self.notify,
            slskmessages.PopupMessage: self.popup_message,
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
            slskmessages.UserPrivileged: self.user_privileged,
            slskmessages.AckNotifyPrivileges: self.ack_notify_privileges,
            slskmessages.NotifyPrivileges: self.notify_privileges,
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

    def peer_init(self, msg):

        """ Peer wants to connect to us, remember them """

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        user = msg.user
        addr = msg.conn.addr
        conn = msg.conn.conn
        msg_type = msg.type
        found_conn = False

        if user != self.config.sections["server"]["login"]:  # We need two connections in our name if we're downloading from ourselves
            for i in self.peerconns:
                if i.username == user and i.type != 'F' and i.type == msg_type:
                    i.addr = addr
                    i.conn = conn
                    i.token = None
                    i.init = msg

                    if i.conntimer is not None:
                        i.conntimer.cancel()

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

        log.add_conn("Received incoming connection of type %(type)s from user %(user)s" % {'type': msg_type, 'user': user})

    def send_message_to_peer(self, user, message, address=None):

        """ Sends message to a peer. Used primarily when we know the username of a peer,
        but don't have an active connection. """

        conn = None

        if message.__class__ is not slskmessages.FileRequest:
            """ Check if there's already a connection object for the specified username """

            for i in self.peerconns:
                if i.username == user and i.type == 'P':
                    conn = i
                    log.add_conn("Found existing connection of type %(type)s for user %(user)s, using it." % {
                        'type': i.type,
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

        log.add_conn("Sending message of type %(type)s to user %(user)s" % {
            'type': message.__class__,
            'user': user
        })

    def initiate_connection_to_peer(self, user, message, address=None):

        """ Prepare to initiate a connection with a peer """

        if message.__class__ is slskmessages.FileRequest:
            message_type = 'F'

        elif message.__class__ is slskmessages.DistribConn:
            message_type = 'D'

        else:
            message_type = 'P'

        init = slskmessages.PeerInit(None, self.config.sections["server"]["login"], message_type, 0)
        addr = None

        if user in self.users:
            addr = self.users[user].addr

        elif address is not None:
            self.users[user] = UserAddr(status=-1, addr=address)
            addr = address

        if addr is None:
            self.queue.put(slskmessages.GetPeerAddress(user))

            if message.__class__ is slskmessages.TransferRequest and self.transfers is not None:
                self.transfers.getting_address(message.req, message.direction)

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

        self.queue.put(slskmessages.OutConn(None, addr, init))

        log.add_conn("Initialising direct connection of type %(type)s to user %(user)s", {
            'type': message_type,
            'user': user
        })

    def connect_to_peer_indirect(self, conn, error):

        """ Send a message to the server to ask the peer to connect to us instead (indirect connection) """

        conn.token = new_id()
        self.queue.put(slskmessages.ConnectToPeer(conn.token, conn.username, conn.type))

        for j in conn.msgs:
            if j.__class__ is slskmessages.TransferRequest and self.transfers is not None:
                self.transfers.got_connect_error(j.req, j.direction)

        conntimeout = ConnectToPeerTimeout(conn, self.network_callback)
        timer = threading.Timer(20.0, conntimeout.timeout)
        timer.setName("ConnectionTimer")
        timer.setDaemon(True)
        timer.start()

        if conn.conntimer is not None:
            conn.conntimer.cancel()

        conn.conntimer = timer

        log.add_conn(
            "Direct connection of type %(type)s to user %(user)s failed, attempting indirect connection. Error: %(error)s", {
                "type": conn.type,
                "user": conn.username,
                "error": error
            }
        )

    def connect_to_peer_request(self, msg):

        """ Peer sent us an indirect connection request via the server, attempt to
        connect to them """

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        user = msg.user
        addr = (msg.ip, msg.port)
        token = msg.token
        msg_type = msg.type
        found_conn = False
        should_connect = True

        init = slskmessages.PeerInit(None, user, msg_type, 0)

        if user != self.config.sections["server"]["login"]:
            for i in self.peerconns:
                if i.username == user and i.type != 'F' and i.type == msg_type:
                    """ Only update existing connection if it hasn't been established yet,
                    otherwise ignore indirect connection request. """

                    found_conn = True

                    if i.conn is None:
                        i.addr = addr
                        i.token = token
                        i.init = init
                        break

                    if i.conntimer is not None:
                        i.conntimer.cancel()

                    should_connect = False
                    break

        if should_connect:
            self.connect_to_peer_direct(user, addr, msg_type, init)

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

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

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

                    i.addr = (msg.ip, msg.port)
                    i.tryaddr = None

                    self.connect_to_peer_direct(user, i.addr, i.type)

                    for j in i.msgs:
                        if j.__class__ is slskmessages.TransferRequest and self.transfers is not None:
                            self.transfers.got_address(j.req, j.direction)
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

                    self.queue.put(slskmessages.GetPeerAddress(user))
                    return

        if user in self.users:
            self.users[user].addr = (msg.ip, msg.port)
        else:
            self.users[user] = UserAddr(addr=(msg.ip, msg.port))

        if user in self.ipblock_requested:

            if self.ipblock_requested[user]:
                self.ui_callback.on_un_block_user(user)
            else:
                self.ui_callback.on_block_user(user)

            del self.ipblock_requested[user]
            return

        if user in self.ipignore_requested:

            if self.ipignore_requested[user]:
                self.ui_callback.on_un_ignore_user(user)
            else:
                self.ui_callback.on_ignore_user(user)

            del self.ipignore_requested[user]
            return

        ip_record = self.geoip.get_all(msg.ip)
        cc = ip_record.country_short

        if cc == "-":
            cc = ""

        self.ui_callback.has_user_flag(user, cc)

        # From this point on all paths should call
        # self.pluginhandler.user_resolve_notification precisely once
        if user in self.private_message_queue:
            self.private_message_queue_process(user)

        if user not in self.ip_requested:
            self.pluginhandler.user_resolve_notification(user, msg.ip, msg.port)
            return

        self.ip_requested.remove(user)
        self.pluginhandler.user_resolve_notification(user, msg.ip, msg.port, cc)

        if cc != "":
            country = " (%(cc)s / %(country)s)" % {'cc': cc, 'country': ip_record.country_long}
        else:
            country = ""

        log.add(_("IP address of %(user)s is %(ip)s, port %(port)i%(country)s"), {
            'user': user,
            'ip': msg.ip,
            'port': msg.port,
            'country': country
        })

    def process_conn_messages(self, peerconn, conn):

        """ A connection is established with the peer, time to queue up our peer
        messages for delivery """

        for j in peerconn.msgs:

            if j.__class__ is slskmessages.UserInfoRequest and self.userinfo is not None:
                self.userinfo.show_user(peerconn.username, conn=conn)

            if j.__class__ is slskmessages.GetSharedFileList and self.userbrowse is not None:
                self.userbrowse.show_user(peerconn.username, conn=conn)

            if j.__class__ is slskmessages.FileRequest and self.transfers is not None:
                self.transfers.got_file_connect(j.req, conn)

            if j.__class__ is slskmessages.TransferRequest and self.transfers is not None:
                self.transfers.got_connect(j.req, conn, j.direction)

            j.conn = conn
            self.queue.put(j)

        peerconn.msgs = []

    def inc_conn(self, msg):
        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

    def out_conn(self, msg):

        """ Networking thread told us that the connection to the peer was successful.
        If we connected directly to the peer, send a PeerInit message. If we connected
        as a result of an indirect connect request by the peer, send a PierceFirewall
        message. Queue up any messages we want to deliver to the peer. """

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        addr = msg.addr

        for i in self.peerconns:
            if i.addr == addr and i.conn is None:
                conn = msg.conn

                if i.token is None:
                    i.init.conn = conn
                    self.queue.put(i.init)

                else:
                    self.queue.put(slskmessages.PierceFireWall(conn, i.token))

                i.conn = conn

                log.add_conn("Connection established with user %(user)s, connection contains messages: %(messages)s" % {
                    'user': i.username,
                    'messages': i.msgs
                })

                # Deliver our messages to the peer
                self.process_conn_messages(i, conn)

                break

    def pierce_fire_wall(self, msg):

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        # Sometimes a token is seemingly not sent by the peer, check if the
        # IP address matches in that case

        for i in self.peerconns:
            if i.token is None or i.conn is not None:
                continue

            if msg.token is None and i.addr == msg.conn.addr or \
                    i.token == msg.token:
                conn = msg.conn.conn

                if i.conntimer is not None:
                    i.conntimer.cancel()

                i.init.conn = conn
                self.queue.put(i.init)
                i.conn = conn

                log.add_conn("Received PierceFirewall message from user %(user)s, connection contains messages: %(messages)s" % {
                    'user': i.username,
                    'messages': i.msgs
                })

                # Deliver our messages to the peer
                self.process_conn_messages(i, conn)

                break

    def close_peer_connection(self, conn, username):

        """ Forcibly close a peer connection. Only used after receiving a search result,
        as we need to get rid of connections before they pile up """

        if conn is None:
            return

        if not self.protothread.socket_still_active(conn.conn):

            for i in reversed(self.peerconns):  # File connections are added after peer connections
                if i.username == username and i.type == 'F':
                    # File transfer in progress, don't kill peer connection yet
                    return

                if i.conn == conn.conn:
                    self.peerconns.remove(i)
                    break

            self.queue.put(slskmessages.ConnClose(conn.conn, callback=False))

    def show_connection_error_message(self, conn):

        """ Request UI to show error messages related to connectivity """

        for i in conn.msgs:
            if i.__class__ in [slskmessages.TransferRequest, slskmessages.FileRequest] and self.transfers is not None:
                self.transfers.got_cant_connect(i.req)

            if i.__class__ is slskmessages.GetSharedFileList and self.userbrowse is not None:
                self.userbrowse.show_connection_error(conn.username)

            if i.__class__ is slskmessages.UserInfoRequest and self.userinfo is not None:
                self.userinfo.show_connection_error(conn.username)

    def cant_connect_to_peer(self, msg):

        """ Server informs us that an indirect connection with a peer has failed.
        Game over. """
        """ DEPRECATED. While we can still receive CantConnectToPeer messages by
        other clients, Nicotine+ does not send such messages anymore. """

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        token = msg.token

        for i in self.peerconns:
            if i.token == token:

                if i.conntimer is not None:
                    i.conntimer.cancel()

                self.peerconns.remove(i)

                self.show_connection_error_message(i)
                log.add_conn("Can't connect to user %s neither directly nor indirectly, giving up", i.username)
                break

    def connect_to_peer_timeout(self, msg):

        """ Peer was not able to repond to our indirect connection request """

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        conn = msg.conn

        try:
            self.peerconns.remove(conn)
        except ValueError:
            pass

        self.show_connection_error_message(conn)
        log.add_conn(
            "Indirect connect request of type %(type)s to user %(user)s expired, giving up", {
                'type': conn.type,
                'user': conn.username
            }
        )

    def closed_connection(self, conn, addr, error=None):

        if conn == self.active_server_conn:

            self.set_status(
                _("Disconnected from server %(host)s:%(port)s"), {
                    'host': addr[0],
                    'port': addr[1]
                }
            )
            userchoice = self.manualdisconnect

            if not self.manualdisconnect:
                self.set_server_timer()
            else:
                self.manualdisconnect = False

            self.active_server_conn = None

            # Clean up connections
            self.peerconns.clear()

            self.watchedusers.clear()
            self.shares.set_connected(False)

            if self.transfers is not None:
                self.transfers.disconnect()

            self.privatechat = self.chatrooms = self.userinfo = self.userbrowse = self.search = self.transfers = self.userlist = None
            self.ui_callback.conn_close(conn, addr)
            self.pluginhandler.server_disconnect_notification(userchoice)

        else:

            """ A peer connection has died, remove it """

            for i in self.peerconns:
                if i.conn == conn:
                    log.add_conn("Connection closed by peer: %(peer)s. Error: %(error)s", {'peer': self.contents(i), 'error': error})

                    if i.conntimer is not None:
                        i.conntimer.cancel()

                    if self.transfers is not None:
                        self.transfers.conn_close(conn, addr, i.username, error)

                    if i.type == 'D':
                        self.parent_conn_closed()

                    self.peerconns.remove(i)
                    return

    def conn_close(self, msg):

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        self.closed_connection(msg.conn, msg.addr)

    def connect_error(self, msg):

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        if msg.connobj.__class__ is slskmessages.ServerConn:

            self.set_status(
                _("Can't connect to server %(host)s:%(port)s: %(error)s"), {
                    'host': msg.connobj.addr[0],
                    'port': msg.connobj.addr[1],
                    'error': msg.err
                }
            )

            self.set_server_timer()

            if self.active_server_conn is not None:
                self.active_server_conn = None

            self.ui_callback.connect_error(msg)

        elif msg.connobj.__class__ is slskmessages.OutConn:

            addr = msg.connobj.addr

            for i in self.peerconns:
                if i.addr == addr and i.conn is None:
                    if i.token is None:

                        """ We can't correct to peer directly, request indirect connection """

                        self.connect_to_peer_indirect(i, msg.err)

                    elif i.conntimer is None:

                        """ Peer sent us an indirect connection request, and we weren't able to
                        connect to them. """

                        for j in i.msgs:
                            if j.__class__ in (slskmessages.TransferRequest, slskmessages.FileRequest) and self.transfers is not None:
                                self.transfers.got_cant_connect(j.req)

                        log.add_conn("Can't connect to user %(user)s indirectly. Error: %(error)s", {
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

        if self.upnp_interval < 1:
            return

        upnp_interval_seconds = self.upnp_interval * 60 * 60

        self.upnp_timer = threading.Timer(upnp_interval_seconds, self.add_upnp_portmapping)
        self.upnp_timer.setName("UPnPTimer")
        self.upnp_timer.setDaemon(True)
        self.upnp_timer.start()

    def add_upnp_portmapping(self):

        # Repeat
        self.start_upnp_timer()

        # Test if we want to do a port mapping
        if self.config.sections["server"]["upnp"]:

            # Initialise a UPnPPortMapping object
            from pynicotine.upnp.portmapper import UPnPPortMapping
            upnp = UPnPPortMapping()

            # Do the port mapping
            upnp.add_port_mapping(self)

    def set_server_timer(self):

        if self.server_timeout_value == -1:
            self.server_timeout_value = 15
        elif 0 < self.server_timeout_value < 600:
            self.server_timeout_value = self.server_timeout_value * 2

        self.servertimer = threading.Timer(self.server_timeout_value, self.server_timeout)
        self.servertimer.setName("ServerTimer")
        self.servertimer.setDaemon(True)
        self.servertimer.start()

        self.set_status(_("The server seems to be down or not responding, retrying in %i seconds"), (self.server_timeout_value))

    def server_timeout(self):
        if not self.config.need_config():
            self.network_callback([slskmessages.ConnectToServer()])

    def stop_timers(self):

        for i in self.peerconns:
            if i.conntimer is not None:
                i.conntimer.cancel()

        if self.servertimer is not None:
            self.servertimer.cancel()

        if self.transfers is not None:
            self.transfers.abort_transfers()

    def connect_to_server(self, msg):
        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))
        self.ui_callback.on_connect()

    # notify user of error when recieving or sending a message
    # @param self NetworkEventProcessor (Class)
    # @param string a string containing an error message
    def notify(self, string):
        log.add_msg_contents("%s", string)

    def contents(self, obj):
        """ Returns variables for object, for debug output """
        try:
            return {s: getattr(obj, s) for s in obj.__slots__ if hasattr(obj, s)}
        except AttributeError:
            return vars(obj)

    def popup_message(self, msg):
        self.set_status(_(msg.title))
        self.ui_callback.popup_message(msg)

    def set_current_connection_count(self, msg):
        self.ui_callback.set_socket_status(msg.msg)

    def inc_port(self, msg):
        self.waitport = msg.port
        self.set_status(_("Listening on port %i"), msg.port)

    def server_conn(self, msg):

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        self.set_status(
            _("Connected to server %(host)s:%(port)s, logging in..."), {
                'host': msg.addr[0],
                'port': msg.addr[1]
            }
        )

        self.active_server_conn = msg.conn
        self.server_timeout_value = -1
        self.users = {}
        self.queue.put(
            slskmessages.Login(
                self.config.sections["server"]["login"],
                self.config.sections["server"]["passw"],

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
            self.queue.put(slskmessages.SetWaitPort(self.waitport))

    def login(self, msg):

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        if msg.success:
            self.queue.put(slskmessages.SetStatus((not self.ui_callback.away) + 1))
            self.queue.put(slskmessages.AddUser(self.config.sections["server"]["login"]))

            self.transfers = transfers.Transfers(self.peerconns, self.queue, self, self.users,
                                                 self.network_callback, self.ui_callback.notifications, self.pluginhandler)
            self.shares.set_connected(True)

            if msg.ip is not None:
                self.ipaddress = msg.ip

            for i in self.config.sections["server"]["userlist"]:
                user = i[0]
                if user not in self.watchedusers:
                    self.queue.put(slskmessages.AddUser(user))

            self.privatechat, self.chatrooms, self.userinfo, self.userbrowse, self.search, downloads, uploads, self.userlist, self.interests = self.ui_callback.init_interface(msg)

            self.transfers.set_transfer_views(downloads, uploads)
            self.shares.send_num_shared_folders_files()

            for thing in self.config.sections["interests"]["likes"]:
                if thing and isinstance(thing, str):
                    self.queue.put(slskmessages.AddThingILike(thing))

            for thing in self.config.sections["interests"]["dislikes"]:
                if thing and isinstance(thing, str):
                    self.queue.put(slskmessages.AddThingIHate(thing))

            self.queue.put(slskmessages.HaveNoParent(1))

            """ TODO: Nicotine+ can currently receive search requests from a parent connection, but
            redirecting results to children is not implemented yet. Tell the server we don't accept
            children for now. """
            self.queue.put(slskmessages.AcceptChildren(0))

            self.queue.put(slskmessages.NotifyPrivileges(1, self.config.sections["server"]["login"]))
            self.privatechat.login()
            self.queue.put(slskmessages.CheckPrivileges())

            """ Request a complete room list. A limited room list not including blacklisted rooms and
            rooms with few users is automatically sent when logging in, but subsequent room list
            requests contain all rooms. """
            self.queue.put(slskmessages.RoomList())

            self.queue.put(slskmessages.PrivateRoomToggle(self.config.sections["server"]["private_chatrooms"]))
            self.pluginhandler.server_connect_notification()
        else:
            self.manualdisconnect = True
            self.set_status(_("Can not log in, reason: %s"), (msg.reason))

    def change_password(self, msg):

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        password = msg.password
        self.config.sections["server"]["passw"] = password
        self.config.write_configuration()
        self.network_callback([slskmessages.PopupMessage(_("Your password has been changed"), "Password is %s" % password)])

    def notify_privileges(self, msg):

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        if msg.token is not None:
            pass

    def user_privileged(self, msg):

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        if self.transfers is not None:
            if msg.privileged is True:
                self.transfers.add_to_privileged(msg.user)

    def ack_notify_privileges(self, msg):

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        if msg.token is not None:
            # Until I know the syntax, sending this message is probably a bad idea
            self.queue.put(slskmessages.AckNotifyPrivileges(msg.token))

    def p_message_user(self, msg):

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        conn = msg.conn.conn
        user = None

        # Get peer's username
        for i in self.peerconns:
            if i.conn is conn:
                user = i.username
                break

        if user is None:
            # No peer connection
            return

        if user != msg.user:
            text = _("(Warning: %(realuser)s is attempting to spoof %(fakeuser)s) ") % {"realuser": user, "fakeuser": msg.user} + msg.msg
            msg.user = user
        else:
            text = msg.msg

        if self.privatechat is not None:
            self.privatechat.show_message(msg, text)

    def message_user(self, msg):

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        if self.privatechat is not None:
            self.privatechat.show_message(msg, msg.msg, msg.newmessage)
            self.queue.put(slskmessages.MessageAcked(msg.msgid))

    def user_joined_room(self, msg):

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        if self.chatrooms is not None:
            self.chatrooms.user_joined_room(msg)

    def public_room_message(self, msg):

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        if self.chatrooms is not None:
            self.chatrooms.public_room_message(msg, msg.msg)
            self.pluginhandler.public_room_message_notification(msg.room, msg.user, msg.msg)

    def join_room(self, msg):

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        if self.chatrooms is not None:
            self.chatrooms.join_room(msg)

    def private_room_users(self, msg):

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        if self.chatrooms is not None:
            self.chatrooms.private_room_users(msg)

    def private_room_owned(self, msg):

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        if self.chatrooms is not None:
            self.chatrooms.private_room_owned(msg)

    def private_room_add_user(self, msg):

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        if self.chatrooms is not None:
            self.chatrooms.private_room_add_user(msg)

    def private_room_remove_user(self, msg):

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        if self.chatrooms is not None:
            self.chatrooms.private_room_remove_user(msg)

    def private_room_operator_added(self, msg):

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        if self.chatrooms is not None:
            self.chatrooms.private_room_operator_added(msg)

    def private_room_operator_removed(self, msg):

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        if self.chatrooms is not None:
            self.chatrooms.private_room_operator_removed(msg)

    def private_room_add_operator(self, msg):

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        if self.chatrooms is not None:
            self.chatrooms.private_room_add_operator(msg)

    def private_room_remove_operator(self, msg):

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        if self.chatrooms is not None:
            self.chatrooms.private_room_remove_operator(msg)

    def private_room_added(self, msg):

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        if self.chatrooms is not None:
            self.chatrooms.private_room_added(msg)

    def private_room_removed(self, msg):

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        if self.chatrooms is not None:
            self.chatrooms.private_room_removed(msg)

    def private_room_disown(self, msg):

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        if self.chatrooms is not None:
            self.chatrooms.private_room_disown(msg)

    def private_room_toggle(self, msg):

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        if self.chatrooms is not None:
            self.chatrooms.toggle_private_rooms(msg.enabled)

    def leave_room(self, msg):

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        if self.chatrooms is not None:
            self.chatrooms.leave_room(msg)

    def private_message_queue_add(self, msg, text):

        user = msg.user

        if user not in self.private_message_queue:
            self.private_message_queue[user] = [[msg, text]]
        else:
            self.private_message_queue[user].append([msg, text])

    def private_message_queue_process(self, user):

        if user in self.private_message_queue:
            for data in self.private_message_queue[user][:]:
                msg, text = data
                self.private_message_queue[user].remove(data)
                self.privatechat.show_message(msg, text)

    def ip_ignored(self, address):

        if address is None:
            return True

        ips = self.config.sections["server"]["ipignorelist"]
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

    def say_chat_room(self, msg):

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        if self.chatrooms is not None:
            event = self.pluginhandler.incoming_public_chat_event(msg.room, msg.user, msg.msg)

            if event is not None:
                (r, n, msg.msg) = event
                self.chatrooms.say_chat_room(msg, msg.msg)
                self.pluginhandler.incoming_public_chat_notification(msg.room, msg.user, msg.msg)

    def add_user(self, msg):

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        self.watchedusers.add(msg.user)

        if msg.userexists and msg.status is None:
            # Legacy support (Soulfind server)
            self.queue.put(slskmessages.GetUserStatus(msg.user))
        else:
            self.get_user_status(msg, log_contents=False)

        if msg.files is not None:
            self.get_user_stats(msg, log_contents=False)

    def privileged_users(self, msg):

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        if self.transfers is not None:
            self.transfers.set_privileged_users(msg.users)
            log.add(_("%i privileged users"), (len(msg.users)))

    def add_to_privileged(self, msg):

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        if self.transfers is not None:
            self.transfers.add_to_privileged(msg.user)

    def check_privileges(self, msg):

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        mins = msg.seconds // 60
        hours = mins // 60
        days = hours // 24

        if msg.seconds == 0:
            log.add(
                _("You have no privileges left. They are not necessary, but allow your downloads to be queued ahead of non-privileged users.")
            )
        else:
            log.add(
                _("%(days)i days, %(hours)i hours, %(minutes)i minutes, %(seconds)i seconds of download privileges left."), {
                    'days': days,
                    'hours': hours % 24,
                    'minutes': mins % 60,
                    'seconds': msg.seconds % 60
                }
            )

        self.privileges_left = msg.seconds

    def admin_message(self, msg):
        log.add("%s", (msg.msg))

    def child_depth(self, msg):
        # TODO: Implement me
        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

    def branch_level(self, msg):
        # TODO: Implement me
        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

    def branch_root(self, msg):
        # TODO: Implement me
        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

    def distrib_child_depth(self, msg):
        # TODO: Implement me
        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

    def distrib_branch_root(self, msg):
        # TODO: Implement me
        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

    def wishlist_interval(self, msg):

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        if self.search is not None:
            self.search.wish_list.set_interval(msg)

    def get_user_status(self, msg, log_contents=True):

        if log_contents:
            log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

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

        if msg.privileged is not None:
            if msg.privileged == 1:
                if self.transfers is not None:
                    self.transfers.add_to_privileged(msg.user)

        if self.interests is not None:
            self.interests.get_user_status(msg)

        if self.userlist is not None:
            self.userlist.get_user_status(msg)

        if self.transfers is not None:
            self.transfers.get_user_status(msg)

        if self.privatechat is not None:
            self.privatechat.get_user_status(msg)

        if self.userinfo is not None:
            self.userinfo.get_user_status(msg)

        if self.userbrowse is not None:
            self.userbrowse.get_user_status(msg)

        if self.chatrooms is not None:
            self.chatrooms.get_user_status(msg)

    def user_interests(self, msg):

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        if self.userinfo is not None:
            self.userinfo.show_interests(msg)

    def get_user_stats(self, msg, log_contents=True):

        if log_contents:
            log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        if msg.user == self.config.sections["server"]["login"]:
            self.speed = msg.avgspeed

        if self.interests is not None:
            self.interests.get_user_stats(msg)

        if self.chatrooms is not None:
            self.chatrooms.get_user_stats(msg)

        if self.userinfo is not None:
            self.userinfo.get_user_stats(msg)

        if self.userlist is not None:
            self.userlist.get_user_stats(msg)

        stats = {
            'avgspeed': msg.avgspeed,
            'downloadnum': msg.downloadnum,
            'files': msg.files,
            'dirs': msg.dirs,
        }

        self.pluginhandler.user_stats_notification(msg.user, stats)

    def user_left_room(self, msg):

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        if self.chatrooms is not None:
            self.chatrooms.user_left_room(msg)

    def relogged(self, msg):
        log.add(_("Someone else is logging in with the same nickname, server is going to disconnect us"))
        self.manualdisconnect = True
        self.pluginhandler.server_disconnect_notification(False)

    def check_user(self, user, ip):
        """
        Check if this user is banned, geoip-blocked, and which shares
        it is allowed to access based on transfer and shares settings.
        """

        if user in self.config.sections["server"]["banlist"]:
            if self.config.sections["transfers"]["usecustomban"]:
                return 0, "Banned (%s)" % self.config.sections["transfers"]["customban"]
            else:
                return 0, "Banned"

        if user in (i[0] for i in self.config.sections["server"]["userlist"]):
            if self.config.sections["transfers"]["enablebuddyshares"]:
                # For sending buddy-only shares
                return 2, ""

            return 1, ""

        if self.config.sections["transfers"]["friendsonly"]:
            return 0, "Sorry, friends only"

        if ip is None or not self.config.sections["transfers"]["geoblock"]:
            return 1, ""

        cc = self.geoip.get_all(ip).country_short

        if cc == "-":
            if self.config.sections["transfers"]["geopanic"]:
                return 0, "Sorry, geographical paranoia"

            return 1, ""

        """ Please note that all country codes are stored in the same string at the first index
        of an array, separated by commas (no idea why...) """

        if self.config.sections["transfers"]["geoblockcc"][0].find(cc) >= 0:
            return 0, "Sorry, your country is blocked"

        return 1, ""

    def check_spoof(self, user, ip, port):

        if user not in self.users:
            return 0

        if self.users[user].addr is not None:

            if len(self.users[user].addr) == 2:
                if self.users[user].addr is not None:
                    u_ip, u_port = self.users[user].addr
                    if u_ip != ip:
                        log.add_warning(_("IP %(ip)s:%(port)s is spoofing user %(user)s with a peer request, blocking because it does not match IP: %(real_ip)s"), {
                            'ip': ip,
                            'port': port,
                            'user': user,
                            'real_ip': u_ip
                        })
                        return 1
        return 0

    def user_info_reply(self, msg):

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        conn = msg.conn.conn

        for i in self.peerconns:
            if i.conn is conn and self.userinfo is not None:
                # probably impossible to do this
                if i.username != self.config.sections["server"]["login"]:
                    indeterminate_progress = change_page = False
                    self.userinfo.show_user(i.username, None, msg, indeterminate_progress, change_page)
                    break

    def user_info_request(self, msg):

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        user = ip = port = None
        conn = msg.conn.conn

        # Get peer's username, ip and port
        for i in self.peerconns:
            if i.conn is conn:
                user = i.username
                if i.addr is not None:
                    ip, port = i.addr
                break

        if user is None:
            # No peer connection
            return

        request_time = time.time()

        if user in self.requested_info:
            if not request_time > 10 + self.requested_info[user]:
                # Ignoring request, because it's 10 or less seconds since the
                # last one by this user
                return

        self.requested_info[user] = request_time

        # Check address is spoofed, if possible
        if user == self.config.sections["server"]["login"]:

            if ip is not None and port is not None:
                log.add(
                    _("Blocking %(user)s from making a UserInfo request, possible spoofing attempt from IP %(ip)s port %(port)s"), {
                        'user': user,
                        'ip': ip,
                        'port': port
                    }
                )
            else:
                log.add(_("Blocking %s from making a UserInfo request, possible spoofing attempt from an unknown IP & port"), user)

            if conn is not None:
                self.queue.put(slskmessages.ConnClose(conn))

            return

        if user in self.config.sections["server"]["banlist"]:

            log.add_warning(
                _("%(user)s is banned, but is making a UserInfo request"), {
                    'user': user
                }
            )

            log.add_warning("%s %s", (msg.__class__, self.contents(msg)))

            return

        try:
            userpic = self.config.sections["userinfo"]["pic"]

            with open(userpic, 'rb') as f:
                pic = f.read()

        except Exception:
            pic = None

        descr = unescape(self.config.sections["userinfo"]["descr"])

        if self.transfers is not None:
            totalupl = self.transfers.get_total_uploads_allowed()
            queuesize = self.transfers.get_upload_queue_sizes()[0]
            slotsavail = self.transfers.allow_new_uploads()

            if self.config.sections["transfers"]["remotedownloads"]:
                uploadallowed = self.config.sections["transfers"]["uploadallowed"]
            else:
                uploadallowed = 0

            self.queue.put(slskmessages.UserInfoReply(conn, descr, pic, totalupl, queuesize, slotsavail, uploadallowed))

        log.add(
            _("%(user)s is making a UserInfo request"), {
                'user': user
            }
        )

    def shared_file_list(self, msg):

        conn = msg.conn.conn

        for i in self.peerconns:
            if i.conn is conn and self.userbrowse is not None:
                if i.username != self.config.sections["server"]["login"]:
                    indeterminate_progress = change_page = False
                    self.userbrowse.show_user(i.username, None, msg, indeterminate_progress, change_page)
                    break

    def file_search_result(self, msg):

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        conn = msg.conn
        addr = conn.addr

        if self.search is not None:
            if addr:
                country = self.geoip.get_all(addr[0]).country_short
            else:
                country = ""

            if country == "-":
                country = ""

            self.search.show_result(msg, msg.user, country)

            # Close peer connection immediately, otherwise we exhaust our connection limit
            self.close_peer_connection(conn, msg.user)

    def transfer_timeout(self, msg):

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        if self.transfers is not None:
            self.transfers.transfer_timeout(msg)

    def check_download_queue(self, msg):

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        if self.transfers is not None:
            self.transfers.check_download_queue()

    def file_download(self, msg):

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        if self.transfers is not None:
            self.transfers.file_download(msg)

    def file_upload(self, msg):

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        if self.transfers is not None:
            self.transfers.file_upload(msg)

    def file_request(self, msg):

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        if self.transfers is not None:
            self.transfers.file_request(msg)

    def file_error(self, msg):

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        if self.transfers is not None:
            self.transfers.file_error(msg)

    def transfer_request(self, msg):
        """ Peer code: 40 """

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        if self.transfers is not None:
            self.transfers.transfer_request(msg)

    def transfer_response(self, msg):
        """ Peer code: 41 """

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        if self.transfers is not None:
            self.transfers.transfer_response(msg)

    def queue_upload(self, msg):
        """ Peer code: 43 """

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        if self.transfers is not None:
            self.transfers.queue_upload(msg)

    def queue_failed(self, msg):
        """ Peer code: 50 """

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        if self.transfers is not None:
            self.transfers.queue_failed(msg)

    def place_in_queue_request(self, msg):
        """ Peer code: 51 """

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        if self.transfers is not None:
            self.transfers.place_in_queue_request(msg)

    def upload_queue_notification(self, msg):
        """ Peer code: 52 """

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        if self.transfers is not None:
            self.transfers.upload_queue_notification(msg)

    def upload_failed(self, msg):
        """ Peer code: 46 """

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        if self.transfers is not None:
            self.transfers.upload_failed(msg)

    def place_in_queue(self, msg):
        """ Peer code: 44 """

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        if self.transfers is not None:
            self.transfers.place_in_queue(msg)

    def get_shared_file_list(self, msg):
        """ Peer code: 4 """

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        user = ip = port = None
        conn = msg.conn.conn

        # Get peer's username, ip and port
        for i in self.peerconns:
            if i.conn is conn:
                user = i.username
                if i.addr is not None:
                    if len(i.addr) != 2:
                        break
                    ip, port = i.addr
                break

        if user is None:
            # No peer connection
            return

        # Check address is spoofed, if possible
        # if self.check_spoof(user, ip, port):
        #     # Message IS spoofed
        #     return
        if user == self.config.sections["server"]["login"]:
            if ip is not None and port is not None:
                log.add(
                    _("%(user)s is making a BrowseShares request, blocking possible spoofing attempt from IP %(ip)s port %(port)s"), {
                        'user': user,
                        'ip': ip,
                        'port': port
                    })
            else:
                log.add(
                    _("%(user)s is making a BrowseShares request, blocking possible spoofing attempt from an unknown IP & port"), {
                        'user': user
                    })

            if conn is not None:
                self.queue.put(slskmessages.ConnClose(conn))
            return

        log.add(_("%(user)s is making a BrowseShares request"), {
            'user': user
        })

        ip, port = msg.conn.addr
        checkuser, reason = self.check_user(user, ip)

        if checkuser == 1:
            # Send Normal Shares
            if self.shares.newnormalshares:
                self.shares.create_compressed_shares_message("normal")
                self.shares.compress_shares("normal")
                self.shares.newnormalshares = False
            m = self.shares.compressed_shares_normal

        elif checkuser == 2:
            # Send Buddy Shares
            if self.shares.newbuddyshares:
                self.shares.create_compressed_shares_message("buddy")
                self.shares.compress_shares("buddy")
                self.shares.newbuddyshares = False
            m = self.shares.compressed_shares_buddy

        else:
            # Nyah, Nyah
            m = slskmessages.SharedFileList(conn, {})
            m.make_network_message(nozlib=0)

        m.conn = conn
        self.queue.put(m)

    def folder_contents_request(self, msg):
        """ Peer code: 36 """

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        conn = msg.conn.conn
        ip, port = msg.conn.addr
        username = None
        checkuser = None
        reason = ""

        for i in self.peerconns:
            if i.conn is conn:
                username = i.username
                checkuser, reason = self.check_user(username, ip)
                break

        if not username:
            return
        if not checkuser:
            self.queue.put(slskmessages.MessageUser(username, "[Automatic Message] " + reason))
            return

        if checkuser == 1:
            shares = self.shares.share_dbs["streams"]
        elif checkuser == 2:
            shares = self.shares.share_dbs["streams"]
        else:
            self.queue.put(slskmessages.TransferResponse(conn, 0, reason=reason, req=0))
            shares = {}

        if checkuser:
            if msg.dir in shares:
                self.queue.put(slskmessages.FolderContentsResponse(conn, msg.dir, shares[msg.dir]))
            elif msg.dir.rstrip('\\') in shares:
                self.queue.put(slskmessages.FolderContentsResponse(conn, msg.dir, shares[msg.dir.rstrip('\\')]))
            else:
                if checkuser == 2:
                    shares = self.shares.share_dbs["streams"]
                    if msg.dir in shares:
                        self.queue.put(slskmessages.FolderContentsResponse(conn, msg.dir, shares[msg.dir]))
                    elif msg.dir.rstrip("\\") in shares:
                        self.queue.put(slskmessages.FolderContentsResponse(conn, msg.dir, shares[msg.dir.rstrip("\\")]))

    def folder_contents_response(self, msg):
        """ Peer code: 37 """

        if self.transfers is not None:
            conn = msg.conn.conn
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
                for i in self.peerconns:
                    if i.conn is conn:
                        username = i.username
                        break

                self.transfers.downloadsview.download_large_folder(username, folder, numfiles, conn, file_list)
            else:
                self.transfers.folder_contents_response(conn, file_list)

    def room_list(self, msg):
        """ Server code: 64 """

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        if self.chatrooms is not None:
            self.chatrooms.set_room_list(msg)
            self.set_status("")

    def global_user_list(self, msg):
        """ Server code: 67 """

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        if self.globallist is not None:
            self.globallist.set_global_users_list(msg)

    def peer_transfer(self, msg):
        if self.userinfo is not None and msg.msg is slskmessages.UserInfoReply:
            self.userinfo.update_gauge(msg)

        if self.userbrowse is not None and msg.msg is slskmessages.SharedFileList:
            self.userbrowse.update_gauge(msg)

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
            log.add_msg_contents("Unknown tunneled message: %s", self.contents(msg))

    def file_search_request(self, msg):
        """ Peer code: 8 """

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        conn = msg.conn.conn

        for i in self.peerconns:
            if i.conn == conn:
                user = i.username
                self.shares.process_search_request(msg.searchterm, user, msg.searchid, direct=True)
                break

    def search_request(self, msg):
        """ Server code: 93 """

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        self.shares.process_search_request(msg.searchterm, msg.user, msg.searchid, direct=False)
        self.pluginhandler.search_request_notification(msg.searchterm, msg.user, msg.searchid)

    def room_search_request(self, msg):
        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))
        self.shares.process_search_request(msg.searchterm, msg.room, msg.searchid, direct=False)

    def distrib_search(self, msg):
        """ Distrib code: 3 """

        self.shares.process_search_request(msg.searchterm, msg.user, msg.searchid, direct=False)
        self.pluginhandler.distrib_search_notification(msg.searchterm, msg.user, msg.searchid)

    def possible_parents(self, msg):
        """ Server code: 102 """

        """ Server sent a list of 10 potential parents, whose purpose is to forward us search requests.
        We attempt to connect to them all at once, since connection errors are fairly common. """

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        potential_parents = msg.list

        if not self.has_parent and potential_parents:

            for user in potential_parents:
                addr = potential_parents[user]

                self.send_message_to_peer(user, slskmessages.DistribConn(), address=addr)

    def get_parent_conn(self):

        for i in self.peerconns:
            if i.type == 'D':
                return i

        return None

    def parent_conn_closed(self):
        """ Tell the server it needs to send us a NetInfo message with a new list of
        potential parents. """

        self.has_parent = False
        self.queue.put(slskmessages.HaveNoParent(1))

    def distrib_branch_level(self, msg):
        """ Distrib code: 4 """

        """ This message is received when we have a successful connection with a potential
        parent. Tell the server who our parent is, and stop requesting new potential parents. """

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        if not self.has_parent:

            for i in self.peerconns[:]:
                if i.type == 'D':
                    """ We previously attempted to connect to all potential parents. Since we now
                    have a parent, stop connecting to the others. """

                    if i.conn != msg.conn.conn:
                        if i.conn is not None:
                            self.queue.put(slskmessages.ConnClose(i.conn, callback=False))

                        if i.conntimer is not None:
                            i.conntimer.cancel()

                        self.peerconns.remove(i)

            parent = self.get_parent_conn()

            if parent is not None:
                self.queue.put(slskmessages.HaveNoParent(0))
                self.queue.put(slskmessages.SearchParent(msg.conn.addr[0]))
                self.has_parent = True
            else:
                self.parent_conn_closed()

    def global_recommendations(self, msg):
        """ Server code: 56 """

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        if self.interests is not None:
            self.interests.global_recommendations(msg)

    def recommendations(self, msg):
        """ Server code: 54 """

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        if self.interests is not None:
            self.interests.recommendations(msg)

    def item_recommendations(self, msg):
        """ Server code: 111 """

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        if self.interests is not None:
            self.interests.item_recommendations(msg)

    def similar_users(self, msg):
        """ Server code: 110 """

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        if self.interests is not None:
            self.interests.similar_users(msg)

    def room_ticker_state(self, msg):
        """ Server code: 113 """

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        if self.chatrooms is not None:
            self.chatrooms.ticker_set(msg)

    def room_ticker_add(self, msg):
        """ Server code: 114 """

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        if self.chatrooms is not None:
            self.chatrooms.ticker_add(msg)

    def room_ticker_remove(self, msg):
        """ Server code: 115 """

        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

        if self.chatrooms is not None:
            self.chatrooms.ticker_remove(msg)

    def update_debug_log_options(self):
        """ Gives the logger updated logging settings """

        should_log = self.config.sections["logging"]["debug_file_output"]
        log_folder = self.config.sections["logging"]["debuglogsdir"]
        timestamp_format = self.config.sections["logging"]["log_timestamp"]

        log.set_log_to_file(should_log)
        log.set_folder(log_folder)
        log.set_timestamp_format(timestamp_format)

    def dummy_message(self, msg):
        log.add_msg_contents("%s %s", (msg.__class__, self.contents(msg)))

    def ignore(self, msg):
        # Ignore received message
        pass
