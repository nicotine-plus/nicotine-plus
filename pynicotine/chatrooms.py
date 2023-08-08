# COPYRIGHT (C) 2020-2023 Nicotine+ Contributors
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

from pynicotine import slskmessages
from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.logfacility import log


class Room:

    __slots__ = ("name", "is_private", "users", "tickers")

    def __init__(self, name=None, is_private=False):

        self.name = name
        self.is_private = is_private
        self.users = set()
        self.tickers = {}


class ChatRooms:
    # Trailing spaces to avoid conflict with regular rooms
    GLOBAL_ROOM_NAME = "Public "
    JOINED_ROOMS_NAME = "Joined Rooms "

    def __init__(self):

        self.completions = set()
        self.server_rooms = set()
        self.joined_rooms = {}
        self.pending_autojoin_rooms = set()
        self.private_rooms = config.sections["private_rooms"]["rooms"]

        for event_name, callback in (
            ("global-room-message", self._global_room_message),
            ("join-room", self._join_room),
            ("leave-room", self._leave_room),
            ("private-room-add-operator", self._private_room_add_operator),
            ("private-room-add-user", self._private_room_add_user),
            ("private-room-added", self._private_room_added),
            ("private-room-operator-added", self._private_room_operator_added),
            ("private-room-operator-removed", self._private_room_operator_removed),
            ("private-room-owned", self._private_room_owned),
            ("private-room-remove-operator", self._private_room_remove_operator),
            ("private-room-remove-user", self._private_room_remove_user),
            ("private-room-removed", self._private_room_removed),
            ("private-room-toggle", self._private_room_toggle),
            ("private-room-users", self._private_room_users),
            ("quit", self._quit),
            ("room-list", self._room_list),
            ("say-chat-room", self._say_chat_room),
            ("server-login", self._server_login),
            ("server-disconnect", self._server_disconnect),
            ("ticker-add", self._ticker_add),
            ("ticker-remove", self._ticker_remove),
            ("ticker-state", self._ticker_state),
            ("user-joined-room", self._user_joined_room),
            ("user-left-room", self._user_left_room)
        ):
            events.connect(event_name, callback)

    def _quit(self):
        self.remove_all_rooms(is_permanent=False)
        self.completions.clear()

    def _server_login(self, msg):

        if not msg.success:
            return

        join_list = self.joined_rooms

        if not join_list:
            join_list = config.sections["server"]["autojoin"]

        for room in join_list:
            if not isinstance(room, str):
                continue

            self.pending_autojoin_rooms.add(room)

            if room == self.GLOBAL_ROOM_NAME:
                self.show_global_room()
            else:
                core.send_message_to_server(slskmessages.JoinRoom(room))

    def _server_disconnect(self, _msg):
        self.server_rooms.clear()
        self.pending_autojoin_rooms.clear()
        self.update_completions()

    def show_global_room(self):
        # Fake a JoinRoom protocol message
        events.emit("join-room", slskmessages.JoinRoom(self.GLOBAL_ROOM_NAME))
        core.send_message_to_server(slskmessages.JoinGlobalRoom())

    def show_room(self, room, is_private=False):

        if room == self.GLOBAL_ROOM_NAME:
            self.show_global_room()

        elif room not in self.joined_rooms:
            core.send_message_to_server(slskmessages.JoinRoom(room, is_private))
            return

        events.emit("show-room", room)

    def remove_room(self, room, is_permanent=True):

        if room not in self.joined_rooms:
            return

        if room == self.GLOBAL_ROOM_NAME:
            core.send_message_to_server(slskmessages.LeaveGlobalRoom())
        else:
            core.send_message_to_server(slskmessages.LeaveRoom(room))

        room_obj = self.joined_rooms.pop(room)
        non_watched_users = room_obj.users.difference(core.watched_users)

        for username in non_watched_users:
            # We haven't explicitly watched the user, server will no longer send status updates
            for dictionary in (core.user_addresses, core.user_countries, core.user_statuses):
                dictionary.pop(username, None)

        if is_permanent:
            if room in config.sections["columns"]["chat_room"]:
                del config.sections["columns"]["chat_room"][room]

            if room in config.sections["server"]["autojoin"]:
                config.sections["server"]["autojoin"].remove(room)

        events.emit("remove-room", room)

    def remove_all_rooms(self, is_permanent=True):
        for room in self.joined_rooms.copy():
            self.remove_room(room, is_permanent)

    def clear_room_messages(self, room):
        events.emit("clear-room-messages", room)

    def echo_message(self, room, message, message_type="local"):
        events.emit("echo-room-message", room, message, message_type)

    def send_message(self, room, message):

        if room not in self.joined_rooms:
            return

        event = core.pluginhandler.outgoing_public_chat_event(room, message)
        if event is None:
            return

        room, message = event
        message = core.privatechat.auto_replace(message)

        core.send_message_to_server(slskmessages.SayChatroom(room, message))
        core.pluginhandler.outgoing_public_chat_notification(room, message)

    def create_private_room(self, room, owner=None, operators=None):

        private_room = self.private_rooms.get(room)

        if private_room is None:
            private_room = self.private_rooms[room] = {
                "users": [],
                "joined": 0,
                "operators": operators or [],
                "owned": False,
                "owner": owner
            }
            return private_room

        private_room["owner"] = owner

        if operators is None:
            return private_room

        for operator in operators:
            if operator not in private_room["operators"]:
                private_room["operators"].append(operator)

        return private_room

    def add_user_to_private_room(self, room, username):
        core.send_message_to_server(slskmessages.PrivateRoomAddUser(room, username))

    def add_operator_to_private_room(self, room, username):
        core.send_message_to_server(slskmessages.PrivateRoomAddOperator(room, username))

    def remove_user_from_private_room(self, room, username):
        core.send_message_to_server(slskmessages.PrivateRoomRemoveUser(room, username))

    def remove_operator_from_private_room(self, room, username):
        core.send_message_to_server(slskmessages.PrivateRoomRemoveOperator(room, username))

    def is_private_room_owned(self, room):
        private_room = self.private_rooms.get(room)
        return private_room is not None and private_room["owner"] == core.login_username

    def is_private_room_member(self, room):
        return room in self.private_rooms

    def is_private_room_operator(self, room):
        private_room = self.private_rooms.get(room)
        return private_room is not None and core.login_username in private_room["operators"]

    def request_room_list(self):
        core.send_message_to_server(slskmessages.RoomList())

    def request_private_room_disown(self, room):

        if not self.is_private_room_owned(room):
            return

        core.send_message_to_server(slskmessages.PrivateRoomDisown(room))
        del self.private_rooms[room]

    def request_private_room_dismember(self, room):

        if not self.is_private_room_member(room):
            return

        core.send_message_to_server(slskmessages.PrivateRoomDismember(room))
        del self.private_rooms[room]

    def request_private_room_toggle(self, enabled):
        core.send_message_to_server(slskmessages.PrivateRoomToggle(enabled))

    def request_update_ticker(self, room, message):
        core.send_message_to_server(slskmessages.RoomTickerSet(room, message))

    def _join_room(self, msg):
        """ Server code: 14 """

        self.joined_rooms[msg.room] = room_obj = Room(name=msg.room, is_private=msg.private)

        if msg.room not in config.sections["server"]["autojoin"]:
            config.sections["server"]["autojoin"].append(msg.room)

        if msg.private:
            self.create_private_room(msg.room, msg.owner, msg.operators)

        for userdata in msg.users:
            username = userdata.username
            core.user_statuses[username] = userdata.status
            room_obj.users.add(username)

            # Request user's IP address, so we can get the country and ignore messages by IP
            if username not in core.user_addresses:
                core.request_ip_address(username)

        core.pluginhandler.join_chatroom_notification(msg.room)

    def _leave_room(self, msg):
        """ Server code: 15 """

        core.pluginhandler.leave_chatroom_notification(msg.room)
        self.remove_room(msg.room)

    def _private_room_users(self, msg):
        """ Server code: 133 """

        private_room = self.private_rooms.get(msg.room)

        if private_room is None:
            private_room = self.create_private_room(msg.room)

        private_room["users"] = msg.users
        private_room["joined"] = msg.numusers

    def _private_room_add_user(self, msg):
        """ Server code: 134 """

        private_room = self.private_rooms.get(msg.room)

        if private_room is not None and msg.user not in private_room["users"]:
            private_room["users"].append(msg.user)

    def _private_room_remove_user(self, msg):
        """ Server code: 135 """

        private_room = self.private_rooms.get(msg.room)

        if private_room is not None and msg.user in private_room["users"]:
            private_room["users"].remove(msg.user)

    def _private_room_added(self, msg):
        """ Server code: 139 """

        if msg.room not in self.private_rooms:
            self.create_private_room(msg.room)
            log.add(_("You have been added to a private room: %(room)s"), {"room": msg.room})

    def _private_room_removed(self, msg):
        """ Server code: 140 """

        if msg.room in self.private_rooms:
            del self.private_rooms[msg.room]

    def _private_room_toggle(self, msg):
        """ Server code: 141 """

        config.sections["server"]["private_chatrooms"] = msg.enabled

    def _private_room_add_operator(self, msg):
        """ Server code: 143 """

        private_room = self.private_rooms.get(msg.room)

        if private_room is not None and msg.user not in private_room["operators"]:
            private_room["operators"].append(msg.user)

    def _private_room_remove_operator(self, msg):
        """ Server code: 144 """

        private_room = self.private_rooms.get(msg.room)

        if private_room is not None and msg.user in private_room["operators"]:
            private_room["operators"].remove(msg.user)

    def _private_room_operator_added(self, msg):
        """ Server code: 145 """

        private_room = self.private_rooms.get(msg.room)

        if private_room is not None and core.login_username not in private_room["operators"]:
            private_room["operators"].append(core.login_username)

    def _private_room_operator_removed(self, msg):
        """ Server code: 146 """

        private_room = self.private_rooms.get(msg.room)

        if private_room is not None and core.login_username in private_room["operators"]:
            private_room["operators"].remove(core.login_username)

    def _private_room_owned(self, msg):
        """ Server code: 148 """

        private_room = self.private_rooms.get(msg.room)

        if private_room is None:
            private_room = self.create_private_room(msg.room)

        private_room["operators"] = msg.operators

    def _global_room_message(self, msg):
        """ Server code: 152 """

        core.pluginhandler.public_room_message_notification(msg.room, msg.user, msg.msg)

    def _room_list(self, msg):
        """ Server code: 64 """

        login_username = core.login_username

        for room, user_count in msg.rooms:
            self.server_rooms.add(room)

        for room, user_count in msg.ownedprivaterooms:
            room_data = self.private_rooms.get(room)

            if room_data is None:
                self.private_rooms[room] = {
                    "users": [],
                    "joined": user_count,
                    "operators": [],
                    "owner": login_username
                }
                continue

            room_data["joined"] = user_count
            room_data["owner"] = login_username

        for room, user_count in msg.otherprivaterooms:
            room_data = self.private_rooms.get(room)

            if room_data is None:
                self.private_rooms[room] = {
                    "users": [],
                    "joined": user_count,
                    "operators": [],
                    "owner": None
                }
                continue

            room_data["joined"] = user_count

            if room_data["owner"] == login_username:
                room_data["owner"] = None

        if config.sections["words"]["roomnames"]:
            self.update_completions()
            core.privatechat.update_completions()

    def _say_chat_room(self, msg):
        """ Server code: 13 """

        room = msg.room

        if room not in self.joined_rooms:
            msg.room = None
            return

        user = msg.user

        log.add_chat(_("Chat message from user '%(user)s' in room '%(room)s': %(message)s"), {
            "user": user,
            "room": room,
            "message": msg.msg
        })

        if core.network_filter.is_user_ignored(user):
            msg.room = None
            return

        if core.network_filter.is_user_ip_ignored(user):
            msg.room = None
            return

        event = core.pluginhandler.incoming_public_chat_event(room, user, msg.msg)
        if event is None:
            msg.room = None
            return

        _room, _user, msg.msg = event
        core.pluginhandler.incoming_public_chat_notification(room, user, msg.msg)

    def _user_joined_room(self, msg):
        """ Server code: 16 """

        room_obj = self.joined_rooms.get(msg.room)

        if room_obj is None:
            msg.room = None
            return

        username = msg.userdata.username
        room_obj.users.add(username)
        core.user_statuses[username] = msg.userdata.status

        # Request user's IP address, so we can get the country and ignore messages by IP
        if username not in core.user_addresses:
            core.request_ip_address(username)

        core.pluginhandler.user_join_chatroom_notification(msg.room, username)

    def _user_left_room(self, msg):
        """ Server code: 17 """

        room_obj = self.joined_rooms.get(msg.room)

        if room_obj is None:
            msg.room = None
            return

        username = msg.username
        room_obj.users.discard(username)

        if username not in core.watched_users:
            # We haven't explicitly watched the user, server will no longer send status updates
            for dictionary in (core.user_addresses, core.user_countries, core.user_statuses):
                dictionary.pop(username, None)

        core.pluginhandler.user_leave_chatroom_notification(msg.room, username)

    def _ticker_state(self, msg):
        """ Server code: 113 """

        room_obj = self.joined_rooms.get(msg.room)

        if room_obj is None:
            msg.room = None
            return

        room_obj.tickers.clear()

        for user, message in msg.msgs:
            if core.network_filter.is_user_ignored(user) or \
                    core.network_filter.is_user_ip_ignored(user):
                # User ignored, ignore ticker message
                continue

            room_obj.tickers[user] = message

    def _ticker_add(self, msg):
        """ Server code: 114 """

        room_obj = self.joined_rooms.get(msg.room)

        if room_obj is None:
            msg.room = None
            return

        user = msg.user

        if core.network_filter.is_user_ignored(user) or core.network_filter.is_user_ip_ignored(user):
            # User ignored, ignore Ticker messages
            return

        room_obj.tickers[user] = msg.msg

    def _ticker_remove(self, msg):
        """ Server code: 115 """

        room_obj = self.joined_rooms.get(msg.room)

        if room_obj is None:
            msg.room = None
            return

        room_obj.tickers.pop(msg.user, None)

    def update_completions(self):

        self.completions.clear()
        self.completions.add(config.sections["server"]["login"])

        if config.sections["words"]["roomnames"]:
            self.completions.update(self.server_rooms)

        if config.sections["words"]["buddies"]:
            self.completions.update(core.userlist.buddies)

        if config.sections["words"]["commands"]:
            self.completions.update(core.pluginhandler.get_command_list("chatroom"))

        events.emit("room-completions", self.completions.copy())
