# COPYRIGHT (C) 2020-2022 Nicotine+ Team
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2016-2018 Mutnick <mutnick@techie.com>
# COPYRIGHT (C) 2008-2011 Quinox <quinox@users.sf.net>
# COPYRIGHT (C) 2009 Hedonist <ak@sensi.org>
# COPYRIGHT (C) 2007 Gallows <g4ll0ws@gmail.com>
# COPYRIGHT (C) 2006-2009 Daelstorm <daelstorm@gmail.com>
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
        self.plugin_dir = os.path.join(self.data_dir, "plugins")
        self.version = "3.2.1.rc2"
        self.python_version = sys.version
        self.gtk_version = ""

        self.application_name = "Nicotine+"
        self.application_id = "org.nicotine_plus.Nicotine"
        self.summary = _("Graphical client for the Soulseek peer-to-peer network")
        self.copyright = """© 2004–2022 Nicotine+ Team
© 2003–2004 Nicotine Team
© 2001–2003 PySoulSeek Contributors"""

        self.website_url = "https://nicotine-plus.org/"
        self.privileges_url = "https://www.slsknet.org/userlogin.php?username=%s"
        self.portchecker_url = "http://tools.slsknet.org/porttest.php?port=%s"
        self.issue_tracker_url = "https://github.com/nicotine-plus/nicotine-plus/issues"
        self.translations_url = "https://nicotine-plus.org/doc/TRANSLATIONS"

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
                data_dir = os.path.join(os.environ['APPDATA'], 'nicotine')
            except KeyError:
                data_dir, _filename = os.path.split(sys.argv[0])

            config_dir = os.path.join(data_dir, "config")
            return config_dir, data_dir

        home = os.path.expanduser("~")

        legacy_dir = os.path.join(home, '.nicotine')

        if os.path.isdir(legacy_dir):
            return legacy_dir, legacy_dir

        def xdg_path(xdg, default):
            path = os.environ.get(xdg)

            path = path.split(':')[0] if path else default

            return os.path.join(path, 'nicotine')

        config_dir = xdg_path('XDG_CONFIG_HOME', os.path.join(home, '.config'))
        data_dir = xdg_path('XDG_DATA_HOME', os.path.join(home, '.local', 'share'))

        return config_dir, data_dir

    def create_config_folder(self):
        """ Create the folder for storing the config file in, if the folder
        doesn't exist """

        path, _filename = os.path.split(self.filename)

        if not path:
            # Only file name specified, use current folder
            return True

        try:
            if not os.path.isdir(path):
                os.makedirs(path)

        except OSError as msg:
            from pynicotine.logfacility import log

            log.add(_("Can't create directory '%(path)s', reported error: %(error)s"),
                    {'path': path, 'error': msg})
            return False

        return True

    def create_data_folder(self):
        """ Create the folder for storing data in (aliases, shared files etc.),
        if the folder doesn't exist """

        try:
            if not os.path.isdir(self.data_dir):
                os.makedirs(self.data_dir)

        except OSError as msg:
            from pynicotine.logfacility import log

            log.add(_("Can't create directory '%(path)s', reported error: %(error)s"),
                    {'path': self.data_dir, 'error': msg})

    def load_config(self):

        from pynicotine.utils import load_file

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
                "portrange": (2234, 2239),
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
                "incompletedir": os.path.join(self.data_dir, 'incomplete'),
                "downloaddir": os.path.join(self.data_dir, 'downloads'),
                "uploaddir": os.path.join(self.data_dir, 'received'),
                "usernamesubfolders": False,
                "shared": [],
                "buddyshared": [],
                "uploadbandwidth": 10,
                "uselimit": False,
                "usealtlimits": False,
                "uploadlimit": 1000,
                "uploadlimitalt": 100,
                "downloadlimit": 0,
                "downloadlimitalt": 100,
                "preferfriends": False,
                "useupslots": False,
                "uploadslots": 2,
                "afterfinish": "",
                "afterfolder": "",
                "lock": True,
                "reverseorder": False,
                "fifoqueue": False,
                "usecustomban": False,
                "limitby": True,
                "customban": "Banned, don't bother retrying",
                "usecustomgeoblock": False,
                "customgeoblock": "Sorry, your country is blocked",
                "queuelimit": 10000,
                "filelimit": 100,
                "friendsonly": False,
                "buddysharestrustedonly": False,
                "friendsnolimits": False,
                "enablebuddyshares": False,
                "enabletransferbuttons": True,
                "groupdownloads": "folder_grouping",
                "groupuploads": "folder_grouping",
                "geoblock": False,
                "geoblockcc": [""],
                "remotedownloads": True,
                "uploadallowed": 2,
                "autoclear_downloads": False,
                "autoclear_uploads": False,
                "uploadsinsubdirs": True,
                "rescanonstartup": True,
                "enablefilters": False,
                "downloadregexp": "",
                "downloadfilters": [
                    ["desktop.ini", 1],
                    ["folder.jpg", 1],
                    ["*.url", 1],
                    ["thumbs.db", 1],
                    ["albumart(_{........-....-....-....-............}_)?(_?(large|small))?\\.jpg", 0]
                ],
                "download_doubleclick": 1,
                "upload_doubleclick": 1,
                "downloadsexpanded": True,
                "uploadsexpanded": True
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
                "cycle": False,
                "dropdown": False,
                "characters": 3,
                "roomnames": True,
                "buddies": True,
                "roomusers": True,
                "commands": True,
                "aliases": True,
                "onematch": False
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
                "timestamps": True,
                "privatechat": True,
                "chatrooms": True,
                "transfers": False,
                "debug_file_output": False,
                "roomlogsdir": os.path.join(log_dir, "rooms"),
                "privatelogsdir": os.path.join(log_dir, "private"),
                "readroomlogs": True,
                "readroomlines": 15,
                "readprivatelines": 15,
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
                "maxresults": 50,
                "enable_history": True,
                "history": [],
                "enablefilters": False,
                "filters_visible": False,
                "defilter": ["", "", "", "", 0, ""],
                "filtercc": [],
                "filterin": [],
                "filterout": [],
                "filtersize": [],
                "filterbr": [],
                "filtertype": [],
                "search_results": True,
                "max_displayed_results": 1500,
                "min_search_chars": 3,
                "remove_special_chars": True,
                "private_search_results": True
            },
            "ui": {
                "dark_mode": False,
                "header_bar": True,
                "icontheme": "",
                "chatme": "#908e8b",
                "chatremote": "",
                "chatlocal": "",
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
                "width": 1000,
                "height": 600,
                "xposition": -1,
                "yposition": -1,
                "maximized": True,
                "urgencyhint": True,
                "file_path_tooltips": True,
                "reverse_file_paths": True
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
                "notification_popup_chatroom_mention": True
            },
            "plugins": {
                "enable": True,
                "enabled": []
            },
            "statistics": {
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
                "geopanic"
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
                "decimalsep"
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
                "logsdir"
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

        # Windows specific stuff
        if sys.platform == "win32":
            self.defaults['players']['npplayer'] = 'other'

        # Initialize config with default values
        for key, value in self.defaults.items():
            self.sections[key] = value.copy()

        self.create_config_folder()
        self.create_data_folder()

        load_file(self.filename, self.parse_config)

        # Update config values from file
        self.set_config()

        if sys.platform == "darwin":
            # Disable header bar in macOS for now due to GTK 3 performance issues
            self.sections["ui"]["header_bar"] = False

        # Convert special download folder share to regular share
        if self.sections["transfers"].get("sharedownloaddir", False):
            shares = self.sections["transfers"]["shared"]
            virtual_name = "Downloaded"
            shared_folder = (virtual_name, self.sections["transfers"]["downloaddir"])

            if shared_folder not in shares and virtual_name not in (x[0] for x in shares):
                shares.append(shared_folder)

        # Load command aliases from legacy file
        try:
            if not self.sections["server"]["command_aliases"] and os.path.exists(self.filename + ".alias"):
                with open(self.filename + ".alias", 'rb') as file_handle:
                    from pynicotine.utils import RestrictedUnpickler
                    self.sections["server"]["command_aliases"] = RestrictedUnpickler(
                        file_handle, encoding='utf-8').load()

        except Exception:
            return

    def parse_config(self, filename):
        """ Parses the config file """

        try:
            with open(filename, 'a+', encoding="utf-8") as file_handle:
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

        os.rename(self.filename, self.filename + ".conv")

        with open(self.filename + ".conv", 'rb') as file_handle:
            rawdata = file_handle.read()

        from_encoding = detect(rawdata)['encoding']

        with open(self.filename + ".conv", encoding=from_encoding) as file_read:
            with open(self.filename, 'w', encoding="utf-8") as file_write:
                for line in file_read:
                    file_write.write(line[:-1] + '\r\n')

        os.remove(self.filename + ".conv")

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
                    log.add(_("Unknown config section '%s'"), i)

                # Check if config option exists in defaults
                elif (j not in self.defaults.get(i, "") and j not in self.removed_options.get(i, "")
                        and i != "plugins" and j != "filter"):
                    log.add(_("Unknown config option '%(option)s' in section '%(section)s'"),
                            {'option': j, 'section': i})

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
                            (i[:120] + '..') if len(i) > 120 else i,
                            (j[:120] + '..') if len(j) > 120 else j,
                            (val[:120] + '..') if len(val) > 120 else val
                        ))

        server = self.sections["server"]

        # Check if server value is valid
        if (len(server["server"]) != 2
                or not isinstance(server["server"][0], str)
                or not isinstance(server["server"][1], int)):

            server["server"] = self.defaults["server"]["server"]

        # Check if port range value is valid
        if (len(server["portrange"]) != 2
                or not all(isinstance(i, int) for i in server["portrange"])):

            server["portrange"] = self.defaults["server"]["portrange"]

        else:
            # Setting the port range in numerical order
            server["portrange"] = (min(server["portrange"]), max(server["portrange"]))

    def write_config_callback(self, filename):
        self.parser.write(filename)

    def write_configuration(self):

        # Write new config options to file
        for section, options in self.sections.items():
            if not self.parser.has_section(section):
                self.parser.add_section(section)

            for option, value in options.items():
                self.parser.set(section, option, str(value))

        # Remove legacy config options
        for section, options in self.removed_options.items():
            if not self.parser.has_section(section):
                continue

            for option in options:
                self.parser.remove_option(section, option)

        if not self.create_config_folder():
            return

        from pynicotine.utils import write_file_and_backup
        write_file_and_backup(self.filename, self.write_config_callback, protect=True)

    def write_config_backup(self, filename):

        from pynicotine.logfacility import log

        if not filename.endswith(".tar.bz2"):
            filename += ".tar.bz2"

        try:
            if os.path.exists(filename):
                raise FileExistsError("File %s exists" % filename)

            import tarfile
            with tarfile.open(filename, "w:bz2") as tar:
                if not os.path.exists(self.filename):
                    raise FileNotFoundError("Config file missing")

                tar.add(self.filename)

        except Exception as error:
            log.add(_("Error backing up config: %s"), error)
            return

        log.add(_("Config backed up to: %s"), filename)


config = Config()
