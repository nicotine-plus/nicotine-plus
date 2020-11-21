# COPYRIGHT (C) 2020 Nicotine+ Team
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
from gettext import gettext as _

from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk

from pynicotine import slskmessages
from pynicotine.gtkgui.dialogs import entry_dialog
from pynicotine.gtkgui.utils import hide_columns
from pynicotine.gtkgui.utils import humanize
from pynicotine.gtkgui.utils import human_speed
from pynicotine.gtkgui.utils import initialise_columns
from pynicotine.gtkgui.utils import load_ui_elements
from pynicotine.gtkgui.utils import PopupMenu
from pynicotine.gtkgui.utils import show_country_tooltip
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

        widths = self.frame.np.config.sections["columns"]["userlist_widths"]
        self.cols = cols = initialise_columns(
            self.UserListTree,
            [_("Status"), widths[0], "pixbuf"],
            [_("Country"), widths[1], "pixbuf"],
            [_("User"), widths[2], "text"],
            [_("Speed"), widths[3], "number"],
            [_("Files"), widths[4], "number"],
            [_("Trusted"), widths[5], "toggle"],
            [_("Notify"), widths[6], "toggle"],
            [_("Privileged"), widths[7], "toggle"],
            [_("Last seen"), widths[8], "text"],
            [_("Comments"), widths[9], "edit"]
        )

        self.col_status, self.col_country, self.col_user, self.col_speed, self.col_files, self.col_trusted, self.col_notify, self.col_privileged, self.col_last_seen, self.col_comments = cols

        hide_columns(cols, config["columns"]["userlist"])

        self.col_status.set_sort_column_id(10)
        self.col_country.set_sort_column_id(14)
        self.col_user.set_sort_column_id(2)
        self.col_speed.set_sort_column_id(11)
        self.col_files.set_sort_column_id(12)
        self.col_trusted.set_sort_column_id(5)
        self.col_notify.set_sort_column_id(6)
        self.col_privileged.set_sort_column_id(7)
        self.col_last_seen.set_sort_column_id(13)
        self.col_comments.set_sort_column_id(9)

        self.col_status.get_widget().hide()
        self.col_country.get_widget().hide()

        if config["columns"]["hideflags"]:
            cols[1].set_visible(0)
            config["columns"]["userlist"][1] = 0

        for render in self.col_trusted.get_cells():
            render.connect('toggled', self.cell_toggle_callback, self.UserListTree, 5)

        for render in self.col_notify.get_cells():
            render.connect('toggled', self.cell_toggle_callback, self.UserListTree, 6)

        for render in self.col_privileged.get_cells():
            render.connect('toggled', self.cell_toggle_callback, self.UserListTree, 7)

        for render in self.col_comments.get_cells():
            render.connect('edited', self.cell_edited_callback, self.UserListTree, 9)

        self.UserListTree.set_model(self.usersmodel)

        """ Buddy list """

        for user in self.frame.np.config.sections["server"]["userlist"]:
            username, comment, notify, privileged, trusted, last_seen, country = user

            try:
                time_from_epoch = time.mktime(time.strptime(last_seen, "%m/%d/%Y %H:%M:%S"))
            except ValueError:
                last_seen = _("Never seen")
                time_from_epoch = 0

            row = [
                self.frame.get_status_image(0),
                self.frame.get_flag_image(country),
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

            self.usersmodel.insert(0, row)

        self.usersmodel.set_sort_column_id(2, Gtk.SortType.ASCENDING)

        """ Popup """

        self.popup_menu_private_rooms = PopupMenu(self.frame, False)
        self.popup_menu = popup = PopupMenu(frame)

        popup.setup(
            ("#" + _("Send _message"), popup.on_send_message),
            ("", None),
            ("#" + _("Show IP a_ddress"), popup.on_show_ip_address),
            ("#" + _("Get user i_nfo"), popup.on_get_user_info),
            ("#" + _("Brow_se files"), popup.on_browse_user),
            ("#" + _("Gi_ve privileges"), popup.on_give_privileges),
            ("$" + _("_Ban this user"), popup.on_ban_user),
            ("$" + _("_Ignore this user"), popup.on_ignore_user),
            ("", None),
            ("$" + _("_Online notify"), self.on_notify),
            ("$" + _("_Privileged"), self.on_privileged),
            ("$" + _("_Trusted"), self.on_trusted),
            ("", None),
            ("#" + _("Edit _comments"), self.on_edit_comments),
            ("#" + _("_Remove"), self.on_remove_user),
            (1, _("Private rooms"), self.popup_menu_private_rooms, popup.on_private_rooms, self.popup_menu_private_rooms)
        )

        items = self.popup_menu.get_children()
        self.menu_send_message = items[0]
        self.menu_show_ip_address = items[2]
        self.menu_get_user_info = items[3]
        self.menu_browse_user = items[4]
        self.menu_give_privileges = items[5]
        self.menu_ban_user = items[6]
        self.menu_ignore_user = items[7]
        self.menu_on_notify = items[9]
        self.menu_on_privileged = items[10]
        self.menu_on_trusted = items[11]
        self.menu_edit_comments = items[13]
        self.menu_remove_user = items[14]
        self.menu_private_rooms = items[15]

        self.UserListTree.connect("button_press_event", self.on_popup_menu)

        self.update_visuals()

    def on_tooltip(self, widget, x, y, keyboard_mode, tooltip):
        return show_country_tooltip(widget, x, y, tooltip, 14, 'flag_')

    def on_add_user(self, widget):

        text = self.AddUserEntry.get_text()
        if not text:
            return

        self.AddUserEntry.set_text("")
        self.add_to_list(text)

    def update_visuals(self):

        for widget in self.__dict__.values():
            update_widget_visuals(widget)

    def on_settings_ban_ignore(self, widget):
        self.frame.on_settings_ban_ignore(widget)

    def cell_toggle_callback(self, widget, index, treeview, pos):

        iterator = self.usersmodel.get_iter(index)
        value = self.usersmodel.get_value(iterator, pos)

        self.usersmodel.set(iterator, pos, not value)

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
                self.usersmodel.set(i.iter, 8, last_seen)
                self.usersmodel.set(i.iter, 13, int(time_from_epoch))
                break

        if not online:
            self.save_user_list()

    def set_comment(self, iterator, store, comments=None):

        user = store.get_value(iterator, 2)

        if comments is not None:

            for i in self.usersmodel:
                if i[2] == user:
                    self.usersmodel.set(iterator, 9, comments)
                    break

            self.save_user_list()

    def conn_close(self):

        for i in self.usersmodel:
            self.usersmodel.set(
                i.iter,
                0, self.frame.get_status_image(0),
                3, "",
                4, "",
                10, 0,
                11, 0,
                12, 0
            )

            if self.usersmodel.get(i.iter, 8)[0] == "":
                user = i[2]
                self.set_last_seen(user)

    def on_popup_menu(self, widget, event):

        d = self.UserListTree.get_path_at_pos(int(event.x), int(event.y))

        if d:
            path, column, x, y = d
            model = self.UserListTree.get_model()
            iterator = model.get_iter(path)
            user = model.get_value(iterator, 2)
            status = model.get_value(iterator, 10)

            if event.button != 3:
                if event.type == Gdk.EventType._2BUTTON_PRESS:
                    self.frame.privatechats.send_message(user, show_user=True)
                    self.frame.change_main_page("private")
                return

            self.popup_menu.set_user(user)

            self.menu_send_message.set_sensitive(status)
            self.menu_show_ip_address.set_sensitive(status)
            self.menu_get_user_info.set_sensitive(status)
            self.menu_browse_user.set_sensitive(status)
            self.menu_give_privileges.set_sensitive(status)
            self.menu_private_rooms.set_sensitive(
                status or
                self.popup_menu.user != self.frame.np.config.sections["server"]["login"]
            )

            self.menu_ban_user.set_active(user in self.frame.np.config.sections["server"]["banlist"])
            self.menu_ignore_user.set_active(user in self.frame.np.config.sections["server"]["ignorelist"])
            self.menu_on_notify.set_active(model.get_value(iterator, 6))
            self.menu_on_privileged.set_active(model.get_value(iterator, 7))
            self.menu_on_trusted.set_active(model.get_value(iterator, 5))

            self.popup_menu.popup(None, None, None, None, event.button, event.time)

    def get_iter(self, user):

        for i in self.usersmodel:
            if i[2] == user:
                return i.iter

        return None

    def get_user_status(self, msg):

        user = msg.user
        status = msg.status
        iterator = self.get_iter(user)

        if iterator is None:
            return

        if status == int(self.usersmodel.get_value(iterator, 10)):
            return

        notify = self.usersmodel.get_value(iterator, 6)

        if notify:
            status_text = [_("User %s is offline"), _("User %s is away"), _("User %s is online")][status]
            log.add(status_text, user)
            self.frame.notifications.new_notification(status_text % user)

        img = self.frame.get_status_image(status)
        self.usersmodel.set(
            iterator,
            0, img,
            10, status
        )

        if status:  # online
            self.set_last_seen(user, online=True)
        elif self.usersmodel.get(iterator, 8)[0] == "":  # disconnected
            self.set_last_seen(user)

    def get_user_stats(self, msg):

        user = msg.user
        iterator = self.get_iter(user)

        if iterator is None:
            return

        country = msg.country
        hspeed = human_speed(msg.avgspeed)
        hfiles = humanize(msg.files)

        self.usersmodel.set(
            iterator,
            3, hspeed,
            4, hfiles,
            11, msg.avgspeed,
            12, msg.files
        )

        if country is not None and country != "":

            country = "flag_" + country
            self.set_user_flag(user, country)

    def set_user_flag(self, user, country):

        iterator = self.get_iter(user)
        if iterator is None:
            return

        if user not in (i[2] for i in self.usersmodel):
            return

        self.usersmodel.set(
            iterator,
            1, self.frame.get_flag_image(country),
            14, country
        )

    def add_to_list(self, user):

        if user in (i[2] for i in self.usersmodel):
            return

        row = [self.frame.get_status_image(0), None, user, "", "", False, False, False, _("Never seen"), "", 0, 0, 0, 0, ""]
        self.usersmodel.append(row)

        self.save_user_list()
        self.frame.np.queue.put(slskmessages.AddUser(user))
        self.frame.np.queue.put(slskmessages.GetPeerAddress(user))

        for widget in self.frame.buddies_combo_entries:
            GLib.idle_add(widget.append, user)

        if self.frame.np.config.sections["words"]["buddies"]:
            GLib.idle_add(self.frame.chatrooms.roomsctrl.update_completions)
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
                    self.usersmodel.set(i.iter, 9, comments)
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

        columns = []
        widths = []

        for column in self.UserListTree.get_columns():
            columns.append(column.get_visible())
            widths.append(column.get_width())

        self.frame.np.config.sections["columns"]["userlist"] = columns
        self.frame.np.config.sections["columns"]["userlist_widths"] = widths

    def remove_from_list(self, user):

        for i in self.usersmodel:
            if i[2] == user:
                self.usersmodel.remove(i.iter)
                break

        self.save_user_list()

        for widget in self.frame.buddies_combo_entries:
            GLib.idle_add(widget.remove, user)

        if self.frame.np.config.sections["words"]["buddies"]:
            GLib.idle_add(self.frame.chatrooms.roomsctrl.update_completions)
            GLib.idle_add(self.frame.privatechats.update_completions)

    def on_remove_user(self, widget):
        self.remove_from_list(self.popup_menu.get_user())

    def on_trusted(self, widget):

        user = self.popup_menu.get_user()

        for i in self.usersmodel:
            if i[2] == user:
                self.usersmodel.set(i.iter, 5, widget.get_active())
                break

        self.save_user_list()

    def on_notify(self, widget):

        user = self.popup_menu.get_user()

        for i in self.usersmodel:
            if i[2] == user:
                self.usersmodel.set(i.iter, 6, widget.get_active())
                break

        self.save_user_list()

    def on_privileged(self, widget):

        user = self.popup_menu.get_user()

        for i in self.usersmodel:
            if i[2] == user:
                self.usersmodel.set(i.iter, 7, widget.get_active())
                break

        self.save_user_list()
