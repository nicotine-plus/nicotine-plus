# COPYRIGHT (C) 2020-2022 Nicotine+ Team
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

import time

from pynicotine import slskmessages
from pynicotine.utils import get_completion_list


class PrivateChats:

    # List of allowed commands
    CMDS = {
        "/al ", "/alias ", "/un ", "/unalias ", "/w ", "/whois ", "/browse ", "/b ", "/ip ", "/pm ", "/m ", "/msg ",
        "/s ", "/search ", "/us ", "/usearch ", "/rs ", "/rsearch ", "/bs ", "/bsearch ", "/j ", "/join ",
        "/ad ", "/add ", "/buddy ", "/rem ", "/unbuddy ", "/ban ", "/ignore ", "/ignoreip ", "/unban ",
        "/unignore ", "/c ", "/close ", "/clear ", "/cl ", "/me ", "/a ", "/away ", "/q ", "/quit ", "/exit ",
        "/now ", "/rescan ", "/info ", "/toggle ", "/ctcpversion "
    }

    CTCP_VERSION = "\x01VERSION\x01"

    def __init__(self, core, config, queue, ui_callback=None):

        self.core = core
        self.config = config
        self.queue = queue
        self.completion_list = []
        self.private_message_queue = {}
        self.automatic_message_times = {}
        self.users = set()
        self.ui_callback = None

        if hasattr(ui_callback, "privatechat"):
            self.ui_callback = ui_callback.privatechat

    def server_login(self):

        for user in self.users:
            self.core.watch_user(user)  # Get notified of user status

        if self.ui_callback:
            self.ui_callback.server_login()

    def server_disconnect(self):
        if self.ui_callback:
            self.ui_callback.server_disconnect()

    def add_user(self, user):

        if user in self.users:
            return

        self.users.add(user)
        self.store_user(user)
        self.core.watch_user(user)

    def store_user(self, user):

        if user not in self.config.sections["privatechat"]["users"]:
            self.config.sections["privatechat"]["users"].append(user)

    def remove_user(self, user):

        if user in self.config.sections["privatechat"]["users"]:
            self.config.sections["privatechat"]["users"].remove(user)

        self.users.remove(user)

    def show_user(self, user, switch_page=True):

        self.add_user(user)

        if self.ui_callback:
            self.ui_callback.show_user(user, switch_page)

    def load_users(self):

        if not self.config.sections["privatechat"]["store"]:
            # Clear list of previously open chats if we don't want to restore them
            self.config.sections["privatechat"]["users"].clear()
            return

        for user in self.config.sections["privatechat"]["users"]:
            if isinstance(user, str) and user not in self.users:
                self.show_user(user, switch_page=False)

        self.update_completions()

    def set_log_config(self, user, log_active):

        if log_active:
            if user not in self.config.sections["logging"]["private_users"]:
                self.config.sections["logging"]["private_users"].append(user)
        else:
            if user in self.config.sections["logging"]["private_users"]:
                self.config.sections["logging"]["private_users"].remove(user)

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

    def send_automatic_message(self, user, message):
        """ Sends a private message with the prefix 'Automatic Message' to a user.
        No message is sent if less than five seconds have passed since the last one. """

        send_time = time.time()

        if user in self.automatic_message_times and (send_time - self.automatic_message_times[user]) < 5:
            return

        self.queue.append(slskmessages.MessageUser(user, "[Automatic Message] " + message))
        self.automatic_message_times[user] = send_time

    def echo_message(self, user, message, message_type="local"):
        if self.ui_callback:
            self.ui_callback.echo_message(user, message, message_type)

    def send_message(self, user, message):

        user_text = self.core.pluginhandler.outgoing_private_chat_event(user, message)
        if user_text is None:
            return

        user, message = user_text

        if message == self.CTCP_VERSION:
            ui_message = "CTCP VERSION"
        else:
            message = ui_message = self.auto_replace(message)

        self.queue.append(slskmessages.MessageUser(user, message))
        self.core.pluginhandler.outgoing_private_chat_notification(user, message)

        if self.ui_callback:
            self.ui_callback.send_message(user, ui_message)

    def get_user_status(self, msg):
        if self.ui_callback:
            self.ui_callback.get_user_status(msg)

    def message_user(self, msg):

        self.queue.append(slskmessages.MessageAcked(msg.msgid))

        if msg.user != "server":
            # Check ignore status for all other users except "server"
            if self.core.network_filter.is_user_ignored(msg.user):
                return

            user_address = self.core.protothread.user_addresses.get(msg.user)

            if user_address is not None:
                ip_address, _port = user_address
                if self.core.network_filter.is_ip_ignored(ip_address):
                    return

            elif msg.newmessage:
                self.queue.append(slskmessages.GetPeerAddress(msg.user))
                self.private_message_queue_add(msg)
                return

        user_text = self.core.pluginhandler.incoming_private_chat_event(msg.user, msg.msg)
        if user_text is None:
            return

        self.show_user(msg.user, switch_page=False)

        _, msg.msg = user_text
        msg.msg = self.censor_chat(msg.msg)

        # SEND CLIENT VERSION to user if the following string is sent
        ctcpversion = False
        if msg.msg == self.CTCP_VERSION:
            ctcpversion = True
            msg.msg = "CTCP VERSION"

        if self.ui_callback:
            self.ui_callback.message_user(msg)

        self.core.pluginhandler.incoming_private_chat_notification(msg.user, msg.msg)

        if ctcpversion and not self.config.sections["server"]["ctcpmsgs"]:
            self.send_message(msg.user, "%s %s" % (self.config.application_name, self.config.version))

        autoreply = self.config.sections["server"]["autoreply"]

        if self.core.away and msg.user not in self.automatic_message_times and autoreply:
            self.send_automatic_message(msg.user, autoreply)

    def update_completions(self):

        self.completion_list = get_completion_list(self.CMDS, self.core.chatrooms.server_rooms)

        if self.ui_callback:
            self.ui_callback.set_completion_list(self.completion_list)
