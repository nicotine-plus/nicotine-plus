# COPYRIGHT (C) 2020-2024 Nicotine+ Contributors
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

from itertools import chain
from threading import Thread

from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.logfacility import log
from pynicotine.slskmessages import CloseConnection
from pynicotine.slskmessages import SharedFileListRequest
from pynicotine.slskmessages import SharedFileListResponse
from pynicotine.slskmessages import UploadQueueNotification
from pynicotine.utils import clean_file
from pynicotine.utils import encode_path


class BrowsedUser:
    __slots__ = ("username", "public_folders", "private_folders", "num_folders", "num_files",
                 "shared_size")

    def __init__(self, username):

        self.username = username
        self.public_folders = {}
        self.private_folders = {}
        self.num_folders = None
        self.num_files = None
        self.shared_size = None

    def clear(self):

        self.public_folders.clear()
        self.private_folders.clear()
        self.num_folders = self.num_files = self.shared_size = None


class UserBrowse:
    __slots__ = ("users",)

    def __init__(self):

        self.users = {}

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

        for username in self.users:
            core.users.watch_user(username, context="userbrowse")  # Get notified of user status

    def send_upload_attempt_notification(self, username):
        """Send notification to user when attempting to initiate upload from
        our end."""

        core.send_message_to_peer(username, UploadQueueNotification())

    def _show_user(self, username, path=None, switch_page=True):

        if username not in self.users:
            self.users[username] = BrowsedUser(username)

        events.emit("user-browse-show-user", user=username, path=path, switch_page=switch_page)

    def remove_user(self, username):

        del self.users[username]
        core.users.unwatch_user(username, context="userbrowse")
        events.emit("user-browse-remove-user", username)

    def remove_all_users(self):
        for username in self.users.copy():
            self.remove_user(username)

    def _parse_local_shares(self, username, msg):
        """Parse a local shares list and show it in the UI."""

        msg.parse_network_message(memoryview(msg.make_network_message()))
        msg.username = username

        events.emit_main_thread("shared-file-list-response", msg)

    def browse_local_shares(self, path=None, permission_level=None, new_request=False, switch_page=True):
        """Browse your own shares."""

        username = core.users.login_username or config.sections["server"]["login"]

        if not username:
            core.setup()
            return

        if username not in self.users or new_request:
            if not permission_level:
                # Check our own permission level, and show relevant shares for it
                current_permission_level, _reason = core.shares.check_user_permission(username)
            else:
                current_permission_level = permission_level

            msg = core.shares.compressed_shares.get(current_permission_level)
            Thread(
                target=self._parse_local_shares, args=(username, msg), name="LocalShareParser", daemon=True
            ).start()

        self._show_user(username, path=path, switch_page=switch_page)
        core.users.watch_user(username, context="userbrowse")

    def request_user_shares(self, username):
        core.send_message_to_peer(username, SharedFileListRequest())

    def browse_user(self, username, path=None, new_request=False, switch_page=True):
        """Browse a user's shares."""

        if not username:
            return

        browsed_user = self.users.get(username)
        local_username = core.users.login_username or config.sections["server"]["login"]

        if browsed_user is not None and new_request:
            browsed_user.clear()

        if username == local_username:
            self.browse_local_shares(path, new_request, switch_page=switch_page)
            return

        self._show_user(username, path=path, switch_page=switch_page)
        core.users.watch_user(username, context="userbrowse")

        if browsed_user is None or new_request:
            self.request_user_shares(username)

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

    def iter_matching_folders(self, requested_folder_path, browsed_user, recurse=False):

        for folders in (browsed_user.public_folders, browsed_user.private_folders):
            for folder_path, files in folders.items():
                if (requested_folder_path != folder_path
                        and not (recurse and folder_path.startswith(f"{requested_folder_path}\\"))):
                    continue

                yield folder_path, files

                if not recurse:
                    return

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
                    shares_list = json.load(file_handle)

            ext = ""

            for _folder_path, files in shares_list:
                # Sanitization
                for file_info in files:
                    if not isinstance(file_info[1], str):
                        raise TypeError("Invalid file name")

                    if not isinstance(file_info[2], int):
                        raise TypeError("Invalid file size")

                    attrs = file_info[4]

                    if isinstance(attrs, dict):
                        # JSON stores file attribute types as strings, convert them back to integers
                        attrs = {int(k): v for k, v in attrs.items()}
                    else:
                        attrs = list(attrs)

                    file_info[3] = ext

        except Exception as error:
            log.add(_("Loading Shares from disk failed: %(error)s"), {"error": error})
            return

        username = os.path.basename(file_path)
        browsed_user = self.users.get(username)

        if browsed_user is not None:
            browsed_user.clear()

        self._show_user(username)

        msg = SharedFileListResponse()
        msg.username = username
        msg.list = shares_list

        events.emit("shared-file-list-response", msg)

    def save_shares_list_to_disk(self, username):

        folder_path = self.create_user_shares_folder()

        if not folder_path:
            return

        try:
            file_path = os.path.join(folder_path, clean_file(username))
            browsed_user = self.users[username]

            with open(encode_path(file_path), "w", encoding="utf-8") as file_handle:
                # Dump every folder to the file individually to avoid large memory usage
                json_encoder = json.JSONEncoder(check_circular=False, ensure_ascii=False)
                is_first_item = True

                file_handle.write("[")

                for folders in (browsed_user.public_folders, browsed_user.private_folders):
                    for item in folders.items():
                        if is_first_item:
                            is_first_item = False
                        else:
                            file_handle.write(",\n")

                        file_handle.write(json_encoder.encode(item))

                file_handle.write("]")

            log.add(_("Saved list of shared files for user '%(user)s' to %(dir)s"),
                    {"user": username, "dir": folder_path})

        except Exception as error:
            log.add(_("Can't save shares, '%(user)s', reported error: %(error)s"), {"user": username, "error": error})

    def download_file(self, username, folder_path, file_data, download_folder_path=None):

        _code, basename, file_size, _ext, file_attributes, *_unused = file_data
        file_path = "\\".join([folder_path, basename])

        core.downloads.enqueue_download(
            username, file_path, folder_path=download_folder_path, size=file_size, file_attributes=file_attributes)

    def download_folder(self, username, requested_folder_path, download_folder_path=None, recurse=False,
                        check_num_files=True):

        if requested_folder_path is None:
            return

        num_files = 0

        for folder_path, files in self.iter_matching_folders(
            requested_folder_path, browsed_user=self.users[username], recurse=recurse
        ):
            num_files += len(files)

        if check_num_files and num_files > 1000:
            # Large folder, ask user for confirmation before downloading
            check_num_files = False
            events.emit(
                "download-large-folder", username, requested_folder_path, num_files,
                self.download_folder, (
                    username, requested_folder_path, download_folder_path, recurse, check_num_files
                )
            )
            return

        for folder_path, files in self.iter_matching_folders(
            requested_folder_path, browsed_user=self.users[username], recurse=recurse
        ):
            # Get final download destination
            destination_folder_path = core.downloads.get_folder_destination(
                username, folder_path, root_folder_path=requested_folder_path,
                download_folder_path=download_folder_path)

            if files:
                for _code, basename, file_size, _ext, file_attributes, *_unused in files:
                    file_path = "\\".join([folder_path, basename])

                    core.downloads.enqueue_download(
                        username, file_path, folder_path=destination_folder_path, size=file_size,
                        file_attributes=file_attributes)

    def upload_file(self, username, folder_path, file_data):

        _code, basename, *_unused = file_data
        file_path = "\\".join([folder_path, basename])

        core.uploads.enqueue_upload(username, file_path)

    def upload_folder(self, username, requested_folder_path, local_browsed_user, recurse=False):

        if not requested_folder_path or not username:
            return

        for folder_path, files in self.iter_matching_folders(
            requested_folder_path, browsed_user=local_browsed_user, recurse=recurse
        ):
            for _code, basename, *_unused in files:
                file_path = "\\".join([folder_path, basename])
                core.uploads.enqueue_upload(username, file_path)

    @staticmethod
    def get_soulseek_url(username, path):

        import urllib.parse
        path = path.replace("\\", "/")
        return "slsk://" + urllib.parse.quote(f"{username}/{path}")

    def open_soulseek_url(self, url):

        import urllib.parse

        url = urllib.parse.unquote(url.replace("slsk://", "", 1))
        username, _separator, file_path = url.partition("/")
        file_path = file_path.replace("/", "\\")

        self.browse_user(username, path=file_path)

    def _shared_file_list_progress(self, username, sock, _buffer_len, _msg_size_total):

        if username not in self.users:
            # We've removed the user. Close the connection to stop the user from
            # sending their response and wasting bandwidth.
            core.send_message_to_network_thread(CloseConnection(sock))

    def _shared_file_list_response(self, msg):

        username = msg.username
        browsed_user = self.users.get(username)
        num_folders = len(msg.list) + len(msg.privatelist)
        num_files = 0
        shared_size = 0

        for _folder_path, files in chain(msg.list, msg.privatelist):
            for file_info in files:
                shared_size += file_info[2]

            num_files += len(files)

        if browsed_user is not None:
            browsed_user.public_folders = dict(msg.list)
            browsed_user.private_folders = dict(msg.privatelist)
            browsed_user.num_folders = num_folders
            browsed_user.num_files = num_files
            browsed_user.shared_size = shared_size

        core.pluginhandler.user_stats_notification(username, stats={
            "avgspeed": None,
            "files": num_files,
            "dirs": num_folders,
            "shared_size": shared_size,
            "source": "peer"
        })
