# COPYRIGHT (C) 2020-2024 Nicotine+ Contributors
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
from pynicotine.utils import censor_text
from pynicotine.utils import find_whole_word


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

    def __init__(self):

        self.completions = set()
        self.server_rooms = set()
        self.joined_rooms = {}
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
            ("start", self._start),
            ("ticker-add", self._ticker_add),
            ("ticker-remove", self._ticker_remove),
            ("ticker-state", self._ticker_state),
            ("user-joined-room", self._user_joined_room),
            ("user-left-room", self._user_left_room)
        ):
            events.connect(event_name, callback)

    def _start(self):

        for room in config.sections["server"]["autojoin"]:
            if isinstance(room, str):
                self.show_room(room, is_private=(room in self.private_rooms), switch_page=False, remembered=True)

    def _quit(self):
        self.remove_all_rooms(is_permanent=False)
        self.completions.clear()

    def _server_login(self, msg):

        if not msg.success:
            return

        # Request a complete room list. A limited room list not including blacklisted rooms and
        # rooms with few users is automatically sent when logging in, but subsequent room list
        # requests contain all rooms.
        core.send_message_to_server(slskmessages.RoomList())

        core.send_message_to_server(slskmessages.PrivateRoomToggle(config.sections["server"]["private_chatrooms"]))

        for room in self.joined_rooms:
            if room == self.GLOBAL_ROOM_NAME:
                core.send_message_to_server(slskmessages.JoinGlobalRoom())
            else:
                core.send_message_to_server(slskmessages.JoinRoom(room))

    def _server_disconnect(self, _msg):

        for room_obj in self.joined_rooms.values():
            room_obj.tickers.clear()
            room_obj.users.clear()

        self.server_rooms.clear()
        self.update_completions()

    def show_room(self, room, is_private=False, switch_page=True, remembered=False):

        room_obj = self.joined_rooms.get(room)

        if room_obj is None:
            self.joined_rooms[room] = room_obj = Room(name=room, is_private=is_private)

            if room not in config.sections["server"]["autojoin"]:
                position = 0 if room == self.GLOBAL_ROOM_NAME else -1
                config.sections["server"]["autojoin"].insert(position, room)

        if not room_obj.users:
            if room == self.GLOBAL_ROOM_NAME:
                core.send_message_to_server(slskmessages.JoinGlobalRoom())
            else:
                core.send_message_to_server(slskmessages.JoinRoom(room, is_private))

        events.emit("show-room", room, is_private, switch_page, remembered)

    def remove_room(self, room, is_permanent=True):

        if room not in self.joined_rooms:
            return

        if room == self.GLOBAL_ROOM_NAME:
            core.send_message_to_server(slskmessages.LeaveGlobalRoom())
        else:
            core.send_message_to_server(slskmessages.LeaveRoom(room))

        room_obj = self.joined_rooms.pop(room)
        non_watched_users = room_obj.users.difference(core.users.watched)

        for username in non_watched_users:
            # We haven't explicitly watched the user, server will no longer send status updates
            for dictionary in (core.users.addresses, core.users.countries, core.users.statuses):
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

        if config.sections["words"]["replacewords"]:
            for word, replacement in config.sections["words"]["autoreplaced"].items():
                message = message.replace(str(word), str(replacement))

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
        return private_room is not None and private_room["owner"] == core.users.login_username

    def is_private_room_member(self, room):
        return room in self.private_rooms

    def is_private_room_operator(self, room):
        private_room = self.private_rooms.get(room)
        return private_room is not None and core.users.login_username in private_room["operators"]

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
        """Server code 14."""

        room_obj = self.joined_rooms.get(msg.room)

        if room_obj is None:
            self.show_room(msg.room, is_private=msg.private, switch_page=False)
            room_obj = self.joined_rooms[msg.room]
        else:
            room_obj.is_private = msg.private

        if msg.private:
            self.create_private_room(msg.room, msg.owner, msg.operators)

        for userdata in msg.users:
            username = userdata.username
            core.users.statuses[username] = userdata.status
            room_obj.users.add(username)

            # Request user's IP address, so we can get the country and ignore messages by IP
            if username not in core.users.addresses:
                core.users.request_ip_address(username)

        core.pluginhandler.join_chatroom_notification(msg.room)

    def _leave_room(self, msg):
        """Server code 15."""

        room_obj = self.joined_rooms.get(msg.room)

        if room_obj is not None:
            room_obj.users.clear()

        core.pluginhandler.leave_chatroom_notification(msg.room)

    def _private_room_users(self, msg):
        """Server code 133."""

        private_room = self.private_rooms.get(msg.room)

        if private_room is None:
            private_room = self.create_private_room(msg.room)

        private_room["users"] = msg.users
        private_room["joined"] = msg.numusers

    def _private_room_add_user(self, msg):
        """Server code 134."""

        private_room = self.private_rooms.get(msg.room)

        if private_room is not None and msg.user not in private_room["users"]:
            private_room["users"].append(msg.user)

    def _private_room_remove_user(self, msg):
        """Server code 135."""

        private_room = self.private_rooms.get(msg.room)

        if private_room is not None and msg.user in private_room["users"]:
            private_room["users"].remove(msg.user)

    def _private_room_added(self, msg):
        """Server code 139."""

        if msg.room in self.private_rooms:
            return

        self.create_private_room(msg.room)

        if msg.room in self.joined_rooms:
            # Room tab previously opened, join room now
            self.show_room(msg.room, is_private=True, switch_page=False)

        log.add(_("You have been added to a private room: %(room)s"), {"room": msg.room})

    def _private_room_removed(self, msg):
        """Server code 140."""

        if msg.room in self.private_rooms:
            del self.private_rooms[msg.room]

    def _private_room_toggle(self, msg):
        """Server code 141."""

        config.sections["server"]["private_chatrooms"] = msg.enabled

    def _private_room_add_operator(self, msg):
        """Server code 143."""

        private_room = self.private_rooms.get(msg.room)

        if private_room is not None and msg.user not in private_room["operators"]:
            private_room["operators"].append(msg.user)

    def _private_room_remove_operator(self, msg):
        """Server code 144."""

        private_room = self.private_rooms.get(msg.room)

        if private_room is not None and msg.user in private_room["operators"]:
            private_room["operators"].remove(msg.user)

    def _private_room_operator_added(self, msg):
        """Server code 145."""

        private_room = self.private_rooms.get(msg.room)

        if private_room is not None and core.users.login_username not in private_room["operators"]:
            private_room["operators"].append(core.users.login_username)

    def _private_room_operator_removed(self, msg):
        """Server code 146."""

        private_room = self.private_rooms.get(msg.room)

        if private_room is not None and core.users.login_username in private_room["operators"]:
            private_room["operators"].remove(core.users.login_username)

    def _private_room_owned(self, msg):
        """Server code 148."""

        private_room = self.private_rooms.get(msg.room)

        if private_room is None:
            private_room = self.create_private_room(msg.room)

        private_room["operators"] = msg.operators

    def _global_room_message(self, msg):
        """Server code 152."""

        self._say_chat_room(msg, is_global=True)

    def _room_list(self, msg):
        """Server code 64."""

        login_username = core.users.login_username

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

    def get_message_type(self, user, text):

        if text.startswith("/me "):
            return "action"

        if user == core.users.login_username:
            return "local"

        if core.users.login_username and find_whole_word(core.users.login_username.lower(), text.lower()) > -1:
            return "hilite"

        return "remote"

    def _say_chat_room(self, msg, is_global=False):
        """Server code 13."""

        room = msg.room
        username = msg.user

        if not is_global:
            if room not in self.joined_rooms:
                msg.room = None
                return

            log.add_chat(_("Chat message from user '%(user)s' in room '%(room)s': %(message)s"), {
                "user": username,
                "room": room,
                "message": msg.message
            })

            if username != "server":
                if core.network_filter.is_user_ignored(username):
                    msg.room = None
                    return

                if core.network_filter.is_user_ip_ignored(username):
                    msg.room = None
                    return

            event = core.pluginhandler.incoming_public_chat_event(room, username, msg.message)
            if event is None:
                msg.room = None
                return

            _room, _username, msg.message = event
        else:
            room = self.GLOBAL_ROOM_NAME

        message = msg.message
        msg.message_type = self.get_message_type(username, message)
        is_action_message = (msg.message_type == "action")

        if is_action_message:
            message = message.replace("/me ", "", 1)

        if config.sections["words"]["censorwords"] and username != core.users.login_username:
            message = censor_text(message, censored_patterns=config.sections["words"]["censored"])

        if is_action_message:
            msg.formatted_message = msg.message = f"* {username} {message}"
        else:
            msg.formatted_message = f"[{username}] {message}"

        if is_global:
            msg.formatted_message = f"{msg.room} | {msg.formatted_message}"

        if config.sections["logging"]["chatrooms"] or room in config.sections["logging"]["rooms"]:
            log.write_log_file(
                folder_path=log.room_folder_path,
                basename=room, text=msg.formatted_message
            )

        if is_global:
            core.pluginhandler.public_room_message_notification(msg.room, username, msg.message)
        else:
            core.pluginhandler.incoming_public_chat_notification(room, username, msg.message)

    def _user_joined_room(self, msg):
        """Server code 16."""

        room_obj = self.joined_rooms.get(msg.room)

        if room_obj is None:
            msg.room = None
            return

        username = msg.userdata.username

        if username == core.users.login_username:
            # Redundant message, we're already present in the list of users
            msg.room = None
            return

        room_obj.users.add(username)
        core.users.statuses[username] = msg.userdata.status

        # Request user's IP address, so we can get the country and ignore messages by IP
        if username not in core.users.addresses:
            core.users.request_ip_address(username)

        core.pluginhandler.user_join_chatroom_notification(msg.room, username)

    def _user_left_room(self, msg):
        """Server code 17."""

        room_obj = self.joined_rooms.get(msg.room)

        if room_obj is None:
            msg.room = None
            return

        username = msg.username
        room_obj.users.discard(username)

        if username not in core.users.watched:
            # We haven't explicitly watched the user, server will no longer send status updates
            for dictionary in (core.users.addresses, core.users.countries, core.users.statuses):
                dictionary.pop(username, None)

        core.pluginhandler.user_leave_chatroom_notification(msg.room, username)

    def _ticker_state(self, msg):
        """Server code 113."""

        room_obj = self.joined_rooms.get(msg.room)

        if room_obj is None:
            msg.room = None
            return

        room_obj.tickers.clear()

        for username, message in msg.msgs:
            if core.network_filter.is_user_ignored(username) or \
                    core.network_filter.is_user_ip_ignored(username):
                # User ignored, ignore ticker message
                continue

            room_obj.tickers[username] = message

    def _ticker_add(self, msg):
        """Server code 114."""

        room_obj = self.joined_rooms.get(msg.room)

        if room_obj is None:
            msg.room = None
            return

        username = msg.user

        if core.network_filter.is_user_ignored(username) or core.network_filter.is_user_ip_ignored(username):
            # User ignored, ignore Ticker messages
            return

        room_obj.tickers[username] = msg.msg

    def _ticker_remove(self, msg):
        """Server code 115."""

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
            self.completions.update(core.buddies.users)

        if config.sections["words"]["commands"]:
            self.completions.update(core.pluginhandler.get_command_list("chatroom"))

        events.emit("room-completions", self.completions.copy())
