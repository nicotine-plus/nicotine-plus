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


class Buddy:
    __slots__ = ("username", "note", "notify_status", "is_prioritized", "is_trusted", "last_seen",
                 "country", "status")

    def __init__(self, username, note, notify_status, is_prioritized, is_trusted, last_seen,
                 country, status):

        self.username = username
        self.note = note
        self.notify_status = notify_status
        self.is_prioritized = is_prioritized
        self.is_trusted = is_trusted
        self.last_seen = last_seen
        self.country = country
        self.status = status


class UserList:

    def __init__(self):

        self.buddies = {}
        self.allow_saving_buddies = False

        for event_name, callback in (
            ("quit", self._quit),
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

            _user, note, notify_status, is_prioritized, is_trusted, last_seen, country = row

            self.buddies[user] = user_data = Buddy(
                username=user,
                note=note,
                notify_status=notify_status,
                is_prioritized=is_prioritized,
                is_trusted=is_trusted,
                last_seen=last_seen,
                country=country,
                status=UserStatus.OFFLINE
            )
            events.emit("add-buddy", user, user_data)

        self.allow_saving_buddies = True

    def _quit(self):
        self.buddies.clear()
        self.allow_saving_buddies = False

    def _server_login(self, msg):

        if not msg.success:
            return

        for user in self.buddies:
            core.watch_user(user)

    def _server_disconnect(self, _msg):

        for user, user_data in self.buddies.items():
            user_data.status = UserStatus.OFFLINE
            self.set_buddy_last_seen(user, is_online=False)

        self.save_buddy_list()

    def add_buddy(self, user):

        if user in self.buddies:
            return

        note = country = ""
        is_trusted = notify_status = is_prioritized = False
        last_seen = "Never seen"

        self.buddies[user] = user_data = Buddy(
            username=user,
            note=note,
            notify_status=notify_status,
            is_prioritized=is_prioritized,
            is_trusted=is_trusted,
            last_seen=last_seen,
            country=country,
            status=UserStatus.OFFLINE
        )
        self.save_buddy_list()

        events.emit("add-buddy", user, user_data)

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

        self.buddies[user].note = note
        self.save_buddy_list()

        events.emit("buddy-note", user, note)

    def set_buddy_notify(self, user, notify):

        if user not in self.buddies:
            return

        self.buddies[user].notify_status = notify
        self.save_buddy_list()

        events.emit("buddy-notify", user, notify)

    def set_buddy_prioritized(self, user, prioritized):

        if user not in self.buddies:
            return

        self.buddies[user].is_prioritized = prioritized
        self.save_buddy_list()

        events.emit("buddy-prioritized", user, prioritized)

    def set_buddy_trusted(self, user, trusted):

        if user not in self.buddies:
            return

        self.buddies[user].is_trusted = trusted
        self.save_buddy_list()

        events.emit("buddy-trusted", user, trusted)

    def set_buddy_last_seen(self, user, is_online):

        if user not in self.buddies:
            return

        previous_last_seen = self.buddies[user].last_seen

        if is_online:
            self.buddies[user].last_seen = ""

        elif not previous_last_seen:
            self.buddies[user].last_seen = time.strftime("%m/%d/%Y %H:%M:%S")

        else:
            return

        events.emit("buddy-last-seen", user, is_online)

    def _user_country(self, user, country_code):

        if not country_code:
            return

        if user not in self.buddies:
            return

        self.buddies[user].country = f"flag_{country_code}"

    def save_buddy_list(self):

        if not self.allow_saving_buddies:
            return

        user_rows = []

        for user, user_data in self.buddies.items():
            user_rows.append([
                user,
                user_data.note,
                user_data.notify_status,
                user_data.is_prioritized,
                user_data.is_trusted,
                user_data.last_seen,
                user_data.country
            ])

        config.sections["server"]["userlist"] = user_rows
        config.write_configuration()

    def _user_status(self, msg):
        """ Server code: 7 """

        user = msg.user

        if user not in self.buddies:
            return

        if msg.status == self.buddies[user].status:
            # Buddy status didn't change, don't show notification'
            return

        self.buddies[user].status = msg.status
        self.set_buddy_last_seen(user, is_online=bool(msg.status))

        notify = self.buddies[user].notify_status

        if not notify:
            return

        if msg.status == UserStatus.AWAY:
            status_text = _("%(user)s is away")

        elif msg.status == UserStatus.ONLINE:
            status_text = _("%(user)s is online")

        else:
            status_text = _("%(user)s is offline")

        log.add(status_text, {"user": user})
        core.notifications.show_notification(status_text % {"user": user}, title=_("Buddy Status"))
