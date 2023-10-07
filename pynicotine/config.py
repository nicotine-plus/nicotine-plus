# COPYRIGHT (C) 2020-2023 Nicotine+ Contributors
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2016-2018 Mutnick <mutnick@techie.com>
# COPYRIGHT (C) 2008-2011 quinox <quinox@users.sf.net>
# COPYRIGHT (C) 2009 hedonist <ak@sensi.org>
# COPYRIGHT (C) 2007 gallows <g4ll0ws@gmail.com>
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

import configparser
import os
import sys

from ast import literal_eval
from collections import defaultdict

from pynicotine.events import events
from pynicotine.i18n import apply_translations
from pynicotine.utils import encode_path
from pynicotine.utils import load_file
from pynicotine.utils import write_file_and_backup


class Config:
    """This class holds configuration information and provides the
    following methods:

    need_config() - returns true if configuration information is incomplete
    read_config() - reads configuration information from file
    write_configuration - writes configuration information to file

    The actual configuration information is stored as a two-level dictionary.
    First-level keys are config sections, second-level keys are config
    parameters.
    """

    def __init__(self):

        config_folder_path, self.data_folder_path = self.get_user_folders()
        self.config_file_path = os.path.join(config_folder_path, "config")
        self.config_loaded = False
        self.parser = configparser.ConfigParser(strict=False, interpolation=None)
        self.sections = defaultdict(dict)
        self.defaults = {}
        self.removed_options = {}

    @staticmethod
    def get_user_folders():
        """Returns a tuple:

        - the config folder
        - the data folder
        """

        if sys.platform == "win32":
            try:
                data_folder_path = os.path.join(os.path.normpath(os.environ["APPDATA"]), "nicotine")
            except KeyError:
                data_folder_path, _basename = os.path.split(sys.argv[0])

            config_folder_path = os.path.join(data_folder_path, "config")
            return config_folder_path, data_folder_path

        home = os.path.expanduser("~")
        legacy_folder_path = os.path.join(home, ".nicotine")

        if os.path.isdir(legacy_folder_path.encode("utf-8")):
            return legacy_folder_path, legacy_folder_path

        def xdg_path(xdg, default):
            path = os.environ.get(xdg)
            path = path.split(":")[0] if path else default

            return os.path.join(path, "nicotine")

        config_folder_path = xdg_path("XDG_CONFIG_HOME", os.path.join(home, ".config"))
        data_folder_path = xdg_path("XDG_DATA_HOME", os.path.join(home, ".local", "share"))

        return config_folder_path, data_folder_path

    def create_config_folder(self):
        """Create the folder for storing the config file in, if the folder
        doesn't exist."""

        folder_path, _basename = os.path.split(self.config_file_path)

        if not folder_path:
            # Only file name specified, use current folder
            return True

        folder_path_encoded = encode_path(folder_path)

        try:
            if not os.path.isdir(folder_path_encoded):
                os.makedirs(folder_path_encoded)

        except OSError as error:
            from pynicotine.logfacility import log

            log.add(_("Can't create directory '%(path)s', reported error: %(error)s"),
                    {"path": folder_path, "error": error})
            return False

        return True

    def create_data_folder(self):
        """Create the folder for storing data in (shared files etc.), if the
        folder doesn't exist."""

        data_folder_path_encoded = encode_path(self.data_folder_path)

        try:
            if not os.path.isdir(data_folder_path_encoded):
                os.makedirs(data_folder_path_encoded)

        except OSError as error:
            from pynicotine.logfacility import log

            log.add(_("Can't create directory '%(path)s', reported error: %(error)s"),
                    {"path": self.data_folder_path, "error": error})

    def load_config(self):

        log_folder_path = os.path.join(self.data_folder_path, "logs")
        self.defaults = {
            "server": {
                "server": ("server.slsknet.org", 2242),
                "login": "",
                "passw": "",
                "interface": "",
                "ctcpmsgs": False,
                "autosearch": [],
                "autoreply": "",
                "portrange": (2234, 2234),
                "upnp": True,
                "upnp_interval": 4,
                "auto_connect_startup": True,
                "userlist": [],
                "banlist": [],
                "ignorelist": [],
                "ipignorelist": {},
                "ipblocklist": {},
                "autojoin": ["nicotine"],
                "autoaway": 15,
                "away": False,
                "private_chatrooms": False,
                "command_aliases": {}
            },
            "transfers": {
                "incompletedir": os.path.join(self.data_folder_path, "incomplete"),
                "downloaddir": os.path.join(self.data_folder_path, "downloads"),
                "uploaddir": os.path.join(self.data_folder_path, "received"),
                "usernamesubfolders": False,
                "shared": [],
                "buddyshared": [],
                "trustedshared": [],
                "uploadbandwidth": 50,
                "use_upload_speed_limit": "unlimited",
                "uploadlimit": 1000,
                "uploadlimitalt": 100,
                "use_download_speed_limit": "unlimited",
                "downloadlimit": 1000,
                "downloadlimitalt": 100,
                "preferfriends": False,
                "useupslots": False,
                "uploadslots": 2,
                "afterfinish": "",
                "afterfolder": "",
                "fifoqueue": False,
                "usecustomban": False,
                "limitby": True,
                "customban": "Banned, don't bother retrying",
                "usecustomgeoblock": False,
                "customgeoblock": "Sorry, your country is blocked",
                "queuelimit": 10000,
                "filelimit": 100,
                "reveal_buddy_shares": False,
                "reveal_trusted_shares": False,
                "friendsnolimits": False,
                "groupdownloads": "folder_grouping",
                "groupuploads": "folder_grouping",
                "geoblock": False,
                "geoblockcc": [""],
                "remotedownloads": False,
                "uploadallowed": 3,
                "autoclear_downloads": False,
                "autoclear_uploads": False,
                "rescanonstartup": True,
                "enablefilters": False,
                "downloadregexp": "",
                "downloadfilters": [
                    ["desktop.ini", 1],
                    ["*.url", 1],
                    ["thumbs.db", 1],
                    ["albumart(_{........-....-....-....-............}_)?(_?(large|small))?\\.jpg", 0]
                ],
                "download_doubleclick": 2,
                "upload_doubleclick": 2,
                "downloadsexpanded": True,
                "uploadsexpanded": True
            },
            "userbrowse": {
                "expand_folders": True
            },
            "userinfo": {
                "descr": "''",
                "pic": ""
            },
            "words": {
                "censored": [],
                "autoreplaced": {
                    "teh ": "the ",
                    "taht ": "that ",
                    "tihng": "thing",
                    "youre": "you're",
                    "jsut": "just",
                    "thier": "their",
                    "tihs": "this"
                },
                "censorfill": "*",
                "censorwords": False,
                "replacewords": False,
                "tab": True,
                "dropdown": False,
                "characters": 3,
                "roomnames": False,
                "buddies": True,
                "roomusers": True,
                "commands": True
            },
            "logging": {
                "debug": False,
                "debugmodes": [],
                "debuglogsdir": os.path.join(log_folder_path, "debug"),
                "logcollapsed": True,
                "transferslogsdir": os.path.join(log_folder_path, "transfers"),
                "rooms_timestamp": "%H:%M:%S",
                "private_timestamp": "%Y-%m-%d %H:%M:%S",
                "log_timestamp": "%Y-%m-%d %H:%M:%S",
                "privatechat": True,
                "chatrooms": True,
                "transfers": False,
                "debug_file_output": False,
                "roomlogsdir": os.path.join(log_folder_path, "rooms"),
                "privatelogsdir": os.path.join(log_folder_path, "private"),
                "readroomlogs": True,
                "readroomlines": 200,
                "readprivatelines": 200,
                "rooms": []
            },
            "privatechat": {
                "store": True,
                "users": []
            },
            "columns": {
                "file_search": {},
                "download": {},
                "upload": {},
                "user_browse": {},
                "buddy_list": {},
                "chat_room": {}
            },
            "searches": {
                "expand_searches": True,
                "group_searches": "folder_grouping",
                "maxresults": 150,
                "enable_history": True,
                "history": [],
                "enablefilters": False,
                "filters_visible": False,
                "defilter": ["", "", "", "", 0, "", ""],
                "filtercc": [],
                "filterin": [],
                "filterout": [],
                "filtersize": [],
                "filterbr": [],
                "filtertype": [],
                "filterlength": [],
                "search_results": True,
                "max_displayed_results": 1500,
                "min_search_chars": 3,
                "remove_special_chars": True,
                "private_search_results": True
            },
            "ui": {
                "language": "",
                "dark_mode": False,
                "header_bar": True,
                "icontheme": "",
                "chatme": "#908e8b",
                "chatremote": "",
                "chatlocal": "",
                "chatcommand": "#908e8b",
                "chathilite": "#5288ce",
                "urlcolor": "#5288ce",
                "useronline": "#16bb5c",
                "useraway": "#c9ae13",
                "useroffline": "#e04f5e",
                "usernamehotspots": True,
                "usernamestyle": "bold",
                "textbg": "",
                "search": "",
                "searchq": "GREY",
                "inputcolor": "",
                "spellcheck": True,
                "exitdialog": 1,
                "tab_default": "",
                "tab_hilite": "#497ec2",
                "tab_changed": "#497ec2",
                "tab_select_previous": True,
                "tabmain": "Top",
                "tabrooms": "Top",
                "tabprivate": "Top",
                "tabinfo": "Top",
                "tabbrowse": "Top",
                "tabsearch": "Top",
                "globalfont": "",
                "textviewfont": "",
                "chatfont": "",
                "tabclosers": True,
                "searchfont": "",
                "listfont": "",
                "browserfont": "",
                "transfersfont": "",
                "last_tab_id": "",
                "modes_visible": {
                    "search": True,
                    "downloads": True,
                    "uploads": True,
                    "userbrowse": True,
                    "userinfo": True,
                    "private": True,
                    "chatrooms": True,
                    "interests": True
                },
                "modes_order": [
                    "search",
                    "downloads",
                    "uploads",
                    "userbrowse",
                    "userinfo",
                    "private",
                    "userlist",
                    "chatrooms",
                    "interests"
                ],
                "buddylistinchatrooms": "tab",
                "trayicon": True,
                "startup_hidden": False,
                "filemanager": "",
                "speechenabled": False,
                "speechprivate": "User %(user)s told you: %(message)s",
                "speechrooms": "In room %(room)s, user %(user)s said: %(message)s",
                "speechcommand": "flite -t $",
                "width": 800,
                "height": 600,
                "xposition": -1,
                "yposition": -1,
                "maximized": True,
                "reverse_file_paths": True,
                "file_size_unit": ""
            },
            "private_rooms": {
                "rooms": {}
            },
            "urls": {
                "protocols": {}
            },
            "interests": {
                "likes": [],
                "dislikes": []
            },
            "players": {
                "default": "",
                "npothercommand": "",
                "npplayer": "mpris",
                "npformatlist": [],
                "npformat": ""
            },
            "notifications": {
                "notification_window_title": True,
                "notification_tab_colors": False,
                "notification_popup_sound": False,
                "notification_popup_file": True,
                "notification_popup_folder": True,
                "notification_popup_private_message": True,
                "notification_popup_chatroom": False,
                "notification_popup_chatroom_mention": True,
                "notification_popup_wish": True
            },
            "plugins": {
                "enable": True,
                "enabled": []
            },
            "statistics": {
                "since_timestamp": 0,
                "started_downloads": 0,
                "completed_downloads": 0,
                "downloaded_size": 0,
                "started_uploads": 0,
                "completed_uploads": 0,
                "uploaded_size": 0
            }
        }

        self.removed_options = {
            "transfers": (
                "pmqueueddir",
                "autoretry_downloads",
                "shownotification",
                "shownotificationperfolder",
                "prioritize",
                "sharedownloaddir",
                "geopanic",
                "enablebuddyshares",
                "friendsonly",
                "enabletransferbuttons",
                "uselimit",
                "usealtlimits",
                "uploadsinsubdirs",
                "reverseorder",
                "lock",
                "buddysharestrustedonly"
            ),
            "server": (
                "lastportstatuscheck",
                "serverlist",
                "enc",
                "fallbackencodings",
                "roomencoding",
                "userencoding",
                "firewalled"
            ),
            "ui": (
                "enabletrans",
                "mozembed",
                "open_in_mozembed",
                "tooltips",
                "transalpha",
                "transfilter",
                "transtint",
                "soundenabled",
                "soundtheme",
                "soundcommand",
                "tab_colors",
                "tab_icons",
                "searchoffline",
                "chat_hidebuttons",
                "tab_reorderable",
                "private_search_results",
                "private_shares",
                "labelmain",
                "labelrooms",
                "labelprivate",
                "labelinfo",
                "labelbrowse",
                "labelsearch",
                "notexists",
                "roomlistcollapsed",
                "showaway",
                "decimalsep",
                "urgencyhint",
                "tab_status_icons",
                "file_path_tooltips"
            ),
            "columns": (
                "downloads",
                "uploads",
                "search",
                "search_widths",
                "downloads_columns",
                "downloads_widths",
                "uploads_columns",
                "uploads_widths",
                "userbrowse",
                "userbrowse_widths",
                "userlist",
                "userlist_widths",
                "chatrooms",
                "chatrooms_widths",
                "download_columns",
                "download_widths",
                "upload_columns",
                "upload_widths",
                "filesearch_columns",
                "filesearch_widths",
                "hideflags"
            ),
            "searches": (
                "distrib_timer",
                "distrib_ignore",
                "reopen_tabs",
                "max_stored_results",
                "re_filter"
            ),
            "userinfo": (
                "descrutf8"
            ),
            "private_rooms": (
                "enabled"
            ),
            "logging": (
                "logsdir",
                "timestamps"
            ),
            "ticker": (
                "default",
                "rooms",
                "hide"
            ),
            "language": (
                "language",
                "setlanguage"
            ),
            "urls": (
                "urlcatching",
                "humanizeurls"
            ),
            "notifications": (
                "notification_tab_icons"
            ),
            "words": (
                "cycle",
                "onematch",
                "aliases"
            )
        }

        self.create_config_folder()
        self.create_data_folder()

        load_file(self.config_file_path, self.parse_config)

        # Update config values from file
        self.set_config()

        language = self.sections["ui"]["language"]

        if language:
            apply_translations(language)

        from pynicotine.logfacility import log
        log.init_log_levels()
        log.add_debug("Using configuration: %(file)s", {"file": self.config_file_path})

        events.connect("quit", self._quit)

    def parse_config(self, file_path):
        """Parses the config file."""

        with open(encode_path(file_path), "a+", encoding="utf-8") as file_handle:
            file_handle.seek(0)
            self.parser.read_file(file_handle)

    def need_config(self):

        # Check if we have specified a username or password
        if not self.sections["server"]["login"] or not self.sections["server"]["passw"]:
            return True

        return False

    def set_config(self):
        """Set config values parsed from file earlier."""

        from pynicotine.logfacility import log

        for i in self.parser.sections():
            for j, val in self.parser.items(i, raw=True):

                # Check if config section exists in defaults
                if i not in self.defaults and i not in self.removed_options:
                    log.add_debug("Unknown config section '%s'", i)

                # Check if config option exists in defaults
                elif (j not in self.defaults.get(i, {}) and j not in self.removed_options.get(i, {})
                        and i != "plugins" and j != "filter"):
                    log.add_debug("Unknown config option '%(option)s' in section '%(section)s'",
                                  {"option": j, "section": i})

                else:
                    # Attempt to get the default value for a config option. If there's no default
                    # value, it's a custom option from a plugin, so no checks are needed.

                    try:
                        default_val = self.defaults[i][j]

                    except KeyError:
                        try:
                            val = literal_eval(val)
                        except Exception:
                            pass

                        self.sections[i][j] = val
                        continue

                    # Check that the value of a config option is of the same type as the default
                    # value. If that's not the case, reset the value.

                    try:
                        if not isinstance(default_val, str):
                            # Values are always read as strings, evaluate them if they aren't
                            # supposed to remain as strings
                            eval_val = literal_eval(val)

                        else:
                            eval_val = val

                        if i != "plugins" and j != "filter":
                            if (isinstance(eval_val, type(default_val))
                                    or (isinstance(default_val, bool)
                                        and isinstance(eval_val, int) and eval_val in {0, 1})):
                                # Value is valid
                                pass

                            else:
                                raise TypeError("Invalid config value type detected")

                        self.sections[i][j] = eval_val

                    except Exception:
                        # Value was unexpected, reset option
                        self.sections[i][j] = default_val

                        log.add("Config error: Couldn't decode '%s' section '%s' value '%s', value has been reset", (
                            (i[:120] + "…") if len(i) > 120 else i,
                            (j[:120] + "…") if len(j) > 120 else j,
                            (val[:120] + "…") if len(val) > 120 else val
                        ))

        # Add any default options not present in the config file
        for section, options in self.defaults.items():
            if section not in self.sections:
                self.sections[section] = {}

            for option, value in options.items():
                if option in self.sections[section]:
                    continue

                # Migrate download speed limit preference
                if option == "use_download_speed_limit" and section == "transfers":
                    if self.sections[section].get("usealtlimits", False):
                        use_speed_limit = "alternative"

                    elif self.sections[section].get("downloadlimit", 0) > 0:
                        use_speed_limit = "primary"

                    else:
                        use_speed_limit = "unlimited"

                    self.sections[section][option] = use_speed_limit
                    continue

                # Migrate upload speed limit preference
                if option == "use_upload_speed_limit" and section == "transfers":
                    if self.sections[section].get("usealtlimits", False):
                        use_speed_limit = "alternative"

                    elif self.sections[section].get("uselimit", False):
                        use_speed_limit = "primary"

                    else:
                        use_speed_limit = "unlimited"

                    self.sections[section][option] = use_speed_limit
                    continue

                # Set default value
                self.sections[section][option] = value

        # Convert special download folder share to regular share
        if self.sections["transfers"].get("sharedownloaddir", False):
            shares = self.sections["transfers"]["shared"]
            virtual_name = "Downloaded"
            shared_folder = (virtual_name, self.sections["transfers"]["downloaddir"])

            if shared_folder not in shares and virtual_name not in (x[0] for x in shares):
                shares.append(shared_folder)

        # Migrate old trusted buddy shares to new format
        if self.sections["transfers"].get("buddysharestrustedonly", False):
            buddy_shares = self.sections["transfers"]["buddyshared"]

            self.sections["transfers"]["trustedshared"] = buddy_shares[:]
            buddy_shares.clear()

        # Check if server value is valid
        server_addr = self.sections["server"]["server"]

        if (len(server_addr) != 2 or not isinstance(server_addr[0], str) or not isinstance(server_addr[1], int)):
            self.sections["server"]["server"] = self.defaults["server"]["server"]

        # Check if port range value is valid
        port_range = self.sections["server"]["portrange"]

        if (len(port_range) != 2 or not all(isinstance(i, int) for i in port_range)):
            self.sections["server"]["portrange"] = self.defaults["server"]["portrange"]

        self.config_loaded = True

    def write_config_callback(self, file_path):
        self.parser.write(file_path)

    def write_configuration(self):

        if not self.config_loaded:
            return

        # Write new config options to file
        for section, options in self.sections.items():
            if not self.parser.has_section(section):
                self.parser.add_section(section)

            for option, value in options.items():
                if value is None:
                    value = ""

                self.parser.set(section, option, str(value))

        # Remove legacy config options
        for section, options in self.removed_options.items():
            if not self.parser.has_section(section):
                continue

            for option in options:
                self.parser.remove_option(section, option)

        if not self.create_config_folder():
            return

        from pynicotine.logfacility import log

        write_file_and_backup(self.config_file_path, self.write_config_callback, protect=True)
        log.add_debug("Saved configuration: %(file)s", {"file": self.config_file_path})

    def write_config_backup(self, file_path):

        from pynicotine.logfacility import log

        if not file_path.endswith(".tar.bz2"):
            file_path += ".tar.bz2"

        file_path_encoded = encode_path(file_path)

        try:
            if os.path.exists(file_path_encoded):
                raise FileExistsError(f"File {file_path} exists")

            import tarfile
            with tarfile.open(file_path_encoded, "w:bz2") as tar:
                if not os.path.exists(file_path_encoded):
                    raise FileNotFoundError("Config file missing")

                tar.add(self.config_file_path)

        except Exception as error:
            log.add(_("Error backing up config: %s"), error)
            return

        log.add(_("Config backed up to: %s"), file_path)

    def _quit(self):

        self.parser.clear()
        self.sections.clear()
        self.defaults.clear()
        self.removed_options.clear()

        self.config_loaded = False


config = Config()
