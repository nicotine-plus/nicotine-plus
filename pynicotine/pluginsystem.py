# COPYRIGHT (C) 2020-2024 Nicotine+ Contributors
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2016 Mutnick <muhing@yahoo.com>
# COPYRIGHT (C) 2008-2011 quinox <quinox@users.sf.net>
# COPYRIGHT (C) 2009 daelstorm <daelstorm@gmail.com>
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
import time

from ast import literal_eval
from collections import defaultdict

from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.logfacility import log
from pynicotine.utils import encode_path


returncode = {
    "break": 0,  # don't give other plugins the event, do let n+ process it
    "zap": 1,    # don't give other plugins the event, don't let n+ process it
    "pass": 2    # do give other plugins the event, do let n+ process it
}                # returning nothing is the same as 'pass'


class BasePlugin:

    # Attributes that can be modified, see examples in the pynicotine/plugins/ folder
    __publiccommands__ = []
    __privatecommands__ = []
    commands = {}
    settings = {}
    metasettings = {}

    # Attributes that are assigned when the plugin loads, do not modify these
    internal_name = None  # Technical plugin name based on plugin folder name
    human_name = None     # Friendly plugin name specified in the PLUGININFO file
    path = None           # Folder path where plugin files are stored
    parent = None         # Reference to PluginHandler
    config = None         # Reference to global Config handler
    core = None           # Reference to Core

    def __init__(self):
        # The plugin class is initializing, plugin settings are not available yet
        pass

    def init(self):
        # Called after __init__() when plugin settings have loaded
        pass

    def loaded_notification(self):
        # The plugin has finished loaded, commands are registered
        pass

    def disable(self):
        # The plugin has started unloading
        pass

    def unloaded_notification(self):
        # The plugin has finished unloading
        pass

    def shutdown_notification(self):
        # Application is shutting down
        pass

    def public_room_message_notification(self, room, user, line):
        # Override method in plugin
        pass

    def search_request_notification(self, searchterm, user, token):
        # Override method in plugin
        pass

    def distrib_search_notification(self, searchterm, user, token):
        # Override method in plugin
        pass

    def incoming_private_chat_event(self, user, line):
        # Override method in plugin
        pass

    def incoming_private_chat_notification(self, user, line):
        # Override method in plugin
        pass

    def incoming_public_chat_event(self, room, user, line):
        # Override method in plugin
        pass

    def incoming_public_chat_notification(self, room, user, line):
        # Override method in plugin
        pass

    def outgoing_private_chat_event(self, user, line):
        # Override method in plugin
        pass

    def outgoing_private_chat_notification(self, user, line):
        # Override method in plugin
        pass

    def outgoing_public_chat_event(self, room, line):
        # Override method in plugin
        pass

    def outgoing_public_chat_notification(self, room, line):
        # Override method in plugin
        pass

    def outgoing_global_search_event(self, text):
        # Override method in plugin
        pass

    def outgoing_room_search_event(self, rooms, text):
        # Override method in plugin
        pass

    def outgoing_buddy_search_event(self, text):
        # Override method in plugin
        pass

    def outgoing_user_search_event(self, users, text):
        # Override method in plugin
        pass

    def outgoing_wishlist_search_event(self, text):
        # Override method in plugin
        pass

    def user_resolve_notification(self, user, ip_address, port, country):
        # Override method in plugin
        pass

    def server_connect_notification(self):
        # Override method in plugin
        pass

    def server_disconnect_notification(self, userchoice):
        # Override method in plugin
        pass

    def join_chatroom_notification(self, room):
        # Override method in plugin
        pass

    def leave_chatroom_notification(self, room):
        # Override method in plugin
        pass

    def user_join_chatroom_notification(self, room, user):
        # Override method in plugin
        pass

    def user_leave_chatroom_notification(self, room, user):
        # Override method in plugin
        pass

    def user_stats_notification(self, user, stats):
        # Override method in plugin
        pass

    def user_status_notification(self, user, status, privileged):
        # Override method in plugin
        pass

    def upload_queued_notification(self, user, virtual_path, real_path):
        # Override method in plugin
        pass

    def upload_started_notification(self, user, virtual_path, real_path):
        # Override method in plugin
        pass

    def upload_finished_notification(self, user, virtual_path, real_path):
        # Override method in plugin
        pass

    def download_started_notification(self, user, virtual_path, real_path):
        # Override method in plugin
        pass

    def download_finished_notification(self, user, virtual_path, real_path):
        # Override method in plugin
        pass

    # The following are functions to make your life easier,
    # you shouldn't override them.

    def log(self, msg, msg_args=None):
        log.add(f"{self.human_name}: {msg}", msg_args)

    def send_public(self, room, text):
        """Send chat message to a room, must already be joined."""

        core.chatrooms.send_message(room, text)

    def send_private(self, user, text, show_ui=True, switch_page=True):
        """Send user message in private.

        show_ui controls if the UI opens a private chat view for the
        user. switch_page controls whether the user's private chat view
        should be opened.
        """

        if show_ui:
            core.privatechat.show_user(user, switch_page)

        core.privatechat.send_message(user, text)

    def echo_public(self, room, text, message_type="local"):
        """Display a raw message in chat rooms (not sent to others).

        message_type changes the type (and color) of the message in the UI.
        available message_type values: action, remote, local, hilite
        """

        core.chatrooms.echo_message(room, text, message_type)

    def echo_private(self, user, text, message_type="local"):
        """Display a raw message in private (not sent to others).

        message_type changes the type (and color) of the message in the UI.
        available message_type values: action, remote, local, hilite
        """

        core.privatechat.show_user(user)
        core.privatechat.echo_message(user, text, message_type)

    def send_message(self, text):
        """Convenience function to send a message to the same user/room a
        plugin command runs for."""

        if self.parent.command_source is None:
            # Function was not called from a command
            return

        command_interface, source = self.parent.command_source

        if command_interface == "cli":
            return

        func = self.send_public if command_interface == "chatroom" else self.send_private
        func(source, text)

    def echo_message(self, text, message_type="local"):
        """Convenience function to display a raw message the same window a
        plugin command runs from."""

        if self.parent.command_source is None:
            # Function was not called from a command
            return

        command_interface, source = self.parent.command_source

        if command_interface == "cli":
            print(text)
            return

        func = self.echo_public if command_interface == "chatroom" else self.echo_private
        func(source, text, message_type)

    def output(self, text):
        self.echo_message(text, message_type="command")


