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
from pynicotine.gtkgui.widgets.dialogs import entry_dialog
from pynicotine.gtkgui.widgets.theme import get_icon
from pynicotine.gtkgui.widgets.ui import GUI_DIR
from pynicotine.logfacility import log


""" Tray Icon """


class BaseImplementation:

    def __init__(self, frame):

        self.frame = frame
        self.menu = None
        self.status = "disconnect"
        self.custom_icons = False

        # If custom icon path was found, use it, otherwise we fall back to system icons
        self.final_icon_path = self.get_final_icon_path()

        self.create_menu()

    def create_item(self, text, callback, check=False):

        if check:
            item = Gtk.CheckMenuItem.new_with_label(text)
        else:
            item = Gtk.MenuItem.new_with_label(text)

        handler = item.connect("activate", callback)
        self.menu.append(item)
        item.show()

        return item, handler

    def create_menu(self):

        if Gtk.get_major_version() == 4:
            return

        self.menu = Gtk.Menu()
        self.hide_show_item, _handler = self.create_item(_("Show Nicotine+"), self.frame.on_window_hide_unhide)
        self.alt_speed_item, self.alt_speed_handler = self.create_item(
            _("Alternative Speed Limits"), self.frame.on_alternative_speed_limit, check=True)

        self.menu.append(Gtk.SeparatorMenuItem())

        self.downloads_item, _handler = self.create_item(_("Downloads"), self.on_downloads)
        self.uploads_item, _handler = self.create_item(_("Uploads"), self.on_uploads)

        self.menu.append(Gtk.SeparatorMenuItem())

        self.connect_item, _handler = self.create_item(_("Connect"), self.frame.on_connect)
        self.disconnect_item, _handler = self.create_item(_("Disconnect"), self.frame.on_disconnect)
        self.away_item, self.away_handler = self.create_item(_("Away"), self.frame.on_away, check=True)

        self.menu.append(Gtk.SeparatorMenuItem())

        self.send_message_item, _handler = self.create_item(_("Send Message"), self.on_open_private_chat)
        self.lookup_info_item, _handler = self.create_item(_("Request User's Info"), self.on_get_a_users_info)
        self.lookup_shares_item, _handler = self.create_item(_("Request User's Shares"), self.on_get_a_users_shares)

        self.menu.append(Gtk.SeparatorMenuItem())

        self.create_item(_("Preferences"), self.frame.on_settings)
        self.create_item(_("Quit"), self.frame.np.quit)

    def update_show_hide_label(self):

        if self.menu is None:
            return

        if self.frame.MainWindow.get_property("visible"):
            text = _("Hide Nicotine+")
        else:
            text = _("Show Nicotine+")

        self.hide_show_item.set_label(text)

    def set_server_actions_sensitive(self, status):

        if self.menu is None:
            return

        for item in (self.disconnect_item, self.away_item, self.send_message_item,
                     self.lookup_info_item, self.lookup_shares_item):

            # Disable menu items when disconnected from server
            item.set_sensitive(status)

        self.connect_item.set_sensitive(not status)

    def set_connected(self, enable):
        self.set_icon("connect" if enable else "disconnect")

    def set_away(self, enable):

        self.set_icon("away" if enable else "connect")

        if self.menu is None:
            return

        with self.away_item.handler_block(self.away_handler):
            # Temporarily disable handler, we only want to change the visual checkbox appearance
            self.away_item.set_active(enable)

    def set_download_status(self, status):

        if self.menu is None:
            return

        self.downloads_item.set_label(status)

    def set_upload_status(self, status):

        if self.menu is None:
            return

        self.uploads_item.set_label(status)

    def set_alternative_speed_limit(self, enable):

        if self.menu is None:
            return

        with self.alt_speed_item.handler_block(self.alt_speed_handler):
            # Temporarily disable handler, we only want to change the visual checkbox appearance
            self.alt_speed_item.set_active(enable)

    @staticmethod
    def check_icon_path(icon_name, icon_path, icon_type="local"):
        """
        Check if tray icons exist in the specified icon path.
        There are two naming schemes for tray icons:
        - System-wide/local icons: "org.nicotine_plus.Nicotine-<icon_name>"
        - Custom icons: "trayicon_<icon_name>"
        """

        if icon_type == "local":
            icon_scheme = config.application_id + "-" + icon_name + "."
        else:
            icon_scheme = "trayicon_" + icon_name + "."

        try:
            for entry in os.scandir(icon_path):
                if entry.is_file() and entry.name.startswith(icon_scheme):
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

    def on_downloads(self, *_args):
        self.frame.change_main_page("downloads")
        self.frame.show()

    def on_uploads(self, *_args):
        self.frame.change_main_page("uploads")
        self.frame.show()

    def on_open_private_chat_response(self, dialog, response_id, _data):

        user = dialog.get_response_value()
        dialog.destroy()

        if response_id != Gtk.ResponseType.OK or not user:
            return

        self.frame.np.privatechats.show_user(user)
        self.frame.change_main_page("private")
        self.frame.show()

    def on_open_private_chat(self, *_args):

        users = (i[0] for i in config.sections["server"]["userlist"])
        entry_dialog(
            parent=self.frame.application.get_active_window(),
            title=config.application_name + ": " + _("Start Messaging"),
            message=_('Enter the name of the user whom you want to send a message:'),
            callback=self.on_open_private_chat_response,
            droplist=users
        )

    def on_get_a_users_info_response(self, dialog, response_id, _data):

        user = dialog.get_response_value()
        dialog.destroy()

        if response_id != Gtk.ResponseType.OK or not user:
            return

        self.frame.np.userinfo.request_user_info(user)
        self.frame.show()

    def on_get_a_users_info(self, *_args):

        users = (i[0] for i in config.sections["server"]["userlist"])
        entry_dialog(
            parent=self.frame.application.get_active_window(),
            title=config.application_name + ": " + _("Request User Info"),
            message=_('Enter the name of the user whose info you want to see:'),
            callback=self.on_get_a_users_info_response,
            droplist=users
        )

    def on_get_a_users_shares_response(self, dialog, response_id, _data):

        user = dialog.get_response_value()
        dialog.destroy()

        if response_id != Gtk.ResponseType.OK or not user:
            return

        self.frame.np.userbrowse.browse_user(user)
        self.frame.show()

    def on_get_a_users_shares(self, *_args):

        users = (i[0] for i in config.sections["server"]["userlist"])
        entry_dialog(
            parent=self.frame.application.get_active_window(),
            title=config.application_name + ": " + _("Request Shares List"),
            message=_('Enter the name of the user whose shares you want to see:'),
            callback=self.on_get_a_users_shares_response,
            droplist=users
        )

    def set_icon(self, status=None, force_update=False):

        if not force_update and not self.is_visible():
            return

        if status is not None:
            self.status = status

        # Check for hilites, and display hilite icon if there is a room or private hilite
        if (self.frame.np.notifications
                and (self.frame.np.notifications.chat_hilites["rooms"]
                     or self.frame.np.notifications.chat_hilites["private"])):
            icon_name = "msg"
        else:
            # If there is no hilite, display the status
            icon_name = self.status

        if self.custom_icons:
            icon_name = "trayicon_" + icon_name
        else:
            icon_name = config.application_id + "-" + icon_name

        self.set_icon_name(icon_name)

    def set_icon_name(self, icon_name):
        pass

    @staticmethod
    def is_visible():
        return False

    def show(self):
        pass

    def hide(self):
        pass


