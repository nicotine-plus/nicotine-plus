# COPYRIGHT (C) 2020-2023 Nicotine+ Contributors
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2016 Mutnick <muhing@yahoo.com>
# COPYRIGHT (C) 2008-2011 quinox <quinox@users.sf.net>
# COPYRIGHT (C) 2006-2009 daelstorm <daelstorm@gmail.com>
# COPYRIGHT (C) 2007 gallows <g4ll0ws@gmail.com>
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

from collections import deque

from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Pango

from pynicotine import slskmessages
from pynicotine.chatrooms import Tickers
from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.popovers.chatcommandhelp import ChatCommandHelp
from pynicotine.gtkgui.popovers.roomlist import RoomList
from pynicotine.gtkgui.popovers.roomwall import RoomWall
from pynicotine.gtkgui.widgets.iconnotebook import IconNotebook
from pynicotine.gtkgui.widgets.dialogs import OptionDialog
from pynicotine.gtkgui.widgets.popupmenu import PopupMenu
from pynicotine.gtkgui.widgets.popupmenu import UserPopupMenu
from pynicotine.gtkgui.widgets.textentry import ChatCompletion
from pynicotine.gtkgui.widgets.textentry import ChatEntry
from pynicotine.gtkgui.widgets.textentry import TextSearchBar
from pynicotine.gtkgui.widgets.textview import TextView
from pynicotine.gtkgui.widgets.theme import USER_STATUS_COLORS
from pynicotine.gtkgui.widgets.theme import USER_STATUS_ICON_NAMES
from pynicotine.gtkgui.widgets.theme import get_flag_icon_name
from pynicotine.gtkgui.widgets.treeview import initialise_columns
from pynicotine.gtkgui.widgets.treeview import save_columns
from pynicotine.gtkgui.widgets.treeview import show_country_tooltip
from pynicotine.gtkgui.widgets.treeview import show_user_status_tooltip
from pynicotine.gtkgui.widgets.ui import UserInterface
from pynicotine.logfacility import log
from pynicotine.slskmessages import UserStatus
from pynicotine.utils import clean_file
from pynicotine.utils import encode_path
from pynicotine.utils import humanize
from pynicotine.utils import human_speed
from pynicotine.utils import PUNCTUATION


