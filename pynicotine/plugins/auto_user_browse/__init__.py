# COPYRIGHT (C) 2021-2024 Nicotine+ Contributors
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

from pynicotine.events import events
from pynicotine.pluginsystem import BasePlugin
from pynicotine.slskmessages import UserStatus


class Plugin(BasePlugin):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.settings = {
            "users": []
        }
        self.metasettings = {
            "users": {
                "description": "Username",
                "type": "list string"
            }
        }
        self.processed_users = set()

    def browse_user(self, user):
        if user in self.processed_users:
            self.core.userbrowse.browse_user(user, switch_page=False)

    def user_status_notification(self, user, status, _privileged):

        if status == UserStatus.OFFLINE:
            self.processed_users.discard(user)
            return

        if user not in self.settings["users"]:
            return

        if user not in self.processed_users:
            # Wait 30 seconds before browsing shares to ensure they are ready
            # and the server doesn't send an invalid port for the user
            self.processed_users.add(user)
            events.schedule(delay=30, callback=self.browse_user, callback_args=(user,))

    def server_disconnect_notification(self, userchoice):
        self.processed_users.clear()
