# COPYRIGHT (C) 2020-2021 Nicotine+ Team
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2016 Mutnick <muhing@yahoo.com>
# COPYRIGHT (C) 2008-2011 Quinox <quinox@users.sf.net>
# COPYRIGHT (C) 2006-2009 Daelstorm <daelstorm@gmail.com>
# COPYRIGHT (C) 2007 Gallows <g4ll0ws@gmail.com>
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
import re
import threading

from collections import deque

from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Pango

from pynicotine import slskmessages
from pynicotine.config import config
from pynicotine.gtkgui.roomlist import RoomList
from pynicotine.gtkgui.roomwall import RoomWall
from pynicotine.gtkgui.roomwall import Tickers
from pynicotine.gtkgui.utils import append_line
from pynicotine.gtkgui.utils import auto_replace
from pynicotine.gtkgui.utils import censor_chat
from pynicotine.gtkgui.utils import copy_all_text
from pynicotine.gtkgui.utils import delete_log
from pynicotine.gtkgui.utils import grab_widget_focus
from pynicotine.gtkgui.utils import load_ui_elements
from pynicotine.gtkgui.utils import open_log
from pynicotine.gtkgui.utils import scroll_bottom
from pynicotine.gtkgui.widgets.iconnotebook import IconNotebook
from pynicotine.gtkgui.widgets.dialogs import option_dialog
from pynicotine.gtkgui.widgets.popupmenu import PopupMenu
from pynicotine.gtkgui.widgets.textentry import ChatEntry
from pynicotine.gtkgui.widgets.textentry import TextSearchBar
from pynicotine.gtkgui.widgets.theme import get_user_status_color
from pynicotine.gtkgui.widgets.theme import update_tag_visuals
from pynicotine.gtkgui.widgets.theme import update_widget_visuals
from pynicotine.gtkgui.widgets.treeview import initialise_columns
from pynicotine.gtkgui.widgets.treeview import save_columns
from pynicotine.gtkgui.widgets.treeview import show_country_tooltip
from pynicotine.gtkgui.widgets.treeview import show_user_status_tooltip
from pynicotine.logfacility import log
from pynicotine.utils import get_completion_list
from pynicotine.utils import get_path
from pynicotine.utils import humanize
from pynicotine.utils import human_speed


