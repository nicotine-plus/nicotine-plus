# COPYRIGHT (C) 2021-2023 Nicotine+ Contributors
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

from pynicotine import slskmessages
from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.logfacility import log
from pynicotine.slskmessages import UserStatus
from pynicotine.utils import encode_path
from pynicotine.utils import unescape


class UserInfo:

    def __init__(self):

        self.users = set()
        self.requested_info_times = {}

        for event_name, callback in (
            ("quit", self._quit),
            ("server-login", self._server_login),
            ("server-disconnect", self._server_disconnect),
            ("user-info-request", self._user_info_request)
        ):
            events.connect(event_name, callback)

    def _quit(self):
        self.users.clear()

    def _server_login(self, msg):

        if not msg.success:
            return

        for user in self.users:
            core.watch_user(user)  # Get notified of user status

    def _server_disconnect(self, _msg):
        self.requested_info_times.clear()

    def show_user(self, user, refresh=False, switch_page=True):

        if user not in self.users:
            self.users.add(user)
            refresh = True

        events.emit("user-info-show-user", user=user, refresh=refresh, switch_page=switch_page)

        if core.user_status == UserStatus.OFFLINE:
            events.emit("peer-connection-error", user)
            return

        if not refresh:
            return

        # Request user description, picture and queue information
        core.send_message_to_peer(user, slskmessages.UserInfoRequest())

        # Request user status, speed and number of shared files
        core.watch_user(user, force_update=True)

        # Request user interests
        core.queue.append(slskmessages.UserInterests(user))

        # Set user country
        events.emit("user-country", user, core.get_user_country(user))

    def remove_user(self, user):
        self.users.remove(user)
        events.emit("user-info-remove-user", user)

    @staticmethod
    def save_user_picture(file_path, picture_bytes):

        try:
            with open(encode_path(file_path), "wb") as file_handle:
                file_handle.write(picture_bytes)

            log.add(_("Picture saved to %s"), file_path)

        except Exception as error:
            log.add(_("Cannot save picture to %(filename)s: %(error)s"), {
                "filename": file_path,
                "error": error
            })

    def _user_info_request(self, msg):
        """ Peer code: 15 """

        user = msg.init.target_user
        ip_address, _port = msg.init.addr
        request_time = time.time()

        if user in self.requested_info_times and request_time < self.requested_info_times[user] + 0.4:
            # Ignoring request, because it's less than half a second since the
            # last one by this user
            return

        self.requested_info_times[user] = request_time

        if core.login_username != user:
            log.add(_("User %(user)s is viewing your profile"), {"user": user})

        status, reason = core.network_filter.check_user(user, ip_address)

        if not status:
            pic = None
            descr = core.ban_message % reason
            descr += "\n\n----------------------------------------------\n\n"
            descr += unescape(config.sections["userinfo"]["descr"])

        else:
            try:
                userpic = config.sections["userinfo"]["pic"]

                with open(encode_path(userpic), "rb") as file_handle:
                    pic = file_handle.read()

            except Exception:
                pic = None

            descr = unescape(config.sections["userinfo"]["descr"])

        totalupl = core.transfers.get_total_uploads_allowed()
        queuesize = core.transfers.get_upload_queue_size()
        slotsavail = core.transfers.allow_new_uploads()

        if config.sections["transfers"]["remotedownloads"]:
            uploadallowed = config.sections["transfers"]["uploadallowed"]
        else:
            uploadallowed = 0

        core.queue.append(
            slskmessages.UserInfoResponse(msg.init, descr, pic, totalupl, queuesize, slotsavail, uploadallowed))
