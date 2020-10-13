# COPYRIGHT (C) 2020 Nicotine+ Team
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
import pickle
import sys
import time

from ast import literal_eval
from gettext import gettext as _
from os.path import exists

from pynicotine.logfacility import log


class RestrictedUnpickler(pickle.Unpickler):
    """
    Don't allow code execution from pickles
    """

    def find_class(self, module, name):
        # Forbid all globals
        raise pickle.UnpicklingError("global '%s.%s' is forbidden" %
                                     (module, name))


class Config:
    """
    This class holds configuration information and provides the
    following methods:

    need_config() - returns true if configuration information is incomplete
    read_config() - reads configuration information from file
    setConfig(config_info_dict) - sets configuration information
    write_configuration - writes configuration information to file
    write_download_queue - writes download queue to file

    The actual configuration information is stored as a two-level dictionary.
    First-level keys are config sections, second-level keys are config
    parameters.
    """

    def __init__(self, filename, data_dir):

        self.filename = filename
        self.data_dir = data_dir
        self.parser = configparser.RawConfigParser()

        try:
            self.parser.read([self.filename], encoding="utf-8")
        except UnicodeDecodeError:
            self.convert_config()
            self.parser.read([self.filename], encoding="utf-8")

        log_dir = os.path.join(data_dir, "logs")

        self.sections = {
            "server": {
                "server": ('server.slsknet.org', 2242),
                "login": '',
                "passw": '',
                "firewalled": False,
                "ctcpmsgs": False,
                "autosearch": [],
                "autoreply": "",
                "portrange": (2234, 2239),
                "upnp": True,
                "userlist": [],
                "banlist": [],
                "ignorelist": [],
                "ipignorelist": {},
                "ipblocklist": {},
                "autojoin": ["nicotine"],
                "autoaway": 15,
                "private_chatrooms": False
            },

            "transfers": {
                "incompletedir": os.path.join(data_dir, 'incompletefiles'),
                "downloaddir": os.path.join(os.path.expanduser("~"), 'nicotine-downloads'),
                "uploaddir": os.path.join(os.path.expanduser("~"), 'nicotine-uploads'),
                "sharedownloaddir": False,
                "shared": [],
                "buddyshared": [],
                "uploadbandwidth": 10,
                "uselimit": False,
                "uploadlimit": 150,
                "downloadlimit": 0,
                "preferfriends": False,
                "useupslots": False,
                "uploadslots": 2,
                "afterfinish": "",
                "afterfolder": "",
                "lock": True,
                "reverseorder": False,
                "prioritize": False,
                "fifoqueue": False,
                "usecustomban": False,
                "limitby": True,
                "customban": "Banned, don't bother retrying",
                "queuelimit": 10000,
                "filelimit": 1000,
                "friendsonly": False,
                "friendsnolimits": False,
                "enablebuddyshares": False,
                "enabletransferbuttons": True,
                "groupdownloads": True,
                "groupuploads": True,
                "geoblock": False,
                "geopanic": False,
                "geoblockcc": [""],
                "remotedownloads": True,
                "uploadallowed": 2,
                "autoclear_downloads": False,
                "autoclear_uploads": False,
                "downloads": [],
                "sharedfiles": {},
                "sharedfilesstreams": {},
                "uploadsinsubdirs": True,
                "wordindex": {},
                "fileindex": {},
                "sharedmtimes": {},
                "bsharedfiles": {},
                "bsharedfilesstreams": {},
                "bwordindex": {},
                "bfileindex": {},
                "bsharedmtimes": {},
                "rescanonstartup": 0,
                "enablefilters": True,
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
                "dropdown": True,
                "characters": 2,
                "roomnames": True,
                "buddies": True,
                "roomusers": True,
                "commands": True,
                "aliases": True,
                "onematch": True
            },

            "logging": {
                "debug": False,
                "debugmodes": [0, 1],
                "debuglogsdir": os.path.join(log_dir, "debug"),
                "logcollapsed": False,
                "transferslogsdir": os.path.join(log_dir, "transfers"),
                "rooms_timestamp": "%H:%M:%S",
                "private_timestamp": "%Y-%m-%d %H:%M:%S",
                "log_timestamp": "%Y-%m-%d %H:%M:%S",
                "timestamps": True,
                "privatechat": False,
                "chatrooms": False,
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
                "store": False,
                "users": []
            },

            "columns": {
                "userbrowse": [1, 1, 1, 1],
                "userbrowse_widths": [600, 100, 70, 0],
                "userlist": [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
                "userlist_widths": [0, 25, 180, 0, 0, 0, 0, 0, 160, 0],
                "chatrooms": {},
                "chatrooms_widths": {},
                "download_columns": [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
                "download_widths": [200, 250, 250, 140, 50, 70, 170, 90, 140, 0],
                "upload_columns": [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
                "upload_widths": [200, 250, 250, 140, 50, 70, 170, 90, 140, 0],
                "filesearch_columns": [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
                "filesearch_widths": [50, 200, 25, 50, 90, 90, 400, 400, 100, 100, 0],
                "hideflags": False
            },

            "searches": {
                "expand_searches": True,
                "group_searches": 1,
                "maxresults": 50,
                "re_filter": False,
                "history": [],
                "enablefilters": False,
                "defilter": ["", "", "", "", 0, ""],
                "filtercc": [],
                "reopen_tabs": False,
                "filterin": [],
                "filterout": [],
                "filtersize": [],
                "filterbr": [],
                "distrib_timer": False,
                "distrib_ignore": 60,
                "search_results": True,
                "max_displayed_results": 1000,
                "max_stored_results": 1500,
                "min_search_chars": 3,
                "remove_special_chars": True
            },

            "ui": {
                "dark_mode": False,
                "icontheme": "",
                "chatme": "FOREST GREEN",
                "chatremote": "",
                "chatlocal": "BLUE",
                "chathilite": "red",
                "urlcolor": "#3D2B7F",
                "useronline": "BLACK",
                "useraway": "ORANGE",
                "useroffline": "#aa0000",
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
                "tab_hilite": "red",
                "tab_changed": "#0000ff",
                "tab_select_previous": True,
                "tab_reorderable": True,
                "tabmain": "Top",
                "tabrooms": "Top",
                "tabprivate": "Top",
                "tabinfo": "Top",
                "tabbrowse": "Top",
                "tabsearch": "Top",
                "tab_status_icons": True,
                "chat_hidebuttons": False,
                "labelmain": 0,
                "labelrooms": 0,
                "labelprivate": 0,
                "labelinfo": 0,
                "labelbrowse": 0,
                "labelsearch": 0,
                "decimalsep": ",",
                "chatfont": "",
                "roomlistcollapsed": False,
                "tabclosers": True,
                "searchfont": "",
                "listfont": "",
                "browserfont": "",
                "transfersfont": "",
                "last_tab_id": 0,
                "modes_visible": {
                    "chatrooms": 1,
                    "private": 1,
                    "downloads": 1,
                    "uploads": 1,
                    "search": 1,
                    "userinfo": 1,
                    "userbrowse": 1,
                    "interests": 1
                },
                "modes_order": [
                    "chatrooms",
                    "private",
                    "downloads",
                    "uploads",
                    "search",
                    "userinfo",
                    "userbrowse",
                    "interests",
                    "userlist"
                ],
                "showaway": False,
                "buddylistinchatrooms": 0,
                "trayicon": True,
                "filemanager": "xdg-open $",
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
                "default": "xdg-open $",
                "npothercommand": "",
                "npplayer": "",
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
            }
        }

        # Windows specific stuff
        if sys.platform.startswith('win'):
            self.sections['ui']['filemanager'] = 'explorer $'

        self.defaults = {}
        for key, value in self.sections.items():
            if isinstance(value, dict):
                if key not in self.defaults:
                    self.defaults[key] = {}

                for key2, value2 in value.items():
                    self.defaults[key][key2] = value2
            else:
                self.defaults[key] = value

        try:
            f = open(filename + ".alias", 'rb')
            self.aliases = RestrictedUnpickler(f).load()
            f.close()
        except Exception:
            self.aliases = {}

    def convert_config(self):
        """ Converts the config to utf-8.
        Mainly for upgrading Windows build. (22 July, 2020) """

        try:
            from chardet import detect
        except ImportError:
            print("Failed to convert config file to UTF-8. Please install python3-chardet and start Nicotine+ again.")
            sys.exit()

        os.rename(self.filename, self.filename + ".conv")

        with open(self.filename + ".conv", 'rb') as f:
            rawdata = f.read()

        from_encoding = detect(rawdata)['encoding']

        with open(self.filename + ".conv", 'r', encoding=from_encoding) as fr:
            with open(self.filename, 'w', encoding="utf-8") as fw:
                for line in fr:
                    fw.write(line[:-1] + '\r\n')

        os.remove(self.filename + ".conv")

    def need_config(self):

        errorlevel = 0

        try:
            for i in self.sections:
                for j in self.sections[i]:

                    if not isinstance(self.sections[i][j], (type(None), type(""))):
                        continue

                    if self.sections[i][j] is None or self.sections[i][j] == '' \
                       and i not in ("userinfo", "ui", "players") \
                       and j not in ("incompletedir", "autoreply", 'afterfinish', 'afterfolder', 'geoblockcc', 'downloadregexp'):

                        # Repair options set to None with defaults
                        if self.sections[i][j] is None and self.defaults[i][j] is not None:

                            self.sections[i][j] = self.defaults[i][j]
                            log.add(
                                _("Config option reset to default: Section: %(section)s, Option: %(option)s, to: %(default)s"), {
                                    'section': i,
                                    'option': j,
                                    'default': self.sections[i][j]
                                }
                            )

                            if errorlevel == 0:
                                errorlevel = 1
                        else:

                            if errorlevel < 2:
                                log.add(_("You need to configure your settings (Server, Username, Password, Download Directory) before connecting..."))
                                errorlevel = 2

        except Exception as error:
            log.add(_("Config error: %s"), error)
            if errorlevel < 3:
                errorlevel = 3

        return errorlevel

    def read_config(self):

        self.sections['transfers']['downloads'] = []

        if exists(os.path.join(self.data_dir, 'transfers.pickle')):
            # <1.2.13 stored transfers inside the main config
            try:
                handle = open(os.path.join(self.data_dir, 'transfers.pickle'), 'rb')
            except IOError as inst:
                log.add_warning(_("Something went wrong while opening your transfer list: %(error)s"), {'error': str(inst)})
            else:
                try:
                    self.sections['transfers']['downloads'] = RestrictedUnpickler(handle).load()
                except Exception as inst:
                    log.add_warning(_("Something went wrong while reading your transfer list: %(error)s"), {'error': str(inst)})
            try:
                handle.close()
            except Exception:
                pass

        path, fn = os.path.split(self.filename)
        try:
            if not os.path.isdir(path):
                os.makedirs(path)
        except OSError as msg:
            log.add_warning("Can't create directory '%s', reported error: %s", (path, msg))

        try:
            if not os.path.isdir(self.data_dir):
                os.makedirs(self.data_dir)
        except OSError as msg:
            log.add_warning("Can't create directory '%s', reported error: %s", (path, msg))

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

        # Checking for unknown section/options
        unknown1 = [
            'login', 'passw', 'enc', 'downloaddir', 'uploaddir', 'customban',
            'descr', 'pic', 'transferslogsdir', 'roomlogsdir', 'privatelogsdir',
            'incompletedir', 'autoreply', 'afterfinish', 'downloadregexp',
            'afterfolder', 'default', 'chatfont', 'npothercommand', 'npplayer',
            'npformat', 'private_timestamp', 'rooms_timestamp', 'log_timestamp',
            'debuglogsdir'
        ]

        unknown2 = {
            'ui': [
                "roomlistcollapsed", "tab_select_previous", "tabclosers",
                "tab_colors", "tab_reorderable", "buddylistinchatrooms", "trayicon",
                "showaway", "usernamehotspots", "exitdialog",
                "tab_icons", "spellcheck", "modes_order", "modes_visible",
                "chat_hidebuttons", "tab_status_icons", "notexists",
                "speechenabled", "enablefilters", "width",
                "height", "xposition", "yposition", "labelmain", "labelrooms",
                "labelprivate", "labelinfo", "labelbrowse", "labelsearch", "maximized",
                "dark_mode"
            ],
            'words': [
                "completion", "censorwords", "replacewords", "autoreplaced",
                "censored", "characters", "tab", "cycle", "dropdown",
                "roomnames", "buddies", "roomusers", "commands",
                "aliases", "onematch"
            ]
        }

        for i in self.parser.sections():
            for j in self.parser.options(i):
                val = self.parser.get(i, j, raw=1)
                if i not in self.sections:
                    log.add_warning(_("Unknown config section '%s'"), i)
                elif j not in self.sections[i] and not (j == "filter" or i in ('plugins',)):
                    log.add_warning(_("Unknown config option '%(option)s' in section '%(section)s'"), {'option': j, 'section': i})
                elif j in unknown1 or (i in unknown2 and j not in unknown2[i]):
                    if val is not None and val != "None":
                        self.sections[i][j] = val
                    else:
                        self.sections[i][j] = None
                else:
                    try:
                        self.sections[i][j] = literal_eval(val)
                    except Exception:
                        self.sections[i][j] = None
                        log.add_warning("CONFIG ERROR: Couldn't decode '%s' section '%s' value '%s'", (str(j), str(i), str(val)))

        # Setting the port range in numerical order
        self.sections["server"]["portrange"] = (min(self.sections["server"]["portrange"]), max(self.sections["server"]["portrange"]))

    def remove_old_option(self, section, option):
        if section in self.parser.sections() and option in self.parser.options(section):
            self.parser.remove_option(section, option)

    def remove_old_section(self, section):
        if section in self.parser.sections():
            self.parser.remove_section(section)

    def write_download_queue(self):

        realfile = os.path.join(self.data_dir, 'transfers.pickle')
        tmpfile = realfile + '.tmp'
        backupfile = realfile + ' .backup'
        try:
            handle = open(tmpfile, 'wb')
        except Exception as inst:
            log.add_warning(_("Something went wrong while opening your transfer list: %(error)s"), {'error': str(inst)})
        else:
            try:
                pickle.dump(self.sections['transfers']['downloads'], handle, protocol=pickle.HIGHEST_PROTOCOL)
                handle.close()
                try:
                    # Please let it be atomic...
                    os.rename(tmpfile, realfile)
                except Exception:
                    # ...ugh. Okay, how about...
                    try:
                        os.unlink(backupfile)
                    except Exception:
                        pass
                    os.rename(realfile, backupfile)
                    os.rename(tmpfile, realfile)
            except Exception as inst:
                log.add_warning(_("Something went wrong while writing your transfer list: %(error)s"), {'error': str(inst)})
        finally:
            try:
                handle.close()
            except Exception:
                pass

    def write_configuration(self):

        external_sections = [
            "sharedfiles", "sharedfilesstreams", "wordindex", "fileindex",
            "sharedmtimes", "bsharedfiles", "bsharedfilesstreams",
            "bwordindex", "bfileindex", "bsharedmtimes", "downloads"
        ]

        for i in self.sections:
            if not self.parser.has_section(i):
                self.parser.add_section(i)
            for j in self.sections[i]:
                if j not in external_sections:
                    self.parser.set(i, j, self.sections[i][j])
                else:
                    self.parser.remove_option(i, j)

        path, fn = os.path.split(self.filename)
        try:
            if not os.path.isdir(path):
                os.makedirs(path)
        except OSError as msg:
            log.add_warning(_("Can't create directory '%(path)s', reported error: %(error)s"), {'path': path, 'error': msg})

        oldumask = os.umask(0o077)

        try:
            f = open(self.filename + ".new", "w", encoding="utf-8")
        except IOError as e:
            log.add_warning(_("Can't save config file, I/O error: %s"), e)
            return
        else:
            try:
                self.parser.write(f)
            except IOError as e:
                log.add_warning(_("Can't save config file, I/O error: %s"), e)
                return
            else:
                f.close()

        os.umask(oldumask)

        # A paranoid precaution since config contains the password
        try:
            os.chmod(self.filename, 0o600)
        except Exception:
            pass

        try:
            s = os.stat(self.filename)
            if s.st_size > 0:
                try:
                    if os.path.exists(self.filename + ".old"):
                        os.remove(self.filename + ".old")
                except OSError:
                    log.add_warning(_("Can't remove %s", self.filename + ".old"))
                try:
                    os.rename(self.filename, self.filename + ".old")
                except OSError as error:
                    log.add_warning(_("Can't back config file up, error: %s"), error)
        except OSError:
            pass

        try:
            os.rename(self.filename + ".new", self.filename)
        except OSError as error:
            log.add_warning(_("Can't rename config file, error: %s"), error)

    def write_config_backup(self, filename=None):

        if filename is None:
            filename = "%s backup %s.tar.bz2", (self.filename, time.strftime("%Y-%m-%d %H:%M:%S"))
        else:
            if filename[-8:-1] != ".tar.bz2":
                filename += ".tar.bz2"
        try:
            if os.path.exists(filename):
                raise FileExistsError("File %s exists", filename)

            import tarfile
            tar = tarfile.open(filename, "w:bz2")

            if not os.path.exists(self.filename):
                raise FileNotFoundError("Config file missing")

            tar.add(self.filename)

            if os.path.exists(self.filename + ".alias"):
                tar.add(self.filename + ".alias")

            tar.close()
        except Exception as e:
            print(e)
            return (1, "Cannot write backup archive: %s", e)

        return (0, filename)

    def write_aliases(self):

        try:
            f = open(self.filename + ".alias", "wb")
        except Exception as e:
            log.add_warning(_("Something went wrong while opening your alias file: %s"), e)
        else:
            try:
                pickle.dump(self.aliases, f, protocol=pickle.HIGHEST_PROTOCOL)
                f.close()
            except Exception as e:
                log.add_warning(_("Something went wrong while saving your alias file: %s"), e)
        finally:
            try:
                f.close()
            except Exception:
                pass

    def add_alias(self, rest):
        if rest:
            args = rest.split(" ", 1)
            if len(args) == 2:
                if args[0] in ("alias", "unalias"):
                    return "I will not alias that!\n"
                self.aliases[args[0]] = args[1]
                self.write_aliases()
            if args[0] in self.aliases:
                return "Alias %s: %s\n" % (args[0], self.aliases[args[0]])
            else:
                return _("No such alias (%s)") % rest + "\n"
        else:
            m = "\n" + _("Aliases:") + "\n"
            for (key, value) in self.aliases.items():
                m = m + "%s: %s\n" % (key, value)
            return m + "\n"

    def unalias(self, rest):
        if rest and rest in self.aliases:
            x = self.aliases[rest]
            del self.aliases[rest]
            self.write_aliases()
            return _("Removed alias %(alias)s: %(action)s\n") % {'alias': rest, 'action': x}
        else:
            return _("No such alias (%(alias)s)\n") % {'alias': rest}
