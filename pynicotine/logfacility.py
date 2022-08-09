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
import threading
import time

from pynicotine import slskmessages
from pynicotine.config import config


class LogFile:

    def __init__(self, path, handle):
        self.path = path
        self.handle = handle
        self.last_active = time.time()


class Logger:

    PREFIXES = {
        "download": "Download",
        "upload": "Upload",
        "search": "Search",
        "chat": "Chat",
        "connection": "Conn",
        "message": "Msg",
        "transfer": "Transfer",
        "miscellaneous": "Misc"
    }

    EXCLUDED_MSGS = {
        slskmessages.ChangePassword,
        slskmessages.DistribEmbeddedMessage,
        slskmessages.DistribSearch,
        slskmessages.EmbeddedMessage,
        slskmessages.SetConnectionStats,
        slskmessages.SharedFileList,
        slskmessages.UnknownPeerMessage
    }

    def __init__(self):

        self.listeners = set()
        self.log_levels = None
        self.file_name = "debug_" + str(int(time.time())) + ".log"
        self.log_files = {}

        self.add_listener(self.log_console)
        self.start_log_file_timer()

    def get_log_file(self, folder_path, base_name):

        file_path = os.path.join(folder_path, base_name)
        log_file = self.log_files.get(file_path)

        if log_file is not None:
            return log_file

        from pynicotine.utils import encode_path

        folder_path_encoded = encode_path(folder_path)
        file_path_encoded = encode_path(file_path)

        if not os.path.exists(folder_path_encoded):
            os.makedirs(folder_path_encoded)

        log_file = self.log_files[file_path] = LogFile(
            path=file_path, handle=open(encode_path(file_path), 'ab'))  # pylint: disable=consider-using-with

        # Disable file access for outsiders
        os.chmod(file_path_encoded, 0o600)

        return log_file

    def write_log_file(self, folder_path, base_name, text, timestamp=None):

        try:
            log_file = self.get_log_file(folder_path, base_name)
            timestamp_format = config.sections["logging"]["log_timestamp"]
            text = "%s %s\n" % (time.strftime(timestamp_format, time.localtime(timestamp)), text)

            log_file.handle.write(text.encode('utf-8', 'replace'))
            log_file.last_active = time.time()

        except Exception as error:
            self.add(_("Couldn't write to log file \"%(filename)s\": %(error)s"), {
                "filename": os.path.join(folder_path, base_name),
                "error": error
            })

    def close_log_file(self, log_file):

        try:
            log_file.handle.close()

        except IOError as error:
            self.add_debug("Failed to close log file \"%(filename)s\": %(error)s", {
                "filename": log_file.path,
                "error": error
            })

        del self.log_files[log_file.path]

    def close_log_files(self):
        for log_file in self.log_files.copy().values():
            self.close_log_file(log_file)

    def _close_inactive_log_files(self):

        current_time = time.time()

        for log_file in self.log_files.copy().values():
            if (current_time - log_file.last_active) >= 10:
                self.close_log_file(log_file)

        # Repeat timer
        self.start_log_file_timer()

    def start_log_file_timer(self):

        thread = threading.Timer(interval=10, function=self._close_inactive_log_files)
        thread.name = "LogFileTimer"
        thread.daemon = True
        thread.start()

    def add_listener(self, callback):
        self.listeners.add(callback)

    def remove_listener(self, callback):
        self.listeners.discard(callback)

    def set_msg_prefix(self, level, msg):

        prefix = self.PREFIXES.get(level)

        if prefix:
            msg = "[%s] %s" % (prefix, msg)

        return msg

    def add(self, msg, msg_args=None, level=None):

        levels = self.log_levels if self.log_levels else config.sections["logging"].get("debugmodes", [])

        # Important messages are always visible
        if level and level not in levels and not level.startswith("important"):
            return

        if level == "message":
            # Compile message contents
            msg_class = msg.__class__

            if msg_class in self.EXCLUDED_MSGS:
                return

            msg = "%s %s" % (msg_class, self.contents(msg))

        msg = self.set_msg_prefix(level, msg)

        if msg_args:
            msg = msg % msg_args

        if config.sections["logging"].get("debug_file_output", False):
            self.write_log_file(
                folder_path=config.sections["logging"]["debuglogsdir"], base_name=self.file_name, text=msg)

        for callback in self.listeners:
            try:
                timestamp_format = config.sections["logging"].get("log_timestamp", "%Y-%m-%d %H:%M:%S")
                callback(timestamp_format, msg, level)
            except Exception as error:
                try:
                    print("Callback on %s failed: %s %s\n%s" % (callback, level, msg, error))
                except OSError:
                    # stdout is gone
                    pass

    def add_download(self, msg, msg_args=None):
        self.log_transfer(msg, msg_args)
        self.add(msg, msg_args=msg_args, level="download")

    def add_upload(self, msg, msg_args=None):
        self.log_transfer(msg, msg_args)
        self.add(msg, msg_args=msg_args, level="upload")

    def add_search(self, msg, msg_args=None):
        self.add(msg, msg_args=msg_args, level="search")

    def add_chat(self, msg, msg_args=None):
        self.add(msg, msg_args=msg_args, level="chat")

    def add_conn(self, msg, msg_args=None):
        self.add(msg, msg_args=msg_args, level="connection")

    def add_msg_contents(self, msg):
        self.add(msg, msg_args=None, level="message")

    def add_transfer(self, msg, msg_args=None):
        self.add(msg, msg_args=msg_args, level="transfer")

    def add_debug(self, msg, msg_args=None):
        self.add(msg, msg_args=msg_args, level="miscellaneous")

    def add_important_error(self, msg, msg_args=None):
        self.add(msg, msg_args=msg_args, level="important_error")

    def add_important_info(self, msg, msg_args=None):
        self.add(msg, msg_args=msg_args, level="important_info")

    @staticmethod
    def contents(obj):
        """ Returns variables for object, for debug output """
        try:
            return {s: getattr(obj, s) for s in obj.__slots__ if hasattr(obj, s)}
        except AttributeError:
            return vars(obj)

    @staticmethod
    def log_console(timestamp_format, msg, _level):
        try:
            print("[" + time.strftime(timestamp_format) + "] " + msg)
        except OSError:
            # stdout is gone
            pass

    def log_transfer(self, msg, msg_args=None):

        if not config.sections["logging"]["transfers"]:
            return

        if msg_args:
            msg = msg % msg_args

        self.write_log_file(
            folder_path=config.sections["logging"]["transferslogsdir"], base_name="transfers.log", text=msg)


log = Logger()
