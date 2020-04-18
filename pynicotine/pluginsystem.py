# -*- coding: utf-8 -*-
#
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2016 Mutnick <muhing@yahoo.com>
# COPYRIGHT (C) 2008-2011 Quinox <quinox@users.sf.net>
# COPYRIGHT (C) 2009 Daelstorm <daelstorm@gmail.com>
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

import imp
import os
import shutil
import sys
import tarfile
from gettext import gettext as _
from time import time
from traceback import extract_stack
from traceback import extract_tb
from traceback import format_list
from traceback import print_exc

import gi
from gi.repository import GObject as gobject

from _thread import start_new_thread
from pynicotine.logfacility import log
from pynicotine.pynicotine import slskmessages
from pynicotine.slskmessages import ToBeEncoded

gi.require_version('Gtk', '3.0')


WIN32 = sys.platform.startswith("win")


returncode = {
    'break': 0,  # don't give other plugins the event, do let n+ process it
    'zap': 1,    # don't give other plugins the event, don't let n+ process it
    'pass': 2    # do give other plugins the event, do let n+ process it
}                # returning nothing is the same as 'pass'

tupletype = type(('', ''))


def cast_to_unicode_if_needed(text, logfunc):
    if isinstance(text, str):
        return text
    try:
        better = str.decode(text, 'utf8')
        logfunc("Plugin problem: casting '%s' to unicode!" % repr(text))
        return better
    except UnicodeError:
        better = str.decode(text, 'utf8', 'replace')
        logfunc("Plugin problem: casting '%s' to unicode, losing characters in the process." % repr(text))
        return better
    except Exception:
        logfunc("Plugin problem: failed to completely cast '%s', you're on your own from here on." % repr(text))
        return text


class InvalidPluginError(Exception):
    pass


