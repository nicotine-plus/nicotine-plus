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

from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Pango

from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.popovers.chatcommandhelp import ChatCommandHelp
from pynicotine.gtkgui.popovers.roomlist import RoomList
from pynicotine.gtkgui.popovers.roomwall import RoomWall
from pynicotine.gtkgui.widgets import ui
from pynicotine.gtkgui.widgets.iconnotebook import IconNotebook
from pynicotine.gtkgui.widgets.dialogs import OptionDialog
from pynicotine.gtkgui.widgets.popupmenu import PopupMenu
from pynicotine.gtkgui.widgets.popupmenu import UserPopupMenu
from pynicotine.gtkgui.widgets.textentry import ChatCompletion
from pynicotine.gtkgui.widgets.textentry import ChatEntry
from pynicotine.gtkgui.widgets.textentry import TextSearchBar
from pynicotine.gtkgui.widgets.textview import ChatView
from pynicotine.gtkgui.widgets.textview import TextView
from pynicotine.gtkgui.widgets.theme import USER_STATUS_ICON_NAMES
from pynicotine.gtkgui.widgets.theme import get_flag_icon_name
from pynicotine.gtkgui.widgets.treeview import TreeView
from pynicotine.logfacility import log
from pynicotine.slskmessages import UserStatus
from pynicotine.utils import clean_file
from pynicotine.utils import humanize
from pynicotine.utils import human_speed


class ChatRooms(IconNotebook):

    def __init__(self, window):

        super().__init__(
            window,
            parent=window.chatrooms_content,
            parent_page=window.chatrooms_page,
            switch_page_callback=self.on_switch_chat,
            reorder_page_callback=self.on_reordered_page
        )

        self.highlighted_rooms = {}
        self.completion = ChatCompletion()
        self.room_list = RoomList(window)
        self.command_help = None
        self.room_wall = None

        if GTK_API_VERSION >= 4:
            self.window.chatrooms_paned.set_resize_start_child(True)
        else:
            self.window.chatrooms_paned.child_set_property(self.window.chatrooms_container, "resize", True)

        for event_name, callback in (
            ("clear-room-messages", self.clear_room_messages),
            ("echo-room-message", self.echo_room_message),
            ("global-room-message", self.global_room_message),
            ("join-room", self.join_room),
            ("remove-room", self.remove_room),
            ("room-completions", self.update_completions),
            ("say-chat-room", self.say_chat_room),
            ("server-disconnect", self.server_disconnect),
            ("show-room", self.show_room),
            ("user-country", self.user_country),
            ("user-joined-room", self.user_joined_room),
            ("user-left-room", self.user_left_room),
            ("user-stats", self.user_stats),
            ("user-status", self.user_status)
        ):
            events.connect(event_name, callback)

    def on_remove_all_pages(self, *_args):
        core.chatrooms.remove_all_rooms()

    def on_restore_removed_page(self, page_args):
        room, is_private = page_args
        core.chatrooms.show_room(room, is_private=is_private)

    def on_reordered_page(self, *_args):

        room_tab_order = {}

        # Find position of opened auto-joined rooms
        for room, room_page in self.pages.items():
            room_position = self.page_num(room_page.container)
            room_tab_order[room_position] = room

        config.sections["server"]["autojoin"] = [room for room_index, room in sorted(room_tab_order.items())]

    def on_switch_chat(self, _notebook, page, _page_num):

        if self.window.current_page_id != self.window.chatrooms_page.id:
            return

        for room, tab in self.pages.items():
            if tab.container != page:
                continue

            self.completion.set_entry(tab.chat_entry)
            tab.update_room_user_completions()

            if self.command_help is None:
                self.command_help = ChatCommandHelp(window=self.window, interface="chatroom")

            if self.room_wall is None:
                self.room_wall = RoomWall(window=self.window)

            self.command_help.widget.unparent()
            self.room_wall.widget.unparent()
            self.room_wall.room = room

            tab.help_button.set_popover(self.command_help.widget)
            tab.room_wall_button.set_popover(self.room_wall.widget)

            if not tab.loaded:
                tab.load()

            # Remove highlight
            self.unhighlight_room(room)
            break

    def on_create_room_response(self, dialog, _response_id, room):
        private = dialog.get_option_value()
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
        self.remove_page(page.container, page_args=(room, page.is_private))
        del self.pages[room]

        if room != core.chatrooms.GLOBAL_ROOM_NAME:
            self.window.search.room_search_combobox.remove_id(room)

    def highlight_room(self, room, user):

        if not room or room in self.highlighted_rooms:
            return

        self.highlighted_rooms[room] = user
        self.window.application.notifications.update_title()
        self.window.application.tray_icon.update_icon()

    def unhighlight_room(self, room):

        if room not in self.highlighted_rooms:
            return

        del self.highlighted_rooms[room]
        self.window.application.notifications.update_title()
        self.window.application.tray_icon.update_icon()

    def join_room(self, msg):

        page = self.pages.get(msg.room)
        is_auto_joined = (msg.room in core.chatrooms.pending_autojoin_rooms)

        if is_auto_joined:
            core.chatrooms.pending_autojoin_rooms.remove(msg.room)

        if page is not None:
            page.join_room(msg)
            return

        self.pages[msg.room] = tab = ChatRoom(self, msg.room, msg.users, is_private=msg.private)
        is_global = (msg.room == core.chatrooms.GLOBAL_ROOM_NAME)

        if is_global:
            self.prepend_page(tab.container, msg.room, focus_callback=tab.on_focus, close_callback=tab.on_leave_room)
        else:
            self.append_page(tab.container, msg.room, focus_callback=tab.on_focus, close_callback=tab.on_leave_room)

        tab.set_label(self.get_tab_label_inner(tab.container))

        if not is_auto_joined:
            # Did not auto-join room, switch to tab
            core.chatrooms.show_room(msg.room)

        if not is_global:
            self.window.search.room_search_combobox.append(msg.room)

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

    def update_completions(self, completions):

        page = self.get_current_page()

        for tab in self.pages.values():
            if tab.container == page:
                tab.update_completions(completions)
                break

    def update_tags(self):
        for page in self.pages.values():
            page.update_tags()

    def server_disconnect(self, *_args):
        for page in self.pages.values():
            page.server_disconnect()


