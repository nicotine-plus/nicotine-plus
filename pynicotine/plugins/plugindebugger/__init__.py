# COPYRIGHT (C) 2020-2021 Nicotine+ Team
# COPYRIGHT (C) 2009 Quinox <quinox@users.sf.net>
#
# GNU GENERAL PUBLIC LICENSE
#    Version 3, 29 June 2007
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from pynicotine.pluginsystem import BasePlugin


class Plugin(BasePlugin):
    __name__ = "Plugin Debugger"

    def init(self):
        self.log('init')

    def LoadNotification(self):  # noqa
        self.log('LoadNotification')

    def IncomingPrivateChatEvent(self, user, line):  # noqa
        self.log('IncomingPrivateChatEvent user=%s, line=%s' % (user, line))

    def IncomingPrivateChatNotification(self, user, line):  # noqa
        self.log('IncomingPrivateChatNotification, user=%s, line=%s' % (user, line))

    def IncomingPublicChatEvent(self, room, user, line):  # noqa
        self.log('IncomingPublicChatEvent, room=%s, user=%s, line=%s' % (room, user, line))

    def IncomingPublicChatNotification(self, room, user, line):  # noqa
        self.log('IncomingPublicChatNotification, room=%s, user=%s, line=%s' % (room, user, line))

    def OutgoingPrivateChatEvent(self, user, line):  # noqa
        self.log('OutgoingPrivateChatEvent, user=%s, line=%s' % (user, line))

    def OutgoingPrivateChatNotification(self, user, line):  # noqa
        self.log('OutgoingPrivateChatNotification, user=%s, line=%s' % (user, line))

    def OutgoingPublicChatEvent(self, room, line):  # noqa
        self.log('OutgoingPublicChatEvent, room=%s, line=%s' % (room, line))

    def OutgoingPublicChatNotification(self, room, line):  # noqa
        self.log('OutgoingPublicChatNotification, room=%s, line=%s' % (room, line))

    def OutgoingGlobalSearchEvent(self, text):  # noqa
        self.log('OutgoingGlobalSearchEvent, text=%s' % (text,))

    def OutgoingRoomSearchEvent(self, rooms, text):  # noqa
        self.log('OutgoingRoomSearchEvent, rooms=%s, text=%s' % (rooms, text))

    def OutgoingBuddySearchEvent(self, text):  # noqa
        self.log('OutgoingBuddySearchEvent, text=%s' % (text,))

    def OutgoingUserSearchEvent(self, users, text):  # noqa
        self.log('OutgoingUserSearchEvent, users=%s, text=%s' % (users, text))

    def UserResolveNotification(self, user, ip, port, country):  # noqa
        self.log('UserResolveNotification, user=%s, ip=%s, port=%s, country=%s' % (user, ip, port, country))

    def ServerConnectNotification(self):  # noqa
        self.log('ServerConnectNotification')

    def ServerDisconnectNotification(self, userchoice):  # noqa
        self.log('ServerDisconnectNotification, userchoice=%s' % (userchoice,))

    def JoinChatroomNotification(self, room):  # noqa
        self.log('JoinChatroomNotification, room=%s' % (room,))

    def LeaveChatroomNotification(self, room):  # noqa
        self.log('LeaveChatroomNotification, room=%s' % (room,))

    def UserJoinChatroomNotification(self, room, user):  # noqa
        self.log('UserJoinChatroomNotification, room=%s, user=%s' % (room, user,))

    def UserLeaveChatroomNotification(self, room, user):  # noqa
        self.log('UserLeaveChatroomNotification, room=%s, user=%s' % (room, user,))

    def ShutdownNotification(self):  # noqa
        self.log('ShutdownNotification')
