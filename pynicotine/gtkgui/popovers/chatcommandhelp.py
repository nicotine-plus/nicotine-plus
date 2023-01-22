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

from pynicotine.core import core
from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.widgets.popover import Popover
from pynicotine.gtkgui.widgets.theme import add_css_class


class ChatCommandHelp(Popover):

    def __init__(self, window, interface):

        self.interface = interface
        self.scrollable = Gtk.ScrolledWindow(visible=True)
        self.container = None

        super().__init__(
            window=window,
            content_box=self.scrollable,
            show_callback=self._update_commands,
            width=600,
            height=450
        )

    def _create_command_section(self, group_name):

        section_container = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, margin_start=18, margin_end=18, margin_top=18, margin_bottom=18,
            spacing=12, visible=True
        )
        section_label = Gtk.Label(label=group_name, selectable=True, wrap=True, xalign=0, visible=True)

        add_css_class(section_label, "heading")

        if GTK_API_VERSION >= 4:
            section_container.append(section_label)   # pylint: disable=no-member
            self.container.append(section_container)  # pylint: disable=no-member
        else:
            section_container.add(section_label)      # pylint: disable=no-member
            self.container.add(section_container)     # pylint: disable=no-member

        return section_container

    def _create_command_row(self, parent, command, description):

        row = Gtk.Box(homogeneous=True, spacing=12, visible=True)
        command_label = Gtk.Label(label=command, selectable=True, wrap=True, xalign=0, visible=True)
        description_label = Gtk.Label(label=description, selectable=True, wrap=True, xalign=0, visible=True)

        add_css_class(command_label, "italic")

        if GTK_API_VERSION >= 4:
            row.append(command_label)      # pylint: disable=no-member
            row.append(description_label)  # pylint: disable=no-member

            parent.append(row)             # pylint: disable=no-member
        else:
            row.add(command_label)         # pylint: disable=no-member
            row.add(description_label)     # pylint: disable=no-member

            parent.add(row)                # pylint: disable=no-member

        return row

    def _update_commands(self, *_args):

        if self.container:
            if GTK_API_VERSION >= 4:
                self.scrollable.set_child(None)         # pylint: disable=no-member
            else:
                self.scrollable.remove(self.container)  # pylint: disable=no-member

        self.container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, visible=True)

        for group_name, commands in core.pluginhandler.get_command_descriptions(self.interface).items():
            section_container = self._create_command_section(group_name)

            for command_usage, description in commands:
                self._create_command_row(section_container, command_usage, description)

        self.scrollable.set_property("child", self.container)
        self.container.child_focus(Gtk.DirectionType.TAB_FORWARD)
