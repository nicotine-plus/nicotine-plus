# Copyright (C) 2007 daelstorm. All rights reserved.
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
#
# Original copyright below
# Copyright (c) 2003-2004 Hyriand. All rights reserved.

import os
import gtk, gobject, pango
import sets
from nicotine_glade import PrivateChatTab
from utils import AppendLine, IconNotebook, PopupMenu, WriteLog, expand_alias, is_alias, EncodingsMenu, SaveEncoding, fixpath
from chatrooms import GetCompletion
from pynicotine import slskmessages
from pynicotine.utils import _, version

class PrivateChats(IconNotebook):
	def __init__(self, frame):
		ui = frame.np.config.sections["ui"]
		IconNotebook.__init__(self, frame.images, ui["labelprivate"], ui["tabclosers"])
		self.popup_enable()

		self.frame = frame
		self.connected = 1
		self.users = {}
		self.connect("switch-page", self.OnSwitchPage)

	def OnSwitchPage(self, notebook, page, page_num, force = 0):
		if self.frame.MainNotebook.get_current_page() != 1 and not force:
			return
		page = notebook.get_nth_page(page_num)
		
		for user, tab in self.users.items():
			if tab.Main == page:
				gobject.idle_add(tab.ChatLine.grab_focus)
				# Remove hilite if selected tab belongs to a user in the hilite list
				if user in self.frame.TrayApp.tray_status["hilites"]["private"]:
					self.frame.ClearNotification("private", tab.user)
					
	def ClearNotifications(self):
		if self.frame.MainNotebook.get_current_page() != 1:
			return
		page = self.frame.PrivatechatNotebook.get_nth_page( self.frame.PrivatechatNotebook.get_current_page())
		for user, tab in self.users.items():
			if tab.Main == page:
				# Remove hilite
				if user in self.frame.TrayApp.tray_status["hilites"]["private"]:
					self.frame.ClearNotification("private", tab.user)
					
	def GetUserStatus(self, msg):
		if msg.user in self.users:
			tab = self.users[msg.user]
			status = [_("Offline"), _("Away"), _("Online")][msg.status]
			self.set_text(tab.Main, "%s (%s)" % (msg.user[:15], status))
			tab.GetUserStatus(msg.status)

	def SendMessage(self, user, text = None, direction = None):
		if user not in self.users:
			tab = PrivateChat(self, user)
			self.users[user] = tab
			self.append_page(tab.Main, user, tab.OnClose)
			if user not in self.frame.np.watchedusers:
				self.frame.np.queue.put(slskmessages.AddUser(user))
			self.frame.np.queue.put(slskmessages.GetUserStatus(user))
		if direction:
			if self.get_current_page() != self.page_num(self.users[user].Main):
				self.set_current_page(self.page_num(self.users[user].Main))
		if text is not None:
			self.users[user].SendMessage(text)
	
	def TabPopup(self, user):
		popup = PopupMenu(self.frame)
		popup.setup(
			("#" + _("Show IP a_ddress"), popup.OnShowIPaddress, gtk.STOCK_NETWORK),
			("#" + _("Get user i_nfo"), popup.OnGetUserInfo, gtk.STOCK_DIALOG_INFO),
			("#" + _("Brow_se files"), popup.OnBrowseUser, gtk.STOCK_HARDDISK),
			("#" + _("Gi_ve privileges"), popup.OnGivePrivileges, gtk.STOCK_JUMP_TO),
			("#" + _("Client Version"), popup.OnVersion, gtk.STOCK_ABOUT ),
			("", None),
			("$" + _("Add user to list"), popup.OnAddToList),
			("$" + _("Ban this user"), popup.OnBanUser),
			("$" + _("Ignore this user"), popup.OnIgnoreUser),
		)
		popup.set_user(user)
		
		items = popup.get_children()
		
		items[6].set_active(user in [i[0] for i in self.frame.np.config.sections["server"]["userlist"]])
		items[7].set_active(user in self.frame.np.config.sections["server"]["banlist"])
		items[8].set_active(user in self.frame.np.config.sections["server"]["ignorelist"])
	
		return popup
		
	def on_tab_click(self, widget, event, child):
		if event.type == gtk.gdk.BUTTON_PRESS:
			n = self.page_num(child)
			page = self.get_nth_page(n)
			username =  [user for user, tab in self.users.items() if tab.Main is page][0]
			if event.button == 3:
				menu = self.TabPopup(username)
				menu.popup(None, None, None, event.button, event.time)
			else:
				self.set_current_page(n)
			return True
		return False
			
	def ShowMessage(self, msg, text, status=None):
		if msg.user in self.frame.np.config.sections["server"]["ignorelist"]:
			return

		
		self.SendMessage(msg.user, None)
		self.request_changed(self.users[msg.user].Main)
		self.frame.RequestIcon(self.frame.PrivateChatTabLabel)
		if self.get_current_page() != self.page_num(self.users[msg.user].Main) or self.frame.MainNotebook.get_current_page() != 1 or not self.frame.is_mapped:
			self.frame.Notification("private", msg.user)
		self.users[msg.user].ShowMessage(text, status, msg.timestamp)
		ctcpversion = 0
		if text == "\x01VERSION\x01":
			ctcpversion = 1
			text = "CTCP VERSION"
		if ctcpversion and self.frame.np.config.sections["server"]["ctcpmsgs"] == 0:
			self.SendMessage(msg.user, "Nicotine-Plus %s" % version)
		
		
		#else:
			#self.frame.MainWindow.set_urgency_hint(False)

	def UpdateColours(self):
		for chat in self.users.values():
			chat.ChangeColours()

	def RemoveTab(self, tab):
		self.remove_page(tab.Main)
		if tab.user in self.frame.TrayApp.tray_status["hilites"]["private"]:
			self.frame.ClearNotification("private", tab.user)
		del self.users[tab.user]
		if tab.user in self.frame.np.config.sections["privatechat"]["users"]:
			self.frame.np.config.sections["privatechat"]["users"].remove(tab.user)

	def Login(self):
		self.connected = 1
		for user in self.users:
			self.users[user].Login()
			
		if self.frame.np.config.sections["privatechat"]["store"]:
			self.frame.np.config.sections["privatechat"]["users"].sort()
			for user in self.frame.np.config.sections["privatechat"]["users"]:
				if user not in self.users.keys():
					self.SendMessage(user, None, 1)
					
	def ConnClose(self):
		self.connected = 0
		for user in self.users:
			self.users[user].ConnClose()
			tab = self.users[user]
			status = _("Offline")
			self.set_text(tab.Main, "%s (%s)" % (user[:15], status))
			tab.GetUserStatus(status)
			
	def UpdateCompletions(self):
		for user in self.users.values():
			user.GetCompletionList()
			
