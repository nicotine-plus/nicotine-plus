# COPYRIGHT (C) 2022 Nicotine+ Contributors
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


class Plugin(BasePlugin):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.commands = {
            "help": {
                "aliases": ["?"],
                "callback": self.help_command,
                "description": "List commands",
                "usage": ["[query]"]
            },
            "rescan": {
                "callback": self.rescan_command,
                "description": _("Rescan shares"),
                "group": _("Configure Shares"),
                "usage": ["[-force]"]
            },
            "hello": {
                "aliases": ["echo", "greet"],
                "callback": self.hello_command,
                "description": "Print something",
                "group": _("Message"),
                "usage": ["[something..]"]
            },
            "away": {
                "aliases": ["a"],
                "callback": self.away_command,
                "description": _("Toggle away status")
            },
            "plugin": {
                "callback": self.plugin_handler_command,
                "description": _("Load or unload a plugin"),
                "usage": ["<toggle|enable|disable>", "<plugin_name>"]
            },
            "quit": {
                "aliases": ["q", "exit"],
                "callback": self.quit_command,
                "description": _("Quit Nicotine+"),
                "usage": ["[-force]"]
            },
            "clear": {
                "aliases": ["cl"],
                "callback": self.clear_command,
                "description": _("Clear chat window"),
                "disable": ["cli"],
                "group": _("Chat"),
            },
            "ctcp": {
                "callback": self.ctcp_command,
                "description": _("Send client-to-client protocol query"),
                "disable": ["cli"],
                "group": _("Chat"),
                "usage": ["<version|ping>", "[user]"]
            },
            "join": {
                "aliases": ["j"],
                "callback": self.join_chat_command,
                "description": _("Join chat room"),
                "disable": ["cli"],
                "group": _("Chat Rooms"),
                "usage": ["<room>"]
            },
            "me": {
                "callback": self.me_chat_command,
                "description": _("Say something in the third-person"),
                "disable": ["cli"],
                "group": _("Chat"),
                "usage": ["<something..>"]
            },
            "msg": {
                "aliases": ["m"],
                "callback": self.msg_chat_command,
                "description": _("Send private message to user"),
                "disable": ["cli"],
                "group": _("Private Chat"),
                "usage": ["<user>", "<message..>"]
            },
            "pm": {
                "callback": self.pm_chat_command,
                "description": _("Open private chat window for user"),
                "disable": ["cli"],
                "group": _("Private Chat"),
                "usage": ["<user>"]
            },
            "say": {
                "callback": self.say_chat_command,
                "description": _("Say message in specified chat room"),
                "disable": ["cli"],
                "group": _("Chat Rooms"),
                "usage": ["<room>", "<message..>"]
            },
            "close": {
                "aliases": ["c"],
                "callback": self.close_command,
                "description": _("Close private chat"),
                "disable": ["cli"],
                "group": _("Private Chat"),
                "usage": ["<user>"],
                "usage_private_chat": ["[user]"]
            },
            "leave": {
                "aliases": ["l"],
                "callback": self.leave_command,
                "description": _("Leave chat room"),
                "disable": ["cli"],
                "group": _("Chat Rooms"),
                "usage": ["<room>"],
                "usage_chatroom": ["[room]"]
            },
            "now": {
                "callback": self.now_playing_command,
                "description": _("Display the Now Playing script's output"),
                # "disable": ["cli"],
                "group": _("Now Playing"),
            },
            "add": {
                "aliases": ["buddy"],
                "callback": self.add_buddy_command,
                "description": _("Add user to buddy list"),
                "group": _("Users"),
                "usage": ["<user>"],
                "usage_private_chat": ["[user]"]
            },
            "rem": {
                "aliases": ["unbuddy"],
                "callback": self.remove_buddy_command,
                "description": _("Remove user from buddy list"),
                "group": _("Users"),
                "usage": ["<buddy>"],
                "usage_private_chat": ["[buddy]"]
            },
            "ban": {
                "callback": self.ban_user_command,
                "description": _("Stop connections from user"),
                "group": _("Users"),
                "usage": ["<user>"],
                "usage_private_chat": ["[user]"]
            },
            "unban": {
                "callback": self.unban_user_command,
                "description": _("Remove user from ban list"),
                "group": _("Users"),
                "usage": ["<user>"],
                "usage_private_chat": ["[user]"]
            },
            "block": {  # new
                "callback": self.ban_user_ip_command,
                "description": _("Stop all connections from same IP as user"),
                "group": _("Network Filters"),
                "usage": ["<user>"],
                "usage_private_chat": ["[user]"]
            },
            "unblock": {  # new
                "callback": self.unban_user_ip_command,
                "description": _("Remove user's IP address from block list"),
                "group": _("Network Filters"),
                "usage": ["<user>"],
                "usage_private_chat": ["[user]"]
            },
            "ignore": {
                "callback": self.ignore_user_command,
                "description": _("Silence chat messages from user"),
                "disable": ["cli"],
                "group": _("Users"),
                "usage": ["<user>"],
                "usage_private_chat": ["[user]"]
            },
            "unignore": {
                "callback": self.unignore_user_command,
                "description": _("Remove user from chat ignore list"),
                "disable": ["cli"],
                "group": _("Users"),
                "usage": ["<user>"],
                "usage_private_chat": ["[user]"]
            },
            "ignoreip": {
                "callback": self.ignore_user_ip_command,
                "description": _("Silence chat messages from IP address of user"),
                "disable": ["cli"],
                "group": _("Network Filters"),
                "usage": ["<user or ip>"],
                "usage_private_chat": ["[user]", "[ip]"]
            },
            "unignoreip": {  # new
                "callback": self.unignore_user_ip_command,
                "description": _("Remove user's IP address from chat ignore list"),
                "disable": ["cli"],
                "group": _("Network Filters"),
                "usage": ["<user or ip>"],
                "usage_private_chat": ["[user]", "[ip]"]
            },
            "ip": {
                "callback": self.ip_user_command,
                "description": _("Show IP address of user"),
                "group": _("Network Filters"),
                "usage": ["<user>"],
                "usage_private_chat": ["[user]"]
            },
            "whois": {
                "aliases": ["info", "w"],
                "callback": self.whois_user_command,
                "description": _("Show info about user"),
                "disable": ["cli"],
                "group": _("Users"),
                "usage": ["<user>"],
                "usage_private_chat": ["[user]"]
            },
            "browse": {
                "aliases": ["b"],
                "callback": self.browse_user_command,
                "description": _("Browse files of user"),
                "disable": ["cli"],
                "group": _("Users"),
                "usage": ["<user>"],
                "usage_private_chat": ["[user]"]
            },
            "search": {
                "aliases": ["s"],
                "callback": self.search_command,
                "description": _("Start global file search"),
                "disable": ["cli"],
                "group": _("Search Files"),
                "usage": ["<query>"]
            },
            "rsearch": {
                "aliases": ["rs"],
                "callback": self.search_rooms_command,
                "description": _("Search files in joined rooms"),
                "disable": ["cli"],
                "group": _("Search Files"),
                "usage": ["<query>"]
            },
            "bsearch": {
                "aliases": ["bs"],
                "callback": self.search_buddies_command,
                "description": _("Search files of all buddies"),
                "disable": ["cli"],
                "group": _("Search Files"),
                "usage": ["<query>"]
            },
            "usearch": {
                "aliases": ["us"],
                "callback": self.search_user_command,
                "description": _("Search a user's shared files"),
                "disable": ["cli"],
                "group": _("Search Files"),
                "usage": ["<\"user name\">", "<query>"]
            },
            "shares": {
                "aliases": ["ls"],
                "callback": self.list_shares_command,
                "description": _("List configured shares"),
                "group": _("Configure Shares")
            },
            "share": {
                "callback": self.share_command,
                "description": _("Add share"),
                "group": _("Configure Shares"),
                "usage": ["<public|buddy>", "<folder path>"]
            },
            "unshare": {
                "callback": self.unshare_command,
                "description": _("Remove share"),
                "group": _("Configure Shares"),
                "usage": ["<public|buddy>", "<virtual name>"]
            }
        }

    def help_command(self, args, user=None, room=None):

        if user is not None:
            command_list = self.parent.private_chat_commands
            interface = "private_chat"  # _("_")
            prefix = "/"

        elif room is not None:
            command_list = self.parent.chatroom_commands
            interface = "chatroom"
            prefix = "/"

        else:
            command_list = self.parent.cli_commands
            interface = "cli"
            prefix = ""

        query = args.split(" ", maxsplit=1)[0].lower().lstrip("/")
        command_groups = {}
        num_commands = 0

        for command, data in command_list.items():
            command_message = command
            aliases = f", {prefix}".join(data.get("aliases", []))
            description = data.get("description", "No description")
            group = data.get("group", f"{self.config.application_name} {_('Commands')}")
            usage = " ".join(data.get(f"usage_{interface}", data.get("usage", [])))

            if aliases:
                command_message += f", {prefix}" + aliases

            if usage:
                command_message += " " + usage

            if args and query not in command_message and query not in group.lower():
                continue

            num_commands += 1

            if interface == "cli":
                # Improved layout for fixed width output
                command_message = command_message.lstrip("/").ljust(24)

            if group not in command_groups:
                command_groups[group] = []

            command_groups[group].append(f"    {command_message}  -  {description}")

        if not num_commands:
            self.output(f"Unknown command: {prefix}{query}. Type {prefix}help for a list of commands.")
            return False

        output = f"Listing {num_commands} {interface} commands"

        if query:
            output += " " + f"matching \"{query}\":"
        else:
            output += ":"

        for group, commands in command_groups.items():
            output += "\n\n" + "  " + group + ":"

            for command in commands:
                output += "\n" + command

        output += "\n"

        if not query:
            output += "\n" + f"Type {prefix}help [query] (without brackets) to list similar commands or aliases"

        if prefix:
            output += "\n" + "Start a command using / (forward slash)"

        self.output(output)
        return True

    """ "Chats" """

    def clear_command(self, _args, user=None, room=None):

        if args:
            return

        if room is not None:
            self.core.chatrooms.clear_room_messages(room)

        elif user is not None:
            self.core.privatechat.clear_private_messages(user)

    def close_command(self, args, user=None, **_unused):

        if args:
            user = args

        if user not in self.core.privatechat.users:
            self.output(_("Not messaging with user %s") % user)
            return False

        self.output(_("Closing private chat of user %s") % user)
        self.core.privatechat.remove_user(user)
        return True

    def ctcp_command(self, args, user=None, **_unused):

        args_split = args.split(maxsplit=1)
        ctcp_query = getattr(self.core.privatechat, f"CTCP_{args_split[0].upper()}")

        if len(args_split) > 1:
            user = args_split[1]

        elif user is None:
            user = self.core.login_username

        self.send_private(user, ctcp_query)

    def join_chat_command(self, args, **_unused):
        self.core.chatrooms.show_room(args)

    def leave_command(self, args, room=None, **_unused):

        if args:
            room = args

        if room not in self.core.chatrooms.joined_rooms:
            self.output(_("Not joined in room %s") % room)
            return False

        self.core.chatrooms.remove_room(room)
        return True

    def me_chat_command(self, args, **_unused):
        self.send_message("/me " + args)  # /me is sent as plain text

    def msg_chat_command(self, args, **_unused):

        args_split = args.split(maxsplit=1)
        user, text = args_split[0], args_split[1]

        self.send_private(user, text, show_ui=True, switch_page=False)

    def pm_chat_command(self, args, **_unused):
        self.core.privatechat.show_user(args)

    def say_chat_command(self, args, **_unused):

        args_split = args.split(maxsplit=1)
        room, text = args_split[0], args_split[1]

        self.send_public(room, text)

    """ "Now Playing" """

    def now_playing_command(self, _args, **_unused):
        # TODO: Untested, move np into a new plugin
        self.core.now_playing.display_now_playing(
            callback=lambda np_message: self.echo_message(np_message))

    """ "Configure Shares" """

    def rescan_command(self, args, **_unused):

        force = (args.lstrip("- ") in ("force", "f"))

        if args and not force:
            self.output("Invalid option")
            return False

        self.core.shares.rescan_shares(force=force)
        return True

    def list_shares_command(self, _args, **_unused):
        # TODO: self.output(self.core.shares.list_shares())
        #       (Status) Group "Virtual Name" Folder Path

        self.output("Not implemented")

    def share_command(self, args, **_unused):

        args_split = args.split(maxsplit=1)
        group, path = args_split[0], args_split[1]

        # TODO: self.core.shares.add_share()
        #       "virtual name" can be derived from the entered folder,
        #       so that it's not needed to specify a string manually.

        # TODO: remove this debug output line
        self.output(f"Not implemented. Entered arguments: group='{group}' path='{path}'")

    def unshare_command(self, args, **_unused):

        args_split = args.split(maxsplit=1)
        group, name = args_split[0], args_split[1]

        # TODO: self.core.shares.remove_share()
        # TODO: remove this debug output line
        self.output(f"Not implemented. Entered arguments: group='{group}' name='{name}'")

    """ "Users" """

    def add_buddy_command(self, args, user=None, **_unused):

        if args:
            user = args

        self.core.userlist.add_buddy(user)

    def remove_buddy_command(self, args, user=None, **_unused):

        if args:
            user = args

        self.core.userlist.remove_buddy(user)

    def ban_user_command(self, args, user=None, **_unused):

        if args:
            user = args

        self.core.network_filter.ban_user(user)

    def unban_user_command(self, args, user=None, **_unused):

        if args:
            user = args

        self.core.network_filter.unban_user(user)

    def ban_user_ip_command(self, args, user=None, **_unused):

        if args:
            user = args

        self.core.network_filter.ban_user_ip(user)

    def unban_user_ip_command(self, args, user=None, **_unused):

        if args:
            user = args

        self.core.network_filter.unban_user_ip(user)

    def ignore_user_command(self, args, user=None, **_unused):

        if args:
            user = args

        self.core.network_filter.ignore_user(user)

    def unignore_user_command(self, args, user=None, **_unused):

        if args:
            user = args

        self.core.network_filter.unignore_user(user)

    def ignore_user_ip_command(self, args, user=None, **_unused):

        if self.is_ip_address(args):
            self.core.network_filter.ignore_ip(args)
            return

        if args:
            user = args

        self.core.network_filter.ignore_user_ip(user)

    def unignore_user_ip_command(self, args, user=None, **_unused):

        if self.is_ip_address(args):
            # TODO: self.core.network_filter.unignore_ip(args)
            self.output(f"Not implemented (unignore by ip), entered arguments: ip_address='{args}' is_ip_address=True")
            return

        if args:
            user = args

        self.core.network_filter.unignore_user_ip(user)

    @staticmethod
    def is_ip_address(ip_address):

        if not ip_address or ip_address.count(".") != 3:
            return False

        for part in ip_address.split("."):
            if part == "*":
                continue

            if not part.isdigit():
                return False

            if 0 > int(part) > 255:
                return False

        return True

    def ip_user_command(self, args, user=None, **_unused):

        if args:
            user = args

        self.core.request_ip_address(user)

    def whois_user_command(self, args, user=None, **_unused):

        if args:
            user = args

        self.core.userinfo.show_user(user)

    def browse_user_command(self, args, user=None, **_unused):

        if args:
            user = args

        self.core.userbrowse.browse_user(user)

    """ "Search" """

    def search_user_command(self, args, user=None, **_unused):

        from shlex import split

        try:
            args_split = split(args)

        except ValueError as error:
            self.output(error)
            return False

        # Support "user name" with spaces in optional quotes
        user = args_split[0]

        # Don't require quotes around search term query
        if len(args_split) == 2:
            query = args_split[1]
        else:
            query = args.strip('" ')[len(user):].strip('" ')

        # TODO: remove this debug output line
        self.output(f"Entered arguments: user='{user}' query='{query}'")

        self.core.search.do_search(query, "user", user=user)
        return True

    def search_command(self, args, **_unused):
        self.core.search.do_search(args, "global")

    def search_rooms_command(self, args, **_unused):
        self.core.search.do_search(args, "rooms")

    def search_buddies_command(self, args, **_unused):
        self.core.search.do_search(args, "buddies")

    """ Application Core "Commands" """

    def away_command(self, _args, **_unused):
        self.core.set_away_mode(self.core.user_status != 1, save_state=True)  # 1 = UserStatus.AWAY
        self.output(_("Status is now %s") % (_("Online") if self.core.user_status == 2 else _("Away")))

    def hello_command(self, args, **_unused):
        self.output(_("Hello there!") + " " + args)

    def plugin_handler_command(self, args, **_unused):

        args_split = args.split(maxsplit=1)
        action, plugin_name = args_split[0], args_split[1].strip('"')
        func = getattr(self.parent, f"{action}_plugin")

        return func(plugin_name)

    def quit_command(self, args, user=None, room=None):

        force = (args.lstrip("- ") in ("force", "f"))

        if args and not force:
            self.output("Invalid option")
            return False

        # TODO: remove debug log code
        if user is not None:
            interface = "private_chat"

        elif room is not None:
            interface = "chatroom"

        else:
            interface = "cli"

        if not force:  # and interface != "cli":  # TODO
            self.output("Headless quit needs [force] due to no support for cli confirmation prompt in core")
            self.log(f"Asking to exit application on {interface} command {args}")
            self.core.confirm_quit()
            return

        self.log(f"Quitting on {interface} command {args}")
        self.core.quit()

    def shutdown_notification(self):
        self.log("Shutdown!")
