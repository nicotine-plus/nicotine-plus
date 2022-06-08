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
                "description": "Show commands"
            },
            "rescan": {
                "callback": self.rescan_command,
                "description": _("Rescan shares"),
            },
            "hello": {
                "callback": self.hello_command,
                "description": "Print message",
                "usage": ["<user>"],
                "aliases": ["say", "greet"],
                "group": _("Message")
            },
            "quit": {
                "callback": self.quit_command,
                "description": _("Quit Nicotine+"),
                "aliases": ["q", "exit"]
            }
        }

        chat_commands = {
            "me": {
                "callback": self.me_command,
                "description": _("Say something in the third-person"),
                "usage": ["<message..>"]
            }
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
        self.echo_message("List of commands:")

        for command, data in command_list.items():
            command_message = command
            usage = " ".join(data.get("usage", []))
            aliases = data.get("aliases", [])

            if aliases:
                command_message = command_message + ", " + ", ".join(aliases)

            if usage:
                command_message += " " + usage

            description = data.get("description", "No description")
            group = data.get("group", _("General"))

            if group not in command_groups:
                command_groups[group] = []

            command_groups[group].append("%s - %s" % (command_message, description))

        for group, commands in command_groups.items():
            self.echo_message("")
            self.echo_message(group + ":")

            for command in commands:
                self.echo_message(command)

    def me_command(self, args, _command_type, _source):
        self.send_message("/me " + args)

    def rescan_command(self, _args, _command_type, _source):
        self.core.shares.rescan_shares()

    def hello_command(self, args, _command_type, _source):
        self.echo_message("Hello there, %s" % args)

    def add_share_command(self, args, _command_type, _source):

        share_type, virtual_name, path = args.split(maxsplit=3)

        self.core.shares.rescan_shares()

    def remove_share_command(self, args, _command_type, _source):

        share_type, virtual_name, *_unused = args.split(maxsplit=2)

        self.core.shares.rescan_shares()

    def list_shares_command(self, _args, _command_type, _source):
        self.echo_message("nothing here yet")

    def quit_command(self, _args, _command_type, _source):
        self.core.quit()
