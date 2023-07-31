# COPYRIGHT (C) 2020-2023 Nicotine+ Contributors
# COPYRIGHT (C) 2018 Mutnick <mutnick@techie.com>
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2008-2011 quinox <quinox@users.sf.net>
# COPYRIGHT (C) 2009 hedonist <ak@sensi.org>
# COPYRIGHT (C) 2006-2009 daelstorm <daelstorm@gmail.com>
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

from gi.repository import GObject

from pynicotine.config import config
from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.dialogs.fileproperties import FileProperties
from pynicotine.gtkgui.widgets import clipboard
from pynicotine.gtkgui.widgets import ui
from pynicotine.gtkgui.widgets.accelerator import Accelerator
from pynicotine.gtkgui.widgets.popupmenu import PopupMenu
from pynicotine.gtkgui.widgets.popupmenu import FilePopupMenu
from pynicotine.gtkgui.widgets.popupmenu import UserPopupMenu
from pynicotine.gtkgui.widgets.theme import add_css_class
from pynicotine.gtkgui.widgets.theme import get_file_type_icon_name
from pynicotine.gtkgui.widgets.theme import remove_css_class
from pynicotine.gtkgui.widgets.treeview import TreeView
from pynicotine.gtkgui.widgets.treeview import create_grouping_menu
from pynicotine.transfers import Transfer
from pynicotine.utils import UINT64_LIMIT
from pynicotine.utils import human_length
from pynicotine.utils import human_size
from pynicotine.utils import human_speed
from pynicotine.utils import humanize


