# SPDX-FileCopyrightText: 2020-2026 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

from dataclasses import dataclass
from dataclasses import field

from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.events import StopEventPropagation
from pynicotine.logfacility import log
from pynicotine.slskmessages import SERVER_USERNAME
from pynicotine.slskmessages import AddRoomMember
from pynicotine.slskmessages import AddRoomOperator
from pynicotine.slskmessages import CancelRoomMembership
from pynicotine.slskmessages import CancelRoomOwnership
from pynicotine.slskmessages import EnableRoomInvitations
from pynicotine.slskmessages import JoinGlobalRoom
from pynicotine.slskmessages import JoinRoom
from pynicotine.slskmessages import LeaveGlobalRoom
from pynicotine.slskmessages import LeaveRoom
from pynicotine.slskmessages import RemoveRoomOperator
from pynicotine.slskmessages import RemoveRoomMember
from pynicotine.slskmessages import RoomList
from pynicotine.slskmessages import RoomType
from pynicotine.slskmessages import SayChatroom
from pynicotine.slskmessages import SetRoomTicker
from pynicotine.slskmessages import UserStatus
from pynicotine.utils import censor_text
from pynicotine.utils import find_whole_word
from pynicotine.utils import replace_text


@dataclass(slots=True, eq=False)
class JoinedRoom:
    name: str
    is_private: bool = False
    users: set[str] = field(default_factory=set)
    tickers: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True, eq=False)
class PrivateRoom:
    name: str
    owner: str | None = None
    members: set[str] = field(default_factory=set)
    operators: set[str] = field(default_factory=set)


