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

from bisect import bisect_left
from socket import inet_aton
from struct import Struct
from sys import intern

from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events

UINT32_UNPACK = Struct(">I").unpack_from


class NetworkFilter:
    """Functions related to banning and ignoring users."""

    __slots__ = ("ip_ban_requested", "ip_ignore_requested", "_banned_users", "_ignored_users",
                 "_ip_range_values", "_ip_range_countries", "_loaded_ip_country_data")

    COUNTRIES = {
        "AD": _("Andorra"),
        "AE": _("United Arab Emirates"),
        "AF": _("Afghanistan"),
        "AG": _("Antigua & Barbuda"),
        "AI": _("Anguilla"),
        "AL": _("Albania"),
        "AM": _("Armenia"),
        "AO": _("Angola"),
        "AQ": _("Antarctica"),
        "AR": _("Argentina"),
        "AS": _("American Samoa"),
        "AT": _("Austria"),
        "AU": _("Australia"),
        "AW": _("Aruba"),
        "AX": _("Åland Islands"),
        "AZ": _("Azerbaijan"),
        "BA": _("Bosnia & Herzegovina"),
        "BB": _("Barbados"),
        "BD": _("Bangladesh"),
        "BE": _("Belgium"),
        "BF": _("Burkina Faso"),
        "BG": _("Bulgaria"),
        "BH": _("Bahrain"),
        "BI": _("Burundi"),
        "BJ": _("Benin"),
        "BL": _("Saint Barthelemy"),
        "BM": _("Bermuda"),
        "BN": _("Brunei Darussalam"),
        "BO": _("Bolivia"),
        "BQ": _("Bonaire, Sint Eustatius and Saba"),
        "BR": _("Brazil"),
        "BS": _("Bahamas"),
        "BT": _("Bhutan"),
        "BV": _("Bouvet Island"),
        "BW": _("Botswana"),
        "BY": _("Belarus"),
        "BZ": _("Belize"),
        "CA": _("Canada"),
        "CC": _("Cocos (Keeling) Islands"),
        "CD": _("Democratic Republic of Congo"),
        "CF": _("Central African Republic"),
        "CG": _("Congo"),
        "CH": _("Switzerland"),
        "CI": _("Ivory Coast"),
        "CK": _("Cook Islands"),
        "CL": _("Chile"),
        "CM": _("Cameroon"),
        "CN": _("China"),
        "CO": _("Colombia"),
        "CR": _("Costa Rica"),
        "CU": _("Cuba"),
        "CV": _("Cabo Verde"),
        "CW": _("Curaçao"),
        "CX": _("Christmas Island"),
        "CY": _("Cyprus"),
        "CZ": _("Czechia"),
        "DE": _("Germany"),
        "DJ": _("Djibouti"),
        "DK": _("Denmark"),
        "DM": _("Dominica"),
        "DO": _("Dominican Republic"),
        "DZ": _("Algeria"),
        "EC": _("Ecuador"),
        "EE": _("Estonia"),
        "EG": _("Egypt"),
        "EH": _("Western Sahara"),
        "ER": _("Eritrea"),
        "ES": _("Spain"),
        "ET": _("Ethiopia"),
        "EU": _("Europe"),
        "FI": _("Finland"),
        "FJ": _("Fiji"),
        "FK": _("Falkland Islands (Malvinas)"),
        "FM": _("Micronesia"),
        "FO": _("Faroe Islands"),
        "FR": _("France"),
        "GA": _("Gabon"),
        "GB": _("Great Britain"),
        "GD": _("Grenada"),
        "GE": _("Georgia"),
        "GF": _("French Guiana"),
        "GG": _("Guernsey"),
        "GH": _("Ghana"),
        "GI": _("Gibraltar"),
        "GL": _("Greenland"),
        "GM": _("Gambia"),
        "GN": _("Guinea"),
        "GP": _("Guadeloupe"),
        "GQ": _("Equatorial Guinea"),
        "GR": _("Greece"),
        "GS": _("South Georgia & South Sandwich Islands"),
        "GT": _("Guatemala"),
        "GU": _("Guam"),
        "GW": _("Guinea-Bissau"),
        "GY": _("Guyana"),
        "HK": _("Hong Kong"),
        "HM": _("Heard & McDonald Islands"),
        "HN": _("Honduras"),
        "HR": _("Croatia"),
        "HT": _("Haiti"),
        "HU": _("Hungary"),
        "ID": _("Indonesia"),
        "IE": _("Ireland"),
        "IL": _("Israel"),
        "IM": _("Isle of Man"),
        "IN": _("India"),
        "IO": _("British Indian Ocean Territory"),
        "IQ": _("Iraq"),
        "IR": _("Iran"),
        "IS": _("Iceland"),
        "IT": _("Italy"),
        "JE": _("Jersey"),
        "JM": _("Jamaica"),
        "JO": _("Jordan"),
        "JP": _("Japan"),
        "KE": _("Kenya"),
        "KG": _("Kyrgyzstan"),
        "KH": _("Cambodia"),
        "KI": _("Kiribati"),
        "KM": _("Comoros"),
        "KN": _("Saint Kitts & Nevis"),
        "KP": _("North Korea"),
        "KR": _("South Korea"),
        "KW": _("Kuwait"),
        "KY": _("Cayman Islands"),
        "KZ": _("Kazakhstan"),
        "LA": _("Laos"),
        "LB": _("Lebanon"),
        "LC": _("Saint Lucia"),
        "LI": _("Liechtenstein"),
        "LK": _("Sri Lanka"),
        "LR": _("Liberia"),
        "LS": _("Lesotho"),
        "LT": _("Lithuania"),
        "LU": _("Luxembourg"),
        "LV": _("Latvia"),
        "LY": _("Libya"),
        "MA": _("Morocco"),
        "MC": _("Monaco"),
        "MD": _("Moldova"),
        "ME": _("Montenegro"),
        "MF": _("Saint Martin"),
        "MG": _("Madagascar"),
        "MH": _("Marshall Islands"),
        "MK": _("North Macedonia"),
        "ML": _("Mali"),
        "MM": _("Myanmar"),
        "MN": _("Mongolia"),
        "MO": _("Macau"),
        "MP": _("Northern Mariana Islands"),
        "MQ": _("Martinique"),
        "MR": _("Mauritania"),
        "MS": _("Montserrat"),
        "MT": _("Malta"),
        "MU": _("Mauritius"),
        "MV": _("Maldives"),
        "MW": _("Malawi"),
        "MX": _("Mexico"),
        "MY": _("Malaysia"),
        "MZ": _("Mozambique"),
        "NA": _("Namibia"),
        "NC": _("New Caledonia"),
        "NE": _("Niger"),
        "NF": _("Norfolk Island"),
        "NG": _("Nigeria"),
        "NI": _("Nicaragua"),
        "NL": _("Netherlands"),
        "NO": _("Norway"),
        "NP": _("Nepal"),
        "NR": _("Nauru"),
        "NU": _("Niue"),
        "NZ": _("New Zealand"),
        "OM": _("Oman"),
        "PA": _("Panama"),
        "PE": _("Peru"),
        "PF": _("French Polynesia"),
        "PG": _("Papua New Guinea"),
        "PH": _("Philippines"),
        "PK": _("Pakistan"),
        "PL": _("Poland"),
        "PM": _("Saint Pierre & Miquelon"),
        "PN": _("Pitcairn"),
        "PR": _("Puerto Rico"),
        "PS": _("State of Palestine"),
        "PT": _("Portugal"),
        "PW": _("Palau"),
        "PY": _("Paraguay"),
        "QA": _("Qatar"),
        "RE": _("Réunion"),
        "RO": _("Romania"),
        "RS": _("Serbia"),
        "RU": _("Russia"),
        "RW": _("Rwanda"),
        "SA": _("Saudi Arabia"),
        "SB": _("Solomon Islands"),
        "SC": _("Seychelles"),
        "SD": _("Sudan"),
        "SE": _("Sweden"),
        "SG": _("Singapore"),
        "SH": _("Saint Helena"),
        "SI": _("Slovenia"),
        "SJ": _("Svalbard & Jan Mayen Islands"),
        "SK": _("Slovak Republic"),
        "SL": _("Sierra Leone"),
        "SM": _("San Marino"),
        "SN": _("Senegal"),
        "SO": _("Somalia"),
        "SR": _("Suriname"),
        "SS": _("South Sudan"),
        "ST": _("Sao Tome & Principe"),
        "SV": _("El Salvador"),
        "SX": _("Sint Maarten"),
        "SY": _("Syria"),
        "SZ": _("Eswatini"),
        "TC": _("Turks & Caicos Islands"),
        "TD": _("Chad"),
        "TF": _("French Southern Territories"),
        "TG": _("Togo"),
        "TH": _("Thailand"),
        "TJ": _("Tajikistan"),
        "TK": _("Tokelau"),
        "TL": _("Timor-Leste"),
        "TM": _("Turkmenistan"),
        "TN": _("Tunisia"),
        "TO": _("Tonga"),
        "TR": _("Türkiye"),
        "TT": _("Trinidad & Tobago"),
        "TV": _("Tuvalu"),
        "TW": _("Taiwan"),
        "TZ": _("Tanzania"),
        "UA": _("Ukraine"),
        "UG": _("Uganda"),
        "UM": _("U.S. Minor Outlying Islands"),
        "US": _("United States"),
        "UY": _("Uruguay"),
        "UZ": _("Uzbekistan"),
        "VA": _("Holy See (Vatican City State)"),
        "VC": _("Saint Vincent & The Grenadines"),
        "VE": _("Venezuela"),
        "VG": _("British Virgin Islands"),
        "VI": _("U.S. Virgin Islands"),
        "VN": _("Viet Nam"),
        "VU": _("Vanuatu"),
        "WF": _("Wallis & Futuna"),
        "WS": _("Samoa"),
        "YE": _("Yemen"),
        "YT": _("Mayotte"),
        "ZA": _("South Africa"),
        "ZM": _("Zambia"),
        "ZW": _("Zimbabwe")
    }

    def __init__(self):

        self.ip_ban_requested = {}
        self.ip_ignore_requested = {}

        self._banned_users = set()
        self._ignored_users = set()
        self._ip_range_values = ()
        self._ip_range_countries = ()
        self._loaded_ip_country_data = False

        for event_name, callback in (
            ("peer-address", self._get_peer_address),
            ("quit", self._quit),
            ("server-disconnect", self._server_disconnect),
            ("start", self._start)
        ):
            events.connect(event_name, callback)

    def _start(self):

        for source, target_set in (
            ("banlist", self._banned_users),
            ("ignorelist", self._ignored_users)
        ):
            for username in config.sections["server"][source]:
                if isinstance(username, str):
                    target_set.add(username)

    def _populate_ip_country_data(self):

        if self._loaded_ip_country_data:
            return

        data_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "external", "data")

        with open(os.path.join(data_path, "ip_country_data.csv"), "r", encoding="utf-8") as file_handle:
            for line in file_handle:
                line = line.strip()

                if not line or line.startswith("#"):
                    continue

                if self._ip_range_values:
                    # String interning to reduce memory usage of duplicate strings
                    self._ip_range_countries = tuple(intern(x) for x in line.split(","))
                    break

                self._ip_range_values = tuple(int(x) for x in line.split(","))

        self._loaded_ip_country_data = True

    def _server_disconnect(self, _msg):
        self.ip_ban_requested.clear()
        self.ip_ignore_requested.clear()

    def _quit(self):

        self._banned_users.clear()
        self._ignored_users.clear()
        self._ip_range_values = ()
        self._ip_range_countries = ()
        self._loaded_ip_country_data = False

    # IP Filter List Management #

    def _request_ip(self, username, action, request_list):
        """Ask for the IP address of an unknown user.

        Once a GetPeerAddress response arrives, either
        ban_unban_user_ip_callback or ignore_unignore_user_ip_callback
        is called.
        """

        if username not in request_list:
            request_list[username] = action

        core.users.request_ip_address(username)

    def _add_user_ip_to_list(self, ip_list, username=None, ip_address=None):
        """Add the current IP address and username of a user to a list."""

        if not username:
            # Try to get a username from currently active connections
            username = self.get_online_username(ip_address)

        elif not self.is_ip_address(ip_address):
            # Try to get a known address for the user, use username as placeholder otherwise
            ip_addresses = self._get_user_ip_addresses(username, ip_list, request_action="add")
            ip_address = next(iter(ip_addresses), f"? ({username})")

        if not ip_address:
            return None

        if ip_address not in ip_list or (username and ip_list[ip_address] != username):
            ip_list[ip_address] = username or ""
            config.write_configuration()

        return ip_address

    def _remove_user_ips_from_list(self, ip_list, username=None, ip_addresses=None):
        """Remove the previously saved IP address of a user from a list."""

        if not ip_addresses:
            # Try to get a known address for the user
            ip_addresses = self._get_user_ip_addresses(username, ip_list, request_action="remove")

        for ip_address in ip_addresses:
            if ip_address in ip_list:
                del ip_list[ip_address]

        config.write_configuration()
        return ip_addresses

    # IP List Lookup Functions #

    @staticmethod
    def _get_previous_user_ip_addresses(username, ip_list):
        """Retrieve IP address of a user previously saved in an IP list."""

        ip_addresses = set()

        if username not in ip_list.values():
            # User is not listed, skip iteration
            return ip_addresses

        for ip_address, i_username in ip_list.items():
            if username == i_username:
                ip_addresses.add(ip_address)

        return ip_addresses

    def _get_user_ip_addresses(self, username, ip_list, request_action):
        """Returns the known IP addresses of a user, requests one otherwise."""

        ip_addresses = set()

        if request_action == "add":
            # Get current IP for user, if known
            online_address = core.users.addresses.get(username)

            if online_address:
                online_ip_address, _port = online_address
                ip_addresses.add(online_ip_address)

        elif request_action == "remove":
            # Remove all known IP addresses for user
            ip_addresses = self._get_previous_user_ip_addresses(username, ip_list)

        if ip_addresses:
            return ip_addresses

        # User's IP address is unknown, request it from the server
        if ip_list == config.sections["server"]["ipblocklist"]:
            request_list = self.ip_ban_requested
        else:
            request_list = self.ip_ignore_requested

        self._request_ip(username, request_action, request_list)
        return ip_addresses

    @staticmethod
    def get_online_username(ip_address):
        """Try to match a username from watched and known connections, for
        updating an IP list item if the username is unspecified."""

        for username, user_address in core.users.addresses.items():
            user_ip_address, _user_port = user_address

            if ip_address == user_ip_address:
                return username

        return None

    def get_country_code(self, ip_address):

        if not self._loaded_ip_country_data:
            self._populate_ip_country_data()

        if not self._ip_range_countries:
            return ""

        ip_num, = UINT32_UNPACK(inet_aton(ip_address))
        ip_index = bisect_left(self._ip_range_values, ip_num)
        country_code = self._ip_range_countries[ip_index]

        return country_code

    @staticmethod
    def is_ip_address(ip_address, allow_zero=True, allow_wildcard=True):
        """Check if the given value is an IPv4 address or not."""

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

    # IP Filter Rule Processing #

    def _check_user_ip_filtered(self, ip_list, username=None, ip_address=None):
        """Check if an IP address is present in a list."""

        if username and username in ip_list.values():
            # Username is present in the list, so we want to filter it
            return True

        if not ip_address:
            address = core.users.addresses.get(username)

            if not address:
                # Username not listed and is offline, so we can't filter it
                return False

            ip_address, _port = address

        if ip_address in ip_list:
            # IP filtered
            return True

        s_address = ip_address.split(".")

        for address in ip_list:
            if "*" not in address:
                # No Wildcard in IP rule
                continue

            # Wildcard in IP rule
            parts = address.split(".")
            seg = 0

            for part in parts:
                # Stop if there's no wildcard or matching string number
                if part not in {s_address[seg], "*"}:
                    break

                seg += 1

                # Last time around
                if seg == 4:
                    # Wildcard filter, add actual IP address and username into list
                    self._add_user_ip_to_list(ip_list, username, ip_address)
                    return True

        # Not filtered
        return False

    # Callbacks #

    def _update_saved_user_ip_addresses(self, ip_list, username, ip_address):
        """Check if a user's IP address has changed and update the lists."""

        previous_ip_addresses = self._get_previous_user_ip_addresses(username, ip_list)

        if not previous_ip_addresses:
            # User is not filtered
            return

        ip_address_placeholder = f"? ({username})"

        if ip_address_placeholder in previous_ip_addresses:
            self._remove_user_ips_from_list(ip_list, ip_addresses=[ip_address_placeholder])

        if ip_address not in previous_ip_addresses:
            self._add_user_ip_to_list(ip_list, username, ip_address)

    def _get_peer_address(self, msg):
        """Server code 3."""

        username = msg.user
        ip_address = msg.ip_address

        if ip_address == "0.0.0.0":
            # User is offline
            return

        # If the IP address changed, make sure our IP ban/ignore list reflects this
        self._update_saved_user_ip_addresses(config.sections["server"]["ipblocklist"], username, ip_address)
        self._update_saved_user_ip_addresses(config.sections["server"]["ipignorelist"], username, ip_address)

        # Check pending "add" and "remove" requests for IP-based filtering of previously offline users
        self._ban_unban_user_ip_callback(username, ip_address)
        self._ignore_unignore_user_ip_callback(username, ip_address)

    # Banning #

    def ban_user(self, username):

        if not self.is_user_banned(username):
            self._banned_users.add(username)
            config.sections["server"]["banlist"].append(username)
            config.write_configuration()

        events.emit("ban-user", username)

    def unban_user(self, username):

        if self.is_user_banned(username):
            self._banned_users.remove(username)
            config.sections["server"]["banlist"].remove(username)
            config.write_configuration()

        events.emit("unban-user", username)

    def ban_user_ip(self, username=None, ip_address=None):

        ip_address = self._add_user_ip_to_list(
            config.sections["server"]["ipblocklist"], username, ip_address)

        events.emit("ban-user-ip", username, ip_address)
        return ip_address

    def unban_user_ip(self, username=None, ip_address=None):

        ip_addresses = {ip_address} if ip_address else set()
        ip_addresses = self._remove_user_ips_from_list(
            config.sections["server"]["ipblocklist"], username, ip_addresses)

        events.emit("unban-user-ip", username, ip_addresses)
        return ip_addresses

    def _ban_unban_user_ip_callback(self, username, ip_address):

        request = self.ip_ban_requested.pop(username, None)

        if request == "add":
            self.ban_user_ip(username, ip_address)

        elif request == "remove":
            self.unban_user_ip(username, ip_address)

    def is_user_banned(self, username):
        return username in self._banned_users

    def is_user_ip_banned(self, username=None, ip_address=None):
        return self._check_user_ip_filtered(
            config.sections["server"]["ipblocklist"], username, ip_address)

    # Ignoring #

    def ignore_user(self, username):

        if not self.is_user_ignored(username):
            self._ignored_users.add(username)
            config.sections["server"]["ignorelist"].append(username)
            config.write_configuration()

        events.emit("ignore-user", username)

    def unignore_user(self, username):

        if self.is_user_ignored(username):
            self._ignored_users.remove(username)
            config.sections["server"]["ignorelist"].remove(username)
            config.write_configuration()

        events.emit("unignore-user", username)

    def ignore_user_ip(self, username=None, ip_address=None):

        ip_address = self._add_user_ip_to_list(
            config.sections["server"]["ipignorelist"], username, ip_address)

        events.emit("ignore-user-ip", username, ip_address)
        return ip_address

    def unignore_user_ip(self, username=None, ip_address=None):

        ip_addresses = {ip_address} if ip_address else set()
        ip_addresses = self._remove_user_ips_from_list(
            config.sections["server"]["ipignorelist"], username, ip_addresses)

        events.emit("unignore-user-ip", username, ip_addresses)
        return ip_addresses

    def _ignore_unignore_user_ip_callback(self, username, ip_address):

        request = self.ip_ignore_requested.pop(username, None)

        if request == "add":
            self.ignore_user_ip(username, ip_address)

        elif request == "remove":
            self.unignore_user_ip(username, ip_address)

    def is_user_ignored(self, username):
        return username in self._ignored_users

    def is_user_ip_ignored(self, username=None, ip_address=None):
        return self._check_user_ip_filtered(
            config.sections["server"]["ipignorelist"], username, ip_address)
