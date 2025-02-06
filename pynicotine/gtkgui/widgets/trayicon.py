# COPYRIGHT (C) 2020-2024 Nicotine+ Contributors
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

from gi.repository import GdkPixbuf
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk

import pynicotine
from pynicotine.config import config
from pynicotine.core import core
from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.application import GTK_GUI_FOLDER_PATH
from pynicotine.gtkgui.widgets.theme import ICON_THEME
from pynicotine.gtkgui.widgets.window import Window
from pynicotine.logfacility import log
from pynicotine.slskmessages import UserStatus
from pynicotine.utils import encode_path
from pynicotine.utils import truncate_string_byte


class ImplementationUnavailable(Exception):
    pass


class BaseImplementation:

    def __init__(self, application):

        self.application = application
        self.menu_items = {}
        self.menu_item_id = 1
        self.activate_callback = application.on_window_hide_unhide
        self.is_visible = True

        self._create_menu()

    def _create_item(self, text=None, callback=None, check=False):

        item = {"id": self.menu_item_id, "visible": True}

        if text is not None:
            item["text"] = text

        if callback is not None:
            item["callback"] = callback

        if check:
            item["toggled"] = False

        self.menu_items[self.menu_item_id] = item
        self.menu_item_id += 1

        return item

    def _set_item_text(self, item, text):
        item["text"] = text

    def _set_item_visible(self, item, visible):
        item["visible"] = visible

    def _set_item_toggled(self, item, toggled):
        item["toggled"] = toggled

    def _create_menu(self):

        self.show_hide_item = self._create_item("placeholder", self.application.on_window_hide_unhide)

        self._create_item()

        self.downloads_item = self._create_item(_("Downloads"), self.application.on_downloads)
        self.uploads_item = self._create_item(_("Uploads"), self.application.on_uploads)

        self._create_item()

        self._create_item(_("Private Chat"), self.application.on_private_chat)
        self._create_item(_("Chat Rooms"), self.application.on_chat_rooms)
        self._create_item(_("Searches"), self.application.on_searches)

        self._create_item()

        self.away_item = self._create_item(_("Away"), self.application.on_away, check=True)
        self.connect_item = self._create_item(_("_Connect"), self.application.on_connect)
        self.disconnect_item = self._create_item(_("_Disconnect"), self.application.on_disconnect)

        self._create_item()

        self._create_item(_("Preferences"), self.application.on_preferences)
        self._create_item(_("_Quit"), self.application.on_quit_request)

    def _update_window_visibility(self):

        if self.application.window is None:
            return

        label = _("Hide Nicotine+") if self.application.window.is_visible() else _("Show Nicotine+")

        if self.show_hide_item.get("text") != label:
            self._set_item_text(self.show_hide_item, label)

    def _update_user_status(self):

        should_update = False
        connect_visible = core.users.login_status == UserStatus.OFFLINE
        away_visible = not connect_visible
        away_toggled = core.users.login_status == UserStatus.AWAY

        if self.connect_item.get("visible") != connect_visible:
            self._set_item_visible(self.connect_item, connect_visible)
            should_update = True

        if self.disconnect_item.get("visible") == connect_visible:
            self._set_item_visible(self.disconnect_item, not connect_visible)
            should_update = True

        if self.away_item.get("visible") != away_visible:
            self._set_item_visible(self.away_item, away_visible)
            should_update = True

        if self.away_item.get("toggled") != away_toggled:
            self._set_item_toggled(self.away_item, away_toggled)
            should_update = True

        if should_update:
            self._update_icon()

    def _update_icon(self):

        # Check for highlights, and display highlight icon if there is a highlighted room or private chat
        if (self.application.window
                and (self.application.window.chatrooms.highlighted_rooms
                     or self.application.window.privatechat.highlighted_users)):
            icon_name = "msg"

        elif core.users.login_status == UserStatus.ONLINE:
            icon_name = "connect"

        elif core.users.login_status == UserStatus.AWAY:
            icon_name = "away"

        else:
            icon_name = "disconnect"

        icon_name = f"{pynicotine.__application_id__}-{icon_name}"
        self._set_icon_name(icon_name)

    def _set_icon_name(self, icon_name):
        # Implemented in subclasses
        pass

    def _update_icon_theme(self):
        # Implemented in subclasses
        pass

    def update(self):

        self.is_visible = config.sections["ui"]["trayicon"]

        self._update_icon_theme()
        self._update_icon()
        self._update_window_visibility()
        self._update_user_status()

    def set_download_status(self, status):
        self._set_item_text(self.downloads_item, status)

    def set_upload_status(self, status):
        self._set_item_text(self.uploads_item, status)

    def show_notification(self, title, message, action=None, action_target=None, high_priority=False):
        # Implemented in subclasses
        pass

    def unload(self, is_shutdown=True):
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
                get_property_closure=self.on_get_property,
                set_property_closure=None
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

        def _emit_signal(self, name, parameters=None):

            self._bus.emit_signal(
                destination_bus_name=None,
                object_path=self._object_path,
                interface_name=self._interface_name,
                signal_name=name,
                parameters=parameters
            )

        def on_method_call(self, _connection, _sender, _path, _interface_name, method_name, parameters, invocation):

            method = self.methods[method_name]
            out_parameters = method.callback(*parameters.unpack())

            invocation.return_value(out_parameters)

        def on_get_property(self, _connection, _sender, _path, _interface_name, property_name):
            prop = self.properties[property_name]
            return GLib.Variant(prop.signature, prop.value)

    class DBusMenuService(DBusService):

        def __init__(self, menu_items):

            super().__init__(
                interface_name="com.canonical.dbusmenu",
                object_path="/StatusNotifierItem/menu",
                bus_type=Gio.BusType.SESSION
            )

            self._items = menu_items

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

        def update_item(self, item):

            item_id = item["id"]

            if item_id not in self._items:
                return

            self._items[item_id] = item

            self._emit_signal(
                name="ItemsPropertiesUpdated",
                parameters=GLib.Variant.new_tuple(
                    GLib.Variant.new_array(
                        children=[
                            GLib.Variant.new_tuple(
                                GLib.Variant.new_int32(item_id),
                                GLib.Variant.new_array(children=self._serialize_item(item))
                            )
                        ],
                    ),
                    GLib.Variant.new_array(child_type=GLib.VariantType("(ias)"))
                )
            )

        @staticmethod
        def _serialize_item(item):

            def dict_entry(key, value):
                return GLib.Variant.new_dict_entry(
                    GLib.Variant.new_string(key),
                    GLib.Variant.new_variant(value)
                )

            props = []

            if "text" in item:
                props.append(dict_entry("label", GLib.Variant.new_string(item["text"])))

                if item.get("toggled") is not None:
                    props.append(dict_entry("toggle-type", GLib.Variant.new_string("checkmark")))
                    props.append(dict_entry("toggle-state", GLib.Variant.new_int32(int(item["toggled"]))))
            else:
                props.append(dict_entry("type", GLib.Variant.new_string("separator")))

            props.append(dict_entry("visible", GLib.Variant.new_boolean(item["visible"])))
            return props

        def on_get_group_properties(self, ids, _properties):

            item_properties = []
            requested_ids = set(ids)

            for idx, item in self._items.items():
                # According to the spec, if no IDs are requested, we should send the entire menu
                if requested_ids and idx not in requested_ids:
                    continue

                item_properties.append(
                    GLib.Variant.new_tuple(
                        GLib.Variant.new_int32(idx),
                        GLib.Variant.new_array(children=self._serialize_item(item))
                    )
                )

            return GLib.Variant.new_tuple(
                GLib.Variant.new_array(children=item_properties)
            )

        def on_get_layout(self, _parent_id, _recursion_depth, _property_names):

            revision = 0
            serialized_items = []

            for idx, item in self._items.items():
                serialized_item = GLib.Variant.new_variant(
                    GLib.Variant.new_tuple(
                        GLib.Variant.new_int32(idx),
                        GLib.Variant.new_array(children=self._serialize_item(item)),
                        GLib.Variant.new_array(child_type=GLib.VariantType("v"))
                    )
                )
                serialized_items.append(serialized_item)

            return GLib.Variant.new_tuple(
                GLib.Variant.new_uint32(revision),
                GLib.Variant.new_tuple(
                    GLib.Variant.new_int32(0),
                    GLib.Variant.new_array(child_type=GLib.VariantType("{sv}")),
                    GLib.Variant.new_array(children=serialized_items)
                )
            )

        def on_event(self, idx, event_id, _data, _timestamp):
            if event_id == "clicked":
                self._items[idx]["callback"]()

    class StatusNotifierItemService(DBusService):

        def __init__(self, activate_callback, menu_items):

            super().__init__(
                interface_name="org.kde.StatusNotifierItem",
                object_path="/StatusNotifierItem",
                bus_type=Gio.BusType.SESSION
            )

            self.menu = StatusNotifierImplementation.DBusMenuService(menu_items)

            for property_name, signature, value in (
                ("Category", "s", "Communications"),
                ("Id", "s", pynicotine.__application_id__),
                ("Title", "s", pynicotine.__application_name__),
                ("ToolTip", "(sa(iiay)ss)", ("", [], pynicotine.__application_name__, "")),
                ("Menu", "o", "/StatusNotifierItem/menu"),
                ("ItemIsMenu", "b", False),
                ("IconName", "s", ""),
                ("IconThemePath", "s", ""),
                ("Status", "s", "Active")
            ):
                self.add_property(property_name, signature, value)

            for method_name, in_args, out_args, callback in (
                ("Activate", ("i", "i"), (), activate_callback),
                ("ProvideXdgActivationToken", ("s",), (), self.on_provide_activation_token)
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

        def update_icon(self):
            self._emit_signal("NewIcon")

        def update_icon_theme(self, icon_path):

            self._emit_signal(
                name="NewIconThemePath",
                parameters=GLib.Variant.new_tuple(
                    GLib.Variant.new_string(icon_path)
                )
            )

        def update_status(self, status):

            self._emit_signal(
                name="NewStatus",
                parameters=GLib.Variant.new_tuple(
                    GLib.Variant.new_string(status)
                )
            )

        def on_provide_activation_token(self, token):
            Window.activation_token = token

    def __init__(self, application):

        super().__init__(application)

        self.tray_icon = None
        self.custom_icons = False

        try:
            self.bus = Gio.bus_get_sync(bus_type=Gio.BusType.SESSION)
            self.tray_icon = self.StatusNotifierItemService(
                activate_callback=self.activate_callback,
                menu_items=self.menu_items
            )
            self.tray_icon.register()

            self.bus.call_sync(
                bus_name="org.kde.StatusNotifierWatcher",
                object_path="/StatusNotifierWatcher",
                interface_name="org.kde.StatusNotifierWatcher",
                method_name="RegisterStatusNotifierItem",
                parameters=GLib.Variant.new_tuple(
                    GLib.Variant.new_string(self.bus.get_unique_name())
                ),
                reply_type=None,
                flags=Gio.DBusCallFlags.NONE,
                timeout_msec=1000,
                cancellable=None
            )

        except GLib.Error as error:
            self.unload()
            raise ImplementationUnavailable(f"StatusNotifier implementation not available: {error}") from error

    @staticmethod
    def _check_icon_path(icon_name, icon_path):
        """Check if tray icons exist in the specified icon path."""

        if not icon_path:
            return False

        icon_path_encoded = encode_path(icon_path)

        if not os.path.isdir(icon_path_encoded):
            return False

        icon_scheme = f"{pynicotine.__application_id__}-{icon_name}.".encode()

        try:
            with os.scandir(icon_path_encoded) as entries:
                for entry in entries:
                    if entry.is_file() and entry.name.startswith(icon_scheme):
                        return True

        except OSError as error:
            log.add_debug("Error accessing tray icon path %s: %s", (icon_path, error))

        return False

    def _get_icon_path(self):
        """Returns an icon path to use for tray icons, or None to fall back to
        system-wide icons."""

        self.custom_icons = False
        custom_icon_path = os.path.join(config.data_folder_path, ".nicotine-icon-theme")

        if hasattr(sys, "real_prefix") or sys.base_prefix != sys.prefix:
            # Virtual environment
            local_icon_path = os.path.join(sys.prefix, "share", "icons", "hicolor", "scalable", "apps")
        else:
            # Git folder
            local_icon_path = os.path.join(GTK_GUI_FOLDER_PATH, "icons", "hicolor", "scalable", "apps")

        for icon_name in ("away", "connect", "disconnect", "msg"):
            # Check if custom icons exist
            if config.sections["ui"]["icontheme"] and self._check_icon_path(icon_name, custom_icon_path):
                self.custom_icons = True
                return custom_icon_path

            # Check if local icons exist
            if self._check_icon_path(icon_name, local_icon_path):
                return local_icon_path

        return ""

    def _set_icon_name(self, icon_name):

        icon_name_property = self.tray_icon.properties["IconName"]

        if self.custom_icons:
            # Use alternative icon names to enforce custom icons, since system-wide icons take precedence
            icon_name = icon_name.replace(pynicotine.__application_id__, "nplus-tray")

        if icon_name_property.value != icon_name:
            icon_name_property.value = icon_name
            self.tray_icon.update_icon()

        if not self.is_visible:
            return

        status_property = self.tray_icon.properties["Status"]
        status = "Active"

        if status_property.value != status:
            status_property.value = status
            self.tray_icon.update_status(status)

    def _update_icon_theme(self):

        # If custom icon path was found, use it, otherwise we fall back to system icons
        icon_path = self._get_icon_path()
        icon_path_property = self.tray_icon.properties["IconThemePath"]

        if icon_path_property.value == icon_path:
            return

        icon_path_property.value = icon_path
        self.tray_icon.update_icon_theme(icon_path)

        if icon_path:
            log.add_debug("Using tray icon path %s", icon_path)

    def _set_item_text(self, item, text):
        super()._set_item_text(item, text)
        self.tray_icon.menu.update_item(item)

    def _set_item_visible(self, item, visible):
        super()._set_item_visible(item, visible)
        self.tray_icon.menu.update_item(item)

    def _set_item_toggled(self, item, toggled):
        super()._set_item_toggled(item, toggled)
        self.tray_icon.menu.update_item(item)

    def unload(self, is_shutdown=True):

        if self.tray_icon is None:
            return

        status_property = self.tray_icon.properties["Status"]
        status = "Passive"

        if status_property.value != status:
            status_property.value = status
            self.tray_icon.update_status(status)

        if is_shutdown:
            self.tray_icon.unregister()
            self.tray_icon = None


class Win32Implementation(BaseImplementation):
    """Windows NotifyIcon implementation.

    https://learn.microsoft.com/en-us/windows/win32/shell/notification-area
    https://learn.microsoft.com/en-us/windows/win32/shell/taskbar
    """

    WINDOW_CLASS_NAME = "NicotineTrayIcon"

    NIM_ADD = 0
    NIM_MODIFY = 1
    NIM_DELETE = 2

    NIF_MESSAGE = 1
    NIF_ICON = 2
    NIF_TIP = 4
    NIF_INFO = 16
    NIF_REALTIME = 64
    NIIF_NOSOUND = 16

    MIIM_STATE = 1
    MIIM_ID = 2
    MIIM_STRING = 64

    MFS_ENABLED = 0
    MFS_UNCHECKED = 0
    MFS_DISABLED = 3
    MFS_CHECKED = 8

    MFT_SEPARATOR = 2048

    WM_NULL = 0
    WM_DESTROY = 2
    WM_CLOSE = 16
    WM_COMMAND = 273
    WM_LBUTTONUP = 514
    WM_RBUTTONUP = 517
    WM_USER = 1024
    WM_TRAYICON = (WM_USER + 1)
    NIN_BALLOONHIDE = (WM_USER + 3)
    NIN_BALLOONTIMEOUT = (WM_USER + 4)
    NIN_BALLOONUSERCLICK = (WM_USER + 5)

    CS_VREDRAW = 1
    CS_HREDRAW = 2
    COLOR_WINDOW = 5
    IDC_ARROW = 32512

    WS_OVERLAPPED = 0
    WS_SYSMENU = 524288
    CW_USEDEFAULT = -2147483648

    IMAGE_ICON = 1
    LR_LOADFROMFILE = 16
    SM_CXSMICON = 49

    if sys.platform == "win32":
        from ctypes import Structure

        class WNDCLASSW(Structure):
            from ctypes import CFUNCTYPE, wintypes

            LPFN_WND_PROC = CFUNCTYPE(
                wintypes.INT,
                wintypes.HWND,
                wintypes.UINT,
                wintypes.WPARAM,
                wintypes.LPARAM
            )
            _fields_ = [
                ("style", wintypes.UINT),
                ("lpfn_wnd_proc", LPFN_WND_PROC),
                ("cb_cls_extra", wintypes.INT),
                ("cb_wnd_extra", wintypes.INT),
                ("h_instance", wintypes.HINSTANCE),
                ("h_icon", wintypes.HICON),
                ("h_cursor", wintypes.HANDLE),
                ("hbr_background", wintypes.HBRUSH),
                ("lpsz_menu_name", wintypes.LPCWSTR),
                ("lpsz_class_name", wintypes.LPCWSTR)
            ]

        class MENUITEMINFOW(Structure):
            from ctypes import wintypes

            _fields_ = [
                ("cb_size", wintypes.UINT),
                ("f_mask", wintypes.UINT),
                ("f_type", wintypes.UINT),
                ("f_state", wintypes.UINT),
                ("w_id", wintypes.UINT),
                ("h_sub_menu", wintypes.HMENU),
                ("hbmp_checked", wintypes.HBITMAP),
                ("hbmp_unchecked", wintypes.HBITMAP),
                ("dw_item_data", wintypes.LPVOID),
                ("dw_type_data", wintypes.LPWSTR),
                ("cch", wintypes.UINT),
                ("hbmp_item", wintypes.HBITMAP)
            ]

        class NOTIFYICONDATAW(Structure):
            from ctypes import wintypes

            _fields_ = [
                ("cb_size", wintypes.DWORD),
                ("h_wnd", wintypes.HWND),
                ("u_id", wintypes.UINT),
                ("u_flags", wintypes.UINT),
                ("u_callback_message", wintypes.UINT),
                ("h_icon", wintypes.HICON),
                ("sz_tip", wintypes.WCHAR * 128),
                ("dw_state", wintypes.DWORD),
                ("dw_state_mask", wintypes.DWORD),
                ("sz_info", wintypes.WCHAR * 256),
                ("u_version", wintypes.UINT),
                ("sz_info_title", wintypes.WCHAR * 64),
                ("dw_info_flags", wintypes.DWORD),
                ("guid_item", wintypes.CHAR * 16),
                ("h_balloon_icon", wintypes.HICON)
            ]

    def __init__(self, application):

        from ctypes import windll

        super().__init__(application)

        self._window_class = None
        self._h_wnd = None
        self._notify_id = None
        self._h_icon = None
        self._menu = None
        self._wm_taskbarcreated = windll.user32.RegisterWindowMessageW("TaskbarCreated")
        self._click_action = None
        self._click_action_target = None

        self._register_class()
        self._create_window()

    def _register_class(self):

        from ctypes import byref, windll

        self._window_class = self.WNDCLASSW(
            style=(self.CS_VREDRAW | self.CS_HREDRAW),
            lpfn_wnd_proc=self.WNDCLASSW.LPFN_WND_PROC(self.on_process_window_message),
            h_cursor=windll.user32.LoadCursorW(0, self.IDC_ARROW),
            hbr_background=self.COLOR_WINDOW,
            lpsz_class_name=self.WINDOW_CLASS_NAME
        )

        windll.user32.RegisterClassW(byref(self._window_class))

    def _unregister_class(self):

        if self._window_class is None:
            return

        from ctypes import windll

        windll.user32.UnregisterClassW(self.WINDOW_CLASS_NAME, self._window_class.h_instance)
        self._window_class = None

    def _create_window(self):

        from ctypes import windll

        style = self.WS_OVERLAPPED | self.WS_SYSMENU
        self._h_wnd = windll.user32.CreateWindowExW(
            0,
            self.WINDOW_CLASS_NAME,
            self.WINDOW_CLASS_NAME,
            style,
            0,
            0,
            self.CW_USEDEFAULT,
            self.CW_USEDEFAULT,
            0,
            0,
            0,
            None
        )

        windll.user32.UpdateWindow(self._h_wnd)

    def _destroy_window(self):

        if self._h_wnd is None:
            return

        from ctypes import windll

        windll.user32.DestroyWindow(self._h_wnd)
        self._h_wnd = None

    def _load_ico_buffer(self, icon_name, icon_size):

        ico_buffer = b""

        if GTK_API_VERSION >= 4:
            icon = ICON_THEME.lookup_icon(icon_name, fallbacks=None, size=icon_size, scale=1, direction=0, flags=0)
            icon_path = icon.get_file().get_path()

            if not icon_path:
                return ico_buffer

            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(icon_path, icon_size, icon_size)
        else:
            icon = ICON_THEME.lookup_icon(icon_name, size=icon_size, flags=0)

            if not icon:
                return ico_buffer

            pixbuf = icon.load_icon()

        _success, ico_buffer = pixbuf.save_to_bufferv("ico")
        return ico_buffer

    def _load_h_icon(self, icon_name):

        from ctypes import windll

        # Attempt to load custom icons first
        icon_size = windll.user32.GetSystemMetrics(self.SM_CXSMICON)
        ico_buffer = self._load_ico_buffer(
            icon_name.replace(f"{pynicotine.__application_id__}-", "nplus-tray-"), icon_size)

        if not ico_buffer:
            # No custom icons present, fall back to default icons
            ico_buffer = self._load_ico_buffer(icon_name, icon_size)

        try:
            import tempfile
            file_handle = tempfile.NamedTemporaryFile(delete=False)

            with file_handle:
                file_handle.write(ico_buffer)

            return windll.user32.LoadImageA(
                0,
                encode_path(file_handle.name),
                self.IMAGE_ICON,
                icon_size,
                icon_size,
                self.LR_LOADFROMFILE
            )

        finally:
            os.remove(file_handle.name)

    def _destroy_h_icon(self):

        from ctypes import windll

        if self._h_icon:
            windll.user32.DestroyIcon(self._h_icon)
            self._h_icon = None

    def _update_notify_icon(self, title="", message="", icon_name=None, click_action=None,
                            click_action_target=None, high_priority=False):
        # pylint: disable=attribute-defined-outside-init,no-member

        if self._h_wnd is None:
            return

        if icon_name:
            self._destroy_h_icon()
            self._h_icon = self._load_h_icon(icon_name)

        if not self.is_visible and not (title or message):
            # When disabled by user, temporarily show tray icon when displaying a notification
            return

        from ctypes import byref, sizeof, windll

        notify_action = self.NIM_MODIFY

        if self._notify_id is None:
            self._notify_id = self.NOTIFYICONDATAW(
                cb_size=sizeof(self.NOTIFYICONDATAW),
                h_wnd=self._h_wnd,
                u_id=0,
                u_flags=(self.NIF_ICON | self.NIF_MESSAGE | self.NIF_TIP | self.NIF_INFO),
                u_callback_message=self.WM_TRAYICON,
                sz_tip=truncate_string_byte(pynicotine.__application_name__, byte_limit=127)
            )
            notify_action = self.NIM_ADD

        if config.sections["notifications"]["notification_popup_sound"]:
            self._notify_id.dw_info_flags &= ~self.NIIF_NOSOUND
        else:
            self._notify_id.dw_info_flags |= self.NIIF_NOSOUND

        if high_priority:
            self._notify_id.u_flags &= ~self.NIF_REALTIME
        else:
            self._notify_id.u_flags |= self.NIF_REALTIME

        self._notify_id.h_icon = self._h_icon
        self._notify_id.sz_info_title = truncate_string_byte(title, byte_limit=63, ellipsize=True)
        self._notify_id.sz_info = truncate_string_byte(message, byte_limit=255, ellipsize=True)

        self._click_action = click_action.replace("app.", "") if click_action else None
        self._click_action_target = GLib.Variant.new_string(click_action_target) if click_action_target else None

        windll.shell32.Shell_NotifyIconW(notify_action, byref(self._notify_id))

    def _remove_notify_icon(self):

        from ctypes import byref, windll

        if self._notify_id:
            windll.shell32.Shell_NotifyIconW(self.NIM_DELETE, byref(self._notify_id))
            self._notify_id = None

        self._destroy_menu()

    def _serialize_menu_item(self, item):
        # pylint: disable=attribute-defined-outside-init,no-member

        from ctypes import sizeof

        item_info = self.MENUITEMINFOW(cb_size=sizeof(self.MENUITEMINFOW))
        w_id = item["id"]
        text = item.get("text")
        is_checked = item.get("toggled")

        item_info.f_mask |= self.MIIM_ID
        item_info.w_id = w_id

        if text is not None:
            item_info.f_mask |= self.MIIM_STRING
            item_info.dw_type_data = text.replace("_", "&")  # Mnemonics use &
        else:
            item_info.f_type |= self.MFT_SEPARATOR

        if is_checked is not None:
            item_info.f_mask |= self.MIIM_STATE
            item_info.f_state |= self.MFS_CHECKED if is_checked else self.MFS_UNCHECKED

        return item_info

    def _show_menu(self):

        from ctypes import byref, windll, wintypes

        self._populate_menu()

        pos = wintypes.POINT()
        windll.user32.GetCursorPos(byref(pos))

        # PRB: Menus for Notification Icons Do Not Work Correctly
        # https://web.archive.org/web/20121015064650/http://support.microsoft.com/kb/135788

        windll.user32.SetForegroundWindow(self._h_wnd)
        windll.user32.TrackPopupMenu(
            self._menu,
            0,
            pos.x,
            pos.y,
            0,
            self._h_wnd,
            None
        )
        windll.user32.PostMessageW(self._h_wnd, self.WM_NULL, 0, 0)

    def _populate_menu(self):

        from ctypes import byref, windll

        self._destroy_menu()

        if self._menu is None:
            self._menu = windll.user32.CreatePopupMenu()

        for item in self.menu_items.values():
            if not item["visible"]:
                continue

            item_id = item["id"]
            item_info = self._serialize_menu_item(item)

            windll.user32.InsertMenuItemW(self._menu, item_id, False, byref(item_info))

    def _destroy_menu(self):

        if self._menu is None:
            return

        from ctypes import windll

        windll.user32.DestroyMenu(self._menu)
        self._menu = None

    def _set_icon_name(self, icon_name):
        self._update_notify_icon(icon_name=icon_name)

    def on_process_window_message(self, h_wnd, msg, w_param, l_param):

        from ctypes import windll, wintypes

        if msg == self.WM_TRAYICON:
            if l_param == self.WM_RBUTTONUP:
                # Icon pressed
                self._show_menu()

            elif l_param == self.WM_LBUTTONUP:
                # Icon pressed
                self.activate_callback()

            elif l_param in {self.NIN_BALLOONHIDE, self.NIN_BALLOONTIMEOUT, self.NIN_BALLOONUSERCLICK}:
                if l_param == self.NIN_BALLOONUSERCLICK and self._click_action is not None:
                    # Notification was clicked, perform action
                    self.application.lookup_action(self._click_action).activate(self._click_action_target)
                    self._click_action = self._click_action_target = None

                if not config.sections["ui"]["trayicon"]:
                    # Notification dismissed, but user has disabled tray icon
                    self._remove_notify_icon()

        elif msg == self.WM_COMMAND:
            # Menu item pressed
            menu_item_id = w_param & 0xFFFF
            menu_item_callback = self.menu_items[menu_item_id]["callback"]
            menu_item_callback()

        elif msg == self._wm_taskbarcreated:
            # Taskbar process restarted, create new icon
            self._remove_notify_icon()
            self._update_notify_icon()

        return windll.user32.DefWindowProcW(
            wintypes.HWND(h_wnd),
            msg,
            wintypes.WPARAM(w_param),
            wintypes.LPARAM(l_param)
        )

    def show_notification(self, title, message, action=None, action_target=None, high_priority=False):

        self._update_notify_icon(
            title=title, message=message, click_action=action, click_action_target=action_target,
            high_priority=high_priority)

    def unload(self, is_shutdown=True):

        self._remove_notify_icon()

        if not is_shutdown:
            # Keep notification support as long as we're running
            return

        self._destroy_h_icon()
        self._destroy_window()
        self._unregister_class()


class StatusIconImplementation(BaseImplementation):

    def __init__(self, application):

        super().__init__(application)

        if not hasattr(Gtk, "StatusIcon") or os.environ.get("WAYLAND_DISPLAY"):
            # GtkStatusIcon does not work on Wayland
            raise ImplementationUnavailable("StatusIcon implementation not available")

        self.tray_icon = Gtk.StatusIcon(tooltip_text=pynicotine.__application_name__)
        self.tray_icon.connect("activate", self.activate_callback)
        self.tray_icon.connect("popup-menu", self.on_status_icon_popup)

        self.gtk_menu = self._build_gtk_menu()
        GLib.idle_add(self._update_icon, priority=GLib.PRIORITY_HIGH_IDLE)

    def on_status_icon_popup(self, _status_icon, button, _activate_time):

        if button == 3:
            time = Gtk.get_current_event_time()
            self.gtk_menu.popup(None, None, None, None, button, time)

    def _set_item_text(self, item, text):
        super()._set_item_text(item, text)
        item["gtk_menu_item"].set_label(text)

    def _set_item_visible(self, item, visible):
        super()._set_item_visible(item, visible)
        item["gtk_menu_item"].set_visible(visible)

    def _set_item_toggled(self, item, toggled):

        super()._set_item_toggled(item, toggled)
        gtk_menu_item = item["gtk_menu_item"]

        with gtk_menu_item.handler_block(item["gtk_handler"]):
            gtk_menu_item.set_active(toggled)

    def _build_gtk_menu(self):

        gtk_menu = Gtk.Menu()

        for item in self.menu_items.values():
            text = item.get("text")

            if text is None:
                item["gtk_menu_item"] = gtk_menu_item = Gtk.SeparatorMenuItem(visible=True)
            else:
                gtk_menu_item_class = Gtk.CheckMenuItem if "toggled" in item else Gtk.MenuItem
                item["gtk_menu_item"] = gtk_menu_item = gtk_menu_item_class(
                    label=text, use_underline=True, visible=True
                )
                item["gtk_handler"] = gtk_menu_item.connect("activate", item["callback"])

            gtk_menu.append(gtk_menu_item)

        return gtk_menu

    def _set_icon_name(self, icon_name):

        if not self.tray_icon.get_visible():
            self.tray_icon.set_visible(True)

        if self.tray_icon.is_embedded() and self.tray_icon.get_icon_name() != icon_name:
            self.tray_icon.set_from_icon_name(icon_name)

    def unload(self, is_shutdown=True):
        if self.tray_icon.get_visible():
            self.tray_icon.set_visible(False)


class TrayIcon:

    def __init__(self, application):

        self.application = application
        self.available = True
        self.implementation = None
        self.watch_id = None

        self._watch_availability()
        self.load()

    def _watch_availability(self):

        if sys.platform in {"win32", "darwin"}:
            return

        if self.watch_id is not None:
            return

        self.watch_id = Gio.bus_watch_name(
            bus_type=Gio.BusType.SESSION,
            name="org.kde.StatusNotifierWatcher",
            flags=Gio.BusNameWatcherFlags.NONE,
            name_appeared_closure=self.load,
            name_vanished_closure=self.unload
        )

    def _unwatch_availability(self):

        if self.watch_id is not None:
            Gio.bus_unwatch_name(self.watch_id)
            self.watch_id = None

    def load(self, *_args):

        self.available = True

        if sys.platform == "win32":
            # Always keep tray icon loaded for Windows notification support
            pass

        elif not config.sections["ui"]["trayicon"]:
            # No need to have tray icon loaded now (unless this is Windows)
            return

        if self.implementation is None:
            if sys.platform == "win32":
                self.implementation = Win32Implementation(self.application)

            elif sys.platform == "darwin":
                self.available = False

            else:
                try:
                    self.implementation = StatusNotifierImplementation(self.application)

                except ImplementationUnavailable:
                    try:
                        self.implementation = StatusIconImplementation(self.application)
                        self._unwatch_availability()

                    except ImplementationUnavailable:
                        self.available = False
                        return

        self.update()

    def set_download_status(self, status):
        if self.implementation:
            self.implementation.set_download_status(status)

    def set_upload_status(self, status):
        if self.implementation:
            self.implementation.set_upload_status(status)

    def show_notification(self, title, message, action=None, action_target=None, high_priority=False):

        if self.implementation:
            self.implementation.show_notification(
                title=title, message=message, action=action, action_target=action_target,
                high_priority=high_priority)

    def update(self):
        if self.implementation:
            self.implementation.update()

    def unload(self, *_args, is_shutdown=True):

        if self.implementation:
            self.implementation.unload(is_shutdown=is_shutdown)
            self.implementation.is_visible = False

        if is_shutdown:
            self.implementation = None
            self.available = False

    def destroy(self):
        self.unload()
        self.__dict__.clear()
