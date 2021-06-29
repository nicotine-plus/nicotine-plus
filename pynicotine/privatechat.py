# COPYRIGHT (C) 2020-2021 Nicotine+ Team
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
from pynicotine.utils import get_completion_list


class PrivateChats:

    # List of allowed commands
    CMDS = {
        "/al ", "/alias ", "/un ", "/unalias ", "/w ", "/whois ", "/browse ", "/b ", "/ip ", "/pm ", "/m ", "/msg ",
        "/s ", "/search ", "/us ", "/usearch ", "/rs ", "/rsearch ", "/bs ", "/bsearch ", "/j ", "/join ",
        "/ad ", "/add ", "/buddy ", "/rem ", "/unbuddy ", "/ban ", "/ignore ", "/ignoreip ", "/unban ",
        "/unignore ", "/clear ", "/cl ", "/me ", "/a ", "/away ", "/q ", "/quit ", "/exit ", "/now ", "/rescan ",
        "/info ", "/toggle ", "/ctcpversion "
    }

    CTCP_VERSION = "\x01VERSION\x01"

    def __init__(self, np, config, queue, ui_callback=None):

        self.np = np
        self.config = config
        self.queue = queue
        self.completion_list = []
        self.private_message_queue = {}
        self.users = {}
        self.ui_callback = None

        if hasattr(ui_callback, "privatechats"):
            self.ui_callback = ui_callback.privatechats

        # Clear list of previously open chats if we don't want to restore them
        if not config.sections["privatechat"]["store"]:
            config.sections["privatechat"]["users"].clear()

    def server_login(self):

        for user in self.users:
            self.np.watch_user(user)  # Get notified of user status

        if not self.config.sections["privatechat"]["store"]:
            return

        for user in self.config.sections["privatechat"]["users"]:
            if isinstance(user, str) and user not in self.users:
                self.show_user(user, switch_page=False)

    def add_user(self, user):

        if user in self.users:
            return

        self.np.watch_user(user)
        self.users[user] = {"autoreplied": False}

        if user not in self.config.sections["privatechat"]["users"]:
            self.config.sections["privatechat"]["users"].append(user)

    def remove_user(self, user):

        if user in self.config.sections["privatechat"]["users"]:
            self.config.sections["privatechat"]["users"].remove(user)

        del self.users[user]

    def show_user(self, user, switch_page=False):

        self.add_user(user)

        if self.ui_callback:
            self.ui_callback.show_user(user, switch_page)

    def auto_replace(self, message):

        if self.config.sections["words"]["replacewords"]:
            autoreplaced = self.config.sections["words"]["autoreplaced"]

            for word, replacement in autoreplaced.items():
                message = message.replace(str(word), str(replacement))

        return message

    def censor_chat(self, message):

        if self.config.sections["words"]["censorwords"]:
            filler = self.config.sections["words"]["censorfill"]
            censored = self.config.sections["words"]["censored"]

            for word in censored:
                word = str(word)
                message = message.replace(word, filler * len(word))

        return message

    def private_message_queue_add(self, msg):

        user = msg.user

        if user not in self.private_message_queue:
            self.private_message_queue[user] = [msg]
        else:
            self.private_message_queue[user].append(msg)

    def private_message_queue_process(self, user):

        if user not in self.private_message_queue:
            return

        for msg in self.private_message_queue[user][:]:
            self.private_message_queue[user].remove(msg)
            self.message_user(msg)

    def echo_message(self, user, text):
        if self.ui_callback:
            self.ui_callback.echo_message(user, text)

    def send_message(self, user, text, bytestring=False):

        if not self.np.active_server_conn:
            return

        user_text = self.np.pluginhandler.outgoing_private_chat_event(user, text)
        if user_text is None:
            return

        _, text = user_text

        if bytestring:
            payload = text
        else:
            payload = self.auto_replace(text)

        self.queue.append(slskmessages.MessageUser(user, payload))
        self.np.pluginhandler.outgoing_private_chat_notification(user, text)

        if self.ui_callback:
            self.ui_callback.send_message(user, payload)

    def get_user_status(self, msg):
        if self.ui_callback:
            self.ui_callback.get_user_status(msg)

    def message_user(self, msg):

        self.queue.append(slskmessages.MessageAcked(msg.msgid))

        if self.np.network_filter.is_user_ignored(msg.user):
            return

        if msg.user in self.np.users and isinstance(self.np.users[msg.user].addr, tuple):
            ip_address, _port = self.np.users[msg.user].addr
            if self.np.network_filter.is_ip_ignored(ip_address):
                return

        elif msg.newmessage:
            self.queue.append(slskmessages.GetPeerAddress(msg.user))
            self.private_message_queue_add(msg)
            return

        user_text = self.np.pluginhandler.incoming_private_chat_event(msg.user, msg.msg)
        if user_text is None:
            return

        _, msg.msg = user_text
        msg.msg = self.censor_chat(msg.msg)

        # SEND CLIENT VERSION to user if the following string is sent
        ctcpversion = 0
        if msg.msg == self.CTCP_VERSION:
            ctcpversion = 1
            msg.msg = "CTCP VERSION"

        self.np.pluginhandler.incoming_private_chat_notification(msg.user, msg.msg)

        if self.ui_callback:
            self.ui_callback.message_user(msg)

        autoreply = self.config.sections["server"]["autoreply"]

        if self.np.away and not self.users[msg.user]["autoreplied"] and autoreply:
            self.send_message(msg.user, "[Auto-Message] %s" % autoreply)
            self.users[msg.user]["autoreplied"] = True

        self.np.notifications.new_tts(
            self.config.sections["ui"]["speechprivate"], {
                "user": msg.user,
                "message": msg.msg
            }
        )

        if ctcpversion and self.config.sections["server"]["ctcpmsgs"] == 0:
            self.send_message(msg.user, "Nicotine+ " + self.config.version)

    def update_completions(self):

        chatrooms = []

        if self.ui_callback:
            chatrooms = self.ui_callback.frame.chatrooms.roomlist.server_rooms

        self.completion_list = get_completion_list(self.CMDS, chatrooms)

        if self.ui_callback:
            self.ui_callback.set_completion_list(self.completion_list)
