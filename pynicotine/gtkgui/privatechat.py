# Copyright (c) 2003-2004 Hyriand. All rights reserved.
#
import gtk
import gobject
import os

from nicotine_glade import PrivateChatTab
from utils import AppendLine, IconNotebook, PopupMenu, WriteLog, expand_alias, EncodingsMenu, SaveEncoding
from chatrooms import GetCompletion
from pynicotine import slskmessages

from pynicotine.utils import _, version

class PrivateChats(IconNotebook):
	def __init__(self, frame):
		IconNotebook.__init__(self, frame.images)
		self.popup_enable()
		self.set_tab_pos(gtk.POS_TOP)
		self.frame = frame
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
				if user in self.frame.tray_status["hilites"]["private"]:
					self.frame.tray_status["hilites"]["private"].remove(user)
					self.frame.load_image(None)
		
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
			self.frame.np.queue.put(slskmessages.GetUserStatus(user))
		if direction:
			if self.get_current_page() != self.page_num(self.users[user].Main):
				self.set_current_page(self.page_num(self.users[user].Main))
		if text is not None:
			self.users[user].SendMessage(text)
	
	def ShowMessage(self, msg, text):
		if msg.user in self.frame.np.config.sections["server"]["ignorelist"]:
			return

		ctcpversion = 0
		if text == "\x01VERSION\x01":
			ctcpversion = 1
			text = "CTCP VERSION"
		self.SendMessage(msg.user, None)
		tab = self.users[msg.user]
		tab.ShowMessage(text)
		if ctcpversion and self.frame.np.config.sections["server"]["ctcpmsgs"] == 0:
			self.SendMessage(msg.user, "Nicotine %s" % version)
		self.request_changed(tab.Main)
		self.frame.RequestIcon(self.frame.PrivateChatTabLabel)
		if self.get_current_page() != self.page_num(self.users[msg.user].Main) or self.frame.notebook1.get_current_page() != 1:
			if msg.user not in self.frame.tray_status["hilites"]["private"]:
				self.frame.tray_status["hilites"]["private"].append(msg.user)
				self.frame.load_image(None)

	def UpdateColours(self):
		for chat in self.users.values():
			chat.UpdateColours()

	def RemoveTab(self, tab):
		self.remove_page(tab.Main)
		del self.users[tab.user]
	
