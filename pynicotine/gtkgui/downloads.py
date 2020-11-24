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
from gi.repository import Gtk

from _thread import start_new_thread
from pynicotine.gtkgui.dialogs import option_dialog
from pynicotine.gtkgui.fileproperties import FileProperties
from pynicotine.gtkgui.transferlist import TransferList
from pynicotine.gtkgui.utils import collapse_treeview
from pynicotine.gtkgui.utils import fill_file_grouping_combobox
from pynicotine.gtkgui.utils import human_size
from pynicotine.gtkgui.utils import human_speed
from pynicotine.gtkgui.utils import open_file_path
from pynicotine.gtkgui.utils import PopupMenu
from pynicotine.gtkgui.utils import set_treeview_selected_row


class Downloads(TransferList):

    def __init__(self, frame, tab_label):

        TransferList.__init__(self, frame, frame.DownloadList, type='download')
        self.tab_label = tab_label

        self.popup_menu_users = PopupMenu(self.frame, False)
        self.popup_menu_clear = popup2 = PopupMenu(self.frame, False)
        popup2.setup(
            ("#" + _("Clear finished/aborted"), self.on_clear_finished_aborted),
            ("#" + _("Clear finished"), self.on_clear_finished),
            ("#" + _("Clear aborted"), self.on_clear_aborted),
            ("#" + _("Clear paused"), self.on_clear_paused),
            ("#" + _("Clear filtered"), self.on_clear_filtered),
            ("#" + _("Clear queued"), self.on_clear_queued)
        )

        self.popup_menu = popup = PopupMenu(frame)
        popup.setup(
            ("#" + _("Copy _URL"), self.on_copy_url),
            ("#" + _("Copy folder URL"), self.on_copy_dir_url),
            ("#" + _("Send to _player"), self.on_play_files),
            ("#" + _("File Properties"), self.on_file_properties),
            ("#" + _("Open folder"), self.on_open_directory),
            ("#" + _("Search"), self.on_file_search),
            (1, _("User(s)"), self.popup_menu_users, self.on_popup_menu_users),
            ("", None),
            ("#" + _("_Retry"), self.on_retry_transfer),
            ("", None),
            ("#" + _("Abor_t"), self.on_abort_transfer),
            ("#" + _("_Clear"), self.on_clear_transfer),
            ("", None),
            (1, _("Clear Groups"), self.popup_menu_clear, None)
        )

        frame.clearFinishedAbortedButton.connect("clicked", self.on_clear_finished_aborted)
        frame.clearQueuedButton.connect("clicked", self.on_try_clear_queued)
        frame.retryTransferButton.connect("clicked", self.on_retry_transfer)
        frame.abortTransferButton.connect("clicked", self.on_abort_transfer)
        frame.deleteTransferButton.connect("clicked", self.on_clear_transfer)
        frame.DownloadList.expand_all()

        self.frame.ToggleAutoclearDownloads.set_active(self.frame.np.config.sections["transfers"]["autoclear_downloads"])
        frame.ToggleAutoclearDownloads.connect("toggled", self.on_toggle_autoclear)

        fill_file_grouping_combobox(frame.ToggleTreeDownloads)
        frame.ToggleTreeDownloads.set_active(self.frame.np.config.sections["transfers"]["groupdownloads"])
        frame.ToggleTreeDownloads.connect("changed", self.on_toggle_tree)
        self.on_toggle_tree(None)

        self.frame.ExpandDownloads.set_active(self.frame.np.config.sections["transfers"]["downloadsexpanded"])
        frame.ExpandDownloads.connect("toggled", self.on_expand_downloads)
        self.on_expand_downloads(None)

    def on_try_clear_queued(self, widget):
        option_dialog(
            parent=self.frame.MainWindow,
            title=_('Clear Queued Downloads'),
            message=_('Are you sure you wish to clear all queued downloads?'),
            callback=self.on_clear_response
        )

    def download_large_folder(self, username, folder, numfiles, conn, file_list):
        option_dialog(
            parent=self.MainWindow,
            title=_("Download %(num)i files?") % {'num': numfiles},
            message=_("Are you sure you wish to download %(num)i files from %(user)s's folder %(folder)s?") % {'num': numfiles, 'user': username, 'folder': folder},
            callback=self.folder_download_response,
            callback_data=(conn, file_list)
        )

    def folder_download_response(self, dialog, response, data):

        if response == Gtk.ResponseType.OK:
            self.np.transfers.folder_contents_response(data[0], data[1])

        dialog.destroy()

    def expand(self, transfer_path, user_path):
        if self.frame.ExpandDownloads.get_active():
            self.frame.DownloadList.expand_to_path(transfer_path)

        elif user_path and self.tree_users == 1:
            # Group by folder, show user folders in collapsed mode

            self.frame.DownloadList.expand_to_path(user_path)

    def on_expand_downloads(self, widget):

        expanded = self.frame.ExpandDownloads.get_active()

        if expanded:
            self.frame.DownloadList.expand_all()
            self.frame.ExpandDownloadsImage.set_from_icon_name("list-remove-symbolic", Gtk.IconSize.BUTTON)
        else:
            collapse_treeview(self.frame.DownloadList, self.tree_users)
            self.frame.ExpandDownloadsImage.set_from_icon_name("list-add-symbolic", Gtk.IconSize.BUTTON)

        self.frame.np.config.sections["transfers"]["downloadsexpanded"] = expanded
        self.frame.np.config.write_configuration()

    def on_toggle_autoclear(self, widget):
        self.frame.np.config.sections["transfers"]["autoclear_downloads"] = self.frame.ToggleAutoclearDownloads.get_active()

    def on_toggle_tree(self, widget):
        self.tree_users = self.frame.ToggleTreeDownloads.get_active()
        self.frame.np.config.sections["transfers"]["groupdownloads"] = self.tree_users

        if self.tree_users == 0:
            self.frame.ExpandDownloads.hide()
        else:
            self.frame.ExpandDownloads.show()

        self.rebuild_transfers()

    def selected_results_all_data(self, model, path, iterator, data):
        if iterator in self.selected_users:
            return

        user = model.get_value(iterator, 0)
        filename = model.get_value(iterator, 2)
        fullname = model.get_value(iterator, 10)
        size = speed = length = queue = immediate = num = country = bitratestr = ""

        for transfer in self.frame.np.transfers.downloads:
            if transfer.user == user and fullname == transfer.filename:
                size = str(human_size(transfer.size))
                try:
                    if transfer.speed:
                        speed = str(human_speed(transfer.speed))
                except Exception:
                    pass
                bitratestr = str(transfer.bitrate)
                length = str(transfer.length)
                break
        else:
            return

        directory = fullname.rsplit("\\", 1)[0]

        data.append({
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
        })

    def on_file_properties(self, widget):

        if not self.frame.np.transfers:
            return

        data = []
        self.widget.get_selection().selected_foreach(self.selected_results_all_data, data)

        if data:
            FileProperties(self.frame, data).show()

    def on_open_directory(self, widget):

        downloaddir = self.frame.np.config.sections["transfers"]["downloaddir"]
        incompletedir = self.frame.np.config.sections["transfers"]["incompletedir"]

        if incompletedir == "":
            incompletedir = downloaddir

        transfer = next(iter(self.selected_transfers))

        complete_path = os.path.join(downloaddir, transfer.path)

        if transfer.path == "":
            if transfer.status == "Finished":
                final_path = downloaddir
            else:
                final_path = incompletedir
        elif os.path.exists(complete_path):  # and tranfer.status is "Finished"
            final_path = complete_path
        else:
            final_path = incompletedir

        # Finally, try to open the directory we got...
        command = self.frame.np.config.sections["ui"]["filemanager"]
        open_file_path(final_path, command)

    def on_key_press_event(self, widget, event):

        key = Gdk.keyval_name(event.keyval)

        if key in ("P", "p"):
            self.on_popup_menu(widget, event, "keyboard")
        else:
            self.select_transfers()

            if key in ("T", "t"):
                self.on_abort_transfer(widget)
            elif key in ("R", "r"):
                self.on_retry_transfer(widget)
            elif key == "Delete":
                self.on_abort_transfer(widget, clear=True)
            else:
                # No key match, continue event
                return False

        widget.stop_emission_by_name("key_press_event")
        return True

    def on_play_files(self, widget, prefix=""):
        start_new_thread(self._on_play_files, (widget, prefix))

    def _on_play_files(self, widget, prefix=""):

        downloaddir = self.frame.np.config.sections["transfers"]["downloaddir"]

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
                command = self.frame.np.config.sections["players"]["default"]
                open_file_path(playfile, command)

    def double_click(self, event):

        self.select_transfers()
        dc = self.frame.np.config.sections["transfers"]["download_doubleclick"]

        if dc == 1:  # Send to player
            self.on_play_files(None)
        elif dc == 2:  # File manager
            self.on_open_directory(None)
        elif dc == 3:  # Search
            self.on_file_search(None)
        elif dc == 4:  # Abort
            self.on_abort_transfer(None)
        elif dc == 5:  # Clear
            self.on_clear_transfer(None)
        elif dc == 6:  # Retry
            self.on_retry_transfer(None)

    def on_popup_menu(self, widget, event, kind):

        if kind == "mouse":
            if event.button == 3:
                set_treeview_selected_row(widget, event)

            else:
                pathinfo = widget.get_path_at_pos(event.x, event.y)

                if pathinfo is None:
                    widget.get_selection().unselect_all()

                elif event.button == 1 and event.type == Gdk.EventType._2BUTTON_PRESS:
                    self.double_click(event)

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
            # Copy URL, Copy Folder URL, Send to player, File Properties, File manager, Search filename
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

    def on_abort_transfer(self, widget, remove_file=False, clear=False):
        self.select_transfers()
        self.abort_transfers(remove_file, clear)

    def on_clear_queued(self, widget):
        self.clear_transfers(["Queued"])

    def on_retry_transfer(self, widget):

        self.select_transfers()

        for transfer in self.selected_transfers:

            if transfer.status in ["Finished", "Old"]:
                continue

            self.frame.np.transfers.abort_transfer(transfer)
            self.frame.np.transfers.get_file(transfer.user, transfer.filename, transfer.path, transfer)
