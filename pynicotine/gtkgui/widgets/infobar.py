# COPYRIGHT (C) 2020-2023 Nicotine+ Contributors
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
from pynicotine.gtkgui.widgets.theme import add_css_class
from pynicotine.gtkgui.widgets.theme import remove_css_class


class InfoBar:

    class InternalInfoBar(Gtk.Box):
        __gtype_name__ = "InfoBar"

        def __init__(self, *args, **kwargs):
            self.set_css_name("infobar")
            super().__init__(*args, **kwargs)

    def __init__(self, parent, button=None):

        self.widget = self.InternalInfoBar(visible=True)
        self.container = Gtk.Box(visible=True)
        self.revealer = Gtk.Revealer(
            child=self.container, transition_type=Gtk.RevealerTransitionType.SLIDE_DOWN, visible=True
        )
        self.label = Gtk.Label(
            height_request=24, hexpand=True, margin_top=6, margin_bottom=6, margin_start=12, margin_end=6,
            wrap=True, visible=True, xalign=0
        )
        self.button_container = Gtk.Box(margin_top=6, margin_bottom=6, margin_end=6, visible=True)
        self.message_type = None

        if GTK_API_VERSION >= 4:
            parent.append(self.widget)                    # pylint: disable=no-member
            self.widget.append(self.revealer)             # pylint: disable=no-member
            self.container.append(self.label)             # pylint: disable=no-member
            self.container.append(self.button_container)  # pylint: disable=no-member

            if button:
                self.button_container.append(button)      # pylint: disable=no-member
        else:
            parent.add(self.widget)                       # pylint: disable=no-member
            self.widget.add(self.revealer)                # pylint: disable=no-member
            self.container.add(self.label)                # pylint: disable=no-member
            self.container.add(self.button_container)     # pylint: disable=no-member

            if button:
                self.button_container.add(button)         # pylint: disable=no-member

        self.set_visible(False)

    def destroy(self):
        self.__dict__.clear()

    def _show_message(self, message, message_type):

        previous_message_type = self.message_type
        self.message_type = message_type

        if previous_message_type:
            remove_css_class(self.widget, previous_message_type)

        add_css_class(self.widget, message_type)

        self.label.set_text(message)
        self.set_visible(True)

    def set_visible(self, visible):
        self.widget.set_visible(visible)
        self.revealer.set_reveal_child(visible)

    def show_error_message(self, message):
        self._show_message(message, message_type="error")

    def show_info_message(self, message):
        self._show_message(message, message_type="info")
