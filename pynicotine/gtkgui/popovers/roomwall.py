# COPYRIGHT (C) 2020-2022 Nicotine+ Contributors
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

from pynicotine import slskmessages
from pynicotine.gtkgui.widgets.textview import TextView
from pynicotine.gtkgui.widgets.theme import update_widget_visuals
from pynicotine.gtkgui.widgets.ui import UserInterface


class RoomWall(UserInterface):

    def __init__(self, frame, core, room):

        super().__init__("ui/popovers/roomwall.ui")
        (
            self.list_view,
            self.message_entry,
            self.message_view,
            self.popover
        ) = self.widgets

        self.frame = frame
        self.core = core
        self.room = room
        self.room_wall_textview = TextView(self.message_view)

        room.room_wall_button.set_popover(self.popover)

    def update_message_list(self):

        tickers = self.room.tickers.get_tickers()
        self.room_wall_textview.append_line(
            "%s" % ("\n".join(["> [%s] %s" % (user, msg) for user, msg in tickers])),
            showstamp=False, scroll=False)

    def clear_room_wall_message(self, update_list=True):

        entry_text = self.message_entry.get_text()
        self.message_entry.set_text("")

        self.room.tickers.remove_ticker(self.core.login_username)
        self.room_wall_textview.clear()

        if update_list:
            self.core.queue.append(slskmessages.RoomTickerSet(self.room.room, ""))
            self.update_message_list()

        return entry_text

    def on_set_room_wall_message(self, *_args):

        entry_text = self.clear_room_wall_message(update_list=False)
        self.core.queue.append(slskmessages.RoomTickerSet(self.room.room, entry_text))

        if entry_text:
            login_username = self.core.login_username
            self.room_wall_textview.append_line("[%s] %s" % (login_username, entry_text), showstamp=False, scroll=False)

        self.update_message_list()

    def on_icon_pressed(self, _entry, icon_pos, *_args):

        if icon_pos == Gtk.EntryIconPosition.PRIMARY:
            self.on_set_room_wall_message()
            return

        self.clear_room_wall_message()

    def update_visuals(self):

        for widget in list(self.__dict__.values()):
            update_widget_visuals(widget)

    def on_show(self, popover, param):

        if not popover.get_property(param.name):
            return

        self.room_wall_textview.clear()
        self.update_message_list()

        login_username = self.core.login_username

        for user, msg in self.room.tickers.get_tickers():
            if user == login_username:
                self.message_entry.set_text(msg)
                self.message_entry.select_region(0, -1)