class ChatRooms(IconNotebook):

    def __init__(self, window):

        super().__init__(
            window,
            parent=window.chatrooms_content,
            parent_page=window.chatrooms_page,
            switch_page_callback=self.on_switch_chat,
            reorder_page_callback=self.on_reordered_page
        )

        self.autojoin_rooms = set()
        self.highlighted_rooms = {}
        self.completion = ChatCompletion()
        self.roomlist = RoomList(window)
        self.command_help = None

        if GTK_API_VERSION >= 4:
            self.window.chatrooms_paned.set_resize_start_child(True)
        else:
            self.window.chatrooms_paned.child_set_property(self.window.chatrooms_container, "resize", True)

        for event_name, callback in (
            ("clear-room-messages", self.clear_room_messages),
            ("echo-room-message", self.echo_room_message),
            ("global-room-message", self.global_room_message),
            ("join-room", self.join_room),
            ("private-room-added", self.private_room_added),
            ("remove-room", self.remove_room),
            ("room-completion-list", self.set_completion_list),
            ("room-list", self.room_list),
            ("say-chat-room", self.say_chat_room),
            ("server-login", self.server_login),
            ("server-disconnect", self.server_disconnect),
            ("show-room", self.show_room),
            ("ticker-add", self.ticker_add),
            ("ticker-remove", self.ticker_remove),
            ("ticker-set", self.ticker_set),
            ("user-country", self.user_country),
            ("user-joined-room", self.user_joined_room),
            ("user-left-room", self.user_left_room),
            ("user-stats", self.user_stats),
            ("user-status", self.user_status)
        ):
            events.connect(event_name, callback)

    def on_reordered_page(self, notebook, _page, _page_num):

        room_tab_order = {}

        # Find position of opened autojoined rooms
        for room, room_page in self.pages.items():

            if room not in config.sections["server"]["autojoin"]:
                continue

            room_tab_order[notebook.page_num(room_page.container)] = room

        pos = 1000

        # Add closed autojoined rooms as well
        for room in config.sections["server"]["autojoin"]:
            if room not in self.pages:
                room_tab_order[pos] = room
                pos += 1

        # Sort by "position"
        rto = sorted(room_tab_order)
        new_autojoin = []
        for roomplace in rto:
            new_autojoin.append(room_tab_order[roomplace])

        # Save
        config.sections["server"]["autojoin"] = new_autojoin

    def on_switch_chat(self, _notebook, page, _page_num):

        if self.window.current_page_id != self.window.chatrooms_page.id:
            return

        for room, tab in self.pages.items():
            if tab.container != page:
                continue

            self.completion.set_entry(tab.chat_entry)
            tab.set_completion_list(core.chatrooms.completion_list[:])

            if self.command_help is None:
                self.command_help = ChatCommandHelp(window=self.window, interface="chatroom")

            self.command_help.widget.unparent()
            tab.help_button.set_popover(self.command_help.widget)

            if not tab.loaded:
                tab.load()

            # Remove highlight
            self.unhighlight_room(room)
            break

    def on_create_room_response(self, dialog, response_id, room):

        private = dialog.get_option_value()

        if response_id == 2:
            # Create a new room
            core.chatrooms.show_room(room, private)

    def on_create_room(self, *_args):

        room = self.window.chatrooms_entry.get_text().strip()

        if not room:
            return

        if room not in core.chatrooms.server_rooms and room not in core.chatrooms.private_rooms:
            OptionDialog(
                parent=self.window,
                title=_("Create New Room?"),
                message=_('Do you really want to create a new room "%s"?') % room,
                option_label=_("Make room private"),
                callback=self.on_create_room_response,
                callback_data=room
            ).show()

        else:
            core.chatrooms.show_room(room)

        self.window.chatrooms_entry.set_text("")

    def clear_room_messages(self, room):

        page = self.pages.get(room)

        if page is not None:
            page.chat_view.clear()
            page.activity_view.clear()

    def clear_notifications(self):

        if self.window.current_page_id != self.window.chatrooms_page.id:
            return

        page = self.get_current_page()

        for room, tab in self.pages.items():
            if tab.container == page:
                # Remove highlight
                self.unhighlight_room(room)
                break

    def room_list(self, msg):

        self.roomlist.set_room_list(msg.rooms, msg.ownedprivaterooms, msg.otherprivaterooms)

        if config.sections["words"]["roomnames"]:
            core.chatrooms.update_completions()
            core.privatechat.update_completions()

    def show_room(self, room):

        page = self.pages.get(room)

        if page is not None:
            self.set_current_page(page.container)
            self.window.change_main_page(self.window.chatrooms_page)

    def remove_room(self, room):

        page = self.pages.get(room)

        if page is None:
            return

        page.clear()
        self.remove_page(page.container)
        del self.pages[room]

        if room == core.chatrooms.GLOBAL_ROOM_NAME:
            self.roomlist.toggle_public_feed(False)
        else:
            self.window.room_search_combobox.remove_all()
            self.window.room_search_combobox.append_text("Joined Rooms ")

            for joined_room in self.pages:
                self.window.room_search_combobox.append_text(joined_room)

    def highlight_room(self, room, user):

        if not room or room in self.highlighted_rooms:
            return

        self.highlighted_rooms[room] = user
        self.window.application.notifications.update_title()
        self.window.application.tray_icon.update_icon()

        if config.sections["ui"]["urgencyhint"] and not self.window.is_active():
            self.window.application.notifications.set_urgency_hint(True)

    def unhighlight_room(self, room):

        if room not in self.highlighted_rooms:
            return

        del self.highlighted_rooms[room]
        self.window.application.notifications.update_title()
        self.window.application.tray_icon.update_icon()

    def join_room(self, msg):

        page = self.pages.get(msg.room)

        if page is not None:
            page.join_room(msg)
            return

        self.pages[msg.room] = tab = ChatRoom(self, msg.room, msg.users)

        self.append_page(tab.container, msg.room, focus_callback=tab.on_focus, close_callback=tab.on_leave_room)
        tab.set_label(self.get_tab_label_inner(tab.container))

        if msg.room in self.autojoin_rooms:
            self.autojoin_rooms.remove(msg.room)
        else:
            # Did not auto-join room, switch to tab
            core.chatrooms.show_room(msg.room)

        if msg.room == core.chatrooms.GLOBAL_ROOM_NAME:
            self.roomlist.toggle_public_feed(True)
        else:
            self.window.room_search_combobox.append_text(msg.room)

    def private_room_added(self, msg):
        user_count = 0
        self.roomlist.update_room(msg.room, user_count)

    def user_stats(self, msg):
        for page in self.pages.values():
            page.user_stats(msg)

    def user_status(self, msg):
        for page in self.pages.values():
            page.user_status(msg)

    def user_country(self, user, country):
        for page in self.pages.values():
            page.user_country(user, country)

    def user_joined_room(self, msg):

        page = self.pages.get(msg.room)

        if page is not None:
            page.user_joined_room(msg)

    def user_left_room(self, msg):

        page = self.pages.get(msg.room)

        if page is not None:
            page.user_left_room(msg)

    def ticker_set(self, msg):

        page = self.pages.get(msg.room)

        if page is not None:
            page.ticker_set(msg)

    def ticker_add(self, msg):

        page = self.pages.get(msg.room)

        if page is not None:
            page.ticker_add(msg)

    def ticker_remove(self, msg):

        page = self.pages.get(msg.room)

        if page is not None:
            page.ticker_remove(msg)

    def echo_room_message(self, room, text, message_type):

        page = self.pages.get(room)

        if page is not None:
            page.echo_room_message(text, message_type)

    def say_chat_room(self, msg):

        page = self.pages.get(msg.room)

        if page is not None:
            page.say_chat_room(msg)

    def global_room_message(self, msg):

        page = self.pages.get(core.chatrooms.GLOBAL_ROOM_NAME)

        if page is not None:
            page.say_chat_room(msg, is_global=True)

    def toggle_chat_buttons(self):
        for page in self.pages.values():
            page.toggle_chat_buttons()

    def set_completion_list(self, completion_list):

        page = self.get_current_page()

        for tab in self.pages.values():
            if tab.container == page:
                tab.set_completion_list(completion_list[:])
                break

    def update_tags(self):
        for page in self.pages.values():
            page.update_tags()

    def save_columns(self):

        for room in config.sections["columns"]["chat_room"].copy():
            if room not in self.pages:
                del config.sections["columns"]["chat_room"][room]

        for page in self.pages.values():
            page.save_columns()

    def server_login(self, msg):

        if not msg.success:
            return

        for room in config.sections["server"]["autojoin"]:
            if isinstance(room, str):
                self.autojoin_rooms.add(room)

    def server_disconnect(self, *_args):

        self.roomlist.clear()
        self.autojoin_rooms.clear()

        for page in self.pages.values():
            page.server_disconnect()


