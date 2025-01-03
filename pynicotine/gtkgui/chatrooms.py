# COPYRIGHT (C) 2020-2024 Nicotine+ Contributors
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
from pynicotine.gtkgui.widgets.textentry import ChatEntry
from pynicotine.gtkgui.widgets.textentry import TextSearchBar
from pynicotine.gtkgui.widgets.textview import ChatView
from pynicotine.gtkgui.widgets.textview import TextView
from pynicotine.gtkgui.widgets.theme import USER_STATUS_ICON_NAMES
from pynicotine.gtkgui.widgets.theme import add_css_class
from pynicotine.gtkgui.widgets.theme import get_flag_icon_name
from pynicotine.gtkgui.widgets.treeview import TreeView
from pynicotine.logfacility import log
from pynicotine.slskmessages import UserData
from pynicotine.slskmessages import UserStatus
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

        self.page = window.chatrooms_page
        self.page.id = "chatrooms"
        self.toolbar = window.chatrooms_toolbar
        self.toolbar_start_content = window.chatrooms_title
        self.toolbar_end_content = window.chatrooms_end
        self.toolbar_default_widget = window.chatrooms_entry

        self.chat_entry = ChatEntry(
            self.window.application, send_message_callback=core.chatrooms.send_message,
            command_callback=core.pluginhandler.trigger_chatroom_command_event,
            enable_spell_check=config.sections["ui"]["spellcheck"]
        )
        self.room_list = RoomList(window)
        self.command_help = None
        self.room_wall = None
        self.highlighted_rooms = {}

        window.chatrooms_entry.set_max_length(core.chatrooms.ROOM_NAME_MAX_LENGTH)

        if GTK_API_VERSION >= 4:
            window.chatrooms_paned.set_resize_start_child(True)
        else:
            window.chatrooms_paned.child_set_property(window.chatrooms_container, "resize", True)

        for event_name, callback in (
            ("clear-room-messages", self.clear_room_messages),
            ("echo-room-message", self.echo_room_message),
            ("global-room-message", self.global_room_message),
            ("ignore-user", self.ignore_user),
            ("ignore-user-ip", self.ignore_user),
            ("join-room", self.join_room),
            ("leave-room", self.leave_room),
            ("peer-address", self.peer_address),
            ("private-room-add-operator", self.private_room_add_operator),
            ("private-room-add-user", self.private_room_add_user),
            ("private-room-remove-operator", self.private_room_remove_operator),
            ("private-room-remove-user", self.private_room_remove_user),
            ("quit", self.quit),
            ("remove-room", self.remove_room),
            ("room-completions", self.update_completions),
            ("say-chat-room", self.say_chat_room),
            ("server-disconnect", self.server_disconnect),
            ("server-login", self.server_login),
            ("show-room", self.show_room),
            ("start", self.start),
            ("unignore-user", self.unignore_user),
            ("unignore-user-ip", self.unignore_user),
            ("user-country", self.user_country),
            ("user-joined-room", self.user_joined_room),
            ("user-left-room", self.user_left_room),
            ("user-stats", self.user_stats),
            ("user-status", self.user_status)
        ):
            events.connect(event_name, callback)

        self.freeze()

    def start(self):
        self.unfreeze()

    def quit(self):
        self.freeze()

    def destroy(self):

        self.chat_entry.destroy()
        self.room_list.destroy()

        if self.command_help is not None:
            self.command_help.destroy()

        if self.room_wall is not None:
            self.room_wall.destroy()

        super().destroy()

    def on_focus(self, *_args):

        if self.window.current_page_id != self.window.chatrooms_page.id:
            return True

        if self.get_n_pages():
            return True

        if self.window.chatrooms_entry.is_sensitive():
            self.window.chatrooms_entry.grab_focus()
            return True

        return False

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

            joined_room = core.chatrooms.joined_rooms.get(room)

            self.chat_entry.set_parent(room, tab.chat_entry_container, tab.chat_view)
            self.chat_entry.set_sensitive(joined_room is not None and joined_room.users)
            tab.update_room_user_completions()

            if self.command_help is None:
                self.command_help = ChatCommandHelp(window=self.window, interface="chatroom")

            if self.room_wall is None:
                self.room_wall = RoomWall(window=self.window)

            self.command_help.set_menu_button(tab.help_button)
            self.room_wall.set_menu_button(tab.room_wall_button)
            self.room_wall.room = room

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
            room = core.chatrooms.sanitize_room_name(room)
            OptionDialog(
                parent=self.window,
                title=_("Create New Room?"),
                message=_('Do you really want to create a new room "%s"?') % room,
                option_label=_("Make room private"),
                callback=self.on_create_room_response,
                callback_data=room
            ).present()
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

    def show_room(self, room, is_private=False, switch_page=True, remembered=False):

        if room not in self.pages:
            is_global = (room == core.chatrooms.GLOBAL_ROOM_NAME)
            tab_position = 0 if is_global and not remembered else -1
            self.pages[room] = tab = ChatRoom(self, room, is_private=is_private, is_global=is_global)

            self.insert_page(
                tab.container, room, focus_callback=tab.on_focus, close_callback=tab.on_leave_room,
                position=tab_position
            )
            tab.set_label(self.get_tab_label_inner(tab.container))

            if not is_global:
                combobox = self.window.search.room_search_combobox
                combobox.append(room)

        if switch_page:
            self.set_current_page(self.pages[room].container)
            self.window.change_main_page(self.window.chatrooms_page)

    def remove_room(self, room):

        page = self.pages.get(room)

        if page is None:
            return

        if page.container == self.get_current_page():
            self.chat_entry.set_parent(None)

            if self.command_help is not None:
                self.command_help.set_menu_button(None)

            if self.room_wall is not None:
                self.room_wall.set_menu_button(None)
                self.room_wall.room = None

        page.clear()
        self.remove_page(page.container, page_args=(room, page.is_private))
        del self.pages[room]
        page.destroy()

        self.chat_entry.clear_unsent_message(room)

        if room != core.chatrooms.GLOBAL_ROOM_NAME:
            combobox = self.window.search.room_search_combobox
            combobox.remove_id(room)

    def highlight_room(self, room, user):

        if not room or room in self.highlighted_rooms:
            return

        self.highlighted_rooms[room] = user
        self.window.update_title()
        self.window.application.tray_icon.update()

    def unhighlight_room(self, room):

        if room not in self.highlighted_rooms:
            return

        del self.highlighted_rooms[room]
        self.window.update_title()
        self.window.application.tray_icon.update()

    def join_room(self, msg):

        page = self.pages.get(msg.room)

        if page is None:
            return

        page.join_room(msg)

        if page.container == self.get_current_page():
            self.chat_entry.set_sensitive(True)
            page.on_focus()

    def leave_room(self, msg):

        page = self.pages.get(msg.room)

        if page is not None:
            page.leave_room()

    def ignore_user(self, username, *_args):
        for page in self.pages.values():
            page.ignore_user(username)

    def unignore_user(self, username, *_args):
        for page in self.pages.values():
            page.unignore_user(username)

    def peer_address(self, msg):
        for page in self.pages.values():
            page.peer_address(msg)

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
            page.global_room_message(msg)

    def private_room_add_operator(self, msg):

        page = self.pages.get(msg.room)

        if page is not None:
            page.private_room_add_operator(msg)

    def private_room_add_user(self, msg):

        page = self.pages.get(msg.room)

        if page is not None:
            page.private_room_add_user(msg)

    def private_room_remove_operator(self, msg):

        page = self.pages.get(msg.room)

        if page is not None:
            page.private_room_remove_operator(msg)

    def private_room_remove_user(self, msg):

        page = self.pages.get(msg.room)

        if page is not None:
            page.private_room_remove_user(msg)

    def update_completions(self, completions):

        page = self.get_current_page()

        for tab in self.pages.values():
            if tab.container == page:
                tab.update_completions(completions)
                break

    def update_widgets(self):

        self.chat_entry.set_spell_check_enabled(config.sections["ui"]["spellcheck"])

        for tab in self.pages.values():
            tab.toggle_chat_buttons()
            tab.update_tags()

    def server_login(self, *_args):
        self.window.chatrooms_title.set_sensitive(True)

    def server_disconnect(self, *_args):

        self.window.chatrooms_title.set_sensitive(False)
        self.chat_entry.set_sensitive(False)

        for page in self.pages.values():
            page.server_disconnect()


