# COPYRIGHT (C) 2020-2022 Nicotine+ Contributors
# COPYRIGHT (C) 2020-2022 Mathias <mail@mathias.is>
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
import sys

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
from pynicotine.upnp import UPnP
from pynicotine.userbrowse import UserBrowse
from pynicotine.userinfo import UserInfo
from pynicotine.userlist import UserList


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
        self.upnp = None
        self.geoip = None
        self.notifications = None

        # Handle Ctrl+C and "kill" exit gracefully
        for signal_type in (signal.SIGINT, signal.SIGTERM):
            signal.signal(signal_type, self.quit)

        self.bindip = bindip
        self.port = port

        self.shutdown = False
        self.away = False
        self.logged_in = False
        self.login_username = None  # Only present while logged in
        self.user_ip_address = None
        self.privileges_left = None
        self.ban_message = "You are banned from downloading my shared files. Ban message: \"%s\""

        self.events = {}
        self.queue = deque()
        self.user_statuses = {}
        self.watched_users = set()
        self.ip_requested = set()

    """ Actions """

    def start(self, ui_callback, network_callback):

        self.ui_callback = ui_callback
        self.network_callback = network_callback
        script_dir = os.path.dirname(__file__)

        log.add(_("Loading %(program)s %(version)s"), {"program": "Python", "version": config.python_version})
        log.add_debug("Using %(program)s executable: %(exe)s", {"program": "Python", "exe": str(sys.executable)})
        log.add_debug("Using %(program)s executable: %(exe)s", {"program": config.application_name, "exe": script_dir})
        log.add(_("Loading %(program)s %(version)s"), {"program": config.application_name, "version": config.version})

        self.geoip = GeoIP(os.path.join(script_dir, "geoip/ipcountrydb.bin"))
        self.notifications = Notifications(config, ui_callback)
        self.network_filter = NetworkFilter(self, config, self.queue, self.geoip)
        self.now_playing = NowPlaying(config)
        self.statistics = Statistics(config, ui_callback)

        self.shares = Shares(self, config, self.queue, self.network_callback, ui_callback)
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
            self.network_callback, self.queue, self.bindip, interface, self.port, port_range)
        self.upnp = UPnP(self, config)
        self.pluginhandler = PluginHandler(self, config)

        # Callback handlers for messages
        self.events = {
            slskmessages.ServerDisconnect: self.server_disconnect,
            slskmessages.Login: self.login,
            slskmessages.ChangePassword: self.change_password,
            slskmessages.MessageUser: self.privatechats.message_user,
            slskmessages.PMessageUser: self.privatechats.p_message_user,
            slskmessages.ExactFileSearch: self.dummy_message,
            slskmessages.RoomAdded: self.dummy_message,
            slskmessages.RoomRemoved: self.dummy_message,
            slskmessages.UserJoinedRoom: self.chatrooms.user_joined_room,
            slskmessages.SayChatroom: self.chatrooms.say_chat_room,
            slskmessages.JoinRoom: self.chatrooms.join_room,
            slskmessages.UserLeftRoom: self.chatrooms.user_left_room,
            slskmessages.CantCreateRoom: self.dummy_message,
            slskmessages.QueuedDownloads: self.dummy_message,
            slskmessages.GetPeerAddress: self.get_peer_address,
            slskmessages.UserInfoReply: self.userinfo.user_info_reply,
            slskmessages.UserInfoRequest: self.userinfo.user_info_request,
            slskmessages.PierceFireWall: self.dummy_message,
            slskmessages.ConnectToPeer: self.connect_to_peer,
            slskmessages.CantConnectToPeer: self.dummy_message,
            slskmessages.MessageProgress: self.message_progress,
            slskmessages.SharedFileList: self.userbrowse.shared_file_list,
            slskmessages.GetSharedFileList: self.shares.get_shared_file_list,
            slskmessages.FileSearchRequest: self.dummy_message,
            slskmessages.FileSearchResult: self.search.file_search_result,
            slskmessages.GetUserStatus: self.get_user_status,
            slskmessages.GetUserStats: self.get_user_stats,
            slskmessages.Relogged: self.dummy_message,
            slskmessages.PeerInit: self.dummy_message,
            slskmessages.CheckDownloadQueue: self.transfers.check_download_queue_callback,
            slskmessages.CheckUploadQueue: self.transfers.check_upload_queue_callback,
            slskmessages.DownloadFile: self.transfers.file_download,
            slskmessages.UploadFile: self.transfers.file_upload,
            slskmessages.FileDownloadInit: self.transfers.file_download_init,
            slskmessages.FileUploadInit: self.transfers.file_upload_init,
            slskmessages.TransferRequest: self.transfers.transfer_request,
            slskmessages.TransferResponse: self.transfers.transfer_response,
            slskmessages.QueueUpload: self.transfers.queue_upload,
            slskmessages.UploadDenied: self.transfers.upload_denied,
            slskmessages.UploadFailed: self.transfers.upload_failed,
            slskmessages.PlaceInQueue: self.transfers.place_in_queue,
            slskmessages.DownloadFileError: self.transfers.download_file_error,
            slskmessages.UploadFileError: self.transfers.upload_file_error,
            slskmessages.DownloadConnClose: self.transfers.download_conn_close,
            slskmessages.UploadConnClose: self.transfers.upload_conn_close,
            slskmessages.FolderContentsResponse: self.transfers.folder_contents_response,
            slskmessages.FolderContentsRequest: self.shares.folder_contents_request,
            slskmessages.RoomList: self.chatrooms.room_list,
            slskmessages.LeaveRoom: self.chatrooms.leave_room,
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
            slskmessages.WishlistInterval: self.search.set_wishlist_interval,
            slskmessages.DistribAliveInterval: self.dummy_message,
            slskmessages.DistribChildDepth: self.dummy_message,
            slskmessages.DistribBranchLevel: self.dummy_message,
            slskmessages.DistribBranchRoot: self.dummy_message,
            slskmessages.AdminMessage: self.admin_message,
            slskmessages.TunneledMessage: self.dummy_message,
            slskmessages.PlaceholdUpload: self.dummy_message,
            slskmessages.PlaceInQueueRequest: self.transfers.place_in_queue_request,
            slskmessages.UploadQueueNotification: self.dummy_message,
            slskmessages.FileSearch: self.search.search_request,
            slskmessages.RoomSearch: self.search.search_request,
            slskmessages.UserSearch: self.search.search_request,
            slskmessages.RelatedSearch: self.dummy_message,
            slskmessages.PossibleParents: self.dummy_message,
            slskmessages.DistribAlive: self.dummy_message,
            slskmessages.DistribSearch: self.search.distrib_search,
            slskmessages.ResetDistributed: self.dummy_message,
            slskmessages.ServerTimeout: self.server_timeout,
            slskmessages.TransferTimeout: self.transfers.transfer_timeout,
            slskmessages.SetConnectionStats: self.set_connection_stats,
            slskmessages.GlobalRecommendations: self.interests.global_recommendations,
            slskmessages.Recommendations: self.interests.recommendations,
            slskmessages.ItemRecommendations: self.interests.item_recommendations,
            slskmessages.SimilarUsers: self.interests.similar_users,
            slskmessages.ItemSimilarUsers: self.interests.item_similar_users,
            slskmessages.UserInterests: self.userinfo.user_interests,
            slskmessages.RoomTickerState: self.chatrooms.ticker_set,
            slskmessages.RoomTickerAdd: self.chatrooms.ticker_add,
            slskmessages.RoomTickerRemove: self.chatrooms.ticker_remove,
            slskmessages.UserPrivileged: self.dummy_message,
            slskmessages.AckNotifyPrivileges: self.dummy_message,
            slskmessages.NotifyPrivileges: self.dummy_message,
            slskmessages.PrivateRoomUsers: self.chatrooms.private_room_users,
            slskmessages.PrivateRoomOwned: self.chatrooms.private_room_owned,
            slskmessages.PrivateRoomAddUser: self.chatrooms.private_room_add_user,
            slskmessages.PrivateRoomRemoveUser: self.chatrooms.private_room_remove_user,
            slskmessages.PrivateRoomAdded: self.chatrooms.private_room_added,
            slskmessages.PrivateRoomRemoved: self.chatrooms.private_room_removed,
            slskmessages.PrivateRoomDisown: self.chatrooms.private_room_disown,
            slskmessages.PrivateRoomToggle: self.chatrooms.private_room_toggle,
            slskmessages.PrivateRoomSomething: self.dummy_message,
            slskmessages.PrivateRoomOperatorAdded: self.chatrooms.private_room_operator_added,
            slskmessages.PrivateRoomOperatorRemoved: self.chatrooms.private_room_operator_removed,
            slskmessages.PrivateRoomAddOperator: self.chatrooms.private_room_add_operator,
            slskmessages.PrivateRoomRemoveOperator: self.chatrooms.private_room_remove_operator,
            slskmessages.PublicRoomMessage: self.chatrooms.public_room_message,
            slskmessages.ShowConnectionErrorMessage: self.show_connection_error_message,
            slskmessages.UnknownPeerMessage: self.ignore
        }

    def quit(self, signal_type=None, _frame=None):

        log.add(_("Quitting %(program)s %(version)s, %(status)s…"), {
            "program": config.application_name,
            "version": config.version,
            "status": _("terminating") if signal_type == signal.SIGTERM else _("application closing")
        })

        # Indicate that a shutdown has started, to prevent UI callbacks from networking thread
        self.shutdown = True

        if self.pluginhandler:
            self.pluginhandler.quit()

        # Shut down networking thread
        if self.protothread:
            if not self.protothread.server_disconnected:
                self.protothread.manual_server_disconnect = True
                self.server_disconnect()

            self.protothread.abort()

        # Save download/upload list to file
        if self.transfers:
            self.transfers.quit()

        # Closing up all shelves db
        if self.shares:
            self.shares.quit()

        if self.ui_callback:
            self.ui_callback.quit()

        log.add(_("Quit %(program)s %(version)s, %(status)s!"), {
            "program": config.application_name,
            "version": config.version,
            "status": _("terminated") if signal_type == signal.SIGTERM else _("done")
        })

    def connect(self):

        if not self.protothread.server_disconnected:
            return True

        if config.need_config():
            log.add(_("You need to specify a username and password before connecting…"))
            self.ui_callback.setup()
            return False

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

        # Clear any potential messages queued up while offline
        self.queue.clear()

        addr = config.sections["server"]["server"]
        login = config.sections["server"]["login"]
        password = config.sections["server"]["passw"]

        self.protothread.server_disconnected = False
        self.queue.append(slskmessages.ServerConnect(addr, login=(login, password)))
        return True

    def disconnect(self):
        self.queue.append(slskmessages.ServerDisconnect())

    def send_message_to_peer(self, user, message, address=None):
        """ Sends message to a peer. Used when we know the username of a peer,
        but don't have/know an active connection. """

        self.queue.append(slskmessages.SendNetworkMessage(user, message, address))

    def set_away_mode(self, is_away, save_state=False):

        if save_state:
            config.sections["server"]["away"] = is_away

        self.away = is_away
        self.request_set_status(is_away and 1 or 2)

        # Reset away message users
        self.privatechats.set_away_mode(is_away)
        self.ui_callback.set_away_mode(is_away)

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

        user_address = self.protothread.user_addresses.get(user)

        if user_address and user != self.protothread.server_username:
            ip_address, _port = user_address
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

    """ Network Events """

    def network_event(self, msgs):

        for i in msgs:
            if self.shutdown:
                return

            if i.__class__ in self.events:
                self.events[i.__class__](i)

            else:
                log.add("No handler for class %s %s", (i.__class__, dir(i)))

        msgs.clear()

    @staticmethod
    def ignore(msg):
        # Ignore received message
        pass

    @staticmethod
    def dummy_message(msg):
        log.add_msg_contents(msg)

    def show_connection_error_message(self, msg):
        """ Request UI to show error messages related to connectivity """

        for i in msg.msgs:
            if i.__class__ in (slskmessages.TransferRequest, slskmessages.FileUploadInit):
                self.transfers.get_cant_connect_upload(i.token)

            elif i.__class__ is slskmessages.QueueUpload:
                self.transfers.get_cant_connect_queue_file(msg.user, i.file)

            elif i.__class__ is slskmessages.GetSharedFileList:
                self.userbrowse.show_connection_error(msg.user)

            elif i.__class__ is slskmessages.UserInfoRequest:
                self.userinfo.show_connection_error(msg.user)

    def message_progress(self, msg):

        if msg.msg_type is slskmessages.SharedFileList:
            self.userbrowse.message_progress(msg)

        elif msg.msg_type is slskmessages.UserInfoReply:
            self.userinfo.message_progress(msg)

    def server_timeout(self, _msg):
        if not config.need_config():
            self.connect()

    def server_disconnect(self, msg=None):

        self.logged_in = False

        # Clean up connections
        self.user_statuses.clear()
        self.watched_users.clear()

        self.pluginhandler.server_disconnect_notification(msg.manual_disconnect if msg else True)

        self.transfers.server_disconnect()
        self.search.server_disconnect()
        self.userlist.server_disconnect()
        self.chatrooms.server_disconnect()
        self.privatechats.server_disconnect()
        self.userinfo.server_disconnect()
        self.userbrowse.server_disconnect()
        self.interests.server_disconnect()
        self.ui_callback.server_disconnect()

        self.login_username = None

    def set_connection_stats(self, msg):
        self.ui_callback.set_connection_stats(msg)

    def login(self, msg):
        """ Server code: 1 """

        log.add_msg_contents(msg)

        if msg.success:
            self.logged_in = True
            self.login_username = msg.username

            self.set_away_mode(config.sections["server"]["away"])
            self.watch_user(msg.username)

            if msg.ip_address is not None:
                self.user_ip_address = msg.ip_address

            self.transfers.server_login()
            self.search.server_login()
            self.userbrowse.server_login()
            self.userinfo.server_login()
            self.userlist.server_login()
            self.privatechats.server_login()
            self.chatrooms.server_login()
            self.ui_callback.server_login()

            if msg.banner:
                log.add(msg.banner)

            self.interests.server_login()
            self.shares.send_num_shared_folders_files()

            self.queue.append(slskmessages.PrivateRoomToggle(config.sections["server"]["private_chatrooms"]))
            self.pluginhandler.server_connect_notification()

        else:
            if msg.reason == "INVALIDPASS":
                self.ui_callback.invalid_password()
                return

            log.add_important_error(_("Unable to connect to the server. Reason: %s"), msg.reason)

    def get_peer_address(self, msg):
        """ Server code: 3 """

        log.add_msg_contents(msg)

        user = msg.user

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

        self.user_statuses[msg.user] = msg.status

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

    def connect_to_peer(self, msg):
        """ Server code: 18 """

        log.add_msg_contents(msg)

        if msg.privileged == 1:
            self.transfers.add_to_privileged(msg.user)

        elif msg.privileged == 0:
            self.transfers.remove_from_privileged(msg.user)

    def get_user_stats(self, msg, log_contents=True):
        """ Server code: 36 """

        if log_contents:
            log.add_msg_contents(msg)

        if msg.user == self.login_username:
            self.transfers.upload_speed = msg.avgspeed

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

    @staticmethod
    def admin_message(msg):
        """ Server code: 66 """

        log.add_important_info(msg.msg)

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
            log.add(_("You have no privileges. Privileges are not required, but allow your downloads "
                      "to be queued ahead of non-privileged users."))
        else:
            log.add(_("%(days)i days, %(hours)i hours, %(minutes)i minutes, %(seconds)i seconds of "
                      "download privileges left."), {
                'days': days,
                'hours': hours % 24,
                'minutes': mins % 60,
                'seconds': msg.seconds % 60
            })

        self.privileges_left = msg.seconds

    @staticmethod
    def change_password(msg):
        """ Server code: 142 """

        log.add_msg_contents(msg)

        password = msg.password
        config.sections["server"]["passw"] = password
        config.write_configuration()

        log.add_important_info(_("Your password has been changed"))
