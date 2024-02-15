# COPYRIGHT (C) 2020-2024 Nicotine+ Contributors
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2016 Mutnick <muhing@yahoo.com>
# COPYRIGHT (C) 2013 eLvErDe <gandalf@le-vert.net>
# COPYRIGHT (C) 2008-2012 quinox <quinox@users.sf.net>
# COPYRIGHT (C) 2009 hedonist <ak@sensi.org>
# COPYRIGHT (C) 2006-2009 daelstorm <daelstorm@gmail.com>
# COPYRIGHT (C) 2003-2004 Hyriand <hyriand@thegraveyard.org>
# COPYRIGHT (C) 2001-2003 Alexander Kanavin
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
import time

from ast import literal_eval
from collections import defaultdict
from os.path import normpath

from pynicotine import slskmessages
from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.logfacility import log
from pynicotine.utils import encode_path
from pynicotine.utils import load_file
from pynicotine.utils import write_file_and_backup


class TransferStatus:
    QUEUED = "Queued"
    GETTING_STATUS = "Getting status"
    TRANSFERRING = "Transferring"
    PAUSED = "Paused"
    CANCELLED = "Cancelled"
    FILTERED = "Filtered"
    FINISHED = "Finished"
    USER_LOGGED_OFF = "User logged off"
    CONNECTION_CLOSED = "Connection closed"
    CONNECTION_TIMEOUT = "Connection timeout"
    DOWNLOAD_FOLDER_ERROR = "Download folder error"
    LOCAL_FILE_ERROR = "Local file error"


class Transfer:
    """This class holds information about a single transfer."""

    __slots__ = ("sock", "username", "virtual_path",
                 "folder_path", "token", "size", "file_handle", "start_time", "last_update",
                 "current_byte_offset", "last_byte_offset", "speed", "time_elapsed",
                 "time_left", "modifier", "queue_position", "file_attributes",
                 "iterator", "status", "legacy_attempt", "size_changed", "request_timer_id")

    def __init__(self, username, virtual_path=None, folder_path=None, size=0, file_attributes=None,
                 status=None, current_byte_offset=None):
        self.username = username
        self.virtual_path = virtual_path
        self.folder_path = folder_path
        self.size = size
        self.status = status
        self.current_byte_offset = current_byte_offset
        self.file_attributes = file_attributes

        self.sock = None
        self.file_handle = None
        self.token = None
        self.queue_position = 0
        self.modifier = None
        self.request_timer_id = None
        self.start_time = None
        self.last_update = None
        self.last_byte_offset = None
        self.speed = 0
        self.time_elapsed = 0
        self.time_left = 0
        self.iterator = None
        self.legacy_attempt = False
        self.size_changed = False

        if file_attributes is None:
            self.file_attributes = {}


