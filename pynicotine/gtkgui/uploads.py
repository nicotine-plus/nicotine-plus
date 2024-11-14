# COPYRIGHT (C) 2020-2024 Nicotine+ Contributors
# COPYRIGHT (C) 2016-2018 Mutnick <mutnick@techie.com>
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2009-2011 quinox <quinox@users.sf.net>
# COPYRIGHT (C) 2009 hedonist <ak@sensi.org>
# COPYRIGHT (C) 2006-2008 daelstorm <daelstorm@gmail.com>
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

from gi.repository import Gtk

from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.popovers.uploadspeeds import UploadSpeeds
from pynicotine.gtkgui.transfers import Transfers
from pynicotine.gtkgui.widgets import clipboard
from pynicotine.gtkgui.widgets.dialogs import OptionDialog
from pynicotine.transfers import TransferStatus
from pynicotine.utils import human_speed
from pynicotine.utils import open_file_path
from pynicotine.utils import open_folder_path


class Uploads(Transfers):

    def __init__(self, window):

        self.path_separator = "\\"
        self.path_label = _("Folder")
        self.retry_label = _("_Retry")
        self.abort_label = _("_Abort")

        self.transfer_page = self.page = window.uploads_page
        self.page.id = "uploads"
        self.toolbar = window.uploads_toolbar
        self.toolbar_start_content = window.uploads_title
        self.toolbar_end_content = window.uploads_end
        self.toolbar_default_widget = window.upload_users_button

        self.user_counter = window.upload_users_label
        self.file_counter = window.upload_files_label
        self.expand_button = window.uploads_expand_button
        self.expand_icon = window.uploads_expand_icon
        self.grouping_button = window.uploads_grouping_button
        self.status_label = window.upload_status_label

        super().__init__(window, transfer_type="upload")

        if GTK_API_VERSION >= 4:
            window.uploads_content.append(self.container)
        else:
            window.uploads_content.add(self.container)

        self.popup_menu_clear.add_items(
            ("#" + _("Finished / Cancelled / Failed"), self.on_clear_finished_failed),
            ("#" + _("Finished / Cancelled"), self.on_clear_finished_cancelled),
            ("", None),
            ("#" + _("Finished"), self.on_clear_finished),
            ("#" + _("Cancelled"), self.on_clear_cancelled),
            ("#" + _("Failed"), self.on_clear_failed),
            ("#" + _("User Logged Off"), self.on_clear_logged_off),
            ("#" + _("Queued…"), self.on_try_clear_queued),
            ("", None),
            ("#" + _("Everything…"), self.on_try_clear_all),
        )
        self.popup_menu_clear.update_model()

        for event_name, callback in (
            ("abort-upload", self.abort_transfer),
            ("abort-uploads", self.abort_transfers),
            ("clear-upload", self.clear_transfer),
            ("clear-uploads", self.clear_transfers),
            ("set-connection-stats", self.set_connection_stats),
            ("start", self.start),
            ("update-upload", self.update_model),
            ("update-upload-limits", self.update_limits),
            ("uploads-shutdown-request", self.shutdown_request),
            ("uploads-shutdown-cancel", self.shutdown_cancel)
        ):
            events.connect(event_name, callback)

        self.upload_speeds = UploadSpeeds(window)

    def start(self):
        self.init_transfers(core.uploads.transfers.values())

    def destroy(self):
        self.upload_speeds.destroy()
        super().destroy()

    def get_transfer_folder_path(self, transfer):

        virtual_path = transfer.virtual_path

        if virtual_path:
            folder_path, _separator, _basename = virtual_path.rpartition("\\")
            return folder_path

        return transfer.folder_path

    def retry_selected_transfers(self):
        core.uploads.retry_uploads(self.selected_transfers)

    def abort_selected_transfers(self):
        core.uploads.abort_uploads(self.selected_transfers, denied_message="Cancelled")

    def remove_selected_transfers(self):
        core.uploads.clear_uploads(uploads=self.selected_transfers)

    def set_connection_stats(self, upload_bandwidth=0, **_kwargs):

        # Sync parent row updates with connection stats
        self._update_pending_parent_rows()

        upload_bandwidth = human_speed(upload_bandwidth)
        upload_bandwidth_text = f"{upload_bandwidth} ( {len(core.uploads.active_users)} )"

        if self.window.upload_status_label.get_text() == upload_bandwidth_text:
            return

        self.window.upload_status_label.set_text(upload_bandwidth_text)
        self.window.application.tray_icon.set_upload_status(
            _("Uploads: %(speed)s") % {"speed": upload_bandwidth})

    def shutdown_request(self):

        icon_name = "system-shutdown-symbolic"
        icon_args = (Gtk.IconSize.BUTTON,) if GTK_API_VERSION == 3 else ()  # pylint: disable=no-member
        toggle_status_action = self.window.lookup_action("toggle-status")

        toggle_status_action.set_enabled(False)
        self.window.user_status_button.set_active(True)
        toggle_status_action.set_enabled(True)

        self.window.user_status_icon.set_from_icon_name(icon_name, *icon_args)
        self.window.user_status_label.set_text(_("Quitting..."))

    def shutdown_cancel(self):
        self.window.update_user_status()

    def on_try_clear_queued(self, *_args):

        OptionDialog(
            parent=self.window,
            title=_("Clear Queued Uploads"),
            message=_("Do you really want to clear all queued uploads?"),
            destructive_response_id="ok",
            callback=self.on_clear_queued
        ).present()

    def on_clear_all_response(self, *_args):
        core.uploads.clear_uploads()

    def on_try_clear_all(self, *_args):

        OptionDialog(
            parent=self.window,
            title=_("Clear All Uploads"),
            message=_("Do you really want to clear all uploads?"),
            destructive_response_id="ok",
            callback=self.on_clear_all_response
        ).present()

    def on_copy_url(self, *_args):

        transfer = next(iter(self.selected_transfers), None)

        if transfer:
            user = config.sections["server"]["login"]
            url = core.userbrowse.get_soulseek_url(user, transfer.virtual_path)
            clipboard.copy_text(url)

    def on_copy_folder_url(self, *_args):

        transfer = next(iter(self.selected_transfers), None)

        if transfer:
            user = config.sections["server"]["login"]
            folder_path, separator, _basename = transfer.virtual_path.rpartition("\\")
            url = core.userbrowse.get_soulseek_url(user, folder_path + separator)

            clipboard.copy_text(url)

    def on_open_file_manager(self, *_args):

        transfer = next(iter(self.selected_transfers), None)

        if transfer:
            open_folder_path(transfer.folder_path)

    def on_open_file(self, *_args):

        for transfer in self.selected_transfers:
            basename = transfer.virtual_path.rpartition("\\")[-1]

            open_file_path(os.path.join(transfer.folder_path, basename))

    def on_browse_folder(self, *_args):

        transfer = next(iter(self.selected_transfers), None)

        if not transfer:
            return

        user = config.sections["server"]["login"]
        path = transfer.virtual_path

        core.userbrowse.browse_user(user, path=path)

    def on_abort_users(self, *_args):

        self.select_transfers()

        for transfer in self.transfer_list:
            if transfer.username in self.selected_users and transfer not in self.selected_transfers:
                self.selected_transfers[transfer] = None

        self.abort_selected_transfers()

    def on_ban_users(self, *_args):

        self.select_transfers()

        for username in self.selected_users:
            core.network_filter.ban_user(username)

    def on_clear_queued(self, *_args):
        core.uploads.clear_uploads(statuses={TransferStatus.QUEUED})

    def on_clear_finished(self, *_args):
        core.uploads.clear_uploads(statuses={TransferStatus.FINISHED})

    def on_clear_cancelled(self, *_args):
        core.uploads.clear_uploads(statuses={TransferStatus.CANCELLED})

    def on_clear_failed(self, *_args):
        core.uploads.clear_uploads(statuses={TransferStatus.CONNECTION_TIMEOUT, TransferStatus.LOCAL_FILE_ERROR})

    def on_clear_logged_off(self, *_args):
        core.uploads.clear_uploads(statuses={TransferStatus.USER_LOGGED_OFF})

    def on_clear_finished_cancelled(self, *_args):
        core.uploads.clear_uploads(statuses={TransferStatus.CANCELLED, TransferStatus.FINISHED})

    def on_clear_finished_failed(self, *_args):
        core.uploads.clear_uploads(
            statuses={TransferStatus.CANCELLED, TransferStatus.FINISHED, TransferStatus.CONNECTION_TIMEOUT,
                      TransferStatus.LOCAL_FILE_ERROR})
