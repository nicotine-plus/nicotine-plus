# COPYRIGHT (C) 2020-2021 Nicotine+ Team
# COPYRIGHT (C) 2018 Mutnick <mutnick@techie.com>
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2009 Quinox <quinox@users.sf.net>
# COPYRIGHT (C) 2006-2009 Daelstorm <daelstorm@gmail.com>
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
import time

from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk

from pynicotine.config import config
from pynicotine.gtkgui.utils import load_ui_elements
from pynicotine.gtkgui.widgets.dialogs import entry_dialog
from pynicotine.gtkgui.widgets.popupmenu import PopupMenu
from pynicotine.gtkgui.widgets.theme import update_widget_visuals
from pynicotine.gtkgui.widgets.treeview import initialise_columns
from pynicotine.gtkgui.widgets.treeview import save_columns
from pynicotine.gtkgui.widgets.treeview import show_country_tooltip
from pynicotine.gtkgui.widgets.treeview import show_user_status_tooltip
from pynicotine.logfacility import log
from pynicotine.utils import humanize
from pynicotine.utils import human_speed


class UserList:

    def __init__(self, frame):

        # Build the window
        self.frame = frame

        load_ui_elements(self, os.path.join(self.frame.gui_dir, "ui", "buddylist.ui"))

        """ Columns """

        self.user_iterators = {}
        self.usersmodel = Gtk.ListStore(
            GObject.TYPE_OBJECT,  # (0)  status icon
            GObject.TYPE_OBJECT,  # (1)  flag
            str,                  # (2)  username
            str,                  # (3)  hspeed
            str,                  # (4)  hfile count
            bool,                 # (5)  trusted
            bool,                 # (6)  notify
            bool,                 # (7)  privileged
            str,                  # (8)  hlast seen
            str,                  # (9)  comments
            int,                  # (10) status
            GObject.TYPE_UINT64,  # (11) speed
            GObject.TYPE_UINT64,  # (12) file count
            int,                  # (13) last seen
            str                   # (14) country
        )

        self.column_numbers = list(range(self.usersmodel.get_n_columns()))
        self.cols = cols = initialise_columns(
            "buddy_list", self.UserListTree,
            ["status", _("Status"), 25, "pixbuf", None],
            ["country", _("Country"), 25, "pixbuf", None],
            ["user", _("User"), 250, "text", None],
            ["speed", _("Speed"), 150, "number", None],
            ["files", _("Files"), 150, "number", None],
            ["trusted", _("Trusted"), 0, "toggle", None],
            ["notify", _("Notify"), 0, "toggle", None],
            ["privileged", _("Privileged"), 0, "toggle", None],
            ["last_seen", _("Last seen"), 160, "text", None],
            ["comments", _("Comments"), 400, "edit", None]
        )

        cols["status"].set_sort_column_id(10)
        cols["country"].set_sort_column_id(14)
        cols["user"].set_sort_column_id(2)
        cols["speed"].set_sort_column_id(11)
        cols["files"].set_sort_column_id(12)
        cols["trusted"].set_sort_column_id(5)
        cols["notify"].set_sort_column_id(6)
        cols["privileged"].set_sort_column_id(7)
        cols["last_seen"].set_sort_column_id(13)
        cols["comments"].set_sort_column_id(9)

        cols["status"].get_widget().hide()
        cols["country"].get_widget().hide()

        if config.sections["columns"]["hideflags"]:
            cols["country"].set_visible(False)

        for render in cols["trusted"].get_cells():
            render.connect('toggled', self.cell_toggle_callback, self.UserListTree, 5)

        for render in cols["notify"].get_cells():
            render.connect('toggled', self.cell_toggle_callback, self.UserListTree, 6)

        for render in cols["privileged"].get_cells():
            render.connect('toggled', self.cell_toggle_callback, self.UserListTree, 7)

        for render in cols["comments"].get_cells():
            render.connect('edited', self.cell_edited_callback, self.UserListTree, 9)

        self.UserListTree.set_model(self.usersmodel)

        """ Lists """

        for row in config.sections["server"]["userlist"]:
            self.append_user_row(row)

        self.usersmodel.set_sort_column_id(2, Gtk.SortType.ASCENDING)

        self.buddies_combo_entries = (
            self.frame.UserSearchCombo, self.frame.PrivateChatCombo, self.frame.UserInfoCombo,
            self.frame.UserBrowseCombo)

        self.buddies_combos_fill()

        """ Popup """

        self.popup_menu_private_rooms = PopupMenu(self.frame)

        self.popup_menu = popup = PopupMenu(frame, self.UserListTree, self.on_popup_menu)
        popup.setup_user_menu(page="userlist")
        popup.setup(
            ("", None),
            ("$" + _("_Online Notify"), self.on_notify),
            ("$" + _("_Privileged"), self.on_privileged),
            ("$" + _("_Trusted"), self.on_trusted),
            ("", None),
            (">" + _("Private Rooms"), self.popup_menu_private_rooms),
            ("#" + _("Edit _Comments..."), self.on_edit_comments),
            ("#" + _("_Remove"), self.on_remove_user)
        )

        self.update_visuals()

    def append_user_row(self, row):

        if not row or not isinstance(row, list):
            return

        username = str(row[0])

        if not username:
            return

        try:
            comment = str(row[1])
        except IndexError:
            comment = ""

        try:
            notify = bool(row[2])
        except IndexError:
            notify = False

        try:
            privileged = bool(row[3])
        except IndexError:
            privileged = False

        try:
            trusted = bool(row[4])
        except IndexError:
            trusted = False

        try:
            last_seen = str(row[5])
        except IndexError:
            last_seen = ""

        try:
            time_from_epoch = time.mktime(time.strptime(last_seen, "%m/%d/%Y %H:%M:%S"))
        except ValueError:
            last_seen = _("Never seen")
            time_from_epoch = 0

        try:
            country = str(row[6])
        except IndexError:
            country = ""

        row = [
            GObject.Value(GObject.TYPE_OBJECT, self.frame.get_status_image(0)),
            GObject.Value(GObject.TYPE_OBJECT, self.frame.get_flag_image(country)),
            username,
            "",
            "",
            trusted,
            notify,
            privileged,
            last_seen,
            comment,
            0,
            0,
            0,
            time_from_epoch,
            country
        ]

        self.user_iterators[username] = self.usersmodel.insert_with_valuesv(0, self.column_numbers, row)

    def buddies_combos_fill(self):

        for widget in self.buddies_combo_entries:
            widget.remove_all()
            widget.append_text("")

            for row in config.sections["server"]["userlist"]:
                if row and isinstance(row, list):
                    widget.append_text(str(row[0]))

    def on_tooltip(self, widget, x, y, keyboard_mode, tooltip):

        status_tooltip = show_user_status_tooltip(widget, x, y, tooltip, 10)
        country_tooltip = show_country_tooltip(widget, x, y, tooltip, 14)

        if status_tooltip:
            return status_tooltip

        if country_tooltip:
            return country_tooltip

    def on_add_user(self, widget, *args):

        username = widget.get_text()

        if not username:
            return

        widget.set_text("")
        self.frame.np.userlist.add_user(username)

    def update_visuals(self):

        for widget in list(self.__dict__.values()):
            update_widget_visuals(widget)

    def on_settings_ban_ignore(self, *args):
        self.frame.on_settings_ban_ignore()

    def cell_toggle_callback(self, widget, index, treeview, pos):

        store = treeview.get_model()
        iterator = store.get_iter(index)

        value = self.usersmodel.get_value(iterator, pos)
        self.usersmodel.set_value(iterator, pos, not value)

        self.save_user_list()

    def cell_edited_callback(self, widget, index, value, treeview, pos):

        if pos != 9:
            return

        store = treeview.get_model()
        iterator = store.get_iter(index)

        self.set_comment(iterator, store, value)

    def set_last_seen(self, user, online=False):

        iterator = self.user_iterators.get(user)

        if iterator is None:
            return

        last_seen = ""
        time_from_epoch = 2147483647  # Gtk only allows range -2147483648 to 2147483647 in set()

        if not online:
            last_seen = time.strftime("%m/%d/%Y %H:%M:%S")
            time_from_epoch = time.mktime(time.strptime(last_seen, "%m/%d/%Y %H:%M:%S"))

        self.usersmodel.set_value(iterator, 8, last_seen)
        self.usersmodel.set_value(iterator, 13, int(time_from_epoch))

        if not online:
            self.save_user_list()

    def set_comment(self, iterator, store, comments=None):

        if comments is not None:
            store.set_value(iterator, 9, comments)
            self.save_user_list()

    def get_selected_username(self, treeview):

        model, iterator = treeview.get_selection().get_selected()

        if iterator is None:
            return None

        return model.get_value(iterator, 2)

    def get_selected_username_details(self, treeview):

        model, iterator = treeview.get_selection().get_selected()

        if iterator is not None:
            username = model.get_value(iterator, 2)
            trusted = model.get_value(iterator, 5)
            notify = model.get_value(iterator, 6)
            privileged = model.get_value(iterator, 7)
            status = model.get_value(iterator, 10)

        else:
            username = trusted = notify = privileged = status = None

        return username, trusted, notify, privileged, status

    def on_row_activated(self, treeview, path, column):

        user = self.get_selected_username(treeview)

        if user is not None:
            self.frame.np.privatechats.show_user(user)
            self.frame.change_main_page("private")

    def on_popup_menu(self, menu, widget):

        username, trusted, notify, privileged, status = self.get_selected_username_details(widget)
        if username is None:
            return True

        menu.set_user(username)
        menu.toggle_user_items()
        menu.populate_private_rooms(self.popup_menu_private_rooms)

        actions = menu.get_actions()

        actions[_("Private Rooms")].set_enabled(
            status or menu.user != config.sections["server"]["login"]
        )

        actions[_("_Online Notify")].set_state(GLib.Variant.new_boolean(notify))
        actions[_("_Privileged")].set_state(GLib.Variant.new_boolean(privileged))
        actions[_("_Trusted")].set_state(GLib.Variant.new_boolean(trusted))

    def get_user_status(self, msg):

        status = msg.status

        if status < 0:
            # User doesn't exist, nothing to do
            return

        user = msg.user
        iterator = self.user_iterators.get(user)

        if iterator is None:
            return

        if status == int(self.usersmodel.get_value(iterator, 10)):
            return

        notify = self.usersmodel.get_value(iterator, 6)

        if notify:
            if status == 1:
                status_text = _("User %s is away")
            elif status == 2:
                status_text = _("User %s is online")
            else:
                status_text = _("User %s is offline")

            log.add(status_text, user)
            self.frame.notifications.new_text_notification(status_text % user)

        img = self.frame.get_status_image(status)
        self.usersmodel.set_value(iterator, 0, GObject.Value(GObject.TYPE_OBJECT, img))
        self.usersmodel.set_value(iterator, 10, GObject.Value(GObject.TYPE_INT64, status))

        if status:  # online
            self.set_last_seen(user, online=True)

        elif not self.usersmodel.get_value(iterator, 8):  # disconnected
            self.set_last_seen(user)

    def get_user_stats(self, msg):

        user = msg.user
        iterator = self.user_iterators.get(user)

        if iterator is None:
            return

        hspeed = human_speed(msg.avgspeed)
        hfiles = humanize(msg.files)

        self.usersmodel.set_value(iterator, 3, hspeed)
        self.usersmodel.set_value(iterator, 4, hfiles)
        self.usersmodel.set_value(iterator, 11, GObject.Value(GObject.TYPE_UINT64, msg.avgspeed))
        self.usersmodel.set_value(iterator, 12, GObject.Value(GObject.TYPE_UINT64, msg.files))

    def set_user_country(self, user, country):

        iterator = self.user_iterators.get(user)

        if iterator is None:
            return

        self.usersmodel.set_value(iterator, 1, GObject.Value(GObject.TYPE_OBJECT, self.frame.get_flag_image(country)))
        self.usersmodel.set_value(iterator, 14, "flag_" + country)

    def add_user(self, user):

        if user in self.user_iterators:
            return

        empty_int = 0
        empty_str = ""

        self.user_iterators[user] = self.usersmodel.insert_with_valuesv(
            -1, self.column_numbers,
            [
                GObject.Value(GObject.TYPE_OBJECT, self.frame.get_status_image(0)),
                GObject.Value(GObject.TYPE_OBJECT, None),
                user,
                empty_str,
                empty_str,
                False,
                False,
                False,
                _("Never seen"),
                empty_str,
                empty_int,
                empty_int,
                empty_int,
                empty_int,
                empty_str
            ]
        )

        self.save_user_list()

        for widget in self.buddies_combo_entries:
            widget.append_text(user)

        if config.sections["words"]["buddies"]:
            self.frame.update_completions()

    def remove_user(self, user):

        if user in self.user_iterators:
            self.usersmodel.remove(self.user_iterators[user])
            del self.user_iterators[user]

        self.save_user_list()
        self.buddies_combos_fill()

        if config.sections["words"]["buddies"]:
            self.frame.update_completions()

    def save_user_list(self):

        user_list = []

        for i in self.usersmodel:
            (status_icon, flag, user, hspeed, hfile_count, trusted, notify, privileged,
                hlast_seen, comments, status, speed, file_count, last_seen, country) = i
            user_list.append([user, comments, notify, privileged, trusted, hlast_seen, country])

        self.frame.np.userlist.save_user_list(user_list)

    def save_columns(self):
        save_columns("buddy_list", self.UserListTree.get_columns())

    def on_trusted(self, action, state):

        user = self.popup_menu.get_user()
        iterator = self.user_iterators.get(user)

        if iterator is None:
            return

        self.usersmodel.set_value(iterator, 5, state)

        self.save_user_list()
        action.set_state(state)

    def on_notify(self, action, state):

        user = self.popup_menu.get_user()
        iterator = self.user_iterators.get(user)

        if iterator is None:
            return

        self.usersmodel.set_value(iterator, 6, state)

        self.save_user_list()
        action.set_state(state)

    def on_privileged(self, action, state):

        user = self.popup_menu.get_user()
        iterator = self.user_iterators.get(user)

        if iterator is None:
            return

        self.usersmodel.set_value(iterator, 7, state)

        self.save_user_list()
        action.set_state(state)

    def on_edit_comments_response(self, dialog, response_id, user):

        iterator = self.user_iterators.get(user)

        if iterator is None:
            return

        comments = dialog.get_response_value()
        dialog.destroy()

        if comments is None:
            return

        self.usersmodel.set_value(iterator, 9, comments)
        self.save_user_list()

    def on_edit_comments(self, *args):

        user = self.popup_menu.get_user()
        iterator = self.user_iterators.get(user)

        if iterator is None:
            return

        comments = self.usersmodel.get_value(iterator, 9) or ""

        entry_dialog(
            parent=self.frame.MainWindow,
            title=_("Edit Comments"),
            message=_("Add a few notes associated with user %s:") % user,
            callback=self.on_edit_comments_response,
            callback_data=user,
            default=comments
        )

    def on_remove_user(self, *args):
        self.frame.np.userlist.remove_user(self.popup_menu.get_user())

    def server_disconnect(self):

        for i in self.usersmodel:
            iterator = i.iter

            self.usersmodel.set_value(iterator, 0, GObject.Value(GObject.TYPE_OBJECT, self.frame.get_status_image(0)))
            self.usersmodel.set_value(iterator, 3, "")
            self.usersmodel.set_value(iterator, 4, "")
            self.usersmodel.set_value(iterator, 10, 0)
            self.usersmodel.set_value(iterator, 11, 0)
            self.usersmodel.set_value(iterator, 12, 0)

            if not self.usersmodel.get_value(iterator, 8):
                user = self.usersmodel.get_value(iterator, 2)
                self.set_last_seen(user)
