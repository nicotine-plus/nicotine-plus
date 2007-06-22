# Copyright (c) 2003-2004 Hyriand. All rights reserved.
#
import os
import gtk, gobject, pango
import sets
from nicotine_glade import PrivateChatTab
from utils import AppendLine, IconNotebook, PopupMenu, WriteLog, expand_alias, EncodingsMenu, SaveEncoding, fixpath
from chatrooms import GetCompletion
from pynicotine import slskmessages
from pynicotine.utils import _, version

class PrivateChats(IconNotebook):
	def __init__(self, frame):
		IconNotebook.__init__(self, frame.images)
		self.popup_enable()
		self.set_tab_pos(gtk.POS_TOP)
		self.frame = frame
		self.connected = 1
		self.users = {}
		self.connect("switch-page", self.OnSwitchPage)

	def OnSwitchPage(self, notebook, page, page_num, force = 0):
		if self.frame.notebook1.get_current_page() != 1 and not force:
			return
		page = notebook.get_nth_page(page_num)
		
		for user, tab in self.users.items():
			if tab.Main == page:
				gobject.idle_add(tab.ChatLine.grab_focus)
				# Remove hilite if selected tab belongs to a user in the hilite list
				if user in self.frame.TrayApp.tray_status["hilites"]["private"]:
					self.frame.ClearNotification("private", tab.user)
		
	def GetUserStatus(self, msg):
		if self.users.has_key(msg.user):
			tab = self.users[msg.user]
			status = [_("Offline"), _("Away"), _("Online")][msg.status]
			self.set_text(tab.Main, "%s (%s)" % (msg.user[:15], status))
			tab.GetUserStatus(msg.status)

	def SendMessage(self, user, text = None, direction = None):
		if not self.users.has_key(user):
			tab = PrivateChat(self, user)
			self.users[user] = tab
			self.append_page(tab.Main, user, tab.OnClose)
			self.frame.np.queue.put(slskmessages.AddUser(user))
			self.frame.np.queue.put(slskmessages.GetUserStatus(user))
		if direction:
			if self.get_current_page() != self.page_num(self.users[user].Main):
				self.set_current_page(self.page_num(self.users[user].Main))
		if text is not None:
			self.users[user].SendMessage(text)
	
	def ShowMessage(self, msg, text, status=None):
		if msg.user in self.frame.np.config.sections["server"]["ignorelist"]:
			return

		ctcpversion = 0
		if text == "\x01VERSION\x01":
			ctcpversion = 1
			text = "CTCP VERSION"
		self.SendMessage(msg.user, None)
		tab = self.users[msg.user]
		tab.ShowMessage(text, status)
		if ctcpversion and self.frame.np.config.sections["server"]["ctcpmsgs"] == 0:
			self.SendMessage(msg.user, "Nicotine-Plus %s" % version)
		self.request_changed(tab.Main)
		self.frame.RequestIcon(self.frame.PrivateChatTabLabel)
		if self.get_current_page() != self.page_num(self.users[msg.user].Main) or self.frame.notebook1.get_current_page() != 1:
			self.frame.Notification("private", msg.user)
		
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

		self.UpdateColours()
		
		# Read log file
		log = os.path.join(self.frame.np.config.sections["logging"]["logsdir"], fixpath(self.user.replace(os.sep, "-")) + ".log")
		try:
			f = open(log, "r")
			d = f.read()
			f.close()
			s = d.split("\n")
			for l in s[-8:-1]:
				AppendLine(self.ChatScroll, l + "\n", self.tag_hilite, "", username=self.user, usertag=self.tag_hilite)
				
		except IOError, e:
			pass

		
	def destroy(self):
		if self.frame.translux:
			self.frame.translux.unsubscribe(self.tlux_chat)
		self.Main.destroy()
		
	def Login(self):
		AppendLine(self.ChatScroll, _("--- reconnected ---"), self.tag_hilite, "%c")
		self.ChangeColours()
	def ConnClose(self):
		AppendLine(self.ChatScroll, _("--- disconnected ---"), self.tag_hilite, "%c")
		self.offlinemessage = 0
		self.ChangeColours()
	def OnPopupMenu(self, widget, event):
		if event.button != 3:
			return
		
		self.popup_menu.popup(None, None, None, event.button, event.time)
		self.ChatScroll.emit_stop_by_name("button_press_event")
		return True
	
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
	
	def ShowMessage(self, text, status=None):
		if text[:4] == "/me ":
			line = "* %s %s" % (self.user, self.frame.CensorChat(text[4:]))
			tag = self.tag_me
		else:
			line = "[%s] %s" % (self.user, self.frame.CensorChat(text))
			tag = self.tag_remote
		line = self.frame.np.decode(line, self.encoding)
		AppendLine(self.ChatScroll, line, tag, "%c", username=self.user, usertag=self.tag_my_username)
		if self.Log.get_active():
			self.logfile = WriteLog(self.logfile, self.frame.np.config.sections["logging"]["logsdir"], self.user, line)
		
		autoreply = self.frame.np.config.sections["server"]["autoreply"]
		if self.frame.away and not self.autoreplied and autoreply:
			self.SendMessage("[Auto-Message] %s" % autoreply)
			self.autoreplied = 1
		if status and not self.offlinemessage:
			AppendLine(self.ChatScroll, _("* Message(s) sent while you were offline."), self.tag_hilite, "%c")
			self.offlinemessage = 1
			

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
		
		AppendLine(self.ChatScroll, message, tag, "%c", username=my_username, usertag=usertag)
		if self.Log.get_active():
			self.logfile = WriteLog(self.logfile, self.frame.np.config.sections["logging"]["logsdir"], self.user, message)
		
		if self.PeerPrivateMessages.get_active():
			# not in the soulseek protocol
			self.frame.np.ProcessRequestToPeer(self.user, slskmessages.PMessageUser(None, my_username, self.frame.AutoReplace(text)))
		else:
			self.frame.np.queue.put(slskmessages.MessageUser(self.user, self.frame.AutoReplace(text)))
			
	CMDS = ["/alias ", "/unalias ", "/whois ", "/browse ", "/ip ", "/pm ", "/msg ", "/search ", "/usearch ", "/rsearch ",
		"/bsearch ", "/add ", "/buddy ", "/rem ", "/unbuddy ", "/ban ", "/ignore ", "/unban ", "/unignore ", "/clear", "/quit", "/rescan", "/nsa", "/info", "/ctcpversion", "/join"]

	def OnEnter(self, widget):
		text = self.frame.np.encode(widget.get_text(), self.encoding)
		result = expand_alias(self.frame.np.config.aliases, text)
		if result is not None:
			text = result
		if not text:
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
		elif cmd in ("/unalias", "/un"):
			AppendLine(self.ChatScroll, self.frame.np.config.Unalias(realargs), None, "")
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
			np = self.frame.now.DisplayNowPlaying(None)
			if np:
				self.SendMessage(np)
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
		if self.status == 1:
			statuscolor = "useraway"
		elif self.status == 2:
			statuscolor = "useronline"
		else:
			statuscolor = "useroffline"
		if self.chats.connected:
			if self.frame.away:
				self.tag_my_username = self.makecolour(buffer, "useraway")
			else:
				self.tag_my_username = self.makecolour(buffer, "useronline")
		else:
			self.tag_my_username = self.makecolour(buffer, "useroffline")
		self.tag_username = self.makecolour(buffer, statuscolor)
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
		
	def changecolour(self, tag, colour):
		if self.frame.np.config.sections["ui"].has_key(colour):
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
		self.frame.SetTextBG(self.ChatScroll)
		self.frame.SetTextBG(self.ChatLine)
		
		if self.chats.connected:
			if self.frame.away:
				self.changecolour(self.tag_my_username, "useraway")
			else:
				self.changecolour(self.tag_my_username, "useronline")
		else:
			self.changecolour(self.tag_my_username, "useroffline")
	def getUserStatusColor(self, status):
		if status == 1:
			color = "useraway"
		elif status == 2:
			color = "useronline"
		else:
			color = "useroffline"
		return color
		
	def GetUserStatus(self, status):
		if status == self.status:
			return
		
		
		self.status = status

		color = self.getUserStatusColor(self.status)

		self.changecolour(self.tag_username, color)
		
		#line = "* " + ["User %s is offline", "User %s is away", "User %s is online"][status] % self.user
		#AppendLine(self.ChatScroll, line, self.tag_hilite, "%c")
	
	def OnClose(self, widget):
		if self.logfile is not None:
			self.logfile.close()
			self.logfile = None
		self.chats.RemoveTab(self)
		self.destroy()


	def GetCompletionList(self, ix=0, text="", widget=None):
		clist = [self.user, self.frame.np.config.sections["server"]["login"], "nicotine"]+ [i[0] for i in self.frame.userlist.userlist]
		if ix == len(text) and text[:1] == "/":
			clist += ["/"+k for k in self.frame.np.config.aliases.keys()] + self.CMDS
		clist = list(sets.Set(clist))
		clist.sort(key=str.lower)
		
		completion = widget.get_completion()
		liststore = completion.get_model()
		liststore.clear()
		for word in clist:
			liststore.append([word])
			
		return clist
		
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
		ix = widget.get_position()
		text = widget.get_text()[:ix].split(" ")[-1]
		
		self.clist = self.GetCompletionList(ix, text, widget=self.ChatLine)
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
