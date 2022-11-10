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
            "close": {
                "description": "Close private chat",
                "aliases": ["c"],
                "disable": ["chatroom", "cli"],
                "callback": self.close_command,
                "usage": ["[user]"],
                "group": "Private Chat"
            },
            "sample": {
                "description": "Sample command description",
                "aliases": ["demo"],
                "disable": ["private_chat"],
                "callback": self.sample_command,
                "callback_private_chat": self.sample_command,
                "usage": ["<choice1|choice2>", "<something..>"],
                "usage_chatroom": ["<choice55|choice2>"]
            }
        }

    def close_command(self, args, user=None, **_unused):

        if args:
            user = args

        if user not in self.core.privatechat.users:
            self.echo_message("Not messaging with user %s" % user)
            return False

        self.echo_message("Closing private chat of user %s" % user)
        self.core.privatechat.remove_user(user)
        return True

    def sample_command(self, _args, **_unused):
        self.echo_message("Hello")
