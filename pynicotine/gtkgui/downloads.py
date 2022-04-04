# COPYRIGHT (C) 2020-2022 Nicotine+ Team
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2016-2018 Mutnick <mutnick@techie.com>
# COPYRIGHT (C) 2013 eL_vErDe <gandalf@le-vert.net>
# COPYRIGHT (C) 2008-2012 Quinox <quinox@users.sf.net>
# COPYRIGHT (C) 2009 Hedonist <ak@sensi.org>
# COPYRIGHT (C) 2006-2009 Daelstorm <daelstorm@gmail.com>
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

from pynicotine.config import config
from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.transferlist import TransferList
from pynicotine.gtkgui.utils import copy_text
from pynicotine.gtkgui.widgets.dialogs import OptionDialog
from pynicotine.utils import open_file_path


class Downloads(TransferList):

    def __init__(self, frame, core):

        self.path_separator = '/'
        self.path_label = _("Path")
        self.retry_label = _("_Resume")
        self.abort_label = _("P_ause")
        self.aborted_status = "Paused"

        self.transfer_page = frame.downloads_page
        self.user_counter = frame.download_users_label
        self.file_counter = frame.download_files_label
        self.expand_button = frame.downloads_expand_button
        self.expand_icon = frame.downloads_expand_icon
        self.grouping_button = frame.downloads_grouping_button

        TransferList.__init__(self, frame, core, transfer_type="download")

        if GTK_API_VERSION >= 4:
            frame.downloads_content.append(self.container)
        else:
            frame.downloads_content.add(self.container)

        self.popup_menu_clear.add_items(
            ("#" + _("Finished / Filtered"), self.on_clear_finished_filtered),
            ("", None),
            ("#" + _("Finished"), self.on_clear_finished),
            ("#" + _("Paused"), self.on_clear_paused),
            ("#" + _("Failed"), self.on_clear_failed),
            ("#" + _("Filtered"), self.on_clear_filtered),
            ("#" + _("Queued…"), self.on_try_clear_queued),
            ("", None),
            ("#" + _("Everything…"), self.on_try_clear_all),
        )
        self.popup_menu_clear.update_model()

    def retry_transfers(self):
        for transfer in self.selected_transfers:
            self.core.transfers.retry_download(transfer)

    def on_try_clear_queued(self, *_args):

        OptionDialog(
            parent=self.frame.window,
            title=_('Clear Queued Downloads'),
            message=_('Do you really want to clear all queued downloads?'),
            callback=self.on_clear_queued_response
        ).show()

    def on_try_clear_all(self, *_args):

        OptionDialog(
            parent=self.frame.window,
            title=_('Clear All Downloads'),
            message=_('Do you really want to clear all downloads?'),
            callback=self.on_clear_all_response
        ).show()

    def folder_download_response(self, _dialog, response_id, msg):
        if response_id == 2:
            self.core.transfers.folder_contents_response(msg)

    def download_large_folder(self, username, folder, numfiles, msg):

        OptionDialog(
            parent=self.frame.window,
            title=_("Download %(num)i files?") % {'num': numfiles},
            message=_("Do you really want to download %(num)i files from %(user)s's folder %(folder)s?") % {
                'num': numfiles, 'user': username, 'folder': folder},
            callback=self.folder_download_response,
            callback_data=msg
        ).show()

    def on_copy_url(self, *_args):

        transfer = next(iter(self.selected_transfers), None)

        if transfer:
            url = self.core.userbrowse.get_soulseek_url(transfer.user, transfer.filename)
            copy_text(url)

    def on_copy_dir_url(self, *_args):

        transfer = next(iter(self.selected_transfers), None)

        if transfer:
            url = self.core.userbrowse.get_soulseek_url(
                transfer.user, transfer.filename.rsplit('\\', 1)[0] + '\\')
            copy_text(url)

    def on_open_file_manager(self, *_args):

        download_folder = config.sections["transfers"]["downloaddir"]
        incomplete_folder = config.sections["transfers"]["incompletedir"] or download_folder

        for transfer in self.selected_transfers:
            if transfer.status == "Finished":
                folder_path = transfer.path or download_folder
                break
        else:
            folder_path = incomplete_folder

        open_file_path(folder_path, command=config.sections["ui"]["filemanager"])

    def on_play_files(self, *_args):

        for transfer in self.selected_transfers:
            file_path = None

            if transfer.file is not None:
                file_path = transfer.file.name

            else:
                # If this file doesn't exist anymore, it may have finished downloading and have been renamed.
                # Try looking in the download directory and match the original filename and size.

                file_path = self.core.transfers.get_existing_download_path(
                    transfer.user, transfer.filename, transfer.path, transfer.size)

            open_file_path(file_path, command=config.sections["players"]["default"])

    def on_browse_folder(self, *_args):

        requested_users = set()
        requested_folders = set()

        for transfer in self.selected_transfers:
            user = transfer.user
            folder = transfer.filename.rsplit('\\', 1)[0] + '\\'

            if user not in requested_users and folder not in requested_folders:
                self.core.userbrowse.browse_user(user, path=folder)

                requested_users.add(user)
                requested_folders.add(folder)

    def on_clear_paused(self, *_args):
        self.clear_transfers(["Paused"])

    def on_clear_finished_filtered(self, *_args):
        self.clear_transfers(["Finished", "Filtered"])

    def on_clear_failed(self, *_args):
        self.clear_transfers(["Connection timeout", "Local file error", "Remote file error", "File not shared"])

    def on_clear_filtered(self, *_args):
        self.clear_transfers(["Filtered"])
