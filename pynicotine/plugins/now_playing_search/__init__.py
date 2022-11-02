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

from pynicotine.pluginsystem import BasePlugin


class Plugin(BasePlugin):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.np_format = None

    def outgoing_global_search_event(self, text):
        return (self.get_np(text),)

    def outgoing_room_search_event(self, rooms, text):
        return rooms, self.get_np(text)

    def outgoing_buddy_search_event(self, text):
        return (self.get_np(text),)

    def outgoing_user_search_event(self, users, text):
        return users, self.get_np(text)

    def get_np(self, text):
        self.np_format = text
        now_playing = self.core.now_playing.get_np(get_format=self.get_format)

        if now_playing:
            return now_playing

        return text

    def get_format(self):
        return self.np_format
