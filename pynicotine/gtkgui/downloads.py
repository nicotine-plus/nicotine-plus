# COPYRIGHT (C) 2020-2024 Nicotine+ Contributors
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

from pynicotine.core import core
from pynicotine.events import events
from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.popovers.downloadspeeds import DownloadSpeeds
from pynicotine.gtkgui.transfers import Transfers
from pynicotine.gtkgui.widgets import clipboard
from pynicotine.gtkgui.widgets.dialogs import OptionDialog
from pynicotine.transfers import TransferStatus
from pynicotine.utils import human_speed
from pynicotine.utils import open_file_path
from pynicotine.utils import open_folder_path


class Downloads(Transfers):

    def __init__(self, window):

        self.path_separator = os.sep
        self.path_label = _("Path")
        self.retry_label = _("_Resume")
        self.abort_label = _("P_ause")

        self.transfer_page = self.page = window.downloads_page
        self.page.id = "downloads"
        self.toolbar = window.downloads_toolbar
        self.toolbar_start_content = window.downloads_title
        self.toolbar_end_content = window.downloads_end
        self.toolbar_default_widget = window.download_users_button

        self.user_counter = window.download_users_label
        self.file_counter = window.download_files_label
        self.expand_button = window.downloads_expand_button
        self.expand_icon = window.downloads_expand_icon
        self.grouping_button = window.downloads_grouping_button
        self.status_label = window.download_status_label

        super().__init__(window, transfer_type="download")

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
            ("folder-download-finished", self.folder_download_finished),
            ("set-connection-stats", self.set_connection_stats),
            ("start", self.start),
            ("update-download", self.update_model),
            ("update-download-limits", self.update_limits)
        ):
            events.connect(event_name, callback)

        self.download_speeds = DownloadSpeeds(window)

    def start(self):
        self.init_transfers(core.downloads.transfers.values())

    def destroy(self):
        self.download_speeds.destroy()
        super().destroy()

    def get_transfer_folder_path(self, transfer):
        return transfer.folder_path

    def retry_selected_transfers(self):
        core.downloads.retry_downloads(self.selected_transfers)

    def abort_selected_transfers(self):
        core.downloads.abort_downloads(self.selected_transfers)

    def remove_selected_transfers(self):
        core.downloads.clear_downloads(downloads=self.selected_transfers)

    def set_connection_stats(self, download_bandwidth=0, **_kwargs):

        # Sync parent row updates with connection stats
        self._update_pending_parent_rows()

        download_bandwidth = human_speed(download_bandwidth)
        download_bandwidth_text = f"{download_bandwidth} ( {len(core.downloads.active_users)} )"

        if self.window.download_status_label.get_text() == download_bandwidth_text:
            return

        self.window.download_status_label.set_text(download_bandwidth_text)
        self.window.application.tray_icon.set_download_status(
            _("Downloads: %(speed)s") % {"speed": download_bandwidth})

    def on_try_clear_queued(self, *_args):

        OptionDialog(
            parent=self.window,
            title=_("Clear Queued Downloads"),
            message=_("Do you really want to clear all queued downloads?"),
            destructive_response_id="ok",
            callback=self.on_clear_queued
        ).present()

    def on_clear_all_response(self, *_args):
        core.downloads.clear_downloads()

    def on_try_clear_all(self, *_args):

        OptionDialog(
            parent=self.window,
            title=_("Clear All Downloads"),
            message=_("Do you really want to clear all downloads?"),
            destructive_response_id="ok",
            callback=self.on_clear_all_response
        ).present()

    def folder_download_response(self, _dialog, _response_id, data):
        download_callback, callback_args = data
        download_callback(*callback_args)

    def folder_download_finished(self, _folder_path):
        if self.window.current_page_id != self.transfer_page.id:
            self.window.notebook.request_tab_changed(self.transfer_page, is_important=True)

    def download_large_folder(self, username, folder, numfiles, download_callback, callback_args):

        OptionDialog(
            parent=self.window,
            title=_("Download %(num)i files?") % {"num": numfiles},
            message=_("Do you really want to download %(num)i files from %(user)s's folder %(folder)s?") % {
                "num": numfiles, "user": username, "folder": folder},
            buttons=[
                ("cancel", _("_Cancel")),
                ("download", _("_Download Folder"))
            ],
            callback=self.folder_download_response,
            callback_data=(download_callback, callback_args)
        ).present()

    def on_copy_url(self, *_args):

        transfer = next(iter(self.selected_transfers), None)

        if transfer:
            url = core.userbrowse.get_soulseek_url(transfer.username, transfer.virtual_path)
            clipboard.copy_text(url)

    def on_copy_folder_url(self, *_args):

        transfer = next(iter(self.selected_transfers), None)

        if transfer:
            folder_path, separator, _basename = transfer.virtual_path.rpartition("\\")
            url = core.userbrowse.get_soulseek_url(transfer.username, folder_path + separator)

            clipboard.copy_text(url)

    def on_open_file_manager(self, *_args):

        folder_path = None

        for transfer in self.selected_transfers:
            file_path = core.downloads.get_current_download_file_path(transfer)
            folder_path = os.path.dirname(file_path)

            if transfer.status == TransferStatus.FINISHED:
                # Prioritize finished downloads
                break

        open_folder_path(folder_path)

    def on_open_file(self, *_args):

        for transfer in self.selected_transfers:
            file_path = core.downloads.get_current_download_file_path(transfer)
            open_file_path(file_path)

    def on_browse_folder(self, *_args):

        transfer = next(iter(self.selected_transfers), None)

        if not transfer:
            return

        user = transfer.username
        path = transfer.virtual_path

        core.userbrowse.browse_user(user, path=path)

    def on_clear_queued(self, *_args):
        core.downloads.clear_downloads(statuses={TransferStatus.QUEUED})

    def on_clear_finished(self, *_args):
        core.downloads.clear_downloads(statuses={TransferStatus.FINISHED})

    def on_clear_paused(self, *_args):
        core.downloads.clear_downloads(statuses={TransferStatus.PAUSED})

    def on_clear_finished_filtered(self, *_args):
        core.downloads.clear_downloads(statuses={TransferStatus.FINISHED, TransferStatus.FILTERED})

    def on_clear_filtered(self, *_args):
        core.downloads.clear_downloads(statuses={TransferStatus.FILTERED})

    def on_clear_deleted(self, *_args):
        core.downloads.clear_downloads(clear_deleted=True)