class ChatRooms(IconNotebook):

    # List of allowed commands. The implementation for them is in the ChatEntry class.
    CMDS = {
        "/al ", "/alias ", "/un ", "/unalias ", "/w ", "/whois ", "/browse ", "/b ", "/ip ", "/pm ", "/m ", "/msg ",
        "/s ", "/search ", "/us ", "/usearch ", "/rs ", "/rsearch ", "/bs ", "/bsearch ", "/j ", "/join ", "/l ", "/leave ",
        "/p ", "/part ", "/ad ", "/add ", "/buddy ", "/rem ", "/unbuddy ", "/ban ", "/ignore ", "/ignoreip ", "/unban ",
        "/unignore ", "/clear ", "/cl ", "/me ", "/a ", "/away ", "/q ", "/quit ", "/exit ", "/now ", "/rescan ", "/tick ", "/t ",
        "/info ", "/toggle ", "/tickers "
    }

    def __init__(self, frame):

        self.frame = frame

        self.completion_list = []
        self.joinedrooms = {}
        self.autojoin = True
        self.private_rooms = config.sections["private_rooms"]["rooms"]
        self.switch_tab = True

        # Config cleanup
        for room, data in self.private_rooms.items():
            if "owner" not in data:
                self.private_rooms[room]["owner"] = None
            if "operator" in data:
                del self.private_rooms[room]["operator"]

        self.roomlist = RoomList(self.frame, self.joinedrooms, self.private_rooms)

        IconNotebook.__init__(
            self,
            self.frame.images,
            tabclosers=config.sections["ui"]["tabclosers"],
            show_hilite_image=config.sections["notifications"]["notification_tab_icons"],
            reorderable=config.sections["ui"]["tab_reorderable"],
            notebookraw=self.frame.ChatNotebookRaw
        )

        self.set_tab_pos(self.frame.get_tab_position(config.sections["ui"]["tabrooms"]))

        self.notebook.connect("switch-page", self.on_switch_chat)
        self.notebook.connect("page-reordered", self.on_reordered_page)

        if Gtk.get_major_version() == 4:
            self.frame.ChatroomsPane.set_property("resize-start-child", True)
        else:
            self.frame.ChatroomsPane.child_set_property(self.notebook, "resize", True)

        self.update_visuals()

    def on_reordered_page(self, notebook, page, page_num, force=0):

        room_tab_order = {}

        # Find position of opened autojoined rooms
        for name, room in self.joinedrooms.items():

            if name not in config.sections["server"]["autojoin"]:
                continue

            room_tab_order[notebook.page_num(room.Main)] = name

        pos = 1000

        # Add closed autojoined rooms as well
        for name in config.sections["server"]["autojoin"]:
            if name not in self.joinedrooms:
                room_tab_order[pos] = name
                pos += 1

        # Sort by "position"
        rto = sorted(room_tab_order.keys())
        new_autojoin = []
        for roomplace in rto:
            new_autojoin.append(room_tab_order[roomplace])

        # Save
        config.sections["server"]["autojoin"] = new_autojoin

    def on_switch_chat(self, notebook, page, page_num, forceupdate=False):

        if self.frame.MainNotebook.get_current_page() != self.frame.MainNotebook.page_num(self.frame.chatroomsvbox) and not forceupdate:
            return

        for name, room in self.joinedrooms.items():
            if room.Main == page:
                GLib.idle_add(grab_widget_focus, room.ChatEntry)

                # Remove hilite
                self.frame.notifications.clear("rooms", None, name)

    def enable_tab_switch(self):
        # Room tabs will be opened when joining rooms
        self.switch_tab = True

    def clear_notifications(self):

        if self.frame.MainNotebook.get_current_page() != self.frame.MainNotebook.page_num(self.frame.chatroomsvbox):
            return

        page = self.get_nth_page(self.get_current_page())

        for name, room in self.joinedrooms.items():
            if room.Main == page:
                # Remove hilite
                self.frame.notifications.clear("rooms", None, name)

    def join_room(self, msg):

        if msg.room in self.joinedrooms:
            self.joinedrooms[msg.room].rejoined(msg.users)
            return

        meta = (msg.room == "Public ")
        self.joinedrooms[msg.room] = tab = ChatRoom(self, msg.room, msg.users, meta)

        self.append_page(tab.Main, msg.room, tab.on_leave)
        tab_label, menu_label = self.get_labels(tab.Main)
        tab.set_label(tab_label)

        if self.switch_tab:
            page_num = self.page_num(tab.Main)
            self.set_current_page(page_num)

        if msg.room != "Public ":
            self.frame.RoomSearchCombo.append_text(msg.room)

        if msg.private:
            self.create_private_room(msg.room, msg.owner, msg.operators)

    def set_room_list(self, msg):

        if self.autojoin:
            self.autojoin = False

            if self.joinedrooms:
                room_list = list(self.joinedrooms.keys())
            else:
                room_list = config.sections["server"]["autojoin"]
                if room_list:
                    # Disable tab focusing while joining rooms
                    self.switch_tab = False

                    timer = threading.Timer(4.0, self.enable_tab_switch)
                    timer.name = "ChatroomTabSwitchTimer"
                    timer.daemon = True
                    timer.start()

            for room in room_list:
                if room == 'Public ':
                    self.roomlist.on_join_public_room(None)

                elif isinstance(room, str):
                    self.frame.np.queue.append(slskmessages.JoinRoom(room))

        self.roomlist.set_room_list(msg.rooms, msg.ownedprivaterooms, msg.otherprivaterooms)

        if config.sections["words"]["roomnames"]:
            self.frame.update_completions()

    def create_private_room(self, room, owner=None, operators=[]):

        if room in self.private_rooms:
            if operators is not None:
                for operator in operators:
                    if operator not in self.private_rooms[room]["operators"]:
                        self.private_rooms[room]["operators"].append(operator)

            self.private_rooms[room]["owner"] = owner
            return

        self.private_rooms[room] = {"users": [], "joined": 0, "operators": operators, "owned": False, "owner": owner}

    def private_room_users(self, msg):

        rooms = self.private_rooms

        if msg.room not in rooms:
            self.create_private_room(msg.room)

        rooms[msg.room]["users"] = msg.users
        rooms[msg.room]["joined"] = msg.numusers

    def private_room_owned(self, msg):

        rooms = self.private_rooms

        if msg.room not in rooms:
            self.create_private_room(msg.room)

        rooms[msg.room]["operators"] = msg.operators

    def private_room_add_user(self, msg):

        rooms = self.private_rooms

        if msg.room in rooms and msg.user not in rooms[msg.room]["users"]:
            rooms[msg.room]["users"].append(msg.user)

    def private_room_remove_user(self, msg):

        rooms = self.private_rooms

        if msg.room in rooms and msg.user in rooms[msg.room]["users"]:
            rooms[msg.room]["users"].remove(msg.user)

    def private_room_operator_added(self, msg):

        rooms = self.private_rooms

        if msg.room in rooms and config.sections["server"]["login"] not in rooms[msg.room]["operators"]:
            rooms[msg.room]["operators"].append(config.sections["server"]["login"])

    def private_room_operator_removed(self, msg):

        rooms = self.private_rooms

        if msg.room in rooms and config.sections["server"]["login"] in rooms[msg.room]["operators"]:
            rooms[msg.room]["operators"].remove(config.sections["server"]["login"])

    def private_room_add_operator(self, msg):

        rooms = self.private_rooms

        if msg.room in rooms and msg.user not in rooms[msg.room]["operators"]:
            rooms[msg.room]["operators"].append(msg.user)

    def private_room_remove_operator(self, msg):

        rooms = self.private_rooms

        if msg.room in rooms and msg.user in rooms[msg.room]["operators"]:
            rooms[msg.room]["operators"].remove(msg.user)

    def private_room_added(self, msg):

        rooms = self.private_rooms
        room = msg.room

        if room not in rooms:
            self.create_private_room(room)
            log.add(_("You have been added to a private room: %(room)s"), {"room": room})

        self.roomlist.set_private_rooms()

    def private_room_removed(self, msg):

        rooms = self.private_rooms

        if msg.room in rooms:
            del rooms[msg.room]

        self.roomlist.set_private_rooms()

    def toggle_private_rooms(self, enabled):
        config.sections["server"]["private_chatrooms"] = enabled

    def private_room_disown(self, msg):
        if msg.room in self.private_rooms and self.private_rooms[msg.room]["owner"] == config.sections["server"]["login"]:
            self.private_rooms[msg.room]["owner"] = None

    def get_user_stats(self, msg):
        for room in self.joinedrooms.values():
            room.get_user_stats(msg.user, msg.avgspeed, msg.files)

    def get_user_status(self, msg):
        for room in self.joinedrooms.values():
            room.get_user_status(msg.user, msg.status)

    def set_user_flag(self, user, country):
        for room in self.joinedrooms.values():
            room.set_user_flag(user, country)

    def user_joined_room(self, msg):

        if msg.room in self.joinedrooms:
            self.joinedrooms[msg.room].user_joined_room(msg.userdata)

    def user_left_room(self, msg):
        self.joinedrooms[msg.room].user_left_room(msg.username)

    def ticker_set(self, msg):
        self.joinedrooms[msg.room].ticker_set(msg)

    def ticker_add(self, msg):
        self.joinedrooms[msg.room].ticker_add(msg)

    def ticker_remove(self, msg):
        self.joinedrooms[msg.room].ticker_remove(msg)

    def say_chat_room(self, msg, text):
        self.joinedrooms[msg.room].say_chat_room(msg, text)

    def public_room_message(self, msg, text):

        try:
            room = self.joinedrooms['Public ']
        except KeyError:
            return

        room.say_chat_room(msg, text, public=True)

    def toggle_chat_buttons(self):
        for room in self.joinedrooms.values():
            room.toggle_chat_buttons()

    def update_visuals(self):

        for room in self.joinedrooms.values():
            room.update_visuals()
            room.update_tags()

        self.roomlist.update_visuals()

    def save_columns(self):

        for room in list(config.sections["columns"]["chat_room"].keys())[:]:
            if room not in self.joinedrooms:
                del config.sections["columns"]["chat_room"][room]

        for room in self.joinedrooms.values():
            room.save_columns()

    def leave_room(self, msg):

        room = self.joinedrooms[msg.room]

        self.remove_page(room.Main)
        del self.joinedrooms[msg.room]

        if msg.room[-1:] != ' ':  # meta rooms
            self.frame.RoomSearchCombo.remove_all()
            self.frame.RoomSearchCombo.append_text("Joined Rooms ")

            for room in self.joinedrooms:
                self.frame.RoomSearchCombo.append_text(room)

    def conn_close(self):

        self.roomlist.clear()

        for room in self.joinedrooms.values():
            room.conn_close()

        self.autojoin = 1

    def update_completions(self):

        self.completion_list = get_completion_list(self.CMDS, self.roomlist.server_rooms)

        for room in self.joinedrooms.values():
            # We need to create a copy of the completion list, due to unique room usernames
            room.set_completion_list(list(self.completion_list))


