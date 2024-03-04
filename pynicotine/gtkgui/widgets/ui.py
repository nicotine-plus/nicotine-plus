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

import os

from gi.repository import Gtk

from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.application import GTK_GUI_FOLDER_PATH
from pynicotine.gtkgui.application import GTK_MINOR_VERSION
from pynicotine.utils import encode_path


# UI Builder #


ui_data = {}


def load(scope, path):

    if path not in ui_data:
        with open(encode_path(os.path.join(GTK_GUI_FOLDER_PATH, "ui", path)), encoding="utf-8") as file_handle:
            ui_content = file_handle.read()

            # Translate UI strings using Python's gettext
            start_tag = ' translatable="yes">'
            end_tag = "</property>"
            start_tag_len = len(start_tag)
            tag_start_pos = ui_content.find(start_tag)

            while tag_start_pos > -1:
                string_start_pos = (tag_start_pos + start_tag_len)
                string_end_pos = ui_content.find(end_tag, string_start_pos)

                original_string = ui_content[string_start_pos:string_end_pos]
                translated_string = _(original_string)

                if original_string != translated_string:
                    ui_content = ui_content[:string_start_pos] + translated_string + ui_content[string_end_pos:]

                # Find next translatable string
                new_string_end_pos = (string_end_pos + (len(translated_string) - len(original_string)))
                tag_start_pos = ui_content.find(start_tag, new_string_end_pos)

            # GTK 4 replacements
            if GTK_API_VERSION >= 4:
                ui_content = (
                    ui_content
                    .replace("GtkRadioButton", "GtkCheckButton")
                    .replace('"can-focus"', '"focusable"'))

                if GTK_MINOR_VERSION >= 10:
                    ui_content = (
                        ui_content
                        .replace("GtkColorButton", "GtkColorDialogButton")
                        .replace("GtkFontButton", "GtkFontDialogButton"))

            ui_data[path] = ui_content

    if GTK_API_VERSION >= 4:
        builder = Gtk.Builder(scope)
        builder.add_from_string(ui_data[path])
        Gtk.Buildable.get_name = Gtk.Buildable.get_buildable_id  # pylint: disable=no-member
    else:
        builder = Gtk.Builder()
        builder.add_from_string(ui_data[path])
        builder.connect_signals(scope)                      # pylint: disable=no-member

    widgets = builder.get_objects()

    for obj in list(widgets):
        try:
            obj_name = Gtk.Buildable.get_name(obj)
            if not obj_name.startswith("_"):
                continue

        except TypeError:
            pass

        widgets.remove(obj)

    widgets.sort(key=Gtk.Buildable.get_name)
    return widgets
