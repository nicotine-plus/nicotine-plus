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

from pynicotine.utils import get_completion_list


class ChatRooms:

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
        self.ui_callback = None

        if hasattr(ui_callback, "chatrooms"):
            self.ui_callback = ui_callback.chatrooms

    def echo_message(self, room, message, message_type):
        if self.ui_callback:
            self.ui_callback.echo_message(room, message, message_type)

    def get_user_stats(self, msg):
        if self.ui_callback:
            self.ui_callback.get_user_stats(msg)

    def join_room(self, msg):
        if self.ui_callback:
            self.ui_callback.join_room(msg)

    def leave_room(self, msg):
        if self.ui_callback:
            self.ui_callback.leave_room(msg)

    def get_user_status(self, msg):
        if self.ui_callback:
            self.ui_callback.get_user_status(msg)

    def private_room_users(self, msg):
        if self.ui_callback:
            self.ui_callback.private_room_users(msg)

    def private_room_add_user(self, msg):
        if self.ui_callback:
            self.ui_callback.private_room_add_user(msg)

    def private_room_remove_user(self, msg):
        if self.ui_callback:
            self.ui_callback.private_room_remove_user(msg)

    def private_room_disown(self, msg):
        if self.ui_callback:
            self.ui_callback.private_room_disown(msg)

    def private_room_added(self, msg):
        if self.ui_callback:
            self.ui_callback.private_room_added(msg)

    def private_room_removed(self, msg):
        if self.ui_callback:
            self.ui_callback.private_room_removed(msg)

    def private_room_toggle(self, msg):
        self.config.sections["server"]["private_chatrooms"] = msg.enabled

    def private_room_add_operator(self, msg):
        if self.ui_callback:
            self.ui_callback.private_room_add_operator(msg)

    def private_room_remove_operator(self, msg):
        if self.ui_callback:
            self.ui_callback.private_room_remove_operator(msg)

    def private_room_operator_added(self, msg):
        if self.ui_callback:
            self.ui_callback.private_room_operator_added(msg)

    def private_room_operator_removed(self, msg):
        if self.ui_callback:
            self.ui_callback.private_room_operator_removed(msg)

    def private_room_owned(self, msg):
        if self.ui_callback:
            self.ui_callback.private_room_owned(msg)

    def public_room_message(self, msg):
        if self.ui_callback:
            self.ui_callback.public_room_message(msg)

    def room_list(self, msg):
        if self.ui_callback:
            self.ui_callback.room_list(msg)

    def say_chat_room(self, msg):
        if self.ui_callback:
            self.ui_callback.say_chat_room(msg)

    def set_user_country(self, user, country):
        if self.ui_callback:
            self.ui_callback.set_user_country(user, country)

    def ticker_add(self, msg):
        if self.ui_callback:
            self.ui_callback.ticker_add(msg)

    def ticker_remove(self, msg):
        if self.ui_callback:
            self.ui_callback.ticker_remove(msg)

    def ticker_set(self, msg):
        if self.ui_callback:
            self.ui_callback.ticker_set(msg)

    def user_joined_room(self, msg):
        if self.ui_callback:
            self.ui_callback.user_joined_room(msg)

    def user_left_room(self, msg):
        if self.ui_callback:
            self.ui_callback.user_left_room(msg)

    def update_completions(self):

        chat_rooms = []

        if self.ui_callback:
            chat_rooms = self.ui_callback.frame.chatrooms.roomlist.server_rooms

        self.completion_list = get_completion_list(self.CMDS, chat_rooms)

        if self.ui_callback:
            self.ui_callback.set_completion_list(self.completion_list)


class Tickers:

    def __init__(self):

        self.messages = []

    def add_ticker(self, user, message):

        message = message.replace("\n", " ")
        self.messages.insert(0, [user, message])

    def remove_ticker(self, user):

        for i, message in enumerate(self.messages):
            if message[0] == user:
                del self.messages[i]
                return

    def get_tickers(self):
        return self.messages

    def set_ticker(self, msgs):
        self.messages = msgs
