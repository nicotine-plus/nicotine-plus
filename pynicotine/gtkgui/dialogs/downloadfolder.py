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
import os.path

from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.gtkgui.widgets import ui
from pynicotine.gtkgui.widgets.accelerator import Accelerator
from pynicotine.gtkgui.widgets.dialogs import Dialog
from pynicotine.gtkgui.widgets.dialogs import EntryDialog
from pynicotine.gtkgui.widgets.dialogs import OptionDialog
from pynicotine.gtkgui.widgets.textentry import CompletionEntry
from pynicotine.gtkgui.widgets.treeview import TreeView
from pynicotine.utils import human_size
from pynicotine.gtkgui.widgets.filechooser import FolderChooser


class DownloadFolder(Dialog):

    def __init__(self, application):

        (
            self.container,
            self.destination_entry,
            self.list_container,
            self.virtual_path,
        ) = ui.load(scope=self, path="dialogs/downloadfolder.ui")

        super().__init__(
            parent=application.window,
            modal=False,
            content_box=self.container,
            title=_("Folder File Download"),
            width=800,
            height=600,
            close_destroy=False
        )

        self.application = application
        self.list_view = TreeView(
            application.window, parent=self.list_container, multi_select=True, activate_row_callback=None,
            columns={
                "filename": {
                    "column_type": "text",
                    "title": "File Name",
                    "width": 1,
                    "expand_column": True
                },
                "size": {
                    "column_type": "text",
                    "title": "Size",
                    "width": 100,
                    "expand_column": False
                },
                "download": {
                    "column_type": "toggle",
                    "title": "Download",
                    "width": 0,
                    "toggle_callback": self.on_download_option
                }
            }
        )
      
    # Pass the Download Folder Data
    def set_folder_list(self, folder_list):

        self.folder_list = folder_list
        self.list_view.clear()

        self.virtual_path.set_text(folder_list["user"] + " : " + folder_list["virtualpath"])
        self.destination_entry.set_text(folder_list["destination"])

        for file in folder_list["filenames"]:
            size = file["size"]
            self.list_view.add_row([file["filename"], (human_size(size)), True])
            #self.list_view.add_row([file["filename"], (human_size(size) + "  (" + "{:,}".format(size) + " bytes)"), True])

    # Toggle Checkbox Value
    def on_download_option(self, list_view, iterator):

        toggle = list_view.get_row_value(iterator, "download")
        list_view.set_row_value(iterator, "download", not toggle)

    # Toggle All Checkbox True
    def on_select_all(self, *_args):

        for iterator in self.list_view.get_all_rows():
            self.list_view.set_row_value(iterator, "download", True)

    # Toggle All Checkbox False
    def on_unselect_all(self, *_args):

        for iterator in self.list_view.get_all_rows():
            self.list_view.set_row_value(iterator, "download", False)

    # Download the Files that are Toggled True
    def on_download(self, *_args):

        destination = self.destination_entry.get_text()       
        username = self.folder_list["user"]
        
        for iterator in self.list_view.get_all_rows():
            toggle = self.list_view.get_row_value(iterator, "download")
            
            if (toggle):
                filename = self.list_view.get_row_value(iterator, "filename")
                virtualpath = self.folder_list["virtualpath"] + filename

                for file in self.folder_list["filenames"]:
                    if file["filename"] == filename:
                        size = file["size"]
                        h_bitrate = file["h_bitrate"]
                        h_length = file["h_length"]
                        break
                
                core.transfers.get_file(username, virtualpath, path=destination, size=size, bitrate=h_bitrate, length=h_length)

        self.close()

    def on_select_destination(self, *_args):

        destination = self.destination_entry.get_text()

        if not os.path.exists(destination):
            destination = config.sections["transfers"]["downloaddir"]

        FolderChooser(
            parent=self.application.window,
            title=_("Select Destination Folder"),
            callback=self.on_download_folders_to_selected,
            initial_folder=destination
        ).show()

    def on_download_folders_to_selected(self, selected, _data):

        self.destination_entry.set_text(selected)

