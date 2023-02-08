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

import os

from xml.etree import ElementTree

from gi.repository import Gtk

from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.application import GTK_GUI_DIR
from pynicotine.utils import encode_path


""" UI Builder """


class UserInterface:

    ui_data = {}

    def __init__(self, scope, path):

        if path not in self.ui_data:
            with open(encode_path(os.path.join(GTK_GUI_DIR, "ui", path)), encoding="utf-8") as file_handle:
                ui_xml_tree = ElementTree.parse(file_handle)

                for node in ui_xml_tree.iterfind('.//*[@translatable="yes"]'):
                    node.text = _(node.text)
                    del node.attrib["translatable"]

                ui_xml_string = ElementTree.tostring(ui_xml_tree.getroot(), encoding="unicode")

                if GTK_API_VERSION >= 4:
                    ui_xml_string = ui_xml_string.replace(
                        "GtkRadioButton", "GtkCheckButton").replace('"can-focus"', '"focusable"')

                self.ui_data[path] = ui_xml_string

        if GTK_API_VERSION >= 4:
            self.builder = Gtk.Builder(scope)
            self.builder.add_from_string(self.ui_data[path])
            Gtk.Buildable.get_name = Gtk.Buildable.get_buildable_id  # pylint: disable=no-member
        else:
            self.builder = Gtk.Builder()
            self.builder.add_from_string(self.ui_data[path])
            self.builder.connect_signals(scope)                      # pylint: disable=no-member

        self.widgets = self.builder.get_objects()

        for obj in list(self.widgets):
            try:
                obj_name = Gtk.Buildable.get_name(obj)
                if not obj_name.startswith("_"):
                    continue

            except TypeError:
                pass

            self.widgets.remove(obj)

        self.widgets.sort(key=Gtk.Buildable.get_name)
