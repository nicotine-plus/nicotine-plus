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
        }

        chat_commands = {
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
                "usage": ["<user>", "[message..]"],
                "group": _("Private Chat")
            },
            "say": {
                "callback": self.say_chat_command,
                "description": _("Say message in specified chat room"),
                "usage": ["<room>", "<message..>"],
                "group": _("Chat Rooms")
            },
            "quit": {
                "callback": self.quit_program_chat_command,
                "description": _("Quit Nicotine+"),
                "usage": ["[force]"],
                "aliases": ["q", "exit"]
            }
        }

        chatroom_commands = {
            "help": {
                "callback": self.help_chatroom_command,
                "description": "Show commands",
                "usage": ["[query]"],
                "aliases": ["?"]
            },
            "clear": {
                "callback": self.clear_chatroom_command,
                "description": _("Clear chat window"),
                "aliases": ["cl"],
                "group": _("Chat")
            },
            "close": {
                "callback": self.close_other_chat_command,
                "description": _("Close private chat"),
                "usage": ["<user>"],
                "aliases": ["c"],
                "group": _("Private Chat")
            },
            "ctcpversion": {
                "callback": self.ctcpversion_other_chat_command,
                "description": _("Ask for a user's client version"),
                "usage": ["[user]"],
                "group": _("Client-To-Client Protocol")
            },
            "leave": {
                "callback": self.leave_chatroom_command,
                "description": _("Leave chat room"),
                "usage": ["[room]"],
                "aliases": ["l"],
                "group": _("Chat Rooms")
            },
        }

        private_chat_commands = {
            "help": {
                "callback": self.help_private_chat_command,
                "description": "Show commands",
                "usage": ["[query]"],
                "aliases": ["?"]
            },
            "clear": {
                "callback": self.clear_private_chat_command,
                "description": _("Clear chat window"),
                "aliases": ["cl"],
                "group": _("Chat")
            },
            "close": {
                "callback": self.close_private_chat_command,
                "description": _("Close private chat"),
                "usage": ["[user]"],
                "aliases": ["c"],
                "group": _("Private Chat")
            },
            "ctcpversion": {
                "callback": self.ctcpversion_private_chat_command,
                "description": _("Ask for a user's client version"),
                "usage": ["[user]"],
                "group": _("Client-To-Client Protocol")
            },
            "leave": {
                "callback": self.leave_other_chat_command,
                "description": _("Leave chat room"),
                "usage": ["<room>"],
                "aliases": ["l"],
                "group": _("Chat Rooms")
            },
        }

        cli_commands = {
            "help": {
                "callback": self.help_cli_command,
                "description": "Show commands",
                "usage": ["[query]"],
                "aliases": ["?"]
            },
            "addshare": {
                "callback": self.add_share_command,
                "description": _("Add share"),
                "usage": ["<public|private>", "<virtual_name>", "<path>"],
                "group": _("Shares")
            },
            "removeshare": {
                "callback": self.remove_share_command,
                "description": _("Remove share"),
                "usage": ["<public|private>", "<virtual_name>"],
                "group": _("Shares")
            },
            "listshares": {
                "callback": self.list_shares_command,
                "description": _("List shares"),
                "group": _("Shares")
            },
            "quit": {
                "callback": self.quit_command,
                "description": _("Quit Nicotine+"),
                "usage": ["[force]"],
                "aliases": ["q", "exit"]
            }
        }

        self.chatroom_commands = {**commands, **chat_commands, **chatroom_commands}
        self.private_chat_commands = {**commands, **chat_commands, **private_chat_commands}
        self.cli_commands = {**commands, **cli_commands}

    def help_chatroom_command(self, args=None, _user=None, _room=None):
        self._list_commands(args, self.parent.chatroom_commands)

    def help_private_chat_command(self, args=None, _user=None, _room=None):
        self._list_commands(args, self.parent.private_chat_commands)

    def help_cli_command(self, args):
        self._list_commands(args, self.parent.cli_commands)

    def _list_commands(self, args, command_list):

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

    def _echo_missing_arg(self, arg):
        self.echo_message("Missing argument: %s" % arg)

    def _echo_unexpect_arg(self, arg):
        self.echo_message("Unexpected argument: %s" % arg.split(" ", maxsplit=1)[0])

    def clear_chatroom_command(self, args=None, _user=None, room=None):

        if args:
            self._echo_unexpect_arg(args)
            return

        self.core.chatrooms.clear_messages(room)

    def clear_private_chat_command(self, args=None, user=None, _room=None):

        if args:
            self._echo_unexpect_arg(args)
            return

        self.core.privatechats.clear_messages(user)

    def close_other_chat_command(self, args=None, _user=None, _room=None):
        self.close_private_chat_command(args=args)

    def close_private_chat_command(self, args=None, user=None, _room=None):

        if args:
            user = args

        if user in self.core.privatechats.users:
            self.echo_message("Closing private chat of user %s" % user)
        elif user:
            self.echo_message("Not messaging with user %s" % user)

        self.core.privatechats.remove_user(user)

    def ctcpversion_other_chat_command(self, args=None, _user=None, _room=None):

        user = args if args else self.core.login_username

        self.ctcpversion_private_chat_command(args=user)

    def ctcpversion_private_chat_command(self, args=None, user=None, _room=None):

        if args:
            user = args

        if self.send_private(user, self.core.privatechats.CTCP_VERSION, show_ui=False):
            self.echo_message("Asked %s for client version" % user)

    def hello_command(self, args=None, _user=None, _room=None):
        self.echo_message("Hello there! %s" % args)

    def join_chat_command(self, args=None, _user=None, _room=None):
        self.core.chatrooms.show_room(args)

    def leave_chatroom_command(self, args=None, _user=None, room=None):

        if args:
            room = args

        if room not in self.core.chatrooms.joined_rooms:
            self.echo_message("Not joined in room %s" % room)
            # return  # in future the gui might need to close a tab even if we are not joined, such as while offline etc

        self.core.chatrooms.remove_room(room)

    def leave_other_chat_command(self, args=None, _user=None, _room=None):
        self.leave_chatroom_command(args=args)

    def me_chat_command(self, args=None, _user=None, _room=None):
        self.send_message("/me " + args)

    def msg_chat_command(self, args=None, _user=None, _room=None):
        self.pm_chat_command(args=args, switch_page=False)

    def pm_chat_command(self, args=None, _user=None, _room=None, switch_page=True):

        args_split = args.split(" ", maxsplit=1)
        user, text = args_split[0], args_split[1] if len(args_split) == 2 else None

        if self.send_private(user, text, show_ui=True, switch_page=switch_page):
            self.echo_message("Private message sent to user %s" % user)

        if switch_page:
            self.log("Private chat with user %s" % user)

    def say_chat_command(self, args=None, _user=None, _room=None):

        args_split = args.split(" ", maxsplit=1)
        room, text = args_split[0], args_split[1]

        if self.send_public(room, text):
            self.log("Chat message sent to room %s" % room)

    def add_share_command(self, _args=None, _user=None, _room=None):

        # share_type, virtual_name, path = args.split(maxsplit=3)

        self.core.shares.rescan_shares()

    def remove_share_command(self, _args=None, _user=None, _room=None):

        # share_type, virtual_name, *_unused = args.split(maxsplit=2)

        self.core.shares.rescan_shares()

    def list_shares_command(self, _args=None, _user=None, _room=None):
        self.echo_message("nothing here yet")

    def rescan_command(self, _args=None, _user=None, _room=None):
        self.core.shares.rescan_shares()

    def away_command(self, _args=None, _user=None, _room=None):
        self.core.set_away_mode(self.core.user_status != 1, save_state=True)  # 1 = UserStatus.AWAY
        self.echo_message("Status is now %s" % (_("Online") if self.core.user_status == 2 else _("Away")))

    def quit_program_chat_command(self, args=None, _user=None, room=None):
        self.quit_command(args=args, interface="chatroom" if room else "private_chat")

    def quit_command(self, args=None, interface="cli"):

        if args and args != "force":
            self._echo_unexpect_arg(args)
            return

        if "force" not in args:
            self.log("Exiting application on %s command %s" % (interface, args))
            self.core.confirm_quit()
            return

        self.log("Quitting on %s command %s" % (interface, args))
        self.core.quit()

    def shutdown_notification(self):
        self.log("Shutdown!")
