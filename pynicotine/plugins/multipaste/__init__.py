from pynicotine.pluginsystem import BasePlugin
from pynicotine.pluginsystem import returncode


class Plugin(BasePlugin):
    __name__ = "Multi Paste"
    settings = {
        'maxpubliclines': 4,
        'maxprivatelines': 8,
    }
    metasettings = {
        'maxpubliclines': {"description": 'The maximum number of lines that will pasted in public', 'type': 'int'},
        'maxprivatelines': {"description": 'The maximum number of lines that will be pasted in private', 'type': 'int'},
    }

    def OutgoingPrivateChatEvent(self, user, line):  # noqa
        lines = [x for x in line.splitlines() if x]

        if len(lines) > 1:
            if len(lines) > self.settings['maxprivatelines']:
                self.log("Posting " + str(self.settings['maxprivatelines']) + " of " + str(len(lines)) + " lines.")
            else:
                self.log("Splitting lines.")
            for split_line in lines[:self.settings['maxprivatelines']]:
                self.sayprivate(user, split_line)

            return returncode['zap']

        return None

    def OutgoingPublicChatEvent(self, room, line):  # noqa
        lines = [x for x in line.splitlines() if x]

        if len(lines) > 1:
            if len(lines) > self.settings['maxpubliclines']:
                self.log("Posting " + str(self.settings['maxpubliclines']) + " of " + str(len(lines)) + " lines.")
            else:
                self.log("Splitting lines.")
            for split_line in lines[:self.settings['maxpubliclines']]:
                self.saypublic(room, split_line)

            return returncode['zap']

        return None
