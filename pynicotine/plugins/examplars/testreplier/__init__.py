# COPYRIGHT (C) 2020-2022 Nicotine+ Contributors
# COPYRIGHT (C) 2008-2010 quinox <quinox@users.sf.net>
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

from random import choice
from pynicotine.pluginsystem import BasePlugin, ResponseThrottle


class Plugin(BasePlugin):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.settings = {
            'replies': ['Test failed.']
        }
        self.metasettings = {
            'replies': {
                'description': 'Replies:',
                'type': 'list string'
            }
        }

        self.throttle = ResponseThrottle(self.core, self.human_name)

    def incoming_public_chat_event(self, room, user, line):

        if line.lower() != 'test':
            return

        if self.throttle.ok_to_respond(room, user, line):
            self.throttle.responded()
            self.send_public(room, choice(self.settings['replies']).lstrip("!"))
