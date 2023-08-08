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

"""
This module contains configuration classes for Nicotine.
"""

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
    """
    This class holds configuration information and provides the
    following methods:

    need_config() - returns true if configuration information is incomplete
    read_config() - reads configuration information from file
    write_configuration - writes configuration information to file

    The actual configuration information is stored as a two-level dictionary.
    First-level keys are config sections, second-level keys are config
    parameters.
    """

    def __init__(self):

        config_dir, self.data_dir = self.get_user_directories()
        self.filename = os.path.join(config_dir, "config")
        self.version = "3.3.0.dev5"
        self.python_version = sys.version.split()[0]
        self.gtk_version = ""

        self.application_name = "Nicotine+"
        self.application_id = "org.nicotine_plus.Nicotine"
        self.author = "Nicotine+ Team"
        self.copyright = """© 2004–2023 Nicotine+ Contributors
© 2003–2004 Nicotine Contributors
© 2001–2003 PySoulSeek Contributors"""

        self.website_url = "https://nicotine-plus.org"
        self.privileges_url = "https://www.slsknet.org/qtlogin.php?username=%s"
        self.portchecker_url = "https://www.slsknet.org/porttest.php?port=%s"
        self.issue_tracker_url = "https://github.com/nicotine-plus/nicotine-plus/issues"
        self.translations_url = "https://nicotine-plus.org/doc/TRANSLATIONS"

        self.config_loaded = False
        self.parser = configparser.ConfigParser(strict=False, interpolation=None)
        self.sections = defaultdict(dict)
        self.defaults = {}
        self.removed_options = {}

    @staticmethod
    def get_user_directories():
        """ Returns a tuple:
        - the config directory
        - the data directory """

        if sys.platform == "win32":
            try:
                data_dir = os.path.join(os.path.normpath(os.environ["APPDATA"]), "nicotine")
            except KeyError:
                data_dir, _filename = os.path.split(sys.argv[0])

            config_dir = os.path.join(data_dir, "config")
            return config_dir, data_dir

        home = os.path.expanduser("~")
        legacy_dir = os.path.join(home, ".nicotine")

        if os.path.isdir(legacy_dir.encode("utf-8")):
            return legacy_dir, legacy_dir

        def xdg_path(xdg, default):
            path = os.environ.get(xdg)
            path = path.split(":")[0] if path else default

            return os.path.join(path, "nicotine")

        config_dir = xdg_path("XDG_CONFIG_HOME", os.path.join(home, ".config"))
        data_dir = xdg_path("XDG_DATA_HOME", os.path.join(home, ".local", "share"))

        return config_dir, data_dir

    def create_config_folder(self):
        """ Create the folder for storing the config file in, if the folder
        doesn't exist """

        path, _filename = os.path.split(self.filename)

        if not path:
            # Only file name specified, use current folder
            return True

        path_encoded = encode_path(path)

        try:
            if not os.path.isdir(path_encoded):
                os.makedirs(path_encoded)

        except OSError as msg:
            from pynicotine.logfacility import log

            log.add(_("Can't create directory '%(path)s', reported error: %(error)s"),
                    {"path": path, "error": msg})
            return False

        return True

    def create_data_folder(self):
        """ Create the folder for storing data in (shared files etc.),
        if the folder doesn't exist """

        data_dir_encoded = encode_path(self.data_dir)

        try:
            if not os.path.isdir(data_dir_encoded):
                os.makedirs(data_dir_encoded)

        except OSError as msg:
            from pynicotine.logfacility import log

            log.add(_("Can't create directory '%(path)s', reported error: %(error)s"),
                    {"path": self.data_dir, "error": msg})

    def load_config(self):

        log_dir = os.path.join(self.data_dir, "logs")
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
                "incompletedir": os.path.join(self.data_dir, "incomplete"),
                "downloaddir": os.path.join(self.data_dir, "downloads"),
                "uploaddir": os.path.join(self.data_dir, "received"),
                "usernamesubfolders": False,
                "shared": [],
                "buddyshared": [],
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
                "lock": True,
                "reverseorder": False,  # TODO: remove in 3.3.0
                "fifoqueue": False,
                "usecustomban": False,
                "limitby": True,
                "customban": "Banned, don't bother retrying",
                "usecustomgeoblock": False,
                "customgeoblock": "Sorry, your country is blocked",
                "queuelimit": 10000,
                "filelimit": 100,
                "buddysharestrustedonly": False,
                "friendsnolimits": False,
                "groupdownloads": "folder_grouping",
                "groupuploads": "folder_grouping",
                "geoblock": False,
                "geoblockcc": [""],
                "remotedownloads": False,
                "uploadallowed": 3,
                "autoclear_downloads": False,
                "autoclear_uploads": False,
                "uploadsinsubdirs": True,
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
                "cycle": False,  # TODO: remove in 3.3.0
                "dropdown": False,
                "characters": 3,
                "roomnames": False,
                "buddies": True,
                "roomusers": True,
                "commands": True,
                "aliases": True,
                "onematch": False  # TODO: remove in 3.3.0
            },
            "logging": {
                "debug": False,
                "debugmodes": [],
                "debuglogsdir": os.path.join(log_dir, "debug"),
                "logcollapsed": True,
                "transferslogsdir": os.path.join(log_dir, "transfers"),
                "rooms_timestamp": "%H:%M:%S",
                "private_timestamp": "%Y-%m-%d %H:%M:%S",
                "log_timestamp": "%Y-%m-%d %H:%M:%S",
                "privatechat": True,
                "chatrooms": True,
                "transfers": False,
                "debug_file_output": False,
                "roomlogsdir": os.path.join(log_dir, "rooms"),
                "privatelogsdir": os.path.join(log_dir, "private"),
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
                "tab_status_icons": True,
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
                "file_path_tooltips": True,
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
                "usealtlimits"
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
                "exact_file_sizes"  # TODO: remove in 3.3.0 (was only in 3.3.0.dev)
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
            )
        }

        self.create_config_folder()
        self.create_data_folder()

        load_file(self.filename, self.parse_config)

        # Update config values from file
        self.set_config()

        language = self.sections["ui"]["language"]

        if language:
            apply_translations(language)

        from pynicotine.logfacility import log
        log.init_log_levels()
        log.add_debug("Using configuration: %(file)s", {"file": self.filename})

        events.connect("quit", self._quit)

    def parse_config(self, filename):
        """ Parses the config file """

        try:
            with open(encode_path(filename), "a+", encoding="utf-8") as file_handle:
                file_handle.seek(0)
                self.parser.read_file(file_handle)

        except UnicodeDecodeError:
            self.convert_config()
            self.parse_config(filename)

    def convert_config(self):
        """ Converts the config to utf-8.
        Mainly for upgrading Windows build. (22 July, 2020) """

        try:
            from chardet import detect

        except ImportError:
            from pynicotine.logfacility import log

            log.add("Failed to convert config file to UTF-8. Please install python3-chardet and start "
                    "the application again.")
            sys.exit()

        conv_filename = encode_path(f"{self.filename}.conv")
        os.replace(self.filename, conv_filename)

        with open(conv_filename, "rb") as file_handle:
            rawdata = file_handle.read()

        from_encoding = detect(rawdata)["encoding"]

        with open(conv_filename, encoding=from_encoding) as file_read:
            with open(encode_path(self.filename), "w", encoding="utf-8") as file_write:
                for line in file_read:
                    file_write.write(line[:-1] + "\r\n")

        os.remove(conv_filename)

    def need_config(self):

        # Check if we have specified a username or password
        if not self.sections["server"]["login"] or not self.sections["server"]["passw"]:
            return True

        return False

    def set_config(self):
        """ Set config values parsed from file earlier """

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
                    """ Attempt to get the default value for a config option. If there's no default
                    value, it's a custom option from a plugin, so no checks are needed. """

                    try:
                        default_val = self.defaults[i][j]

                    except KeyError:
                        try:
                            val = literal_eval(val)
                        except Exception:
                            pass

                        self.sections[i][j] = val
                        continue

                    """ Check that the value of a config option is of the same type as the default
                    value. If that's not the case, reset the value. """

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
                                        and isinstance(eval_val, int) and eval_val in (0, 1))):
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

                # Migrate file size units (TODO: remove as only in 3.3.0.dev)
                if option == "file_size_unit" and section == "ui":
                    file_size_unit = "B" if self.sections[section].get("exact_file_sizes", False) else ""
                    self.sections[section][option] = file_size_unit
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

        # Check if server value is valid
        server_addr = self.sections["server"]["server"]

        if (len(server_addr) != 2 or not isinstance(server_addr[0], str) or not isinstance(server_addr[1], int)):
            self.sections["server"]["server"] = self.defaults["server"]["server"]

        # Check if port range value is valid
        port_range = self.sections["server"]["portrange"]

        if (len(port_range) != 2 or not all(isinstance(i, int) for i in port_range)):
            self.sections["server"]["portrange"] = self.defaults["server"]["portrange"]

        self.config_loaded = True

    def write_config_callback(self, filename):
        self.parser.write(filename)

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

        write_file_and_backup(self.filename, self.write_config_callback, protect=True)
        log.add_debug("Saved configuration: %(file)s", {"file": self.filename})

    def write_config_backup(self, filename):

        from pynicotine.logfacility import log

        if not filename.endswith(".tar.bz2"):
            filename += ".tar.bz2"

        filename_encoded = encode_path(filename)

        try:
            if os.path.exists(filename_encoded):
                raise FileExistsError(f"File {filename} exists")

            import tarfile
            with tarfile.open(filename_encoded, "w:bz2") as tar:
                if not os.path.exists(filename_encoded):
                    raise FileNotFoundError("Config file missing")

                tar.add(self.filename)

        except Exception as error:
            log.add(_("Error backing up config: %s"), error)
            return

        log.add(_("Config backed up to: %s"), filename)

    def _quit(self):

        self.parser.clear()
        self.sections.clear()
        self.defaults.clear()
        self.removed_options.clear()

        self.config_loaded = False


config = Config()
