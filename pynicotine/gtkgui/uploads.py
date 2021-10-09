# COPYRIGHT (C) 2020-2021 Nicotine+ Team
# COPYRIGHT (C) 2016-2018 Mutnick <mutnick@techie.com>
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2009-2011 Quinox <quinox@users.sf.net>
# COPYRIGHT (C) 2009 Hedonist <ak@sensi.org>
# COPYRIGHT (C) 2006-2008 Daelstorm <daelstorm@gmail.com>
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
from pynicotine.gtkgui.transferlist import TransferList
from pynicotine.gtkgui.widgets.dialogs import option_dialog
from pynicotine.utils import open_file_path


class Uploads(TransferList):

    def __init__(self, frame):

        self.retry_label = _("_Retry")
        self.abort_label = _("_Abort")
        self.aborted_status = _("Aborted")

        TransferList.__init__(self, frame, type='upload')

        self.popup_menu_clear.setup(
            ("#" + _("Finished / Aborted / Failed"), self.on_clear_finished_failed),
            ("#" + _("Finished / Aborted"), self.on_clear_finished_aborted),
            ("", None),
            ("#" + _("Finished"), self.on_clear_finished),
            ("#" + _("Aborted"), self.on_clear_aborted),
            ("#" + _("Failed"), self.on_clear_failed),
            ("#" + _("Queued..."), self.on_try_clear_queued),
            ("", None),
            ("#" + _("Clear All..."), self.on_try_clear_all),
        )

    def on_try_clear_queued(self, *args):

        option_dialog(
            parent=self.frame.MainWindow,
            title=_('Clear Queued Uploads'),
            message=_('Are you sure you wish to clear all queued uploads?'),
            callback=self.on_clear_response,
            callback_data="queued"
        )

    def on_try_clear_all(self, *args):

        option_dialog(
            parent=self.frame.MainWindow,
            title=_('Clear All Uploads'),
            message=_('Are you sure you wish to clear all uploads?'),
            callback=self.on_clear_response,
            callback_data="all"
        )

    def on_open_file_manager(self, *args):

        transfer = next(iter(self.selected_transfers), None)

        if not transfer or not os.path.exists(transfer.path):
            return

        # Finally, try to open the directory we got...
        command = config.sections["ui"]["filemanager"]
        open_file_path(transfer.path, command)

    def on_play_files(self, *args):

        for transfer in self.selected_transfers:
            basename = str.split(transfer.filename, '\\')[-1]
            playfile = os.path.join(transfer.path, basename)

            if os.path.exists(playfile):
                command = config.sections["players"]["default"]
                open_file_path(playfile, command)

    def on_browse_folder(self, *args):

        transfer = next(iter(self.selected_transfers), None)

        if not transfer:
            return

        user = config.sections["server"]["login"]
        folder = transfer.filename.rsplit('\\', 1)[0]

        self.frame.np.userbrowse.browse_user(user, folder=folder)

    def on_abort_user(self, *args):

        self.select_transfers()

        for user in self.selected_users:
            for transfer in self.transfer_list:
                if transfer.user == user:
                    self.selected_transfers.add(transfer)

        self.abort_transfers()

    def on_clear_aborted(self, *args):
        self.clear_transfers(["Aborted", "Cancelled", "Disallowed extension", "User logged off"])

    def on_clear_failed(self, *args):
        self.clear_transfers(["Cannot connect", "Local file error", "Remote file error"])

    def on_clear_finished_aborted(self, *args):
        self.clear_transfers(["Aborted", "Cancelled", "Disallowed extension", "User logged off", "Finished"])

    def on_clear_finished_failed(self, *args):
        self.clear_transfers(["Aborted", "Cancelled", "Disallowed extension", "User logged off", "Finished",
                              "Cannot connect", "Local file error", "Remote file error"])
