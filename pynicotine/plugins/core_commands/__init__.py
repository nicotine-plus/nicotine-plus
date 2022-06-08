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

        new_commands = {
            "rescan": {
                "callback": self.rescan_command,
                "description": _("Rescan shares"),
                "group": _("General")
            },
            "hello": {
                "callback": self.hello_command,
                "description": "Print message",
                "usage": ["<user>"],
                "aliases": ["say", "greet"],
                "group": _("Message")
            }
        }

        separate_commands = {
            "help": {
                "callback": None,
                "description": "Show commands",
                "group": _("General")
            }
        }

        separate_commands["help"]["callback"] = self.help_command_public
        self.chatroom_commands = {**new_commands, **separate_commands}

        separate_commands["help"]["callback"] = self.help_command_private
        self.private_chat_commands = {**new_commands, **separate_commands}

        separate_commands["help"]["callback"] = self.help_command_cli
        self.cli_commands = {**new_commands, **separate_commands}

    def help_output(self, command_list):

        command_groups = {}
        self.echo_message("List of commands:")

        for command, data in command_list.items():
            aliases = data.get("aliases", [])
            aliases.insert(0, command)

            commands = ", ".join(aliases)
            usage = " ".join(data.get("usage", []))
            description = data.get("description", "No description")

            group = data.get("group", _("General"))

            if group not in command_groups:
                command_groups[group] = []

            command_groups[group].append("%s %s - %s" % (commands, usage, description))

        for group, commands in command_groups.items():
            self.echo_message("")
            self.echo_message(group + ":")

            for command in commands:
                self.echo_message(command)

    def help_command_public(self, _source, _args):
        self.help_output(self.parent.public_commands)

    def help_command_private(self, _source, _args):
        self.help_output(self.parent.private_commands)

    def help_command_cli(self, _source, _args):
        self.help_output(self.parent.cli_commands)

    def rescan_command(self, _source, _args):
        self.core.shares.rescan_shares()

    def hello_command(self, _source, args):
        self.echo_message("Hello there, %s" % args)
