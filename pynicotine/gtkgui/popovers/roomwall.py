# COPYRIGHT (C) 2020-2023 Nicotine+ Contributors
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

    def __init__(self, window, room):

        (
            self.container,
            self.message_entry,
            self.message_view_container,
        ) = ui.load(scope=self, path="popovers/roomwall.ui")

        super().__init__(
            window=window,
            content_box=self.container,
            show_callback=self.on_show,
            width=600,
            height=500
        )

        self.room = room
        self.message_view = TextView(self.message_view_container, editable=False, vertical_margin=4,
                                     pixels_above_lines=3, pixels_below_lines=3)

        room.room_wall_button.set_popover(self.widget)

    def update_message_list(self):

        tickers = self.room.tickers.get_tickers()
        self.message_view.append_line("\n".join([f"> [{user}] {msg}" for user, msg in tickers]))

    def clear_room_wall_message(self, update_list=True):

        entry_text = self.message_entry.get_text()
        self.message_entry.set_text("")

        self.room.tickers.remove_ticker(core.login_username)
        self.message_view.clear()

        if update_list:
            self.room.tickers.set_ticker("")
            self.update_message_list()

        return entry_text

    def on_set_room_wall_message(self, *_args):

        entry_text = self.clear_room_wall_message(update_list=False)
        self.room.tickers.set_ticker(entry_text)

        if entry_text:
            user = core.login_username
            self.message_view.append_line(f"> [{user}] {entry_text}")

        self.update_message_list()

    def on_icon_pressed(self, _entry, icon_pos, *_args):

        if icon_pos == Gtk.EntryIconPosition.PRIMARY:
            self.on_set_room_wall_message()
            return

        self.clear_room_wall_message()

    def on_show(self, *_args):

        self.message_view.clear()
        self.update_message_list()

        login_username = core.login_username

        for user, msg in self.room.tickers.get_tickers():
            if user == login_username:
                self.message_entry.set_text(msg)
                self.message_entry.select_region(0, -1)
