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

import os
import time

from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.logfacility import log
from pynicotine.shares import PermissionLevel
from pynicotine.slskmessages import CloseConnection
from pynicotine.slskmessages import UserInfoRequest
from pynicotine.slskmessages import UserInfoResponse
from pynicotine.slskmessages import UserInterests
from pynicotine.utils import encode_path
from pynicotine.utils import unescape


class UserInfo:
    __slots__ = ("users", "requested_info_times")

    def __init__(self):

        self.users = set()
        self.requested_info_times = {}

        for event_name, callback in (
            ("quit", self._quit),
            ("server-login", self._server_login),
            ("server-disconnect", self._server_disconnect),
            ("user-info-progress", self._user_info_progress),
            ("user-info-request", self._user_info_request)
        ):
            events.connect(event_name, callback)

    def _quit(self):
        self.remove_all_users()

    def _server_login(self, msg):

        if not msg.success:
            return

        for username in self.users:
            core.users.watch_user(username, context="userinfo")  # Get notified of user status

    def _server_disconnect(self, _msg):
        self.requested_info_times.clear()

    def _get_user_info_response(self, requesting_username=None, requesting_ip_address=None):

        if requesting_username is not None and requesting_ip_address is not None:
            permission_level, reject_reason = core.shares.check_user_permission(
                requesting_username, requesting_ip_address)
        else:
            permission_level = PermissionLevel.PUBLIC
            reject_reason = None

        if permission_level == PermissionLevel.BANNED:
            # Hide most details from banned users
            pic = None
            descr = ""
            totalupl = queuesize = uploadallowed = 0
            slotsavail = False

            if reject_reason:
                descr = f"You are not allowed to download my shared files.\nReason: {reject_reason}"
        else:
            try:
                with open(encode_path(os.path.expandvars(config.sections["userinfo"]["pic"])), "rb") as file_handle:
                    pic = file_handle.read()

            except Exception:
                pic = None

            descr = unescape(config.sections["userinfo"]["descr"])

            totalupl = core.uploads.get_total_uploads_allowed()
            queuesize = core.uploads.get_upload_queue_size(requesting_username)
            slotsavail = core.uploads.is_new_upload_accepted()

            if config.sections["transfers"]["remotedownloads"]:
                uploadallowed = config.sections["transfers"]["uploadallowed"]
            else:
                uploadallowed = 0

        msg = UserInfoResponse(
            descr=descr, pic=pic, totalupl=totalupl, queuesize=queuesize, slotsavail=slotsavail,
            uploadallowed=uploadallowed
        )
        msg.username = core.users.login_username or config.sections["server"]["login"]
        return msg

    def show_user(self, username=None, refresh=False, switch_page=True):

        local_username = core.users.login_username or config.sections["server"]["login"]

        if not username:
            username = local_username

            if not username:
                core.setup()
                return

        if username not in self.users:
            self.users.add(username)
            refresh = True

        events.emit("user-info-show-user", user=username, refresh=refresh, switch_page=switch_page)

        if not refresh:
            return

        # Request user status, speed and number of shared files
        core.users.watch_user(username, context="userinfo")

        # Request user interests
        core.send_message_to_server(UserInterests(username))

        if username == local_username:
            msg = self._get_user_info_response()
            events.emit("user-info-response", msg)
        else:
            # Request user description, picture and queue information
            core.send_message_to_peer(username, UserInfoRequest())

    def remove_user(self, username):

        self.users.remove(username)
        core.users.unwatch_user(username, context="userinfo")
        events.emit("user-info-remove-user", username)

    def remove_all_users(self):
        for username in self.users.copy():
            self.remove_user(username)

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

    def _user_info_progress(self, username, sock, _buffer_len, _msg_size_total):

        if username not in self.users:
            # We've removed the user. Close the connection to stop the user from
            # sending their response and wasting bandwidth.
            core.send_message_to_network_thread(CloseConnection(sock))

    def _user_info_request(self, msg):
        """Peer code 15."""

        username = msg.username
        ip_address, _port = msg.addr
        request_time = time.monotonic()

        if username in self.requested_info_times and request_time < self.requested_info_times[username] + 0.4:
            # Ignoring request, because it's less than half a second since the
            # last one by this user
            return

        self.requested_info_times[username] = request_time
        msg = self._get_user_info_response(username, ip_address)

        log.add(_("User %(user)s is viewing your profile"), {"user": username})
        core.send_message_to_peer(username, msg)
