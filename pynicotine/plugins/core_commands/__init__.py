# COPYRIGHT (C) 2022 Nicotine+ Team
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

        commands = {
            "help": {
                "callback": self.help_command,
                "description": "List commands",
                "usage": ["[query]"],
                "aliases": ["?"]
            },
            "rescan": {
                "callback": self.rescan_command,
                "description": _("Rescan shares"),
                "group": _("Shares")
            },
            "hello": {
                "callback": self.hello_command,
                "description": "Print something",
                "usage": ["[something..]"],
                "aliases": ["echo", "greet"],
                "group": _("Message")
            },
            "away": {
                "callback": self.away_command,
                "description": _("Toggle away status"),
                "aliases": ["a"]
            },
            "quit": {
                "callback": self.quit_command,
                "description": _("Quit Nicotine+"),
                "usage": ["[-force]", ""],  # "" disallow extra args
                "aliases": ["q", "exit"]
            },

            "add": {
                "callback": self.add_buddy_command,
                "description": _("Add user to buddy list"),
                "usage": ["<user>"],
                "aliases": ["buddy"],
                "group": _("Users")
            },
            "rem": {
                "callback": self.remove_buddy_command,
                "description": _("Remove user from buddy list"),
                "usage": ["<buddy>"],
                "aliases": ["unbuddy"],
                "group": _("Users")
            },
            "ban": {
                "callback": self.ban_user_command,
                "description": _("Stop connections from user"),
                "usage": ["<user>"],
                "group": _("Users")
            },
            "unban": {
                "callback": self.unban_user_command,
                "description": _("Remove user from ban list"),
                "usage": ["<user>"],
                "group": _("Users")
            },
            "block": {  # new untested
                "callback": self.block_user_ip_command,
                "description": _("Stop all connections from same IP as user"),
                "usage": ["<user>"],
                "group": _("Users")
            },
            "unblock": {  # new untested
                "callback": self.unblock_user_ip_command,
                "description": _("Remove user's IP address from block list"),
                "usage": ["<user>"],
                "group": _("Users")
            },

            "ip": {
                "callback": self.ip_user_command,
                "description": _("Show IP address of user"),
                "usage": ["<user>"],
                "group": _("Network Filters")
            },

        }

        chat_commands = {
            "clear": {
                "callback": self.clear_command,
                "description": _("Clear chat window"),
                "usage": [""],  # "" disallow any args
                "aliases": ["cl"],
                "group": _("Chat")
            },
            "join": {
                "callback": self.join_chat_command,
                "description": _("Join chat room"),
                "usage": ["<room>"],
                "aliases": ["j"],
                "group": _("Chat Rooms")
            },
            "me": {
                "callback": self.me_chat_command,
                "description": _("Say something in the third-person"),
                "usage": ["<something..>"],
                "group": _("Chat")
            },
            "msg": {
                "callback": self.msg_chat_command,
                "description": _("Send private message to user"),
                "usage": ["<user>", "<message..>"],
                "aliases": ["m"],
                "group": _("Private Chat")
            },
            "pm": {
                "callback": self.pm_chat_command,
                "description": _("Open private chat window for user"),
                "usage": ["<user>"],
                "group": _("Private Chat")
            },
            "say": {
                "callback": self.say_chat_command,
                "description": _("Say message in specified chat room"),
                "usage": ["<room>", "<message..>"],
                "group": _("Chat Rooms")
            },
            "ctcpversion": {
                "callback": self.ctcpversion_command,
                "description": _("Ask for a user's client version"),
                "usage": ["[user]"],
            },

            "ignore": {
                "callback": self.ignore_user_command,
                "description": _("Silence chat messages from user"),
                "usage": ["<user>"],
                "group": _("Users")
            },
            "unignore": {
                "callback": self.unignore_user_command,
                "description": _("Remove user from ignore list"),
                "usage": ["<user>"],
                "group": _("Users")
            },
            "ignoreip": {
                "callback": self.ignore_user_ip_command,
                "description": _("Silence chat messages from IP address of user"),
                "usage": ["<user>"],
                "group": _("Users")
            },
            "unignoreip": {  # new
                "callback": self.unignore_user_ip_command,
                "description": _("Remove user's IP address from chat ignore list"),
                "usage": ["<user>"],
                "group": _("Users")
            },

            "ipignore": {  # new untested
                "callback": self.ignore_ip_command,
                "description": _("Silence chat from anyone at IP address"),
                "usage": ["<ip_address>"],
                "group": _("Network Filters")
            },
            "ipunignore": {  # new untested
                "callback": self.unignore_ip_command,
                "description": _("Remove IP address from chat ignore list"),
                "usage": ["<ip_address>"],
                "group": _("Network Filters")
            },

            "whois": {
                "callback": self.whois_user_command,
                "description": _("Show info about user"),
                "usage": ["<user>"],
                "aliases": ["info"],  # new
                "group": _("Users")
            },
            "browse": {
                "callback": self.browse_user_command,
                "description": _("Browse files of user"),
                "usage": ["<user>"],
                "aliases": ["b"],
                "group": _("Users")
            },

        }

        chatroom_commands = {
            "close": {
                "callback": self.close_command,
                "description": _("Close private chat"),
                "usage": ["<user>"],
                "aliases": ["c"],
                "group": _("Private Chat")
            },
            "leave": {
                "callback": self.leave_command,
                "description": _("Leave chat room"),
                "usage": ["[room]"],
                "aliases": ["l"],
                "group": _("Chat Rooms")
            },

        }

        private_chat_commands = {
            "close": {
                "callback": self.close_command,
                "description": _("Close private chat"),
                "usage": ["[user]"],
                "aliases": ["c"],
                "group": _("Private Chat")
            },
            "leave": {
                "callback": self.leave_command,
                "description": _("Leave chat room"),
                "usage": ["<room>"],
                "aliases": ["l"],
                "group": _("Chat Rooms")
            },

            "add": {
                "callback": self.add_buddy_command,
                "description": _("Add user to buddy list"),
                "usage": ["[user]"],
                "aliases": ["buddy"],
                "group": _("Users")
            },
            "rem": {
                "callback": self.remove_buddy_command,
                "description": _("Remove user from buddy list"),
                "usage": ["[buddy]"],
                "aliases": ["unbuddy"],
                "group": _("Users")
            },
            "ban": {
                "callback": self.ban_user_command,
                "description": _("Stop connections from user"),
                "usage": ["[user]"],
                "group": _("Users")
            },
            "unban": {
                "callback": self.unban_user_command,
                "description": _("Remove user from ban list"),
                "usage": ["[user]"],
                "group": _("Users")
            },
            "block": {  # new
                "callback": self.block_user_ip_command,
                "description": _("Stop connections to IP of user"),
                "usage": ["[user]"],
                "aliases": ["banip"],  # new
                "group": _("Users")
            },
            "unblock": {  # new
                "callback": self.unblock_user_ip_command,
                "description": _("Remove user from IP block list"),
                "usage": ["[user]"],
                "aliases": ["unbanip"],  # new
                "group": _("Users")
            },
            "ignore": {
                "callback": self.ignore_user_command,
                "description": _("Silence chat messages from user"),
                "usage": ["[user]"],
                "group": _("Users")
            },
            "unignore": {
                "callback": self.unignore_user_command,
                "description": _("Remove user from ignore list"),
                "usage": ["[user]"],
                "group": _("Users")
            },
            "ignoreip": {
                "callback": self.ignore_user_ip_command,
                "description": _("Silence chat messages from IP address of user"),
                "usage": ["[user]"],
                "group": _("Users")
            },
            "unignoreip": {  # new
                "callback": self.unignore_user_ip_command,
                "description": _("Remove user's IP address from chat ignore list"),
                "usage": ["[user]"],
                "group": _("Users")
            },

            "ip": {
                "callback": self.ip_user_command,
                "description": _("Show IP address of user"),
                "usage": ["[user]"],
                "group": _("Network Filters")
            },

            "whois": {
                "callback": self.whois_user_command,
                "description": _("Show info about user"),
                "usage": ["[user]"],
                "aliases": ["info"],  # new
                "group": _("Users")
            },
            "browse": {
                "callback": self.browse_user_command,
                "description": _("Browse files of user"),
                "usage": ["[user]"],
                "aliases": ["b"],
                "group": _("Users")
            },

        }

        cli_commands = {
            "addshare": {
                "callback": self.add_share_command,
                "description": _("Add share"),
                "usage": ["<public|private|buddy>", "<virtual_name>", "<path>"],
                "group": _("Shares")
            },
            "removeshare": {
                "callback": self.remove_share_command,
                "description": _("Remove share"),
                "usage": ["<public|private|buddy>", "<virtual_name>"],
                "group": _("Shares")
            },
            "listshares": {
                "callback": self.list_shares_command,
                "description": _("List shares"),
                "group": _("Shares")
            },

        }

        self.chatroom_commands = {**commands, **chat_commands, **chatroom_commands}
        self.private_chat_commands = {**commands, **chat_commands, **private_chat_commands}
        self.cli_commands = {**commands, **cli_commands}

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
            command_message = command if prefix else command.lstrip("/")
            usage = " ".join(data.get("usage", []))
            aliases = data.get("aliases", [])

            if aliases:
                command_message = command_message + f", {prefix}" + f", {prefix}".join(aliases)

            if usage:
                command_message += " " + usage

            description = data.get("description", "No description")
            group = data.get("group", f"{self.config.application_name} {_('Commands')}")
            group_words = group.lower()

            if not args or query in command_message or query in group_words:
                if group not in command_groups:
                    command_groups[group] = []

                command_groups[group].append("    %s  -  %s" % (command_message, description))
                num_commands += 1

        if not num_commands:
            self.echo_unknown_command(f"{prefix}{query}")
            return False

        output = f"Listing {num_commands} {interface} commands with <required> and [optional] arguments"
        output += " " + f"matching \"{query}\"" + ":" if query else ":"

        for group, commands in command_groups.items():
            output += "\n\n" + "  " + group + ":"

            for command in commands:
                output += "\n" + command

        output += "\n\n" + "Use /help [query] (without brackets) to find similar commands or aliases"
        output += "\n" + "Start a command using / (forward slash)" if prefix else ""

        return output

    """ "Chats" """

    def clear_command(self, _args, user=None, room=None):

        if room is not None:
            self.core.chatrooms.clear_messages(room)

        elif user is not None:
            self.core.privatechats.clear_messages(user)

    def close_command(self, args, user=None, **_unused):

        if args:
            user = args

        if user not in self.core.privatechats.users:
            self.echo_message("Not messaging with user %s" % user)
            return False

        self.echo_message("Closing private chat of user %s" % user)
        self.core.privatechats.remove_user(user)
        return True

    def ctcpversion_command(self, args, user=None, **_unused):

        if args:
            user = args

        elif user is None:
            user = self.core.login_username

        if self.send_private(user, self.core.privatechats.CTCP_VERSION, show_ui=False):
            return "Asked %s for client version" % user

        return False

    def hello_command(self, args, **_unused):
        return "Hello there! %s" % args

    def join_chat_command(self, args, **_unused):
        self.core.chatrooms.show_room(args)

    def leave_command(self, args, room=None, **_unused):

        if args:
            room = args

        if room not in self.core.chatrooms.joined_rooms:
            self.echo_message("Not joined in room %s" % room)
            return False

        self.core.chatrooms.remove_room(room)
        return True

    def me_chat_command(self, args, **_unused):
        return self.send_message("/me " + args)

    def msg_chat_command(self, args, **_unused):

        args_split = args.split(" ", maxsplit=1)
        user, text = args_split[0], args_split[1]

        if self.send_private(user, text, show_ui=True, switch_page=False):
            return "Private message sent to user %s" % user

        return False

    def pm_chat_command(self, args, **_unused):
        self.core.privatechats.show_user(args)
        self.log("Private chat with user %s" % args)  # don't echo after switch_tab

    def say_chat_command(self, args, **_unused):

        args_split = args.split(" ", maxsplit=1)
        room, text = args_split[0], args_split[1]

        if self.send_public(room, text):
            return "Chat message sent to room %s" % room

        return False

    """ "Shares" """

    def add_share_command(self, args):

        args_split = args.split(maxsplit=2)  # "\""
        group, name, path = args_split[0], args_split[1], args_split[2]

        self.echo_message(f"nothing here yet, you entered: group='{group}' name='{name}' path='{path}'")

    def remove_share_command(self, args):

        args_split = args.split(maxsplit=1)
        group, name = args_split[0], args_split[1]

        self.echo_message(f"nothing here yet, you entered: group='{group}' name='{name}'")

    def list_shares_command(self, args):
        self.echo_message(f"nothing here yet, you entered: {args}")

    def rescan_command(self, _args, **_unused):
        self.core.shares.rescan_shares()

    """ "User" """

    def add_buddy_command(self, args, user=None, **_unused):

        if args:
            user = args

        # TODO: None of the user commands return anything
        return self.core.userlist.add_user(user)

    def remove_buddy_command(self, args, user=None, **_unused):

        if args:
            user = args

        return self.core.userlist.remove_user(user)

    def ban_user_command(self, args, user=None, **_unused):

        if args:
            user = args

        return self.core.network_filter.ban_user(user)

    def unban_user_command(self, args, user=None, **_unused):

        if args:
            user = args

        return self.core.network_filter.unban_user(user)

    def block_user_ip_command(self, args, user=None, **_unused):

        if args:
            user = args

        return self.core.network_filter.block_user_ip(user)

    def unblock_user_ip_command(self, args, user=None, **_unused):

        if args:
            user = args

        return self.core.network_filter.unblock_user_ip(user)

    def ignore_user_command(self, args, user=None, **_unused):

        if args:
            user = args

        return self.core.network_filter.ignore_user(user)

    def unignore_user_command(self, args, user=None, **_unused):

        if args:
            user = args

        return self.core.network_filter.unignore_user(user)

    def ignore_user_ip_command(self, args, user=None, **_unused):

        if args:
            user = args

        return self.core.network_filter.ignore_user_ip(user)

    def unignore_user_ip_command(self, args, user=None, **_unused):

        if args:
            user = args

        return self.core.network_filter.unignore_user_ip(user)

    def ip_user_command(self, args, user=None, **_unused):

        if args:
            user = args

        # Echoing the IP will be difficult because it waits for a server response message
        # could we use a user_resolve_notification() or similar?
        return self.core.request_ip_address(user)

    def ignore_ip_command(self, args, **_unused):
        return self.core.network_filter.ignore_ip(args)

    def unignore_ip_command(self, args, **_unused):
        # TODO: self.core.network_filter.unignore_ip(ip_address)
        self.echo_message(f"nothing here yet, you entered: {args}")

    def whois_user_command(self, args, user=None, **_unused):

        if args:
            user = args

        return self.core.userinfo.request_user_info(user)

    def browse_user_command(self, args, user=None, **_unused):

        if args:
            user = args

        return self.core.userbrowse.browse_user(user)

    """ General "Commands" """

    def away_command(self, _args, **_unused):
        self.core.set_away_mode(self.core.user_status != 1, save_state=True)  # 1 = UserStatus.AWAY
        self.echo_message("Status is now %s" % (_("Online") if self.core.user_status == 2 else _("Away")))

    def quit_command(self, args, user=None, room=None):

        if user is not None:
            interface = "private_chat"

        elif room is not None:
            interface = "chatroom"

        else:
            interface = "cli"

        if "force" not in args:
            self.log("Exiting application on %s command %s" % (interface, args))
            self.core.confirm_quit()
            return

        self.log("Quitting on %s command %s" % (interface, args))
        self.core.quit()

    def shutdown_notification(self):
        self.log("Shutdown!")
