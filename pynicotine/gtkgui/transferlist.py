# COPYRIGHT (C) 2020-2022 Nicotine+ Team
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

from sys import maxsize

from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk

from pynicotine.config import config
from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.dialogs.fileproperties import FileProperties
from pynicotine.gtkgui.utils import copy_text
from pynicotine.gtkgui.widgets.accelerator import Accelerator
from pynicotine.gtkgui.widgets.popupmenu import PopupMenu
from pynicotine.gtkgui.widgets.theme import update_widget_visuals
from pynicotine.gtkgui.widgets.treeview import collapse_treeview
from pynicotine.gtkgui.widgets.treeview import create_grouping_menu
from pynicotine.gtkgui.widgets.treeview import initialise_columns
from pynicotine.gtkgui.widgets.treeview import save_columns
from pynicotine.gtkgui.widgets.treeview import select_user_row_iter
from pynicotine.gtkgui.widgets.treeview import show_file_path_tooltip
from pynicotine.gtkgui.widgets.treeview import verify_grouping_mode
from pynicotine.gtkgui.widgets.ui import UserInterface
from pynicotine.transfers import Transfer
from pynicotine.utils import human_length
from pynicotine.utils import human_size
from pynicotine.utils import human_speed


class TransferList(UserInterface):

    path_separator = path_label = retry_label = abort_label = aborted_status = None
    page_id = user_counter = file_counter = expand_button = expand_icon = grouping_button = None

    def __init__(self, frame, core, transfer_type):

        super().__init__("ui/" + transfer_type + "s.ui")
        (
            self.clear_all_button,
            self.container,
            self.tree_view
        ) = self.widgets

        self.frame = frame
        self.core = core
        self.type = transfer_type

        if GTK_API_VERSION >= 4:
            self.clear_all_button.set_has_frame(False)

        Accelerator("t", self.tree_view, self.on_abort_transfers_accelerator)
        Accelerator("r", self.tree_view, self.on_retry_transfers_accelerator)
        Accelerator("Delete", self.tree_view, self.on_clear_transfers_accelerator)
        Accelerator("<Alt>Return", self.tree_view, self.on_file_properties_accelerator)

        self.last_ui_update = 0
        self.transfer_list = []
        self.users = {}
        self.paths = {}
        self.selected_users = []
        self.selected_transfers = []
        self.tree_users = None

        # Status list
        self.statuses = {
            "Queued": _("Queued"),
            "Queued (prioritized)": _("Queued (prioritized)"),
            "Queued (privileged)": _("Queued (privileged)"),
            "Getting status": _("Getting status"),
            "Transferring": _("Transferring"),
            "Cannot connect": _("Cannot connect"),
            "Pending shutdown.": _("Pending shutdown"),
            "User logged off": _("User logged off"),
            "Disallowed extension": _("Disallowed extension"),  # Sent by Soulseek NS for filtered extensions
            "Aborted": _("Aborted"),
            "Cancelled": _("Cancelled"),
            "Paused": _("Paused"),
            "Finished": _("Finished"),
            "Filtered": _("Filtered"),
            "Banned": _("Banned"),
            "Blocked country": _("Blocked country"),
            "Too many files": _("Too many files"),
            "Too many megabytes": _("Too many megabytes"),
            "File not shared": _("File not shared"),
            "File not shared.": _("File not shared"),  # Newer variant containing a dot
            "Download folder error": _("Download folder error"),
            "Local file error": _("Local file error"),
            "Remote file error": _("Remote file error")
        }
        self.deprioritized_statuses = ("", "Paused", "Aborted", "Finished", "Filtered")

        self.transfersmodel = Gtk.TreeStore(
            str,                   # (0)  user
            str,                   # (1)  path
            str,                   # (2)  file name
            str,                   # (3)  translated status
            str,                   # (4)  hqueue position
            int,                   # (5)  percent
            str,                   # (6)  hsize
            str,                   # (7)  hspeed
            str,                   # (8)  htime elapsed
            str,                   # (9)  htime left
            GObject.TYPE_UINT64,   # (10) size
            GObject.TYPE_UINT64,   # (11) current bytes
            GObject.TYPE_UINT64,   # (12) speed
            GObject.TYPE_UINT,     # (13) queue position
            int,                   # (14) time elapsed
            int,                   # (15) time left
            GObject.TYPE_PYOBJECT  # (16) transfer object
        )

        self.column_numbers = list(range(self.transfersmodel.get_n_columns()))
        self.cols = cols = initialise_columns(
            frame, transfer_type, self.tree_view,
            ["user", _("User"), 200, "text", None],
            ["path", self.path_label, 400, "text", None],
            ["filename", _("Filename"), 400, "text", None],
            ["status", _("Status"), 140, "text", None],
            ["queue_position", _("Queue Position"), 75, "number", None],
            ["percent", _("Percent"), 70, "progress", None],
            ["size", _("Size"), 170, "number", None],
            ["speed", _("Speed"), 90, "number", None],
            ["time_elapsed", _("Time Elapsed"), 140, "number", None],
            ["time_left", _("Time Left"), 140, "number", None],
        )

        cols["user"].set_sort_column_id(0)
        cols["path"].set_sort_column_id(1)
        cols["filename"].set_sort_column_id(2)
        cols["status"].set_sort_column_id(3)
        cols["queue_position"].set_sort_column_id(13)
        cols["percent"].set_sort_column_id(5)
        cols["size"].set_sort_column_id(10)
        cols["speed"].set_sort_column_id(12)
        cols["time_elapsed"].set_sort_column_id(14)
        cols["time_left"].set_sort_column_id(15)

        self.tree_view.set_model(self.transfersmodel)

        state = GLib.Variant("s", verify_grouping_mode(config.sections["transfers"]["group%ss" % transfer_type]))
        action = Gio.SimpleAction(name="%sgrouping" % transfer_type, parameter_type=GLib.VariantType("s"), state=state)
        action.connect("change-state", self.on_toggle_tree)
        frame.window.add_action(action)
        action.change_state(state)

        menu = create_grouping_menu(
            frame.window, config.sections["transfers"]["group%ss" % transfer_type], self.on_toggle_tree)
        self.grouping_button.set_menu_model(menu)

        self.expand_button.connect("toggled", self.on_expand_tree)
        self.expand_button.set_active(config.sections["transfers"]["%ssexpanded" % transfer_type])

        self.popup_menu_users = PopupMenu(frame)
        self.popup_menu_clear = PopupMenu(frame)
        self.clear_all_button.set_menu_model(self.popup_menu_clear.model)

        self.popup_menu_copy = PopupMenu(frame)
        self.popup_menu_copy.add_items(
            ("#" + _("Copy _File Path"), self.on_copy_file_path),
            ("#" + _("Copy _URL"), self.on_copy_url),
            ("#" + _("Copy Folder U_RL"), self.on_copy_dir_url)
        )

        self.popup_menu = PopupMenu(frame, self.tree_view, self.on_popup_menu)
        self.popup_menu.add_items(
            ("#" + "selected_files", None),
            ("", None),
            ("#" + _("Send to _Player"), self.on_play_files),
            ("#" + _("_Open in File Manager"), self.on_open_file_manager),
            ("#" + _("F_ile Properties"), self.on_file_properties),
            ("", None),
            ("#" + _("_Search"), self.on_file_search),
            ("#" + _("_Browse Folder(s)"), self.on_browse_folder),
            ("", None),
            ("#" + self.retry_label, self.on_retry_transfer),
            ("#" + self.abort_label, self.on_abort_transfer),
            ("#" + _("_Clear"), self.on_clear_transfer),
            ("", None),
            (">" + _("Clear Groups"), self.popup_menu_clear),
            (">" + _("Copy"), self.popup_menu_copy),
            (">" + _("User(s)"), self.popup_menu_users)
        )

        self.update_visuals()

    def init_transfers(self, transfer_list):
        self.transfer_list = transfer_list
        self.update_model(forceupdate=True)

    def server_login(self):
        pass

    def server_disconnect(self):
        pass

    def rebuild_transfers(self):
        self.clear_model()
        self.update_model()

    def save_columns(self):
        save_columns(self.type, self.tree_view.get_columns())

    def update_visuals(self):

        for widget in list(self.__dict__.values()):
            update_widget_visuals(widget, list_font_target="transfersfont")

    def select_transfers(self):

        self.selected_transfers.clear()
        self.selected_users.clear()

        model, paths = self.tree_view.get_selection().get_selected_rows()

        for path in paths:
            iterator = model.get_iter(path)
            self.select_transfer(model, iterator, select_user=True)

            # If we're in grouping mode, select any transfers under the selected
            # user or folder
            self.select_child_transfers(model, model.iter_children(iterator))

    def select_child_transfers(self, model, iterator):

        while iterator is not None:
            self.select_transfer(model, iterator)
            self.select_child_transfers(model, model.iter_children(iterator))
            iterator = model.iter_next(iterator)

    def select_transfer(self, model, iterator, select_user=False):

        transfer = model.get_value(iterator, 16)

        if transfer.filename is not None and transfer not in self.selected_transfers:
            self.selected_transfers.append(transfer)

        if select_user and transfer.user not in self.selected_users:
            self.selected_users.append(transfer.user)

    def new_transfer_notification(self, finished=False):
        if self.frame.current_page_id != self.page_id:
            self.frame.request_tab_hilite(self.page_id, mentioned=finished)

    def on_ban(self, *_args):

        self.select_transfers()

        for user in self.selected_users:
            self.core.network_filter.ban_user(user)

    def on_file_search(self, *_args):

        transfer = next(iter(self.selected_transfers), None)

        if not transfer:
            return

        self.frame.search_entry.set_text(transfer.filename.rsplit("\\", 1)[1])
        self.frame.change_main_page(self.frame.search_page)

    def translate_status(self, status):

        translated_status = self.statuses.get(status)

        if translated_status:
            return translated_status

        return status

    def update_num_users_files(self):
        self.user_counter.set_text(str(len(self.users)))
        self.file_counter.set_text(str(len(self.transfer_list)))

    def update_model(self, transfer=None, forceupdate=False, update_parent=True):

        if not forceupdate and self.frame.current_page_id != self.page_id:
            # No need to do unnecessary work if transfers are not visible
            return

        if transfer is not None:
            self.update_specific(transfer)

        elif self.transfer_list:
            for transfer_i in reversed(self.transfer_list):
                self.update_specific(transfer_i)

        if update_parent:
            self.update_parent_rows(transfer)

    def update_parent_rows(self, transfer=None):

        if self.tree_users != "ungrouped":
            if transfer is not None:
                username = transfer.user
                path = transfer.path if self.type == "download" else transfer.filename.rsplit('\\', 1)[0]
                user_path = username + path

                user_path_iter = self.paths.get(user_path)
                user_iter = self.users.get(username)

                if user_path_iter:
                    self.update_parent_row(user_path_iter, user_path, folder=True)

                if user_iter:
                    self.update_parent_row(user_iter, username)

            else:
                for user_path, user_path_iter in list(self.paths.items()):
                    self.update_parent_row(user_path_iter, user_path, folder=True)

                for username, user_iter in list(self.users.items()):
                    self.update_parent_row(user_iter, username)

        # Show tab description if necessary
        self.container.get_parent().set_visible(self.transfer_list)

    @staticmethod
    def get_hqueue_position(queue_position):
        return str(queue_position) if queue_position > 0 else ""

    @staticmethod
    def get_hsize(current_byte_offset, size):
        return "%s / %s" % (human_size(current_byte_offset), human_size(size))

    @staticmethod
    def get_hspeed(speed):
        return human_speed(speed) if speed > 0 else ""

    @staticmethod
    def get_helapsed(elapsed):
        return human_length(elapsed) if elapsed >= 1 else ""

    @staticmethod
    def get_hleft(left):
        return human_length(left) if left >= 1 else ""

    @staticmethod
    def get_percent(current_byte_offset, size):
        return min(((100 * int(current_byte_offset)) / int(size)), 100) if size > 0 else 100

    @staticmethod
    def get_size(size):

        try:
            size = int(size)

            if size < 0 or size > maxsize:
                size = 0

        except TypeError:
            size = 0

        return size

    def update_parent_row(self, initer, key, folder=False):

        speed = 0.0
        total_size = current_bytes = 0
        elapsed = 0
        salient_status = ""

        iterator = self.transfersmodel.iter_children(initer)

        if iterator is None:
            # Remove parent row if no children are present anymore
            dictionary = self.paths if folder else self.users
            self.transfersmodel.remove(initer)
            del dictionary[key]
            return

        while iterator is not None:
            transfer = self.transfersmodel.get_value(iterator, 16)
            status = transfer.status

            if status == "Transferring" or salient_status in self.deprioritized_statuses:
                salient_status = status

            if status == "Filtered":
                # We don't want to count filtered files when calculating the progress
                iterator = self.transfersmodel.iter_next(iterator)
                continue

            elapsed += transfer.time_elapsed or 0
            total_size += self.get_size(transfer.size)
            current_bytes += transfer.current_byte_offset or 0
            speed += transfer.speed or 0

            iterator = self.transfersmodel.iter_next(iterator)

        transfer = self.transfersmodel.get_value(initer, 16)

        if transfer.status != salient_status:
            self.transfersmodel.set_value(initer, 3, self.translate_status(salient_status))
            transfer.status = salient_status

        if transfer.speed != speed:
            self.transfersmodel.set_value(initer, 7, self.get_hspeed(speed))
            self.transfersmodel.set_value(initer, 12, GObject.Value(GObject.TYPE_UINT64, speed))
            transfer.speed = speed

        if transfer.time_elapsed != elapsed:
            left = (total_size - current_bytes) / speed if speed > 0 else 0

            self.transfersmodel.set_value(initer, 8, self.get_helapsed(elapsed))
            self.transfersmodel.set_value(initer, 9, self.get_hleft(left))
            self.transfersmodel.set_value(initer, 14, elapsed)
            self.transfersmodel.set_value(initer, 15, left)
            transfer.time_elapsed = elapsed

        if transfer.current_byte_offset != current_bytes:
            self.transfersmodel.set_value(initer, 5, self.get_percent(current_bytes, total_size))
            self.transfersmodel.set_value(initer, 6, "%s / %s" % (human_size(current_bytes), human_size(total_size)))
            self.transfersmodel.set_value(initer, 11, GObject.Value(GObject.TYPE_UINT64, current_bytes))
            transfer.current_byte_offset = current_bytes

        if transfer.size != total_size:
            self.transfersmodel.set_value(initer, 6, "%s / %s" % (human_size(current_bytes), human_size(total_size)))
            self.transfersmodel.set_value(initer, 10, GObject.Value(GObject.TYPE_UINT64, total_size))
            transfer.size = total_size

    def update_specific(self, transfer=None):

        current_byte_offset = transfer.current_byte_offset or 0
        queue_position = transfer.queue_position or 0
        modifier = transfer.modifier
        status = transfer.status or ""

        if modifier and status == "Queued":
            # Priority status
            status = status + " (%s)" % modifier

        size = self.get_size(transfer.size)
        speed = transfer.speed or 0
        hspeed = self.get_hspeed(speed)
        elapsed = transfer.time_elapsed or 0
        helapsed = self.get_helapsed(elapsed)
        left = transfer.time_left or 0
        initer = transfer.iterator

        # Modify old transfer
        if initer is not None:
            translated_status = self.translate_status(status)

            if self.transfersmodel.get_value(initer, 3) != translated_status:
                self.transfersmodel.set_value(initer, 3, translated_status)

            if self.transfersmodel.get_value(initer, 7) != hspeed:
                self.transfersmodel.set_value(initer, 7, hspeed)
                self.transfersmodel.set_value(initer, 12, GObject.Value(GObject.TYPE_UINT64, speed))

            if self.transfersmodel.get_value(initer, 8) != helapsed:
                self.transfersmodel.set_value(initer, 8, helapsed)
                self.transfersmodel.set_value(initer, 9, self.get_hleft(left))
                self.transfersmodel.set_value(initer, 14, elapsed)
                self.transfersmodel.set_value(initer, 15, left)

            if self.transfersmodel.get_value(initer, 11) != current_byte_offset:
                percent = self.get_percent(current_byte_offset, size)

                self.transfersmodel.set_value(initer, 5, percent)
                self.transfersmodel.set_value(initer, 6, self.get_hsize(current_byte_offset, size))
                self.transfersmodel.set_value(initer, 11, GObject.Value(GObject.TYPE_UINT64, current_byte_offset))

            elif self.transfersmodel.get_value(initer, 10) != size:
                self.transfersmodel.set_value(initer, 6, self.get_hsize(current_byte_offset, size))
                self.transfersmodel.set_value(initer, 10, GObject.Value(GObject.TYPE_UINT64, size))

            if self.transfersmodel.get_value(initer, 13) != queue_position:
                self.transfersmodel.set_value(initer, 4, self.get_hqueue_position(queue_position))
                self.transfersmodel.set_value(initer, 13, GObject.Value(GObject.TYPE_UINT, queue_position))

            return

        expand_user = False
        expand_folder = False

        filename = transfer.filename
        user = transfer.user
        shortfn = filename.split("\\")[-1]

        if self.tree_users != "ungrouped":
            # Group by folder or user

            empty_int = 0
            empty_str = ""

            if user not in self.users:
                # Create Parent if it doesn't exist
                # ProgressRender not visible (last column sets 4th column)
                self.users[user] = self.transfersmodel.insert_with_values(
                    None, -1, self.column_numbers,
                    [
                        user,
                        empty_str,
                        empty_str,
                        empty_str,
                        empty_str,
                        empty_int,
                        empty_str,
                        empty_str,
                        empty_str,
                        empty_str,
                        empty_int,
                        empty_int,
                        empty_int,
                        empty_int,
                        empty_int,
                        empty_int,
                        Transfer(user=user)
                    ]
                )

                if self.tree_users == "folder_grouping":
                    expand_user = True
                else:
                    expand_user = self.expand_button.get_active()

            parent = self.users[user]

            if self.tree_users == "folder_grouping":
                # Group by folder

                """ Paths can be empty if files are downloaded individually, make sure we
                don't add files to the wrong user in the TreeView """
                full_path = path = transfer.path if self.type == "download" else transfer.filename.rsplit('\\', 1)[0]
                user_path = user + path

                if config.sections["ui"]["reverse_file_paths"]:
                    path = self.path_separator.join(reversed(path.split(self.path_separator)))

                if user_path not in self.paths:
                    self.paths[user_path] = self.transfersmodel.insert_with_values(
                        self.users[user], -1, self.column_numbers,
                        [
                            user,
                            path,
                            empty_str,
                            empty_str,
                            empty_str,
                            empty_int,
                            empty_str,
                            empty_str,
                            empty_str,
                            empty_str,
                            empty_int,
                            empty_int,
                            empty_int,
                            empty_int,
                            empty_int,
                            empty_int,
                            Transfer(user=user, path=full_path)
                        ]
                    )
                    expand_folder = self.expand_button.get_active()

                parent = self.paths[user_path]
        else:
            # No grouping
            # We use this list to get the total number of users
            self.users.setdefault(user, set()).add(transfer)
            parent = None

        # Add a new transfer
        if self.tree_users == "folder_grouping":
            # Group by folder, path not visible
            path = ""
        else:
            path = transfer.path if self.type == "download" else transfer.filename.rsplit('\\', 1)[0]

            if config.sections["ui"]["reverse_file_paths"]:
                path = self.path_separator.join(reversed(path.split(self.path_separator)))

        iterator = self.transfersmodel.insert_with_values(
            parent, -1, self.column_numbers,
            (
                user,
                path,
                shortfn,
                self.translate_status(status),
                self.get_hqueue_position(queue_position),
                self.get_percent(current_byte_offset, size),
                self.get_hsize(current_byte_offset, size),
                hspeed,
                helapsed,
                self.get_hleft(left),
                GObject.Value(GObject.TYPE_UINT64, size),
                GObject.Value(GObject.TYPE_UINT64, current_byte_offset),
                GObject.Value(GObject.TYPE_UINT64, speed),
                GObject.Value(GObject.TYPE_UINT, queue_position),
                elapsed,
                left,
                transfer
            )
        )
        transfer.iterator = iterator
        self.update_num_users_files()

        if expand_user:
            self.tree_view.expand_row(self.transfersmodel.get_path(self.users[user]), False)

        if expand_folder:
            self.tree_view.expand_row(self.transfersmodel.get_path(self.paths[user_path]), False)

    def clear_model(self):

        self.users.clear()
        self.paths.clear()
        self.selected_transfers.clear()
        self.selected_users.clear()
        self.transfersmodel.clear()

        for transfer in self.transfer_list:
            transfer.iterator = None

    def retry_transfers(self):
        pass

    def abort_transfers(self, clear=False):

        for transfer in self.selected_transfers:
            if transfer.status != "Finished":
                self.core.transfers.abort_transfer(transfer, send_fail_message=True)

                if not clear:
                    transfer.status = self.aborted_status
                    self.update_model(transfer)

            if clear:
                self.remove_specific(transfer, update_parent=False)

        self.update_parent_rows()
        self.update_num_users_files()

    def remove_specific(self, transfer, cleartreeviewonly=False, update_parent=True):

        user = transfer.user

        if self.tree_users == "ungrouped" and user in self.users:
            # No grouping
            self.users[user].discard(transfer)

            if not self.users[user]:
                del self.users[user]

        if transfer in self.core.transfers.transfer_request_times:
            del self.core.transfers.transfer_request_times[transfer]

        if not cleartreeviewonly:
            self.transfer_list.remove(transfer)

        if transfer.iterator is not None:
            self.transfersmodel.remove(transfer.iterator)

        if update_parent:
            self.update_parent_rows(transfer)
            self.update_num_users_files()

    def clear_transfers(self, statuses=None):

        for transfer in self.transfer_list.copy():
            if statuses is None or transfer.status in statuses:
                self.core.transfers.abort_transfer(transfer, send_fail_message=True)
                self.remove_specific(transfer)

    def add_popup_menu_user(self, popup, user):

        popup.setup_user_menu(user)
        popup.add_items(
            ("", None),
            ("#" + _("Select User's Transfers"), self.on_select_user_transfers, user)
        )
        popup.update_model()
        popup.toggle_user_items()

    def populate_popup_menu_users(self):

        self.popup_menu_users.clear()

        if not self.selected_users:
            return

        # Multiple users, create submenus for each user
        if len(self.selected_users) > 1:
            for user in self.selected_users:
                popup = PopupMenu(self.frame)
                self.add_popup_menu_user(popup, user)
                self.popup_menu_users.add_items((">" + user, popup))
                self.popup_menu_users.update_model()
            return

        # Single user, add items directly to "User(s)" submenu
        user = next(iter(self.selected_users), None)
        self.add_popup_menu_user(self.popup_menu_users, user)

    def on_expand_tree(self, widget):

        expanded = widget.get_active()

        if expanded:
            icon_name = "go-up-symbolic"
            self.tree_view.expand_all()

        else:
            icon_name = "go-down-symbolic"
            collapse_treeview(self.tree_view, self.tree_users)

        self.expand_icon.set_property("icon-name", icon_name)

        config.sections["transfers"]["%ssexpanded" % self.type] = expanded
        config.write_configuration()

    def on_toggle_tree(self, action, state):

        mode = state.get_string()
        active = mode != "ungrouped"

        config.sections["transfers"]["group%ss" % self.type] = mode
        self.tree_view.set_show_expanders(active)
        self.expand_button.set_visible(active)

        self.tree_users = mode

        if self.transfer_list:
            self.rebuild_transfers()

        action.set_state(state)

    @staticmethod
    def on_tooltip(widget, pos_x, pos_y, _keyboard_mode, tooltip):
        return show_file_path_tooltip(widget, pos_x, pos_y, tooltip, 16, transfer=True)

    def on_popup_menu(self, menu, _widget):

        self.select_transfers()
        num_selected_transfers = len(self.selected_transfers)
        menu.set_num_selected_files(num_selected_transfers)

        self.populate_popup_menu_users()

    def on_row_activated(self, _treeview, _path, _column):

        self.select_transfers()
        action = config.sections["transfers"]["%s_doubleclick" % self.type]

        if action == 1:    # Send to Player
            self.on_play_files()

        elif action == 2:  # Open in File Manager
            self.on_open_file_manager()

        elif action == 3:  # Search
            self.on_file_search()

        elif action == 4:  # Pause / Abort
            self.abort_transfers()

        elif action == 5:  # Clear
            self.abort_transfers(clear=True)

        elif action == 6:  # Resume / Retry
            self.retry_transfers()

        elif action == 7:  # Browse Folder
            self.on_browse_folder()

    def on_select_user_transfers(self, *args):

        if not self.selected_users:
            return

        selected_user = args[-1]

        sel = self.tree_view.get_selection()
        fmodel = self.tree_view.get_model()
        sel.unselect_all()

        iterator = fmodel.get_iter_first()

        select_user_row_iter(fmodel, sel, 0, selected_user, iterator)

        self.select_transfers()

    def on_abort_transfers_accelerator(self, *_args):
        """ T: abort transfer """

        self.select_transfers()
        self.abort_transfers()
        return True

    def on_retry_transfers_accelerator(self, *_args):
        """ R: retry transfers """

        self.select_transfers()
        self.retry_transfers()
        return True

    def on_clear_transfers_accelerator(self, *_args):
        """ Delete: clear transfers """

        self.select_transfers()
        self.abort_transfers(clear=True)
        return True

    def on_file_properties_accelerator(self, *_args):
        """ Alt+Return: show file properties dialog """

        self.select_transfers()
        self.on_file_properties()
        return True

    def on_file_properties(self, *_args):

        data = []

        for transfer in self.selected_transfers:
            fullname = transfer.filename
            filename = fullname.split("\\")[-1]
            directory = fullname.rsplit("\\", 1)[0]

            data.append({
                "user": transfer.user,
                "fn": fullname,
                "filename": filename,
                "directory": directory,
                "path": transfer.path,
                "queue_position": transfer.queue_position,
                "speed": transfer.speed,
                "size": transfer.size,
                "bitrate": transfer.bitrate,
                "length": transfer.length
            })

        if data:
            FileProperties(self.frame, self.core, data, download_button=False).show()

    def on_copy_url(self, *_args):
        pass

    def on_copy_dir_url(self, *_args):
        pass

    def on_copy_file_path(self, *_args):

        transfer = next(iter(self.selected_transfers), None)

        if transfer:
            copy_text(transfer.filename)

    def on_play_files(self, *_args):
        pass

    def on_open_file_manager(self, *_args):
        pass

    def on_browse_folder(self, *_args):
        pass

    def on_retry_transfer(self, *_args):
        self.select_transfers()
        self.retry_transfers()

    def on_abort_transfer(self, *_args):
        self.select_transfers()
        self.abort_transfers()

    def on_clear_transfer(self, *_args):
        self.select_transfers()
        self.abort_transfers(clear=True)

    def on_clear_queued_response(self, dialog, response_id, _data):

        dialog.destroy()

        if response_id == 2:
            self.clear_transfers(["Queued"])

    def on_clear_all_response(self, dialog, response_id, _data):

        dialog.destroy()

        if response_id == 2:
            self.clear_transfers()

    def on_clear_queued(self, *_args):
        self.clear_transfers(["Queued"])

    def on_clear_finished(self, *_args):
        self.clear_transfers(["Finished"])