class Transfers:

    def __init__(self, transfers_file_path):

        self.transfers = {}
        self.queued_transfers = {}
        self.queued_users = defaultdict(dict)
        self.active_users = defaultdict(dict)
        self.failed_users = defaultdict(dict)
        self.transfers_file_path = transfers_file_path
        self.total_bandwidth = 0

        self._allow_saving_transfers = False
        self._user_queue_limits = defaultdict(int)
        self._user_queue_sizes = defaultdict(int)

        for event_name, callback in (
            ("quit", self._quit),
            ("server-login", self._server_login),
            ("server-disconnect", self._server_disconnect),
            ("start", self._start)
        ):
            events.connect(event_name, callback)

    def _start(self):

        self._load_transfers()
        self._allow_saving_transfers = True

        # Save list of transfers every 3 minutes
        events.schedule(delay=180, callback=self._save_transfers, repeat=True)

        self.update_transfer_limits()

    def _quit(self):

        self._save_transfers()
        self._allow_saving_transfers = False

        self.transfers.clear()
        self.failed_users.clear()

    def _server_login(self, msg):

        if not msg.success:
            return

        # Watch transfers for user status updates
        for username in self.failed_users:
            core.users.watch_user(username)

        self.update_transfer_limits()

    def _server_disconnect(self, _msg):

        for users in (self.queued_users, self.active_users, self.failed_users):
            for transfers in users.copy().values():
                for transfer in transfers.copy().values():
                    self._abort_transfer(transfer, status=TransferStatus.USER_LOGGED_OFF)

        self.queued_transfers.clear()
        self.queued_users.clear()
        self.active_users.clear()
        self._user_queue_limits.clear()
        self._user_queue_sizes.clear()

        self.total_bandwidth = 0

    # Load Transfers #

    @staticmethod
    def _load_transfers_file(transfers_file):
        """Loads a file of transfers in json format."""

        transfers_file = encode_path(transfers_file)

        if not os.path.isfile(transfers_file):
            return None

        with open(transfers_file, encoding="utf-8") as handle:
            # JSON stores file attribute types as strings, convert them back to integers with object_hook
            return json.load(handle, object_hook=lambda d: {int(k): v for k, v in d.items()})

    @staticmethod
    def _load_legacy_transfers_file(transfers_file):
        """Loads a download queue file in pickle format (legacy)"""

        transfers_file = encode_path(transfers_file)

        if not os.path.isfile(transfers_file):
            return None

        with open(transfers_file, "rb") as handle:
            from pynicotine.shares import RestrictedUnpickler
            return RestrictedUnpickler(handle, encoding="utf-8").load()

    def _load_transfers(self):
        raise NotImplementedError

    def _load_file_attributes(self, num_attributes, transfer_row):

        if num_attributes < 7:
            return None

        loaded_file_attributes = transfer_row[6]

        if not loaded_file_attributes:
            return None

        if isinstance(loaded_file_attributes, dict):
            # Found dictionary with file attributes (Nicotine+ >=3.3.0), nothing more to do
            return loaded_file_attributes

        try:
            # Check if a dictionary is represented in string format
            return {int(k): v for k, v in literal_eval(loaded_file_attributes).items()}

        except (AttributeError, ValueError):
            pass

        # Legacy bitrate/duration strings (Nicotine+ <3.3.0)
        file_attributes = {}
        bitrate = str(loaded_file_attributes)
        is_vbr = (" (vbr)" in bitrate)

        try:
            file_attributes[slskmessages.FileAttribute.BITRATE] = int(bitrate.replace(" (vbr)", ""))

            if is_vbr:
                file_attributes[slskmessages.FileAttribute.VBR] = int(is_vbr)

        except ValueError:
            # No valid bitrate value found
            pass

        if num_attributes < 8:
            return file_attributes

        loaded_length = str(transfer_row[7])

        if ":" not in loaded_length:
            return file_attributes

        # Convert HH:mm:ss to seconds
        seconds = 0

        for part in loaded_length.split(":"):
            seconds = seconds * 60 + int(part, 10)

        file_attributes[slskmessages.FileAttribute.DURATION] = seconds

        return file_attributes

    def _get_stored_transfers(self, transfers_file_path, load_func, load_only_finished=False):

        transfer_rows = load_file(transfers_file_path, load_func)

        if not transfer_rows:
            return

        allowed_statuses = {TransferStatus.PAUSED, TransferStatus.FILTERED, TransferStatus.FINISHED}
        normalized_paths = {}

        for transfer_row in transfer_rows:
            num_attributes = len(transfer_row)

            if num_attributes < 3:
                continue

            # Username / virtual path / folder path
            username = transfer_row[0]

            if not isinstance(username, str):
                continue

            virtual_path = transfer_row[1]

            if not isinstance(virtual_path, str):
                continue

            folder_path = transfer_row[2]

            if not isinstance(folder_path, str):
                continue

            if folder_path:
                # Normalize and cache path
                if folder_path not in normalized_paths:
                    normalized_paths[folder_path] = normpath(folder_path)

                folder_path = normalized_paths[folder_path]

            # Status
            if num_attributes >= 4:
                status = transfer_row[3]

            if status == "Aborted":
                status = TransferStatus.PAUSED

            if load_only_finished and status != TransferStatus.FINISHED:
                continue

            if status not in allowed_statuses:
                status = TransferStatus.USER_LOGGED_OFF

            # Size / offset
            size = 0
            current_byte_offset = None

            if num_attributes >= 5:
                loaded_size = transfer_row[4]

                if loaded_size and isinstance(loaded_size, (int, float)):
                    size = loaded_size // 1

            if num_attributes >= 6:
                loaded_byte_offset = transfer_row[5]

                if loaded_byte_offset and isinstance(loaded_byte_offset, (int, float)):
                    current_byte_offset = loaded_byte_offset // 1

            # File attributes
            file_attributes = self._load_file_attributes(num_attributes, transfer_row)

            yield (
                Transfer(
                    username, virtual_path, folder_path, size, file_attributes, status,
                    current_byte_offset
                )
            )

    # File Actions #

    @staticmethod
    def _close_file(transfer):

        file_handle = transfer.file_handle
        transfer.file_handle = None

        if file_handle is None:
            return

        try:
            file_handle.close()

        except Exception as error:
            log.add_transfer("Failed to close file %(filename)s: %(error)s", {
                "filename": file_handle.name.decode("utf-8", "replace"),
                "error": error
            })

    # Limits #

    def update_transfer_limits(self):
        raise NotImplementedError

    # Events #

    def _transfer_timeout(self, transfer):
        raise NotImplementedError

    # Transfer Actions #

    def _append_transfer(self, transfer):
        raise NotImplementedError

    def _abort_transfer(self, transfer, denied_message=None, status=None, update_parent=True):
        raise NotImplementedError

    def _update_transfer(self, transfer):
        raise NotImplementedError

    def _finish_transfer(self, transfer):
        raise NotImplementedError

    def _auto_clear_transfer(self, transfer):
        raise NotImplementedError

    def _clear_transfer(self, transfer):
        raise NotImplementedError

    def _enqueue_transfer(self, transfer):

        core.users.watch_user(transfer.username)

        transfer.status = TransferStatus.QUEUED

        self.queued_users[transfer.username][transfer.virtual_path] = transfer
        self.queued_transfers[transfer] = None
        self._user_queue_sizes[transfer.username] += transfer.size

    def _enqueue_limited_transfers(self, username):
        raise NotImplementedError

    def _dequeue_transfer(self, transfer):

        username = transfer.username
        virtual_path = transfer.virtual_path

        if virtual_path not in self.queued_users.get(username, {}):
            return

        self._user_queue_sizes[username] -= transfer.size
        del self.queued_transfers[transfer]
        del self.queued_users[username][virtual_path]

        if self._user_queue_sizes[username] <= 0:
            del self._user_queue_sizes[username]

        if not self.queued_users[username]:
            del self.queued_users[username]

            # No more queued transfers, resume limited transfers if present
            self._enqueue_limited_transfers(username)

        transfer.queue_position = 0

    def _activate_transfer(self, transfer, token):

        core.users.watch_user(transfer.username)

        transfer.status = TransferStatus.GETTING_STATUS
        transfer.token = token
        transfer.speed = 0
        transfer.queue_position = 0

        # When our port is closed, certain clients can take up to ~30 seconds before they
        # initiate a 'F' connection, since they only send an indirect connection request after
        # attempting to connect to our port for a certain time period.
        # Known clients: Nicotine+ 2.2.0 - 3.2.0, 2 s; Soulseek NS, ~20 s; soulseeX, ~30 s.
        # To account for potential delays while initializing the connection, add 15 seconds
        # to the timeout value.

        transfer.request_timer_id = events.schedule(
            delay=45, callback=self._transfer_timeout, callback_args=(transfer,))

        self.active_users[transfer.username][token] = transfer

    def _deactivate_transfer(self, transfer):

        username = transfer.username
        token = transfer.token

        if token is None or token not in self.active_users.get(username, {}):
            return

        del self.active_users[username][token]

        if not self.active_users[username]:
            del self.active_users[username]

        if transfer.speed:
            self.total_bandwidth = max(0, self.total_bandwidth - transfer.speed)

        if transfer.request_timer_id is not None:
            events.cancel_scheduled(transfer.request_timer_id)
            transfer.request_timer_id = None

        transfer.sock = None
        transfer.token = None

    def _fail_transfer(self, transfer):
        self.failed_users[transfer.username][transfer.virtual_path] = transfer

    def _unfail_transfer(self, transfer):

        username = transfer.username
        virtual_path = transfer.virtual_path

        if virtual_path not in self.failed_users.get(username, {}):
            return

        del self.failed_users[username][virtual_path]

        if not self.failed_users[username]:
            del self.failed_users[username]

    # Saving #

    def _get_transfer_rows(self):
        """Get a list of transfers to dump to file."""
        return [
            [transfer.username, transfer.virtual_path, transfer.folder_path, transfer.status, transfer.size,
             transfer.current_byte_offset, transfer.file_attributes]
            for transfer in self.transfers.values()
        ]

    def _save_transfers_callback(self, file_handle):

        # We can't use indent=0 to add line breaks, since Python's C-based json encoder doesn't
        # support this. Add them using replace() instead.
        file_handle.write(
            json.dumps(self._get_transfer_rows(), check_circular=False, ensure_ascii=False).replace('], ["', '],\n["'))

    def _save_transfers(self):
        """Save list of transfers."""

        if not self._allow_saving_transfers:
            # Don't save if transfers didn't load properly!
            return

        config.create_data_folder()
        write_file_and_backup(self.transfers_file_path, self._save_transfers_callback)