class ChatRoom:

    def __init__(self, chatrooms, room, users):

        ui_template = UserInterface(scope=self, path="chatrooms.ui")
        (
            self.activity_container,
            self.activity_search_bar,
            self.activity_search_entry,
            self.activity_view_container,
            self.auto_join_toggle,
            self.chat_container,
            self.chat_entry,
            self.chat_entry_row,
            self.chat_paned,
            self.chat_search_bar,
            self.chat_search_entry,
            self.chat_view_container,
            self.container,
            self.help_button,
            self.log_toggle,
            self.room_wall_button,
            self.speech_toggle,
            self.users_action_row,
            self.users_container,
            self.users_label,
            self.users_list_view,
            self.users_paned
        ) = ui_template.widgets

        self.chatrooms = chatrooms
        self.window = chatrooms.window
        self.room = room

        if GTK_API_VERSION >= 4:
            self.users_paned.set_resize_start_child(True)
            self.users_paned.set_shrink_start_child(False)
            self.users_paned.set_resize_end_child(False)
            self.users_paned.set_shrink_end_child(False)
            self.chat_paned.set_shrink_end_child(False)
        else:
            self.users_paned.child_set_property(self.chat_paned, "resize", True)
            self.users_paned.child_set_property(self.chat_paned, "shrink", False)
            self.users_paned.child_set_property(self.users_container, "resize", False)
            self.users_paned.child_set_property(self.users_container, "shrink", False)
            self.chat_paned.child_set_property(self.chat_container, "shrink", False)

        self.tickers = Tickers()
        self.room_wall = RoomWall(self.window, self)
        self.loaded = False

        self.users = {}

        self.activity_view = TextView(self.activity_view_container, editable=False, horizontal_margin=10,
                                      vertical_margin=5, pixels_below_lines=2)
        self.chat_view = TextView(self.chat_view_container, editable=False, horizontal_margin=10,
                                  vertical_margin=5, pixels_below_lines=2)

        # Event Text Search
        self.activity_search_bar = TextSearchBar(self.activity_view.widget, self.activity_search_bar,
                                                 self.activity_search_entry)

        # Chat Text Search
        self.chat_search_bar = TextSearchBar(self.chat_view.widget, self.chat_search_bar, self.chat_search_entry,
                                             controller_widget=self.chat_container, focus_widget=self.chat_entry)

        # Chat Entry
        ChatEntry(self.window.application, self.chat_entry, chatrooms.completion, room, slskmessages.SayChatroom,
                  core.chatrooms.send_message, is_chatroom=True)

        self.log_toggle.set_active(config.sections["logging"]["chatrooms"])
        if not self.log_toggle.get_active():
            self.log_toggle.set_active(self.room in config.sections["logging"]["rooms"])

        self.auto_join_toggle.set_active(room in config.sections["server"]["autojoin"])
        self.auto_join_toggle.connect("toggled", self.on_autojoin)

        self.toggle_chat_buttons()

        if room not in config.sections["columns"]["chat_room"]:
            config.sections["columns"]["chat_room"][room] = {}

        self.usersmodel = Gtk.ListStore(
            str,                  # (0)  status_icon
            str,                  # (1)  flag
            str,                  # (2)  username
            str,                  # (3)  h_speed
            str,                  # (4)  h_files
            int,                  # (5)  status
            GObject.TYPE_UINT,    # (6)  avgspeed
            GObject.TYPE_UINT,    # (7)  files
            str,                  # (8)  country
            Pango.Weight,         # (9)  username_weight
            Pango.Underline       # (10) username_underline
        )
        self.users_list_view.set_model(self.usersmodel)

        self.column_numbers = list(range(self.usersmodel.get_n_columns()))
        attribute_columns = (9, 10)
        self.cols = cols = initialise_columns(
            self.window, ("chat_room", room), self.users_list_view,
            ["status", _("Status"), 25, "icon", None],
            ["country", _("Country"), 30, "icon", None],
            ["user", _("User"), 155, "text", attribute_columns],
            ["speed", _("Speed"), 100, "number", None],
            ["files", _("Files"), -1, "number", None]
        )

        cols["status"].set_sort_column_id(5)
        cols["country"].set_sort_column_id(8)
        cols["user"].set_sort_column_id(2)
        cols["speed"].set_sort_column_id(6)
        cols["files"].set_sort_column_id(7)

        cols["status"].get_widget().set_visible(False)
        cols["country"].get_widget().set_visible(False)

        for userdata in users:
            self.add_user_row(userdata)

        self.usersmodel.set_sort_column_id(2, Gtk.SortType.ASCENDING)

        self.popup_menu_private_rooms_chat = UserPopupMenu(self.window.application)
        self.popup_menu_private_rooms_list = UserPopupMenu(self.window.application)

        self.popup_menu_user_chat = UserPopupMenu(self.window.application, self.chat_view.widget,
                                                  connect_events=False)
        self.popup_menu_user_list = UserPopupMenu(self.window.application, self.users_list_view,
                                                  self.on_popup_menu_user)

        for menu, menu_private_rooms in (
            (self.popup_menu_user_chat, self.popup_menu_private_rooms_chat),
            (self.popup_menu_user_list, self.popup_menu_private_rooms_list)
        ):
            menu.setup_user_menu()
            menu.add_items(
                ("", None),
                ("#" + _("Sear_ch User's Files"), menu.on_search_user),
                (">" + _("Private Rooms"), menu_private_rooms)
            )

        self.popup_menu_activity_view = PopupMenu(self.window.application, self.activity_view.widget,
                                                  self.on_popup_menu_log)
        self.popup_menu_activity_view.add_items(
            ("#" + _("Find…"), self.on_find_activity_log),
            ("", None),
            ("#" + _("Copy"), self.activity_view.on_copy_text),
            ("#" + _("Copy All"), self.activity_view.on_copy_all_text),
            ("", None),
            ("#" + _("Clear Activity View"), self.activity_view.on_clear_all_text),
            ("", None),
            ("#" + _("_Leave Room"), self.on_leave_room)
        )

        self.popup_menu_chat_view = PopupMenu(self.window.application, self.chat_view.widget, self.on_popup_menu_chat)
        self.popup_menu_chat_view.add_items(
            ("#" + _("Find…"), self.on_find_room_log),
            ("", None),
            ("#" + _("Copy"), self.chat_view.on_copy_text),
            ("#" + _("Copy Link"), self.chat_view.on_copy_link),
            ("#" + _("Copy All"), self.chat_view.on_copy_all_text),
            ("", None),
            ("#" + _("View Room Log"), self.on_view_room_log),
            ("#" + _("Delete Room Log…"), self.on_delete_room_log),
            ("", None),
            ("#" + _("Clear Message View"), self.chat_view.on_clear_all_text),
            ("#" + _("_Leave Room"), self.on_leave_room)
        )

        self.tab_menu = PopupMenu(self.window.application)
        self.tab_menu.add_items(
            ("#" + _("_Leave Room"), self.on_leave_room)
        )

        self.setup_public_feed()
        self.chat_entry.grab_focus()

        self.count_users()
        self.create_tags()
        self.read_room_logs()

    def load(self):

        # Get the X position of the rightmost edge of the user list, and set the width to 400
        window_width = self.window.get_width()
        position = (self.window.chatrooms_paned.get_position() or self.window.horizontal_paned.get_position()
                    or window_width)
        self.users_paned.set_position(position - 400)

        GLib.idle_add(self.read_room_logs_finished)
        self.loaded = True

    def clear(self):

        self.activity_view.clear()
        self.chat_view.clear()

        for menu in (self.popup_menu_private_rooms_chat, self.popup_menu_private_rooms_list,
                     self.popup_menu_user_chat, self.popup_menu_user_list, self.users_list_view.column_menu,
                     self.popup_menu_activity_view, self.popup_menu_chat_view, self.tab_menu):
            menu.clear()

    def set_label(self, label):
        self.tab_menu.set_parent(label)

    def setup_public_feed(self):

        if self.room != core.chatrooms.GLOBAL_ROOM_NAME:
            return

        for widget in (self.activity_container, self.users_container, self.chat_entry,
                       self.room_wall_button, self.help_button):
            widget.set_visible(False)

        self.users_action_row.remove(self.auto_join_toggle)

        if GTK_API_VERSION >= 4:
            self.chat_entry_row.append(self.auto_join_toggle)  # pylint: disable=no-member
        else:
            self.chat_entry_row.add(self.auto_join_toggle)     # pylint: disable=no-member

        self.speech_toggle.set_active(False)  # Public feed is jibberish and too fast for TTS
        self.chat_entry.set_sensitive(False)
        self.chat_entry_row.set_halign(Gtk.Align.END)

    def add_user_row(self, userdata):

        username = userdata.username
        status = userdata.status
        country_code = userdata.country or ""  # country can be None, ensure string is used
        status_icon_name = USER_STATUS_ICON_NAMES.get(status, "")
        flag_icon_name = get_flag_icon_name(country_code)
        h_speed = ""
        avgspeed = userdata.avgspeed

        if avgspeed > 0:
            h_speed = human_speed(avgspeed)

        files = userdata.files
        h_files = humanize(files)

        weight = Pango.Weight.NORMAL
        underline = Pango.Underline.NONE

        if self.room in core.chatrooms.private_rooms:
            if username == core.chatrooms.private_rooms[self.room]["owner"]:
                weight = Pango.Weight.BOLD
                underline = Pango.Underline.SINGLE

            elif username in core.chatrooms.private_rooms[self.room]["operators"]:
                weight = Pango.Weight.BOLD
                underline = Pango.Underline.NONE

        iterator = self.usersmodel.insert_with_valuesv(
            -1, self.column_numbers,
            [
                status_icon_name,
                flag_icon_name,
                username,
                h_speed,
                h_files,
                status,
                GObject.Value(GObject.TYPE_UINT, avgspeed),
                GObject.Value(GObject.TYPE_UINT, files),
                country_code,
                weight,
                underline
            ]
        )

        self.users[username] = iterator

    def read_room_logs_finished(self):

        self.activity_view.scroll_bottom()
        self.chat_view.scroll_bottom()

        self.activity_view.auto_scroll = self.chat_view.auto_scroll = True

    def read_room_logs(self):

        numlines = config.sections["logging"]["readroomlines"]

        if not numlines:
            return

        filename = f"{clean_file(self.room)}.log"
        path = os.path.join(config.sections["logging"]["roomlogsdir"], filename)

        try:
            self.append_log_lines(path, numlines)
        except OSError:
            pass

    def append_log_lines(self, path, numlines):

        with open(encode_path(path), "rb") as lines:
            # Only show as many log lines as specified in config
            lines = deque(lines, numlines)
            login = config.sections["server"]["login"]

            for line in lines:
                try:
                    line = line.decode("utf-8")

                except UnicodeDecodeError:
                    line = line.decode("latin-1")

                user = tag = usertag = None

                if " [" in line and "] " in line:
                    start = line.find(" [") + 2
                    end = line.find("] ", start)

                    if end > start:
                        user = line[start:end]
                        usertag = self.get_user_tag(user)

                        if user == login:
                            tag = self.tag_local

                        elif self.find_whole_word(login.lower(), line.lower(), after=end) > -1:
                            tag = self.tag_highlight

                        else:
                            tag = self.tag_remote

                elif "* " in line:
                    tag = self.tag_action

                if user != login:
                    self.chat_view.append_line(core.privatechat.censor_chat(line), tag=tag, username=user,
                                               usertag=usertag)
                else:
                    self.chat_view.append_line(line, tag=tag, username=user, usertag=usertag)

            if lines:
                timestamp_format = config.sections["logging"]["rooms_timestamp"]
                self.chat_view.append_line(_("--- old messages above ---"), tag=self.tag_highlight,
                                           timestamp_format=timestamp_format)

    def populate_user_menu(self, user, menu, menu_private_rooms):

        menu.set_user(user)
        menu.toggle_user_items()
        menu.populate_private_rooms(menu_private_rooms)

        private_rooms_enabled = (menu_private_rooms.items and menu.user != core.login_username)
        menu.actions[_("Private Rooms")].set_enabled(private_rooms_enabled)

    def on_find_activity_log(self, *_args):
        self.activity_search_bar.set_visible(True)

    def on_find_room_log(self, *_args):
        self.chat_search_bar.set_visible(True)

    @staticmethod
    def get_selected_username(treeview):

        model, iterator = treeview.get_selection().get_selected()

        if iterator is None:
            return None

        return model.get_value(iterator, 2)

    def on_row_activated(self, treeview, _path, _column):

        user = self.get_selected_username(treeview)

        if user is not None:
            core.userinfo.show_user(user)

    def on_popup_menu_user(self, menu, treeview):
        user = self.get_selected_username(treeview)
        self.populate_user_menu(user, menu, self.popup_menu_private_rooms_list)

    def on_popup_menu_log(self, menu, _textview):
        menu.actions[_("Copy")].set_enabled(self.activity_view.get_has_selection())

    def on_popup_menu_chat(self, menu, _textview):
        menu.actions[_("Copy")].set_enabled(self.chat_view.get_has_selection())
        menu.actions[_("Copy Link")].set_enabled(bool(self.chat_view.get_url_for_current_pos()))

    def toggle_chat_buttons(self):
        self.speech_toggle.set_visible(config.sections["ui"]["speechenabled"])

    def ticker_set(self, msg):

        self.tickers.clear_tickers()

        for user, message in msg.msgs:
            if core.network_filter.is_user_ignored(user) or \
                    core.network_filter.is_user_ip_ignored(user):
                # User ignored, ignore Ticker messages
                continue

            self.tickers.add_ticker(user, message)

    def ticker_add(self, msg):

        user = msg.user

        if core.network_filter.is_user_ignored(user) or core.network_filter.is_user_ip_ignored(user):
            # User ignored, ignore Ticker messages
            return

        self.tickers.add_ticker(msg.user, msg.msg)

    def ticker_remove(self, msg):
        self.tickers.remove_ticker(msg.user)

    def show_notification(self, login, room, user, text, tag, is_global=False):

        if user == login:
            return

        mentioned = (tag == self.tag_highlight)
        self.chatrooms.request_tab_changed(self.container, is_important=mentioned)

        if is_global and room in core.chatrooms.joined_rooms:
            # Don't show notifications about the Public feed that's duplicated in an open tab
            return

        if mentioned:
            log.add(_("%(user)s mentioned you in room %(room)s") % {"user": user, "room": room})

            if config.sections["notifications"]["notification_popup_chatroom_mention"]:
                core.notifications.show_chatroom_notification(
                    room, text,
                    title=_("Mentioned by %(user)s in Room %(room)s") % {"user": user, "room": room},
                    high_priority=True
                )

        if (self.chatrooms.get_current_page() == self.container
                and self.window.current_page_id == self.window.chatrooms_page.id and self.window.is_active()):
            # Don't show notifications if the chat is open and the window is in use
            return

        if mentioned:
            # We were mentioned, update tray icon and show urgency hint
            self.chatrooms.highlight_room(room, user)
            return

        if not is_global and config.sections["notifications"]["notification_popup_chatroom"]:
            # Don't show notifications for public feed room, they're too noisy
            core.notifications.show_chatroom_notification(
                room, text,
                title=_("Message by %(user)s in Room %(room)s") % {"user": user, "room": room}
            )

    @staticmethod
    def find_whole_word(word, text, after=0):
        """ Returns start position of a whole word that is not in a subword """

        if word not in text:
            return -1

        word_boundaries = [" "] + PUNCTUATION
        whole = False
        start = 0

        while not whole and start > -1:
            start = text.find(word, after)
            after = start + len(word)

            whole = ((text[after] if after < len(text) else " ") in word_boundaries
                     and (text[start - 1] if start > 0 else " ") in word_boundaries)

        return start if whole else -1

    def say_chat_room(self, msg, is_global=False):

        user = msg.user
        login_username = core.login_username
        text = msg.msg
        room = msg.room

        if user == login_username:
            tag = self.tag_local
        elif self.find_whole_word(login_username.lower(), text.lower()) > -1:
            tag = self.tag_highlight
        else:
            tag = self.tag_remote

        if text.startswith("/me "):
            tag = self.tag_action
            line = f"* {user} {text[4:]}"
            speech = line[2:]
        else:
            line = f"[{user}] {text}"
            speech = text

        if is_global:
            line = f"{room} | {line}"

        line = "\n-- ".join(line.split("\n"))
        usertag = self.get_user_tag(user)
        timestamp_format = config.sections["logging"]["rooms_timestamp"]

        if user != login_username:
            self.chat_view.append_line(
                core.privatechat.censor_chat(line), tag=tag,
                username=user, usertag=usertag, timestamp_format=timestamp_format
            )

            if self.speech_toggle.get_active():
                core.notifications.new_tts(
                    config.sections["ui"]["speechrooms"], {"room": room, "user": user, "message": speech}
                )

        else:
            self.chat_view.append_line(
                line, tag=tag,
                username=user, usertag=usertag, timestamp_format=timestamp_format
            )

        self.show_notification(login_username, room, user, speech, tag, is_global)

        if self.log_toggle.get_active():
            log.write_log_file(
                folder_path=config.sections["logging"]["roomlogsdir"],
                base_name=f"{clean_file(self.room)}.log", text=line
            )

    def echo_room_message(self, text, message_type):

        if hasattr(self, f"tag_{message_type}"):
            tag = getattr(self, f"tag_{message_type}")
        else:
            tag = self.tag_local

        if message_type != "command":
            timestamp_format = config.sections["logging"]["rooms_timestamp"]
        else:
            timestamp_format = None

        self.chat_view.append_line(text, tag, timestamp_format=timestamp_format)

    def user_joined_room(self, msg):

        userdata = msg.userdata
        username = userdata.username

        if username in self.users:
            return

        # Add to completion list, and completion drop-down
        self.chatrooms.completion.add_completion(username)

        if not core.network_filter.is_user_ignored(username) and not core.network_filter.is_user_ip_ignored(username):
            self.activity_view.append_line(
                _("%s joined the room") % username, tag=self.tag_log,
                timestamp_format=config.sections["logging"]["rooms_timestamp"]
            )

        self.add_user_row(userdata)

        self.update_user_tag(username)
        self.count_users()

    def user_left_room(self, msg):

        username = msg.username

        if username not in self.users:
            return

        # Remove from completion list, and completion drop-down
        if username not in core.userlist.buddies:
            self.chatrooms.completion.remove_completion(username)

        if not core.network_filter.is_user_ignored(username) and \
                not core.network_filter.is_user_ip_ignored(username):
            timestamp_format = config.sections["logging"]["rooms_timestamp"]
            self.activity_view.append_line(_("%s left the room") % username, tag=self.tag_log,
                                           timestamp_format=timestamp_format)

        self.usersmodel.remove(self.users[username])
        del self.users[username]

        self.update_user_tag(username)
        self.count_users()

    def count_users(self):

        user_count = len(self.users)
        self.users_label.set_text(humanize(user_count))
        self.chatrooms.roomlist.update_room(self.room, user_count)

    def user_stats(self, msg):

        iterator = self.users.get(msg.user)

        if iterator is None:
            return

        speed = msg.avgspeed
        num_files = msg.files
        h_speed = ""

        if speed > 0:
            h_speed = human_speed(speed)

        self.usersmodel.set_value(iterator, 3, h_speed)
        self.usersmodel.set_value(iterator, 4, humanize(num_files))
        self.usersmodel.set_value(iterator, 6, GObject.Value(GObject.TYPE_UINT, speed))
        self.usersmodel.set_value(iterator, 7, GObject.Value(GObject.TYPE_UINT, num_files))

    def user_status(self, msg):

        user = msg.user
        iterator = self.users.get(user)

        if iterator is None:
            return

        status = msg.status
        status_icon_name = USER_STATUS_ICON_NAMES.get(status)

        if not status_icon_name:
            return

        if status == self.usersmodel.get_value(iterator, 5):
            return

        if status == UserStatus.AWAY:
            action = _("%s has gone away")

        elif status == UserStatus.ONLINE:
            action = _("%s has returned")

        else:
            # If we reach this point, the server did something wrong. The user should have
            # left the room before an offline status is sent.
            return

        if not core.network_filter.is_user_ignored(user) and not core.network_filter.is_user_ip_ignored(user):
            self.activity_view.append_line(
                action % user, tag=self.tag_log, timestamp_format=config.sections["logging"]["rooms_timestamp"])

        self.usersmodel.set_value(iterator, 0, status_icon_name)
        self.usersmodel.set_value(iterator, 5, status)

        self.update_user_tag(user)

    def user_country(self, user, country_code):

        iterator = self.users.get(user)

        if iterator is None:
            return

        if self.usersmodel.get_value(iterator, 8) == country_code:
            # Country didn't change, no need to update
            return

        flag_icon_name = get_flag_icon_name(country_code)

        if not flag_icon_name:
            return

        self.usersmodel.set_value(iterator, 1, flag_icon_name)
        self.usersmodel.set_value(iterator, 8, country_code)

    def user_name_event(self, pos_x, pos_y, user):

        menu = self.popup_menu_user_chat
        menu.update_model()
        self.populate_user_menu(user, menu, self.popup_menu_private_rooms_chat)
        menu.popup(pos_x, pos_y)

    def create_tags(self):

        self.tag_log = self.activity_view.create_tag("chatremote")

        self.tag_remote = self.chat_view.create_tag("chatremote")
        self.tag_local = self.chat_view.create_tag("chatlocal")
        self.tag_command = self.chat_view.create_tag("chatcommand")
        self.tag_action = self.chat_view.create_tag("chatme")
        self.tag_highlight = self.chat_view.create_tag("chathilite")

        self.tag_users = {}

    def get_user_tag(self, username):

        if username not in self.tag_users:
            self.tag_users[username] = self.chat_view.create_tag(callback=self.user_name_event, username=username)
            self.update_user_tag(username)

        return self.tag_users[username]

    def update_user_tag(self, username):

        if username not in self.tag_users:
            return

        if username not in self.users:
            color = "useroffline"
        else:
            status = self.usersmodel.get_value(self.users[username], 5)
            color = USER_STATUS_COLORS.get(status)

        self.chat_view.update_tag(self.tag_users[username], color)

    def update_tags(self):

        for tag in (self.tag_remote, self.tag_local, self.tag_command, self.tag_action,
                    self.tag_highlight, self.tag_log):
            self.chat_view.update_tag(tag)

        for tag in self.tag_users.values():
            self.chat_view.update_tag(tag)

        self.chat_view.update_tags()

    def save_columns(self):
        save_columns("chat_room", self.users_list_view.get_columns(), subpage=self.room)

    def server_disconnect(self):

        self.usersmodel.clear()
        self.users.clear()
        self.count_users()

        if (self.room not in config.sections["server"]["autojoin"]
                and self.room in config.sections["columns"]["chat_room"]):
            del config.sections["columns"]["chat_room"][self.room]

        timestamp_format = config.sections["logging"]["rooms_timestamp"]
        self.chat_view.append_line(_("--- disconnected ---"), tag=self.tag_highlight, timestamp_format=timestamp_format)

        for username in self.tag_users:
            self.update_user_tag(username)

    def join_room(self, msg):

        # Temporarily disable sorting for increased performance
        sort_column, sort_type = self.usersmodel.get_sort_column_id()
        self.usersmodel.set_default_sort_func(lambda *args: 0)
        self.usersmodel.set_sort_column_id(-1, Gtk.SortType.ASCENDING)

        for userdata in msg.users:
            username = userdata.username

            if username in self.users:
                self.usersmodel.remove(self.users[username])

            self.add_user_row(userdata)

        if sort_column is not None and sort_type is not None:
            self.usersmodel.set_sort_column_id(sort_column, sort_type)

        # Spit this line into chat log
        timestamp_format = config.sections["logging"]["rooms_timestamp"]
        self.chat_view.append_line(_("--- reconnected ---"), tag=self.tag_highlight, timestamp_format=timestamp_format)

        # Update user count
        self.count_users()

        # Build completion list
        self.set_completion_list(core.chatrooms.completion_list[:])

        # Update all username tags in chat log
        for username in self.tag_users:
            self.update_user_tag(username)

    def on_autojoin(self, *_args):

        autojoin = config.sections["server"]["autojoin"]
        active = self.auto_join_toggle.get_active()

        if not active and self.room in autojoin:
            autojoin.remove(self.room)

        elif active and self.room not in autojoin:
            autojoin.append(self.room)

        config.write_configuration()

    def on_focus(self, *_args):
        self.chat_entry.grab_focus()

    def on_leave_room(self, *_args):

        if self.room == core.chatrooms.GLOBAL_ROOM_NAME:
            self.chatrooms.roomlist.public_feed_toggle.set_active(False)
            return

        core.chatrooms.remove_room(self.room)

    @staticmethod
    def on_tooltip(widget, pos_x, pos_y, _keyboard_mode, tooltip):

        status_tooltip = show_user_status_tooltip(widget, pos_x, pos_y, tooltip, 5)
        country_tooltip = show_country_tooltip(widget, pos_x, pos_y, tooltip, 8)

        if status_tooltip:
            return status_tooltip

        if country_tooltip:
            return country_tooltip

        return None

    def on_log_toggled(self, *_args):

        if not self.log_toggle.get_active():
            if self.room in config.sections["logging"]["rooms"]:
                config.sections["logging"]["rooms"].remove(self.room)
            return

        if self.room not in config.sections["logging"]["rooms"]:
            config.sections["logging"]["rooms"].append(self.room)

    def on_view_room_log(self, *_args):
        log.open_log(config.sections["logging"]["roomlogsdir"], self.room)

    def on_delete_room_log_response(self, _dialog, response_id, _data):

        if response_id == 2:
            log.delete_log(config.sections["logging"]["roomlogsdir"], self.room)
            self.activity_view.clear()
            self.chat_view.clear()

    def on_delete_room_log(self, *_args):

        OptionDialog(
            parent=self.window,
            title=_("Delete Logged Messages?"),
            message=_("Do you really want to permanently delete all logged messages for this room?"),
            callback=self.on_delete_room_log_response
        ).show()

    def set_completion_list(self, completion_list):

        if not config.sections["words"]["tab"]:
            return

        # We want to include users for this room only
        if config.sections["words"]["roomusers"]:
            completion_list += self.users

        # No duplicates
        completion_list = list(set(completion_list))
        completion_list.sort(key=str.lower)

        self.chatrooms.completion.set_completion_list(completion_list)
