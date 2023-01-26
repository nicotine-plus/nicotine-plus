# COPYRIGHT (C) 2020-2022 Nicotine+ Contributors
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


class ChatRooms:
    GLOBAL_ROOM_NAME = "Public "  # Trailing space to avoid conflict with regular rooms

    def __init__(self):

        self.server_rooms = set()
        self.joined_rooms = set()
        self.private_rooms = config.sections["private_rooms"]["rooms"]
        self.completion_list = []

        for event_name, callback in (
            ("global-room-message", self._global_room_message),
            ("join-room", self._join_room),
            ("leave-room", self._leave_room),
            ("private-room-add-operator", self._private_room_add_operator),
            ("private-room-add-user", self._private_room_add_user),
            ("private-room-added", self._private_room_added),
            ("private-room-disown", self._private_room_disown),
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
            ("user-joined-room", self._user_joined_room),
            ("user-left-room", self._user_left_room)
        ):
            events.connect(event_name, callback)

    def _quit(self):
        self.joined_rooms.clear()
        self.completion_list.clear()

    def _server_login(self, msg):

        if not msg.success:
            return

        join_list = self.joined_rooms

        if not join_list:
            join_list = config.sections["server"]["autojoin"]

        for room in join_list:
            if room == self.GLOBAL_ROOM_NAME:
                core.queue.append(slskmessages.JoinGlobalRoom())

            elif isinstance(room, str):
                core.queue.append(slskmessages.JoinRoom(room))

    def _server_disconnect(self, _msg):
        self.server_rooms.clear()

    def show_room(self, room, private=False):

        if room == self.GLOBAL_ROOM_NAME:
            # Fake a JoinRoom protocol message
            events.emit("join-room", slskmessages.JoinRoom(room))
            core.queue.append(slskmessages.JoinGlobalRoom())

        elif room not in self.joined_rooms:
            core.queue.append(slskmessages.JoinRoom(room, private))
            return

        events.emit("show-room", room)

    def remove_room(self, room):

        if room == self.GLOBAL_ROOM_NAME:
            core.queue.append(slskmessages.LeaveGlobalRoom())
        else:
            core.queue.append(slskmessages.LeaveRoom(room))

        self.joined_rooms.discard(room)

        if room in config.sections["columns"]["chat_room"]:
            del config.sections["columns"]["chat_room"][room]

        events.emit("remove-room", room)

    def clear_room_messages(self, room):
        events.emit("clear-room-messages", room)

    def echo_message(self, room, message, message_type="local"):
        events.emit("echo-room-message", room, message, message_type)

    def send_message(self, room, message):

        event = core.pluginhandler.outgoing_public_chat_event(room, message)
        if event is None:
            return

        room, message = event
        message = core.privatechat.auto_replace(message)

        core.queue.append(slskmessages.SayChatroom(room, message))
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

    def is_private_room_owned(self, room):
        private_room = self.private_rooms.get(room)
        return private_room is not None and private_room["owner"] == core.login_username

    def is_private_room_member(self, room):
        return room in self.private_rooms

    def is_private_room_operator(self, room):
        private_room = self.private_rooms.get(room)
        return private_room is not None and core.login_username in private_room["operators"]

    def request_room_list(self):
        core.queue.append(slskmessages.RoomList())

    def request_private_room_disown(self, room):

        if not self.is_private_room_owned(room):
            return

        core.queue.append(slskmessages.PrivateRoomDisown(room))
        del self.private_rooms[room]

    def request_private_room_dismember(self, room):

        if not self.is_private_room_member(room):
            return

        core.queue.append(slskmessages.PrivateRoomDismember(room))
        del self.private_rooms[room]

    def request_private_room_toggle(self, enabled):
        core.queue.append(slskmessages.PrivateRoomToggle(enabled))

    def _join_room(self, msg):
        """ Server code: 14 """

        self.joined_rooms.add(msg.room)

        if msg.private:
            self.create_private_room(msg.room, msg.owner, msg.operators)

        for userdata in msg.users:
            # Request user's IP address, so we can get the country and ignore messages by IP
            core.queue.append(slskmessages.GetPeerAddress(userdata.username))

        core.pluginhandler.join_chatroom_notification(msg.room)

    def _leave_room(self, msg):
        """ Server code: 15 """

        core.pluginhandler.leave_chatroom_notification(msg.room)

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

    def _private_room_disown(self, msg):
        """ Server code: 137 """

        private_room = self.private_rooms.get(msg.room)

        if private_room is not None and private_room["owner"] == core.login_username:
            private_room["owner"] = None

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

        for room in msg.rooms:
            self.server_rooms.add(room[0])

        for room in msg.ownedprivaterooms:
            room_data = self.private_rooms.get(room[0])

            if room_data is None:
                self.private_rooms[room[0]] = {"users": [], "joined": room[1], "operators": [], "owner": login_username}
                continue

            room_data["joined"] = room[1]
            room_data["owner"] = login_username

        for room in msg.otherprivaterooms:
            room_data = self.private_rooms.get(room[0])

            if room_data is None:
                self.private_rooms[room[0]] = {"users": [], "joined": room[1], "operators": [], "owner": None}
                continue

            room_data["joined"] = room[1]

            if room_data["owner"] == login_username:
                room_data["owner"] = None

    def _say_chat_room(self, msg):
        """ Server code: 13 """

        user = msg.user

        log.add_chat(_("Chat message from user '%(user)s' in room '%(room)s': %(message)s"), {
            "user": user,
            "room": msg.room,
            "message": msg.msg
        })

        if core.network_filter.is_user_ignored(user):
            msg.room = None
            return

        if core.network_filter.is_user_ip_ignored(user):
            msg.room = None
            return

        event = core.pluginhandler.incoming_public_chat_event(msg.room, user, msg.msg)
        if event is None:
            msg.room = None
            return

        _room, _user, msg.msg = event
        core.pluginhandler.incoming_public_chat_notification(msg.room, user, msg.msg)

    def _user_joined_room(self, msg):
        """ Server code: 16 """

        user = msg.userdata.username

        # Request user's IP address, so we can get the country and ignore messages by IP
        core.queue.append(slskmessages.GetPeerAddress(user))

        core.pluginhandler.user_join_chatroom_notification(msg.room, user)

    def _user_left_room(self, msg):
        """ Server code: 17 """

        core.pluginhandler.user_leave_chatroom_notification(msg.room, msg.username)

    def update_completions(self):

        self.completion_list = [config.sections["server"]["login"]]

        if config.sections["words"]["roomnames"]:
            self.completion_list += self.server_rooms

        if config.sections["words"]["buddies"]:
            self.completion_list += list(core.userlist.buddies)

        if config.sections["words"]["commands"]:
            self.completion_list += list(core.pluginhandler.chatroom_commands)

        events.emit("room-completion-list", self.completion_list)


class Tickers:

    def __init__(self):

        self.messages = []

    def add_ticker(self, user, message):

        message = message.replace("\n", " ")
        self.messages.insert(0, (user, message))

    def remove_ticker(self, user):

        for i, message in enumerate(self.messages):
            if message[0] == user:
                del self.messages[i]
                return

    def get_tickers(self):
        return self.messages

    def clear_tickers(self):
        self.messages.clear()
