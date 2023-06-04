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

from gi.repository import Gtk
from locale import strxfrm
from pynicotine.logfacility import log
from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.gtkgui.widgets import ui
from pynicotine.gtkgui.widgets.dialogs import Dialog
from pynicotine.gtkgui.widgets.dialogs import OptionDialog
from pynicotine.gtkgui.widgets.treeview import TreeView
from pynicotine.gtkgui.widgets.infobar import InfoBar
from pynicotine.gtkgui.widgets.filechooser import FolderChooser
from pynicotine import slskmessages
from pynicotine.utils import human_size

class DownloadFolder(Dialog):

    def __init__(self, application):

        (
            self.container,
            self.destination_entry,
            self.info_bar,
            self.list_container,
            self.virtual_path
        ) = ui.load(scope=self, path="dialogs/downloadfolder.ui")

        super().__init__(
            parent=application.window,
            modal=False,
            content_box=self.container,
            title=_("Folder File Download"),
            width=800,
            height=600,
            close_callback=self.on_close,
            close_destroy=False
        )

        self.info_bar = InfoBar(self.info_bar)
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

        self.info_bar.show_message(_("Loading"), message_type=Gtk.MessageType.INFO)

        for event_name, callback in (
            ("folder-contents-response", self._folder_contents_response),
            ("peer-connection-error", self._peer_connection_error)
        ):
            events.connect(event_name, callback)

    def _peer_connection_error(self, user, msgs=None, is_offline=False):

        if msgs is None:
            return

        for i in msgs:
            if i.__class__ is slskmessages.FolderContentsRequest:
                self.toggle_enabled_view(False, user)
                self.info_bar.show_message(user + " " + _("offline"), message_type=Gtk.MessageType.ERROR)

    def toggle_enabled_view(self, validFiles, user = ""):

        self.container.set_sensitive(validFiles)
        if (validFiles):
            self.info_bar.set_visible(False)

    # Pass the Download Folder Data
    def set_folder_Files(self, folder_Files = None):

        self.toggle_enabled_view(True)

        if folder_Files is not None:
            self.folder_Files = folder_Files

        self.list_view.clear()

        self.virtual_path.set_text(self.folder_Files["user"] + " : " + self.folder_Files["virtualpath"])
        self.destination_entry.set_text(self.folder_Files["destination"])

        for file in self.folder_Files["filenames"]:
            size = file["size"]
            self.list_view.add_row([file["filename"], (human_size(size)), True])

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
        username = self.folder_Files["user"]

        for iterator in self.list_view.get_all_rows():
            toggle = self.list_view.get_row_value(iterator, "download")

            if (toggle):
                filename = self.list_view.get_row_value(iterator, "filename")
                virtualpath = self.folder_Files["virtualpath"] + filename

                for file in self.folder_Files["filenames"]:
                    if file["filename"] == filename:
                        size = file["size"]
                        h_bitrate = file["h_bitrate"]
                        h_length = file["h_length"]
                        break
                
                core.transfers.get_file(username, virtualpath, path=destination, size=size, bitrate=h_bitrate, length=h_length)

        self.close()

    # Capture the Dialog Close event
    def on_close(self, *_args):

        # The Dialog object is not Destroyed so Clear the content of the Dialog before closing.
        self.list_view.clear()
        self.virtual_path.set_text("")
        self.destination_entry.set_text("")
        self.info_bar.show_message(_("Loading"), message_type=Gtk.MessageType.INFO)

    # Choose Download Location through Folder Chooser
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

    # Set Selected Folder
    def on_download_folders_to_selected(self, selected, _data):

        self.destination_entry.set_text(selected)

    # Download Folder Search Response
    def _folder_contents_response(self, msg, check_num_files=True):
        """ Peer code: 37 """
        """ When we got a contents of a folder, get all the files in it, but
        skip the files in subfolders """

        username = msg.init.target_user
        file_list = msg.list

        log.add_transfer("Received response for folder content request from user %s", username)

        # Create a structure of the Files available to download.
        folderFiles = {
            "user": username,
            "virtualpath": None,
            "destination": None,
            "filenames": []
        }

        # Iterate through backend response and populate File structure.
        for i in file_list:
            for directory in file_list[i]:
                if os.path.commonprefix([i, directory]) != directory:
                    continue

                files = file_list[i][directory][:]
                num_files = len(files)

                destination = core.transfers.get_folder_destination(username, directory)
                folderFiles["destination"] = destination

                virtualpath = directory.rstrip("\\") + "\\"
                folderFiles["virtualpath"] = virtualpath

                if num_files > 1:
                    files.sort(key=lambda x: strxfrm(x[1]))

                log.add_transfer(("Attempting to download files in folder %(folder)s for user %(user)s. "
                                  "Destination path: %(destination)s"), {
                                    "folder": directory,
                                    "user": username,
                                    "destination": destination
                                })

                for file in files:
                    size = file[2]
                    h_bitrate, _bitrate, h_length, _length = slskmessages.FileListMessage.parse_result_bitrate_length(
                        size, file[4])

                    folderFiles["filenames"].append({
                        "filename": file[1],
                        "size": file[2],
                        "h_bitrate": h_bitrate,
                        "h_length": h_length
                    })

        self.folder_Files = folderFiles
        file_count = len(folderFiles["filenames"])
        
        if check_num_files and file_count > 100:
            # Present Confirmation you would like to download all the files
            OptionDialog(
                parent=self.application.window,
                title=_("Download %(num)i files?") % {"num": file_count},
                message=_("Do you really want to download %(num)i files from %(user)s's folder %(folder)s?") % {
                    "num": file_count, "user": username, "folder": folderFiles["virtualpath"]},
                    callback=self.folder_download_response,
                    callback_data=msg).show()
            
            return        
        
        self.set_folder_Files()

    # Check Confirmation for large file count
    def folder_download_response(self, _dialog, response_id, msg):
        if response_id == 2:
            self.set_folder_Files()
            return
        
        self.toggle_enabled_view(False)
        self.info_bar.show_message(_("Too many files"), message_type=Gtk.MessageType.ERROR)