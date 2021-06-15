# pylint: disable=attribute-defined-outside-init

from random import choice
from pynicotine.pluginsystem import BasePlugin, ResponseThrottle


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

    def IncomingPublicChatEvent(self, room, user, line):  # noqa
        if line.lower() == 'test':
            if self.throttle.ok_to_respond(room, user, line, 10):
                self.throttle.responded()
                self.saypublic(room, choice(self.settings['replies']))