class ChatRoom:

    def __init__(self, chatrooms, room, is_private, is_global):

        (
            self.activity_container,
            self.activity_search_bar,
            self.activity_view_container,
            self.chat_container,
            self.chat_entry_container,
            self.chat_entry_row,
            self.chat_paned,
            self.chat_search_bar,
            self.chat_view_container,
            self.container,
            self.help_button,
            self.log_toggle,
            self.room_wall_button,
            self.room_wall_label,
            self.speech_toggle,
            self.users_container,
            self.users_label,
            self.users_list_container
        ) = ui.load(scope=self, path="chatrooms.ui")

        self.chatrooms = chatrooms
        self.window = chatrooms.window
        self.room = room
        self.is_private = is_private
        self.is_global = is_global

        if GTK_API_VERSION >= 4:
            self.chat_paned.set_shrink_end_child(False)

            inner_button = next(iter(self.room_wall_button))
            self.room_wall_button.set_has_frame(False)
            self.room_wall_label.set_mnemonic_widget(inner_button)
        else:
            self.chat_paned.child_set_property(self.chat_container, "shrink", False)

        self.loaded = False

        self.activity_view = TextView(
            self.activity_view_container, parse_urls=False, editable=False,
            horizontal_margin=10, vertical_margin=5, pixels_below_lines=2
        )
        self.chat_view = ChatView(
            self.chat_view_container, chat_entry=self.chatrooms.chat_entry, editable=False,
            horizontal_margin=10, vertical_margin=5, pixels_below_lines=2,
            status_users=core.chatrooms.joined_rooms[room].users,
            username_event=self.username_event
        )

        # Event Text Search
        self.activity_search_bar = TextSearchBar(
            self.activity_view.widget, self.activity_search_bar,
            placeholder_text=_("Search activity log…")
        )

        # Chat Text Search
        self.chat_search_bar = TextSearchBar(
            self.chat_view.widget, self.chat_search_bar,
            controller_widget=self.chat_container, focus_widget=self.chatrooms.chat_entry,
            placeholder_text=_("Search chat log…")
        )

        self.log_toggle.set_active(room in config.sections["logging"]["rooms"])
        self.toggle_chat_buttons()

        if GTK_API_VERSION >= 4:
            inner_button = next(iter(self.help_button))
            add_css_class(widget=inner_button, css_class="image-button")

        self.users_list_view = TreeView(
            self.window, parent=self.users_list_container, name="chat_room", secondary_name=room,
            persistent_sort=True, activate_row_callback=self.on_row_activated,
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
                    "width": 110,
                    "expand_column": True,
                    "iterator_key": True,
                    "default_sort_type": "ascending",
                    "text_underline_column": "username_underline_data",
                    "text_weight_column": "username_weight_data",
                    "sensitive_column": "is_unignored_data"
                },
                "speed": {
                    "column_type": "number",
                    "title": _("Speed"),
                    "width": 80,
                    "sort_column": "speed_data",
                    "expand_column": True,
                    "sensitive_column": "is_unignored_data"
                },
                "files": {
                    "column_type": "number",
                    "title": _("Files"),
                    "sort_column": "files_data",
                    "expand_column": True,
                    "sensitive_column": "is_unignored_data"
                },

                # Hidden data columns
                "speed_data": {"data_type": GObject.TYPE_UINT},
                "files_data": {"data_type": GObject.TYPE_UINT},
                "username_weight_data": {"data_type": Pango.Weight},
                "username_underline_data": {"data_type": Pango.Underline},
                "is_unignored_data": {"data_type": GObject.TYPE_BOOLEAN}
            }
        )

        self.popup_menu_user_chat = UserPopupMenu(
            self.window.application, parent=self.chat_view.widget, connect_events=False,
            tab_name="chatrooms"
        )
        self.popup_menu_user_list = UserPopupMenu(
            self.window.application, parent=self.users_list_view.widget,
            callback=self.on_popup_menu_user, tab_name="chatrooms"
        )

        for menu in (self.popup_menu_user_chat, self.popup_menu_user_list):
            menu.add_items(
                ("", None),
                ("#" + _("Sear_ch User's Files"), menu.on_search_user)
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
            ("", None)
        )
        if not self.window.application.isolated_mode:
            self.popup_menu_chat_view.add_items(
                ("#" + _("View Room Log"), self.on_view_room_log)
            )
        self.popup_menu_chat_view.add_items(
            ("#" + _("Delete Room Log…"), self.on_delete_room_log),
            ("", None),
            ("#" + _("Clear Message View"), self.chat_view.on_clear_all_text),
            ("#" + _("_Leave Room"), self.on_leave_room)
        )

        self.tab_menu = PopupMenu(self.window.application)
        self.tab_menu.add_items(
            ("#" + _("_Leave Room"), self.on_leave_room)
        )

        self.popup_menus = (
            self.popup_menu_user_chat, self.popup_menu_user_list,
            self.popup_menu_activity_view, self.popup_menu_chat_view, self.tab_menu
        )

        self.setup_public_feed()
        self.prepend_old_messages()

    def load(self):
        GLib.idle_add(self.read_room_logs_finished)
        self.loaded = True

    def clear(self):

        self.activity_view.clear()
        self.chat_view.clear()
        self.users_list_view.clear()

    def destroy(self):

        for menu in self.popup_menus:
            menu.destroy()

        self.activity_view.destroy()
        self.chat_view.destroy()
        self.users_list_view.destroy()
        self.__dict__.clear()

    def set_label(self, label):
        self.tab_menu.set_parent(label)

    def setup_public_feed(self):

        if not self.is_global:
            return

        for widget in (self.activity_container, self.users_container, self.chat_entry_container, self.help_button):
            widget.set_visible(False)

        self.speech_toggle.set_active(False)  # Public feed is jibberish and too fast for TTS
        self.chat_entry_row.set_halign(Gtk.Align.END)

    def add_user_row(self, userdata):

        username = userdata.username
        status = userdata.status
        status_icon_name = USER_STATUS_ICON_NAMES.get(status, "")
        flag_icon_name = get_flag_icon_name(userdata.country)
        speed = userdata.avgspeed or 0
        files = userdata.files
        h_speed = human_speed(speed) if speed > 0 else ""
        h_files = humanize(files) if files is not None else ""
        weight = Pango.Weight.NORMAL
        underline = Pango.Underline.NONE
        is_unignored = not (core.network_filter.is_user_ignored(username)
                            or core.network_filter.is_user_ip_ignored(username))

        if self.room in core.chatrooms.private_rooms:
            if username == core.chatrooms.private_rooms[self.room].owner:
                weight = Pango.Weight.BOLD
                underline = Pango.Underline.SINGLE

            elif username in core.chatrooms.private_rooms[self.room].operators:
                weight = Pango.Weight.BOLD
                underline = Pango.Underline.NONE

        self.users_list_view.add_row([
            status_icon_name,
            flag_icon_name,
            username,
            h_speed,
            h_files,
            speed,
            files or 0,
            weight,
            underline,
            is_unignored
        ], select_row=False)

    def read_room_logs_finished(self):

        if not hasattr(self, "chat_view"):
            # Tab was closed
            return

        self.activity_view.scroll_bottom()
        self.chat_view.scroll_bottom()

        self.activity_view.auto_scroll = self.chat_view.auto_scroll = True

    def prepend_old_messages(self):

        log_lines = log.read_log(
            folder_path=log.room_folder_path,
            basename=self.room,
            num_lines=config.sections["logging"]["readroomlines"]
        )

        self.chat_view.append_log_lines(log_lines, login_username=config.sections["server"]["login"])

    def populate_room_users(self, joined_users):

        # Temporarily disable sorting for increased performance
        self.users_list_view.freeze()

        for userdata in joined_users:
            username = userdata.username
            iterator = self.users_list_view.iterators.get(username)

            if iterator is not None:
                self.users_list_view.remove_row(iterator)

            self.add_user_row(userdata)

        private_room = core.chatrooms.private_rooms.get(self.room)

        # List private room members who are offline/not currently joined
        if private_room is not None:
            owner = private_room.owner

            for username in private_room.members:
                if username not in self.users_list_view.iterators:
                    self.add_user_row(UserData(username, status=UserStatus.OFFLINE))

            if owner and owner not in self.users_list_view.iterators:
                self.add_user_row(UserData(owner, status=UserStatus.OFFLINE))

        self.users_list_view.unfreeze()

        # Update user count
        self.update_user_count()

        # Update all username tags in chat log
        self.chat_view.update_user_tags()

        # Add room users to completion list
        if self.chatrooms.get_current_page() == self.container:
            self.update_room_user_completions()

    def populate_user_menu(self, user, menu):
        menu.set_user(user)
        menu.toggle_user_items()

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
        self.populate_user_menu(user, menu)

    def on_popup_menu_log(self, menu, _textview):
        menu.actions[_("Copy")].set_enabled(self.activity_view.get_has_selection())

    def on_popup_menu_chat(self, menu, _textview):
        menu.actions[_("Copy")].set_enabled(self.chat_view.get_has_selection())
        menu.actions[_("Copy Link")].set_enabled(bool(self.chat_view.get_url_for_current_pos()))

    def toggle_chat_buttons(self):

        is_log_toggle_visible = not config.sections["logging"]["chatrooms"]
        is_speech_toggle_visible = config.sections["ui"]["speechenabled"]

        self.log_toggle.set_visible(is_log_toggle_visible)
        self.speech_toggle.set_visible(is_speech_toggle_visible)

        if self.is_global:
            self.chat_entry_row.set_visible(is_log_toggle_visible or is_speech_toggle_visible)

    def _show_notification(self, room, user, text, is_mentioned):

        self.chatrooms.request_tab_changed(self.container, is_important=is_mentioned, is_quiet=self.is_global)

        if self.is_global and room in core.chatrooms.joined_rooms:
            # Don't show notifications about the Public feed that's duplicated in an open tab
            return

        if is_mentioned:
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

        if is_mentioned:
            # We were mentioned, update tray icon and show urgency hint
            self.chatrooms.highlight_room(room, user)
            return

        if not self.is_global and config.sections["notifications"]["notification_popup_chatroom"]:
            # Don't show notifications for public feed room, they're too noisy
            core.notifications.show_chatroom_notification(
                room, text,
                title=_("Message by %(user)s in Room %(room)s") % {"user": user, "room": room}
            )

    def say_chat_room(self, msg):

        username = msg.user
        room = msg.room
        message = msg.message
        formatted_message = msg.formatted_message
        message_type = msg.message_type
        usertag = self.chat_view.get_user_tag(username)

        if message_type != "local":
            if self.speech_toggle.get_active():
                core.notifications.new_tts(
                    config.sections["ui"]["speechrooms"], {"room": room, "user": username, "message": message}
                )

            self._show_notification(
                room, username, message, is_mentioned=(message_type == "hilite"))

        self.chat_view.append_line(
            formatted_message, message_type=message_type, username=username, usertag=usertag,
            timestamp_format=config.sections["logging"]["rooms_timestamp"]
        )

    def global_room_message(self, msg):
        self.say_chat_room(msg)

    def echo_room_message(self, text, message_type):

        if message_type != "command":
            timestamp_format = config.sections["logging"]["rooms_timestamp"]
        else:
            timestamp_format = None

        self.chat_view.append_line(text, message_type=message_type, timestamp_format=timestamp_format)

    def user_joined_room(self, msg):

        userdata = msg.userdata
        username = userdata.username
        iterator = self.users_list_view.iterators.get(username)

        if iterator is not None:
            if not self.is_private:
                return

            self.users_list_view.remove_row(iterator)

        # Add to completion list, and completion drop-down
        if self.chatrooms.get_current_page() == self.container:
            self.chatrooms.chat_entry.add_completion(username)

        if (username != core.users.login_username
                and not core.network_filter.is_user_ignored(username)
                and not core.network_filter.is_user_ip_ignored(username)):
            self.activity_view.append_line(
                _("%s joined the room") % username,
                timestamp_format=config.sections["logging"]["rooms_timestamp"]
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
        if self.chatrooms.get_current_page() == self.container and username not in core.buddies.users:
            self.chatrooms.chat_entry.remove_completion(username)

        if not core.network_filter.is_user_ignored(username) and \
                not core.network_filter.is_user_ip_ignored(username):
            timestamp_format = config.sections["logging"]["rooms_timestamp"]
            self.activity_view.append_line(_("%s left the room") % username, timestamp_format=timestamp_format)

        if self.is_private:
            status_icon_name = USER_STATUS_ICON_NAMES[UserStatus.OFFLINE]
            empty_str = ""
            empty_int = 0

            self.users_list_view.set_row_values(
                iterator,
                column_ids=["status", "speed", "speed_data", "files", "files_data", "country"],
                values=[status_icon_name, empty_str, empty_int, empty_str, empty_int, empty_str]
            )
        else:
            self.users_list_view.remove_row(iterator)

        self.chat_view.update_user_tag(username)
        self.update_user_count()

    def private_room_add_operator(self, msg):

        iterator = self.users_list_view.iterators.get(msg.user)

        if iterator is None:
            return

        self.users_list_view.set_row_values(
            iterator,
            column_ids=["username_weight_data", "username_underline_data"],
            values=[Pango.Weight.BOLD, Pango.Underline.NONE]
        )

    def private_room_add_user(self, msg):

        username = msg.user
        iterator = self.users_list_view.iterators.get(username)

        if iterator is not None:
            return

        self.add_user_row(UserData(username, status=UserStatus.OFFLINE))

        self.chat_view.update_user_tag(username)
        self.update_user_count()

    def private_room_remove_operator(self, msg):

        iterator = self.users_list_view.iterators.get(msg.user)

        if iterator is None:
            return

        self.users_list_view.set_row_values(
            iterator,
            column_ids=["username_weight_data", "username_underline_data"],
            values=[Pango.Weight.NORMAL, Pango.Underline.NONE]
        )

    def private_room_remove_user(self, msg):

        username = msg.user
        iterator = self.users_list_view.iterators.get(username)

        if iterator is None:
            return

        self.users_list_view.remove_row(iterator)

        self.chat_view.update_user_tag(username)
        self.update_user_count()

    def update_user_count(self):
        user_count = len(self.users_list_view.iterators)
        self.users_label.set_text(humanize(user_count))

    def ignore_user(self, username):

        iterator = self.users_list_view.iterators.get(username)

        if iterator is None:
            return

        if self.users_list_view.get_row_value(iterator, "is_unignored_data"):
            self.users_list_view.set_row_value(iterator, "is_unignored_data", False)

    def unignore_user(self, username):

        iterator = self.users_list_view.iterators.get(username)

        if iterator is None:
            return

        if (core.network_filter.is_user_ignored(username)
                or core.network_filter.is_user_ip_ignored(username)):
            return

        if not self.users_list_view.get_row_value(iterator, "is_unignored_data"):
            self.users_list_view.set_row_value(iterator, "is_unignored_data", True)

    def peer_address(self, msg):

        username = msg.user

        if not core.network_filter.is_user_ip_ignored(username):
            return

        self.ignore_user(username)

    def user_stats(self, msg):

        user = msg.user
        iterator = self.users_list_view.iterators.get(user)

        if iterator is None:
            return

        if user not in core.chatrooms.joined_rooms[self.room].users:
            # Private room member offline/not currently joined
            return

        speed = msg.avgspeed or 0
        num_files = msg.files or 0
        column_ids = []
        column_values = []

        if speed != self.users_list_view.get_row_value(iterator, "speed_data"):
            h_speed = human_speed(speed) if speed > 0 else ""

            column_ids.extend(("speed", "speed_data"))
            column_values.extend((h_speed, speed))

        if num_files != self.users_list_view.get_row_value(iterator, "files_data"):
            h_num_files = humanize(num_files)

            column_ids.extend(("files", "files_data"))
            column_values.extend((h_num_files, num_files))

        if column_ids:
            self.users_list_view.set_row_values(iterator, column_ids, column_values)

    def user_status(self, msg):

        user = msg.user
        iterator = self.users_list_view.iterators.get(user)

        if iterator is None:
            return

        if user not in core.chatrooms.joined_rooms[self.room].users:
            # Private room member offline/not currently joined
            return

        status = msg.status
        status_icon_name = USER_STATUS_ICON_NAMES.get(status)

        if not status_icon_name or status_icon_name == self.users_list_view.get_row_value(iterator, "status"):
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

        self.chat_view.update_user_tag(user)

    def user_country(self, user, country_code):

        iterator = self.users_list_view.iterators.get(user)

        if iterator is None:
            return

        if user not in core.chatrooms.joined_rooms[self.room].users:
            # Private room member offline/not currently joined
            return

        flag_icon_name = get_flag_icon_name(country_code)

        if flag_icon_name and flag_icon_name != self.users_list_view.get_row_value(iterator, "country"):
            self.users_list_view.set_row_value(iterator, "country", flag_icon_name)

    def username_event(self, pos_x, pos_y, user):

        menu = self.popup_menu_user_chat
        menu.update_model()
        self.populate_user_menu(user, menu)
        menu.popup(pos_x, pos_y)

    def update_tags(self):
        self.chat_view.update_tags()

    def server_disconnect(self):
        self.leave_room()

    def join_room(self, msg):

        self.is_private = msg.private
        self.populate_room_users(msg.users)

        self.activity_view.append_line(
            _("%s joined the room") % core.users.login_username,
            timestamp_format=config.sections["logging"]["rooms_timestamp"]
        )

    def leave_room(self):

        self.users_list_view.clear()
        self.update_user_count()

        if self.chatrooms.get_current_page() == self.container:
            self.update_room_user_completions()

        self.chat_view.update_user_tags()

    def on_focus(self, *_args):

        if self.window.current_page_id == self.window.chatrooms_page.id:
            widget = self.chatrooms.chat_entry if self.chatrooms.chat_entry.get_sensitive() else self.chat_view
            widget.grab_focus()

        return True

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
        log.open_log(log.room_folder_path, self.room)

    def on_delete_room_log_response(self, *_args):

        log.delete_log(log.room_folder_path, self.room)
        self.activity_view.clear()
        self.chat_view.clear()

    def on_delete_room_log(self, *_args):

        OptionDialog(
            parent=self.window,
            title=_("Delete Logged Messages?"),
            message=_("Do you really want to permanently delete all logged messages for this room?"),
            destructive_response_id="ok",
            callback=self.on_delete_room_log_response
        ).present()

    def update_room_user_completions(self):
        self.update_completions(core.chatrooms.completions.copy())

    def update_completions(self, completions):

        # We want to include users for this room only
        if config.sections["words"]["roomusers"]:
            room_users = core.chatrooms.joined_rooms[self.room].users
            completions.update(room_users)

        self.chatrooms.chat_entry.set_completions(completions)
