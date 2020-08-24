# COPYRIGHT (C) 2020 Nicotine+ Team
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

from gi.repository import Gtk as gtk

from pynicotine import slskmessages
from pynicotine.gtkgui.utils import AppendLine


class RoomWall:

    def __init__(self, frame, room):

        self.frame = frame
        self.room = room

        builder = gtk.Builder()
        builder.set_translation_domain('nicotine')
        builder.add_from_file(os.path.join(os.path.dirname(os.path.realpath(__file__)), "ui", "roomwall.ui"))

        self.RoomWall = builder.get_object("RoomWall")
        builder.connect_signals(self)

        for i in builder.get_objects():
            try:
                self.__dict__[gtk.Buildable.get_name(i)] = i
            except TypeError:
                pass

        self.RoomWall.set_transient_for(frame.MainWindow)

        self.RoomWall.connect("destroy", self.hide)
        self.RoomWall.connect("destroy-event", self.hide)
        self.RoomWall.connect("delete-event", self.hide)
        self.RoomWall.connect("delete_event", self.hide)

    def OnSetRoomWallMessage(self, widget):
        result = self.RoomWallEntry.get_text()
        self.RoomWallEntry.set_text("")

        config = self.frame.np.config.sections
        room_name = self.room.room

        self.frame.np.queue.put(slskmessages.RoomTickerSet(room_name, result))

        self.RoomWallList.get_buffer().set_text("")

        login = config["server"]["login"]

        if result:
            AppendLine(self.RoomWallList, "[%s] %s" % (login, result), showstamp=False, scroll=False)

        tickers = self.room.Tickers.get_tickers()
        AppendLine(self.RoomWallList, "%s" % ("\n".join(["[%s] %s" % (user, msg) for (user, msg) in tickers if not user == login])), showstamp=False, scroll=False)

    def hide(self, w=None, event=None):
        self.RoomWallList.get_buffer().set_text("")
        self.RoomWall.hide()
        return True

    def show(self):
        tickers = self.room.Tickers.get_tickers()
        AppendLine(self.RoomWallList, "%s" % ("\n".join(["[%s] %s" % (user, msg) for (user, msg) in tickers])), showstamp=False, scroll=False)
        self.RoomWall.show()


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
