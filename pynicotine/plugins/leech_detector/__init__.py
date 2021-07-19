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

    __name__ = "Leech Detector"
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

    def upload_queued_notification(self, user, virtual_path, real_path):

        if user in self.probed:
            return

        self.probed[user] = 'requesting'
        self.core.queue.append(slskmessages.GetUserStats(user))
        self.log('New user %s, requesting information...', user)

    def user_stats_notification(self, user, stats):

        if user not in self.probed:
            # We did not trigger this notification
            return

        status = self.probed[user]

        if status != 'requesting':
            # We already dealt with this user.
            return

        self.probed[user] = 'processed'

        if stats['files'] > 0:
            self.log('User %s is okay, sharing %s files', (user, stats['files']))
            return

        if not self.settings['message']:
            self.log("User %s doesn't share any files, but no complaint message is specified.", user)
            return

        for line in self.settings['message'].splitlines():
            self.send_private(user, line, show_ui=False)

        self.log("User %s doesn't share any files, sent complaint.", user)
