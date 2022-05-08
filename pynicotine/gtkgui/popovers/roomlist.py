# COPYRIGHT (C) 2020-2022 Nicotine+ Team
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
from pynicotine.gtkgui.widgets.accelerator import Accelerator
from pynicotine.gtkgui.widgets.popupmenu import PopupMenu
from pynicotine.gtkgui.widgets.textentry import CompletionEntry
from pynicotine.gtkgui.widgets.theme import update_widget_visuals
from pynicotine.gtkgui.widgets.treeview import initialise_columns
from pynicotine.gtkgui.widgets.ui import UserInterface


class RoomList(UserInterface):

    def __init__(self, frame, core):

        super().__init__("ui/popovers/roomlist.ui")
        (
            self.list_view,
            self.popover,
            self.private_room_toggle,
            self.public_feed_toggle,
            self.refresh_button,
            self.search_entry
        ) = self.widgets

        self.frame = frame
        self.core = core
        self.room_iters = {}
        self.initializing_feed = False

        self.room_model = Gtk.ListStore(
            str,
            int,
            Pango.Weight,
            Pango.Underline
        )

        self.room_filter = self.room_model.filter_new()
        self.room_filter.set_visible_func(self.room_match_function)
        self.room_model_filtered = Gtk.TreeModelSort(model=self.room_filter)
        self.list_view.set_model(self.room_model_filtered)

        self.column_numbers = list(range(self.room_model.get_n_columns()))
        attribute_columns = (2, 3)
        self.cols = initialise_columns(
            frame, None, self.list_view,
            ["room", _("Room"), 260, "text", attribute_columns],
            ["users", _("Users"), 100, "number", attribute_columns]
        )
        self.cols["room"].set_sort_column_id(0)
        self.cols["users"].set_sort_column_id(1)

        self.popup_room = None
        self.popup_menu = PopupMenu(self.frame, self.list_view, self.on_popup_menu)
        self.popup_menu.add_items(
            ("#" + _("Join Room"), self.on_popup_join),
            ("#" + _("Leave Room"), self.on_popup_leave),
            ("", None),
            ("#" + _("Disown Private Room"), self.on_popup_private_room_disown),
            ("#" + _("Cancel Room Membership"), self.on_popup_private_room_dismember)
        )

        self.private_room_toggle.set_active(config.sections["server"]["private_chatrooms"])
        self.private_room_toggle.connect("toggled", self.on_toggle_accept_private_room)

        Accelerator("<Primary>f", self.popover, self.on_search_accelerator)
        CompletionEntry(frame.chatrooms_entry, self.room_model, column=0)

        if Gtk.get_major_version() >= 4:
            frame.room_list_button.get_first_child().get_style_context().add_class("arrow-button")

        frame.room_list_button.set_popover(self.popover)

    @staticmethod
    def get_selected_room(treeview):

        model, iterator = treeview.get_selection().get_selected()

        if iterator is None:
            return None

        return model.get_value(iterator, 0)

    @staticmethod
    def private_rooms_sort(model, iter1, iter2, _column):

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

    def room_match_function(self, model, iterator, _data=None):

        query = self.search_entry.get_text().lower()

        if not query:
            return True

        value = model.get_value(iterator, 0)

        if query in value.lower():
            return True

        return False

    def set_room_list(self, rooms, owned_rooms, other_private_rooms):

        # Temporarily disable sorting for improved performance
        sort_column, sort_type = self.room_model.get_sort_column_id()
        self.room_model.set_default_sort_func(lambda *_args: 0)
        self.room_model.set_sort_column_id(-1, Gtk.SortType.DESCENDING)

        self.clear()

        for room, users in owned_rooms:
            self.update_room(room, users, private=True, owned=True)

        for room, users in other_private_rooms:
            self.update_room(room, users, private=True)

        for room, users in rooms:
            self.update_room(room, users)

        self.room_model.set_default_sort_func(self.private_rooms_sort)

        if sort_column is not None and sort_type is not None:
            self.room_model.set_sort_column_id(sort_column, sort_type)

    def toggle_public_feed(self, active):

        self.initializing_feed = True
        self.public_feed_toggle.set_active(active)
        self.initializing_feed = False

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

    def on_row_activated(self, treeview, _path, _column):

        room = self.get_selected_room(treeview)

        if room is not None and room not in self.core.chatrooms.joined_rooms:
            self.popup_room = room
            self.on_popup_join()

    def on_popup_menu(self, menu, widget):

        if self.room_model is None:
            return True

        room = self.get_selected_room(widget)
        self.popup_room = room

        menu.actions[_("Join Room")].set_enabled(room not in self.core.chatrooms.joined_rooms)
        menu.actions[_("Leave Room")].set_enabled(room in self.core.chatrooms.joined_rooms)

        menu.actions[_("Disown Private Room")].set_enabled(self.core.chatrooms.is_private_room_owned(room))
        menu.actions[_("Cancel Room Membership")].set_enabled(self.core.chatrooms.is_private_room_member(room))
        return False

    def on_popup_join(self, *_args):
        self.core.chatrooms.request_join_room(self.popup_room)
        self.popover.hide()

    def on_toggle_public_feed(self, *_args):

        if self.initializing_feed:
            return

        if self.public_feed_toggle.get_active():
            self.core.chatrooms.request_join_public_room()
            self.popover.hide()
            return

        self.core.chatrooms.request_leave_public_room()

    def on_popup_private_room_disown(self, *_args):
        self.core.chatrooms.request_private_room_disown(self.popup_room)

    def on_popup_private_room_dismember(self, *_args):
        self.core.chatrooms.request_private_room_dismember(self.popup_room)

    def on_popup_leave(self, *_args):
        self.core.chatrooms.request_leave_room(self.popup_room)

    def on_search_room(self, *_args):
        self.room_filter.refilter()

    def on_refresh(self, *_args):
        self.core.chatrooms.request_room_list()

    def on_toggle_accept_private_room(self, *_args):
        self.core.chatrooms.request_private_room_toggle(self.private_room_toggle.get_active())

    def on_search_accelerator(self, *_args):
        """ Ctrl+F: Search rooms """

        self.search_entry.grab_focus()
        return True

    def update_visuals(self):
        for widget in list(self.__dict__.values()):
            update_widget_visuals(widget)

    def clear(self):
        self.room_model.clear()
        self.room_iters.clear()
