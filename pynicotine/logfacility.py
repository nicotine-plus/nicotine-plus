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

import textwrap
import time

from sys import stdout

from pynicotine.utils import write_log


class logger(object):
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

        timestamp = time.localtime()

        if self.log_to_file:
            write_log(self.folder, self.file_name, msg, self.timestamp_format)

        for callback in self.listeners:
            try:
                callback(timestamp, level, msg)
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


useconsole = True
try:
    CONSOLEENCODING = stdout.encoding
except AttributeError:
    print("stdout does not have an encoding attribute - disabling console logging.")
    useconsole = False

if useconsole:
    if not CONSOLEENCODING or CONSOLEENCODING.lower() == 'ascii':
        # ASCII is quite improbable, lets just hope the user hasnt set up
        # everything properly and its really UTF8
        CONSOLEENCODING = 'UTF8'
    CONSOLEWIDTH = 80
    try:
        # Fixed, you better not resize your window!
        import sys
        import fcntl
        import termios
        import struct
        data = fcntl.ioctl(sys.stdout.fileno(), termios.TIOCGWINSZ, '1234')
        CONSOLEWIDTH = struct.unpack('hh', data)[1]
    except Exception:
        pass

    TIMEFORMAT = "%a %H:%M "

    wrapper = textwrap.TextWrapper()
    wrapper.width = CONSOLEWIDTH
    wrapper.subsequent_indent = " " * len(time.strftime(TIMEFORMAT))
    wrapper.expand_tabs = False
    wrapper.replace_whitespace = True


def consolelogger(timestamp, level, msg):
    if level in (1,):
        wrapper.initial_indent = time.strftime(TIMEFORMAT, timestamp)
        for i in wrapper.wrap(msg):
            print(i)
    else:
        pass


try:
    log
except NameError:
    log = logger()
    if useconsole:
        log.addlistener(consolelogger)  # by default let's display important stuff in the console
