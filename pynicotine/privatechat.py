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

import pynicotine
from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.logfacility import log
from pynicotine.slskmessages import MessageAcked
from pynicotine.slskmessages import MessageUser
from pynicotine.slskmessages import MessageUsers
from pynicotine.slskmessages import SayChatroom
from pynicotine.slskmessages import UserStatus
from pynicotine.utils import censor_text
from pynicotine.utils import find_whole_word


class PrivateChat:
    __slots__ = ("completions", "private_message_queue", "away_message_users", "users")

    CTCP_VERSION = "\x01VERSION\x01"

    def __init__(self):

        self.completions = set()
        self.private_message_queue = {}
        self.away_message_users = set()
        self.users = set()

        for event_name, callback in (
            ("message-user", self._message_user),
            ("peer-address", self._get_peer_address),
            ("quit", self._quit),
            ("server-login", self._server_login),
            ("server-disconnect", self._server_disconnect),
            ("start", self._start),
            ("user-status", self._user_status)
        ):
            events.connect(event_name, callback)

    def _start(self):

        if not config.sections["privatechat"]["store"]:
            # Clear list of previously open chats if we don't want to restore them
            config.sections["privatechat"]["users"].clear()
            return

        for username in config.sections["privatechat"]["users"]:
            if isinstance(username, str) and username not in self.users:
                self.show_user(username, switch_page=False, remembered=True)

        self.update_completions()

    def _quit(self):
        self.remove_all_users(is_permanent=False)
        self.completions.clear()

    def _server_login(self, msg):

        if not msg.success:
            return

        for username in self.users:
            core.users.watch_user(username, context="privatechat")  # Get notified of user status

    def _server_disconnect(self, _msg):

        self.private_message_queue.clear()
        self.away_message_users.clear()
        self.update_completions()

    def add_user(self, username):

        if username in self.users:
            return

        self.users.add(username)

        if username not in config.sections["privatechat"]["users"]:
            config.sections["privatechat"]["users"].insert(0, username)

    def remove_user(self, username, is_permanent=True):

        if is_permanent and username in config.sections["privatechat"]["users"]:
            config.sections["privatechat"]["users"].remove(username)

        self.users.remove(username)
        core.users.unwatch_user(username, context="privatechat")
        events.emit("private-chat-remove-user", username)

    def remove_all_users(self, is_permanent=True):
        for username in self.users.copy():
            self.remove_user(username, is_permanent)

    def show_user(self, username, switch_page=True, remembered=False):

        self.add_user(username)
        events.emit("private-chat-show-user", username, switch_page, remembered)
        core.users.watch_user(username, context="privatechat")

    def clear_private_messages(self, username):
        events.emit("clear-private-messages", username)

    def private_message_queue_add(self, msg):
        """Queue a private message until we've received a user's IP address."""

        username = msg.user

        if username not in self.private_message_queue:
            self.private_message_queue[username] = [msg]
        else:
            self.private_message_queue[username].append(msg)

    def send_automatic_message(self, username, message):
        self.send_message(username, f"[Automatic Message] {message}")

    def echo_message(self, username, message, message_type="local"):
        events.emit("echo-private-message", username, message, message_type)

    def send_message(self, username, message):

        user_text = core.pluginhandler.outgoing_private_chat_event(username, message)
        if user_text is None:
            return

        username, message = user_text

        if config.sections["words"]["replacewords"] and message != self.CTCP_VERSION:
            for word, replacement in config.sections["words"]["autoreplaced"].items():
                message = message.replace(str(word), str(replacement))

        core.send_message_to_server(MessageUser(username, message))
        core.pluginhandler.outgoing_private_chat_notification(username, message)

        events.emit("message-user", MessageUser(username, message))

    def send_message_users(self, target, message):

        if not message:
            return

        users = None

        if target == "buddies":
            users = set(core.buddies.users)

        elif target == "downloading":
            users = core.uploads.get_downloading_users()

        if users:
            core.send_message_to_server(MessageUsers(users, message))

    def _get_peer_address(self, msg):
        """Server code 3.

        Received a user's IP address, process any queued private
        messages and check if the IP is ignored
        """

        username = msg.user

        if username not in self.private_message_queue:
            return

        for queued_msg in self.private_message_queue[username][:]:
            self.private_message_queue[username].remove(queued_msg)
            queued_msg.user = username
            events.emit("message-user", queued_msg, queued_message=True)

    def _user_status(self, msg):
        """Server code 7."""

        if msg.user == core.users.login_username and msg.status != UserStatus.AWAY:
            # Reset list of users we've sent away messages to when the away session ends
            self.away_message_users.clear()

        if msg.status == UserStatus.OFFLINE:
            self.private_message_queue.pop(msg.user, None)

    def get_message_type(self, text, is_outgoing_message):

        if text.startswith("/me "):
            return "action"

        if is_outgoing_message:
            return "local"

        if core.users.login_username and find_whole_word(core.users.login_username.lower(), text.lower()) > -1:
            return "hilite"

        return "remote"

    def _message_user(self, msg, queued_message=False):
        """Server code 22."""

        is_outgoing_message = (msg.message_id is None)

        username = msg.user
        tag_username = (core.users.login_username if is_outgoing_message else username)
        message = msg.message
        timestamp = msg.timestamp if not msg.is_new_message else None

        if not is_outgoing_message:
            if not queued_message:
                log.add_chat(_("Private message from user '%(user)s': %(message)s"), {
                    "user": username,
                    "message": message
                })

                core.send_message_to_server(MessageAcked(msg.message_id))

            if username == "server":
                start_str = "The room you are trying to enter ("

                if message.startswith(start_str) and ") " in message:
                    # Redirect message to chat room tab if join wasn't successful
                    msg.user = None
                    room = message[len(start_str):message.rfind(") ")]
                    events.emit("say-chat-room", SayChatroom(room=room, message=message, user=username))
                    return
            else:
                # Check ignore status for all other users except "server"
                if core.network_filter.is_user_ignored(username):
                    msg.user = None
                    return

                user_address = core.users.addresses.get(username)

                if user_address is not None:
                    if core.network_filter.is_user_ip_ignored(username):
                        msg.user = None
                        return

                elif not queued_message:
                    # Ask for user's IP address and queue the private message until we receive the address
                    if username not in self.private_message_queue:
                        core.users.request_ip_address(username)

                    self.private_message_queue_add(msg)
                    msg.user = None
                    return

            user_text = core.pluginhandler.incoming_private_chat_event(username, message)
            if user_text is None:
                msg.user = None
                return

            self.show_user(username, switch_page=False)

            _username, msg.message = user_text
            message = msg.message

        msg.message_type = self.get_message_type(message, is_outgoing_message)
        is_action_message = (msg.message_type == "action")
        is_ctcp_version = (message == self.CTCP_VERSION)

        # SEND CLIENT VERSION to user if the following string is sent
        if is_ctcp_version:
            msg.message = message = "CTCP VERSION"

        if is_action_message:
            message = message.replace("/me ", "", 1)

        if not is_outgoing_message and config.sections["words"]["censorwords"]:
            message = censor_text(message, censored_patterns=config.sections["words"]["censored"])

        if is_action_message:
            msg.formatted_message = msg.message = f"* {tag_username} {message}"
        else:
            msg.formatted_message = f"[{tag_username}] {message}"

        if config.sections["logging"]["privatechat"] or username in config.sections["logging"]["private_chats"]:
            log.write_log_file(
                folder_path=log.private_chat_folder_path,
                basename=username, text=msg.formatted_message, timestamp=timestamp
            )

        if is_outgoing_message:
            return

        core.pluginhandler.incoming_private_chat_notification(username, msg.message)

        if is_ctcp_version and not config.sections["server"]["ctcpmsgs"]:
            self.send_message(username, f"{pynicotine.__application_name__} {pynicotine.__version__}")

        if not msg.is_new_message:
            # Message was sent while offline, don't auto-reply
            return

        autoreply = config.sections["server"]["autoreply"]

        if (autoreply and core.users.login_status == UserStatus.AWAY
                and username not in self.away_message_users):
            self.send_automatic_message(username, autoreply)
            self.away_message_users.add(username)

    def update_completions(self):

        self.completions.clear()
        self.completions.add(config.sections["server"]["login"])

        if config.sections["words"]["roomnames"]:
            self.completions.update(core.chatrooms.server_rooms)

        if config.sections["words"]["buddies"]:
            self.completions.update(core.buddies.users)

        if config.sections["words"]["commands"]:
            self.completions.update(core.pluginhandler.get_command_list("private_chat"))

        events.emit("private-chat-completions", self.completions.copy())
