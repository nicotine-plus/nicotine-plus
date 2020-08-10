# COPYRIGHT (C) 2020 Nicotine+ Team
# COPYRIGHT (C) 2018 Mutnick <mutnick@techie.com>
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2008-2011 Quinox <quinox@users.sf.net>
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
from gettext import gettext as _
from math import ceil
from time import time

from gi.repository import GLib
from gi.repository import GObject as gobject
from gi.repository import Gtk as gtk

from pynicotine.gtkgui.utils import HideColumns
from pynicotine.gtkgui.utils import HumanSize
from pynicotine.gtkgui.utils import HumanSpeed
from pynicotine.gtkgui.utils import InitialiseColumns
from pynicotine.gtkgui.utils import PopupMenu
from pynicotine.gtkgui.utils import SelectUserRowIter


class TransferList:

    MINIMUM_GUI_DELAY = 1  # in seconds
    MINIMUM_GUI_DELAY_SLEEP = int(ceil(MINIMUM_GUI_DELAY * 2000))  # in ms

    def __init__(self, frame, widget, type):
        self.frame = frame
        self.widget = widget
        self.type = type
        self.list = None
        self.users = {}
        self.paths = {}
        self.lastupdate = 0
        self.finalupdatetimerid = None

        widget.get_selection().set_mode(gtk.SelectionMode.MULTIPLE)
        widget.set_enable_tree_lines(True)
        widget.set_rubber_banding(True)

        self.transfersmodel = gtk.TreeStore(
            str,                   # (0)  user
            str,                   # (1)  path
            str,                   # (2)  file name
            str,                   # (3)  status
            str,                   # (4)  hqueue position
            gobject.TYPE_UINT64,   # (5)  percent
            str,                   # (6)  hsize
            str,                   # (7)  hspeed
            str,                   # (8)  htime elapsed
            str,                   # (9)  time left
            str,                   # (10) path
            str,                   # (11) status (non-translated)
            gobject.TYPE_UINT64,   # (12) size
            gobject.TYPE_UINT64,   # (13) current bytes
            gobject.TYPE_UINT64,   # (14) speed
            gobject.TYPE_UINT64,   # (15) time elapsed
            gobject.TYPE_UINT64,   # (16) file count
            gobject.TYPE_UINT64,   # (17) queue position
        )

        widths = self.frame.np.config.sections["columns"]["{}_widths".format(type)]
        self.cols = cols = InitialiseColumns(
            widget,
            [_("User"), widths[0], "text", self.CellDataFunc],
            [_("Path"), widths[1], "text", self.CellDataFunc],
            [_("Filename"), widths[2], "text", self.CellDataFunc],
            [_("Status"), widths[3], "text", self.CellDataFunc],
            [_("Queue Position"), widths[4], "number", self.CellDataFunc],
            [_("Percent"), widths[5], "progress"],
            [_("Size"), widths[6], "number", self.CellDataFunc],
            [_("Speed"), widths[7], "number", self.CellDataFunc],
            [_("Time elapsed"), widths[8], "number", self.CellDataFunc],
            [_("Time left"), widths[9], "number", self.CellDataFunc]
        )

        self.col_user, self.col_path, self.col_filename, self.col_status, self.col_position, self.col_percent, self.col_human_size, self.col_human_speed, self.col_time_elapsed, self.col_time_left = cols

        HideColumns(cols, self.frame.np.config.sections["columns"][self.type + "_columns"])

        self.col_user.set_sort_column_id(0)
        self.col_path.set_sort_column_id(1)
        self.col_filename.set_sort_column_id(2)
        self.col_status.set_sort_column_id(11)
        self.col_position.set_sort_column_id(17)
        self.col_percent.set_sort_column_id(5)
        self.col_human_size.set_sort_column_id(12)
        self.col_human_speed.set_sort_column_id(14)
        self.col_time_elapsed.set_sort_column_id(8)
        self.col_time_left.set_sort_column_id(9)

        widget.set_model(self.transfersmodel)

        widget.connect("button_press_event", self.OnPopupMenu, "mouse")
        widget.connect("key-press-event", self.on_key_press_event)

        self.UpdateColours()

    def saveColumns(self):
        columns = []
        widths = []

        for column in self.widget.get_columns():
            columns.append(column.get_visible())
            widths.append(column.get_width())

        self.frame.np.config.sections["columns"][self.type + "_columns"] = columns
        self.frame.np.config.sections["columns"][self.type + "_widths"] = widths

    def UpdateColours(self):
        self.frame.SetTextBG(self.widget)
        self.frame.ChangeListFont(self.widget, self.frame.np.config.sections["ui"]["transfersfont"])

    def CellDataFunc(self, column, cellrenderer, model, iter, dummy="dummy"):

        colour = self.frame.np.config.sections["ui"]["search"]
        if colour == "":
            colour = None

        cellrenderer.set_property("foreground", colour)

    def InitInterface(self, list):
        self.list = list
        self.update()
        self.widget.set_sensitive(True)

    def ConnClose(self):
        self.widget.set_sensitive(False)
        self.list = None
        self.Clear()

    def select_transfers(self):
        self.selected_transfers = set()
        self.selected_users = set()

        self.widget.get_selection().selected_foreach(self.SelectedTransfersCallback)

    def OnBan(self, widget):
        self.select_transfers()

        for user in self.selected_users:
            self.frame.BanUser(user)

    def OnFileSearch(self, widget):

        for transfer in self.selected_transfers:
            self.frame.SearchEntry.set_text(transfer.filename.rsplit("\\", 1)[1])
            self.frame.ChangeMainPage(None, "search")
            break

    def RebuildTransfers(self):
        if self.frame.np.transfers is None:
            return

        self.Clear()
        self.update()

    def SelectedTransfersCallback(self, model, path, iter):

        self.SelectTransfer(model, iter, selectuser=True)

        # If we're in grouping mode, select any transfers under the selected
        # user or folder
        self.SelectChildTransfers(model, model.iter_children(iter))

    def SelectChildTransfers(self, model, iter):

        while iter is not None:
            self.SelectTransfer(model, iter)
            self.SelectChildTransfers(model, model.iter_children(iter))
            iter = model.iter_next(iter)

    def SelectTransfer(self, model, iter, selectuser=False):
        user = model.get_value(iter, 0)
        file = model.get_value(iter, 10)

        for i in self.list:
            if i.user == user and i.filename == file:
                self.selected_transfers.add(i)
                break

        if selectuser:
            self.selected_users.add(user)

    def TranslateStatus(self, status):

        if status == "Waiting for download":
            newstatus = _("Waiting for download")
        elif status == "Waiting for upload":
            newstatus = _("Waiting for upload")
        elif status == "Requesting file":
            newstatus = _("Requesting file")
        elif status == "Initializing transfer":
            newstatus = _("Initializing transfer")
        elif status == "Cannot connect":
            newstatus = _("Cannot connect")
        elif status == "Waiting for peer to connect":
            newstatus = _("Waiting for peer to connect")
        elif status == "Connecting":
            newstatus = _("Connecting")
        elif status == "Getting address":
            newstatus = _("Getting address")
        elif status == "Getting status":
            newstatus = _("Getting status")
        elif status == "Queued":
            newstatus = _("Queued")
        elif status == "User logged off":
            newstatus = _("User logged off")
        elif status == "Aborted":
            newstatus = _("Aborted")
        elif status == "Finished":
            newstatus = _("Finished")
        elif status == "Paused":
            newstatus = _("Paused")
        elif status == "Transferring":
            newstatus = _("Transferring")
        elif status == "Filtered":
            newstatus = _("Filtered")
        elif status == "Connection closed by peer":
            newstatus = _("Connection closed by peer")
        elif status == "File not shared":
            newstatus = _("File not shared")
        elif status == "Establishing connection":
            newstatus = _("Establishing connection")
        elif status == "Download directory error":
            newstatus = _("Download directory error")
        elif status == "Local file error":
            newstatus = _("Local file error")
        elif status == "Remote file error":
            newstatus = _("Remote file error")
        else:
            newstatus = status

        return newstatus

    def finalupdate(self, func):

        now = time()

        # I had a logical explanation about why it has to be 3*delay, but I
        # forgot. Something to do with the timeout being 2*delay
        if (now - self.lastupdate) < (3 * self.MINIMUM_GUI_DELAY):
            # The list has been updated recently,
            # trying again later.
            return True

        self.update(forced=True)  # delayed updates can never trigger a new timer
        self.finalupdatetimerid = None

        return False  # Stopping timeout

    def update(self, transfer=None, forced=False, nochildupdate=False):

        current_page = self.frame.MainNotebook.get_current_page()
        my_page = self.frame.MainNotebook.page_num(self.myvbox)

        if (current_page == my_page):
            self._update(transfer, forced, nochildupdate)

    def _update(self, transfer=None, forced=True, nochildupdate=False):

        now = time()

        if forced:
            self.lastupdate = time()  # ...we're working...

        if transfer is not None:
            self.update_specific(transfer)
        elif not nochildupdate and self.list is not None:

            for i in self.list:
                self.update_specific(i)

        self.frame.UpdateBandwidth()

        # The rest is just summarizing so it's not too important.
        # It's fairly CPU intensive though, so we only do it if we haven't updated it recently
        if not forced and (now - self.lastupdate) < self.MINIMUM_GUI_DELAY:
            if not self.finalupdatetimerid:
                self.finalupdatetimerid = True  # I'm not sure if gobject returns fast enough
                self.finalupdatetimerid = GLib.timeout_add(self.MINIMUM_GUI_DELAY_SLEEP, self.finalupdate, self.update)
            return

        self.lastupdate = time()  # ...we're working...

        # Save downloads to file
        if self.frame.np.transfers is not None:
            self.frame.np.transfers.SaveDownloads()

        # Remove empty parent rows
        for (path, pathiter) in [x for x in self.paths.items()]:
            if not self.transfersmodel.iter_has_child(pathiter):
                self.transfersmodel.remove(pathiter)
                del self.paths[path]
            else:
                self.update_parent_row(pathiter)

        for (username, useriter) in [x for x in self.users.items()]:
            if useriter != 0:
                if not self.transfersmodel.iter_has_child(useriter):
                    self.transfersmodel.remove(useriter)
                    del self.users[username]
                    self.frame.UpdateBandwidth()
                else:
                    self.update_parent_row(useriter)
            else:
                # No grouping

                for transfer in self.list:
                    if transfer.user == username:
                        break
                else:
                    del self.users[username]
                    self.frame.UpdateBandwidth()

        self.lastupdate = time()  # ...and we're done

    def update_parent_row(self, initer):
        files = self.transfersmodel.iter_n_children(initer)
        speed = 0.0
        percent = totalsize = position = 0
        hspeed = helapsed = left = ""
        elapsed = 0
        filecount = 0
        salientstatus = ""
        extensions = {}

        for f in range(files):

            iter = self.transfersmodel.iter_nth_child(initer, f)
            status = self.transfersmodel.get_value(iter, 11)

            if salientstatus in ('', "Finished", "Filtered"):  # we prefer anything over ''/finished
                salientstatus = status

            filename = self.transfersmodel.get_value(iter, 10)
            parts = filename.rsplit('.', 1)

            if len(parts) == 2:
                ext = parts[1]
                try:
                    extensions[ext.lower()] += 1
                except KeyError:
                    extensions[ext.lower()] = 1

            if status == "Filtered":
                # We don't want to count filtered files when calculating the progress
                continue

            elapsed += self.transfersmodel.get_value(iter, 15)
            totalsize += self.transfersmodel.get_value(iter, 12)
            position += self.transfersmodel.get_value(iter, 13)
            filecount += self.transfersmodel.get_value(iter, 16)

            if status == "Transferring":
                speed += float(self.transfersmodel.get_value(iter, 14))
                left = self.transfersmodel.get_value(iter, 9)

            if status in ("Transferring", "Banned", "Getting address", "Establishing connection"):
                salientstatus = status

        if totalsize > 0:
            percent = ((100 * position) / totalsize)

        if speed > 0:
            hspeed = HumanSpeed(speed)
            left = self.frame.np.transfers.getTime((totalsize - position) / speed / 1024)

        if elapsed > 0:
            helapsed = self.frame.np.transfers.getTime(elapsed)

        if len(extensions) == 0:
            extensions = ""
        elif len(extensions) == 1:
            extensions = " (" + _("All %(ext)s") % {'ext': list(extensions.keys())[0]} + ")"
        else:
            extensionlst = [(extensions[key], key) for key in extensions]
            extensionlst.sort(reverse=True)
            extensions = " (" + ", ".join([str(count) + " " + ext for (count, ext) in extensionlst]) + ")"

        self.transfersmodel.set(
            initer,
            2, _("%(number)2s files ") % {'number': filecount} + extensions,
            3, self.TranslateStatus(salientstatus),
            5, percent,
            6, "%s / %s" % (HumanSize(position), HumanSize(totalsize)),
            7, hspeed,
            8, helapsed,
            9, left,
            11, salientstatus,
            12, totalsize,
            13, position,
            14, speed,
            15, elapsed,
            16, filecount,
        )

    def update_specific(self, transfer=None):

        fn = transfer.filename
        user = transfer.user
        shortfn = fn.split("\\")[-1]
        currentbytes = transfer.currentbytes
        place = transfer.place

        hspeed = helapsed = ""

        if currentbytes is None:
            currentbytes = 0

        status = transfer.status
        hstatus = self.TranslateStatus(status)

        try:
            size = int(transfer.size)
        except TypeError:
            size = 0

        hsize = "%s / %s" % (HumanSize(currentbytes), HumanSize(size))

        if transfer.modifier:
            hsize += " (%s)" % transfer.modifier

        speed = transfer.speed or 0
        elapsed = transfer.timeelapsed or 0
        left = transfer.timeleft

        if speed > 0:
            # transfer.speed is in KB
            speed = float(speed) * 1024
            hspeed = HumanSpeed(speed)

        if elapsed > 0:
            helapsed = self.frame.np.transfers.getTime(elapsed)

        try:
            icurrentbytes = int(currentbytes)
            if icurrentbytes == int(transfer.size):
                percent = 100
            else:
                percent = ((100 * icurrentbytes) / int(size))
        except Exception:
            icurrentbytes = 0
            percent = 0

        filecount = 1

        # Modify old transfer
        if transfer.iter is not None:
            if self.TreeUsers == 1:
                # Group by folder, path not visible
                path = None
            else:
                path = '/'.join(reversed(transfer.path.split('/')))

            self.transfersmodel.set(
                transfer.iter,
                1, path,
                2, shortfn,
                3, hstatus,
                4, str(place),
                5, percent,
                6, str(hsize),
                7, hspeed,
                8, helapsed,
                9, left,
                11, status,
                12, size,
                13, currentbytes,
                14, speed,
                15, elapsed,
                17, place
            )
        else:
            if self.TreeUsers > 0:
                # Group by folder or user

                if user not in self.users:
                    # Create Parent if it doesn't exist
                    # ProgressRender not visible (last column sets 4th column)
                    self.users[user] = self.transfersmodel.append(
                        None,
                        [user, "", "", "", "", 0, "", "", "", "", "", "", 0, 0, 0, 0, filecount, 0]
                    )

                parent = self.users[user]

                if self.TreeUsers == 1:
                    # Group by folder

                    """ Paths can be empty if files are downloaded individually, make sure we
                    don't add files to the wrong user in the TreeView """
                    path = transfer.path
                    user_path = user + path
                    reverse_path = '/'.join(reversed(path.split('/')))

                    if user_path not in self.paths:
                        self.paths[user_path] = self.transfersmodel.append(
                            self.users[user],
                            [user, reverse_path, "", "", "", 0, "", "", "", "", "", "", 0, 0, 0, 0, filecount, 0]
                        )

                    parent = self.paths[user_path]
            else:
                # No grouping

                if user not in self.users:
                    # Insert dummy value. We use this list to get the total number of users
                    self.users[user] = 0

                parent = None

            # Add a new transfer
            if self.TreeUsers == 1:
                # Group by folder, path not visible
                path = None
            else:
                path = '/'.join(reversed(transfer.path.split('/')))

            iter = self.transfersmodel.append(
                parent,
                (user, path, shortfn, status, str(place), percent, str(hsize), hspeed, helapsed, left, fn, transfer.status, size, icurrentbytes, speed, elapsed, filecount, place)
            )
            transfer.iter = iter

            # Expand path
            if parent is not None:
                path = self.transfersmodel.get_path(iter)
                self.expand(path)

    def remove_specific(self, transfer, cleartreeviewonly=False):
        if not cleartreeviewonly:
            self.list.remove(transfer)

        if transfer.iter is not None:
            self.transfersmodel.remove(transfer.iter)

        self.update(nochildupdate=True)

    def Clear(self):
        self.users.clear()
        self.paths.clear()
        self.selected_transfers = set()
        self.selected_users = set()
        self.transfersmodel.clear()

        if self.list is not None:
            for i in self.list:
                i.iter = None

    def OnPopupMenuUsers(self, widget):

        self.popup_menu_users.clear()

        if len(self.selected_users) > 0:

            items = []

            for user in self.selected_users:

                popup = PopupMenu(self.frame, False)
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
                    ("#" + _("Select User's Transfers"), self.OnSelectUserTransfers)
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

    def OnSelectUserTransfers(self, widget):

        if len(self.selected_users) == 0:
            return

        selected_user = widget.get_parent().user

        sel = self.widget.get_selection()
        fmodel = self.widget.get_model()
        sel.unselect_all()

        iter = fmodel.get_iter_first()

        SelectUserRowIter(fmodel, sel, 0, selected_user, iter)

        self.select_transfers()

    def OnCopyURL(self, widget):
        i = next(iter(self.selected_transfers))
        self.frame.SetClipboardURL(i.user, i.filename)

    def OnCopyDirURL(self, widget):

        i = next(iter(self.selected_transfers))
        path = "\\".join(i.filename.split("\\")[:-1])

        if path[:-1] != "/":
            path += "/"

        self.frame.SetClipboardURL(i.user, path)

    def OnAbortTransfer(self, widget, remove=False, clear=False):

        for i in self.selected_transfers:

            if i.status != "Finished":
                self.frame.np.transfers.AbortTransfer(i, remove)

                if not clear:
                    i.status = "Aborted"
                    self.update(i)

            if clear:
                self.remove_specific(i)

    def OnClearTransfer(self, widget):
        self.OnAbortTransfer(widget, False, True)

    def ClearTransfers(self, status):

        for i in self.list[:]:
            if i.status in status:
                if i.transfertimer is not None:
                    i.transfertimer.cancel()
                self.remove_specific(i)

    def OnClearFinished(self, widget):
        self.ClearTransfers(["Finished"])

    def OnClearAborted(self, widget):
        statuslist = ["Aborted", "Cancelled"]
        self.ClearTransfers(statuslist)

    def OnClearFiltered(self, widget):
        statuslist = ["Filtered"]
        self.ClearTransfers(statuslist)

    def OnClearFailed(self, widget):
        statuslist = ["Cannot connect", "Connection closed by peer", "Local file error", "Remote file error", "Getting address", "Waiting for peer to connect", "Initializing transfer"]
        self.ClearTransfers(statuslist)

    def OnClearPaused(self, widget):
        statuslist = ["Paused"]
        self.ClearTransfers(statuslist)

    def OnClearFinishedAborted(self, widget):
        statuslist = ["Aborted", "Cancelled", "Finished", "Filtered"]
        self.ClearTransfers(statuslist)

    def OnClearFinishedErred(self, widget):
        statuslist = ["Aborted", "Cancelled", "Finished", "Filtered", "Cannot connect", "Connection closed by peer", "Local file error", "Remote file error"]
        self.ClearTransfers(statuslist)

    def OnClearQueued(self, widget):
        self.ClearTransfers(["Queued"])