class AppIndicatorImplementation(BaseImplementation):

    def __init__(self, frame):

        super().__init__(frame)

        try:
            # Check if AyatanaAppIndicator3 is available
            gi.require_version('AyatanaAppIndicator3', '0.1')
            from gi.repository import AyatanaAppIndicator3
            self.implementation_class = AyatanaAppIndicator3

        except (ImportError, ValueError):
            try:
                # Check if AppIndicator3 is available
                gi.require_version('AppIndicator3', '0.1')
                from gi.repository import AppIndicator3
                self.implementation_class = AppIndicator3

            except (ImportError, ValueError) as error:
                raise AttributeError("AppIndicator implementation not available") from error

        self.tray_icon = self.implementation_class.Indicator.new(
            id=config.application_name,
            icon_name="",
            category=self.implementation_class.IndicatorCategory.APPLICATION_STATUS)

        self.tray_icon.set_menu(self.menu)

        # Action to hide/unhide main window when middle clicking the tray icon
        self.tray_icon.set_secondary_activate_target(self.menu.get_children()[0])

        if self.final_icon_path:
            log.add_debug("Using tray icon path %s", self.final_icon_path)
            self.tray_icon.set_icon_theme_path(self.final_icon_path)

    def set_icon_name(self, icon_name):
        self.tray_icon.set_icon_full(icon_name, config.application_name)

    def is_visible(self):
        return self.tray_icon.get_status() == self.implementation_class.IndicatorStatus.ACTIVE

    def show(self):

        if self.is_visible():
            return

        self.tray_icon.set_status(self.implementation_class.IndicatorStatus.ACTIVE)

    def hide(self):

        if self.is_visible():
            return

        self.tray_icon.set_status(self.implementation_class.IndicatorStatus.PASSIVE)


