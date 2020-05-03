import gc

from pynicotine.pluginsystem import BasePlugin


def enable(plugins):
    global PLUGIN
    PLUGIN = Plugin(plugins)


def disable(plugins):
    global PLUGIN
    PLUGIN = None


class Plugin(BasePlugin):
    __name__ = "Memory Debugger"
    # settings = {'maxpubliclines':4,
    #            'maxprivatelines':8,
    #           }
    # metasettings = {'maxpubliclines': {"description": 'The maximum number of lines that will pasted in public', 'type':'int'},
    #                'maxprivatelines': {"description": 'The maximum number of lines that will be pasted in private', 'type':'int'},
    #               }

    def init(self):
        self.log("""Tweaking garbage collection. Is it currently turned on? %s
Current thresholds: %s
Current counts: %s
Enabling GB debug output (check stderr)""" % (str(gc.isenabled()), repr(gc.get_threshold()), repr(gc.get_count())))
        # self.log("Enabling GB debug output (check stderr)")
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
