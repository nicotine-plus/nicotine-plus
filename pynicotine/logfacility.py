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

        if not msg_args and level == 4:
            # Compile message contents
            msg = "%s %s" % (msg.__class__, self.contents(msg))

        msg = self.set_msg_prefix(level, msg)

        if msg_args:
            msg = msg % msg_args

        if self.log_to_file:
            self.write_log(self.folder, self.file_name, msg, self.timestamp_format)

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

    def contents(self, obj):
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
            self.add("Failed to remove listener %s, does not exist." % (callback,), 1)

    def set_log_levels(self, levels):
        self.log_levels = levels

    def update_debug_log_options(self, should_log, log_folder, timestamp_format):
        """ Gives the logger updated logging settings """

        self.log_to_file = should_log
        self.folder = log_folder
        self.timestamp_format = timestamp_format

    def write_log(self, logsdir, filename, msg, timestamp_format="%Y-%m-%d %H:%M:%S"):

        try:
            filename = filename.replace(os.sep, "-") + ".log"
            oldumask = os.umask(0o077)

            if not os.path.exists(logsdir):
                os.makedirs(logsdir)

            from pynicotine.utils import get_path
            get_path(logsdir, filename, self.write_log_callback, (oldumask, timestamp_format, msg))

        except Exception as error:
            print(_("Couldn't write to log file \"%s\": %s") % (filename, error))

    def write_log_callback(self, path, data):

        oldumask, timestamp_format, msg = data

        with open(path, 'ab', 0) as logfile:
            os.umask(oldumask)

            text = "%s %s\n" % (time.strftime(timestamp_format), msg)
            logfile.write(text.encode('utf-8', 'replace'))


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
