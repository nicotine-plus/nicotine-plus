# -*- coding: utf-8 -*-

from pynicotine.gtkgui.pluginsystem import BasePlugin, returncode

class Plugin(BasePlugin):
    __name__ = "Spamfilter"
    __version__ = "2008-09-02r00"
    def IncomingPrivateChatEvent(self, nick, line):
        if line.lower().find('Buy Viagra Now') > -1:
            self.log("Blocked spam from %s: %s" % (nick, line))
            return returncode['zap']
