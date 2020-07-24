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
import glob
import os

from gettext import gettext as _

from pynicotine import slskmessages
from pynicotine.gtkgui.dialogs import ComboBoxDialog
from pynicotine.gtkgui.utils import PopupMenu
from pynicotine.logfacility import log
from pynicotine.utils import installPrefix


class TrayApp:

    def __init__(self, frame):
        try:
            # Check if AppIndicator3 is available
            gi.require_version('AppIndicator3', '0.1')
            from gi.repository import AppIndicator3  # noqa: F401
            self.appindicator = AppIndicator3
        except (ImportError, ValueError):
            # No AppIndicator3, Fall back to GtkStatusIcon
            from gi.repository import Gtk
            self.appindicator = None
            self.gtk = Gtk

        self.frame = frame
        self.trayicon = None
        self.tray_status = {
            "status": "trayicon_disconnect",
            "last": "trayicon_disconnect"
        }
        self.CreateMenu()

    def CreateMenu(self):
        try:
            self.tray_popup_menu_server = popup0 = PopupMenu(self, False)
            popup0.setup(
                ("#" + _("Connect"), self.frame.OnConnect),
                ("#" + _("Disconnect"), self.frame.OnDisconnect)
            )

            self.tray_popup_menu = popup = PopupMenu(self, False)
            popup.setup(
                ("#" + _("Hide / Show Nicotine+"), self.HideUnhideWindow),
                (1, _("Server"), self.tray_popup_menu_server, self.OnPopupServer),
                ("#" + _("Settings"), self.frame.OnSettings),
                ("#" + _("Send Message"), self.OnOpenPrivateChat),
                ("#" + _("Lookup a User's IP"), self.OnGetAUsersIP),
                ("#" + _("Lookup a User's Info"), self.OnGetAUsersInfo),
                ("#" + _("Lookup a User's Shares"), self.OnGetAUsersShares),
                ("$" + _("Toggle Away"), self.frame.OnAway),
                ("#" + _("Quit"), self.frame.OnExit)
            )
        except Exception as e:
            log.addwarning(_('ERROR: tray menu, %(error)s') % {'error': e})

    def OnOpenPrivateChat(self, widget, prefix=""):

        # popup
        users = []
        for entry in self.frame.np.config.sections["server"]["userlist"]:
            users.append(entry[0])

        users.sort()
        user = ComboBoxDialog(
            parent=self.frame.MainWindow,
            title=_('Nicotine+') + ": " + _("Start Messaging"),
            message=_('Enter the User who you wish to send a private message:'),
            droplist=users
        )

        if user is not None:
            self.frame.privatechats.SendMessage(user, None, 1)
            self.frame.ChangeMainPage(None, "private")

    def OnGetAUsersInfo(self, widget, prefix=""):

        # popup
        users = []
        for entry in self.frame.np.config.sections["server"]["userlist"]:
            users.append(entry[0])

        users.sort()
        user = ComboBoxDialog(
            parent=self.frame.MainWindow,
            title=_('Nicotine+') + ": " + _("Get User Info"),
            message=_('Enter the User whose User Info you wish to receive:'),
            droplist=users
        )

        if user is None:
            pass
        else:
            self.frame.LocalUserInfoRequest(user)

    def OnGetAUsersIP(self, widget, prefix=""):
        users = []
        for entry in self.frame.np.config.sections["server"]["userlist"]:
            users.append(entry[0])
        users.sort()
        user = ComboBoxDialog(
            parent=self.frame.MainWindow,
            title=_('Nicotine+') + ": " + _("Get A User's IP"),
            message=_('Enter the User whose IP Address you wish to receive:'),
            droplist=users
        )
        if user is None:
            pass
        else:
            self.frame.np.queue.put(slskmessages.GetPeerAddress(user))

    def OnGetAUsersShares(self, widget, prefix=""):
        users = []
        for entry in self.frame.np.config.sections["server"]["userlist"]:
            users.append(entry[0])
        users.sort()
        user = ComboBoxDialog(
            parent=self.frame.MainWindow,
            title=_('Nicotine+') + ": " + _("Get A User's Shares List"),
            message=_('Enter the User whose Shares List you wish to receive:'),
            droplist=users
        )
        if user is None:
            pass
        else:
            self.frame.BrowseUser(user)

    def OnPopupServer(self, widget):
        items = self.tray_popup_menu_server.get_children()

        if self.tray_status["status"] == "trayicon_disconnect":
            items[0].set_sensitive(True)
            items[1].set_sensitive(False)
        else:
            items[0].set_sensitive(False)
            items[1].set_sensitive(True)
        return

    # GtkStatusIcon fallback
    def OnStatusIconPopup(self, status_icon, button, activate_time):
        if button == 3:
            self.tray_popup_menu.popup(None, None, None, None, button, activate_time)

    def Create(self):
        self.Load()
        self.Draw()

    def Load(self):
        if self.trayicon is None:
            if self.appindicator is not None:
                trayicon = self.appindicator.Indicator.new(
                    "Nicotine+",
                    "",
                    self.appindicator.IndicatorCategory.APPLICATION_STATUS)
                trayicon.set_menu(self.tray_popup_menu)

                iconpath = self.frame.np.config.sections["ui"]["icontheme"]
                for iconname in ["trayicon_away", "trayicon_connect", "trayicon_disconnect", "trayicon_msg"]:
                    if not glob.glob(os.path.join(iconpath, iconname) + ".*"):
                        # Fall back to system-wide tray icon location
                        prefix = installPrefix()
                        iconpath = os.path.join(prefix, "share/nicotine/trayicons")
                        if not glob.glob(os.path.join(iconpath, iconname) + ".*"):
                            # Nicotine+ is not installed system-wide, load tray icons from current folder
                            iconpath = os.path.join(os.getcwd(), "img")
                            break
                        break

                trayicon.set_icon_theme_path(iconpath)
            else:
                # GtkStatusIcon fallback
                trayicon = self.gtk.StatusIcon()

            self.trayicon = trayicon

        if self.appindicator is not None:
            self.trayicon.set_status(self.appindicator.IndicatorStatus.ACTIVE)
        else:
            # GtkStatusIcon fallback
            self.trayicon.set_visible(True)

    def destroy_trayicon(self):
        if not self.IsTrayIconVisible():
            return

        if self.appindicator is not None:
            self.trayicon.set_status(self.appindicator.IndicatorStatus.PASSIVE)
        else:
            # GtkStatusIcon fallback
            self.trayicon.set_visible(False)

    def Draw(self):
        if not self.IsTrayIconVisible():
            return

        if self.appindicator is not None:
            # Action to hide/unhide main window when middle clicking the tray icon
            hide_unhide_item = self.tray_popup_menu.get_children()[0]
            self.trayicon.set_secondary_activate_target(hide_unhide_item)
        else:
            # GtkStatusIcon fallback
            self.trayicon.connect("activate", self.HideUnhideWindow)
            self.trayicon.connect("popup-menu", self.OnStatusIconPopup)

        self.SetImage(self.tray_status["status"])
        self.SetToolTip("Nicotine+")

    def HideUnhideWindow(self, widget):
        if self.frame.MainWindow.get_property("visible"):
            self.frame.MainWindow.hide()
        else:
            self.frame.MainWindow.show()

            self.frame.chatrooms.roomsctrl.ClearNotifications()
            self.frame.privatechats.ClearNotifications()

    def IsTrayIconVisible(self):
        if self.trayicon is None:
            return False

        if self.appindicator is None:
            return self.trayicon.get_visible()

        if self.appindicator is not None and self.trayicon.get_status() != self.appindicator.IndicatorStatus.ACTIVE:
            return False

        return True

    def SetImage(self, status=None):
        if not self.IsTrayIconVisible():
            return

        try:
            if status is not None:
                self.tray_status["status"] = status

            # Check for hilites, and display hilite icon if there is a room or private hilite
            if self.frame.hilites["rooms"] == [] and self.frame.hilites["private"] == []:
                # If there is no hilite, display the status
                icon = self.tray_status["status"]
            else:
                icon = "trayicon_msg"

            if icon != self.tray_status["last"]:
                self.tray_status["last"] = icon

            if self.appindicator is not None:
                self.trayicon.set_icon_full(icon, "Nicotine+")
            else:
                # GtkStatusIcon fallback
                self.trayicon.set_from_pixbuf(self.frame.images[icon])

        except Exception as e:
            log.addwarning(_("ERROR: cannot set trayicon image: %(error)s") % {'error': e})

    def SetToolTip(self, string):
        if self.trayicon is not None:
            if self.appindicator is not None:
                self.trayicon.set_title(string)
            else:
                # GtkStatusIcon fallback
                self.trayicon.set_tooltip_text(string)
