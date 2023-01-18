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


""" Window """


class Window:

    active_dialogs = []  # Class variable keeping dialog objects alive

    def __init__(self, widget):

        self.widget = widget

        signal_name = "notify::focus-widget" if GTK_API_VERSION >= 4 else "set-focus"
        widget.connect(signal_name, self.on_focus_widget_changed)

    def connect_signal(self, widget, signal, callback):

        try:
            widget.handler_block_by_func(callback)

        except TypeError:
            widget.connect(signal, callback)
            return

        widget.handler_unblock_by_func(callback)

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

    @staticmethod
    def on_popover_closed(popover):

        focus_widget = popover.get_parent() if GTK_API_VERSION >= 4 else popover.get_relative_to()

        if focus_widget.get_focusable():
            focus_widget.grab_focus()
            return

        focus_widget.child_focus(Gtk.DirectionType.TAB_FORWARD)

    @staticmethod
    def on_combobox_popup_shown(combobox, param):

        visible = combobox.get_property(param.name)

        if visible:
            return

        # Always focus the text entry after the popup is closed
        if combobox.get_has_entry():
            entry = combobox.get_child()
            entry.grab_focus_without_selecting()
            entry.set_position(-1)
            return

        # Workaround for GTK 4 issue where wrong widget receives focus after closing popup
        if GTK_API_VERSION >= 4:
            combobox.grab_focus()

    def on_focus_widget_changed(self, *_args):

        focus_widget = self.widget.get_focus()

        if focus_widget is None:
            return

        # Workaround for GTK 4 issue where wrong widget receives focus after closing popover
        if GTK_API_VERSION >= 4:
            popover = focus_widget.get_ancestor(Gtk.Popover)

            if popover is not None:
                self.connect_signal(popover, "closed", self.on_popover_closed)
                return

        combobox = focus_widget.get_ancestor(Gtk.ComboBoxText)

        if combobox is not None:
            self.connect_signal(combobox, "notify::popup-shown", self.on_combobox_popup_shown)
