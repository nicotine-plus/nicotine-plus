# SPDX-FileCopyrightText: 2020-2025 Nicotine+ Contributors
# SPDX-FileCopyrightText: 2009 quinox <quinox@users.sf.net>
# SPDX-License-Identifier: GPL-3.0-or-later

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
            self.log("Forcing collection of generation %s…", i)
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
