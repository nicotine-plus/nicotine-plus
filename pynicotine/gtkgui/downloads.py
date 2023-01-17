# COPYRIGHT (C) 2020-2022 Nicotine+ Contributors
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2016-2018 Mutnick <mutnick@techie.com>
# COPYRIGHT (C) 2013 eLvErDe <gandalf@le-vert.net>
# COPYRIGHT (C) 2008-2012 quinox <quinox@users.sf.net>
# COPYRIGHT (C) 2009 hedonist <ak@sensi.org>
# COPYRIGHT (C) 2006-2009 daelstorm <daelstorm@gmail.com>
# COPYRIGHT (C) 2003-2004 Hyriand <hyriand@thegraveyard.org>
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

from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.popovers.downloadspeeds import DownloadSpeeds
from pynicotine.gtkgui.transferlist import TransferList
from pynicotine.gtkgui.utils import copy_text
from pynicotine.gtkgui.widgets.dialogs import OptionDialog
from pynicotine.utils import open_file_path


class Downloads(TransferList):

    def __init__(self, window):

        self.path_separator = "/"
        self.path_label = _("Path")
        self.retry_label = _("_Resume")
        self.abort_label = _("P_ause")
        self.deprioritized_statuses = {"Paused", "Finished", "Filtered"}

        self.transfer_page = window.downloads_page
        self.user_counter = window.download_users_label
        self.file_counter = window.download_files_label
        self.expand_button = window.downloads_expand_button
        self.expand_icon = window.downloads_expand_icon
        self.grouping_button = window.downloads_grouping_button

        TransferList.__init__(self, window, transfer_type="download")

        if GTK_API_VERSION >= 4:
            window.downloads_content.append(self.container)
        else:
            window.downloads_content.add(self.container)

        self.popup_menu_clear.add_items(
            ("#" + _("Finished / Filtered"), self.on_clear_finished_filtered),
            ("", None),
            ("#" + _("Finished"), self.on_clear_finished),
            ("#" + _("Paused"), self.on_clear_paused),
            ("#" + _("Filtered"), self.on_clear_filtered),
            ("#" + _("Deleted"), self.on_clear_deleted),
            ("#" + _("Queued…"), self.on_try_clear_queued),
            ("", None),
            ("#" + _("Everything…"), self.on_try_clear_all),
        )
        self.popup_menu_clear.update_model()

        for event_name, callback in (
            ("abort-download", self.abort_transfer),
            ("abort-downloads", self.abort_transfers),
            ("clear-download", self.clear_transfer),
            ("clear-downloads", self.clear_transfers),
            ("download-large-folder", self.download_large_folder),
            ("download-notification", self.new_transfer_notification),
            ("start", self.start),
            ("update-download", self.update_model),
            ("update-downloads", self.update_model)
        ):
            events.connect(event_name, callback)

        self.download_speeds = DownloadSpeeds(window)

    def start(self):
        self.init_transfers(core.transfers.downloads)

    def retry_selected_transfers(self):
        core.transfers.retry_downloads(self.selected_transfers)

    def abort_selected_transfers(self):
        core.transfers.abort_downloads(self.selected_transfers)

    def clear_selected_transfers(self):
        core.transfers.clear_downloads(downloads=self.selected_transfers)

    def on_clear_queued_response(self, _dialog, response_id, _data):
        if response_id == 2:
            core.transfers.clear_downloads(statuses=["Queued"])

    def on_try_clear_queued(self, *_args):

        OptionDialog(
            parent=self.window,
            title=_("Clear Queued Downloads"),
            message=_("Do you really want to clear all queued downloads?"),
            callback=self.on_clear_queued_response
        ).show()

    def on_clear_all_response(self, _dialog, response_id, _data):
        if response_id == 2:
            core.transfers.clear_downloads()

    def on_try_clear_all(self, *_args):

        OptionDialog(
            parent=self.window,
            title=_("Clear All Downloads"),
            message=_("Do you really want to clear all downloads?"),
            callback=self.on_clear_all_response
        ).show()

    def folder_download_response(self, _dialog, response_id, msg):
        if response_id == 2:
            events.emit("folder-contents-response", msg, check_num_files=False)

    def download_large_folder(self, username, folder, numfiles, msg):

        OptionDialog(
            parent=self.window,
            title=_("Download %(num)i files?") % {"num": numfiles},
            message=_("Do you really want to download %(num)i files from %(user)s's folder %(folder)s?") % {
                "num": numfiles, "user": username, "folder": folder},
            callback=self.folder_download_response,
            callback_data=msg
        ).show()

    def on_copy_url(self, *_args):

        transfer = next(iter(self.selected_transfers), None)

        if transfer:
            url = core.userbrowse.get_soulseek_url(transfer.user, transfer.filename)
            copy_text(url)

    def on_copy_dir_url(self, *_args):

        transfer = next(iter(self.selected_transfers), None)

        if transfer:
            url = core.userbrowse.get_soulseek_url(
                transfer.user, transfer.filename.rsplit("\\", 1)[0] + "\\")
            copy_text(url)

    def on_open_file_manager(self, *_args):

        for transfer in self.selected_transfers:
            file_path = core.transfers.get_current_download_file_path(
                transfer.user, transfer.filename, transfer.path, transfer.size)
            folder_path = os.path.dirname(file_path)

            if transfer.status == "Finished":
                # Prioritize finished downloads
                break

        open_file_path(folder_path, command=config.sections["ui"]["filemanager"])

    def on_play_files(self, *_args):

        for transfer in self.selected_transfers:
            file_path = core.transfers.get_current_download_file_path(
                transfer.user, transfer.filename, transfer.path, transfer.size)

            open_file_path(file_path, command=config.sections["players"]["default"])

    def on_browse_folder(self, *_args):

        requested_users = set()
        requested_folders = set()

        for transfer in self.selected_transfers:
            user = transfer.user
            folder = transfer.filename.rsplit("\\", 1)[0] + "\\"

            if user not in requested_users and folder not in requested_folders:
                core.userbrowse.browse_user(user, path=folder)

                requested_users.add(user)
                requested_folders.add(folder)

    def on_clear_queued(self, *_args):
        core.transfers.clear_downloads(statuses=["Queued"])

    def on_clear_finished(self, *_args):
        core.transfers.clear_downloads(statuses=["Finished"])

    def on_clear_paused(self, *_args):
        core.transfers.clear_downloads(statuses=["Paused"])

    def on_clear_finished_filtered(self, *_args):
        core.transfers.clear_downloads(statuses=["Finished", "Filtered"])

    def on_clear_filtered(self, *_args):
        core.transfers.clear_downloads(statuses=["Filtered"])

    def on_clear_deleted(self, *_args):
        core.transfers.clear_downloads(clear_deleted=True)
