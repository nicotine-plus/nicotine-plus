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

from collections import OrderedDict

from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk

from pynicotine.config import config
from pynicotine.gtkgui.application import GTK_GUI_DIR
from pynicotine.gtkgui.widgets.dialogs import EntryDialog
from pynicotine.logfacility import log
from pynicotine.slskmessages import UserStatus
from pynicotine.utils import encode_path


""" Tray Icon """


class ImplementationUnavailable(Exception):
    pass


class BaseImplementation:

    def __init__(self, frame, core):

        self.frame = frame
        self.core = core
        self.menu_items = OrderedDict()
        self.menu_item_id = 1

        self.create_menu()

    def create_item(self, text=None, callback=None, check=False):

        item = {"id": self.menu_item_id, "sensitive": True, "visible": True}

        if text is not None:
            item["text"] = text

        if callback is not None:
            item["callback"] = callback

        if check:
            item["toggled"] = False

        self.menu_items[self.menu_item_id] = item
        self.menu_item_id += 1

        return item

    @staticmethod
    def set_item_text(item, text):
        item["text"] = text

    @staticmethod
    def set_item_sensitive(item, sensitive):
        item["sensitive"] = sensitive

    @staticmethod
    def set_item_visible(item, visible):
        item["visible"] = visible

    @staticmethod
    def set_item_toggled(item, toggled):
        item["toggled"] = toggled

    def create_menu(self):

        self.show_item = self.create_item(_("Show Nicotine+"), self.frame.on_window_hide_unhide)
        self.hide_item = self.create_item(_("Hide Nicotine+"), self.frame.on_window_hide_unhide)
        self.alt_speed_item = self.create_item(
            _("Alternative Speed Limits"), self.frame.on_alternative_speed_limit, check=True)

        self.create_item()

        self.downloads_item = self.create_item(_("Downloads"), self.on_downloads)
        self.uploads_item = self.create_item(_("Uploads"), self.on_uploads)

        self.create_item()

        self.connect_item = self.create_item(_("Connect"), self.frame.on_connect)
        self.disconnect_item = self.create_item(_("Disconnect"), self.frame.on_disconnect)
        self.away_item = self.create_item(_("Away"), self.frame.on_away, check=True)

        self.create_item()

        self.send_message_item = self.create_item(_("Send Message"), self.on_open_private_chat)
        self.lookup_info_item = self.create_item(_("Request User's Info"), self.on_get_a_users_info)
        self.lookup_shares_item = self.create_item(_("Request User's Shares"), self.on_get_a_users_shares)

        self.create_item()

        self.create_item(_("Preferences"), self.frame.on_settings)
        self.create_item(_("Quit"), self.core.quit)

    def update_window_visibility(self):

        visible = self.frame.window.get_property("visible")

        self.set_item_visible(self.show_item, not visible)
        self.set_item_visible(self.hide_item, visible)

        self.update_menu()

    def update_user_status(self):

        sensitive = self.core.user_status != UserStatus.OFFLINE

        for item in (self.away_item, self.send_message_item,
                     self.lookup_info_item, self.lookup_shares_item):

            # Disable menu items when disconnected from server
            self.set_item_sensitive(item, sensitive)

        self.set_item_visible(self.connect_item, not sensitive)
        self.set_item_visible(self.disconnect_item, sensitive)
        self.set_item_toggled(self.away_item, self.core.user_status == UserStatus.AWAY)

        self.update_icon()
        self.update_menu()

    def update_alternative_speed_limit_status(self):
        self.set_item_toggled(self.alt_speed_item, config.sections["transfers"]["usealtlimits"])
        self.update_menu()

    def update_icon(self, force_update=False):

        if not force_update and not self.is_visible():
            return

        # Check for hilites, and display hilite icon if there is a room or private hilite
        if (self.core.notifications
                and (self.core.notifications.chat_hilites["rooms"]
                     or self.core.notifications.chat_hilites["private"])):
            icon_name = "msg"

        elif self.core.user_status == UserStatus.ONLINE:
            icon_name = "connect"

        elif self.core.user_status == UserStatus.AWAY:
            icon_name = "away"

        else:
            icon_name = "disconnect"

        icon_name = config.application_id + "-" + icon_name
        self.set_icon_name(icon_name)

    def set_icon_name(self, icon_name):
        # Implemented in subclasses
        pass

    def update_icon_theme(self):
        # Implemented in subclasses
        pass

    def update_menu(self):
        # Implemented in subclasses
        pass

    def set_download_status(self, status):
        self.set_item_text(self.downloads_item, status)
        self.update_menu()

    def set_upload_status(self, status):
        self.set_item_text(self.uploads_item, status)
        self.update_menu()

    def on_downloads(self, *_args):
        self.frame.change_main_page(self.frame.downloads_page)
        self.frame.show()

    def on_uploads(self, *_args):
        self.frame.change_main_page(self.frame.uploads_page)
        self.frame.show()

    def on_open_private_chat_response(self, dialog, _response_id, _data):

        user = dialog.get_entry_value()

        if not user:
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

    def on_get_a_users_info_response(self, dialog, _response_id, _data):

        user = dialog.get_entry_value()

        if not user:
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

    def on_get_a_users_shares_response(self, dialog, _response_id, _data):

        user = dialog.get_entry_value()

        if not user:
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

    def is_visible(self):  # pylint:disable=no-self-use
        # Implemented in subclasses
        return False

    def show(self):
        # Implemented in subclasses
        pass

    def hide(self):
        # Implemented in subclasses
        pass


