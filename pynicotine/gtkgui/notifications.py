# COPYRIGHT (C) 2020 Nicotine+ Team
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
import gi
import sys
import _thread

from gettext import gettext as _

from gi.repository import GLib

from pynicotine.utils import executeCommand
from pynicotine.utils import version


class Notifications:

    def __init__(self, frame):
        try:
            # Notification support
            gi.require_version('Notify', '0.7')
            from gi.repository import Notify
            Notify.init("Nicotine+")
            self.notification_provider = Notify
        except (ImportError, ValueError):
            try:
                # Windows support via plyer
                from plyer import notification
                self.notification_provider = notification
            except (ImportError, ValueError):
                self.notification_provider = None

        self.frame = frame
        self.tts = []
        self.tts_playing = False
        self.continue_playing = False

    def Add(self, location, user, room=None, tab=True):

        if location == "rooms" and room is not None and user is not None:
            if room not in self.frame.hilites["rooms"]:
                self.frame.hilites["rooms"].append(room)

                self.frame.TrayApp.SetImage()
        elif location == "private":
            if user in self.frame.hilites[location]:
                self.frame.hilites[location].remove(user)
                self.frame.hilites[location].append(user)
            elif user not in self.frame.hilites[location]:
                self.frame.hilites[location].append(user)

                self.frame.TrayApp.SetImage()

        if tab and self.frame.np.config.sections["ui"]["urgencyhint"] and not self.frame.got_focus:
            self.frame.MainWindow.set_urgency_hint(True)

        self.SetTitle(user)

    def ClearPage(self, notebook, item):

        (page, label, window, focused) = item
        location = None

        if notebook is self.frame.ChatNotebook:
            location = "rooms"
            self.Clear(location, room=label)
        elif notebook is self.frame.PrivatechatNotebook:
            location = "private"
            self.Clear(location, user=label)

    def Clear(self, location, user=None, room=None):

        if location == "rooms" and room is not None:
            if room in self.frame.hilites["rooms"]:
                self.frame.hilites["rooms"].remove(room)
            self.SetTitle(room)
        elif location == "private":
            if user in self.frame.hilites["private"]:
                self.frame.hilites["private"].remove(user)
            self.SetTitle(user)

        self.frame.TrayApp.SetImage()

    def SetTitle(self, user=None):

        if self.frame.hilites["rooms"] == [] and self.frame.hilites["private"] == []:
            # Reset Title
            if self.frame.MainWindow.get_title() != _("Nicotine+") + " " + version:
                self.frame.MainWindow.set_title(_("Nicotine+") + " " + version)
        elif self.frame.np.config.sections["notifications"]["notification_window_title"]:
            # Private Chats have a higher priority
            if len(self.frame.hilites["private"]) > 0:
                user = self.frame.hilites["private"][-1]
                self.frame.MainWindow.set_title(
                    _("Nicotine+") + " " + version + " :: " + _("Private Message from %(user)s") % {'user': user}
                )
            # Allow for the possibility the username is not available
            elif len(self.frame.hilites["rooms"]) > 0:
                room = self.frame.hilites["rooms"][-1]
                if user is None:
                    self.frame.MainWindow.set_title(
                        _("Nicotine+") + " " + version + " :: " + _("You've been mentioned in the %(room)s room") % {'room': room}
                    )
                else:
                    self.frame.MainWindow.set_title(
                        _("Nicotine+") + " " + version + " :: " + _("%(user)s mentioned you in the %(room)s room") % {'user': user, 'room': room}
                    )

    def new_tts(self, message):

        if not self.frame.np.config.sections["ui"]["speechenabled"]:
            return

        if message not in self.tts:
            self.tts.append(message)
            _thread.start_new_thread(self.play_tts, ())

    def play_tts(self):

        if self.tts_playing:
            self.continue_playing = True
            return

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

        executeCommand(self.frame.np.config.sections["ui"]["speechcommand"], message)

    def NewNotificationPopup(self, message, title="Nicotine+", soundnamenotify="message-sent-instant", soundnamewin="SystemAsterisk"):

        if self.notification_provider is None:
            return

        try:
            notification_popup = self.notification_provider.Notification.new(title, message)
            notification_popup.set_hint("desktop-entry", GLib.Variant("s", "org.nicotine_plus.Nicotine"))

            if self.frame.np.config.sections["notifications"]["notification_popup_sound"]:
                notification_popup.set_hint("sound-name", GLib.Variant("s", soundnamenotify))

            notification_popup.set_image_from_pixbuf(self.frame.images["notify"])

            try:
                notification_popup.show()
            except Exception as error:
                self.frame.logMessage(_("Notification Error: %s") % str(error))
        except AttributeError:
            # Fall back to plyer

            self.notificationprovider.notify(
                app_name="Nicotine+",
                title=title,
                message=message
            )

            if sys.platform == "win32" and self.frame.np.config.sections["notifications"]["notification_popup_sound"]:
                import winsound
                winsound.PlaySound(soundnamewin, winsound.SND_ALIAS)
