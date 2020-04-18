from pynicotine.pluginsystem import BasePlugin


def enable(plugins):
    global PLUGIN
    PLUGIN = Plugin(plugins)


def disable(plugins):
    global PLUGIN
    PLUGIN = None


class Plugin(BasePlugin):
    __name__ = "Test Replyer"
    __version__ = "2008-10-29r00"
    __author__ = "quinox"
    __desc__ = """Replies to messages 'test' in chatrooms with the message 'Test failed.'"""

    def IncomingPublicChatEvent(self, room, nick, line):
        if line.lower() == 'test':
            self.saypublic(room, 'Test failed.')
