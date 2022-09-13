# COPYRIGHT (C) 2022 Nicotine+ Contributors
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

from pynicotine.gtkgui.application import GTK_API_VERSION

""" Popover """


class Popover:

    def __init__(self, window, content_box=None, show_callback=None, close_callback=None, width=0, height=0):

        self.window = window
        self.show_callback = show_callback
        self.close_callback = close_callback

        self.default_width = width
        self.default_height = height

        self.popover = Gtk.Popover(child=content_box)
        self.popover.get_style_context().add_class("generic-popover")
        self.popover.connect("notify::visible", self._on_show)
        self.popover.connect("closed", self._on_close)

        if GTK_API_VERSION >= 4:
            # Workaround for https://gitlab.gnome.org/GNOME/gtk/-/issues/4529
            self.popover.set_autohide(False)

    def _on_show(self, _popover, param):

        if not self.popover.get_property(param.name):
            return

        if GTK_API_VERSION >= 4:
            # Workaround for https://gitlab.gnome.org/GNOME/gtk/-/issues/4529
            self.popover.child_focus(Gtk.DirectionType.TAB_FORWARD)

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

        if GTK_API_VERSION >= 4:
            main_window_width = self.window.get_width()
            main_window_height = self.window.get_height()
        else:
            main_window_width, main_window_height = self.window.get_size()

        if main_window_width and popover_width > main_window_width:
            popover_width = main_window_width - 60

        if main_window_height and popover_height > main_window_height:
            popover_height = main_window_height - 60

        self.popover.get_child().set_size_request(popover_width, popover_height)

    def show(self):
        self.popover.popup()

    def close(self):
        self.popover.popdown()
