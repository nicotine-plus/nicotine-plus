# SPDX-FileCopyrightText: 2020-2025 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import signal
import sys
import threading
from threading import Thread
from types import FrameType
from typing import IO
from typing import TYPE_CHECKING

import pynicotine
from pynicotine.config import config
from pynicotine.events import events
from pynicotine.logfacility import log
from pynicotine.notifications import Notifications
from pynicotine.nowplaying import NowPlaying
from pynicotine.portchecker import PortChecker
from pynicotine.portmapper import PortMapper
from pynicotine.slskmessages import InternalMessage
from pynicotine.slskmessages import PeerMessage
from pynicotine.slskmessages import ServerConnect
from pynicotine.slskmessages import ServerDisconnect
from pynicotine.slskmessages import ServerMessage
from pynicotine.slskmessages import ServerReconnect
from pynicotine.slskproto import NetworkThread

if TYPE_CHECKING:
    from pynicotine.buddies import Buddies
    from pynicotine.chatrooms import ChatRooms
    from pynicotine.downloads import Downloads
    from pynicotine.interests import Interests
    from pynicotine.networkfilter import NetworkFilter
    from pynicotine.pluginsystem import PluginHandler
    from pynicotine.privatechat import PrivateChat
    from pynicotine.search import Search
    from pynicotine.shares import Shares
    from pynicotine.transfers import Statistics
    from pynicotine.uploads import Uploads
    from pynicotine.userbrowse import UserBrowse
    from pynicotine.userinfo import UserInfo
    from pynicotine.users import Users

__all__ = ["Core", "UpdateChecker", "core"]


