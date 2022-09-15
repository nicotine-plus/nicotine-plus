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

from pynicotine import slskmessages
from pynicotine.logfacility import log
from pynicotine.slskmessages import UserStatus
from pynicotine.utils import encode_path
from pynicotine.utils import unescape


class UserInfo:

    def __init__(self, core, config, queue, ui_callback=None):

        self.core = core
        self.config = config
        self.queue = queue
        self.users = set()
        self.requested_info_times = {}
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

        if self.ui_callback:
            self.ui_callback.remove_user(user)

    def show_user(self, user, switch_page=True):
        if self.ui_callback:
            self.ui_callback.show_user(user, switch_page)

    def request_user_info(self, user, switch_page=True):

        self.add_user(user)
        self.show_user(user, switch_page)

        if self.core.user_status == UserStatus.OFFLINE:
            self.show_connection_error(user)
            return

        # Request user description, picture and queue information
        self.core.send_message_to_peer(user, slskmessages.UserInfoRequest())

        # Request user status, speed and number of shared files
        self.core.watch_user(user, force_update=True)

        # Request user interests
        self.queue.append(slskmessages.UserInterests(user))

        # Request user country
        self.set_user_country(user, self.core.get_user_country(user))

    def show_connection_error(self, username):
        if self.ui_callback:
            self.ui_callback.show_connection_error(username)

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

    def peer_message_progress(self, msg):
        if self.ui_callback:
            self.ui_callback.peer_message_progress(msg)

    def peer_connection_closed(self, msg):
        if self.ui_callback:
            self.ui_callback.peer_connection_closed(msg)

    def get_user_stats(self, msg):
        """ Server code: 36 """

        if self.ui_callback:
            self.ui_callback.get_user_stats(msg)

    def get_user_status(self, msg):
        """ Server code: 7 """

        if self.ui_callback:
            self.ui_callback.get_user_status(msg)

    def set_user_country(self, user, country_code):
        if self.ui_callback:
            self.ui_callback.set_user_country(user, country_code)

    def user_info_request(self, msg):
        """ Peer code: 15 """

        user = msg.init.target_user
        ip_address, _port = msg.init.addr
        request_time = time.time()

        if user in self.requested_info_times and request_time < self.requested_info_times[user] + 0.4:
            # Ignoring request, because it's less than half a second since the
            # last one by this user
            return

        self.requested_info_times[user] = request_time

        if self.core.login_username != user:
            log.add(_("User %(user)s is reading your user info"), {'user': user})

        status, reason = self.core.network_filter.check_user(user, ip_address)

        if not status:
            pic = None
            descr = self.core.ban_message % reason
            descr += "\n\n----------------------------------------------\n\n"
            descr += unescape(self.config.sections["userinfo"]["descr"])

        else:
            try:
                userpic = self.config.sections["userinfo"]["pic"]

                with open(encode_path(userpic), 'rb') as file_handle:
                    pic = file_handle.read()

            except Exception:
                pic = None

            descr = unescape(self.config.sections["userinfo"]["descr"])

        totalupl = self.core.transfers.get_total_uploads_allowed()
        queuesize = self.core.transfers.get_upload_queue_size()
        slotsavail = self.core.transfers.allow_new_uploads()

        if self.config.sections["transfers"]["remotedownloads"]:
            uploadallowed = self.config.sections["transfers"]["uploadallowed"]
        else:
            uploadallowed = 0

        self.queue.append(
            slskmessages.UserInfoReply(msg.init, descr, pic, totalupl, queuesize, slotsavail, uploadallowed))

    def user_info_reply(self, msg):
        """ Peer code: 16 """

        if self.ui_callback:
            user = msg.init.target_user
            self.ui_callback.user_info_reply(user, msg)

    def user_interests(self, msg):
        """ Server code: 57 """

        if self.ui_callback:
            self.ui_callback.user_interests(msg)
