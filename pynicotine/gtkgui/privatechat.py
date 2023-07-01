# COPYRIGHT (C) 2020-2023 Nicotine+ Contributors
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

import os

from gi.repository import GLib

from pynicotine import slskmessages
from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.gtkgui.popovers.chatcommandhelp import ChatCommandHelp
from pynicotine.gtkgui.popovers.chathistory import ChatHistory
from pynicotine.gtkgui.widgets import ui
from pynicotine.gtkgui.widgets.iconnotebook import IconNotebook
from pynicotine.gtkgui.widgets.popupmenu import PopupMenu
from pynicotine.gtkgui.widgets.popupmenu import UserPopupMenu
from pynicotine.gtkgui.widgets.dialogs import OptionDialog
from pynicotine.gtkgui.widgets.textentry import ChatCompletion
from pynicotine.gtkgui.widgets.textentry import ChatEntry
from pynicotine.gtkgui.widgets.textentry import TextSearchBar
from pynicotine.gtkgui.widgets.textview import ChatView
from pynicotine.logfacility import log
from pynicotine.utils import clean_file


class PrivateChats(IconNotebook):

    def __init__(self, window):

        super().__init__(
            window,
            parent=window.private_content,
            parent_page=window.private_page,
            switch_page_callback=self.on_switch_chat,
            reorder_page_callback=self.on_reordered_page
        )

        self.highlighted_users = []
        self.completion = ChatCompletion()
        self.history = ChatHistory(window)
        self.command_help = None

        for event_name, callback in (
            ("clear-private-messages", self.clear_messages),
            ("echo-private-message", self.echo_private_message),
            ("message-user", self.message_user),
            ("private-chat-completions", self.update_completions),
            ("private-chat-show-user", self.show_user),
            ("private-chat-remove-user", self.remove_user),
            ("send-private-message", self.send_message),
            ("server-disconnect", self.server_disconnect),
            ("user-status", self.user_status)
        ):
            events.connect(event_name, callback)

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

            self.completion.set_entry(tab.chat_entry)
            tab.update_room_user_completions()

            if self.command_help is None:
                self.command_help = ChatCommandHelp(window=self.window, interface="private_chat")

            self.command_help.widget.unparent()
            tab.help_button.set_popover(self.command_help.widget)

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

        if msg.user == core.login_username:
            for page in self.pages.values():
                # We've enabled/disabled away mode, update our username color in all chats
                page.chat_view.update_user_tag(msg.user)

    def show_user(self, user, switch_page=True):

        if user not in self.pages:
            self.pages[user] = page = PrivateChat(self, user)
            self.append_page(page.container, user, focus_callback=page.on_focus,
                             close_callback=page.on_close, user=user)
            page.set_label(self.get_tab_label_inner(page.container))

        if switch_page:
            self.set_current_page(self.pages[user].container)
            self.window.change_main_page(self.window.private_page)

    def remove_user(self, user):

        page = self.pages.get(user)

        if page is None:
            return

        page.clear()
        self.remove_page(page.container)
        del self.pages[user]

    def highlight_user(self, user):

        if not user or user in self.highlighted_users:
            return

        self.highlighted_users.append(user)
        self.window.application.notifications.update_title()
        self.window.application.tray_icon.update_icon()

        if config.sections["ui"]["urgencyhint"] and not self.window.is_active():
            self.window.application.notifications.set_urgency_hint(True)

    def unhighlight_user(self, user):

        if user not in self.highlighted_users:
            return

        self.highlighted_users.remove(user)
        self.window.application.notifications.update_title()
        self.window.application.tray_icon.update_icon()

    def echo_private_message(self, user, text, message_type):

        page = self.pages.get(user)

        if page is not None:
            page.echo_private_message(text, message_type)

    def send_message(self, user, text):

        page = self.pages.get(user)

        if page is not None:
            page.send_message(text)

    def message_user(self, msg, **_unused):

        page = self.pages.get(msg.user)

        if page is not None:
            page.message_user(msg)

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

        for user, page in self.pages.items():
            page.server_disconnect()
            self.set_user_status(page.container, user, slskmessages.UserStatus.OFFLINE)


