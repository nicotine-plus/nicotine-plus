# COPYRIGHT (C) 2020-2021 Nicotine+ Team
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

import threading

from pynicotine import slskmessages
from pynicotine.logfacility import log
from pynicotine.utils import RestrictedUnpickler


class UserBrowse:

    def __init__(self, core, config, ui_callback=None):

        self.core = core
        self.config = config
        self.users = set()
        self.ui_callback = None

        if hasattr(ui_callback, "userbrowse"):
            self.ui_callback = ui_callback.userbrowse

    def server_login(self):
        for user in self.users:
            self.core.watch_user(user)  # Get notified of user status

    def server_disconnect(self):
        if self.ui_callback:
            self.ui_callback.server_disconnect()

    def send_upload_attempt_notification(self, username):
        """ Send notification to user when attempting to initiate upload from our end """

        self.core.send_message_to_peer(username, slskmessages.UploadQueueNotification(None))

    def add_user(self, user):

        if user not in self.users:
            self.core.watch_user(user, force_update=True)
            self.users.add(user)

    def remove_user(self, user):
        self.users.remove(user)

    def show_user(self, user, folder=None, local_shares_type=None, indeterminate_progress=False, switch_page=True):

        self.add_user(user)

        if self.ui_callback:
            self.ui_callback.show_user(user, folder, local_shares_type, indeterminate_progress, switch_page)

    def parse_local_shares(self, username, msg):
        """ Parse a local shares list and show it in the UI """

        built = msg.make_network_message()
        msg.parse_network_message(built)

        self.shared_file_list(username, msg)

    def browse_local_public_shares(self, folder=None, new_request=None):
        """ Browse your own public shares """

        username = self.config.sections["server"]["login"]

        if username not in self.users or new_request:
            msg = self.core.shares.get_compressed_shares_message("normal")
            thread = threading.Thread(target=self.parse_local_shares, args=(username, msg))
            thread.name = "LocalShareParser"
            thread.daemon = True
            thread.start()

        self.show_user(username, folder=folder, local_shares_type="normal", indeterminate_progress=True)

    def browse_local_buddy_shares(self, folder=None, new_request=False):
        """ Browse your own buddy shares """

        username = self.config.sections["server"]["login"]

        if username not in self.users or new_request:
            msg = self.core.shares.get_compressed_shares_message("buddy")
            thread = threading.Thread(target=self.parse_local_shares, args=(username, msg))
            thread.name = "LocalBuddyShareParser"
            thread.daemon = True
            thread.start()

        self.show_user(username, folder=folder, local_shares_type="buddy", indeterminate_progress=True)

    def browse_user(self, username, folder=None, local_shares_type=None, new_request=False, switch_page=True):
        """ Browse a user's shares """

        if not username:
            return

        if username == self.config.sections["server"]["login"]:
            if local_shares_type == "normal":
                self.browse_local_public_shares(folder, new_request)
                return

            self.browse_local_buddy_shares(folder, new_request)
            return

        if username not in self.users or new_request:
            self.core.send_message_to_peer(username, slskmessages.GetSharedFileList(None))

        self.show_user(username, folder=folder, switch_page=switch_page)

    @staticmethod
    def get_shares_list_from_disk(filename):

        try:
            try:
                # Try legacy format first
                import bz2

                with bz2.BZ2File(filename) as file_handle:
                    shares_list = RestrictedUnpickler(file_handle, encoding='utf-8').load()

            except Exception:
                # Try new format

                with open(filename, encoding="utf-8") as file_handle:
                    import json
                    shares_list = json.load(file_handle)

            if not isinstance(shares_list, (list, dict)):
                raise TypeError("Bad data in file %(sharesdb)s" % {'sharesdb': filename})

            return shares_list

        except Exception as msg:
            log.add(_("Loading Shares from disk failed: %(error)s"), {'error': msg})

        return None

    def load_local_shares_list(self, username, shares_list):

        self.show_user(username)

        msg = slskmessages.SharedFileList(None)
        msg.list = shares_list

        self.shared_file_list(username, msg)

    def show_connection_error(self, username):
        if self.ui_callback:
            self.ui_callback.show_connection_error(username)

    def set_conn(self, username, conn):
        if self.ui_callback:
            self.ui_callback.set_conn(username, conn)

    def get_user_status(self, msg):
        if self.ui_callback:
            self.ui_callback.get_user_status(msg)

    def shared_file_list(self, user, msg):
        if self.ui_callback:
            self.ui_callback.shared_file_list(user, msg)

    def update_gauge(self, msg):
        if self.ui_callback:
            self.ui_callback.update_gauge(msg)
