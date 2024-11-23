# COPYRIGHT (C) 2020-2024 Nicotine+ Contributors
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

from gi.repository import Gtk

from pynicotine.core import core
from pynicotine.gtkgui.widgets import ui
from pynicotine.gtkgui.widgets.popover import Popover
from pynicotine.gtkgui.widgets.textview import TextView


class RoomWall(Popover):

    def __init__(self, window):

        (
            self.container,
            self.message_entry,
            self.message_view_container,
        ) = ui.load(scope=self, path="popovers/roomwall.ui")

        super().__init__(
            window=window,
            content_box=self.container,
            show_callback=self._on_show,
            width=650,
            height=500
        )

        self.room = None
        self.message_view = TextView(self.message_view_container, editable=False, vertical_margin=4,
                                     pixels_above_lines=3, pixels_below_lines=3)

    def destroy(self):
        self.message_view.destroy()
        super().destroy()

    def _update_message_list(self):

        tickers = core.chatrooms.joined_rooms[self.room].tickers
        newline = "\n"
        messages = [f"> [{user}] {msg.replace(newline, ' ')}" for user, msg in reversed(list(tickers.items()))]

        self.message_view.append_line(newline.join(messages))
        self.message_view.place_cursor_at_line(0)

    def on_set_room_wall_message(self, *_args):

        entry_text = self.message_entry.get_text()
        core.chatrooms.request_update_ticker(self.room, entry_text)

        core.chatrooms.joined_rooms[self.room].tickers.pop(core.users.login_username, None)
        self.message_view.clear()

        if entry_text:
            self.message_view.append_line(f"> [{core.users.login_username}] {entry_text}")
            self.message_entry.set_text("")

        self._update_message_list()

    def on_icon_pressed(self, _entry, icon_pos, *_args):

        if icon_pos == Gtk.EntryIconPosition.SECONDARY:
            # Clear message
            self.message_entry.set_text("")

        self.on_set_room_wall_message()

    def _on_show(self, *_args):

        self.message_view.clear()
        self._update_message_list()

        login_username = core.users.login_username
        message = core.chatrooms.joined_rooms[self.room].tickers.get(login_username, "")

        self.message_entry.set_text(message)
        self.message_entry.select_region(0, -1)
