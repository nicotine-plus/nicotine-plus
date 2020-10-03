# COPYRIGHT (C) 2020 Nicotine+ Team
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
import os
from gettext import gettext as _

from gi.repository import Gdk
from gi.repository import Gtk as gtk

from _thread import start_new_thread
from pynicotine.gtkgui.dialogs import MetaDialog
from pynicotine.gtkgui.dialogs import OptionDialog
from pynicotine.gtkgui.transferlist import TransferList
from pynicotine.gtkgui.utils import CollapseTreeview
from pynicotine.gtkgui.utils import FillFileGroupingCombobox
from pynicotine.gtkgui.utils import HumanSize
from pynicotine.gtkgui.utils import HumanSpeed
from pynicotine.gtkgui.utils import PopupMenu
from pynicotine.gtkgui.utils import SetTreeviewSelectedRow
from pynicotine.utils import executeCommand


class Downloads(TransferList):

    def __init__(self, frame):

        TransferList.__init__(self, frame, frame.DownloadList, type='download')
        self.myvbox = self.frame.downloadsvbox

        self.popup_menu_users = PopupMenu(self.frame, False)
        self.popup_menu_clear = popup2 = PopupMenu(self.frame, False)
        popup2.setup(
            ("#" + _("Clear finished/aborted"), self.OnClearFinishedAborted),
            ("#" + _("Clear finished"), self.OnClearFinished),
            ("#" + _("Clear aborted"), self.OnClearAborted),
            ("#" + _("Clear paused"), self.OnClearPaused),
            ("#" + _("Clear filtered"), self.OnClearFiltered),
            ("#" + _("Clear queued"), self.OnClearQueued)
        )

        self.popup_menu = popup = PopupMenu(frame)
        popup.setup(
            ("#" + _("Copy _URL"), self.OnCopyURL),
            ("#" + _("Copy folder URL"), self.OnCopyDirURL),
            ("#" + _("Send to _player"), self.OnPlayFiles),
            ("#" + _("View Metadata of file(s)"), self.OnDownloadMeta),
            ("#" + _("Open folder"), self.OnOpenDirectory),
            ("#" + _("Search"), self.OnFileSearch),
            (1, _("User(s)"), self.popup_menu_users, self.OnPopupMenuUsers),
            ("", None),
            ("#" + _("_Retry"), self.OnRetryTransfer),
            ("", None),
            ("#" + _("Abor_t"), self.OnAbortTransfer),
            ("#" + _("Abort & Delete"), self.OnAbortRemoveTransfer),
            ("#" + _("_Clear"), self.OnClearTransfer),
            ("", None),
            (1, _("Clear Groups"), self.popup_menu_clear, None)
        )

        frame.clearFinishedAbortedButton.connect("clicked", self.OnClearFinishedAborted)
        frame.clearQueuedButton.connect("clicked", self.OnTryClearQueued)
        frame.retryTransferButton.connect("clicked", self.OnRetryTransfer)
        frame.abortTransferButton.connect("clicked", self.OnSelectAbortTransfer)
        frame.deleteTransferButton.connect("clicked", self.OnAbortRemoveTransfer)
        frame.banDownloadButton.connect("clicked", self.OnBan)
        frame.DownloadList.expand_all()

        self.frame.ToggleAutoclearDownloads.set_active(self.frame.np.config.sections["transfers"]["autoclear_downloads"])
        frame.ToggleAutoclearDownloads.connect("toggled", self.OnToggleAutoclear)

        FillFileGroupingCombobox(frame.ToggleTreeDownloads)
        frame.ToggleTreeDownloads.set_active(self.frame.np.config.sections["transfers"]["groupdownloads"])
        frame.ToggleTreeDownloads.connect("changed", self.OnToggleTree)
        self.OnToggleTree(None)

        self.frame.ExpandDownloads.set_active(self.frame.np.config.sections["transfers"]["downloadsexpanded"])
        frame.ExpandDownloads.connect("toggled", self.OnExpandDownloads)
        self.OnExpandDownloads(None)

    def OnTryClearQueued(self, widget):

        direction = "down"
        OptionDialog(
            parent=self.frame.MainWindow,
            title=_('Clear Queued Downloads'),
            message=_('Are you sure you wish to clear all queued downloads?'),
            callback=self.frame.on_clear_response,
            callback_data=direction
        )

    def expand(self, path):
        if self.frame.ExpandDownloads.get_active():
            self.frame.DownloadList.expand_to_path(path)
        else:
            CollapseTreeview(self.frame.DownloadList, self.TreeUsers)

    def OnExpandDownloads(self, widget):

        expanded = self.frame.ExpandDownloads.get_active()

        if expanded:
            self.frame.DownloadList.expand_all()
            self.frame.ExpandDownloadsImage.set_from_icon_name("list-remove-symbolic", gtk.IconSize.BUTTON)
        else:
            CollapseTreeview(self.frame.DownloadList, self.TreeUsers)
            self.frame.ExpandDownloadsImage.set_from_icon_name("list-add-symbolic", gtk.IconSize.BUTTON)

        self.frame.np.config.sections["transfers"]["downloadsexpanded"] = expanded
        self.frame.np.config.writeConfiguration()

    def OnToggleAutoclear(self, widget):
        self.frame.np.config.sections["transfers"]["autoclear_downloads"] = self.frame.ToggleAutoclearDownloads.get_active()

    def OnToggleTree(self, widget):
        self.TreeUsers = self.frame.ToggleTreeDownloads.get_active()
        self.frame.np.config.sections["transfers"]["groupdownloads"] = self.TreeUsers

        if self.TreeUsers == 0:
            self.frame.ExpandDownloads.hide()
        else:
            self.frame.ExpandDownloads.show()

        self.RebuildTransfers()

    def MetaBox(self, title="Meta Data", message="", data=None, modal=True, Search=False):

        win = MetaDialog(self.frame, message, data, modal, Search=Search)
        win.set_title(title)
        win.show()
        gtk.main()

        return win.ret

    def SelectedResultsAllData(self, model, path, iter, data):
        if iter in self.selected_users:
            return

        user = model.get_value(iter, 0)
        filename = model.get_value(iter, 2)
        fullname = model.get_value(iter, 10)
        size = speed = "0"
        length = None
        queue = immediate = num = country = bitratestr = ""

        for transfer in self.frame.np.transfers.downloads:
            if transfer.user == user and fullname == transfer.filename:
                size = HumanSize(transfer.size)
                try:
                    speed = HumanSpeed(transfer.speed)
                except Exception:
                    pass
                bitratestr = str(transfer.bitrate)
                length = str(transfer.length)
                break
        else:
            return

        directory = fullname.rsplit("\\", 1)[0]

        data[len(data)] = {
            "user": user,
            "fn": fullname,
            "position": num,
            "filename": filename,
            "directory": directory,
            "size": size,
            "speed": speed,
            "queue": queue,
            "immediate": immediate,
            "bitrate": bitratestr,
            "length": length,
            "country": country
        }

    def OnDownloadMeta(self, widget):

        if not self.frame.np.transfers:
            return

        data = {}
        self.widget.get_selection().selected_foreach(self.SelectedResultsAllData, data)

        if data != {}:
            self.MetaBox(title=_("Downloads Metadata"), message=_("<b>Metadata</b> for Downloads"), data=data, modal=True, Search=False)

    def OnOpenDirectory(self, widget):

        downloaddir = self.frame.np.config.sections["transfers"]["downloaddir"]
        incompletedir = self.frame.np.config.sections["transfers"]["incompletedir"]

        if incompletedir == "":
            incompletedir = downloaddir

        filemanager = self.frame.np.config.sections["ui"]["filemanager"]
        transfer = next(iter(self.selected_transfers))

        complete_path = os.path.join(downloaddir, transfer.path)

        if transfer.path == "":
            if transfer.status == "Finished":
                executeCommand(filemanager, downloaddir)
            else:
                executeCommand(filemanager, incompletedir)
        elif os.path.exists(complete_path):  # and tranfer.status is "Finished"
            executeCommand(filemanager, complete_path)
        else:
            executeCommand(filemanager, incompletedir)

    def OnSelectAbortTransfer(self, widget):
        self.select_transfers()

        self.OnAbortTransfer(widget, False)

    def on_key_press_event(self, widget, event):

        key = Gdk.keyval_name(event.keyval)

        if key in ("P", "p"):
            self.OnPopupMenu(widget, event, "keyboard")
        else:
            self.select_transfers()

            if key in ("T", "t"):
                self.OnAbortTransfer(widget)
            elif key in ("R", "r"):
                self.OnRetryTransfer(widget)
            elif key == "Delete":
                self.OnAbortTransfer(widget, True, True)
            else:
                # No key match, continue event
                return False

        widget.stop_emission_by_name("key_press_event")
        return True

    def OnPlayFiles(self, widget, prefix=""):
        start_new_thread(self._OnPlayFiles, (widget, prefix))

    def _OnPlayFiles(self, widget, prefix=""):

        executable = self.frame.np.config.sections["players"]["default"]
        downloaddir = self.frame.np.config.sections["transfers"]["downloaddir"]

        if "$" not in executable:
            return

        for fn in self.selected_transfers:

            playfile = None

            if fn.file is not None and os.path.exists(fn.file.name):
                playfile = fn.file.name
            else:
                # If this file doesn't exist anymore, it may have finished downloading and have been renamed
                # try looking in the download directory and match the original filename.
                basename = str.split(fn.filename, '\\')[-1]
                path = os.sep.join([downloaddir, basename])

                if os.path.exists(path):
                    playfile = path

            if playfile:
                executeCommand(executable, playfile, background=False)

    def DoubleClick(self, event):

        self.select_transfers()
        dc = self.frame.np.config.sections["transfers"]["download_doubleclick"]

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
        elif dc == 6:  # Retry
            self.OnRetryTransfer(None)

    def OnPopupMenu(self, widget, event, kind):

        if kind == "mouse":
            if event.button == 3:
                SetTreeviewSelectedRow(widget, event)

            else:
                pathinfo = widget.get_path_at_pos(event.x, event.y)

                if pathinfo is None:
                    widget.get_selection().unselect_all()

                elif event.button == 1 and event.type == Gdk.EventType._2BUTTON_PRESS:
                    self.DoubleClick(event)

                return False

        self.select_transfers()

        users = len(self.selected_users) > 0
        files = len(self.selected_transfers) > 0

        items = self.popup_menu.get_children()
        if users:
            items[6].set_sensitive(True)  # Users Menu
        else:
            items[6].set_sensitive(False)  # Users Menu

        if files:
            act = True
        else:
            # Disable options
            # Copy URL, Copy Folder URL, Send to player, View Meta, File manager, Search filename
            act = False

        for i in range(0, 6):
            items[i].set_sensitive(act)

        if not users or not files:
            # Disable options
            # Abort, Abort and Remove, retry, clear
            act = False
        else:
            act = True

        for i in range(8, 13):
            items[i].set_sensitive(act)

        self.popup_menu.popup(None, None, None, None, 3, event.time)

        if kind == "keyboard":
            widget.stop_emission_by_name("key_press_event")
        elif kind == "mouse":
            widget.stop_emission_by_name("button_press_event")

        return True

    def OnRetryTransfer(self, widget):

        self.select_transfers()

        for transfer in self.selected_transfers:

            if transfer.status in ["Finished", "Old"]:
                continue

            self.frame.np.transfers.AbortTransfer(transfer)
            self.frame.np.transfers.getFile(transfer.user, transfer.filename, transfer.path, transfer)

    def OnAbortRemoveTransfer(self, widget):
        self.select_transfers()

        self.OnClearTransfer(widget)
