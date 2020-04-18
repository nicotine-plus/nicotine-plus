from pynicotine.pluginsystem import BasePlugin


def enable(plugins):
    global PLUGIN
    PLUGIN = Plugin(plugins)


def disable(plugins):
    global PLUGIN
    PLUGIN = None


class Plugin(BasePlugin):
    __name__ = "Plugin Debugger"
    __version__ = "2009-05-27r00"
    __author__ = "quinox"
    __desc__ = """Plugin to examine the flow of events of the plugin system. Not useful if you're not a programmer."""

    def init(self):
        self.log('init')

    def LoadNotification(self):
        self.log('LoadNotification')
        pass

    def IncomingPrivateChatEvent(self, user, line):
        self.log('IncomingPrivateChatEvent user=%s, line=%s' % (user, line))
        pass

    def IncomingPrivateChatNotification(self, user, line):
        self.log('IncomingPrivateChatNotification, user=%s, line=%s' % (user, line))
        pass

    def IncomingPublicChatEvent(self, room, user, line):
        self.log('IncomingPublicChatEvent, room=%s, user=%s, line=%s' % (room, user, line))
        pass

    def IncomingPublicChatNotification(self, room, user, line):
        self.log('IncomingPublicChatNotification, room=%s, user=%s, line=%s' % (room, user, line))
        pass

    def OutgoingPrivateChatEvent(self, user, line):
        self.log('OutgoingPrivateChatEvent, user=%s, line=%s' % (user, line))
        pass

    def OutgoingPrivateChatNotification(self, user, line):
        self.log('OutgoingPrivateChatNotification, user=%s, line=%s' % (room, line))  # noqa: F821
        pass

    def OutgoingPublicChatEvent(self, room, line):
        self.log('OutgoingPublicChatEvent, room=%s, line=%s' % (room, line))
        pass

    def OutgoingPublicChatNotification(self, room, line):
        self.log('OutgoingPublicChatNotification, room=%s, line=%s' % (room, line))
        pass

    def OutgoingGlobalSearchEvent(self, text):
        self.log('OutgoingGlobalSearchEvent, text=%s' % (text,))
        pass

    def OutgoingRoomSearchEvent(self, rooms, text):
        self.log('OutgoingRoomSearchEvent, rooms=%s, text=%s' % (rooms, text))
        pass

    def OutgoingBuddySearchEvent(self, text):
        self.log('OutgoingBuddySearchEvent, text=%s' % (text,))
        pass

    def OutgoingUserSearchEvent(self, users):
        self.log('OutgoingUserSearchEvent, users=%s' % (users,))
        pass

    def UserResolveNotification(self, user, ip, port, country):
        self.log('UserResolveNotification, user=%s, ip=%s, port=%s, country=%s' % (user, ip, port, country))
        pass

    def ServerConnectNotification(self):
        self.log('ServerConnectNotification')
        pass

    def ServerDisconnectNotification(self, userchoice):
        self.log('ServerDisconnectNotification, userchoice=%s' % (userchoice,))
        pass

    def JoinChatroomNotification(self, room):
        self.log('JoinChatroomNotification, room=%s' % (room,))
        pass

    def LeaveChatroomNotification(self, room):
        self.log('LeaveChatroomNotification, room=%s' % (room,))
        pass
