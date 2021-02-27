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

from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Pango

from pynicotine import slskmessages
from pynicotine.gtkgui.chatrooms import get_completion
from pynicotine.gtkgui.dialogs import option_dialog
from pynicotine.gtkgui.utils import add_alias
from pynicotine.gtkgui.utils import append_line
from pynicotine.gtkgui.utils import expand_alias
from pynicotine.gtkgui.utils import IconNotebook
from pynicotine.gtkgui.utils import is_alias
from pynicotine.gtkgui.utils import load_ui_elements
from pynicotine.gtkgui.utils import open_log
from pynicotine.gtkgui.utils import PopupMenu
from pynicotine.gtkgui.utils import scroll_bottom
from pynicotine.gtkgui.utils import TextSearchBar
from pynicotine.gtkgui.utils import set_widget_color
from pynicotine.gtkgui.utils import set_widget_font
from pynicotine.gtkgui.utils import triggers_context_menu
from pynicotine.gtkgui.utils import unalias
from pynicotine.gtkgui.utils import update_widget_visuals
from pynicotine.logfacility import log
from pynicotine.utils import clean_file
from pynicotine.utils import version
from pynicotine.utils import write_log


CTCP_VERSION = "\x01VERSION\x01"


class PrivateChats(IconNotebook):

    CMDS = set(
        [
            "/alias ", "/unalias ", "/whois ", "/browse ", "/ip ", "/pm ", "/msg ", "/search ", "/usearch ", "/rsearch ",
            "/bsearch ", "/join ", "/add ", "/buddy ", "/rem ", "/unbuddy ", "/ban ", "/ignore ", "/ignoreip ", "/unban ", "/unignore ",
            "/clear ", "/quit ", "/exit ", "/rescan ", "/info ", "/ctcpversion "
        ]
    )

    def __init__(self, frame):

        self.frame = frame

        config = frame.np.config.sections

        IconNotebook.__init__(
            self,
            self.frame.images,
            angle=config["ui"]["labelprivate"],
            tabclosers=config["ui"]["tabclosers"],
            show_hilite_image=config["notifications"]["notification_tab_icons"],
            reorderable=config["ui"]["tab_reorderable"],
            show_status_image=config["ui"]["tab_status_icons"],
            notebookraw=self.frame.PrivatechatNotebookRaw
        )

        self.popup_enable()

        self.connected = 1
        self.users = {}
        self.clist = []

        self.notebook.connect("switch-page", self.on_switch_chat)

        # Clear list of previously open chats if we don't want to restore them
        if not frame.np.config.sections["privatechat"]["store"]:
            frame.np.config.sections["privatechat"]["users"].clear()

    def on_switch_chat(self, notebook, page, page_num, forceupdate=False):

        if self.frame.MainNotebook.get_current_page() != self.frame.MainNotebook.page_num(self.frame.privatechatvbox) and not forceupdate:
            return

        for user, tab in list(self.users.items()):
            if tab.Main == page:
                GLib.idle_add(tab.ChatLine.grab_focus)
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

    def focused(self, page, focused):

        if not focused:
            return

        for user, tab in list(self.users.items()):
            if tab.Main == page:
                if user in self.frame.hilites["private"]:
                    self.frame.notifications.clear("private", tab.user)

    def get_user_status(self, msg):

        if msg.user in self.users:
            tab = self.users[msg.user]

            self.set_user_status(tab.Main, msg.user, msg.status)
            tab.get_user_status(msg.status)

    def send_message(self, user, text=None, show_user=False, bytestring=False):

        if user not in self.users:
            tab = PrivateChat(self, user)
            self.users[user] = tab

            if user not in self.frame.np.config.sections["privatechat"]["users"]:
                self.frame.np.config.sections["privatechat"]["users"].append(user)

            try:
                status = self.frame.np.users[user].status
            except Exception:
                # Offline
                status = 0

            if user not in self.frame.np.watchedusers:
                self.frame.np.queue.put(slskmessages.AddUser(user))

            self.append_page(tab.Main, user, tab.on_close, status=status)

        if show_user:
            if self.get_current_page() != self.page_num(self.users[user].Main):
                self.set_current_page(self.page_num(self.users[user].Main))

        if text is not None:
            self.users[user].send_message(text, bytestring=bytestring)

    def on_tab_popup(self, widget, page):

        username = self.get_page_owner(page, self.users)

        if username not in self.users:
            return False

        menu = PopupMenu(self.frame)
        menu.setup_user_menu(username)
        menu.get_items()[_("Send _Message")].set_visible(False)

        menu.append_item(("", None))
        menu.append_item(("#" + _("Close All Tabs"), menu.on_close_all_tabs, self))
        menu.append_item(("#" + _("_Close Tab"), self.users[username].on_close))
        menu.toggle_user_items()

        menu.popup()
        return True

    def on_tab_click(self, widget, event, page):

        if triggers_context_menu(event):
            return self.on_tab_popup(widget, page)

        if event.button == 2:
            username = self.get_page_owner(page, self.users)
            self.users[username].on_close(widget)
            return True

        return False

    def close_all_tabs(self, dialog, response, data):

        if response == Gtk.ResponseType.OK:
            for user in self.users.copy():
                self.users[user].on_close(dialog)

        dialog.destroy()

    def show_message(self, msg, text, newmessage=True):

        if msg.user in self.frame.np.config.sections["server"]["ignorelist"]:
            return

        if msg.user in self.frame.np.users and isinstance(self.frame.np.users[msg.user].addr, tuple):
            ip, port = self.frame.np.users[msg.user].addr
            if self.frame.np.ip_ignored(ip):
                return

        elif newmessage:
            self.frame.np.queue.put(slskmessages.GetPeerAddress(msg.user))
            self.frame.np.private_message_queue_add(msg, text)
            return

        user_text = self.frame.np.pluginhandler.incoming_private_chat_event(msg.user, text)
        if user_text is None:
            return

        (u, text) = user_text

        self.send_message(msg.user, None)
        chat = self.users[msg.user]
        self.request_changed(chat.Main)

        # Hilight main private chats Label
        self.frame.request_tab_icon(self.frame.PrivateChatTabLabel)

        # Show notifications if the private chats notebook isn't selected,
        # the tab is not selected, or the main window isn't mapped
        if self.get_current_page() != self.page_num(chat.Main) or \
           self.frame.MainNotebook.get_current_page() != self.frame.MainNotebook.page_num(self.frame.privatechatvbox) or \
           not self.frame.MainWindow.get_property("visible"):
            self.frame.notifications.add("private", msg.user)

            if self.frame.np.config.sections["notifications"]["notification_popup_private_message"]:
                self.frame.notifications.new_notification(
                    text,
                    title=_("Private message from %s") % msg.user,
                    priority=Gio.NotificationPriority.HIGH
                )

        # SEND CLIENT VERSION to user if the following string is sent
        ctcpversion = 0
        if text == CTCP_VERSION:
            ctcpversion = 1
            text = "CTCP VERSION"

        self.users[msg.user].show_message(text, newmessage, msg.timestamp)

        if ctcpversion and self.frame.np.config.sections["server"]["ctcpmsgs"] == 0:
            self.send_message(msg.user, GLib.get_application_name() + " " + version)

        self.frame.np.pluginhandler.incoming_private_chat_notification(msg.user, text)

    def update_visuals(self):
        for chat in self.users.values():
            chat.update_visuals()
            chat.update_tags()

    def remove_tab(self, tab):

        if tab.user in self.frame.hilites["private"]:
            self.frame.notifications.clear("private", tab.user)

        del self.users[tab.user]

        # Update completions on exit
        self.update_completions()

        if tab.user in self.frame.np.config.sections["privatechat"]["users"]:
            self.frame.np.config.sections["privatechat"]["users"].remove(tab.user)

        self.remove_page(tab.Main)

    def login(self):

        self.connected = 1
        for user in self.users:
            self.users[user].login()

        if not self.frame.np.config.sections["privatechat"]["store"]:
            return

        for user in self.frame.np.config.sections["privatechat"]["users"]:
            if isinstance(user, str) and user not in self.users:
                self.send_message(user)

    def conn_close(self):

        self.connected = 0

        for user in self.users:
            self.users[user].conn_close()
            tab = self.users[user]

            self.set_user_status(tab.Main, user, 0)

    def update_completions(self):

        config = self.frame.np.config.sections["words"]
        clist = [self.frame.np.config.sections["server"]["login"], "nicotine"] + list(self.users.keys())

        if config["buddies"]:
            clist += [i[0] for i in self.frame.np.config.sections["server"]["userlist"]]

        if config["aliases"]:
            clist += ["/" + k for k in list(self.frame.np.config.sections["server"]["command_aliases"].keys())]

        if config["commands"]:
            clist += self.CMDS

        self.clist = clist

        for user in list(self.users.values()):
            user.get_completion_list(clist=list(self.clist))


