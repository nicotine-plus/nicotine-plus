# COPYRIGHT (C) 2020-2023 Nicotine+ Contributors
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

import json
import os

from threading import Thread

from pynicotine import slskmessages
from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.logfacility import log
from pynicotine.utils import clean_file
from pynicotine.utils import encode_path


class UserBrowse:

    def __init__(self):

        self.user_shares = {}

        for event_name, callback in (
            ("quit", self._quit),
            ("server-login", self._server_login),
            ("shared-file-list-progress", self._shared_file_list_progress),
            ("shared-file-list-response", self._shared_file_list_response)
        ):
            events.connect(event_name, callback)

    def _quit(self):
        self.remove_all_users()

    def _server_login(self, msg):

        if not msg.success:
            return

        for username in self.user_shares:
            core.watch_user(username)  # Get notified of user status

    def send_upload_attempt_notification(self, username):
        """Send notification to user when attempting to initiate upload from
        our end."""

        core.send_message_to_peer(username, slskmessages.UploadQueueNotification())

    def _show_user(self, username, path=None, local_share_type=None, switch_page=True):

        if username not in self.user_shares:
            self.user_shares[username] = {}

        events.emit(
            "user-browse-show-user", user=username, path=path, local_share_type=local_share_type,
            switch_page=switch_page)

    def remove_user(self, username):
        del self.user_shares[username]
        events.emit("user-browse-remove-user", username)

    def remove_all_users(self):
        for username in self.user_shares.copy():
            self.remove_user(username)

    def _parse_local_shares(self, username, msg):
        """Parse a local shares list and show it in the UI."""

        built = msg.make_network_message()
        msg.parse_network_message(built)
        msg.init = slskmessages.PeerInit(target_user=username)

        events.emit_main_thread("shared-file-list-response", msg)

    def browse_local_shares(self, path=None, share_type="buddy", new_request=False):
        """Browse your own shares."""

        username = config.sections["server"]["login"] or "Default"

        if username not in self.user_shares or new_request:
            msg = core.shares.compressed_shares.get(share_type)
            Thread(
                target=self._parse_local_shares, args=(username, msg), name="LocalShareParser", daemon=True
            ).start()

        self._show_user(username, path=path, local_share_type=share_type)

    def browse_user(self, username, path=None, local_share_type="buddy", new_request=False, switch_page=True):
        """Browse a user's shares."""

        if not username:
            return

        user_share = self.user_shares.get(username)

        if user_share and new_request:
            user_share.clear()

        if username == (config.sections["server"]["login"] or "Default"):
            self.browse_local_shares(path, local_share_type, new_request)
            return

        self._show_user(username, path=path, switch_page=switch_page)

        if core.user_status == slskmessages.UserStatus.OFFLINE:
            events.emit("peer-connection-error", username)
            return

        core.watch_user(username)

        if not user_share or new_request:
            core.send_message_to_peer(username, slskmessages.SharedFileListRequest())

    def create_user_shares_folder(self):

        shares_folder = os.path.join(config.data_folder_path, "usershares")
        shares_folder_encoded = encode_path(shares_folder)

        try:
            if not os.path.isdir(shares_folder_encoded):
                os.makedirs(shares_folder_encoded)

        except Exception as error:
            log.add(_("Can't create directory '%(folder)s', reported error: %(error)s"),
                    {"folder": shares_folder, "error": error})
            return None

        return shares_folder

    def load_shares_list_from_disk(self, file_path):

        file_path_encoded = encode_path(file_path)

        try:
            try:
                # Try legacy format first
                import bz2

                with bz2.BZ2File(file_path_encoded) as file_handle:
                    from pynicotine.shares import RestrictedUnpickler
                    shares_list = RestrictedUnpickler(file_handle, encoding="utf-8").load()

            except Exception:
                # Try new format

                with open(file_path_encoded, encoding="utf-8") as file_handle:
                    # JSON stores file attribute types as strings, convert them back to integers with object_hook
                    shares_list = json.load(file_handle, object_hook=lambda d: {int(k): v for k, v in d.items()})

            # Basic sanity check
            for _folder, files in shares_list:
                for _code, _basename, _size, _ext, _attrs, *_unused in files:
                    break

        except Exception as error:
            log.add(_("Loading Shares from disk failed: %(error)s"), {"error": error})
            return

        username = os.path.basename(file_path)
        user_share = self.user_shares.get(username)

        if user_share:
            user_share.clear()

        self._show_user(username)

        msg = slskmessages.SharedFileListResponse(init=slskmessages.PeerInit(target_user=username))
        msg.list = shares_list

        events.emit("shared-file-list-response", msg)

    def save_shares_list_to_disk(self, username):

        folder_path = self.create_user_shares_folder()

        if not folder_path:
            return

        try:
            file_path = os.path.join(folder_path, clean_file(username))

            with open(encode_path(file_path), "w", encoding="utf-8") as file_handle:
                # Dump every folder to the file individually to avoid large memory usage
                json_encoder = json.JSONEncoder(check_circular=False, ensure_ascii=False)
                is_first_item = True

                file_handle.write("[")

                for item in self.user_shares[username].items():
                    if is_first_item:
                        is_first_item = False
                    else:
                        file_handle.write(", ")

                    file_handle.write(json_encoder.encode(item))

                file_handle.write("]")

            log.add(_("Saved list of shared files for user '%(user)s' to %(dir)s"),
                    {"user": username, "dir": folder_path})

        except Exception as error:
            log.add(_("Can't save shares, '%(user)s', reported error: %(error)s"), {"user": username, "error": error})

    def download_file(self, username, folder_path, file_data, download_folder_path=None):

        _code, basename, file_size, _ext, file_attributes, *_unused = file_data
        file_path = "\\".join([folder_path, basename])

        core.downloads.get_file(
            username, file_path, folder_path=download_folder_path, size=file_size, file_attributes=file_attributes)

    def download_folder(self, username, requested_folder_path, download_folder_path=None, recurse=False):

        if requested_folder_path is None:
            return

        for folder_path, files in self.user_shares[username].items():
            if not recurse and requested_folder_path != folder_path:
                continue

            if requested_folder_path not in folder_path:
                # Not a subfolder of the requested folder, skip
                continue

            # Get final download destination
            destination_folder_path = core.downloads.get_folder_destination(
                username, folder_path, root_folder_path=requested_folder_path,
                download_folder_path=download_folder_path)

            if files:
                for _code, basename, file_size, _ext, file_attributes, *_unused in files:
                    file_path = "\\".join([folder_path, basename])

                    core.downloads.get_file(
                        username, file_path, folder_path=destination_folder_path, size=file_size,
                        file_attributes=file_attributes)

            if not recurse:
                # Downloading a single folder, no need to continue
                return

    def upload_file(self, username, folder_path, file_data, locally_queued=False):

        _code, basename, file_size, *_unused = file_data
        file_path = "\\".join([folder_path, basename])

        core.uploads.push_file(username, file_path, size=file_size, locally_queued=locally_queued)

    def upload_folder(self, username, requested_folder_path, recurse=False):

        if not requested_folder_path or not username:
            return

        for folder_path, files in self.user_shares[username].items():
            if not recurse and requested_folder_path != folder_path:
                continue

            if requested_folder_path not in folder_path:
                # Not a subfolder of the requested folder, skip
                continue

            if files:
                locally_queued = False

                for _code, basename, file_size, *_unused in files:
                    file_path = "\\".join([folder_path, basename])

                    core.uploads.push_file(username, file_path, size=file_size, locally_queued=locally_queued)
                    locally_queued = True

            if not recurse:
                # Uploading a single folder, no need to continue
                return

    @staticmethod
    def get_soulseek_url(username, path):

        import urllib.parse
        path = path.replace("\\", "/")
        return "slsk://" + urllib.parse.quote(f"{username}/{path}")

    def open_soulseek_url(self, url):

        import urllib.parse
        url_split = urllib.parse.unquote(url[7:]).split("/", 1)

        if len(url_split) >= 2:
            username, file_path = url_split
            file_path = file_path.replace("/", "\\")
        else:
            username, = url_split
            file_path = None

        self.browse_user(username, path=file_path)

    def _shared_file_list_progress(self, username, sock, _buffer_len, _msg_size_total):

        if username not in self.user_shares:
            # We've removed the user. Close the connection to stop the user from
            # sending their response and wasting bandwidth.
            core.send_message_to_network_thread(slskmessages.CloseConnection(sock))

    def _shared_file_list_response(self, msg):

        username = msg.init.target_user

        if username in self.user_shares:
            self.user_shares[username] = dict(msg.list + msg.privatelist) if msg.privatelist else dict(msg.list)
