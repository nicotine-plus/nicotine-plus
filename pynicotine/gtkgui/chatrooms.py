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

from collections import deque

from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Pango

from pynicotine import slskmessages
from pynicotine.chatrooms import Tickers
from pynicotine.config import config
from pynicotine.gtkgui.roomlist import RoomList
from pynicotine.gtkgui.roomwall import RoomWall
from pynicotine.gtkgui.widgets.iconnotebook import IconNotebook
from pynicotine.gtkgui.widgets.dialogs import option_dialog
from pynicotine.gtkgui.widgets.popupmenu import PopupMenu
from pynicotine.gtkgui.widgets.textentry import ChatEntry
from pynicotine.gtkgui.widgets.textentry import CompletionEntry
from pynicotine.gtkgui.widgets.textentry import TextSearchBar
from pynicotine.gtkgui.widgets.textview import TextView
from pynicotine.gtkgui.widgets.theme import get_flag_image
from pynicotine.gtkgui.widgets.theme import get_status_image
from pynicotine.gtkgui.widgets.theme import get_user_status_color
from pynicotine.gtkgui.widgets.theme import update_widget_visuals
from pynicotine.gtkgui.widgets.treeview import initialise_columns
from pynicotine.gtkgui.widgets.treeview import save_columns
from pynicotine.gtkgui.widgets.treeview import show_country_tooltip
from pynicotine.gtkgui.widgets.treeview import show_user_status_tooltip
from pynicotine.gtkgui.widgets.ui import UserInterface
from pynicotine.logfacility import log
from pynicotine.utils import delete_log
from pynicotine.utils import get_path
from pynicotine.utils import humanize
from pynicotine.utils import human_speed
from pynicotine.utils import open_log


