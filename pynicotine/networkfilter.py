# COPYRIGHT (C) 2020-2021 Nicotine+ Team
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


class NetworkFilter:
    """ Functions related to banning, blocking and ignoring users """

    def __init__(self, network_processor, config, users, queue, geoip):

        self.network_processor = network_processor
        self.config = config
        self.users = users
        self.queue = queue
        self.geoip = geoip
        self.ipblock_requested = {}
        self.ipignore_requested = {}

    """ General """

    def _request_ip(self, user, action, list_type):
        """ Ask for the IP address of a user. Once a GetPeerAddress response arrives,
        either block_unblock_user_ip_callback or ignore_unignore_user_ip_callback
        is called. """

        if list_type == "block":
            request_list = self.ipblock_requested
        else:
            request_list = self.ipignore_requested

        if user not in self.users or not isinstance(self.users[user].addr, tuple):
            if user not in request_list:
                request_list[user] = action

            self.queue.append(slskmessages.GetPeerAddress(user))
            return True

        return False

    def _add_user_ip_to_list(self, user, list_type):
        """ Add the current IP of a user to a list. """

        if list_type == "block":
            ip_list = self.config.sections["server"]["ipblocklist"]
        else:
            ip_list = self.config.sections["server"]["ipignorelist"]

        if self._request_ip(user, "add", list_type):
            return

        ip_address, _port = self.users[user].addr
        if ip_address not in ip_list or ip_list[ip_address] != user:
            ip_list[ip_address] = user
            self.config.write_configuration()

    def _remove_user_ip_from_list(self, user, list_type):
        """ Attempt to remove the previously saved IP address of a user from a list. """

        if list_type == "block":
            cached_ip = self.get_cached_blocked_user_ip(user)
            ip_list = self.config.sections["server"]["ipblocklist"]
        else:
            cached_ip = self.get_cached_ignored_user_ip(user)
            ip_list = self.config.sections["server"]["ipignorelist"]

        if cached_ip is not None:
            del ip_list[cached_ip]
            self.config.write_configuration()
            return

        if self._request_ip(user, "remove", list_type):
            return

        ip_address, _port = self.users[user].addr
        if ip_address in ip_list:
            del ip_list[ip_address]
            self.config.write_configuration()

    def _get_cached_user_ip(self, user, list_type):
        """ Retrieve the IP address of a user previously saved in a list. """

        if list_type == "block":
            ip_list = self.config.sections["server"]["ipblocklist"]
        else:
            ip_list = self.config.sections["server"]["ipignorelist"]

        for ip_address, username in ip_list.items():
            if user == username:
                return ip_address

        return None

    def _is_ip_in_list(self, address, list_type):
        """ Check if an IP address exists in a list, disregarding the username
        the address is paired with. """

        if address is None:
            return True

        if list_type == "block":
            ip_list = self.config.sections["server"]["ipblocklist"]
        else:
            ip_list = self.config.sections["server"]["ipignorelist"]

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
                    # Wildcard blocked
                    return True

        # Not blocked
        return False

    def check_user(self, user, ip_address):
        """ Check if this user is banned, geoip-blocked, and which shares
        it is allowed to access based on transfer and shares settings. """

        if self.is_user_banned(user):
            if self.config.sections["transfers"]["usecustomban"]:
                return 0, "Banned (%s)" % self.config.sections["transfers"]["customban"]

            return 0, "Banned"

        for row in self.config.sections["server"]["userlist"]:
            if row[0] != user:
                continue

            if self.config.sections["transfers"]["buddysharestrustedonly"] and not row[4]:
                # Only trusted buddies allowed, and user isn't trusted
                return 1, ""

            if self.config.sections["transfers"]["enablebuddyshares"]:
                # For sending buddy-only shares
                return 2, ""

            # Buddy list users bypass geoblock
            return 1, ""

        if self.config.sections["transfers"]["friendsonly"]:
            return 0, "Sorry, friends only"

        if ip_address is None or not self.config.sections["transfers"]["geoblock"]:
            return 1, ""

        country_code = self.geoip.get_country_code(ip_address)

        if country_code == "-":
            if self.config.sections["transfers"]["geopanic"]:
                return 0, "Blocked country (Sorry, geographical paranoia)"

            return 1, ""

        """ Please note that all country codes are stored in the same string at the first index
        of an array, separated by commas (no idea why...) """

        if self.config.sections["transfers"]["geoblockcc"][0].find(country_code) >= 0:
            if self.config.sections["transfers"]["usecustomgeoblock"]:
                return 0, "Blocked country (%s)" % self.config.sections["transfers"]["customgeoblock"]

            return 0, "Blocked country"

        return 1, ""

    def update_saved_user_ip_filters(self, user):
        """ When we know a user's IP address has changed, we call this function to
        update the IP saved in lists. """

        if user not in self.users or not isinstance(self.users[user].addr, tuple):
            return

        new_ip, _new_port = self.users[user].addr
        cached_blocked_ip = self.get_cached_blocked_user_ip(user)

        if cached_blocked_ip is not None and cached_blocked_ip != new_ip:
            self.unblock_user_ip(user)
            self.block_user_ip(user)

        cached_ignored_ip = self.get_cached_ignored_user_ip(user)

        if cached_ignored_ip is not None and cached_ignored_ip != new_ip:
            self.unignore_user_ip(user)
            self.ignore_user_ip(user)

    """ Banning """

    def ban_user(self, user):

        if self.is_user_banned(user):
            return

        self.config.sections["server"]["banlist"].append(user)
        self.config.write_configuration()

        self.network_processor.transfers.ban_user(user)

    def unban_user(self, user):

        if self.is_user_banned(user):
            self.config.sections["server"]["banlist"].remove(user)
            self.config.write_configuration()

    def block_user_ip(self, user):
        self._add_user_ip_to_list(user, "block")

    def unblock_user_ip(self, user):
        self._remove_user_ip_from_list(user, "block")

    def block_unblock_user_ip_callback(self, user):

        if user not in self.ipblock_requested:
            return False

        if self.ipblock_requested[user] == "remove":
            self.unblock_user_ip(user)
        else:
            self.block_user_ip(user)

        del self.ipblock_requested[user]
        return True

    def get_cached_blocked_user_ip(self, user):
        return self._get_cached_user_ip(user, "block")

    def is_user_banned(self, user):
        return user in self.config.sections["server"]["banlist"]

    def is_ip_blocked(self, address):
        return self._is_ip_in_list(address, "block")

    """ Ignoring """

    def ignore_user(self, user):
        if not self.is_user_ignored(user):
            self.config.sections["server"]["ignorelist"].append(user)
            self.config.write_configuration()

    def unignore_user(self, user):
        if self.is_user_ignored(user):
            self.config.sections["server"]["ignorelist"].remove(user)
            self.config.write_configuration()

    def ignore_ip(self, ip_address):

        if not ip_address or ip_address.count(".") != 3:
            return

        ipignorelist = self.config.sections["server"]["ipignorelist"]

        if ip_address not in ipignorelist:
            ipignorelist[ip_address] = ""
            self.config.write_configuration()

    def ignore_user_ip(self, user):
        self._add_user_ip_to_list(user, "ignore")

    def unignore_user_ip(self, user):
        self._remove_user_ip_from_list(user, "ignore")

    def ignore_unignore_user_ip_callback(self, user):

        if user not in self.ipignore_requested:
            return False

        if self.ipignore_requested[user] == "remove":
            self.unignore_user_ip(user)
        else:
            self.ignore_user_ip(user)

        del self.ipignore_requested[user]
        return True

    def get_cached_ignored_user_ip(self, user):
        return self._get_cached_user_ip(user, "ignore")

    def is_user_ignored(self, user):
        return user in self.config.sections["server"]["ignorelist"]

    def is_ip_ignored(self, address):
        return self._is_ip_in_list(address, "ignore")

    def is_user_ip_ignored(self, user):

        if user not in self.users or not isinstance(self.users[user].addr, tuple):
            return False

        ip_address, _port = self.users[user].addr
        if self.is_ip_ignored(ip_address):
            return True

        return False
