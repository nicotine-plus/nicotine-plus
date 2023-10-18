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
import os.path
import time

from ast import literal_eval
from collections import deque

from pynicotine import slskmessages
from pynicotine.config import config
from pynicotine.events import events
from pynicotine.logfacility import log
from pynicotine.utils import encode_path
from pynicotine.utils import load_file
from pynicotine.utils import write_file_and_backup


class Transfer:
    """This class holds information about a single transfer."""

    __slots__ = ("sock", "username", "virtual_path",
                 "folder_path", "token", "size", "file_handle", "start_time", "last_update",
                 "current_byte_offset", "last_byte_offset", "speed", "time_elapsed",
                 "time_left", "modifier", "queue_position", "file_attributes",
                 "iterator", "status", "legacy_attempt", "size_changed")

    def __init__(self, username=None, virtual_path=None, folder_path=None, status=None, token=None, size=0,
                 current_byte_offset=None, file_attributes=None):
        self.username = username
        self.virtual_path = virtual_path
        self.folder_path = folder_path
        self.size = size
        self.status = status
        self.token = token
        self.current_byte_offset = current_byte_offset
        self.file_attributes = file_attributes or {}

        self.sock = None
        self.file_handle = None
        self.queue_position = 0
        self.modifier = None
        self.start_time = None
        self.last_update = None
        self.last_byte_offset = None
        self.speed = None
        self.time_elapsed = 0
        self.time_left = None
        self.iterator = None
        self.legacy_attempt = False
        self.size_changed = False


class Transfers:

    def __init__(self, transfers_file_path):

        self.transfers_file_path = transfers_file_path
        self.allow_saving_transfers = False
        self.transfers = deque()
        self.transfer_request_times = {}

        self._transfer_timeout_timer_id = None

        for event_name, callback in (
            ("quit", self._quit),
            ("server-login", self._server_login),
            ("server-disconnect", self._server_disconnect),
            ("start", self._start)
        ):
            events.connect(event_name, callback)

    def _start(self):

        self.load_transfers()
        self.allow_saving_transfers = True

        # Save list of transfers every 3 minutes
        events.schedule(delay=180, callback=self.save_transfers, repeat=True)

        self.update_transfer_limits()

    def _quit(self):

        self.save_transfers()
        self.allow_saving_transfers = False

        self.transfers.clear()

    def _server_login(self, msg):

        if not msg.success:
            return

        # Check for transfer timeouts
        self._transfer_timeout_timer_id = events.schedule(delay=1, callback=self._check_transfer_timeouts, repeat=True)

        self.update_transfer_limits()

    def _server_disconnect(self, _msg):

        for timer_id in (self._transfer_timeout_timer_id,):
            events.cancel_scheduled(timer_id)

        self.transfer_request_times.clear()

    @staticmethod
    def load_transfers_file(transfers_file):
        """Loads a file of transfers in json format."""

        transfers_file = encode_path(transfers_file)

        if not os.path.isfile(transfers_file):
            return None

        with open(transfers_file, encoding="utf-8") as handle:
            # JSON stores file attribute types as strings, convert them back to integers with object_hook
            return json.load(handle, object_hook=lambda d: {int(k): v for k, v in d.items()})

    @staticmethod
    def load_legacy_transfers_file(transfers_file):
        """Loads a download queue file in pickle format (legacy)"""

        transfers_file = encode_path(transfers_file)

        if not os.path.isfile(transfers_file):
            return None

        with open(transfers_file, "rb") as handle:
            from pynicotine.shares import RestrictedUnpickler
            return RestrictedUnpickler(handle, encoding="utf-8").load()

    def load_transfers(self):
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

    def add_stored_transfers(self, transfers_file_path, load_func, load_only_finished=False):

        transfer_rows = load_file(transfers_file_path, load_func)

        if not transfer_rows:
            return

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
                folder_path = os.path.normpath(folder_path)

            # Status
            loaded_status = None

            if num_attributes >= 4:
                loaded_status = str(transfer_row[3])

            if load_only_finished and loaded_status != "Finished":
                continue

            if loaded_status in {"Aborted", "Paused"}:
                status = "Paused"

            elif loaded_status in {"Filtered", "Finished"}:
                status = loaded_status

            else:
                status = "User logged off"

            # Size / offset
            size = 0
            current_byte_offset = None

            if num_attributes >= 5:
                loaded_size = transfer_row[4]

                if loaded_size and isinstance(loaded_size, (int, float)):
                    size = int(loaded_size)

            if num_attributes >= 6:
                loaded_byte_offset = transfer_row[5]

                if loaded_byte_offset and isinstance(loaded_byte_offset, (int, float)):
                    current_byte_offset = int(loaded_byte_offset)

            # File attributes
            file_attributes = self._load_file_attributes(num_attributes, transfer_row)

            self.transfers.appendleft(
                Transfer(
                    username=username, virtual_path=virtual_path, folder_path=folder_path, status=status, size=size,
                    current_byte_offset=current_byte_offset, file_attributes=file_attributes
                )
            )

    # File Actions #

    @staticmethod
    def close_file(transfer):

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

    def _check_transfer_timeouts(self):

        current_time = time.time()

        if self.transfer_request_times:
            for transfer, start_time in self.transfer_request_times.copy().items():
                # When our port is closed, certain clients can take up to ~30 seconds before they
                # initiate a 'F' connection, since they only send an indirect connection request after
                # attempting to connect to our port for a certain time period.
                # Known clients: Nicotine+ 2.2.0 - 3.2.0, 2 s; Soulseek NS, ~20 s; soulseeX, ~30 s.
                # To account for potential delays while initializing the connection, add 15 seconds
                # to the timeout value.

                if (current_time - start_time) >= 45:
                    self._transfer_timeout(transfer)

    # Saving #

    def get_transfer_rows(self):
        """Get a list of transfers to dump to file."""
        return [
            [transfer.username, transfer.virtual_path, transfer.folder_path, transfer.status, transfer.size,
             transfer.current_byte_offset, transfer.file_attributes]
            for transfer in reversed(self.transfers)
        ]

    def save_transfers_callback(self, file_handle):
        file_handle.write(json.dumps(self.get_transfer_rows(), check_circular=False, ensure_ascii=False))

    def save_transfers(self):
        """Save list of transfers."""

        if not self.allow_saving_transfers:
            # Don't save if transfers didn't load properly!
            return

        config.create_data_folder()
        write_file_and_backup(self.transfers_file_path, self.save_transfers_callback)


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

        for stat_id in config.defaults["statistics"]:
            self.update_ui(stat_id)

    def _quit(self):
        self.session_stats.clear()

    def append_stat_value(self, stat_id, stat_value):

        self.session_stats[stat_id] += stat_value
        config.sections["statistics"][stat_id] += stat_value
        self.update_ui(stat_id)

    def update_ui(self, stat_id):

        session_stat_value = self.session_stats[stat_id]
        total_stat_value = config.sections["statistics"][stat_id]

        events.emit("update-stat-value", stat_id, session_stat_value, total_stat_value)

    def reset_stats(self):

        for stat_id in config.defaults["statistics"]:
            stat_value = 0 if stat_id != "since_timestamp" else int(time.time())
            self.session_stats[stat_id] = config.sections["statistics"][stat_id] = stat_value

            self.update_ui(stat_id)