class PrivateChat(PrivateChatTab):
	def __init__(self, chats, user):
		PrivateChatTab.__init__(self, False)
		
		self.user = user
		self.chats = chats
		self.frame = chats.frame
		self.logfile = None
		self.autoreplied = 0
		self.offlinemessage = 0
		self.status = -1
		self.clist = []
		self.Elist = {}
		self.encoding, m = EncodingsMenu(self.frame.np, "userencoding", user)
		self.EncodingStore = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
		self.Encoding.set_size_request(100, -1)
		self.Encoding.set_model(self.EncodingStore)
		cell2 = gtk.CellRendererText()
		self.Encoding.pack_start(cell2, False)
		self.Encoding.add_attribute(cell2, 'text', 1)
		for item in m:
			self.Elist[item[1]] = self.EncodingStore.append([item[1], item[0] ])
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
			self.hbox5.pack_start(self.ChatLine)
			self.hbox5.reorder_child(self.ChatLine, 0)
			
		completion = gtk.EntryCompletion()
		self.ChatLine.set_completion(completion)
		liststore = gtk.ListStore(gobject.TYPE_STRING)
		completion.set_model(liststore)
		
		completion.set_text_column(0)
		completion.set_match_func(self.frame.EntryCompletionFindMatch, self.ChatLine)
		completion.connect("match-selected", self.frame.EntryCompletionFoundMatch, self.ChatLine)
		
		self.Log.set_active(self.frame.np.config.sections["logging"]["privatechat"])

		if self.frame.translux:
			self.tlux_chat = lambda: self.ChatScroll.get_window(gtk.TEXT_WINDOW_TEXT)
			self.frame.translux.subscribe(self.ChatScroll, self.tlux_chat)
			self.ChatScroll.get_parent().get_vadjustment().connect("value-changed", lambda *args: self.ChatScroll.queue_draw())
			self.ChatScroll.get_parent().get_hadjustment().connect("value-changed", lambda *args: self.ChatScroll.queue_draw())
		
		self.popup_menu_user = popup = PopupMenu(self.frame)
		popup.setup(
			("#" + _("Show IP a_ddress"), popup.OnShowIPaddress, gtk.STOCK_NETWORK),
			("#" + _("Get user i_nfo"), popup.OnGetUserInfo, gtk.STOCK_DIALOG_INFO),
			("#" + _("Brow_se files"), popup.OnBrowseUser, gtk.STOCK_HARDDISK),
			("#" + _("Gi_ve privileges"), popup.OnGivePrivileges, gtk.STOCK_JUMP_TO),
			("#" + _("Client Version"), popup.OnVersion, gtk.STOCK_ABOUT ),
			("", None),
			("$" + _("Add user to list"), popup.OnAddToList),
			("$" + _("Ban this user"), popup.OnBanUser),
			("$" + _("Ignore this user"), popup.OnIgnoreUser),
		)
		popup.set_user(user)
		self.popup_menu = popup = PopupMenu(self.frame)
		popup.setup(
			("USERMENU", _("User"), self.popup_menu_user, self.OnPopupMenuUser),
			("", None),
			("#" + _("Find"), self.OnFindChatLog, gtk.STOCK_FIND),
			("", None),
			("#" + _("Copy"), self.OnCopyChatLog, gtk.STOCK_COPY),
			("#" + _("Copy All"), self.OnCopyAllChatLog, gtk.STOCK_COPY),
			("", None),
			("#" + _("Clear log"), self.OnClearChatLog, gtk.STOCK_CLEAR),
			("", None),
			("#" + _("Close"), self.OnClose, gtk.STOCK_CANCEL),
			
			
		)
		popup.set_user(user)
		self.ChatScroll.connect("button_press_event", self.OnPopupMenu)
		self.ChatScroll.connect("key_press_event", self.OnPopupMenu)

		self.UpdateColours()
		
		# Read log file
		log = os.path.join(self.frame.np.config.sections["logging"]["privatelogsdir"], fixpath(self.user.replace(os.sep, "-")) + ".log")
		try:
			f = open(log, "r")
			d = f.read()
			f.close()
			s = d.split("\n")
			for l in s[-8:-1]:
				AppendLine(self.ChatScroll, l + "\n", self.tag_hilite, timestamp_format="", username=self.user, usertag=self.tag_hilite)
				
		except IOError, e:
			pass
		self.GetCompletionList()
		
	def destroy(self):
		if self.frame.translux:
			self.frame.translux.unsubscribe(self.tlux_chat)
		self.Main.destroy()
		
	def Login(self):
		timestamp_format=self.frame.np.config.sections["logging"]["private_timestamp"]
		AppendLine(self.ChatScroll, _("--- reconnected ---"), self.tag_hilite, timestamp_format=timestamp_format)
		self.ChangeColours()
		
	def ConnClose(self):
		timestamp_format=self.frame.np.config.sections["logging"]["private_timestamp"]
		AppendLine(self.ChatScroll, _("--- disconnected ---"), self.tag_hilite, timestamp_format=timestamp_format)
		self.status = -1
		self.offlinemessage = 0
		self.ChangeColours()
		
	def OnPopupMenu(self, widget, event):
		if event.type == gtk.gdk.BUTTON_PRESS and event.button == 3:

			self.popup_menu.popup(None, None, None, event.button, event.time)
			self.ChatScroll.emit_stop_by_name("button_press_event")
			return True
		elif event.type == gtk.gdk.KEY_PRESS:

			if event.keyval == gtk.gdk.keyval_from_name("Menu"):
				self.popup_menu.popup(None, None, None, 0, 0)
				self.ChatScroll.emit_stop_by_name("key_press_event")
				return True

		return False
	
	def OnPopupMenuUser(self, widget):
		items = self.popup_menu_user.get_children()
		
		items[6].set_active(self.user in [i[0] for i in self.frame.np.config.sections["server"]["userlist"]])
		items[7].set_active(self.user in self.frame.np.config.sections["server"]["banlist"])
		items[8].set_active(self.user in self.frame.np.config.sections["server"]["ignorelist"])
	
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
		if text[:4] == "/me ":
			line = "* %s %s" % (self.user, self.frame.CensorChat(text[4:]))
			speech = line[2:]
			tag = self.tag_me
		else:
			line = "[%s] %s" % (self.user, self.frame.CensorChat(text))
			speech = self.frame.CensorChat(text)
			tag = self.tag_remote
		line = self.frame.np.decode(line, self.encoding)
		timestamp_format=self.frame.np.config.sections["logging"]["private_timestamp"]
		AppendLine(self.ChatScroll, line, tag, timestamp=timestamp, timestamp_format=timestamp_format, username=self.user, usertag=self.tag_username)
		if self.Log.get_active():
			self.logfile = WriteLog(self.logfile, self.frame.np.config.sections["logging"]["privatelogsdir"], self.user, line)
		
		autoreply = self.frame.np.config.sections["server"]["autoreply"]
		if self.frame.away and not self.autoreplied and autoreply:
			self.SendMessage("[Auto-Message] %s" % autoreply)
			self.autoreplied = 1
		if status and not self.offlinemessage:
			
			AppendLine(self.ChatScroll, _("* Message(s) sent while you were offline."), self.tag_hilite, timestamp_format=timestamp_format)
			self.offlinemessage = 1
		self.frame.new_tts(self.frame.np.config.sections["ui"]["speechprivate"] %(self.frame.tts_clean(self.user), self.frame.tts_clean(speech)) )

	def SendMessage(self, text):
		my_username = self.frame.np.config.sections["server"]["login"]
		if text[:4] == "/me ":
			line = "* %s %s" % (my_username, text[4:])
			usertag = tag = self.tag_me
			message = self.frame.np.decode(line, self.encoding)
		else:
			
			if text == "\x01VERSION\x01":
				line = "CTCP VERSION"
			else:
				line = text
			tag = self.tag_local
			usertag = self.tag_my_username
			message = "[" + my_username + "] " + self.frame.np.decode(line, self.encoding)
		timestamp_format=self.frame.np.config.sections["logging"]["private_timestamp"]
		AppendLine(self.ChatScroll, message, tag, timestamp_format=timestamp_format, username=my_username, usertag=usertag)
		if self.Log.get_active():
			self.logfile = WriteLog(self.logfile, self.frame.np.config.sections["logging"]["privatelogsdir"], self.user, message)
		
		if self.PeerPrivateMessages.get_active():
			# not in the soulseek protocol
			self.frame.np.ProcessRequestToPeer(self.user, slskmessages.PMessageUser(None, my_username, self.frame.AutoReplace(text)))
		else:
			self.frame.np.queue.put(slskmessages.MessageUser(self.user, self.frame.AutoReplace(text)))
			
	CMDS = ["/alias ", "/unalias ", "/whois ", "/browse ", "/ip ", "/pm ", "/msg ", "/search ", "/usearch ", "/rsearch ",
		"/bsearch ", "/add ", "/buddy ", "/rem ", "/unbuddy ", "/ban ", "/ignore ", "/unban ", "/unignore ", "/clear", "/quit", "/rescan", "/nsa", "/info", "/ctcpversion", "/join"]

		
	def threadAlias(self, alias):
		text = expand_alias(self.frame.np.config.aliases, alias)
		if not text:
			return
		if text[:2] == "//":
			text = text[1:]
		self.frame.np.queue.put(slskmessages.SayChatroom(self.room, self.frame.AutoReplace(text)))

			
	def OnEnter(self, widget):
		text = self.frame.np.encode(widget.get_text(), self.encoding)

		if not text:
			widget.set_text("")
			return
		if is_alias(self.frame.np.config.aliases, text):
			import thread
			thread.start_new_thread(self.threadAlias, (text,))
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
				self.frame.np.queue.put(slskmessages.GetPeerAddress(args))
		elif cmd == "/nsa":
			if args:
				self.frame.LocalUserInfoRequest(args)
				self.frame.BrowseUser(args)
				self.frame.OnUserInfo(None)
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
				self.frame.searches.DoSearch(realargs, 0)
				self.frame.OnSearch(None)
		elif cmd in ["/us", "/usearch"]:
			if realargs:
				self.frame.searches.DoSearch(realargs, 3, [self.user])
				self.frame.OnSearch(None)
		elif cmd in ["/rs", "/rsearch"]:
			if realargs:
				self.frame.searches.DoSearch(realargs, 1)
				self.frame.OnSearch(None)
		elif cmd in ["/bs", "/bsearch"]:
			if realargs:
				self.frame.searches.DoSearch(realargs, 2)
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
		elif cmd == "/unban":
			if args:
				self.frame.UnbanUser(args)
		elif cmd == "/unignore":
			if args:
				self.frame.UnignoreUser(args)
		elif cmd == "/ctcpversion":
			if args:
				self.frame.privatechats.SendMessage(args, "\x01VERSION\x01", 1)
		elif cmd in ["/clear", "/cl"]:
			self.ChatScroll.get_buffer().set_text("")
		elif cmd in ["/a", "/away"]:
			self.frame.OnAway(None)
		elif cmd in ["/q", "/quit"]:
			self.frame.OnExit(None)
		elif cmd in ["/c", "/close"]:
			self.OnClose(None)
		elif cmd == "/now":
			import thread
			thread.start_new_thread(self.NowPlayingThread, ())
		elif cmd == "/rescan":
			self.frame.OnRescan()
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

	def NowPlayingThread(self):
		np = self.frame.now.DisplayNowPlaying(None)
		if np:
			self.SendMessage(np)
			
	def makecolour(self, buffer, colour):
		color = self.frame.np.config.sections["ui"][colour]
		if color == "":
			color = self.backupcolor
		else:
			color = gtk.gdk.color_parse(color)
		
		font = self.frame.np.config.sections["ui"]["chatfont"]
		tag = buffer.create_tag()
		tag.set_property("foreground-gdk", color)
		tag.set_property("font", font)
		return tag
		
	def UpdateColours(self):
		map = self.frame.MainWindow.get_style().copy()
		self.backupcolor = map.text[gtk.STATE_NORMAL]

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
			self.tag_username.set_property("weight",  pango.WEIGHT_BOLD)
			self.tag_my_username.set_property("weight",  pango.WEIGHT_BOLD)
		else:
			self.tag_username.set_property("weight",  pango.WEIGHT_NORMAL)
			self.tag_my_username.set_property("weight",  pango.WEIGHT_NORMAL)
		if usernamestyle == "italic":
			self.tag_username.set_property("style",  pango.STYLE_ITALIC)
			self.tag_my_username.set_property("style",  pango.STYLE_ITALIC)
		else:
			self.tag_username.set_property("style",  pango.STYLE_NORMAL)
			self.tag_my_username.set_property("style",  pango.STYLE_NORMAL)
		if usernamestyle == "underline":
			self.tag_username.set_property("underline", pango.UNDERLINE_SINGLE)
			self.tag_my_username.set_property("underline", pango.UNDERLINE_SINGLE)
		else:
			self.tag_username.set_property("underline", pango.UNDERLINE_NONE)
			self.tag_my_username.set_property("underline", pango.UNDERLINE_NONE)
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
			color = gtk.gdk.color_parse(color)
		tag.set_property("foreground-gdk", color)
		tag.set_property("font", font)
		if colour in ["useraway", "useronline", "useroffline"]:
			usernamestyle = self.frame.np.config.sections["ui"]["usernamestyle"]
			if usernamestyle == "bold":
				tag.set_property("weight",  pango.WEIGHT_BOLD)
			else:
				tag.set_property("weight",  pango.WEIGHT_NORMAL)
			if usernamestyle == "italic":
				tag.set_property("style",  pango.STYLE_ITALIC)
			else:
				tag.set_property("style",  pango.STYLE_NORMAL)
			if usernamestyle == "underline":
				tag.set_property("underline", pango.UNDERLINE_SINGLE)
			else:
				tag.set_property("underline", pango.UNDERLINE_NONE)
	
			
	def ChangeColours(self):
		map = self.ChatScroll.get_style().copy()
		self.backupcolor = map.text[gtk.STATE_NORMAL]
		
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

	
	def OnClose(self, widget):
		if self.logfile is not None:
			self.logfile.close()
			self.logfile = None
		self.chats.RemoveTab(self)
		self.destroy()


	def GetCompletionList(self, ix=0, text=""):
		config = self.frame.np.config.sections["words"]
		completion = self.ChatLine.get_completion()
		completion.set_popup_single_match(not config["onematch"])
		completion.set_minimum_key_length(config["characters"])
		
		liststore = completion.get_model()
		liststore.clear()
		self.clist = []
		
		if not config["tab"]:
			return
		
		clist = [self.user, self.frame.np.config.sections["server"]["login"], "nicotine"]
		if config["buddies"]:
			clist += [i[0] for i in self.frame.userlist.userlist]
		if config["aliases"]:
			clist += ["/"+k for k in self.frame.np.config.aliases.keys()]
		if config["commands"]:
			clist += self.CMDS
		if config["roomnames"]:
			clist += self.frame.chatrooms.roomsctrl.rooms
		
		# no duplicates
		clist = list(sets.Set(clist))
		clist.sort(key=str.lower)
		
		completion.set_popup_completion(False)
		if config["dropdown"]:
			for word in clist:
				liststore.append([word])
		completion.set_popup_completion(True)
		self.clist = clist
	

		
	def OnKeyPress(self, widget, event):
		if event.keyval == gtk.gdk.keyval_from_name("Prior"):
			scrolled = self.ChatScroll.get_parent()
			adj = scrolled.get_vadjustment()
			adj.set_value(adj.value - adj.page_increment)
		elif event.keyval == gtk.gdk.keyval_from_name("Next"):
			scrolled = self.ChatScroll.get_parent()
			adj = scrolled.get_vadjustment()
			max = adj.upper - adj.page_size
			new = adj.value + adj.page_increment
			if new > max:
				new = max
			adj.set_value(new)
		if event.keyval != gtk.gdk.keyval_from_name("Tab"):
			return False
		config = self.frame.np.config.sections["words"]
		if not config["tab"]:
			return False
		ix = widget.get_position()
		text = widget.get_text()[:ix].split(" ")[-1]
		
		if widget.get_text()[:1] == "/":
			self.GetCompletionList(ix, text)
			
		completion, single = GetCompletion(text, self.clist)
		
		if completion:
			widget.insert_text(completion, ix)
			widget.set_position(ix + len(completion))
		widget.emit_stop_by_name("key_press_event")
		return True

	def OnLogToggled(self, widget):
		if not widget.get_active() and self.logfile is not None:
			self.logfile.close()
			self.logfile = None

	def OnEncodingChanged(self, widget):
		try:
			# PyGTK 2.6
			encoding = self.Encoding.get_active_text()
		except:
			# PyGTK 2.4
			iter = self.Encoding.get_active_iter()
			encoding_model = self.Encoding.get_model()
			encoding = encoding_model.get_value(iter, 0)
		if encoding != self.encoding:
			self.encoding = encoding
			SaveEncoding(self.frame.np, "userencoding", self.user, self.encoding)
