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

import sys
import time

from ctypes import Structure, byref, sizeof
from threading import Thread

from gi.repository import Gdk
from gi.repository import Gio

from pynicotine.config import config
from pynicotine.core import core
from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.logfacility import log
from pynicotine.utils import truncate_string_byte


class Notifications:

    def __init__(self, frame):

        self.frame = frame
        self.application = Gio.Application.get_default()

        if sys.platform == "win32":
            self.win_notification = WinNotify(self.frame.tray_icon)

    def add(self, location, user, room=None):

        item = room if location == "rooms" else user

        if core.notifications.add_hilite_item(location, item):
            self.frame.tray_icon.update_icon()

        if config.sections["ui"]["urgencyhint"] and not self.frame.window.is_active():
            self.set_urgency_hint(True)

        self.set_title(user)

    def clear(self, location, user=None, room=None):

        item = room if location == "rooms" else user

        if core.notifications.remove_hilite_item(location, item):
            self.set_title(item)
            self.frame.tray_icon.update_icon()

    def set_title(self, user=None):

        app_name = config.application_name

        if (not core.notifications.chat_hilites["rooms"]
                and not core.notifications.chat_hilites["private"]):
            # Reset Title
            self.frame.window.set_title(app_name)
            return

        if not config.sections["notifications"]["notification_window_title"]:
            return

        if core.notifications.chat_hilites["private"]:
            # Private Chats have a higher priority
            user = core.notifications.chat_hilites["private"][-1]

            self.frame.window.set_title(
                app_name + " - " + _("Private Message from %(user)s") % {'user': user}
            )

        elif core.notifications.chat_hilites["rooms"]:
            # Allow for the possibility the username is not available
            room = core.notifications.chat_hilites["rooms"][-1]

            if user is None:
                self.frame.window.set_title(
                    app_name + " - " + _("You've been mentioned in the %(room)s room") % {'room': room}
                )
            else:
                self.frame.window.set_title(
                    app_name + " - " + _("%(user)s mentioned you in the %(room)s room") % {'user': user, 'room': room}
                )

    def set_urgency_hint(self, enabled):

        if GTK_API_VERSION >= 4:
            surface = self.frame.window.get_surface()
        else:
            surface = self.frame.window.get_window()

        try:
            surface.set_urgency_hint(enabled)

        except AttributeError:
            # No support for urgency hints
            pass

    def new_text_notification(self, message, title=None, priority=Gio.NotificationPriority.NORMAL):

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

            notification_popup = Gio.Notification.new(title)
            notification_popup.set_body(message)
            notification_popup.set_priority(priority)

            self.application.send_notification(None, notification_popup)

            if config.sections["notifications"]["notification_popup_sound"]:
                Gdk.Display.get_default().beep()

        except Exception as error:
            log.add(_("Unable to show notification: %s"), str(error))


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
            self.tray_icon.show()

        # Need to account for the null terminated character appended to the message length by Windows
        self.nid.sz_info_title = truncate_string_byte(title, byte_limit=63, ellipsize=True)
        self.nid.sz_info = truncate_string_byte(message, byte_limit=255, ellipsize=True)

        windll.shell32.Shell_NotifyIconW(self.NIM_MODIFY, byref(self.nid))
        time.sleep(timeout)

        if not has_tray_icon:
            self.tray_icon.hide()
