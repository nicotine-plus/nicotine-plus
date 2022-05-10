# COPYRIGHT (C) 2021-2022 Nicotine+ Contributors
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

import time

from pynicotine.config import config
from pynicotine.slskmessages import UserStatus


class UserList:

    def __init__(self, core, queue, ui_callback=None):

        self.core = core
        self.queue = queue
        self.ui_callback = getattr(ui_callback, "userlist", None)
        self.buddies = {}

    def server_login(self):
        for user in self.buddies:
            self.core.watch_user(user)

    def server_disconnect(self):

        for user in self.buddies:
            self.set_user_last_seen(user, online=False)

        if self.ui_callback:
            self.ui_callback.server_disconnect()

    def load_users(self):

        for row in config.sections["server"]["userlist"]:
            user = row[0]

            if isinstance(user, str):
                self.add_user(user, row)

    def add_user(self, user, row=None):

        if user in self.buddies:
            return

        new_user = (row is None)

        if not row or not isinstance(row, list):
            row = [user, "", False, False, False, "Never seen", ""]

        self.buddies[user] = row
        self.save_user_list()

        if self.ui_callback:
            self.ui_callback.add_user(user, row)

        if self.core.user_status == UserStatus.OFFLINE:
            return

        # Request user status, speed and number of shared files
        self.core.watch_user(user, force_update=True)

        # Request user country
        if new_user:
            self.set_user_country(user, self.core.get_user_country(user))

    def remove_user(self, user):

        if user in self.buddies:
            del self.buddies[user]

        self.save_user_list()

        if self.ui_callback:
            self.ui_callback.remove_user(user)

    def set_user_note(self, user, note):

        if user not in self.buddies:
            return

        self.buddies[user][1] = note
        self.save_user_list()

        if self.ui_callback:
            self.ui_callback.set_user_note(user, note)

    def set_user_trusted(self, user, trusted):

        if user not in self.buddies:
            return

        self.buddies[user][2] = trusted
        self.save_user_list()

        if self.ui_callback:
            self.ui_callback.set_user_trusted(user, trusted)

    def set_user_notify(self, user, notify):

        if user not in self.buddies:
            return

        self.buddies[user][3] = notify
        self.save_user_list()

        if self.ui_callback:
            self.ui_callback.set_user_notify(user, notify)

    def set_user_prioritized(self, user, prioritized):

        if user not in self.buddies:
            return

        self.buddies[user][4] = prioritized
        self.save_user_list()

        if self.ui_callback:
            self.ui_callback.set_user_prioritized(user, prioritized)

    def set_user_last_seen(self, user, online):

        if user not in self.buddies:
            return

        previous_last_seen = self.buddies[user][5]

        if online:
            self.buddies[user][5] = ""
            self.save_user_list()

        elif not previous_last_seen:
            self.buddies[user][5] = time.strftime("%m/%d/%Y %H:%M:%S")
            self.save_user_list()

        else:
            return

        if self.ui_callback:
            self.ui_callback.set_user_last_seen(user, online)

    def set_user_country(self, user, country_code):

        if user not in self.buddies:
            return

        self.buddies[user][6] = country_code
        self.save_user_list()

        if self.ui_callback:
            self.ui_callback.set_user_country(user, country_code)

    def save_user_list(self):
        config.sections["server"]["userlist"] = list(self.buddies.values())

    def get_user_status(self, msg):
        """ Server code: 7 """

        self.set_user_last_seen(msg.user, online=bool(msg.status))

        if self.ui_callback:
            self.ui_callback.get_user_status(msg)

    def get_user_stats(self, msg):
        """ Server code: 36 """

        if self.ui_callback:
            self.ui_callback.get_user_stats(msg)
