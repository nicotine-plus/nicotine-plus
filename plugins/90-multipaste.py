# -*- coding: utf-8 -*-

from pynicotine.pluginsystem import BasePlugin, returncode

class Plugin(BasePlugin):
    __name__ = "Multi Paste"
    __version__ = "2008-07-03r00"
    __desc__ = """This plugin intercepts messages you send with newlines in them, and splits them up in separate messages. This is useful on the official Soulseek servers since they block messages with newlines."""
    settings = {'maxpubliclines':4,
                'maxprivatelines':8,
               }
    metasettings = [('maxpubliclines', 'The maximum number of lines that will pasted in public', {'type':'int'}),
                    ('maxprivatelines', 'The maximum number of lines that will be pasted in private', {'type':'int'}),
                   ]
    def OutgoingPrivateChatEvent(self, nick, line):
        lines = [x for x in line.split('\n') if x]
        if len(lines) > 1:
            if len(lines) > self.settings['maxprivatelines']:
                self.log("Posting " + str(self.settings['maxprivatelines']) + " of " + str(len(lines)) + " lines.")
            else:
                self.log("Splitting lines.")
            for l in lines[:self.settings['maxprivatelines']]:
                self.sayprivate(nick, l)
            return returncode['zap']
    def OutgoingPublicChatEvent(self, room, line):
        lines = [x for x in line.split('\n') if x]
        if len(lines) > 1:
            if len(lines) > self.settings['maxpubliclines']:
                self.log("Posting " + str(self.settings['maxpubliclines']) + " of " + str(len(lines)) + " lines.")
            else:
                self.log("Splitting lines.")
            for l in lines[:self.settings['maxpubliclines']]:
                self.saypublic(room, l)
            return returncode['zap']
