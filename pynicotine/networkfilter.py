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

    def _request_ip(self, user, action, list_type, online=True):
        """ Ask for the IP address of an unknown user. Once a GetPeerAddress
         response arrives, either ban_unban_user_ip_callback or
         ignore_unignore_user_ip_callback is called. """

        if list_type == "ban":
            request_list = self.ip_ban_requested
        else:
            request_list = self.ip_ignore_requested

        if user not in request_list:
            request_list[user] = action

        if not online:
            # We already know this user is probably offline
            return

        core.queue.append(slskmessages.GetPeerAddress(user))

    def _add_user_ip_to_list(self, list_type, user, ip_address):
        """ Add the current IP address and username of a user to a list """

        if list_type == "ban":
            ip_list = config.sections["server"]["ipblocklist"]
        else:
            ip_list = config.sections["server"]["ipignorelist"]

        if self.is_ip_address(ip_address, allow_zero=False) and not user:
            # Try to get a username from currently active connections
            user = self.get_known_username(ip_address) or ""

        elif user and not self.is_ip_address(ip_address, allow_zero=False):
            # Try to get an address from currently active connections
            ip_address = self.get_known_ip_address(user)

            if not self.is_ip_address(ip_address, allow_zero=False):
                cached_ip = self._get_cached_user_ip(user, ip_list) or ""
                offline = cached_ip.startswith("?.?.?.?") or cached_ip == "0.0.0.0"

                # Queue a callback to update the filter, only try one time
                self._request_ip(user, "add", list_type, online=not offline)

                # Add a unique dummy entry for now, so it can be updated later
                ip_address = f"?.?.?.? [{user}]"

        if ip_address not in ip_list or ip_list[ip_address] != user != "":
            ip_list[ip_address] = user
            config.write_configuration()

        # Close connection and print output as confirmation on CLI
        return ip_address

    def _remove_user_ip_from_list(self, list_type, user, ip_address):
        """ Remove the previously saved IP address of a user from a list """

        if list_type == "ban":
            ip_list = config.sections["server"]["ipblocklist"]
        else:
            ip_list = config.sections["server"]["ipignorelist"]

        if user and not ip_address or ip_address is None:
            # Try to get an address from currently active connections
            cached_ip = self._get_cached_user_ip(user, ip_list) or ""
            ip_address = cached_ip or self.get_known_ip_address(user)

            if ip_address.startswith("?.?.?.?") or ip_address == "0.0.0.0":
                # Allow deleting dummy entries (the offline default IP
                # "0.0.0.0" entry is not saved in filters since 3.3.0)
                pass

            elif not self.is_ip_address(ip_address, allow_zero=False):
                # IP unknown, queue a callback to remove the filter later
                self._request_ip(user, "remove", list_type, online=True)

                # Print output as confirmation on CLI also do username list
                return user

        if ip_address in ip_list:
            del ip_list[ip_address]
            config.write_configuration()

        # Print output as confirmation on CLI
        return ip_address

    """ IP List Lookup Functions """

    @staticmethod
    def _get_cached_user_ip(user, ip_list):
        """ Retrieve IP address of a user previously saved in an IP list, for
        setting Ban/Ignore IP Address check buttons in user actions menus """

        for ip_address, username in ip_list.items():
            if user == username:
                return ip_address

        return None

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

    @staticmethod
    def _is_ip_in_list(address, ip_list):
        """ Check if an IP address exists in a list, disregarding the username
        the address is paired with. """

        if address is None:
            return True

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
                    # Wildcard filter
                    return True

        # Not filtered
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
            if not self.is_ip_address(ip_address, allow_wildcard=False, allow_zero=False):
                # We can't close wildcard patterns nor dummy (zero) addresses
                continue

            core.queue.append(slskmessages.CloseConnectionIP(ip_address))

    """ Callbacks """

    def _update_saved_user_ip_address(self, user, new_ip):
        """ Check if a user's IP address has changed and update the lists """

        cached_banned_ip = self.get_cached_banned_user_ip(user)

        if cached_banned_ip is not None and cached_banned_ip != new_ip:
            self.unban_user_ip(user, cached_banned_ip)
            self.ban_user_ip(user, new_ip)

        cached_ignored_ip = self.get_cached_ignored_user_ip(user)

        if cached_ignored_ip is not None and cached_ignored_ip != new_ip:
            self.unignore_user_ip(user, cached_ignored_ip)
            self.ignore_user_ip(user, new_ip)

    def _get_peer_address(self, msg):
        """ Server code: 3 """

        ip_address = msg.ip_address

        if not self.is_ip_address(ip_address, allow_zero=False):
            # User is offline if ip_address "0.0.0.0" (not None!)
            return

        user = msg.user

        # If the IP address changed, make sure our IP ban/ignore list reflects this
        self._update_saved_user_ip_address(user, ip_address)

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

        banned_ip_address = self._add_user_ip_to_list("ban", user, ip_address)

        if self.is_ip_address(banned_ip_address, allow_wildcard=False, allow_zero=False):
            # We can't close wildcard patterns nor dummy (zero) address entries
            core.queue.append(slskmessages.CloseConnectionIP(banned_ip_address))

        return banned_ip_address

    def unban_user_ip(self, user=None, ip_address=None):
        return self._remove_user_ip_from_list("ban", user, ip_address)

    def _ban_unban_user_ip_callback(self, user, ip_address):

        request = self.ip_ban_requested.pop(user, None)

        if request is None:
            return

        if request == "remove":
            self.unban_user_ip(user, ip_address)
        else:
            self.ban_user_ip(user, ip_address)

    def get_cached_banned_user_ip(self, user):
        return self._get_cached_user_ip(user, config.sections["server"]["ipblocklist"])

    def is_user_banned(self, user):
        return user in config.sections["server"]["banlist"]

    def is_ip_banned(self, address):
        return self._is_ip_in_list(address, config.sections["server"]["ipblocklist"])

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
        return self._add_user_ip_to_list("ignore", user, ip_address)

    def unignore_user_ip(self, user=None, ip_address=None):
        return self._remove_user_ip_from_list("ignore", user, ip_address)

    def _ignore_unignore_user_ip_callback(self, user, ip_address):

        request = self.ip_ignore_requested.pop(user, None)

        if request is None:
            return

        if request == "remove":
            self.unignore_user_ip(user, ip_address)
        else:
            self.ignore_user_ip(user, ip_address)

    def get_cached_ignored_user_ip(self, user):
        return self._get_cached_user_ip(user, config.sections["server"]["ipignorelist"])

    def is_user_ignored(self, user):
        return user in config.sections["server"]["ignorelist"]

    def is_ip_ignored(self, address):
        return self._is_ip_in_list(address, config.sections["server"]["ipignorelist"])

    def is_user_ip_ignored(self, user):

        user_address = core.user_addresses.get(user)

        if user_address:
            ip_address, _port = user_address

            if self.is_ip_ignored(ip_address):
                return True

        return False
