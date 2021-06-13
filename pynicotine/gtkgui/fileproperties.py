# COPYRIGHT (C) 2020-2021 Nicotine+ Team
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2008-2009 Quinox <quinox@users.sf.net>
# COPYRIGHT (C) 2006-2009 Daelstorm <daelstorm@gmail.com>
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

from gi.repository import Gdk
from gi.repository import Gtk

from pynicotine.gtkgui.utils import load_ui_elements
from pynicotine.gtkgui.widgets.dialogs import generic_dialog


class FileProperties:

    def __init__(self, frame, properties):

        self.frame = frame
        self.properties = properties

        load_ui_elements(self, os.path.join(self.frame.gui_dir, "ui", "dialogs", "fileproperties.ui"))

        self.dialog = generic_dialog(
            parent=frame.MainWindow,
            content_box=self.Main,
            title=_("File Properties"),
            width=600,
            height=0
        )

        self.current_index = 0

    def on_previous(self, *args):
        self.current_index -= 1

        if self.current_index < 0:
            self.current_index = len(self.properties) - 1

        self.update_current_file()

    def on_next(self, *args):
        self.current_index += 1

        if self.current_index >= len(self.properties):
            self.current_index = 0

        self.update_current_file()

    def on_download_item(self, *args):
        if not self.frame.np.transfers:
            return

        properties = self.properties[self.current_index]
        self.frame.np.transfers.get_file(properties["user"], properties["fn"], "", checkduplicate=True)

    def update_title(self):
        self.dialog.set_title(_("File Properties (%(num)i of %(total)i)") % {
            'num': self.current_index + 1,
            'total': len(self.properties)
        })

    def update_current_file(self):
        """ Updates the UI with properties for the selected file """

        properties = self.properties[self.current_index]

        if len(self.properties) <= 1:
            self.navigation_buttons.hide()

        self.filename_value.set_text(properties["filename"])
        self.folder_value.set_text(properties["directory"])
        self.filesize_value.set_text(str(properties["size"]))
        self.username_value.set_text(properties["user"])

        bitrate = properties["bitrate"]
        length = properties["length"]
        immediate = properties["immediate"]
        speed = properties["speed"]
        country = properties["country"]

        if bitrate:
            self.bitrate_value.set_text(bitrate)
            self.bitrate_label.show()
            self.bitrate_value.show()
        else:
            self.bitrate_label.hide()
            self.bitrate_value.hide()

        if length:
            self.length_value.set_text(length)
            self.length_label.show()
            self.length_value.show()
        else:
            self.length_label.hide()
            self.length_value.hide()

        if bitrate and length:
            self.empty_1.show()
        else:
            self.empty_1.hide()

        if immediate:
            self.immediate_value.set_text(immediate)
            self.immediate_label.show()
            self.immediate_value.show()
        else:
            self.immediate_label.hide()
            self.immediate_value.hide()

        if immediate == "N":
            self.queue_value.set_text(properties["queue"])
            self.queue_label.show()
            self.queue_value.show()
        else:
            self.queue_label.hide()
            self.queue_value.hide()

        if speed:
            self.speed_value.set_text(speed)
            self.speed_label.show()
            self.speed_value.show()
        else:
            self.speed_label.hide()
            self.speed_value.hide()

        if country:
            self.country_value.set_text(country)
            self.country_label.show()
            self.country_value.show()
        else:
            self.country_label.hide()
            self.country_value.hide()

        self.update_title()

    def show(self):

        self.update_current_file()
        self.dialog.present_with_time(Gdk.CURRENT_TIME)

        if Gtk.get_major_version() == 3:
            self.dialog.get_window().set_functions(
                Gdk.WMFunction.RESIZE | Gdk.WMFunction.MOVE | Gdk.WMFunction.CLOSE
            )