class PluginHandler(object):

    frame = None  # static variable... but should it be?
    guiqueue = []  # fifo isn't supported by older python

    def __init__(self, frame, plugindir):
        self.frame = frame
        log.add(_("Loading plugin handler"))
        self.myUsername = self.frame.np.config.sections["server"]["login"]
        self.plugindirs = []
        self.enabled_plugins = {}
        self.loaded_plugins = {}
        self.type2cast = {
            'integer': int,
            'int': int,
            'float': float,
            'string': str,
            'str': str
        }

        try:
            os.makedirs(plugindir)
        except Exception:
            pass

        self.plugindirs.append(plugindir)

        if os.path.isdir(plugindir):
            # self.load_directory(self.plugindir)
            self.load_enabled()
        else:
            log.add(_("It appears '%s' is not a directory, not loading plugins.") % plugindir)

    def __findplugin(self, pluginname):
        for directory in self.plugindirs:
            fullpath = os.path.join(directory, pluginname)
            if os.path.exists(fullpath):
                return fullpath
        return None

    def toggle_plugin(self, pluginname):
        on = pluginname in self.enabled_plugins
        if on:
            self.disable_plugin(pluginname)
        else:
            self.enable_plugin(pluginname)

    def load_plugin(self, pluginname):
        path = self.__findplugin(pluginname)
        if path is None:
            log.add(_("Failed to load plugin '%s', could not find it.") % pluginname)
            return False
        sys.path.insert(0, path)
        plugin = imp.load_source(pluginname, os.path.join(path, '__init__.py'))
        instance = plugin.Plugin(self)
        self.plugin_settings(instance)
        instance.LoadNotification()
        # log.add("Loaded plugin %s (version %s) from %s" % (instance.__name__, instance.__version__, modulename))
        # self.plugins.append((module, instance))
        sys.path = sys.path[1:]
        self.loaded_plugins[pluginname] = plugin
        return plugin

    def install_plugin(self, path):
        try:
            tar = tarfile.open(path, "r:*")  # transparently supports gz, bz2
        except (tarfile.ReadError, OSError):
            raise InvalidPluginError(_('Plugin archive is not in the correct format'))

        # ensure the paths in the archive are sane
        mems = tar.getmembers()
        base = os.path.basename(path)[:-4]
        if os.path.isdir(os.path.join(self.plugindirs[0], base)):
            raise InvalidPluginError(_('A plugin with the name "%s" is '
                                       'already installed') % base)

        for m in mems:
            if not m.name.startswith(base):
                raise InvalidPluginError(_("Plugin archive contains an unsafe path"))

        tar.extractall(self.plugindirs[0])

    def uninstall_plugin(self, pluginname):
        self.disable_plugin(pluginname)
        for dir in self.plugindirs:
            try:
                shutil.rmtree(self.__findplugin(pluginname))
                return True
            except Exception:
                pass
        return False

    def enable_plugin(self, pluginname):
        if pluginname in self.enabled_plugins:
            return
        try:
            plugin = self.load_plugin(pluginname)
            if not plugin:
                raise Exception("Error loading plugin '%s'" % pluginname)
            plugin.enable(self)
            self.enabled_plugins[pluginname] = plugin
            log.add(_("Enabled plugin %s") % plugin.PLUGIN.__name__)
        except Exception:
            print_exc()
            log.addwarning(_("Unable to enable plugin %s") % pluginname)
            # common.log_exception(logger)
            return False
        return True

    def list_installed_plugins(self):
        pluginlist = []
        for dir in self.plugindirs:
            if os.path.exists(dir):
                for file in os.listdir(dir):
                    if file not in pluginlist and os.path.isdir(os.path.join(dir, file)):
                        pluginlist.append(file)
        return pluginlist

    def disable_plugin(self, pluginname):
        if pluginname not in self.enabled_plugins:
            return
        try:
            plugin = self.enabled_plugins[pluginname]
            log.add(_("Disabled plugin {}".format(plugin.PLUGIN.__name__)))
            del self.enabled_plugins[pluginname]
            plugin.disable(self)
        except Exception:
            print_exc()
            log.addwarning(_("Unable to fully disable plugin %s") % pluginname)
            # common.log_exception(logger)
            return False
        return True

    def get_plugin_settings(self, pluginname):
        if pluginname in self.enabled_plugins:
            plugin = self.enabled_plugins[pluginname]
            if hasattr(plugin.PLUGIN, "metasettings"):
                return plugin.PLUGIN.metasettings

    def get_plugin_info(self, pluginname):
        path = os.path.join(self.__findplugin(pluginname), 'PLUGININFO')
        f = open(path)
        infodict = {}
        for line in f:
            try:
                key, val = line.split("=", 1)
                infodict[key] = eval(val)
            except ValueError:
                pass  # this happens on blank lines
        return infodict

    def save_enabled(self):
        self.frame.np.config.sections["plugins"]["enabled"] = list(self.enabled_plugins.keys())

    def check_enabled(self):
        if self.frame.np.config.sections["plugins"]["enable"]:
            self.load_enabled()
        else:
            to_enable = self.frame.np.config.sections["plugins"]["enabled"]  # noqa: F841
            for plugin in self.enabled_plugins:
                self.enabled_plugins[plugin].disable(self)

    def load_enabled(self):
        enable = self.frame.np.config.sections["plugins"]["enable"]
        if not enable:
            return
        to_enable = self.frame.np.config.sections["plugins"]["enabled"]
        for plugin in to_enable:
            self.enable_plugin(plugin)

    def plugin_settings(self, plugin):
        try:
            if not hasattr(plugin, "settings"):
                return
            if plugin.__id__ not in self.frame.np.config.sections["plugins"]:
                self.frame.np.config.sections["plugins"][plugin.__id__] = plugin.settings
            for i in plugin.settings:
                if i not in self.frame.np.config.sections["plugins"][plugin.__id__]:
                    self.frame.np.config.sections["plugins"][plugin.__id__][i] = plugin.settings[i]
            customsettings = self.frame.np.config.sections["plugins"][plugin.__id__]

            for key in customsettings:
                if key in plugin.settings:
                    plugin.settings[key] = customsettings[key]

                else:
                    log.add(_("Stored setting '%(name)s' is no longer present in the plugin") % {'name': key})
        except KeyError:
            log.add("No custom settings found for %s" % (plugin.__name__,))
            pass

    def TriggerPublicCommandEvent(self, room, command, args):
        return self._TriggerCommand("plugin.PLUGIN.PublicCommandEvent", command, room, args)

    def TriggerPrivateCommandEvent(self, user, command, args):
        return self._TriggerCommand("plugin.PLUGIN.PrivateCommandEvent", command, user, args)

    def _TriggerCommand(self, strfunc, command, source, args):
        for module, plugin in list(self.enabled_plugins.items()):
            try:
                if plugin.PLUGIN is None:
                    continue
                func = eval(strfunc)
                ret = func(command, source, args)
                if ret is not None:
                    if ret == returncode['zap']:
                        return True
                    elif ret == returncode['pass']:
                        pass
                    else:
                        log.add(_("Plugin %(module)s returned something weird, '%(value)s', ignoring") % {'module': module, 'value': str(ret)})
            except Exception:
                log.add(_("Plugin %(module)s failed with error %(errortype)s: %(error)s.\nTrace: %(trace)s\nProblem area:%(area)s") % {
                    'module': module,
                    'errortype': sys.exc_info()[0],
                    'error': sys.exc_info()[1],
                    'trace': ''.join(format_list(extract_stack())),
                    'area': ''.join(format_list(extract_tb(sys.exc_info()[2])))
                })
        return False

    def TriggerEvent(self, function, args):
        """Triggers an event for the plugins. Since events and notifications
        are precisely the same except for how n+ responds to them, both can be
        triggered by this function."""
        hotpotato = args
        for module, plugin in list(self.enabled_plugins.items()):
            try:
                func = eval("plugin.PLUGIN." + function)
                ret = func(*hotpotato)
                if ret is not None and type(ret) != tupletype:
                    if ret == returncode['zap']:
                        return None
                    elif ret == returncode['break']:
                        return hotpotato
                    elif ret == returncode['pass']:
                        pass
                    else:
                        log.add(_("Plugin %(module)s returned something weird, '%(value)s', ignoring") % {'module': module, 'value': ret})
                if ret is not None:
                    hotpotato = ret
            except Exception:
                log.add(_("Plugin %(module)s failed with error %(errortype)s: %(error)s.\nTrace: %(trace)s\nProblem area:%(area)s") % {
                    'module': module,
                    'errortype': sys.exc_info()[0],
                    'error': sys.exc_info()[1],
                    'trace': ''.join(format_list(extract_stack())),
                    'area': ''.join(format_list(extract_tb(sys.exc_info()[2])))
                })
        return hotpotato

    def SearchRequestNotification(self, searchterm, user, searchid):
        start_new_thread(self.TriggerEvent, ("SearchRequestNotification", (searchterm, user, searchid)))

    def DistribSearchNotification(self, searchterm, user, searchid):
        start_new_thread(self.TriggerEvent, ("DistribSearchNotification", (searchterm, user, searchid)))

    def PublicRoomMessageNotification(self, room, user, line):
        start_new_thread(self.TriggerEvent, ("PublicRoomMessageNotification", (room, user, line)))

    def IncomingPrivateChatEvent(self, user, line):
        if user != self.myUsername:
            # dont trigger the scripts on our own talking - we've got "Outgoing" for that
            return self.TriggerEvent("IncomingPrivateChatEvent", (user, line))
        else:
            return (user, line)

    def IncomingPrivateChatNotification(self, user, line):
        start_new_thread(self.TriggerEvent, ("IncomingPrivateChatNotification", (user, line)))

    def IncomingPublicChatEvent(self, room, user, line):
        return self.TriggerEvent("IncomingPublicChatEvent", (room, user, line))

    def IncomingPublicChatNotification(self, room, user, line):
        start_new_thread(self.TriggerEvent, ("IncomingPublicChatNotification", (room, user, line)))

    def OutgoingPrivateChatEvent(self, user, line):
        if line is not None:
            # if line is None nobody actually said anything
            return self.TriggerEvent("OutgoingPrivateChatEvent", (user, line))
        else:
            return (user, line)

    def OutgoingPrivateChatNotification(self, user, line):
        start_new_thread(self.TriggerEvent, ("OutgoingPrivateChatNotification", (user, line)))

    def OutgoingPublicChatEvent(self, room, line):
        return self.TriggerEvent("OutgoingPublicChatEvent", (room, line))

    def OutgoingPublicChatNotification(self, room, line):
        start_new_thread(self.TriggerEvent, ("OutgoingPublicChatNotification", (room, line)))

    def OutgoingGlobalSearchEvent(self, text):
        return self.TriggerEvent("OutgoingGlobalSearchEvent", (text,))

    def OutgoingRoomSearchEvent(self, rooms, text):
        return self.TriggerEvent("OutgoingRoomSearchEvent", (rooms, text))

    def OutgoingBuddySearchEvent(self, text):
        return self.TriggerEvent("OutgoingBuddySearchEvent", (text,))

    def OutgoingUserSearchEvent(self, users):
        return self.TriggerEvent("OutgoingUserSearchEvent", (users,))

    def UserResolveNotification(self, user, ip, port, country=None):
        """Notification for user IP:Port resolving.

        Note that country is only set when the user requested the resolving"""
        start_new_thread(self.TriggerEvent, ("UserResolveNotification", (user, ip, port, country)))

    def ServerConnectNotification(self):
        start_new_thread(self.TriggerEvent, ("ServerConnectNotification", (),))

    def ServerDisconnectNotification(self, userchoice):
        start_new_thread(self.TriggerEvent, ("ServerDisconnectNotification", (userchoice, )))

    def JoinChatroomNotification(self, room):
        start_new_thread(self.TriggerEvent, ("JoinChatroomNotification", (room,)))

    def LeaveChatroomNotification(self, room):
        start_new_thread(self.TriggerEvent, ("LeaveChatroomNotification", (room,)))

    def UploadQueuedNotification(self, user, virtualfile, realfile):
        start_new_thread(self.TriggerEvent, ("UploadQueuedNotification", (user, virtualfile, realfile)))

    def UserStatsNotification(self, user, stats):
        start_new_thread(self.TriggerEvent, ("UserStatsNotification", (user, stats)))

    # other functions
    def appendqueue(self, item):
        # We cannot do a test after adding the item since it's possible
        # this function will be called twice simultaneously - and then
        # len(self.guiqueue) might be 2 for both calls.
        # Calling the processQueue twice is not a problem though.
        addidle = False
        self.guiqueue.append(item)
        if len(self.guiqueue) >= 0:
            addidle = True
        if addidle:
            gobject.idle_add(self.processQueue)

    def log(self, text):
        self.appendqueue({'type': 'logtext', 'text': text})

    def saychatroom(self, room, text):
        text = cast_to_unicode_if_needed(text, log.addwarning)
        self.frame.np.queue.put(slskmessages.SayChatroom(room, ToBeEncoded(text, 'UTF-8')))

    def sayprivate(self, user, text):
        '''Send user message in private (showing up in GUI)'''
        self.appendqueue({'type': 'sayprivate', 'user': user, 'text': text})

    def sendprivate(self, user, text):
        '''Send user message in private (not showing up in GUI)'''
        self.appendqueue({'type': 'sendprivate', 'user': user, 'text': text})

    def processQueue(self):
        while len(self.guiqueue) > 0:
            i = self.guiqueue.pop(0)
            if i['type'] == 'logtext':
                log.add(i['text'])
            elif i['type'] == 'sayprivate':
                # If we use the np the chat lines only show up on the receiving end, we won't see anything ourselves.
                self.frame.privatechats.users[i['user']].SendMessage(i['text'])
            elif i['type'] == 'sendprivate':
                self.frame.privatechats.SendMessage(i['user'], i['text'])
            else:
                log.add(_('Unknown queue item %(type)s: %(item)s' % {
                    'type': i['type'],
                    'item': repr(i)
                }))
        return False


