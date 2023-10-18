# COPYRIGHT (C) 2023 Nicotine+ Contributors
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
            "sample": {
                "aliases": ["demo"],
                "description": "Sample command description",
                "disable": ["private_chat"],
                "callback": self.sample_command,
                "callback_private_chat": self.sample_command,
                "parameters": ["<choice1|choice2>", "<something..>"],
                "parameters_chatroom": ["<choice55|choice2>"]
            }
        }

    def sample_command(self, _args, **_unused):
        self.output("Hello")
