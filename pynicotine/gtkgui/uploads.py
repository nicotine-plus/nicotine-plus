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
from pynicotine.gtkgui.utils import open_file_path
from pynicotine.gtkgui.widgets.messagedialogs import option_dialog


class Uploads(TransferList):

    def __init__(self, frame, tab_label):

        TransferList.__init__(self, frame, type='upload')
        self.tab_label = tab_label

        self.popup_menu_clear.setup(
            ("#" + _("Clear Finished / Failed"), self.on_clear_finished_failed),
            ("#" + _("Clear Finished / Aborted"), self.on_clear_finished_aborted),
            ("#" + _("Clear Finished"), self.on_clear_finished),
            ("#" + _("Clear Aborted"), self.on_clear_aborted),
            ("#" + _("Clear Failed"), self.on_clear_failed),
            ("#" + _("Clear Queued"), self.on_clear_queued)
        )

    def on_try_clear_queued(self, *args):

        option_dialog(
            parent=self.frame.MainWindow,
            title=_('Clear Queued Uploads'),
            message=_('Are you sure you wish to clear all queued uploads?'),
            callback=self.on_clear_response
        )

    def on_open_directory(self, *args):

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

    def on_abort_user(self, *args):

        self.select_transfers()

        for user in self.selected_users:
            for transfer in self.list:
                if transfer.user == user:
                    self.selected_transfers.add(transfer)

        self.abort_transfers()

    def on_clear_aborted(self, *args):
        self.clear_transfers(["Aborted", "Cancelled", "User logged off"])

    def on_clear_failed(self, *args):
        self.clear_transfers(["Cannot connect", "Local file error", "Remote file error"])

    def on_clear_finished_aborted(self, *args):
        self.clear_transfers(["Aborted", "Cancelled", "User logged off", "Finished"])

    def on_clear_finished_failed(self, *args):
        self.clear_transfers(["Aborted", "Cancelled", "User logged off", "Finished", "Cannot connect", "Local file error", "Remote file error"])
