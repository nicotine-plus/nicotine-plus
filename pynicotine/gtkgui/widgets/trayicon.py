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

import pynicotine
from pynicotine import slskmessages
from pynicotine.config import config
from pynicotine.core import core
from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.application import GTK_GUI_FOLDER_PATH
from pynicotine.gtkgui.widgets.theme import ICON_THEME
from pynicotine.gtkgui.widgets.window import Window
from pynicotine.logfacility import log
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

        self.create_menu()

    def create_item(self, text=None, callback=None, check=False):

        item = {"id": self.menu_item_id, "sensitive": True}

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
    def set_item_toggled(item, toggled):
        item["toggled"] = toggled

    def create_menu(self):

        self.show_hide_item = self.create_item("default", self.application.on_window_hide_unhide)

        self.create_item()

        self.downloads_item = self.create_item(_("Downloads"), self.application.on_downloads)
        self.uploads_item = self.create_item(_("Uploads"), self.application.on_uploads)

        self.create_item()

        self.create_item(_("Private Chat"), self.application.on_private_chat)
        self.create_item(_("Chat Rooms"), self.application.on_chat_rooms)
        self.create_item(_("Searches"), self.application.on_searches)

        self.create_item()

        self.connect_disconnect_item = self.create_item("default", self.application.on_connect_disconnect)
        self.away_item = self.create_item(_("Away"), self.application.on_away, check=True)

        self.create_item()

        self.create_item(_("Preferences"), self.application.on_preferences)
        self.create_item(_("_Quit"), self.application.on_quit_request)

    def update_window_visibility(self):

        if self.application.window is None:
            return

        if self.application.window.is_visible():
            label = _("Hide Nicotine+")
        else:
            label = _("Show Nicotine+")

        self.set_item_text(self.show_hide_item, label)
        self.update_menu()

    def update_user_status(self):

        sensitive = core.users.login_status != slskmessages.UserStatus.OFFLINE
        label = _("_Disconnect") if sensitive else _("_Connect")

        self.set_item_sensitive(self.away_item, sensitive)

        self.set_item_text(self.connect_disconnect_item, label)
        self.set_item_toggled(self.away_item, core.users.login_status == slskmessages.UserStatus.AWAY)

        self.update_icon()
        self.update_menu()

    def update_icon(self):

        # Check for highlights, and display highlight icon if there is a highlighted room or private chat
        if (self.application.window
                and (self.application.window.chatrooms.highlighted_rooms
                     or self.application.window.privatechat.highlighted_users)):
            icon_name = "msg"

        elif core.users.login_status == slskmessages.UserStatus.ONLINE:
            icon_name = "connect"

        elif core.users.login_status == slskmessages.UserStatus.AWAY:
            icon_name = "away"

        else:
            icon_name = "disconnect"

        icon_name = f"{pynicotine.__application_id__}-{icon_name}"
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

    def show_notification(self, title, message):
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
                object_path="/StatusNotifierItem/menu",
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
                    "enabled": GLib.Variant("b", item["sensitive"])
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
            if event_id == "clicked":
                self._items[idx]["callback"]()

    class StatusNotifierItemService(DBusService):

        def __init__(self, activate_callback):

            super().__init__(
                interface_name="org.kde.StatusNotifierItem",
                object_path="/StatusNotifierItem",
                bus_type=Gio.BusType.SESSION
            )

            self.menu = StatusNotifierImplementation.DBusMenuService()

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

        def on_provide_activation_token(self, token):
            Window.activation_token = token

    def __init__(self, application):

        super().__init__(application)

        self.tray_icon = None
        self.custom_icons = False

        try:
            self.bus = Gio.bus_get_sync(bus_type=Gio.BusType.SESSION)
            self.tray_icon = self.StatusNotifierItemService(activate_callback=self.activate_callback)
            self.tray_icon.register()

            self.bus.call_sync(
                bus_name="org.kde.StatusNotifierWatcher",
                object_path="/StatusNotifierWatcher",
                interface_name="org.kde.StatusNotifierWatcher",
                method_name="RegisterStatusNotifierItem",
                parameters=GLib.Variant("(s)", (self.bus.get_unique_name(),)),
                reply_type=None,
                flags=Gio.DBusCallFlags.NONE,
                timeout_msec=-1
            )

        except GLib.Error as error:
            self.unload()
            raise ImplementationUnavailable(f"StatusNotifier implementation not available: {error}") from error

        self.update_menu()

    @staticmethod
    def check_icon_path(icon_name, icon_path):
        """Check if tray icons exist in the specified icon path."""

        if not icon_path:
            return False

        icon_scheme = f"{pynicotine.__application_id__}-{icon_name}."

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
            icon_name = icon_name.replace(pynicotine.__application_id__, "nplus-tray")

        self.tray_icon.properties["IconName"].value = icon_name
        self.tray_icon.emit_signal("NewIcon")

        if not self.is_visible:
            return

        status = "Active"

        if self.tray_icon.properties["Status"].value != status:
            self.tray_icon.properties["Status"].value = status
            self.tray_icon.emit_signal("NewStatus", status)

    def update_icon_theme(self):

        # If custom icon path was found, use it, otherwise we fall back to system icons
        icon_path = self.get_icon_path()
        self.tray_icon.properties["IconThemePath"].value = icon_path
        self.tray_icon.emit_signal("NewIconThemePath", icon_path)

        if icon_path:
            log.add_debug("Using tray icon path %s", icon_path)

    def update_menu(self):
        self.tray_icon.menu.set_items(self.menu_items)

    def unload(self, is_shutdown=True):

        if self.tray_icon is None:
            return

        status = "Passive"

        self.tray_icon.properties["Status"].value = status
        self.tray_icon.emit_signal("NewStatus", status)

        if is_shutdown:
            self.tray_icon.unregister()


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

        self._register_class()
        self._create_window()
        self.update_icon()

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

    def _update_notify_icon(self, title="", message="", icon_name=None):
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

        action = self.NIM_MODIFY

        if self._notify_id is None:
            self._notify_id = self.NOTIFYICONDATAW(
                cb_size=sizeof(self.NOTIFYICONDATAW),
                h_wnd=self._h_wnd,
                u_id=0,
                u_flags=(self.NIF_ICON | self.NIF_MESSAGE | self.NIF_TIP | self.NIF_INFO),
                u_callback_message=self.WM_TRAYICON,
                sz_tip=truncate_string_byte(pynicotine.__application_name__, byte_limit=127)
            )
            action = self.NIM_ADD

        if config.sections["notifications"]["notification_popup_sound"]:
            self._notify_id.dw_info_flags &= ~self.NIIF_NOSOUND
        else:
            self._notify_id.dw_info_flags |= self.NIIF_NOSOUND

        self._notify_id.h_icon = self._h_icon
        self._notify_id.sz_info_title = truncate_string_byte(title, byte_limit=63, ellipsize=True)
        self._notify_id.sz_info = truncate_string_byte(message, byte_limit=255, ellipsize=True)

        windll.shell32.Shell_NotifyIconW(action, byref(self._notify_id))

    def _remove_notify_icon(self):

        from ctypes import byref, windll

        if self._notify_id:
            windll.shell32.Shell_NotifyIconW(self.NIM_DELETE, byref(self._notify_id))
            self._notify_id = None

        if self._menu:
            windll.user32.DestroyMenu(self._menu)
            self._menu = None

    def _serialize_menu_item(self, item):
        # pylint: disable=attribute-defined-outside-init,no-member

        from ctypes import sizeof

        item_info = self.MENUITEMINFOW(cb_size=sizeof(self.MENUITEMINFOW))
        w_id = item["id"]
        text = item.get("text")
        is_checked = item.get("toggled")
        is_sensitive = item.get("sensitive")

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

        if is_sensitive is not None:
            item_info.f_mask |= self.MIIM_STATE
            item_info.f_state |= self.MFS_ENABLED if is_sensitive else self.MFS_DISABLED

        return item_info

    def _show_menu(self):

        from ctypes import byref, windll, wintypes

        if self._menu is None:
            self.update_menu()

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

    def update_menu(self):

        from ctypes import byref, windll

        if self._menu is None:
            self._menu = windll.user32.CreatePopupMenu()

        for item in self.menu_items.values():
            item_id = item["id"]
            item_info = self._serialize_menu_item(item)

            if not windll.user32.SetMenuItemInfoW(self._menu, item_id, False, byref(item_info)):
                windll.user32.InsertMenuItemW(self._menu, item_id, False, byref(item_info))

    def set_icon_name(self, icon_name):
        self._update_notify_icon(icon_name=icon_name)

    def show_notification(self, title, message):
        self._update_notify_icon(title=title, message=message)

    def on_process_window_message(self, h_wnd, msg, w_param, l_param):

        from ctypes import windll, wintypes

        if msg == self.WM_TRAYICON:
            if l_param == self.WM_RBUTTONUP:
                # Icon pressed
                self._show_menu()

            elif l_param == self.WM_LBUTTONUP:
                # Icon pressed
                self.activate_callback()

            elif l_param in (self.NIN_BALLOONHIDE, self.NIN_BALLOONTIMEOUT, self.NIN_BALLOONUSERCLICK):
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

    def unload(self, is_shutdown=True):

        self._remove_notify_icon()

        if not is_shutdown:
            # Keep notification support as long as we're running
            return

        self._destroy_h_icon()
        self._destroy_window()
        self._unregister_class()


