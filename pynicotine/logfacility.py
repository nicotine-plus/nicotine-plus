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
from collections import deque

class logger(object):
    def __init__(self, maxlogitems=1):
        # self.pop is used to support older verions of python
        self.listeners = set()
        try:
            self.history = deque([], maxlogitems)
            self.pop = -1 # -1 means 'let python do the popping'
        except TypeError:
            self.history = deque([])
            self.pop = maxlogitems+1 # 100 more items before we start popping. Python < 2.6 support
        self.add("Initializing logging facility")
    def addwarning(self, msg):
        self.add(msg, 1)
    def add(self, msg, level=0):
        ''' Logging levels
        None - Deprecated (calls that haven't been updated yet)
        0    - Normal messages and (Human-Readable) Errors
        1    - Warnings & Tracebacks
        2    - Search Results
        3    - Peer Connections
        4    - Message Contents
        5    - Transfers
        6    - Connection, Bandwidth and Usage Statistics
        '''
        timestamp = time.localtime()
        self.history.append((timestamp, level, msg))
        if self.pop > 0:
            self.pop -= 1
        if self.pop == 0:
            self.history.popleft()
        for callback in self.listeners:
            #try:
                callback(timestamp, level, msg)
            #except:
            #    print "Callback on %s failed" % (callback,)
            #    pass
    def addlistener(self, callback):
        self.add("Adding listener %s" % (callback,))
        self.listeners.add(callback)
    def removelistener(self, callback):
        try:
            self.listeners.remove(callback)
        except KeyError:
            self.add("Failed to remove listener %s, does not exist." % (callback,), 1)
def consolelogger(timestamp, level, msg):
    if level in (None,):
        print "-- %s %s" % (time.asctime(timestamp), msg)
    elif level in (1,):
        print "%s %s" % (time.asctime(timestamp), msg)
    else:
        pass
try:
    log
except NameError:
    log = logger()
log.addlistener(consolelogger) # by default let's display important stuff in the console
