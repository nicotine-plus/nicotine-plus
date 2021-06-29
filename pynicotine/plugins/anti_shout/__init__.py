# COPYRIGHT (C) 2020-2021 Nicotine+ Team
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


class Plugin(BasePlugin):

    __name__ = "Anti SHOUT"
    settings = {
        'maxscore': 0.6,
        'minlength': 10,
    }
    metasettings = {
        'maxscore': {
            'description': 'The maximum ratio capitals/noncapitals before fixing capitalization',
            'type': 'float', 'minimum': 0, 'maximum': 1, 'stepsize': 0.1},
        'minlength': {
            'description': 'Lines shorter than this never not be altered', 'type': 'integer',
            'minimum': 0},
    }

    @staticmethod
    def capitalize(text):

        # Dont alter words that look like protocol links (fe http://, ftp://)
        if text.find('://') > -1:
            return text

        return text.capitalize()

    def IncomingPrivateChatEvent(self, user, line):  # noqa
        return (user, self.antishout(line))

    def IncomingPublicChatEvent(self, room, user, line):  # noqa
        return (room, user, self.antishout(line))

    def antishout(self, line):

        lowers = len([x for x in line if x.islower()])
        uppers = len([x for x in line if x.isupper()])
        score = -2  # unknown state (could be: no letters at all)

        if uppers > 0:
            score = -1  # We have at least some upper letters

        if lowers > 0:
            score = uppers / float(lowers)

        newline = line

        if len(line) > self.settings['minlength'] and (score == -1 or score > self.settings['maxscore']):
            newline = '. '.join([self.capitalize(x) for x in line.split('. ')])

        if newline == line:
            return newline

        return newline + " [as]"
