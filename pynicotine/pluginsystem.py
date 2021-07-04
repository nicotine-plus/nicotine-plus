# COPYRIGHT (C) 2020-2021 Nicotine+ Team
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

import os
import sys

from ast import literal_eval
from time import time

from pynicotine import slskmessages
from pynicotine.logfacility import log


returncode = {
    'break': 0,  # don't give other plugins the event, do let n+ process it
    'zap': 1,    # don't give other plugins the event, don't let n+ process it
    'pass': 2    # do give other plugins the event, do let n+ process it
}                # returning nothing is the same as 'pass'


class PluginHandler:

    def __init__(self, core, config):

        self.core = core
        self.config = config

        log.add_debug("Loading plugin handler")

        self.my_username = self.config.sections["server"]["login"]
        self.plugindirs = []
        self.enabled_plugins = {}

        try:
            os.makedirs(config.plugin_dir)
        except Exception:
            pass

        # Load system-wide plugins
        prefix = os.path.dirname(os.path.realpath(__file__))
        self.plugindirs.append(os.path.join(prefix, "plugins"))

        # Load home directory plugins
        self.plugindirs.append(config.plugin_dir)

        if os.path.isdir(config.plugin_dir):
            self.load_enabled()
        else:
            log.add(_("It appears '%s' is not a directory, not loading plugins."), config.plugin_dir)

    def update_completions(self, plugin):

        if self.core.ui_callback and plugin.__publiccommands__ and self.config.sections["words"]["commands"]:
            self.core.ui_callback.chatrooms.update_completions()

        if plugin.__privatecommands__ and self.config.sections["words"]["commands"]:
            self.core.privatechats.update_completions()

    def __findplugin(self, pluginname):
        for directory in self.plugindirs:
            fullpath = os.path.join(directory, pluginname)

            if os.path.exists(fullpath):
                return fullpath

        return None

    def toggle_plugin(self, pluginname):

        enabled = pluginname in self.enabled_plugins

        if enabled:
            self.disable_plugin(pluginname)
        else:
            self.enable_plugin(pluginname)

    def load_plugin(self, pluginname):

        try:
            # Import builtin plugin
            from importlib import import_module
            plugin = import_module("pynicotine.plugins." + pluginname)

        except Exception:
            # Import user plugin
            path = self.__findplugin(pluginname)

            if path is None:
                log.add(_("Failed to load plugin '%s', could not find it."), pluginname)
                return False

            import importlib.util
            spec = importlib.util.spec_from_file_location(pluginname, os.path.join(path, '__init__.py'))
            plugin = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(plugin)

        if hasattr(plugin, "enable"):
            log.add(
                "Plugin '%s': top-level enable() function is obsolete, please use BasePlugin.init() instead",
                pluginname)

        if hasattr(plugin, "disable"):
            log.add(
                "Plugin '%s': top-level disable() function is obsolete, please use BasePlugin.disable() instead",
                pluginname)

        instance = plugin.Plugin(self, self.config, self.core)
        self.plugin_settings(pluginname, instance)
        instance.LoadNotification()

        return instance

    def enable_plugin(self, pluginname):

        # Our config file doesn't play nicely with some characters
        if "=" in pluginname:
            log.add(
                _("Unable to enable plugin %(name)s. Plugin folder name contains invalid characters: %(characters)s"), {
                    "name": pluginname,
                    "characters": "="
                })
            return False

        if pluginname in self.enabled_plugins:
            return False

        try:
            plugin = self.load_plugin(pluginname)

            if not plugin:
                raise Exception("Error loading plugin '%s'" % pluginname)

            plugin.init()

            if self.core.ui_callback:
                for trigger, _func in plugin.__publiccommands__:
                    self.core.ui_callback.chatrooms.CMDS.add('/' + trigger + ' ')

            for trigger, _func in plugin.__privatecommands__:
                self.core.privatechats.CMDS.add('/' + trigger + ' ')

            self.update_completions(plugin)

            self.enabled_plugins[pluginname] = plugin
            log.add(_("Enabled plugin %s"), plugin.__name__)

        except Exception:
            from traceback import format_exc
            log.add(_("Unable to enable plugin %(module)s\n%(exc_trace)s"),
                    {'module': pluginname, 'exc_trace': format_exc()})
            return False

        return True

    def list_installed_plugins(self):
        pluginlist = []

        for folder in self.plugindirs:
            if os.path.isdir(folder):
                for file in os.listdir(folder):
                    if file not in pluginlist and os.path.isdir(os.path.join(folder, file)):
                        pluginlist.append(file)

        return pluginlist

    def disable_plugin(self, pluginname):
        if pluginname not in self.enabled_plugins:
            return False

        try:
            plugin = self.enabled_plugins[pluginname]

            log.add(_("Disabled plugin {}".format(plugin.__name__)))
            plugin.disable()

            if self.core.ui_callback:
                for trigger, _func in plugin.__publiccommands__:
                    self.core.ui_callback.chatrooms.CMDS.remove('/' + trigger + ' ')

            for trigger, _func in plugin.__privatecommands__:
                self.core.privatechats.CMDS.remove('/' + trigger + ' ')

            self.update_completions(plugin)

            del self.enabled_plugins[pluginname]
            del plugin

        except Exception:
            from traceback import format_exc
            log.add(_("Unable to fully disable plugin %(module)s\n%(exc_trace)s"),
                    {'module': pluginname, 'exc_trace': format_exc()})
            return False

        return True

    def get_plugin_settings(self, pluginname):
        if pluginname in self.enabled_plugins:
            plugin = self.enabled_plugins[pluginname]

            if plugin.metasettings:
                return plugin.metasettings

        return None

    def get_plugin_info(self, pluginname):
        path = os.path.join(self.__findplugin(pluginname), 'PLUGININFO')

        with open(path) as file_handle:
            infodict = {}

            for line in file_handle:
                try:
                    key, val = line.split("=", 1)
                    infodict[key.strip()] = literal_eval(val.strip())
                except ValueError:
                    pass  # this happens on blank lines

        return infodict

    def save_enabled(self):
        self.config.sections["plugins"]["enabled"] = list(self.enabled_plugins.keys())

    def load_enabled(self):
        enable = self.config.sections["plugins"]["enable"]

        if not enable:
            return

        to_enable = self.config.sections["plugins"]["enabled"]

        for plugin in to_enable:
            self.enable_plugin(plugin)

    def plugin_settings(self, pluginname, plugin):
        try:
            if not plugin.settings:
                return

            if pluginname not in self.config.sections["plugins"]:
                self.config.sections["plugins"][pluginname] = plugin.settings

            for i in plugin.settings:
                if i not in self.config.sections["plugins"][pluginname]:
                    self.config.sections["plugins"][pluginname][i] = plugin.settings[i]

            customsettings = self.config.sections["plugins"][pluginname]

            for key in customsettings:
                if key in plugin.settings:
                    plugin.settings[key] = customsettings[key]

                else:
                    log.add(_("Stored setting '%(name)s' is no longer present in the plugin"), {'name': key})

        except KeyError:
            log.add("No custom settings found for %s", (plugin.__name__,))

    def trigger_public_command_event(self, room, command, args):
        return self._trigger_command(command, room, args, public_command=True)

    def trigger_private_command_event(self, user, command, args):
        return self._trigger_command(command, user, args, public_command=False)

    def _trigger_command(self, command, source, args, public_command):

        for module, plugin in self.enabled_plugins.items():
            try:
                if plugin is None:
                    continue

                return_value = None

                if public_command:
                    for trigger, func in plugin.__publiccommands__:
                        if trigger == command:
                            return_value = func(plugin, source, args)

                else:
                    for trigger, func in plugin.__privatecommands__:
                        if trigger == command:
                            return_value = func(plugin, source, args)

                if return_value is None:
                    # Nothing changed, continue to the next plugin
                    continue

                if return_value == returncode['zap']:
                    return True

                if return_value == returncode['pass']:
                    continue

                log.add(_("Plugin %(module)s returned something weird, '%(value)s', ignoring"),
                        {'module': module, 'value': str(return_value)})

            except Exception:
                from traceback import extract_stack
                from traceback import extract_tb
                from traceback import format_list

                log.add(_("Plugin %(module)s failed with error %(errortype)s: %(error)s.\n"
                          "Trace: %(trace)s\nProblem area:%(area)s"), {
                    'module': module,
                    'errortype': sys.exc_info()[0],
                    'error': sys.exc_info()[1],
                    'trace': ''.join(format_list(extract_stack())),
                    'area': ''.join(format_list(extract_tb(sys.exc_info()[2])))
                })

        return False

    def trigger_event(self, function, args):
        """ Triggers an event for the plugins. Since events and notifications
        are precisely the same except for how n+ responds to them, both can be
        triggered by this function. """

        for module, plugin in self.enabled_plugins.items():
            try:
                return_value = getattr(plugin, function)(*args)

                if return_value is None:
                    # Nothing changed, continue to the next plugin
                    continue

                if isinstance(return_value, tuple):
                    # The original args were modified, update them
                    args = return_value
                    continue

                if return_value == returncode['zap']:
                    return None

                if return_value == returncode['break']:
                    return args

                if return_value == returncode['pass']:
                    continue

                log.add(_("Plugin %(module)s returned something weird, '%(value)s', ignoring"),
                        {'module': module, 'value': return_value})

            except Exception:
                from traceback import extract_stack
                from traceback import extract_tb
                from traceback import format_list

                log.add(_("Plugin %(module)s failed with error %(errortype)s: %(error)s.\n"
                          "Trace: %(trace)s\nProblem area:%(area)s"), {
                    'module': module,
                    'errortype': sys.exc_info()[0],
                    'error': sys.exc_info()[1],
                    'trace': ''.join(format_list(extract_stack())),
                    'area': ''.join(format_list(extract_tb(sys.exc_info()[2])))
                })

        return args

    def search_request_notification(self, searchterm, user, searchid):
        self.trigger_event("SearchRequestNotification", (searchterm, user, searchid))

    def distrib_search_notification(self, searchterm, user, searchid):
        self.trigger_event("DistribSearchNotification", (searchterm, user, searchid))

    def public_room_message_notification(self, room, user, line):
        self.trigger_event("PublicRoomMessageNotification", (room, user, line))

    def incoming_private_chat_event(self, user, line):
        if user != self.my_username:
            # dont trigger the scripts on our own talking - we've got "Outgoing" for that
            return self.trigger_event("IncomingPrivateChatEvent", (user, line))

        return (user, line)

    def incoming_private_chat_notification(self, user, line):
        self.trigger_event("IncomingPrivateChatNotification", (user, line))

    def incoming_public_chat_event(self, room, user, line):
        return self.trigger_event("IncomingPublicChatEvent", (room, user, line))

    def incoming_public_chat_notification(self, room, user, line):
        self.trigger_event("IncomingPublicChatNotification", (room, user, line))

    def outgoing_private_chat_event(self, user, line):
        if line is not None:
            # if line is None nobody actually said anything
            return self.trigger_event("OutgoingPrivateChatEvent", (user, line))

        return (user, line)

    def outgoing_private_chat_notification(self, user, line):
        self.trigger_event("OutgoingPrivateChatNotification", (user, line))

    def outgoing_public_chat_event(self, room, line):
        return self.trigger_event("OutgoingPublicChatEvent", (room, line))

    def outgoing_public_chat_notification(self, room, line):
        self.trigger_event("OutgoingPublicChatNotification", (room, line))

    def outgoing_global_search_event(self, text):
        return self.trigger_event("OutgoingGlobalSearchEvent", (text,))

    def outgoing_room_search_event(self, rooms, text):
        return self.trigger_event("OutgoingRoomSearchEvent", (rooms, text))

    def outgoing_buddy_search_event(self, text):
        return self.trigger_event("OutgoingBuddySearchEvent", (text,))

    def outgoing_user_search_event(self, users, text):
        return self.trigger_event("OutgoingUserSearchEvent", (users, text))

    def user_resolve_notification(self, user, ip_address, port, country=None):
        """Notification for user IP:Port resolving.

        Note that country is only set when the user requested the resolving"""
        self.trigger_event("UserResolveNotification", (user, ip_address, port, country))

    def server_connect_notification(self):
        self.trigger_event("ServerConnectNotification", (),)

    def server_disconnect_notification(self, userchoice):
        self.trigger_event("ServerDisconnectNotification", (userchoice, ))

    def join_chatroom_notification(self, room):
        self.trigger_event("JoinChatroomNotification", (room,))

    def leave_chatroom_notification(self, room):
        self.trigger_event("LeaveChatroomNotification", (room,))

    def user_join_chatroom_notification(self, room, user):
        self.trigger_event("UserJoinChatroomNotification", (room, user,))

    def user_leave_chatroom_notification(self, room, user):
        self.trigger_event("UserLeaveChatroomNotification", (room, user,))

    def user_stats_notification(self, user, stats):
        self.trigger_event("UserStatsNotification", (user, stats))

    def upload_queued_notification(self, user, virtual_path, real_path):
        self.trigger_event("UploadQueuedNotification", (user, virtual_path, real_path))

    def upload_started_notification(self, user, virtual_path, real_path):
        self.trigger_event("UploadStartedNotification", (user, virtual_path, real_path))

    def upload_finished_notification(self, user, virtual_path, real_path):
        self.trigger_event("UploadFinishedNotification", (user, virtual_path, real_path))

    def download_started_notification(self, user, virtual_path, real_path):
        self.trigger_event("DownloadStartedNotification", (user, virtual_path, real_path))

    def download_finished_notification(self, user, virtual_path, real_path):
        self.trigger_event("DownloadFinishedNotification", (user, virtual_path, real_path))

    def shutdown_notification(self):
        self.trigger_event("ShutdownNotification", (),)


