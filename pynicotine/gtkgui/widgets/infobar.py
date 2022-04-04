# COPYRIGHT (C) 2020-2022 Nicotine+ Contributors
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


class InfoBar:
    """ Wrapper for setting up a GtkInfoBar """

    def __init__(self, info_bar, message_type):

        self.info_bar = info_bar
        self.info_bar.set_message_type(message_type)
        self.info_bar.set_show_close_button(True)
        self.info_bar.connect("response", self._hide)

        self.revealer = self.info_bar.get_ancestor(Gtk.Revealer)
        self.label = Gtk.Label(wrap=True, visible=True, xalign=0)

        if GTK_API_VERSION >= 4:
            self.info_bar.add_child(self.label)
        else:
            self.info_bar.get_content_area().add(self.label)

        self.set_visible(False)

    def _hide(self, *_args):
        self.set_visible(False)

    def set_visible(self, visible):

        if GTK_API_VERSION >= 4:
            # Workaround for infinite gtk_widget_measure loop when hiding info bar
            self.revealer.set_visible(visible)

        self.revealer.set_reveal_child(visible)

    def show_message(self, message):
        self.label.set_text(message)
        self.set_visible(True)