class ChatRoom:

    def __init__(self, chatrooms, room, users, meta=False):

        self.chatrooms = chatrooms
        self.frame = chatrooms.frame
        self.room = room
        self.meta = meta  # not a real room if set to True

        # Build the window
        load_ui_elements(self, os.path.join(self.frame.gui_dir, "ui", "chatrooms.ui"))
        load_ui_elements(self, os.path.join(self.frame.gui_dir, "ui", "popovers", "chatroomcommands.ui"))

        self.ShowChatHelp.set_popover(self.AboutChatRoomCommandsPopover)

        if Gtk.get_major_version() == 4:
            self.ShowChatHelp.set_icon_name("dialog-question-symbolic")

            self.ChatPaned.set_property("resize-start-child", True)
            self.ChatPaned.set_property("shrink-start-child", False)
            self.ChatPaned.set_property("resize-end-child", False)
            self.ChatPaned.set_property("shrink-end-child", True)

            self.ChatPanedSecond.set_property("resize-start-child", False)
            self.ChatPanedSecond.set_property("shrink-end-child", False)

        else:
            self.ShowChatHelp.set_image(Gtk.Image.new_from_icon_name("dialog-question-symbolic", Gtk.IconSize.BUTTON))

            self.ChatPaned.child_set_property(self.ChatPanedSecond, "resize", True)
            self.ChatPaned.child_set_property(self.ChatPanedSecond, "shrink", False)
            self.ChatPaned.child_set_property(self.UserView, "resize", False)
            self.ChatPaned.child_set_property(self.UserView, "shrink", False)

            self.ChatPanedSecond.child_set_property(self.ActivityView, "resize", False)
            self.ChatPanedSecond.child_set_property(self.ChatView, "shrink", False)

        self.tickers = Tickers()
        self.room_wall = RoomWall(self.frame, self)
        self.leaving = False

        self.users = {}

        # Log Text Search
        TextSearchBar(self.RoomLog, self.LogSearchBar, self.LogSearchEntry)

        # Chat Text Search
        TextSearchBar(self.ChatScroll, self.ChatSearchBar, self.ChatSearchEntry)

        # Chat Entry
        self.entry = ChatEntry(self.frame, self.ChatEntry, room, slskmessages.SayChatroom, self.send_message, self.chatrooms.CMDS, self.ChatScroll, is_chatroom=True)

        self.Log.set_active(config.sections["logging"]["chatrooms"])
        if not self.Log.get_active():
            self.Log.set_active((self.room in config.sections["logging"]["rooms"]))

        self.AutoJoin.set_active((room in config.sections["server"]["autojoin"]))

        self.toggle_chat_buttons()

        if room not in config.sections["columns"]["chat_room"]:
            config.sections["columns"]["chat_room"][room] = {}

        self.usersmodel = Gtk.ListStore(
            GObject.TYPE_OBJECT,  # (0)  status_image
            GObject.TYPE_OBJECT,  # (1)  flag
            str,                  # (2)  username
            str,                  # (3)  h_speed
            str,                  # (4)  h_files
            int,                  # (5)  status
            GObject.TYPE_UINT64,  # (6)  avgspeed
            GObject.TYPE_UINT64,  # (7)  files
            str                   # (8)  country
        )
        self.UserList.set_model(self.usersmodel)

        self.column_numbers = list(range(self.usersmodel.get_n_columns()))
        self.cols = cols = initialise_columns(
            ("chat_room", room), self.UserList,
            ["status", _("Status"), 25, "pixbuf", None],
            ["country", _("Country"), 25, "pixbuf", None],
            ["user", _("User"), 100, "text", self.user_column_draw],
            ["speed", _("Speed"), 100, "number", None],
            ["files", _("Files"), 100, "number", None]
        )

        cols["status"].set_sort_column_id(5)
        cols["country"].set_sort_column_id(8)
        cols["user"].set_sort_column_id(2)
        cols["speed"].set_sort_column_id(6)
        cols["files"].set_sort_column_id(7)

        cols["status"].get_widget().hide()
        cols["country"].get_widget().hide()

        if config.sections["columns"]["hideflags"]:
            cols["country"].set_visible(False)

        for userdata in users:
            self.add_user_row(userdata)

        self.usersmodel.set_sort_column_id(2, Gtk.SortType.ASCENDING)

        self.popup_menu_private_rooms = PopupMenu(self.frame)

        self.popup_menu = popup = PopupMenu(self.frame, self.UserList, self.on_popup_menu)
        popup.setup_user_menu()
        popup.setup(
            ("", None),
            ("#" + _("Sear_ch User's Files"), popup.on_search_user),
            (">" + _("Private Rooms"), self.popup_menu_private_rooms)
        )

        PopupMenu(self.frame, self.RoomLog).setup(
            ("#" + _("Find..."), self.on_find_activity_log),
            ("", None),
            ("#" + _("Copy"), self.on_copy_activity_log),
            ("#" + _("Copy All"), self.on_copy_all_activity_log),
            ("", None),
            ("#" + _("Clear Activity View"), self.on_clear_activity_log),
            ("", None),
            ("#" + _("_Leave Room"), self.on_leave)
        )

        PopupMenu(self.frame, self.ChatScroll).setup(
            ("#" + _("Find..."), self.on_find_room_log),
            ("", None),
            ("#" + _("Copy"), self.on_copy_room_log),
            ("#" + _("Copy All"), self.on_copy_all_room_log),
            ("", None),
            ("#" + _("View Room Log"), self.on_view_room_log),
            ("#" + _("Delete Room Log..."), self.on_delete_room_log),
            ("", None),
            ("#" + _("Clear Message View"), self.on_clear_messages),
            ("#" + _("_Leave Room"), self.on_leave)
        )

        self.tab_menu = PopupMenu(self.frame)
        self.tab_menu.setup(
            ("#" + _("_Leave Room"), self.on_leave)
        )

        self.ChatEntry.grab_focus()
        self.set_completion_list(list(self.chatrooms.completion_list))

        self.count_users()
        self.create_tags()
        self.update_visuals()
        self.read_room_logs()

    def set_label(self, label):
        self.tab_menu.set_widget(label)

    def add_user_row(self, userdata):

        username = userdata.username
        status = userdata.status
        country = userdata.country or ""  # country can be None, ensure string is used
        status_image = self.frame.get_status_image(status)
        flag_image = self.frame.get_flag_image(country)

        # Request user's IP address, so we can get the country
        self.frame.np.queue.append(slskmessages.GetPeerAddress(username))

        avgspeed = userdata.avgspeed
        files = userdata.files
        hspeed = human_speed(avgspeed)
        hfiles = humanize(files)

        if Gtk.get_major_version() == 4:
            self.usersmodel.insert_with_valuesv = self.usersmodel.insert_with_values

        iterator = self.usersmodel.insert_with_valuesv(
            -1, self.column_numbers,
            [
                GObject.Value(GObject.TYPE_OBJECT, status_image),
                GObject.Value(GObject.TYPE_OBJECT, flag_image),
                username,
                hspeed,
                hfiles,
                status,
                GObject.Value(GObject.TYPE_UINT64, avgspeed),
                GObject.Value(GObject.TYPE_UINT64, files),
                country
            ]
        )

        self.users[username] = iterator

    def read_room_logs(self):

        if not config.sections["logging"]["readroomlogs"]:
            return

        filename = self.room.replace(os.sep, "-") + ".log"

        try:
            numlines = int(config.sections["logging"]["readroomlines"])
        except Exception:
            numlines = 15

        try:
            get_path(config.sections["logging"]["roomlogsdir"], filename, self.append_log_lines, numlines)

        except IOError:
            pass

        GLib.idle_add(scroll_bottom, self.ChatScroll.get_parent())

    def append_log_lines(self, path, numlines):

        try:
            self._append_log_lines(path, numlines, 'utf-8')

        except UnicodeDecodeError:
            self._append_log_lines(path, numlines, 'latin-1')

    def _append_log_lines(self, path, numlines, encoding='utf-8'):

        with open(path, 'r', encoding=encoding) as lines:
            # Only show as many log lines as specified in config
            lines = deque(lines, numlines)

            for line in lines:

                # Try to parse line for username
                if len(line) > 20 and line[10].isspace() and line[11].isdigit() and line[20] in ("[", "*"):

                    if line[20] == "[" and line[20:].find("] ") != -1:
                        namepos = line[20:].find("] ")
                        user = line[21:20 + namepos].strip()
                        self.get_user_tag(user)
                        usertag = self.tag_users[user]
                    else:
                        user = None
                        usertag = None

                    if user == config.sections["server"]["login"]:
                        tag = self.tag_local
                    elif line[20] == "*":
                        tag = self.tag_me
                    elif line[20 + namepos:].upper().find(config.sections["server"]["login"].upper()) > -1:
                        tag = self.tag_hilite
                    else:
                        tag = self.tag_remote
                else:
                    user = None
                    tag = None
                    usertag = None

                line = re.sub(r"\\s\\s+", "  ", line)

                if user != config.sections["server"]["login"]:
                    append_line(self.ChatScroll, censor_chat(line), tag, username=user, usertag=usertag, timestamp_format="", scroll=False)
                else:
                    append_line(self.ChatScroll, line, tag, username=user, usertag=usertag, timestamp_format="", scroll=False)

            if lines:
                append_line(self.ChatScroll, _("--- old messages above ---"), self.tag_hilite)

    def populate_user_menu(self, user):

        self.popup_menu.set_user(user)
        self.popup_menu.toggle_user_items()

        me = (self.popup_menu.user is None or self.popup_menu.user == config.sections["server"]["login"])
        self.popup_menu.get_actions()[_("Private Rooms")].set_enabled(not me)
        self.popup_menu.populate_private_rooms(self.popup_menu_private_rooms)

    def on_find_activity_log(self, *args):
        self.LogSearchBar.set_search_mode(True)

    def on_find_room_log(self, *args):
        self.ChatSearchBar.set_search_mode(True)

    def get_selected_username(self, treeview):

        model, iterator = treeview.get_selection().get_selected()

        if iterator is None:
            return None

        return model.get_value(iterator, 2)

    def on_row_activated(self, treeview, path, column):

        user = self.get_selected_username(treeview)

        if user is not None:
            self.frame.privatechats.send_message(user, show_user=True)
            self.frame.change_main_page("private")

    def on_popup_menu(self, menu, treeview):

        user = self.get_selected_username(treeview)
        if user is None:
            return True

        self.populate_user_menu(user)

    def on_show_room_wall(self, *args):
        self.room_wall.show()

    def toggle_chat_buttons(self):
        self.Speech.set_visible(config.sections["ui"]["speechenabled"])

    def ticker_set(self, msg):

        self.tickers.set_ticker([])
        for user in msg.msgs:
            if self.frame.np.network_filter.is_user_ignored(user) or self.frame.np.network_filter.is_user_ip_ignored(user):
                # User ignored, ignore Ticker messages
                return

            self.tickers.add_ticker(user, msg.msgs[user])

    def ticker_add(self, msg):

        user = msg.user
        if self.frame.np.network_filter.is_user_ignored(user) or self.frame.np.network_filter.is_user_ip_ignored(user):
            # User ignored, ignore Ticker messages
            return

        self.tickers.add_ticker(msg.user, msg.msg)

    def ticker_remove(self, msg):
        self.tickers.remove_ticker(msg.user)

    def show_notification(self, login, user, text, tag):

        if user == login:
            return

        if tag == self.tag_hilite:

            # Hilight top-level tab label
            self.frame.request_tab_icon(self.frame.ChatTabLabel, status=1)

            # Hilight sub-level tab label
            self.chatrooms.request_hilite(self.Main)

            if config.sections["notifications"]["notification_popup_chatroom_mention"]:
                self.frame.notifications.new_notification(
                    text,
                    title=_("%s mentioned you in the %s room") % (user, self.room),
                    priority=Gio.NotificationPriority.HIGH
                )

        else:
            # Hilight top-level tab label
            self.frame.request_tab_icon(self.frame.ChatTabLabel, status=0)

            # Hilight sub-level tab label
            self.chatrooms.request_changed(self.Main)

        # Don't show notifications if the chat is open and the window
        # is in use
        if self.chatrooms.get_current_page() == self.chatrooms.page_num(self.chatrooms.joinedrooms[self.room].Main) and \
           self.frame.MainNotebook.get_current_page() == self.frame.MainNotebook.page_num(self.frame.chatroomsvbox) and \
           self.frame.MainWindow.is_active():
            return

        if tag == self.tag_hilite:
            # We were mentioned, update tray icon and show urgency hint
            self.frame.notifications.add("rooms", user, self.room)

        elif config.sections["notifications"]["notification_popup_chatroom"]:
            self.frame.notifications.new_notification(
                text,
                title=_("Message by %s in the %s room") % (user, self.room),
                priority=Gio.NotificationPriority.HIGH
            )

    def say_chat_room(self, msg, text, public=False):

        user = msg.user

        if self.frame.np.network_filter.is_user_ignored(user):
            return

        if self.frame.np.network_filter.is_user_ip_ignored(user):
            return

        text = re.sub("\\s\\s+", "  ", text)
        login = config.sections["server"]["login"]

        if user == login:
            tag = self.tag_local
        elif text.upper().find(login.upper()) > -1:
            tag = self.tag_hilite
        else:
            tag = self.tag_remote

        self.show_notification(login, user, text, tag)

        if text[:4] == "/me ":

            if public:
                line = "%s | * %s %s" % (msg.room, user, text[4:])
            else:
                line = "* %s %s" % (user, text[4:])

            speech = line[2:]
            tag = self.tag_me
        else:

            if public:
                line = "%s | [%s] %s" % (msg.room, user, text)
            else:
                line = "[%s] %s" % (user, text)

            speech = text

        line = "\n-- ".join(line.split("\n"))
        if self.Log.get_active():
            timestamp_format = config.sections["logging"]["log_timestamp"]
            log.write_log(config.sections["logging"]["roomlogsdir"], self.room, line, timestamp_format)

        self.get_user_tag(user)

        timestamp_format = config.sections["logging"]["rooms_timestamp"]

        if user != login:

            append_line(
                self.ChatScroll, censor_chat(line), tag,
                username=user, usertag=self.tag_users[user], timestamp_format=timestamp_format
            )

            if self.Speech.get_active():

                self.frame.notifications.new_tts(
                    config.sections["ui"]["speechrooms"] % {
                        "room": self.room,
                        "user": self.frame.notifications.tts_clean(user),
                        "message": self.frame.notifications.tts_clean(speech)
                    }
                )
        else:
            append_line(
                self.ChatScroll, line, tag,
                username=user, usertag=self.tag_users[user], timestamp_format=timestamp_format
            )

    def get_user_tag(self, user):

        if user not in self.users:
            color = "useroffline"
        else:
            color = get_user_status_color(self.usersmodel.get_value(self.users[user], 5))

        if user not in self.tag_users:
            self.tag_users[user] = self.create_tag(self.ChatScroll.get_buffer(), color, user)
        else:
            update_tag_visuals(self.tag_users[user], color)

    def show_tickers(self):
        tickers = self.tickers.get_tickers()
        header = _("All tickers / wall messages for %(room)s:") % {'room': self.room}
        log.add("%s\n%s", (header, "\n".join(["[%s] %s" % (user, msg) for (user, msg) in tickers])))

    def send_message(self, text):

        event = self.frame.np.pluginhandler.outgoing_public_chat_event(self.room, text)
        if event is not None:
            (r, text) = event
            self.say(auto_replace(text))
            self.frame.np.pluginhandler.outgoing_public_chat_notification(self.room, text)

    def say(self, text):
        text = re.sub("\\s\\s+", "  ", text)
        self.frame.np.queue.append(slskmessages.SayChatroom(self.room, text))

    def user_joined_room(self, userdata):

        username = userdata.username

        if username in self.users:
            return

        # Add to completion list, and completion drop-down
        self.entry.add_completion(username)

        if not self.frame.np.network_filter.is_user_ignored(username) and not self.frame.np.network_filter.is_user_ip_ignored(username):
            append_line(self.RoomLog, _("%s joined the room") % username, self.tag_log)

        self.add_user_row(userdata)

        self.get_user_tag(username)
        self.count_users()

    def user_left_room(self, username):

        if username not in self.users:
            return

        # Remove from completion list, and completion drop-down
        if username not in (i[0] for i in config.sections["server"]["userlist"]):
            self.entry.remove_completion(username)

        if not self.frame.np.network_filter.is_user_ignored(username) and not self.frame.np.network_filter.is_user_ip_ignored(username):
            append_line(self.RoomLog, _("%s left the room") % username, self.tag_log)

        self.usersmodel.remove(self.users[username])
        del self.users[username]

        self.get_user_tag(username)
        self.count_users()

    def count_users(self):

        user_count = len(self.users)
        self.LabelPeople.set_text(str(user_count))
        self.chatrooms.roomlist.update_room(self.room, user_count)

    def user_column_draw(self, column, cellrenderer, model, iterator, dummy="dummy"):

        if self.room in self.chatrooms.private_rooms:
            user = self.usersmodel.get_value(iterator, 2)

            if user == self.chatrooms.private_rooms[self.room]["owner"]:
                cellrenderer.set_property("underline", Pango.Underline.SINGLE)
                cellrenderer.set_property("weight", Pango.Weight.BOLD)

            elif user in (self.chatrooms.private_rooms[self.room]["operators"]):
                cellrenderer.set_property("weight", Pango.Weight.BOLD)
                cellrenderer.set_property("underline", Pango.Underline.NONE)

            else:
                cellrenderer.set_property("weight", Pango.Weight.NORMAL)
                cellrenderer.set_property("underline", Pango.Underline.NONE)

    def get_user_stats(self, user, avgspeed, files):

        if user not in self.users:
            return

        self.usersmodel.set_value(self.users[user], 3, human_speed(avgspeed))
        self.usersmodel.set_value(self.users[user], 4, humanize(files))
        self.usersmodel.set_value(self.users[user], 6, GObject.Value(GObject.TYPE_UINT64, avgspeed))
        self.usersmodel.set_value(self.users[user], 7, GObject.Value(GObject.TYPE_UINT64, files))

    def get_user_status(self, user, status):

        if user not in self.users:
            return

        img = self.frame.get_status_image(status)
        if img == self.usersmodel.get_value(self.users[user], 0):
            return

        if status == 1:
            action = _("%s has gone away")
        else:
            action = _("%s has returned")

        if not self.frame.np.network_filter.is_user_ignored(user) and not self.frame.np.network_filter.is_user_ip_ignored(user):
            append_line(self.RoomLog, action % user, self.tag_log)

        if user in self.tag_users:
            color = get_user_status_color(status)
            update_tag_visuals(self.tag_users[user], color)

        self.usersmodel.set_value(self.users[user], 0, GObject.Value(GObject.TYPE_OBJECT, img))
        self.usersmodel.set_value(self.users[user], 5, status)

    def set_user_flag(self, user, country):

        if user not in self.users:
            return

        if self.usersmodel.get_value(self.users[user], 8) == country:
            # Country didn't change, no need to update
            return

        self.usersmodel.set_value(self.users[user], 1, GObject.Value(GObject.TYPE_OBJECT, self.frame.get_flag_image(country)))
        self.usersmodel.set_value(self.users[user], 8, country)

    def update_visuals(self):

        for widget in list(self.__dict__.values()):
            update_widget_visuals(widget, update_text_tags=False)

        self.room_wall.update_visuals()

    def user_name_event(self, tag, widget, event, iterator, user):
        """
        Mouse buttons:
        1 = left button
        2 = middle button
        3 = right button
        """
        if event.button.type == Gdk.EventType.BUTTON_PRESS and event.button.button in (1, 2, 3):

            # Chat, Userlists use the normal popup system
            self.populate_user_menu(user)
            self.popup_menu.popup(event.x, event.y, button=event.button.button)

        return True

    def create_tag(self, buffer, color, username=None):

        tag = buffer.create_tag()
        update_tag_visuals(tag, color)

        if username and Gtk.get_major_version() == 3:
            tag.connect("event", self.user_name_event, username)

        return tag

    def create_tags(self):

        log_buffer = self.RoomLog.get_buffer()
        self.tag_log = self.create_tag(log_buffer, "chatremote")

        chat_buffer = self.ChatScroll.get_buffer()
        self.tag_remote = self.create_tag(chat_buffer, "chatremote")
        self.tag_local = self.create_tag(chat_buffer, "chatlocal")
        self.tag_me = self.create_tag(chat_buffer, "chatme")
        self.tag_hilite = self.create_tag(chat_buffer, "chathilite")

        self.tag_users = {}

    def update_tags(self):

        update_tag_visuals(self.tag_remote, "chatremote")
        update_tag_visuals(self.tag_local, "chatlocal")
        update_tag_visuals(self.tag_me, "chatme")
        update_tag_visuals(self.tag_hilite, "chathilite")
        update_tag_visuals(self.tag_log, "chatremote")

        for user in self.tag_users:
            self.get_user_tag(user)

    def on_leave(self, *args):

        if self.leaving:
            return

        self.leaving = True

        if self.room in config.sections["columns"]["chat_room"]:
            del config.sections["columns"]["chat_room"][self.room]

        if not self.meta:
            self.frame.np.queue.append(slskmessages.LeaveRoom(self.room))

        elif self.room == 'Public ':
            self.frame.np.queue.append(slskmessages.LeavePublicRoom())
            self.chatrooms.leave_room(slskmessages.LeaveRoom(self.room))  # Faking protocol msg

        self.frame.np.pluginhandler.leave_chatroom_notification(self.room)

    def save_columns(self):
        save_columns("chat_room", self.UserList.get_columns(), subpage=self.room)

    def conn_close(self):

        append_line(self.ChatScroll, _("--- disconnected ---"), self.tag_hilite)
        self.usersmodel.clear()
        self.UserList.set_sensitive(False)
        self.users.clear()
        self.count_users()

        if not self.AutoJoin.get_active() and self.room in config.sections["columns"]["chat_room"]:
            del config.sections["columns"]["chat_room"][self.room]

        for tag in self.tag_users.values():
            update_tag_visuals(tag, "useroffline")

        self.tickers.set_ticker([])

    def rejoined(self, users):

        # Update user list with an inexpensive sorting function
        self.usersmodel.set_default_sort_func(lambda *args: -1)
        self.usersmodel.set_sort_column_id(-1, Gtk.SortType.ASCENDING)

        for userdata in users:
            username = userdata.username

            if username in self.users:
                self.usersmodel.remove(self.users[username])

            self.add_user_row(userdata)

        self.UserList.set_sensitive(True)

        # Reinitialize sorting after loop is complet
        self.usersmodel.set_sort_column_id(2, Gtk.SortType.ASCENDING)
        self.usersmodel.set_default_sort_func(lambda *args: -1)

        # Spit this line into chat log
        append_line(self.ChatScroll, _("--- reconnected ---"), self.tag_hilite)

        # Update user count
        self.count_users()

        # Build completion list
        self.set_completion_list(list(self.chatrooms.completion_list))

        # Update all username tags in chat log
        for user in self.tag_users:
            self.get_user_tag(user)

    def on_autojoin(self, widget):

        autojoin = config.sections["server"]["autojoin"]

        if not widget.get_active():
            if self.room in autojoin:
                autojoin.remove(self.room)
        else:
            if self.room not in autojoin:
                autojoin.append(self.room)

        config.write_configuration()

    def on_tooltip(self, widget, x, y, keyboard_mode, tooltip):

        status_tooltip = show_user_status_tooltip(widget, x, y, tooltip, 5)
        country_tooltip = show_country_tooltip(widget, x, y, tooltip, 8, strip_prefix="")

        if status_tooltip:
            return status_tooltip

        if country_tooltip:
            return country_tooltip

    def on_log_toggled(self, widget):

        if not widget.get_active():
            if self.room in config.sections["logging"]["rooms"]:
                config.sections["logging"]["rooms"].remove(self.room)
            return

        if self.room not in config.sections["logging"]["rooms"]:
            config.sections["logging"]["rooms"].append(self.room)

    def on_copy_all_activity_log(self, *args):
        copy_all_text(self.RoomLog, self.frame.clipboard)

    def on_copy_all_room_log(self, *args):
        copy_all_text(self.ChatScroll, self.frame.clipboard)

    def on_copy_activity_log(self, *args):
        self.RoomLog.emit("copy-clipboard")

    def on_copy_room_log(self, *args):
        self.ChatScroll.emit("copy-clipboard")

    def on_view_room_log(self, *args):
        open_log(config.sections["logging"]["roomlogsdir"], self.room)

    def on_delete_room_log_response(self, dialog, response_id, data):

        dialog.destroy()

        if response_id == Gtk.ResponseType.OK:
            delete_log(config.sections["logging"]["roomlogsdir"], self.room)
            self.on_clear_messages()
            self.on_clear_activity_log()

    def on_delete_room_log(self, *args):

        option_dialog(
            parent=self.frame.MainWindow,
            title=_('Delete Logged Messages?'),
            message=_('Are you sure you wish to permanently delete all logged messages for this room?'),
            callback=self.on_delete_room_log_response
        )

    def on_clear_messages(self, *args):
        self.ChatScroll.get_buffer().set_text("")

    def on_clear_activity_log(self, *args):
        self.RoomLog.get_buffer().set_text("")

    def set_completion_list(self, completion_list):

        # We want to include users for this room only
        if config.sections["words"]["roomusers"]:
            completion_list += self.users.keys()

        # No duplicates
        completion_list = list(set(completion_list))
        completion_list.sort(key=lambda v: v.lower())

        self.entry.set_completion_list(completion_list)