class ResponseThrottle:

    """
    ResponseThrottle - Mutnick 2016

    See 'reddit' and my other plugins for example use

    Purpose: Avoid flooding chat room with plugin responses
        Some plugins respond based on user requests and we do not want
        to respond too much and encounter a temporary server chat ban

    Some of the throttle logic is guesswork as server code is closed source, but works adequately.
    """

    def __init__(self, core, plugin_name, logging=False):

        self.core = core
        self.plugin_name = plugin_name
        self.logging = logging
        self.plugin_usage = {}

        self.room = None
        self.nick = None
        self.request = None

    def ok_to_respond(self, room, nick, request, seconds_limit_min=30):

        self.room = room
        self.nick = nick
        self.request = request

        willing_to_respond = True
        current_time = time()

        if room not in self.plugin_usage:
            self.plugin_usage[room] = {'last_time': 0, 'last_request': "", 'last_nick': ""}

        last_time = self.plugin_usage[room]['last_time']
        last_nick = self.plugin_usage[room]['last_nick']
        last_request = self.plugin_usage[room]['last_request']

        port = False
        try:
            _ip_address, port = self.core.users[nick].addr
        except Exception:
            port = True

        if self.core.network_filter.is_user_ignored(nick):
            willing_to_respond, reason = False, "The nick is ignored"

        elif self.core.network_filter.is_user_ip_ignored(nick):
            willing_to_respond, reason = False, "The nick's Ip is ignored"

        elif not port:
            willing_to_respond, reason = False, "Request likely from simple PHP based griefer bot"

        elif [nick, request] == [last_nick, last_request]:
            if (current_time - last_time) < 12 * seconds_limit_min:
                willing_to_respond, reason = False, "Too soon for same nick to request same resource in room"

        elif request == last_request:
            if (current_time - last_time) < 3 * seconds_limit_min:
                willing_to_respond, reason = False, "Too soon for different nick to request same resource in room"

        else:
            recent_responses = 0

            for responded_room, room_dict in self.plugin_usage.items():
                if (current_time - room_dict['last_time']) < seconds_limit_min:
                    recent_responses += 1

                    if responded_room == room:
                        willing_to_respond, reason = False, "Responded in specified room too recently"
                        break

            if recent_responses > 3:
                willing_to_respond, reason = False, "Responded in multiple rooms enough"

        if self.logging and not willing_to_respond:
            base_log_msg = "{} plugin request rejected - room '{}', nick '{}'".format(self.plugin_name, room, nick)
            log.add_debug("{} - {}".format(base_log_msg, reason))

        return willing_to_respond

    def responded(self):
        # possible TODO's: we could actually say public the msg here
        # make more stateful - track past msg's as additional responder willingness criteria, etc
        self.plugin_usage[self.room] = {'last_time': time(), 'last_request': self.request, 'last_nick': self.nick}


