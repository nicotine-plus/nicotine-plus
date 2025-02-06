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

from gi.repository import Gtk

from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.widgets.theme import add_css_class


class Popover:

    def __init__(self, window, content_box=None, show_callback=None, close_callback=None, width=0, height=0):

        self.window = window
        self.show_callback = show_callback
        self.close_callback = close_callback

        self.default_width = width
        self.default_height = height

        self.widget = Gtk.Popover(child=content_box)
        self.menu_button = None
        self.widget.connect("map", self._on_map)
        self.widget.connect("unmap", self._on_unmap)

        add_css_class(self.widget, "custom")

        if GTK_API_VERSION == 3:
            return

        # Workaround for GTK bug where clicks stop working after clicking inside popover once
        if os.environ.get("GDK_BACKEND") == "broadway":
            self.widget.set_has_arrow(False)  # pylint: disable=no-member

        # Workaround for popover not closing in GTK 4
        # https://gitlab.gnome.org/GNOME/gtk/-/issues/4529
        self.has_clicked_content = False

        for widget, callback in (
            (self.widget, self._on_click_popover_gtk4),
            (content_box.get_parent(), self._on_click_content_gtk4)
        ):
            gesture_click = Gtk.GestureClick(button=0)
            gesture_click.connect("pressed", callback)
            widget.add_controller(gesture_click)

    def _on_click_popover_gtk4(self, *_args):

        if not self.has_clicked_content:
            # Clicked outside the popover, close it. Normally GTK handles this,
            # but due to a bug, a popover intercepts clicks outside it after
            # closing a child popover.
            self.close()

        self.has_clicked_content = False

    def _on_click_content_gtk4(self, *_args):
        self.has_clicked_content = True

    def _on_map(self, *_args):

        self._resize_popover()

        if self.show_callback is not None:
            self.show_callback(self)

    def _on_unmap(self, *_args):
        if self.close_callback is not None:
            self.close_callback(self)

    def _resize_popover(self):

        popover_width = self.default_width
        popover_height = self.default_height

        if not popover_width and not popover_height:
            return

        if GTK_API_VERSION == 3:
            main_window_width = self.window.get_width()
            main_window_height = self.window.get_height()

            if main_window_width and popover_width > main_window_width:
                popover_width = main_window_width - 60

            if main_window_height and popover_height > main_window_height:
                popover_height = main_window_height - 60

        scrollable = self.widget.get_child()

        scrollable.set_max_content_width(popover_width)
        scrollable.set_max_content_height(popover_height)

    def set_menu_button(self, menu_button):

        if self.menu_button:
            self.menu_button.set_popover(None)

        if menu_button:
            menu_button.set_popover(self.widget)

        self.menu_button = menu_button

    def present(self):
        self.widget.popup()

    def close(self, use_transition=True):

        if use_transition:
            self.widget.popdown()
            return

        self.widget.set_visible(False)

    def destroy(self):
        self.set_menu_button(None)
        self.__dict__.clear()
