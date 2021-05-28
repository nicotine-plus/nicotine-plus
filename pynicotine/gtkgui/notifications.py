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

import sys
import textwrap
import threading
import time

from ctypes import Structure, sizeof

from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk

from pynicotine.config import config
from pynicotine.logfacility import log
from pynicotine.utils import execute_command


class Notifications:

    def __init__(self, frame):

        self.frame = frame
        self.application = Gio.Application.get_default()
        self.tts = []
        self.tts_playing = False
        self.continue_playing = False

        if sys.platform == "win32":
            self.win_notification = WinNotify(self.frame.tray_icon)

    def add(self, location, user, room=None):

        if location == "rooms" and room is not None and user is not None:
            if room not in self.frame.hilites[location]:
                self.frame.hilites[location].append(room)
                self.frame.tray_icon.set_image()

        elif location == "private":
            if user in self.frame.hilites[location]:
                self.frame.hilites[location].remove(user)
                self.frame.hilites[location].append(user)

            elif user not in self.frame.hilites[location]:
                self.frame.hilites[location].append(user)
                self.frame.tray_icon.set_image()

        if Gtk.get_major_version() == 3 and config.sections["ui"]["urgencyhint"] and \
                not self.frame.MainWindow.is_active():
            self.frame.MainWindow.set_urgency_hint(True)

        self.set_title(user)

    def clear(self, location, user=None, room=None):

        if location == "rooms" and room is not None:
            if room in self.frame.hilites["rooms"]:
                self.frame.hilites["rooms"].remove(room)

            self.set_title(room)

        elif location == "private":
            if user in self.frame.hilites["private"]:
                self.frame.hilites["private"].remove(user)

            self.set_title(user)

        self.frame.tray_icon.set_image()

    def set_title(self, user=None):

        app_name = GLib.get_application_name()

        if not self.frame.hilites["rooms"] and not self.frame.hilites["private"]:
            # Reset Title
            self.frame.MainWindow.set_title(app_name)
            return

        if not config.sections["notifications"]["notification_window_title"]:
            return

        if self.frame.hilites["private"]:
            # Private Chats have a higher priority
            user = self.frame.hilites["private"][-1]

            self.frame.MainWindow.set_title(
                app_name + " - " + _("Private Message from %(user)s") % {'user': user}
            )

        elif self.frame.hilites["rooms"]:
            # Allow for the possibility the username is not available
            room = self.frame.hilites["rooms"][-1]

            if user is None:
                self.frame.MainWindow.set_title(
                    app_name + " - " + _("You've been mentioned in the %(room)s room") % {'room': room}
                )
            else:
                self.frame.MainWindow.set_title(
                    app_name + " - " + _("%(user)s mentioned you in the %(room)s room") % {'user': user, 'room': room}
                )

    def new_tts(self, message):

        if not config.sections["ui"]["speechenabled"]:
            return

        if message in self.tts:
            return

        self.tts.append(message)

        if self.tts_playing:
            # Avoid spinning up useless threads
            self.continue_playing = True
            return

        thread = threading.Thread(target=self.play_tts)
        thread.name = "TTS"
        thread.daemon = True
        thread.start()

    def play_tts(self):

        for message in self.tts[:]:
            self.tts_player(message)

            if message in self.tts:
                self.tts.remove(message)

        self.tts_playing = False
        if self.continue_playing:
            self.continue_playing = False
            self.play_tts()

    def tts_clean(self, message):

        for i in ["_", "[", "]", "(", ")"]:
            message = message.replace(i, " ")

        return message

    def tts_player(self, message):

        self.tts_playing = True

        try:
            execute_command(config.sections["ui"]["speechcommand"], message, background=False)

        except Exception as error:
            log.add(_("Text-to-speech for message failed: %s"), str(error))

    def new_notification(self, message, title=None, priority=Gio.NotificationPriority.NORMAL):

        if title is None:
            title = GLib.get_application_name()

        try:
            if sys.platform == "win32":
                self.win_notification.notify(
                    title=title,
                    message=message
                )

                if config.sections["notifications"]["notification_popup_sound"]:
                    import winsound
                    winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS)

                return

            notification_popup = Gio.Notification.new(title)
            notification_popup.set_body(message)

            if self.frame.images["notify"]:
                notification_popup.set_icon(self.frame.images["notify"])

            notification_popup.set_priority(priority)

            self.application.send_notification(None, notification_popup)

            if config.sections["notifications"]["notification_popup_sound"]:
                Gdk.beep()

        except Exception as error:
            log.add(_("Unable to show notification popup: %s"), str(error))


class WinNotify:
    """ Implements a Windows balloon tip for GtkStatusIcon """

    NIF_INFO = NIIF_NOSOUND = 0x10
    NIM_MODIFY = 1

    def __init__(self, tray_icon):

        from ctypes import windll
        from ctypes.wintypes import DWORD, HICON, HWND, UINT, WCHAR

        class NOTIFYICONDATA(Structure):
            _fields_ = [
                ("cbSize", DWORD),
                ("hWnd", HWND),
                ("uID", UINT),
                ("uFlags", UINT),
                ("uCallbackMessage", UINT),
                ("hIcon", HICON),
                ("szTip", WCHAR * 128),
                ("dwState", DWORD),
                ("dwStateMask", DWORD),
                ("szInfo", WCHAR * 256),
                ("uVersion", UINT),
                ("szInfoTitle", WCHAR * 64),
                ("dwInfoFlags", DWORD)
            ]

        self.tray_icon = tray_icon
        self.queue = []
        self.worker = None

        self.nid = NOTIFYICONDATA()
        self.nid.cbSize = sizeof(NOTIFYICONDATA)
        self.nid.hWnd = windll.user32.FindWindowW("gtkstatusicon-observer", None)
        self.nid.uFlags = self.NIF_INFO
        self.nid.dwInfoFlags = self.NIIF_NOSOUND

    def notify(self, **kwargs):

        self.queue.append(kwargs)

        if self.worker and self.worker.is_alive():
            return

        self.worker = threading.Thread(target=self.work)
        self.worker.name = "WinNotify"
        self.worker.daemon = True
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

        self.nid.szInfoTitle = textwrap.shorten(title, width=64, placeholder="...")
        self.nid.szInfo = textwrap.shorten(message, width=256, placeholder="...")

        windll.shell32.Shell_NotifyIconW(self.NIM_MODIFY, self.nid)
        time.sleep(timeout)

        if not has_tray_icon:
            self.tray_icon.hide()