class BasePlugin(object):

    __name__ = "BasePlugin"
    __desc__ = "No description provided"
    # __id__ = "baseplugin_original" # you normally don't have to set this manually
    __version__ = "2016-08-30"
    __publiccommands__ = []
    __privatecommands__ = []

    def __init__(self, parent):
        # Never override this function, override init() instead
        self.parent = parent
        self.frame = parent.frame
        try:
            self.__id__
        except AttributeError:
            # See http://docs.python.org/library/configparser.html
            # %(name)s will lead to replacements so we need to filter out those symbols.
            self.__id__ = self.__name__.lower().replace(' ', '_').replace('%', '_').replace('=', '_')
        self.init()
        for (trigger, func) in self.__publiccommands__:
            self.frame.chatrooms.roomsctrl.CMDS.add('/' + trigger + ' ')
        for (trigger, func) in self.__privatecommands__:
            self.frame.privatechats.CMDS.add('/' + trigger + ' ')

    def init(self):
        pass

    def LoadSettings(self, settings):
        self.settings = settings

    def LoadNotification(self):
        pass

    def PublicRoomMessageNotification(self, room, user, line):
        pass

    def SearchRequestNotification(self, searchterm, user, searchid):
        pass

    def DistribSearchNotification(self, searchterm, user, searchid):
        pass

    def IncomingPrivateChatEvent(self, user, line):
        pass

    def IncomingPrivateChatNotification(self, user, line):
        pass

    def IncomingPublicChatEvent(self, room, user, line):
        pass

    def IncomingPublicChatNotification(self, room, user, line):
        pass

    def OutgoingPrivateChatEvent(self, user, line):
        pass

    def OutgoingPrivateChatNotification(self, user, line):
        pass

    def OutgoingPublicChatEvent(self, room, line):
        pass

    def OutgoingPublicChatNotification(self, room, line):
        pass

    def OutgoingGlobalSearchEvent(self, text):
        pass

    def OutgoingRoomSearchEvent(self, rooms, text):
        pass

    def OutgoingBuddySearchEvent(self, text):
        pass

    def OutgoingUserSearchEvent(self, users):
        pass

    def UserResolveNotification(self, user, ip, port, country):
        pass

    def ServerConnectNotification(self):
        pass

    def ServerDisconnectNotification(self, userchoice):
        pass

    def JoinChatroomNotification(self, room):
        pass

    def LeaveChatroomNotification(self, room):
        pass

    def UploadQueuedNotification(self, user, virtualfile, realfile):
        pass

    def UserStatsNotification(self, user, stats):
        pass

    # The following are functions to make your life easier,
    # you shouldn't override them.
    def log(self, text):
        self.parent.log(self.__name__ + ": " + text)

    def saypublic(self, room, text):
        self.parent.saychatroom(room, text)

    def sayprivate(self, user, text):
        '''Send user message in private (shows up in GUI)'''
        self.parent.sayprivate(user, text)

    def sendprivate(self, user, text):
        '''Send user message in private (doesn't show up in GUI)'''
        self.parent.sendprivate(user, text)

    def fakepublic(self, room, user, text):
        try:
            room = self.frame.chatrooms.roomsctrl.joinedrooms[room]
        except KeyError:
            return False
        text = cast_to_unicode_if_needed(text, self.log)
        msg = slskmessages.SayChatroom(room, ToBeEncoded(text, 'UTF-8'))
        msg.user = user
        room.SayChatRoom(msg, text)
        return True

    # The following are functions used by the plugin system,
    # you are not allowed to override these.
    def PublicCommandEvent(self, command, room, args):
        for (trigger, func) in self.__publiccommands__:
            if trigger == command:
                return func(self, room, args)

    def PrivateCommandEvent(self, command, user, args):
        for (trigger, func) in self.__privatecommands__:
            if trigger == command:
                return func(self, user, args)


