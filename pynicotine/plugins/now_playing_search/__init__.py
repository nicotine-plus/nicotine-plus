# SPDX-FileCopyrightText: 2020-2023 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

from pynicotine.pluginsystem import BasePlugin


class Plugin(BasePlugin):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.np_format = None

    def outgoing_global_search_event(self, search_term):
        return (self.get_np(search_term),)

    def outgoing_room_search_event(self, room, search_term):
        return room, self.get_np(search_term)

    def outgoing_buddy_search_event(self, search_term):
        return (self.get_np(search_term),)

    def outgoing_user_search_event(self, users, search_term):
        return users, self.get_np(search_term)

    def get_np(self, search_term):
        self.np_format = search_term
        now_playing = self.core.now_playing.get_np(get_format=self.get_format)

        if now_playing:
            return now_playing

        return search_term

    def get_format(self):
        return self.np_format
