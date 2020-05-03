# -*- coding: utf-8 -*-
#
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

import gi
from gi.repository import GObject as gobject
from gi.repository import Gtk as gtk

from pynicotine.gtkgui.utils import HumanSize
from pynicotine.gtkgui.utils import HumanSpeed
from pynicotine.gtkgui.utils import InitialiseColumns
from pynicotine.gtkgui.utils import float_sort_func
from pynicotine.gtkgui.utils import int_sort_func
from pynicotine.utils import cmp

gi.require_version('Gtk', '3.0')


class TransferList:

    MINIMUM_GUI_DELAY = 1  # in seconds
    MINIMUM_GUI_DELAY_SLEEP = int(ceil(MINIMUM_GUI_DELAY * 2000))  # in ms

    status_tab = [
        _("Getting status"),
        _("Waiting for download"),
        _("Waiting for upload"),
        _("Getting address"),
        _("Connecting"),
        _("Waiting for peer to connect"),
        _("Cannot connect"),
        _("User logged off"),
        _("Requesting file"),
        _("Initializing transfer"),
        _("Filtered"),
        _("Download directory error"),
        _("Local file error"),
        _("File not shared"),
        _("Aborted"),
        _("Paused"),
        _("Queued"),
        _("Transferring"),
        _("Finished")
    ]

    def __init__(self, frame, widget, type):
        self.frame = frame
        self.widget = widget
        self.type = type
        self.transfers = []
        self.list = None
        self.selected_transfers = []
        self.selected_users = []
        self.users = {}
        self.lastupdate = 0
        self.finalupdatetimerid = None
        widget.get_selection().set_mode(gtk.SelectionMode.MULTIPLE)

        columntypes = [
            gobject.TYPE_STRING,
            gobject.TYPE_STRING,
            gobject.TYPE_STRING,
            gobject.TYPE_STRING,
            gobject.TYPE_INT,
            gobject.TYPE_STRING,
            gobject.TYPE_STRING,
            gobject.TYPE_STRING,
            gobject.TYPE_STRING,
            gobject.TYPE_STRING,
            gobject.TYPE_STRING,
            gobject.TYPE_INT,
            gobject.TYPE_INT,
            gobject.TYPE_INT,
            gobject.TYPE_BOOLEAN,
            gobject.TYPE_STRING
        ]

        self.transfersmodel = gtk.TreeStore(*columntypes)
        widths = self.frame.np.config.sections["columns"]["{}_widths".format(type)]
        self.cols = cols = InitialiseColumns(
            widget,
            [_("User"), widths[0], "text", self.CellDataFunc],
            [_("Filename"), widths[1], "text", self.CellDataFunc],
            [_("Status"), widths[2], "text", self.CellDataFunc],
            [_("Queue Position"), widths[3], "text", self.CellDataFunc],
            [_("Percent"), widths[4], "progress"],
            [_("Size"), widths[5], "text", self.CellDataFunc],
            [_("Speed"), widths[6], "text", self.CellDataFunc],
            [_("Time elapsed"), widths[7], "text", self.CellDataFunc],
            [_("Time left"), widths[8], "text", self.CellDataFunc],
            [_("Path"), widths[9], "text", self.CellDataFunc]
        )

        self.col_user, self.col_filename, self.col_status, self.col_position, self.col_percent, self.col_human_size, self.col_human_speed, self.col_time_elapsed, self.col_time_left, self.col_path = cols

        self.col_user.set_sort_column_id(0)
        self.col_filename.set_sort_column_id(1)
        self.col_status.set_sort_column_id(2)

        # Only view progress renderer on transfers, not user tree parents
        self.transfersmodel.set_sort_func(2, self.status_sort_func, 2)
        self.col_position.set_sort_column_id(3)
        self.transfersmodel.set_sort_func(3, int_sort_func, 3)
        self.col_percent.set_sort_column_id(11)

        self.col_percent.set_attributes(self.col_percent.get_cells()[0], value=4, visible=14)

        self.col_human_size.set_sort_column_id(12)
        self.col_human_speed.set_sort_column_id(6)
        self.col_time_elapsed.set_sort_column_id(7)
        self.col_time_left.set_sort_column_id(8)
        self.col_path.set_sort_column_id(9)

        self.transfersmodel.set_sort_func(11, self.progress_sort_func, 4)
        self.transfersmodel.set_sort_func(6, float_sort_func, 6)

        widget.set_model(self.transfersmodel)

        self.UpdateColours()

    def UpdateColours(self):
        self.frame.SetTextBG(self.widget)
        self.frame.ChangeListFont(self.widget, self.frame.np.config.sections["ui"]["transfersfont"])

    def CellDataFunc(self, column, cellrenderer, model, iter, dummy="dummy"):

        colour = self.frame.np.config.sections["ui"]["search"]
        if colour == "":
            colour = None

        cellrenderer.set_property("foreground", colour)

    def get_status_index(self, val):

        try:
            return int(val)
        except Exception:
            if val in self.status_tab:
                return self.status_tab.index(val)
            else:
                return -len(self.status_tab)

    def status_sort_func(self, model, iter1, iter2, column):

        val1 = self.get_status_index(model.get_value(iter1, column))
        val2 = self.get_status_index(model.get_value(iter2, column))

        return cmp(val1, val2)

    def progress_sort_func(self, model, iter1, iter2, column):

        # We want 0% to be always below anything else,
        # so we have to look up whether we are ascending or descending
        ascending = True
        if model.get_sort_column_id()[1] == gtk.SortType.DESCENDING:
            ascending = False

        val1 = self.get_status_index(model.get_value(iter1, column))
        val2 = self.get_status_index(model.get_value(iter2, column))

        if val1 == 0 and val2 == 0:
            return 0

        if val1 == 0:
            return -1 + (ascending * 2)

        if val2 == 0:
            return 1 - (ascending * 2)

        return cmp(val1, val2)

    def InitInterface(self, list):
        self.list = list
        self.update()
        self.widget.set_sensitive(True)

    def ConnClose(self):
        self.widget.set_sensitive(False)
        self.list = None
        self.Clear()
        self.transfersmodel.clear()
        self.transfers = []
        self.users.clear()
        self.selected_transfers = []
        self.selected_users = []

    def SelectedTransfersCallback(self, model, path, iter):

        user = model.get_value(iter, 0)
        file = model.get_value(iter, 10)

        for i in self.list:
            if i.user == user and i.filename == file:
                self.selected_transfers.append(i)
                break

        if user not in self.selected_users:
            self.selected_users.append(user)

    def SelectCurrentRow(self, event, kind):

        # If nothing is selected (first click was right-click?) try to select the current row
        if self.selected_transfers == [] and self.selected_users == [] and kind == "mouse":

            d = self.widget.get_path_at_pos(int(event.x), int(event.y))

            if d:

                path, column, x, y = d
                iter = self.transfersmodel.get_iter(path)
                user = self.transfersmodel.get_value(iter, 0)
                file = self.transfersmodel.get_value(iter, 10)

                if path is not None:
                    sel = self.widget.get_selection()
                    sel.unselect_all()
                    sel.select_path(path)

                for i in self.list:
                    if i.user == user and i.filename == file:
                        self.selected_transfers.append(i)
                        break

                if user not in self.selected_users:
                    self.selected_users.append(user)

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

    def replace(self, oldtransfer, newtransfer):

        for i in self.transfers:
            if i[2] == oldtransfer:
                i[2] = newtransfer
                self.update_specific(newtransfer)
                return
        else:
            print(("WARNING: Could not find transfer %s." % oldtransfer))

    def update(self, transfer=None, forced=False):

        current_page = self.frame.MainNotebook.get_current_page()
        my_page = self.frame.MainNotebook.page_num(self.myvbox)

        if (current_page == my_page):
            self._update(transfer, forced)

        self.frame.UpdateBandwidth()

    def _update(self, transfer=None, forced=True):

        now = time()

        if forced:
            self.lastupdate = time()  # ...we're working...

        if transfer is not None:
            self.update_specific(transfer)
        elif self.list is not None:

            # This seems to me to be O(n^2), perhaps constructing a temp. dict
            # from self.list would be better?
            for i in self.transfers[:]:
                for j in self.list:
                    if [j.user, j.filename] == i[0]:
                        break
                else:
                    # Remove transfers from treeview that aren't in the transfer list
                    self.transfersmodel.remove(i[1])
                    self.transfers.remove(i)

            for i in self.list:
                self.update_specific(i)

        # The rest is just summarizing so it's not too important.
        # It's fairly CPU intensive though, so we only do it if we haven't updated it recently
        if not forced and (now - self.lastupdate) < self.MINIMUM_GUI_DELAY:
            if not self.finalupdatetimerid:
                self.finalupdatetimerid = True  # I'm not sure if gobject returns fast enough
                self.finalupdatetimerid = gobject.timeout_add(self.MINIMUM_GUI_DELAY_SLEEP, self.finalupdate, self.update)
            return

        self.lastupdate = time()  # ...we're working...

        # Remove empty parent rows
        for (username, user) in [x for x in self.users.items()]:

            if not self.transfersmodel.iter_has_child(user):
                self.transfersmodel.remove(user)
                del self.users[username]
            else:

                files = self.transfersmodel.iter_n_children(user)
                ispeed = 0.0
                percent = totalsize = position = 0
                elapsed = left = ""
                elap = 0
                salientstatus = ""
                extensions = {}

                for f in range(files):

                    iter = self.transfersmodel.iter_nth_child(user, f)
                    filename = self.transfersmodel.get_value(iter, 10)
                    parts = filename.rsplit('.', 1)

                    if len(parts) == 2:
                        ext = parts[1]
                        try:
                            extensions[ext.lower()] += 1
                        except KeyError:
                            extensions[ext.lower()] = 1

                    for transfer in self.list:
                        if [transfer.user, transfer.filename] == [username, filename] and transfer.timeelapsed is not None:
                            elap += transfer.timeelapsed
                            break

                    totalsize += self.transfersmodel.get_value(iter, 12)
                    position += self.transfersmodel.get_value(iter, 13)
                    status = self.transfersmodel.get_value(iter, 2)

                    if status == _("Transferring"):
                        str_speed = self.transfersmodel.get_value(iter, 15)
                        if str_speed != "":
                            ispeed += float(str_speed)

                        left = self.transfersmodel.get_value(iter, 8)

                    if salientstatus in ('', _("Finished")):  # we prefer anything over ''/finished
                        salientstatus = status

                    if status in (_("Transferring"), _("Banned"), _("Getting address"), _("Establishing connection")):
                        salientstatus = status

                try:
                    speed = "%.1f" % ispeed
                except TypeError:
                    speed = str(ispeed)

                if totalsize > 0:
                    percent = ((100 * position) / totalsize)

                if ispeed <= 0.0:
                    left = "∞"
                else:
                    left = self.frame.np.transfers.getTime((totalsize - position) / ispeed / 1024)

                elapsed = self.frame.np.transfers.getTime(elap)

                if len(extensions) == 0:
                    extensions = "Unknown"
                elif len(extensions) == 1:
                    extensions = _("All %(ext)s") % {'ext': list(extensions.keys())[0]}
                else:
                    extensionlst = [(extensions[key], key) for key in extensions]
                    extensionlst.sort(reverse=True)
                    extensions = ", ".join([str(count) + " " + ext for (count, ext) in extensionlst])

                self.transfersmodel.set(
                    user,
                    1, _("%(number)2s files ") % {'number': files} + " (" + extensions + ")",
                    2, salientstatus,
                    4, percent,
                    5, "%s / %s" % (HumanSize(position), HumanSize(totalsize)),
                    6, HumanSpeed(speed),
                    7, elapsed,
                    8, left,
                    12, ispeed,
                    14, True,
                    15, speed
                )

        self.lastupdate = time()  # ...and we're done

    def update_specific(self, transfer=None):

        if transfer not in self.list:
            return

        fn = transfer.filename
        user = transfer.user
        shortfn = self.frame.np.transfers.encode(fn.split("\\")[-1], user)
        currentbytes = transfer.currentbytes
        place = transfer.place

        if currentbytes is None:
            currentbytes = 0

        key = [user, fn]

        status = HumanSize(self.TranslateStatus(transfer.status))
        istatus = self.get_status_index(transfer.status)

        try:
            size = int(transfer.size)
        except TypeError:
            size = 0

        hsize = "%s / %s" % (HumanSize(currentbytes), HumanSize(size))

        if transfer.modifier:
            hsize += " (%s)" % transfer.modifier

        try:
            speed = "%.1f" % transfer.speed
        except TypeError:
            speed = str(transfer.speed)

        elap = transfer.timeelapsed
        left = str(transfer.timeleft)

        if speed == "None":
            speed = ""
        else:
            # transfer.speed is in KB
            speed = float(speed) * 1024

        if elap is None:
            elap = 0

        elap = self.frame.np.transfers.getTime(elap)

        if left == "None":
            left = ""

        try:
            icurrentbytes = int(currentbytes)
            if icurrentbytes == int(transfer.size):
                percent = 100
            else:
                percent = ((100 * icurrentbytes) / int(size))
        except Exception as e:  # noqa: F841
            icurrentbytes = 0
            percent = 0

        # Modify old transfer
        for i in self.transfers:

            if i[0] != key:
                continue

            if i[2] != transfer:
                continue

            self.transfersmodel.set(
                i[1],
                1, shortfn,
                2, status,
                3, str(place),
                4, percent,
                5, str(hsize),
                6, HumanSpeed(speed),
                7, elap,
                8, left,
                9, self.frame.np.decode(transfer.path),
                11, istatus,
                12, size,
                13, currentbytes,
                15, str(speed)
            )

            break
        else:
            newparent = False
            if self.TreeUsers:
                if user not in self.users:
                    # Create Parent if it doesn't exist
                    # ProgressRender not visible (last column sets 4th column)
                    self.users[user] = self.transfersmodel.append(
                        None,
                        [user, "", "", "", 0, "", "", "", "", "", "", 0, 0, 0, False, ""]
                    )
                    newparent = True

                parent = self.users[user]
            else:
                parent = None

            # Add a new transfer
            path = self.frame.np.decode(transfer.path)

            iter = self.transfersmodel.append(
                parent,
                [user, shortfn, status, str(place), percent, str(hsize), HumanSpeed(speed), elap, left, path, fn, istatus, size, icurrentbytes, True, str(speed)]
            )

            # Expand path
            path = self.transfersmodel.get_path(iter)
            self.transfers.append([key, iter, transfer])

            if newparent:
                self.expandcollapse(self.transfersmodel.get_path(parent))

    def Clear(self):
        self.users.clear()
        self.transfers = []
        self.selected_transfers = []
        self.selected_users = []
        self.transfersmodel.clear()

    def OnCopyURL(self, widget):
        i = self.selected_transfers[0]
        self.frame.SetClipboardURL(i.user, i.filename)

    def OnCopyDirURL(self, widget):

        i = self.selected_transfers[0]
        path = "\\".join(i.filename.split("\\")[:-1]) + "\\"

        if path[:-1] != "/":
            path += "/"

        self.frame.SetClipboardURL(i.user, path)

    def OnAbortTransfer(self, widget, remove=False, clear=False):

        transfers = self.selected_transfers

        for i in transfers:

            self.frame.np.transfers.AbortTransfer(i, remove)
            i.status = "Aborted"
            i.req = None

            if clear:
                for t in self.list[:]:
                    if i.user == t.user and i.filename == t.filename:
                        self.list.remove(t)

        self.update()

    def OnClearTransfer(self, widget):
        self.OnAbortTransfer(widget, False, True)

    def ClearTransfers(self, status):

        for i in self.list[:]:
            if i.status in status:
                if i.transfertimer is not None:
                    i.transfertimer.cancel()
                self.list.remove(i)

        self.update()

    def OnClearFinished(self, widget):
        self.ClearTransfers(["Finished"])

    def OnClearAborted(self, widget):
        statuslist = ["Aborted", "Cancelled"]
        self.ClearTransfers(statuslist)

    def OnClearFiltered(self, widget):
        statuslist = ["Filtered"]
        self.ClearTransfers(statuslist)

    def OnClearFailed(self, widget):
        statuslist = ["Cannot connect", "Connection closed by peer", "Local file error", "Getting address", "Waiting for peer to connect", "Initializing transfer"]
        self.ClearTransfers(statuslist)

    def OnClearPaused(self, widget):
        statuslist = ["Paused"]
        self.ClearTransfers(statuslist)

    def OnClearFinishedAborted(self, widget):
        statuslist = ["Aborted", "Cancelled", "Finished", "Filtered"]
        self.ClearTransfers(statuslist)

    def OnClearFinishedErred(self, widget):
        statuslist = ["Aborted", "Cancelled", "Finished", "Filtered", "Cannot connect", "Connection closed by peer", "Local file error"]
        self.ClearTransfers(statuslist)

    def OnClearQueued(self, widget):
        self.ClearTransfers(["Queued"])
