# -*- coding: utf-8 -*-

from pynicotine.gtkgui.pluginsystem import BasePlugin, returncode
from pynicotine.gtkgui.chatrooms import ChatRoom
from pynicotine import slskmessages

class Plugin(BasePlugin):
    __name__ = "Merged Chat"
    __version__ = "2009-01-18r00"
    __mergeroom__ = "MergeView " # last space is important!
    def init(self):
        self.roomsctrl = self.frame.chatrooms.roomsctrl
        self.active = True
    def _createIfNeeded(self):
        if self.__mergeroom__ not in self.roomsctrl.joinedrooms:
            self.room = ChatRoom(self.roomsctrl, self.__mergeroom__, {}, meta = True)
            self.roomsctrl.joinedrooms[self.__mergeroom__] = self.room
            angle = 0
            try:
                angle = int(self.frame.np.config.sections["ui"]["labelrooms"])
            except Exception, e:
                print e
                pass
            self.frame.ChatNotebook.append_page(self.room.Main, self.__mergeroom__, self.room.OnLeave, angle)
            self.room.CountUsers()
    def createMergeview(self, room, args):
        if not self.active:
            self.active = True
            self.log("Creating view")
            self._createIfNeeded()
        else:
            self.log("Already active.")
        return returncode['zap']
    def ServerDisconnectNotification(self):
        self.log('Were disconnected, merge needs to be destroyed')
    def IncomingPublicChatEvent(self, room, user, text):
        if not self.active:
            return
        if room != self.__mergeroom__:
            self._createIfNeeded()
            if not self.fakepublic(self.__mergeroom__, self.join(room, user), text):
                self.log('Failed to fake message!')
    def OutgoingPublicChatEvent(self, room, text):
        if not self.active:
            return
        self._createIfNeeded()
        if room == self.__mergeroom__:
            (realroom, sep, realtext) = text.partition(': ')
            if room in self.roomsctrl.joinedrooms:
                self.saypublic(realroom, realtext)
                self.fakepublic(self.__mergeroom__, self.join(realroom, self.parent.myUsername), realtext)
            else:
                self.log("You are not in room '%s'!" % (realroom,))
            return returncode['zap']
    def OutgoingPublicChatNotification(self, room, text):
        if not self.active:
            return
        if room != self.__mergeroom__:
            self.fakepublic(self.__mergeroom__, self.join(room, self.parent.myUsername), text)
    def LeaveChatroomNotification(self, room):
        if room == self.__mergeroom__:
            self.active = False
            self.roomsctrl.LeaveRoom(slskmessages.LeaveRoom(room)) # Faking protocol msg
    def join(self, room, user):
        return "%s | %s" % (room, user)
    __publiccommands__ = [('mergeview', createMergeview)]
