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

from pynicotine.gtkgui.widgets.ui import UserInterface
from pynicotine.gtkgui.widgets.dialogs import dialog_show
from pynicotine.gtkgui.widgets.dialogs import generic_dialog
from pynicotine.utils import human_length
from pynicotine.utils import human_size
from pynicotine.utils import human_speed
from pynicotine.utils import humanize


class FileProperties(UserInterface):

    def __init__(self, frame, properties, total_size=0, total_length=0, download_button=True):

        super().__init__("ui/dialogs/fileproperties.ui")

        self.frame = frame
        self.properties = properties
        self.total_size = total_size
        self.total_length = total_length

        self.dialog = generic_dialog(
            parent=frame.MainWindow,
            content_box=self.Main,
            title=_("File Properties"),
            width=600,
            height=0
        )

        if not download_button:
            self.download.hide()

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
        self.frame.np.transfers.get_file(properties["user"], properties["fn"], size=properties["size"],
                                         bitrate=properties.get("bitrate"), length=properties.get("length"))

    def update_title(self):

        index = self.current_index + 1
        total_files = len(self.properties)
        total_size = str(human_size(self.total_size))

        if self.total_length:
            self.dialog.set_title(_("File Properties (%(num)i of %(total)i  /  %(size)s  /  %(length)s)") % {
                'num': index, 'total': total_files, 'size': total_size,
                'length': str(human_length(self.total_length))
            })
            return

        self.dialog.set_title(_("File Properties (%(num)i of %(total)i  /  %(size)s)") % {
                              'num': index, 'total': total_files, 'size': total_size})

    def update_current_file(self):
        """ Updates the UI with properties for the selected file """

        properties = self.properties[self.current_index]

        if len(self.properties) <= 1:
            self.navigation_buttons.hide()

        self.filename_value.set_text(str(properties["filename"]))
        self.folder_value.set_text(str(properties["directory"]))
        self.filesize_value.set_text("%s (%s B)" % (human_size(properties["size"]), humanize(properties["size"])))
        self.username_value.set_text(str(properties["user"]))

        path = properties.get("path") or ""
        bitrate = properties.get("bitrate") or ""
        length = properties.get("length") or ""
        queue_position = properties.get("queue_position") or 0
        speed = properties.get("speed") or 0
        country = properties.get("country") or ""

        self.path_value.set_text(str(path))
        self.path.set_visible(bool(path))

        self.bitrate_value.set_text(str(bitrate))
        self.bitrate.set_visible(bool(bitrate))

        self.length_value.set_text(str(length))
        self.length.set_visible(bool(length))

        self.queue_value.set_text(str(humanize(queue_position)))
        self.queue.set_visible(bool(queue_position))

        self.speed_value.set_text(str(human_speed(speed)))
        self.speed.set_visible(bool(speed))

        self.country_value.set_text(str(country))
        self.country.set_visible(bool(country))

        self.update_title()

    def show(self):
        self.update_current_file()
        dialog_show(self.dialog)
