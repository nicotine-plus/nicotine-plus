# COPYRIGHT (C) 2020-2021 Nicotine+ Team
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


class UserInterface:

    def __init__(self, filename):

        try:
            current_path = os.path.dirname(os.path.realpath(__file__))
            gui_dir = os.path.normpath(os.path.join(current_path, ".."))
            filename = os.path.join(gui_dir, filename)

            with open(filename, "r", encoding="utf-8") as f:
                if Gtk.get_major_version() == 4:
                    builder = Gtk.Builder(self)
                    builder.add_from_string(
                        f.read()
                        .replace("GtkRadioButton", "GtkCheckButton")
                    )
                    Gtk.Buildable.get_name = Gtk.Buildable.get_buildable_id
                else:
                    builder = Gtk.Builder()
                    builder.add_from_string(
                        f.read()
                        .replace("<property name=\"focusable\">0</property>",
                                 "<property name=\"can-focus\">0</property>")
                    )
                    builder.connect_signals(self)

            for obj in builder.get_objects():
                try:
                    obj_name = Gtk.Buildable.get_name(obj)

                    if not obj_name.startswith("_"):
                        setattr(self, obj_name, obj)

                except TypeError:
                    pass

        except Exception as e:
            log.add(_("Failed to load ui file %(file)s: %(error)s"), {
                "file": filename,
                "error": e
            })
            sys.exit()
