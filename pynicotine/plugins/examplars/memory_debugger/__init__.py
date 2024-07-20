# COPYRIGHT (C) 2020-2023 Nicotine+ Contributors
# COPYRIGHT (C) 2009 quinox <quinox@users.sf.net>
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

    def __init__(self, *args, **kwargs):

        import tracemalloc

        super().__init__(*args, **kwargs)

        self.log(
            "Tweaking garbage collection. Is it currently turned on? %s\n"
            "Current thresholds: %s\n"
            "Current counts: %s\n"
            "Enabling GB debug output (check stderr)\n"
            "Enabling tracemalloc",
            (str(gc.isenabled()), repr(gc.get_threshold()), repr(gc.get_count())))    # pylint: disable=no-member

        gc.set_debug(gc.DEBUG_STATS | gc.DEBUG_COLLECTABLE | gc.DEBUG_UNCOLLECTABLE)  # pylint: disable=no-member
        tracemalloc.start()                                                           # pylint: disable=no-member

        for i in range(3):
            self.log("Forcing collection of generation %s...", i)
            self.log("Collected %s objects", gc.collect(i))

        unclaimed = [f"A total of {len(gc.garbage)} objects that could not be freed:"]

        for i in gc.garbage:
            unclaimed.append(f"{type(i)}: {str(i)} ({repr(i)})")

        self.log("\n".join(unclaimed))
        self.log("Done.")

    def disable(self):

        import tracemalloc

        gc.set_debug(0)  # pylint: disable=no-member
        snapshot = tracemalloc.take_snapshot()

        self.log("[ Top 50 memory allocations ]\n")

        for i in range(50):
            memory_stat = snapshot.statistics("lineno")[i]
            self.log(memory_stat)

            tb_stat = snapshot.statistics("traceback")[i]
            self.log("%s memory blocks: %.1f KiB", (tb_stat.count, tb_stat.size / 1024))
            for line in tb_stat.traceback.format():
                self.log(line)

            self.log("")

        tracemalloc.stop()  # pylint: disable=no-member
