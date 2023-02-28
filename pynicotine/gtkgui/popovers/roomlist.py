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

from gi.repository import GObject
from gi.repository import Pango

from pynicotine.config import config
from pynicotine.core import core
from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.widgets.accelerator import Accelerator
from pynicotine.gtkgui.widgets.popover import Popover
from pynicotine.gtkgui.widgets.popupmenu import PopupMenu
from pynicotine.gtkgui.widgets.textentry import CompletionEntry
from pynicotine.gtkgui.widgets.theme import add_css_class
from pynicotine.gtkgui.widgets.treeview import TreeView
from pynicotine.gtkgui.widgets.ui import UserInterface
from pynicotine.utils import humanize


class RoomList(Popover):

    def __init__(self, window):

        ui_template = UserInterface(scope=self, path="popovers/roomlist.ui")
        (
            self.container,
            self.list_container,
            self.private_room_toggle,
            self.public_feed_toggle,
            self.refresh_button,
            self.search_entry
        ) = ui_template.widgets

        super().__init__(
            window=window,
            content_box=self.container,
            width=350,
            height=500
        )

        self.initializing_feed = False

        self.list_view = TreeView(
            self.window, parent=self.list_container,
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
                    "default_sort_column": "descending"
                },

                # Hidden data columns
                "users_data": {"data_type": GObject.TYPE_UINT},
                "room_weight_data": {"data_type": Pango.Weight},
                "room_underline_data": {"data_type": Pango.Underline}
            }
        )

        self.popup_room = None
        self.popup_menu = PopupMenu(window.application, self.list_view.widget, self.on_popup_menu)
        self.popup_menu.add_items(
            ("#" + _("Join Room"), self.on_popup_join),
            ("#" + _("Leave Room"), self.on_popup_leave),
            ("", None),
            ("#" + _("Disown Private Room"), self.on_popup_private_room_disown),
            ("#" + _("Cancel Room Membership"), self.on_popup_private_room_dismember)
        )

        self.private_room_toggle.set_active(config.sections["server"]["private_chatrooms"])
        self.private_room_toggle.connect("toggled", self.on_toggle_accept_private_room)

        Accelerator("<Primary>f", self.widget, self.on_search_accelerator)
        CompletionEntry(window.chatrooms_entry, self.list_view.model, column=0)

        if GTK_API_VERSION >= 4:
            add_css_class(widget=window.room_list_button.get_first_child(), css_class="arrow-button")

        window.room_list_button.set_popover(self.widget)

    def get_selected_room(self):

        for iterator in self.list_view.get_selected_rows():
            return self.list_view.get_row_value(iterator, "room")

        return None

    def set_room_list(self, rooms, owned_rooms, other_private_rooms):

        self.list_view.disable_sorting()
        self.clear()

        for room, users in owned_rooms:
            self.update_room(room, users, private=True, owned=True)

        for room, users in other_private_rooms:
            self.update_room(room, users, private=True)

        for room, users in rooms:
            self.update_room(room, users)

        self.list_view.enable_sorting()

    def toggle_public_feed(self, active):

        self.initializing_feed = True
        self.public_feed_toggle.set_active(active)
        self.initializing_feed = False

    def update_room(self, room, user_count, private=False, owned=False):

        iterator = self.list_view.iterators.get(room)
        h_user_count = humanize(user_count)

        if private or owned:
            # Show private/owned rooms first
            user_count += 10000000

        if iterator is not None:
            self.list_view.set_row_value(iterator, "users", h_user_count)
            self.list_view.set_row_value(iterator, "users_data", user_count)
            return

        text_weight = Pango.Weight.BOLD if private else Pango.Weight.NORMAL
        text_underline = Pango.Underline.SINGLE if owned else Pango.Underline.NONE

        self.list_view.add_row([
            room,
            h_user_count,
            user_count,
            text_weight,
            text_underline
        ], select_row=False)

    def clear(self):
        self.list_view.clear()

    def on_row_activated(self, *_args):

        room = self.get_selected_room()

        if room is not None:
            self.popup_room = room
            self.on_popup_join()

    def on_popup_menu(self, menu, _widget):

        room = self.get_selected_room()
        self.popup_room = room

        menu.actions[_("Join Room")].set_enabled(room not in core.chatrooms.joined_rooms)
        menu.actions[_("Leave Room")].set_enabled(room in core.chatrooms.joined_rooms)

        menu.actions[_("Disown Private Room")].set_enabled(core.chatrooms.is_private_room_owned(room))
        menu.actions[_("Cancel Room Membership")].set_enabled(core.chatrooms.is_private_room_member(room))

    def on_popup_join(self, *_args):
        core.chatrooms.show_room(self.popup_room)
        self.close(use_transition=False)

    def on_toggle_public_feed(self, *_args):

        if self.initializing_feed:
            return

        if self.public_feed_toggle.get_active():
            core.chatrooms.show_room(core.chatrooms.GLOBAL_ROOM_NAME)
            self.close(use_transition=False)
            return

        core.chatrooms.remove_room(core.chatrooms.GLOBAL_ROOM_NAME)

    def on_popup_private_room_disown(self, *_args):
        core.chatrooms.request_private_room_disown(self.popup_room)

    def on_popup_private_room_dismember(self, *_args):
        core.chatrooms.request_private_room_dismember(self.popup_room)

    def on_popup_leave(self, *_args):
        core.chatrooms.remove_room(self.popup_room)

    def on_refresh(self, *_args):
        core.chatrooms.request_room_list()

    def on_toggle_accept_private_room(self, *_args):
        core.chatrooms.request_private_room_toggle(self.private_room_toggle.get_active())

    def on_search_accelerator(self, *_args):
        """ Ctrl+F: Search rooms """

        self.search_entry.grab_focus()
        return True
