from pynicotine.pluginsystem import BasePlugin
from pynicotine.pluginsystem import returncode


def enable(plugins):
    global PLUGIN
    PLUGIN = Plugin(plugins)


def disable(plugins):
    global PLUGIN
    PLUGIN = None


class Plugin(BasePlugin):
    __name__ = "Spamfilter"
    settings = {
        'minlength': 200,
        'maxlength': 400,
        'maxdiffcharacters': 10,
        'badprivatephrases': ['buy viagra now', 'mybrute.com', 'mybrute.es', '0daymusic.biz']
    }
    metasettings = {
        'minlength': {"description": 'The minimum length of a line before it\'s considered as '
                                     + 'ASCII spam',
                      'type': 'integer'},
        'maxdiffcharacters': {"description": 'The maximum number of different characters that is '
                                             + 'still considered ASCII spam',
                              'type': 'integer'},
        'maxlength': {"description": 'The maximum length of a line before it\'s considered as spam.',
                      'type': 'integer'},
        'badprivatephrases': {"description": 'Filter chat room and private messages containing the following phrases:',
                              'type': 'list string'},
    }

    def LoadNotification(self):  # noqa
        self.log('A line should be at least %s long with a maximum of %s different characters \
                 before it\'s considered ASCII spam.' %
                 (self.settings['minlength'], self.settings['maxdiffcharacters']))

    def check_phrases(self, user, line):

        for phrase in self.settings['badprivatephrases']:
            if line.lower().find(phrase) > -1:
                self.log("Blocked spam from %s: %s" % (user, line))
                return returncode['zap']

        return None

    def IncomingPublicChatEvent(self, room, user, line):  # noqa

        if len(line) >= self.settings['minlength'] and len(set(line)) < self.settings['maxdiffcharacters']:
            self.log('Filtered ASCII spam from "%s" in room "%s"' % (user, room))
            return returncode['zap']

        if len(line) > self.settings['maxlength']:
            self.log('Filtered really long line (%s characters) from "%s" in room "%s"' % (len(line), user, room))
            return returncode['zap']

        return self.check_phrases(user, line)

    def IncomingPrivateChatEvent(self, user, line):  # noqa
        return self.check_phrases(user, line)