class Statistics:

    def __init__(self):

        self.session_stats = {}

        for event_name, callback in (
            ("quit", self._quit),
            ("start", self._start)
        ):
            events.connect(event_name, callback)

    def _start(self):

        # Only populate total since date on first run
        if (not config.sections["statistics"]["since_timestamp"]
                and config.sections["statistics"] == config.defaults["statistics"]):
            config.sections["statistics"]["since_timestamp"] = int(time.time())

        for stat_id in config.defaults["statistics"]:
            self.session_stats[stat_id] = 0 if stat_id != "since_timestamp" else int(time.time())

    def _quit(self):
        self.session_stats.clear()

    def append_stat_value(self, stat_id, stat_value):

        self.session_stats[stat_id] += stat_value
        config.sections["statistics"][stat_id] += stat_value

        self._update_stat(stat_id)

    def _update_stat(self, stat_id):

        session_stat_value = self.session_stats[stat_id]
        total_stat_value = config.sections["statistics"][stat_id]

        events.emit("update-stat", stat_id, session_stat_value, total_stat_value)

    def update_stats(self):
        for stat_id in self.session_stats:
            self._update_stat(stat_id)

    def reset_stats(self):

        for stat_id in config.defaults["statistics"]:
            stat_value = 0 if stat_id != "since_timestamp" else int(time.time())
            self.session_stats[stat_id] = config.sections["statistics"][stat_id] = stat_value

        self.update_stats()
