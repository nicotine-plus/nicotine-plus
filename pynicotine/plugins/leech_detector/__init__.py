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
            'message': 'Please consider sharing more files if you would like to download from me again. Thanks :)',
            'num_files': 1,
            'num_folders': 1,
            'open_private_chat': True
        }
        self.metasettings = {
            'message': {
                'description': ('Private chat message to send to leechers. Each line is sent as a separate message, '
                                'too many message lines may get you temporarily banned for spam!'),
                'type': 'textview'
            },
            'num_files': {
                'description': 'Require users to have a minimum number of shared files:',
                'type': 'int', 'minimum': 1
            },
            'num_folders': {
                'description': 'Require users to have a minimum number of shared folders:',
                'type': 'int', 'minimum': 1
            },
            'open_private_chat': {
                'description': 'Open chat tabs when sending private messages to leechers',
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

        if self.settings['message']:
            str_log_start = "complain to leecher"
        else:
            str_log_start = "log leecher"

        self.log(
            "Ready to %ss, require users have a minimum of %d files in %d shared public folders.",
            (str_log_start, self.settings['num_files'], self.settings['num_folders'])
        )

    def upload_queued_notification(self, user, virtual_path, real_path):

        if user in self.probed:
            # We already have stats for this user.
            return

        self.probed[user] = 'requesting'
        self.core.queue.append(slskmessages.GetUserStats(user))
        self.log("Requesting statistics for new user %s...", user)

    def user_stats_notification(self, user, stats):

        if user not in self.probed:
            # We did not trigger this notification
            return

        if self.probed[user] != 'requesting':
            # We already dealt with this user.
            return

        if stats['files'] >= self.settings['num_files'] and stats['dirs'] >= self.settings['num_folders']:
            self.log("User %s is okay, sharing %s files in %s folders.", (user, stats['files'], stats['dirs']))
            self.probed[user] = 'okay'
            return

        if user in (i[0] for i in self.config.sections["server"]["userlist"]):
            self.log("Buddy %s is only sharing %s files in %s folders.", (user, stats['files'], stats['dirs']))
            self.probed[user] = 'buddy'
            return

        if stats['files'] == 0 and stats['dirs'] == 0:
            ## ToDo: Implement alternate fallback method (num_files | num_folders) from Browse Shares (Issue #1565) ##
            self.log("User %s seems to have zero files and no public shared folder, the server could be wrong.", user)
            self.probed[user] = 'zero'
            return

        self.log("Leecher %s detected, only sharing %s files in %s folders.", (user, stats['files'], stats['dirs']))
        self.probed[user] = 'leecher'

    def upload_finished_notification(self, user, *_):

        if user not in self.probed:
            return

        if self.probed[user] != 'leecher':
            return

        self.probed[user] = 'processed'

        if not self.settings['message']:
            self.log("Leecher %s doesn't share enough files, but no complaint message is specified.", user)
            return

        for line in self.settings['message'].splitlines():
            self.send_private(user, line, show_ui=self.settings['open_private_chat'], switch_page=False)

        self.log("Leecher %s doesn't share enough files, sent complaint.", user)
