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

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.settings = {
            'message': 'Please consider sharing more files before downloading from me. Thanks :)',
            'num_files': 1,
            'num_folders': 1,
            'open_private_chat': True
        }
        self.metasettings = {
            'message': {
                'description': ('Message to send to leechers. New lines are sent as separate messages, '
                                'too many lines may get you tempbanned for spam!'),
                'type': 'textview'
            },
            'num_files': {
                'description': 'Least required number of shared files',
                'type': 'int', 'minimum': 1
            },
            'num_folders': {
                'description': 'Least required number of shared folders',
                'type': 'int', 'minimum': 1
            },
            'open_private_chat': {
                'description': 'Open private chat tabs when sending messages to leechers',
                'type': 'bool'
            }
        }

        self.probed = {}

    def loaded_notification(self):

        min_num_files = self.metasettings['num_files']['minimum']
        min_num_folders = self.metasettings['num_folders']['minimum']

        if self.settings['num_files'] < min_num_files:
            self.settings['num_files'] = min_num_files

        if self.settings['num_folders'] < min_num_folders:
            self.settings['num_folders'] = min_num_folders

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

        if stats['files'] >= self.settings['num_files'] and stats['dirs'] >= self.settings['num_folders']:
            self.log('User %s is okay, sharing %s files and %s folders', (user, stats['files'], stats['dirs']))
            return

        if not self.settings['message']:
            self.log("User %s doesn't share enough files, but no complaint message is specified.", user)
            return

        show_ui = False

        if self.settings['open_private_chat']:
            show_ui = True

        for line in self.settings['message'].splitlines():
            self.send_private(user, line, show_ui=show_ui, switch_page=False)

        self.log("User %s doesn't share enough files, sent complaint.", user)
