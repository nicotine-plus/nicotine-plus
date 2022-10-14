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
                "description": "Toggle away status"
            },
            "quit": {
                "callback": self.quit_command,
                "description": _("Quit Nicotine+"),
                "usage": ["[force]"],
                "aliases": ["q", "exit"]
            }
        }

        chat_commands = {
            "clear": {
                "callback": self.clear_command,
                "description": _("Clear chat window"),
                "aliases": ["cl"],
                "group": _("Chat")
            },
            "close": {
                "callback": self.close_command,
                "description": _("Close private chat"),
                "usage": ["[user]"],
                "aliases": ["c"],
                "group": _("Private Chat")
            },
            "join": {
                "callback": self.join_command,
                "description": _("Join chat room"),
                "usage": ["<room>"],
                "aliases": ["j"],
                "group": _("Chat Rooms")
            },
            "leave": {
                "callback": self.leave_command,
                "description": _("Leave chat room"),
                "usage": ["[room]"],
                "aliases": ["l"],
                "group": _("Chat Rooms")
            },
            "me": {
                "callback": self.me_command,
                "description": _("Say something in the third-person"),
                "usage": ["<something..>"],
                "group": _("Chat")
            },
            "msg": {
                "callback": self.msg_command,
                "description": _("Send private message to user"),
                "usage": ["<user>", "[message..]"],
                "aliases": ["m"],
                "group": _("Private Chat")
            },
            "pm": {
                "callback": self.pm_command,
                "description": _("Open private chat window for user"),
                "usage": ["<user>", "[message..]"],
                "group": _("Private Chat")
            },
            "say": {
                "callback": self.say_command,
                "description": _("Say message in specified chat room"),
                "usage": ["<room>", "<message..>"],
                "group": _("Chat Rooms")
            },
        }

        cli_commands = {
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
            }
        }

        self.chatroom_commands = {**commands, **chat_commands}
        self.private_chat_commands = {**commands, **chat_commands}
        self.cli_commands = {**commands, **cli_commands}

    def help_command(self, _args, command_type, _source):

        if command_type == "chatroom":
            command_list = self.parent.chatroom_commands

        elif command_type == "private_chat":
            command_list = self.parent.private_chat_commands

        elif command_type == "cli":
            command_list = self.parent.cli_commands

        command_groups = {}

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

            if group not in command_groups:
                command_groups[group] = []

            command_groups[group].append("    %s  -  %s" % (command_message, description))

        for group, commands in command_groups.items():
            self.echo_message("")
            self.echo_message("  " + group + ":")

            for command in commands:
                self.echo_message(command)

    def close_command(self, args, command_type, source):

        if not args and command_type == "private_chat":
            self.core.privatechats.remove_user(source)

        elif args in self.core.privatechats.users:
            self.core.privatechats.remove_user(args)
            self.echo_message("Closed private chat of user %s" % args)

        elif args:
            self.echo_message("Not chatting with user %s" % args)

        elif command_type != "private_chat":
            # TODO: maybe consider diverting to leave_command(room)
            self.echo_message("Missing argument: %s" % ('[user]'))

    def clear_command(self, args, command_type, source):

        if args:
            self.echo_message("Unexpected argument: %s" % (args))
            return

        if command_type == "chatroom":
            self.core.chatrooms.clear_messages(source)

        elif command_type == "private_chat":
            self.core.privatechats.clear_messages(source)

    def join_command(self, args, _command_type, _source):

        room = args

        if room in self.core.chatrooms.joined_rooms:
            # TODO: core needs show_room() tab switch ui_callback
            self.echo_message("Already joined in room %s" % room)
            return

        if room not in self.core.chatrooms.server_rooms and room not in self.core.chatrooms.private_rooms:
            self.echo_message("Creating new room %s" % room)

        self.echo_message("Joining room %s" % room)
        self.core.chatrooms.request_join_room(room)

    def leave_command(self, args, command_type, source):

        if args:
            room = args  # optional argument for leaving any room
        else:
            room = source if command_type == "chatroom" else None

        if room is None:
            self.echo_message("Missing argument: %s" % ('[room]'))
            return

        if not room in self.core.chatrooms.joined_rooms:
            self.echo_message("Not joined in room %s" % room)
            return

        self.echo_message("Leaving room %s" % room)
        self.core.chatrooms.request_leave_room(room)

    def me_command(self, args, _command_type, _source):
        self.send_message("/me " + args)

    def msg_command(self, args, _command_type, _source):
        # Send private chat [message] to <user> or open chat window if no [message]

        args_split = args.split(" ", maxsplit=1)
        user, text = args_split[0], args_split[1] if len(args_split) == 2 else None

        if text:
            self.send_private(user, text, switch_page=False)
            self.echo_message("Private message sent to user %s" % user)
        else:
            self.core.privatechats.show_user(user)
            self.echo_message("Private chat opened with user %s" % user)

    def pm_command(self, args, _command_type, _source):
        # Open private chat window for <user> and optionally send [message]

        args_split = args.split(" ", maxsplit=1)
        user, text = args_split[0], args_split[1] if len(args_split) == 2 else None

        if text:
            self.send_private(user, text, switch_page=True)
            self.echo_message("Private message sent to user %s" % user)
        else:
            self.core.privatechats.show_user(user)
            self.echo_message("Private chat opened with user %s" % user)

    def private_message_command(self, _args, _command_type, _source):  # , switch_page=True):
        # TODO: combine pm_command(switch_page=True) with msg_command(switch_page=False)
        #
        # "Plugin core_commands failed with error <class 'TypeError'>:
        # private_message_command() got multiple values for argument 'switch_page'.
        pass

    def rescan_command(self, _args, _command_type, _source):
        self.core.shares.rescan_shares()

    def say_command(self, args, _command_type, _source):

        args_split = args.split(" ", maxsplit=1)
        room, text = args_split[0], args_split[1]

        if not room in self.core.chatrooms.joined_rooms:
            self.echo_message("Not joined in room %s" % room)
            return

        self.send_public(room, text)
        self.echo_message("Chat message sent to room %s" % room)

    def hello_command(self, args, _command_type, _source):
        self.echo_message("Hello there! %s" % args)

    def add_share_command(self, _args, _command_type, _source):

        # share_type, virtual_name, path = args.split(maxsplit=3)

        self.core.shares.rescan_shares()

    def remove_share_command(self, _args, _command_type, _source):

        # share_type, virtual_name, *_unused = args.split(maxsplit=2)

        self.core.shares.rescan_shares()

    def list_shares_command(self, _args, _command_type, _source):
        self.echo_message("nothing here yet")

    def away_command(self, _args, _command_type, _source):
        self.core.set_away_mode(self.core.user_status != 1, save_state=True)  # 1 = UserStatus.AWAY
        self.echo_message("Status is now %s" % ("Online" if self.core.user_status == 2 else "Away"))

    def shutdown_notification(self):
        self.log("Shutdown!")

    def quit_command(self, args, command_type, _source):

        if self.core.ui_callback and not "force" in args:  # and not command_type == "cli":
            self.log("Exiting application on %s command %s" % (command_type, args))
            # TODO: X Window System error 'BadImplementation (server does not implement operation)'
            # '     Details: serial 28078 error_code 17 request_code 20 (core protocol) minor_code 0
            self.core.ui_callback.on_quit()
            return

        self.log("Quitting on %s command %s" % (command_type, args))
        # TODO: Gtk-ERROR **: 12:13:37.433: Unknown segment type: \x80\x9d\x9b\u0003
        self.core.quit()  # Fatal Python error: Segmentation fault
