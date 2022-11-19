# COPYRIGHT (C) 2020-2022 Nicotine+ Contributors
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
from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.transferlist import TransferList
from pynicotine.gtkgui.utils import copy_text
from pynicotine.gtkgui.widgets.dialogs import OptionDialog
from pynicotine.utils import open_file_path


class Uploads(TransferList):

    def __init__(self, frame):

        self.path_separator = '\\'
        self.path_label = _("Folder")
        self.retry_label = _("_Retry")
        self.abort_label = _("_Abort")

        self.transfer_page = frame.uploads_page
        self.user_counter = frame.upload_users_label
        self.file_counter = frame.upload_files_label
        self.expand_button = frame.uploads_expand_button
        self.expand_icon = frame.uploads_expand_icon
        self.grouping_button = frame.uploads_grouping_button

        TransferList.__init__(self, frame, transfer_type="upload")

        if GTK_API_VERSION >= 4:
            frame.uploads_content.append(self.container)
        else:
            frame.uploads_content.add(self.container)

        self.popup_menu_clear.add_items(
            ("#" + _("Finished / Aborted / Failed"), self.on_clear_finished_failed),
            ("#" + _("Finished / Aborted"), self.on_clear_finished_aborted),
            ("", None),
            ("#" + _("Finished"), self.on_clear_finished),
            ("#" + _("Aborted"), self.on_clear_aborted),
            ("#" + _("Failed"), self.on_clear_failed),
            ("#" + _("User logged off"), self.on_clear_logged_out),
            ("#" + _("Queued…"), self.on_try_clear_queued),
            ("", None),
            ("#" + _("Everything…"), self.on_try_clear_all),
        )
        self.popup_menu_clear.update_model()

    def retry_selected_transfers(self):
        core.transfers.retry_uploads(self.selected_transfers)

    def abort_selected_transfers(self):
        core.transfers.abort_uploads(self.selected_transfers, denied_message="Cancelled")

    def clear_selected_transfers(self):
        core.transfers.clear_uploads(uploads=self.selected_transfers)

    def on_clear_queued_response(self, _dialog, response_id, _data):
        if response_id == 2:
            core.transfers.clear_uploads(statuses=["Queued"])

    def on_try_clear_queued(self, *_args):

        OptionDialog(
            parent=self.frame.window,
            title=_('Clear Queued Uploads'),
            message=_('Do you really want to clear all queued uploads?'),
            callback=self.on_clear_queued_response
        ).show()

    def on_clear_all_response(self, _dialog, response_id, _data):
        if response_id == 2:
            core.transfers.clear_uploads()

    def on_try_clear_all(self, *_args):

        OptionDialog(
            parent=self.frame.window,
            title=_('Clear All Uploads'),
            message=_('Do you really want to clear all uploads?'),
            callback=self.on_clear_all_response
        ).show()

    def on_copy_url(self, *_args):

        transfer = next(iter(self.selected_transfers), None)

        if transfer:
            user = config.sections["server"]["login"]
            url = core.userbrowse.get_soulseek_url(user, transfer.filename)
            copy_text(url)

    def on_copy_dir_url(self, *_args):

        transfer = next(iter(self.selected_transfers), None)

        if transfer:
            user = config.sections["server"]["login"]
            url = core.userbrowse.get_soulseek_url(user, transfer.filename.rsplit('\\', 1)[0] + '\\')
            copy_text(url)

    def on_open_file_manager(self, *_args):

        transfer = next(iter(self.selected_transfers), None)

        if transfer:
            open_file_path(file_path=transfer.path, command=config.sections["ui"]["filemanager"])

    def on_play_files(self, *_args):

        for transfer in self.selected_transfers:
            base_name = str.split(transfer.filename, '\\')[-1]

            open_file_path(file_path=os.path.join(transfer.path, base_name),
                           command=config.sections["players"]["default"])

    def on_browse_folder(self, *_args):

        transfer = next(iter(self.selected_transfers), None)

        if not transfer:
            return

        user = config.sections["server"]["login"]
        folder = transfer.filename.rsplit('\\', 1)[0] + '\\'

        core.userbrowse.browse_user(user, path=folder)

    def on_abort_users(self, *_args):

        self.select_transfers()

        for transfer in self.transfer_list:
            if transfer.user in self.selected_users and transfer not in self.selected_transfers:
                self.selected_transfers[transfer] = None

        self.abort_selected_transfers()

    def on_ban_users(self, *_args):
        self.select_transfers()
        core.transfers.ban_users(self.selected_users)

    def on_clear_queued(self, *_args):
        core.transfers.clear_uploads(statuses=["Queued"])

    def on_clear_finished(self, *_args):
        core.transfers.clear_uploads(statuses=["Finished"])

    def on_clear_aborted(self, *_args):
        core.transfers.clear_uploads(statuses=["Aborted", "Cancelled", "Disallowed extension"])

    def on_clear_failed(self, *_args):
        core.transfers.clear_uploads(statuses=["Connection timeout", "Local file error", "Remote file error"])

    def on_clear_logged_out(self, *_args):
        core.transfers.clear_uploads(statuses=["User logged off"])

    def on_clear_finished_aborted(self, *_args):
        core.transfers.clear_uploads(statuses=["Aborted", "Cancelled", "Disallowed extension", "Finished"])

    def on_clear_finished_failed(self, *_args):
        core.transfers.clear_uploads(
            statuses=["Aborted", "Cancelled", "Disallowed extension", "Finished", "Connection timeout",
                      "Local file error", "Remote file error"])
