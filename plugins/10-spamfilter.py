# -*- coding: utf-8 -*-

from pynicotine.pluginsystem import BasePlugin, returncode

class Plugin(BasePlugin):
    __name__ = "Spamfilter"
    __version__ = "2009-01-28r00"
    settings = {'minlength':200,
                'maxlength':400,
                'maxdiffcharacters':10,
               }
    metasettings = [('minlength', 'The minimum length of a line before it\'s considered as ASCII spam', int),
                    ('maxdiffcharacters', 'The maximum number of different characters that is still considered ASCII spam', int),
                    ('<hr>'),
                    ('maxlength', 'The maximum length of a line before it\'s considered as spam.', int),
                   ]
    def LoadNotification(self):
        self.log('A line should be  at least %s long with a maximum of %s different characters before it\'s considered ASCII spam.' % (self.settings['minlength'], self.settings['maxdiffcharacters']))
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
