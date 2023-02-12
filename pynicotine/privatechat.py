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
from pynicotine.slskmessages import UserStatus


class PrivateChat:

    def __init__(self):

        self.completion_list = []
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
            ("set-away-mode", self._set_away_mode),
            ("user-status", self._user_status)
        ):
            events.connect(event_name, callback)

    def _start(self):

        if not config.sections["privatechat"]["store"]:
            return

        for user in config.sections["privatechat"]["users"]:
            if isinstance(user, str) and user not in self.users:
                self.show_user(user, switch_page=False)

        self.update_completions()

    def _quit(self):
        self.completion_list.clear()
        self.users.clear()

    def _server_login(self, msg):

        if not msg.success:
            return

        for user in self.users:
            core.watch_user(user)  # Get notified of user status

    def _server_disconnect(self, _msg):
        self.private_message_queue.clear()
        self.away_message_users.clear()

    def _set_away_mode(self, is_away):

        if not is_away:
            # Reset list of users we've sent away messages to when the away session ends
            self.away_message_users.clear()

    def add_user(self, user):

        if user in self.users:
            return

        self.users.add(user)

        if user not in config.sections["privatechat"]["users"]:
            config.sections["privatechat"]["users"].append(user)

    def remove_user(self, user):

        if user in config.sections["privatechat"]["users"]:
            config.sections["privatechat"]["users"].remove(user)

        self.users.remove(user)
        events.emit("private-chat-remove-user", user)

    def show_user(self, user, switch_page=True):

        self.add_user(user)
        events.emit("private-chat-show-user", user, switch_page)
        core.watch_user(user)

    def clear_private_messages(self, user):
        events.emit("clear-private-messages", user)

    def auto_replace(self, message):

        if config.sections["words"]["replacewords"]:
            autoreplaced = config.sections["words"]["autoreplaced"]

            for word, replacement in autoreplaced.items():
                message = message.replace(str(word), str(replacement))

        return message

    def censor_chat(self, message):

        if config.sections["words"]["censorwords"]:
            filler = config.sections["words"]["censorfill"]
            censored = config.sections["words"]["censored"]

            for word in censored:
                word = str(word)
                message = message.replace(word, filler * len(word))

        return message

    def private_message_queue_add(self, msg):
        """ Queue a private message until we've received a user's IP address """

        user = msg.user

        if user not in self.private_message_queue:
            self.private_message_queue[user] = [msg]
        else:
            self.private_message_queue[user].append(msg)

    def send_automatic_message(self, user, message):
        self.send_message(user, f"[Automatic Message] {message}")

    def echo_message(self, user, message, message_type="local"):
        events.emit("echo-private-message", user, message, message_type)

    def send_message(self, user, message):

        user_text = core.pluginhandler.outgoing_private_chat_event(user, message)
        if user_text is None:
            return

        user, message = user_text

        if message.startswith("\x01") and message.endswith("\x01"):
            ui_message = f"CTCP {message[1:-1]}"
        else:
            message = ui_message = self.auto_replace(message)

        core.queue.append(slskmessages.MessageUser(user, message))
        core.pluginhandler.outgoing_private_chat_notification(user, message)

        events.emit("send-private-message", user, ui_message)

    def send_message_users(self, target, message):

        if not message:
            return

        users = None

        if target == "buddies":
            users = set(core.userlist.buddies)

        elif target == "downloading":
            users = core.transfers.get_downloading_users()

        if users:
            core.queue.append(slskmessages.MessageUsers(users, message))

    def _get_peer_address(self, msg):
        """ Server code: 3 """
        """ Received a user's IP address, process any queued private messages and check
        if the IP is ignored """

        user = msg.user

        if user not in self.private_message_queue:
            return

        for msg_obj in self.private_message_queue[user][:]:
            self.private_message_queue[user].remove(msg_obj)
            msg_obj.user = user
            events.emit("message-user", msg_obj, queued_message=True)

    def _user_status(self, msg):
        """ Server code: 7 """

        if msg.status == UserStatus.OFFLINE:
            self.private_message_queue.pop(msg.user, None)

    def _message_user(self, msg, queued_message=False):
        """ Server code: 22 """

        user = msg.user

        if not queued_message:
            log.add_chat(_("Private message from user '%(user)s': %(message)s"), {
                "user": user,
                "message": msg.msg
            })

            core.queue.append(slskmessages.MessageAcked(msg.msgid))

        if user != "server":
            # Check ignore status for all other users except "server"
            if core.network_filter.is_user_ignored(user):
                msg.user = None
                return

            user_address = core.user_addresses.get(user)

            if user_address is not None:
                if core.network_filter.is_user_ip_ignored(user):
                    msg.user = None
                    return

            elif not queued_message:
                # Ask for user's IP address and queue the private message until we receive the address
                if user not in self.private_message_queue:
                    core.queue.append(slskmessages.GetPeerAddress(user))

                self.private_message_queue_add(msg)
                msg.user = None
                return

        user_text = core.pluginhandler.incoming_private_chat_event(user, msg.msg)
        if user_text is None:
            msg.user = None
            return

        self.show_user(user, switch_page=False)

        _user, msg.msg = user_text
        msg.msg = self.censor_chat(msg.msg)
        ctcp_query = ctcp_reply = ""

        if msg.msg.startswith("\x01") and msg.msg.endswith("\x01"):
            ctcp_query = msg.msg[1:-1].strip()
            msg.msg = f"CTCP {ctcp_query}"

            if ctcp_query == "VERSION":
                ctcp_reply = f"{ctcp_query}: {config.application_name} {config.version}"
            else:
                ctcp_reply = f"ERRMSG {ctcp_query}: Unknown query, available CTCP keywords are VERSION"

        core.pluginhandler.incoming_private_chat_notification(user, msg.msg)

        if ctcp_reply and not config.sections["server"]["ctcpmsgs"]:
            self.send_message(user, ctcp_reply)

        if not msg.newmessage:
            # Message was sent while offline, don't auto-reply
            return

        autoreply = config.sections["server"]["autoreply"]

        if autoreply and core.user_status == UserStatus.AWAY and user not in self.away_message_users:
            self.send_automatic_message(user, autoreply)
            self.away_message_users.add(user)

    def update_completions(self):

        self.completion_list = [config.sections["server"]["login"]]

        if config.sections["words"]["roomnames"]:
            self.completion_list += core.chatrooms.server_rooms

        if config.sections["words"]["buddies"]:
            self.completion_list += list(core.userlist.buddies)

        if config.sections["words"]["commands"]:
            self.completion_list += list(core.pluginhandler.private_chat_commands)

        events.emit("private-chat-completion-list", self.completion_list)
