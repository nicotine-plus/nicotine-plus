# COPYRIGHT (C) 2020-2022 Nicotine+ Contributors
# COPYRIGHT (C) 2020-2022 Mathias <mail@mathias.is>
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2016 Mutnick <muhing@yahoo.com>
# COPYRIGHT (C) 2013 eLvErDe <gandalf@le-vert.net>
# COPYRIGHT (C) 2008-2012 quinox <quinox@users.sf.net>
# COPYRIGHT (C) 2009 hedonist <ak@sensi.org>
# COPYRIGHT (C) 2006-2009 daelstorm <daelstorm@gmail.com>
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
import threading

from collections import deque

from pynicotine import slskmessages
from pynicotine.cli import cli
from pynicotine.config import config
from pynicotine.events import events
from pynicotine.logfacility import log


class Core:
    """ Core contains handlers for various messages from (mainly) the networking thread.
    This class links the networking thread and user interface. """

    def __init__(self):

        self.network_filter = None
        self.statistics = None
        self.shares = None
        self.search = None
        self.transfers = None
        self.interests = None
        self.userbrowse = None
        self.userinfo = None
        self.userlist = None
        self.privatechat = None
        self.chatrooms = None
        self.pluginhandler = None
        self.now_playing = None
        self.protothread = None
        self.geoip = None
        self.notifications = None
        self.update_checker = None

        # Handle Ctrl+C and "kill" exit gracefully
        for signal_type in (signal.SIGINT, signal.SIGTERM):
            signal.signal(signal_type, self.quit)

        self.bindip = None
        self.port = None

        self.shutdown = False
        self.enable_cli = False
        self.user_status = slskmessages.UserStatus.OFFLINE
        self.login_username = None  # Only present while logged in
        self.user_ip_address = None
        self.privileges_left = None
        self.ban_message = 'You are banned from downloading my shared files. Ban message: "%s"'

        self.queue = deque()
        self.message_events = {}
        self.user_addresses = {}
        self.user_statuses = {}
        self.watched_users = set()
        self._ip_requested = set()

        for event_name, callback in (
            ("admin-message", self._admin_message),
            ("change-password", self._change_password),
            ("check-privileges", self._check_privileges),
            ("peer-address", self._get_peer_address),
            ("privileged-users", self._privileged_users),
            ("server-disconnect", self._server_disconnect),
            ("server-login", self._server_login),
            ("server-timeout", self._server_timeout),
            ("thread-callback", self._thread_callback),
            ("user-stats", self._user_stats),
            ("user-status", self._user_status),
            ("watch-user", self._watch_user)
        ):
            events.connect(event_name, callback)

    def init_components(self, enable_cli=False):

        from pynicotine.chatrooms import ChatRooms
        from pynicotine.geoip import GeoIP
        from pynicotine.interests import Interests
        from pynicotine.networkfilter import NetworkFilter
        from pynicotine.notifications import Notifications
        from pynicotine.nowplaying import NowPlaying
        from pynicotine.pluginsystem import PluginHandler
        from pynicotine.privatechat import PrivateChat
        from pynicotine.search import Search
        from pynicotine.shares import Shares
        from pynicotine.slskproto import SoulseekNetworkThread
        from pynicotine.statistics import Statistics
        from pynicotine.transfers import Transfers
        from pynicotine.updatechecker import UpdateChecker
        from pynicotine.userbrowse import UserBrowse
        from pynicotine.userinfo import UserInfo
        from pynicotine.userlist import UserList

        self.enable_cli = enable_cli
        self._init_thread_exception_hook()
        config.load_config()

        if enable_cli:
            cli.enable_logging()

        script_dir = os.path.dirname(__file__)

        log.add(_("Loading %(program)s %(version)s"), {"program": "Python", "version": config.python_version})
        log.add_debug("Using %(program)s executable: %(exe)s", {"program": "Python", "exe": str(sys.executable)})
        log.add_debug("Using %(program)s executable: %(exe)s", {"program": config.application_name, "exe": script_dir})
        log.add(_("Loading %(program)s %(version)s"), {"program": config.application_name, "version": config.version})

        self.queue.clear()
        self.protothread = SoulseekNetworkThread(queue=self.queue, user_addresses=self.user_addresses)

        self.geoip = GeoIP()
        self.notifications = Notifications()
        self.network_filter = NetworkFilter()
        self.now_playing = NowPlaying()
        self.statistics = Statistics()
        self.update_checker = UpdateChecker()

        self.shares = Shares()
        self.search = Search()
        self.transfers = Transfers()
        self.interests = Interests()
        self.userbrowse = UserBrowse()
        self.userinfo = UserInfo()
        self.userlist = UserList()
        self.privatechat = PrivateChat()
        self.chatrooms = ChatRooms()
        self.pluginhandler = PluginHandler()

    def _init_thread_exception_hook(self):

        def thread_excepthook(args):
            sys.excepthook(*args[:3])

        if hasattr(threading, "excepthook"):
            threading.excepthook = thread_excepthook
            return

        # Workaround for Python <= 3.7
        init_thread = threading.Thread.__init__

        def init_thread_excepthook(self, *args, **kwargs):

            init_thread(self, *args, **kwargs)
            run_thread = self.run

            def run_with_excepthook(*args2, **kwargs2):
                try:
                    run_thread(*args2, **kwargs2)
                except Exception:
                    thread_excepthook(sys.exc_info())

            self.run = run_with_excepthook

        threading.Thread.__init__ = init_thread_excepthook

    """ Actions """

    def start(self):

        if self.enable_cli:
            cli.enable_prompt()

        events.emit("start")

    def setup(self):
        events.emit("setup")

    def confirm_quit(self, remember=False):

        if config.sections["ui"]["exitdialog"] != 0:  # 0: 'Quit program'
            events.emit("confirm-quit", remember)
            return

        self.quit()

    def quit(self, signal_type=None, _frame=None):

        log.add(_("Quitting %(program)s %(version)s, %(status)s…"), {
            "program": config.application_name,
            "version": config.version,
            "status": _("terminating") if signal_type == signal.SIGTERM else _("application closing")
        })

        # Indicate that a shutdown has started, to prevent UI callbacks from networking thread
        self.shutdown = True
        manual_disconnect = True

        events.emit("server-disconnect", manual_disconnect)
        events.emit("quit")

        log.add(_("Quit %(program)s %(version)s, %(status)s!"), {
            "program": config.application_name,
            "version": config.version,
            "status": _("terminated") if signal_type == signal.SIGTERM else _("done")
        })
        log.close_log_files()

    def connect(self):

        if config.need_config():
            log.add(_("You need to specify a username and password before connecting…"))
            self.setup()
            return

        events.emit("enable-message-queue")

        self.queue.append(slskmessages.ServerConnect(
            addr=config.sections["server"]["server"],
            login=(config.sections["server"]["login"], config.sections["server"]["passw"]),
            interface=config.sections["server"]["interface"],
            bound_ip=self.bindip,
            listen_port_range=(self.port, self.port) if self.port else config.sections["server"]["portrange"]
        ))

    def disconnect(self):
        self.queue.append(slskmessages.ServerDisconnect())

    def send_message_to_peer(self, user, message):
        """ Sends message to a peer. Used when we know the username of a peer,
        but don't have/know an active connection. """

        self.queue.append(slskmessages.SendNetworkMessage(user, message))

    def set_away_mode(self, is_away, save_state=False):

        if save_state:
            config.sections["server"]["away"] = is_away

        self.user_status = slskmessages.UserStatus.AWAY if is_away else slskmessages.UserStatus.ONLINE
        self.request_set_status(is_away and 1 or 2)

        # Reset away message users
        events.emit("set-away-mode", is_away)

    def request_change_password(self, password):
        self.queue.append(slskmessages.ChangePassword(password))

    def request_check_privileges(self):
        self.queue.append(slskmessages.CheckPrivileges())

    def request_give_privileges(self, user, days):
        self.queue.append(slskmessages.GivePrivileges(user, days))

    def request_ip_address(self, username):
        self._ip_requested.add(username)
        self.queue.append(slskmessages.GetPeerAddress(username))

    def request_set_status(self, status):
        self.queue.append(slskmessages.SetStatus(status))

    def get_user_country(self, user):
        """ Retrieve a user's country code if previously cached, otherwise request
        user's IP address to determine country """

        if self.user_status == slskmessages.UserStatus.OFFLINE:
            return None

        user_address = self.user_addresses.get(user)

        if user_address and user != self.login_username:
            ip_address, _port = user_address
            country_code = self.geoip.get_country_code(ip_address)
            return country_code

        if user not in self._ip_requested:
            self.queue.append(slskmessages.GetPeerAddress(user))

        return None

    def watch_user(self, user, force_update=False):
        """ Tell the server we want to be notified of status/stat updates
        for a user """

        if self.user_status == slskmessages.UserStatus.OFFLINE:
            return

        if not force_update and user in self.watched_users:
            # Already being watched, and we don't need to re-fetch the status/stats
            return

        self.queue.append(slskmessages.WatchUser(user))

        # Get privilege status
        self.queue.append(slskmessages.GetUserStatus(user))

        self.watched_users.add(user)

    """ Message Callbacks """

    def _thread_callback(self, callback, *args, **kwargs):
        callback(*args, **kwargs)

    def _server_timeout(self):
        if not config.need_config():
            self.connect()

    def _server_disconnect(self, manual_disconnect=False):

        self.user_status = slskmessages.UserStatus.OFFLINE

        # Clean up connections
        self.user_addresses.clear()
        self.user_statuses.clear()
        self.watched_users.clear()

        if self.pluginhandler:
            self.pluginhandler.server_disconnect_notification(manual_disconnect)

        self.login_username = None

    def _server_login(self, msg):
        """ Server code: 1 """

        if msg.success:
            self.user_status = slskmessages.UserStatus.ONLINE
            self.login_username = msg.username

            self.set_away_mode(config.sections["server"]["away"])
            self.watch_user(msg.username)

            if msg.ip_address is not None:
                self.user_ip_address = msg.ip_address

            if msg.banner:
                log.add(msg.banner)

            self.queue.append(slskmessages.PrivateRoomToggle(config.sections["server"]["private_chatrooms"]))
            self.pluginhandler.server_connect_notification()

        else:
            if msg.reason == slskmessages.LoginFailure.PASSWORD:
                events.emit("invalid-password")
                return

            log.add(_("Unable to connect to the server. Reason: %s"), msg.reason, title=_("Cannot Connect"))

    def _get_peer_address(self, msg):
        """ Server code: 3 """

        user = msg.user
        country_code = self.geoip.get_country_code(msg.ip_address)
        events.emit("user-country", user, country_code)

        if user not in self._ip_requested:
            self.pluginhandler.user_resolve_notification(user, msg.ip_address, msg.port)
            return

        self._ip_requested.remove(user)
        self.pluginhandler.user_resolve_notification(user, msg.ip_address, msg.port, country_code)

        if country_code:
            country_name = self.geoip.country_code_to_name(country_code)
            country = f" ({country_code} / {country_name})"
        else:
            country = ""

        if msg.ip_address == "0.0.0.0":
            log.add(_("Cannot retrieve the IP of user %s, since this user is offline"), user)
            return

        log.add(_("IP address of user %(user)s: %(ip)s, port %(port)i%(country)s"), {
            "user": user,
            "ip": msg.ip_address,
            "port": msg.port,
            "country": country
        }, title=_("IP Address"))

    def _watch_user(self, msg):
        """ Server code: 5 """

        if msg.userexists:
            events.emit("user-stats", msg)
            return

        # User does not exist, server will not keep us informed if the user is created later
        self.watched_users.discard(msg.user)

    def _user_status(self, msg):
        """ Server code: 7 """

        user = msg.user
        status = msg.status

        if status not in (slskmessages.UserStatus.OFFLINE, slskmessages.UserStatus.ONLINE,
                          slskmessages.UserStatus.AWAY):
            log.add_debug("Received an unknown status %(status)s for user %(user)s from the server", {
                "status": status,
                "user": user
            })

        if user in self.watched_users:
            self.user_statuses[user] = status

        self.pluginhandler.user_status_notification(user, status, msg.privileged)

    def _user_stats(self, msg):
        """ Server code: 36 """

        stats = {
            "avgspeed": msg.avgspeed,
            "uploadnum": msg.uploadnum,
            "files": msg.files,
            "dirs": msg.dirs,
        }

        self.pluginhandler.user_stats_notification(msg.user, stats)

    @staticmethod
    def _admin_message(msg):
        """ Server code: 66 """

        log.add(msg.msg, title=_("Soulseek Announcement"))

    def _privileged_users(self, msg):
        """ Server code: 69 """

        for user in msg.users:
            events.emit("add-privileged-user", user)

        log.add(_("%i privileged users"), (len(msg.users)))

    def _check_privileges(self, msg):
        """ Server code: 92 """

        mins = msg.seconds // 60
        hours = mins // 60
        days = hours // 24

        if msg.seconds == 0:
            log.add(_("You have no Soulseek privileges. While privileges are active, your downloads "
                      "will be queued ahead of those of non-privileged users."))
        else:
            log.add(_("%(days)i days, %(hours)i hours, %(minutes)i minutes, %(seconds)i seconds of "
                      "Soulseek privileges left"), {
                "days": days,
                "hours": hours % 24,
                "minutes": mins % 60,
                "seconds": msg.seconds % 60
            })

        self.privileges_left = msg.seconds

    @staticmethod
    def _change_password(msg):
        """ Server code: 142 """

        password = msg.password
        config.sections["server"]["passw"] = password
        config.write_configuration()

        log.add(_("Your password has been changed"), title=_("Password Changed"))


core = Core()