class PrivateChat:

    def __init__(self, chats, user):

        self.user = user
        self.chats = chats
        self.frame = chats.frame

        # We should reference the user as soon as possible
        self.chats.users[self.user] = self

        load_ui_elements(self, os.path.join(self.frame.gui_dir, "ui", "privatechat.ui"))

        self.autoreplied = 0
        self.offlinemessage = 0
        self.status = -1
        self.clist = []

        # Text Search
        TextSearchBar(self.ChatScroll, self.SearchBar, self.SearchEntry)

        # Spell Check
        if self.frame.spell_checker is None:
            self.frame.init_spell_checker()

        if self.frame.spell_checker and self.frame.np.config.sections["ui"]["spellcheck"]:
            from gi.repository import Gspell
            spell_buffer = Gspell.EntryBuffer.get_from_gtk_entry_buffer(self.ChatLine.get_buffer())
            spell_buffer.set_spell_checker(self.frame.spell_checker)
            spell_view = Gspell.Entry.get_from_gtk_entry(self.ChatLine)
            spell_view.set_inline_spell_checking(True)

        completion = Gtk.EntryCompletion()
        self.ChatLine.set_completion(completion)
        liststore = Gtk.ListStore(GObject.TYPE_STRING)
        completion.set_model(liststore)

        completion.set_text_column(0)
        completion.set_match_func(self.frame.entry_completion_find_match, self.ChatLine)
        completion.connect("match-selected", self.frame.entry_completion_found_match, self.ChatLine)

        self.Log.set_active(self.frame.np.config.sections["logging"]["privatechat"])

        self.popup_menu_user = popup = PopupMenu(self.frame, False)
        popup.setup_user_menu(user)
        popup.get_items()[_("Send _Message")].set_visible(False)

        self.popup_menu = popup = PopupMenu(self.frame)
        popup.setup(
            ("USERMENU", _("User"), self.popup_menu_user, self.on_popup_menu_user),
            ("", None),
            ("#" + _("Find"), self.on_find_chat_log),
            ("", None),
            ("#" + _("Copy"), self.on_copy_chat_log),
            ("#" + _("Copy All"), self.on_copy_all_chat_log),
            ("", None),
            ("#" + _("View Chat Log"), self.on_view_chat_log),
            ("#" + _("Delete Chat Log"), self.on_delete_chat_log),
            ("", None),
            ("#" + _("Clear Message View"), self.on_clear_messages),
            ("#" + _("_Close Tab"), self.on_close)
        )

        popup.set_user(user)

        self.create_tags()
        self.update_visuals()

        self.chats.update_completions()

        self.read_private_log()

    def read_private_log(self):

        # Read log file
        config = self.frame.np.config.sections
        log = os.path.join(config["logging"]["privatelogsdir"], clean_file(self.user.replace(os.sep, "-")) + ".log")

        try:
            numlines = int(config["logging"]["readprivatelines"])
        except Exception:
            numlines = 15

        try:
            try:
                self.append_log_lines(log, numlines, 'utf-8')

            except UnicodeDecodeError:
                self.append_log_lines(log, numlines, 'latin-1')

        except IOError:
            pass

        GLib.idle_add(scroll_bottom, self.ChatScroll.get_parent())

    def append_log_lines(self, log, numlines, encoding='utf-8'):

        with open(log, 'r', encoding=encoding) as lines:
            # Only show as many log lines as specified in config
            lines = deque(lines, numlines)

            for line in lines:
                append_line(self.ChatScroll, line, self.tag_hilite, timestamp_format="", username=self.user, usertag=self.tag_hilite, scroll=False)

    def login(self):
        timestamp_format = self.frame.np.config.sections["logging"]["private_timestamp"]
        append_line(self.ChatScroll, _("--- reconnected ---"), self.tag_hilite, timestamp_format=timestamp_format)
        self.update_tags()

    def conn_close(self):
        timestamp_format = self.frame.np.config.sections["logging"]["private_timestamp"]
        append_line(self.ChatScroll, _("--- disconnected ---"), self.tag_hilite, timestamp_format=timestamp_format)
        self.status = -1
        self.offlinemessage = 0
        self.update_tags()

    def on_message_view_clicked(self, widget, event):

        if triggers_context_menu(event):
            return self.on_popup_menu(widget)

        return False

    def on_popup_menu(self, widget):
        self.popup_menu.popup()
        return True

    def on_popup_menu_user(self, widget):
        self.popup_menu_user.toggle_user_items()
        return True

    def on_find_chat_log(self, widget):
        self.SearchBar.set_search_mode(True)

    def on_copy_chat_log(self, widget):

        bound = self.ChatScroll.get_buffer().get_selection_bounds()
        if bound is not None and len(bound) == 2:
            start, end = bound
            log = self.ChatScroll.get_buffer().get_text(start, end, True)
            self.frame.clip.set_text(log, -1)

    def on_copy_all_chat_log(self, widget):
        start, end = self.ChatScroll.get_buffer().get_bounds()
        log = self.ChatScroll.get_buffer().get_text(start, end, True)
        self.frame.clip.set_text(log, -1)

    def on_view_chat_log(self, widget):
        open_log(self.frame.np.config.sections["logging"]["privatelogsdir"], self.user)

    def delete_chat_log_response(self, dialog, response, data):

        if response == Gtk.ResponseType.OK:
            log_path = os.path.join(
                self.frame.np.config.sections["logging"]["privatelogsdir"],
                clean_file(self.user.replace(os.sep, "-")) + ".log"
            )

            try:
                if os.path.exists(log_path):
                    os.remove(log_path)

            except Exception as e:
                log.add(_("Failed to remove logged chat messages for user '%(user)s'. Error: %(error)s"), {
                    "user": self.user,
                    "error": e
                })

            self.on_clear_messages(dialog)

        dialog.destroy()

    def on_delete_chat_log(self, widget):

        option_dialog(
            parent=self.frame.MainWindow,
            title=_('Delete Logged Messages?'),
            message=_('Are you sure you wish to permanently delete all logged messages for this user?'),
            callback=self.delete_chat_log_response
        )

    def on_clear_messages(self, widget):
        self.ChatScroll.get_buffer().set_text("")

    def on_show_chat_help(self, widget):

        if not hasattr(self, "AboutPrivateChatCommandsPopover"):
            load_ui_elements(self, os.path.join(self.frame.gui_dir, "ui", "popovers", "privatechatcommands.ui"))
            self.AboutPrivateChatCommandsPopover.set_relative_to(self.ShowChatHelp)

        try:
            self.AboutPrivateChatCommandsPopover.popup()

        except AttributeError:
            # GTK <3.22 support
            self.AboutPrivateChatCommandsPopover.set_transitions_enabled(True)
            self.AboutPrivateChatCommandsPopover.show()

    def show_message(self, text, newmessage=True, timestamp=None):

        self.create_tags()

        if text[:4] == "/me ":
            line = "* %s %s" % (self.user, self.frame.censor_chat(text[4:]))
            speech = line[2:]
            tag = self.tag_me
        else:
            line = "[%s] %s" % (self.user, self.frame.censor_chat(text))
            speech = self.frame.censor_chat(text)
            tag = self.tag_remote

        timestamp_format = self.frame.np.config.sections["logging"]["private_timestamp"]
        if not newmessage and not self.offlinemessage:
            append_line(
                self.ChatScroll,
                _("* Message(s) sent while you were offline. Timestamps are reported by the server and can be off."),
                self.tag_hilite,
                timestamp_format=timestamp_format
            )
            self.offlinemessage = 1

        if newmessage and self.offlinemessage:
            self.offlinemessage = False

        if not newmessage:

            # The timestamps from the server are off by a lot, so we'll only use them when this is an offline message
            # Also, they are in UTC so we need to correct them
            if daylight:
                timestamp -= (3600 * daylight)
            else:
                timestamp += altzone

            append_line(self.ChatScroll, line, self.tag_hilite, timestamp=timestamp, timestamp_format=timestamp_format, username=self.user, usertag=self.tag_username)
        else:
            append_line(self.ChatScroll, line, tag, timestamp_format=timestamp_format, username=self.user, usertag=self.tag_username)

        if self.Log.get_active():
            timestamp_format = self.frame.np.config.sections["logging"]["log_timestamp"]
            write_log(self.frame.np.config.sections["logging"]["privatelogsdir"], self.user, line, timestamp_format)

        autoreply = self.frame.np.config.sections["server"]["autoreply"]
        if self.frame.away and not self.autoreplied and autoreply:
            self.send_message("[Auto-Message] %s" % autoreply)
            self.autoreplied = 1

        self.frame.notifications.new_tts(
            self.frame.np.config.sections["ui"]["speechprivate"] % {
                "user": self.frame.notifications.tts_clean(self.user),
                "message": self.frame.notifications.tts_clean(speech)
            }
        )

    def send_message(self, text, bytestring=False):

        user_text = self.frame.np.pluginhandler.outgoing_private_chat_event(self.user, text)
        if user_text is None:
            return

        (u, text) = user_text

        my_username = self.frame.np.config.sections["server"]["login"]

        if text[:4] == "/me ":
            line = "* %s %s" % (my_username, text[4:])
            usertag = tag = self.tag_me
        else:

            if text == CTCP_VERSION:
                line = "CTCP VERSION"
            else:
                line = text

            tag = self.tag_local
            usertag = self.tag_my_username
            line = "[%s] %s" % (my_username, line)

        timestamp_format = self.frame.np.config.sections["logging"]["private_timestamp"]
        append_line(self.ChatScroll, line, tag, timestamp_format=timestamp_format, username=my_username, usertag=usertag)

        if self.Log.get_active():
            timestamp_format = self.frame.np.config.sections["logging"]["log_timestamp"]
            write_log(self.frame.np.config.sections["logging"]["privatelogsdir"], self.user, line, timestamp_format)

        if bytestring:
            payload = text
        else:
            payload = self.frame.auto_replace(text)

        if self.PeerPrivateMessages.get_active():
            # not in the soulseek protocol
            self.frame.np.send_message_to_peer(self.user, slskmessages.PMessageUser(None, my_username, payload))
        else:
            self.frame.np.queue.put(slskmessages.MessageUser(self.user, payload))

        self.frame.np.pluginhandler.outgoing_private_chat_notification(self.user, text)

    def thread_alias(self, alias):

        text = expand_alias(alias)
        if not text:
            log.add(_('Alias "%s" returned nothing'), alias)
            return

        if text[:2] == "//":
            text = text[1:]

        self.frame.np.queue.put(slskmessages.MessageUser(self.user, self.frame.auto_replace(text)))

    def on_enter(self, widget):

        text = widget.get_text()

        if not text:
            widget.set_text("")
            return

        if is_alias(text):
            import _thread
            _thread.start_new_thread(self.thread_alias, (text,))
            widget.set_text("")
            return

        s = text.split(" ", 1)
        cmd = s[0]
        if len(s) == 2 and s[1]:
            args = arg_self = s[1]
        else:
            args = ""
            arg_self = self.user

        if cmd in ("/alias", "/al"):

            append_line(self.ChatScroll, add_alias(args), None, "")
            if self.frame.np.config.sections["words"]["aliases"]:
                self.frame.chatrooms.update_completions()
                self.frame.privatechats.update_completions()

        elif cmd in ("/unalias", "/un"):

            append_line(self.ChatScroll, unalias(args), None, "")
            if self.frame.np.config.sections["words"]["aliases"]:
                self.frame.chatrooms.update_completions()
                self.frame.privatechats.update_completions()

        elif cmd in ("/join", "/j"):
            if args:
                self.frame.np.queue.put(slskmessages.JoinRoom(args))

        elif cmd in ("/w", "/whois", "/info"):
            self.frame.local_user_info_request(arg_self)
            self.frame.change_main_page("userinfo")

        elif cmd in ("/b", "/browse"):
            self.frame.browse_user(arg_self)
            self.frame.change_main_page("userbrowse")

        elif cmd == "/ip":
            self.frame.np.ip_requested.add(arg_self)
            self.frame.np.queue.put(slskmessages.GetPeerAddress(arg_self))

        elif cmd == "/pm":
            if args:
                self.frame.privatechats.send_message(args, show_user=True)
                self.frame.change_main_page("private")

        elif cmd in ("/m", "/msg"):
            if args:
                s = args.split(" ", 1)
                user = s[0]
                if len(s) == 2:
                    msg = s[1]
                else:
                    msg = None

                self.frame.privatechats.send_message(user, msg, show_user=True)
                self.frame.change_main_page("private")

        elif cmd in ("/s", "/search"):
            if args:
                self.frame.searches.do_search(args, 0)
                self.frame.on_search(None)
                self.frame.change_main_page("search")

        elif cmd in ("/us", "/usearch"):
            if args:
                self.frame.searches.do_search(args, 3, [self.user])
                self.frame.on_search(None)
                self.frame.change_main_page("search")

        elif cmd in ("/rs", "/rsearch"):
            if args:
                self.frame.searches.do_search(args, 1)
                self.frame.on_search(None)
                self.frame.change_main_page("search")

        elif cmd in ("/bs", "/bsearch"):
            if args:
                self.frame.searches.do_search(args, 2)
                self.frame.on_search(None)
                self.frame.change_main_page("search")

        elif cmd in ("/ad", "/add", "/buddy"):
            if args:
                self.frame.userlist.add_to_list(args)

        elif cmd in ("/rem", "/unbuddy"):
            if args:
                self.frame.userlist.remove_from_list(args)

        elif cmd == "/ban":
            if args:
                self.frame.ban_user(args)

        elif cmd == "/ignore":
            if args:
                self.frame.ignore_user(args)

        elif cmd == "/ignoreip":
            if args:
                self.frame.ignore_ip(args)

        elif cmd == "/unban":
            if args:
                self.frame.unban_user(args)

        elif cmd == "/unignore":
            if args:
                self.frame.unignore_user(args)

        elif cmd == "/ctcpversion":
            if arg_self:
                self.frame.privatechats.send_message(arg_self, CTCP_VERSION, show_user=True, bytestring=True)

        elif cmd in ("/clear", "/cl"):
            self.ChatScroll.get_buffer().set_text("")

        elif cmd in ("/a", "/away"):
            self.frame.on_away(None)

        elif cmd in ("/q", "/quit", "/exit"):
            self.frame.on_quit(None)
            return

        elif cmd in ("/c", "/close"):
            self.on_close(None)

        elif cmd == "/now":
            self.display_now_playing()

        elif cmd == "/rescan":
            # Rescan public shares if needed
            if not self.frame.np.config.sections["transfers"]["friendsonly"] and self.np.config.sections["transfers"]["shared"]:
                self.frame.on_rescan()

            # Rescan buddy shares if needed
            if self.frame.np.config.sections["transfers"]["enablebuddyshares"]:
                self.frame.on_buddy_rescan()

        elif cmd[:1] == "/" and self.frame.np.pluginhandler.trigger_private_command_event(self.user, cmd[1:], args):
            pass

        elif cmd[:1] == "/" and cmd != "/me" and cmd[:2] != "//":
            log.add(_("Command %s is not recognized"), text)
            return

        else:
            if text[:2] == "//":
                text = text[1:]

            if self.chats.connected:
                self.send_message(text)
                widget.set_text("")

            return

        widget.set_text("")

    def display_now_playing(self):
        self.frame.np.now_playing.display_now_playing(callback=self.send_message)

    def update_visuals(self):

        for widget in self.__dict__.values():
            update_widget_visuals(widget, update_text_tags=False)

    def create_tag(self, buffer, color):

        tag = buffer.create_tag()
        set_widget_color(tag, self.frame.np.config.sections["ui"][color])
        set_widget_font(tag, self.frame.np.config.sections["ui"]["chatfont"])

        return tag

    def create_tags(self):

        buffer = self.ChatScroll.get_buffer()
        self.tag_remote = self.create_tag(buffer, "chatremote")
        self.tag_local = self.create_tag(buffer, "chatlocal")
        self.tag_me = self.create_tag(buffer, "chatme")
        self.tag_hilite = self.create_tag(buffer, "chathilite")

        if self.status == 1 and self.frame.np.config.sections["ui"]["showaway"]:
            statuscolor = "useraway"
        elif self.status == 2 or not self.frame.np.config.sections["ui"]["showaway"] and self.status == 1:
            statuscolor = "useronline"
        else:
            statuscolor = "useroffline"

        self.tag_username = self.create_tag(buffer, statuscolor)

        if self.chats.connected:
            if self.frame.away and self.frame.np.config.sections["ui"]["showaway"]:
                self.tag_my_username = self.create_tag(buffer, "useraway")
            else:
                self.tag_my_username = self.create_tag(buffer, "useronline")
        else:
            self.tag_my_username = self.create_tag(buffer, "useroffline")

        usernamestyle = self.frame.np.config.sections["ui"]["usernamestyle"]

        if usernamestyle == "bold":
            self.tag_username.set_property("weight", Pango.Weight.BOLD)
            self.tag_my_username.set_property("weight", Pango.Weight.BOLD)
        else:
            self.tag_username.set_property("weight", Pango.Weight.NORMAL)
            self.tag_my_username.set_property("weight", Pango.Weight.NORMAL)

        if usernamestyle == "italic":
            self.tag_username.set_property("style", Pango.Style.ITALIC)
            self.tag_my_username.set_property("style", Pango.Style.ITALIC)
        else:
            self.tag_username.set_property("style", Pango.Style.NORMAL)
            self.tag_my_username.set_property("style", Pango.Style.NORMAL)

        if usernamestyle == "underline":
            self.tag_username.set_property("underline", Pango.Underline.SINGLE)
            self.tag_my_username.set_property("underline", Pango.Underline.SINGLE)
        else:
            self.tag_username.set_property("underline", Pango.Underline.NONE)
            self.tag_my_username.set_property("underline", Pango.Underline.NONE)

    def update_tag_visuals(self, tag, color):

        set_widget_color(tag, self.frame.np.config.sections["ui"][color])
        set_widget_font(tag, self.frame.np.config.sections["ui"]["chatfont"])

        if color in ("useraway", "useronline", "useroffline"):

            usernamestyle = self.frame.np.config.sections["ui"]["usernamestyle"]

            if usernamestyle == "bold":
                tag.set_property("weight", Pango.Weight.BOLD)
            else:
                tag.set_property("weight", Pango.Weight.NORMAL)

            if usernamestyle == "italic":
                tag.set_property("style", Pango.Style.ITALIC)
            else:
                tag.set_property("style", Pango.Style.NORMAL)

            if usernamestyle == "underline":
                tag.set_property("underline", Pango.Underline.SINGLE)
            else:
                tag.set_property("underline", Pango.Underline.NONE)

    def update_tags(self):

        self.update_tag_visuals(self.tag_remote, "chatremote")
        self.update_tag_visuals(self.tag_local, "chatlocal")
        self.update_tag_visuals(self.tag_me, "chatme")
        self.update_tag_visuals(self.tag_hilite, "chathilite")

        color = self.get_user_status_color(self.status)
        self.update_tag_visuals(self.tag_username, color)

        if self.chats.connected:
            if self.frame.away and self.frame.np.config.sections["ui"]["showaway"]:
                self.update_tag_visuals(self.tag_my_username, "useraway")
            else:
                self.update_tag_visuals(self.tag_my_username, "useronline")
        else:
            self.update_tag_visuals(self.tag_my_username, "useroffline")

    def get_user_status_color(self, status):

        if status == 1:
            color = "useraway"
        elif status == 2:
            color = "useronline"
        else:
            color = "useroffline"

        if not self.frame.np.config.sections["ui"]["showaway"] and color == "useraway":
            color = "useronline"

        return color

    def get_user_status(self, status):

        if status == self.status:
            return

        self.status = status
        color = self.get_user_status_color(self.status)
        self.update_tag_visuals(self.tag_username, color)

    def on_close(self, widget):

        self.chats.remove_tab(self)

    def get_completion_list(self, ix=0, text="", clist=None):

        config = self.frame.np.config.sections["words"]

        completion = self.ChatLine.get_completion()
        completion.set_popup_single_match(not config["onematch"])
        completion.set_minimum_key_length(config["characters"])

        liststore = completion.get_model()
        liststore.clear()

        if clist is None:
            clist = []

        if not config["tab"]:
            return

        # no duplicates
        def _combilower(x):
            try:
                return str.lower(x)
            except Exception:
                return str.lower(x)

        clist = list(set(clist))
        clist.sort(key=_combilower)

        completion.set_popup_completion(False)

        if config["dropdown"]:
            for word in clist:
                liststore.append([word])

            completion.set_popup_completion(True)

        self.clist = clist

    def on_key_press(self, widget, event):

        if event.keyval == Gdk.keyval_from_name("Prior"):

            scrolled = self.ChatScroll.get_parent()
            adj = scrolled.get_vadjustment()
            adj.set_value(adj.value - adj.page_increment)

        elif event.keyval == Gdk.keyval_from_name("Next"):

            scrolled = self.ChatScroll.get_parent()
            adj = scrolled.get_vadjustment()
            maximum = adj.upper - adj.page_size
            new = adj.value + adj.page_increment

            if new > maximum:
                new = maximum

            adj.set_value(new)

        if event.keyval != Gdk.keyval_from_name("Tab"):
            return False

        config = self.frame.np.config.sections["words"]
        if not config["tab"]:
            return False

        ix = widget.get_position()
        text = widget.get_text()[:ix].split(" ")[-1]
        preix = ix - len(text)

        completion, single = get_completion(text, self.chats.clist)

        if completion:
            widget.delete_text(preix, ix)
            widget.insert_text(completion, ix)
            widget.set_position(preix + len(completion))

        widget.stop_emission_by_name("key_press_event")

        return True