class ChatRooms:
    __slots__ = ("completions", "server_rooms", "joined_rooms", "private_rooms")

    # Trailing spaces to avoid conflict with regular rooms
    GLOBAL_ROOM_NAME = "Public "
    ROOM_NAME_MAX_LENGTH = 24

    def __init__(self):

        self.completions = set()
        self.server_rooms = set()
        self.joined_rooms = {}
        self.private_rooms = {}

        for event_name, callback in (
            ("add-room-operator", self._add_room_operator),
            ("add-room-member", self._add_room_member),
            ("enable-room-invitations", self._enable_room_invitations),
            ("global-room-message", self._global_room_message),
            ("join-room", self._join_room),
            ("leave-room", self._leave_room),
            ("quit", self._quit),
            ("remove-room-member", self._remove_room_member),
            ("remove-room-operator", self._remove_room_operator),
            ("room-invitation-rejected", self._room_invitation_rejected),
            ("room-members", self._room_members),
            ("room-membership-granted", self._room_membership_granted),
            ("room-membership-revoked", self._room_membership_revoked),
            ("room-operators", self._room_operators),
            ("room-operatorship-granted", self._room_operatorship_granted),
            ("room-operatorship-revoked", self._room_operatorship_revoked),
            ("room-list", self._room_list),
            ("room-ticker-added", self._room_ticker_added),
            ("room-ticker-removed", self._room_ticker_removed),
            ("room-tickers", self._room_tickers),
            ("say-chat-room", self._say_chat_room),
            ("server-disconnect", self._server_disconnect),
            ("server-login", self._server_login),
            ("start", self._start),
            ("user-joined-room", self._user_joined_room),
            ("user-left-room", self._user_left_room)
        ):
            events.connect(event_name, callback)

    def _start(self):

        for room_name in config.sections["server"]["autojoin"]:
            if isinstance(room_name, str):
                self.show_room(
                    room_name, is_private=(room_name in self.private_rooms), switch_page=False, remembered=True)

    def _quit(self):
        self.remove_all_rooms(is_permanent=False)
        self.completions.clear()

    def _server_login(self, msg):

        if not msg.success:
            return

        # Request a complete room list. A limited room list not including blacklisted rooms and
        # rooms with few users is automatically sent when logging in, but subsequent room list
        # requests contain all rooms.
        self.request_room_list()

        self.request_enable_room_invitations(config.sections["server"]["private_chatrooms"])

        for room_name in self.joined_rooms:
            if room_name == self.GLOBAL_ROOM_NAME:
                core.send_message_to_server(JoinGlobalRoom())
            else:
                core.send_message_to_server(JoinRoom(room_name))

    def _server_disconnect(self, _msg):

        for room in self.joined_rooms.values():
            room.tickers.clear()
            room.users.clear()

        self.server_rooms.clear()
        self.private_rooms.clear()
        self.update_completions()

    def show_room(self, room_name, is_private=False, switch_page=True, remembered=False):

        room = self.joined_rooms.get(room_name)

        if room is None:
            self.joined_rooms[room_name] = room = JoinedRoom(name=room_name, is_private=is_private)

            if room_name not in config.sections["server"]["autojoin"]:
                if room_name == self.GLOBAL_ROOM_NAME:
                    config.sections["server"]["autojoin"].insert(0, room_name)
                else:
                    config.sections["server"]["autojoin"].append(room_name)

        if not room.users:
            if room_name == self.GLOBAL_ROOM_NAME:
                core.send_message_to_server(JoinGlobalRoom())
            else:
                core.send_message_to_server(
                    JoinRoom(room_name, RoomType.PRIVATE if is_private else RoomType.PUBLIC)
                )

        events.emit("show-room", room_name, is_private, switch_page, remembered)

    def remove_room(self, room_name, is_permanent=True):

        if room_name not in self.joined_rooms:
            return

        if room_name == self.GLOBAL_ROOM_NAME:
            core.send_message_to_server(LeaveGlobalRoom())
        else:
            core.send_message_to_server(LeaveRoom(room_name))

        room = self.joined_rooms.pop(room_name)

        for username in room.users:
            core.users.unwatch_user(username, context=f"chatrooms_{room_name}")

        if is_permanent:
            if room_name in config.sections["columns"]["chat_room"]:
                del config.sections["columns"]["chat_room"][room_name]

            if room_name in config.sections["server"]["autojoin"]:
                config.sections["server"]["autojoin"].remove(room_name)

        events.emit("remove-room", room_name)

    def remove_all_rooms(self, is_permanent=True):
        for room_name in self.joined_rooms.copy():
            self.remove_room(room_name, is_permanent)

    @classmethod
    def sanitize_room_name(cls, room_name):
        """Sanitize room name according to server requirements."""

        # Replace non-ASCII characters
        room_name = room_name.strip().encode("ascii", errors="replace").decode()

        # Remove two or more consecutive spaces
        room_name = " ".join(room_name.split())

        # Limit to 24 characters
        room_name = room_name[:cls.ROOM_NAME_MAX_LENGTH]
        return room_name

    def clear_room_messages(self, room_name):
        events.emit("clear-room-messages", room_name)

    def echo_message(self, room_name, message, message_type="local"):
        events.emit("echo-room-message", room_name, message, message_type)

    def send_message(self, room_name, message):

        if core.users.login_status == UserStatus.OFFLINE:
            return

        if room_name not in self.joined_rooms:
            return

        event = core.pluginhandler.outgoing_public_chat_event(room_name, message)
        if event is None:
            return

        room_name, message = event

        if config.sections["words"]["replacewords"]:
            message = replace_text(message, config.sections["words"]["autoreplaced"])

        # Server rejects messages containing newlines, filter them
        message = message.replace("\r", "").replace("\n", " ")

        core.send_message_to_server(SayChatroom(room_name, message))
        core.pluginhandler.outgoing_public_chat_notification(room_name, message)

    def request_add_room_member(self, room_name, username):
        core.send_message_to_server(AddRoomMember(room_name, username))

    def request_add_room_operator(self, room_name, username):
        core.send_message_to_server(AddRoomOperator(room_name, username))

    def request_remove_room_member(self, room_name, username):
        core.send_message_to_server(RemoveRoomMember(room_name, username))

    def request_remove_room_operator(self, room_name, username):
        core.send_message_to_server(RemoveRoomOperator(room_name, username))

    def is_room_owner(self, room_name):
        private_room = self.private_rooms.get(room_name)
        return private_room is not None and private_room.owner == core.users.login_username

    def is_room_member(self, room_name):
        return room_name in self.private_rooms

    def is_room_operator(self, room_name):
        private_room = self.private_rooms.get(room_name)
        return private_room is not None and core.users.login_username in private_room.operators

    def request_room_list(self):
        core.send_message_to_server(RoomList())

    def request_cancel_room_ownership(self, room_name):

        if not self.is_room_owner(room_name):
            return

        core.send_message_to_server(CancelRoomOwnership(room_name))

    def request_cancel_room_membership(self, room_name):

        if not self.is_room_member(room_name):
            return

        core.send_message_to_server(CancelRoomMembership(room_name))

    def request_enable_room_invitations(self, enabled):
        core.send_message_to_server(EnableRoomInvitations(enabled))

    def request_update_ticker(self, room_name, message):
        core.send_message_to_server(SetRoomTicker(room_name, message))

    def _update_room_user(self, room, user_stats):

        username = user_stats.username
        room.users.add(username)
        core.users.watch_user(username, context=f"chatrooms_{room.name}", is_implicit=True)

        watched_user = core.users.watched[username]
        watched_user.upload_speed = user_stats.upload_speed
        watched_user.num_files = user_stats.num_files
        watched_user.num_folders = user_stats.num_folders

        core.users.statuses[username] = user_stats.status

        # Request user's IP address, so we can get the country and ignore messages by IP
        if username not in core.users.addresses:
            core.users.request_ip_address(username)

        # Replace server-provided country with our own
        if username in core.users.countries:
            user_stats.country_code = core.users.countries[username]

    def _update_private_room(self, room_name, owner=None, members=None, operators=None):

        private_room = self.private_rooms.get(room_name)

        if private_room is None:
            private_room = self.private_rooms[room_name] = PrivateRoom(room_name)
            core.pluginhandler.private_room_membership_granted_notification(room_name)

        if owner:
            private_room.owner = owner
            core.pluginhandler.private_room_member_added_notification(room_name, owner)

        if members:
            for member in members:
                private_room.members.add(member)
                core.pluginhandler.private_room_member_added_notification(room_name, member)

        if operators:
            for operator in operators:
                private_room.operators.add(operator)
                core.pluginhandler.private_room_operator_added_notification(room_name, operator)

        self.server_rooms.add(room_name)

    def _room_invitation_rejected(self, username):
        log.add(_("User %(user)s has not enabled private room invitations"), {"user": username})

    def _join_room(self, msg):
        """Server code 14."""

        room_name = msg.room_name
        room = self.joined_rooms.get(room_name)

        if room is None:
            # Reject unsolicited room join messages from the server
            core.send_message_to_server(LeaveRoom(room_name))
            raise StopEventPropagation()

        room.is_private = (msg.room_type == RoomType.PRIVATE)
        self.server_rooms.add(room_name)

        if room.is_private:
            self._update_private_room(room_name, owner=msg.owner, operators=msg.operators)

        for user_stats in msg.users:
            self._update_room_user(room, user_stats)

        core.pluginhandler.join_chatroom_notification(room_name)

    def _leave_room(self, msg):
        """Server code 15."""

        room_name = msg.room_name
        room = self.joined_rooms.get(room_name)

        if room is None or not room.users:
            raise StopEventPropagation()

        for username in room.users:
            core.users.unwatch_user(username, context=f"chatrooms_{room_name}")

        room.users.clear()
        core.pluginhandler.leave_chatroom_notification(room_name)

    def _room_members(self, msg):
        """Server code 133."""

        self._update_private_room(msg.room_name, members=msg.members)

    def _add_room_member(self, msg):
        """Server code 134."""

        username = msg.username
        room_name = msg.room_name
        private_room = self.private_rooms.get(room_name)

        if private_room is None:
            raise StopEventPropagation()

        private_room.members.add(username)
        core.pluginhandler.private_room_member_added_notification(room_name, username)

        if username != core.users.login_username:
            log.add(_("User %(user)s has been added to private room %(room)s"), {
                "user": username,
                "room": room_name
            })

    def _remove_room_member(self, msg):
        """Server code 135."""

        username = msg.username
        room_name = msg.room_name
        private_room = self.private_rooms.get(room_name)

        if private_room is None:
            raise StopEventPropagation()

        private_room.members.discard(username)
        core.pluginhandler.private_room_member_removed_notification(room_name, username)

        if username != core.users.login_username:
            log.add(_("User %(user)s has been removed from private room %(room)s"), {
                "user": username,
                "room": room_name
            })

    def _room_membership_granted(self, msg):
        """Server code 139."""

        room_name = msg.room_name

        if room_name in self.private_rooms:
            raise StopEventPropagation()

        self._update_private_room(room_name)

        if room_name in self.joined_rooms:
            # Room tab previously opened, join room now
            self.show_room(room_name, is_private=True, switch_page=False)

        log.add(_("You have been added to private room %(room)s"), {"room": room_name})

    def _room_membership_revoked(self, msg):
        """Server code 140."""

        room_name = msg.room_name

        if room_name not in self.private_rooms:
            raise StopEventPropagation()

        core.pluginhandler.private_room_membership_revoked_notification(room_name)

        self.server_rooms.discard(room_name)
        del self.private_rooms[room_name]

        log.add(_("You have been removed from private room %(room)s"), {"room": room_name})

    def _enable_room_invitations(self, msg):
        """Server code 141."""

        config.sections["server"]["private_chatrooms"] = msg.enable

    def _add_room_operator(self, msg):
        """Server code 143."""

        username = msg.username
        room_name = msg.room_name
        private_room = self.private_rooms.get(room_name)

        if private_room is None:
            raise StopEventPropagation()

        private_room.operators.add(username)
        core.pluginhandler.private_room_operator_added_notification(room_name, username)

        if username != core.users.login_username:
            log.add(_("User %(user)s is now an operator of room %(room)s"), {
                "user": username,
                "room": room_name
            })

    def _remove_room_operator(self, msg):
        """Server code 144."""

        username = msg.username
        room_name = msg.room_name
        private_room = self.private_rooms.get(room_name)

        if private_room is None:
            raise StopEventPropagation()

        private_room.operators.discard(username)
        core.pluginhandler.private_room_operator_removed_notification(room_name, username)

        if username != core.users.login_username:
            log.add(_("User %(user)s is no longer an operator of room %(room)s"), {
                "user": username,
                "room": room_name
            })

    def _room_operatorship_granted(self, msg):
        """Server code 145."""

        room_name = msg.room_name
        private_room = self.private_rooms.get(room_name)

        if private_room is None:
            raise StopEventPropagation()

        private_room.operators.add(core.users.login_username)
        core.pluginhandler.private_room_operatorship_granted_notification(room_name)

        log.add(_("You are now an operator of room %(room)s"), {"room": room_name})

    def _room_operatorship_revoked(self, msg):
        """Server code 146."""

        room_name = msg.room_name
        private_room = self.private_rooms.get(room_name)

        if private_room is None:
            raise StopEventPropagation()

        private_room.operators.discard(core.users.login_username)
        core.pluginhandler.private_room_operatorship_revoked_notification(room_name)

        log.add(_("You are no longer an operator of room %(room)s"), {"room": room_name})

    def _room_operators(self, msg):
        """Server code 148."""

        self._update_private_room(msg.room_name, operators=msg.operators)

    def _global_room_message(self, msg):
        """Server code 152."""

        if self.GLOBAL_ROOM_NAME not in self.joined_rooms:
            raise StopEventPropagation()

        self._say_chat_room(msg, is_global=True)

    def _room_list(self, msg):
        """Server code 64."""

        for room_stats in msg.rooms:
            self.server_rooms.add(room_stats.name)

        for room_stats in msg.rooms_owner:
            self._update_private_room(room_stats.name, owner=core.users.login_username)

        for room_stats in msg.rooms_member:
            self._update_private_room(room_stats.name)

        if config.sections["words"]["roomnames"]:
            self.update_completions()
            core.privatechat.update_completions()

    def get_message_type(self, username, message):

        if message.startswith("/me "):
            return "action"

        if username == core.users.login_username:
            return "local"

        return "remote"

    def get_mention_type(self, username, message):

        message_lower = message.lower()

        if core.users.login_username and find_whole_word(core.users.login_username.lower(), message_lower) > -1:
            return "self", core.users.login_username

        if not config.sections["words"]["watch_keywords"]:
            return None, None

        username_lower = username.lower()

        for word in config.sections["words"]["keywords"]:
            word_lower = word.strip().lower()

            if not word_lower:
                continue

            if find_whole_word(word_lower, message_lower) > -1:
                return "keyword", word

            if word_lower == username_lower:
                return "username", username

        return None, None

    def _say_chat_room(self, msg, is_global=False):
        """Server code 13."""

        room_name = msg.room_name
        username = msg.username

        if not is_global:
            if room_name not in self.joined_rooms:
                raise StopEventPropagation()

            if username != SERVER_USERNAME and not self.joined_rooms[room_name].users:
                raise StopEventPropagation()

            log.add_chat(_("Chat message from user '%(user)s' in room '%(room)s': %(message)s"), {
                "user": username,
                "room": room_name,
                "message": msg.message
            })

            if username != "server":
                if core.network_filter.is_user_ignored(username):
                    raise StopEventPropagation()

                if core.network_filter.is_user_ip_ignored(username):
                    raise StopEventPropagation()

            event = core.pluginhandler.incoming_public_chat_event(room_name, username, msg.message)
            if event is None:
                raise StopEventPropagation()

            _room_name, _username, msg.message = event
        else:
            room_name = self.GLOBAL_ROOM_NAME

        message = msg.message
        msg.message_type = self.get_message_type(username, message)
        is_action_message = (msg.message_type == "action")
        msg.mention_type, msg.mention_keyword = self.get_mention_type(username, message)

        if is_action_message:
            msg.message = message = message.replace("/me ", "", 1)

        if config.sections["words"]["censorwords"] and username != core.users.login_username:
            msg.message = message = censor_text(message, censored_patterns=config.sections["words"]["censored"])

        if config.sections["logging"]["chatrooms"] or room_name in config.sections["logging"]["rooms"]:
            if is_action_message:
                formatted_message = f"* {username} {message}"
            else:
                formatted_message = f"[{username}] {message}"

            if is_global:
                formatted_message = f"{msg.room_name} | {formatted_message}"

            log.write_log_file(
                folder_path=log.room_folder_path,
                basename=room_name, text=formatted_message
            )

        if is_global:
            core.pluginhandler.public_room_message_notification(msg.room_name, username, msg.message)
        else:
            core.pluginhandler.incoming_public_chat_notification(room_name, username, msg.message)

    def _user_joined_room(self, msg):
        """Server code 16."""

        room_name = msg.room_name
        room = self.joined_rooms.get(room_name)

        if room is None or not room.users:
            raise StopEventPropagation()

        self._update_room_user(room, msg.stats)
        core.pluginhandler.user_join_chatroom_notification(room_name, msg.username)

    def _user_left_room(self, msg):
        """Server code 17."""

        room_name = msg.room_name
        room = self.joined_rooms.get(room_name)

        if room is None or not room.users:
            raise StopEventPropagation()

        username = msg.username
        room.users.discard(username)
        core.users.unwatch_user(username, context=f"chatrooms_{room_name}")

        core.pluginhandler.user_leave_chatroom_notification(room_name, username)

    def _room_tickers(self, msg):
        """Server code 113."""

        room = self.joined_rooms.get(msg.room_name)

        if room is None or not room.users:
            raise StopEventPropagation()

        room.tickers.clear()

        for ticker in msg.tickers:
            if core.network_filter.is_user_ignored(ticker.username) or \
                    core.network_filter.is_user_ip_ignored(ticker.username):
                # User ignored, ignore ticker message
                continue

            room.tickers[ticker.username] = ticker.content

    def _room_ticker_added(self, msg):
        """Server code 114."""

        room = self.joined_rooms.get(msg.room_name)

        if room is None or not room.users:
            raise StopEventPropagation()

        ticker = msg.ticker
        username = ticker.username

        if core.network_filter.is_user_ignored(username) or core.network_filter.is_user_ip_ignored(username):
            # User ignored, ignore Ticker messages
            return

        room.tickers[username] = ticker.content

    def _room_ticker_removed(self, msg):
        """Server code 115."""

        room = self.joined_rooms.get(msg.room_name)

        if room is None or not room.users:
            raise StopEventPropagation()

        room.tickers.pop(msg.username, None)

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
