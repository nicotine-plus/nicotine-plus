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

    def __init__(self, window):

        # Workaround for GTK 4 issue where wrong widget receives focus after closing popover
        if GTK_API_VERSION >= 4:
            window.connect("notify::focus-widget", self.on_focus_widget_changed)

    @staticmethod
    def on_popover_closed(popover):

        focus_widget = popover.get_parent()

        if focus_widget.get_focusable():
            focus_widget.grab_focus()
            return

        focus_widget.child_focus(Gtk.DirectionType.TAB_FORWARD)

    def on_focus_widget_changed(self, window, param):

        widget = window.get_property(param.name)

        if widget is None:
            return

        popover = widget.get_ancestor(Gtk.Popover)

        if popover is None:
            return

        try:
            popover.handler_block_by_func(self.on_popover_closed)

        except TypeError:
            popover.connect("closed", self.on_popover_closed)
            return

        popover.handler_unblock_by_func(self.on_popover_closed)
