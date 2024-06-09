# COPYRIGHT (C) 2022-2024 Nicotine+ Contributors
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

import sys

from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import Gtk

from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.application import LIBADWAITA_API_VERSION


class Window:

    DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1 = 19
    DWMWA_USE_IMMERSIVE_DARK_MODE = 20

    active_dialogs = []  # Class variable keeping dialog objects alive
    activation_token = None

    def __init__(self, widget):

        self.widget = widget

        if GTK_API_VERSION == 3:
            return

        if sys.platform == "win32":
            widget.connect("realize", self._on_realize_win32)

            # Use dark window controls on Windows when requested
            if LIBADWAITA_API_VERSION:
                from gi.repository import Adw  # pylint: disable=no-name-in-module
                Adw.StyleManager.get_default().connect("notify::dark", self._on_dark_mode_win32)

        elif sys.platform == "darwin":
            # Workaround to restore Ctrl-click to show context menu on macOS
            gesture_click = Gtk.GestureClick()
            gesture_click.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
            gesture_click.connect("pressed", self._on_click_gtk4_darwin)
            widget.add_controller(gesture_click)  # pylint: disable=no-member

    def _menu_popup(self, controller, widget):
        if controller.is_active():
            widget.activate_action("menu.popup")

    def _on_realize_win32(self, *_args):

        from ctypes import windll

        # Don't overlap taskbar when auto-hidden
        h_wnd = self.get_surface().get_handle()
        windll.user32.SetPropW(h_wnd, "NonRudeHWND", True)

        # Set dark window controls
        if LIBADWAITA_API_VERSION:
            from gi.repository import Adw  # pylint: disable=no-name-in-module
            self._on_dark_mode_win32(Adw.StyleManager.get_default())

    def _on_dark_mode_win32(self, style_manager, *_args):

        surface = self.get_surface()

        if surface is None:
            return

        h_wnd = surface.get_handle()

        if h_wnd is None:
            return

        from ctypes import byref, c_int, sizeof, windll

        value = c_int(int(style_manager.get_dark()))

        if not windll.dwmapi.DwmSetWindowAttribute(
            h_wnd, self.DWMWA_USE_IMMERSIVE_DARK_MODE, byref(value), sizeof(value)
        ):
            windll.dwmapi.DwmSetWindowAttribute(
                h_wnd, self.DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1, byref(value), sizeof(value)
            )

    def _on_click_gtk4_darwin(self, controller, _num_p, pos_x, pos_y, *_args):

        event = controller.get_last_event()

        if not event.get_modifier_state() & Gdk.ModifierType.CONTROL_MASK:
            return False

        cursor_widget = self.widget.pick(pos_x, pos_y, Gtk.PickFlags.DEFAULT)
        widget = cursor_widget.get_ancestor(Gtk.Text)

        if widget is None:
            widget = cursor_widget.get_ancestor(Gtk.TextView)

        if widget is None:
            widget = cursor_widget.get_ancestor(Gtk.Label)

        if widget is not None:
            GLib.idle_add(self._menu_popup, controller, widget)

        return False

    def get_surface(self):

        if GTK_API_VERSION >= 4:
            return self.widget.get_surface()

        return self.widget.get_window()

    def get_width(self):

        if GTK_API_VERSION >= 4:
            return self.widget.get_width()

        width, _height = self.widget.get_size()
        return width

    def get_height(self):

        if GTK_API_VERSION >= 4:
            return self.widget.get_height()

        _width, height = self.widget.get_size()
        return height

    def get_position(self):

        if GTK_API_VERSION >= 4:
            return None

        return self.widget.get_position()

    def is_active(self):
        return self.widget.is_active()

    def is_maximized(self):
        return self.widget.is_maximized()

    def is_visible(self):
        return self.widget.get_visible()

    def set_title(self, title):
        self.widget.set_title(title)

    def present(self):

        if self.activation_token is not None:
            # Set XDG activation token if provided by tray icon
            self.widget.set_startup_id(self.activation_token)

        self.widget.present()

    def hide(self):
        self.widget.set_visible(False)

    def close(self, *_args):
        self.widget.close()

    def destroy(self):
        self.widget.destroy()
        self.__dict__.clear()
