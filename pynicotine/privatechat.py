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

import pynicotine
from pynicotine import slskmessages
from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.logfacility import log


class PrivateChat:

    CTCP_VERSION = "\x01VERSION\x01"

    def __init__(self):

        self.completions = set()
        self.private_message_queue = {}
        self.away_message_users = set()
        self.users = set()

        # Clear list of previously open chats if we don't want to restore them
        if not config.sections["privatechat"]["store"]:
            config.sections["privatechat"]["users"].clear()

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
            core.watch_user(username)  # Get notified of user status

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
        events.emit("private-chat-remove-user", username)

    def remove_all_users(self, is_permanent=True):
        for username in self.users.copy():
            self.remove_user(username, is_permanent)

    def show_user(self, username, switch_page=True, remembered=False):

        self.add_user(username)
        events.emit("private-chat-show-user", username, switch_page, remembered)
        core.watch_user(username)

    def clear_private_messages(self, username):
        events.emit("clear-private-messages", username)

    def auto_replace(self, message):

        if config.sections["words"]["replacewords"]:
            autoreplaced = config.sections["words"]["autoreplaced"]

            for word, replacement in autoreplaced.items():
                message = message.replace(str(word), str(replacement))

        return message

    def censor_chat(self, message):

        if config.sections["words"]["censorwords"]:
            filler = "*"
            censored = config.sections["words"]["censored"]

            for word in censored:
                word = str(word)
                message = message.replace(word, filler * len(word))

        return message

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

        if message == self.CTCP_VERSION:
            ui_message = "CTCP VERSION"
        else:
            message = ui_message = self.auto_replace(message)

        core.send_message_to_server(slskmessages.MessageUser(username, message))
        core.pluginhandler.outgoing_private_chat_notification(username, message)

        events.emit("send-private-message", username, ui_message)

    def send_message_users(self, target, message):

        if not message:
            return

        users = None

        if target == "buddies":
            users = set(core.userlist.buddies)

        elif target == "downloading":
            users = core.uploads.get_downloading_users()

        if users:
            core.send_message_to_server(slskmessages.MessageUsers(users, message))

    def _get_peer_address(self, msg):
        """Server code 3.

        Received a user's IP address, process any queued private
        messages and check if the IP is ignored
        """

        username = msg.user

        if username not in self.private_message_queue:
            return

        for msg_obj in self.private_message_queue[username][:]:
            self.private_message_queue[username].remove(msg_obj)
            msg_obj.user = username
            events.emit("message-user", msg_obj, queued_message=True)

    def _user_status(self, msg):
        """Server code 7."""

        if msg.user == core.login_username and msg.status != slskmessages.UserStatus.AWAY:
            # Reset list of users we've sent away messages to when the away session ends
            self.away_message_users.clear()

        if msg.status == slskmessages.UserStatus.OFFLINE:
            self.private_message_queue.pop(msg.user, None)

    def _message_user(self, msg, queued_message=False):
        """Server code 22."""

        username = msg.user
        message = msg.msg

        if not queued_message:
            log.add_chat(_("Private message from user '%(user)s': %(message)s"), {
                "user": username,
                "message": message
            })

            core.send_message_to_server(slskmessages.MessageAcked(msg.msgid))

        if username == "server":
            start_str = "The room you are trying to enter ("

            if message.startswith(start_str) and ") " in message:
                # Redirect message to chat room tab if join wasn't successful
                msg.user = None
                room = message[len(start_str):message.rfind(") ")]
                events.emit("say-chat-room", slskmessages.SayChatroom(room=room, msg=message, user=username))
                return
        else:
            # Check ignore status for all other users except "server"
            if core.network_filter.is_user_ignored(username):
                msg.user = None
                return

            user_address = core.user_addresses.get(username)

            if user_address is not None:
                if core.network_filter.is_user_ip_ignored(username):
                    msg.user = None
                    return

            elif not queued_message:
                # Ask for user's IP address and queue the private message until we receive the address
                if username not in self.private_message_queue:
                    core.request_ip_address(username)

                self.private_message_queue_add(msg)
                msg.user = None
                return

        user_text = core.pluginhandler.incoming_private_chat_event(username, message)
        if user_text is None:
            msg.user = None
            return

        self.show_user(username, switch_page=False)

        _username, msg.msg = user_text
        msg.msg = message = self.censor_chat(msg.msg)

        # SEND CLIENT VERSION to user if the following string is sent
        ctcpversion = False
        if message == self.CTCP_VERSION:
            ctcpversion = True
            msg.msg = message = "CTCP VERSION"

        core.pluginhandler.incoming_private_chat_notification(username, message)

        if ctcpversion and not config.sections["server"]["ctcpmsgs"]:
            self.send_message(username, f"{pynicotine.__application_name__} {pynicotine.__version__}")

        if not msg.newmessage:
            # Message was sent while offline, don't auto-reply
            return

        autoreply = config.sections["server"]["autoreply"]

        if autoreply and core.user_status == slskmessages.UserStatus.AWAY and username not in self.away_message_users:
            self.send_automatic_message(username, autoreply)
            self.away_message_users.add(username)

    def update_completions(self):

        self.completions.clear()
        self.completions.add(config.sections["server"]["login"])

        if config.sections["words"]["roomnames"]:
            self.completions.update(core.chatrooms.server_rooms)

        if config.sections["words"]["buddies"]:
            self.completions.update(core.userlist.buddies)

        if config.sections["words"]["commands"]:
            self.completions.update(core.pluginhandler.get_command_list("private_chat"))

        events.emit("private-chat-completions", self.completions.copy())