class StatusNotifierImplementation(BaseImplementation):

    class DBusService:

        def __init__(self, interface_name, object_path, bus_type):

            self._interface_name = interface_name
            self._object_path = object_path

            self._bus = Gio.bus_get_sync(bus_type)
            self._property_signatures = {}
            self._property_values = {}
            self._signal_signatures = {}
            self._method_signatures = {}
            self._method_callbacks = {}
            self._registration_id = None

        def register(self):

            xml_output = "<node name='/'><interface name='%s'>" % self._interface_name

            for property_name, signature in self._property_signatures.items():
                xml_output += "<property name='%s' type='%s' access='read'/>" % (property_name, signature)

            for method_name, (in_args, out_args) in self._method_signatures.items():
                xml_output += "<method name='%s'>" % method_name

                for in_signature in in_args:
                    xml_output += "<arg type='%s' direction='in'/>" % in_signature
                for out_signature in out_args:
                    xml_output += "<arg type='%s' direction='out'/>" % out_signature

                xml_output += "</method>"

            for signal_name, args in self._signal_signatures.items():
                xml_output += "<signal name='%s'>" % signal_name

                for signature in args:
                    xml_output += "<arg type='%s'/>" % signature

                xml_output += "</signal>"

            xml_output += "</interface></node>"

            registration_id = self._bus.register_object(
                self._object_path,
                Gio.DBusNodeInfo.new_for_xml(xml_output).interfaces[0],
                self.on_method_call,
                self.on_get_property,
                None
            )

            if not registration_id:
                raise GLib.Error("Failed to register object with path %s" % self._object_path)

            self._registration_id = registration_id

        def unregister(self):

            if self._registration_id is None:
                return

            self._bus.unregister_object(self._registration_id)
            self._registration_id = None

        def _add_property(self, name, signature):
            self._property_signatures[name] = signature
            self._property_values[name] = None

        def _remove_property(self, name):
            del self._property_signatures[name]
            del self._property_values[name]

        def set_property_value(self, name, value):
            self._property_values[name] = value

        def get_property_value(self, name):
            return self._property_values[name]

        def _add_signal(self, name, signature):
            self._signal_signatures[name] = signature

        def _remove_signal(self, name):
            del self._signal_signatures[name]

        def emit_signal(self, name, *args):

            self._bus.emit_signal(
                None,
                self._object_path,
                self._interface_name,
                name,
                GLib.Variant("(%s)" % "".join(self._signal_signatures[name]), args)
            )

        def _add_method(self, name, in_args, out_args, callback):
            self._method_signatures[name] = (in_args, out_args)
            self._method_callbacks[name] = callback

        def _remove_method(self, name):
            del self._method_signatures[name]
            del self._method_callbacks[name]

        def on_method_call(self, _connection, _sender, _path, _interface_name, method_name, parameters, invocation):

            _in_args, out_args = self._method_signatures[method_name]
            callback = self._method_callbacks[method_name]
            result = callback(*parameters.unpack())
            return_value = None

            if out_args:
                return_value = GLib.Variant("(%s)" % "".join(out_args), result)

            invocation.return_value(return_value)

        def on_get_property(self, _connection, _sender, _path, _interface_name, property_name):

            return GLib.Variant(
                self._property_signatures[property_name],
                self._property_values[property_name]
            )

    class DBusMenuService(DBusService):

        def __init__(self):

            super().__init__(
                interface_name="com.canonical.dbusmenu",
                object_path="/org/ayatana/NotificationItem/Nicotine/Menu",
                bus_type=Gio.BusType.SESSION
            )

            self._items = OrderedDict()
            self._revision = 0

            for method_name, in_args, out_args, callback in (
                ("GetGroupProperties", ("ai", "as"), ("a(ia{sv})",), self.on_get_group_properties),
                ("GetLayout", ("i", "i", "as"), ("u", "(ia{sv}av)"), self.on_get_layout),
                ("Event", ("i", "s", "v", "u"), (), self.on_event),
            ):
                self._add_method(method_name, in_args, out_args, callback)

            for signal_name, value in (
                ("LayoutUpdated", ("u", "i")),
            ):
                self._add_signal(signal_name, value)

        def set_items(self, items):

            self._items = items

            self._revision += 1
            self.emit_signal("LayoutUpdated", self._revision, 0)

        @staticmethod
        def _serialize_item(item):

            if "text" in item:
                props = {
                    "label": GLib.Variant("s", item["text"]),
                    "enabled": GLib.Variant("b", item["sensitive"]),
                    "visible": GLib.Variant("b", item["visible"])
                }

                if item.get("toggled") is not None:
                    props["toggle-type"] = GLib.Variant("s", "checkmark")
                    props["toggle-state"] = GLib.Variant("i", int(item["toggled"]))

                return props

            return {"type": GLib.Variant("s", "separator")}

        def on_get_group_properties(self, ids, _properties):

            item_properties = []

            for idx, item in self._items.items():
                if idx in ids:
                    item_properties.append((idx, self._serialize_item(item)))

            return (item_properties,)

        def on_get_layout(self, _parent_id, _recursion_depth, _property_names):

            serialized_items = []

            for idx, item in self._items.items():
                serialized_item = GLib.Variant("(ia{sv}av)", (idx, self._serialize_item(item), []))
                serialized_items.append(serialized_item)

            return (self._revision, (0, {}, serialized_items))

        def on_event(self, idx, event_id, _data, _timestamp):

            if event_id != "clicked":
                return

            self._items[idx]["callback"]()

    class StatusNotifierItemService(DBusService):

        def __init__(self, activate_callback):

            super().__init__(
                interface_name="org.kde.StatusNotifierItem",
                object_path="/org/ayatana/NotificationItem/Nicotine",
                bus_type=Gio.BusType.SESSION
            )

            self.menu = StatusNotifierImplementation.DBusMenuService()

            for property_name, signature in (
                ("Category", "s"),
                ("Id", "s"),
                ("Title", "s"),
                ("ToolTip", "(sa(iiay)ss)"),
                ("Menu", "o"),
                ("ItemIsMenu", "b"),
                ("IconName", "s"),
                ("IconThemePath", "s"),
                ("Status", "s")
            ):
                self._add_property(property_name, signature)

            for property_name, value in (
                ("Category", "Communications"),
                ("Id", config.application_id),
                ("Title", config.application_name),
                ("ToolTip", ("", [], config.application_name, "")),
                ("Menu", "/org/ayatana/NotificationItem/Nicotine/Menu"),
                ("ItemIsMenu", False),
                ("IconName", ""),
                ("IconThemePath", ""),
                ("Status", "Active")
            ):
                self.set_property_value(property_name, value)

            for method_name, in_args, out_args, callback in (
                ("Activate", ("i", "i"), (), activate_callback),
            ):
                self._add_method(method_name, in_args, out_args, callback)

            for signal_name, value in (
                ("NewIcon", ()),
                ("NewIconThemePath", ("s",)),
                ("NewStatus", ("s",))
            ):
                self._add_signal(signal_name, value)

        def register(self):
            self.menu.register()
            super().register()

        def unregister(self):
            super().unregister()
            self.menu.unregister()

    def __init__(self, frame, core):

        super().__init__(frame, core)

        self.tray_icon = None
        self.custom_icons = False

        try:
            self.bus = Gio.bus_get_sync(Gio.BusType.SESSION)
            self.tray_icon = self.StatusNotifierItemService(activate_callback=frame.on_window_hide_unhide)
            self.tray_icon.register()

            self.bus.call_sync(
                "org.kde.StatusNotifierWatcher",
                "/StatusNotifierWatcher",
                "org.kde.StatusNotifierWatcher",
                "RegisterStatusNotifierItem",
                GLib.Variant("(s)", ("/org/ayatana/NotificationItem/Nicotine",)),
                None,
                Gio.DBusCallFlags.NONE, -1
            )

        except GLib.Error as error:
            if self.tray_icon is not None:
                self.tray_icon.unregister()

            raise ImplementationUnavailable("StatusNotifier implementation not available: %s" % error) from error

        self.update_menu()
        self.update_icon_theme()

    @staticmethod
    def check_icon_path(icon_name, icon_path):
        """ Check if tray icons exist in the specified icon path """

        if not icon_path:
            return False

        icon_scheme = config.application_id + "-" + icon_name + "."

        try:
            with os.scandir(encode_path(icon_path)) as entries:
                for entry in entries:
                    if entry.is_file() and entry.name.decode("utf-8", "replace").startswith(icon_scheme):
                        return True

        except OSError as error:
            log.add_debug("Error accessing tray icon path %(path)s: %(error)s" %
                          {"path": icon_path, "error": error})

        return False

    def get_icon_path(self):
        """ Returns an icon path to use for tray icons, or None to fall back to
        system-wide icons. """

        self.custom_icons = False
        custom_icon_path = os.path.join(config.data_dir, ".nicotine-icon-theme")

        if hasattr(sys, "real_prefix") or sys.base_prefix != sys.prefix:
            # Virtual environment
            local_icon_path = os.path.join(sys.prefix, "share", "icons", "hicolor", "scalable", "status")
        else:
            # Git folder
            local_icon_path = os.path.join(GTK_GUI_DIR, "icons", "hicolor", "scalable", "status")

        for icon_name in ("away", "connect", "disconnect", "msg"):

            # Check if custom icons exist
            if self.check_icon_path(icon_name, custom_icon_path):
                self.custom_icons = True
                return custom_icon_path

            # Check if local icons exist
            if self.check_icon_path(icon_name, local_icon_path):
                return local_icon_path

        return ""

    def set_icon_name(self, icon_name):

        if self.custom_icons:
            # Use alternative icon names to enforce custom icons, since system-wide icons take precedence
            icon_name = icon_name.replace(config.application_id, "nplus-tray")

        self.tray_icon.set_property_value("IconName", icon_name)
        self.tray_icon.emit_signal("NewIcon")

    def update_icon_theme(self):

        # If custom icon path was found, use it, otherwise we fall back to system icons
        icon_path = self.get_icon_path()
        self.tray_icon.set_property_value("IconThemePath", icon_path)
        self.tray_icon.emit_signal("NewIconThemePath", icon_path)

        self.update_icon()

        if icon_path:
            log.add_debug("Using tray icon path %s", icon_path)

    def update_menu(self):
        self.tray_icon.menu.set_items(self.menu_items)

    def is_visible(self):
        return self.tray_icon.get_property_value("Status") == "Active"

    def show(self):

        status = "Active"
        self.tray_icon.set_property_value("Status", status)
        self.tray_icon.emit_signal("NewStatus", status)

    def hide(self):

        status = "Passive"
        self.tray_icon.set_property_value("Status", status)
        self.tray_icon.emit_signal("NewStatus", status)


