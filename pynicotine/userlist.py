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


class UserList:

    def __init__(self, core, config, queue, ui_callback):

        self.core = core
        self.config = config
        self.queue = queue
        self.ui_callback = None

        if hasattr(ui_callback, "userlist"):
            self.ui_callback = ui_callback.userlist

    def server_login(self):

        for row in self.config.sections["server"]["userlist"]:
            if row and isinstance(row, list):
                user = str(row[0])
                self.core.watch_user(user)

    def server_disconnect(self):
        if self.ui_callback:
            self.ui_callback.server_disconnect()

    def add_user(self, user):

        if self.ui_callback:
            self.ui_callback.add_user(user)

        if not self.core.logged_in:
            return

        # Request user status, speed and number of shared files
        self.core.watch_user(user, force_update=True)

        # Request user country
        self.set_user_country(user, self.core.get_user_country(user))

    def remove_user(self, user):
        if self.ui_callback:
            self.ui_callback.remove_user(user)

    def save_user_list(self, user_list):
        self.config.sections["server"]["userlist"] = user_list
        self.config.write_configuration()

    def get_user_status(self, msg):
        """ Server code: 7 """

        if self.ui_callback:
            self.ui_callback.get_user_status(msg)

    def set_user_country(self, user, country_code):
        if self.ui_callback:
            self.ui_callback.set_user_country(user, country_code)

    def get_user_stats(self, msg):
        """ Server code: 36 """

        if self.ui_callback:
            self.ui_callback.get_user_stats(msg)
