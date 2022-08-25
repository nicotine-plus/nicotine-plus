# COPYRIGHT (C) 2020-2022 Nicotine+ Contributors
# COPYRIGHT (C) 2009 Daelstorm <daelstorm@gmail.com>
# COPYRIGHT (C) 2009 Quinox <quinox@users.sf.net>
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
from pynicotine.pluginsystem import returncode
from collections import deque


class Plugin(BasePlugin):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.settings = {
            'minlength': 200,
            'maxlength': 400,
            'maxdiffcharacters': 10,
            'repeatlines': 3,
            'badprivatephrases': ['buy viagra now', 'mybrute.com', 'mybrute.es', '0daymusic.biz']
        }
        self.metasettings = {
            'minlength': {
                'description': 'The minimum length of a line before it\'s considered as ASCII spam',
                'type': 'integer'
            },
            'maxdiffcharacters': {
                'description': 'The maximum number of different characters that is still considered ASCII spam',
                'type': 'integer'
            },
            'maxlength': {
                'description': 'The maximum length of a line before it\'s considered as spam.',
                'type': 'integer'
            },
            'repeatlines': {
                'description': 'Consider a line to be spam if it was already said within previous lines:',
                'type': 'integer'
            },
            'badprivatephrases': {
                'description': 'Filter chat room and private messages containing the following phrases:',
                'type': 'list string'
            }
        }
        self.lines = {}

    def loaded_notification(self):

        self.log('A line should be at least %s long with a maximum of %s different characters '
                 'before it\'s considered ASCII spam.',
                 (self.settings['minlength'], self.settings['maxdiffcharacters']))

        if self.settings['repeatlines']:
            self.log("Consider a line to be spam if it was already said within %i previous lines",
                     (self.settings['repeatlines']))

            for room in self.core.chatrooms.joined_rooms:
                self.join_chatroom_notification(room)

    def join_chatroom_notification(self, room):
        self.lines[room] = deque("", maxlen=self.settings['repeatlines'])

    def leave_chatroom_notification(self, room):
        self.lines[room].clear()

    def check_phrases(self, user, line):

        for phrase in self.settings['badprivatephrases']:
            if line.lower().find(phrase) > -1:
                self.log("Blocked spam from %s: %s", (user, line))
                return returncode['zap']

        return None

    def incoming_public_chat_event(self, room, user, line):

        if self.settings['repeatlines']:
            if line in self.lines[room]:
                self.log('Filtered repeated line from "%s" in room "%s"', (user, line))
                return returncode['zap']

            self.lines[room].append(line)

        if len(line) >= self.settings['minlength'] and len(set(line)) < self.settings['maxdiffcharacters']:
            self.log('Filtered ASCII spam from "%s" in room "%s"', (user, room))
            return returncode['zap']

        if len(line) > self.settings['maxlength']:
            self.log('Filtered really long line (%s characters) from "%s" in room "%s"', (len(line), user, room))
            return returncode['zap']

        return self.check_phrases(user, line)

    def incoming_private_chat_event(self, user, line):
        return self.check_phrases(user, line)
