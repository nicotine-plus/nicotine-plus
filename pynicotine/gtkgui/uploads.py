# COPYRIGHT (C) 2020 Nicotine+ Team
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
from gettext import gettext as _

from gi.repository import Gdk
from gi.repository import Gtk as gtk

from _thread import start_new_thread
from pynicotine import slskmessages
from pynicotine.gtkgui.dialogs import OptionDialog
from pynicotine.gtkgui.transferlist import TransferList
from pynicotine.gtkgui.utils import CollapseTreeview
from pynicotine.gtkgui.utils import FillFileGroupingCombobox
from pynicotine.gtkgui.utils import PopupMenu
from pynicotine.gtkgui.utils import SetTreeviewSelectedRow
from pynicotine.utils import executeCommand


class Uploads(TransferList):

    def __init__(self, frame):

        TransferList.__init__(self, frame, frame.UploadList, type='upload')
        self.myvbox = self.frame.uploadsvbox

        self.popup_menu_users = PopupMenu(self.frame, False)
        self.popup_menu_clear = popup2 = PopupMenu(self.frame, False)
        popup2.setup(
            ("#" + _("Clear finished/erred"), self.OnClearFinishedErred),
            ("#" + _("Clear finished/aborted"), self.OnClearFinishedAborted),
            ("#" + _("Clear finished"), self.OnClearFinished),
            ("#" + _("Clear aborted"), self.OnClearAborted),
            ("#" + _("Clear queued"), self.OnClearQueued),
            ("#" + _("Clear failed"), self.OnClearFailed)
        )

        self.popup_menu = popup = PopupMenu(frame)
        popup.setup(
            ("#" + _("Copy _URL"), self.OnCopyURL),
            ("#" + _("Copy folder URL"), self.OnCopyDirURL),
            ("#" + _("Send to _player"), self.OnPlayFiles),
            ("#" + _("Open Directory"), self.OnOpenDirectory),
            ("#" + _("Search"), self.OnFileSearch),
            (1, _("User(s)"), self.popup_menu_users, self.OnPopupMenuUsers),
            ("", None),
            ("#" + _("Abor_t"), self.OnAbortTransfer),
            ("#" + _("_Clear"), self.OnClearTransfer),
            ("#" + _("_Retry"), self.OnUploadTransfer),
            ("", None),
            (1, _("Clear Groups"), self.popup_menu_clear, None)
        )

        frame.clearUploadFinishedErredButton.connect("clicked", self.OnClearFinishedErred)
        frame.clearUploadQueueButton.connect("clicked", self.OnTryClearQueued)
        frame.abortUploadButton.connect("clicked", self.OnAbortTransfer)
        frame.abortUserUploadButton.connect("clicked", self.OnAbortUser)
        frame.banUploadButton.connect("clicked", self.OnBan)
        frame.UploadList.expand_all()

        self.frame.ToggleAutoclearUploads.set_active(self.frame.np.config.sections["transfers"]["autoclear_uploads"])
        frame.ToggleAutoclearUploads.connect("toggled", self.OnToggleAutoclear)

        FillFileGroupingCombobox(frame.ToggleTreeUploads)
        frame.ToggleTreeUploads.set_active(self.frame.np.config.sections["transfers"]["groupuploads"])
        frame.ToggleTreeUploads.connect("changed", self.OnToggleTree)
        self.OnToggleTree(None)

        self.frame.ExpandUploads.set_active(self.frame.np.config.sections["transfers"]["uploadsexpanded"])
        frame.ExpandUploads.connect("toggled", self.OnExpandUploads)

        self.OnExpandUploads(None)

    def OnTryClearQueued(self, widget):

        direction = "up"

        win = OptionDialog(self.frame, _("Clear All Queued Uploads?"), modal=True, option=False, third="")
        win.connect("response", self.frame.on_clear_response, direction)
        win.set_title(_("Nicotine+") + ": " + _("Clear Queued Transfers"))

        win.show()

    def OnOpenDirectory(self, widget):

        downloaddir = self.frame.np.config.sections["transfers"]["downloaddir"]
        incompletedir = self.frame.np.config.sections["transfers"]["incompletedir"]

        if incompletedir == "":
            incompletedir = downloaddir

        filemanager = self.frame.np.config.sections["ui"]["filemanager"]
        transfer = self.selected_transfers[0]

        if os.path.exists(transfer.path):
            executeCommand(filemanager, transfer.path)
        else:
            executeCommand(filemanager, incompletedir)

    def expand(self, path):
        if self.frame.ExpandDownloads.get_active():
            self.frame.UploadList.expand_to_path(path)
        else:
            CollapseTreeview(self.frame.UploadList, self.TreeUsers)

    def OnExpandUploads(self, widget):

        expanded = self.frame.ExpandUploads.get_active()

        if expanded:
            self.frame.UploadList.expand_all()
            self.frame.ExpandUploadsImage.set_from_icon_name("list-remove-symbolic", gtk.IconSize.BUTTON)
        else:
            CollapseTreeview(self.frame.UploadList, self.TreeUsers)
            self.frame.ExpandUploadsImage.set_from_icon_name("list-add-symbolic", gtk.IconSize.BUTTON)

        self.frame.np.config.sections["transfers"]["uploadsexpanded"] = expanded
        self.frame.np.config.writeConfiguration()

    def OnToggleAutoclear(self, widget):
        self.frame.np.config.sections["transfers"]["autoclear_uploads"] = self.frame.ToggleAutoclearUploads.get_active()

    def OnToggleTree(self, widget):

        self.TreeUsers = self.frame.ToggleTreeUploads.get_active()
        self.frame.np.config.sections["transfers"]["groupuploads"] = self.TreeUsers

        self.RebuildTransfers()

        if self.TreeUsers == 0:
            self.frame.ExpandUploads.hide()
        else:
            self.frame.ExpandUploads.show()

    def OnAbortUser(self, widget):

        self.select_transfers()

        for user in self.selected_users:
            for i in self.list[:]:
                if i.user == user:
                    if i not in self.selected_transfers:
                        self.selected_transfers.append(i)

        TransferList.OnAbortTransfer(self, widget, False, False)
        self.frame.np.transfers.calcUploadQueueSizes()
        self.frame.np.transfers.checkUploadQueue()

    def OnUploadTransfer(self, widget):

        self.select_transfers()

        for transfer in self.selected_transfers:
            filename = transfer.filename
            path = transfer.path
            user = transfer.user

            if user in self.frame.np.transfers.getTransferringUsers():
                continue

            self.frame.np.ProcessRequestToPeer(user, slskmessages.UploadQueueNotification(None))
            self.frame.np.transfers.pushFile(user, filename, path, transfer)

        self.frame.np.transfers.checkUploadQueue()

    def on_key_press_event(self, widget, event):

        key = Gdk.keyval_name(event.keyval)

        if key in ("P", "p"):
            self.OnPopupMenu(widget, event, "keyboard")
        else:
            self.select_transfers()

            if key in ("T", "t"):
                self.OnAbortTransfer(widget)
            elif key == "Delete":
                self.OnAbortTransfer(widget, False, True)
            else:
                # No key match, continue event
                return False

        widget.stop_emission_by_name("key_press_event")
        return True

    def OnPlayFiles(self, widget, prefix=""):
        start_new_thread(self._OnPlayFiles, (widget, prefix))

    def _OnPlayFiles(self, widget, prefix=""):

        executable = self.frame.np.config.sections["players"]["default"]

        if "$" not in executable:
            return

        for fn in self.selected_transfers:
            file = fn.filename.replace("\\", os.sep)
            if os.path.exists(file):
                executeCommand(executable, file, background=False)

    def OnPopupMenu(self, widget, event, kind):

        if kind == "mouse":
            if event.button != 3:
                if event.button == 1 and event.type == Gdk.EventType._2BUTTON_PRESS:
                    self.DoubleClick(event)
                return False

            SetTreeviewSelectedRow(widget, event)

        self.select_transfers()

        users = len(self.selected_users) > 0
        multi_users = len(self.selected_users) > 1  # noqa: F841
        files = len(self.selected_transfers) > 0
        multi_files = len(self.selected_transfers) > 1

        items = self.popup_menu.get_children()
        if users:
            items[5].set_sensitive(True)  # Users Menu
        else:
            items[5].set_sensitive(False)  # Users Menu

        if files and not multi_files:
            act = True
        else:
            act = False

        items[0].set_sensitive(act)
        items[1].set_sensitive(act)

        if users and files:
            act = True
        else:
            act = False

        for i in list(range(3, 5)) + list(range(6, 10)):
            items[i].set_sensitive(act)

        items[2].set_sensitive(act)  # send to player

        self.popup_menu.popup(None, None, None, None, 3, event.time)

        if kind == "keyboard":
            widget.stop_emission_by_name("key_press_event")
        elif kind == "mouse":
            widget.stop_emission_by_name("button_press_event")

        return True

    def ClearByUser(self, user):

        for i in self.list[:]:
            if i.user == user:
                if i.transfertimer is not None:
                    i.transfertimer.cancel()
                self.remove_specific(i)

        self.frame.np.transfers.calcUploadQueueSizes()
        self.frame.np.transfers.checkUploadQueue()

    def DoubleClick(self, event):

        self.select_transfers()
        dc = self.frame.np.config.sections["transfers"]["upload_doubleclick"]

        if dc == 1:  # Send to player
            self.OnPlayFiles(None)
        elif dc == 2:  # File manager
            self.OnOpenDirectory(None)
        elif dc == 3:  # Search
            self.OnFileSearch(None)
        elif dc == 4:  # Abort
            self.OnAbortTransfer(None, False)
        elif dc == 5:  # Clear
            self.OnClearTransfer(None)

    def OnAbortTransfer(self, widget, remove=False, clear=False):

        self.select_transfers()

        TransferList.OnAbortTransfer(self, widget, remove, clear)
        self.frame.np.transfers.calcUploadQueueSizes()
        self.frame.np.transfers.checkUploadQueue()

    def OnClearQueued(self, widget):

        self.select_transfers()

        TransferList.OnClearQueued(self, widget)
        self.frame.np.transfers.calcUploadQueueSizes()
        self.frame.np.transfers.checkUploadQueue()

    def OnClearFailed(self, widget):

        TransferList.OnClearFailed(self, widget)
        self.frame.np.transfers.calcUploadQueueSizes()
        self.frame.np.transfers.checkUploadQueue()