class StatusIconImplementation(BaseImplementation):

    def __init__(self, frame, core):

        super().__init__(frame, core)

        if not hasattr(Gtk, "StatusIcon") or sys.platform == "darwin" or os.getenv("WAYLAND_DISPLAY"):
            # GtkStatusIcon does not work on macOS and Wayland
            raise ImplementationUnavailable("StatusIcon implementation not available")

        self.tray_icon = Gtk.StatusIcon(tooltip_text=config.application_name)
        self.tray_icon.connect("activate", self.frame.on_window_hide_unhide)
        self.tray_icon.connect("popup-menu", self.on_status_icon_popup)

        self.gtk_menu = self.build_gtk_menu()

    def on_status_icon_popup(self, _status_icon, button, _activate_time):

        if button == 3:
            time = Gtk.get_current_event_time()
            self.gtk_menu.popup(None, None, None, None, button, time)

    @staticmethod
    def set_item_text(item, text):
        BaseImplementation.set_item_text(item, text)
        item["gtk_menu_item"].set_label(text)

    @staticmethod
    def set_item_sensitive(item, sensitive):
        BaseImplementation.set_item_sensitive(item, sensitive)
        item["gtk_menu_item"].set_sensitive(sensitive)

    @staticmethod
    def set_item_visible(item, visible):
        BaseImplementation.set_item_visible(item, visible)
        item["gtk_menu_item"].set_visible(visible)

    @staticmethod
    def set_item_toggled(item, toggled):

        BaseImplementation.set_item_toggled(item, toggled)
        gtk_menu_item = item["gtk_menu_item"]

        with gtk_menu_item.handler_block(item["gtk_handler"]):
            gtk_menu_item.set_active(toggled)

    def build_gtk_menu(self):

        gtk_menu = Gtk.Menu()

        for item in self.menu_items.values():
            text = item.get("text")

            if text is None:
                gtk_menu_item = Gtk.SeparatorMenuItem()
            else:
                if "toggled" in item:
                    gtk_menu_item = Gtk.CheckMenuItem.new_with_label(text)
                else:
                    gtk_menu_item = Gtk.MenuItem.new_with_label(text)

                item["gtk_handler"] = gtk_menu_item.connect("activate", item["callback"])

            item["gtk_menu_item"] = gtk_menu_item

            gtk_menu_item.show()
            gtk_menu.append(gtk_menu_item)

        return gtk_menu

    def set_icon_name(self, icon_name):
        self.tray_icon.set_from_icon_name(icon_name)

    def is_visible(self):
        return self.tray_icon.get_visible() and self.tray_icon.is_embedded()

    def show(self):

        if self.is_visible():
            return

        self.tray_icon.set_visible(True)

    def hide(self):

        if not self.is_visible():
            return

        self.tray_icon.set_visible(False)


