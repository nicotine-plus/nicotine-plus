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
from gettext import gettext as _
from time import altzone
from time import daylight

import gi
from gi.repository import Gdk
from gi.repository import GObject as gobject
from gi.repository import Gtk as gtk
from gi.repository import Pango as pango

from pynicotine import slskmessages
from pynicotine.gtkgui.chatrooms import GetCompletion
from pynicotine.gtkgui.utils import AppendLine
from pynicotine.gtkgui.utils import EncodingsMenu
from pynicotine.gtkgui.utils import IconNotebook
from pynicotine.gtkgui.utils import PopupMenu
from pynicotine.gtkgui.utils import SaveEncoding
from pynicotine.gtkgui.utils import WriteLog
from pynicotine.gtkgui.utils import expand_alias
from pynicotine.gtkgui.utils import fixpath
from pynicotine.gtkgui.utils import is_alias
from pynicotine.logfacility import log
from pynicotine.slskmessages import ToBeEncoded
from pynicotine.utils import version

gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('Pango', '1.0')


CTCP_VERSION = "\x01VERSION\x01"


class PrivateChats(IconNotebook):

    CMDS = set(
        [
            "/alias ", "/unalias ", "/whois ", "/browse ", "/ip ", "/pm ", "/msg ", "/search ", "/usearch ", "/rsearch ",
            "/bsearch ", "/join ", "/add ", "/buddy ", "/rem ", "/unbuddy ", "/ban ", "/ignore ", "/ignoreip ", "/unban ", "/unignore ",
            "/clear ", "/quit ", "/exit ", "/rescan ", "/info ", "/attach ", "/detach ", "/ctcpversion "
        ]
    )

    def __init__(self, frame):

        self.frame = frame

        ui = frame.np.config.sections["ui"]

        IconNotebook.__init__(
            self,
            self.frame.images,
            angle=ui["labelprivate"],
            tabclosers=ui["tabclosers"],
            show_image=ui["tab_icons"],
            reorderable=ui["tab_reorderable"],
            show_status_image=ui["tab_status_icons"],
            notebookraw=self.frame.PrivatechatNotebookRaw
        )

        self.popup_enable()

        self.connected = 1
        self.users = {}
        self.clist = []

        self.Notebook.connect("switch-page", self.OnSwitchPage)

    def OnSwitchPage(self, notebook, page, page_num, force=0):

        if self.frame.MainNotebook.get_current_page() != self.frame.MainNotebook.page_num(self.frame.privatevbox) and not force:
            return

        page = notebook.get_nth_page(page_num)

        for user, tab in list(self.users.items()):
            if tab.Main == page:
                gobject.idle_add(tab.ChatLine.grab_focus)
                # Remove hilite if selected tab belongs to a user in the hilite list
                if user in self.frame.TrayApp.tray_status["hilites"]["private"]:
                    self.frame.Notifications.Clear("private", tab.user)

    def ClearNotifications(self):

        if self.frame.MainNotebook.get_current_page() != self.frame.MainNotebook.page_num(self.frame.privatevbox):
            return

        page = self.get_nth_page(self.get_current_page())

        for user, tab in list(self.users.items()):
            if tab.Main == page:
                # Remove hilite
                if user in self.frame.TrayApp.tray_status["hilites"]["private"]:
                    self.frame.Notifications.Clear("private", tab.user)

    def Focused(self, page, focused):

        if not focused:
            return

        for user, tab in list(self.users.items()):
            if tab.Main == page:
                if user in self.frame.TrayApp.tray_status["hilites"]["private"]:
                    self.frame.Notifications.Clear("private", tab.user)

    def GetUserStatus(self, msg):

        if msg.user in self.users:

            tab = self.users[msg.user]
            status = [_("Offline"), _("Away"), _("Online")][msg.status]

            if not self.frame.np.config.sections["ui"]["tab_status_icons"]:
                self.set_text(tab.Main, "%s (%s)" % (msg.user[:15], status))
            else:
                self.set_text(tab.Main, msg.user)

            self.set_status_image(tab.Main, msg.status)
            tab.GetUserStatus(msg.status)

    def SendMessage(self, user, text=None, direction=None, bytestring=False):

        if user not in self.users:
            tab = PrivateChat(self, user)
            self.users[user] = tab
            self.append_page(tab.Main, user, tab.OnClose)
            self.frame.np.queue.put(slskmessages.AddUser(user))

        if direction:
            if self.get_current_page() != self.page_num(self.users[user].Main):
                self.set_current_page(self.page_num(self.users[user].Main))

        if text is not None:
            self.users[user].SendMessage(text, bytestring=bytestring)

    def TabPopup(self, user):

        if user not in self.users:
            return

        popup = PopupMenu(self.frame)
        popup.setup(
            ("#" + _("Show IP a_ddress"), popup.OnShowIPaddress),
            ("#" + _("Get user i_nfo"), popup.OnGetUserInfo),
            ("#" + _("Brow_se files"), popup.OnBrowseUser),
            ("#" + _("Gi_ve privileges"), popup.OnGivePrivileges),
            ("#" + _("Client Version"), popup.OnVersion),
            ("", None),
            ("$" + _("Add user to list"), popup.OnAddToList),
            ("$" + _("Ban this user"), popup.OnBanUser),
            ("$" + _("Ignore this user"), popup.OnIgnoreUser),
            ("$" + _("B_lock this user's IP Address"), popup.OnBlockUser),
            ("$" + _("Ignore this user's IP Address"), popup.OnIgnoreIP),
            ("", None),
            ("#" + _("Detach this tab"), self.users[user].Detach),
            ("#" + _("Close this tab"), self.users[user].OnClose)
        )

        popup.set_user(user)

        me = (popup.user is None or popup.user == self.frame.np.config.sections["server"]["login"])
        items = popup.get_children()

        items[6].set_active(user in [i[0] for i in self.frame.np.config.sections["server"]["userlist"]])
        items[7].set_active(user in self.frame.np.config.sections["server"]["banlist"])
        items[8].set_active(user in self.frame.np.config.sections["server"]["ignorelist"])
        items[9].set_active(self.frame.UserIpIsBlocked(user))
        items[9].set_sensitive(not me)
        items[10].set_active(self.frame.UserIpIsIgnored(user))
        items[10].set_sensitive(not me)

        return popup

    def on_tab_click(self, widget, event, child):

        if event.type == Gdk.EventType.BUTTON_PRESS:

            n = self.page_num(child)
            page = self.get_nth_page(n)
            username = [user for user, tab in list(self.users.items()) if tab.Main is page][0]

            if event.button == 2:
                self.users[username].OnClose(widget)
                return True

            if event.button == 3:
                menu = self.TabPopup(username)
                menu.popup(None, None, None, None, event.button, event.time)
                return True

            return False

        return False

    def ShowMessage(self, msg, text, status=None):

        if msg.user in self.frame.np.config.sections["server"]["ignorelist"]:
            return

        if msg.user in self.frame.np.users and type(self.frame.np.users[msg.user].addr) is tuple:
            ip, port = self.frame.np.users[msg.user].addr
            if self.frame.np.ipIgnored(ip):
                return
        else:
            self.frame.np.queue.put(slskmessages.GetPeerAddress(msg.user))
            self.frame.np.PrivateMessageQueueAdd(msg, text)
            return

        user_text = self.frame.pluginhandler.IncomingPrivateChatEvent(msg.user, text)
        if user_text is None:
            return

        (u, text) = user_text

        self.SendMessage(msg.user, None)
        chat = self.users[msg.user]
        self.request_changed(chat.Main)

        if self.is_tab_detached(chat.Main):
            # Only show notifications if window is not focused, and don't highlight main window
            if not self.is_detached_tab_focused(chat.Main):
                self.frame.Notifications.Add("private", msg.user)
        else:
            # If tab isn't detached
            # Hilight main private chats Label
            self.frame.RequestIcon(self.frame.PrivateChatTabLabel, chat.Main)

            # Show notifications if the private chats notebook isn't selected,
            # the tab is not selected, or the main window isn't mapped
            if self.get_current_page() != self.page_num(chat.Main) or \
               self.frame.MainNotebook.get_current_page() != self.frame.MainNotebook.page_num(self.frame.privatevbox) or \
               not self.frame.is_mapped:
                self.frame.Notifications.Add("private", msg.user)

        # SEND CLIENT VERSION to user if the following string is sent
        ctcpversion = 0
        if text == CTCP_VERSION:
            ctcpversion = 1
            text = "CTCP VERSION"

        self.users[msg.user].ShowMessage(text, status, msg.timestamp)

        if ctcpversion and self.frame.np.config.sections["server"]["ctcpmsgs"] == 0:
            self.SendMessage(msg.user, "Nicotine+ %s" % version)

        self.frame.pluginhandler.IncomingPrivateChatNotification(msg.user, text)

    def UpdateColours(self):
        for chat in list(self.users.values()):
            chat.ChangeColours()

    def RemoveTab(self, tab):

        if tab.user in self.frame.TrayApp.tray_status["hilites"]["private"]:
            self.frame.Notifications.Clear("private", tab.user)

        del self.users[tab.user]

        # Update completions on exit
        self.UpdateCompletions()

        if tab.user in self.frame.np.config.sections["privatechat"]["users"]:
            self.frame.np.config.sections["privatechat"]["users"].remove(tab.user)

        if self.is_tab_detached(tab.Main):
            tab.Main.get_parent_window().destroy()
        else:
            self.remove_page(tab.Main)
            tab.Main.destroy()

    def Login(self):

        self.connected = 1
        for user in self.users:
            self.users[user].Login()

        if self.frame.np.config.sections["privatechat"]["store"]:
            self.frame.np.config.sections["privatechat"]["users"].sort()
            for user in self.frame.np.config.sections["privatechat"]["users"]:
                if user not in self.users:
                    self.SendMessage(user, None, 1)

    def ConnClose(self):

        self.connected = 0
        for user in self.users:
            self.users[user].ConnClose()
            tab = self.users[user]
            self.set_text(tab.Main, "%s (%s)" % (user[:15], _("Offline")))
            self.set_status_image(tab.Main, 0)
            tab.GetUserStatus(0)

    def UpdateCompletions(self):

        config = self.frame.np.config.sections["words"]
        clist = [self.frame.np.config.sections["server"]["login"], "nicotine"] + list(self.users.keys())

        if config["buddies"]:
            clist += [i[0] for i in self.frame.userlist.userlist]

        if config["aliases"]:
            clist += ["/" + k for k in list(self.frame.np.config.aliases.keys())]

        if config["commands"]:
            clist += self.CMDS

        self.clist = clist

        for user in list(self.users.values()):
            user.GetCompletionList(clist=list(self.clist))


