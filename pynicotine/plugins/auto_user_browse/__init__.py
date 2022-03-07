# COPYRIGHT (C) 2021-2022 Nicotine+ Team
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


class Plugin(BasePlugin):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.settings = {
            'users': []
        }
        self.metasettings = {
            'users': {
                'description': 'Username',
                'type': 'list string'
            }
        }
        self.user_statuses = {}

    def user_status_notification(self, user, status, _privileged):

        if user not in self.settings['users']:
            return

        if status <= 0:
            self.user_statuses[user] = status
            return

        previous_status = self.user_statuses.get(user, 0)

        if previous_status <= 0:
            # User was previously offline
            self.user_statuses[user] = status
            self.core.userbrowse.browse_user(user, switch_page=False)
