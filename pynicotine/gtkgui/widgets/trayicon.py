# COPYRIGHT (C) 2020-2023 Nicotine+ Contributors
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

from gi.repository import Gio
from gi.repository import GLib

from pynicotine.config import config
from pynicotine.core import core
from pynicotine.gtkgui.application import GTK_GUI_DIR
from pynicotine.gtkgui.widgets.dialogs import EntryDialog
from pynicotine.logfacility import log
from pynicotine.slskmessages import UserStatus
from pynicotine.utils import encode_path


""" Tray Icon """


class ImplementationUnavailable(Exception):
    pass


class BaseImplementation:

    def __init__(self, application):

        self.application = application
        self.menu_items = {}
        self.menu_item_id = 1

        self.create_menu()

    def unload(self):
        # Implemented in subclasses
        pass

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

        self.show_item = self.create_item(_("Show Nicotine+"), self.on_window_hide_unhide)
        self.hide_item = self.create_item(_("Hide Nicotine+"), self.on_window_hide_unhide)

        self.create_item()

        self.downloads_item = self.create_item(_("Downloads"), self.on_downloads)
        self.uploads_item = self.create_item(_("Uploads"), self.on_uploads)

        self.create_item()

        self.connect_item = self.create_item(_("Connect"), self.application.on_connect)
        self.disconnect_item = self.create_item(_("Disconnect"), self.application.on_disconnect)
        self.away_item = self.create_item(_("Away"), self.application.on_away, check=True)

        self.create_item()

        self.send_message_item = self.create_item(_("Send Message"), self.on_open_private_chat)
        self.lookup_info_item = self.create_item(_("View User Profile"), self.on_get_a_users_info)
        self.lookup_shares_item = self.create_item(_("Browse Shares"), self.on_get_a_users_shares)

        self.create_item()

        self.create_item(_("Preferences"), self.application.on_preferences)
        self.create_item(_("Quit"), core.quit)

    def update_window_visibility(self):

        if self.application.window is None:
            return

        visible = self.application.window.is_visible()

        self.set_item_visible(self.show_item, not visible)
        self.set_item_visible(self.hide_item, visible)

        self.update_menu()

    def update_user_status(self):

        sensitive = core.user_status != UserStatus.OFFLINE

        for item in (self.away_item, self.send_message_item,
                     self.lookup_info_item, self.lookup_shares_item):

            # Disable menu items when disconnected from server
            self.set_item_sensitive(item, sensitive)

        self.set_item_visible(self.connect_item, not sensitive)
        self.set_item_visible(self.disconnect_item, sensitive)
        self.set_item_toggled(self.away_item, core.user_status == UserStatus.AWAY)

        self.update_icon()
        self.update_menu()

    def update_icon(self, force_update=False):

        if not force_update and not self.is_visible():
            return

        # Check for highlights, and display highlight icon if there is a highlighted room or private chat
        if (self.application.window
                and (self.application.window.chatrooms.highlighted_rooms
                     or self.application.window.privatechat.highlighted_users)):
            icon_name = "msg"

        elif core.user_status == UserStatus.ONLINE:
            icon_name = "connect"

        elif core.user_status == UserStatus.AWAY:
            icon_name = "away"

        else:
            icon_name = "disconnect"

        icon_name = f"{config.application_id}-{icon_name}"
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

    def on_window_hide_unhide(self, *_args):

        if self.application.window.is_visible():
            self.application.window.hide()
            return

        self.application.window.show()

    def on_downloads(self, *_args):
        self.application.window.change_main_page(self.application.window.downloads_page)
        self.application.window.show()

    def on_uploads(self, *_args):
        self.application.window.change_main_page(self.application.window.uploads_page)
        self.application.window.show()

    def on_open_private_chat_response(self, dialog, _response_id, _data):

        user = dialog.get_entry_value()

        if not user:
            return

        core.privatechat.show_user(user)
        self.application.window.show()

    def on_open_private_chat(self, *_args):

        EntryDialog(
            parent=self.application.window,
            title=_("Start Messaging"),
            message=_("Enter the name of the user whom you want to send a message:"),
            callback=self.on_open_private_chat_response,
            droplist=sorted(core.userlist.buddies)
        ).show()

    def on_get_a_users_info_response(self, dialog, _response_id, _data):

        user = dialog.get_entry_value()

        if not user:
            return

        core.userinfo.show_user(user)
        self.application.window.show()

    def on_get_a_users_info(self, *_args):

        EntryDialog(
            parent=self.application.window,
            title=_("View User Profile"),
            message=_("Enter the name of the user whose profile you want to see:"),
            callback=self.on_get_a_users_info_response,
            droplist=sorted(core.userlist.buddies)
        ).show()

    def on_get_a_users_shares_response(self, dialog, _response_id, _data):

        user = dialog.get_entry_value()

        if not user:
            return

        core.userbrowse.browse_user(user)
        self.application.window.show()

    def on_get_a_users_shares(self, *_args):

        EntryDialog(
            parent=self.application.window,
            title=_("Browse Shares"),
            message=_("Enter the name of the user whose shares you want to see:"),
            callback=self.on_get_a_users_shares_response,
            droplist=sorted(core.userlist.buddies)
        ).show()

    def is_visible(self):  # pylint:disable=no-self-use
        # Implemented in subclasses
        return False

    def set_visible(self, _visible):
        # Implemented in subclasses
        pass


