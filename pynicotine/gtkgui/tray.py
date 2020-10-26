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
from pynicotine.gtkgui.dialogs import combo_box_dialog
from pynicotine.gtkgui.utils import PopupMenu
from pynicotine.logfacility import log


class TrayApp:

    def __init__(self, frame):
        try:
            # Check if AyatanaAppIndicator3 is available
            gi.require_version('AyatanaAppIndicator3', '0.1')
            from gi.repository import AyatanaAppIndicator3  # noqa: F401
            self.appindicator = AyatanaAppIndicator3
        except (ImportError, ValueError):
            try:
                # Check if AppIndicator3 is available
                gi.require_version('AppIndicator3', '0.1')
                from gi.repository import AppIndicator3  # noqa: F401
                self.appindicator = AppIndicator3
            except (ImportError, ValueError):
                # No AppIndicator support, fall back to GtkStatusIcon
                from gi.repository import Gtk
                self.appindicator = None
                self.gtk = Gtk

        self.frame = frame
        self.trayicon = None
        self.custom_icons = False
        self.local_icons = False
        self.tray_status = {
            "status": "disconnect",
            "last": "disconnect"
        }
        self.create_menu()

    def create_menu(self):
        try:
            self.tray_popup_menu_server = popup0 = PopupMenu(self, False)
            popup0.setup(
                ("#" + _("Connect"), self.frame.on_connect),
                ("#" + _("Disconnect"), self.frame.on_disconnect)
            )

            self.tray_popup_menu = popup = PopupMenu(self, False)
            popup.setup(
                ("#" + _("Hide / Show Nicotine+"), self.on_hide_unhide_window),
                (1, _("Server"), self.tray_popup_menu_server, self.on_popup_server),
                ("#" + _("Downloads"), self.on_downloads),
                ("#" + _("Uploads"), self.on_uploads),
                ("#" + _("Send Message"), self.on_open_private_chat),
                ("#" + _("Lookup a User's IP"), self.on_get_a_users_ip),
                ("#" + _("Lookup a User's Info"), self.on_get_a_users_info),
                ("#" + _("Lookup a User's Shares"), self.on_get_a_users_shares),
                ("$" + _("Toggle Away"), self.frame.on_away),
                ("#" + _("Settings"), self.frame.on_settings),
                ("#" + _("Quit"), self.frame.on_quit)
            )
        except Exception as e:
            log.add_warning(_('ERROR: tray menu, %(error)s'), {'error': e})

    def on_hide_unhide_window(self, widget):
        if self.frame.MainWindow.get_property("visible"):
            self.frame.MainWindow.hide()
        else:
            self.show_window()

    def on_downloads(self, widget):
        self.frame.on_downloads()
        self.show_window()

    def on_uploads(self, widget):
        self.frame.on_uploads()
        self.show_window()

    def on_open_private_chat(self, widget, prefix=""):

        # popup
        users = []
        for entry in self.frame.np.config.sections["server"]["userlist"]:
            users.append(entry[0])

        users.sort()
        user = combo_box_dialog(
            parent=self.frame.MainWindow,
            title="Nicotine+" + ": " + _("Start Messaging"),
            message=_('Enter the User who you wish to send a private message:'),
            droplist=users
        )

        if user is not None:
            self.frame.privatechats.send_message(user, show_user=True)
            self.frame.change_main_page("private")
            self.show_window()

    def on_get_a_users_info(self, widget, prefix=""):

        # popup
        users = []
        for entry in self.frame.np.config.sections["server"]["userlist"]:
            users.append(entry[0])

        users.sort()
        user = combo_box_dialog(
            parent=self.frame.MainWindow,
            title="Nicotine+" + ": " + _("Get User Info"),
            message=_('Enter the User whose User Info you wish to receive:'),
            droplist=users
        )

        if user is not None:
            self.frame.local_user_info_request(user)

    def on_get_a_users_ip(self, widget, prefix=""):
        users = []
        for entry in self.frame.np.config.sections["server"]["userlist"]:
            users.append(entry[0])
        users.sort()
        user = combo_box_dialog(
            parent=self.frame.MainWindow,
            title="Nicotine+" + ": " + _("Get A User's IP"),
            message=_('Enter the User whose IP Address you wish to receive:'),
            droplist=users
        )
        if user is not None:
            if user not in self.frame.np.ip_requested:
                self.frame.np.ip_requested.append(user)

            self.frame.np.queue.put(slskmessages.GetPeerAddress(user))

    def on_get_a_users_shares(self, widget, prefix=""):
        users = []
        for entry in self.frame.np.config.sections["server"]["userlist"]:
            users.append(entry[0])
        users.sort()
        user = combo_box_dialog(
            parent=self.frame.MainWindow,
            title="Nicotine+" + ": " + _("Get A User's Shares List"),
            message=_('Enter the User whose Shares List you wish to receive:'),
            droplist=users
        )
        if user is not None:
            self.frame.browse_user(user)

    def on_popup_server(self, widget):
        items = self.tray_popup_menu_server.get_children()

        if self.tray_status["status"] == "disconnect":
            items[0].set_sensitive(True)
            items[1].set_sensitive(False)
        else:
            items[0].set_sensitive(False)
            items[1].set_sensitive(True)

    # GtkStatusIcon fallback
    def on_status_icon_popup(self, status_icon, button, activate_time):
        if button == 3:
            self.tray_popup_menu.popup(None, None, None, None, button, activate_time)

    def create(self):
        self.load()
        self.draw()

    def load(self):
        """ Create """
        if self.trayicon is None:
            if self.appindicator is not None:
                trayicon = self.appindicator.Indicator.new(
                    "Nicotine+",
                    "",
                    self.appindicator.IndicatorCategory.APPLICATION_STATUS)
                trayicon.set_menu(self.tray_popup_menu)
            else:
                # GtkStatusIcon fallback
                trayicon = self.gtk.StatusIcon()

            self.trayicon = trayicon

        """ Set up icons """
        custom_icon_path = self.frame.np.config.sections["ui"]["icontheme"]
        final_icon_path = ""

        for icon_name in ["away", "connect", "disconnect", "msg"]:
            """
            There are two naming schemes for tray icons:
            - System-wide/local icons: "org.nicotine_plus.Nicotine-<icon_name>"
            - Custom icons: "trayicon_<icon_name>"
            """

            if glob.glob(os.path.join(custom_icon_path, "trayicon_" + icon_name) + ".*"):
                final_icon_path = custom_icon_path
                self.custom_icons = True
                break

            if glob.glob(os.path.join("img", "tray", "org.nicotine_plus.Nicotine-" + icon_name) + ".*"):
                final_icon_path = os.path.abspath(
                    os.path.join("img", "tray")
                )
                self.local_icons = True
                break

        # If custom icon path was found, use it, otherwise we fall back to system icons
        if self.appindicator is not None and final_icon_path:
            self.trayicon.set_icon_theme_path(final_icon_path)

        """ Set visible """
        if self.appindicator is not None:
            self.trayicon.set_status(self.appindicator.IndicatorStatus.ACTIVE)
        else:
            # GtkStatusIcon fallback
            self.trayicon.set_visible(True)

    def hide(self):
        if not self.is_tray_icon_visible():
            return

        if self.appindicator is not None:
            self.trayicon.set_status(self.appindicator.IndicatorStatus.PASSIVE)
        else:
            # GtkStatusIcon fallback
            self.trayicon.set_visible(False)

    def draw(self):
        if not self.is_tray_icon_visible():
            return

        if self.appindicator is not None:
            # Action to hide/unhide main window when middle clicking the tray icon
            hide_unhide_item = self.tray_popup_menu.get_children()[0]
            self.trayicon.set_secondary_activate_target(hide_unhide_item)
        else:
            # GtkStatusIcon fallback
            self.trayicon.connect("activate", self.on_hide_unhide_window)
            self.trayicon.connect("popup-menu", self.on_status_icon_popup)

        self.set_image(self.tray_status["status"])

    def show_window(self):
        self.frame.MainWindow.show()

        self.frame.chatrooms.roomsctrl.clear_notifications()
        self.frame.privatechats.clear_notifications()

    def is_tray_icon_visible(self):
        if self.trayicon is None:
            return False

        if self.appindicator is None:
            return self.trayicon.get_visible()

        if self.appindicator is not None and self.trayicon.get_status() != self.appindicator.IndicatorStatus.ACTIVE:
            return False

        return True

    def set_image(self, status=None):
        if not self.is_tray_icon_visible():
            return

        try:
            if status is not None:
                self.tray_status["status"] = status

            # Check for hilites, and display hilite icon if there is a room or private hilite
            if self.frame.hilites["rooms"] == [] and self.frame.hilites["private"] == []:
                # If there is no hilite, display the status
                icon_name = self.tray_status["status"]
            else:
                icon_name = "msg"

            if icon_name != self.tray_status["last"]:
                self.tray_status["last"] = icon_name

            if self.appindicator is not None:
                if self.custom_icons:
                    icon_name = "trayicon_" + icon_name
                else:
                    icon_name = "org.nicotine_plus.Nicotine-" + icon_name

                self.trayicon.set_icon_full(icon_name, "Nicotine+")

            else:
                # GtkStatusIcon fallback
                if self.custom_icons or self.local_icons:
                    self.trayicon.set_from_pixbuf(
                        self.frame.images["trayicon_" + icon_name]
                    )
                else:
                    self.trayicon.set_from_icon_name("org.nicotine_plus.Nicotine-" + icon_name)

        except Exception as e:
            log.add_warning(_("ERROR: cannot set trayicon image: %(error)s"), {'error': e})

    def set_transfer_status(self, download, upload):
        if self.trayicon is not None:
            self.tray_popup_menu.get_children()[2].set_label(download)
            self.tray_popup_menu.get_children()[3].set_label(upload)
