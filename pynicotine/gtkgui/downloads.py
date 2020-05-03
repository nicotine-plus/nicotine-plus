# -*- coding: utf-8 -*-
#
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
import string
from gettext import gettext as _

import gi
from gi.repository import Gdk
from gi.repository import Gtk as gtk

from _thread import start_new_thread
from pynicotine import slskmessages
from pynicotine.gtkgui.entrydialog import MetaDialog
from pynicotine.gtkgui.entrydialog import OptionDialog
from pynicotine.gtkgui.transferlist import TransferList
from pynicotine.gtkgui.utils import HumanSize
from pynicotine.gtkgui.utils import PopupMenu
from pynicotine.gtkgui.utils import PressHeader
from pynicotine.utils import executeCommand

gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')


class Downloads(TransferList):

    def __init__(self, frame):

        TransferList.__init__(self, frame, frame.DownloadList, type='downloads')
        self.myvbox = self.frame.downloadsvbox
        self.frame.DownloadList.set_property("rules-hint", True)
        self.accel_group = gtk.AccelGroup()

        self.popup_menu2 = popup2 = PopupMenu(frame)
        popup2.setup(
            ("#" + _("Clear finished/aborted"), self.OnClearFinishedAborted),
            ("#" + _("Clear finished"), self.OnClearFinished),
            ("#" + _("Clear aborted"), self.OnClearAborted),
            ("#" + _("Clear paused"), self.OnClearPaused),
            ("#" + _("Clear filtered"), self.OnClearFiltered),
            ("#" + _("Clear queued"), self.OnClearQueued)
        )
        self.popup_menu_users = PopupMenu(frame)

        self.popup_menu = popup = PopupMenu(frame)
        popup.setup(
            ("#" + _("Get place in _queue"), self.OnGetPlaceInQueue),
            ("", None),
            ("#" + _("Copy _URL"), self.OnCopyURL),
            ("#" + _("Copy folder URL"), self.OnCopyDirURL),
            ("#" + _("Send to _player"), self.OnPlayFiles),
            ("#" + _("View Metadata of file(s)"), self.OnDownloadMeta),
            ("#" + _("Open Directory"), self.OnOpenDirectory),
            ("#" + _("Search"), self.OnFileSearch),
            (1, _("User(s)"), self.popup_menu_users, self.OnPopupMenuUsers),
            ("", None),
            ("#" + _("_Retry"), self.OnRetryTransfer),
            ("", None),
            ("#" + _("Abor_t"), self.OnAbortTransfer),
            ("#" + _("Abort & Delete"), self.OnAbortRemoveTransfer),
            ("#" + _("_Clear"), self.OnClearTransfer),
            ("", None),
            (1, _("Clear Groups"), self.popup_menu2, None)
        )

        frame.DownloadList.connect("button_press_event", self.OnPopupMenu, "mouse")
        frame.DownloadList.connect("key-press-event", self.on_key_press_event)
        cols = frame.DownloadList.get_columns()

        for i in range(9):

            parent = cols[i].get_widget().get_ancestor(gtk.Button)
            if parent:
                parent.connect("button_press_event", PressHeader)

            # Read Show / Hide column settings from last session
            cols[i].set_visible(self.frame.np.config.sections["columns"]["downloads_columns"][i])

        frame.clearFinishedAbortedButton.connect("clicked", self.OnClearFinishedAborted)
        frame.clearQueuedButton.connect("clicked", self.OnTryClearQueued)
        frame.retryTransferButton.connect("clicked", self.OnRetryTransfer)
        frame.abortTransferButton.connect("clicked", self.OnSelectAbortTransfer)
        frame.deleteTransferButton.connect("clicked", self.OnAbortRemoveTransfer)
        frame.banDownloadButton.connect("clicked", self.OnBan)
        frame.DownloadList.expand_all()

        self.frame.ToggleAutoRetry.set_active(self.frame.np.config.sections["transfers"]["autoretry_downloads"])
        frame.ToggleAutoRetry.connect("toggled", self.OnToggleAutoRetry)

        self.frame.ToggleTreeDownloads.set_active(self.frame.np.config.sections["transfers"]["groupdownloads"])
        frame.ToggleTreeDownloads.connect("toggled", self.OnToggleTree)
        self.OnToggleTree(None)

        self.frame.ExpandDownloads.set_active(self.frame.np.config.sections["transfers"]["downloadsexpanded"])
        frame.ExpandDownloads.connect("toggled", self.OnExpandDownloads)
        self.OnExpandDownloads(None)

    def saveColumns(self):
        columns = []
        widths = []
        for column in self.frame.DownloadList.get_columns():
            columns.append(column.get_visible())
            widths.append(column.get_width())
        self.frame.np.config.sections["columns"]["downloads_columns"] = columns
        self.frame.np.config.sections["columns"]["downloads_widths"] = widths

    def OnToggleAutoRetry(self, widget):
        self.frame.np.config.sections["transfers"]["autoretry_downloads"] = self.frame.ToggleAutoRetry.get_active()

    def OnTryClearQueued(self, widget):

        direction = "down"
        win = OptionDialog(self.frame, _("Clear All Queued Downloads?"), modal=True, status=None, option=False, third="")
        win.connect("response", self.frame.on_clear_response, direction)
        win.set_title(_("Nicotine+") + ": " + _("Clear Queued Transfers"))
        win.set_icon(self.frame.images["n"])
        win.show()

    def expandcollapse(self, path):

        if self.frame.ExpandDownloads.get_active():
            self.frame.DownloadList.expand_row(path, True)
        else:
            self.frame.DownloadList.collapse_row(path)

    def OnExpandDownloads(self, widget):

        expanded = self.frame.ExpandDownloads.get_active()

        if expanded:
            self.frame.DownloadList.expand_all()
            self.frame.ExpandDownloadsImage.set_from_stock(gtk.STOCK_REMOVE, 4)
        else:
            self.frame.DownloadList.collapse_all()
            self.frame.ExpandDownloadsImage.set_from_stock(gtk.STOCK_ADD, 4)

        self.frame.np.config.sections["transfers"]["downloadsexpanded"] = expanded
        self.frame.np.config.writeConfiguration()

    def OnToggleTree(self, widget):

        self.TreeUsers = self.frame.ToggleTreeDownloads.get_active()
        self.frame.np.config.sections["transfers"]["groupdownloads"] = self.TreeUsers

        if not self.TreeUsers:
            self.frame.ExpandDownloads.hide()
        else:
            self.frame.ExpandDownloads.show()

        self.RebuildTransfers()

    def MetaBox(self, title="Meta Data", message="", data=None, modal=True, Search=False):

        win = MetaDialog(self.frame, message, data, modal, Search=Search)
        win.set_title(title)
        win.set_icon(self.frame.images["n"])
        win.show()
        gtk.main()

        return win.ret

    def SelectedResultsAllData(self, model, path, iter, data):
        if iter in self.selected_users:
            return

        user = model.get_value(iter, 0)
        filename = model.get_value(iter, 1)
        fullname = model.get_value(iter, 10)
        size = speed = "0"
        length = bitrate = None  # noqa: F841
        queue = immediate = num = country = bitratestr = ""

        for transfer in self.frame.np.transfers.downloads:
            if transfer.user == user and fullname == transfer.filename:
                size = HumanSize(transfer.size)
                try:
                    speed = str(int(transfer.speed))
                    speed += _(" KB/s")
                except Exception:
                    pass
                bitratestr = str(transfer.bitrate)
                length = str(transfer.length)

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
            self.MetaBox(title=_("Nicotine+:") + " " + _("Downloads Metadata"), message=_("<b>Metadata</b> for Downloads"), data=data, modal=True, Search=False)

    def OnOpenDirectory(self, widget):

        downloaddir = self.frame.np.config.sections["transfers"]["downloaddir"]
        incompletedir = self.frame.np.config.sections["transfers"]["incompletedir"]

        if incompletedir == "":
            incompletedir = downloaddir

        filemanager = self.frame.np.config.sections["ui"]["filemanager"]
        transfer = self.selected_transfers[0]

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

    def RebuildTransfers(self):

        if self.frame.np.transfers is None:
            return

        self.Clear()
        self.update()

    def select_transfers(self):
        self.selected_transfers = []
        self.selected_users = []
        self.widget.get_selection().selected_foreach(self.SelectedTransfersCallback)

    def OnBan(self, widgets):
        self.select_transfers()
        for user in self.selected_users:
            self.frame.BanUser(user)

    def OnSelectAbortTransfer(self, widget):
        self.select_transfers()
        self.OnAbortTransfer(widget, False)

    def OnSelectUserTransfer(self, widget):

        if len(self.selected_users) == 0:
            return

        selected_user = widget.parent.user

        sel = self.frame.DownloadList.get_selection()
        fmodel = self.frame.DownloadList.get_model()
        sel.unselect_all()

        for item in self.transfers:
            user_file, iter, transfer = item
            user, filepath = user_file
            if selected_user == user:
                ix = fmodel.get_path(iter)
                sel.select_path(ix,)

        self.select_transfers()

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

    def OnPlayFiles(self, widget, prefix=""):
        start_new_thread(self._OnPlayFiles, (widget, prefix))

    def _OnPlayFiles(self, widget, prefix=""):

        executable = self.frame.np.config.sections["players"]["default"]
        downloaddir = self.frame.np.config.sections["transfers"]["downloaddir"]

        if "$" not in executable:
            return

        for fn in self.selected_transfers:

            if fn.file is None:
                continue
            playfile = None

            if os.path.exists(fn.file.name):
                playfile = fn.file.name
            else:
                # If this file doesn't exist anymore, it may have finished downloading and have been renamed
                # try looking in the download directory and match the original filename.
                basename = string.split(fn.filename, '\\')[-1]
                path = os.sep.join([downloaddir, basename])
                if os.path.exists(path):
                    playfile = path

            if playfile:
                executeCommand(executable, playfile, background=False)

    def OnPopupMenuUsers(self, widget):

        self.selected_transfers = []
        self.selected_users = []
        self.widget.get_selection().selected_foreach(self.SelectedTransfersCallback)

        self.popup_menu_users.clear()

        if len(self.selected_users) > 0:

            items = []
            self.selected_users.sort(key=str.lower)

            for user in self.selected_users:

                popup = PopupMenu(self.frame)
                popup.setup(
                    ("#" + _("Send _message"), popup.OnSendMessage),
                    ("#" + _("Show IP a_ddress"), popup.OnShowIPaddress),
                    ("#" + _("Get user i_nfo"), popup.OnGetUserInfo),
                    ("#" + _("Brow_se files"), popup.OnBrowseUser),
                    ("#" + _("Gi_ve privileges"), popup.OnGivePrivileges),
                    ("", None),
                    ("$" + _("_Add user to list"), popup.OnAddToList),
                    ("$" + _("_Ban this user"), popup.OnBanUser),
                    ("$" + _("_Ignore this user"), popup.OnIgnoreUser),
                    ("#" + _("Select User's Transfers"), self.OnSelectUserTransfer)
                )
                popup.set_user(user)

                items.append((1, user, popup, self.OnPopupMenuUser, popup))

            self.popup_menu_users.setup(*items)

        return True

    def OnPopupMenuUser(self, widget, popup=None):

        if popup is None:
            return

        menu = popup
        user = menu.user
        items = menu.get_children()

        act = False
        if len(self.selected_users) >= 1:
            act = True

        items[0].set_sensitive(act)
        items[1].set_sensitive(act)
        items[2].set_sensitive(act)
        items[3].set_sensitive(act)

        items[6].set_active(user in [i[0] for i in self.frame.np.config.sections["server"]["userlist"]])
        items[7].set_active(user in self.frame.np.config.sections["server"]["banlist"])
        items[8].set_active(user in self.frame.np.config.sections["server"]["ignorelist"])

        for i in range(4, 9):
            items[i].set_sensitive(act)

        return True

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
            if event.button != 3:
                if event.button == 1 and event.type == Gdk.EventType._2BUTTON_PRESS:
                    self.DoubleClick(event)
                return False

        self.selected_transfers = []
        self.selected_users = []
        self.widget.get_selection().selected_foreach(self.SelectedTransfersCallback)

        users = len(self.selected_users) > 0
        multi_users = len(self.selected_users) > 1  # noqa: F841
        files = len(self.selected_transfers) > 0
        multi_files = len(self.selected_transfers) > 1

        self.SelectCurrentRow(event, kind)

        items = self.popup_menu.get_children()
        if users:
            items[7].set_sensitive(True)  # Users Menu
        else:
            items[7].set_sensitive(False)  # Users Menu

        if files:
            act = True
        else:
            act = False

        items[0].set_sensitive(act)  # Place
        items[4].set_sensitive(act)  # Send to player
        items[5].set_sensitive(act)  # View Meta
        items[6].set_sensitive(act)  # File manager
        items[8].set_sensitive(act)  # Search filename

        act = False
        if not multi_files and files:
            act = True

        items[2].set_sensitive(act)  # Copy URL
        items[3].set_sensitive(act)  # Copy Folder URL

        if not users or not files:
            # Disable options
            # Abort, Abort and Remove, retry, clear
            act = False
        else:
            act = True

        for i in range(10, 15):
            items[i].set_sensitive(act)

        self.popup_menu.popup(None, None, None, None, 3, event.time)

        if kind == "keyboard":
            widget.emit_stop_by_name("key_press_event")
        elif kind == "mouse":
            widget.emit_stop_by_name("button_press_event")

        return True

    def update(self, transfer=None, forced=False):

        TransferList.update(self, transfer, forced)
        if transfer is None and self.frame.np.transfers is not None:
            self.frame.np.transfers.SaveDownloads()

    def OnGetPlaceInQueue(self, widget):

        self.select_transfers()

        for i in self.selected_transfers:
            if i.status != "Queued":
                continue
            self.frame.np.ProcessRequestToPeer(i.user, slskmessages.PlaceInQueueRequest(None, i.filename))

    def OnFileSearch(self, widget):

        self.select_transfers()

        for transfer in self.selected_transfers:
            self.frame.SearchEntry.set_text(transfer.filename.rsplit("\\", 1)[1])
            self.frame.ChangeMainPage(None, "search")
            break

    def OnRetryTransfer(self, widget):

        self.select_transfers()

        for transfer in self.selected_transfers:

            if transfer.status in ["Finished", "Old"]:
                continue

            self.frame.np.transfers.AbortTransfer(transfer)
            transfer.req = None
            self.frame.np.transfers.getFile(transfer.user, transfer.filename, transfer.path, transfer)

        self.frame.np.transfers.SaveDownloads()

    def OnAbortRemoveTransfer(self, widget):
        self.select_transfers()
        self.OnClearTransfer(widget)
