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

from pynicotine.events import events


class Notifications:
    __slots__ = ()

    def show_notification(self, message, title=None):
        events.emit("show-notification", message, title=title)

    def show_chatroom_notification(self, room, message, title=None, high_priority=False):
        events.emit("show-chatroom-notification", room, message, title=title, high_priority=high_priority)

    def show_download_notification(self, message, title=None, high_priority=False):
        events.emit("show-download-notification", message, title=title, high_priority=high_priority)

    def show_private_chat_notification(self, username, message, title=None):
        events.emit("show-private-chat-notification", username, message, title=title)

    def show_search_notification(self, search_token, message, title=None):
        events.emit("show-search-notification", search_token, message, title=title)

    def show_upload_notification(self, message, title=None):
        events.emit("show-upload-notification", message, title=title)
