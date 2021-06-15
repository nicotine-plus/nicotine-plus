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
