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
from gi.repository import GLib
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

    def __init__(self, frame, widget, type):
        self.frame = frame
        self.widget = widget
        self.type = type
        self.list = None
        self.selected_transfers = []
        self.selected_users = []
        self.users = {}
        self.paths = {}
        self.lastupdate = 0
        self.finalupdatetimerid = None
        widget.get_selection().set_mode(gtk.SelectionMode.MULTIPLE)
        widget.set_enable_tree_lines(True)
        widget.set_rubber_banding(True)

        columntypes = [
            gobject.TYPE_STRING,   # user
            gobject.TYPE_STRING,   # path
            gobject.TYPE_STRING,   # file name
            gobject.TYPE_STRING,   # status
            gobject.TYPE_STRING,   # queue position
            gobject.TYPE_UINT64,   # percent
            gobject.TYPE_STRING,   # hsize
            gobject.TYPE_STRING,   # hspeed
            gobject.TYPE_STRING,   # htime elapsed
            gobject.TYPE_STRING,   # time left
            gobject.TYPE_STRING,   # path
            gobject.TYPE_STRING,   # status (non-translated)
            gobject.TYPE_UINT64,   # size
            gobject.TYPE_UINT64,   # current bytes
            gobject.TYPE_BOOLEAN,  # percent visible (?)
            gobject.TYPE_STRING,   # speed
            gobject.TYPE_UINT64    # time elapsed
        ]

        self.transfersmodel = gtk.TreeStore(*columntypes)
        widths = self.frame.np.config.sections["columns"]["{}_widths".format(type)]

        self.cols = cols = InitialiseColumns(
            widget,
            [_("User"), widths[0], "text", self.CellDataFunc],
            [_("Path"), widths[1], "text", self.CellDataFunc],
            [_("Filename"), widths[2], "text", self.CellDataFunc],
            [_("Status"), widths[3], "text", self.CellDataFunc],
            [_("Queue Position"), widths[4], "text", self.CellDataFunc],
            [_("Percent"), widths[5], "progress"],
            [_("Size"), widths[6], "text", self.CellDataFunc],
            [_("Speed"), widths[7], "text", self.CellDataFunc],
            [_("Time elapsed"), widths[8], "text", self.CellDataFunc],
            [_("Time left"), widths[9], "text", self.CellDataFunc]
        )

        self.col_user, self.col_path, self.col_filename, self.col_status, self.col_position, self.col_percent, self.col_human_size, self.col_human_speed, self.col_time_elapsed, self.col_time_left = cols

        self.col_user.set_sort_column_id(0)
        self.col_path.set_sort_column_id(1)
        self.col_filename.set_sort_column_id(2)
        self.col_status.set_sort_column_id(3)

        # Only view progress renderer on transfers, not user tree parents
        self.transfersmodel.set_sort_func(3, self.status_sort_func, 3)
        self.col_position.set_sort_column_id(4)
        self.transfersmodel.set_sort_func(4, int_sort_func, 4)
        self.col_percent.set_sort_column_id(11)

        self.col_percent.set_attributes(self.col_percent.get_cells()[0], value=5, visible=14)

        self.col_human_size.set_sort_column_id(12)
        self.col_human_speed.set_sort_column_id(7)
        self.col_time_elapsed.set_sort_column_id(8)
        self.col_time_left.set_sort_column_id(9)

        self.transfersmodel.set_sort_func(11, self.progress_sort_func, 5)
        self.transfersmodel.set_sort_func(7, float_sort_func, 7)

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
        self.users.clear()
        self.paths.clear()
        self.selected_transfers = []
        self.selected_users = []

    def select_transfers(self):
        self.selected_transfers = []
        self.selected_users = []
        self.widget.get_selection().selected_foreach(self.SelectedTransfersCallback)

    def OnBan(self, widget):
        self.select_transfers()

        for user in self.selected_users:
            self.frame.BanUser(user)

    def OnFileSearch(self, widget):
        self.select_transfers()

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

        user = model.get_value(iter, 0)
        file = model.get_value(iter, 10)

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

            for i in self.list:
                self.update_specific(i)

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

                files = self.transfersmodel.iter_n_children(pathiter)
                ispeed = 0.0
                percent = totalsize = position = 0
                helapsed = left = ""
                elapsed = 0
                salientstatus = ""
                extensions = {}

                for f in range(files):

                    iter = self.transfersmodel.iter_nth_child(pathiter, f)
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

                    if status == _("Filtered"):
                        # We don't want to count filtered files when calculating the progress
                        continue

                    elapsed += self.transfersmodel.get_value(iter, 16)
                    totalsize += self.transfersmodel.get_value(iter, 12)
                    position += self.transfersmodel.get_value(iter, 13)

                    if status == "Transferring":
                        str_speed = self.transfersmodel.get_value(iter, 15)
                        if str_speed != "":
                            ispeed += float(str_speed)

                        left = self.transfersmodel.get_value(iter, 9)

                    if status in ("Transferring", "Banned", "Getting address", "Establishing connection"):
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

                helapsed = self.frame.np.transfers.getTime(elapsed)

                if len(extensions) == 0:
                    extensions = "Unknown"
                elif len(extensions) == 1:
                    extensions = _("All %(ext)s") % {'ext': list(extensions.keys())[0]}
                else:
                    extensionlst = [(extensions[key], key) for key in extensions]
                    extensionlst.sort(reverse=True)
                    extensions = ", ".join([str(count) + " " + ext for (count, ext) in extensionlst])

                self.transfersmodel.set(
                    pathiter,
                    2, _("%(number)2s files ") % {'number': files} + " (" + extensions + ")",
                    3, self.TranslateStatus(salientstatus),
                    5, percent,
                    6, "%s / %s" % (HumanSize(position), HumanSize(totalsize)),
                    7, HumanSpeed(speed),
                    8, helapsed,
                    9, left,
                    12, ispeed,
                    14, True,
                    15, speed,
                    16, elapsed
                )

        for (username, useriter) in [x for x in self.users.items()]:
            if not self.transfersmodel.iter_has_child(useriter):
                self.transfersmodel.remove(useriter)
                del self.users[username]

        self.lastupdate = time()  # ...and we're done

    def update_specific(self, transfer=None):

        fn = transfer.filename
        user = transfer.user
        shortfn = fn.split("\\")[-1]
        currentbytes = transfer.currentbytes
        place = transfer.place

        if currentbytes is None:
            currentbytes = 0

        status = self.TranslateStatus(transfer.status)

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

        elapsed = transfer.timeelapsed
        left = str(transfer.timeleft)

        if speed == "None":
            speed = ""
        else:
            # transfer.speed is in KB
            speed = float(speed) * 1024

        if elapsed is None:
            elapsed = 0

        helapsed = self.frame.np.transfers.getTime(elapsed)

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
        if transfer.iter is not None:
            if self.TreeUsers:
                path = None
            else:
                path = transfer.path

            self.transfersmodel.set(
                transfer.iter,
                1, path,
                2, shortfn,
                3, status,
                4, str(place),
                5, percent,
                6, str(hsize),
                7, HumanSpeed(speed),
                8, helapsed,
                9, left,
                11, transfer.status,
                12, size,
                13, currentbytes,
                15, str(speed),
                16, elapsed
            )
        else:
            if self.TreeUsers:
                if user not in self.users:
                    # Create Parent if it doesn't exist
                    # ProgressRender not visible (last column sets 4th column)
                    self.users[user] = self.transfersmodel.append(
                        None,
                        [user, "", "", "", "", 0, "", "", "", "", "", "", 0, 0, False, "", 0]
                    )

                """ Paths can be empty if files are downloaded individually, make sure we
                don't add files to the wrong user in the TreeView """
                path = user + transfer.path

                if path not in self.paths:
                    self.paths[path] = self.transfersmodel.append(
                        self.users[user],
                        [user, transfer.path, "", "", "", 0, "", "", "", "", "", "", 0, 0, False, "", 0]
                    )

                parent = self.paths[path]
            else:
                parent = None

            # Add a new transfer
            if self.TreeUsers:
                path = None
            else:
                path = transfer.path

            iter = self.transfersmodel.append(
                parent,
                (user, path, shortfn, status, str(place), percent, str(hsize), HumanSpeed(speed), helapsed, left, fn, transfer.status, size, icurrentbytes, True, str(speed), elapsed)
            )

            # Expand path
            transfer.iter = iter

            if parent is not None:
                path = self.transfersmodel.get_path(iter)
                self.expand(path)

    def Clear(self):
        self.users.clear()
        self.paths.clear()
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
                self.list.remove(i)
                self.transfersmodel.remove(i.iter)

        self.update()

    def OnClearTransfer(self, widget):
        self.OnAbortTransfer(widget, False, True)

    def ClearTransfers(self, status):

        for i in self.list[:]:
            if i.status in status:
                if i.transfertimer is not None:
                    i.transfertimer.cancel()
                self.list.remove(i)
                self.transfersmodel.remove(i.iter)

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
