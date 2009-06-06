# -*- coding: utf-8 -*-

from pynicotine.pluginsystem import BasePlugin

class Plugin(BasePlugin):
    __name__ = "Test Replyer"
    __version__ = "2008-10-29r00"
    __author__ = "quinox"
    __desc__ = """Replies to messages 'test' in chatrooms with the message 'Test failed.'"""
    def IncomingPublicChatEvent(self, room, nick, line):
        if (line.lower() == 'test'):
            self.saypublic(room, 'Test failed.')
