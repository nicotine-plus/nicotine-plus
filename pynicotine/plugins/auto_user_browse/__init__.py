# SPDX-FileCopyrightText: 2021-2025 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

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
