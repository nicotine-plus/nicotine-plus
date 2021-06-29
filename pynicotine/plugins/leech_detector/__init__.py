# pylint: disable=attribute-defined-outside-init

# COPYRIGHT (C) 2020-2021 Nicotine+ Team
# COPYRIGHT (C) 2011 Quinox <quinox@users.sf.net>
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

from pynicotine import slskmessages
from pynicotine.pluginsystem import BasePlugin


class Plugin(BasePlugin):
    __name__ = "Leech detector"
    settings = {
        'message': 'You are not sharing any files, that makes me a sad panda :(',
    }
    metasettings = {
        'message': {
            'description': 'Message to send to leechers (new lines are sent as separate messages, '
                           + 'too many lines may get you tempbanned for spam)',
            'type': 'textview'},
    }

    def init(self):
        self.probed = {}

    def UploadQueuedNotification(self, user, virtualfile, realfile):  # noqa
        try:
            self.probed[user]
        except KeyError:
            self.probed[user] = 'requesting'
            self.core.queue.append(slskmessages.GetUserStats(user))
            self.log('New user %s, requesting information...' % user)

    def UserStatsNotification(self, user, stats):  # noqa
        try:
            status = self.probed[user]
        except KeyError:
            # we did not trigger this notification
            return
        if status == 'requesting':
            if stats['files'] == 0:
                for line in self.settings['message'].splitlines():
                    self.sendprivate(user, line)

                self.log("User %s doesn't share any files, sent complaint." % user)
            else:
                self.log('User %s is okay, sharing %s files' % (user, stats['files']))
            self.probed[user] = 'processed'
        else:
            # We already dealt with this user.
            pass
