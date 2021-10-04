# COPYRIGHT (C) 2021 Nicotine+ Team
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


class UserInfo:

    def __init__(self, core, config, queue, ui_callback=None):

        self.core = core
        self.config = config
        self.queue = queue
        self.users = set()
        self.ui_callback = None

        if hasattr(ui_callback, "userinfo"):
            self.ui_callback = ui_callback.userinfo

    def server_login(self):
        for user in self.users:
            self.core.watch_user(user)  # Get notified of user status

    def server_disconnect(self):
        if self.ui_callback:
            self.ui_callback.server_disconnect()

    def add_user(self, user):
        if user not in self.users:
            self.users.add(user)

    def remove_user(self, user):
        self.users.remove(user)

    def show_user(self, user, switch_page=True):
        if self.ui_callback:
            self.ui_callback.show_user(user, switch_page)

    def request_user_info(self, user, switch_page=True):

        self.add_user(user)
        self.show_user(user, switch_page)

        # Request user description, picture and queue information
        self.core.send_message_to_peer(user, slskmessages.UserInfoRequest(None))

        # Request user status, speed and number of shared files
        self.core.watch_user(user, force_update=True)

        # Request user interests
        self.queue.append(slskmessages.UserInterests(user))

        # Request user country
        self.set_user_country(user, self.core.get_user_country(user))

    def set_conn(self, username, conn):
        if self.ui_callback:
            self.ui_callback.set_conn(username, conn)

    def show_connection_error(self, username):
        if self.ui_callback:
            self.ui_callback.show_connection_error(username)

    def get_user_stats(self, msg):
        if self.ui_callback:
            self.ui_callback.get_user_stats(msg)

    def get_user_status(self, msg):
        if self.ui_callback:
            self.ui_callback.get_user_status(msg)

    def set_user_country(self, user, country_code):
        if self.ui_callback:
            self.ui_callback.set_user_country(user, country_code)

    def update_gauge(self, msg):
        if self.ui_callback:
            self.ui_callback.update_gauge(msg)

    def user_info_reply(self, user, msg):
        if self.ui_callback:
            self.ui_callback.user_info_reply(user, msg)

    def user_interests(self, msg):
        if self.ui_callback:
            self.ui_callback.user_interests(msg)
