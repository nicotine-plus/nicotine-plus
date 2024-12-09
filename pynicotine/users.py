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

import pynicotine
from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.logfacility import log
from pynicotine.slskmessages import ChangePassword
from pynicotine.slskmessages import CheckPrivileges
from pynicotine.slskmessages import GetPeerAddress
from pynicotine.slskmessages import GetUserStats
from pynicotine.slskmessages import GetUserStatus
from pynicotine.slskmessages import GivePrivileges
from pynicotine.slskmessages import LoginFailure
from pynicotine.slskmessages import SetStatus
from pynicotine.slskmessages import UnwatchUser
from pynicotine.slskmessages import UserStatus
from pynicotine.slskmessages import WatchUser
from pynicotine.utils import UINT32_LIMIT
from pynicotine.utils import open_uri


class WatchedUser:

    __slots__ = ("username", "upload_speed", "files", "folders", "contexts", "is_implicit")

    def __init__(self, username):

        self.username = username
        self.upload_speed = None
        self.files = None
        self.folders = None
        self.contexts = set()
        self.is_implicit = True


class Users:
    __slots__ = ("login_status", "login_username", "public_ip_address", "public_port",
                 "server_hostname", "server_port", "privileges_left", "_should_open_privileges_url",
                 "addresses", "countries", "statuses", "watched", "privileged", "_ip_requested",
                 "_pending_watch_removals")
    USERNAME_MAX_LENGTH = 30

    def __init__(self):

        self.login_status = UserStatus.OFFLINE
        self.login_username = None  # Only present while logged in
        self.public_ip_address = None
        self.public_port = None
        self.server_hostname = None
        self.server_port = None
        self.privileges_left = None
        self._should_open_privileges_url = False

        self.addresses = {}
        self.countries = {}
        self.statuses = {}
        self.watched = {}
        self.privileged = set()
        self._ip_requested = {}
        self._pending_watch_removals = set()

        for event_name, callback in (
            ("admin-message", self._admin_message),
            ("change-password", self._change_password),
            ("check-privileges", self._check_privileges),
            ("connect-to-peer", self._connect_to_peer),
            ("peer-address", self._get_peer_address),
            ("privileged-users", self._privileged_users),
            ("server-disconnect", self._server_disconnect),
            ("server-login", self._server_login),
            ("user-stats", self._user_stats),
            ("user-status", self._user_status),
            ("watch-user", self._watch_user)
        ):
            events.connect(event_name, callback)

    def set_away_mode(self, is_away, save_state=False):

        if save_state:
            config.sections["server"]["away"] = is_away

        self.login_status = UserStatus.AWAY if is_away else UserStatus.ONLINE
        self.request_set_status(self.login_status)

        # Fake a user status message, since server doesn't send updates when we
        # disable away mode
        events.emit("user-status", GetUserStatus(self.login_username, self.login_status))

    def open_privileges_url(self):

        default_server_hostname, _port = config.defaults["server"]["server"]
        default_server_domain = default_server_hostname.split(".", maxsplit=1)[-1]

        if not self.server_hostname or not self.server_hostname.endswith(f".{default_server_domain}"):
            # Only official server is supported for now
            return

        import urllib.parse

        login = urllib.parse.quote(self.login_username)
        open_uri(pynicotine.__privileges_url__ % login)

    def request_change_password(self, password):
        core.send_message_to_server(ChangePassword(password))

    def request_check_privileges(self, should_open_url=False):
        self._should_open_privileges_url = should_open_url
        core.send_message_to_server(CheckPrivileges())

    def request_give_privileges(self, username, days):
        if UINT32_LIMIT >= days > 0:
            core.send_message_to_server(GivePrivileges(username, days))

    def request_ip_address(self, username, notify=False):

        if username in self._ip_requested:
            return

        self._ip_requested[username] = notify
        core.send_message_to_server(GetPeerAddress(username))

    def request_set_status(self, status):
        core.send_message_to_server(SetStatus(status))

    def request_user_stats(self, username):
        core.send_message_to_server(GetUserStats(username))

    def watch_user(self, username, context=None, is_implicit=False):
        """Tells the server we want to be notified of status updates for a
        user.

        context is a string specifying where the user is being watched.
        The same context must be provided when calling unwatch_user(), when
        we no longer wish to receive updates for the user in said context.

        is_implicit is set when receiving status updates from the server
        without sending a message first. At present, this only happens for
        users in a joined chat room.
        """

        if self.login_status == UserStatus.OFFLINE:
            return

        watched_user = self.watched.get(username)

        if watched_user is None:
            self.watched[username] = watched_user = WatchedUser(username)

        if not context:
            log.add("Calling watch_user() without providing a 'context' argument is deprecated.")
            context = "unknown"

        if context in watched_user.contexts:
            return

        if not is_implicit and watched_user.is_implicit:
            core.send_message_to_server(WatchUser(username))
            core.send_message_to_server(GetUserStatus(username))  # Get privilege status
            watched_user.is_implicit = False

        watched_user.contexts.add(context)
        log.add_conn("Watching user %s in context '%s'. Active contexts: %s",
                     (username, context, watched_user.contexts))

    def unwatch_user(self, username, context):
        """Tells the server we no longer wish to receive status updates for a
        user.

        context must be the same as previously provided in watch_user().
        """

        watched_user = self.watched.get(username)

        if watched_user is None:
            return

        watched_user.contexts.discard(context)
        log.add_conn("Unwatching user %s in context '%s'. Remaining contexts: %s",
                     (username, context, watched_user.contexts))

        if watched_user.contexts:
            return

        if not watched_user.is_implicit:
            core.send_message_to_server(UnwatchUser(username))

        if username in self.addresses:
            del self.addresses[username]

        if username in self.countries:
            del self.countries[username]

        if username in self.statuses:
            del self.statuses[username]

        del self.watched[username]

    def _server_disconnect(self, msg):

        self.login_status = UserStatus.OFFLINE

        if core.pluginhandler:
            core.pluginhandler.server_disconnect_notification(msg.manual_disconnect)

        # Clean up connections
        self.addresses.clear()
        self.countries.clear()
        self.statuses.clear()
        self.watched.clear()
        self.privileged.clear()
        self._ip_requested.clear()
        self._pending_watch_removals.clear()

        self.login_username = None
        self.public_ip_address = None
        self.public_port = None
        self.server_hostname = None
        self.server_port = None
        self.privileges_left = None
        self._should_open_privileges_url = False

    def _server_login(self, msg):
        """Server code 1."""

        if msg.success:
            self.login_status = UserStatus.ONLINE
            self.login_username = username = msg.username
            _local_ip_address, self.public_port = msg.local_address
            self.server_hostname, self.server_port = msg.server_address
            self.addresses[username] = msg.local_address

            core.send_message_to_server(CheckPrivileges())
            self.set_away_mode(config.sections["server"]["away"])
            self.watch_user(username, context="login")

            if msg.ip_address is not None:
                self.public_ip_address = msg.ip_address
                self.countries[username] = country_code = core.network_filter.get_country_code(msg.ip_address)
                events.emit("user-country", username, country_code)

            if msg.banner:
                log.add(msg.banner)

            core.pluginhandler.server_connect_notification()
            return

        if msg.reason == LoginFailure.USERNAME:
            events.emit("invalid-username")
            return

        if msg.reason == LoginFailure.PASSWORD:
            events.emit("invalid-password")
            return

        log.add(_("Unable to connect to the server. Reason: %s"), msg.reason, title=_("Cannot Connect"))

    def _get_peer_address(self, msg):
        """Server code 3."""

        username = msg.user
        notify = self._ip_requested.pop(username, None)
        ip_address = msg.ip_address
        user_offline = (ip_address == "0.0.0.0")
        country_code = core.network_filter.get_country_code(ip_address)

        if user_offline:
            self.addresses.pop(username, None)
            self.countries.pop(username, None)

        elif username in self.watched:
            # Only cache IP address of watched users, otherwise we won't know if
            # a user reconnects and changes their IP address.
            # Don't update our own IP address, since we already store a local IP
            # address.

            if username != self.login_username:
                self.addresses[username] = (ip_address, msg.port)

            self.countries[username] = country_code
            events.emit("user-country", username, country_code)

        if not notify:
            core.pluginhandler.user_resolve_notification(username, ip_address, msg.port)
            return

        core.pluginhandler.user_resolve_notification(username, ip_address, msg.port, country_code)

        if user_offline:
            log.add(_("Cannot retrieve the IP of user %s, since this user is offline"), username)
            return

        if country_code:
            country_name = core.network_filter.COUNTRIES.get(country_code, _("Unknown"))
            country = f" ({country_code} / {country_name})"
        else:
            country = ""

        log.add(_("IP address of user %(user)s: %(ip)s, port %(port)i%(country)s"), {
            "user": username,
            "ip": msg.ip_address,
            "port": msg.port,
            "country": country
        }, title=_("IP Address"))

    def _watch_user(self, msg):
        """Server code 5."""

        if not msg.userexists:
            # User does not exist. The server will not keep us informed if the user is created
            # later, so we need to remove the user from our list.
            # Due to a bug, the server will in rare cases tell us a user doesn't exist, while
            # the user is actually online. Remove the user when we receive a UserStatus message
            # telling us the user is offline.
            self._pending_watch_removals.add(msg.user)
            return

        if msg.contains_stats:
            events.emit("user-stats", msg)

    def _user_status(self, msg):
        """Server code 7."""

        username = msg.user
        status = msg.status
        is_privileged = msg.privileged

        if is_privileged is not None:
            if is_privileged:
                self.privileged.add(username)

            elif username in self.privileged:
                self.privileged.remove(username)

        if status not in {UserStatus.OFFLINE, UserStatus.ONLINE, UserStatus.AWAY}:
            log.add_debug("Received an unknown status %s for user %s from the server",
                          (status, username))

        # Ignore invalid status updates for our own username in case we've already
        # changed our status again by the time they arrive from the server
        if username == self.login_username and status != self.login_status:
            msg.user = None
            return

        is_watched = (username in self.watched)

        # User went offline, reset stored IP address and country
        if status == UserStatus.OFFLINE:
            self.addresses.pop(username, None)
            self.countries.pop(username, None)

            if username in self._pending_watch_removals:
                # User does not exist, remove it from list
                log.add_conn("Unwatching non-existent user %s", username)
                self.watched.pop(username, None)

        elif is_watched:
            user_status = self.statuses.get(username)

            # Online user seen for the first time, request IP address and country
            if user_status is None:
                self.request_ip_address(username)

            # Previously watched user logged in again. Server will not send user stats, so request them.
            elif user_status == UserStatus.OFFLINE:
                self.request_user_stats(username)
                self.request_ip_address(username)

        if is_watched:
            self.statuses[username] = status

        self._pending_watch_removals.discard(username)
        core.pluginhandler.user_status_notification(username, status, msg.privileged)

    def _connect_to_peer(self, msg):
        """Server code 18."""

        username = msg.user
        is_privileged = msg.privileged

        if is_privileged is None:
            return

        if is_privileged:
            self.privileged.add(username)

        elif username in self.privileged:
            self.privileged.remove(username)

    def _user_stats(self, msg):
        """Server code 36."""

        username = msg.user
        upload_speed = msg.avgspeed
        files = msg.files
        folders = msg.dirs

        stats = self.watched.get(username)

        if stats is not None:
            stats.upload_speed = upload_speed
            stats.files = files
            stats.folders = folders

        core.pluginhandler.user_stats_notification(msg.user, stats={
            "avgspeed": upload_speed,
            "files": files,
            "dirs": folders,
            "shared_size": None,
            "source": "server"
        })

    @staticmethod
    def _admin_message(msg):
        """Server code 66."""

        log.add(msg.msg, title=_("Soulseek Announcement"))

    def _privileged_users(self, msg):
        """Server code 69."""

        for username in msg.users:
            self.privileged.add(username)

    def _check_privileges(self, msg):
        """Server code 92."""

        mins = msg.seconds // 60
        hours = mins // 60
        days = hours // 24

        if msg.seconds <= 0:
            log.add(_("You have no Soulseek privileges. While privileges are active, your downloads "
                      "will be queued ahead of those of non-privileged users."))

            if self._should_open_privileges_url:
                self.open_privileges_url()
        else:
            log.add(_("%(days)i days, %(hours)i hours, %(minutes)i minutes, %(seconds)i seconds of "
                      "Soulseek privileges left"), {
                "days": days,
                "hours": hours % 24,
                "minutes": mins % 60,
                "seconds": msg.seconds % 60
            })

        self.privileges_left = msg.seconds
        self._should_open_privileges_url = False

    @staticmethod
    def _change_password(msg):
        """Server code 142."""

        config.sections["server"]["passw"] = msg.password
        config.write_configuration()

        log.add(_("Your password has been changed"), title=_("Password Changed"))
