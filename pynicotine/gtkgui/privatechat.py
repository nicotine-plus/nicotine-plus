# COPYRIGHT (C) 2020-2021 Nicotine+ Team
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

import os

from collections import deque
from time import altzone
from time import daylight

from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk

from pynicotine import slskmessages
from pynicotine.config import config
from pynicotine.gtkgui.utils import append_line
from pynicotine.gtkgui.utils import copy_all_text
from pynicotine.gtkgui.utils import delete_log
from pynicotine.gtkgui.utils import grab_widget_focus
from pynicotine.gtkgui.utils import load_ui_elements
from pynicotine.gtkgui.utils import open_log
from pynicotine.gtkgui.utils import scroll_bottom
from pynicotine.gtkgui.widgets.iconnotebook import IconNotebook
from pynicotine.gtkgui.widgets.popupmenu import PopupMenu
from pynicotine.gtkgui.widgets.dialogs import option_dialog
from pynicotine.gtkgui.widgets.textentry import ChatEntry
from pynicotine.gtkgui.widgets.textentry import TextSearchBar
from pynicotine.gtkgui.widgets.theme import get_user_status_color
from pynicotine.gtkgui.widgets.theme import update_tag_visuals
from pynicotine.gtkgui.widgets.theme import update_widget_visuals
from pynicotine.logfacility import log
from pynicotine.utils import get_path


class PrivateChats(IconNotebook):

    def __init__(self, frame):

        self.frame = frame
        self.pages = {}

        IconNotebook.__init__(
            self,
            self.frame.images,
            tabclosers=config.sections["ui"]["tabclosers"],
            show_hilite_image=config.sections["notifications"]["notification_tab_icons"],
            show_status_image=config.sections["ui"]["tab_status_icons"],
            notebookraw=self.frame.PrivatechatNotebookRaw
        )

        self.notebook.connect("switch-page", self.on_switch_chat)

    def on_switch_chat(self, notebook, page, page_num, forceupdate=False):

        if self.frame.MainNotebook.get_current_page() != \
                self.frame.MainNotebook.page_num(self.frame.privatechatvbox) and not forceupdate:
            return

        for user, tab in list(self.pages.items()):
            if tab.Main == page:
                GLib.idle_add(grab_widget_focus, tab.ChatLine)

                # Remove hilite if selected tab belongs to a user in the hilite list
                self.frame.notifications.clear("private", tab.user)

    def clear_notifications(self):

        if self.frame.MainNotebook.get_current_page() != self.frame.MainNotebook.page_num(self.frame.privatechatvbox):
            return

        page = self.get_nth_page(self.get_current_page())

        for user, tab in list(self.pages.items()):
            if tab.Main == page:
                # Remove hilite
                self.frame.notifications.clear("private", tab.user)

    def get_user_status(self, msg):

        if msg.user in self.pages:
            page = self.pages[msg.user]

            self.set_user_status(page.Main, msg.user, msg.status)
            page.get_user_status(msg.status)

    def set_completion_list(self, completion_list):
        for user in self.pages.values():
            user.set_completion_list(list(completion_list))

    def show_user(self, user, switch_page=True):

        if user not in self.pages:
            try:
                status = self.frame.np.users[user].status
            except Exception:
                # Offline
                status = 0

            self.pages[user] = page = PrivateChat(self, user, status)

            self.append_page(page.Main, user, page.on_close, status=status)
            page.set_label(self.get_tab_label_inner(page.Main))

        if switch_page:
            if self.get_current_page() != self.page_num(self.pages[user].Main):
                self.set_current_page(self.page_num(self.pages[user].Main))

    def echo_message(self, user, text):
        if user in self.pages:
            self.pages[user].echo_message(text)

    def send_message(self, user, text):
        if user in self.pages:
            self.pages[user].send_message(text)

    def show_notification(self, user, text):

        chat = self.pages[user]

        # Hilight top-level tab label
        self.frame.request_tab_icon(self.frame.PrivateChatTabLabel)

        # Highlight sub-level tab label
        self.request_changed(chat.Main)

        # Don't show notifications if the private chat is open and the window
        # is in use
        if self.get_current_page() == self.page_num(chat.Main) and \
           self.frame.MainNotebook.get_current_page() == \
           self.frame.MainNotebook.page_num(self.frame.privatechatvbox) and \
           self.frame.MainWindow.is_active():
            return

        # Update tray icon and show urgency hint
        self.frame.notifications.add("private", user)

        if config.sections["notifications"]["notification_popup_private_message"]:
            self.frame.notifications.new_text_notification(
                text,
                title=_("Private message from %s") % user,
                priority=Gio.NotificationPriority.HIGH
            )

    def message_user(self, msg):

        self.frame.np.privatechats.show_user(msg.user)
        self.show_notification(msg.user, msg.msg)

        self.pages[msg.user].message_user(msg)

    def update_visuals(self):

        for page in self.pages.values():
            page.update_visuals()
            page.update_tags()

    def server_login(self):
        for user, page in self.pages.items():
            page.server_login()

    def server_disconnect(self):

        for user, page in self.pages.items():
            page.server_disconnect()
            self.set_user_status(page.Main, user, 0)