class TrayIcon:

    def __init__(self, frame, core):

        self.frame = frame
        self.core = core
        self.available = True
        self.implementation = None

        self.watch_availability()
        self.load()

    def watch_availability(self):

        if sys.platform in ("win32", "darwin"):
            return

        Gio.bus_watch_name(
            Gio.BusType.SESSION,
            "org.kde.StatusNotifierWatcher",
            Gio.BusNameWatcherFlags.NONE,
            self.load,
            None
        )

    def load(self, *_args):

        self.available = True

        if sys.platform == "win32":
            # Always keep tray icon loaded for Windows notification support
            pass

        elif not config.sections["ui"]["trayicon"]:
            # No need to have tray icon loaded now (unless this is Windows)
            return

        if self.implementation is None:
            try:
                self.implementation = StatusNotifierImplementation(self.frame, self.core)

            except ImplementationUnavailable:
                try:
                    self.implementation = StatusIconImplementation(self.frame, self.core)

                except ImplementationUnavailable:
                    self.available = False
                    return

            self.refresh_state()

        if config.sections["ui"]["trayicon"]:
            self.show()
            return

        self.hide()

    def update_window_visibility(self):
        if self.implementation:
            self.implementation.update_window_visibility()

    def update_user_status(self):
        if self.implementation:
            self.implementation.update_user_status()

    def update_alternative_speed_limit_status(self):
        if self.implementation:
            self.implementation.update_alternative_speed_limit_status()

    def update_icon(self, force_update=False):
        if self.implementation:
            self.implementation.update_icon(force_update)

    def update_icon_theme(self):
        if self.implementation:
            self.implementation.update_icon_theme()

    def set_download_status(self, status):
        if self.implementation:
            self.implementation.set_download_status(status)

    def set_upload_status(self, status):
        if self.implementation:
            self.implementation.set_upload_status(status)

    def refresh_state(self):

        self.update_icon(force_update=True)
        self.update_window_visibility()
        self.update_user_status()
        self.update_alternative_speed_limit_status()

    def is_visible(self):

        if self.implementation:
            return self.implementation.is_visible()

        return False

    def show(self):
        if self.implementation:
            self.implementation.show()

    def hide(self):
        if self.implementation:
            self.implementation.hide()
