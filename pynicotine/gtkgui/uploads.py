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
from gi.repository import Gtk

from _thread import start_new_thread
from pynicotine import slskmessages
from pynicotine.gtkgui.dialogs import option_dialog
from pynicotine.gtkgui.transferlist import TransferList
from pynicotine.gtkgui.utils import collapse_treeview
from pynicotine.gtkgui.utils import fill_file_grouping_combobox
from pynicotine.gtkgui.utils import open_file_path
from pynicotine.gtkgui.utils import PopupMenu
from pynicotine.gtkgui.utils import set_treeview_selected_row


class Uploads(TransferList):

    def __init__(self, frame, tab_label):

        TransferList.__init__(self, frame, frame.UploadList, type='upload')
        self.tab_label = tab_label

        self.popup_menu_users = PopupMenu(self.frame, False)
        self.popup_menu_clear = popup2 = PopupMenu(self.frame, False)
        popup2.setup(
            ("#" + _("Clear finished/erred"), self.on_clear_finished_erred),
            ("#" + _("Clear finished/aborted"), self.on_clear_finished_aborted),
            ("#" + _("Clear finished"), self.on_clear_finished),
            ("#" + _("Clear aborted"), self.on_clear_aborted),
            ("#" + _("Clear queued"), self.on_clear_queued),
            ("#" + _("Clear failed"), self.on_clear_failed)
        )

        self.popup_menu = popup = PopupMenu(frame)
        popup.setup(
            ("#" + _("Copy _URL"), self.on_copy_url),
            ("#" + _("Copy folder URL"), self.on_copy_dir_url),
            ("#" + _("Send to _player"), self.on_play_files),
            ("#" + _("Open folder"), self.on_open_directory),
            ("#" + _("Search"), self.on_file_search),
            (1, _("User(s)"), self.popup_menu_users, self.on_popup_menu_users),
            ("", None),
            ("#" + _("Abor_t"), self.on_abort_transfer),
            ("#" + _("_Clear"), self.on_clear_transfer),
            ("#" + _("_Retry"), self.on_upload_transfer),
            ("", None),
            (1, _("Clear Groups"), self.popup_menu_clear, None)
        )

        frame.clearUploadFinishedErredButton.connect("clicked", self.on_clear_finished_erred)
        frame.clearUploadQueueButton.connect("clicked", self.on_try_clear_queued)
        frame.abortUploadButton.connect("clicked", self.on_abort_transfer)
        frame.abortUserUploadButton.connect("clicked", self.on_abort_user)
        frame.banUploadButton.connect("clicked", self.on_ban)
        frame.UploadList.expand_all()

        self.frame.ToggleAutoclearUploads.set_active(self.frame.np.config.sections["transfers"]["autoclear_uploads"])
        frame.ToggleAutoclearUploads.connect("toggled", self.on_toggle_autoclear)

        fill_file_grouping_combobox(frame.ToggleTreeUploads)
        frame.ToggleTreeUploads.set_active(self.frame.np.config.sections["transfers"]["groupuploads"])
        frame.ToggleTreeUploads.connect("changed", self.on_toggle_tree)
        self.on_toggle_tree(None)

        self.frame.ExpandUploads.set_active(self.frame.np.config.sections["transfers"]["uploadsexpanded"])
        frame.ExpandUploads.connect("toggled", self.on_expand_uploads)

        self.on_expand_uploads(None)

    def on_try_clear_queued(self, widget):
        option_dialog(
            parent=self.frame.MainWindow,
            title=_('Clear Queued Uploads'),
            message=_('Are you sure you wish to clear all queued uploads?'),
            callback=self.on_clear_response
        )

    def on_open_directory(self, widget):

        downloaddir = self.frame.np.config.sections["transfers"]["downloaddir"]
        incompletedir = self.frame.np.config.sections["transfers"]["incompletedir"]

        if incompletedir == "":
            incompletedir = downloaddir

        transfer = next(iter(self.selected_transfers))

        if os.path.exists(transfer.path):
            final_path = transfer.path
        else:
            final_path = incompletedir

        # Finally, try to open the directory we got...
        command = self.frame.np.config.sections["ui"]["filemanager"]
        open_file_path(final_path, command)

    def expand(self, transfer_path, user_path):
        if self.frame.ExpandUploads.get_active():
            self.frame.UploadList.expand_to_path(transfer_path)

        elif user_path and self.tree_users == 1:
            # Group by folder, show user folders in collapsed mode

            self.frame.UploadList.expand_to_path(user_path)

    def on_expand_uploads(self, widget):

        expanded = self.frame.ExpandUploads.get_active()

        if expanded:
            self.frame.UploadList.expand_all()
            self.frame.ExpandUploadsImage.set_from_icon_name("list-remove-symbolic", Gtk.IconSize.BUTTON)
        else:
            collapse_treeview(self.frame.UploadList, self.tree_users)
            self.frame.ExpandUploadsImage.set_from_icon_name("list-add-symbolic", Gtk.IconSize.BUTTON)

        self.frame.np.config.sections["transfers"]["uploadsexpanded"] = expanded
        self.frame.np.config.write_configuration()

    def on_toggle_autoclear(self, widget):
        self.frame.np.config.sections["transfers"]["autoclear_uploads"] = self.frame.ToggleAutoclearUploads.get_active()

    def on_toggle_tree(self, widget):

        self.tree_users = self.frame.ToggleTreeUploads.get_active()
        self.frame.np.config.sections["transfers"]["groupuploads"] = self.tree_users

        self.rebuild_transfers()

        if self.tree_users == 0:
            self.frame.ExpandUploads.hide()
        else:
            self.frame.ExpandUploads.show()

    def on_key_press_event(self, widget, event):

        key = Gdk.keyval_name(event.keyval)

        if key in ("P", "p"):
            self.on_popup_menu(widget, event, "keyboard")
        else:
            self.select_transfers()

            if key in ("T", "t"):
                self.on_abort_transfer(widget)
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

        for fn in self.selected_transfers:
            playfile = fn.realfilename

            if os.path.exists(playfile):
                command = self.frame.np.config.sections["players"]["default"]
                open_file_path(playfile, command)

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
            items[5].set_sensitive(True)  # Users Menu
        else:
            items[5].set_sensitive(False)  # Users Menu

        if files:
            act = True
        else:
            # Disable options
            # Copy URL, Copy Folder URL, Send to player, File manager, Search filename
            act = False

        for i in range(0, 5):
            items[i].set_sensitive(act)

        if users and files:
            act = True
        else:
            act = False

        for i in range(7, 10):
            items[i].set_sensitive(act)

        self.popup_menu.popup(None, None, None, None, 3, event.time)

        if kind == "keyboard":
            widget.stop_emission_by_name("key_press_event")
        elif kind == "mouse":
            widget.stop_emission_by_name("button_press_event")

        return True

    def double_click(self, event):

        self.select_transfers()
        dc = self.frame.np.config.sections["transfers"]["upload_doubleclick"]

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

    def clear_by_user(self, user):

        for i in self.list[:]:
            if i.user == user:
                if i.transfertimer is not None:
                    i.transfertimer.cancel()
                self.remove_specific(i)

        self.frame.np.transfers.calc_upload_queue_sizes()
        self.frame.np.transfers.check_upload_queue()

    def on_abort_transfer(self, widget, remove_file=False, clear=False):

        self.select_transfers()

        self.abort_transfers(remove_file, clear)

        self.frame.np.transfers.calc_upload_queue_sizes()
        self.frame.np.transfers.check_upload_queue()

    def on_abort_user(self, widget):

        self.select_transfers()

        for user in self.selected_users:
            for i in self.list:
                if i.user == user:
                    self.selected_transfers.add(i)

        self.on_abort_transfer(widget)
        self.frame.np.transfers.calc_upload_queue_sizes()
        self.frame.np.transfers.check_upload_queue()

    def on_clear_queued(self, widget):

        self.clear_transfers(["Queued"])

        self.frame.np.transfers.calc_upload_queue_sizes()
        self.frame.np.transfers.check_upload_queue()

    def on_clear_failed(self, widget):

        self.clear_transfers(["Cannot connect", "Connection closed by peer", "Local file error", "Remote file error", "Getting address", "Waiting for peer to connect", "Initializing transfer"])

        self.frame.np.transfers.calc_upload_queue_sizes()
        self.frame.np.transfers.check_upload_queue()

    def on_upload_transfer(self, widget):

        self.select_transfers()

        for transfer in self.selected_transfers:
            filename = transfer.filename
            path = transfer.path
            user = transfer.user

            if user in self.frame.np.transfers.get_transferring_users():
                continue

            self.frame.np.send_message_to_peer(user, slskmessages.UploadQueueNotification(None))
            self.frame.np.transfers.push_file(user, filename, path, transfer=transfer)

        self.frame.np.transfers.check_upload_queue()
