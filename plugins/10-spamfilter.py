# -*- coding: utf-8 -*-

from pynicotine.gtkgui.pluginsystem import BasePlugin, returncode

class Plugin(BasePlugin):
    __name__ = "Spamfilter"
    __version__ = "2009-01-28r00"
    def init(self):
        self.minlength = 200
        self.maxlength = 400
        self.maxdiffcharacters = 10
    def IncomingPublicChatEvent(self, room, user, line):
        if len(line) >= self.minlength and len(set(line)) < self.maxdiffcharacters:
            self.log('Filtered ASCII spam from "%s" in room "%s"' % (user, room))
            return returncode['zap']
        if len(line) > self.maxlength:
            self.log('Filtered really long line (%s characters) from "%s" in room "%s"' % (len(line), user, room))
            return returncode['zap']
    def IncomingPrivateChatEvent(self, user, line):
        if line.lower().find('Buy Viagra Now') > -1:
            self.log("Blocked spam from %s: %s" % (user, line))
            return returncode['zap']
