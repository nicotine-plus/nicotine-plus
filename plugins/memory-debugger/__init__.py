# -*- coding: utf-8 -*-

import gc

from pynicotine.pluginsystem import BasePlugin, returncode

def enable(plugins):
    global PLUGIN
    PLUGIN = Plugin(plugins)

def disable(plugins):
    global PLUGIN
    PLUGIN = None

class Plugin(BasePlugin):
    __name__ = "Memory Debugger"
    #settings = {'maxpubliclines':4,
    #            'maxprivatelines':8,
    #           }
    #metasettings = {'maxpubliclines': {"description": 'The maximum number of lines that will pasted in public', 'type':'int'},
    #                'maxprivatelines': {"description": 'The maximum number of lines that will be pasted in private', 'type':'int'},
    #               }
    def LoadNotification(self):
        self.log("""Tweaking garbage collection. Is it currently turned on? %s
Current thresholds: %s
Current counts: %s
Enabling GB debug output (check stderr)""" % (str(gc.isenabled()), repr(gc.get_threshold()), repr(gc.get_count())))
        self.log("Enabling GB debug output (check stderr)")
        gc.set_debug(gc.DEBUG_LEAK)
        self.log("All done. See terminal for GB debug output.")
