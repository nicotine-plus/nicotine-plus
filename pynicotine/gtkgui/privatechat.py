# COPYRIGHT (C) 2020-2022 Nicotine+ Team
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2008-2011 Quinox <quinox@users.sf.net>
# COPYRIGHT (C) 2007 Gallows <g4ll0ws@gmail.com>
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

from collections import deque

from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk

from pynicotine import slskmessages
from pynicotine.config import config
from pynicotine.gtkgui.widgets.iconnotebook import IconNotebook
from pynicotine.gtkgui.widgets.popupmenu import PopupMenu
from pynicotine.gtkgui.widgets.dialogs import option_dialog
from pynicotine.gtkgui.widgets.textentry import ChatCompletion
from pynicotine.gtkgui.widgets.textentry import ChatEntry
from pynicotine.gtkgui.widgets.textentry import TextSearchBar
from pynicotine.gtkgui.widgets.textview import TextView
from pynicotine.gtkgui.widgets.theme import get_user_status_color
from pynicotine.gtkgui.widgets.theme import update_widget_visuals
from pynicotine.gtkgui.widgets.ui import UserInterface
from pynicotine.logfacility import log
from pynicotine.utils import clean_file
from pynicotine.utils import delete_log
from pynicotine.utils import get_path
from pynicotine.utils import open_log


class PrivateChats(IconNotebook):

    def __init__(self, frame):

        IconNotebook.__init__(self, frame, frame.private_notebook, "private")
        self.notebook.connect("switch-page", self.on_switch_chat)

        self.completion = ChatCompletion()
        self.command_help = UserInterface("ui/popovers/privatechatcommands.ui")

        if Gtk.get_major_version() == 4:
            # Scroll to the focused widget
            self.command_help.container.get_child().set_scroll_to_focus(True)

    def on_switch_chat(self, _notebook, page, _page_num):

        if self.frame.current_page_id != self.page_id:
            return

        for user, tab in self.pages.items():
            if tab.Main == page:
                GLib.idle_add(lambda: tab.ChatLine.grab_focus() == -1)  # pylint:disable=cell-var-from-loop

                self.completion.set_entry(tab.ChatLine)
                tab.set_completion_list(list(self.frame.np.privatechats.completion_list))

                self.command_help.popover.unparent()
                tab.ShowChatHelp.set_popover(self.command_help.popover)

                # If the tab hasn't been opened previously, scroll chat to bottom
                if not tab.opened:
                    GLib.idle_add(tab.chat_textview.scroll_bottom)
                    tab.opened = True

                # Remove hilite if selected tab belongs to a user in the hilite list
                self.frame.notifications.clear("private", user)
                break

    def clear_notifications(self):

        if self.frame.current_page_id != self.page_id:
            return

        page = self.get_nth_page(self.get_current_page())

        for user, tab in self.pages.items():
            if tab.Main == page:
                # Remove hilite
                self.frame.notifications.clear("private", user)
                break

    def get_user_status(self, msg):

        page = self.pages.get(msg.user)
        if page is not None:
            self.set_user_status(page.Main, msg.user, msg.status)
            page.update_remote_username_tag(msg.status)

        if msg.user == self.frame.np.login_username:
            for page in self.pages.values():
                # We've enabled/disabled away mode, update our username color in all chats
                page.update_local_username_tag(msg.status)

    def show_user(self, user, switch_page=True):

        if user not in self.pages:
            self.pages[user] = page = PrivateChat(self, user)
            self.append_page(page.Main, user, page.on_close, user=user)
            page.set_label(self.get_tab_label_inner(page.Main))

        if switch_page and self.get_current_page() != self.page_num(self.pages[user].Main):
            self.set_current_page(self.page_num(self.pages[user].Main))

    def echo_message(self, user, text, message_type):

        page = self.pages.get(user)
        if page is not None:
            page.echo_message(text, message_type)

    def send_message(self, user, text):

        page = self.pages.get(user)
        if page is not None:
            page.send_message(text)

    def message_user(self, msg):

        page = self.pages.get(msg.user)
        if page is not None:
            page.message_user(msg)

    def set_completion_list(self, completion_list):

        page = self.get_nth_page(self.get_current_page())

        for tab in self.pages.values():
            if tab.Main == page:
                tab.set_completion_list(list(completion_list))
                break

    def update_visuals(self):

        for page in self.pages.values():
            page.update_visuals()
            page.update_tags()

    def server_login(self):
        for page in self.pages.values():
            page.server_login()

    def server_disconnect(self):

        for user, page in self.pages.items():
            page.server_disconnect()
            self.set_user_status(page.Main, user, 0)