class ResponseThrottle:
    """
    ResponseThrottle - Mutnick 2016

    See 'testreplier' plugin for example use

    Purpose: Avoid flooding chat room with plugin responses
        Some plugins respond based on user requests and we do not want
        to respond too much and encounter a temporary server chat ban

    Some of the throttle logic is guesswork as server code is closed source, but works adequately.
    """

    def __init__(self, core, plugin_name, logging=False):  # pylint: disable=redefined-outer-name

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
        current_time = time.monotonic()

        if room not in self.plugin_usage:
            self.plugin_usage[room] = {"last_time": 0, "last_request": "", "last_nick": ""}

        last_time = self.plugin_usage[room]["last_time"]
        last_nick = self.plugin_usage[room]["last_nick"]
        last_request = self.plugin_usage[room]["last_request"]

        try:
            _ip_address, port = self.core.users.addresses[nick]
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
                if (current_time - room_dict["last_time"]) < seconds_limit_min:
                    recent_responses += 1

                    if responded_room == room:
                        willing_to_respond, reason = False, "Responded in specified room too recently"
                        break

            if recent_responses > 3:
                willing_to_respond, reason = False, "Responded in multiple rooms enough"

        if self.logging and not willing_to_respond:
            log.add_debug("%s plugin request rejected - room '%s', nick '%s' - %s",
                          (self.plugin_name, room, nick, reason))

        return willing_to_respond

    def responded(self):
        self.plugin_usage[self.room] = {
            "last_time": time.monotonic(), "last_request": self.request, "last_nick": self.nick}


