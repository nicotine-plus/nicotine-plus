# COPYRIGHT (C) 2020-2022 Nicotine+ Team
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

        self.log('__init__()')

    def init(self):
        self.log('init()')

    def disable(self):
        self.log('disable()')

    def loaded_notification(self):
        self.log('loaded_notification()')

    def unloaded_notification(self):
        self.log('unloaded_notification()')

    def shutdown_notification(self):
        self.log('shutdown_notification()')

    def public_room_message_notification(self, room, user, line):
        self.log('public_room_message_notification(room=%s, user=%s, line=%s)', (room, user, line))

    def search_request_notification(self, searchterm, user, searchid):
        self.log('search_request_notification(searchterm=%s, user=%s, searchid=%s)', (searchterm, user, searchid))

    def distrib_search_notification(self, searchterm, user, searchid):
        # Verbose:
        # self.log('distrib_search_notification(searchterm=%s, user=%s, searchid=%s)', (searchterm, user, searchid))
        pass

    def incoming_private_chat_event(self, user, line):
        self.log('incoming_private_chat_event(user=%s, line=%s)', (user, line))

    def incoming_private_chat_notification(self, user, line):
        self.log('incoming_private_chat_notification(user=%s, line=%s)', (user, line))

    def incoming_public_chat_event(self, room, user, line):
        self.log('incoming_public_chat_event(room=%s, user=%s, line=%s)', (room, user, line))

    def incoming_public_chat_notification(self, room, user, line):
        self.log('incoming_public_chat_notification(room=%s, user=%s, line=%s)', (room, user, line))

    def outgoing_private_chat_event(self, user, line):
        self.log('outgoing_private_chat_event(user=%s, line=%s)', (user, line))

    def outgoing_private_chat_notification(self, user, line):
        self.log('outgoing_private_chat_notification(user=%s, line=%s)', (user, line))

    def outgoing_public_chat_event(self, room, line):
        self.log('outgoing_public_chat_event(room=%s, line=%s)', (room, line))

    def outgoing_public_chat_notification(self, room, line):
        self.log('outgoing_public_chat_notification(room=%s, line=%s)', (room, line))

    def outgoing_global_search_event(self, text):
        self.log('outgoing_global_search_event(text=%s)', (text,))

    def outgoing_room_search_event(self, rooms, text):
        self.log('outgoing_room_search_event(rooms=%s, text=%s)', (rooms, text))

    def outgoing_buddy_search_event(self, text):
        self.log('outgoing_buddy_search_event(text=%s)', (text,))

    def outgoing_user_search_event(self, users, text):
        self.log('outgoing_user_search_event(users=%s, text=%s)', (users, text))

    def user_resolve_notification(self, user, ip_address, port, country):
        self.log('user_resolve_notification(user=%s, ip_address=%s, port=%s, country=%s)',
                 (user, ip_address, port, country))

    def server_connect_notification(self):
        self.log('server_connect_notification()')

    def server_disconnect_notification(self, userchoice):
        self.log('server_disconnect_notification(userchoice=%s)', (userchoice,))

    def join_chatroom_notification(self, room):
        self.log('join_chatroom_notification(room=%s)', (room,))

    def leave_chatroom_notification(self, room):
        self.log('leave_chatroom_notification(room=%s)', (room,))

    def user_join_chatroom_notification(self, room, user):
        self.log('user_join_chatroom_notification(room=%s, user=%s)', (room, user,))

    def user_leave_chatroom_notification(self, room, user):
        self.log('user_leave_chatroom_notification(room=%s, user=%s)', (room, user,))

    def user_stats_notification(self, user, stats):
        self.log('user_stats_notification(user=%s, stats=%s)', (user, stats))

    def user_status_notification(self, user, status, privileged):
        self.log('user_status_notification(user=%s, status=%s, privileged=%s)', (user, status, privileged))

    def upload_queued_notification(self, user, virtual_path, real_path):
        self.log('upload_queued_notification(user=%s, virtual_path=%s, real_path=%s)', (user, virtual_path, real_path))

    def upload_started_notification(self, user, virtual_path, real_path):
        self.log('upload_started_notification(user=%s, virtual_path=%s, real_path=%s)', (user, virtual_path, real_path))

    def upload_finished_notification(self, user, virtual_path, real_path):
        self.log('upload_finished_notification(user=%s, virtual_path=%s, real_path=%s)', (user, virtual_path, real_path))

    def download_started_notification(self, user, virtual_path, real_path):
        self.log('download_started_notification(user=%s, virtual_path=%s, real_path=%s)',
                 (user, virtual_path, real_path))

    def download_finished_notification(self, user, virtual_path, real_path):
        self.log('download_finished_notification(user=%s, virtual_path=%s, real_path=%s)',
                 (user, virtual_path, real_path))