class TransferList:

    path_separator = path_label = retry_label = abort_label = None
    deprioritized_statuses = ()
    transfer_page = user_counter = file_counter = expand_button = expand_icon = grouping_button = None

    def __init__(self, window, transfer_type):

        (
            self.clear_all_button,
            self.container,
            self.tree_container
        ) = ui.load(scope=self, path=f"{transfer_type}s.ui")

        self.window = window
        self.type = transfer_type

        if GTK_API_VERSION >= 4:
            self.clear_all_button.set_has_frame(False)

        self.transfer_list = []
        self.users = {}
        self.paths = {}
        self.grouping_mode = None
        self.row_id = 0
        self.file_properties = None

        # Use dict instead of list for faster membership checks
        self.selected_users = {}
        self.selected_transfers = {}

        # Status list
        self.statuses = {
            "Queued": _("Queued"),
            "Queued (prioritized)": _("Queued (prioritized)"),
            "Queued (privileged)": _("Queued (privileged)"),
            "Getting status": _("Getting status"),
            "Transferring": _("Transferring"),
            "Connection timeout": _("Connection timeout"),
            "Pending shutdown.": _("Pending shutdown"),
            "User logged off": _("User logged off"),
            "Disallowed extension": _("Disallowed extension"),
            "Cancelled": _("Cancelled"),
            "Paused": _("Paused"),
            "Finished": _("Finished"),
            "Filtered": _("Filtered"),
            "Banned": _("Banned"),
            "Too many files": _("Too many files"),
            "Too many megabytes": _("Too many megabytes"),
            "File not shared": _("File not shared"),
            "File not shared.": _("File not shared"),
            "Download folder error": _("Download folder error"),
            "Local file error": _("Local file error"),
            "Remote file error": _("Remote file error")
        }

        self.tree_view = TreeView(
            window, parent=self.tree_container, name=transfer_type,
            multi_select=True, activate_row_callback=self.on_row_activated,
            delete_accelerator_callback=self.on_clear_transfers_accelerator,
            columns={
                # Visible columns
                "user": {
                    "column_type": "text",
                    "title": _("User"),
                    "width": 200
                },
                "path": {
                    "column_type": "text",
                    "title": self.path_label,
                    "width": 200,
                    "expand_column": True,
                    "tooltip_callback": self.on_file_path_tooltip
                },
                "file_type": {
                    "column_type": "icon",
                    "title": _("File Type"),
                    "width": 40,
                    "hide_header": True
                },
                "filename": {
                    "column_type": "text",
                    "title": _("Filename"),
                    "width": 200,
                    "expand_column": True,
                    "tooltip_callback": self.on_file_path_tooltip
                },
                "status": {
                    "column_type": "text",
                    "title": _("Status"),
                    "width": 140
                },
                "queue_position": {
                    "column_type": "number",
                    "title": _("Queue"),
                    "width": 90,
                    "sort_column": "queue_position_data"
                },
                "percent": {
                    "column_type": "progress",
                    "title": _("Percent"),
                    "width": 90
                },
                "size": {
                    "column_type": "number",
                    "title": _("Size"),
                    "width": 180,
                    "sort_column": "size_data"
                },
                "speed": {
                    "column_type": "number",
                    "title": _("Speed"),
                    "width": 100,
                    "sort_column": "speed_data"
                },
                "time_elapsed": {
                    "column_type": "number",
                    "title": _("Time Elapsed"),
                    "width": 140,
                    "sort_column": "time_elapsed_data"
                },
                "time_left": {
                    "column_type": "number",
                    "title": _("Time Left"),
                    "width": 140,
                    "sort_column": "time_left_data"
                },

                # Hidden data columns
                "size_data": {"data_type": GObject.TYPE_UINT64},
                "current_bytes_data": {"data_type": GObject.TYPE_UINT64},
                "speed_data": {"data_type": GObject.TYPE_UINT64},
                "queue_position_data": {"data_type": GObject.TYPE_UINT},
                "time_elapsed_data": {"data_type": int},
                "time_left_data": {"data_type": GObject.TYPE_UINT64},
                "transfer_data": {"data_type": GObject.TYPE_PYOBJECT},
                "id_data": {
                    "data_type": GObject.TYPE_UINT64,
                    "default_sort_type": "ascending",
                    "iterator_key": True
                }
            }
        )

        Accelerator("t", self.tree_view.widget, self.on_abort_transfers_accelerator)
        Accelerator("r", self.tree_view.widget, self.on_retry_transfers_accelerator)
        Accelerator("<Alt>Return", self.tree_view.widget, self.on_file_properties_accelerator)

        menu = create_grouping_menu(
            window, config.sections["transfers"][f"group{transfer_type}s"], self.on_toggle_tree)
        self.grouping_button.set_menu_model(menu)

        if GTK_API_VERSION >= 4:
            add_css_class(widget=self.grouping_button.get_first_child(), css_class="image-button")

        self.expand_button.connect("toggled", self.on_expand_tree)
        self.expand_button.set_active(config.sections["transfers"][f"{transfer_type}sexpanded"])

        self.popup_menu_users = UserPopupMenu(window.application, tab_name="transfers")
        self.popup_menu_clear = PopupMenu(window.application)
        self.clear_all_button.set_menu_model(self.popup_menu_clear.model)

        self.popup_menu_copy = PopupMenu(window.application)
        self.popup_menu_copy.add_items(
            ("#" + _("Copy _File Path"), self.on_copy_file_path),
            ("#" + _("Copy _URL"), self.on_copy_url),
            ("#" + _("Copy Folder U_RL"), self.on_copy_dir_url)
        )

        self.popup_menu = FilePopupMenu(
            window.application, parent=self.tree_view.widget, callback=self.on_popup_menu
        )
        self.popup_menu.add_items(
            ("#" + _("Send to _Player"), self.on_play_files),
            ("#" + _("_Open in File Manager"), self.on_open_file_manager),
            ("#" + _("F_ile Properties"), self.on_file_properties),
            ("", None),
            ("#" + self.retry_label, self.on_retry_transfer),
            ("#" + self.abort_label, self.on_abort_transfer),
            ("#" + _("_Clear"), self.on_clear_transfer),
            ("", None),
            ("#" + _("_Browse Folder(s)"), self.on_browse_folder),
            ("#" + _("_Search"), self.on_file_search),
            ("", None),
            (">" + _("Copy"), self.popup_menu_copy),
            (">" + _("Clear All"), self.popup_menu_clear),
            (">" + _("User Actions"), self.popup_menu_users)
        )

    def init_transfers(self, transfer_list):
        self.transfer_list = transfer_list
        self.update_model()

    def select_transfers(self):

        self.selected_transfers.clear()
        self.selected_users.clear()

        for iterator in self.tree_view.get_selected_rows():
            transfer = self.tree_view.get_row_value(iterator, "transfer_data")
            self.select_transfer(transfer, select_user=True)

    def select_child_transfers(self, transfer):

        if transfer.filename is not None:
            return

        # Dummy Transfer object for user/folder rows
        user = transfer.user

        if transfer.path is not None:
            user_path = user + transfer.path
            row_data = self.paths[user_path]
        else:
            row_data = self.users[user]

        _row_iter, child_transfers = row_data

        for i_transfer in child_transfers:
            self.select_transfer(i_transfer)

    def select_transfer(self, transfer, select_user=False):

        if transfer.filename is not None and transfer not in self.selected_transfers:
            self.selected_transfers[transfer] = None

        if select_user and transfer.user not in self.selected_users:
            self.selected_users[transfer.user] = None

        self.select_child_transfers(transfer)

    def new_transfer_notification(self, finished=False):
        if self.window.current_page_id != self.transfer_page.id:
            self.window.notebook.request_tab_changed(self.transfer_page, is_important=finished)

    def on_file_search(self, *_args):

        transfer = next(iter(self.selected_transfers), None)

        if not transfer:
            return

        self.window.search_entry.set_text(transfer.filename.rsplit("\\", 1)[1])
        self.window.change_main_page(self.window.search_page)

    def translate_status(self, status):

        translated_status = self.statuses.get(status)

        if translated_status:
            return translated_status

        return status

    def update_num_users_files(self):
        self.user_counter.set_text(humanize(len(self.users)))
        self.file_counter.set_text(humanize(len(self.transfer_list)))

    def update_model(self, transfer=None, update_parent=True):

        if self.window.current_page_id != self.transfer_page.id:
            # No need to do unnecessary work if transfers are not visible
            return

        update_counters = False

        if transfer is not None:
            update_counters = self.update_specific(transfer)

        elif self.transfer_list:
            for transfer_i in reversed(self.transfer_list):
                row_added = self.update_specific(transfer_i)

                if row_added and not update_counters:
                    update_counters = True

        if update_parent:
            self.update_parent_rows(transfer)

        if update_counters:
            self.update_num_users_files()

        self.tree_view.redraw()

    def update_parent_rows(self, transfer=None):

        # Show tab description if necessary
        self.container.get_parent().set_visible(bool(self.transfer_list))

        if self.grouping_mode == "ungrouped":
            return

        if transfer is not None:
            username = transfer.user

            if self.paths:
                user_path = username + self.get_transfer_folder_path(transfer)
                user_path_iter, user_path_child_transfers = self.paths[user_path]
                self.update_parent_row(user_path_iter, user_path_child_transfers, user_path=user_path)

            user_iter, user_child_transfers = self.users[username]
            self.update_parent_row(user_iter, user_child_transfers, username=username)

        else:
            if self.paths:
                for user_path, (user_path_iter, child_transfers) in self.paths.copy().items():
                    self.update_parent_row(user_path_iter, child_transfers, user_path=user_path)

            for username, (user_iter, child_transfers) in self.users.copy().items():
                self.update_parent_row(user_iter, child_transfers, username=username)

    @staticmethod
    def get_hqueue_position(queue_position):
        return str(queue_position) if queue_position > 0 else ""

    @staticmethod
    def get_hsize(current_byte_offset, size):
        return f"{human_size(current_byte_offset)} / {human_size(size)}"

    @staticmethod
    def get_hspeed(speed):
        return human_speed(speed) if speed > 0 else ""

    @staticmethod
    def get_helapsed(elapsed):
        return human_length(elapsed) if elapsed > 0 else ""

    @staticmethod
    def get_hleft(left):
        return human_length(left) if left >= 1 else ""

    @staticmethod
    def get_percent(current_byte_offset, size):
        return min(((100 * int(current_byte_offset)) / int(size)), 100) if size > 0 else 100

    def update_parent_row(self, iterator, child_transfers, username=None, user_path=None):

        speed = 0.0
        total_size = current_byte_offset = 0
        elapsed = 0
        parent_status = "Finished"

        if not child_transfers:
            # Remove parent row if no children are present anymore
            if user_path:
                transfer = self.tree_view.get_row_value(iterator, "transfer_data")
                _user_iter, user_child_transfers = self.users[transfer.user]
                user_child_transfers.remove(transfer)
                del self.paths[user_path]
            else:
                del self.users[username]

            self.tree_view.remove_row(iterator)
            return

        for transfer in child_transfers:
            status = transfer.status

            if status == "Transferring":
                # "Transferring" status always has the highest priority
                parent_status = status
                speed += transfer.speed or 0

            elif parent_status in self.deprioritized_statuses and status != "Finished":
                # "Finished" status always has the lowest priority
                parent_status = status

            if status == "Filtered" and transfer.filename:
                # We don't want to count filtered files when calculating the progress
                continue

            elapsed += transfer.time_elapsed or 0
            total_size += transfer.size or 0
            current_byte_offset += transfer.current_byte_offset or 0

        transfer = self.tree_view.get_row_value(iterator, "transfer_data")
        total_size = min(total_size, UINT64_LIMIT)
        current_byte_offset = min(current_byte_offset, UINT64_LIMIT)

        if transfer.status != parent_status:
            self.tree_view.set_row_value(iterator, "status", self.translate_status(parent_status))
            transfer.status = parent_status

        if transfer.speed != speed:
            self.tree_view.set_row_value(iterator, "speed", self.get_hspeed(speed))
            self.tree_view.set_row_value(iterator, "speed_data", speed)
            transfer.speed = speed

        if transfer.time_elapsed != elapsed:
            left = (total_size - current_byte_offset) / speed if speed and total_size > current_byte_offset else 0
            self.tree_view.set_row_value(iterator, "time_elapsed", self.get_helapsed(elapsed))
            self.tree_view.set_row_value(iterator, "time_left", self.get_hleft(left))
            self.tree_view.set_row_value(iterator, "time_elapsed_data", elapsed)
            self.tree_view.set_row_value(iterator, "time_left_data", left)
            transfer.time_elapsed = elapsed

        if transfer.current_byte_offset != current_byte_offset:
            self.tree_view.set_row_value(iterator, "percent", self.get_percent(current_byte_offset, total_size))
            self.tree_view.set_row_value(iterator, "size", self.get_hsize(current_byte_offset, total_size))
            self.tree_view.set_row_value(iterator, "current_bytes_data", current_byte_offset)
            transfer.current_byte_offset = current_byte_offset

        if transfer.size != total_size:
            self.tree_view.set_row_value(iterator, "percent", self.get_percent(current_byte_offset, total_size))
            self.tree_view.set_row_value(iterator, "size", self.get_hsize(current_byte_offset, total_size))
            self.tree_view.set_row_value(iterator, "size_data", total_size)
            transfer.size = total_size

    def update_specific(self, transfer):

        current_byte_offset = transfer.current_byte_offset or 0
        queue_position = transfer.queue_position or 0
        status = transfer.status or ""

        if transfer.modifier and status == "Queued":
            # Priority status
            status = status + f" ({transfer.modifier})"

        size = transfer.size or 0
        speed = transfer.speed or 0
        elapsed = transfer.time_elapsed or 0
        left = transfer.time_left or 0
        iterator = transfer.iterator

        # Modify old transfer
        if iterator is not None:
            translated_status = self.translate_status(status)

            if self.tree_view.get_row_value(iterator, "status") != translated_status:
                self.tree_view.set_row_value(iterator, "status", translated_status)

            if self.tree_view.get_row_value(iterator, "speed_data") != speed:
                self.tree_view.set_row_value(iterator, "speed", self.get_hspeed(speed))
                self.tree_view.set_row_value(iterator, "speed_data", speed)

            if self.tree_view.get_row_value(iterator, "time_elapsed_data") != elapsed:
                self.tree_view.set_row_value(iterator, "time_elapsed", self.get_helapsed(elapsed))
                self.tree_view.set_row_value(iterator, "time_left", self.get_hleft(left))
                self.tree_view.set_row_value(iterator, "time_elapsed_data", elapsed)
                self.tree_view.set_row_value(iterator, "time_left_data", left)

            if self.tree_view.get_row_value(iterator, "current_bytes_data") != current_byte_offset:
                self.tree_view.set_row_value(iterator, "percent", self.get_percent(current_byte_offset, size))
                self.tree_view.set_row_value(iterator, "size", self.get_hsize(current_byte_offset, size))
                self.tree_view.set_row_value(iterator, "current_bytes_data", current_byte_offset)

            elif self.tree_view.get_row_value(iterator, "size_data") != size:
                self.tree_view.set_row_value(iterator, "percent", self.get_percent(current_byte_offset, size))
                self.tree_view.set_row_value(iterator, "size", self.get_hsize(current_byte_offset, size))
                self.tree_view.set_row_value(iterator, "size_data", size)

            if self.tree_view.get_row_value(iterator, "queue_position_data") != queue_position:
                self.tree_view.set_row_value(iterator, "queue_position", self.get_hqueue_position(queue_position))
                self.tree_view.set_row_value(iterator, "queue_position_data", queue_position)

            return False

        expand_user = False
        expand_folder = False
        user_iterator = None
        user_path_iterator = None
        parent_iterator = None

        user = transfer.user
        shortfn = transfer.filename.split("\\")[-1]
        original_path = path = self.get_transfer_folder_path(transfer)

        if config.sections["ui"]["reverse_file_paths"]:
            path = self.path_separator.join(reversed(path.split(self.path_separator)))

        if self.grouping_mode != "ungrouped":
            # Group by folder or user

            empty_int = 0
            empty_str = ""

            if user not in self.users:
                # Create parent if it doesn't exist
                iterator = self.tree_view.add_row(
                    [
                        user,
                        empty_str,
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
                        Transfer(user=user),  # Dummy Transfer object
                        self.row_id
                    ], select_row=False
                )

                if self.grouping_mode == "folder_grouping":
                    expand_user = True
                else:
                    expand_user = self.expand_button.get_active()

                self.row_id += 1
                self.users[user] = (iterator, [])

            user_iterator, user_child_transfers = self.users[user]

            if self.grouping_mode == "folder_grouping":
                # Group by folder

                # Make sure we don't add files to the wrong user in the TreeView
                user_path = user + original_path

                if user_path not in self.paths:
                    path_transfer = Transfer(user=user, path=original_path)  # Dummy Transfer object
                    iterator = self.tree_view.add_row(
                        [
                            user,
                            path,
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
                            path_transfer,
                            self.row_id
                        ], select_row=False, parent_iterator=user_iterator
                    )
                    user_child_transfers.append(path_transfer)
                    expand_folder = self.expand_button.get_active()
                    self.row_id += 1
                    self.paths[user_path] = (iterator, [])

                user_path_iterator, user_path_child_transfers = self.paths[user_path]
                parent_iterator = user_path_iterator
                user_path_child_transfers.append(transfer)

                # Group by folder, path not visible in file rows
                path = ""
            else:
                parent_iterator = user_iterator
                user_child_transfers.append(transfer)
        else:
            # No grouping
            if user not in self.users:
                self.users[user] = (None, [])

            user_iterator, user_child_transfers = self.users[user]
            user_child_transfers.append(transfer)

        # Add a new transfer
        row = [
            user,
            path,
            get_file_type_icon_name(shortfn),
            shortfn,
            self.translate_status(status),
            self.get_hqueue_position(queue_position),
            self.get_percent(current_byte_offset, size),
            self.get_hsize(current_byte_offset, size),
            self.get_hspeed(speed),
            self.get_helapsed(elapsed),
            self.get_hleft(left),
            size,
            current_byte_offset,
            speed,
            queue_position,
            elapsed,
            left,
            transfer,
            self.row_id
        ]

        transfer.iterator = self.tree_view.add_row(row, select_row=False, parent_iterator=parent_iterator)
        self.row_id += 1

        if expand_user:
            self.tree_view.expand_row(user_iterator)

        if expand_folder:
            self.tree_view.expand_row(user_path_iterator)

        return True

    def clear_model(self):

        self.users.clear()
        self.paths.clear()
        self.selected_transfers.clear()
        self.selected_users.clear()
        self.tree_view.clear()

        for transfer in self.transfer_list:
            transfer.iterator = None

    def get_transfer_folder_path(self, _transfer):
        # Implemented in subclasses
        raise NotImplementedError

    def retry_selected_transfers(self):
        # Implemented in subclasses
        raise NotImplementedError

    def abort_selected_transfers(self):
        # Implemented in subclasses
        raise NotImplementedError

    def clear_selected_transfers(self):
        # Implemented in subclasses
        raise NotImplementedError

    def abort_transfer(self, transfer, status_message=None, update_parent=True):
        if status_message is not None:
            self.update_model(transfer, update_parent=update_parent)

    def abort_transfers(self, _transfers, _status_message=None):
        self.update_parent_rows()

    def clear_transfer(self, transfer, update_parent=True):

        if transfer.iterator is None:
            return

        user = transfer.user

        if self.grouping_mode == "folder_grouping":
            user_path = user + self.get_transfer_folder_path(transfer)
            _user_path_iter, user_path_child_transfers = self.paths[user_path]
            user_path_child_transfers.remove(transfer)
        else:
            _user_iter, user_child_transfers = self.users[user]
            user_child_transfers.remove(transfer)

            if self.grouping_mode == "ungrouped" and not user_child_transfers:
                del self.users[user]

        self.tree_view.remove_row(transfer.iterator)
        transfer.iterator = None

        if update_parent:
            self.update_parent_rows(transfer)
            self.update_num_users_files()

    def clear_transfers(self, *_args):
        self.update_parent_rows()
        self.update_num_users_files()

    def add_popup_menu_user(self, popup, user):

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
                popup = UserPopupMenu(self.window.application, username=user, tab_name="transfers")
                self.add_popup_menu_user(popup, user)
                self.popup_menu_users.add_items((">" + user, popup))
                self.popup_menu_users.update_model()
            return

        # Single user, add items directly to "User Actions" submenu
        user = next(iter(self.selected_users), None)
        self.popup_menu_users.setup_user_menu(user)
        self.add_popup_menu_user(self.popup_menu_users, user)

    def on_expand_tree(self, *_args):

        expanded = self.expand_button.get_active()

        if expanded:
            icon_name = "go-up-symbolic"
            self.tree_view.expand_all_rows()

        else:
            icon_name = "go-down-symbolic"
            self.tree_view.collapse_all_rows()

            if self.grouping_mode == "folder_grouping":
                self.tree_view.expand_root_rows()

        self.expand_icon.set_property("icon-name", icon_name)

        config.sections["transfers"][f"{self.type}sexpanded"] = expanded
        config.write_configuration()

    def on_toggle_tree(self, action, state):

        mode = state.get_string()
        active = mode != "ungrouped"
        popover = self.grouping_button.get_popover()

        if popover is not None:
            popover.set_visible(False)

        if GTK_API_VERSION >= 4:
            # Ensure buttons are flat in libadwaita
            css_class_function = add_css_class if active else remove_css_class
            css_class_function(widget=self.grouping_button.get_parent(), css_class="linked")

        config.sections["transfers"][f"group{self.type}s"] = mode
        self.tree_view.set_show_expanders(active)
        self.expand_button.set_visible(active)

        self.grouping_mode = mode

        self.clear_model()
        self.tree_view.has_tree = active
        self.tree_view.create_model()

        if self.transfer_list:
            self.update_model()

        action.set_state(state)

    def on_popup_menu(self, menu, _widget):

        self.select_transfers()
        menu.set_num_selected_files(len(self.selected_transfers))

        self.populate_popup_menu_users()

    def on_file_path_tooltip(self, treeview, iterator):
        transfer = treeview.get_row_value(iterator, "transfer_data")
        return transfer.filename or transfer.path

    def on_row_activated(self, _treeview, iterator, _column_id):

        if self.tree_view.collapse_row(iterator):
            return

        if self.tree_view.expand_row(iterator):
            return

        self.select_transfers()
        action = config.sections["transfers"][f"{self.type}_doubleclick"]

        if action == 1:    # Send to Player
            self.on_play_files()

        elif action == 2:  # Open in File Manager
            self.on_open_file_manager()

        elif action == 3:  # Search
            self.on_file_search()

        elif action == 4:  # Pause / Abort
            self.abort_selected_transfers()

        elif action == 5:  # Clear
            self.clear_selected_transfers()

        elif action == 6:  # Resume / Retry
            self.retry_selected_transfers()

        elif action == 7:  # Browse Folder
            self.on_browse_folder()

    def on_select_user_transfers(self, *args):

        if not self.selected_users:
            return

        selected_user = args[-1]
        _user_iterator, user_child_transfers = self.users[selected_user]

        self.tree_view.unselect_all_rows()

        for transfer in user_child_transfers:
            iterator = transfer.iterator

            if iterator:
                self.tree_view.select_row(iterator, should_scroll=False)
                continue

            # Dummy Transfer object for folder rows
            user_path = transfer.user + transfer.path
            user_path_data = self.paths.get(user_path)

            if not user_path_data:
                continue

            _user_path_iter, user_path_child_transfers = user_path_data

            for i_transfer in user_path_child_transfers:
                self.tree_view.select_row(i_transfer.iterator, should_scroll=False)

    def on_abort_transfers_accelerator(self, *_args):
        """ T: abort transfer """

        self.select_transfers()
        self.abort_selected_transfers()
        return True

    def on_retry_transfers_accelerator(self, *_args):
        """ R: retry transfers """

        self.select_transfers()
        self.retry_selected_transfers()
        return True

    def on_clear_transfers_accelerator(self, *_args):
        """ Delete: clear transfers """

        self.select_transfers()
        self.clear_selected_transfers()
        return True

    def on_file_properties_accelerator(self, *_args):
        """ Alt+Return: show file properties dialog """

        self.select_transfers()
        self.on_file_properties()
        return True

    def on_file_properties(self, *_args):

        data = []
        selected_size = 0

        for transfer in self.selected_transfers:
            fullname = transfer.filename
            filename = fullname.split("\\")[-1]
            directory = fullname.rsplit("\\", 1)[0]
            file_size = transfer.size
            selected_size += file_size

            data.append({
                "user": transfer.user,
                "fn": fullname,
                "filename": filename,
                "directory": directory,
                "path": transfer.path,
                "queue_position": transfer.queue_position,
                "speed": transfer.speed,
                "size": file_size,
                "file_attributes": transfer.file_attributes
            })

        if data:
            if self.file_properties is None:
                self.file_properties = FileProperties(self.window.application, download_button=False)

            self.file_properties.update_properties(data, total_size=selected_size)
            self.file_properties.show()

    def on_copy_url(self, *_args):
        # Implemented in subclasses
        raise NotImplementedError

    def on_copy_dir_url(self, *_args):
        # Implemented in subclasses
        raise NotImplementedError

    def on_copy_file_path(self, *_args):

        transfer = next(iter(self.selected_transfers), None)

        if transfer:
            clipboard.copy_text(transfer.filename)

    def on_play_files(self, *_args):
        # Implemented in subclasses
        raise NotImplementedError

    def on_open_file_manager(self, *_args):
        # Implemented in subclasses
        raise NotImplementedError

    def on_browse_folder(self, *_args):
        # Implemented in subclasses
        raise NotImplementedError

    def on_retry_transfer(self, *_args):
        self.select_transfers()
        self.retry_selected_transfers()

    def on_abort_transfer(self, *_args):
        self.select_transfers()
        self.abort_selected_transfers()

    def on_clear_transfer(self, *_args):
        self.select_transfers()
        self.clear_selected_transfers()
