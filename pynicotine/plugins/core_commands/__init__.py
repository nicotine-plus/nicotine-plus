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
                "description": "Show commands",
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
                "usage": ["[force]"],
                "choices": ["force"],
                "aliases": ["q", "exit"]
            }
        }

        chat_commands = {
            "clear": {
                "callback": self.clear_command,
                "description": _("Clear chat window"),
                "aliases": ["cl"],
                "choices": [-1],
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
                "group": _("Client-To-Client Protocol")
            },
            "ipignore": {  # new untested
                "callback": self.ignore_ip_command,
                "description": _("Silence chat from anyone at IP address"),
                "usage": ["<ip_address>"],
                "group": None
            },
            "ipunignore": {  # new untested
                "callback": self.unignore_ip_command,
                "description": _("Remove IP address from chat ignore list"),
                "usage": ["<ip_address>"],
                "group": None
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
            "add": {
                "callback": self.add_buddy_command,
                "description": _("Add user to buddy list"),
                "usage": ["<user>"],
                "aliases": ["buddy"],
                "group": _("User")
            },
            "rem": {
                "callback": self.remove_buddy_command,
                "description": _("Remove user from buddy list"),
                "usage": ["<buddy>"],
                "aliases": ["unbuddy"],
                "group": _("User")
            },
            "ban": {
                "callback": self.ban_user_command,
                "description": _("Stop file transfers to user"),
                "usage": ["<user>"],
                "group": _("User")
            },
            "unban": {
                "callback": self.unban_user_command,
                "description": _("Remove user from ban list"),
                "usage": ["<user>"],
                "group": _("User")
            },
            "block": {  # new
                "callback": self.block_user_ip_command,
                "description": _("Stop file transfers to IP of user"),
                "usage": ["<user>"],
                "aliases": ["banip"],  # new
                "group": _("User")
            },
            "unblock": {  # new
                "callback": self.unban_user_command,
                "description": _("Remove user from IP block list"),
                "usage": ["<user>"],
                "aliases": ["unbanip"],  # new
                "group": _("User")
            },
            "ignore": {
                "callback": self.ignore_user_command,
                "description": _("Silence chat messages from user"),
                "usage": ["<user>"],
                "group": _("User")
            },
            "unignore": {
                "callback": self.unignore_user_command,
                "description": _("Remove user from ignore list"),
                "usage": ["<user>"],
                "group": _("User")
            },
            "ignoreip": {
                "callback": self.ignore_user_ip_command,
                "description": _("Silence chat messages from IP address of user"),
                "usage": ["<user>"],
                "group": _("User")
            },
            "unignoreip": {  # new
                "callback": self.unignore_user_ip_command,
                "description": _("Remove user's IP address from chat ignore list"),
                "usage": ["<user>"],
                "group": None
            },
            "ip": {
                "callback": self.ip_user_command,
                "description": _("Show IP address of user"),
                "usage": ["<user>"],
                "group": _("User")
            },
            "whois": {
                "callback": self.whois_user_command,
                "description": _("Show info about user"),
                "usage": ["<user>"],
                "group": _("User")
            },

            "browse": {
                "callback": self.browse_user_command,
                "description": _("Browse files of user"),
                "usage": ["<user>"],
                "aliases": ["b"],
                "group": _("User")
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
                "group": _("User")
            },
            "rem": {
                "callback": self.remove_buddy_command,
                "description": _("Remove user from buddy list"),
                "usage": ["[buddy]"],
                "aliases": ["unbuddy"],
                "group": _("User")
            },
            "ban": {
                "callback": self.ban_user_command,
                "description": _("Stop file transfers to user"),
                "usage": ["[user]"],
                "group": _("User")
            },
            "unban": {
                "callback": self.unban_user_command,
                "description": _("Remove user from ban list"),
                "usage": ["[user]"],
                "group": _("User")
            },
            "block": {  # new
                "callback": self.block_user_ip_command,
                "description": _("Stop file transfers to IP of user"),
                "usage": ["[user]"],
                "aliases": ["banip"],  # new
                "group": _("User")
            },
            "unblock": {  # new
                "callback": self.unblock_user_ip_command,
                "description": _("Remove user from IP block list"),
                "usage": ["[user]"],
                "aliases": ["unbanip"],  # new
                "group": _("User")
            },
            "ignore": {
                "callback": self.ignore_user_command,
                "description": _("Silence chat messages from user"),
                "usage": ["[user]"],
                "group": _("User")
            },
            "unignore": {
                "callback": self.unignore_user_command,
                "description": _("Remove user from ignore list"),
                "usage": ["[user"],
                "group": _("User")
            },
            "ignoreip": {
                "callback": self.ignore_user_ip_command,
                "description": _("Silence chat messages from IP address of user"),
                "usage": ["[user]"],
                "group": _("User")
            },
            "unignoreip": {
                "callback": self.unignore_user_ip_command,
                "description": _("Remove user's IP address from ignore list"),
                "usage": ["[user]"],
                "group": _("User")
            },
            "ip": {
                "callback": self.ip_user_command,
                "description": _("Show IP address of user"),
                "usage": ["[user]"],
                "group": _("User")
            },
            "whois": {
                "callback": self.whois_user_command,
                "description": _("Show info about user"),
                "usage": ["[user]"],
                "aliases": ["info"],  # new
                "group": _("User")
            },

            "browse": {
                "callback": self.browse_user_command,
                "description": _("Browse files of user"),
                "usage": ["[user]"],
                "aliases": ["b"],
                "group": _("User")
            },

        }

        cli_commands = {
            "addshare": {
                "callback": self.add_share_command,
                "description": _("Add share"),
                "usage": ["<public|private>", "<virtual_name>", "<path>"],
                "choices": ["public", "private"],
                "group": _("Shares")
            },
            "removeshare": {
                "callback": self.remove_share_command,
                "description": _("Remove share"),
                "usage": ["<public|private>", "<virtual_name>"],
                "choices": ["public", "private"],
                "group": _("Shares")
            },
            "listshares": {
                "callback": self.list_shares_command,
                "description": _("List shares"),
                "group": _("Shares")
            },
            "add": {
                "callback": self.add_buddy_command,
                "description": _("Add user to buddy list"),
                "usage": ["<user>"],
                "aliases": ["buddy"],
                "group": _("User")
            },
            "rem": {
                "callback": self.remove_buddy_command,
                "description": _("Remove user from buddy list"),
                "usage": ["<buddy>"],
                "aliases": ["unbuddy"],
                "group": _("User")
            },
            "ban": {
                "callback": self.ban_user_command,
                "description": _("Stop file transfers to user"),
                "usage": ["<user>"],
                "group": _("User")
            },
            "unban": {
                "callback": self.unban_user_command,
                "description": _("Remove user from ban list"),
                "usage": ["<user>"],
                "group": _("User")
            },
            "block": {  # new untested
                "callback": self.block_user_ip_command,
                "description": _("Stop file transfers to IP of user"),
                "usage": ["<user>"],
                "aliases": ["banip"],  # new
                "group": None
            },
            "unblock": {  # new untested
                "callback": self.unblock_user_ip_command,
                "description": _("Remove user from IP block list"),
                "usage": ["<user>"],
                "aliases": ["unbanip"],  # new
                "group": None
            },

        }

        self.chatroom_commands = {**commands, **chat_commands, **chatroom_commands}
        self.private_chat_commands = {**commands, **chat_commands, **private_chat_commands}
        self.cli_commands = {**commands, **cli_commands}

    def help_command(self, args, user=None, room=None):

        if user is not None:
            command_list = self.parent.private_chat_commands

        elif room is not None:
            command_list = self.parent.chatroom_commands

        else:
            command_list = self.parent.cli_commands

        query = args.split(" ", maxsplit=1)[0].lower().lstrip("/")
        command_groups = {}
        num_commands = 0

        for command, data in command_list.items():
            command_message = command
            usage = " ".join(data.get("usage", []))
            aliases = data.get("aliases", [])

            if aliases:
                command_message = command_message + " /" + " /".join(aliases)

            if usage:
                command_message += " " + usage

            description = data.get("description", "No description")
            group = data.get("group", _("Commands"))

            if group is None:
                # Hidden command
                continue

            group_words = group.lower().split(" ")

            if not args or query in command or query in (a for a in aliases) or query in group_words:
                if group not in command_groups:
                    command_groups[group] = []

                command_groups[group].append("    %s  -  %s" % (command_message, description))
                num_commands += 1

        if not num_commands:
            self.echo_unknown_command(query)

        elif num_commands >= 2 and query:
            self.echo_message("List of %i commands matching \"%s\":" % (num_commands, query))

        for group, commands in command_groups.items():
            self.echo_message("")
            self.echo_message("  " + group + ":")

            for command in commands:
                self.echo_message(command)

        return ("To search for a command, type /help [command]")

    """ "Chats" """

    def clear_command(self, _args, user=None, room=None):

        if room is not None:
            self.core.chatrooms.clear_messages(room)

        elif user is not None:
            self.core.privatechats.clear_messages(user)

        return 0

    def close_command(self, args, user=None, **_unused):

        if args:
            user = args

        if user in self.core.privatechats.users:
            self.echo_message("Closing private chat of user %s" % user)
        elif user:
            self.echo_message("Not messaging with user %s" % user)

        self.core.privatechats.remove_user(user)

        return 0

    def ctcpversion_command(self, args, user=None, **_unused):

        if args:
            user = args

        elif user is None:
            user = self.core.login_username

        if self.send_private(user, self.core.privatechats.CTCP_VERSION, show_ui=False):
            self.echo_message("Asked %s for client version" % user)

    def hello_command(self, args, **_unused):
        return ("Hello there! %s" % args)

    def join_chat_command(self, args, **_unused):
        self.core.chatrooms.show_room(args)

        return 0  # don't let a None echo steal the tab back again

    def leave_command(self, args, room=None, **_unused):

        if args:
            room = args

        if room not in self.core.chatrooms.joined_rooms:
            self.echo_message("Not joined in room %s" % room)
            # return  # in future the gui might need to close a tab even if we are not joined, such as while offline etc

        self.core.chatrooms.remove_room(room)

    def me_chat_command(self, args, **_unused):
        self.send_message("/me " + args)

        return 0  # don't need any echo if we're chatting

    def msg_chat_command(self, args, **_unused):

        args_split = args.split(" ", maxsplit=1)
        user, text = args_split[0], args_split[1]

        if self.send_private(user, text, show_ui=True, switch_page=False):
            return ("Private message sent to user %s" % user)

    def pm_chat_command(self, args, **_unused):
        self.core.privatechats.show_user(args)
        self.log("Private chat with user %s" % args)

        return 0  # don't let a None echo steal the tab back again (hence the use of log above instead of echo_message)

    def say_chat_command(self, args, **_unused):

        args_split = args.split(" ", maxsplit=1)
        room, text = args_split[0], args_split[1]

        if self.send_public(room, text):
            return ("Chat message sent to room %s" % room)

    """ "Shares" """

    def add_share_command(self, args):

        args_split = args.split(" ", maxsplit=3)  # "\""
        access, name, path = args_split[0], args_split[1], args_split[2]

        self.echo_message(f"nothing here yet, you entered: access='{access}' name='{name}' path='{path}'")

    def remove_share_command(self, args):

        args_split = args.split(" ", maxsplit=2)
        access, name = args_split[0], args_split[1]

        self.echo_message(f"nothing here yet, you entered: access='{access}' name='{name}'")

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

    def unban_user_command(self, args, user=None, **_unused):

        if args:
            user = args

        return self.core.network_filter.unban_user(user)

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

    def ignore_ip_command(self, args, **_unused):
        return self.core.network_filter.ignore_ip(args)

    def unignore_ip_command(self, args, **_unused):
        # TODO: self.core.network_filter.unignore_ip(ip_address)
        self.echo_message(f"nothing here yet, you entered: {args}")

    def ip_user_command(self, args, user=None, **_unused):

        if args:
            user = args

        # Echoing the IP will be difficult because it waits for a server response message
        # could we use a user_resolve_notification() or similar?
        return self.core.request_ip_address(user)

    def user_resolve_notification(self, _user, _ip_address, _port, _country):
        pass  # TODO: this wont work, we need request_ip_address_response_notification()

    def whois_user_command(self, args, user=None, **_unused):

        if args:
            user = args

        self.core.userinfo.request_user_info(user)  # TODO: returns None which blocks the switch tab
        return 0

    def browse_user_command(self, args, user=None, **_unused):

        if args:
            user = args

        self.core.userbrowse.browse_user(user)  # TODO: returns None which blocks the switch tab
        return 0

    """ General purpose "Commands" """

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