class PrivateChat:

    def __init__(self, chats, user):

        self.user = user
        self.chats = chats
        self.frame = chats.frame

        # We should reference the user as soon as possible
        self.chats.users[self.user] = self

        builder = gtk.Builder()

        builder.set_translation_domain('nicotine')
        builder.add_from_file(os.path.join(os.path.dirname(os.path.realpath(__file__)), "ui", "privatechat.ui"))

        self.PrivateChatTab = builder.get_object("PrivateChatTab")

        for i in builder.get_objects():
            try:
                self.__dict__[gtk.Buildable.get_name(i)] = i
            except TypeError:
                pass

        self.PrivateChatTab.remove(self.Main)
        self.PrivateChatTab.destroy()

        builder.connect_signals(self)

        self.autoreplied = 0
        self.offlinemessage = 0
        self.status = -1
        self.clist = []

        # Encoding Combobox
        self.Elist = {}
        self.encoding, m = EncodingsMenu(self.frame.np, "userencoding", user)
        self.EncodingStore = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
        self.Encoding.set_model(self.EncodingStore)

        cell = gtk.CellRendererText()
        self.Encoding.pack_start(cell, True)
        self.Encoding.add_attribute(cell, 'text', 0)

        cell2 = gtk.CellRendererText()
        self.Encoding.pack_start(cell2, False)
        self.Encoding.add_attribute(cell2, 'text', 1)

        for item in m:
            self.Elist[item[1]] = self.EncodingStore.append([item[1], item[0]])
            if self.encoding == item[1]:
                self.Encoding.set_active_iter(self.Elist[self.encoding])

        if self.frame.SEXY and self.frame.np.config.sections["ui"]["spellcheck"]:
            import sexy
            self.hbox5.remove(self.ChatLine)
            self.ChatLine.destroy()
            self.ChatLine = sexy.SpellEntry()
            self.ChatLine.show()
            self.ChatLine.connect("activate", self.OnEnter)
            self.ChatLine.connect("key_press_event", self.OnKeyPress)
            self.hbox5.pack_start(self.ChatLine, True, True, 0)
            self.hbox5.reorder_child(self.ChatLine, 0)

        completion = gtk.EntryCompletion()
        self.ChatLine.set_completion(completion)
        liststore = gtk.ListStore(gobject.TYPE_STRING)
        completion.set_model(liststore)

        completion.set_text_column(0)
        completion.set_match_func(self.frame.EntryCompletionFindMatch, self.ChatLine)
        completion.connect("match-selected", self.frame.EntryCompletionFoundMatch, self.ChatLine)

        self.Log.set_active(self.frame.np.config.sections["logging"]["privatechat"])

        self.popup_menu_user = popup = PopupMenu(self.frame)
        popup.setup(
            ("#" + _("Show IP a_ddress"), popup.OnShowIPaddress),
            ("#" + _("Get user i_nfo"), popup.OnGetUserInfo),
            ("#" + _("Brow_se files"), popup.OnBrowseUser),
            ("#" + _("Gi_ve privileges"), popup.OnGivePrivileges),
            ("#" + _("Client Version"), popup.OnVersion),
            ("", None),
            ("$" + _("Add user to list"), popup.OnAddToList),
            ("$" + _("Ban this user"), popup.OnBanUser),
            ("$" + _("Ignore this user"), popup.OnIgnoreUser),
            ("$" + _("B_lock this user's IP Address"), popup.OnBlockUser),
            ("$" + _("Ignore this user's IP Address"), popup.OnIgnoreIP)
        )

        popup.set_user(user)

        self.popup_menu = popup = PopupMenu(self.frame)
        popup.setup(
            ("USERMENU", _("User"), self.popup_menu_user, self.OnPopupMenuUser),
            ("", None),
            ("#" + _("Find"), self.OnFindChatLog),
            ("", None),
            ("#" + _("Copy"), self.OnCopyChatLog),
            ("#" + _("Copy All"), self.OnCopyAllChatLog),
            ("", None),
            ("#" + _("Clear log"), self.OnClearChatLog),
            ("", None),
            ("#" + _("Close"), self.OnClose)
        )

        popup.set_user(user)

        self.ChatScroll.connect("button_press_event", self.OnPopupMenu)
        self.ChatScroll.connect("key_press_event", self.OnPopupMenu)

        self.UpdateColours()

        self.chats.UpdateCompletions()

        self.ReadPrivateLog()

    def ReadPrivateLog(self):

        # Read log file
        config = self.frame.np.config.sections
        log = os.path.join(config["logging"]["privatelogsdir"], fixpath(self.user.replace(os.sep, "-")) + ".log")

        try:
            lines = int(config["logging"]["readprivatelines"])
        except Exception:
            lines = 15

        try:
            f = open(log, "r")
            d = f.read()
            f.close()
            s = d.split("\n")
            for l in s[- lines:-1]:
                AppendLine(self.ChatScroll, l + "\n", self.tag_hilite, timestamp_format="", username=self.user, usertag=self.tag_hilite)
        except IOError as e:  # noqa: F841
            pass

        gobject.idle_add(self.frame.ScrollBottom, self.ChatScroll.get_parent())

    def Login(self):
        timestamp_format = self.frame.np.config.sections["logging"]["private_timestamp"]
        AppendLine(self.ChatScroll, _("--- reconnected ---"), self.tag_hilite, timestamp_format=timestamp_format)
        self.ChangeColours()

    def ConnClose(self):
        timestamp_format = self.frame.np.config.sections["logging"]["private_timestamp"]
        AppendLine(self.ChatScroll, _("--- disconnected ---"), self.tag_hilite, timestamp_format=timestamp_format)
        self.status = -1
        self.offlinemessage = 0
        self.ChangeColours()

    def OnPopupMenu(self, widget, event):

        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3:

            self.popup_menu.popup(None, None, None, None, event.button, event.time)
            self.ChatScroll.emit_stop_by_name("button_press_event")
            return True

        elif event.type == Gdk.EventType.KEY_PRESS:

            if event.keyval == Gdk.keyval_from_name("Menu"):

                self.popup_menu.popup(None, None, None, None, 0, 0)
                self.ChatScroll.emit_stop_by_name("key_press_event")
                return True

        return False

    def OnPopupMenuUser(self, widget):

        items = self.popup_menu_user.get_children()
        me = (self.popup_menu_user.user is None or self.popup_menu_user.user == self.frame.np.config.sections["server"]["login"])

        items[6].set_active(self.user in [i[0] for i in self.frame.np.config.sections["server"]["userlist"]])
        items[7].set_active(self.user in self.frame.np.config.sections["server"]["banlist"])
        items[8].set_active(self.user in self.frame.np.config.sections["server"]["ignorelist"])
        items[9].set_active(self.frame.UserIpIsBlocked(self.user))
        items[9].set_sensitive(not me)
        items[10].set_active(self.frame.UserIpIsIgnored(self.user))
        items[10].set_sensitive(not me)

        return True

    def OnFindChatLog(self, widget):
        self.frame.OnFindTextview(widget, self.ChatScroll)

    def OnCopyChatLog(self, widget):

        bound = self.ChatScroll.get_buffer().get_selection_bounds()
        if bound is not None and len(bound) == 2:
            start, end = bound
            log = self.ChatScroll.get_buffer().get_text(start, end)
            self.frame.clip.set_text(log)

    def OnCopyAllChatLog(self, widget):
        start, end = self.ChatScroll.get_buffer().get_bounds()
        log = self.ChatScroll.get_buffer().get_text(start, end)
        self.frame.clip.set_text(log)

    def OnClearChatLog(self, widget):
        self.ChatScroll.get_buffer().set_text("")

    def ShowMessage(self, text, status=None, timestamp=None):

        self.UpdateColours()

        if text[:4] == "/me ":
            line = "* %s %s" % (self.user, self.frame.CensorChat(text[4:]))
            speech = line[2:]
            tag = self.tag_me
        else:
            line = "[%s] %s" % (self.user, self.frame.CensorChat(text))
            speech = self.frame.CensorChat(text)
            tag = self.tag_remote

        timestamp_format = self.frame.np.config.sections["logging"]["private_timestamp"]
        if status and not self.offlinemessage:
            AppendLine(
                self.ChatScroll,
                _("* Message(s) sent while you were offline. Timestamps are reported by the server and can be off."),
                self.tag_hilite,
                timestamp_format=timestamp_format
            )
            self.offlinemessage = 1

        if not status and self.offlinemessage:
            self.offlinemessage = False

        if status:
            # The timestamps from the server are off by a lot, so we'll only use them when this is an offline message
            # Also, they are in UTC so we need to correct them
            if daylight:
                timestamp -= (3600 * daylight)
            else:
                timestamp += altzone

            AppendLine(self.ChatScroll, line, self.tag_hilite, timestamp=timestamp, timestamp_format=timestamp_format, username=self.user, usertag=self.tag_username)
        else:
            AppendLine(self.ChatScroll, line, tag, timestamp_format=timestamp_format, username=self.user, usertag=self.tag_username)

        if self.Log.get_active():
            WriteLog(self.frame.np.config.sections["logging"]["privatelogsdir"], self.user, line)

        autoreply = self.frame.np.config.sections["server"]["autoreply"]
        if self.frame.away and not self.autoreplied and autoreply:
            self.SendMessage("[Auto-Message] %s" % autoreply)
            self.autoreplied = 1

        self.frame.Notifications.new_tts(
            self.frame.np.config.sections["ui"]["speechprivate"] % {
                "user": self.frame.Notifications.tts_clean(self.user),
                "message": self.frame.Notifications.tts_clean(speech)
            }
        )

    def SendMessage(self, text, bytestring=False):

        user_text = self.frame.pluginhandler.OutgoingPrivateChatEvent(self.user, text)
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
        AppendLine(self.ChatScroll, line, tag, timestamp_format=timestamp_format, username=my_username, usertag=usertag)

        if self.Log.get_active():
            WriteLog(self.frame.np.config.sections["logging"]["privatelogsdir"], self.user, line)

        if bytestring:
            payload = text
        else:
            payload = ToBeEncoded(self.frame.AutoReplace(text), self.encoding)

        if self.PeerPrivateMessages.get_active():
            # not in the soulseek protocol
            self.frame.np.ProcessRequestToPeer(self.user, slskmessages.PMessageUser(None, my_username, payload))
        else:
            self.frame.np.queue.put(slskmessages.MessageUser(self.user, payload))

    def threadAlias(self, alias):

        text = expand_alias(self.frame.np.config.aliases, alias)
        if not text:
            log.add(_('Alias "%s" returned nothing') % alias)
            return

        if text[:2] == "//":
            text = text[1:]

        self.frame.np.queue.put(slskmessages.MessageUser(self.user, ToBeEncoded(self.frame.AutoReplace(text), self.encoding)))

    def OnEnter(self, widget):

        text = widget.get_text()

        if not text:
            widget.set_text("")
            return

        if is_alias(self.frame.np.config.aliases, text):
            import _thread
            _thread.start_new_thread(self.threadAlias, (text,))
            widget.set_text("")
            return

        s = text.split(" ", 1)
        cmd = s[0]
        if len(s) == 2 and s[1]:
            realargs = args = s[1]
        else:
            args = self.user
            realargs = ""

        if cmd in ("/alias", "/al"):

            AppendLine(self.ChatScroll, self.frame.np.config.AddAlias(realargs), None, "")
            if self.frame.np.config.sections["words"]["aliases"]:
                self.frame.chatrooms.roomsctrl.UpdateCompletions()
                self.frame.privatechats.UpdateCompletions()

        elif cmd in ("/unalias", "/un"):

            AppendLine(self.ChatScroll, self.frame.np.config.Unalias(realargs), None, "")
            if self.frame.np.config.sections["words"]["aliases"]:
                self.frame.chatrooms.roomsctrl.UpdateCompletions()
                self.frame.privatechats.UpdateCompletions()

        elif cmd in ["/join", "/j"]:
            self.frame.np.queue.put(slskmessages.JoinRoom(args))

        elif cmd in ["/w", "/whois", "/info"]:
            if args:
                self.frame.LocalUserInfoRequest(args)
                self.frame.OnUserInfo(None)

        elif cmd in ["/b", "/browse"]:
            if args:
                self.frame.BrowseUser(args)
                self.frame.OnUserBrowse(None)

        elif cmd == "/ip":
            if args:
                user = args
                if user not in self.frame.np.ip_requested:
                    self.frame.np.ip_requested.append(user)
                self.frame.np.queue.put(slskmessages.GetPeerAddress(user))

        elif cmd == "/pm":
            if realargs:
                self.frame.privatechats.SendMessage(realargs, None, 1)

        elif cmd in ["/m", "/msg"]:
            if realargs:
                s = realargs.split(" ", 1)
                user = s[0]
                if len(s) == 2:
                    msg = s[1]
                else:
                    msg = None

                self.frame.privatechats.SendMessage(user, msg)

        elif cmd in ["/s", "/search"]:
            if realargs:
                self.frame.Searches.DoSearch(realargs, 0)
                self.frame.OnSearch(None)

        elif cmd in ["/us", "/usearch"]:
            if realargs:
                self.frame.Searches.DoSearch(realargs, 3, [self.user])
                self.frame.OnSearch(None)

        elif cmd in ["/rs", "/rsearch"]:
            if realargs:
                self.frame.Searches.DoSearch(realargs, 1)
                self.frame.OnSearch(None)

        elif cmd in ["/bs", "/bsearch"]:
            if realargs:
                self.frame.Searches.DoSearch(realargs, 2)
                self.frame.OnSearch(None)

        elif cmd in ["/ad", "/add", "/buddy"]:
            if args:
                self.frame.userlist.AddToList(args)

        elif cmd in ["/rem", "/unbuddy"]:
            if args:
                self.frame.userlist.RemoveFromList(args)

        elif cmd == "/ban":
            if args:
                self.frame.BanUser(args)

        elif cmd == "/ignore":
            if args:
                self.frame.IgnoreUser(args)

        elif cmd == "/ignoreip":
            if args:
                self.frame.IgnoreIP(args)

        elif cmd == "/unban":
            if args:
                self.frame.UnbanUser(args)

        elif cmd == "/unignore":
            if args:
                self.frame.UnignoreUser(args)

        elif cmd == "/ctcpversion":
            if args:
                self.frame.privatechats.SendMessage(args, CTCP_VERSION, 1, bytestring=True)

        elif cmd in ["/clear", "/cl"]:
            self.ChatScroll.get_buffer().set_text("")

        elif cmd in ["/a", "/away"]:
            self.frame.OnAway(None)

        elif cmd in ["/q", "/quit", "/exit"]:
            self.frame.OnExit(None)
            return

        elif cmd in ["/c", "/close"]:
            self.OnClose(None)

        elif cmd == "/now":
            self.NowPlayingThread()

        elif cmd == "/detach":
            self.Detach()

        elif cmd == "/attach":
            self.Attach()

        elif cmd == "/rescan":
            self.frame.OnRescan()

        elif cmd[:1] == "/" and self.frame.pluginhandler.TriggerPrivateCommandEvent(self.user, cmd[1:], args):
            pass

        elif cmd and cmd[:1] == "/" and cmd != "/me" and cmd[:2] != "//":
            self.frame.logMessage(_("Command %s is not recognized") % text)
            return

        else:

            if text[:2] == "//":
                text = text[1:]

            if self.chats.connected:
                self.SendMessage(text)
                widget.set_text("")

            return

        widget.set_text("")

    def Attach(self, widget=None):
        self.chats.attach_tab(self.Main)
        gobject.idle_add(self.frame.ScrollBottom, self.ChatScroll.get_parent())

    def Detach(self, widget=None):
        self.chats.detach_tab(
            self.Main,
            _("Nicotine+ Private Chat: %(user)s (%(status)s)") % {
                'user': self.user,
                'status': [_("Offline"), _("Away"), _("Online")][self.status]
            }
        )
        gobject.idle_add(self.frame.ScrollBottom, self.ChatScroll.get_parent())

    def NowPlayingThread(self):
        np = self.frame.now.DisplayNowPlaying(None, 0, self.SendMessage)  # noqa: F841

    def makecolour(self, buffer, colour):

        color = self.frame.np.config.sections["ui"][colour]
        if color == "":
            color = Gdk.color_parse(self.backupcolor)
        else:
            color = Gdk.color_parse(color)

        font = self.frame.np.config.sections["ui"]["chatfont"]
        tag = buffer.create_tag()
        tag.set_property("foreground-gdk", color)
        tag.set_property("font", font)

        return tag

    def UpdateColours(self):

        map = self.frame.MainWindow.get_style().copy()

        try:
            self.backupcolor = map.text[gtk.StateFlags.NORMAL]
        except IndexError:
            self.backupcolor = ''

        buffer = self.ChatScroll.get_buffer()
        self.tag_remote = self.makecolour(buffer, "chatremote")
        self.tag_local = self.makecolour(buffer, "chatlocal")
        self.tag_me = self.makecolour(buffer, "chatme")
        self.tag_hilite = self.makecolour(buffer, "chathilite")

        if self.status == 1 and self.frame.np.config.sections["ui"]["showaway"]:
            statuscolor = "useraway"
        elif self.status == 2 or not self.frame.np.config.sections["ui"]["showaway"] and self.status == 1:
            statuscolor = "useronline"
        else:
            statuscolor = "useroffline"

        self.tag_username = self.makecolour(buffer, statuscolor)

        if self.chats.connected:
            if self.frame.away and self.frame.np.config.sections["ui"]["showaway"]:
                self.tag_my_username = self.makecolour(buffer, "useraway")
            else:
                self.tag_my_username = self.makecolour(buffer, "useronline")
        else:
            self.tag_my_username = self.makecolour(buffer, "useroffline")

        usernamestyle = self.frame.np.config.sections["ui"]["usernamestyle"]

        if usernamestyle == "bold":
            self.tag_username.set_property("weight", pango.Weight.BOLD)
            self.tag_my_username.set_property("weight", pango.Weight.BOLD)
        else:
            self.tag_username.set_property("weight", pango.Weight.NORMAL)
            self.tag_my_username.set_property("weight", pango.Weight.NORMAL)

        if usernamestyle == "italic":
            self.tag_username.set_property("style", pango.Style.ITALIC)
            self.tag_my_username.set_property("style", pango.Style.ITALIC)
        else:
            self.tag_username.set_property("style", pango.Style.NORMAL)
            self.tag_my_username.set_property("style", pango.Style.NORMAL)

        if usernamestyle == "underline":
            self.tag_username.set_property("underline", pango.Underline.SINGLE)
            self.tag_my_username.set_property("underline", pango.Underline.SINGLE)
        else:
            self.tag_username.set_property("underline", pango.Underline.NONE)
            self.tag_my_username.set_property("underline", pango.Underline.NONE)

        self.frame.SetTextBG(self.ChatScroll)
        self.frame.SetTextBG(self.ChatLine)
        self.frame.SetTextBG(self.Log)
        self.frame.SetTextBG(self.PeerPrivateMessages)

    def changecolour(self, tag, colour):

        if colour in self.frame.np.config.sections["ui"]:
            color = self.frame.np.config.sections["ui"][colour]
        else:
            color = ""

        font = self.frame.np.config.sections["ui"]["chatfont"]

        if color == "":
            color = self.backupcolor
        else:
            color = Gdk.color_parse(color)

        tag.set_property("foreground-gdk", color)
        tag.set_property("font", font)

        if colour in ["useraway", "useronline", "useroffline"]:

            usernamestyle = self.frame.np.config.sections["ui"]["usernamestyle"]

            if usernamestyle == "bold":
                tag.set_property("weight", pango.Weight.BOLD)
            else:
                tag.set_property("weight", pango.Weight.NORMAL)

            if usernamestyle == "italic":
                tag.set_property("style", pango.Style.ITALIC)
            else:
                tag.set_property("style", pango.Style.NORMAL)

            if usernamestyle == "underline":
                tag.set_property("underline", pango.Underline.SINGLE)
            else:
                tag.set_property("underline", pango.Underline.NONE)

    def ChangeColours(self):

        map = self.ChatScroll.get_style().copy()
        self.backupcolor = map.text[gtk.StateFlags.NORMAL]

        self.changecolour(self.tag_remote, "chatremote")
        self.changecolour(self.tag_local, "chatlocal")
        self.changecolour(self.tag_me, "chatme")
        self.changecolour(self.tag_hilite, "chathilite")

        color = self.getUserStatusColor(self.status)
        self.changecolour(self.tag_username, color)

        if self.chats.connected:
            if self.frame.away and self.frame.np.config.sections["ui"]["showaway"]:
                self.changecolour(self.tag_my_username, "useraway")
            else:
                self.changecolour(self.tag_my_username, "useronline")
        else:
            self.changecolour(self.tag_my_username, "useroffline")

        self.frame.SetTextBG(self.ChatScroll)
        self.frame.SetTextBG(self.ChatLine)

    def getUserStatusColor(self, status):

        if status == 1:
            color = "useraway"
        elif status == 2:
            color = "useronline"
        else:
            color = "useroffline"

        if not self.frame.np.config.sections["ui"]["showaway"] and color == "useraway":
            color = "useronline"

        return color

    def GetUserStatus(self, status):

        if status == self.status:
            return

        self.status = status
        color = self.getUserStatusColor(self.status)
        self.changecolour(self.tag_username, color)
        statusword = [_("Offline"), _("Away"), _("Online")][status]
        title = _("Nicotine+ Private Chat: %(user)s (%(status)s)") % {'user': self.user, 'status': statusword}
        self.chats.set_detached_tab_title(self.Main, title)

    def OnClose(self, widget):

        self.chats.RemoveTab(self)

    def GetCompletionList(self, ix=0, text="", clist=[]):

        config = self.frame.np.config.sections["words"]

        completion = self.ChatLine.get_completion()
        completion.set_popup_single_match(not config["onematch"])
        completion.set_minimum_key_length(config["characters"])

        liststore = completion.get_model()
        liststore.clear()

        self.clist = []

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

    def OnKeyPress(self, widget, event):

        if event.keyval == Gdk.keyval_from_name("Prior"):

            scrolled = self.ChatScroll.get_parent()
            adj = scrolled.get_vadjustment()
            adj.set_value(adj.value - adj.page_increment)

        elif event.keyval == Gdk.keyval_from_name("Next"):

            scrolled = self.ChatScroll.get_parent()
            adj = scrolled.get_vadjustment()
            max = adj.upper - adj.page_size
            new = adj.value + adj.page_increment

            if new > max:
                new = max

            adj.set_value(new)

        if event.keyval != Gdk.keyval_from_name("Tab"):
            return False

        config = self.frame.np.config.sections["words"]
        if not config["tab"]:
            return False

        ix = widget.get_position()
        text = widget.get_text()[:ix].split(" ")[-1]
        preix = ix - len(text)

        completion, single = GetCompletion(text, self.chats.clist)

        if completion:
            widget.delete_text(preix, ix)
            widget.insert_text(completion, ix)
            widget.set_position(preix + len(completion))

        widget.emit_stop_by_name("key_press_event")

        return True

    def OnEncodingChanged(self, widget):

        encoding = self.Encoding.get_model().get(self.Encoding.get_active_iter(), 0)[0]

        if encoding != self.encoding:
            self.encoding = encoding
            SaveEncoding(self.frame.np, "userencoding", self.user, self.encoding)