class PrivateChat:

    def __init__(self, chats, user):

        (
            self.chat_entry,
            self.chat_view_container,
            self.container,
            self.help_button,
            self.log_toggle,
            self.search_bar,
            self.search_entry,
            self.speech_toggle
        ) = ui.load(scope=self, path="privatechat.ui")

        self.user = user
        self.chats = chats
        self.window = chats.window

        self.loaded = False
        self.offline_message = False

        self.chat_view = ChatView(self.chat_view_container, editable=False, horizontal_margin=10,
                                  vertical_margin=5, pixels_below_lines=2, username_event=self.username_event)

        # Text Search
        self.search_bar = TextSearchBar(self.chat_view.widget, self.search_bar, self.search_entry,
                                        controller_widget=self.container, focus_widget=self.chat_entry)

        # Chat Entry
        ChatEntry(self.window.application, self.chat_entry, chats.completion, user, slskmessages.MessageUser,
                  core.privatechat.send_message)

        self.log_toggle.set_active(config.sections["logging"]["privatechat"])

        self.toggle_chat_buttons()

        self.popup_menu_user_chat = UserPopupMenu(self.window.application, self.chat_view.widget,
                                                  connect_events=False)
        self.popup_menu_user_tab = UserPopupMenu(self.window.application, None, self.on_popup_menu_user)

        for menu in (self.popup_menu_user_chat, self.popup_menu_user_tab):
            menu.setup_user_menu(user, page="privatechat")
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
            ("", None),
            ("#" + _("View Chat Log"), self.on_view_chat_log),
            ("#" + _("Delete Chat Log…"), self.on_delete_chat_log),
            ("", None),
            ("#" + _("Clear Message View"), self.chat_view.on_clear_all_text),
            ("", None),
            (">" + _("User"), self.popup_menu_user_tab),
        )

        self.read_private_log()

    def load(self):
        GLib.idle_add(self.read_private_log_finished)
        self.loaded = True

    def read_private_log_finished(self):
        self.chat_view.scroll_bottom()
        self.chat_view.auto_scroll = True

    def read_private_log(self):

        numlines = config.sections["logging"]["readprivatelines"]

        if not numlines:
            return

        filename = f"{clean_file(self.user)}.log"
        path = os.path.join(config.sections["logging"]["privatelogsdir"], filename)

        try:
            self.chat_view.append_log_lines(
                path, numlines, timestamp_format=config.sections["logging"]["private_timestamp"]
            )
        except OSError:
            pass

    def server_disconnect(self):
        self.offline_message = False
        self.chat_view.update_user_tags()

    def clear(self):

        self.chat_view.clear()
        self.chats.unhighlight_user(self.user)

        for menu in (self.popup_menu_user_chat, self.popup_menu_user_tab, self.popup_menu):
            menu.clear()

    def set_label(self, label):
        self.popup_menu_user_tab.set_parent(label)

    def on_popup_menu_chat(self, menu, _widget):

        self.popup_menu_user_tab.toggle_user_items()

        menu.actions[_("Copy")].set_enabled(self.chat_view.get_has_selection())
        menu.actions[_("Copy Link")].set_enabled(bool(self.chat_view.get_url_for_current_pos()))

    def on_popup_menu_user(self, _menu, _widget):
        self.popup_menu_user_tab.toggle_user_items()

    def toggle_chat_buttons(self):
        self.speech_toggle.set_visible(config.sections["ui"]["speechenabled"])

    def on_find_chat_log(self, *_args):
        self.search_bar.set_visible(True)

    def on_view_chat_log(self, *_args):
        log.open_log(config.sections["logging"]["privatelogsdir"], self.user)

    def on_delete_chat_log_response(self, *_args):

        log.delete_log(config.sections["logging"]["privatelogsdir"], self.user)
        self.chats.history.remove_user(self.user)
        self.chat_view.clear()

    def on_delete_chat_log(self, *_args):

        OptionDialog(
            parent=self.window,
            title=_("Delete Logged Messages?"),
            message=_("Do you really want to permanently delete all logged messages for this user?"),
            destructive_response_id="ok",
            callback=self.on_delete_chat_log_response
        ).show()

    def _show_notification(self, text, tag, is_buddy):

        mentioned = (tag == self.chat_view.tag_highlight)
        self.chats.request_tab_changed(self.container, is_important=is_buddy or mentioned)

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

        text = msg.msg
        newmessage = msg.newmessage
        timestamp = msg.timestamp if not newmessage else None
        is_buddy = (self.user in core.userlist.buddies)
        usertag = self.chat_view.get_user_tag(self.user)
        tag = self.chat_view.get_line_tag(self.user, text, core.login_username)

        self._show_notification(text, tag, is_buddy)

        if tag == self.chat_view.tag_action:
            line = f"* {self.user} {text[4:]}"
            speech = line[2:]
        else:
            line = f"[{self.user}] {text}"
            speech = text

        timestamp_format = config.sections["logging"]["private_timestamp"]

        if not newmessage:
            tag = usertag = self.chat_view.tag_highlight

            if not self.offline_message:
                self.chat_view.append_line(_("* Messages sent while you were offline"), tag=tag,
                                           timestamp_format=timestamp_format)
                self.offline_message = True

        else:
            self.offline_message = False

        self.chat_view.append_line(line, tag=tag, timestamp=timestamp, timestamp_format=timestamp_format,
                                   username=self.user, usertag=usertag)

        if self.speech_toggle.get_active():
            core.notifications.new_tts(
                config.sections["ui"]["speechprivate"], {"user": self.user, "message": speech}
            )

        if self.log_toggle.get_active():
            log.write_log_file(
                folder_path=config.sections["logging"]["privatelogsdir"], base_name=f"{clean_file(self.user)}.log",
                text=line, timestamp=timestamp
            )
            self.chats.history.update_user(self.user, line)

    def echo_private_message(self, text, message_type):

        if hasattr(self, f"tag_{message_type}"):
            tag = getattr(self, f"tag_{message_type}")
        else:
            tag = self.chat_view.tag_local

        if message_type != "command":
            timestamp_format = config.sections["logging"]["private_timestamp"]
        else:
            timestamp_format = None

        self.chat_view.append_line(text, tag=tag, timestamp_format=timestamp_format)

    def send_message(self, text):

        my_username = core.login_username
        tag = self.chat_view.get_line_tag(my_username, text)

        if tag == self.chat_view.tag_action:
            line = f"* {my_username} {text[4:]}"
        else:
            line = f"[{my_username}] {text}"

        self.chat_view.append_line(line, tag=tag, timestamp_format=config.sections["logging"]["private_timestamp"],
                                   username=my_username, usertag=self.chat_view.get_user_tag(my_username))

        if self.log_toggle.get_active():
            log.write_log_file(
                folder_path=config.sections["logging"]["privatelogsdir"],
                base_name=f"{clean_file(self.user)}.log", text=line
            )
            self.chats.history.update_user(self.user, line)

    def username_event(self, pos_x, pos_y, user):

        self.popup_menu_user_chat.update_model()
        self.popup_menu_user_chat.set_user(user)
        self.popup_menu_user_chat.toggle_user_items()
        self.popup_menu_user_chat.popup(pos_x, pos_y)

    def update_tags(self):
        self.chat_view.update_tags()

    def on_focus(self, *_args):
        self.chat_entry.grab_focus()

    def on_close(self, *_args):
        core.privatechat.remove_user(self.user)

    def on_close_all_tabs(self, *_args):
        self.chats.remove_all_pages()

    def update_room_user_completions(self):
        self.update_completions(core.privatechat.completions.copy())

    def update_completions(self, completions):

        # Tab-complete the recipient username
        completions.add(self.user)

        self.chats.completion.set_completions(completions)
