# COPYRIGHT (C) 2020-2022 Nicotine+ Contributors
# COPYRIGHT (C) 2018 Mutnick <mutnick@techie.com>
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2009 quinox <quinox@users.sf.net>
# COPYRIGHT (C) 2006-2009 daelstorm <daelstorm@gmail.com>
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

import time

from gi.repository import GObject

from pynicotine.config import config
from pynicotine.gtkgui.widgets.dialogs import EntryDialog
from pynicotine.gtkgui.widgets.popupmenu import UserPopupMenu
from pynicotine.gtkgui.widgets.textentry import CompletionEntry
from pynicotine.gtkgui.widgets.theme import get_flag_icon_name
from pynicotine.gtkgui.widgets.theme import get_status_icon_name
from pynicotine.gtkgui.widgets.theme import update_widget_visuals
from pynicotine.gtkgui.widgets.treeview import TreeView
from pynicotine.gtkgui.widgets.ui import UserInterface
from pynicotine.logfacility import log
from pynicotine.slskmessages import UserStatus
from pynicotine.utils import humanize
from pynicotine.utils import human_speed


class UserList:

    def __init__(self, frame, core):

        ui_template = UserInterface(scope=self, path="buddylist.ui")
        (
            self.container,
            self.list_container,
            self.toolbar
        ) = ui_template.widgets

        self.frame = frame
        self.core = core

        # Columns
        self.user_iterators = {}
        self.list_view = TreeView(
            frame, parent=self.list_container, name="buddy_list",
            activate_row_callback=self.on_row_activated, tooltip_callback=self.on_tooltip,
            columns=[
                # Visible columns
                {"column_id": "status", "column_type": "icon", "title": _("Status"), "width": 25,
                 "sort_column": 10, "hide_header": True},
                {"column_id": "country", "column_type": "icon", "title": _("Country"), "width": 25,
                 "sort_column": 14, "hide_header": True},
                {"column_id": "user", "column_type": "text", "title": _("User"), "width": 250,
                 "sort_column": 2, "default_sort_column": "ascending", "iterator_key": True},
                {"column_id": "speed", "column_type": "number", "title": _("Speed"), "width": 150,
                 "sort_column": 11},
                {"column_id": "files", "column_type": "number", "title": _("Files"), "width": 150,
                 "sort_column": 12},
                {"column_id": "trusted", "column_type": "toggle", "title": _("Trusted"), "width": 0,
                 "sort_column": 5, "toggle_callback": self.on_trusted},
                {"column_id": "notify", "column_type": "toggle", "title": _("Notify"), "width": 0,
                 "sort_column": 6, "toggle_callback": self.on_notify},
                {"column_id": "privileged", "column_type": "toggle", "title": _("Prioritized"), "width": 0,
                 "sort_column": 7, "toggle_callback": self.on_prioritized},
                {"column_id": "last_seen", "column_type": "text", "title": _("Last Seen"), "width": 160,
                 "sort_column": 13},
                {"column_id": "comments", "column_type": "text", "title": _("Note"), "width": 400,
                 "sort_column": 9},

                # Hidden data columns
                {"column_id": "status_hidden", "data_type": int},
                {"column_id": "speed_hidden", "data_type": GObject.TYPE_UINT},
                {"column_id": "files_hidden", "data_type": GObject.TYPE_UINT},
                {"column_id": "last_seen_hidden", "data_type": int},
                {"column_id": "country_hidden", "data_type": str}
            ]
        )

        # Lists
        for combo_box in (self.frame.user_search_combobox, self.frame.userinfo_combobox,
                          self.frame.userbrowse_combobox):
            combo_box.set_model(self.list_view.model)
            combo_box.set_entry_text_column(2)

            CompletionEntry(combo_box.get_child(), self.list_view.model, column=2)

        # Popup menus
        self.popup_menu_private_rooms = UserPopupMenu(self.frame)

        self.popup_menu = popup = UserPopupMenu(frame, self.list_view.widget, self.on_popup_menu)
        popup.setup_user_menu(page="userlist")
        popup.add_items(
            ("", None),
            ("#" + _("Add User _Note…"), self.on_add_note),
            (">" + _("Private Rooms"), self.popup_menu_private_rooms),
            ("#" + _("_Remove"), self.on_remove_user)
        )

        self.update_visuals()

    def save_columns(self):
        self.list_view.save_columns()

    def update_visible(self):

        if config.sections["ui"]["buddylistinchatrooms"] in ("always", "chatrooms"):
            return

        self.frame.userlist_content.set_visible(self.user_iterators)

    def update_visuals(self):
        for widget in self.__dict__.values():
            update_widget_visuals(widget)

    def get_selected_username(self):

        iterators = self.list_view.get_selected_rows()

        if not iterators:
            return None

        return self.list_view.get_row_value(iterators[0], 2)

    def on_row_activated(self, _list_view, _iterator, column_id):

        user = self.get_selected_username()

        if user is None:
            return

        if column_id == "comments":
            self.on_add_note()
            return

        self.core.privatechat.show_user(user)

    def on_popup_menu(self, menu, _widget):

        username = self.get_selected_username()
        menu.set_user(username)
        menu.toggle_user_items()
        menu.populate_private_rooms(self.popup_menu_private_rooms)

        private_rooms_enabled = (self.popup_menu_private_rooms.items and menu.user != self.core.login_username)
        menu.actions[_("Private Rooms")].set_enabled(private_rooms_enabled)

    def get_user_status(self, msg):

        user = msg.user
        iterator = self.user_iterators.get(user)

        if iterator is None:
            return

        status = msg.status

        if status == self.list_view.get_row_value(iterator, 10):
            return

        notify = self.list_view.get_row_value(iterator, 6)

        if notify:
            if status == UserStatus.AWAY:
                status_text = _("User %s is away")
            elif status == UserStatus.ONLINE:
                status_text = _("User %s is online")
            else:
                status_text = _("User %s is offline")

            log.add(status_text, user)
            self.frame.notifications.new_text_notification(status_text % user)

        status_icon = get_status_icon_name(status)

        self.list_view.set_row_value(iterator, 0, status_icon)
        self.list_view.set_row_value(iterator, 10, status)

    def get_user_stats(self, msg):

        user = msg.user
        iterator = self.user_iterators.get(user)

        if iterator is None:
            return

        h_speed = ""
        avgspeed = msg.avgspeed

        if avgspeed > 0:
            h_speed = human_speed(avgspeed)

        files = msg.files
        h_files = humanize(files)

        self.list_view.set_row_value(iterator, 3, h_speed)
        self.list_view.set_row_value(iterator, 4, h_files)
        self.list_view.set_row_value(iterator, 11, GObject.Value(GObject.TYPE_UINT, avgspeed))
        self.list_view.set_row_value(iterator, 12, GObject.Value(GObject.TYPE_UINT, files))

    def add_user(self, user, row):

        _user, note, notify, prioritized, trusted, last_seen, country = row

        try:
            time_from_epoch = time.mktime(time.strptime(last_seen, "%m/%d/%Y %H:%M:%S"))
        except ValueError:
            last_seen = _("Never seen")
            time_from_epoch = 0

        self.user_iterators[user] = self.list_view.add_row([
            get_status_icon_name(UserStatus.OFFLINE),
            get_flag_icon_name(country),
            str(user),
            "", "",
            bool(trusted),
            bool(notify),
            bool(prioritized),
            str(last_seen),
            str(note),
            0, 0, 0,
            time_from_epoch,
            str(country)
        ])

        self.update_visible()

        if config.sections["words"]["buddies"]:
            self.frame.update_completions()

    def remove_user(self, user):

        if user in self.user_iterators:
            self.list_view.remove_row(self.user_iterators[user])
            del self.user_iterators[user]

        self.update_visible()

        if config.sections["words"]["buddies"]:
            self.frame.update_completions()

    def set_user_note(self, user, note):

        iterator = self.user_iterators.get(user)

        if iterator is not None:
            self.list_view.set_row_value(iterator, 9, note)

    def set_user_trusted(self, user, trusted):

        iterator = self.user_iterators.get(user)

        if iterator is not None:
            self.list_view.set_row_value(iterator, 5, trusted)

    def set_user_notify(self, user, notify):

        iterator = self.user_iterators.get(user)

        if iterator is not None:
            self.list_view.set_row_value(iterator, 6, notify)

    def set_user_prioritized(self, user, prioritized):

        iterator = self.user_iterators.get(user)

        if iterator is not None:
            self.list_view.set_row_value(iterator, 7, prioritized)

    def set_user_last_seen(self, user, online):

        iterator = self.user_iterators.get(user)

        if iterator is None:
            return

        last_seen = ""
        time_from_epoch = 2147483647  # Gtk only allows range -2147483648 to 2147483647 in set()

        if not online:
            last_seen = time.strftime("%m/%d/%Y %H:%M:%S")
            time_from_epoch = time.mktime(time.strptime(last_seen, "%m/%d/%Y %H:%M:%S"))

        self.list_view.set_row_value(iterator, 8, last_seen)
        self.list_view.set_row_value(iterator, 13, int(time_from_epoch))

    def set_user_country(self, user, country_code):

        iterator = self.user_iterators.get(user)

        if iterator is None:
            return

        flag_icon = get_flag_icon_name(country_code or "")

        if not flag_icon:
            return

        self.list_view.set_row_value(iterator, 1, flag_icon)
        self.list_view.set_row_value(iterator, 14, "flag_" + country_code)

    def on_add_user(self, *_args):

        username = self.frame.add_buddy_entry.get_text().strip()

        if not username:
            return

        self.frame.add_buddy_entry.set_text("")
        self.core.userlist.add_user(username)

    def on_remove_user(self, *_args):
        self.core.userlist.remove_user(self.get_selected_username())

    def on_trusted(self, list_view, iterator):

        user = list_view.get_row_value(iterator, 2)
        value = list_view.get_row_value(iterator, 5)

        self.core.userlist.set_user_trusted(user, not value)

    def on_notify(self, list_view, iterator):

        user = list_view.get_row_value(iterator, 2)
        value = list_view.get_row_value(iterator, 6)

        self.core.userlist.set_user_notify(user, not value)

    def on_prioritized(self, list_view, iterator):

        user = list_view.get_row_value(iterator, 2)
        value = list_view.get_row_value(iterator, 7)

        self.core.userlist.set_user_prioritized(user, not value)

    def on_add_note_response(self, dialog, _response_id, user):

        iterator = self.user_iterators.get(user)

        if iterator is None:
            return

        note = dialog.get_entry_value()

        if note is None:
            return

        self.core.userlist.set_user_note(user, note)

    def on_add_note(self, *_args):

        user = self.get_selected_username()
        iterator = self.user_iterators.get(user)

        if iterator is None:
            return

        note = self.list_view.get_row_value(iterator, 9) or ""

        EntryDialog(
            parent=self.frame.window,
            title=_("Add User Note"),
            message=_("Add a note about user %s:") % user,
            callback=self.on_add_note_response,
            callback_data=user,
            default=note
        ).show()

    @staticmethod
    def on_tooltip(list_view, pos_x, pos_y, _keyboard_mode, tooltip):

        status_tooltip = list_view.show_user_status_tooltip(pos_x, pos_y, tooltip, 10)
        country_tooltip = list_view.show_country_tooltip(pos_x, pos_y, tooltip, 14)

        if status_tooltip:
            return status_tooltip

        if country_tooltip:
            return country_tooltip

        return False

    def server_disconnect(self):

        for iterator in self.list_view.get_all_rows():
            self.list_view.set_row_value(iterator, 0, get_status_icon_name(UserStatus.OFFLINE))
            self.list_view.set_row_value(iterator, 3, "")
            self.list_view.set_row_value(iterator, 4, "")
            self.list_view.set_row_value(iterator, 10, 0)
            self.list_view.set_row_value(iterator, 11, 0)
            self.list_view.set_row_value(iterator, 12, 0)
