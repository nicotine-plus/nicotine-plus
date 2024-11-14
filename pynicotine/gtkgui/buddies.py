# COPYRIGHT (C) 2020-2024 Nicotine+ Contributors
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
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.widgets import ui
from pynicotine.gtkgui.widgets.dialogs import EntryDialog
from pynicotine.gtkgui.widgets.popupmenu import UserPopupMenu
from pynicotine.gtkgui.widgets.theme import USER_STATUS_ICON_NAMES
from pynicotine.gtkgui.widgets.theme import get_flag_icon_name
from pynicotine.gtkgui.widgets.treeview import TreeView
from pynicotine.slskmessages import UserStatus
from pynicotine.utils import UINT64_LIMIT
from pynicotine.utils import humanize
from pynicotine.utils import human_speed


class Buddies:

    def __init__(self, window):

        (
            self.container,
            self.list_container,
            self.side_toolbar
        ) = ui.load(scope=self, path="buddies.ui")

        self.window = window
        self.page = window.userlist_page
        self.page.id = "userlist"
        self.toolbar = window.userlist_toolbar
        self.toolbar_start_content = window.userlist_title
        self.toolbar_end_content = window.userlist_end
        self.toolbar_default_widget = window.add_buddy_entry

        # Columns
        self.list_view = TreeView(
            window, parent=self.list_container, name="buddy_list",
            persistent_sort=True, activate_row_callback=self.on_row_activated,
            delete_accelerator_callback=self.on_remove_buddy,
            columns={
                # Visible columns
                "status": {
                    "column_type": "icon",
                    "title": _("Status"),
                    "width": 25,
                    "hide_header": True
                },
                "country": {
                    "column_type": "icon",
                    "title": _("Country"),
                    "width": 30,
                    "hide_header": True
                },
                "user": {
                    "column_type": "text",
                    "title": _("User"),
                    "width": 250,
                    "default_sort_type": "ascending",
                    "iterator_key": True
                },
                "speed": {
                    "column_type": "number",
                    "title": _("Speed"),
                    "width": 150,
                    "sort_column": "speed_data"
                },
                "files": {
                    "column_type": "number",
                    "title": _("Files"),
                    "width": 150,
                    "sort_column": "files_data"
                },
                "trusted": {
                    "column_type": "toggle",
                    "title": _("Trusted"),
                    "width": 0,
                    "toggle_callback": self.on_trusted
                },
                "notify": {
                    "column_type": "toggle",
                    "title": _("Notify"),
                    "width": 0,
                    "toggle_callback": self.on_notify
                },
                "privileged": {
                    "column_type": "toggle",
                    "title": _("Prioritized"),
                    "width": 0,
                    "toggle_callback": self.on_prioritized
                },
                "last_seen": {
                    "column_type": "text",
                    "title": _("Last Seen"),
                    "width": 160,
                    "sort_column": "last_seen_data"
                },
                "comments": {
                    "column_type": "text",
                    "title": _("Note"),
                    "width": 400
                },

                # Hidden data columns
                "speed_data": {"data_type": GObject.TYPE_UINT},
                "files_data": {"data_type": GObject.TYPE_UINT},
                "last_seen_data": {"data_type": GObject.TYPE_UINT64}
            }
        )

        # Popup menus
        self.popup_menu = popup = UserPopupMenu(
            window.application, parent=self.list_view.widget, callback=self.on_popup_menu,
            tab_name="userlist"
        )
        popup.add_items(
            ("#" + _("Add User _Note…"), self.on_add_note),
            ("", None),
            ("#" + _("Remove"), self.on_remove_buddy)
        )

        # Events
        for event_name, callback in (
            ("add-buddy", self.add_buddy),
            ("buddy-note", self.buddy_note),
            ("buddy-notify", self.buddy_notify),
            ("buddy-last-seen", self.buddy_last_seen),
            ("buddy-prioritized", self.buddy_prioritized),
            ("buddy-trusted", self.buddy_trusted),
            ("remove-buddy", self.remove_buddy),
            ("server-disconnect", self.server_disconnect),
            ("start", self.start),
            ("user-country", self.user_country),
            ("user-stats", self.user_stats),
            ("user-status", self.user_status)
        ):
            events.connect(event_name, callback)

        self.set_buddy_list_position()

    def start(self):

        comboboxes = (
            self.window.search.user_search_combobox,
            self.window.userbrowse.userbrowse_combobox,
            self.window.userinfo.userinfo_combobox
        )

        for combobox in comboboxes:
            combobox.freeze()

        self.list_view.freeze()

        for username, user_data in core.buddies.users.items():
            self.add_buddy(username, user_data, select_row=False)

        for combobox in comboboxes:
            combobox.unfreeze()

        self.list_view.unfreeze()

    def destroy(self):

        self.list_view.destroy()
        self.popup_menu.destroy()

        self.__dict__.clear()

    def on_focus(self, *_args):

        self.update_visible()

        if self.container.get_parent().get_visible():
            self.list_view.grab_focus()
            return True

        return False

    def set_buddy_list_position(self):

        parent_container = self.container.get_parent()
        mode = config.sections["ui"]["buddylistinchatrooms"]

        if mode not in {"tab", "chatrooms", "always"}:
            mode = "tab"

        if parent_container == self.window.buddy_list_container:
            if mode == "always":
                return

            self.window.buddy_list_container.remove(self.container)
            self.window.buddy_list_container.set_visible(False)

        elif parent_container == self.window.chatrooms_buddy_list_container:
            if mode == "chatrooms":
                return

            self.window.chatrooms_buddy_list_container.remove(self.container)
            self.window.chatrooms_buddy_list_container.set_visible(False)

        elif parent_container == self.window.userlist_content:
            if mode == "tab":
                return

            self.window.userlist_content.remove(self.container)

        if mode == "always":
            if GTK_API_VERSION >= 4:
                self.window.buddy_list_container.append(self.container)
            else:
                self.window.buddy_list_container.add(self.container)

            self.side_toolbar.set_visible(True)
            self.window.buddy_list_container.set_visible(True)
            return

        if mode == "chatrooms":
            if GTK_API_VERSION >= 4:
                self.window.chatrooms_buddy_list_container.append(self.container)
            else:
                self.window.chatrooms_buddy_list_container.add(self.container)

            self.side_toolbar.set_visible(True)
            self.window.chatrooms_buddy_list_container.set_visible(True)
            return

        if mode == "tab":
            self.side_toolbar.set_visible(False)

            if GTK_API_VERSION >= 4:
                self.window.userlist_content.append(self.container)
            else:
                self.window.userlist_content.add(self.container)

    def update_visible(self):

        if config.sections["ui"]["buddylistinchatrooms"] in {"always", "chatrooms"}:
            return

        self.window.userlist_content.set_visible(bool(self.list_view.iterators))

    def get_selected_username(self):

        for iterator in self.list_view.get_selected_rows():
            return self.list_view.get_row_value(iterator, "user")

        return None

    def on_row_activated(self, _list_view, _iterator, column_id):

        user = self.get_selected_username()

        if user is None:
            return

        if column_id == "comments":
            self.on_add_note()
            return

        core.privatechat.show_user(user)

    def on_popup_menu(self, menu, _widget):

        username = self.get_selected_username()
        menu.set_user(username)
        menu.toggle_user_items()

    def user_status(self, msg):

        iterator = self.list_view.iterators.get(msg.user)

        if iterator is None:
            return

        status = msg.status
        status_icon_name = USER_STATUS_ICON_NAMES.get(status)

        if status_icon_name and status_icon_name != self.list_view.get_row_value(iterator, "status"):
            self.list_view.set_row_value(iterator, "status", status_icon_name)

    def user_stats(self, msg):

        iterator = self.list_view.iterators.get(msg.user)

        if iterator is None:
            return

        speed = msg.avgspeed or 0
        num_files = msg.files or 0
        column_ids = []
        column_values = []

        if speed != self.list_view.get_row_value(iterator, "speed_data"):
            h_speed = human_speed(speed) if speed > 0 else ""

            column_ids.extend(("speed", "speed_data"))
            column_values.extend((h_speed, speed))

        if num_files != self.list_view.get_row_value(iterator, "files_data"):
            h_num_files = humanize(num_files)

            column_ids.extend(("files", "files_data"))
            column_values.extend((h_num_files, num_files))

        if column_ids:
            self.list_view.set_row_values(iterator, column_ids, column_values)

    def add_buddy(self, user, user_data, select_row=True):

        status = user_data.status
        country_code = user_data.country

        if country_code:
            country_code = country_code.replace("flag_", "")

        stats = core.users.watched.get(user)

        if stats is not None:
            speed = stats.upload_speed or 0
            files = stats.files
        else:
            speed = 0
            files = None

        h_speed = human_speed(speed) if speed > 0 else ""
        h_files = humanize(files) if files is not None else ""
        last_seen = UINT64_LIMIT
        h_last_seen = ""

        if user_data.last_seen:
            try:
                last_seen_time = time.strptime(user_data.last_seen, "%m/%d/%Y %H:%M:%S")
                last_seen = time.mktime(last_seen_time)
                h_last_seen = time.strftime("%x %X", last_seen_time)

            except ValueError:
                last_seen = 0
                h_last_seen = _("Never seen")

        self.list_view.add_row([
            USER_STATUS_ICON_NAMES.get(status, ""),
            get_flag_icon_name(country_code),
            str(user),
            h_speed,
            h_files,
            bool(user_data.is_trusted),
            bool(user_data.notify_status),
            bool(user_data.is_prioritized),
            str(h_last_seen),
            str(user_data.note),
            speed,
            files or 0,
            last_seen
        ], select_row=select_row)

        for combobox in (
            self.window.search.user_search_combobox,
            self.window.userbrowse.userbrowse_combobox,
            self.window.userinfo.userinfo_combobox
        ):
            combobox.append(str(user))

        self.update_visible()

    def remove_buddy(self, user):

        iterator = self.list_view.iterators.get(user)

        if iterator is None:
            return

        self.list_view.remove_row(iterator)
        self.update_visible()

        for combobox in (
            self.window.search.user_search_combobox,
            self.window.userbrowse.userbrowse_combobox,
            self.window.userinfo.userinfo_combobox
        ):
            combobox.remove_id(user)

    def buddy_note(self, user, note):

        iterator = self.list_view.iterators.get(user)

        if iterator is not None:
            self.list_view.set_row_value(iterator, "comments", note)

    def buddy_trusted(self, user, trusted):

        iterator = self.list_view.iterators.get(user)

        if iterator is not None:
            self.list_view.set_row_value(iterator, "trusted", trusted)

    def buddy_notify(self, user, notify):

        iterator = self.list_view.iterators.get(user)

        if iterator is not None:
            self.list_view.set_row_value(iterator, "notify", notify)

    def buddy_prioritized(self, user, prioritized):

        iterator = self.list_view.iterators.get(user)

        if iterator is not None:
            self.list_view.set_row_value(iterator, "privileged", prioritized)

    def buddy_last_seen(self, user, online):

        iterator = self.list_view.iterators.get(user)

        if iterator is None:
            return

        last_seen = UINT64_LIMIT
        h_last_seen = ""

        if not online:
            last_seen = time.time()
            h_last_seen = time.strftime("%x %X", time.localtime(last_seen))

        self.list_view.set_row_values(
            iterator,
            column_ids=["last_seen", "last_seen_data"],
            values=[h_last_seen, last_seen]
        )

    def user_country(self, user, country_code):

        iterator = self.list_view.iterators.get(user)

        if iterator is None:
            return

        flag_icon_name = get_flag_icon_name(country_code)

        if flag_icon_name and flag_icon_name != self.list_view.get_row_value(iterator, "country"):
            self.list_view.set_row_value(iterator, "country", flag_icon_name)

    def on_add_buddy(self, *_args):

        username = self.window.add_buddy_entry.get_text().strip()

        if not username:
            return

        self.window.add_buddy_entry.set_text("")
        core.buddies.add_buddy(username)
        self.list_view.grab_focus()

    def on_remove_buddy(self, *_args):
        core.buddies.remove_buddy(self.get_selected_username())

    def on_trusted(self, list_view, iterator):

        user = list_view.get_row_value(iterator, "user")
        value = list_view.get_row_value(iterator, "trusted")

        core.buddies.set_buddy_trusted(user, not value)

    def on_notify(self, list_view, iterator):

        user = list_view.get_row_value(iterator, "user")
        value = list_view.get_row_value(iterator, "notify")

        core.buddies.set_buddy_notify(user, not value)

    def on_prioritized(self, list_view, iterator):

        user = list_view.get_row_value(iterator, "user")
        value = list_view.get_row_value(iterator, "privileged")

        core.buddies.set_buddy_prioritized(user, not value)

    def on_add_note_response(self, dialog, _response_id, user):

        iterator = self.list_view.iterators.get(user)

        if iterator is None:
            return

        note = dialog.get_entry_value()

        if note is None:
            return

        core.buddies.set_buddy_note(user, note)

    def on_add_note(self, *_args):

        user = self.get_selected_username()
        iterator = self.list_view.iterators.get(user)

        if iterator is None:
            return

        note = self.list_view.get_row_value(iterator, "comments") or ""

        EntryDialog(
            parent=self.window,
            title=_("Add User Note"),
            message=_("Add a note about user %s:") % user,
            action_button_label=_("_Add"),
            callback=self.on_add_note_response,
            callback_data=user,
            default=note
        ).present()

    def server_disconnect(self, *_args):
        for iterator in self.list_view.iterators.values():
            self.list_view.set_row_value(iterator, "status", USER_STATUS_ICON_NAMES[UserStatus.OFFLINE])
