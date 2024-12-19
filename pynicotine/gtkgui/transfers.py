# COPYRIGHT (C) 2020-2024 Nicotine+ Contributors
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

import os

from itertools import islice

from gi.repository import GObject
from gi.repository import Gtk

from pynicotine.config import config
from pynicotine.core import core
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
from pynicotine.slskmessages import FileListMessage
from pynicotine.slskmessages import TransferRejectReason
from pynicotine.transfers import Transfer
from pynicotine.transfers import TransferStatus
from pynicotine.utils import UINT64_LIMIT
from pynicotine.utils import human_length
from pynicotine.utils import human_size
from pynicotine.utils import human_speed
from pynicotine.utils import humanize


class Transfers:

    STATUSES = {
        TransferStatus.QUEUED: _("Queued"),
        f"{TransferStatus.QUEUED} (prioritized)": _("Queued (prioritized)"),
        f"{TransferStatus.QUEUED} (privileged)": _("Queued (privileged)"),
        TransferStatus.GETTING_STATUS: _("Getting status"),
        TransferStatus.TRANSFERRING: _("Transferring"),
        TransferStatus.CONNECTION_CLOSED: _("Connection closed"),
        TransferStatus.CONNECTION_TIMEOUT: _("Connection timeout"),
        TransferStatus.USER_LOGGED_OFF: _("User logged off"),
        TransferStatus.PAUSED: _("Paused"),
        TransferStatus.CANCELLED: _("Cancelled"),
        TransferStatus.FINISHED: _("Finished"),
        TransferStatus.FILTERED: _("Filtered"),
        TransferStatus.DOWNLOAD_FOLDER_ERROR: _("Download folder error"),
        TransferStatus.LOCAL_FILE_ERROR: _("Local file error"),
        TransferRejectReason.BANNED: _("Banned"),
        TransferRejectReason.FILE_NOT_SHARED: _("File not shared"),
        TransferRejectReason.PENDING_SHUTDOWN: _("Pending shutdown"),
        TransferRejectReason.FILE_READ_ERROR: _("File read error")
    }
    STATUS_PRIORITIES = {
        TransferStatus.FILTERED: 0,
        TransferStatus.FINISHED: 1,
        TransferStatus.PAUSED: 2,
        TransferStatus.CANCELLED: 3,
        TransferStatus.QUEUED: 4,
        f"{TransferStatus.QUEUED} (prioritized)": 4,
        f"{TransferStatus.QUEUED} (privileged)": 4,
        TransferStatus.USER_LOGGED_OFF: 5,
        TransferStatus.CONNECTION_CLOSED: 6,
        TransferStatus.CONNECTION_TIMEOUT: 7,
        TransferRejectReason.FILE_NOT_SHARED: 8,
        TransferRejectReason.PENDING_SHUTDOWN: 9,
        TransferRejectReason.FILE_READ_ERROR: 10,
        TransferStatus.LOCAL_FILE_ERROR: 11,
        TransferStatus.DOWNLOAD_FOLDER_ERROR: 12,
        TransferRejectReason.BANNED: 13,
        TransferStatus.GETTING_STATUS: 9998,
        TransferStatus.TRANSFERRING: 9999
    }
    PENDING_ITERATOR_REBUILD = 0
    PENDING_ITERATOR_ADD = 1
    PENDING_ITERATORS = {PENDING_ITERATOR_REBUILD, PENDING_ITERATOR_ADD}
    UNKNOWN_STATUS_PRIORITY = 1000

    path_separator = path_label = retry_label = abort_label = None
    transfer_page = user_counter = file_counter = expand_button = expand_icon = grouping_button = status_label = None

    def __init__(self, window, transfer_type):

        (
            self.clear_all_button,
            self.clear_all_label,
            self.container,
            self.tree_container
        ) = ui.load(scope=self, path=f"{transfer_type}s.ui")

        self.window = window
        self.type = transfer_type

        if GTK_API_VERSION >= 4:
            inner_button = next(iter(self.clear_all_button))
            self.clear_all_button.set_has_frame(False)
            self.clear_all_label.set_mnemonic_widget(inner_button)

        self.transfer_list = {}
        self.users = {}
        self.paths = {}
        self.pending_folder_rows = set()
        self.pending_user_rows = set()
        self.grouping_mode = None
        self.row_id = 0
        self.file_properties = None
        self.initialized = False

        # Use dict instead of list for faster membership checks
        self.selected_users = {}
        self.selected_transfers = {}

        self.tree_view = TreeView(
            window, parent=self.tree_container, name=transfer_type,
            multi_select=True, persistent_sort=True, activate_row_callback=self.on_row_activated,
            delete_accelerator_callback=self.on_remove_transfers_accelerator,
            columns={
                # Visible columns
                "user": {
                    "column_type": "text",
                    "title": _("User"),
                    "width": 200,
                    "sensitive_column": "is_sensitive_data"
                },
                "path": {
                    "column_type": "text",
                    "title": self.path_label,
                    "width": 200,
                    "expand_column": True,
                    "tooltip_callback": self.on_file_path_tooltip,
                    "sensitive_column": "is_sensitive_data"
                },
                "file_type": {
                    "column_type": "icon",
                    "title": _("File Type"),
                    "width": 40,
                    "hide_header": True,
                    "sensitive_column": "is_sensitive_data"
                },
                "filename": {
                    "column_type": "text",
                    "title": _("Filename"),
                    "width": 200,
                    "expand_column": True,
                    "tooltip_callback": self.on_file_path_tooltip,
                    "sensitive_column": "is_sensitive_data"
                },
                "status": {
                    "column_type": "text",
                    "title": _("Status"),
                    "width": 140,
                    "sensitive_column": "is_sensitive_data"
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
                    "width": 90,
                    "sensitive_column": "is_sensitive_data"
                },
                "size": {
                    "column_type": "number",
                    "title": _("Size"),
                    "width": 180,
                    "sort_column": "size_data",
                    "sensitive_column": "is_sensitive_data"
                },
                "speed": {
                    "column_type": "number",
                    "title": _("Speed"),
                    "width": 100,
                    "sort_column": "speed_data",
                    "sensitive_column": "is_sensitive_data"
                },
                "time_elapsed": {
                    "column_type": "number",
                    "title": _("Time Elapsed"),
                    "width": 140,
                    "sort_column": "time_elapsed_data",
                    "sensitive_column": "is_sensitive_data"
                },
                "time_left": {
                    "column_type": "number",
                    "title": _("Time Left"),
                    "width": 140,
                    "sort_column": "time_left_data",
                    "sensitive_column": "is_sensitive_data"
                },

                # Hidden data columns
                "size_data": {"data_type": GObject.TYPE_UINT64},
                "current_bytes_data": {"data_type": GObject.TYPE_UINT64},
                "speed_data": {"data_type": GObject.TYPE_UINT64},
                "queue_position_data": {"data_type": GObject.TYPE_UINT},
                "time_elapsed_data": {"data_type": GObject.TYPE_INT},
                "time_left_data": {"data_type": GObject.TYPE_UINT64},
                "is_sensitive_data": {"data_type": GObject.TYPE_BOOLEAN},
                "transfer_data": {"data_type": GObject.TYPE_PYOBJECT},
                "id_data": {
                    "data_type": GObject.TYPE_INT,
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
            inner_button = next(iter(self.grouping_button))
            add_css_class(widget=inner_button, css_class="image-button")

            # Workaround for GTK bug where clicks stop working after clicking inside popover once
            if os.environ.get("GDK_BACKEND") == "broadway":
                popover = list(self.grouping_button)[-1]
                popover.set_has_arrow(False)

        self.expand_button.connect("toggled", self.on_expand_tree)
        self.expand_button.set_active(config.sections["transfers"][f"{transfer_type}sexpanded"])

        self.popup_menu_users = UserPopupMenu(window.application, tab_name="transfers")
        self.popup_menu_clear = PopupMenu(window.application)
        self.popup_menu_clear.set_menu_button(self.clear_all_button)

        self.popup_menu_copy = PopupMenu(window.application)
        self.popup_menu_copy.add_items(
            ("#" + _("Copy _File Path"), self.on_copy_file_path),
            ("#" + _("Copy _URL"), self.on_copy_url),
            ("#" + _("Copy Folder U_RL"), self.on_copy_folder_url)
        )

        self.popup_menu = FilePopupMenu(
            window.application, parent=self.tree_view.widget, callback=self.on_popup_menu
        )
        if not self.window.application.isolated_mode:
            self.popup_menu.add_items(
                ("#" + _("_Open File"), self.on_open_file),
                ("#" + _("Open in File _Manager"), self.on_open_file_manager)
            )
        self.popup_menu.add_items(
            ("#" + _("F_ile Properties"), self.on_file_properties),
            ("", None),
            ("#" + self.retry_label, self.on_retry_transfer),
            ("#" + self.abort_label, self.on_abort_transfer),
            ("#" + _("Remove"), self.on_remove_transfer),
            ("", None),
            ("#" + _("View User _Profile"), self.on_user_profile),
            ("#" + _("_Browse Folder"), self.on_browse_folder),
            ("#" + _("_Search"), self.on_file_search),
            ("", None),
            (">" + _("Copy"), self.popup_menu_copy),
            (">" + _("Clear All"), self.popup_menu_clear),
            (">" + _("User Actions"), self.popup_menu_users)
        )

    def destroy(self):

        self.clear_model()
        self.tree_view.destroy()
        self.popup_menu.destroy()
        self.popup_menu_users.destroy()
        self.popup_menu_clear.destroy()
        self.popup_menu_copy.destroy()

        self.__dict__.clear()

    def on_focus(self, *_args):

        self.update_model()
        self.window.notebook.remove_tab_changed(self.transfer_page)

        if self.container.get_parent().get_visible():
            self.tree_view.grab_focus()
            return True

        return False

    def init_transfers(self, transfer_list):

        self.transfer_list = transfer_list

        for transfer in transfer_list:
            # Tab highlights are only used when transfers are appended, but we
            # won't create a transfer row until the tab is active. To prevent
            # spurious highlights when a previously added transfer changes, but
            # the tab wasn't activated yet (iterator is None), mark the iterator
            # as pending.
            transfer.iterator = self.PENDING_ITERATOR_REBUILD

        self.container.get_parent().set_visible(bool(transfer_list))

    def select_transfers(self):

        self.selected_transfers.clear()
        self.selected_users.clear()

        for iterator in self.tree_view.get_selected_rows():
            transfer = self.tree_view.get_row_value(iterator, "transfer_data")
            self.select_transfer(transfer, select_user=True)

    def select_child_transfers(self, transfer):

        if transfer.virtual_path is not None:
            return

        # Dummy Transfer object for user/folder rows
        user = transfer.username
        folder_path = self.get_transfer_folder_path(transfer)

        if folder_path is not None:
            user_folder_path = user + folder_path
            row_data = self.paths[user_folder_path]
        else:
            row_data = self.users[user]

        _row_iter, child_transfers = row_data

        for i_transfer in child_transfers:
            self.select_transfer(i_transfer)

    def select_transfer(self, transfer, select_user=False):

        if transfer.virtual_path is not None and transfer not in self.selected_transfers:
            self.selected_transfers[transfer] = None

        if select_user and transfer.username not in self.selected_users:
            self.selected_users[transfer.username] = None

        self.select_child_transfers(transfer)

    def on_file_search(self, *_args):

        transfer = next(iter(self.selected_transfers), None)

        if not transfer:
            return

        _folder_path, _separator, basename = transfer.virtual_path.rpartition("\\")

        self.window.search_entry.set_text(basename)
        self.window.change_main_page(self.window.search_page)

    def translate_status(self, status):

        translated_status = self.STATUSES.get(status)

        if translated_status:
            return translated_status

        return status

    def update_limits(self):
        """Underline status bar bandwidth labels when alternative speed limits
        are active."""

        if config.sections["transfers"][f"use_{self.type}_speed_limit"] == "alternative":
            add_css_class(self.status_label, "underline")
            return

        remove_css_class(self.status_label, "underline")

    def update_num_users_files(self):
        self.user_counter.set_text(humanize(len(self.users)))
        self.file_counter.set_text(humanize(len(self.transfer_list)))

    def update_model(self, transfer=None, update_parent=True):

        if self.window.current_page_id != self.transfer_page.id:
            if transfer is not None and transfer.iterator is None:
                self.window.notebook.request_tab_changed(self.transfer_page)
                transfer.iterator = self.PENDING_ITERATOR_ADD

            # No need to do unnecessary work if transfers are not visible
            return

        has_disabled_sorting = False
        has_selected_parent = False
        update_counters = False
        use_reverse_file_path = config.sections["ui"]["reverse_file_paths"]

        if transfer is not None:
            update_counters = self.update_specific(transfer, use_reverse_file_path=use_reverse_file_path)

        elif self.transfer_list:
            for transfer_i in self.transfer_list:
                select_parent = (not has_selected_parent and transfer_i.iterator == self.PENDING_ITERATOR_ADD)
                row_added = self.update_specific(transfer_i, select_parent, use_reverse_file_path)

                if select_parent:
                    has_selected_parent = True

                if not row_added:
                    continue

                update_counters = True

                if not has_disabled_sorting:
                    # Optimization: disable sorting while adding rows
                    self.tree_view.freeze()
                    has_disabled_sorting = True

        if update_parent:
            self.update_parent_rows(transfer)

        if update_counters:
            self.update_num_users_files()

        if has_disabled_sorting:
            self.tree_view.unfreeze()

        if not self.initialized:
            self.on_expand_tree()
            self.initialized = True

        self.tree_view.redraw()

    def _update_pending_parent_rows(self):

        for user_folder_path in self.pending_folder_rows:
            if user_folder_path not in self.paths:
                continue

            user_folder_path_iter, user_folder_path_child_transfers = self.paths[user_folder_path]
            self.update_parent_row(
                user_folder_path_iter, user_folder_path_child_transfers, user_folder_path=user_folder_path)

        for username in self.pending_user_rows:
            if username not in self.users:
                continue

            user_iter, user_child_transfers = self.users[username]
            self.update_parent_row(user_iter, user_child_transfers, username=username)

        self.pending_folder_rows.clear()
        self.pending_user_rows.clear()

    def update_parent_rows(self, transfer=None):

        if self.grouping_mode == "ungrouped":
            return

        if transfer is not None:
            username = transfer.username

            if self.paths:
                user_folder_path = username + self.get_transfer_folder_path(transfer)
                self.pending_folder_rows.add(user_folder_path)

            self.pending_user_rows.add(username)
            return

        if self.paths:
            for user_folder_path, (user_folder_path_iter, child_transfers) in self.paths.copy().items():
                self.update_parent_row(user_folder_path_iter, child_transfers, user_folder_path=user_folder_path)

        for username, (user_iter, child_transfers) in self.users.copy().items():
            self.update_parent_row(user_iter, child_transfers, username=username)

    @staticmethod
    def get_hqueue_position(queue_position):
        return str(queue_position) if queue_position > 0 else ""

    @staticmethod
    def get_hsize(current_byte_offset, size):

        if current_byte_offset >= size:
            return human_size(size)

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

        if current_byte_offset > size or size <= 0:
            return 100

        # Multiply first to avoid decimals
        return (100 * current_byte_offset) // size

    def update_parent_row(self, iterator, child_transfers, username=None, user_folder_path=None):

        speed = 0.0
        total_size = current_byte_offset = 0
        elapsed = 0
        parent_status = TransferStatus.FINISHED

        if not child_transfers:
            # Remove parent row if no children are present anymore
            if user_folder_path:
                transfer = self.tree_view.get_row_value(iterator, "transfer_data")
                _user_iter, user_child_transfers = self.users[transfer.username]
                user_child_transfers.remove(transfer)
                del self.paths[user_folder_path]
            else:
                del self.users[username]

            self.tree_view.remove_row(iterator)

            if not self.tree_view.iterators:
                # Show tab description
                self.container.get_parent().set_visible(False)

            self.update_num_users_files()
            return

        for transfer in child_transfers:
            status = transfer.status

            if status == TransferStatus.TRANSFERRING:
                # "Transferring" status always has the highest priority
                parent_status = status
                speed += transfer.speed

            elif parent_status in self.STATUS_PRIORITIES:
                parent_status_priority = self.STATUS_PRIORITIES[parent_status]
                status_priority = self.STATUS_PRIORITIES.get(status, self.UNKNOWN_STATUS_PRIORITY)

                if status_priority > parent_status_priority:
                    parent_status = status

            if status == TransferStatus.FILTERED and transfer.virtual_path:
                # We don't want to count filtered files when calculating the progress
                continue

            elapsed += transfer.time_elapsed
            total_size += transfer.size
            current_byte_offset += transfer.current_byte_offset or 0

        transfer = self.tree_view.get_row_value(iterator, "transfer_data")

        if total_size > UINT64_LIMIT:  # pylint: disable=consider-using-min-builtin
            total_size = UINT64_LIMIT

        if current_byte_offset > UINT64_LIMIT:  # pylint: disable=consider-using-min-builtin
            current_byte_offset = UINT64_LIMIT

        should_update_size = False
        column_ids = []
        column_values = []

        if transfer.status != parent_status:
            column_ids.append("status")
            column_values.append(self.translate_status(parent_status))

            if parent_status == TransferStatus.USER_LOGGED_OFF:
                column_ids.append("is_sensitive_data")
                column_values.append(False)

            elif transfer.status == TransferStatus.USER_LOGGED_OFF:
                column_ids.append("is_sensitive_data")
                column_values.append(True)

            transfer.status = parent_status

        if transfer.speed != speed:
            column_ids.extend(("speed", "speed_data"))
            column_values.extend((self.get_hspeed(speed), speed))

            transfer.speed = speed

        if transfer.time_elapsed != elapsed:
            left = (total_size - current_byte_offset) / speed if speed and total_size > current_byte_offset else 0
            column_ids.extend(("time_elapsed", "time_left", "time_elapsed_data", "time_left_data"))
            column_values.extend((self.get_helapsed(elapsed), self.get_hleft(left), elapsed, left))

            transfer.time_elapsed = elapsed

        if transfer.current_byte_offset != current_byte_offset:
            column_ids.append("current_bytes_data")
            column_values.append(current_byte_offset)

            transfer.current_byte_offset = current_byte_offset
            should_update_size = True

        if transfer.size != total_size:
            column_ids.append("size_data")
            column_values.append(total_size)

            transfer.size = total_size
            should_update_size = True

        if should_update_size:
            column_ids.extend(("percent", "size"))
            column_values.extend((
                self.get_percent(current_byte_offset, total_size),
                self.get_hsize(current_byte_offset, total_size)
            ))

        if column_ids:
            self.tree_view.set_row_values(iterator, column_ids, column_values)

    def update_specific(self, transfer, select_parent=False, use_reverse_file_path=True):

        current_byte_offset = transfer.current_byte_offset or 0
        queue_position = transfer.queue_position
        status = transfer.status or ""

        if transfer.modifier and status == TransferStatus.QUEUED:
            # Priority status
            status += f" ({transfer.modifier})"

        translated_status = self.translate_status(status)
        size = transfer.size
        speed = transfer.speed
        elapsed = transfer.time_elapsed
        left = transfer.time_left
        iterator = transfer.iterator

        # Modify old transfer
        if iterator and iterator not in self.PENDING_ITERATORS:
            should_update_size = False
            old_translated_status = self.tree_view.get_row_value(iterator, "status")
            column_ids = []
            column_values = []

            if old_translated_status != translated_status:
                column_ids.append("status")
                column_values.append(translated_status)

                if transfer.status == TransferStatus.USER_LOGGED_OFF:
                    column_ids.append("is_sensitive_data")
                    column_values.append(False)

                elif old_translated_status == _("User logged off"):
                    column_ids.append("is_sensitive_data")
                    column_values.append(True)

            if self.tree_view.get_row_value(iterator, "speed_data") != speed:
                column_ids.extend(("speed", "speed_data"))
                column_values.extend((self.get_hspeed(speed), speed))

            if self.tree_view.get_row_value(iterator, "time_elapsed_data") != elapsed:
                column_ids.extend(("time_elapsed", "time_left", "time_elapsed_data", "time_left_data"))
                column_values.extend((self.get_helapsed(elapsed), self.get_hleft(left), elapsed, left))

            if self.tree_view.get_row_value(iterator, "current_bytes_data") != current_byte_offset:
                column_ids.append("current_bytes_data")
                column_values.append(current_byte_offset)
                should_update_size = True

            if self.tree_view.get_row_value(iterator, "size_data") != size:
                column_ids.append("size_data")
                column_values.append(size)
                should_update_size = True

            if self.tree_view.get_row_value(iterator, "queue_position_data") != queue_position:
                column_ids.extend(("queue_position", "queue_position_data"))
                column_values.extend((self.get_hqueue_position(queue_position), queue_position))

            if should_update_size:
                column_ids.extend(("percent", "size"))
                column_values.extend((
                    self.get_percent(current_byte_offset, size),
                    self.get_hsize(current_byte_offset, size)
                ))

            if column_ids:
                self.tree_view.set_row_values(iterator, column_ids, column_values)

            return False

        expand_allowed = self.initialized
        expand_user = False
        expand_folder = False
        user_iterator = None
        user_folder_path_iterator = None
        parent_iterator = None
        select_iterator = None

        user = transfer.username
        folder_path, _separator, basename = transfer.virtual_path.rpartition("\\")
        original_folder_path = folder_path = self.get_transfer_folder_path(transfer)
        is_sensitive = (status != TransferStatus.USER_LOGGED_OFF)

        if use_reverse_file_path:
            parts = folder_path.split(self.path_separator)
            parts.reverse()
            folder_path = self.path_separator.join(parts)

        if not self.tree_view.iterators:
            # Hide tab description
            self.container.get_parent().set_visible(True)

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
                        translated_status,
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
                        is_sensitive,
                        Transfer(user, status=status),  # Dummy Transfer object
                        self.row_id
                    ], select_row=False
                )

                if expand_allowed:
                    expand_user = self.grouping_mode == "folder_grouping" or self.expand_button.get_active()

                self.row_id += 1
                self.users[user] = (iterator, [])

            user_iterator, user_child_transfers = self.users[user]
            parent_iterator = user_iterator

            if select_parent:
                select_iterator = parent_iterator

            if self.grouping_mode == "folder_grouping":
                # Group by folder

                # Make sure we don't add files to the wrong user in the TreeView
                user_folder_path = user + original_folder_path

                if user_folder_path not in self.paths:
                    path_transfer = Transfer(  # Dummy Transfer object
                        user, folder_path=original_folder_path, status=status
                    )
                    iterator = self.tree_view.add_row(
                        [
                            user,
                            folder_path,
                            empty_str,
                            empty_str,
                            translated_status,
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
                            is_sensitive,
                            path_transfer,
                            self.row_id
                        ], select_row=False, parent_iterator=user_iterator
                    )
                    user_child_transfers.append(path_transfer)
                    expand_folder = expand_allowed and self.expand_button.get_active()
                    self.row_id += 1
                    self.paths[user_folder_path] = (iterator, [])

                user_folder_path_iterator, user_folder_path_child_transfers = self.paths[user_folder_path]
                parent_iterator = user_folder_path_iterator
                user_folder_path_child_transfers.append(transfer)

                if select_parent and (expand_user or self.tree_view.is_row_expanded(user_iterator)):
                    select_iterator = parent_iterator

                # Group by folder, path not visible in file rows
                folder_path = ""
            else:
                user_child_transfers.append(transfer)
        else:
            # No grouping
            if user not in self.users:
                self.users[user] = (None, [])

            user_iterator, user_child_transfers = self.users[user]
            user_child_transfers.append(transfer)

        # Add a new transfer
        transfer.iterator = self.tree_view.add_row([
            user,
            folder_path,
            get_file_type_icon_name(basename),
            basename,
            translated_status,
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
            is_sensitive,
            transfer,
            self.row_id
        ], select_row=False, parent_iterator=parent_iterator)
        self.row_id += 1

        if expand_user and user_iterator is not None:
            self.tree_view.expand_row(user_iterator)

        if expand_folder and user_folder_path_iterator is not None:
            self.tree_view.expand_row(user_folder_path_iterator)

        if select_iterator and (not self.tree_view.is_row_selected(select_iterator)
                                or self.tree_view.get_num_selected_rows() != 1):
            # Select parent row of newly added transfer, and scroll to it.
            # Unselect any other rows to prevent accidental actions on previously
            # selected transfers.
            self.tree_view.unselect_all_rows()
            self.tree_view.select_row(select_iterator, expand_rows=False)

        return True

    def clear_model(self):

        self.initialized = False
        self.users.clear()
        self.paths.clear()
        self.pending_folder_rows.clear()
        self.pending_user_rows.clear()
        self.selected_transfers.clear()
        self.selected_users.clear()
        self.tree_view.clear()
        self.row_id = 0

        for transfer in self.transfer_list:
            transfer.iterator = self.PENDING_ITERATOR_REBUILD

    def get_transfer_folder_path(self, _transfer):
        # Implemented in subclasses
        raise NotImplementedError

    def retry_selected_transfers(self):
        # Implemented in subclasses
        raise NotImplementedError

    def abort_selected_transfers(self):
        # Implemented in subclasses
        raise NotImplementedError

    def remove_selected_transfers(self):
        # Implemented in subclasses
        raise NotImplementedError

    def abort_transfer(self, transfer, status_message=None, update_parent=True):
        if status_message is not None and status_message != TransferStatus.QUEUED:
            self.update_model(transfer, update_parent=update_parent)

    def abort_transfers(self, _transfers, _status_message=None):
        self.update_parent_rows()

    def clear_transfer(self, transfer, update_parent=True):

        iterator = transfer.iterator
        transfer.iterator = None

        if not iterator or iterator in self.PENDING_ITERATORS:
            return

        user = transfer.username

        if self.grouping_mode == "folder_grouping":
            user_folder_path = user + self.get_transfer_folder_path(transfer)
            _user_folder_path_iter, user_folder_path_child_transfers = self.paths[user_folder_path]
            user_folder_path_child_transfers.remove(transfer)
        else:
            _user_iter, user_child_transfers = self.users[user]
            user_child_transfers.remove(transfer)

            if self.grouping_mode == "ungrouped" and not user_child_transfers:
                del self.users[user]

        self.tree_view.remove_row(iterator)

        if update_parent:
            self.update_parent_rows(transfer)
            self.update_num_users_files()

        if not self.tree_view.iterators:
            # Show tab description
            self.container.get_parent().set_visible(False)

    def clear_transfers(self, *_args):
        self.update_parent_rows()

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

        # Multiple users, create submenus for some of them
        if len(self.selected_users) > 1:
            for user in islice(self.selected_users, 20):
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

        if not self.expand_button.get_visible():
            return

        expanded = self.expand_button.get_active()

        if expanded:
            icon_name = "view-restore-symbolic"
            self.tree_view.expand_all_rows()
        else:
            icon_name = "view-fullscreen-symbolic"
            self.tree_view.collapse_all_rows()

            if self.grouping_mode == "folder_grouping":
                self.tree_view.expand_root_rows()

        icon_args = (Gtk.IconSize.BUTTON,) if GTK_API_VERSION == 3 else ()  # pylint: disable=no-member
        self.expand_icon.set_from_icon_name(icon_name, *icon_args)

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
        return transfer.virtual_path or self.get_transfer_folder_path(transfer)

    def on_row_activated(self, _treeview, iterator, _column_id):

        if self.tree_view.collapse_row(iterator):
            return

        if self.tree_view.expand_row(iterator):
            return

        self.select_transfers()
        action = config.sections["transfers"][f"{self.type}_doubleclick"]

        if self.window.application.isolated_mode and action in {1, 2}:
            # External applications not available in isolated_mode mode
            return

        if action == 1:    # Open File
            self.on_open_file()

        elif action == 2:  # Open in File Manager
            self.on_open_file_manager()

        elif action == 3:  # Search
            self.on_file_search()

        elif action == 4:  # Pause / Abort
            self.abort_selected_transfers()

        elif action == 5:  # Remove
            self.remove_selected_transfers()

        elif action == 6:  # Resume / Retry
            self.retry_selected_transfers()

        elif action == 7:  # Browse Folder
            self.on_browse_folder()

    def on_select_user_transfers(self, _action, _parameter, selected_user):

        if not self.selected_users:
            return

        _user_iterator, user_child_transfers = self.users[selected_user]

        self.tree_view.unselect_all_rows()

        for transfer in user_child_transfers:
            iterator = transfer.iterator

            if iterator:
                self.tree_view.select_row(iterator, should_scroll=False)
                continue

            # Dummy Transfer object for folder rows
            user_folder_path = transfer.username + self.get_transfer_folder_path(transfer)
            user_folder_path_data = self.paths.get(user_folder_path)

            if not user_folder_path_data:
                continue

            _user_folder_path_iter, user_folder_path_child_transfers = user_folder_path_data

            for i_transfer in user_folder_path_child_transfers:
                self.tree_view.select_row(i_transfer.iterator, should_scroll=False)

    def on_abort_transfers_accelerator(self, *_args):
        """T - abort transfer."""

        self.select_transfers()
        self.abort_selected_transfers()
        return True

    def on_retry_transfers_accelerator(self, *_args):
        """R - retry transfers."""

        self.select_transfers()
        self.retry_selected_transfers()
        return True

    def on_remove_transfers_accelerator(self, *_args):
        """Delete - remove transfers."""

        self.select_transfers()
        self.remove_selected_transfers()
        return True

    def on_file_properties_accelerator(self, *_args):
        """Alt+Return - show file properties dialog."""

        self.select_transfers()
        self.on_file_properties()
        return True

    def on_user_profile(self, *_args):

        username = next(iter(self.selected_users), None)

        if username:
            core.userinfo.show_user(username)

    def on_file_properties(self, *_args):

        data = []
        selected_size = 0
        selected_length = 0

        for transfer in self.selected_transfers:
            username = transfer.username
            watched_user = core.users.watched.get(username)
            speed = 0
            file_path = transfer.virtual_path
            file_size = transfer.size
            file_attributes = transfer.file_attributes
            _bitrate, length, *_unused = FileListMessage.parse_file_attributes(file_attributes)
            selected_size += file_size

            if length:
                selected_length += length

            folder_path, _separator, basename = file_path.rpartition("\\")

            if watched_user is not None:
                speed = watched_user.upload_speed or 0

            data.append({
                "user": transfer.username,
                "file_path": file_path,
                "basename": basename,
                "virtual_folder_path": folder_path,
                "real_folder_path": transfer.folder_path,
                "queue_position": transfer.queue_position,
                "speed": speed,
                "size": file_size,
                "file_attributes": file_attributes,
                "country_code": core.users.countries.get(username)
            })

        if data:
            if self.file_properties is None:
                self.file_properties = FileProperties(self.window.application)

            self.file_properties.update_properties(data, selected_size, selected_length)
            self.file_properties.present()

    def on_copy_url(self, *_args):
        # Implemented in subclasses
        raise NotImplementedError

    def on_copy_folder_url(self, *_args):
        # Implemented in subclasses
        raise NotImplementedError

    def on_copy_file_path(self, *_args):

        transfer = next(iter(self.selected_transfers), None)

        if transfer:
            clipboard.copy_text(transfer.virtual_path)

    def on_open_file(self, *_args):
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

    def on_remove_transfer(self, *_args):
        self.select_transfers()
        self.remove_selected_transfers()