class PrivateChat(UserInterface):

    def __init__(self, chats, user):

        super().__init__("ui/privatechat.ui")

        self.user = user
        self.chats = chats
        self.frame = chats.frame

        self.opened = False
        self.offline_message = False
        self.status = 0

        if user in self.frame.np.user_statuses:
            self.status = self.frame.np.user_statuses[user] or 0

        # Text Search
        TextSearchBar(self.ChatScroll, self.SearchBar, self.SearchEntry,
                      controller_widget=self.Main, focus_widget=self.ChatLine)

        self.chat_textview = TextView(self.ChatScroll, font="chatfont")

        # Chat Entry
        ChatEntry(self.frame, self.ChatLine, chats.completion, user, slskmessages.MessageUser,
                  self.frame.np.privatechats.send_message, self.frame.np.privatechats.CMDS)

        self.Log.set_active(config.sections["logging"]["privatechat"])

        self.popup_menu_user_chat = PopupMenu(self.frame, self.ChatScroll, connect_events=False)
        self.popup_menu_user_tab = PopupMenu(self.frame, None, self.on_popup_menu_user)

        for menu in (self.popup_menu_user_chat, self.popup_menu_user_tab):
            menu.setup_user_menu(user, page="privatechat")
            menu.add_items(
                ("", None),
                ("#" + _("Close All Tabs…"), self.on_close_all_tabs),
                ("#" + _("_Close Tab"), self.on_close)
            )

        popup = PopupMenu(self.frame, self.ChatScroll, self.on_popup_menu_chat)
        popup.add_items(
            ("#" + _("Find…"), self.on_find_chat_log),
            ("", None),
            ("#" + _("Copy"), self.chat_textview.on_copy_text),
            ("#" + _("Copy Link"), self.chat_textview.on_copy_link),
            ("#" + _("Copy All"), self.chat_textview.on_copy_all_text),
            ("", None),
            ("#" + _("View Chat Log"), self.on_view_chat_log),
            ("#" + _("Delete Chat Log…"), self.on_delete_chat_log),
            ("", None),
            ("#" + _("Clear Message View"), self.chat_textview.on_clear_all_text),
            ("", None),
            (">" + _("User"), self.popup_menu_user_tab),
        )

        self.create_tags()
        self.update_visuals()

        self.read_private_log()

    def read_private_log(self):

        # Read log file
        filename = clean_file(self.user) + ".log"
        numlines = config.sections["logging"]["readprivatelines"]

        try:
            get_path(config.sections["logging"]["privatelogsdir"], filename, self.append_log_lines, numlines)

        except OSError:
            pass

    def append_log_lines(self, path, numlines):

        with open(path, "rb") as lines:
            # Only show as many log lines as specified in config
            lines = deque(lines, numlines)

            for line in lines:
                try:
                    line = line.decode("utf-8")

                except UnicodeDecodeError:
                    line = line.decode("latin-1")

                self.chat_textview.append_line(line, self.tag_hilite, timestamp_format="", scroll=False)

    def server_login(self):
        timestamp_format = config.sections["logging"]["private_timestamp"]
        self.chat_textview.append_line(_("--- reconnected ---"), self.tag_hilite, timestamp_format=timestamp_format)

    def server_disconnect(self):

        timestamp_format = config.sections["logging"]["private_timestamp"]
        self.chat_textview.append_line(_("--- disconnected ---"), self.tag_hilite, timestamp_format=timestamp_format)
        self.status = -1
        self.offline_message = False

        # Offline color for usernames
        self.update_remote_username_tag(status=0)
        self.update_local_username_tag(status=0)

    def set_label(self, label):
        self.popup_menu_user_tab.set_parent(label)

    def on_popup_menu_chat(self, menu, _widget):

        self.popup_menu_user_tab.toggle_user_items()

        menu.actions[_("Copy")].set_enabled(self.chat_textview.get_has_selection())
        menu.actions[_("Copy Link")].set_enabled(bool(self.chat_textview.get_url_for_selected_pos()))

    def on_popup_menu_user(self, _menu, _widget):
        self.popup_menu_user_tab.toggle_user_items()

    def on_find_chat_log(self, *_args):
        self.SearchBar.set_search_mode(True)

    def on_view_chat_log(self, *_args):
        open_log(config.sections["logging"]["privatelogsdir"], self.user)

    def on_delete_chat_log_response(self, dialog, response_id, _data):

        dialog.destroy()

        if response_id == 2:
            delete_log(config.sections["logging"]["privatelogsdir"], self.user)
            self.chat_textview.clear()

    def on_delete_chat_log(self, *_args):

        option_dialog(
            parent=self.frame.MainWindow,
            title=_('Delete Logged Messages?'),
            message=_('Do you really want to permanently delete all logged messages for this user?'),
            callback=self.on_delete_chat_log_response
        )

    def show_notification(self, text):

        self.chats.request_tab_hilite(self.Main)

        if (self.chats.get_current_page() == self.chats.page_num(self.Main)
                and self.frame.current_page_id == self.chats.page_id and self.frame.MainWindow.is_active()):
            # Don't show notifications if the chat is open and the window is in use
            return

        # Update tray icon and show urgency hint
        self.frame.notifications.add("private", self.user)

        if config.sections["notifications"]["notification_popup_private_message"]:
            self.frame.notifications.new_text_notification(
                text,
                title=_("Private message from %s") % self.user,
                priority=Gio.NotificationPriority.HIGH
            )

    def message_user(self, msg):

        text = msg.msg
        newmessage = msg.newmessage
        timestamp = msg.timestamp if not newmessage else None
        usertag = self.tag_username

        self.show_notification(text)

        if text.startswith("/me "):
            line = "* %s %s" % (self.user, text[4:])
            tag = self.tag_action
        else:
            line = "[%s] %s" % (self.user, text)
            tag = self.tag_remote

        timestamp_format = config.sections["logging"]["private_timestamp"]

        if not newmessage:
            tag = usertag = self.tag_hilite

            if not self.offline_message:
                self.chat_textview.append_line(_("* Message(s) sent while you were offline. Timestamps are reported by "
                                                 "the server and can be off."), tag, timestamp_format=timestamp_format)
                self.offline_message = True

        else:
            self.offline_message = False

        self.chat_textview.append_line(line, tag, timestamp=timestamp, timestamp_format=timestamp_format,
                                       username=self.user, usertag=usertag)

        if self.Log.get_active():
            log.write_log(config.sections["logging"]["privatelogsdir"], self.user, line,
                          timestamp, timestamp_format=config.sections["logging"]["log_timestamp"])

    def echo_message(self, text, message_type):

        tag = self.tag_local
        timestamp_format = config.sections["logging"]["private_timestamp"]

        if hasattr(self, "tag_" + str(message_type)):
            tag = getattr(self, "tag_" + str(message_type))

        self.chat_textview.append_line(text, tag, timestamp_format=timestamp_format)

    def send_message(self, text):

        my_username = self.frame.np.login_username

        if text.startswith("/me "):
            line = "* %s %s" % (my_username, text[4:])
            tag = self.tag_action
        else:
            line = "[%s] %s" % (my_username, text)
            tag = self.tag_local

        self.chat_textview.append_line(line, tag, timestamp_format=config.sections["logging"]["private_timestamp"],
                                       username=my_username, usertag=self.tag_my_username)

        if self.Log.get_active():
            log.write_log(config.sections["logging"]["privatelogsdir"], self.user, line,
                          timestamp_format=config.sections["logging"]["log_timestamp"])

    def update_visuals(self):

        for widget in list(self.__dict__.values()):
            update_widget_visuals(widget)

    def user_name_event(self, pos_x, pos_y, user):

        self.popup_menu_user_chat.update_model()
        self.popup_menu_user_chat.set_user(user)
        self.popup_menu_user_chat.toggle_user_items()
        self.popup_menu_user_chat.popup(pos_x, pos_y, button=1)

    def create_tags(self):

        self.tag_remote = self.chat_textview.create_tag("chatremote")
        self.tag_local = self.chat_textview.create_tag("chatlocal")
        self.tag_action = self.chat_textview.create_tag("chatme")
        self.tag_hilite = self.chat_textview.create_tag("chathilite")

        color = get_user_status_color(self.status)
        self.tag_username = self.chat_textview.create_tag(color, callback=self.user_name_event, username=self.user)

        if not self.frame.np.logged_in:
            color = "useroffline"
        else:
            color = "useraway" if self.frame.np.away else "useronline"

        my_username = config.sections["server"]["login"]
        self.tag_my_username = self.chat_textview.create_tag(color, callback=self.user_name_event, username=my_username)

    def update_remote_username_tag(self, status):

        if status == self.status:
            return

        self.status = status

        color = get_user_status_color(status)
        self.chat_textview.update_tag(self.tag_username, color)

    def update_local_username_tag(self, status):
        color = get_user_status_color(status)
        self.chat_textview.update_tag(self.tag_my_username, color)

    def update_tags(self):

        for tag in (self.tag_remote, self.tag_local, self.tag_action, self.tag_hilite,
                    self.tag_username, self.tag_my_username):
            self.chat_textview.update_tag(tag)

    def on_close(self, *_args):

        self.frame.notifications.clear("private", self.user)
        del self.chats.pages[self.user]
        self.frame.np.privatechats.remove_user(self.user)

        self.chats.remove_page(self.Main)

    def on_close_all_tabs(self, *_args):
        self.chats.remove_all_pages()

    def set_completion_list(self, completion_list):

        # Tab-complete the recepient username
        completion_list.append(self.user)

        # No duplicates
        completion_list = list(set(completion_list))
        completion_list.sort(key=lambda v: v.lower())

        self.chats.completion.set_completion_list(completion_list)