class StatusNotifierImplementation(BaseImplementation):

    class DBusProperty:

        def __init__(self, name, signature, value):

            self.name = name
            self.signature = signature
            self.value = value

    class DBusSignal:

        def __init__(self, name, args):
            self.name = name
            self.args = args

    class DBusMethod:

        def __init__(self, name, in_args, out_args, callback):

            self.name = name
            self.in_args = in_args
            self.out_args = out_args
            self.callback = callback

    class DBusService:

        def __init__(self, interface_name, object_path, bus_type):

            self._interface_name = interface_name
            self._object_path = object_path

            self._bus = Gio.bus_get_sync(bus_type)
            self._registration_id = None
            self.properties = {}
            self.signals = {}
            self.methods = {}

        def register(self):

            xml_output = f"<node name='/'><interface name='{self._interface_name}'>"

            for property_name, prop in self.properties.items():
                xml_output += f"<property name='{property_name}' type='{prop.signature}' access='read'/>"

            for method_name, method in self.methods.items():
                xml_output += f"<method name='{method_name}'>"

                for in_signature in method.in_args:
                    xml_output += f"<arg type='{in_signature}' direction='in'/>"
                for out_signature in method.out_args:
                    xml_output += f"<arg type='{out_signature}' direction='out'/>"

                xml_output += "</method>"

            for signal_name, signal in self.signals.items():
                xml_output += f"<signal name='{signal_name}'>"

                for signature in signal.args:
                    xml_output += f"<arg type='{signature}'/>"

                xml_output += "</signal>"

            xml_output += "</interface></node>"

            registration_id = self._bus.register_object(
                object_path=self._object_path,
                interface_info=Gio.DBusNodeInfo.new_for_xml(xml_output).interfaces[0],
                method_call_closure=self.on_method_call,
                get_property_closure=self.on_get_property
            )

            if not registration_id:
                raise GLib.Error(f"Failed to register object with path {self._object_path}")

            self._registration_id = registration_id

        def unregister(self):

            if self._registration_id is None:
                return

            self._bus.unregister_object(self._registration_id)
            self._registration_id = None

        def add_property(self, name, signature, value):
            self.properties[name] = StatusNotifierImplementation.DBusProperty(name, signature, value)

        def add_signal(self, name, args):
            self.signals[name] = StatusNotifierImplementation.DBusSignal(name, args)

        def add_method(self, name, in_args, out_args, callback):
            self.methods[name] = StatusNotifierImplementation.DBusMethod(name, in_args, out_args, callback)

        def emit_signal(self, name, *args):

            arg_types = "".join(self.signals[name].args)

            self._bus.emit_signal(
                destination_bus_name=None,
                object_path=self._object_path,
                interface_name=self._interface_name,
                signal_name=name,
                parameters=GLib.Variant(f"({arg_types})", args)
            )

        def on_method_call(self, _connection, _sender, _path, _interface_name, method_name, parameters, invocation):

            method = self.methods[method_name]
            result = method.callback(*parameters.unpack())
            out_arg_types = "".join(method.out_args)
            return_value = None

            if method.out_args:
                return_value = GLib.Variant(f"({out_arg_types})", result)

            invocation.return_value(return_value)

        def on_get_property(self, _connection, _sender, _path, _interface_name, property_name):
            prop = self.properties[property_name]
            return GLib.Variant(prop.signature, prop.value)

    class DBusMenuService(DBusService):

        def __init__(self):

            super().__init__(
                interface_name="com.canonical.dbusmenu",
                object_path="/org/ayatana/NotificationItem/Nicotine/Menu",
                bus_type=Gio.BusType.SESSION
            )

            self._items = {}
            self._revision = 0

            for method_name, in_args, out_args, callback in (
                ("GetGroupProperties", ("ai", "as"), ("a(ia{sv})",), self.on_get_group_properties),
                ("GetLayout", ("i", "i", "as"), ("u", "(ia{sv}av)"), self.on_get_layout),
                ("Event", ("i", "s", "v", "u"), (), self.on_event),
            ):
                self.add_method(method_name, in_args, out_args, callback)

            for signal_name, value in (
                ("LayoutUpdated", ("u", "i")),
            ):
                self.add_signal(signal_name, value)

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

            return self._revision, (0, {}, serialized_items)

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

            for property_name, signature, value in (
                ("Category", "s", "Communications"),
                ("Id", "s", config.application_id),
                ("Title", "s", config.application_name),
                ("ToolTip", "(sa(iiay)ss)", ("", [], config.application_name, "")),
                ("Menu", "o", "/org/ayatana/NotificationItem/Nicotine/Menu"),
                ("ItemIsMenu", "b", False),
                ("IconName", "s", ""),
                ("IconThemePath", "s", ""),
                ("Status", "s", "Active")
            ):
                self.add_property(property_name, signature, value)

            for method_name, in_args, out_args, callback in (
                ("Activate", ("i", "i"), (), activate_callback),
            ):
                self.add_method(method_name, in_args, out_args, callback)

            for signal_name, value in (
                ("NewIcon", ()),
                ("NewIconThemePath", ("s",)),
                ("NewStatus", ("s",))
            ):
                self.add_signal(signal_name, value)

        def register(self):
            self.menu.register()
            super().register()

        def unregister(self):
            super().unregister()
            self.menu.unregister()

    def __init__(self, application):

        super().__init__(application)

        self.tray_icon = None
        self.custom_icons = False

        try:
            self.bus = Gio.bus_get_sync(bus_type=Gio.BusType.SESSION)
            self.tray_icon = self.StatusNotifierItemService(activate_callback=self.on_window_hide_unhide)
            self.tray_icon.register()

            self.bus.call_sync(
                bus_name="org.kde.StatusNotifierWatcher",
                object_path="/StatusNotifierWatcher",
                interface_name="org.kde.StatusNotifierWatcher",
                method_name="RegisterStatusNotifierItem",
                parameters=GLib.Variant("(s)", ("/org/ayatana/NotificationItem/Nicotine",)),
                reply_type=None,
                flags=Gio.DBusCallFlags.NONE,
                timeout_msec=-1
            )

        except GLib.Error as error:
            self.unload()
            raise ImplementationUnavailable(f"StatusNotifier implementation not available: {error}") from error

        self.update_menu()
        self.update_icon_theme()

    def unload(self):
        if self.tray_icon is not None:
            self.tray_icon.unregister()

    @staticmethod
    def check_icon_path(icon_name, icon_path):
        """ Check if tray icons exist in the specified icon path """

        if not icon_path:
            return False

        icon_scheme = f"{config.application_id}-{icon_name}."

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

        self.tray_icon.properties["IconName"].value = icon_name
        self.tray_icon.emit_signal("NewIcon")

    def update_icon_theme(self):

        # If custom icon path was found, use it, otherwise we fall back to system icons
        icon_path = self.get_icon_path()
        self.tray_icon.properties["IconThemePath"].value = icon_path
        self.tray_icon.emit_signal("NewIconThemePath", icon_path)

        self.update_icon()

        if icon_path:
            log.add_debug("Using tray icon path %s", icon_path)

    def update_menu(self):
        self.tray_icon.menu.set_items(self.menu_items)

    def is_visible(self):
        return self.tray_icon.properties["Status"].value == "Active"

    def set_visible(self, visible):

        status = "Active" if visible else "Passive"

        self.tray_icon.properties["Status"].value = status
        self.tray_icon.emit_signal("NewStatus", status)


class TrayIcon:

    def __init__(self, application):

        self.application = application
        self.available = True
        self.implementation = None

        self.watch_availability()
        self.load()

    def watch_availability(self):

        if sys.platform in ("win32", "darwin"):
            return

        Gio.bus_watch_name(
            bus_type=Gio.BusType.SESSION,
            name="org.kde.StatusNotifierWatcher",
            flags=Gio.BusNameWatcherFlags.NONE,
            name_appeared_closure=self.load,
            name_vanished_closure=self.unload
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
                self.implementation = StatusNotifierImplementation(self.application)

            except ImplementationUnavailable:
                self.available = False
                return

            self.refresh_state()

        self.set_visible(config.sections["ui"]["trayicon"])

    def unload(self, *_args):

        self.available = False

        if self.implementation:
            self.implementation.unload()
            self.implementation = None

    def update_window_visibility(self):
        if self.implementation:
            self.implementation.update_window_visibility()

    def update_user_status(self):
        if self.implementation:
            self.implementation.update_user_status()

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

    def is_visible(self):

        if self.implementation:
            return self.implementation.is_visible()

        return False

    def set_visible(self, visible):
        if self.implementation:
            self.implementation.set_visible(visible)