class BasePlugin:

    __name__ = "BasePlugin"
    __publiccommands__ = []
    __privatecommands__ = []
    settings = {}
    metasettings = {}

    def __init__(self, parent, config, core):

        # Never override this function, override init() instead
        self.parent = parent
        self.config = config
        self.core = core
        self.frame = core.ui_callback

    def init(self):
        # Custom enable function for plugins
        pass

    def disable(self):
        # Custom disable function for plugins
        pass

    def LoadSettings(self, settings):  # pylint: disable=invalid-name, # noqa
        self.settings = settings

    def LoadNotification(self):  # pylint: disable=invalid-name, # noqa
        pass

    def PublicRoomMessageNotification(self, room, user, line):  # pylint: disable=invalid-name, # noqa
        pass

    def SearchRequestNotification(self, searchterm, user, searchid):  # pylint: disable=invalid-name, # noqa
        pass

    def DistribSearchNotification(self, searchterm, user, searchid):  # pylint: disable=invalid-name, # noqa
        pass

    def IncomingPrivateChatEvent(self, user, line):  # pylint: disable=invalid-name, # noqa
        pass

    def IncomingPrivateChatNotification(self, user, line):  # pylint: disable=invalid-name, # noqa
        pass

    def IncomingPublicChatEvent(self, room, user, line):  # pylint: disable=invalid-name, # noqa
        pass

    def IncomingPublicChatNotification(self, room, user, line):  # pylint: disable=invalid-name, # noqa
        pass

    def OutgoingPrivateChatEvent(self, user, line):  # pylint: disable=invalid-name, # noqa
        pass

    def OutgoingPrivateChatNotification(self, user, line):  # pylint: disable=invalid-name, # noqa
        pass

    def OutgoingPublicChatEvent(self, room, line):  # pylint: disable=invalid-name, # noqa
        pass

    def OutgoingPublicChatNotification(self, room, line):  # pylint: disable=invalid-name, # noqa
        pass

    def OutgoingGlobalSearchEvent(self, text):  # pylint: disable=invalid-name, # noqa
        pass

    def OutgoingRoomSearchEvent(self, rooms, text):  # pylint: disable=invalid-name, # noqa
        pass

    def OutgoingBuddySearchEvent(self, text):  # pylint: disable=invalid-name, # noqa
        pass

    def OutgoingUserSearchEvent(self, users, text):  # pylint: disable=invalid-name, # noqa
        pass

    def UserResolveNotification(self, user, ip, port, country):  # pylint: disable=invalid-name, # noqa
        pass

    def ServerConnectNotification(self):  # pylint: disable=invalid-name, # noqa
        pass

    def ServerDisconnectNotification(self, userchoice):  # pylint: disable=invalid-name, # noqa
        pass

    def JoinChatroomNotification(self, room):  # pylint: disable=invalid-name, # noqa
        pass

    def LeaveChatroomNotification(self, room):  # pylint: disable=invalid-name, # noqa
        pass

    def UserJoinChatroomNotification(self, room, user):  # pylint: disable=invalid-name, # noqa
        pass

    def UserLeaveChatroomNotification(self, room, user):  # pylint: disable=invalid-name, # noqa
        pass

    def UserStatsNotification(self, user, stats):  # pylint: disable=invalid-name, # noqa
        pass

    def UploadQueuedNotification(self, user, virtual_path, real_path):  # pylint: disable=invalid-name, # noqa
        pass

    def UploadStartedNotification(self, user, virtual_path, real_path):  # pylint: disable=invalid-name, # noqa
        pass

    def UploadFinishedNotification(self, user, virtual_path, real_path):  # pylint: disable=invalid-name, # noqa
        pass

    def DownloadStartedNotification(self, user, virtual_path, real_path):  # pylint: disable=invalid-name, # noqa
        pass

    def DownloadFinishedNotification(self, user, virtual_path, real_path):  # pylint: disable=invalid-name, # noqa
        pass

    def ShutdownNotification(self):  # pylint: disable=invalid-name, # noqa
        pass

    # The following are functions to make your life easier,
    # you shouldn't override them.
    def log(self, text):
        log.add(self.__name__ + ": " + text)

    def saypublic(self, room, text):
        self.core.queue.append(slskmessages.SayChatroom(room, text))

    def sayprivate(self, user, text):
        """ Send user message in private (showing up in GUI) """

        self.core.privatechats.show_user(user)
        self.core.privatechats.send_message(user, text)

    def sendprivate(self, user, text):
        """ Send user message in private (not showing up in GUI) """

        self.core.privatechats.send_message(user, text)

    def fakepublic(self, room, user, text):
        try:
            room = self.core.chatrooms.joinedrooms[room]
        except KeyError:
            return False

        msg = slskmessages.SayChatroom(room, text)
        msg.user = user
        room.say_chat_room(msg, text)
        return True

    def echo_private(self, user, msg):
        """ Display a raw message in private (not sent to others) """

        self.core.privatechats.show_user(user)
        self.core.privatechats.echo_message(user, msg)
