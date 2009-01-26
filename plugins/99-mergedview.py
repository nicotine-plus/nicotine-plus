# -*- coding: utf-8 -*-

from pynicotine.gtkgui.pluginsystem import BasePlugin, returncode
from pynicotine.gtkgui.chatrooms import ChatRoom
from pynicotine import slskmessages

class Plugin(BasePlugin):
    __name__ = "Merged Chat"
    __version__ = "2009-01-26r00"
    __mergeroom__ = "Joined Rooms " # last space is important!
    def init(self):
        self.roomsctrl = self.frame.chatrooms.roomsctrl
        self.active = True
        self.lastmessage = None
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
    #def ServerDisconnectNotification(self):
    #    self.log('Were disconnected, merge needs to be destroyed')
    def IncomingPublicChatNotification(self, room, user, text):
        if not self.active:
            return
        if room != self.__mergeroom__:
            self._createIfNeeded()
            self.fakepublic(self.__mergeroom__, self.joinPublic(room, user), text)
            self.lastmessage = ('Public', room)
    def IncomingPrivateChatNotification(self, user, text):
        if not self.active:
            return
        self._createIfNeeded()
        self.fakepublic(self.__mergeroom__, self.joinPrivate(user, self.parent.myUsername), text)
        self.lastmessage = ('Message', user)
    def OutgoingPublicChatEvent(self, room, text):
        if not self.active:
            return
        if room != self.__mergeroom__:
            return
        (realroom, sep, realtext) = text.partition(': ')
        if realtext:
            if realroom in self.roomsctrl.joinedrooms:
                self.saypublic(realroom, realtext)
                #self.fakepublic(self.__mergeroom__, self.joinPublic(realroom, self.parent.myUsername), realtext)
            else:
                self.log('You are not active in room "%s", not sending message' % (realroom,))
        else:
            self.log('Either prefix your message with the room name followed by a colon (:), or use /reply to send a message to the person/room that last spoke.')
        return returncode['zap']
    #def OutgoingPublicChatNotification(self, room, text):
    #    if not self.active:
    #        return
    #    if room != self.__mergeroom__:
    #        self._createIfNeeded()
    #        self.fakepublic(self.__mergeroom__, self.joinPublic(room, self.parent.myUsername), text)
    def OutgoingPrivateChatNotification(self, user, text):
        self._createIfNeeded()
        self.fakepublic(self.__mergeroom__, self.joinPrivate(self.parent.myUsername, user), text)
    def LeaveChatroomNotification(self, room):
        if room == self.__mergeroom__:
            self.active = False
            self.roomsctrl.LeaveRoom(slskmessages.LeaveRoom(room)) # Faking protocol msg
    def replyMessage(self, command, room, args):
        if self.lastmessage:
            (type, destination) = self.lastmessage
            if type == 'Public':
                self.saypublic(destination, text)
                self.fakepublic(self.__mergeroom__, self.joinPublic(destination, self.parent.myUsername), realtext)
            elif type == 'PM':
                self.sayprivate(destination, text)
                self.fakepublic(self.__mergeroom__, self.joinPM(destination, self.parent.myUsername), realtext)
            else:
                self.log("EEK, programming error. (%s, %s)" % self.lastmessage)
        else:
            self.log("Nobody spoke so far, who am I supposed to send it to?")
    def joinPublic(self, room, user):
        return "public %s | %s" % (room, user)
    def joinPM(self, source, destination):
        return "pm %s -> %s" % (source, destination)
    __publiccommands__ = [('mergeview', createMergeview)]
    __publiccommands__ = [('r', replyMessage), ('reply', replyMessage)]

