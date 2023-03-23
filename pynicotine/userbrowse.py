# COPYRIGHT (C) 2020-2022 Nicotine+ Contributors
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
from pynicotine.utils import RestrictedUnpickler


class UserBrowse:

    def __init__(self):

        self.user_shares = {}

        for event_name, callback in (
            ("quit", self._quit),
            ("server-login", self._server_login),
            ("shared-file-list-response", self._shared_file_list_response)
        ):
            events.connect(event_name, callback)

    def _quit(self):
        self.user_shares.clear()

    def _server_login(self, msg):

        if not msg.success:
            return

        for user in self.user_shares:
            core.watch_user(user)  # Get notified of user status

    def send_upload_attempt_notification(self, username):
        """ Send notification to user when attempting to initiate upload from our end """

        core.send_message_to_peer(username, slskmessages.UploadQueueNotification())

    def _show_user(self, user, path=None, local_shares_type=None, switch_page=True):

        if user not in self.user_shares:
            self.user_shares[user] = {}

        events.emit(
            "user-browse-show-user", user=user, path=path, local_shares_type=local_shares_type, switch_page=switch_page)

    def remove_user(self, user):
        del self.user_shares[user]
        events.emit("user-browse-remove-user", user)

    def _parse_local_shares(self, username, msg):
        """ Parse a local shares list and show it in the UI """

        built = msg.make_network_message()
        msg.parse_network_message(built)
        msg.init = slskmessages.PeerInit(target_user=username)

        events.emit_main_thread("shared-file-list-response", msg)

    def browse_local_shares(self, path=None, share_type=None, new_request=False):
        """ Browse your own shares """

        username = config.sections["server"]["login"] or "Default"

        if username not in self.user_shares or new_request:
            msg = core.shares.get_compressed_shares_message(share_type)
            Thread(
                target=self._parse_local_shares, args=(username, msg), name="LocalShareParser", daemon=True
            ).start()

        self._show_user(username, path=path, local_shares_type=share_type)

    def browse_user(self, username, path=None, local_shares_type="buddy", new_request=False, switch_page=True):
        """ Browse a user's shares """

        if not username:
            return

        user_share = self.user_shares.get(username)

        if user_share and new_request:
            user_share.clear()

        if username == (config.sections["server"]["login"] or "Default"):
            self.browse_local_shares(path, local_shares_type, new_request)
            return

        self._show_user(username, path=path, switch_page=switch_page)

        if core.user_status == slskmessages.UserStatus.OFFLINE:
            events.emit("peer-connection-error", username)
            return

        core.watch_user(username, force_update=True)

        if not user_share or new_request:
            core.send_message_to_peer(username, slskmessages.SharedFileListRequest())

    def create_user_shares_folder(self):

        shares_folder = os.path.join(config.data_dir, "usershares")
        shares_folder_encoded = encode_path(shares_folder)

        try:
            if not os.path.isdir(shares_folder_encoded):
                os.makedirs(shares_folder_encoded)

        except Exception as error:
            log.add(_("Can't create directory '%(folder)s', reported error: %(error)s"),
                    {"folder": shares_folder, "error": error})
            return None

        return shares_folder

    def load_shares_list_from_disk(self, filename):

        filename_encoded = encode_path(filename)

        def json_keys_to_integer(dictionary):
            # JSON stores file attribute types as strings, convert them back to integers
            return {int(k): v for k, v in dictionary}

        try:
            try:
                # Try legacy format first
                import bz2

                with bz2.BZ2File(filename_encoded) as file_handle:
                    shares_list = RestrictedUnpickler(file_handle, encoding="utf-8").load()

            except Exception:
                # Try new format

                with open(filename_encoded, encoding="utf-8") as file_handle:
                    shares_list = json.load(file_handle, object_pairs_hook=json_keys_to_integer)

            # Basic sanity check
            for _folder, files in shares_list:
                for _code, _filename, _size, _ext, _attrs, *_unused in files:
                    break

        except Exception as msg:
            log.add(_("Loading Shares from disk failed: %(error)s"), {"error": msg})
            return

        username = filename.replace("\\", os.sep).split(os.sep)[-1]
        user_share = self.user_shares.get(username)

        if user_share:
            user_share.clear()

        self._show_user(username)

        msg = slskmessages.SharedFileListResponse(init=slskmessages.PeerInit(target_user=username))
        msg.list = shares_list

        events.emit("shared-file-list-response", msg)

    def save_shares_list_to_disk(self, user):

        shares_folder = self.create_user_shares_folder()

        if not shares_folder:
            return

        try:
            path = os.path.join(shares_folder, clean_file(user))

            with open(encode_path(path), "w", encoding="utf-8") as file_handle:
                # Add line breaks for readability, but avoid indentation to decrease file size
                json.dump(list(self.user_shares[user].items()), file_handle, ensure_ascii=False, indent=0)

            log.add(_("Saved list of shared files for user '%(user)s' to %(dir)s"),
                    {"user": user, "dir": shares_folder})

        except Exception as error:
            log.add(_("Can't save shares, '%(user)s', reported error: %(error)s"), {"user": user, "error": error})

    def download_file(self, user, folder, file_data, prefix=""):

        virtualpath = "\\".join([folder, file_data[1]])
        size = file_data[2]
        h_bitrate, _bitrate, h_length, _length = slskmessages.FileListMessage.parse_result_bitrate_length(
            size, file_data[4])

        core.transfers.get_file(user, virtualpath, prefix, size=size, bitrate=h_bitrate, length=h_length)

    def download_folder(self, user, requested_folder, prefix="", recurse=False):

        if requested_folder is None:
            return

        remove_prefix = requested_folder.rsplit("\\", 1)[0]

        for folder, files in self.user_shares[user].items():
            if not recurse and requested_folder != folder:
                continue

            if requested_folder not in folder:
                # Not a subfolder of the requested folder, skip
                continue

            # Remember custom download location
            if prefix:
                core.transfers.requested_folders[user][folder] = prefix

            # Get final download destination
            destination = core.transfers.get_folder_destination(user, folder, remove_prefix)

            if files:
                for file_data in files:
                    virtualpath = "\\".join([folder, file_data[1]])
                    size = file_data[2]
                    h_bitrate, _bitrate, h_length, _length = slskmessages.FileListMessage.parse_result_bitrate_length(
                        size, file_data[4])

                    core.transfers.get_file(user, virtualpath, destination,
                                            size=size, bitrate=h_bitrate, length=h_length)

            if not recurse:
                # Downloading a single folder, no need to continue
                return

    def upload_file(self, user, folder, file_data, locally_queued=False):

        virtualpath = "\\".join([folder, file_data[1]])
        size = file_data[2]

        core.transfers.push_file(user, virtualpath, size, locally_queued=locally_queued)

    def upload_folder(self, user, requested_folder, recurse=False):

        if not requested_folder or not user:
            return

        for folder, files in self.user_shares[user].items():
            if not recurse and requested_folder != folder:
                continue

            if requested_folder not in folder:
                # Not a subfolder of the requested folder, skip
                continue

            if files:
                locally_queued = False

                for file_data in files:
                    filename = "\\".join([folder, file_data[1]])
                    size = file_data[2]

                    core.transfers.push_file(user, filename, size, locally_queued=locally_queued)
                    locally_queued = True

            if not recurse:
                # Uploading a single folder, no need to continue
                return

    @staticmethod
    def get_soulseek_url(user, path):
        import urllib.parse
        path = path.replace("\\", "/")
        return "slsk://" + urllib.parse.quote(f"{user}/{path}")

    def open_soulseek_url(self, url):

        import urllib.parse
        url_split = urllib.parse.unquote(url[7:]).split("/", 1)

        if len(url_split) >= 2:
            user, file_path = url_split
            file_path = file_path.replace("/", "\\")
        else:
            user, = url_split
            file_path = None

        self.browse_user(user, path=file_path)

    def _shared_file_list_response(self, msg):

        user = msg.init.target_user

        if user in self.user_shares:
            self.user_shares[user] = dict(msg.list + msg.privatelist)
