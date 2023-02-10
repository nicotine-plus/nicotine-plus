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

    """ IP Filter List Management """

    def _request_ip(self, user, action, request_list):
        """ Ask for the IP address of an unknown user. Once a GetPeerAddress
         response arrives, either ban_unban_user_ip_callback or
         ignore_unignore_user_ip_callback is called. """

        if user not in request_list:
            request_list[user] = action

        core.queue.append(slskmessages.GetPeerAddress(user))

    def _add_user_ip_to_list(self, ip_list, username=None, ip_address=None):
        """ Add the current IP address and username of a user to a list """

        if not username:
            # Try to get a username from currently active connections
            username = self.get_online_username(ip_address)

        elif not self.is_ip_address(ip_address):
            # Try to get a known address for the user, use username as placeholder otherwise
            ip_addresses = self._get_user_ip_addresses(username, ip_list, request_action="add")
            ip_address = next(iter(ip_addresses), f"? ({username})")

        if ip_address and (ip_address not in ip_list or ip_list[ip_address] != username):
            ip_list[ip_address] = username
            config.write_configuration()

        return ip_address

    def _remove_user_ips_from_list(self, ip_list, username=None, ip_addresses=None):
        """ Remove the previously saved IP address of a user from a list """

        if not ip_addresses:
            # Try to get a known address for the user
            ip_addresses = self._get_user_ip_addresses(username, ip_list, request_action="remove")

        for ip_address in ip_addresses:
            if ip_address in ip_list:
                del ip_list[ip_address]

        config.write_configuration()
        return ip_addresses

    """ IP List Lookup Functions """

    @staticmethod
    def _get_previous_user_ip_addresses(user, ip_list):
        """ Retrieve IP address of a user previously saved in an IP list, for
        setting Ban/Ignore IP Address check buttons in user actions menus """

        ip_addresses = set()

        for ip_address, username in ip_list.items():
            if user == username:
                ip_addresses.add(ip_address)

        return ip_addresses

    @staticmethod
    def get_online_user_ip_address(user):
        """ Try to lookup an address from watched known connections,
        for updating an IP list item if the address is unspecified """

        user_address = core.user_addresses.get(user)

        if not user_address:
            # User is offline
            return None

        user_ip_address, _user_port = user_address
        return user_ip_address

    def _get_user_ip_addresses(self, user, ip_list, request_action):
        """ Returns the known IP addresses of a user, requests one otherwise """

        ip_addresses = set()

        if request_action == "add":
            # Get current IP for user, if known
            online_ip_address = self.get_online_user_ip_address(user)

            if online_ip_address:
                ip_addresses.add(online_ip_address)

        elif request_action == "remove":
            # Remove all known IP addresses for user
            ip_addresses = self._get_previous_user_ip_addresses(user, ip_list)

        if ip_addresses:
            return ip_addresses

        # User's IP address is unknown, request it from the server
        if ip_list == config.sections["server"]["ipblocklist"]:
            request_list = self.ip_ban_requested
        else:
            request_list = self.ip_ignore_requested

        self._request_ip(user, request_action, request_list)
        return ip_addresses

    @staticmethod
    def get_online_username(ip_address):
        """ Try to match a username from watched and known connections,
        for updating an IP list item if the username is unspecified """

        for username, user_address in core.user_addresses.items():
            if ip_address == user_address[0]:
                return username

        return None

    @staticmethod
    def is_ip_address(ip_address, allow_zero=True, allow_wildcard=True):
        """ Check if the given value is an IPv4 address or not """

        if not ip_address or ip_address is None or ip_address.count(".") != 3:
            return False

        if not allow_zero and ip_address == "0.0.0.0":
            # User is offline if ip_address "0.0.0.0" (not None!)
            return False

        for part in ip_address.split("."):
            if allow_wildcard and part == "*":
                continue

            if not part.isdigit():
                return False

            if int(part) > 255:
                return False

        return True

    """ IP Filter Rule Processing """

    def _check_user_ips_filtered(self, ip_list, username=None, ip_addresses=None):
        """ Check if an IP address is present in a list """

        if not ip_addresses:
            # Get all known IP addresses for user
            ip_addresses = self._get_previous_user_ip_addresses(username, ip_list)
            online_ip_address = self.get_online_user_ip_address(username)

            if online_ip_address:
                ip_addresses.add(online_ip_address)

            elif username and f"? ({username})" in ip_addresses:
                # Username placeholder present. We don't know the user's IP address yet, but we want to filter it.
                return True

            if not ip_addresses:
                return False

        for ip_address in ip_addresses:
            s_address = ip_address.split(".")

            for address in ip_list:
                # No Wildcard in IP
                if "*" not in address:
                    if ip_address == address:
                        return True
                    continue

                # Wildcard in IP
                parts = address.split(".")
                seg = 0

                for part in parts:
                    # Stop if there's no wildcard or matching string number
                    if part not in (s_address[seg], "*"):
                        break

                    seg += 1

                    # Last time around
                    if seg == 4:
                        # Wildcard filter
                        return True

        # Not filtered
        return False

    def check_user(self, user, ip_address=None):
        """ Check if this user is banned, geoip-blocked, and which shares
        it is allowed to access based on transfer and shares settings. """

        if self.is_user_banned(user) or self.is_user_ip_banned(user, ip_address):
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
            # We can't close wildcard patterns nor dummy (zero) addresses
            if self.is_ip_address(ip_address, allow_wildcard=False, allow_zero=False):
                core.queue.append(slskmessages.CloseConnectionIP(ip_address))

    """ Callbacks """

    def _update_saved_user_ip_addresses(self, ip_list, username, ip_address):
        """ Check if a user's IP address has changed and update the lists """

        previous_ip_addresses = self._get_previous_user_ip_addresses(username, ip_list)

        if not previous_ip_addresses:
            # User is not banned
            return

        ip_address_placeholder = f"? ({username})"

        if ip_address_placeholder in previous_ip_addresses:
            self._remove_user_ips_from_list(ip_list, ip_addresses=[ip_address_placeholder])

        if ip_address not in previous_ip_addresses:
            self._add_user_ip_to_list(ip_list, username, ip_address)

    def _get_peer_address(self, msg):
        """ Server code: 3 """

        user = msg.user

        if user not in core.user_addresses:
            # User is offline
            return

        ip_address = msg.ip_address

        # If the IP address changed, make sure our IP ban/ignore list reflects this
        self._update_saved_user_ip_addresses(config.sections["server"]["ipblocklist"], user, ip_address)
        self._update_saved_user_ip_addresses(config.sections["server"]["ipignorelist"], user, ip_address)

        # Check pending "add" and "remove" requests for IP-based filtering of previously offline users
        self._ban_unban_user_ip_callback(user, ip_address)
        self._ignore_unignore_user_ip_callback(user, ip_address)

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

    def ban_user_ip(self, user=None, ip_address=None):

        ip_address = self._add_user_ip_to_list(config.sections["server"]["ipblocklist"], user, ip_address)

        if self.is_ip_address(ip_address, allow_wildcard=False, allow_zero=False):
            # We can't close wildcard patterns nor dummy (zero) address entries
            core.queue.append(slskmessages.CloseConnectionIP(ip_address))

        return ip_address

    def unban_user_ip(self, user=None, ip_address=None):
        ip_addresses = {ip_address} if ip_address else set()
        return self._remove_user_ips_from_list(config.sections["server"]["ipblocklist"], user, ip_addresses)

    def _ban_unban_user_ip_callback(self, user, ip_address):

        request = self.ip_ban_requested.pop(user, None)

        if request == "add":
            self.ban_user_ip(user, ip_address)

        elif request == "remove":
            self.unban_user_ip(user, ip_address)

    def get_previous_banned_user_ips(self, user):
        return self._get_previous_user_ip_addresses(user, config.sections["server"]["ipblocklist"])

    def is_user_banned(self, user):
        return user in config.sections["server"]["banlist"]

    def is_user_ip_banned(self, user=None, ip_address=None):
        ip_addresses = {ip_address} if ip_address else set()
        return self._check_user_ips_filtered(config.sections["server"]["ipblocklist"], user, ip_addresses)

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

    def ignore_user_ip(self, user=None, ip_address=None):
        return self._add_user_ip_to_list(config.sections["server"]["ipignorelist"], user, ip_address)

    def unignore_user_ip(self, user=None, ip_address=None):
        ip_addresses = {ip_address} if ip_address else set()
        return self._remove_user_ips_from_list(config.sections["server"]["ipignorelist"], user, ip_addresses)

    def _ignore_unignore_user_ip_callback(self, user, ip_address):

        request = self.ip_ignore_requested.pop(user, None)

        if request == "add":
            self.ignore_user_ip(user, ip_address)

        elif request == "remove":
            self.unignore_user_ip(user, ip_address)

    def get_previous_ignored_user_ips(self, user):
        return self._get_previous_user_ip_addresses(user, config.sections["server"]["ipignorelist"])

    def is_user_ignored(self, user):
        return user in config.sections["server"]["ignorelist"]

    def is_user_ip_ignored(self, user=None, ip_address=None):
        ip_addresses = {ip_address} if ip_address else set()
        return self._check_user_ips_filtered(config.sections["server"]["ipignorelist"], user, ip_addresses)
