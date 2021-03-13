from pynicotine.pluginsystem import BasePlugin


def enable(plugins):
    global PLUGIN
    PLUGIN = Plugin(plugins)


def disable(plugins):
    global PLUGIN
    PLUGIN = None


class Plugin(BasePlugin):
    __name__ = "Test Replier"

    def IncomingPublicChatEvent(self, room, nick, line):  # noqa
        if line.lower() == 'test':
            self.saypublic(room, 'Test failed.')
