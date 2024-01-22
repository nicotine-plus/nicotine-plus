# COPYRIGHT (C) 2022-2023 Nicotine+ Contributors
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

from gi.repository import Gtk

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
        self.widget.connect("notify::visible", self._on_visible_changed)
        self.widget.connect("closed", self._on_close)

        add_css_class(self.widget, "generic-popover")

    def _on_visible_changed(self, *_args):

        if not self.widget.is_visible():
            return

        self._resize_popover()

        if self.show_callback is not None:
            self.show_callback(self)

    def _on_close(self, *_args):
        if self.close_callback is not None:
            self.close_callback(self)

    def _resize_popover(self):

        popover_width = self.default_width
        popover_height = self.default_height

        if not popover_width and not popover_height:
            return

        main_window_width = self.window.get_width()
        main_window_height = self.window.get_height()

        if main_window_width and popover_width > main_window_width:
            popover_width = main_window_width - 60

        if main_window_height and popover_height > main_window_height:
            popover_height = main_window_height - 60

        self.widget.get_child().set_size_request(popover_width, popover_height)

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