class Core:
    """Core handles initialization, quitting, as well as the various components
    used by the application.
    """

    __slots__ = ("shares", "users", "network_filter", "statistics", "search", "downloads",
                 "uploads", "interests", "userbrowse", "userinfo", "buddies", "privatechat",
                 "chatrooms", "pluginhandler", "now_playing", "portmapper", "notifications",
                 "port_checker", "update_checker", "_network_thread", "cli_interface_address",
                 "cli_listen_port", "cli_rescanning", "enabled_components")

    def __init__(self):
        self.shares: "Shares | None" = None
        self.users: "Users | None" = None
        self.network_filter: "NetworkFilter | None" = None
        self.statistics: "Statistics | None" = None
        self.search: "Search | None" = None
        self.downloads: "Downloads | None" = None
        self.uploads: "Uploads | None" = None
        self.interests: "Interests | None" = None
        self.userbrowse: "UserBrowse | None" = None
        self.userinfo: "UserInfo | None" = None
        self.buddies: "Buddies | None" = None
        self.privatechat: "PrivateChat | None" = None
        self.chatrooms: "ChatRooms | None" = None
        self.pluginhandler: "PluginHandler | None" = None
        self.now_playing: NowPlaying | None = None
        self.portmapper: PortMapper | None = None
        self.notifications: Notifications | None = None
        self.port_checker: PortChecker | None = None
        self.update_checker: UpdateChecker | None = None
        self._network_thread: NetworkThread | None = None

        self.cli_interface_address: str | None = None
        self.cli_listen_port: int | None = None
        self.cli_rescanning: bool | None = None

        self.enabled_components: set[str] = set()

    def init_components(
        self, enabled_components: set[str] | None = None, isolated_mode: bool = False
    ):
        # Enable all components by default
        if enabled_components is None:
            enabled_components = {
                "error_handler",
                "signal_handler",
                "cli",
                "portmapper",
                "network_thread",
                "shares",
                "users",
                "notifications",
                "network_filter",
                "now_playing",
                "statistics",
                "port_checker",
                "update_checker",
                "search",
                "downloads",
                "uploads",
                "interests",
                "userbrowse",
                "userinfo",
                "buddies",
                "chatrooms",
                "privatechat",
                "pluginhandler",
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
            ("server-reconnect", self._server_reconnect),
        ):
            events.connect(event_name, callback)

        if not isolated_mode and "portmapper" in enabled_components:
            self.portmapper = PortMapper()

        if "network_thread" in enabled_components:
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
            self.notifications = Notifications()

        if "network_filter" in enabled_components:
            from pynicotine.networkfilter import NetworkFilter

            self.network_filter = NetworkFilter()

        if "now_playing" in enabled_components:
            self.now_playing = NowPlaying()

        if "statistics" in enabled_components:
            from pynicotine.transfers import Statistics

            self.statistics = Statistics()

        if "port_checker" in enabled_components:
            self.port_checker = PortChecker()

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

        signals = [signal.SIGINT, signal.SIGTERM]

        if hasattr(signal, "SIGHUP"):
            signals.append(signal.SIGHUP)  # Terminal was closed

        for signal_type in signals:
            signal.signal(signal_type, self.quit)

    def _init_error_handler(self):
        def thread_excepthook(args):
            sys.excepthook(*args[:3])

        threading.excepthook = thread_excepthook

    def start(self):
        script_folder_path = os.path.dirname(__file__)

        log.add(
            _("Starting %(program)s %(version)s"),
            {
                "program": pynicotine.__application_name__,
                "version": pynicotine.__version__,
            },
        )
        log.add(
            _("Loaded %(program)s %(version)s"),
            {"program": "Python", "version": sys.version.split()[0]},
        )
        log.add_debug(
            "Using %s executable: %s",
            (pynicotine.__application_name__, script_folder_path),
        )
        log.add_debug("Using %s executable: %s", ("Python", sys.executable))

        if "cli" in self.enabled_components:
            from pynicotine.cli import cli

            cli.enable_prompt()

        events.emit("start")

    def setup(self):
        events.emit("setup")

    def confirm_quit(self):
        events.emit("confirm-quit")

    def quit(self, signal_type: int | None = None, _frame: FrameType | None = None):
        log.add(
            _("Quitting %(program)s %(version)s, %(status)s…"),
            {
                "program": pynicotine.__application_name__,
                "version": pynicotine.__version__,
                "status": _("terminating")
                if signal_type == signal.SIGTERM
                else _("application closing"),
            },
        )

        # Allow the networking thread to finish up before quitting
        events.emit("schedule-quit")

    def _schedule_quit(self):
        events.emit("quit")

    def _quit(self):
        config.write_configuration()

        log.add(
            _("Quit %(program)s %(version)s!"),
            {
                "program": pynicotine.__application_name__,
                "version": pynicotine.__version__,
            },
        )

    def connect(self):
        if config.need_config():
            log.add(_("You need to specify a username and password before connecting…"))
            self.setup()
            return

        events.emit("enable-message-queue")

        self.send_message_to_network_thread(
            ServerConnect(
                addr=config.sections["server"]["server"],
                login=(
                    config.sections["server"]["login"],
                    config.sections["server"]["passw"],
                ),
                interface_name=config.sections["server"]["interface"],
                interface_address=self.cli_interface_address,
                listen_port=self.cli_listen_port
                or config.sections["server"]["portrange"][0],
                portmapper=self.portmapper,
            )
        )

    def disconnect(self):
        self.send_message_to_network_thread(ServerDisconnect())

    def reconnect(self):
        self.send_message_to_network_thread(ServerReconnect())

    def _server_reconnect(self, _msg: ServerReconnect):
        self.connect()

    def send_message_to_network_thread(self, message: InternalMessage):
        """Sends message to the networking thread to inform about something."""
        events.emit("queue-network-message", message)

    def send_message_to_server(self, message: ServerMessage):
        """Sends message to the server."""
        events.emit("queue-network-message", message)

    def send_message_to_peer(self, username: str, message: PeerMessage):
        """Sends message to a peer."""

        message.username = username
        events.emit("queue-network-message", message)


class UpdateChecker:
    __slots__ = ("_thread",)

    def __init__(self):
        self._thread: Thread | None = None

    def check(self):
        if self._thread is not None and self._thread.is_alive():
            return

        self._thread = Thread(target=self._check, name="UpdateChecker")
        self._thread.start()

    def _check(self):
        try:
            error_message = None
            h_latest_version, latest_version = self.retrieve_latest_version()
            current_version = self.create_integer_version(pynicotine.__version__)
            is_outdated = current_version < latest_version

        except Exception as error:
            error_message = str(error)
            h_latest_version = None
            is_outdated = False

        events.emit_main_thread(
            "check-latest-version", h_latest_version, is_outdated, error_message
        )

    @staticmethod
    def create_integer_version(version: str):
        major, minor, patch = version.split(".")[:3]
        stable = 1

        if "dev" in version or "rc" in version:
            # Example: 2.0.1.dev1
            # A dev version will be one less than a stable version
            stable = 0

        return (
            (int(major) << 24)
            + (int(minor) << 16)
            + (int(patch.split("rc", 1)[0]) << 8)
            + stable
        )

    @classmethod
    def retrieve_latest_version(cls):
        import json
        from urllib.request import urlopen

        response: IO[bytes]
        with urlopen("https://pypi.org/pypi/nicotine-plus/json", timeout=5) as response:
            response_body = response.read().decode("utf-8", "replace")

        data = json.loads(response_body)
        h_latest_version: str = data["info"]["version"]
        latest_version = cls.create_integer_version(h_latest_version)

        return h_latest_version, latest_version


core = Core()
