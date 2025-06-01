# SPDX-FileCopyrightText: 2020-2025 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

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
