# -*- coding: utf-8 -*-

from pynicotine.gtkgui.pluginsystem import BasePlugin, returncode

class Plugin(BasePlugin):
    __name__ = "Multi Paste"
    __version__ = "2008-07-03r00"
    __MAXPUBLICLINES__ = 4
    __MAXPRIVATELINES__ = 8
    def OutgoingPrivateChatEvent(self, nick, line):
        lines = [x for x in line.split('\n') if x]
        if len(lines) > 1:
            if len(lines) > self.__MAXPRIVATELINES__:
                self.log("Posting " + str(self.__MAXPRIVATELINES__) + " of " + str(len(lines)) + " lines.")
            else:
                self.log("Splitting lines.")
            for l in lines[:self.__MAXPRIVATELINES__]:
                self.parent.SayPrivate(nick, l)
            return returncode['zap']
    def OutgoingPublicChatEvent(self, room, line):
        lines = [x for x in line.split('\n') if x]
        if len(lines) > 1:
            if len(lines) > self.__MAXPUBLICLINES__:
                self.log("Posting " + str(self.__MAXPUBLICLINES__) + " of " + str(len(lines)) + " lines.")
            else:
                self.log("Splitting lines.")
            for l in lines[:self.__MAXPUBLICLINES__]:
                self.parent.saychatroom(room, l)
            return returncode['zap']
