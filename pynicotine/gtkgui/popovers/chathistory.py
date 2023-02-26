# COPYRIGHT (C) 2022 Nicotine+ Contributors
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

import glob
import os
import time

from collections import deque

from pynicotine.config import config
from pynicotine.core import core
from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.widgets.accelerator import Accelerator
from pynicotine.gtkgui.widgets.popover import Popover
from pynicotine.gtkgui.widgets.textentry import CompletionEntry
from pynicotine.gtkgui.widgets.theme import add_css_class
from pynicotine.gtkgui.widgets.treeview import TreeView
from pynicotine.gtkgui.widgets.ui import UserInterface
from pynicotine.utils import encode_path


class ChatHistory(Popover):

    def __init__(self, window):

        ui_template = UserInterface(scope=self, path="popovers/chathistory.ui")
        (
            self.container,
            self.list_container,
            self.search_entry
        ) = ui_template.widgets

        super().__init__(
            window=window,
            content_box=self.container,
            width=1000,
            height=700
        )

        self.list_view = TreeView(
            window, parent=self.list_container, activate_row_callback=self.on_show_user,
            columns={
                "user": {
                    "column_type": "text",
                    "title": _("User"),
                    "width": 175
                },
                "latest_message": {
                    "column_type": "text",
                    "title": _("Latest Message")
                }
            }
        )
        self.list_view.set_search_entry(self.search_entry)

        Accelerator("<Primary>f", self.widget, self.on_search_accelerator)
        CompletionEntry(window.private_entry, self.list_view.model, column=0)

        if GTK_API_VERSION >= 4:
            add_css_class(widget=window.private_history_button.get_first_child(), css_class="arrow-button")

        window.private_history_button.set_popover(self.widget)
        self.load_users()

    def load_user(self, file_path):
        """ Reads the username and latest message from a given log file path. Usernames are
        first extracted from the file name. In case the extracted username contains underscores,
        attempt to fetch the original username from logged messages, since illegal filename
        characters are substituted with underscores. """

        username = os.path.basename(file_path[:-4]).decode("utf-8", "replace")
        is_safe_username = ("_" not in username)
        login_username = config.sections["server"]["login"]

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

        return username, latest_message

    def load_users(self):

        log_path = os.path.join(config.sections["logging"]["privatelogsdir"], "*.log")
        user_logs = sorted(glob.glob(encode_path(log_path)), key=os.path.getmtime)

        for file_path in user_logs:
            try:
                username, latest_message = self.load_user(file_path)

                if latest_message is not None:
                    self.update_user(username, latest_message.strip())

            except OSError:
                continue

    def remove_user(self, username):

        iterator = self.list_view.iterators.get(username)

        if iterator is not None:
            self.list_view.remove_row(iterator)

    def update_user(self, username, message, add_timestamp=False):

        self.remove_user(username)

        if add_timestamp:
            timestamp_format = config.sections["logging"]["log_timestamp"]
            timestamp = time.strftime(timestamp_format)
            message = f"{timestamp} {message}"

        self.list_view.add_row([username, message], select_row=False, prepend=True)

    def on_show_user(self, *_args):

        for iterator in self.list_view.get_selected_rows():
            username = self.list_view.get_row_value(iterator, "user")

            core.privatechat.show_user(username)
            self.close(use_transition=False)
            return

    def on_search_accelerator(self, *_args):
        """ Ctrl+F: Search users """

        self.search_entry.grab_focus()
        return True
