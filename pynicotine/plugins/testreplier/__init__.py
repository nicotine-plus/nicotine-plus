from pynicotine.pluginsystem import BasePlugin, ResponseThrottle
from random import choice


def enable(plugins):
    global PLUGIN
    PLUGIN = Plugin(plugins)


def disable(plugins):
    global PLUGIN
    PLUGIN = None


class Plugin(BasePlugin):
    __name__ = "Test Replier"
    settings = {
        'replies': ['Test failed.']
    }
    metasettings = {
        'replies': {
            'description': 'Replies:',
            'type': 'list string'}
    }

    def init(self):
        self.throttle = ResponseThrottle(self.np, self.__name__)

    def IncomingPublicChatEvent(self, room, nick, line):  # noqa
        if line.lower() == 'test':
            if self.throttle.ok_to_respond(room, nick, line, 10):
                self.throttle.responded()
                self.saypublic(room, choice(self.settings['replies']))
