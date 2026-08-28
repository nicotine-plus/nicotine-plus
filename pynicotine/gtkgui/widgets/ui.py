# SPDX-FileCopyrightText: 2020-2023 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

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

    for obj in widgets[:]:
        try:
            obj_name = Gtk.Buildable.get_name(obj)
            if not obj_name.startswith("_"):
                continue

        except TypeError:
            pass

        widgets.remove(obj)

    widgets.sort(key=Gtk.Buildable.get_name)
    return widgets
