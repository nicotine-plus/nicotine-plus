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

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.log('__init__')

    def init(self):
        self.log('Init')

    def disable(self):
        self.log('Disable')

    def loaded_notification(self):
        self.log('LoadedNotification')

    def unloaded_notification(self):
        self.log('UnloadedNotification')

    def shutdown_notification(self):
        self.log('ShutdownNotification')

    def public_room_message_notification(self, room, user, line):
        self.log('PublicRoomMessageNotification, room=%s, user=%s, line=%s', (room, user, line))

    def incoming_private_chat_event(self, user, line):
        self.log('IncomingPrivateChatEvent, user=%s, line=%s', (user, line))

    def incoming_private_chat_notification(self, user, line):
        self.log('IncomingPrivateChatNotification, user=%s, line=%s', (user, line))

    def incoming_public_chat_event(self, room, user, line):
        self.log('IncomingPublicChatEvent, room=%s, user=%s, line=%s', (room, user, line))

    def incoming_public_chat_notification(self, room, user, line):
        self.log('IncomingPublicChatNotification, room=%s, user=%s, line=%s', (room, user, line))

    def outgoing_private_chat_event(self, user, line):
        self.log('OutgoingPrivateChatEvent, user=%s, line=%s', (user, line))

    def outgoing_private_chat_notification(self, user, line):
        self.log('OutgoingPrivateChatNotification, user=%s, line=%s', (user, line))

    def outgoing_public_chat_event(self, room, line):
        self.log('OutgoingPublicChatEvent, room=%s, line=%s', (room, line))

    def outgoing_public_chat_notification(self, room, line):
        self.log('OutgoingPublicChatNotification, room=%s, line=%s', (room, line))

    def outgoing_global_search_event(self, text):
        self.log('OutgoingGlobalSearchEvent, text=%s', (text,))

    def outgoing_room_search_event(self, rooms, text):
        self.log('OutgoingRoomSearchEvent, rooms=%s, text=%s', (rooms, text))

    def outgoing_buddy_search_event(self, text):
        self.log('OutgoingBuddySearchEvent, text=%s', (text,))

    def outgoing_user_search_event(self, users, text):
        self.log('OutgoingUserSearchEvent, users=%s, text=%s', (users, text))

    def user_resolve_notification(self, user, ip_address, port, country):
        self.log('UserResolveNotification, user=%s, ip_address=%s, port=%s, country=%s',
                 (user, ip_address, port, country))

    def server_connect_notification(self):
        self.log('ServerConnectNotification')

    def server_disconnect_notification(self, userchoice):
        self.log('ServerDisconnectNotification, userchoice=%s', (userchoice,))

    def join_chatroom_notification(self, room):
        self.log('JoinChatroomNotification, room=%s', (room,))

    def leave_chatroom_notification(self, room):
        self.log('LeaveChatroomNotification, room=%s', (room,))

    def user_join_chatroom_notification(self, room, user):
        self.log('UserJoinChatroomNotification, room=%s, user=%s', (room, user,))

    def user_leave_chatroom_notification(self, room, user):
        self.log('UserLeaveChatroomNotification, room=%s, user=%s', (room, user,))

    def user_stats_notification(self, user, stats):
        self.log('UserStatsNotification, user=%s, stats=%s', (user, stats))

    def upload_queued_notification(self, user, virtual_path, real_path):
        self.log('UploadQueuedNotification, user=%s, virtual_path=%s, real_path=%s', (user, virtual_path, real_path))

    def upload_started_notification(self, user, virtual_path, real_path):
        self.log('UploadStartedNotification, user=%s, virtual_path=%s, real_path=%s', (user, virtual_path, real_path))

    def upload_finished_notification(self, user, virtual_path, real_path):
        self.log('UploadFinishedNotification, user=%s, virtual_path=%s, real_path=%s', (user, virtual_path, real_path))

    def download_started_notification(self, user, virtual_path, real_path):
        self.log('DownloadStartedNotification, user=%s, virtual_path=%s, real_path=%s',
                 (user, virtual_path, real_path))

    def download_finished_notification(self, user, virtual_path, real_path):
        self.log('DownloadFinishedNotification, user=%s, virtual_path=%s, real_path=%s',
                 (user, virtual_path, real_path))
