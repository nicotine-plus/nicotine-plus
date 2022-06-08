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

        commands = [
            ('rescan', self.rescan_command, _("Rescan shares")),
            ('hello', self.hello_command, "Print message", ["<user>"])
        ]

        self.__publiccommands__ = commands[:] + [('help', self.help_command_public, "Show commands")]
        self.__privatecommands__ = commands[:] + [('help', self.help_command_private, "Show commands")]
        self.__clicommands__ = commands[:] + [('help', self.help_command_cli, "Show commands")]

    def help_output(self, command_list):

        self.echo_message("List of commands:")

        for command, (description, usage) in command_list.items():
            self.echo_message("%s %s - %s" % (command, " ".join(usage), description))

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
