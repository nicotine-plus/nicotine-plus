# COPYRIGHT (C) 2020-2022 Nicotine+ Team
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
import sys

from gi.repository import Gtk

from pynicotine.logfacility import log


""" UI Builder """


GUI_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))
UI_DATA = {}


class UserInterface:

    def __init__(self, filename):

        try:
            if filename not in UI_DATA:
                with open(os.path.join(GUI_DIR, filename), "r", encoding="utf-8") as file_handle:
                    if Gtk.get_major_version() == 4:
                        UI_DATA[filename] = file_handle.read().replace(
                            "GtkRadioButton", "GtkCheckButton").replace("\"can-focus\"", "\"focusable\"")
                    else:
                        UI_DATA[filename] = file_handle.read()

            if Gtk.get_major_version() == 4:
                builder = Gtk.Builder(self)
                builder.add_from_string(UI_DATA[filename])
                Gtk.Buildable.get_name = Gtk.Buildable.get_buildable_id
            else:
                builder = Gtk.Builder.new_from_string(UI_DATA[filename], -1)
                builder.connect_signals(self)

            for obj in builder.get_objects():
                try:
                    obj_name = Gtk.Buildable.get_name(obj)

                    if not obj_name.startswith("_"):
                        setattr(self, obj_name, obj)

                except TypeError:
                    pass

        except Exception as error:
            log.add(_("Failed to load ui file %(file)s: %(error)s"), {
                "file": filename,
                "error": error
            })
            sys.exit()
