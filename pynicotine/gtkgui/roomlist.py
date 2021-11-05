# COPYRIGHT (C) 2020-2021 Nicotine+ Team
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

from gi.repository import Gtk
from gi.repository import Pango

from pynicotine.config import config
from pynicotine.gtkgui.widgets.popupmenu import PopupMenu
from pynicotine.gtkgui.widgets.theme import update_widget_visuals
from pynicotine.gtkgui.widgets.treeview import initialise_columns
from pynicotine.gtkgui.widgets.ui import UserInterface


class RoomList(UserInterface):

    def __init__(self, frame):

        super().__init__("ui/popovers/roomlist.ui")

        self.frame = frame
        self.room_iters = {}

        self.room_model = Gtk.ListStore(
            str,
            int,
            Pango.Weight,
            Pango.Underline
        )

        self.room_filter = self.room_model.filter_new()
        self.room_filter.set_visible_func(self.room_match_function)

        try:
            self.room_model_filtered = Gtk.TreeModelSort.new_with_model(self.room_filter)

        except AttributeError:
            # Older GTK versions
            self.room_model_filtered = Gtk.TreeModelSort.sort_new_with_model(self.room_filter)

        self.list_view.set_model(self.room_model_filtered)

        self.column_numbers = list(range(self.room_model.get_n_columns()))
        attribute_columns = (2, 3)
        self.cols = initialise_columns(
            None, self.list_view,
            ["room", _("Room"), 260, "text", attribute_columns],
            ["users", _("Users"), 100, "number", attribute_columns]
        )
        self.cols["room"].set_sort_column_id(0)
        self.cols["users"].set_sort_column_id(1)

        self.popup_room = None
        self.popup_menu = PopupMenu(self.frame, self.list_view, self.on_popup_menu)
        self.popup_menu.setup(
            ("#" + _("Join Room"), self.on_popup_join),
            ("#" + _("Leave Room"), self.on_popup_leave),
            ("", None),
            ("#" + _("Disown Private Room"), self.on_popup_private_room_disown),
            ("#" + _("Cancel Room Membership"), self.on_popup_private_room_dismember)
        )

        self.list_view.set_headers_clickable(True)

        self.search_iter = None
        self.query = ""

        self.private_room_check.set_active(config.sections["server"]["private_chatrooms"])
        self.private_room_check.connect("toggled", self.on_toggle_accept_private_room)

        if Gtk.get_major_version() == 4:
            button = frame.RoomList.get_first_child()
            button.set_child(frame.RoomListLabel)
            button.get_style_context().add_class("image-text-button")
            button.get_style_context().remove_class("image-button")
        else:
            frame.RoomList.add(frame.RoomListLabel)

        frame.RoomList.set_popover(self.popover)

    def get_selected_room(self, treeview):

        model, iterator = treeview.get_selection().get_selected()

        if iterator is None:
            return None

        return model.get_value(iterator, 0)

    def private_rooms_sort(self, model, iter1, iter2, column):

        try:
            private1 = model.get_value(iter1, 2) * 10000
            private1 += model.get_value(iter1, 1)
        except Exception:
            private1 = 0

        try:
            private2 = model.get_value(iter2, 2) * 10000
            private2 += model.get_value(iter2, 1)
        except Exception:
            private2 = 0

        return (private1 > private2) - (private1 < private2)

    def room_match_function(self, model, iterator, data=None):

        query = self.search_entry.get_text().lower()

        if not query:
            return True

        value = model.get_value(iterator, 0)

        if query in value.lower():
            return True

        return False

    def set_room_list(self, rooms, owned_rooms, other_private_rooms):

        # Temporarily disable sorting for improved performance
        self.room_model.set_sort_func(1, lambda *args: 0)
        self.room_model.set_default_sort_func(lambda *args: 0)
        self.room_model.set_sort_column_id(-1, Gtk.SortType.DESCENDING)

        self.clear()

        for room, users in owned_rooms:
            self.update_room(room, users, private=True, owned=True)

        for room, users in other_private_rooms:
            self.update_room(room, users, private=True)

        for room, users in rooms:
            self.update_room(room, users)

        self.room_model.set_sort_func(1, self.private_rooms_sort, 1)
        self.room_model.set_sort_column_id(1, Gtk.SortType.DESCENDING)
        self.room_model.set_default_sort_func(self.private_rooms_sort)

    def update_room(self, room, user_count, private=False, owned=False):

        iterator = self.room_iters.get(room)

        if iterator is not None:
            self.room_model.set_value(iterator, 1, user_count)
            return

        text_weight = Pango.Weight.BOLD if private else Pango.Weight.NORMAL
        text_underline = Pango.Underline.SINGLE if owned else Pango.Underline.NONE

        self.room_iters[room] = self.room_model.insert_with_valuesv(
            -1, self.column_numbers,
            [room, user_count, text_weight, text_underline]
        )

    def on_row_activated(self, treeview, path, column):

        room = self.get_selected_room(treeview)

        if room is not None and room not in self.frame.np.chatrooms.joined_rooms:
            self.popup_room = room
            self.on_popup_join()

    def on_popup_menu(self, menu, widget):

        if self.room_model is None:
            return True

        room = self.get_selected_room(widget)

        self.popup_room = room
        prooms_enabled = True

        actions = menu.get_actions()

        actions[_("Join Room")].set_enabled(room not in self.frame.np.chatrooms.joined_rooms)
        actions[_("Leave Room")].set_enabled(room in self.frame.np.chatrooms.joined_rooms)

        actions[_("Disown Private Room")].set_enabled(self.frame.np.chatrooms.is_private_room_owned(self.popup_room))
        actions[_("Cancel Room Membership")].set_enabled(
            (prooms_enabled and self.frame.np.chatrooms.is_private_room_member(self.popup_room)))

    def on_popup_join(self, *args):
        self.frame.np.chatrooms.request_join_room(self.popup_room)

    def on_show_chat_feed(self, *args):

        if self.feed_check.get_active():
            self.frame.np.chatrooms.request_join_public_room()
            return

        self.frame.np.chatrooms.request_leave_public_room()

    def on_popup_private_room_disown(self, *args):
        self.frame.np.chatrooms.request_private_room_disown(self.popup_room)

    def on_popup_private_room_dismember(self, *args):
        self.frame.np.chatrooms.request_private_room_dismember(self.popup_room)

    def on_popup_leave(self, *args):
        self.frame.np.chatrooms.request_leave_room(self.popup_room)

    def on_search_room(self, *args):
        self.room_filter.refilter()

    def on_refresh(self, *args):
        self.frame.np.chatrooms.request_room_list()

    def on_toggle_accept_private_room(self, widget):
        self.frame.np.chatrooms.request_private_room_toggle(self.private_room_check.get_active())

    def update_visuals(self):
        for widget in list(self.__dict__.values()):
            update_widget_visuals(widget)

    def clear(self):
        self.room_model.clear()
        self.room_iters.clear()
