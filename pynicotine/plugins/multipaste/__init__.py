# COPYRIGHT (C) 2020-2021 Nicotine+ Team
# COPYRIGHT (C) 2009 Daelstorm <daelstorm@gmail.com>
# COPYRIGHT (C) 2008 Quinox <quinox@users.sf.net>
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


class Plugin(BasePlugin):

    __name__ = "Multi Paste"
    settings = {
        'maxpubliclines': 4,
        'maxprivatelines': 8,
    }
    metasettings = {
        'maxpubliclines': {"description": 'The maximum number of lines that will pasted in public', 'type': 'int'},
        'maxprivatelines': {"description": 'The maximum number of lines that will be pasted in private', 'type': 'int'},
    }

    def OutgoingPrivateChatEvent(self, user, line):  # noqa

        lines = [x for x in line.splitlines() if x]

        if len(lines) > 1:
            if len(lines) > self.settings['maxprivatelines']:
                self.log("Posting " + str(self.settings['maxprivatelines']) + " of " + str(len(lines)) + " lines.")
            else:
                self.log("Splitting lines.")
            for split_line in lines[:self.settings['maxprivatelines']]:
                self.sayprivate(user, split_line)

            return returncode['zap']

        return None

    def OutgoingPublicChatEvent(self, room, line):  # noqa

        lines = [x for x in line.splitlines() if x]

        if len(lines) > 1:
            if len(lines) > self.settings['maxpubliclines']:
                self.log("Posting " + str(self.settings['maxpubliclines']) + " of " + str(len(lines)) + " lines.")
            else:
                self.log("Splitting lines.")
            for split_line in lines[:self.settings['maxpubliclines']]:
                self.saypublic(room, split_line)

            return returncode['zap']

        return None
