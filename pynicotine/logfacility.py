# COPYRIGHT (C) 2020 Nicotine+ Team
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
    """Coordinates log messages. Has a message history for listeners that are
    not yet present right at startup."""

    def __init__(self):

        self.listeners = set()
        self.log_to_file = False
        self.folder = ""
        self.file_name = "debug_" + str(int(time.time()))
        self.timestamp_format = "%Y-%m-%d %H:%M:%S"

    def addwarning(self, msg):
        """Add a message with the level corresponding to warnings."""
        self.add(msg, 1)

    def adddebug(self, msg):
        """Add a message with the level corresponding to debug info."""
        self.add(msg, 6)

    def add(self, msg, level=0):
        """Add a message. The list of logging levels is as follows:
        None - Deprecated (calls that haven't been updated yet)
        0    - Normal messages and (Human-Readable) Errors
        1    - Warnings & Tracebacks
        2    - Search Results
        3    - Peer Connections
        4    - Message Contents
        5    - Transfers
        6    - Connection, Bandwidth and Usage Statistics
        """

        if self.log_to_file:
            write_log(self.folder, self.file_name, msg, self.timestamp_format)

        for callback in self.listeners:
            try:
                callback(self.timestamp_format, level, msg)
            except Exception as e:
                print("Callback on %s failed: %s %s\n%s" % (callback, level, msg, e))
                pass

    def addlistener(self, callback):
        self.listeners.add(callback)

    def removelistener(self, callback):
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


class Console(object):

    def __init__(self, logger):
        self.levels = (1,)
        logger.addlistener(self.consolelogger)

    def consolelogger(self, timestamp_format, level, msg):
        if level in self.levels:
            print("[" + time.strftime(timestamp_format) + "] " + msg)

    def set_levels(self, levels):
        self.levels = levels


try:
    log
except NameError:
    log = Logger()
    console = Console(log)