class StatusIconImplementation(BaseImplementation):

    def __init__(self, frame):

        super().__init__(frame)

        if not hasattr(Gtk, "StatusIcon") or sys.platform == "darwin":
            # Tray icons don't work as expected on macOS
            raise AttributeError("StatusIcon implementation not available")

        self.tray_icon = Gtk.StatusIcon(tooltip_text=config.application_name)
        self.tray_icon.connect("activate", self.frame.on_window_hide_unhide)
        self.tray_icon.connect("popup-menu", self.on_status_icon_popup)

    def on_status_icon_popup(self, _status_icon, button, _activate_time):

        if button == 3:
            time = Gtk.get_current_event_time()
            self.menu.popup(None, None, None, None, button, time)

    def set_icon_name(self, icon_name):

        if self.custom_icons:
            self.tray_icon.set_from_gicon(get_icon(icon_name))
        else:
            self.tray_icon.set_from_icon_name(icon_name)

    def is_visible(self):
        return self.tray_icon.get_visible() and self.tray_icon.is_embedded()

    def show(self):

        if self.is_visible():
            return

        self.tray_icon.set_visible(True)

    def hide(self):

        if self.is_visible():
            return

        self.tray_icon.set_visible(False)


class TrayIcon:

    def __init__(self, frame, use_trayicon):

        self.frame = frame
        self.available = True
        self.implementation = None

        self.load(use_trayicon)

    def load(self, use_trayicon=None):

        if sys.platform == "win32":
            # Always keep tray icon loaded for notification support
            pass

        elif use_trayicon is None:
            if not config.sections["ui"]["trayicon"]:
                return

        elif not use_trayicon:
            return

        if self.implementation is None:
            try:
                self.implementation = AppIndicatorImplementation(self.frame)

            except AttributeError:
                try:
                    self.implementation = StatusIconImplementation(self.frame)

                except AttributeError:
                    self.implementation = BaseImplementation(self.frame)
                    self.available = False

            self.set_server_actions_sensitive(False)
            self.set_alternative_speed_limit(config.sections["transfers"]["usealtlimits"])

        if config.sections["ui"]["trayicon"]:
            self.show()

            # Gtk.StatusIcon.is_embedded() may not be true yet (observed in LXDE), force an icon update
            self.set_icon(force_update=True)
            return

        self.set_icon("msg", force_update=True)
        self.hide()

    def update_show_hide_label(self):
        self.implementation.update_show_hide_label()

    def set_away(self, enable):
        self.implementation.set_away(enable)

    def set_connected(self, enable):
        self.implementation.set_connected(enable)

    def set_server_actions_sensitive(self, status):
        self.implementation.set_server_actions_sensitive(status)

    def set_download_status(self, status):
        self.implementation.set_download_status(status)

    def set_upload_status(self, status):
        self.implementation.set_upload_status(status)

    def set_alternative_speed_limit(self, enable):
        self.implementation.set_alternative_speed_limit(enable)

    def set_icon(self, status=None, force_update=False):
        self.implementation.set_icon(status, force_update)

    def is_visible(self):
        return self.implementation.is_visible()

    def show(self):
        self.implementation.show()

    def hide(self):
        self.implementation.hide()
