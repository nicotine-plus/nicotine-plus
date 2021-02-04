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

import time

from pynicotine.utils import write_log


class Logger(object):

    def __init__(self):

        self.listeners = set()
        self.log_to_file = False
        self.folder = ""
        self.file_name = "debug_" + str(int(time.time()))
        self.timestamp_format = "%Y-%m-%d %H:%M:%S"
        self.log_levels = (0, 1)

    def set_msg_prefix(self, level, msg):

        if level == 1:
            prefix = "Warn"
        elif level == 2:
            prefix = "Search"
        elif level == 3:
            prefix = "Conn"
        elif level == 4:
            prefix = "Msg"
        elif level == 5:
            prefix = "Transfer"
        elif level == 6:
            prefix = "Stat"
        else:
            prefix = ""

        if prefix:
            msg = "[%s] %s" % (prefix, msg)

        return msg

    def add(self, msg, msg_args=None, level=0):
        """Add a message. The list of logging levels is as follows:
        None - Deprecated (calls that haven't been updated yet)
        0    - Normal messages and (Human-Readable) Errors
        1    - Warnings & Tracebacks
        2    - Search Results
        3    - Peer Connections
        4    - Message Contents
        5    - Transfers
        6    - Statistics
        """

        if level not in self.log_levels:
            return

        msg = self.set_msg_prefix(level, msg)

        if msg_args:
            msg = msg % msg_args

        if self.log_to_file:
            write_log(self.folder, self.file_name, msg, self.timestamp_format)

        for callback in self.listeners:
            try:
                callback(self.timestamp_format, level, msg)
            except Exception as e:
                print("Callback on %s failed: %s %s\n%s" % (callback, level, msg, e))

    def add_warning(self, msg, msg_args=None):
        self.add(msg, msg_args=msg_args, level=1)

    def add_search(self, msg, msg_args=None):
        self.add(msg, msg_args=msg_args, level=2)

    def add_conn(self, msg, msg_args=None):
        self.add(msg, msg_args=msg_args, level=3)

    def add_msg_contents(self, msg, msg_args=None):
        self.add(msg, msg_args=msg_args, level=4)

    def add_transfer(self, msg, msg_args=None):
        self.add(msg, msg_args=msg_args, level=5)

    def add_debug(self, msg, msg_args=None):
        self.add(msg, msg_args=msg_args, level=6)

    def add_listener(self, callback):
        self.listeners.add(callback)

    def remove_listener(self, callback):
        try:
            self.listeners.remove(callback)
        except KeyError:
            self.add("Failed to remove listener %s, does not exist." % (callback,), 1)

    def set_log_to_file(self, write):
        self.log_to_file = write

    def set_folder(self, folder):
        self.folder = folder

    def set_timestamp_format(self, timestamp_format):
        self.timestamp_format = timestamp_format

    def set_log_levels(self, levels):
        self.log_levels = levels


class Console(object):

    def __init__(self, logger):
        self.log_levels = (1,)
        logger.add_listener(self.console_logger)

    def console_logger(self, timestamp_format, level, msg):
        if level in self.log_levels:
            print("[" + time.strftime(timestamp_format) + "] " + msg)

    def set_log_levels(self, levels):
        self.log_levels = levels


try:
    log
except NameError:
    log = Logger()
    console = Console(log)
