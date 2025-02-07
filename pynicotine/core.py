# COPYRIGHT (C) 2020-2024 Nicotine+ Contributors
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

import os
import sys
import threading

import pynicotine
from pynicotine.config import config
from pynicotine.events import events
from pynicotine.logfacility import log


class Core:
    """Core handles initialization, quitting, as well as the various components
    used by the application.
    """

    __slots__ = ("shares", "users", "network_filter", "statistics", "search", "downloads",
                 "uploads", "interests", "userbrowse", "userinfo", "buddies", "privatechat",
                 "chatrooms", "pluginhandler", "now_playing", "portmapper", "notifications",
                 "update_checker", "_network_thread", "cli_interface_address",
                 "cli_listen_port", "enabled_components")

    def __init__(self):

        self.shares = None
        self.users = None
        self.network_filter = None
        self.statistics = None
        self.search = None
        self.downloads = None
        self.uploads = None
        self.interests = None
        self.userbrowse = None
        self.userinfo = None
        self.buddies = None
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

    def init_components(self, enabled_components=None, isolated_mode=False):

        # Enable all components by default
        if enabled_components is None:
            enabled_components = {
                "error_handler", "signal_handler", "cli", "portmapper", "network_thread", "shares", "users",
                "notifications", "network_filter", "now_playing", "statistics", "update_checker",
                "search", "downloads", "uploads", "interests", "userbrowse", "userinfo", "buddies",
                "chatrooms", "privatechat", "pluginhandler"
            }

        self.enabled_components = enabled_components

        if "error_handler" in enabled_components:
            self._init_error_handler()

        if "signal_handler" in enabled_components:
            self._init_signal_handler()

        if "cli" in enabled_components:
            from pynicotine.cli import cli
            cli.enable_logging()

        config.load_config(isolated_mode)
        events.enable()

        for event_name, callback in (
            ("quit", self._quit),
            ("server-reconnect", self._server_reconnect)
        ):
            events.connect(event_name, callback)

        script_folder_path = os.path.dirname(__file__)

        log.add(_("Loading %(program)s %(version)s"), {
            "program": "Python",
            "version": sys.version.split()[0]
        })
        log.add_debug("Using %s executable: %s", ("Python", sys.executable))
        log.add(_("Loading %(program)s %(version)s"), {
            "program": pynicotine.__application_name__,
            "version": pynicotine.__version__
        })
        log.add_debug("Using %s executable: %s", (pynicotine.__application_name__, script_folder_path))

        if "portmapper" in enabled_components:
            from pynicotine.portmapper import PortMapper
            self.portmapper = PortMapper()

        if "network_thread" in enabled_components:
            from pynicotine.slskproto import NetworkThread
            self._network_thread = NetworkThread()
        else:
            events.connect("schedule-quit", self._schedule_quit)

        if "shares" in enabled_components:
            # Initialized before "users" component in order to send share stats to server
            # before watching our username, otherwise we get outdated stats back.
            from pynicotine.shares import Shares
            self.shares = Shares()

        if "users" in enabled_components:
            from pynicotine.users import Users
            self.users = Users()

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

        if "buddies" in enabled_components:
            from pynicotine.buddies import Buddies
            self.buddies = Buddies()

        if "chatrooms" in enabled_components:
            from pynicotine.chatrooms import ChatRooms
            self.chatrooms = ChatRooms()

        if "privatechat" in enabled_components:
            from pynicotine.privatechat import PrivateChat
            self.privatechat = PrivateChat()

        if "pluginhandler" in enabled_components:
            from pynicotine.pluginsystem import PluginHandler
            self.pluginhandler = PluginHandler(isolated_mode)

    def _init_signal_handler(self):
        """Handle Ctrl+C and "kill" exit gracefully."""

        import signal

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

    def start(self):

        if "cli" in self.enabled_components:
            from pynicotine.cli import cli
            cli.enable_prompt()

        events.emit("start")

    def setup(self):
        events.emit("setup")

    def confirm_quit(self):
        events.emit("confirm-quit")

    def quit(self, signal_type=None, _frame=None):

        import signal
        log.add(_("Quitting %(program)s %(version)s, %(status)s…"), {
            "program": pynicotine.__application_name__,
            "version": pynicotine.__version__,
            "status": _("terminating") if signal_type == signal.SIGTERM else _("application closing")
        })

        # Allow the networking thread to finish up before quitting
        events.emit("schedule-quit")

    def _schedule_quit(self):
        events.emit("quit")

    def _quit(self):

        config.write_configuration()

        log.add(_("Quit %(program)s %(version)s!"), {
            "program": pynicotine.__application_name__,
            "version": pynicotine.__version__
        })

    def connect(self):

        if config.need_config():
            log.add(_("You need to specify a username and password before connecting…"))
            self.setup()
            return

        from pynicotine.slskmessages import ServerConnect

        events.emit("enable-message-queue")

        self.send_message_to_network_thread(ServerConnect(
            addr=config.sections["server"]["server"],
            login=(config.sections["server"]["login"], config.sections["server"]["passw"]),
            interface_name=config.sections["server"]["interface"],
            interface_address=self.cli_interface_address,
            listen_port=self.cli_listen_port or config.sections["server"]["portrange"][0],
            portmapper=self.portmapper
        ))

    def disconnect(self):
        from pynicotine.slskmessages import ServerDisconnect
        self.send_message_to_network_thread(ServerDisconnect())

    def reconnect(self):
        from pynicotine.slskmessages import ServerReconnect
        self.send_message_to_network_thread(ServerReconnect())

    def _server_reconnect(self, _msg):
        self.connect()

    def send_message_to_network_thread(self, message):
        """Sends message to the networking thread to inform about something."""
        events.emit("queue-network-message", message)

    def send_message_to_server(self, message):
        """Sends message to the server."""
        events.emit("queue-network-message", message)

    def send_message_to_peer(self, username, message):
        """Sends message to a peer."""

        message.username = username
        events.emit("queue-network-message", message)


class UpdateChecker:
    __slots__ = ("_thread",)

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

        import json
        from urllib.request import urlopen

        with urlopen("https://pypi.org/pypi/nicotine-plus/json", timeout=5) as response:
            response_body = response.read().decode("utf-8", "replace")

        data = json.loads(response_body)
        h_latest_version = data["info"]["version"]
        latest_version = cls.create_integer_version(h_latest_version)

        return h_latest_version, latest_version


core = Core()
