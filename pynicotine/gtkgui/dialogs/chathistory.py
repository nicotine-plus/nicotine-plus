# SPDX-FileCopyrightText: 2022-2025 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import time

from collections import deque

from gi.repository import GObject

from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.gtkgui.widgets import ui
from pynicotine.gtkgui.widgets.accelerator import Accelerator
from pynicotine.gtkgui.widgets.dialogs import Dialog
from pynicotine.gtkgui.widgets.dialogs import EntryDialog
from pynicotine.gtkgui.widgets.dialogs import OptionDialog
from pynicotine.gtkgui.widgets.popupmenu import PopupMenu
from pynicotine.gtkgui.widgets.theme import USER_STATUS_ICON_NAMES
from pynicotine.gtkgui.widgets.treeview import TreeView
from pynicotine.logfacility import log
from pynicotine.slskmessages import UserStatus
from pynicotine.utils import encode_path


class ChatHistory(Dialog):

    def __init__(self, application):

        (
            self.container,
            self.list_container,
            self.search_entry
        ) = ui.load(scope=self, path="dialogs/chathistory.ui")

        super().__init__(
            parent=application.window,
            content_box=self.container,
            show_callback=self.on_show,
            title=_("Chat History"),
            width=960,
            height=700
        )
        application.add_window(self.widget)

        self.list_view = TreeView(
            application.window, parent=self.list_container, activate_row_callback=self.on_show_user,
            search_entry=self.search_entry,
            columns={
                "status": {
                    "column_type": "icon",
                    "title": _("Status"),
                    "width": 25,
                    "hide_header": True
                },
                "user": {
                    "column_type": "text",
                    "title": _("User"),
                    "width": 175,
                    "iterator_key": True
                },
                "latest_message": {
                    "column_type": "text",
                    "title": _("Latest Message"),
                    "sort_column": "timestamp_data",
                    "default_sort_type": "descending",
                    "tabular": True
                },

                # Hidden data columns
                "timestamp_data": {"data_type": GObject.TYPE_UINT64}
            }
        )

        self.popup_menu = PopupMenu(application, self.list_view.widget)
        self.popup_menu.add_items(
            ("#" + _("_Open Chat"), self.on_show_user),
            ("", None),
            ("#" + _("Delete Chat Log…"), self.on_delete_chat_log)
        )

        Accelerator("<Primary>f", self.widget, self.on_search_accelerator)
        Accelerator("Down", self.search_entry, self.on_focus_list_view_accelerator)

        self.load_users()

        for event_name, callback in (
            ("server-login", self.server_login),
            ("server-disconnect", self.server_disconnect),
            ("user-status", self.user_status)
        ):
            events.connect(event_name, callback)

    def destroy(self):

        self.popup_menu.destroy()
        self.list_view.destroy()

        super().destroy()

    def server_login(self, msg):
        if msg.success and self.is_visible():
            self.update_user_statuses()

    def server_disconnect(self, *_args):
        if self.is_visible():
            self.update_user_statuses()

    @staticmethod
    def load_user(file_path):
        """Reads the username and latest message from a given log file path.

        Usernames are first extracted from the file name. In case the
        extracted username contains underscores, attempt to fetch the
        original username from logged messages, since illegal filename
        characters are substituted with underscores.
        """

        username = os.path.basename(file_path[:-4]).decode("utf-8", "replace")
        is_safe_username = ("_" not in username)
        login_username = config.sections["server"]["login"]
        timestamp = os.path.getmtime(file_path)

        read_num_lines = 1 if is_safe_username else 25
        latest_message = None

        with open(file_path, "rb") as lines:
            lines = deque(lines, read_num_lines)

            for line in lines:
                try:
                    line = line.decode("utf-8")

                except UnicodeDecodeError:
                    line = line.decode("latin-1")

                if latest_message is None:
                    latest_message = line

                    if is_safe_username:
                        break

                    username_chars = set(username.replace("_", ""))

                if login_username in line:
                    continue

                if " [" not in line or "] " not in line:
                    continue

                start = line.find(" [") + 2
                end = line.find("] ", start)
                line_username_len = (end - start)

                if len(username) != line_username_len:
                    continue

                line_username = line[start:end]

                if username == line_username:
                    # Nothing to do, username is already correct
                    break

                if username_chars.issubset(line_username):
                    username = line_username
                    break

        return username, latest_message, timestamp

    def load_users(self):

        self.list_view.freeze()

        try:
            with os.scandir(encode_path(log.private_chat_folder_path)) as entries:
                for entry in entries:
                    if not entry.is_file() or not entry.name.endswith(b".log"):
                        continue

                    try:
                        username, latest_message, timestamp = self.load_user(entry.path)

                    except OSError:
                        continue

                    if latest_message is not None:
                        self.update_user(username, latest_message.strip(), timestamp)

        except OSError:
            pass

        self.list_view.unfreeze()

    def remove_user(self, username):

        iterator = self.list_view.iterators.get(username)

        if iterator is not None:
            self.list_view.remove_row(iterator)

        if not self.list_view.iterators:
            self.list_container.set_visible(False)

    def update_user(self, username, message, timestamp=None):

        self.remove_user(username)

        if not timestamp:
            timestamp_format = config.sections["logging"]["log_timestamp"]
            timestamp = time.time()
            h_timestamp = time.strftime(timestamp_format)
            message = f"{h_timestamp} [{username}] {message}"

        iterator = self.list_view.add_row([
            "",
            username,
            message,
            int(timestamp)
        ], select_row=False)

        if self.is_visible():
            self.set_user_status_icon(username, iterator)

        if not self.list_container.get_visible():
            self.list_container.set_visible(True)

    def set_user_status_icon(self, username, iterator):

        # We don't watch all historic users for status updates due to
        # the amount of server traffic a large history would generate
        if username in core.privatechat.users:
            status_icon_name = USER_STATUS_ICON_NAMES[core.users.statuses.get(username, UserStatus.OFFLINE)]
        else:
            status_icon_name = ""  # Blank icon to indicate chat tab closed

        if status_icon_name != self.list_view.get_row_value(iterator, "status"):
            self.list_view.set_row_value(iterator, "status", status_icon_name)

    def update_user_statuses(self):

        for iterator in self.list_view.iterators.values():
            username = self.list_view.get_row_value(iterator, "user")
            self.set_user_status_icon(username, iterator)

    def user_status(self, msg):

        username = msg.user
        iterator = self.list_view.iterators.get(username)

        if iterator is None:
            return

        self.set_user_status_icon(username, iterator)

    def on_show_user(self, *_args):

        for iterator in self.list_view.get_selected_rows():
            username = self.list_view.get_row_value(iterator, "user")

            core.privatechat.show_user(username)
            self.close()
            return

    def on_message_user_response(self, dialog, _response_id, _data):

        username = dialog.get_entry_value().strip()

        if not username:
            return

        core.privatechat.show_user(username)
        self.close()

    def on_message_user(self, *_args):

        EntryDialog(
            parent=self,
            title=_("Message User"),
            message=_("Enter the name of the user you want to message:"),
            action_button_label=_("_Message User"),
            callback=self.on_message_user_response,
            droplist=sorted(core.buddies.users)
        ).present()

    def on_delete_chat_log_response(self, _dialog, _response_id, username):
        log.delete_log(log.private_chat_folder_path, username)
        self.remove_user(username)

    def on_delete_chat_log(self, *_args):

        for iterator in self.list_view.get_selected_rows():
            username = self.list_view.get_row_value(iterator, "user")

            OptionDialog(
                parent=self.parent,
                title=_("Delete Logged Messages?"),
                message=_("Do you really want to permanently delete all logged messages for this user?"),
                destructive_response_id="ok",
                callback=self.on_delete_chat_log_response,
                callback_data=username
            ).present()
            return

    def on_search_accelerator(self, *_args):
        """Ctrl+F - Search users."""

        self.search_entry.grab_focus()
        return True

    def on_focus_list_view_accelerator(self, *_args):
        """Down - Focus list view."""

        if not self.list_container.get_visible():
            return False

        self.list_view.grab_focus()
        return True

    def on_show(self, *_args):
        self.update_user_statuses()
