# COPYRIGHT (C) 2020-2024 Nicotine+ Contributors
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
from pynicotine.gtkgui.widgets import ui
from pynicotine.gtkgui.widgets.dialogs import Dialog
from pynicotine.slskmessages import FileListMessage
from pynicotine.utils import human_length
from pynicotine.utils import human_size
from pynicotine.utils import human_speed
from pynicotine.utils import humanize


class FileProperties(Dialog):

    def __init__(self, application):

        self.properties = {}
        self.total_size = 0
        self.total_length = 0
        self.current_index = 0

        (
            self.container,
            self.country_row,
            self.country_value_label,
            self.folder_value_label,
            self.length_row,
            self.length_value_label,
            self.name_value_label,
            self.next_button,
            self.path_row,
            self.path_value_label,
            self.previous_button,
            self.quality_row,
            self.quality_value_label,
            self.queue_row,
            self.queue_value_label,
            self.size_value_label,
            self.speed_row,
            self.speed_value_label,
            self.username_value_label
        ) = ui.load(scope=self, path="dialogs/fileproperties.ui")

        super().__init__(
            parent=application.window,
            content_box=self.container,
            buttons_start=(self.previous_button, self.next_button),
            default_button=self.next_button,
            title=_("File Properties"),
            width=600
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
        """Updates the UI with properties for the selected file."""

        properties = self.properties[self.current_index]

        for button in (self.previous_button, self.next_button):
            button.set_visible(len(self.properties) > 1)

        size = properties["size"]
        h_size = human_size(size)

        self.name_value_label.set_text(properties["basename"])
        self.folder_value_label.set_text(properties["virtual_folder_path"])
        self.size_value_label.set_text(f"{h_size} ({size} B)")  # Don't humanize exact size for easier use in filter
        self.username_value_label.set_text(properties["user"])

        real_folder_path = properties.get("real_folder_path", "")
        h_quality, _bitrate, h_length, _length = FileListMessage.parse_audio_quality_length(
            size, properties.get("file_attributes"), always_show_bitrate=True)
        queue_position = properties.get("queue_position", 0)
        speed = properties.get("speed", 0)
        country_code = properties.get("country_code")
        country_name = core.network_filter.COUNTRIES.get(country_code)
        country = f"{country_name} ({country_code})" if country_name else ""

        self.path_value_label.set_text(real_folder_path)
        self.path_row.set_visible(bool(real_folder_path))

        self.quality_value_label.set_text(h_quality)
        self.quality_row.set_visible(bool(h_quality))

        self.length_value_label.set_text(h_length)
        self.length_row.set_visible(bool(h_length))

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