class ChatRooms(IconNotebook):

    def __init__(self, frame):

        self.frame = frame
        self.page_id = "chatrooms"
        self.pages = {}
        self.autojoin_rooms = set()
        self.roomlist = RoomList(self.frame)

        IconNotebook.__init__(self, self.frame, self.frame.chatrooms_notebook)
        self.notebook.connect("switch-page", self.on_switch_chat)
        self.notebook.connect("page-reordered", self.on_reordered_page)

        CompletionEntry(frame.ChatroomsEntry, self.roomlist.room_model)

        if Gtk.get_major_version() == 4:
            self.frame.ChatroomsPane.set_resize_start_child(True)
        else:
            self.frame.ChatroomsPane.child_set_property(self.notebook, "resize", True)

        self.update_visuals()

    def on_reordered_page(self, notebook, page, page_num, force=0):

        room_tab_order = {}

        # Find position of opened autojoined rooms
        for room, page in self.pages.items():

            if room not in config.sections["server"]["autojoin"]:
                continue

            room_tab_order[notebook.page_num(page.Main)] = room

        pos = 1000

        # Add closed autojoined rooms as well
        for room in config.sections["server"]["autojoin"]:
            if room not in self.pages:
                room_tab_order[pos] = room
                pos += 1

        # Sort by "position"
        rto = sorted(room_tab_order.keys())
        new_autojoin = []
        for roomplace in rto:
            new_autojoin.append(room_tab_order[roomplace])

        # Save
        config.sections["server"]["autojoin"] = new_autojoin

    def on_switch_chat(self, notebook, page, page_num):

        if self.frame.current_page_id != self.page_id:
            return

        for room, tab in self.pages.items():
            if tab.Main == page:
                GLib.idle_add(lambda: tab.ChatEntry.grab_focus() == -1)

                # If the tab hasn't been opened previously, scroll chat to bottom
                if not tab.opened:
                    GLib.idle_add(tab.log_textview.scroll_bottom)
                    GLib.idle_add(tab.chat_textview.scroll_bottom)
                    tab.opened = True

                # Remove hilite
                self.frame.notifications.clear("rooms", None, room)
                break

    def clear_notifications(self):

        if self.frame.current_page_id != self.page_id:
            return

        page = self.get_nth_page(self.get_current_page())

        for room, tab in self.pages.items():
            if tab.Main == page:
                # Remove hilite
                self.frame.notifications.clear("rooms", None, room)
                break

    def room_list(self, msg):

        self.roomlist.set_room_list(msg.rooms, msg.ownedprivaterooms, msg.otherprivaterooms)

        if config.sections["words"]["roomnames"]:
            self.frame.update_completions()

    def join_room(self, msg):

        page = self.pages.get(msg.room)

        if page is not None:
            page.rejoined(msg.users)
            return

        self.pages[msg.room] = tab = ChatRoom(self, msg.room, msg.users)

        self.append_page(tab.Main, msg.room, tab.on_leave_room)
        tab.set_label(self.get_tab_label_inner(tab.Main))

        if msg.room in self.autojoin_rooms:
            self.autojoin_rooms.remove(msg.room)
        else:
            # Did not auto-join room, switch to tab
            page_num = self.page_num(tab.Main)
            self.set_current_page(page_num)

        if msg.room != "Public ":
            self.frame.RoomSearchCombo.append_text(msg.room)

        if self.get_n_pages() > 0:
            self.frame.chatrooms_status_page.hide()

    def leave_room(self, msg):

        page = self.pages.get(msg.room)

        if page is None:
            return

        self.remove_page(page.Main)
        del self.pages[msg.room]

        if msg.room != "Public ":
            self.frame.RoomSearchCombo.remove_all()
            self.frame.RoomSearchCombo.append_text("Joined Rooms ")

            for room in self.pages:
                self.frame.RoomSearchCombo.append_text(room)

        if self.get_n_pages() == 0:
            self.frame.chatrooms_status_page.show()

    def private_room_users(self, msg):
        pass

    def private_room_owned(self, msg):
        pass

    def private_room_add_user(self, msg):
        pass

    def private_room_remove_user(self, msg):
        pass

    def private_room_operator_added(self, msg):
        pass

    def private_room_operator_removed(self, msg):
        pass

    def private_room_add_operator(self, msg):
        pass

    def private_room_remove_operator(self, msg):
        pass

    def private_room_added(self, msg):
        user_count = 0
        self.roomlist.update_room(msg.room, user_count)

    def private_room_removed(self, msg):
        pass

    def private_room_disown(self, msg):
        pass

    def get_user_stats(self, msg):
        for page in self.pages.values():
            page.get_user_stats(msg.user, msg.avgspeed, msg.files)

    def get_user_status(self, msg):
        for page in self.pages.values():
            page.get_user_status(msg.user, msg.status)

    def set_user_country(self, user, country):
        for page in self.pages.values():
            page.set_user_country(user, country)

    def user_joined_room(self, msg):

        page = self.pages.get(msg.room)
        if page is not None:
            page.user_joined_room(msg.userdata)

    def user_left_room(self, msg):

        page = self.pages.get(msg.room)
        if page is not None:
            page.user_left_room(msg.username)

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

    def echo_message(self, room, text, message_type):

        page = self.pages.get(room)
        if page is not None:
            page.echo_message(text, message_type)

    def say_chat_room(self, msg):

        page = self.pages.get(msg.room)
        if page is not None:
            page.say_chat_room(msg)

    def public_room_message(self, msg):

        page = self.pages.get("Public ")
        if page is not None:
            page.say_chat_room(msg, public=True)

    def toggle_chat_buttons(self):
        for page in self.pages.values():
            page.toggle_chat_buttons()

    def set_completion_list(self, completion_list):
        for page in self.pages.values():
            page.set_completion_list(list(completion_list))

    def update_visuals(self):

        for page in self.pages.values():
            page.update_visuals()
            page.update_tags()

        self.roomlist.update_visuals()

    def save_columns(self):

        for room in list(config.sections["columns"]["chat_room"].keys())[:]:
            if room not in self.pages:
                del config.sections["columns"]["chat_room"][room]

        for page in self.pages.values():
            page.save_columns()

    def server_login(self):

        for room in config.sections["server"]["autojoin"]:
            if room == 'Public ':
                self.roomlist.feed_check.set_active(True)

            elif isinstance(room, str):
                self.autojoin_rooms.add(room)

    def server_disconnect(self):

        self.roomlist.clear()
        self.autojoin_rooms.clear()

        for page in self.pages.values():
            page.server_disconnect()