class PluginHandler:
    __slots__ = ("plugin_folders", "enabled_plugins", "command_source", "commands",
                 "user_plugin_folder", "_load_now_playing_sender")

    def __init__(self, isolated_mode=False):

        self.plugin_folders = []
        self.enabled_plugins = {}
        self.command_source = None
        self.commands = {
            "chatroom": {},
            "private_chat": {},
            "cli": {}
        }
        self._load_now_playing_sender = (
            not isolated_mode
            and sys.platform not in {"win32", "darwin"}
            and "SNAP_NAME" not in os.environ
        )

        # Load system-wide plugins
        prefix = os.path.dirname(os.path.realpath(__file__))
        self.plugin_folders.append(os.path.join(prefix, "plugins"))

        # Load home folder plugins
        self.user_plugin_folder = os.path.join(config.data_folder_path, "plugins")
        self.plugin_folders.append(self.user_plugin_folder)

        for event_name, callback in (
            ("cli-command", self._cli_command),
            ("start", self._start),
            ("quit", self._quit)
        ):
            events.connect(event_name, callback)

    def _start(self):

        BasePlugin.parent = self
        BasePlugin.config = config
        BasePlugin.core = core

        log.add(_("Loading plugin system"))
        self.enable_plugin("core_commands")

        if not config.sections["plugins"]["enable"]:
            return

        to_enable = config.sections["plugins"]["enabled"]
        log.add_debug("Enabled plugin(s): %s", ', '.join(to_enable))

        for plugin in to_enable:
            self.enable_plugin(plugin)

    def _quit(self):

        # Notify plugins
        self.shutdown_notification()

        # Disable plugins
        for plugin in self.list_installed_plugins():
            self.disable_plugin(plugin, is_permanent=False)

    def _cli_command(self, command, args):
        self.trigger_cli_command_event(command, args)

    def update_completions(self, plugin):

        if not config.sections["words"]["commands"]:
            return

        if plugin.commands or plugin.__publiccommands__:
            core.chatrooms.update_completions()

        if plugin.commands or plugin.__privatecommands__:
            core.privatechat.update_completions()

    def get_plugin_path(self, plugin_name):

        for folder_path in self.plugin_folders:
            file_path = os.path.join(folder_path, plugin_name)

            if os.path.isdir(encode_path(file_path)):
                return file_path

        return None

    def _import_plugin_instance(self, plugin_name):

        if plugin_name == "now_playing_sender" and not self._load_now_playing_sender:
            # MPRIS is not available on Windows and macOS
            return None

        plugin_path = self.get_plugin_path(plugin_name)

        try:
            # Import builtin plugin
            from importlib import import_module
            plugin = import_module(f"pynicotine.plugins.{plugin_name}")

        except Exception:
            # Import user plugin
            if plugin_path is None:
                log.add_debug("Failed to load plugin '%s', could not find it", plugin_name)
                return None

            # Add plugin folder to path in order to support relative imports
            sys.path.append(plugin_path)

            import importlib.util
            spec = importlib.util.spec_from_file_location(plugin_name, os.path.join(plugin_path, "__init__.py"))
            plugin = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(plugin)

        # Set class attributes to make name available while initializing plugin
        BasePlugin.internal_name = plugin_name
        BasePlugin.human_name = self.get_plugin_info(plugin_name).get("Name", plugin_name)
        BasePlugin.path = plugin_path

        instance = plugin.Plugin()
        instance.internal_name = BasePlugin.internal_name
        instance.human_name = BasePlugin.human_name
        instance.path = BasePlugin.path

        # Reset class attributes
        BasePlugin.internal_name = BasePlugin.human_name = BasePlugin.path = None

        self.plugin_settings(plugin_name, instance)

        if hasattr(plugin, "enable"):
            instance.log("top-level enable() function is obsolete, please use BasePlugin.__init__() instead")

        if hasattr(plugin, "disable"):
            instance.log("top-level disable() function is obsolete, please use BasePlugin.disable() instead")

        if hasattr(instance, "LoadNotification"):
            instance.log("LoadNotification() is obsolete, please use init()")

        return instance

    def enable_plugin(self, plugin_name):

        # Our config file doesn't play nicely with some characters
        if "=" in plugin_name:
            log.add(
                _("Unable to load plugin %(name)s. Plugin folder name contains invalid characters: %(characters)s"), {
                    "name": plugin_name,
                    "characters": "="
                })
            return False

        if plugin_name in self.enabled_plugins:
            return False

        try:
            plugin = self._import_plugin_instance(plugin_name)

            if plugin is None:
                return False

            plugin.init()

            for command, data in plugin.commands.items():
                if not data:
                    continue

                disabled_interfaces = data.get("disable", [])

                if "group" not in data:
                    # Group commands under human-friendly plugin name by default
                    data["group"] = plugin.human_name

                for command_interface, command_list in self.commands.items():
                    if command_interface in disabled_interfaces:
                        continue

                    if command in command_list:
                        log.add(_("Conflicting %(interface)s command in plugin %(name)s: %(command)s"),
                                {"interface": command_interface, "name": plugin.human_name, "command": f"/{command}"})
                        continue

                    command_list[command] = data

            # Legacy commands
            for command_interface, attribute_name, plugin_commands in (
                ("chatroom", "__publiccommands__", plugin.__publiccommands__),
                ("private_chat", "__privatecommands__", plugin.__privatecommands__)
            ):
                interface_commands = self.commands.get(command_interface)

                for command, _func in plugin_commands:
                    if command not in interface_commands:
                        interface_commands[command] = None
                        plugin.log(f"/{command}: {attribute_name} is deprecated, please use the new "
                                   f"command system. See pynicotine/plugins/ in the Git repository for examples.")

            self.update_completions(plugin)

            if plugin_name not in config.sections["plugins"]["enabled"]:
                config.sections["plugins"]["enabled"].append(plugin_name)

            self.enabled_plugins[plugin_name] = plugin
            plugin.loaded_notification()

            log.add(_("Loaded plugin %s"), plugin.human_name)

        except Exception:
            from traceback import format_exc
            log.add(_("Unable to load plugin %(module)s\n%(exc_trace)s"),
                    {"module": plugin_name, "exc_trace": format_exc()})
            return False

        return True

    def list_installed_plugins(self):

        plugin_list = []

        for folder_path in self.plugin_folders:
            try:
                for entry in os.scandir(encode_path(folder_path)):
                    file_path = entry.name.decode("utf-8", "replace")

                    if file_path == "core_commands":
                        continue

                    if file_path == "now_playing_sender" and not self._load_now_playing_sender:
                        # MPRIS is not available on Windows and macOS
                        continue

                    if entry.is_dir() and file_path not in plugin_list:
                        plugin_list.append(file_path)

            except OSError:
                # Folder error, skip
                continue

        return plugin_list

    def disable_plugin(self, plugin_name, is_permanent=True):

        if plugin_name == "core_commands":
            return False

        if plugin_name not in self.enabled_plugins:
            return False

        plugin = self.enabled_plugins[plugin_name]
        plugin_path = None

        try:
            plugin_path = str(plugin.path)
            plugin.disable()

            for command, data in plugin.commands.items():
                for command_list in self.commands.values():
                    # Remove only if data matches command as defined in this plugin
                    if data and data == command_list.get(command):
                        del command_list[command]

            # Legacy commands
            for command_interface, plugin_commands in (
                ("chatroom", plugin.__publiccommands__),
                ("private_chat", plugin.__privatecommands__)
            ):
                interface_commands = self.commands.get(command_interface)

                for command, _func in plugin_commands:
                    if command in interface_commands and interface_commands.get(command) is None:
                        del interface_commands[command]

            self.update_completions(plugin)
            plugin.unloaded_notification()
            log.add(_("Unloaded plugin %s"), plugin.human_name)

        except Exception:
            from traceback import format_exc
            log.add(_("Unable to unload plugin %(module)s\n%(exc_trace)s"),
                    {"module": plugin_name, "exc_trace": format_exc()})
            return False

        finally:
            if not plugin_path:
                plugin_path = str(self.get_plugin_path(plugin_name))

            # Remove references to relative modules
            if plugin_path in sys.path:
                sys.path.remove(plugin_path)

            for name, module in sys.modules.copy().items():
                try:
                    if module.__file__.startswith(plugin_path):
                        sys.modules.pop(name, None)
                        del module

                except AttributeError:
                    # Builtin module
                    continue

            # Remove any event callbacks registered by the plugin
            for callbacks in events._callbacks.values():  # pylint: disable=protected-access
                for function in callbacks[:]:
                    if function.__module__ is not None and function.__module__.split(".", 1)[0] == plugin_name:
                        callbacks.remove(function)

            # Remove any event callbacks scheduled by the plugin
            for event_id, event in events._scheduler_events.copy().items():  # pylint: disable=protected-access
                function = event.callback

                if function is None:
                    continue

                if function.__module__ is not None and function.__module__.split(".", 1)[0] == plugin_name:
                    events.cancel_scheduled(event_id)

            if is_permanent and plugin_name in config.sections["plugins"]["enabled"]:
                config.sections["plugins"]["enabled"].remove(plugin_name)

            del self.enabled_plugins[plugin_name]
            del plugin

        return True

    def toggle_plugin(self, plugin_name):

        enabled = plugin_name in self.enabled_plugins

        if enabled:
            # Return False is plugin is unloaded
            return not self.disable_plugin(plugin_name)

        return self.enable_plugin(plugin_name)

    def reload_plugin(self, plugin_name):
        self.disable_plugin(plugin_name)
        self.enable_plugin(plugin_name)

    def get_plugin_settings(self, plugin_name):

        if plugin_name in self.enabled_plugins:
            plugin = self.enabled_plugins[plugin_name]

            if plugin.metasettings:
                return plugin.metasettings

        return None

    def get_plugin_info(self, plugin_name):

        plugin_info = {}
        plugin_path = self.get_plugin_path(plugin_name)

        if plugin_path is None:
            return plugin_info

        info_path = os.path.join(plugin_path, "PLUGININFO")

        with open(encode_path(info_path), encoding="utf-8") as file_handle:
            for line in file_handle:
                try:
                    key, _separator, value = line.partition("=")
                    key = key.strip()
                    value = value.strip()

                    # Translatable string
                    if value.startswith("_(") and value.endswith(")"):
                        plugin_info[key] = _(literal_eval(value[2:-1]))
                        continue

                    plugin_info[key] = literal_eval(value)

                except Exception:
                    pass  # this can happen on blank lines

        return plugin_info

    @staticmethod
    def show_plugin_error(plugin_name, error):

        from traceback import format_tb

        log.add(_("Plugin %(module)s failed with error %(errortype)s: %(error)s.\n"
                  "Trace: %(trace)s"), {
            "module": plugin_name,
            "errortype": type(error),
            "error": error,
            "trace": "".join(format_tb(error.__traceback__))
        })

    def plugin_settings(self, plugin_name, plugin):

        plugin_name = plugin_name.lower()

        if not plugin.settings:
            return

        previous_settings = config.sections["plugins"].get(plugin_name, {})

        for key in previous_settings:
            if key not in plugin.settings:
                log.add_debug("Stored setting '%s' is no longer present in the '%s' plugin",
                              (key, plugin_name))
                continue

            plugin.settings[key] = previous_settings[key]

        # Persist plugin settings in the config
        config.sections["plugins"][plugin_name] = plugin.settings

    def get_command_list(self, command_interface):
        """Returns a list of every command and alias available.

        Currently used for auto-completion in chats.
        """

        commands = []

        for command, data in self.commands.get(command_interface).items():
            commands.append(f"/{command} ")

            if not data:
                continue

            for alias in data.get("aliases", []):
                commands.append(f"/{alias} ")

        return commands

    def get_command_groups_data(self, command_interface, search_query=None):
        """Returns the available command groups and data of commands in them.

        Currently used for the /help command.
        """

        command_groups = defaultdict(list)

        for command, data in self.commands.get(command_interface).items():
            aliases = []
            parameters = []
            description = _("No description")
            group = _("Miscellaneous")

            if data:
                aliases = data.get("aliases", [])
                parameters = data.get(f"parameters_{command_interface}", data.get("parameters", []))
                description = data.get("description", description)
                group = data.get("group", group)

            if (search_query
                    and search_query not in group.lower()
                    and search_query not in command.lower()
                    and not any(search_query in alias for alias in aliases)
                    and not any(search_query in parameter for parameter in parameters)
                    and search_query not in description.lower()):
                continue

            command_groups[group].append((command, aliases, parameters, description))

        return command_groups

    def trigger_chatroom_command_event(self, room, command, args):
        return self._trigger_command(command, args, room=room)

    def trigger_private_chat_command_event(self, user, command, args):
        return self._trigger_command(command, args, user=user)

    def trigger_cli_command_event(self, command, args):
        return self._trigger_command(command, args)

    def _trigger_command(self, command, args, user=None, room=None):

        plugin = None
        command_found = False
        is_successful = False

        for module, plugin in self.enabled_plugins.items():
            if plugin is None:
                continue

            if room is not None:
                self.command_source = ("chatroom", room)
                legacy_commands = plugin.__publiccommands__

            elif user is not None:
                self.command_source = ("private_chat", user)
                legacy_commands = plugin.__privatecommands__

            else:
                self.command_source = ("cli", None)
                legacy_commands = []

            try:
                for trigger, data in plugin.commands.items():
                    aliases = data.get("aliases", [])

                    if command != trigger and command not in aliases:
                        continue

                    command_interface = self.command_source[0]
                    disabled_interfaces = data.get("disable", [])

                    if command_interface in disabled_interfaces:
                        continue

                    command_found = True
                    rejection_message = None
                    parameters = data.get(f"parameters_{command_interface}", data.get("parameters", []))
                    args_split = args.split()
                    num_args = len(args_split)
                    num_required_args = 0

                    for i, parameter in enumerate(parameters):
                        if parameter.startswith("<"):
                            num_required_args += 1

                        if num_args < num_required_args:
                            rejection_message = _("Missing %s argument") % parameter
                            break

                        if num_args <= i or "|" not in parameter:
                            continue

                        choices = parameter[1:-1].split("|")

                        if args_split[i] not in choices:
                            rejection_message = _("Invalid argument, possible choices: %s") % " | ".join(choices)
                            break

                    if rejection_message:
                        plugin.output(rejection_message)
                        plugin.output(_("Usage: %(command)s %(parameters)s") % {
                            "command": f"/{command}",
                            "parameters": " ".join(parameters)
                        })
                        break

                    callback = data.get(f"callback_{command_interface}", data.get("callback"))

                    if room is not None:
                        is_successful = callback(args, room=room)

                    elif user is not None:
                        is_successful = callback(args, user=user)

                    else:
                        is_successful = callback(args)

                    if is_successful is None:
                        # Command didn't return anything, default to success
                        is_successful = True

                if not command_found:
                    for trigger, func in legacy_commands:
                        if trigger == command:
                            func(self.command_source[1], args)
                            is_successful = True
                            command_found = True
                            break

            except Exception as error:
                self.show_plugin_error(module, error)
                plugin = None
                break

            if command_found:
                plugin = None
                break

        if plugin:
            plugin.output(_("Unknown command: %(command)s. Type %(help_command)s to list available commands.") % {
                "command": f"/{command}",
                "help_command": "/help"
            })

        self.command_source = None
        return is_successful

    def _trigger_event(self, function_name, args):
        """Triggers an event for the plugins.

        Since events and notifications are precisely the same except for
        how n+ responds to them, both can be triggered by this function.
        """

        for module, plugin in self.enabled_plugins.items():
            try:
                return_value = getattr(plugin, function_name)(*args)

            except Exception as error:
                self.show_plugin_error(module, error)
                continue

            if return_value is None:
                # Nothing changed, continue to the next plugin
                continue

            if isinstance(return_value, tuple):
                # The original args were modified, update them
                args = return_value
                continue

            if return_value == returncode["zap"]:
                return None

            if return_value == returncode["break"]:
                return args

            if return_value == returncode["pass"]:
                continue

            log.add_debug("Plugin %s returned something weird, '%s', ignoring", (module, return_value))

        return args

    def search_request_notification(self, searchterm, user, token):
        self._trigger_event("search_request_notification", (searchterm, user, token))

    def distrib_search_notification(self, searchterm, user, token):
        self._trigger_event("distrib_search_notification", (searchterm, user, token))

    def public_room_message_notification(self, room, user, line):
        self._trigger_event("public_room_message_notification", (room, user, line))

    def incoming_private_chat_event(self, user, line):
        if user != core.users.login_username:
            # dont trigger the scripts on our own talking - we've got "Outgoing" for that
            return self._trigger_event("incoming_private_chat_event", (user, line))

        return user, line

    def incoming_private_chat_notification(self, user, line):
        self._trigger_event("incoming_private_chat_notification", (user, line))

    def incoming_public_chat_event(self, room, user, line):
        return self._trigger_event("incoming_public_chat_event", (room, user, line))

    def incoming_public_chat_notification(self, room, user, line):
        self._trigger_event("incoming_public_chat_notification", (room, user, line))

    def outgoing_private_chat_event(self, user, line):
        if line is not None:
            # if line is None nobody actually said anything
            return self._trigger_event("outgoing_private_chat_event", (user, line))

        return user, line

    def outgoing_private_chat_notification(self, user, line):
        self._trigger_event("outgoing_private_chat_notification", (user, line))

    def outgoing_public_chat_event(self, room, line):
        return self._trigger_event("outgoing_public_chat_event", (room, line))

    def outgoing_public_chat_notification(self, room, line):
        self._trigger_event("outgoing_public_chat_notification", (room, line))

    def outgoing_global_search_event(self, text):
        return self._trigger_event("outgoing_global_search_event", (text,))

    def outgoing_room_search_event(self, rooms, text):
        return self._trigger_event("outgoing_room_search_event", (rooms, text))

    def outgoing_buddy_search_event(self, text):
        return self._trigger_event("outgoing_buddy_search_event", (text,))

    def outgoing_user_search_event(self, users, text):
        return self._trigger_event("outgoing_user_search_event", (users, text))

    def outgoing_wishlist_search_event(self, text):
        return self._trigger_event("outgoing_wishlist_search_event", (text,))

    def user_resolve_notification(self, user, ip_address, port, country=None):
        """Notification for user IP:Port resolving.

        Note that country is only set when the user requested the
        resolving
        """
        self._trigger_event("user_resolve_notification", (user, ip_address, port, country))

    def server_connect_notification(self):
        self._trigger_event("server_connect_notification", (),)

    def server_disconnect_notification(self, userchoice):
        self._trigger_event("server_disconnect_notification", (userchoice, ))

    def join_chatroom_notification(self, room):
        self._trigger_event("join_chatroom_notification", (room,))

    def leave_chatroom_notification(self, room):
        self._trigger_event("leave_chatroom_notification", (room,))

    def user_join_chatroom_notification(self, room, user):
        self._trigger_event("user_join_chatroom_notification", (room, user,))

    def user_leave_chatroom_notification(self, room, user):
        self._trigger_event("user_leave_chatroom_notification", (room, user,))

    def user_stats_notification(self, user, stats):
        self._trigger_event("user_stats_notification", (user, stats))

    def user_status_notification(self, user, status, privileged):
        self._trigger_event("user_status_notification", (user, status, privileged))

    def upload_queued_notification(self, user, virtual_path, real_path):
        self._trigger_event("upload_queued_notification", (user, virtual_path, real_path))

    def upload_started_notification(self, user, virtual_path, real_path):
        self._trigger_event("upload_started_notification", (user, virtual_path, real_path))

    def upload_finished_notification(self, user, virtual_path, real_path):
        self._trigger_event("upload_finished_notification", (user, virtual_path, real_path))

    def download_started_notification(self, user, virtual_path, real_path):
        self._trigger_event("download_started_notification", (user, virtual_path, real_path))

    def download_finished_notification(self, user, virtual_path, real_path):
        self._trigger_event("download_finished_notification", (user, virtual_path, real_path))

    def shutdown_notification(self):
        self._trigger_event("shutdown_notification", (),)
