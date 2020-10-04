from pynicotine.pluginsystem import BasePlugin


def enable(plugins):
    global PLUGIN
    PLUGIN = Plugin(plugins)


def disable(plugins):
    global PLUGIN
    PLUGIN = None


class Plugin(BasePlugin):
    __name__ = "Plugin Debugger"

    def init(self):
        self.log('init')

    def LoadNotification(self):
        self.log('LoadNotification')

    def IncomingPrivateChatEvent(self, user, line):
        self.log('IncomingPrivateChatEvent user=%s, line=%s' % (user, line))

    def IncomingPrivateChatNotification(self, user, line):
        self.log('IncomingPrivateChatNotification, user=%s, line=%s' % (user, line))

    def IncomingPublicChatEvent(self, room, user, line):
        self.log('IncomingPublicChatEvent, room=%s, user=%s, line=%s' % (room, user, line))

    def IncomingPublicChatNotification(self, room, user, line):
        self.log('IncomingPublicChatNotification, room=%s, user=%s, line=%s' % (room, user, line))

    def OutgoingPrivateChatEvent(self, user, line):
        self.log('OutgoingPrivateChatEvent, user=%s, line=%s' % (user, line))

    def OutgoingPrivateChatNotification(self, user, line):
        self.log('OutgoingPrivateChatNotification, user=%s, line=%s' % (user, line))

    def OutgoingPublicChatEvent(self, room, line):
        self.log('OutgoingPublicChatEvent, room=%s, line=%s' % (room, line))

    def OutgoingPublicChatNotification(self, room, line):
        self.log('OutgoingPublicChatNotification, room=%s, line=%s' % (room, line))

    def OutgoingGlobalSearchEvent(self, text):
        self.log('OutgoingGlobalSearchEvent, text=%s' % (text,))

    def OutgoingRoomSearchEvent(self, rooms, text):
        self.log('OutgoingRoomSearchEvent, rooms=%s, text=%s' % (rooms, text))

    def OutgoingBuddySearchEvent(self, text):
        self.log('OutgoingBuddySearchEvent, text=%s' % (text,))

    def OutgoingUserSearchEvent(self, users):
        self.log('OutgoingUserSearchEvent, users=%s' % (users,))

    def UserResolveNotification(self, user, ip, port, country):
        self.log('UserResolveNotification, user=%s, ip=%s, port=%s, country=%s' % (user, ip, port, country))

    def ServerConnectNotification(self):
        self.log('ServerConnectNotification')

    def ServerDisconnectNotification(self, userchoice):
        self.log('ServerDisconnectNotification, userchoice=%s' % (userchoice,))

    def JoinChatroomNotification(self, room):
        self.log('JoinChatroomNotification, room=%s' % (room,))

    def LeaveChatroomNotification(self, room):
        self.log('LeaveChatroomNotification, room=%s' % (room,))
