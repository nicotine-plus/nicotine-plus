# COPYRIGHT (C) 2020-2023 Nicotine+ Contributors
# COPYRIGHT (C) 2020-2023 Mathias <mail@mathias.is>
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

import json
import os
import signal
import sys
import threading

import pynicotine
from pynicotine import slskmessages
from pynicotine.cli import cli
from pynicotine.config import config
from pynicotine.events import events
from pynicotine.logfacility import log
from pynicotine.utils import UINT32_LIMIT


class Core:
    """Core contains handlers for various messages from (mainly) the networking
    thread.

    This class links the networking thread and user interface.
    """

    def __init__(self):

        self.network_filter = None
        self.statistics = None
        self.shares = None
        self.search = None
        self.downloads = None
        self.uploads = None
        self.interests = None
        self.userbrowse = None
        self.userinfo = None
        self.userlist = None
        self.privatechat = None
        self.chatrooms = None
        self.pluginhandler = None
        self.now_playing = None
        self.portmapper = None
        self.notifications = None
        self.update_checker = None
        self._network_thread = None

        self.cli_interface_address = None
        self.cli_listen_port = None

        self.enabled_components = set()
        self.user_status = slskmessages.UserStatus.OFFLINE
        self.login_username = None  # Only present while logged in
        self.public_ip_address = None
        self.public_port = None
        self.privileges_left = None

        self.user_addresses = {}
        self.user_countries = {}
        self.user_statuses = {}
        self.watched_users = {}
        self._ip_requested = {}

    def init_components(self, enabled_components=None):

        # Enable all components by default
        if enabled_components is None:
            enabled_components = {
                "error_handler", "signal_handler", "cli", "portmapper", "network_thread",
                "notifications", "network_filter", "now_playing", "statistics", "update_checker",
                "shares", "search", "downloads", "uploads", "interests", "userbrowse", "userinfo", "userlist",
                "chatrooms", "privatechat", "pluginhandler"
            }

        self.enabled_components = enabled_components

        if "error_handler" in enabled_components:
            self._init_error_handler()

        if "signal_handler" in enabled_components:
            self._init_signal_handler()

        if "cli" in enabled_components:
            cli.enable_logging()

        config.load_config()
        events.enable()

        for event_name, callback in (
            ("admin-message", self._admin_message),
            ("change-password", self._change_password),
            ("check-privileges", self._check_privileges),
            ("peer-address", self._get_peer_address),
            ("privileged-users", self._privileged_users),
            ("quit", self._quit),
            ("server-disconnect", self._server_disconnect),
            ("server-login", self._server_login),
            ("server-timeout", self._server_timeout),
            ("thread-callback", self._thread_callback),
            ("user-stats", self._user_stats),
            ("user-status", self._user_status),
            ("watch-user", self._watch_user)
        ):
            events.connect(event_name, callback)

        script_folder_path = os.path.dirname(__file__)

        log.add(_("Loading %(program)s %(version)s"), {"program": "Python", "version": sys.version.split()[0]})
        log.add_debug("Using %(program)s executable: %(exe)s", {"program": "Python", "exe": str(sys.executable)})
        log.add_debug("Using %(program)s executable: %(exe)s", {
            "program": pynicotine.__application_name__, "exe": script_folder_path})
        log.add(_("Loading %(program)s %(version)s"), {
            "program": pynicotine.__application_name__, "version": pynicotine.__version__})

        if "portmapper" in enabled_components:
            from pynicotine.portmapper import PortMapper
            self.portmapper = PortMapper()

        if "network_thread" in enabled_components:
            from pynicotine.slskproto import NetworkThread
            self._network_thread = NetworkThread()
        else:
            events.connect("schedule-quit", self._schedule_quit)

        if "notifications" in enabled_components:
            from pynicotine.notifications import Notifications
            self.notifications = Notifications()

        if "network_filter" in enabled_components:
            from pynicotine.networkfilter import NetworkFilter
            self.network_filter = NetworkFilter()

        if "now_playing" in enabled_components:
            from pynicotine.nowplaying import NowPlaying
            self.now_playing = NowPlaying()

        if "statistics" in enabled_components:
            from pynicotine.transfers import Statistics
            self.statistics = Statistics()

        if "update_checker" in enabled_components:
            self.update_checker = UpdateChecker()

        if "shares" in enabled_components:
            from pynicotine.shares import Shares
            self.shares = Shares()

        if "search" in enabled_components:
            from pynicotine.search import Search
            self.search = Search()

        if "downloads" in enabled_components:
            from pynicotine.downloads import Downloads
            self.downloads = Downloads()

        if "uploads" in enabled_components:
            from pynicotine.uploads import Uploads
            self.uploads = Uploads()

        if "interests" in enabled_components:
            from pynicotine.interests import Interests
            self.interests = Interests()

        if "userbrowse" in enabled_components:
            from pynicotine.userbrowse import UserBrowse
            self.userbrowse = UserBrowse()

        if "userinfo" in enabled_components:
            from pynicotine.userinfo import UserInfo
            self.userinfo = UserInfo()

        if "userlist" in enabled_components:
            from pynicotine.userlist import UserList
            self.userlist = UserList()

        if "chatrooms" in enabled_components:
            from pynicotine.chatrooms import ChatRooms
            self.chatrooms = ChatRooms()

        if "privatechat" in enabled_components:
            from pynicotine.privatechat import PrivateChat
            self.privatechat = PrivateChat()

        if "pluginhandler" in enabled_components:
            from pynicotine.pluginsystem import PluginHandler
            self.pluginhandler = PluginHandler()

    def _init_signal_handler(self):
        """Handle Ctrl+C and "kill" exit gracefully."""

        for signal_type in (signal.SIGINT, signal.SIGTERM):
            signal.signal(signal_type, self.quit)

    def _init_error_handler(self):

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

    # Actions #

    def start(self):

        if "cli" in self.enabled_components:
            cli.enable_prompt()

        events.emit("start")

    def setup(self):
        events.emit("setup")

    def confirm_quit(self, only_on_active_uploads=False):
        events.emit("confirm-quit", only_on_active_uploads)

    def quit(self, signal_type=None, _frame=None, should_finish_uploads=False):

        if not should_finish_uploads:
            log.add(_("Quitting %(program)s %(version)s, %(status)s…"), {
                "program": pynicotine.__application_name__,
                "version": pynicotine.__version__,
                "status": _("terminating") if signal_type == signal.SIGTERM else _("application closing")
            })

        # Allow the networking thread to finish up before quitting
        events.emit("schedule-quit", should_finish_uploads)

    def connect(self):

        if self.user_status != slskmessages.UserStatus.OFFLINE:
            return

        if config.need_config():
            log.add(_("You need to specify a username and password before connecting…"))
            self.setup()
            return

        events.emit("enable-message-queue")

        self.send_message_to_network_thread(slskmessages.ServerConnect(
            addr=config.sections["server"]["server"],
            login=(config.sections["server"]["login"], config.sections["server"]["passw"]),
            interface_name=config.sections["server"]["interface"],
            interface_address=self.cli_interface_address,
            listen_port=self.cli_listen_port or config.sections["server"]["portrange"][0],
            portmapper=self.portmapper
        ))

    def disconnect(self):
        if self.user_status != slskmessages.UserStatus.OFFLINE:
            self.send_message_to_network_thread(slskmessages.ServerDisconnect())

    def send_message_to_network_thread(self, message):
        """Sends message to the networking thread to inform about something."""
        events.emit("queue-network-message", message)

    def send_message_to_server(self, message):
        """Sends message to the server."""
        events.emit("queue-network-message", message)

    def send_message_to_peer(self, username, message):
        """Sends message to a peer."""
        events.emit("queue-network-message", slskmessages.SendNetworkMessage(username, message))

    def set_away_mode(self, is_away, save_state=False):

        if save_state:
            config.sections["server"]["away"] = is_away

        self.user_status = slskmessages.UserStatus.AWAY if is_away else slskmessages.UserStatus.ONLINE
        self.request_set_status(self.user_status)

        # Fake a user status message, since server doesn't send updates when we
        # disable away mode
        events.emit("user-status", slskmessages.GetUserStatus(core.login_username, self.user_status))

    def request_change_password(self, password):
        self.send_message_to_server(slskmessages.ChangePassword(password))

    def request_check_privileges(self):
        self.send_message_to_server(slskmessages.CheckPrivileges())

    def request_give_privileges(self, username, days):
        if UINT32_LIMIT >= days > 0:
            self.send_message_to_server(slskmessages.GivePrivileges(username, days))

    def request_ip_address(self, username, notify=False):

        if username in self._ip_requested:
            return

        self._ip_requested[username] = notify
        self.send_message_to_server(slskmessages.GetPeerAddress(username))

    def request_set_status(self, status):
        self.send_message_to_server(slskmessages.SetStatus(status))

    def request_user_stats(self, username):
        self.send_message_to_server(slskmessages.GetUserStats(username))

    def watch_user(self, username):
        """Tell the server we want to be notified of status/stat updates for a
        user."""

        if self.user_status == slskmessages.UserStatus.OFFLINE:
            return

        if username in self.watched_users:
            return

        self.send_message_to_server(slskmessages.WatchUser(username))
        self.send_message_to_server(slskmessages.GetUserStatus(username))  # Get privilege status

        self.watched_users[username] = {}

    # Message Callbacks #

    def _thread_callback(self, callback, *args, **kwargs):
        callback(*args, **kwargs)

    def _schedule_quit(self, _should_finish_uploads):
        events.emit("quit")

    def _quit(self):

        self._network_thread = None
        self.portmapper = None
        self.notifications = None
        self.network_filter = None
        self.now_playing = None
        self.statistics = None
        self.update_checker = None

        self.shares = None
        self.search = None
        self.downloads = None
        self.uploads = None
        self.interests = None
        self.userbrowse = None
        self.userinfo = None
        self.userlist = None
        self.chatrooms = None
        self.privatechat = None
        self.pluginhandler = None

        config.write_configuration()

        log.add(_("Quit %(program)s %(version)s!"), {
            "program": pynicotine.__application_name__,
            "version": pynicotine.__version__
        })

    def _server_timeout(self):
        if not config.need_config():
            self.connect()

    def _server_disconnect(self, manual_disconnect=False):

        self.user_status = slskmessages.UserStatus.OFFLINE

        # Clean up connections
        self.user_addresses.clear()
        self.user_countries.clear()
        self.user_statuses.clear()
        self.watched_users.clear()
        self._ip_requested.clear()

        if self.pluginhandler:
            self.pluginhandler.server_disconnect_notification(manual_disconnect)

        self.login_username = None
        self.public_ip_address = None
        self.public_port = None

    def _server_login(self, msg):
        """Server code 1."""

        if msg.success:
            self.user_status = slskmessages.UserStatus.ONLINE
            self.login_username = msg.username
            _local_ip_address, self.public_port = msg.local_address
            self.user_addresses[self.login_username] = msg.local_address

            self.set_away_mode(config.sections["server"]["away"])
            self.watch_user(msg.username)

            if msg.ip_address is not None:
                self.public_ip_address = msg.ip_address
                self.user_countries[msg.username] = self.network_filter.get_country_code(msg.ip_address)

            if msg.banner:
                log.add(msg.banner)

            self.send_message_to_server(slskmessages.PrivateRoomToggle(config.sections["server"]["private_chatrooms"]))
            self.pluginhandler.server_connect_notification()

        else:
            if msg.reason == slskmessages.LoginFailure.PASSWORD:
                events.emit("invalid-password")
                return

            log.add(_("Unable to connect to the server. Reason: %s"), msg.reason, title=_("Cannot Connect"))

    def _get_peer_address(self, msg):
        """Server code 3."""

        username = msg.user
        notify = self._ip_requested.pop(username, None)
        addr = (msg.ip_address, msg.port)
        user_offline = (addr == ("0.0.0.0", 0))

        # We already store a local IP address for our username
        if username != self.login_username and not user_offline:
            self.user_addresses[username] = addr

        self.user_countries[username] = country_code = self.network_filter.get_country_code(msg.ip_address)
        events.emit("user-country", username, country_code)

        if not notify:
            self.pluginhandler.user_resolve_notification(username, msg.ip_address, msg.port)
            return

        self.pluginhandler.user_resolve_notification(username, msg.ip_address, msg.port, country_code)

        if country_code:
            country_name = self.network_filter.COUNTRIES.get(country_code, _("Unknown"))
            country = f" ({country_code} / {country_name})"
        else:
            country = ""

        if msg.ip_address == "0.0.0.0":
            log.add(_("Cannot retrieve the IP of user %s, since this user is offline"), username)
            return

        log.add(_("IP address of user %(user)s: %(ip)s, port %(port)i%(country)s"), {
            "user": username,
            "ip": msg.ip_address,
            "port": msg.port,
            "country": country
        }, title=_("IP Address"))

    def _watch_user(self, msg):
        """Server code 5."""

        if msg.userexists:
            if msg.status is not None:  # Soulfind server support, sends userexists but no additional data
                events.emit("user-stats", msg)
            return

        # User does not exist, server will not keep us informed if the user is created later
        self.watched_users.pop(msg.user, None)

    def _user_status(self, msg):
        """Server code 7."""

        username = msg.user
        status = msg.status

        if status not in {slskmessages.UserStatus.OFFLINE, slskmessages.UserStatus.ONLINE,
                          slskmessages.UserStatus.AWAY}:
            log.add_debug("Received an unknown status %(status)s for user %(user)s from the server", {
                "status": status,
                "user": username
            })

        # Ignore invalid status updates for our own username in case we've already
        # changed our status again by the time they arrive from the server
        if username == core.login_username and status != self.user_status:
            msg.user = None
            return

        # Store statuses for watched users, update statuses of room members
        if username in self.watched_users or username in self.user_statuses:
            self.user_statuses[username] = status

        # User went offline, reset stored IP address and country
        if status == slskmessages.UserStatus.OFFLINE:
            self.user_addresses.pop(username, None)
            self.user_countries.pop(username, None)

        self.pluginhandler.user_status_notification(username, status, msg.privileged)

    def _user_stats(self, msg):
        """Server code 36."""

        username = msg.user
        upload_speed = msg.avgspeed
        files = msg.files
        folders = msg.dirs

        if username in self.watched_users:
            self.watched_users[username].update({
                "upload_speed": upload_speed,
                "files": files,
                "folders": folders
            })

        self.pluginhandler.user_stats_notification(msg.user, stats={
            "avgspeed": msg.avgspeed,
            "uploadnum": upload_speed,
            "files": files,
            "dirs": folders,
        })

    @staticmethod
    def _admin_message(msg):
        """Server code 66."""

        log.add(msg.msg, title=_("Soulseek Announcement"))

    def _privileged_users(self, msg):
        """Server code 69."""

        for username in msg.users:
            events.emit("add-privileged-user", username)

        log.add(_("%i privileged users"), (len(msg.users)))

    def _check_privileges(self, msg):
        """Server code 92."""

        mins = msg.seconds // 60
        hours = mins // 60
        days = hours // 24

        if msg.seconds <= 0:
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
        """Server code 142."""

        password = msg.password
        config.sections["server"]["passw"] = password
        config.write_configuration()

        log.add(_("Your password has been changed"), title=_("Password Changed"))


