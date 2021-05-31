# COPYRIGHT (C) 2020-2021 Nicotine+ Team
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

from gi.repository import Gdk
from gi.repository import Gtk

from pynicotine import slskmessages
from pynicotine.config import config
from pynicotine.gtkgui.utils import append_line
from pynicotine.gtkgui.utils import load_ui_elements
from pynicotine.gtkgui.widgets.dialogs import generic_dialog
from pynicotine.gtkgui.widgets.theme import update_widget_visuals


class RoomWall:

    def __init__(self, frame, room):

        self.frame = frame
        self.room = room

        load_ui_elements(self, os.path.join(self.frame.gui_dir, "ui", "dialogs", "roomwall.ui"))

        self.RoomWallDialog = generic_dialog(
            parent=frame.MainWindow,
            content_box=self.Main,
            quit_callback=self.hide,
            title=_("Room Wall"),
            width=800,
            height=600
        )

    def on_set_room_wall_message(self, *args):

        result = self.RoomWallEntry.get_text()
        self.RoomWallEntry.set_text("")

        self.frame.np.queue.append(slskmessages.RoomTickerSet(self.room.room, result))

        if result:
            login = config.sections["server"]["login"]
            self.room.tickers.remove_ticker(login)
            self.room.tickers.add_ticker(login, result)

        tickers = self.room.tickers.get_tickers()
        self.RoomWallList.get_buffer().set_text("")
        append_line(self.RoomWallList, "%s" % ("\n".join(["[%s] %s" % (user, msg) for (user, msg) in tickers])), showstamp=False, scroll=False)

    def update_visuals(self):

        for widget in list(self.__dict__.values()):
            update_widget_visuals(widget)

    def hide(self, *args):

        self.RoomWallList.get_buffer().set_text("")
        self.RoomWallDialog.hide()
        return True

    def show(self):

        tickers = self.room.tickers.get_tickers()
        append_line(self.RoomWallList, "%s" % ("\n".join(["[%s] %s" % (user, msg) for (user, msg) in tickers])), showstamp=False, scroll=False)

        login = config.sections["server"]["login"]

        for user, msg in tickers:
            if user == login:
                self.RoomWallEntry.set_text(msg)
                self.RoomWallEntry.select_region(0, -1)

        self.RoomWallDialog.present_with_time(Gdk.CURRENT_TIME)

        if Gtk.get_major_version == 3:
            self.RoomWallDialog.get_window().set_functions(
                Gdk.WMFunction.RESIZE | Gdk.WMFunction.MOVE | Gdk.WMFunction.CLOSE
            )


class Tickers:

    def __init__(self):

        self.messages = []

    def add_ticker(self, user, message):

        message = message.replace("\n", " ")
        self.messages.insert(0, [user, message])

    def remove_ticker(self, user):

        for i in range(len(self.messages)):
            if self.messages[i][0] == user:
                del self.messages[i]
                return

    def get_tickers(self):
        return self.messages

    def set_ticker(self, msgs):
        self.messages = msgs
