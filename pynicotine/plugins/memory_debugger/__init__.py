# COPYRIGHT (C) 2020-2021 Nicotine+ Team
# COPYRIGHT (C) 2009 Quinox <quinox@users.sf.net>
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

import gc

from pynicotine.pluginsystem import BasePlugin


class Plugin(BasePlugin):

    __name__ = "Memory Debugger"

    def init(self):

        self.log("""Tweaking garbage collection. Is it currently turned on? %s
Current thresholds: %s
Current counts: %s
Enabling GB debug output (check stderr)""" % (str(gc.isenabled()), repr(gc.get_threshold()), repr(gc.get_count())))

        gc.set_debug(gc.DEBUG_STATS)
        self.log("Forcing collection of generation 0...")
        gc.collect(0)
        self.log("Forcing collection of generation 1...")
        gc.collect(1)
        self.log("Forcing collection of generation 2...")
        gc.collect(2)
        unclaimed = ['A total of %s objects that could not be freed:' % (len(gc.garbage),)]
        for i in gc.garbage:
            unclaimed.append('%s: %s (%s)' % (type(i), str(i), repr(i)))
        self.log('\n'.join(unclaimed))
        self.log("Done.")

    def disable(self):
        gc.set_debug(0)
