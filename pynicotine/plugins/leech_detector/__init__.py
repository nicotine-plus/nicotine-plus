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
        'message': "Please consider sharing more files before downloading from me again. Thanks :)",
        'num_files': 10,
        'num_folders': 1,
        'num_tolerate': 20,
        'send_minimums': True,
        'nonzero_numbers': True,
        'open_private_chat': True
    }
    metasettings = {
        'num_tolerate': {
            'description': "Maximum number of leeched downloads to tolerate before complaining:", 'type': 'int',
            'minimum': 0,
            'maximum': 999
        },
        'message': {
            'description': "Automatically send a private chat message to leechers. Each new line is sent as a separate message, "
                            + "too many message lines may get you temporarily banned for spam!", 'type': 'textview'
        },
        'send_minimums': {
            'description': "Notify leechers about the required minimums (creates an additional message line)", 'type': 'bool'
        },
        'num_files': {
            'description': "Require users to have a minimum number of shared files:", 'type': 'int',
            'minimum': 1
        },
        'num_folders': {
            'description': "Require users to have a minimum number of shared folders:", 'type': 'int',
            'minimum': 1
        },
        'nonzero_numbers': {
            'description': "Only send message if server reports non-zero numbers that are definitely correct", 'type': 'bool'
        },
        'open_private_chat': {
            'description': "Open private chat tabs when sending messages to leechers", 'type': 'bool'
        }
    }

    def init(self):

        self.probed = {}
        self.uploaded = {}
        self.complained = {}
        self.files = {}
        self.dirs = {}
        
        self.check_thresholds()

        if self.settings['message'] or self.settings['send_minimums']:
            self.log("Complain to leechers after tolerating %d downloads, require users have minimum %d files in %d shared public folders.", (
                     self.settings['num_tolerate'], self.settings['num_files'], self.settings['num_folders']))
        else:
            self.log("Log leechers after tolerating %d downloads, require users have minimum %d files in %d shared public folders.", (
                     self.settings['num_tolerate'], self.settings['num_files'], self.settings['num_folders']))


    def check_thresholds(self):

        if self.settings['num_files'] < self.metasettings['num_files']['minimum']:
            self.settings['num_files'] = self.metasettings['num_files']['minimum']

        if self.settings['num_folders'] < self.metasettings['num_folders']['minimum']:
            self.settings['num_folders'] = self.metasettings['num_folders']['minimum']

        if self.settings['num_tolerate'] > self.metasettings['num_tolerate']['maximum']:
            self.settings['num_tolerate'] = self.metasettings['num_tolerate']['maximum']


    def upload_queued_notification(self, user, *_):

        if user in self.probed:
            # We already have stats for this user
            return

        self.probed[user] = 0
        self.uploaded[user] = 0
        self.complained[user] = 0

        self.log("Requesting statistics for new user %s...", user)

        self.core.queue.append(slskmessages.GetUserStats(user))


    def user_stats_notification(self, user, stats):

        if user not in self.probed:
            # We did not trigger this notification
            return

        self.probed[user] = self.probed[user] + 1
        
        if stats['files'] == 0:
            # ToDo Issue #1565: Implement alternate fallback method to try get values from User Browse response
            self.log("User %s seems to have no public shares (zero), after %d attempts to get statistics from server.", (
                     user, self.probed[user]))
            if self.settings['nonzero_numbers']:
                return

        self.files[user] = stats['files']
        self.dirs[user] = stats['dirs']

        if self.probed[user] == 1:
            # We see this user for the first time
            self.check_thresholds()
            
            if self.files[user] >= self.settings['num_files'] and self.dirs[user] >= self.settings['num_folders']:
                self.log("New user %s has %d files in %d shared public folders available. Okay.", (
                         user, status, self.files[user], self.dirs[user]))
            else:
                self.log("New user %s has only %d files in %d shared public folders. A maximum of %d leeches will be tolerated.", (
                         user, self.files[user], self.dirs[user], self.settings['num_tolerate']))


    def upload_finished_notification(self, user, *_):

        if user not in self.uploaded:
            # We did not trigger this notification
            return

        """ Count Successful Transfers """

        self.uploaded[user] = self.uploaded[user] + 1

        self.check_thresholds()

        if self.uploaded[user] > self.settings['num_tolerate'] or self.complained[user] >= 1:
            # We already dealt with this user, or max tolerate is set to zero (unlimited)
            return

        elif self.uploaded[user] < self.settings['num_tolerate']:
            # We allowed some downloads without complaining yet
            return

        elif self.uploaded[user] == self.settings['num_tolerate']:
            # We tolerated the maximum so process leecher rules now
            status = self.uploaded[user]

        else:
            # We lost track so avoid complaining in error
            self.log("User %s got %s downloads, has %s files in %s shared public folders available. %s attempts to determine leeching status unknown.",
                     (user, self.uploaded[user], self.files[user], self.dirs[user], self.probed[user]))
            status = self.uploaded[user] = self.files[user] = self.dirs[user] = None
            return

        """ Leecher Conditions """

        if self.files[user] >= self.settings['num_files'] and self.dirs[user] >= self.settings['num_folders']:
            # Not a leecher
            self.log("User %s finished %d downloads, has %s files in %s shared public folders available. Okay.",
                     (user, status, self.files[user], self.dirs[user]))
            status = self.files[user] = self.dirs[user] = None
            return

        if not self.settings['message'] and self.settings['send_minimums'] == False:
            self.log("User %s leeched %s downloads, has only %s files in %s shared public folders. No complaint message specified.",
                     (user, status, self.files[user], self.dirs[user]))
            status = self.files[user] = self.dirs[user] = None
            return

        if user in (i[0] for i in self.config.sections["server"]["userlist"]):
            if self.config.sections["transfers"]["friendsnolimits"]:
                self.log("Buddy %s finished %d downloads, has only %s files in %s shared public folders available. Allowed.",
                         (user, status, self.files[user], self.dirs[user]))
                status = self.files[user] = self.dirs[user] = None
                return   # Do not complain to buddies
            
            else:        # Do complain to buddies
                self.log("Buddy %s finished %d downloads, has only %s files in %s shared public folders available. Limited.",
                         (user, status, self.files[user], self.dirs[user]))

        if self.settings['nonzero_numbers'] and self.files[user] == 0 and self.dirs[user] == 0:
            # ToDo Issue #1565: Implement alternate fallback method to try get values from User Browse response
            self.log("User %s leeching %s downloads, seems to have no public shares (zero). Not complaining incase server is wrong.",
                     (user, status))
            status = None
            return

        """ Complain """

        if self.settings['send_minimums']:
            str_minimums = "After %s downloads, this Leech Detector requires you have at least %s files in %s public shared folders (counted only %s files)."
            self.send_private(user, str_minimums  % (status, self.settings['num_files'], self.settings['num_folders'], self.files[user]),
                              show_ui=self.settings['open_private_chat'], switch_page=False)
            self.complained[user] = self.complained[user] + 1

        for line in self.settings['message'].splitlines():
            self.send_private(user, line, show_ui=self.settings['open_private_chat'], switch_page=False)
            self.complained[user] = self.complained[user] + 1

        self.log("User %s leeched %s downloads, has only %s files in %s shared public folders. %d private chat messages sent to leecher!",
                 (user, status, self.files[user], self.dirs[user], self.complained[user]))

        status = self.files[user] = self.dirs[user] = None
