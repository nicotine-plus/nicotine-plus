# COPYRIGHT (C) 2020-2023 Nicotine+ Contributors
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

from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.popovers.uploadspeeds import UploadSpeeds
from pynicotine.gtkgui.transfers import Transfers
from pynicotine.gtkgui.widgets import clipboard
from pynicotine.gtkgui.widgets.dialogs import OptionDialog
from pynicotine.utils import open_file_path
from pynicotine.utils import open_folder_path


class Uploads(Transfers):

    def __init__(self, window):

        self.path_separator = "\\"
        self.path_label = _("Folder")
        self.retry_label = _("_Retry")
        self.abort_label = _("_Abort")
        self.deprioritized_statuses = {"Cancelled", "Finished"}

        self.transfer_page = window.uploads_page
        self.user_counter = window.upload_users_label
        self.file_counter = window.upload_files_label
        self.expand_button = window.uploads_expand_button
        self.expand_icon = window.uploads_expand_icon
        self.grouping_button = window.uploads_grouping_button

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
            ("start", self.start),
            ("update-upload", self.update_model),
            ("update-uploads", self.update_model),
            ("upload-notification", self.new_transfer_notification)
        ):
            events.connect(event_name, callback)

        self.upload_speeds = UploadSpeeds(window)

    def start(self):
        self.init_transfers(core.uploads.transfers.values())

    def get_transfer_folder_path(self, transfer):
        virtual_path = transfer.virtual_path
        return virtual_path.rsplit("\\", 1)[0] if virtual_path else transfer.folder_path

    def retry_selected_transfers(self):
        core.uploads.retry_uploads(self.selected_transfers)

    def abort_selected_transfers(self):
        core.uploads.abort_uploads(self.selected_transfers, denied_message="Cancelled")

    def clear_selected_transfers(self):
        core.uploads.clear_uploads(uploads=self.selected_transfers)

    def on_clear_queued_response(self, *_args):
        core.uploads.clear_uploads(statuses=["Queued"])

    def on_try_clear_queued(self, *_args):

        OptionDialog(
            parent=self.window,
            title=_("Clear Queued Uploads"),
            message=_("Do you really want to clear all queued uploads?"),
            destructive_response_id="ok",
            callback=self.on_clear_queued_response
        ).show()

    def on_clear_all_response(self, *_args):
        core.uploads.clear_uploads()

    def on_try_clear_all(self, *_args):

        OptionDialog(
            parent=self.window,
            title=_("Clear All Uploads"),
            message=_("Do you really want to clear all uploads?"),
            destructive_response_id="ok",
            callback=self.on_clear_all_response
        ).show()

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
            url = core.userbrowse.get_soulseek_url(user, transfer.virtual_path.rsplit("\\", 1)[0] + "\\")
            clipboard.copy_text(url)

    def on_open_file_manager(self, *_args):

        transfer = next(iter(self.selected_transfers), None)

        if transfer:
            open_folder_path(transfer.folder_path)

    def on_open_file(self, *_args):

        for transfer in self.selected_transfers:
            basename = transfer.virtual_path.split("\\")[-1]

            open_file_path(os.path.join(transfer.folder_path, basename))

    def on_browse_folder(self, *_args):

        transfer = next(iter(self.selected_transfers), None)

        if not transfer:
            return

        user = config.sections["server"]["login"]
        folder_path = transfer.virtual_path.rsplit("\\", 1)[0] + "\\"

        core.userbrowse.browse_user(user, path=folder_path)

    def on_abort_users(self, *_args):

        self.select_transfers()

        for transfer in self.transfer_list:
            if transfer.username in self.selected_users and transfer not in self.selected_transfers:
                self.selected_transfers[transfer] = None

        self.abort_selected_transfers()

    def on_ban_users(self, *_args):
        self.select_transfers()
        core.uploads.ban_users(self.selected_users)

    def on_clear_queued(self, *_args):
        core.uploads.clear_uploads(statuses=["Queued"])

    def on_clear_finished(self, *_args):
        core.uploads.clear_uploads(statuses=["Finished"])

    def on_clear_cancelled(self, *_args):
        core.uploads.clear_uploads(statuses=["Cancelled", "Disallowed extension"])

    def on_clear_failed(self, *_args):
        core.uploads.clear_uploads(statuses=["Connection timeout", "Local file error", "Remote file error"])

    def on_clear_logged_off(self, *_args):
        core.uploads.clear_uploads(statuses=["User logged off"])

    def on_clear_finished_cancelled(self, *_args):
        core.uploads.clear_uploads(statuses=["Cancelled", "Disallowed extension", "Finished"])

    def on_clear_finished_failed(self, *_args):
        core.uploads.clear_uploads(
            statuses=["Cancelled", "Disallowed extension", "Finished", "Connection timeout",
                      "Local file error", "Remote file error"])
