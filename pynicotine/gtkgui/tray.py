# -*- coding: utf-8 -*-
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
import sys

from pynicotine.gtkgui.utils import PopupMenu
from pynicotine.logfacility import log


class TrayApp:

    def __init__(self, frame):
        gi.require_version('AppIndicator3', '0.1')
        from gi.repository import AppIndicator3 as appindicator

        self.appindicator = appindicator
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
                ("#" + _("Send Message"), self.frame.OnOpenPrivateChat),
                ("#" + _("Lookup a User's IP"), self.frame.OnGetAUsersIP),
                ("#" + _("Lookup a User's Info"), self.frame.OnGetAUsersInfo),
                ("#" + _("Lookup a User's Shares"), self.frame.OnGetAUsersShares),
                ("$" + _("Toggle Away"), self.frame.OnAway),
                ("#" + _("Quit"), self.frame.OnExit)
            )
        except Exception as e:
            log.addwarning(_('ERROR: tray menu, %(error)s') % {'error': e})

    def OnPopupServer(self, widget):
        items = self.tray_popup_menu_server.get_children()

        if self.tray_status["status"] == "trayicon_disconnect":
            items[0].set_sensitive(True)
            items[1].set_sensitive(False)
        else:
            items[0].set_sensitive(False)
            items[1].set_sensitive(True)
        return

    def Create(self):
        self.Load()
        self.Draw()

    def Load(self):
        if self.trayicon is None:
            trayicon = self.appindicator.Indicator.new(
                "Nicotine+",
                "",
                self.appindicator.IndicatorCategory.APPLICATION_STATUS)
            trayicon.set_menu(self.tray_popup_menu)

            iconpath = self.frame.np.config.sections["ui"]["icontheme"]
            for iconname in ["trayicon_away", "trayicon_connect", "trayicon_disconnect", "trayicon_msg"]:
                if not glob.glob(os.path.join(iconpath, iconname) + ".*"):
                    # Fall back to system-wide tray icon location
                    iconpath = os.path.join(sys.prefix, "share/nicotine/trayicons")
                    if not glob.glob(os.path.join(iconpath, iconname) + ".*"):
                        # Nicotine+ is not installed system-wide, load tray icons from current folder
                        iconpath = os.path.join(os.getcwd(), "img")
                        break
                    break

            trayicon.set_icon_theme_path(iconpath)
            self.trayicon = trayicon

        self.trayicon.set_status(self.appindicator.IndicatorStatus.ACTIVE)

    def destroy_trayicon(self):
        if not self.IsTrayIconVisible():
            return

        self.trayicon.set_status(self.appindicator.IndicatorStatus.PASSIVE)

    def Draw(self):
        if not self.IsTrayIconVisible():
            return

        self.SetImage(self.tray_status["status"])
        self.SetToolTip("Nicotine+")

    def HideUnhideWindow(self, widget):
        if self.frame.is_mapped:
            self.frame.MainWindow.unmap()
            self.frame.is_mapped = False
        else:
            self.frame.MainWindow.map()
            # weird, but this allows us to easily a minimized nicotine from one
            # desktop to another by clicking on the tray icon
            if self.frame.minimized:
                self.frame.MainWindow.present()

            self.frame.MainWindow.grab_focus()
            self.frame.is_mapped = True

            self.frame.chatrooms.roomsctrl.ClearNotifications()
            self.frame.privatechats.ClearNotifications()

    def IsTrayIconVisible(self):
        if self.trayicon is None or self.trayicon.get_status() != self.appindicator.IndicatorStatus.ACTIVE:
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

            self.trayicon.set_icon_full(icon, "Nicotine+")

        except Exception as e:
            log.addwarning(_("ERROR: cannot set trayicon image: %(error)s") % {'error': e})

    def SetToolTip(self, string):
        if self.trayicon is not None:
            self.trayicon.set_title(string)
