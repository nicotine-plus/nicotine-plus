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
from pynicotine.gtkgui.utils import auto_replace
from pynicotine.gtkgui.utils import censor_chat
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
from pynicotine.utils import get_completion_list
from pynicotine.utils import get_path


class PrivateChats(IconNotebook):

    # List of allowed commands. The implementation for them is in the ChatEntry class.
    CMDS = {
        "/al ", "/alias ", "/un ", "/unalias ", "/w ", "/whois ", "/browse ", "/b ", "/ip ", "/pm ", "/m ", "/msg ",
        "/s ", "/search ", "/us ", "/usearch ", "/rs ", "/rsearch ", "/bs ", "/bsearch ", "/j ", "/join ",
        "/ad ", "/add ", "/buddy ", "/rem ", "/unbuddy ", "/ban ", "/ignore ", "/ignoreip ", "/unban ",
        "/unignore ", "/clear ", "/cl ", "/me ", "/a ", "/away ", "/q ", "/quit ", "/exit ", "/now ", "/rescan ",
        "/info ", "/toggle ", "/ctcpversion "
    }

    CTCP_VERSION = "\x01VERSION\x01"

    def __init__(self, frame):

        self.frame = frame

        IconNotebook.__init__(
            self,
            self.frame.images,
            tabclosers=config.sections["ui"]["tabclosers"],
            show_hilite_image=config.sections["notifications"]["notification_tab_icons"],
            reorderable=config.sections["ui"]["tab_reorderable"],
            show_status_image=config.sections["ui"]["tab_status_icons"],
            notebookraw=self.frame.PrivatechatNotebookRaw
        )

        self.connected = True
        self.users = {}
        self.completion_list = []
        self.private_message_queue = {}

        self.notebook.connect("switch-page", self.on_switch_chat)

        # Clear list of previously open chats if we don't want to restore them
        if not config.sections["privatechat"]["store"]:
            config.sections["privatechat"]["users"].clear()

    def on_switch_chat(self, notebook, page, page_num, forceupdate=False):

        if self.frame.MainNotebook.get_current_page() != \
                self.frame.MainNotebook.page_num(self.frame.privatechatvbox) and not forceupdate:
            return

        for user, tab in list(self.users.items()):
            if tab.Main == page:
                GLib.idle_add(grab_widget_focus, tab.ChatLine)

                # Remove hilite if selected tab belongs to a user in the hilite list
                if user in self.frame.hilites["private"]:
                    self.frame.notifications.clear("private", tab.user)

    def clear_notifications(self):

        if self.frame.MainNotebook.get_current_page() != self.frame.MainNotebook.page_num(self.frame.privatechatvbox):
            return

        page = self.get_nth_page(self.get_current_page())

        for user, tab in list(self.users.items()):
            if tab.Main == page:
                # Remove hilite
                if user in self.frame.hilites["private"]:
                    self.frame.notifications.clear("private", tab.user)

    def get_user_status(self, msg):

        if msg.user in self.users:
            tab = self.users[msg.user]

            self.set_user_status(tab.Main, msg.user, msg.status)
            tab.get_user_status(msg.status)

    def send_message(self, user, text=None, show_user=False, bytestring=False):

        if user not in self.users:
            try:
                status = self.frame.np.users[user].status
            except Exception:
                # Offline
                status = 0

            self.users[user] = tab = PrivateChat(self, user, status)

            if user not in config.sections["privatechat"]["users"]:
                config.sections["privatechat"]["users"].append(user)

            # Get notified of user status
            self.frame.np.watch_user(user)

            self.append_page(tab.Main, user, tab.on_close, status=status)
            tab.set_label(self.get_tab_label_inner(tab.Main))

        if show_user:
            if self.get_current_page() != self.page_num(self.users[user].Main):
                self.set_current_page(self.page_num(self.users[user].Main))

        if text is not None:
            self.users[user].send_message(text, bytestring=bytestring)

    def private_message_queue_add(self, msg, text):

        user = msg.user

        if user not in self.private_message_queue:
            self.private_message_queue[user] = [[msg, text]]
        else:
            self.private_message_queue[user].append([msg, text])

    def private_message_queue_process(self, user):

        if user not in self.private_message_queue:
            return

        for data in self.private_message_queue[user][:]:
            msg, text = data
            self.private_message_queue[user].remove(data)
            self.show_message(msg, text)

    def show_notification(self, user, text):

        chat = self.users[user]

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
            self.frame.notifications.new_notification(
                text,
                title=_("Private message from %s") % user,
                priority=Gio.NotificationPriority.HIGH
            )

    def show_message(self, msg, text, newmessage=True):

        if self.frame.np.network_filter.is_user_ignored(msg.user):
            return

        if msg.user in self.frame.np.users and isinstance(self.frame.np.users[msg.user].addr, tuple):
            ip, port = self.frame.np.users[msg.user].addr
            if self.frame.np.network_filter.is_ip_ignored(ip):
                return

        elif newmessage:
            self.frame.np.queue.append(slskmessages.GetPeerAddress(msg.user))
            self.private_message_queue_add(msg, text)
            return

        user_text = self.frame.np.pluginhandler.incoming_private_chat_event(msg.user, text)
        if user_text is None:
            return

        (u, text) = user_text

        self.send_message(msg.user, None)
        self.show_notification(msg.user, text)

        # SEND CLIENT VERSION to user if the following string is sent
        ctcpversion = 0
        if text == self.CTCP_VERSION:
            ctcpversion = 1
            text = "CTCP VERSION"

        self.users[msg.user].show_message(text, newmessage, msg.timestamp)

        if ctcpversion and config.sections["server"]["ctcpmsgs"] == 0:
            self.send_message(msg.user, GLib.get_application_name() + " " + config.version)

        self.frame.np.pluginhandler.incoming_private_chat_notification(msg.user, text)

    def update_visuals(self):
        for chat in self.users.values():
            chat.update_visuals()
            chat.update_tags()

    def remove_tab(self, tab):

        if tab.user in self.frame.hilites["private"]:
            self.frame.notifications.clear("private", tab.user)

        del self.users[tab.user]

        if tab.user in config.sections["privatechat"]["users"]:
            config.sections["privatechat"]["users"].remove(tab.user)

        self.remove_page(tab.Main)

    def login(self):

        self.connected = True

        for user in self.users:
            self.users[user].login()

            # Get notified of user status
            self.frame.np.watch_user(user)

        if not config.sections["privatechat"]["store"]:
            return

        for user in config.sections["privatechat"]["users"]:
            if isinstance(user, str) and user not in self.users:
                self.send_message(user)

    def conn_close(self):

        self.connected = False

        for user in self.users:
            self.users[user].conn_close()
            tab = self.users[user]

            self.set_user_status(tab.Main, user, 0)

    def update_completions(self):

        self.completion_list = get_completion_list(self.CMDS, self.frame.chatrooms.roomlist.server_rooms)

        for user in self.users.values():
            user.set_completion_list(list(self.completion_list))


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

        self.autoreplied = False
        self.offlinemessage = False
        self.status = status

        # Text Search
        TextSearchBar(self.ChatScroll, self.SearchBar, self.SearchEntry)

        # Chat Entry
        self.entry = ChatEntry(self.frame, self.ChatLine, user, slskmessages.MessageUser,
                               self.send_message, self.chats.CMDS, self.ChatScroll)

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
        self.set_completion_list(list(self.chats.completion_list))

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

    def login(self):
        timestamp_format = config.sections["logging"]["private_timestamp"]
        append_line(self.ChatScroll, _("--- reconnected ---"), self.tag_hilite, timestamp_format=timestamp_format)
        self.update_tags()

    def conn_close(self):
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

    def show_message(self, text, newmessage=True, timestamp=None):

        if text[:4] == "/me ":
            line = "* %s %s" % (self.user, censor_chat(text[4:]))
            speech = line[2:]
            tag = self.tag_me
        else:
            line = "[%s] %s" % (self.user, censor_chat(text))
            speech = censor_chat(text)
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

        autoreply = config.sections["server"]["autoreply"]
        if self.frame.np.away and not self.autoreplied and autoreply:
            self.send_message("[Auto-Message] %s" % autoreply)
            self.autoreplied = True

        self.frame.notifications.new_tts(
            config.sections["ui"]["speechprivate"] % {
                "user": self.frame.notifications.tts_clean(self.user),
                "message": self.frame.notifications.tts_clean(speech)
            }
        )

    def send_message(self, text, bytestring=False):

        if not self.chats.connected:
            return

        user_text = self.frame.np.pluginhandler.outgoing_private_chat_event(self.user, text)
        if user_text is None:
            return

        (u, text) = user_text

        my_username = config.sections["server"]["login"]

        if text[:4] == "/me ":
            line = "* %s %s" % (my_username, text[4:])
            usertag = tag = self.tag_me
        else:

            if text == self.chats.CTCP_VERSION:
                line = "CTCP VERSION"
            else:
                line = text

            tag = self.tag_local
            usertag = self.tag_my_username
            line = "[%s] %s" % (my_username, line)

        timestamp_format = config.sections["logging"]["private_timestamp"]
        append_line(self.ChatScroll, line, tag, timestamp_format=timestamp_format,
                    username=my_username, usertag=usertag)

        if self.Log.get_active():
            timestamp_format = config.sections["logging"]["log_timestamp"]
            log.write_log(config.sections["logging"]["privatelogsdir"], self.user, line, timestamp_format)

        if bytestring:
            payload = text
        else:
            payload = auto_replace(text)

        self.frame.np.queue.append(slskmessages.MessageUser(self.user, payload))
        self.frame.np.pluginhandler.outgoing_private_chat_notification(self.user, text)

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

        if self.chats.connected:
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

        if self.chats.connected:
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
        self.chats.remove_tab(self)

    def on_close_all_tabs(self, *args):
        self.chats.remove_all_pages()

    def set_completion_list(self, completion_list):

        # Tab-complete the recepient username
        completion_list.append(self.user)

        # No duplicates
        completion_list = list(set(completion_list))
        completion_list.sort(key=lambda v: v.lower())

        self.entry.set_completion_list(completion_list)