class PrivateChat:

    def __init__(self, chats, user, status):

        self.user = user
        self.chats = chats
        self.frame = chats.frame

        load_ui_elements(self, os.path.join(self.frame.gui_dir, "ui", "privatechat.ui"))
        load_ui_elements(self, os.path.join(self.frame.gui_dir, "ui", "popovers", "privatechatcommands.ui"))

        self.ShowChatHelp.set_popover(self.AboutPrivateChatCommandsPopover)

        if Gtk.get_major_version() == 4:
            self.ShowChatHelp.set_icon_name("dialog-question-symbolic")
        else:
            self.ShowChatHelp.set_image(Gtk.Image.new_from_icon_name("dialog-question-symbolic", Gtk.IconSize.BUTTON))

        self.offlinemessage = False
        self.status = status

        # Text Search
        TextSearchBar(self.ChatScroll, self.SearchBar, self.SearchEntry)

        # Chat Entry
        self.entry = ChatEntry(self.frame, self.ChatLine, user, slskmessages.MessageUser,
                               self.frame.np.privatechats.send_message, self.frame.np.privatechats.CMDS,
                               self.ChatScroll)

        self.Log.set_active(config.sections["logging"]["privatechat"])

        self.popup_menu_user = popup = PopupMenu(self.frame, None, self.on_popup_menu)
        popup.setup_user_menu(user, page="privatechat")
        popup.setup(
            ("", None),
            ("#" + _("Close All Tabs..."), self.on_close_all_tabs),
            ("#" + _("_Close Tab"), self.on_close)
        )

        popup = PopupMenu(self.frame, self.ChatScroll, self.on_popup_menu)
        popup.setup(
            ("#" + _("Find..."), self.on_find_chat_log),
            ("", None),
            ("#" + _("Copy"), self.on_copy_chat_log),
            ("#" + _("Copy All"), self.on_copy_all_chat_log),
            ("", None),
            ("#" + _("View Chat Log"), self.on_view_chat_log),
            ("#" + _("Delete Chat Log..."), self.on_delete_chat_log),
            ("", None),
            ("#" + _("Clear Message View"), self.on_clear_messages),
            ("", None),
            (">" + _("User"), self.popup_menu_user),
        )
        popup.set_user(user)

        self.create_tags()
        self.update_visuals()
        self.set_completion_list(list(self.frame.np.privatechats.completion_list))

        self.read_private_log()

    def read_private_log(self):

        # Read log file
        filename = self.user.replace(os.sep, "-") + ".log"

        try:
            numlines = int(config.sections["logging"]["readprivatelines"])
        except Exception:
            numlines = 15

        try:
            get_path(config.sections["logging"]["privatelogsdir"], filename, self.append_log_lines, numlines)

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
                append_line(self.ChatScroll, line, self.tag_hilite, timestamp_format="", username=self.user,
                            usertag=self.tag_hilite, scroll=False)

    def server_login(self):
        timestamp_format = config.sections["logging"]["private_timestamp"]
        append_line(self.ChatScroll, _("--- reconnected ---"), self.tag_hilite, timestamp_format=timestamp_format)
        self.update_tags()

    def server_disconnect(self):
        timestamp_format = config.sections["logging"]["private_timestamp"]
        append_line(self.ChatScroll, _("--- disconnected ---"), self.tag_hilite, timestamp_format=timestamp_format)
        self.status = -1
        self.offlinemessage = False
        self.update_tags()

    def set_label(self, label):
        self.popup_menu_user.set_widget(label)

    def on_popup_menu(self, menu, widget):
        self.popup_menu_user.toggle_user_items()

    def on_find_chat_log(self, *args):
        self.SearchBar.set_search_mode(True)

    def on_copy_chat_log(self, *args):
        self.ChatScroll.emit("copy-clipboard")

    def on_copy_all_chat_log(self, *args):
        copy_all_text(self.ChatScroll)

    def on_view_chat_log(self, *args):
        open_log(config.sections["logging"]["privatelogsdir"], self.user)

    def on_delete_chat_log_response(self, dialog, response_id, data):

        dialog.destroy()

        if response_id == Gtk.ResponseType.OK:
            delete_log(config.sections["logging"]["privatelogsdir"], self.user)
            self.on_clear_messages()

    def on_delete_chat_log(self, *args):

        option_dialog(
            parent=self.frame.MainWindow,
            title=_('Delete Logged Messages?'),
            message=_('Are you sure you wish to permanently delete all logged messages for this user?'),
            callback=self.on_delete_chat_log_response
        )

    def on_clear_messages(self, *args):
        self.ChatScroll.get_buffer().set_text("")

    def message_user(self, msg):

        text = msg.msg
        newmessage = msg.newmessage
        timestamp = msg.timestamp

        if text[:4] == "/me ":
            line = "* %s %s" % (self.user, text[4:])
            tag = self.tag_me
        else:
            line = "[%s] %s" % (self.user, text)
            tag = self.tag_remote

        timestamp_format = config.sections["logging"]["private_timestamp"]

        if not newmessage and not self.offlinemessage:
            append_line(
                self.ChatScroll,
                _("* Message(s) sent while you were offline. Timestamps are reported by the server and can be off."),
                self.tag_hilite,
                timestamp_format=timestamp_format
            )
            self.offlinemessage = True

        if newmessage and self.offlinemessage:
            self.offlinemessage = False

        if not newmessage:

            # The timestamps from the server are off by a lot, so we'll only use them when this is an offline message
            # Also, they are in UTC so we need to correct them
            if daylight:
                timestamp -= (3600 * daylight)
            else:
                timestamp += altzone

            append_line(self.ChatScroll, line, self.tag_hilite, timestamp=timestamp, timestamp_format=timestamp_format,
                        username=self.user, usertag=self.tag_username)
        else:
            append_line(self.ChatScroll, line, tag, timestamp_format=timestamp_format, username=self.user,
                        usertag=self.tag_username)

        if self.Log.get_active():
            timestamp_format = config.sections["logging"]["log_timestamp"]
            log.write_log(config.sections["logging"]["privatelogsdir"], self.user, line, timestamp_format)

    def echo_message(self, text):

        tag = self.tag_me
        timestamp_format = config.sections["logging"]["private_timestamp"]
        append_line(self.ChatScroll, text, tag, timestamp_format=timestamp_format)

    def send_message(self, text):

        my_username = config.sections["server"]["login"]

        if text[:4] == "/me ":
            line = "* %s %s" % (my_username, text[4:])
            usertag = tag = self.tag_me

        else:
            tag = self.tag_local
            usertag = self.tag_my_username
            line = "[%s] %s" % (my_username, text)

        timestamp_format = config.sections["logging"]["private_timestamp"]
        append_line(self.ChatScroll, line, tag, timestamp_format=timestamp_format,
                    username=my_username, usertag=usertag)

        if self.Log.get_active():
            timestamp_format = config.sections["logging"]["log_timestamp"]
            log.write_log(config.sections["logging"]["privatelogsdir"], self.user, line, timestamp_format)

    def update_visuals(self):

        for widget in list(self.__dict__.values()):
            update_widget_visuals(widget, update_text_tags=False)

    def create_tag(self, buffer, color):

        tag = buffer.create_tag()
        update_tag_visuals(tag, color)

        return tag

    def create_tags(self):

        buffer = self.ChatScroll.get_buffer()
        self.tag_remote = self.create_tag(buffer, "chatremote")
        self.tag_local = self.create_tag(buffer, "chatlocal")
        self.tag_me = self.create_tag(buffer, "chatme")
        self.tag_hilite = self.create_tag(buffer, "chathilite")

        color = get_user_status_color(self.status)
        self.tag_username = self.create_tag(buffer, color)

        if self.frame.np.active_server_conn:
            if self.frame.np.away and config.sections["ui"]["showaway"]:
                self.tag_my_username = self.create_tag(buffer, "useraway")
            else:
                self.tag_my_username = self.create_tag(buffer, "useronline")
        else:
            self.tag_my_username = self.create_tag(buffer, "useroffline")

    def update_tags(self):

        update_tag_visuals(self.tag_remote, "chatremote")
        update_tag_visuals(self.tag_local, "chatlocal")
        update_tag_visuals(self.tag_me, "chatme")
        update_tag_visuals(self.tag_hilite, "chathilite")

        color = get_user_status_color(self.status)
        update_tag_visuals(self.tag_username, color)

        if self.frame.np.active_server_conn:
            if self.frame.np.away and config.sections["ui"]["showaway"]:
                update_tag_visuals(self.tag_my_username, "useraway")
            else:
                update_tag_visuals(self.tag_my_username, "useronline")
        else:
            update_tag_visuals(self.tag_my_username, "useroffline")

    def get_user_status(self, status):

        if status == self.status:
            return

        self.status = status

        color = get_user_status_color(self.status)
        update_tag_visuals(self.tag_username, color)

    def on_close(self, *args):

        self.frame.notifications.clear("private", self.user)
        del self.chats.pages[self.user]
        self.frame.np.privatechats.remove_user(self.user)

        self.chats.remove_page(self.Main)

    def on_close_all_tabs(self, *args):
        self.chats.remove_all_pages()

    def set_completion_list(self, completion_list):

        # Tab-complete the recepient username
        completion_list.append(self.user)

        # No duplicates
        completion_list = list(set(completion_list))
        completion_list.sort(key=lambda v: v.lower())

        self.entry.set_completion_list(completion_list)