class ResponseThrottle(object):

    """
    ResponseThrottle - Mutnick 2016

    See 'reddit' and my other plugins for example use

    Purpose: Avoid flooding chat room with plugin responses
        Some plugins respond based on user requests and we do not want
        to respond too much and encounter a temporary server chat ban

    Some of the throttle logic is guesswork as server code is closed source, but works adequately.
    """

    def __init__(self, frame, plugin_name, logging=False):
        self.frame = frame
        self.plugin_name = plugin_name
        self.logging = logging
        self.plugin_usage = {}

    def ok_to_respond(self, room, nick, request, seconds_limit_min=30):
        self.room = room
        self.nick = nick
        self.request = request

        willing_to_respond = True
        current_time = time()

        if room not in list(self.plugin_usage.keys()):
            self.plugin_usage[room] = {'last_time': 0, 'last_request': "", 'last_nick': ""}

        last_time = self.plugin_usage[room]['last_time']
        last_nick = self.plugin_usage[room]['last_nick']
        last_request = self.plugin_usage[room]['last_request']

        port = False
        try:
            ip, port = self.frame.np.users[nick].addr
        except Exception:
            port = True

        if nick in self.frame.np.config.sections["server"]["ignorelist"]:
            willing_to_respond, reason = False, "The nick is ignored"
        elif self.frame.UserIpIsIgnored(nick):
            willing_to_respond, reason = False, "The nick's Ip is ignored"
        elif not port:
            willing_to_respond, reason = False, "Request likely from simple PHP based griefer bot"
        elif [nick, request] == [last_nick, last_request]:
            if (current_time - last_time) < 12 * seconds_limit_min:
                willing_to_respond, reason = False, "Too soon for same nick to request same resource in room"
        elif (request == last_request):
            if (current_time - last_time) < 3 * seconds_limit_min:
                willing_to_respond, reason = False, "Too soon for different nick to request same resource in room"
        else:
            recent_responses = 0
            for responded_room in self.plugin_usage:
                if (current_time - self.plugin_usage[responded_room]['last_time']) < seconds_limit_min:
                    recent_responses += 1
                    if responded_room == room:
                        willing_to_respond, reason = False, "Responded in specified room too recently"
                        break
            if recent_responses > 3:
                willing_to_respond, reason = False, "Responded in multiple rooms enough"

        if self.logging:
            if not willing_to_respond:
                base_log_msg = "{} plugin request rejected - room '{}', nick '{}'".format(self.plugin_name, room, nick)
                log.adddebug("{} - {}".format(base_log_msg, reason))

        return willing_to_respond

    def responded(self, msg=""):
        # possible TODO's: we could actually say public the msg here
        # make more stateful - track past msg's as additional responder willingness criteria, etc
        self.plugin_usage[self.room] = {'last_time': time(), 'last_request': self.request, 'last_nick': self.nick}
