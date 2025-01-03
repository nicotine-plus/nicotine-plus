# COPYRIGHT (C) 2020-2024 Nicotine+ Contributors
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2008-2011 quinox <quinox@users.sf.net>
# COPYRIGHT (C) 2007 gallows <g4ll0ws@gmail.com>
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

from gi.repository import GLib

from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.popovers.chatcommandhelp import ChatCommandHelp
from pynicotine.gtkgui.popovers.chathistory import ChatHistory
from pynicotine.gtkgui.widgets import ui
from pynicotine.gtkgui.widgets.iconnotebook import IconNotebook
from pynicotine.gtkgui.widgets.popupmenu import PopupMenu
from pynicotine.gtkgui.widgets.popupmenu import UserPopupMenu
from pynicotine.gtkgui.widgets.dialogs import OptionDialog
from pynicotine.gtkgui.widgets.textentry import ChatEntry
from pynicotine.gtkgui.widgets.textentry import TextSearchBar
from pynicotine.gtkgui.widgets.textview import ChatView
from pynicotine.gtkgui.widgets.theme import add_css_class
from pynicotine.logfacility import log
from pynicotine.slskmessages import UserStatus


class PrivateChats(IconNotebook):

    def __init__(self, window):

        super().__init__(
            window,
            parent=window.private_content,
            parent_page=window.private_page,
            switch_page_callback=self.on_switch_chat,
            reorder_page_callback=self.on_reordered_page
        )

        self.page = window.private_page
        self.page.id = "private"
        self.toolbar = window.private_toolbar
        self.toolbar_start_content = window.private_title
        self.toolbar_end_content = window.private_end
        self.toolbar_default_widget = window.private_entry

        self.chat_entry = ChatEntry(
            window.application, send_message_callback=core.privatechat.send_message,
            command_callback=core.pluginhandler.trigger_private_chat_command_event,
            enable_spell_check=config.sections["ui"]["spellcheck"]
        )
        self.history = ChatHistory(window)
        self.command_help = None
        self.highlighted_users = []

        for event_name, callback in (
            ("clear-private-messages", self.clear_messages),
            ("echo-private-message", self.echo_private_message),
            ("message-user", self.message_user),
            ("private-chat-completions", self.update_completions),
            ("private-chat-show-user", self.show_user),
            ("private-chat-remove-user", self.remove_user),
            ("quit", self.quit),
            ("server-disconnect", self.server_disconnect),
            ("server-login", self.server_login),
            ("start", self.start),
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
        self.history.destroy()

        if self.command_help is not None:
            self.command_help.destroy()

        super().destroy()

    def on_focus(self, *_args):

        if self.window.current_page_id != self.window.private_page.id:
            return True

        if self.get_n_pages():
            return True

        if self.window.private_entry.is_sensitive():
            self.window.private_entry.grab_focus()
            return True

        return False

    def on_remove_all_pages(self, *_args):
        core.privatechat.remove_all_users()

    def on_restore_removed_page(self, page_args):
        username, = page_args
        core.privatechat.show_user(username)

    def on_reordered_page(self, *_args):

        tab_order = {}

        for user, tab in self.pages.items():
            tab_position = self.page_num(tab.container)
            tab_order[tab_position] = user

        config.sections["privatechat"]["users"] = [user for tab_index, user in sorted(tab_order.items())]

    def on_switch_chat(self, _notebook, page, _page_num):

        if self.window.current_page_id != self.window.private_page.id:
            return

        for user, tab in self.pages.items():
            if tab.container != page:
                continue

            self.chat_entry.set_parent(user, tab.chat_entry_container, tab.chat_view)
            tab.update_room_user_completions()

            if self.command_help is None:
                self.command_help = ChatCommandHelp(window=self.window, interface="private_chat")

            self.command_help.set_menu_button(tab.help_button)

            if not tab.loaded:
                tab.load()

            # Remove highlight if selected tab belongs to a user in the list of highlights
            self.unhighlight_user(user)
            break

    def on_get_private_chat(self, *_args):

        username = self.window.private_entry.get_text().strip()

        if not username:
            return

        self.window.private_entry.set_text("")
        core.privatechat.show_user(username)

    def clear_messages(self, user):

        page = self.pages.get(user)

        if page is not None:
            page.chat_view.clear()

    def clear_notifications(self):

        if self.window.current_page_id != self.window.private_page.id:
            return

        page = self.get_current_page()

        for user, tab in self.pages.items():
            if tab.container == page:
                # Remove highlight
                self.unhighlight_user(user)
                break

    def user_status(self, msg):

        page = self.pages.get(msg.user)

        if page is not None:
            self.set_user_status(page.container, msg.user, msg.status)
            page.chat_view.update_user_tag(msg.user)

        if msg.user == core.users.login_username:
            for page in self.pages.values():
                # We've enabled/disabled away mode, update our username color in all chats
                page.chat_view.update_user_tag(msg.user)

    def show_user(self, user, switch_page=True, remembered=False):

        if user not in self.pages:
            self.pages[user] = page = PrivateChat(self, user)
            tab_position = -1 if remembered else 0

            self.insert_page(
                page.container, user, focus_callback=page.on_focus, close_callback=page.on_close, user=user,
                position=tab_position
            )
            page.set_label(self.get_tab_label_inner(page.container))

        if switch_page:
            self.set_current_page(self.pages[user].container)
            self.window.change_main_page(self.window.private_page)

    def remove_user(self, user):

        page = self.pages.get(user)

        if page is None:
            return

        if page.container == self.get_current_page():
            self.chat_entry.set_parent(None)

            if self.command_help is not None:
                self.command_help.set_menu_button(None)

        page.clear()
        self.remove_page(page.container, page_args=(user,))
        del self.pages[user]
        page.destroy()

        self.chat_entry.clear_unsent_message(user)

    def highlight_user(self, user):

        if not user or user in self.highlighted_users:
            return

        self.highlighted_users.append(user)
        self.window.update_title()
        self.window.application.tray_icon.update()

    def unhighlight_user(self, user):

        if user not in self.highlighted_users:
            return

        self.highlighted_users.remove(user)
        self.window.update_title()
        self.window.application.tray_icon.update()

    def echo_private_message(self, user, text, message_type):

        page = self.pages.get(user)

        if page is not None:
            page.echo_private_message(text, message_type)

    def message_user(self, msg, **_unused):

        page = self.pages.get(msg.user)

        if page is not None:
            page.message_user(msg)

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

    def server_login(self, msg):

        if not msg.success:
            return

        page = self.get_current_page()
        self.chat_entry.set_sensitive(True)

        for tab in self.pages.values():
            if tab.container == page:
                tab.on_focus()
                break

    def server_disconnect(self, *_args):

        self.chat_entry.set_sensitive(False)

        for user, page in self.pages.items():
            page.server_disconnect()
            self.set_user_status(page.container, user, UserStatus.OFFLINE)


class PrivateChat:

    def __init__(self, chats, user):

        (
            self.chat_entry_container,
            self.chat_view_container,
            self.container,
            self.help_button,
            self.log_toggle,
            self.search_bar,
            self.speech_toggle
        ) = ui.load(scope=self, path="privatechat.ui")

        self.user = user
        self.chats = chats
        self.window = chats.window

        self.loaded = False
        self.offline_message = False

        self.chat_view = ChatView(
            self.chat_view_container, chat_entry=self.chats.chat_entry, editable=False,
            horizontal_margin=10, vertical_margin=5, pixels_below_lines=2,
            username_event=self.username_event
        )

        # Text Search
        self.search_bar = TextSearchBar(
            self.chat_view.widget, self.search_bar,
            controller_widget=self.container, focus_widget=self.chats.chat_entry,
            placeholder_text=_("Search chat log…")
        )

        self.log_toggle.set_active(user in config.sections["logging"]["private_chats"])
        self.toggle_chat_buttons()

        if GTK_API_VERSION >= 4:
            inner_button = next(iter(self.help_button))
            add_css_class(widget=inner_button, css_class="image-button")

        self.popup_menu_user_chat = UserPopupMenu(
            self.window.application, parent=self.chat_view.widget, connect_events=False,
            username=user, tab_name="privatechat"
        )
        self.popup_menu_user_tab = UserPopupMenu(
            self.window.application, callback=self.on_popup_menu_user, username=user,
            tab_name="privatechat"
        )

        for menu in (self.popup_menu_user_chat, self.popup_menu_user_tab):
            menu.add_items(
                ("", None),
                ("#" + _("Close All Tabs…"), self.on_close_all_tabs),
                ("#" + _("_Close Tab"), self.on_close)
            )

        self.popup_menu = PopupMenu(self.window.application, self.chat_view.widget, self.on_popup_menu_chat)
        self.popup_menu.add_items(
            ("#" + _("Find…"), self.on_find_chat_log),
            ("", None),
            ("#" + _("Copy"), self.chat_view.on_copy_text),
            ("#" + _("Copy Link"), self.chat_view.on_copy_link),
            ("#" + _("Copy All"), self.chat_view.on_copy_all_text),
            ("", None)
        )
        if not self.window.application.isolated_mode:
            self.popup_menu.add_items(
                ("#" + _("View Chat Log"), self.on_view_chat_log)
            )
        self.popup_menu.add_items(
            ("#" + _("Delete Chat Log…"), self.on_delete_chat_log),
            ("", None),
            ("#" + _("Clear Message View"), self.chat_view.on_clear_all_text),
            ("", None),
            (">" + _("User Actions"), self.popup_menu_user_tab),
        )

        self.popup_menus = (self.popup_menu, self.popup_menu_user_chat, self.popup_menu_user_tab)

        self.prepend_old_messages()

    def load(self):
        GLib.idle_add(self.read_private_log_finished)
        self.loaded = True

    def read_private_log_finished(self):

        if not hasattr(self, "chat_view"):
            # Tab was closed
            return

        self.chat_view.scroll_bottom()
        self.chat_view.auto_scroll = True

    def prepend_old_messages(self):

        log_lines = log.read_log(
            folder_path=log.private_chat_folder_path,
            basename=self.user,
            num_lines=config.sections["logging"]["readprivatelines"]
        )

        self.chat_view.append_log_lines(log_lines, login_username=config.sections["server"]["login"])

    def server_disconnect(self):
        self.offline_message = False
        self.chat_view.update_user_tags()

    def clear(self):
        self.chat_view.clear()
        self.chats.unhighlight_user(self.user)

    def destroy(self):

        for menu in self.popup_menus:
            menu.destroy()

        self.chat_view.destroy()
        self.search_bar.destroy()
        self.__dict__.clear()

    def set_label(self, label):
        self.popup_menu_user_tab.set_parent(label)

    def on_popup_menu_chat(self, menu, _widget):

        self.popup_menu_user_tab.toggle_user_items()

        menu.actions[_("Copy")].set_enabled(self.chat_view.get_has_selection())
        menu.actions[_("Copy Link")].set_enabled(bool(self.chat_view.get_url_for_current_pos()))

    def on_popup_menu_user(self, _menu, _widget):
        self.popup_menu_user_tab.toggle_user_items()

    def toggle_chat_buttons(self):
        self.log_toggle.set_visible(not config.sections["logging"]["privatechat"])
        self.speech_toggle.set_visible(config.sections["ui"]["speechenabled"])

    def on_log_toggled(self, *_args):

        if not self.log_toggle.get_active():
            if self.user in config.sections["logging"]["private_chats"]:
                config.sections["logging"]["private_chats"].remove(self.user)
            return

        if self.user not in config.sections["logging"]["private_chats"]:
            config.sections["logging"]["private_chats"].append(self.user)

    def on_find_chat_log(self, *_args):
        self.search_bar.set_visible(True)

    def on_view_chat_log(self, *_args):
        log.open_log(log.private_chat_folder_path, self.user)

    def on_delete_chat_log_response(self, *_args):

        log.delete_log(log.private_chat_folder_path, self.user)
        self.chats.history.remove_user(self.user)
        self.chat_view.clear()

    def on_delete_chat_log(self, *_args):

        OptionDialog(
            parent=self.window,
            title=_("Delete Logged Messages?"),
            message=_("Do you really want to permanently delete all logged messages for this user?"),
            destructive_response_id="ok",
            callback=self.on_delete_chat_log_response
        ).present()

    def _show_notification(self, text, is_mentioned=False):

        is_buddy = (self.user in core.buddies.users)

        self.chats.request_tab_changed(self.container, is_important=is_buddy or is_mentioned)

        if (self.chats.get_current_page() == self.container
                and self.window.current_page_id == self.window.private_page.id and self.window.is_active()):
            # Don't show notifications if the chat is open and the window is in use
            return

        # Update tray icon and show urgency hint
        self.chats.highlight_user(self.user)

        if config.sections["notifications"]["notification_popup_private_message"]:
            core.notifications.show_private_chat_notification(
                self.user, text,
                title=_("Private Message from %(user)s") % {"user": self.user}
            )

    def message_user(self, msg):

        is_outgoing_message = (msg.message_id is None)
        is_new_message = msg.is_new_message
        message_type = msg.message_type

        username = msg.user
        tag_username = (core.users.login_username if is_outgoing_message else username)
        usertag = self.chat_view.get_user_tag(tag_username)

        timestamp = msg.timestamp if not is_new_message else None
        timestamp_format = config.sections["logging"]["private_timestamp"]
        message = msg.message
        formatted_message = msg.formatted_message

        if not is_outgoing_message:
            self._show_notification(message, is_mentioned=(message_type == "hilite"))

            if self.speech_toggle.get_active():
                core.notifications.new_tts(
                    config.sections["ui"]["speechprivate"], {"user": tag_username, "message": message}
                )

        if not is_outgoing_message and not is_new_message:
            if not self.offline_message:
                self.chat_view.append_line(
                    _("* Messages sent while you were offline"), message_type="hilite",
                    timestamp_format=timestamp_format
                )
                self.offline_message = True

        else:
            self.offline_message = False

        self.chat_view.append_line(
            formatted_message, message_type=message_type, timestamp=timestamp, timestamp_format=timestamp_format,
            username=tag_username, usertag=usertag
        )
        self.chats.history.update_user(username, formatted_message)

    def echo_private_message(self, text, message_type):

        if message_type != "command":
            timestamp_format = config.sections["logging"]["private_timestamp"]
        else:
            timestamp_format = None

        self.chat_view.append_line(text, message_type=message_type, timestamp_format=timestamp_format)

    def username_event(self, pos_x, pos_y, user):

        self.popup_menu_user_chat.update_model()
        self.popup_menu_user_chat.set_user(user)
        self.popup_menu_user_chat.toggle_user_items()
        self.popup_menu_user_chat.popup(pos_x, pos_y)

    def update_tags(self):
        self.chat_view.update_tags()

    def on_focus(self, *_args):

        if self.window.current_page_id == self.window.private_page.id:
            widget = self.chats.chat_entry if self.chats.chat_entry.get_sensitive() else self.chat_view
            widget.grab_focus()

        return True

    def on_close(self, *_args):
        core.privatechat.remove_user(self.user)

    def on_close_all_tabs(self, *_args):
        self.chats.remove_all_pages()

    def update_room_user_completions(self):
        self.update_completions(core.privatechat.completions.copy())

    def update_completions(self, completions):

        # Tab-complete the recipient username
        completions.add(self.user)

        self.chats.chat_entry.set_completions(completions)
