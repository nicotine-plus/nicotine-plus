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

import os
import sys
import time

from pynicotine import slskmessages
from pynicotine.config import config
from pynicotine.events import events
from pynicotine.utils import clean_file
from pynicotine.utils import encode_path
from pynicotine.utils import open_file_path


class LogFile:

    def __init__(self, path, handle):
        self.path = path
        self.handle = handle
        self.last_active = time.time()


class LogLevel:
    DEFAULT = "default"
    DOWNLOAD = "download"
    UPLOAD = "upload"
    SEARCH = "search"
    CHAT = "chat"
    CONNECTION = "connection"
    MESSAGE = "message"
    TRANSFER = "transfer"
    MISCELLANEOUS = "miscellaneous"


class Logger:

    PREFIXES = {
        LogLevel.DOWNLOAD: "Download",
        LogLevel.UPLOAD: "Upload",
        LogLevel.SEARCH: "Search",
        LogLevel.CHAT: "Chat",
        LogLevel.CONNECTION: "Conn",
        LogLevel.MESSAGE: "Msg",
        LogLevel.TRANSFER: "Transfer",
        LogLevel.MISCELLANEOUS: "Misc"
    }

    EXCLUDED_MSGS = {
        slskmessages.ChangePassword,
        slskmessages.DistribEmbeddedMessage,
        slskmessages.DistribSearch,
        slskmessages.EmbeddedMessage,
        slskmessages.SharedFileListResponse,
        slskmessages.UnknownPeerMessage
    }

    def __init__(self):

        current_date_time = time.strftime("%Y-%m-%d_%H-%M-%S")
        self.debug_file_name = f"debug_{current_date_time}.log"
        self.transfers_file_name = f"transfers_{current_date_time}.log"

        self._log_levels = {LogLevel.DEFAULT}
        self._log_files = {}

        events.schedule(delay=10, callback=self._close_inactive_log_files, repeat=True)

    """ Log Levels """

    def init_log_levels(self):

        self._log_levels = {LogLevel.DEFAULT}

        for level in config.sections["logging"]["debugmodes"]:
            self._log_levels.add(level)

    def add_log_level(self, log_level, is_permanent=True):

        self._log_levels.add(log_level)

        if not is_permanent:
            return

        log_levels = config.sections["logging"]["debugmodes"]

        if log_level not in log_levels:
            log_levels.append(log_level)

    def remove_log_level(self, log_level, is_permanent=True):

        self._log_levels.discard(log_level)

        if not is_permanent:
            return

        log_levels = config.sections["logging"]["debugmodes"]

        if log_level in log_levels:
            log_levels.remove(log_level)

    """ Log Files """

    def _get_log_file(self, folder_path, base_name):

        file_path = os.path.join(folder_path, base_name)
        log_file = self._log_files.get(file_path)

        if log_file is not None:
            return log_file

        folder_path_encoded = encode_path(folder_path)
        file_path_encoded = encode_path(file_path)

        if not os.path.exists(folder_path_encoded):
            os.makedirs(folder_path_encoded)

        log_file = self._log_files[file_path] = LogFile(
            path=file_path, handle=open(encode_path(file_path), "ab"))  # pylint: disable=consider-using-with

        # Disable file access for outsiders
        os.chmod(file_path_encoded, 0o600)

        return log_file

    def write_log_file(self, folder_path, base_name, text, timestamp=None):

        log_file = self._get_log_file(folder_path, base_name)
        timestamp_format = config.sections["logging"]["log_timestamp"]
        timestamp = time.strftime(timestamp_format, time.localtime(timestamp))
        text = f"{timestamp} {text}\n"

        try:
            log_file.handle.write(text.encode("utf-8", "replace"))
            log_file.last_active = time.time()

        except Exception as error:
            # Avoid infinite recursion
            should_log_file = (folder_path != config.sections["logging"]["debuglogsdir"])

            self.add(_('Couldn\'t write to log file "%(filename)s": %(error)s'), {
                "filename": os.path.join(folder_path, base_name),
                "error": error
            }, should_log_file=should_log_file)

    def close_log_file(self, log_file):

        try:
            log_file.handle.close()

        except OSError as error:
            self.add_debug('Failed to close log file "%(filename)s": %(error)s', {
                "filename": log_file.path,
                "error": error
            })

        del self._log_files[log_file.path]

    def close_log_files(self):
        for log_file in self._log_files.copy().values():
            self.close_log_file(log_file)

    def _close_inactive_log_files(self):

        current_time = time.time()

        for log_file in self._log_files.copy().values():
            if (current_time - log_file.last_active) >= 10:
                self.close_log_file(log_file)

    def open_log(self, folder, filename):
        self._handle_log(folder, filename, self.open_log_callback)

    def delete_log(self, folder, filename):
        self._handle_log(folder, filename, self.delete_log_callback)

    def _handle_log(self, folder, filename, callback):

        folder_encoded = encode_path(folder)
        path = os.path.join(folder, f"{clean_file(filename)}.log")

        try:
            if not os.path.isdir(folder_encoded):
                os.makedirs(folder_encoded)

            callback(path)

        except Exception as error:
            log.add(_("Cannot access log file %(path)s: %(error)s"), {"path": path, "error": error})

    def open_log_callback(self, path):
        open_file_path(path, create_file=True)

    def delete_log_callback(self, path):
        os.remove(encode_path(path))

    def log_transfer(self, msg, msg_args=None):

        if not config.sections["logging"]["transfers"]:
            return

        if msg_args:
            msg = msg % msg_args

        self.write_log_file(
            folder_path=config.sections["logging"]["transferslogsdir"], base_name=self.transfers_file_name, text=msg)

    """ Log Messages """

    def _format_log_message(self, level, msg, msg_args):

        prefix = self.PREFIXES.get(level)

        if msg_args:
            msg = msg % msg_args

        if prefix:
            msg = f"[{prefix}] {msg}"

        return msg

    def add(self, msg, msg_args=None, title=None, level=LogLevel.DEFAULT, should_log_file=True):

        if level not in self._log_levels:
            return

        if level == LogLevel.MESSAGE:
            # Compile message contents
            if msg.__class__ in self.EXCLUDED_MSGS:
                return

            msg_direction = "OUT" if msg_args else "IN"
            msg = f"{msg_direction}: {msg}"
            msg_args = None

        msg = self._format_log_message(level, msg, msg_args)

        if should_log_file and config.sections["logging"].get("debug_file_output", False):
            self.write_log_file(
                folder_path=config.sections["logging"]["debuglogsdir"], base_name=self.debug_file_name, text=msg)

        try:
            timestamp_format = config.sections["logging"].get("log_timestamp", "%Y-%m-%d %H:%M:%S")
            events.emit("log-message", timestamp_format, msg, title, level)

        except Exception as error:
            try:
                print(f"Log callback failed: {level} {msg}\n{error}", flush=True)

            except OSError:
                # stdout is gone, prevent future errors
                sys.stdout = open(os.devnull, "w", encoding="utf-8")  # pylint: disable=consider-using-with

    def add_download(self, msg, msg_args=None):
        self.log_transfer(msg, msg_args)
        self.add(msg, msg_args=msg_args, level=LogLevel.DOWNLOAD)

    def add_upload(self, msg, msg_args=None):
        self.log_transfer(msg, msg_args)
        self.add(msg, msg_args=msg_args, level=LogLevel.UPLOAD)

    def add_search(self, msg, msg_args=None):
        self.add(msg, msg_args=msg_args, level=LogLevel.SEARCH)

    def add_chat(self, msg, msg_args=None):
        self.add(msg, msg_args=msg_args, level=LogLevel.CHAT)

    def add_conn(self, msg, msg_args=None):
        self.add(msg, msg_args=msg_args, level=LogLevel.CONNECTION)

    def add_msg_contents(self, msg, is_outgoing=False):
        self.add(msg, msg_args=is_outgoing, level=LogLevel.MESSAGE)

    def add_transfer(self, msg, msg_args=None):
        self.add(msg, msg_args=msg_args, level=LogLevel.TRANSFER)

    def add_debug(self, msg, msg_args=None):
        self.add(msg, msg_args=msg_args, level=LogLevel.MISCELLANEOUS)


log = Logger()
