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

import os
import sys
import time

from ctypes import Structure, byref, sizeof
from threading import Thread

from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GLib

from pynicotine.config import config
from pynicotine.events import events
from pynicotine.logfacility import log
from pynicotine.utils import truncate_string_byte


class Notifications:

    def __init__(self, application):

        self.application = application

        if sys.platform == "win32":
            self.win_notification = WinNotify(self.application.tray_icon)

        for event_name, callback in (
            ("show-notification", self._show_notification),
            ("show-chatroom-notification", self._show_chatroom_notification),
            ("show-download-notification", self._show_download_notification),
            ("show-private-chat-notification", self._show_private_chat_notification),
            ("show-search-notification", self._show_search_notification)
        ):
            events.connect(event_name, callback)

    def update_title(self):

        app_name = config.application_name

        if (not self.application.window.chatrooms.highlighted_rooms
                and not self.application.window.privatechat.highlighted_users):
            # Reset Title
            self.application.window.set_title(app_name)
            return

        if not config.sections["notifications"]["notification_window_title"]:
            return

        if self.application.window.privatechat.highlighted_users:
            # Private Chats have a higher priority
            user = self.application.window.privatechat.highlighted_users[-1]
            notification_text = _("Private Message from %(user)s") % {"user": user}

            self.application.window.set_title(f"{app_name} - {notification_text}")

        elif self.application.window.chatrooms.highlighted_rooms:
            # Allow for the possibility the username is not available
            room, user = list(self.application.window.chatrooms.highlighted_rooms.items())[-1]
            notification_text = _("Mentioned by %(user)s in Room %(room)s") % {"user": user, "room": room}

            self.application.window.set_title(f"{app_name} - {notification_text}")

    def set_urgency_hint(self, enabled):

        surface = self.application.window.get_surface()

        try:
            surface.set_urgency_hint(enabled)

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
                self.win_notification.notify(
                    title=title,
                    message=message
                )

                if config.sections["notifications"]["notification_popup_sound"]:
                    import winsound  # pylint:disable=import-error
                    winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS)

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


class WinNotify:
    """ Implements a Windows balloon tip for GtkStatusIcon """

    NIF_INFO = NIIF_NOSOUND = 0x10
    NIM_MODIFY = 1

    def __init__(self, tray_icon):

        from ctypes import windll
        from ctypes.wintypes import DWORD, HICON, HWND, UINT, WCHAR

        class NOTIFYICONDATA(Structure):
            _fields_ = [
                ("cb_size", DWORD),
                ("h_wnd", HWND),
                ("u_id", UINT),
                ("u_flags", UINT),
                ("u_callback_message", UINT),
                ("h_icon", HICON),
                ("sz_tip", WCHAR * 128),
                ("dw_state", DWORD),
                ("dw_state_mask", DWORD),
                ("sz_info", WCHAR * 256),
                ("u_version", UINT),
                ("sz_info_title", WCHAR * 64),
                ("dw_info_flags", DWORD)
            ]

        self.tray_icon = tray_icon
        self.queue = []
        self.worker = None

        self.nid = NOTIFYICONDATA()
        self.nid.cb_size = sizeof(NOTIFYICONDATA)
        self.nid.h_wnd = windll.user32.FindWindowW("gtkstatusicon-observer", None)
        self.nid.u_flags = self.NIF_INFO
        self.nid.dw_info_flags = self.NIIF_NOSOUND
        self.nid.sz_info_title = ""
        self.nid.sz_info = ""

    def notify(self, **kwargs):

        self.queue.append(kwargs)

        if self.worker and self.worker.is_alive():
            return

        self.worker = Thread(target=self.work, name="WinNotify", daemon=True)
        self.worker.start()

    def work(self):

        while self.queue:
            kwargs = self.queue.pop(0)
            self._notify(**kwargs)

    def _notify(self, title="", message="", timeout=10):

        from ctypes import windll
        has_tray_icon = config.sections["ui"]["trayicon"]

        if not has_tray_icon:
            # Tray icon was disabled by the user. Enable it temporarily to show a notification.
            self.tray_icon.set_visible(True)

        # Need to account for the null terminated character appended to the message length by Windows
        self.nid.sz_info_title = truncate_string_byte(title, byte_limit=63, ellipsize=True)
        self.nid.sz_info = truncate_string_byte(message, byte_limit=255, ellipsize=True)

        windll.shell32.Shell_NotifyIconW(self.NIM_MODIFY, byref(self.nid))
        time.sleep(timeout)

        if not has_tray_icon:
            self.tray_icon.set_visible(False)
