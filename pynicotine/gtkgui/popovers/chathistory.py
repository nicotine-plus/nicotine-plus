# COPYRIGHT (C) 2022 Nicotine+ Team
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

from gi.repository import Gtk

from pynicotine.config import config
from pynicotine.gtkgui.widgets.textentry import CompletionEntry
from pynicotine.gtkgui.widgets.theme import update_widget_visuals
from pynicotine.gtkgui.widgets.treeview import initialise_columns
from pynicotine.gtkgui.widgets.ui import UserInterface


class ChatHistory(UserInterface):

    def __init__(self, frame, core):

        super().__init__("ui/popovers/chathistory.ui")
        self.list_view, self.popover = self.widgets

        self.frame = frame
        self.core = core
        self.iters = {}

        self.model = Gtk.ListStore(str, str)
        self.list_view.set_model(self.model)

        self.column_numbers = list(range(self.model.get_n_columns()))
        self.cols = initialise_columns(
            frame, None, self.list_view,
            ["user", _("User"), 175, "text", None],
            ["latest_message", _("Latest Message"), -1, "text", None]
        )
        self.cols["user"].set_sort_column_id(0)
        self.cols["latest_message"].set_sort_column_id(1)

        CompletionEntry(frame.private_entry, self.model, column=0)

        if Gtk.get_major_version() == 4:
            frame.private_history_button.get_first_child().get_style_context().add_class("arrow-button")

        frame.private_history_button.set_popover(self.popover)
        self.load_users()

    def load_users(self):

        log_path = os.path.join(config.sections["logging"]["privatelogsdir"], "*.log")
        user_logs = sorted(glob.glob(log_path.encode("utf-8")), key=os.path.getmtime)

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

        iterator = self.iters.get(username)

        if iterator is not None:
            self.model.remove(iterator)

    def update_user(self, username, message):

        self.remove_user(username)

        self.iters[username] = self.model.insert_with_valuesv(
            0, self.column_numbers,
            [username, message]
        )

    def update_visuals(self):
        for widget in list(self.__dict__.values()):
            update_widget_visuals(widget)

    def on_row_activated(self, _treeview, path, _column):

        iterator = self.model.get_iter(path)
        username = self.model.get_value(iterator, 0)

        self.core.privatechats.show_user(username)
        self.popover.hide()
