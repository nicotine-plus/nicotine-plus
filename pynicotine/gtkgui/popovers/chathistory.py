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

from collections import deque

from pynicotine.config import config
from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.widgets.textentry import CompletionEntry
from pynicotine.gtkgui.widgets.theme import update_widget_visuals
from pynicotine.gtkgui.widgets.treeview import TreeView
from pynicotine.gtkgui.widgets.ui import UserInterface
from pynicotine.utils import encode_path


class ChatHistory(UserInterface):

    def __init__(self, frame, core):

        super().__init__("ui/popovers/chathistory.ui")
        self.list_container, self.popover = self.widgets

        self.frame = frame
        self.core = core

        self.list_view = TreeView(
            frame, parent=self.list_container, activate_row_callback=self.on_row_activated,
            columns=[
                {"column_id": "user", "column_type": "text", "title": _("User"), "width": 175,
                 "sort_column": 0},
                {"column_id": "latest_message", "column_type": "text", "title": _("Latest Message"), "sort_column": 1}
            ]
        )

        CompletionEntry(frame.private_entry, self.list_view.model, column=0)

        if GTK_API_VERSION >= 4:
            frame.private_history_button.get_first_child().get_style_context().add_class("arrow-button")

        frame.private_history_button.set_popover(self.popover)
        self.load_users()

    def load_users(self):

        log_path = os.path.join(config.sections["logging"]["privatelogsdir"], "*.log")
        user_logs = sorted(glob.glob(encode_path(log_path)), key=os.path.getmtime, reverse=True)

        for file_path in user_logs:
            username = os.path.basename(file_path[:-4]).decode("utf-8", "replace")

            try:
                with open(file_path, "rb") as lines:
                    lines = deque(lines, 1)

                    if not lines:
                        continue

                    try:
                        line = lines[0].decode("utf-8")

                    except UnicodeDecodeError:
                        line = lines[0].decode("latin-1")

                self.update_user(username, line.strip())

            except OSError:
                pass

    def remove_user(self, username):

        iterator = self.list_view.iterators.get(username)

        if iterator is not None:
            self.list_view.remove_row(iterator)

    def update_user(self, username, message):
        self.remove_user(username)
        self.list_view.add_row([username, message], select_row=False)

    def update_visuals(self):
        for widget in list(self.__dict__.values()):
            update_widget_visuals(widget)

    def on_row_activated(self, list_view, iterator):
        username = list_view.get_row_value(iterator, 0)

        self.core.privatechats.show_user(username)
        self.popover.hide()
