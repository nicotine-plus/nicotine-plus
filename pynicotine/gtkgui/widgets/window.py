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

import os
import sys

from gi.repository import Gtk

from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.application import GTK_MINOR_VERSION
from pynicotine.gtkgui.application import GTK_MICRO_VERSION
from pynicotine.gtkgui.application import LIBADWAITA_API_VERSION


class Window:

    DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1 = 19
    DWMWA_USE_IMMERSIVE_DARK_MODE = 20

    active_dialogs = []  # Class variable keeping dialog objects alive
    activation_token = None

    def __init__(self, widget):

        self.widget = widget
        self._dark_mode_handler = None
        self._text_widget = None

        if GTK_API_VERSION == 3:
            return

        self.widget.connect("notify::focus-widget", self._on_focus_widget_changed)

        if sys.platform == "win32":
            widget.connect("realize", self._on_realize_win32)

            # Use dark window controls on Windows when requested
            if LIBADWAITA_API_VERSION:
                from gi.repository import Adw  # pylint: disable=no-name-in-module
                self._dark_mode_handler = Adw.StyleManager.get_default().connect(
                    "notify::dark", self._on_dark_mode_win32
                )

        elif os.environ.get("GDK_BACKEND") == "broadway":
            # Workaround for GTK 4 bug where broadwayd uses a lot of CPU after hiding window
            self.widget.connect("hide", self._on_hide_broadway)

    def _on_focus_widget_changed(self, *_args):

        focus_widget = self.widget.get_focus()

        if focus_widget is None:
            return

        popover = focus_widget.get_ancestor(Gtk.Popover)

        # Workaround for GTK 4 bug where broadwayd uses a lot of CPU after hiding popover
        if popover is not None and os.environ.get("GDK_BACKEND") == "broadway":
            popover.hide_handler_broadway = popover.connect_after("hide", self._on_popover_hide_broadway)

        if not (4, 16, 0) <= (GTK_API_VERSION, GTK_MINOR_VERSION, GTK_MICRO_VERSION) <= (4, 16, 5):
            return

        # Workaround for GTK 4.16 bug where text is replaced when inserting emoji
        if not isinstance(popover, Gtk.EmojiChooser):
            self._text_widget = focus_widget if isinstance(focus_widget, Gtk.Text) else None
            return

        if self._text_widget is None:
            return

        popover.old_text = self._text_widget.get_text()
        popover.old_pos = self._text_widget.get_position()

        popover.picked_handler = popover.connect("emoji-picked", self._on_emoji_chooser_picked)
        popover.hide_handler = popover.connect("hide", self._on_emoji_chooser_hide)

    def _on_emoji_chooser_picked(self, chooser, emoji):

        old_text = chooser.old_text
        old_pos = chooser.old_pos
        new_text = old_text[:old_pos] + emoji + old_text[old_pos:]

        self._text_widget.set_text(new_text)
        self._text_widget.set_position(old_pos + len(emoji))

    def _on_emoji_chooser_hide(self, chooser):

        if chooser.picked_handler is not None:
            chooser.disconnect(chooser.picked_handler)
            chooser.picked_handler = None

        if chooser.hide_handler is not None:
            chooser.disconnect(chooser.hide_handler)
            chooser.hide_handler = None

    def _on_popover_hide_broadway(self, popover):

        if popover.hide_handler_broadway is not None:
            popover.disconnect(popover.hide_handler_broadway)
            popover.hide_handler_broadway = None

        popover.unrealize()

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

    def _on_hide_broadway(self, *_args):
        self.widget.unrealize()

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

    def maximize(self):
        self.widget.maximize()

    def unmaximize(self):
        self.widget.unmaximize()

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

        if self._dark_mode_handler is not None:
            from gi.repository import Adw  # pylint: disable=no-name-in-module
            Adw.StyleManager.get_default().disconnect(self._dark_mode_handler)

        self.widget.destroy()
        self.__dict__.clear()
