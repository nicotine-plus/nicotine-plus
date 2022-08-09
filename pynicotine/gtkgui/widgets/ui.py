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
import sys

from gi.repository import Gtk

from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.application import GTK_GUI_DIR
from pynicotine.i18n import TRANSLATION_DOMAIN
from pynicotine.logfacility import log
from pynicotine.utils import encode_path


""" UI Builder """


class UserInterface:

    ui_data = {}

    def __init__(self, filename):

        try:
            if filename not in self.ui_data:
                with open(encode_path(os.path.join(GTK_GUI_DIR, filename)), encoding="utf-8") as file_handle:
                    if GTK_API_VERSION >= 4:
                        self.ui_data[filename] = file_handle.read().replace(
                            "GtkRadioButton", "GtkCheckButton").replace("\"can-focus\"", "\"focusable\"")
                    else:
                        self.ui_data[filename] = file_handle.read()

            if GTK_API_VERSION >= 4:
                self.builder = Gtk.Builder(self)
                self.builder.set_translation_domain(TRANSLATION_DOMAIN)
                self.builder.add_from_string(self.ui_data[filename])
                Gtk.Buildable.get_name = Gtk.Buildable.get_buildable_id  # pylint: disable=no-member
            else:
                self.builder = Gtk.Builder(translation_domain=TRANSLATION_DOMAIN)
                self.builder.add_from_string(self.ui_data[filename])
                self.builder.connect_signals(self)                       # pylint: disable=no-member

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

        except Exception as error:
            log.add(_("Failed to load ui file %(file)s: %(error)s"), {
                "file": filename,
                "error": error
            })
            sys.exit()
