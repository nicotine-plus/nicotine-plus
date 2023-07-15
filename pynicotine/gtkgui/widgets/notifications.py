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

import os
import sys

from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GLib

from pynicotine.config import config
from pynicotine.events import events
from pynicotine.logfacility import log


class Notifications:

    def __init__(self, application):

        self.application = application

        for event_name, callback in (
            ("show-notification", self._show_notification),
            ("show-chatroom-notification", self._show_chatroom_notification),
            ("show-download-notification", self._show_download_notification),
            ("show-private-chat-notification", self._show_private_chat_notification),
            ("show-search-notification", self._show_search_notification)
        ):
            events.connect(event_name, callback)

    def update_title(self):

        notification_text = ""

        if not config.sections["notifications"]["notification_window_title"]:
            # Reset Title
            pass

        elif self.application.window.privatechat.highlighted_users:
            # Private Chats have a higher priority
            user = self.application.window.privatechat.highlighted_users[-1]
            notification_text = _("Private Message from %(user)s") % {"user": user}

        elif self.application.window.chatrooms.highlighted_rooms:
            # Allow for the possibility the username is not available
            room, user = list(self.application.window.chatrooms.highlighted_rooms.items())[-1]
            notification_text = _("Mentioned by %(user)s in Room %(room)s") % {"user": user, "room": room}

        elif any(is_important for is_important in self.application.window.search.unread_pages.values()):
            notification_text = _("Wishlist Results Found")

        self.set_urgency_hint(bool(notification_text))

        if not notification_text:
            self.application.window.set_title(config.application_name)
            return

        self.application.window.set_title(f"{config.application_name} - {notification_text}")

    def set_urgency_hint(self, enabled):

        surface = self.application.window.get_surface()
        is_active = self.application.window.is_active()

        try:
            surface.set_urgency_hint(enabled and not is_active)

        except AttributeError:
            # No support for urgency hints
            pass

    def _show_notification(self, message, title=None, action=None, action_target=None, high_priority=False):

        if title is None:
            title = config.application_name

        title = title.strip()
        message = message.strip()

        try:
            if sys.platform == "win32":
                self.application.tray_icon.show_notification(title=title, message=message)
                return

            priority = Gio.NotificationPriority.HIGH if high_priority else Gio.NotificationPriority.NORMAL

            notification = Gio.Notification.new(title)
            notification.set_body(message)
            notification.set_priority(priority)

            # Unity doesn't support default click actions, and replaces the notification with a dialog.
            # Disable actions to prevent this from happening.
            if action and os.environ.get("XDG_SESSION_DESKTOP") != "unity":
                if action_target:
                    notification.set_default_action_and_target(action, GLib.Variant("s", action_target))
                else:
                    notification.set_default_action(action)

            self.application.send_notification(event_id=None, notification=notification)

            if config.sections["notifications"]["notification_popup_sound"]:
                Gdk.Display.get_default().beep()

        except Exception as error:
            log.add(_("Unable to show notification: %s"), str(error))

    def _show_chatroom_notification(self, room, message, title=None, high_priority=False):
        self._show_notification(
            message, title, action="app.chatroom-notification-activated", action_target=room,
            high_priority=high_priority)

    def _show_download_notification(self, message, title=None, high_priority=False):
        self._show_notification(
            message, title, action="app.download-notification-activated", high_priority=high_priority)

    def _show_private_chat_notification(self, user, message, title=None):
        self._show_notification(
            message, title, action="app.private-chat-notification-activated", action_target=user, high_priority=True)

    def _show_search_notification(self, search_token, message, title=None):
        self._show_notification(
            message, title, action="app.search-notification-activated", action_target=search_token, high_priority=True)