class TrayIcon:

    def __init__(self, application):

        self.application = application
        self.available = True
        self.implementation = None

        self.watch_availability()
        self.load()

    def watch_availability(self):

        if sys.platform in {"win32", "darwin"}:
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
            if sys.platform == "win32":
                self.implementation = Win32Implementation(self.application)
            else:
                try:
                    self.implementation = StatusNotifierImplementation(self.application)

                except ImplementationUnavailable:
                    self.available = False
                    return

        self.refresh_state()

    def update_window_visibility(self):
        if self.implementation:
            self.implementation.update_window_visibility()

    def update_user_status(self):
        if self.implementation:
            self.implementation.update_user_status()

    def update_icon(self):
        if self.implementation:
            self.implementation.update_icon()

    def update_icon_theme(self):
        if self.implementation:
            self.implementation.update_icon_theme()

    def set_download_status(self, status):
        if self.implementation:
            self.implementation.set_download_status(status)

    def set_upload_status(self, status):
        if self.implementation:
            self.implementation.set_upload_status(status)

    def show_notification(self, title, message):
        if self.implementation:
            self.implementation.show_notification(title=title, message=message)

    def refresh_state(self):

        if not self.implementation:
            return

        self.implementation.is_visible = True

        self.update_icon_theme()
        self.update_icon()
        self.update_window_visibility()
        self.update_user_status()

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
