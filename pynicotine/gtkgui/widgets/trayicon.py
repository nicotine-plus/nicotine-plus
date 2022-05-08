# COPYRIGHT (C) 2020-2022 Nicotine+ Team
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
import gi

from gi.repository import Gtk

from pynicotine.config import config
from pynicotine.gtkgui.widgets.dialogs import EntryDialog
from pynicotine.gtkgui.widgets.theme import get_icon
from pynicotine.gtkgui.widgets.ui import GUI_DIR
from pynicotine.logfacility import log


""" Status Icon / AppIndicator """


class TrayIcon:

    def __init__(self, frame, core):

        try:
            # Check if AyatanaAppIndicator3 is available
            gi.require_version('AyatanaAppIndicator3', '0.1')
            from gi.repository import AyatanaAppIndicator3
            self.appindicator = AyatanaAppIndicator3

        except (ImportError, ValueError):
            try:
                # Check if AppIndicator3 is available
                gi.require_version('AppIndicator3', '0.1')
                from gi.repository import AppIndicator3
                self.appindicator = AppIndicator3

            except (ImportError, ValueError):
                # No AppIndicator support, fall back to GtkStatusIcon
                self.appindicator = None

        self.frame = frame
        self.core = core
        self.tray_icon = None
        self.custom_icons = False
        self.final_icon_path = None
        self.tray_status = {
            "status": "disconnect",
            "last": "disconnect"
        }
        self.create_menu()

    def create_item(self, text, callback, check=False):

        if check:
            item = Gtk.CheckMenuItem.new_with_label(text)
        else:
            item = Gtk.MenuItem.new_with_label(text)

        handler = item.connect("activate", callback)
        self.tray_popup_menu.append(item)
        item.show()

        return item, handler

    def create_menu(self):

        if Gtk.get_major_version() == 4:
            return

        self.tray_popup_menu = Gtk.Menu()
        self.hide_show_item, _handler = self.create_item(_("Show Nicotine+"), self.frame.on_window_hide_unhide)
        self.alt_speed_item, self.alt_speed_handler = self.create_item(
            _("Alternative Speed Limits"), self.frame.on_alternative_speed_limit, check=True)

        self.tray_popup_menu.append(Gtk.SeparatorMenuItem())

        self.downloads_item, _handler = self.create_item(_("Downloads"), self.on_downloads)
        self.uploads_item, _handler = self.create_item(_("Uploads"), self.on_uploads)

        self.tray_popup_menu.append(Gtk.SeparatorMenuItem())

        self.connect_item, _handler = self.create_item(_("Connect"), self.frame.on_connect)
        self.disconnect_item, _handler = self.create_item(_("Disconnect"), self.frame.on_disconnect)
        self.away_item, self.away_handler = self.create_item(_("Away"), self.frame.on_away, check=True)

        self.tray_popup_menu.append(Gtk.SeparatorMenuItem())

        self.send_message_item, _handler = self.create_item(_("Send Message"), self.on_open_private_chat)
        self.lookup_info_item, _handler = self.create_item(_("Request User's Info"), self.on_get_a_users_info)
        self.lookup_shares_item, _handler = self.create_item(_("Request User's Shares"), self.on_get_a_users_shares)

        self.tray_popup_menu.append(Gtk.SeparatorMenuItem())

        self.create_item(_("Preferences"), self.frame.on_settings)
        self.create_item(_("Quit"), self.core.quit)

    def on_downloads(self, *_args):
        self.frame.change_main_page(self.frame.downloads_page)
        self.frame.show()

    def on_uploads(self, *_args):
        self.frame.change_main_page(self.frame.uploads_page)
        self.frame.show()

    def on_open_private_chat_response(self, dialog, response_id, _data):

        user = dialog.get_response_value()
        dialog.destroy()

        if response_id != Gtk.ResponseType.OK or not user:
            return

        self.core.privatechats.show_user(user)
        self.frame.change_main_page(self.frame.private_page)
        self.frame.show()

    def on_open_private_chat(self, *_args):

        users = (i[0] for i in config.sections["server"]["userlist"])
        EntryDialog(
            parent=self.frame.application.get_active_window(),
            title=config.application_name + ": " + _("Start Messaging"),
            message=_('Enter the name of the user whom you want to send a message:'),
            callback=self.on_open_private_chat_response,
            droplist=users
        ).show()

    def on_get_a_users_info_response(self, dialog, response_id, _data):

        user = dialog.get_response_value()
        dialog.destroy()

        if response_id != Gtk.ResponseType.OK or not user:
            return

        self.core.userinfo.request_user_info(user)
        self.frame.show()

    def on_get_a_users_info(self, *_args):

        users = (i[0] for i in config.sections["server"]["userlist"])
        EntryDialog(
            parent=self.frame.application.get_active_window(),
            title=config.application_name + ": " + _("Request User Info"),
            message=_('Enter the name of the user whose info you want to see:'),
            callback=self.on_get_a_users_info_response,
            droplist=users
        ).show()

    def on_get_a_users_shares_response(self, dialog, response_id, _data):

        user = dialog.get_response_value()
        dialog.destroy()

        if response_id != Gtk.ResponseType.OK or not user:
            return

        self.core.userbrowse.browse_user(user)
        self.frame.show()

    def on_get_a_users_shares(self, *_args):

        users = (i[0] for i in config.sections["server"]["userlist"])
        EntryDialog(
            parent=self.frame.application.get_active_window(),
            title=config.application_name + ": " + _("Request Shares List"),
            message=_('Enter the name of the user whose shares you want to see:'),
            callback=self.on_get_a_users_shares_response,
            droplist=users
        ).show()

    # GtkStatusIcon fallback
    def on_status_icon_popup(self, _status_icon, button, _activate_time):

        if button == 3:
            time = Gtk.get_current_event_time()
            self.tray_popup_menu.popup(None, None, None, None, button, time)

    @staticmethod
    def check_icon_path(icon_name, icon_path, icon_type="local"):

        """
        Check if tray icons exist in the specified icon path.
        There are two naming schemes for tray icons:
        - System-wide/local icons: "org.nicotine_plus.Nicotine-<icon_name>"
        - Custom icons: "trayicon_<icon_name>"
        """

        if not icon_path:
            return False

        if icon_type == "local":
            icon_scheme = config.application_id + "-" + icon_name + "."
        else:
            icon_scheme = "trayicon_" + icon_name + "."

        try:
            for entry in os.scandir(icon_path.encode("utf-8")):
                if entry.is_file() and entry.name.decode("utf-8").startswith(icon_scheme):
                    return True

        except OSError as error:
            log.add_debug("Error accessing %(type)s tray icon path %(path)s: %(error)s" %
                          {"type": icon_type, "path": icon_path, "error": error})

        return False

    def get_final_icon_path(self):

        """ Returns an icon path to use for tray icons, or None to fall back to
        system-wide icons. """

        custom_icon_path = config.sections["ui"]["icontheme"]

        if hasattr(sys, "real_prefix") or sys.base_prefix != sys.prefix:
            # Virtual environment
            local_icon_path = os.path.join(sys.prefix, "share", "icons", "hicolor", "scalable", "apps")
        else:
            # Git folder
            local_icon_path = os.path.join(GUI_DIR, "icons", "hicolor", "scalable", "apps")

        for icon_name in ("away", "connect", "disconnect", "msg"):

            # Check if custom icons exist
            if self.check_icon_path(icon_name, custom_icon_path, icon_type="custom"):
                self.custom_icons = True
                return custom_icon_path

            # Check if local icons exist
            if self.check_icon_path(icon_name, local_icon_path, icon_type="local"):
                return local_icon_path

        return None

    def load(self, use_trayicon=None):

        if Gtk.get_major_version() == 4:
            return

        if sys.platform == "darwin":
            # Tray icons don't work as expected on macOS
            return

        if sys.platform == "win32":
            # Always keep tray icon loaded for notification support
            pass

        elif use_trayicon is None:
            if not config.sections["ui"]["trayicon"]:
                return

        elif not use_trayicon:
            return

        if self.tray_icon is None:
            if self.appindicator is not None:
                tray_icon = self.appindicator.Indicator.new(
                    id=config.application_name,
                    icon_name="",
                    category=self.appindicator.IndicatorCategory.APPLICATION_STATUS)
                tray_icon.set_menu(self.tray_popup_menu)

                # Action to hide/unhide main window when middle clicking the tray icon
                tray_icon.set_secondary_activate_target(self.hide_show_item)

                # If custom icon path was found, use it, otherwise we fall back to system icons
                self.final_icon_path = self.get_final_icon_path()

                if self.final_icon_path:
                    log.add_debug("Using tray icon path %s", self.final_icon_path)
                    tray_icon.set_icon_theme_path(self.final_icon_path)

            else:
                # GtkStatusIcon fallback
                tray_icon = Gtk.StatusIcon(tooltip_text=config.application_name)
                tray_icon.connect("activate", self.frame.on_window_hide_unhide)
                tray_icon.connect("popup-menu", self.on_status_icon_popup)

            self.tray_icon = tray_icon
            self.set_server_actions_sensitive(False)

        self.set_alternative_speed_limit(config.sections["transfers"]["usealtlimits"])

        if use_trayicon or config.sections["ui"]["trayicon"]:
            self.show()

            # Gtk.StatusIcon.is_embedded() may not be true yet (observed in LXDE), force an icon update
            self.set_icon(self.tray_status["status"], force_update=True)
            return

        self.set_icon("msg", force_update=True)
        self.hide()

    def show(self):

        if self.is_visible():
            return

        if self.appindicator is not None:
            self.tray_icon.set_status(self.appindicator.IndicatorStatus.ACTIVE)
        else:
            # GtkStatusIcon fallback
            self.tray_icon.set_visible(True)

    def hide(self):

        if not self.is_visible():
            return

        if self.appindicator is not None:
            self.tray_icon.set_status(self.appindicator.IndicatorStatus.PASSIVE)
        else:
            # GtkStatusIcon fallback
            self.tray_icon.set_visible(False)

    def is_visible(self):

        if self.tray_icon is None:
            return False

        if self.appindicator is None:
            return self.tray_icon.get_visible() and self.tray_icon.is_embedded()

        if self.appindicator is not None and self.tray_icon.get_status() != self.appindicator.IndicatorStatus.ACTIVE:
            return False

        return True

    def update_show_hide_label(self):

        if self.tray_icon is None:
            return

        if self.frame.window.get_property("visible"):
            text = _("Hide Nicotine+")
        else:
            text = _("Show Nicotine+")

        self.hide_show_item.set_label(text)

    def set_icon(self, status=None, force_update=False):

        if not force_update and not self.is_visible():
            return

        if status is not None:
            self.tray_status["status"] = status

        # Check for hilites, and display hilite icon if there is a room or private hilite
        if (self.core.notifications
                and (self.core.notifications.chat_hilites["rooms"]
                     or self.core.notifications.chat_hilites["private"])):
            icon_name = "msg"
        else:
            # If there is no hilite, display the status
            icon_name = self.tray_status["status"]

        if icon_name != self.tray_status["last"]:
            self.tray_status["last"] = icon_name

        if self.custom_icons:
            icon_name = "trayicon_" + icon_name
        else:
            icon_name = config.application_id + "-" + icon_name

        if self.appindicator is not None:
            self.tray_icon.set_icon_full(icon_name, config.application_name)

        else:
            # GtkStatusIcon fallback
            if self.custom_icons:
                self.tray_icon.set_from_gicon(get_icon(icon_name))
            else:
                self.tray_icon.set_from_icon_name(icon_name)

    def set_away(self, enable):

        if self.tray_icon is None:
            return

        if enable:
            self.tray_status["status"] = "away"
        else:
            self.tray_status["status"] = "connect"

        self.set_icon()

        with self.away_item.handler_block(self.away_handler):
            # Temporarily disable handler, we only want to change the visual checkbox appearance
            self.away_item.set_active(enable)

    def set_connected(self, enable):

        if self.tray_icon is None:
            return

        if enable:
            self.tray_status["status"] = "connect"
        else:
            self.tray_status["status"] = "disconnect"

        self.set_icon()

    def set_server_actions_sensitive(self, status):

        if self.tray_icon is None:
            return

        for i in (self.disconnect_item, self.away_item, self.send_message_item,
                  self.lookup_info_item, self.lookup_shares_item):

            """ Disable menu items when disconnected from server """
            i.set_sensitive(status)

        self.connect_item.set_sensitive(not status)

    def set_download_status(self, status):

        if self.tray_icon is None:
            return

        self.downloads_item.set_label(status)

    def set_upload_status(self, status):

        if self.tray_icon is None:
            return

        self.uploads_item.set_label(status)

    def set_alternative_speed_limit(self, enable):

        if self.tray_icon is None:
            return

        with self.alt_speed_item.handler_block(self.alt_speed_handler):
            # Temporarily disable handler, we only want to change the visual checkbox appearance
            self.alt_speed_item.set_active(enable)
