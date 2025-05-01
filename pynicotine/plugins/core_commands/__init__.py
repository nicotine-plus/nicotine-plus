# COPYRIGHT (C) 2022-2024 Nicotine+ Contributors
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

from pynicotine.pluginsystem import BasePlugin
from pynicotine.shares import PermissionLevel
from pynicotine.slskmessages import UserStatus


class _CommandGroup:
    CHAT = _("Chat")
    CHAT_ROOMS = _("Chat Rooms")
    PRIVATE_CHAT = _("Private Chat")
    NETWORK_FILTERS = _("Network Filters")
    SEARCH_FILES = _("Search Files")
    SHARES = _("Shares")
    USERS = _("Users")


class Plugin(BasePlugin):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.commands = {
            "help": {
                "aliases": ["?"],
                "callback": self.help_command,
                "description": _("List available commands"),
                "parameters": ["[query]"]
            },
            "connect": {
                "callback": self.connect_command,
                "description": _("Connect to the server"),
            },
            "disconnect": {
                "callback": self.disconnect_command,
                "description": _("Disconnect from the server"),
            },
            "away": {
                "aliases": ["a"],
                "callback": self.away_command,
                "description": _("Toggle away status"),
            },
            "plugin": {
                "callback": self.plugin_handler_command,
                "description": _("Manage plugins"),
                "parameters": ["<toggle|reload|info>", "<plugin name>"]
            },
            "quit": {
                "aliases": ["q", "exit"],
                "callback": self.quit_command,
                "description": _("Quit Nicotine+"),
                "parameters": ["[force]"]
            },
            "clear": {
                "aliases": ["cl"],
                "callback": self.clear_command,
                "description": _("Clear chat window"),
                "disable": ["cli"],
                "group": _CommandGroup.CHAT,
            },
            "me": {
                "callback": self.me_command,
                "description": _("Say something in the third-person"),
                "disable": ["cli"],
                "group": _CommandGroup.CHAT,
                "parameters": ["<something..>"]
            },
            "now": {
                "callback": self.now_command,
                "description": _("Announce the song currently playing"),
                "disable": ["cli"],
                "group": _CommandGroup.CHAT
            },
            "join": {
                "aliases": ["j"],
                "callback": self.join_command,
                "description": _("Join chat room"),
                "disable": ["cli"],
                "group": _CommandGroup.CHAT_ROOMS,
                "parameters": ["<room>"]
            },
            "leave": {
                "aliases": ["l"],
                "callback": self.leave_command,
                "description": _("Leave chat room"),
                "disable": ["cli"],
                "group": _CommandGroup.CHAT_ROOMS,
                "parameters": ["<room>"],
                "parameters_chatroom": ["[room]"]
            },
            "say": {
                "callback": self.say_command,
                "description": _("Say message in specified chat room"),
                "disable": ["cli"],
                "group": _CommandGroup.CHAT_ROOMS,
                "parameters": ["<room>", "<message..>"]
            },
            "pm": {
                "callback": self.pm_command,
                "description": _("Open private chat"),
                "disable": ["cli"],
                "group": _CommandGroup.PRIVATE_CHAT,
                "parameters": ["<user>"]
            },
            "close": {
                "aliases": ["c"],
                "callback": self.close_command,
                "description": _("Close private chat"),
                "disable": ["cli"],
                "group": _CommandGroup.PRIVATE_CHAT,
                "parameters_chatroom": ["<user>"],
                "parameters_private_chat": ["[user]"]
            },
            "ctcpversion": {
                "callback": self.ctcpversion_command,
                "description": _("Request user's client version"),
                "disable": ["cli"],
                "group": _CommandGroup.PRIVATE_CHAT,
                "parameters_chatroom": ["<user>"],
                "parameters_private_chat": ["[user]"]
            },
            "msg": {
                "aliases": ["m"],
                "callback": self.msg_command,
                "description": _("Send private message to user"),
                "disable": ["cli"],
                "group": _CommandGroup.PRIVATE_CHAT,
                "parameters": ["<user>", "<message..>"]
            },
            "add": {
                "aliases": ["buddy"],
                "callback": self.add_buddy_command,
                "description": _("Add user to buddy list"),
                "group": _CommandGroup.USERS,
                "parameters": ["<user>"],
                "parameters_private_chat": ["[user]"]
            },
            "rem": {
                "aliases": ["unbuddy"],
                "callback": self.remove_buddy_command,
                "description": _("Remove buddy from buddy list"),
                "group": _CommandGroup.USERS,
                "parameters": ["<user>"],
                "parameters_private_chat": ["[user]"]
            },
            "browse": {
                "aliases": ["b"],
                "callback": self.browse_user_command,
                "description": _("Browse files of user"),
                "disable": ["cli"],
                "group": _CommandGroup.USERS,
                "parameters": ["<user>"],
                "parameters_private_chat": ["[user]"]
            },
            "whois": {
                "aliases": ["info", "w"],
                "callback": self.whois_command,
                "description": _("Show user profile information"),
                "disable": ["cli"],
                "group": _CommandGroup.USERS,
                "parameters": ["<user>"],
                "parameters_private_chat": ["[user]"]
            },
            "ip": {
                "callback": self.ip_address_command,
                "description": _("Show IP address or username"),
                "group": _CommandGroup.NETWORK_FILTERS,
                "parameters": ["<user or ip>"],
                "parameters_private_chat": ["[user or ip]"]
            },
            "ban": {
                "callback": self.ban_command,
                "description": _("Block connections from user or IP address"),
                "group": _CommandGroup.NETWORK_FILTERS,
                "parameters": ["<user or ip>"],
                "parameters_private_chat": ["[user or ip]"]
            },
            "unban": {
                "callback": self.unban_command,
                "description": _("Remove user or IP address from ban lists"),
                "group": _CommandGroup.NETWORK_FILTERS,
                "parameters": ["<user or ip>"],
                "parameters_private_chat": ["[user or ip]"]
            },
            "ignore": {
                "callback": self.ignore_command,
                "description": _("Silence messages from user or IP address"),
                "disable": ["cli"],
                "group": _CommandGroup.NETWORK_FILTERS,
                "parameters": ["<user or ip>"],
                "parameters_private_chat": ["[user or ip]"]
            },
            "unignore": {
                "callback": self.unignore_command,
                "description": _("Remove user or IP address from ignore lists"),
                "disable": ["cli"],
                "group": _CommandGroup.NETWORK_FILTERS,
                "parameters": ["<user or ip>"],
                "parameters_private_chat": ["[user or ip]"]
            },
            "share": {
                "callback": self.share_command,
                "description": _("Add share"),
                "group": _CommandGroup.SHARES,
                "parameters": ["<public|buddy|trusted>", "<folder path>"]
            },
            "unshare": {
                "callback": self.unshare_command,
                "description": _("Remove share"),
                "group": _CommandGroup.SHARES,
                "parameters": ["<virtual name or folder path>"]
            },
            "shares": {
                "aliases": ["ls"],
                "callback": self.list_shares_command,
                "description": _("List shares"),
                "group": _CommandGroup.SHARES,
                "parameters": ["[public|buddy|trusted]"]
            },
            "rescan": {
                "callback": self.rescan_command,
                "description": _("Rescan shares"),
                "group": _CommandGroup.SHARES,
                "parameters": ["[force|rebuild]"]
            },
            "search": {
                "aliases": ["s"],
                "callback": self.search_command,
                "description": _("Start global file search"),
                "disable": ["cli"],
                "group": _CommandGroup.SEARCH_FILES,
                "parameters": ["<query>"]
            },
            "rsearch": {
                "aliases": ["rs"],
                "callback": self.search_rooms_command,
                "description": _("Search files in joined rooms"),
                "disable": ["cli"],
                "group": _CommandGroup.SEARCH_FILES,
                "parameters": ["<query>"]
            },
            "bsearch": {
                "aliases": ["bs"],
                "callback": self.search_buddies_command,
                "description": _("Search files of all buddies"),
                "disable": ["cli"],
                "group": _CommandGroup.SEARCH_FILES,
                "parameters": ["<query>"]
            },
            "usearch": {
                "aliases": ["us"],
                "callback": self.search_user_command,
                "description": _("Search a user's shared files"),
                "disable": ["cli"],
                "group": _CommandGroup.SEARCH_FILES,
                "parameters": ["<user>", "<query>"]
            }
        }

    # Application Commands #

    def help_command(self, args, user=None, room=None):

        if user is not None:
            command_interface = "private_chat"

        elif room is not None:
            command_interface = "chatroom"

        else:
            command_interface = "cli"

        search_query = " ".join(args.lower().split(" ", maxsplit=1))
        command_groups = self.parent.get_command_groups_data(command_interface, search_query=search_query)
        num_commands = sum(len(command_groups[x]) for x in command_groups)
        output_text = ""

        if not search_query:
            output_text += _("Listing %(num)i available commands:") % {"num": num_commands}
        else:
            output_text += _('Listing %(num)i available commands matching "%(query)s":') % {
                "num": num_commands,
                "query": search_query
            }

        for group_name, command_data in command_groups.items():
            output_text += f"\n\n{group_name}:"

            for command, aliases, parameters, description in command_data:
                command_message = f"/{', /'.join([command] + aliases)} {' '.join(parameters)}".strip()
                output_text += f"\n\t{command_message}  -  {description}"

        if not search_query:
            output_text += "\n\n" + _("Type %(command)s to list similar commands") % {"command": "/help [query]"}

        elif not num_commands:
            output_text += "\n" + _("Type %(command)s to list available commands") % {"command": "/help"}

        self.output(output_text)

    def connect_command(self, _args, **_unused):
        if self.core.users.login_status == UserStatus.OFFLINE:
            self.core.connect()

    def disconnect_command(self, _args, **_unused):
        if self.core.users.login_status != UserStatus.OFFLINE:
            self.core.disconnect()

    def away_command(self, _args, **_unused):

        if self.core.users.login_status == UserStatus.OFFLINE:
            self.output(_("%(user)s is offline") % {"user": self.config.sections["server"]["login"]})
            return

        self.core.users.set_away_mode(self.core.users.login_status != UserStatus.AWAY, save_state=True)

        if self.core.users.login_status == UserStatus.ONLINE:
            self.output(_("%(user)s is online") % {"user": self.core.users.login_username})
        else:
            self.output(_("%(user)s is away") % {"user": self.core.users.login_username})

    def quit_command(self, args, **_unused):

        force = (args.lstrip("-") in {"force", "f"})

        if force:
            self.core.quit()
        else:
            self.core.confirm_quit()

    # Chat #

    def clear_command(self, _args, user=None, room=None):

        if room is not None:
            self.core.chatrooms.clear_room_messages(room)

        elif user is not None:
            self.core.privatechat.clear_private_messages(user)

    def me_command(self, args, **_unused):
        self.send_message("/me " + args)  # /me is sent as plain text

    def now_command(self, _args, **_unused):
        self.core.now_playing.display_now_playing(callback=self.send_message)

    # Chat Rooms #

    def join_command(self, args, **_unused):
        room = self.core.chatrooms.sanitize_room_name(args)
        self.core.chatrooms.show_room(room)

    def leave_command(self, args, room=None, **_unused):

        if args:
            room = args

        if room not in self.core.chatrooms.joined_rooms:
            self.output(_("Not joined in room %s") % room)
            return False

        self.core.chatrooms.remove_room(room)
        return True

    def say_command(self, args, **_unused):

        room, text = args.split(maxsplit=1)

        if room not in self.core.chatrooms.joined_rooms:
            self.output(_("Not joined in room %s") % room)
            return False

        self.send_public(room, text)
        return True

    # Private Chat #

    def pm_command(self, args, **_unused):
        self.core.privatechat.show_user(args)

    def close_command(self, args, user=None, **_unused):

        if args:
            user = args

        if user not in self.core.privatechat.users:
            self.output(_("Not messaging with user %s") % user)
            return False

        self.core.privatechat.remove_user(user)
        self.output(_("Closed private chat of user %s") % user)
        return True

    def ctcpversion_command(self, args, user=None, **_unused):

        if args:
            user = args

        self.send_private(user, self.core.privatechat.CTCP_VERSION, show_ui=True)

    def msg_command(self, args, **_unused):
        user, text = args.split(maxsplit=1)
        self.send_private(user, text, show_ui=True, switch_page=False)

    # Users #

    def add_buddy_command(self, args, user=None, **_unused):

        if args:
            user = args

        self.core.buddies.add_buddy(user)

    def remove_buddy_command(self, args, user=None, **_unused):

        if args:
            user = args

        self.core.buddies.remove_buddy(user)

    def browse_user_command(self, args, user=None, **_unused):

        if args:
            user = args

        self.core.userbrowse.browse_user(user)

    def whois_command(self, args, user=None, **_unused):

        if args:
            user = args

        self.core.userinfo.show_user(user)

    # Network Filters #

    def ip_address_command(self, args, user=None, **_unused):

        if self.core.network_filter.is_ip_address(args):
            self.output(self.core.network_filter.get_online_username(args))
            return

        if args:
            user = args

        self.core.users.request_ip_address(user, notify=True)

    def ban_command(self, args, user=None, **_unused):

        if self.core.network_filter.is_ip_address(args):
            banned_ip_address = self.core.network_filter.ban_user_ip(ip_address=args)
        else:
            if args:
                user = args

            banned_ip_address = None
            self.core.network_filter.ban_user(user)

        self.output(_("Banned %s") % (banned_ip_address or user))

    def unban_command(self, args, user=None, **_unused):

        if self.core.network_filter.is_ip_address(args):
            unbanned_ip_addresses = self.core.network_filter.unban_user_ip(ip_address=args)
            self.core.network_filter.unban_user(self.core.network_filter.get_online_username(args))
        else:
            if args:
                user = args

            unbanned_ip_addresses = self.core.network_filter.unban_user_ip(user)
            self.core.network_filter.unban_user(user)

        self.output(_("Unbanned %s") % (" & ".join(unbanned_ip_addresses) or user))

    def ignore_command(self, args, user=None, **_unused):

        if self.core.network_filter.is_ip_address(args):
            ignored_ip_address = self.core.network_filter.ignore_user_ip(ip_address=args)
        else:
            if args:
                user = args

            ignored_ip_address = None
            self.core.network_filter.ignore_user(user)

        self.output(_("Ignored %s") % (ignored_ip_address or user))

    def unignore_command(self, args, user=None, **_unused):

        if self.core.network_filter.is_ip_address(args):
            unignored_ip_addresses = self.core.network_filter.unignore_user_ip(ip_address=args)
            self.core.network_filter.unignore_user(self.core.network_filter.get_online_username(args))
        else:
            if args:
                user = args

            unignored_ip_addresses = self.core.network_filter.unignore_user_ip(user)
            self.core.network_filter.unignore_user(user)

        self.output(_("Unignored %s") % (" & ".join(unignored_ip_addresses) or user))

    # Configure Shares #

    def rescan_command(self, args, **_unused):

        rebuild = ("rebuild" in args)
        force = ("force" in args) or rebuild

        self.core.shares.rescan_shares(rebuild=rebuild, force=force)

    def list_shares_command(self, args, **_unused):

        permission_levels = {
            0: PermissionLevel.PUBLIC,
            1: PermissionLevel.BUDDY,
            2: PermissionLevel.TRUSTED
        }
        share_groups = self.core.shares.get_shared_folders()
        num_total = num_listed = 0

        for group_index, share_group in enumerate(share_groups):
            permission_level = permission_levels.get(group_index)
            num_shares = len(share_group)
            num_total += num_shares

            if not num_shares or args and permission_level not in args.lower():
                continue

            self.output("\n" + f"{num_shares} {permission_level} shares:")

            for virtual_name, folder_path, *_ignored in share_group:
                self.output(f'• "{virtual_name}" {folder_path}')

            num_listed += num_shares

        self.output("\n" + _("%(num_listed)s shares listed (%(num_total)s configured)") % {
            "num_listed": num_listed,
            "num_total": num_total
        })

    def share_command(self, args, **_unused):

        permission_level, folder_path = args.split(maxsplit=1)
        folder_path = folder_path.strip(' "')
        virtual_name = self.core.shares.add_share(folder_path, permission_level=permission_level)

        if not virtual_name:
            self.output(_("Cannot share inaccessible folder \"%s\"") % folder_path)
            return False

        self.output(_("Added %(group_name)s share \"%(virtual_name)s\" (rescan required)") % {
            "group_name": permission_level,
            "virtual_name": virtual_name
        })
        return True

    def unshare_command(self, args, **_unused):

        virtual_name_or_folder_path = args.strip(' "')

        if not self.core.shares.remove_share(virtual_name_or_folder_path):
            self.output(_("No share with name \"%s\"") % virtual_name_or_folder_path)
            return False

        self.output(_("Removed share \"%s\" (rescan required)") % virtual_name_or_folder_path)
        return True

    # Search Files #

    def search_command(self, args, **_unused):
        self.core.search.do_search(args, "global")

    def search_rooms_command(self, args, **_unused):
        self.core.search.do_search(args, "rooms")

    def search_buddies_command(self, args, **_unused):
        self.core.search.do_search(args, "buddies")

    def search_user_command(self, args, **_unused):
        user, query = args.split(maxsplit=1)
        self.core.search.do_search(query, "user", users=[user])

    # Plugin Commands #

    def plugin_handler_command(self, args, **_unused):

        action, plugin_name = args.split(maxsplit=1)

        if action == "toggle":
            self.parent.toggle_plugin(plugin_name)

        elif action == "reload":
            self.parent.reload_plugin(plugin_name)

        elif action == "info":
            plugin_info = self.parent.get_plugin_info(plugin_name)

            for key, value in plugin_info.items():
                self.output(f"• {key}: {value}")
