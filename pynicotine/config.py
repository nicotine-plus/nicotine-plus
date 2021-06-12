# COPYRIGHT (C) 2020-2021 Nicotine+ Team
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

from pynicotine.logfacility import log


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
        self.version = "3.1.0.dev1"

        self.parser = configparser.ConfigParser(strict=False, interpolation=None)

        log_dir = os.path.join(self.data_dir, "logs")
        self.defaults = {
            "server": {
                "server": ('server.slsknet.org', 2242),
                "login": '',
                "passw": '',
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
                "sharedownloaddir": False,
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
                "geopanic": False,
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
                "chat_room": {},
                "hideflags": False
            },

            "searches": {
                "expand_searches": True,
                "group_searches": "folder_grouping",
                "maxresults": 50,
                "re_filter": False,
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
                "remove_special_chars": True
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
                "notexists": True,
                "tab_default": "",
                "tab_hilite": "#497ec2",
                "tab_changed": "#497ec2",
                "tab_select_previous": True,
                "tab_reorderable": True,
                "tabmain": "Top",
                "tabrooms": "Top",
                "tabprivate": "Top",
                "tabinfo": "Top",
                "tabbrowse": "Top",
                "tabsearch": "Top",
                "tab_status_icons": True,
                "labelmain": 0,
                "labelrooms": 0,
                "labelprivate": 0,
                "labelinfo": 0,
                "labelbrowse": 0,
                "labelsearch": 0,
                "decimalsep": ",",
                "globalfont": "",
                "chatfont": "",
                "roomlistcollapsed": False,
                "tabclosers": True,
                "searchfont": "",
                "listfont": "",
                "browserfont": "",
                "transfersfont": "",
                "last_tab_id": 0,
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
                "showaway": False,
                "buddylistinchatrooms": "tab",
                "trayicon": True,
                "startup_hidden": False,
                "filemanager": "",
                "speechenabled": False,
                "speechprivate": "%(user)s told you.. %(message)s",
                "speechrooms": "In %(room)s, %(user)s said %(message)s",
                "speechcommand": "flite -t $",
                "width": 1000,
                "height": 600,
                "xposition": -1,
                "yposition": -1,
                "maximized": True,
                "urgencyhint": True
            },

            "private_rooms": {
                "rooms": {}
            },

            "urls": {
                "urlcatching": True,
                "protocols": {},
                "humanizeurls": True
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
                "notification_tab_icons": True,
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

        # Windows specific stuff
        if sys.platform == "win32":
            self.defaults['players']['npplayer'] = 'other'

        # Initialize config with default values
        self.sections = defaultdict(dict)

        for key, value in self.defaults.items():
            self.sections[key] = value.copy()

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
            log.add(_("Can't create directory '%(path)s', reported error: %(error)s"), {'path': path, 'error': msg})
            return False

        return True

    def create_data_folder(self):
        """ Create the folder for storing data in (aliases, shared files etc.),
        if the folder doesn't exist """

        try:
            if not os.path.isdir(self.data_dir):
                os.makedirs(self.data_dir)

        except OSError as msg:
            log.add(_("Can't create directory '%(path)s', reported error: %(error)s"), {'path': self.data_dir, 'error': msg})

    def load_config(self):

        self.create_config_folder()
        self.create_data_folder()

        try:
            self.parse_config()

        except UnicodeDecodeError:
            self.convert_config()
            self.parse_config()

        # Clean up old config options
        self.remove_old_options()

        # Update config values from file
        self.set_config()

        # Load command aliases from legacy file
        try:
            if not self.sections["server"]["command_aliases"] and os.path.exists(self.filename + ".alias"):
                with open(self.filename + ".alias", 'rb') as file_handle:
                    from pynicotine.utils import RestrictedUnpickler
                    self.sections["server"]["command_aliases"] = RestrictedUnpickler(file_handle, encoding='utf-8').load()

        except Exception:
            return

    def parse_config(self):
        """ Parses the config file """

        try:
            with open(self.filename, 'a+', encoding="utf-8") as file_handle:
                file_handle.seek(0)
                self.parser.read_file(file_handle)

        except configparser.ParsingError:
            # Ignore parsing errors, the offending lines are removed later
            pass

        except Exception as error:
            # Miscellaneous failure, default config will be used
            log.add(_("Unable to parse config file: %s"), error)

    def convert_config(self):
        """ Converts the config to utf-8.
        Mainly for upgrading Windows build. (22 July, 2020) """

        try:
            from chardet import detect

        except ImportError:
            print("Failed to convert config file to UTF-8. Please install python3-chardet and start Nicotine+ again.")
            sys.exit()

        os.rename(self.filename, self.filename + ".conv")

        with open(self.filename + ".conv", 'rb') as file_handle:
            rawdata = file_handle.read()

        from_encoding = detect(rawdata)['encoding']

        with open(self.filename + ".conv", 'r', encoding=from_encoding) as file_read:
            with open(self.filename, 'w', encoding="utf-8") as file_write:
                for line in file_read:
                    file_write.write(line[:-1] + '\r\n')

        os.remove(self.filename + ".conv")

    def need_config(self):

        # Check if we have specified a username or password
        if not self.sections["server"]["login"] or \
                not self.sections["server"]["passw"]:
            return True

        return False

    def set_config(self):
        """ Set config values parsed from file earlier """

        for i in self.parser.sections():
            for j, val in self.parser.items(i, raw=True):

                # Check if config section exists in defaults
                if i not in self.defaults:
                    log.add(_("Unknown config section '%s'"), i)

                # Check if config option exists in defaults
                elif j not in self.defaults[i] and i != "plugins" and j != "filter":
                    log.add(_("Unknown config option '%(option)s' in section '%(section)s'"), {'option': j, 'section': i})

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
                            if (isinstance(default_val, bool) and isinstance(eval_val, int) and eval_val != 0 and eval_val != 1) or \
                                    (not isinstance(default_val, bool) and type(eval_val) != type(default_val)):

                                raise TypeError("Invalid config value type detected")

                        self.sections[i][j] = eval_val

                    except Exception:
                        # Value was unexpected, reset option
                        self.sections[i][j] = default_val

                        log.add("Config error: Couldn't decode '%s' section '%s' value '%s', value has been reset", (
                            (i[:120] + '..') if len(i) > 120 else i,
                            (j[:120] + '..') if len(j) > 120 else j,
                            (val[:120] + '..') if len(val) > 120 else val
                        )
                        )

        server = self.sections["server"]

        # Check if server value is valid
        if len(server["server"]) != 2 or \
                not isinstance(server["server"][0], str) or \
                not isinstance(server["server"][1], int):

            server["server"] = self.defaults["server"]["server"]

        # Check if port range value is valid
        if len(server["portrange"]) != 2 or \
                not all(isinstance(i, int) for i in server["portrange"]):

            server["portrange"] = self.defaults["server"]["portrange"]

        else:
            # Setting the port range in numerical order
            server["portrange"] = (min(server["portrange"]), max(server["portrange"]))

    def remove_old_options(self):

        # Transition from 1.2.16 -> 1.4.0
        # Do the cleanup early so we don't get the annoying
        # 'Unknown config option ...' message
        self.remove_old_option("transfers", "pmqueueddir")
        self.remove_old_option("server", "lastportstatuscheck")
        self.remove_old_option("server", "serverlist")
        self.remove_old_option("userinfo", "descrutf8")
        self.remove_old_option("ui", "enabletrans")
        self.remove_old_option("ui", "mozembed")
        self.remove_old_option("ui", "open_in_mozembed")
        self.remove_old_option("ui", "tooltips")
        self.remove_old_option("ui", "transalpha")
        self.remove_old_option("ui", "transfilter")
        self.remove_old_option("ui", "transtint")
        self.remove_old_option("language", "language")
        self.remove_old_option("language", "setlanguage")
        self.remove_old_section("language")

        # Transition from 1.4.1 -> 1.4.2
        self.remove_old_option("columns", "downloads")
        self.remove_old_option("columns", "uploads")

        # Remove old encoding settings (1.4.3)
        self.remove_old_option("server", "enc")
        self.remove_old_option("server", "fallbackencodings")
        self.remove_old_option("server", "roomencoding")
        self.remove_old_option("server", "userencoding")

        # Remove soundcommand config, replaced by GSound (1.4.3)
        self.remove_old_option("ui", "soundcommand")

        # Remove old column widths in preparation for "group by folder"-feature
        self.remove_old_option("columns", "search")
        self.remove_old_option("columns", "search_widths")
        self.remove_old_option("columns", "downloads_columns")
        self.remove_old_option("columns", "downloads_widths")
        self.remove_old_option("columns", "uploads_columns")
        self.remove_old_option("columns", "uploads_widths")

        # Remove auto-retry failed downloads-option, this is now default behavior
        self.remove_old_option("transfers", "autoretry_downloads")

        # Remove old notification/sound settings
        self.remove_old_option("transfers", "shownotification")
        self.remove_old_option("transfers", "shownotificationperfolder")
        self.remove_old_option("ui", "soundenabled")
        self.remove_old_option("ui", "soundtheme")
        self.remove_old_option("ui", "tab_colors")
        self.remove_old_option("ui", "tab_icons")

        # Remove dropped offline user text color in search results
        self.remove_old_option("ui", "searchoffline")

        # Seems to be superseded by ("server", "private_chatrooms")
        self.remove_old_option("private_rooms", "enabled")

        # Remove everything ticker-related, no longer necessary after the introduction of room walls
        self.remove_old_section("ticker")

        # Remove old log folder option, superseded by individual log folders for transfers and debug messages
        self.remove_old_option("logging", "logsdir")

        # Remove option to stop responding to searches for a certain time
        self.remove_old_option("searches", "distrib_timer")
        self.remove_old_option("searches", "distrib_ignore")

        # Remove "I can receive direct connections"-option, it's redundant now
        self.remove_old_option("server", "firewalled")

        # Remove old column options
        self.remove_old_option("columns", "userbrowse")
        self.remove_old_option("columns", "userbrowse_widths")
        self.remove_old_option("columns", "userlist")
        self.remove_old_option("columns", "userlist_widths")
        self.remove_old_option("columns", "chatrooms")
        self.remove_old_option("columns", "chatrooms_widths")
        self.remove_old_option("columns", "download_columns")
        self.remove_old_option("columns", "download_widths")
        self.remove_old_option("columns", "upload_columns")
        self.remove_old_option("columns", "upload_widths")
        self.remove_old_option("columns", "filesearch_columns")
        self.remove_old_option("columns", "filesearch_widths")

        # Remove option to prioritize sfv/md5 files when downloading
        self.remove_old_option("transfers", "prioritize")

        # Remove option to reopen closed search tabs when new results come in
        self.remove_old_option("searches", "reopen_tabs")

        # Remove option to toggle chatroom arrow buttons, since they no longer exist
        self.remove_old_option("ui", "chat_hidebuttons")

        # Remove max stored search results, only visible search result limit is used now
        self.remove_old_option("searches", "max_stored_results")

    def remove_old_option(self, section, option):

        if section in self.parser.sections() and option in self.parser.options(section):
            self.parser.remove_option(section, option)

    def remove_old_section(self, section):

        if section in self.parser.sections():
            self.parser.remove_section(section)

    def write_config_callback(self, filename):
        self.parser.write(filename)

    def write_configuration(self):

        for i in self.sections:
            if not self.parser.has_section(i):
                self.parser.add_section(i)

            for j in self.sections[i]:
                self.parser.set(i, j, str(self.sections[i][j]))

        if not self.create_config_folder():
            return

        from pynicotine.utils import write_file_and_backup
        write_file_and_backup(self.filename, self.write_config_callback, protect=True)

    def write_config_backup(self, filename):

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
            print(error)
            return (True, "Cannot write backup archive: %s" % error)

        return (False, filename)


config = Config()
