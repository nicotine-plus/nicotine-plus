# COPYRIGHT (C) 2020 Nicotine+ Team
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2016-2018 Mutnick <mutnick@techie.com>
# COPYRIGHT (C) 2008-2011 Quinox <quinox@users.sf.net>
# COPYRIGHT (C) 2006-2009 Daelstorm <daelstorm@gmail.com>
# COPYRIGHT (C) 2009 Hedonist <ak@sensi.org>
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

from pynicotine import slskmessages
from pynicotine.gtkgui.utils import load_ui_elements
from pynicotine.gtkgui.utils import update_widget_visuals


class RoomList:

    def __init__(self, frame):

        # Build the window
        self.frame = frame

        load_ui_elements(self, os.path.join(self.frame.gui_dir, "ui", "roomlist.ui"))

        self.search_iter = None
        self.query = ""
        self.room_model = self.RoomsList.get_model()

        self.AcceptPrivateRoom.set_active(self.frame.np.config.sections["server"]["private_chatrooms"])
        self.AcceptPrivateRoom.connect("toggled", self.on_toggle_accept_private_room)

    def on_search_room(self, widget):

        if self.room_model is not self.RoomsList.get_model():
            self.room_model = self.RoomsList.get_model()
            self.search_iter = self.room_model.get_iter_first()

        room = self.SearchRooms.get_text().lower()

        if not room:
            return

        if self.query == room:
            if self.search_iter is None:
                self.search_iter = self.room_model.get_iter_first()
            else:
                self.search_iter = self.room_model.iter_next(self.search_iter)
        else:
            self.search_iter = self.room_model.get_iter_first()
            self.query = room

        while self.search_iter:

            room_match, size = self.room_model.get(self.search_iter, 0, 1)
            if self.query in room_match.lower():
                path = self.room_model.get_path(self.search_iter)
                self.RoomsList.set_cursor(path)
                break

            self.search_iter = self.room_model.iter_next(self.search_iter)

    def on_refresh(self, widget):
        self.frame.np.queue.put(slskmessages.RoomList())

    def on_toggle_accept_private_room(self, widget):

        value = self.AcceptPrivateRoom.get_active()
        self.frame.np.queue.put(slskmessages.PrivateRoomToggle(value))

    def update_visuals(self):

        for widget in self.__dict__.values():
            update_widget_visuals(widget)