class ChatRoom(UserInterface):

    def __init__(self, chatrooms, room, users):

        super().__init__("ui/chatrooms.ui")

        self.chatrooms = chatrooms
        self.frame = chatrooms.frame
        self.room = room

        self.command_help = UserInterface("ui/popovers/chatroomcommands.ui")

        self.ShowChatHelp.set_popover(self.command_help.popover)

        if Gtk.get_major_version() == 4:
            self.ShowRoomWall.set_icon_name("view-list-symbolic")
            self.ShowChatHelp.set_icon_name("dialog-question-symbolic")

            self.ChatPaned.set_resize_start_child(True)
            self.ChatPaned.set_shrink_start_child(False)
            self.ChatPaned.set_resize_end_child(False)
            self.ChatPanedSecond.set_shrink_end_child(False)

        else:
            self.ShowRoomWall.set_image(Gtk.Image.new_from_icon_name("view-list-symbolic", Gtk.IconSize.BUTTON))
            self.ShowChatHelp.set_image(Gtk.Image.new_from_icon_name("dialog-question-symbolic", Gtk.IconSize.BUTTON))

            self.ChatPaned.child_set_property(self.ChatPanedSecond, "resize", True)
            self.ChatPaned.child_set_property(self.ChatPanedSecond, "shrink", False)
            self.ChatPaned.child_set_property(self.UserView, "resize", False)
            self.ChatPanedSecond.child_set_property(self.ChatView, "shrink", False)

        self.tickers = Tickers()
        self.room_wall = RoomWall(self.frame, self)
        self.leaving = False
        self.opened = False

        self.users = {}

        # Log Text Search
        TextSearchBar(self.RoomLog, self.LogSearchBar, self.LogSearchEntry)

        self.log_textview = TextView(self.RoomLog, font="chatfont")

        # Chat Text Search
        TextSearchBar(self.ChatScroll, self.ChatSearchBar, self.ChatSearchEntry,
                      controller_widget=self.ChatView, focus_widget=self.ChatEntry)

        self.chat_textview = TextView(self.ChatScroll, font="chatfont")

        # Chat Entry
        self.entry = ChatEntry(self.frame, self.ChatEntry, room, slskmessages.SayChatroom,
                               self.frame.np.chatrooms.send_message, self.frame.np.chatrooms.CMDS, is_chatroom=True)

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
            str,                  # (8)  country
            Pango.Weight,         # (9)  username_weight
            Pango.Underline       # (10) username_underline
        )
        self.UserList.set_model(self.usersmodel)

        self.column_numbers = list(range(self.usersmodel.get_n_columns()))
        attribute_columns = (9, 10)
        self.cols = cols = initialise_columns(
            ("chat_room", room), self.UserList,
            ["status", _("Status"), 25, "pixbuf", None],
            ["country", _("Country"), 25, "pixbuf", None],
            ["user", _("User"), 100, "text", attribute_columns],
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

        PopupMenu(self.frame, self.RoomLog, self.on_popup_menu_log).setup(
            ("#" + _("Find…"), self.on_find_activity_log),
            ("", None),
            ("#" + _("Copy"), self.log_textview.on_copy_text),
            ("#" + _("Copy All"), self.log_textview.on_copy_all_text),
            ("", None),
            ("#" + _("Clear Activity View"), self.log_textview.on_clear_all_text),
            ("", None),
            ("#" + _("_Leave Room"), self.on_leave_room)
        )

        PopupMenu(self.frame, self.ChatScroll, self.on_popup_menu_chat).setup(
            ("#" + _("Find…"), self.on_find_room_log),
            ("", None),
            ("#" + _("Copy"), self.chat_textview.on_copy_text),
            ("#" + _("Copy Link"), self.chat_textview.on_copy_link),
            ("#" + _("Copy All"), self.chat_textview.on_copy_all_text),
            ("", None),
            ("#" + _("View Room Log"), self.on_view_room_log),
            ("#" + _("Delete Room Log…"), self.on_delete_room_log),
            ("", None),
            ("#" + _("Clear Message View"), self.chat_textview.on_clear_all_text),
            ("#" + _("_Leave Room"), self.on_leave_room)
        )

        self.tab_menu = PopupMenu(self.frame)
        self.tab_menu.setup(
            ("#" + _("_Leave Room"), self.on_leave_room)
        )

        self.ChatEntry.grab_focus()
        self.set_completion_list(list(self.frame.np.chatrooms.completion_list))

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
        status_image = get_status_image(status)
        flag_image = get_flag_image(country)

        # Request user's IP address, so we can get the country and ignore messages by IP
        self.frame.np.queue.append(slskmessages.GetPeerAddress(username))

        h_speed = ""
        avgspeed = userdata.avgspeed

        if avgspeed > 0:
            h_speed = human_speed(avgspeed)

        files = userdata.files
        h_files = humanize(files)

        weight = Pango.Weight.NORMAL
        underline = Pango.Underline.NONE

        if self.room in self.frame.np.chatrooms.private_rooms:
            if username == self.frame.np.chatrooms.private_rooms[self.room]["owner"]:
                weight = Pango.Weight.BOLD
                underline = Pango.Underline.SINGLE

            elif username in self.frame.np.chatrooms.private_rooms[self.room]["operators"]:
                weight = Pango.Weight.BOLD
                underline = Pango.Underline.NONE

        iterator = self.usersmodel.insert_with_valuesv(
            -1, self.column_numbers,
            [
                GObject.Value(GObject.TYPE_OBJECT, status_image),
                GObject.Value(GObject.TYPE_OBJECT, flag_image),
                username,
                h_speed,
                h_files,
                status,
                GObject.Value(GObject.TYPE_UINT64, avgspeed),
                GObject.Value(GObject.TYPE_UINT64, files),
                country,
                weight,
                underline
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

    def append_log_lines(self, path, numlines):

        try:
            self._append_log_lines(path, numlines, 'utf-8')

        except UnicodeDecodeError:
            self._append_log_lines(path, numlines, 'latin-1')

    def _append_log_lines(self, path, numlines, encoding='utf-8'):

        with open(path, 'r', encoding=encoding) as lines:
            # Only show as many log lines as specified in config
            lines = deque(lines, numlines)
            login = config.sections["server"]["login"]

            for line in lines:
                user = None
                tag = None
                usertag = None

                if "[" in line and "] " in line:
                    start = line.find("[")
                    end = line.find("] ")

                    if end > start:
                        user = line[start + 1:end].strip()
                        usertag = self.get_user_tag(user)

                        if user == login:
                            tag = self.tag_local

                        elif login.lower() in line[end:].lower():
                            tag = self.tag_hilite

                        else:
                            tag = self.tag_remote

                elif "* " in line:
                    tag = self.tag_action

                if user != login:
                    self.chat_textview.append_line(self.frame.np.privatechats.censor_chat(line), tag, username=user,
                                                   usertag=usertag, timestamp_format="", scroll=False)
                else:
                    self.chat_textview.append_line(line, tag, username=user, usertag=usertag,
                                                   timestamp_format="", scroll=False)

            if lines:
                self.chat_textview.append_line(_("--- old messages above ---"), self.tag_hilite, scroll=False)

    def populate_user_menu(self, user):

        self.popup_menu.set_user(user)
        self.popup_menu.toggle_user_items()
        self.popup_menu.populate_private_rooms(self.popup_menu_private_rooms)

        private_rooms_enabled = (self.popup_menu_private_rooms.items
                                 and self.popup_menu.user != config.sections["server"]["login"])

        self.popup_menu.get_actions()[_("Private Rooms")].set_enabled(private_rooms_enabled)

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
            self.frame.np.privatechats.show_user(user)
            self.frame.change_main_page("private")

    def on_popup_menu(self, menu, treeview):

        user = self.get_selected_username(treeview)
        if user is None:
            return True

        self.populate_user_menu(user)

    def on_popup_menu_log(self, menu, textview):

        actions = menu.get_actions()
        actions[_("Copy")].set_enabled(self.log_textview.get_has_selection())

    def on_popup_menu_chat(self, menu, textview):

        actions = menu.get_actions()
        actions[_("Copy")].set_enabled(self.chat_textview.get_has_selection())
        actions[_("Copy Link")].set_enabled(bool(self.chat_textview.get_url_for_selected_pos()))

    def toggle_chat_buttons(self):
        self.Speech.set_visible(config.sections["ui"]["speechenabled"])

    def update_room_wall_tooltip(self, active):

        if active:
            self.ShowRoomWall.set_tooltip_text(_("Room wall (personal message set)"))
            return

        self.ShowRoomWall.set_tooltip_text(_("Room wall"))

    def ticker_set(self, msg):

        self.tickers.set_ticker([])
        login = config.sections["server"]["login"]
        has_own_ticker = False

        for user in msg.msgs:
            if user == login:
                has_own_ticker = True

            if self.frame.np.network_filter.is_user_ignored(user) or \
                    self.frame.np.network_filter.is_user_ip_ignored(user):
                # User ignored, ignore Ticker messages
                continue

            self.tickers.add_ticker(user, msg.msgs[user])

        self.update_room_wall_tooltip(has_own_ticker)

    def ticker_add(self, msg):

        user = msg.user
        login = config.sections["server"]["login"]

        if user == login:
            self.update_room_wall_tooltip(True)

        if self.frame.np.network_filter.is_user_ignored(user) or self.frame.np.network_filter.is_user_ip_ignored(user):
            # User ignored, ignore Ticker messages
            return

        self.tickers.add_ticker(msg.user, msg.msg)

    def ticker_remove(self, msg):

        login = config.sections["server"]["login"]

        if msg.user == login:
            self.update_room_wall_tooltip(False)

        self.tickers.remove_ticker(msg.user)

    def show_notification(self, login, user, text, tag):

        if user == login:
            return

        if tag == self.tag_hilite:

            # Hilight top-level tab label
            self.frame.request_tab_hilite(self.chatrooms.page_id, status=1)

            # Hilight sub-level tab label
            self.chatrooms.request_hilite(self.Main)

            if config.sections["notifications"]["notification_popup_chatroom_mention"]:
                self.frame.notifications.new_text_notification(
                    text,
                    title=_("%(user)s mentioned you in the %(room)s room") % {"user": user, "room": self.room},
                    priority=Gio.NotificationPriority.HIGH
                )

        else:
            # Hilight top-level tab label
            self.frame.request_tab_hilite(self.chatrooms.page_id, status=0)

            # Hilight sub-level tab label
            self.chatrooms.request_changed(self.Main)

        # Don't show notifications if the chat is open and the window
        # is in use
        if self.chatrooms.get_current_page() == \
           self.chatrooms.page_num(self.Main) and \
           self.frame.current_page_id == self.chatrooms.page_id and \
           self.frame.MainWindow.is_active():
            return

        if tag == self.tag_hilite:
            # We were mentioned, update tray icon and show urgency hint
            self.frame.notifications.add("rooms", user, self.room)

        elif config.sections["notifications"]["notification_popup_chatroom"]:
            self.frame.notifications.new_text_notification(
                text,
                title=_("Message by %(user)s in the %(room)s room") % {"user": user, "room": self.room},
                priority=Gio.NotificationPriority.HIGH
            )

    def say_chat_room(self, msg, public=False):

        user = msg.user
        text = msg.msg

        if self.frame.np.network_filter.is_user_ignored(user):
            return

        if self.frame.np.network_filter.is_user_ip_ignored(user):
            return

        login = config.sections["server"]["login"]

        if user == login:
            tag = self.tag_local
        elif text.upper().find(login.upper()) > -1:
            tag = self.tag_hilite
        else:
            tag = self.tag_remote

        self.show_notification(login, user, text, tag)

        if text.startswith("/me "):
            if public:
                line = "%s | * %s %s" % (msg.room, user, text[4:])
            else:
                line = "* %s %s" % (user, text[4:])

            speech = line[2:]
            tag = self.tag_action

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

        usertag = self.get_user_tag(user)
        timestamp_format = config.sections["logging"]["rooms_timestamp"]

        if user != login:
            self.chat_textview.append_line(
                self.frame.np.privatechats.censor_chat(line), tag,
                username=user, usertag=usertag, timestamp_format=timestamp_format
            )

            if self.Speech.get_active():

                self.frame.np.notifications.new_tts(
                    config.sections["ui"]["speechrooms"], {
                        "room": self.room,
                        "user": user,
                        "message": speech
                    }
                )
        else:
            self.chat_textview.append_line(
                line, tag,
                username=user, usertag=usertag, timestamp_format=timestamp_format
            )

    def echo_message(self, text, message_type):

        tag = self.tag_action
        timestamp_format = config.sections["logging"]["rooms_timestamp"]

        if hasattr(self, "tag_" + str(message_type)):
            tag = getattr(self, "tag_" + str(message_type))

        self.chat_textview.append_line(text, tag, timestamp_format=timestamp_format)

    def user_joined_room(self, userdata):

        username = userdata.username

        if username in self.users:
            return

        # Add to completion list, and completion drop-down
        self.entry.add_completion(username)

        if not self.frame.np.network_filter.is_user_ignored(username) and \
                not self.frame.np.network_filter.is_user_ip_ignored(username):
            self.log_textview.append_line(_("%s joined the room") % username, self.tag_log)

        self.add_user_row(userdata)

        self.update_user_tag(username)
        self.count_users()

    def user_left_room(self, username):

        if username not in self.users:
            return

        # Remove from completion list, and completion drop-down
        if username not in (i[0] for i in config.sections["server"]["userlist"]):
            self.entry.remove_completion(username)

        if not self.frame.np.network_filter.is_user_ignored(username) and \
                not self.frame.np.network_filter.is_user_ip_ignored(username):
            self.log_textview.append_line(_("%s left the room") % username, self.tag_log)

        self.usersmodel.remove(self.users[username])
        del self.users[username]

        self.update_user_tag(username)
        self.count_users()

    def count_users(self):

        user_count = len(self.users)
        self.LabelPeople.set_text(str(user_count))
        self.chatrooms.roomlist.update_room(self.room, user_count)

    def get_user_stats(self, user, avgspeed, files):

        if user not in self.users:
            return

        h_speed = ""

        if avgspeed > 0:
            h_speed = human_speed(avgspeed)

        self.usersmodel.set_value(self.users[user], 3, h_speed)
        self.usersmodel.set_value(self.users[user], 4, humanize(files))
        self.usersmodel.set_value(self.users[user], 6, GObject.Value(GObject.TYPE_UINT64, avgspeed))
        self.usersmodel.set_value(self.users[user], 7, GObject.Value(GObject.TYPE_UINT64, files))

    def get_user_status(self, user, status):

        if user not in self.users:
            return

        img = get_status_image(status)
        if img == self.usersmodel.get_value(self.users[user], 0):
            return

        if status == 1:
            action = _("%s has gone away")
        else:
            action = _("%s has returned")

        if not self.frame.np.network_filter.is_user_ignored(user) and \
                not self.frame.np.network_filter.is_user_ip_ignored(user):
            self.log_textview.append_line(action % user, self.tag_log)

        self.usersmodel.set_value(self.users[user], 0, GObject.Value(GObject.TYPE_OBJECT, img))
        self.usersmodel.set_value(self.users[user], 5, status)

        self.update_user_tag(user)

    def set_user_country(self, user, country):

        if user not in self.users:
            return

        if self.usersmodel.get_value(self.users[user], 8) == country:
            # Country didn't change, no need to update
            return

        flag_image = get_flag_image(country)

        if not flag_image:
            return

        self.usersmodel.set_value(self.users[user], 1, GObject.Value(GObject.TYPE_OBJECT, flag_image))
        self.usersmodel.set_value(self.users[user], 8, country)

    def update_visuals(self):

        for widget in list(self.__dict__.values()):
            update_widget_visuals(widget)

        self.room_wall.update_visuals()

    def user_name_event(self, x, y, user):
        self.populate_user_menu(user)
        self.popup_menu.popup(x, y, button=1)

    def create_tags(self):

        self.tag_log = self.log_textview.create_tag("chatremote")

        self.tag_remote = self.chat_textview.create_tag("chatremote")
        self.tag_local = self.chat_textview.create_tag("chatlocal")
        self.tag_action = self.chat_textview.create_tag("chatme")
        self.tag_hilite = self.chat_textview.create_tag("chathilite")

        self.tag_users = {}

    def get_user_tag(self, username):

        if username not in self.tag_users:
            self.tag_users[username] = self.chat_textview.create_tag(callback=self.user_name_event, username=username)
            self.update_user_tag(username)

        return self.tag_users[username]

    def update_user_tag(self, username):

        if username not in self.tag_users:
            return

        if username not in self.users:
            color = "useroffline"
        else:
            status = self.usersmodel.get_value(self.users[username], 5)
            color = get_user_status_color(status)

        self.chat_textview.update_tag(self.tag_users[username], color)

    def update_tags(self):

        for tag in (self.tag_remote, self.tag_local, self.tag_action, self.tag_hilite, self.tag_log):
            self.chat_textview.update_tag(tag)

        for tag in self.tag_users.values():
            self.chat_textview.update_tag(tag)

    def save_columns(self):
        save_columns("chat_room", self.UserList.get_columns(), subpage=self.room)

    def server_disconnect(self):

        self.usersmodel.clear()
        self.users.clear()
        self.count_users()

        if (self.room not in config.sections["server"]["autojoin"]
                and self.room in config.sections["columns"]["chat_room"]):
            del config.sections["columns"]["chat_room"][self.room]

        self.tickers.set_ticker([])

        self.chat_textview.append_line(_("--- disconnected ---"), self.tag_hilite)
        self.UserList.set_sensitive(False)

        for username in self.tag_users:
            self.update_user_tag(username)

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
        self.chat_textview.append_line(_("--- reconnected ---"), self.tag_hilite)

        # Update user count
        self.count_users()

        # Build completion list
        self.set_completion_list(list(self.frame.np.chatrooms.completion_list))

        # Update all username tags in chat log
        for username in self.tag_users:
            self.update_user_tag(username)

    def on_autojoin(self, widget):

        autojoin = config.sections["server"]["autojoin"]
        active = widget.get_active()

        if not active and self.room in autojoin:
            autojoin.remove(self.room)

        elif active and self.room not in autojoin:
            autojoin.append(self.room)

        config.write_configuration()

    def on_leave_room(self, *args):

        if self.leaving:
            return

        self.leaving = True

        if self.room in config.sections["columns"]["chat_room"]:
            del config.sections["columns"]["chat_room"][self.room]

        if self.room == "Public ":
            self.chatrooms.roomlist.feed_check.set_active(False)
            return

        self.frame.np.chatrooms.request_leave_room(self.room)

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

    def on_view_room_log(self, *args):
        open_log(config.sections["logging"]["roomlogsdir"], self.room)

    def on_delete_room_log_response(self, dialog, response_id, data):

        dialog.destroy()

        if response_id == Gtk.ResponseType.OK:
            delete_log(config.sections["logging"]["roomlogsdir"], self.room)
            self.log_textview.clear()
            self.chat_textview.clear()

    def on_delete_room_log(self, *args):

        option_dialog(
            parent=self.frame.MainWindow,
            title=_('Delete Logged Messages?'),
            message=_('Do you really want to permanently delete all logged messages for this room?'),
            callback=self.on_delete_room_log_response
        )

    def on_ignore_users_settings(self, *args):
        self.frame.on_settings(page='IgnoredUsers')

    def set_completion_list(self, completion_list):

        # We want to include users for this room only
        if config.sections["words"]["roomusers"]:
            completion_list += self.users.keys()

        # No duplicates
        completion_list = list(set(completion_list))
        completion_list.sort(key=lambda v: v.lower())

        self.entry.set_completion_list(completion_list)
