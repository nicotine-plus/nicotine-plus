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

from pynicotine.gtkgui.widgets.ui import UserInterface
from pynicotine.gtkgui.widgets.dialogs import dialog_show
from pynicotine.gtkgui.widgets.dialogs import generic_dialog


class FileProperties(UserInterface):

    def __init__(self, frame, properties):

        super().__init__("ui/dialogs/fileproperties.ui")

        self.frame = frame
        self.properties = properties

        self.dialog = generic_dialog(
            parent=frame.MainWindow,
            content_box=self.Main,
            title=_("File Properties"),
            width=600,
            height=0
        )

        self.current_index = 0

    def on_previous(self, *_args):

        self.current_index -= 1

        if self.current_index < 0:
            self.current_index = len(self.properties) - 1

        self.update_current_file()

    def on_next(self, *_args):

        self.current_index += 1

        if self.current_index >= len(self.properties):
            self.current_index = 0

        self.update_current_file()

    def on_download_item(self, *_args):
        properties = self.properties[self.current_index]
        self.frame.np.transfers.get_file(properties["user"], properties["fn"])

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

        bitrate = properties["bitrate"] or ""
        length = properties["length"] or ""
        queue = properties["queue"] or ""
        speed = properties["speed"] or ""
        country = properties["country"] or ""

        self.bitrate_value.set_text(bitrate)
        self.bitrate_label.get_parent().set_visible(bool(bitrate))
        self.bitrate_value.get_parent().set_visible(bool(bitrate))

        self.length_value.set_text(length)
        self.length_label.get_parent().set_visible(bool(length))
        self.length_value.get_parent().set_visible(bool(length))

        self.queue_value.set_text(queue)
        self.queue_label.get_parent().set_visible(bool(queue))
        self.queue_value.get_parent().set_visible(bool(queue))

        self.speed_value.set_text(speed)
        self.speed_label.get_parent().set_visible(bool(speed))
        self.speed_value.get_parent().set_visible(bool(speed))

        self.country_value.set_text(country)
        self.country_label.get_parent().set_visible(bool(country))
        self.country_value.get_parent().set_visible(bool(country))

        self.update_title()

    def show(self):
        self.update_current_file()
        dialog_show(self.dialog)
