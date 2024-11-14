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

from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Pango

from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.widgets import ui
from pynicotine.gtkgui.widgets.accelerator import Accelerator
from pynicotine.gtkgui.widgets.popover import Popover
from pynicotine.gtkgui.widgets.popupmenu import PopupMenu
from pynicotine.gtkgui.widgets.textentry import CompletionEntry
from pynicotine.gtkgui.widgets.theme import add_css_class
from pynicotine.gtkgui.widgets.treeview import TreeView
from pynicotine.utils import humanize


class RoomList(Popover):

    PRIVATE_USERS_OFFSET = 10000000

    def __init__(self, window):

        (
            self.container,
            self.list_container,
            self.private_room_toggle,
            self.public_feed_toggle,
            self.refresh_button,
            self.search_entry
        ) = ui.load(scope=self, path="popovers/roomlist.ui")

        super().__init__(
            window=window,
            content_box=self.container,
            width=450,
            height=500
        )

        self.list_view = TreeView(
            window, parent=self.list_container,
            activate_row_callback=self.on_row_activated, search_entry=self.search_entry,
            columns={
                # Visible columns
                "room": {
                    "column_type": "text",
                    "title": _("Room"),
                    "width": 260,
                    "expand_column": True,
                    "text_underline_column": "room_underline_data",
                    "text_weight_column": "room_weight_data"
                },
                "users": {
                    "column_type": "number",
                    "title": _("Users"),
                    "sort_column": "users_data",
                    "default_sort_type": "descending"
                },

                # Hidden data columns
                "users_data": {"data_type": GObject.TYPE_UINT},
                "is_private_data": {"data_type": GObject.TYPE_BOOLEAN},
                "room_weight_data": {"data_type": Pango.Weight},
                "room_underline_data": {"data_type": Pango.Underline}
            }
        )

        self.popup_room = None
        self.popup_menu = PopupMenu(window.application, self.list_view.widget, self.on_popup_menu)
        self.popup_menu.add_items(
            ("=" + _("Join Room"), self.on_popup_join),
            ("=" + _("Leave Room"), self.on_popup_leave),
            ("", None),
            ("=" + _("Disown Private Room"), self.on_popup_private_room_disown),
            ("=" + _("Cancel Room Membership"), self.on_popup_private_room_cancel_membership)
        )

        for toggle in (self.public_feed_toggle, self.private_room_toggle):
            parent = next(iter(toggle.get_parent()))

            if GTK_API_VERSION >= 4:
                parent.gesture_click = Gtk.GestureClick()
                parent.add_controller(parent.gesture_click)
            else:
                parent.set_has_window(True)
                parent.gesture_click = Gtk.GestureMultiPress(widget=parent)

            parent.gesture_click.connect("released", self.on_toggle_label_pressed, toggle)

        self.private_room_toggle.set_active(config.sections["server"]["private_chatrooms"])
        self.private_room_toggle.connect("notify::active", self.on_toggle_accept_private_room)

        Accelerator("<Primary>f", self.widget, self.on_search_accelerator)
        self.completion_entry = CompletionEntry(window.chatrooms_entry, self.list_view.model, column=0)

        if GTK_API_VERSION >= 4:
            inner_button = next(iter(window.room_list_button))
            add_css_class(widget=inner_button, css_class="arrow-button")

        self.set_menu_button(window.room_list_button)

        for event_name, callback in (
            ("join-room", self.join_room),
            ("private-room-added", self.private_room_added),
            ("remove-room", self.remove_room),
            ("room-list", self.room_list),
            ("server-disconnect", self.clear),
            ("show-room", self.show_room),
            ("user-joined-room", self.user_joined_room),
            ("user-left-room", self.user_left_room)
        ):
            events.connect(event_name, callback)

    def destroy(self):

        self.list_view.destroy()
        self.popup_menu.destroy()
        self.completion_entry.destroy()

        super().destroy()

    def get_selected_room(self):

        for iterator in self.list_view.get_selected_rows():
            return self.list_view.get_row_value(iterator, "room")

        return None

    def toggle_accept_private_room(self, active):
        self.private_room_toggle.set_active(active)

    def add_room(self, room, user_count=0, is_private=False, is_owned=False):

        h_user_count = humanize(user_count)

        if is_private:
            # Large internal value to sort private rooms first
            user_count += self.PRIVATE_USERS_OFFSET

        text_weight = Pango.Weight.BOLD if is_private else Pango.Weight.NORMAL
        text_underline = Pango.Underline.SINGLE if is_owned else Pango.Underline.NONE

        self.list_view.add_row([
            room,
            h_user_count,
            user_count,
            is_private,
            text_weight,
            text_underline
        ], select_row=False)

    def update_room_user_count(self, room, user_count=None, decrement=False):

        iterator = self.list_view.iterators.get(room)

        if iterator is None:
            return

        is_private = self.list_view.get_row_value(iterator, "is_private_data")

        if user_count is None:
            user_count = self.list_view.get_row_value(iterator, "users_data")

            if decrement:
                if user_count > 0:
                    user_count -= 1
            else:
                user_count += 1

        elif is_private:
            # Large internal value to sort private rooms first
            user_count += self.PRIVATE_USERS_OFFSET

        h_user_count = humanize(user_count - self.PRIVATE_USERS_OFFSET) if is_private else humanize(user_count)

        self.list_view.set_row_values(
            iterator,
            column_ids=["users", "users_data"],
            values=[h_user_count, user_count]
        )

    def clear(self, *_args):
        self.list_view.clear()

    def private_room_added(self, msg):
        self.add_room(msg.room, is_private=True)

    def join_room(self, msg):

        room = msg.room

        if room not in core.chatrooms.joined_rooms:
            return

        user_count = len(msg.users)

        if room not in self.list_view.iterators:
            self.add_room(
                room, user_count, is_private=msg.private,
                is_owned=(msg.owner == core.users.login_username)
            )

        self.update_room_user_count(room, user_count=user_count)

    def show_room(self, room, *_args):
        if room == core.chatrooms.GLOBAL_ROOM_NAME:
            self.public_feed_toggle.set_active(True)

    def remove_room(self, room):

        if room == core.chatrooms.GLOBAL_ROOM_NAME:
            self.public_feed_toggle.set_active(False)

        self.update_room_user_count(room, decrement=True)

    def user_joined_room(self, msg):
        if msg.userdata.username != core.users.login_username:
            self.update_room_user_count(msg.room)

    def user_left_room(self, msg):
        if msg.username != core.users.login_username:
            self.update_room_user_count(msg.room, decrement=True)

    def room_list(self, msg):

        self.list_view.freeze()
        self.clear()

        for room, user_count in msg.ownedprivaterooms:
            self.add_room(room, user_count, is_private=True, is_owned=True)

        for room, user_count in msg.otherprivaterooms:
            self.add_room(room, user_count, is_private=True)

        for room, user_count in msg.rooms:
            self.add_room(room, user_count)

        self.list_view.unfreeze()

    def on_row_activated(self, *_args):

        room = self.get_selected_room()

        if room is not None:
            self.popup_room = room
            self.on_popup_join()

    def on_popup_menu(self, menu, _widget):

        room = self.get_selected_room()
        self.popup_room = room

        is_private_room_owned = core.chatrooms.is_private_room_owned(room)
        is_private_room_member = core.chatrooms.is_private_room_member(room)

        menu.actions[_("Join Room")].set_enabled(room not in core.chatrooms.joined_rooms)
        menu.actions[_("Leave Room")].set_enabled(room in core.chatrooms.joined_rooms)

        menu.actions[_("Disown Private Room")].set_enabled(is_private_room_owned)
        menu.actions[_("Cancel Room Membership")].set_enabled(is_private_room_member and not is_private_room_owned)

    def on_popup_join(self, *_args):
        core.chatrooms.show_room(self.popup_room)
        self.close(use_transition=False)

    def on_toggle_label_pressed(self, _controller, _num_p, _pos_x, _pos_y, toggle):
        toggle.emit("activate")

    def on_toggle_public_feed(self, *_args):

        global_room_name = core.chatrooms.GLOBAL_ROOM_NAME

        if self.public_feed_toggle.get_active():
            if global_room_name not in core.chatrooms.joined_rooms:
                core.chatrooms.show_room(global_room_name)

            self.close(use_transition=False)
            return

        core.chatrooms.remove_room(global_room_name)

    def on_popup_private_room_disown(self, *_args):
        core.chatrooms.request_private_room_disown(self.popup_room)

    def on_popup_private_room_cancel_membership(self, *_args):
        core.chatrooms.request_private_room_cancel_membership(self.popup_room)

    def on_popup_leave(self, *_args):
        core.chatrooms.remove_room(self.popup_room)

    def on_refresh(self, *_args):
        core.chatrooms.request_room_list()

    def on_toggle_accept_private_room(self, *_args):
        active = config.sections["server"]["private_chatrooms"] = self.private_room_toggle.get_active()
        core.chatrooms.request_private_room_toggle(active)

    def on_search_accelerator(self, *_args):
        """Ctrl+F - Search rooms."""

        self.search_entry.grab_focus()
        return True
