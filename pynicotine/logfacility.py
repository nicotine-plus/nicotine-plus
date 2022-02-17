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

import os
import time

from pynicotine.config import config


class Logger:

    def __init__(self):

        self.listeners = set()
        self.log_levels = None
        self.file_name = "debug_" + str(int(time.time()))

    @staticmethod
    def set_msg_prefix(level, msg):

        if level == "download":
            prefix = "Download"
        elif level == "upload":
            prefix = "Upload"
        elif level == "search":
            prefix = "Search"
        elif level == "chat":
            prefix = "Chat"
        elif level == "connection":
            prefix = "Conn"
        elif level == "message":
            prefix = "Msg"
        elif level == "transfer":
            prefix = "Transfer"
        elif level == "miscellaneous":
            prefix = "Misc"
        else:
            prefix = ""

        if prefix:
            msg = "[%s] %s" % (prefix, msg)

        return str(msg)

    def add(self, msg, msg_args=None, level=None):

        if self.log_levels:
            levels = self.log_levels
        else:
            levels = config.sections["logging"].get("debugmodes", "")

        # Important messages are always visible
        if level and not level.startswith("important") and level not in levels:
            return

        if not msg_args and level == "message":
            # Compile message contents
            msg = "%s %s" % (msg.__class__, self.contents(msg))

        msg = self.set_msg_prefix(level, msg)

        if msg_args:
            msg = msg % msg_args

        timestamp_format = config.sections["logging"].get("log_timestamp", "%Y-%m-%d %H:%M:%S")

        if config.sections["logging"].get("debug_file_output", False):
            folder = config.sections["logging"]["debuglogsdir"]

            self.write_log(folder, self.file_name, msg, timestamp_format=timestamp_format)

        for callback in self.listeners:
            try:
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

    def add_msg_contents(self, msg, msg_args=None):
        self.add(msg, msg_args=msg_args, level="message")

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

    def add_listener(self, callback):
        self.listeners.add(callback)

    def remove_listener(self, callback):
        try:
            self.listeners.remove(callback)
        except KeyError:
            self.add("Failed to remove listener %s, does not exist.", callback)

    def log_transfer(self, msg, msg_args=None):

        if not config.sections["logging"]["transfers"]:
            return

        folder = config.sections["logging"]["transferslogsdir"]
        timestamp_format = config.sections["logging"]["log_timestamp"]

        if msg_args:
            msg = msg % msg_args

        self.write_log(folder, "transfers", msg, timestamp_format=timestamp_format)

    def write_log(self, logsdir, filename, msg, timestamp=None, timestamp_format="%Y-%m-%d %H:%M:%S"):

        try:
            from pynicotine.utils import clean_file
            filename = clean_file(filename) + ".log"
            oldumask = os.umask(0o077)

            if not os.path.exists(logsdir):
                os.makedirs(logsdir)

            from pynicotine.utils import get_path
            get_path(logsdir, filename, self.write_log_callback, (oldumask, timestamp, timestamp_format, msg))

        except Exception as error:
            self.add(_("Couldn't write to log file \"%(filename)s\": %(error)s") %
                     {"filename": filename, "error": error})

    @staticmethod
    def write_log_callback(path, data):

        oldumask, timestamp, timestamp_format, msg = data

        with open(path, 'ab', 0) as logfile:
            os.umask(oldumask)

            text = "%s %s\n" % (time.strftime(timestamp_format, time.localtime(timestamp)), msg)
            logfile.write(text.encode('utf-8', 'replace'))


class Console:

    def __init__(self, logger):
        logger.add_listener(self.console_logger)

    @staticmethod
    def console_logger(timestamp_format, msg, _level):
        try:
            print("[" + time.strftime(timestamp_format) + "] " + msg)
        except OSError:
            # stdout is gone
            pass


log = Logger()
Console(log)
