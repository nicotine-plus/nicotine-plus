from pynicotine.pluginsystem import BasePlugin
from pynicotine.pluginsystem import returncode


def enable(plugins):
    global PLUGIN
    PLUGIN = Plugin(plugins)


def disable(plugins):
    global PLUGIN
    PLUGIN = None


class Plugin(BasePlugin):
    __name__ = "Multipaste"
    settings = {
        'maxpubliclines': 4,
        'maxprivatelines': 8,
    }
    metasettings = {
        'maxpubliclines': {"description": 'The maximum number of lines that will pasted in public', 'type': 'int'},
        'maxprivatelines': {"description": 'The maximum number of lines that will be pasted in private', 'type': 'int'},
    }

    def OutgoingPrivateChatEvent(self, nick, line):  # noqa
        lines = [x for x in line.split(r'\n') if x]
        if len(lines) > 1:
            if len(lines) > self.settings['maxprivatelines']:
                self.log("Posting " + str(self.settings['maxprivatelines']) + " of " + str(len(lines)) + " lines.")
            else:
                self.log("Splitting lines.")
            for line in lines[:self.settings['maxprivatelines']]:
                self.sayprivate(nick, line)
            return returncode['zap']

    def OutgoingPublicChatEvent(self, room, line):  # noqa
        lines = [x for x in line.split(r'\n') if x]
        if len(lines) > 1:
            if len(lines) > self.settings['maxpubliclines']:
                self.log("Posting " + str(self.settings['maxpubliclines']) + " of " + str(len(lines)) + " lines.")
            else:
                self.log("Splitting lines.")
            for line in lines[:self.settings['maxpubliclines']]:
                self.saypublic(room, line)
            return returncode['zap']
