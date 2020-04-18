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
from collections import deque
from sys import stdout


class logger(object):
    """Coordinates log messages. Has a message history for listeners that are
    not yet present right at startup."""

    def __init__(self, maxlogitems=100):
        # self.pop is used to support older versions of python
        self.listeners = set()
        try:
            self.history = deque([], maxlogitems)
            self.pop = -1  # -1 means 'let python do the popping'
        except TypeError:
            self.history = deque([])
            self.pop = maxlogitems + 1  # value is how many items to go before we start popping. Python < 2.6 support

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
        self.history.append((timestamp, level, msg))
        if self.pop > 0:
            self.pop -= 1
        if self.pop == 0:
            self.history.popleft()
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
