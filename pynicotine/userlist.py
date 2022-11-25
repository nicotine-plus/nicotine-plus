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
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.logfacility import log
from pynicotine.slskmessages import UserStatus


class UserList:

    def __init__(self):

        self.buddies = {}

        for event_name, callback in (
            ("server-login", self._server_login),
            ("server-disconnect", self._server_disconnect),
            ("start", self._start),
            ("user-country", self._user_country),
            ("user-status", self._user_status)
        ):
            events.connect(event_name, callback)

    def _start(self):

        for row in config.sections["server"]["userlist"]:
            if not row:
                continue

            user = row[0]

            if not isinstance(user, str) or not isinstance(row, list):
                continue

            if user in self.buddies:
                continue

            num_items = len(row)

            if num_items <= 1:
                note = ""
                row.append(note)

            if num_items <= 2:
                notify = False
                row.append(notify)

            if num_items <= 3:
                prioritized = False
                row.append(prioritized)

            if num_items <= 4:
                trusted = False
                row.append(trusted)

            if num_items <= 5:
                last_seen = "Never seen"
                row.append(last_seen)

            if num_items <= 6:
                country = ""
                row.append(country)

            self.buddies[user] = row
            events.emit("add-buddy", user, row)

    def _server_login(self, msg):

        if not msg.success:
            return

        for user in self.buddies:
            core.watch_user(user)

    def _server_disconnect(self, _msg):

        for user in self.buddies:
            self.set_buddy_last_seen(user, online=False)

        self.save_buddy_list()

    def add_buddy(self, user):

        if user in self.buddies:
            return

        note = country = ""
        trusted = notify = prioritized = False
        last_seen = "Never seen"

        self.buddies[user] = row = [user, note, notify, prioritized, trusted, last_seen, country]
        self.save_buddy_list()

        events.emit("add-buddy", user, row)

        if core.user_status == UserStatus.OFFLINE:
            return

        # Request user status, speed and number of shared files
        core.watch_user(user, force_update=True)

        # Set user country
        events.emit("user-country", user, core.get_user_country(user))

    def remove_buddy(self, user):

        if user in self.buddies:
            del self.buddies[user]

        self.save_buddy_list()
        events.emit("remove-buddy", user)

    def set_buddy_note(self, user, note):

        if user not in self.buddies:
            return

        self.buddies[user][1] = note
        self.save_buddy_list()

        events.emit("buddy-note", user, note)

    def set_buddy_notify(self, user, notify):

        if user not in self.buddies:
            return

        self.buddies[user][2] = notify
        self.save_buddy_list()

        events.emit("buddy-notify", user, notify)

    def set_buddy_prioritized(self, user, prioritized):

        if user not in self.buddies:
            return

        self.buddies[user][3] = prioritized
        self.save_buddy_list()

        events.emit("buddy-prioritized", user, prioritized)

    def set_buddy_trusted(self, user, trusted):

        if user not in self.buddies:
            return

        self.buddies[user][4] = trusted
        self.save_buddy_list()

        events.emit("buddy-trusted", user, trusted)

    def set_buddy_last_seen(self, user, online):

        if user not in self.buddies:
            return

        previous_last_seen = self.buddies[user][5]

        if online:
            self.buddies[user][5] = ""

        elif not previous_last_seen:
            self.buddies[user][5] = time.strftime("%m/%d/%Y %H:%M:%S")

        else:
            return

        events.emit("buddy-last-seen", user, online)

    def _user_country(self, user, country_code):

        if not country_code:
            return

        if user not in self.buddies:
            return

        self.buddies[user][6] = "flag_" + country_code

    def save_buddy_list(self):
        config.sections["server"]["userlist"] = list(self.buddies.values())
        config.write_configuration()

    def _user_status(self, msg):
        """ Server code: 7 """

        user = msg.user

        if user not in self.buddies:
            return

        notify = self.buddies[user][2]
        self.set_buddy_last_seen(user, online=bool(msg.status))

        if not notify:
            return

        if msg.status == UserStatus.AWAY:
            status_text = _("%(user)s is away")

        elif msg.status == UserStatus.ONLINE:
            status_text = _("%(user)s is online")

        else:
            status_text = _("%(user)s is offline")

        log.add(status_text, {"user": user})
        core.notifications.show_text_notification(status_text % {"user": user}, title=_("Buddy Online Status"))