class UpdateChecker:

    def __init__(self):
        self._thread = None

    def check(self):

        if self._thread and self._thread.is_alive():
            return

        self._thread = threading.Thread(target=self._check, name="UpdateChecker", daemon=True)
        self._thread.start()

    def _check(self):

        try:
            error_message = None
            h_latest_version, latest_version = self.retrieve_latest_version()
            current_version = self.create_integer_version(pynicotine.__version__)
            is_outdated = (current_version < latest_version)

        except Exception as error:
            error_message = str(error)
            h_latest_version = None
            is_outdated = False

        events.emit_main_thread("check-latest-version", h_latest_version, is_outdated, error_message)

    @staticmethod
    def create_integer_version(version):

        major, minor, patch = version.split(".")[:3]
        stable = 1

        if "dev" in version or "rc" in version:
            # Example: 2.0.1.dev1
            # A dev version will be one less than a stable version
            stable = 0

        return (int(major) << 24) + (int(minor) << 16) + (int(patch.split("rc", 1)[0]) << 8) + stable

    @classmethod
    def retrieve_latest_version(cls):

        from urllib.request import urlopen
        with urlopen("https://pypi.org/pypi/nicotine-plus/json", timeout=5) as response:
            response_body = response.read().decode("utf-8")

        data = json.loads(response_body)
        h_latest_version = data["info"]["version"]
        latest_version = cls.create_integer_version(h_latest_version)

        return h_latest_version, latest_version


core = Core()
