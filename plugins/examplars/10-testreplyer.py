# -*- coding: utf-8 -*-

from pynicotine.gtkgui.pluginsystem import BasePlugin

class Plugin(BasePlugin):
    __name__ = "Test Replyer"
    __version__ = "2008-10-29r00"
    def IncomingPublicChatEvent(self, room, nick, line):
        if (line.lower() == 'test'):
            self.parent.saypublic(room, 'Test failed.')