class PrivateChat(PrivateChatTab):
	def __init__(self, chats, user):
		PrivateChatTab.__init__(self, False)
		
		self.user = user
		self.chats = chats
		self.frame = chats.frame
		self.logfile = None
		self.autoreplied = 0
		self.status = -1

		self.encoding, m = EncodingsMenu(self.frame.np, "userencoding", user)
		for item in m:
			self.Encoding.append_text(item)
		if self.encoding in m:
			self.Encoding.set_active(m.index(self.encoding))
		
		self.Log.set_active(self.frame.np.config.sections["logging"]["privatechat"])

		self.UpdateColours()

		if self.frame.translux:
			self.tlux_chat = lambda: self.ChatScroll.get_window(gtk.TEXT_WINDOW_TEXT)
			self.frame.translux.subscribe(self.ChatScroll, self.tlux_chat)
			self.ChatScroll.get_parent().get_vadjustment().connect("value-changed", lambda *args: self.ChatScroll.queue_draw())
			self.ChatScroll.get_parent().get_hadjustment().connect("value-changed", lambda *args: self.ChatScroll.queue_draw())

		self.popup_menu = popup = PopupMenu(self.frame)
		popup.setup(
			(_("Close"), self.OnClose),
			("", None),
			(_("Show IP address"), popup.OnShowIPaddress),
			(_("Get user info"), popup.OnGetUserInfo),
			(_("Browse files"), popup.OnBrowseUser),
			(_("Give privileges"), popup.OnGivePrivileges),
			("$" + _("Add user to list"), popup.OnAddToList),
			("$" + _("Ban this user"), popup.OnBanUser),
			("$" + _("Ignore this user"), popup.OnIgnoreUser),
			(_("Client Version"), popup.OnVersion ),
		)
		popup.set_user(user)
		self.ChatScroll.connect("button_press_event", self.OnPopupMenu)

		log = os.path.join(self.frame.np.config.sections["logging"]["logsdir"], self.user.replace(os.sep, "-") + ".log")
		try:
			f = open(log, "r")
			d = f.read()
			f.close()
			s = d.split("\n")
			for l in s[-8:-1]:
				AppendLine(self.ChatScroll, l + "\n", self.tag_hilite, "")
		except IOError, e:
			pass

				
	def destroy(self):
		if self.frame.translux:
			self.frame.translux.unsubscribe(self.tlux_chat)
		self.Main.destroy()

	def OnPopupMenu(self, widget, event):
		if event.button != 3:
			return
		items = self.popup_menu.get_children()
		items[6].set_active(self.user in [i[0] for i in self.frame.np.config.sections["server"]["userlist"]])
		items[7].set_active(self.user in self.frame.np.config.sections["server"]["banlist"])
		items[8].set_active(self.user in self.frame.np.config.sections["server"]["ignorelist"])
		self.popup_menu.popup(None, None, None, event.button, event.time)
		self.ChatScroll.emit_stop_by_name("button_press_event")
		return True

	def ShowMessage(self, text):
		if text[:4] == "/me ":
			line = "* %s %s" % (self.user, text[4:])
			tag = self.tag_me
		else:
			line = "[%s] %s" % (self.user, text)
			tag = self.tag_remote
		line = self.frame.np.decode(line, self.encoding)
		AppendLine(self.ChatScroll, line, tag, "%c")
		if self.Log.get_active():
			self.logfile = WriteLog(self.logfile, self.frame.np.config.sections["logging"]["logsdir"], self.user, line)
		
		autoreply = self.frame.np.config.sections["server"]["autoreply"]
		if self.frame.away and not self.autoreplied and autoreply:
			self.SendMessage("[Auto-Message] %s" % autoreply)
			self.autoreplied = 1

	def SendMessage(self, text):

		if text[:4] == "/me ":
			line = "* %s %s" % (self.frame.np.config.sections["server"]["login"], text[4:])
			tag = self.tag_me
		else:
			
			if text == "\x01VERSION\x01":
				line = "CTCP VERSION"
			else:
				line = text
			tag = self.tag_local
			
		AppendLine(self.ChatScroll, self.frame.np.decode(line, self.encoding), tag, "%c")
		if self.Log.get_active():
			self.logfile = WriteLog(self.logfile, self.frame.np.config.sections["logging"]["logsdir"], self.user, line)
		self.frame.np.queue.put(slskmessages.MessageUser(self.user, text))
	
	CMDS = ["/alias ", "/unalias ", "/whois ", "/browse ", "/ip ", "/pm ", "/msg ", "/search ", "/usearch ", "/rsearch ",
		"/bsearch ", "/add ", "/ban ", "/ignore ", "/unban ", "/unignore ", "/clear", "/quit", "/rescan", "/nsa", "/info", "/ctcpversion"]

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
		elif cmd in ["/ad", "/add"]:
			if args:
				self.frame.userlist.AddToList(args)
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
		elif cmd == "/rescan":
			self.frame.OnRescan()
		elif cmd and cmd[:1] == "/" and cmd != "/me" and cmd[:2] != "//":
			self.frame.logMessage(_("Command %s is not recognized") % text)
			return
		else:
			if text[:2] == "//":
				text = text[1:]
			self.SendMessage(text)
		widget.set_text("")

	def UpdateColours(self):
		def makecolour(buffer, colour):
			colour = self.frame.np.config.sections["ui"][colour]
			font = self.frame.np.config.sections["ui"]["chatfont"]
			if colour:
				return buffer.create_tag(foreground = colour, font=font)
			else:
				return buffer.create_tag( font=font)

				
		buffer = self.ChatScroll.get_buffer()
		self.tag_remote = makecolour(buffer, "chatremote")
		self.tag_local = makecolour(buffer, "chatlocal")
		self.tag_me = makecolour(buffer, "chatme")
		self.tag_hilite = makecolour(buffer, "chathilite")

	def GetUserStatus(self, status):
		if status == self.status:
			return
		self.status = status
		line = "* " + ["User %s is offline", "User %s is away", "User %s is online"][status] % self.user
		AppendLine(self.ChatScroll, line, self.tag_hilite, "%c")
	
	def OnClose(self, widget):
		if self.logfile is not None:
			self.logfile.close()
			self.logfile = None
		self.chats.RemoveTab(self)
		self.destroy()

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
		list = [self.user] + [i[0] for i in self.frame.userlist.userlist] + ["nicotine"]
		if ix == len(text) and text[:1] == "/":
			list += ["/"+k for k in self.frame.np.config.aliases.keys()] + self.CMDS
		completion, single = GetCompletion(text, list)
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
