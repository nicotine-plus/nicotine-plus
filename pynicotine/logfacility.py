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

import os
import sys
import time

from collections import deque

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
        self.last_active = time.monotonic()


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
        self.debug_file_name = f"debug_{current_date_time}"
        self.downloads_file_name = f"downloads_{current_date_time}"
        self.uploads_file_name = f"uploads_{current_date_time}"

        self.debug_folder_path = None
        self.transfer_folder_path = None
        self.room_folder_path = None
        self.private_chat_folder_path = None

        self._log_levels = {LogLevel.DEFAULT}
        self._log_files = {}

        events.connect("quit", self._close_log_files)
        events.schedule(delay=10, callback=self._close_inactive_log_files, repeat=True)

    # Log Levels #

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

    # Log Files #

    def _get_log_file(self, folder_path, basename, should_create_file=True):

        file_path = os.path.join(folder_path, clean_file(f"{basename}.log"))
        log_file = self._log_files.get(file_path)

        if log_file is not None:
            return log_file

        folder_path_encoded = encode_path(folder_path)
        file_path_encoded = encode_path(file_path)

        if not should_create_file and not os.path.isfile(file_path_encoded):
            return log_file

        if not os.path.exists(folder_path_encoded):
            os.makedirs(folder_path_encoded)

        log_file = LogFile(
            path=file_path, handle=open(file_path_encoded, "ab+"))  # pylint: disable=consider-using-with

        # Disable file access for outsiders
        os.chmod(file_path_encoded, 0o600)

        return log_file

    def write_log_file(self, folder_path, basename, text, timestamp=None):

        folder_path = os.path.normpath(folder_path)

        try:
            log_file = self._get_log_file(folder_path, basename)
            timestamp_format = config.sections["logging"]["log_timestamp"]

            if timestamp_format:
                timestamp = time.strftime(timestamp_format, time.localtime(timestamp))
                text = f"{timestamp} {text}\n"
            else:
                text += "\n"

            log_file.handle.write(text.encode("utf-8", "replace"))
            log_file.last_active = time.monotonic()

        except Exception as error:
            # Avoid infinite recursion
            should_log_file = (folder_path != self.debug_folder_path)

            self.add(_('Couldn\'t write to log file "%(filename)s": %(error)s'), {
                "filename": os.path.join(folder_path, clean_file(f"{basename}.log")),
                "error": error
            }, should_log_file=should_log_file)

    def _close_log_file(self, log_file):

        try:
            log_file.handle.close()

        except OSError as error:
            self.add_debug('Failed to close log file "%(filename)s": %(error)s', {
                "filename": log_file.path,
                "error": error
            })

        del self._log_files[log_file.path]

    def _close_log_files(self):
        for log_file in self._log_files.copy().values():
            self._close_log_file(log_file)

    def _close_inactive_log_files(self):

        current_time = time.monotonic()

        for log_file in self._log_files.copy().values():
            if (current_time - log_file.last_active) >= 10:
                self._close_log_file(log_file)

    def _normalize_folder_path(self, folder_path):
        return os.path.normpath(os.path.expandvars(folder_path))

    def update_folder_paths(self):

        self.debug_folder_path = self._normalize_folder_path(config.sections["logging"]["debuglogsdir"])
        self.transfer_folder_path = self._normalize_folder_path(config.sections["logging"]["transferslogsdir"])
        self.room_folder_path = self._normalize_folder_path(config.sections["logging"]["roomlogsdir"])
        self.private_chat_folder_path = self._normalize_folder_path(config.sections["logging"]["privatelogsdir"])

    def open_log(self, folder_path, basename):
        self._handle_log(folder_path, basename, self.open_log_callback)

    def read_log(self, folder_path, basename, num_lines):

        lines = None
        log_file = None

        try:
            log_file = self._get_log_file(folder_path, basename, should_create_file=False)

            if log_file is not None:
                # Read the number of lines specified from the beginning of the file,
                # then go back to the end of the file to append new lines
                log_file.handle.seek(0)
                lines = deque(log_file.handle, num_lines)
                log_file.handle.seek(0, os.SEEK_END)

        except Exception as error:
            log.add(_("Cannot access log file %(path)s: %(error)s"), {
                "path": os.path.join(folder_path, clean_file(f"{basename}.log")),
                "error": error
            })

            if log_file is not None:
                # In case seek() failed, close log file to prevent future write attempts
                self._close_log_file(log_file)

        return lines

    def delete_log(self, folder_path, basename):
        self._handle_log(folder_path, basename, self.delete_log_callback)

    def _handle_log(self, folder_path, basename, callback):

        folder_path_encoded = encode_path(folder_path)
        file_path = os.path.join(folder_path, clean_file(f"{basename}.log"))

        try:
            if not os.path.isdir(folder_path_encoded):
                os.makedirs(folder_path_encoded)

            callback(file_path)

        except Exception as error:
            log.add(_("Cannot access log file %(path)s: %(error)s"), {"path": file_path, "error": error})

    def open_log_callback(self, file_path):
        open_file_path(file_path, create_file=True)

    def delete_log_callback(self, file_path):
        os.remove(encode_path(file_path))

    def log_transfer(self, basename, msg, msg_args=None):

        if not config.sections["logging"]["transfers"]:
            return

        if msg_args:
            msg %= msg_args

        self.write_log_file(folder_path=self.transfer_folder_path, basename=basename, text=msg)

    # Log Messages #

    def _format_log_message(self, level, msg, msg_args):

        prefix = self.PREFIXES.get(level)

        if msg_args:
            msg %= msg_args

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
            events.invoke_main_thread(
                self.write_log_file, folder_path=self.debug_folder_path,
                basename=self.debug_file_name, text=msg)

        try:
            timestamp_format = config.sections["logging"].get("log_timestamp", "%x %X")
            events.emit("log-message", timestamp_format, msg, title, level)

        except Exception as error:
            try:
                print(f"Log callback failed: {level} {msg}\n{error}", flush=True)

            except OSError:
                # stdout is gone, prevent future errors
                sys.stdout = open(os.devnull, "w", encoding="utf-8")  # pylint: disable=consider-using-with

    def add_download(self, msg, msg_args=None):
        self.log_transfer(self.downloads_file_name, msg, msg_args)
        self.add(msg, msg_args=msg_args, level=LogLevel.DOWNLOAD)

    def add_upload(self, msg, msg_args=None):
        self.log_transfer(self.uploads_file_name, msg, msg_args)
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
