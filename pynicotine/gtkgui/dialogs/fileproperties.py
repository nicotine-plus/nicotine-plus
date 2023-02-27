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

from pynicotine.core import core
from pynicotine.gtkgui.widgets.ui import UserInterface
from pynicotine.gtkgui.widgets.dialogs import Dialog
from pynicotine.utils import human_length
from pynicotine.utils import human_size
from pynicotine.utils import human_speed
from pynicotine.utils import humanize


class FileProperties(Dialog):

    def __init__(self, application, download_button=True):

        self.properties = {}
        self.total_size = 0
        self.total_length = 0
        self.current_index = 0

        ui_template = UserInterface(scope=self, path="dialogs/fileproperties.ui")
        (
            self.bitrate_row,
            self.bitrate_value_label,
            self.container,
            self.country_row,
            self.country_value_label,
            self.download_button,
            self.filename_value_label,
            self.filesize_value_label,
            self.folder_value_label,
            self.length_row,
            self.length_value_label,
            self.next_button,
            self.path_row,
            self.path_value_label,
            self.previous_button,
            self.queue_row,
            self.queue_value_label,
            self.speed_row,
            self.speed_value_label,
            self.username_value_label
        ) = ui_template.widgets

        Dialog.__init__(
            self,
            parent=application.window,
            content_box=self.container,
            buttons_start=(self.previous_button, self.next_button),
            buttons_end=(self.download_button,) if download_button else (),
            default_button=self.next_button,
            title=_("File Properties"),
            width=600,
            close_destroy=False
        )

    def update_title(self):

        index = self.current_index + 1
        total_files = len(self.properties)
        total_size = human_size(self.total_size)

        if self.total_length:
            self.set_title(_("File Properties (%(num)i of %(total)i  /  %(size)s  /  %(length)s)") % {
                "num": index, "total": total_files, "size": total_size,
                "length": human_length(self.total_length)
            })
            return

        self.set_title(_("File Properties (%(num)i of %(total)i  /  %(size)s)") % {
                       "num": index, "total": total_files, "size": total_size})

    def update_current_file(self):
        """ Updates the UI with properties for the selected file """

        properties = self.properties[self.current_index]

        for button in (self.previous_button, self.next_button):
            button.set_visible(len(self.properties) > 1)

        h_size = human_size(properties["size"])
        bytes_size = humanize(properties["size"])

        self.filename_value_label.set_text(properties["filename"])
        self.folder_value_label.set_text(properties["directory"])
        self.filesize_value_label.set_text(f"{h_size} ({bytes_size} B)")
        self.username_value_label.set_text(properties["user"])

        path = properties.get("path") or ""
        bitrate = properties.get("bitrate") or ""
        length = properties.get("length") or ""
        queue_position = properties.get("queue_position") or 0
        speed = properties.get("speed") or 0
        country = properties.get("country") or ""

        self.path_value_label.set_text(path)
        self.path_row.set_visible(bool(path))

        self.bitrate_value_label.set_text(bitrate)
        self.bitrate_row.set_visible(bool(bitrate))

        self.length_value_label.set_text(length)
        self.length_row.set_visible(bool(length))

        self.queue_value_label.set_text(humanize(queue_position))
        self.queue_row.set_visible(bool(queue_position))

        self.speed_value_label.set_text(human_speed(speed))
        self.speed_row.set_visible(bool(speed))

        self.country_value_label.set_text(country)
        self.country_row.set_visible(bool(country))

        self.update_title()

    def update_properties(self, properties, total_size=0, total_length=0):

        self.properties = properties
        self.total_size = total_size
        self.total_length = total_length
        self.current_index = 0

        self.update_current_file()

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

        core.transfers.get_file(
            properties["user"], properties["fn"], size=properties["size"],
            bitrate=properties.get("bitrate"), length=properties.get("length")
        )
