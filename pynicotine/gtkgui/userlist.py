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

from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk

from pynicotine import slskmessages
from pynicotine.gtkgui.dialogs import entry_dialog
from pynicotine.gtkgui.utils import humanize
from pynicotine.gtkgui.utils import human_speed
from pynicotine.gtkgui.utils import initialise_columns
from pynicotine.gtkgui.utils import load_ui_elements
from pynicotine.gtkgui.utils import PopupMenu
from pynicotine.gtkgui.utils import save_columns
from pynicotine.gtkgui.utils import set_treeview_selected_row
from pynicotine.gtkgui.utils import show_country_tooltip
from pynicotine.gtkgui.utils import triggers_context_menu
from pynicotine.gtkgui.utils import update_widget_visuals
from pynicotine.logfacility import log


class UserList:

    def __init__(self, frame):

        # Build the window
        self.frame = frame
        config = self.frame.np.config.sections

        load_ui_elements(self, os.path.join(self.frame.gui_dir, "ui", "buddylist.ui"))

        """ Columns """

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
            GObject.TYPE_INT64,   # (10) status
            GObject.TYPE_UINT64,  # (11) speed
            GObject.TYPE_UINT64,  # (12) file count
            int,                  # (13) last seen
            str                   # (14) country
        )

        self.column_numbers = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]
        self.cols = cols = initialise_columns(
            "buddy_list",
            self.UserListTree,
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

        if config["columns"]["hideflags"]:
            cols["country"].set_visible(0)
            config["columns"]["buddy_list"]["country"]["visible"] = 0

        for render in cols["trusted"].get_cells():
            render.connect('toggled', self.cell_toggle_callback, self.UserListTree, 5)

        for render in cols["notify"].get_cells():
            render.connect('toggled', self.cell_toggle_callback, self.UserListTree, 6)

        for render in cols["privileged"].get_cells():
            render.connect('toggled', self.cell_toggle_callback, self.UserListTree, 7)

        for render in cols["comments"].get_cells():
            render.connect('edited', self.cell_edited_callback, self.UserListTree, 9)

        self.UserListTree.set_model(self.usersmodel)

        """ Buddy list """

        for user in self.frame.np.config.sections["server"]["userlist"]:
            try:
                username, comment, notify, privileged, trusted, last_seen, country = user
            except ValueError:
                # Invalid user row
                continue

            try:
                time_from_epoch = time.mktime(time.strptime(last_seen, "%m/%d/%Y %H:%M:%S"))
            except ValueError:
                last_seen = _("Never seen")
                time_from_epoch = 0

            row = [
                self.frame.get_status_image(0),
                self.frame.get_flag_image(country),
                str(username),
                "",
                "",
                trusted,
                notify,
                privileged,
                str(last_seen),
                str(comment),
                0,
                0,
                0,
                time_from_epoch,
                str(country)
            ]

            self.usersmodel.insert(0, row)

        self.usersmodel.set_sort_column_id(2, Gtk.SortType.ASCENDING)

        self.buddies_combo_entries = (
            self.frame.UserSearchCombo, self.frame.PrivateChatCombo, self.frame.UserInfoCombo, self.frame.UserBrowseCombo
        )

        self.buddies_combos_fill()

        """ Popup """

        self.popup_menu_private_rooms = PopupMenu(self.frame, False)
        self.popup_menu = popup = PopupMenu(frame)
        popup.setup_user_menu()
        popup.get_items()[_("_Add User To List")].set_visible(False)

        popup.append_item(("", None))
        popup.append_item(("$" + _("_Online Notify"), self.on_notify))
        popup.append_item(("$" + _("_Privileged"), self.on_privileged))
        popup.append_item(("$" + _("_Trusted"), self.on_trusted))
        popup.append_item(("", None))
        popup.append_item((1, _("Private Rooms"), self.popup_menu_private_rooms, popup.on_private_rooms, self.popup_menu_private_rooms))
        popup.append_item(("#" + _("Edit _Comments"), self.on_edit_comments))
        popup.append_item(("#" + _("_Remove"), self.on_remove_user))

        self.update_visuals()

    def buddies_combos_fill(self):

        for widget in self.buddies_combo_entries:
            widget.remove_all()
            widget.append_text("")

            for user in self.frame.np.config.sections["server"]["userlist"]:
                widget.append_text(str(user[0]))

    def on_tooltip(self, widget, x, y, keyboard_mode, tooltip):
        return show_country_tooltip(widget, x, y, tooltip, 14)

    def on_add_user(self, widget, *args):

        text = widget.get_text()

        if not text:
            return

        widget.set_text("")
        self.add_to_list(text)

    def update_visuals(self):

        for widget in self.__dict__.values():
            update_widget_visuals(widget)

    def on_settings_ban_ignore(self, widget):
        self.frame.on_settings_ban_ignore(widget)

    def cell_toggle_callback(self, widget, index, treeview, pos):

        iterator = self.usersmodel.get_iter(index)
        value = self.usersmodel.get_value(iterator, pos)

        self.usersmodel.set_value(iterator, pos, not value)

        self.save_user_list()

    def cell_edited_callback(self, widget, index, value, treeview, pos):

        store = treeview.get_model()
        iterator = store.get_iter(index)

        if pos == 9:
            self.set_comment(iterator, store, value)

    def set_last_seen(self, user, online=False):

        last_seen = ""
        time_from_epoch = 2147483647  # Gtk only allows range -2147483648 to 2147483647 in set()

        if not online:
            last_seen = time.strftime("%m/%d/%Y %H:%M:%S")
            time_from_epoch = time.mktime(time.strptime(last_seen, "%m/%d/%Y %H:%M:%S"))

        for i in self.usersmodel:
            if i[2] == user:
                self.usersmodel.set_value(i.iter, 8, last_seen)
                self.usersmodel.set_value(i.iter, 13, int(time_from_epoch))
                break

        if not online:
            self.save_user_list()

    def set_comment(self, iterator, store, comments=None):

        user = store.get_value(iterator, 2)

        if comments is not None:

            for i in self.usersmodel:
                if i[2] == user:
                    self.usersmodel.set_value(iterator, 9, comments)
                    break

            self.save_user_list()

    def conn_close(self):

        for i in self.usersmodel:
            iterator = i.iter

            self.usersmodel.set_value(iterator, 0, GObject.Value(GObject.TYPE_OBJECT, self.frame.get_status_image(0)))
            self.usersmodel.set_value(iterator, 3, "")
            self.usersmodel.set_value(iterator, 4, "")
            self.usersmodel.set_value(iterator, 10, 0)
            self.usersmodel.set_value(iterator, 11, 0)
            self.usersmodel.set_value(iterator, 12, 0)

            if self.usersmodel.get(iterator, 8)[0] == "":
                user = i[2]
                self.set_last_seen(user)

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

    def on_list_clicked(self, widget, event):

        if triggers_context_menu(event):
            set_treeview_selected_row(widget, event)
            return self.on_popup_menu(widget)

        if event.type == Gdk.EventType._2BUTTON_PRESS:
            user = self.get_selected_username(widget)

            if user is not None:
                self.frame.privatechats.send_message(user, show_user=True)
                self.frame.change_main_page("private")
                return True

        return False

    def on_popup_menu(self, widget):

        username, trusted, notify, privileged, status = self.get_selected_username_details(widget)
        if username is None:
            return False

        self.popup_menu.set_user(username)
        self.popup_menu.toggle_user_items()

        items = self.popup_menu.get_items()

        items[_("Private Rooms")].set_sensitive(
            status or
            self.popup_menu.user != self.frame.np.config.sections["server"]["login"]
        )

        items[_("_Online Notify")].set_active(notify)
        items[_("_Privileged")].set_active(privileged)
        items[_("_Trusted")].set_active(trusted)

        self.popup_menu.popup()
        return True

    def get_iter(self, user):

        for i in self.usersmodel:
            if i[2] == user:
                return i.iter

        return None

    def get_user_status(self, msg):

        status = msg.status

        if status < 0:
            # User doesn't exist, nothing to do
            return

        user = msg.user
        iterator = self.get_iter(user)

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
            self.frame.notifications.new_notification(status_text % user)

        img = self.frame.get_status_image(status)
        self.usersmodel.set_value(iterator, 0, GObject.Value(GObject.TYPE_OBJECT, img))
        self.usersmodel.set_value(iterator, 10, GObject.Value(GObject.TYPE_INT64, status))

        if status:  # online
            self.set_last_seen(user, online=True)
        elif self.usersmodel.get(iterator, 8)[0] == "":  # disconnected
            self.set_last_seen(user)

    def get_user_stats(self, msg):

        user = msg.user
        iterator = self.get_iter(user)

        if iterator is None:
            return

        hspeed = human_speed(msg.avgspeed)
        hfiles = humanize(msg.files)

        self.usersmodel.set_value(iterator, 3, hspeed)
        self.usersmodel.set_value(iterator, 4, hfiles)
        self.usersmodel.set_value(iterator, 11, GObject.Value(GObject.TYPE_UINT64, msg.avgspeed))
        self.usersmodel.set_value(iterator, 12, GObject.Value(GObject.TYPE_UINT64, msg.files))

    def set_user_flag(self, user, country):

        iterator = self.get_iter(user)
        if iterator is None:
            return

        if user not in (i[2] for i in self.usersmodel):
            return

        self.usersmodel.set_value(iterator, 1, GObject.Value(GObject.TYPE_OBJECT, self.frame.get_flag_image(country)))
        self.usersmodel.set_value(iterator, 14, "flag_" + country)

    def add_to_list(self, user):

        if user in (i[2] for i in self.usersmodel):
            return

        empty_int = 0
        empty_str = ""

        self.usersmodel.insert_with_valuesv(
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
        self.frame.np.queue.put(slskmessages.AddUser(user))

        # Request user's IP address, so we can get the country
        self.frame.np.queue.put(slskmessages.GetPeerAddress(user))

        for widget in self.buddies_combo_entries:
            widget.append_text(user)

        if self.frame.np.config.sections["words"]["buddies"]:
            GLib.idle_add(self.frame.chatrooms.update_completions)
            GLib.idle_add(self.frame.privatechats.update_completions)

    def on_edit_comments(self, widget):

        user = self.popup_menu.get_user()

        for i in self.usersmodel:
            if i[2] == user:
                comments = i[9]
                break
        else:
            comments = ""

        comments = entry_dialog(self.frame.MainWindow, _("Edit comments") + "...", _("Comments") + ":", comments)

        if comments is not None:
            for i in self.usersmodel:
                if i[2] == user:
                    i[9] = comments
                    self.usersmodel.set_value(i.iter, 9, comments)
                    break

            self.save_user_list()

    def save_user_list(self):

        user_list = []

        for i in self.usersmodel:
            status_icon, flag, user, hspeed, hfile_count, trusted, notify, privileged, hlast_seen, comments, status, speed, file_count, last_seen, country = i
            user_list.append([user, comments, notify, privileged, trusted, hlast_seen, country])

        self.frame.np.config.sections["server"]["userlist"] = user_list
        self.frame.np.config.write_configuration()

    def save_columns(self):
        save_columns("buddy_list", self.UserListTree.get_columns())

    def remove_from_list(self, user):

        for i in self.usersmodel:
            if i[2] == user:
                self.usersmodel.remove(i.iter)
                break

        self.save_user_list()

        self.buddies_combos_fill()

        if self.frame.np.config.sections["words"]["buddies"]:
            GLib.idle_add(self.frame.chatrooms.update_completions)
            GLib.idle_add(self.frame.privatechats.update_completions)

    def on_remove_user(self, widget):
        self.remove_from_list(self.popup_menu.get_user())

    def on_trusted(self, widget):

        user = self.popup_menu.get_user()

        for i in self.usersmodel:
            if i[2] == user:
                self.usersmodel.set_value(i.iter, 5, widget.get_active())
                break

        self.save_user_list()

    def on_notify(self, widget):

        user = self.popup_menu.get_user()

        for i in self.usersmodel:
            if i[2] == user:
                self.usersmodel.set_value(i.iter, 6, widget.get_active())
                break

        self.save_user_list()

    def on_privileged(self, widget):

        user = self.popup_menu.get_user()

        for i in self.usersmodel:
            if i[2] == user:
                self.usersmodel.set_value(i.iter, 7, widget.get_active())
                break

        self.save_user_list()
