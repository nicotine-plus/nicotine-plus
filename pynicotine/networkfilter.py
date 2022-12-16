# COPYRIGHT (C) 2020-2022 Nicotine+ Contributors
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

from pynicotine import slskmessages
from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events


class NetworkFilter:
    """ Functions related to banning and ignoring users """

    def __init__(self):
        self.ip_ban_requested = {}
        self.ip_ignore_requested = {}

        for event_name, callback in (
            ("peer-address", self._get_peer_address),
            ("server-disconnect", self._server_disconnect)
        ):
            events.connect(event_name, callback)

    def _server_disconnect(self, _msg):
        self.ip_ban_requested.clear()
        self.ip_ignore_requested.clear()

    """ General """

    def _request_ip(self, user, action, list_type):
        """ Ask for the IP address of a user. Once a GetPeerAddress response arrives,
        either ban_unban_user_ip_callback or ignore_unignore_user_ip_callback
        is called. """

        if user in core.user_addresses:
            return False

        if list_type == "ban":
            request_list = self.ip_ban_requested
        else:
            request_list = self.ip_ignore_requested

        if user not in request_list:
            request_list[user] = action

        core.queue.append(slskmessages.GetPeerAddress(user))
        return True

    def _add_user_ip_to_list(self, user, list_type):
        """ Add the current IP of a user to a list. """

        if list_type == "ban":
            ip_list = config.sections["server"]["ipblocklist"]
        else:
            ip_list = config.sections["server"]["ipignorelist"]

        if self._request_ip(user, "add", list_type):
            return None

        ip_address, _port = core.user_addresses[user]

        if ip_address not in ip_list or ip_list[ip_address] != user:
            ip_list[ip_address] = user
            config.write_configuration()

        return ip_address

    def _remove_user_ip_from_list(self, user, list_type):
        """ Attempt to remove the previously saved IP address of a user from a list. """

        if list_type == "ban":
            cached_ip = self.get_cached_banned_user_ip(user)
            ip_list = config.sections["server"]["ipblocklist"]
        else:
            cached_ip = self.get_cached_ignored_user_ip(user)
            ip_list = config.sections["server"]["ipignorelist"]

        if cached_ip is not None:
            del ip_list[cached_ip]
            config.write_configuration()
            return

        if self._request_ip(user, "remove", list_type):
            return

        ip_address, _port = core.user_addresses[user]

        if ip_address in ip_list:
            del ip_list[ip_address]
            config.write_configuration()

    def _get_cached_user_ip(self, user, list_type):
        """ Retrieve the IP address of a user previously saved in a list. """

        if list_type == "ban":
            ip_list = config.sections["server"]["ipblocklist"]
        else:
            ip_list = config.sections["server"]["ipignorelist"]

        for ip_address, username in ip_list.items():
            if user == username:
                return ip_address

        return None

    def _is_ip_in_list(self, address, list_type):
        """ Check if an IP address exists in a list, disregarding the username
        the address is paired with. """

        if address is None:
            return True

        if list_type == "ban":
            ip_list = config.sections["server"]["ipblocklist"]
        else:
            ip_list = config.sections["server"]["ipignorelist"]

        s_address = address.split(".")

        for ip_address in ip_list:

            # No Wildcard in IP
            if "*" not in ip_address:
                if address == ip_address:
                    return True
                continue

            # Wildcard in IP
            parts = ip_address.split(".")
            seg = 0

            for part in parts:
                # Stop if there's no wildcard or matching string number
                if part not in (s_address[seg], "*"):
                    break

                seg += 1

                # Last time around
                if seg == 4:
                    # Wildcard ban
                    return True

        # Not banned
        return False

    def check_user(self, user, ip_address):
        """ Check if this user is banned, geoip-blocked, and which shares
        it is allowed to access based on transfer and shares settings. """

        if self.is_user_banned(user) or (ip_address is not None and self.is_ip_banned(ip_address)):
            if config.sections["transfers"]["usecustomban"]:
                ban_message = config.sections["transfers"]["customban"]
                return 0, f"Banned ({ban_message})"

            return 0, "Banned"

        user_data = core.userlist.buddies.get(user)

        if user_data:
            if config.sections["transfers"]["buddysharestrustedonly"] and not user_data.is_trusted:
                # Only trusted buddies allowed, and user isn't trusted
                return 1, ""

            # For sending buddy-only shares
            return 2, ""

        if ip_address is None or not config.sections["transfers"]["geoblock"]:
            return 1, ""

        country_code = core.geoip.get_country_code(ip_address)

        # Please note that all country codes are stored in the same string at the first index
        # of an array, separated by commas (no idea why this decision was made...)

        if country_code and config.sections["transfers"]["geoblockcc"][0].find(country_code) >= 0:
            if config.sections["transfers"]["usecustomgeoblock"]:
                ban_message = config.sections["transfers"]["customgeoblock"]
                return 0, f"Banned ({ban_message})"

            return 0, "Banned"

        return 1, ""

    def close_banned_ip_connections(self):
        """ Close all connections whose IP address exists in the ban list """

        for ip_address in config.sections["server"]["ipblocklist"]:
            core.queue.append(slskmessages.CloseConnectionIP(ip_address))

    def update_saved_user_ip_filters(self, user):
        """ When we know a user's IP address has changed, we call this function to
        update the IP saved in lists. """

        user_address = core.user_addresses.get(user)

        if not user_address:
            # User is offline
            return

        new_ip, _new_port = user_address
        cached_banned_ip = self.get_cached_banned_user_ip(user)

        if cached_banned_ip is not None and cached_banned_ip != new_ip:
            self.unban_user_ip(user)
            self.ban_user_ip(user)

        cached_ignored_ip = self.get_cached_ignored_user_ip(user)

        if cached_ignored_ip is not None and cached_ignored_ip != new_ip:
            self.unignore_user_ip(user)
            self.ignore_user_ip(user)

    def _get_peer_address(self, msg):
        """ Server code: 3 """

        user = msg.user

        # If the IP address changed, make sure our IP ban/ignore list reflects this
        self.update_saved_user_ip_filters(user)

        self.ban_unban_user_ip_callback(user)
        self.ignore_unignore_user_ip_callback(user)

    """ Banning """

    def ban_user(self, user):

        if self.is_user_banned(user):
            return

        config.sections["server"]["banlist"].append(user)
        config.write_configuration()

        core.transfers.ban_users({user})
        events.emit("ban-user", user)

    def unban_user(self, user):

        if not self.is_user_banned(user):
            return

        config.sections["server"]["banlist"].remove(user)
        config.write_configuration()

        events.emit("unban-user", user)

    def ban_user_ip(self, user):
        ip_address = self._add_user_ip_to_list(user, "ban")

        if ip_address:
            core.queue.append(slskmessages.CloseConnectionIP(ip_address))

    def unban_user_ip(self, user):
        self._remove_user_ip_from_list(user, "ban")

    def ban_unban_user_ip_callback(self, user):

        request = self.ip_ban_requested.pop(user, None)

        if request is None:
            return False

        if user not in core.user_addresses:
            # User is offline
            return False

        if request == "remove":
            self.unban_user_ip(user)
        else:
            self.ban_user_ip(user)

        return True

    def get_cached_banned_user_ip(self, user):
        return self._get_cached_user_ip(user, "ban")

    def is_user_banned(self, user):
        return user in config.sections["server"]["banlist"]

    def is_ip_banned(self, address):
        return self._is_ip_in_list(address, "ban")

    """ Ignoring """

    def ignore_user(self, user):

        if self.is_user_ignored(user):
            return

        config.sections["server"]["ignorelist"].append(user)
        config.write_configuration()

        events.emit("ignore-user", user)

    def unignore_user(self, user):

        if not self.is_user_ignored(user):
            return

        config.sections["server"]["ignorelist"].remove(user)
        config.write_configuration()

        events.emit("unignore-user", user)

    def ignore_ip(self, ip_address):

        if not ip_address or ip_address.count(".") != 3:
            return

        ip_ignore_list = config.sections["server"]["ipignorelist"]

        if ip_address not in ip_ignore_list:
            ip_ignore_list[ip_address] = ""
            config.write_configuration()

    def ignore_user_ip(self, user):
        self._add_user_ip_to_list(user, "ignore")

    def unignore_user_ip(self, user):
        self._remove_user_ip_from_list(user, "ignore")

    def ignore_unignore_user_ip_callback(self, user):

        request = self.ip_ignore_requested.pop(user, None)

        if request is None:
            return False

        if user not in core.user_addresses:
            # User is offline
            return False

        if request == "remove":
            self.unignore_user_ip(user)
        else:
            self.ignore_user_ip(user)

        return True

    def get_cached_ignored_user_ip(self, user):
        return self._get_cached_user_ip(user, "ignore")

    def is_user_ignored(self, user):
        return user in config.sections["server"]["ignorelist"]

    def is_ip_ignored(self, address):
        return self._is_ip_in_list(address, "ignore")

    def is_user_ip_ignored(self, user):

        user_address = core.user_addresses.get(user)

        if user_address:
            ip_address, _port = user_address

            if self.is_ip_ignored(ip_address):
                return True

        return False