class ChatRoom:

    def __init__(self, chatrooms, room, users, is_private):

        (
            self.activity_container,
            self.activity_search_bar,
            self.activity_search_entry,
            self.activity_view_container,
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
            self.users_container,
            self.users_label,
            self.users_list_container,
            self.users_paned
        ) = ui.load(scope=self, path="chatrooms.ui")

        self.chatrooms = chatrooms
        self.window = chatrooms.window
        self.room = room
        self.is_private = is_private

        if GTK_API_VERSION >= 4:
            self.users_paned.set_resize_start_child(True)
            self.users_paned.set_shrink_start_child(False)
            self.users_paned.set_resize_end_child(False)
            self.users_paned.set_shrink_end_child(False)
            self.chat_paned.set_shrink_end_child(False)

            self.room_wall_button.set_has_frame(False)
        else:
            self.users_paned.child_set_property(self.chat_paned, "resize", True)
            self.users_paned.child_set_property(self.chat_paned, "shrink", False)
            self.users_paned.child_set_property(self.users_container, "resize", False)
            self.users_paned.child_set_property(self.users_container, "shrink", False)
            self.chat_paned.child_set_property(self.chat_container, "shrink", False)

        self.loaded = False

        self.activity_view = TextView(self.activity_view_container, parse_urls=False, editable=False,
                                      horizontal_margin=10, vertical_margin=5, pixels_below_lines=2)
        self.chat_view = ChatView(self.chat_view_container, chat_entry=self.chat_entry, editable=False,
                                  horizontal_margin=10, vertical_margin=5, pixels_below_lines=2,
                                  status_users=core.chatrooms.joined_rooms[self.room].users,
                                  username_event=self.username_event)

        # Event Text Search
        self.activity_search_bar = TextSearchBar(self.activity_view.widget, self.activity_search_bar,
                                                 self.activity_search_entry)

        # Chat Text Search
        self.chat_search_bar = TextSearchBar(self.chat_view.widget, self.chat_search_bar, self.chat_search_entry,
                                             controller_widget=self.chat_container, focus_widget=self.chat_entry)

        # Chat Entry
        ChatEntry(self.window.application, self.chat_entry, self.chat_view, chatrooms.completion, room,
                  core.chatrooms.send_message, is_chatroom=True)

        self.log_toggle.set_active(config.sections["logging"]["chatrooms"])
        if not self.log_toggle.get_active():
            self.log_toggle.set_active(self.room in config.sections["logging"]["rooms"])

        self.toggle_chat_buttons()

        self.users_list_view = TreeView(
            self.window, parent=self.users_list_container, name="chat_room", secondary_name=room,
            activate_row_callback=self.on_row_activated,
            columns={
                # Visible columns
                "status": {
                    "column_type": "icon",
                    "title": _("Status"),
                    "width": 25,
                    "sort_column": "status_data",
                    "hide_header": True
                },
                "country": {
                    "column_type": "icon",
                    "title": _("Country"),
                    "width": 30,
                    "sort_column": "country_data",
                    "hide_header": True
                },
                "user": {
                    "column_type": "text",
                    "title": _("User"),
                    "width": 155,
                    "expand_column": True,
                    "iterator_key": True,
                    "default_sort_type": "ascending",
                    "text_underline_column": "username_underline_data",
                    "text_weight_column": "username_weight_data"
                },
                "speed": {
                    "column_type": "number",
                    "title": _("Speed"),
                    "width": 100,
                    "sort_column": "speed_data",
                    "expand_column": True
                },
                "files": {
                    "column_type": "number",
                    "title": _("Files"),
                    "sort_column": "files_data",
                    "expand_column": True
                },

                # Hidden data columns
                "status_data": {"data_type": int},
                "speed_data": {"data_type": GObject.TYPE_UINT},
                "files_data": {"data_type": GObject.TYPE_UINT},
                "country_data": {"data_type": str},
                "username_weight_data": {"data_type": Pango.Weight},
                "username_underline_data": {"data_type": Pango.Underline}
            }
        )

        self.users_list_view.disable_sorting()

        for userdata in users:
            self.add_user_row(userdata)

        self.users_list_view.enable_sorting()

        self.popup_menu_private_rooms_chat = UserPopupMenu(self.window.application, tab_name="chatrooms")
        self.popup_menu_private_rooms_list = UserPopupMenu(self.window.application, tab_name="chatrooms")

        self.popup_menu_user_chat = UserPopupMenu(
            self.window.application, parent=self.chat_view.widget, connect_events=False,
            tab_name="chatrooms"
        )
        self.popup_menu_user_list = UserPopupMenu(
            self.window.application, parent=self.users_list_view.widget,
            callback=self.on_popup_menu_user, tab_name="chatrooms"
        )

        for menu, menu_private_rooms in (
            (self.popup_menu_user_chat, self.popup_menu_private_rooms_chat),
            (self.popup_menu_user_list, self.popup_menu_private_rooms_list)
        ):
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
        self.update_user_count()
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
        self.users_list_view.clear()

        for menu in (self.popup_menu_private_rooms_chat, self.popup_menu_private_rooms_list,
                     self.popup_menu_user_chat, self.popup_menu_user_list, self.users_list_view.column_menu,
                     self.popup_menu_activity_view, self.popup_menu_chat_view, self.tab_menu):
            menu.clear()

    def set_label(self, label):
        self.tab_menu.set_parent(label)

    def setup_public_feed(self):

        if self.room != core.chatrooms.GLOBAL_ROOM_NAME:
            return

        for widget in (self.activity_container, self.users_container, self.chat_entry, self.help_button):
            widget.set_visible(False)

        self.speech_toggle.set_active(False)  # Public feed is jibberish and too fast for TTS
        self.chat_entry.set_sensitive(False)
        self.chat_entry_row.set_halign(Gtk.Align.END)

    def add_user_row(self, userdata):

        username = userdata.username
        status = userdata.status
        country_code = core.user_countries.get(username) or userdata.country or ""
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

        self.users_list_view.add_row([
            status_icon_name,
            flag_icon_name,
            username,
            h_speed,
            h_files,
            status,
            avgspeed,
            files,
            country_code,
            weight,
            underline
        ], select_row=False)

    def read_room_logs_finished(self):

        self.activity_view.scroll_bottom()
        self.chat_view.scroll_bottom()

        self.activity_view.auto_scroll = self.chat_view.auto_scroll = True

    def read_room_logs(self):

        numlines = config.sections["logging"]["readroomlines"]
        filename = f"{clean_file(self.room)}.log"
        path = os.path.join(config.sections["logging"]["roomlogsdir"], filename)

        self.chat_view.append_log_lines(
            path, numlines, timestamp_format=config.sections["logging"]["rooms_timestamp"]
        )

    def populate_user_menu(self, user, menu, menu_private_rooms):

        menu.set_user(user)
        menu.toggle_user_items()
        menu.populate_private_rooms(menu_private_rooms)

        private_rooms_enabled = (menu_private_rooms.items and user != core.login_username)
        menu.actions[_("Private Rooms")].set_enabled(private_rooms_enabled)

    def on_find_activity_log(self, *_args):
        self.activity_search_bar.set_visible(True)

    def on_find_room_log(self, *_args):
        self.chat_search_bar.set_visible(True)

    def get_selected_username(self):

        for iterator in self.users_list_view.get_selected_rows():
            return self.users_list_view.get_row_value(iterator, "user")

        return None

    def on_row_activated(self, _list_view, _path, _column):

        user = self.get_selected_username()

        if user is not None:
            core.userinfo.show_user(user)

    def on_popup_menu_user(self, menu, _widget):
        user = self.get_selected_username()
        self.populate_user_menu(user, menu, self.popup_menu_private_rooms_list)

    def on_popup_menu_log(self, menu, _textview):
        menu.actions[_("Copy")].set_enabled(self.activity_view.get_has_selection())

    def on_popup_menu_chat(self, menu, _textview):
        menu.actions[_("Copy")].set_enabled(self.chat_view.get_has_selection())
        menu.actions[_("Copy Link")].set_enabled(bool(self.chat_view.get_url_for_current_pos()))

    def toggle_chat_buttons(self):
        self.speech_toggle.set_visible(config.sections["ui"]["speechenabled"])

    def _show_notification(self, login, room, user, text, tag, is_global):

        if user == login:
            return

        mentioned = (tag == self.chat_view.tag_highlight)
        self.chatrooms.request_tab_changed(self.container, is_important=mentioned, is_quiet=is_global)

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

    def say_chat_room(self, msg, is_global=False):

        user = msg.user
        login_username = core.login_username
        text = msg.msg
        room = msg.room
        tag = self.chat_view.get_line_tag(user, text, login_username)

        if tag == self.chat_view.tag_action:
            line = f"* {user} {text[4:]}"
            speech = line[2:]
        else:
            line = f"[{user}] {text}"
            speech = text

        if is_global:
            line = f"{room} | {line}"

        line = "\n-- ".join(line.split("\n"))
        usertag = self.chat_view.get_user_tag(user)
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

        self._show_notification(login_username, room, user, speech, tag, is_global)

        if self.log_toggle.get_active():
            log.write_log_file(
                folder_path=config.sections["logging"]["roomlogsdir"],
                base_name=f"{clean_file(self.room)}.log", text=line
            )

    def echo_room_message(self, text, message_type):

        if hasattr(self, f"tag_{message_type}"):
            tag = getattr(self.chat_view, f"tag_{message_type}")
        else:
            tag = self.chat_view.tag_local

        if message_type != "command":
            timestamp_format = config.sections["logging"]["rooms_timestamp"]
        else:
            timestamp_format = None

        self.chat_view.append_line(text, tag, timestamp_format=timestamp_format)

    def user_joined_room(self, msg):

        userdata = msg.userdata
        username = userdata.username

        if username in self.users_list_view.iterators:
            return

        # Add to completion list, and completion drop-down
        if self.chatrooms.completion.entry == self.chat_entry:
            self.chatrooms.completion.add_completion(username)

        if not core.network_filter.is_user_ignored(username) and not core.network_filter.is_user_ip_ignored(username):
            self.activity_view.append_line(
                _("%s joined the room") % username, timestamp_format=config.sections["logging"]["rooms_timestamp"]
            )

        self.add_user_row(userdata)

        self.chat_view.update_user_tag(username)
        self.update_user_count()

    def user_left_room(self, msg):

        username = msg.username
        iterator = self.users_list_view.iterators.get(username)

        if iterator is None:
            return

        # Remove from completion list, and completion drop-down
        if self.chatrooms.completion.entry == self.chat_entry and username not in core.userlist.buddies:
            self.chatrooms.completion.remove_completion(username)

        if not core.network_filter.is_user_ignored(username) and \
                not core.network_filter.is_user_ip_ignored(username):
            timestamp_format = config.sections["logging"]["rooms_timestamp"]
            self.activity_view.append_line(_("%s left the room") % username, timestamp_format=timestamp_format)

        self.users_list_view.remove_row(iterator)

        self.chat_view.update_user_tag(username)
        self.update_user_count()

    def update_user_count(self):
        user_count = len(self.users_list_view.iterators)
        self.users_label.set_text(humanize(user_count))

    def user_stats(self, msg):

        iterator = self.users_list_view.iterators.get(msg.user)

        if iterator is None:
            return

        speed = msg.avgspeed
        num_files = msg.files
        h_speed = ""

        if speed > 0:
            h_speed = human_speed(speed)

        self.users_list_view.set_row_value(iterator, "speed", h_speed)
        self.users_list_view.set_row_value(iterator, "files", humanize(num_files))
        self.users_list_view.set_row_value(iterator, "speed_data", speed)
        self.users_list_view.set_row_value(iterator, "files_data", num_files)

    def user_status(self, msg):

        user = msg.user
        iterator = self.users_list_view.iterators.get(user)

        if iterator is None:
            return

        status = msg.status
        status_icon_name = USER_STATUS_ICON_NAMES.get(status)

        if not status_icon_name:
            return

        if status == self.users_list_view.get_row_value(iterator, "status_data"):
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
                action % user, timestamp_format=config.sections["logging"]["rooms_timestamp"])

        self.users_list_view.set_row_value(iterator, "status", status_icon_name)
        self.users_list_view.set_row_value(iterator, "status_data", status)

        self.chat_view.update_user_tag(user)

    def user_country(self, user, country_code):

        iterator = self.users_list_view.iterators.get(user)

        if iterator is None:
            return

        if self.users_list_view.get_row_value(iterator, "country_data") == country_code:
            # Country didn't change, no need to update
            return

        flag_icon_name = get_flag_icon_name(country_code)

        if not flag_icon_name:
            return

        self.users_list_view.set_row_value(iterator, "country", flag_icon_name)
        self.users_list_view.set_row_value(iterator, "country_data", country_code)

    def username_event(self, pos_x, pos_y, user):

        menu = self.popup_menu_user_chat
        menu.update_model()
        self.populate_user_menu(user, menu, self.popup_menu_private_rooms_chat)
        menu.popup(pos_x, pos_y)

    def update_tags(self):
        self.chat_view.update_tags()

    def server_disconnect(self):

        self.users_list_view.clear()
        self.update_user_count()

        if self.chatrooms.get_current_page() == self.container:
            self.update_room_user_completions()

        self.chat_view.update_user_tags()

    def join_room(self, msg):

        # Temporarily disable sorting for increased performance
        self.users_list_view.disable_sorting()

        for userdata in msg.users:
            username = userdata.username
            iterator = self.users_list_view.iterators.get(username)

            if iterator is not None:
                self.users_list_view.remove_row(iterator)

            self.add_user_row(userdata)

        self.users_list_view.enable_sorting()

        # Update user count
        self.update_user_count()

        # Update all username tags in chat log
        self.chat_view.update_user_tags()

        # Add room users to completion list
        if self.chatrooms.get_current_page() == self.container:
            self.update_room_user_completions()

    def on_focus(self, *_args):
        widget = self.chat_entry if self.chat_entry.get_sensitive() else self.chat_view.widget
        widget.grab_focus()

    def on_leave_room(self, *_args):
        core.chatrooms.remove_room(self.room)

    def on_log_toggled(self, *_args):

        if not self.log_toggle.get_active():
            if self.room in config.sections["logging"]["rooms"]:
                config.sections["logging"]["rooms"].remove(self.room)
            return

        if self.room not in config.sections["logging"]["rooms"]:
            config.sections["logging"]["rooms"].append(self.room)

    def on_view_room_log(self, *_args):
        log.open_log(config.sections["logging"]["roomlogsdir"], self.room)

    def on_delete_room_log_response(self, *_args):

        log.delete_log(config.sections["logging"]["roomlogsdir"], self.room)
        self.activity_view.clear()
        self.chat_view.clear()

    def on_delete_room_log(self, *_args):

        OptionDialog(
            parent=self.window,
            title=_("Delete Logged Messages?"),
            message=_("Do you really want to permanently delete all logged messages for this room?"),
            destructive_response_id="ok",
            callback=self.on_delete_room_log_response
        ).show()

    def update_room_user_completions(self):
        self.update_completions(core.chatrooms.completions.copy())

    def update_completions(self, completions):

        # We want to include users for this room only
        if config.sections["words"]["roomusers"]:
            room_users = core.chatrooms.joined_rooms[self.room].users
            completions.update(room_users)

        self.chatrooms.completion.set_completions(completions)
