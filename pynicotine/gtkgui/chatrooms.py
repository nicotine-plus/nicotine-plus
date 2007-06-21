# Copyright (c) 2003-2004 Hyriand. All rights reserved.
#
import gtk
import gobject
import locale
import pango
from pynicotine import slskmessages
from nicotine_glade import ChatRoomTab
from utils import InitialiseColumns, AppendLine, PopupMenu, FastListModel, string_sort_func, WriteLog, int_sort_func, Humanize, expand_alias, EncodingsMenu, SaveEncoding, PressHeader
from pynicotine.utils import _
from ticker import Ticker

def GetCompletion(part, list):
	matches = []
	for match in list:
		if match in matches:
			continue
		if match[:len(part)] == part and len(match) > len(part):
			#print match
			matches.append(match)
	
	if len(matches) == 0:
		return "", 0
	elif len(matches) == 1:
		return matches[0][len(part):], 1
	else:
		prefix = matches[0]
		for item in matches:
			for i in range(len(prefix)):
				if prefix[:i+1] != item[:i+1]:
					prefix = prefix[:i]
					break
		return prefix[len(part):], 0

class RoomsListModel(FastListModel):
	COLUMNS = 2
	COLUMN_TYPES = (gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_INT)
	
	def __init__(self, rooms):
		FastListModel.__init__(self)
		for room in rooms:
			self.data.append([room[0], Humanize(room[1]), room[1]])
		self.sort_col = 1
		self.sort_order = gtk.SORT_DESCENDING
		self.sort()
	
	def sort(self):
		if self.sort_col == 0:
			func = locale.strcoll
			col = 0
		else:
			func = cmp
			col = 2
		if self.sort_order == gtk.SORT_DESCENDING:
			self.data.sort(lambda r2, r1: func(r1[col], r2[col]))
		else:
			self.data.sort(lambda r1, r2: func(r1[col], r2[col]))

class RoomsControl:
	def __init__(self, frame):
		self.frame = frame
		self.joinedrooms = {}
		self.autojoin = 1
		
		cols = InitialiseColumns(frame.roomlist.RoomsList,
			[_("Room"), 150, "text", self.frame.CellDataFunc],
			[_("Users"), -1, "text", self.frame.CellDataFunc],
		)
		
		for ix in range(len(cols)):
			col = cols[ix]
			col.connect("clicked", self.OnResort, ix)
		
		cols[1].set_sort_indicator(True)
		cols[1].set_sort_order(gtk.SORT_DESCENDING)
		for i in range (2):
			parent = cols[i].get_widget().get_ancestor(gtk.Button)
			if parent:
				parent.connect('button_press_event', PressHeader)

		self.roomsmodel = RoomsListModel([])
		frame.roomlist.RoomsList.set_model(self.roomsmodel)
		
		self.popup_room = None
		self.popup_menu = PopupMenu().setup(
			("#" + _("Join room"), self.OnPopupJoin, gtk.STOCK_JUMP_TO ),
			("#" + _("Leave room"), self.OnPopupLeave, gtk.STOCK_CLOSE),
			( "", None ),
			("#" + _("Refresh"), self.OnPopupRefresh, gtk.STOCK_REFRESH ),
		)
		frame.roomlist.RoomsList.connect("button_press_event", self.OnListClicked)
		frame.roomlist.RoomsList.set_headers_clickable(True)
		
		self.frame.ChatNotebook.connect("switch-page", self.OnSwitchPage)
		try:
			self.frame.ChatNotebook.connect("page-reordered", self.OnReorderedPage)
		except:
			# No PyGTK 2.10! Gosh, you really need to get with the times!
			pass
		self.frame.SetTextBG(self.frame.roomlist.RoomsList)
		self.frame.SetTextBG(self.frame.roomlist.CreateRoomEntry)
		
	def OnReorderedPage(self, notebook, page, page_num, force=0):
		room_tab_order = {}
		# Find position of opened autojoined rooms
		for name, room in self.joinedrooms.items():
			if name not in self.frame.np.config.sections["server"]["autojoin"]:
				continue
			room_tab_order [ notebook.page_num(room.Main) ] = name
		pos = 1000
		# Add closed autojoined rooms as well
		for name in self.frame.np.config.sections["server"]["autojoin"]:
			if not self.joinedrooms.has_key(name):
				room_tab_order [ pos ] = name
				pos += 1
		# Sort by "position"
		rto = room_tab_order.keys()
		rto.sort()
		new_autojoin = []
		for roomplace in rto:
			new_autojoin.append(room_tab_order[roomplace])
		# Save
		self.frame.np.config.sections["server"]["autojoin"] = new_autojoin
		
	def OnSwitchPage(self, notebook, page, page_num, force=0):
		if self.frame.notebook1.get_current_page() != 0 and not force:
			return
		page = notebook.get_nth_page(page_num)
		for name, room in self.joinedrooms.items():
			if room.Main == page:
				gobject.idle_add(room.entry3.grab_focus)
				# Remove hilite
				if name in self.frame.TrayApp.tray_status["hilites"]["rooms"]:
					self.frame.ClearNotification("rooms", None, name)

			
	def OnResort(self, column, column_id):
		if self.roomsmodel.sort_col == column_id:
			order = self.roomsmodel.sort_order
			if order == gtk.SORT_ASCENDING:
				order = gtk.SORT_DESCENDING
			else:
				order = gtk.SORT_ASCENDING
			column.set_sort_order(order)
			self.roomsmodel.sort_order = order
			self.frame.roomlist.RoomsList.set_model(None)
			self.roomsmodel.sort()
			self.frame.roomlist.RoomsList.set_model(self.roomsmodel)
			return
		cols = self.frame.roomlist.RoomsList.get_columns()
		cols[column_id].set_sort_indicator(True)
		cols[self.roomsmodel.sort_col].set_sort_indicator(False)
		self.roomsmodel.sort_col = column_id
		self.OnResort(column, column_id)
		
	def OnListClicked(self, widget, event):
		if self.roomsmodel is None:
			return False
		if event.button == 1 and event.type == gtk.gdk._2BUTTON_PRESS:
			d = self.frame.roomlist.RoomsList.get_path_at_pos(int(event.x), int(event.y))
			if d:
				path, column, x, y = d
				room = self.roomsmodel.get_value(self.roomsmodel.get_iter(path), 0)
				if not room in self.joinedrooms.keys():
					self.frame.np.queue.put(slskmessages.JoinRoom(room))
			return True
		elif event.button == 3:
			return self.OnPopupMenu(widget, event)
		return False
		
	def OnPopupMenu(self, widget, event):
		if event.button != 3 or self.roomsmodel is None:
			return
		items = self.popup_menu.get_children()
		d = self.frame.roomlist.RoomsList.get_path_at_pos(int(event.x), int(event.y))
		if d:
			path, column, x, y = d
			room = self.roomsmodel.get_value(self.roomsmodel.get_iter(path), 0)
			if room in self.joinedrooms.keys():
				act = (False, True)
			else:
				act = (True, False)
		else:
			room = None
			act = (False, False)
		self.popup_room = room
		items[0].set_sensitive(act[0])
		items[1].set_sensitive(act[1])
		self.popup_menu.popup(None, None, None, event.button, event.time)
	
	def OnPopupJoin(self, widget):
		self.frame.np.queue.put(slskmessages.JoinRoom(self.popup_room))
	
	def OnPopupLeave(self, widget):
		self.frame.np.queue.put(slskmessages.LeaveRoom(self.popup_room))
		
	def OnPopupRefresh(self, widget):
		self.frame.np.queue.put(slskmessages.RoomList())
		
	def JoinRoom(self, msg):
		if self.joinedrooms.has_key(msg.room):
			self.joinedrooms[msg.room].Rejoined(msg.users)
			return
		tab = ChatRoom(self, msg.room, msg.users)
		self.joinedrooms[msg.room] = tab
		self.frame.ChatNotebook.append_page(tab.Main, msg.room, tab.OnLeave)
		
		self.frame.searchroomslist[msg.room] = self.frame.RoomSearchCombo_List.append([msg.room])
		tab.CountUsers()
		

	def SetRoomList(self, msg):
		if self.autojoin:
			self.autojoin = 0
			if self.joinedrooms.keys():
				list = self.joinedrooms.keys()
			else:
				list = self.frame.np.config.sections["server"]["autojoin"]

			for room in list:
				self.frame.np.queue.put(slskmessages.JoinRoom(room))

		self.roomsmodel = RoomsListModel(msg.rooms)
		self.frame.roomlist.RoomsList.set_model(self.roomsmodel)

	def GetUserStats(self, msg):
		for room in self.joinedrooms.values():
			room.GetUserStats(msg.user, msg.avgspeed, msg.files)
	
	def GetUserStatus(self, msg):
		for room in self.joinedrooms.values():
			room.GetUserStatus(msg.user, msg.status)
			
	def UserJoinedRoom(self, msg):
		if self.joinedrooms.has_key(msg.room):
			self.joinedrooms[msg.room].UserJoinedRoom(msg.username, msg.userdata)
	
	def UserLeftRoom(self, msg):
		self.joinedrooms[msg.room].UserLeftRoom(msg.username)
	
	def TickerSet(self, msg):
		self.joinedrooms[msg.room].TickerSet(msg)

	def TickerAdd(self, msg):
		self.joinedrooms[msg.room].TickerAdd(msg)

	def TickerRemove(self, msg):
		self.joinedrooms[msg.room].TickerRemove(msg)

	def SayChatRoom(self, msg, text):
		if msg.user in self.frame.np.config.sections["server"]["ignorelist"]:
			return
		self.joinedrooms[msg.room].SayChatRoom(msg, text)
	
	def UpdateColours(self):
		self.frame.SetTextBG(self.frame.roomlist.RoomsList)
		self.frame.SetTextBG(self.frame.roomlist.CreateRoomEntry)
		for room in self.joinedrooms.values():
			room.ChangeColours()
			
	def saveColumns(self):
		for room in self.frame.np.config.sections["columns"]["chatrooms"].keys()[:]:
			if room not in self.joinedrooms.keys():
				del self.frame.np.config.sections["columns"]["chatrooms"][room]
		for room in self.joinedrooms.values():
			room.saveColumns()
		

	def LeaveRoom(self, msg):
		room = self.joinedrooms[msg.room]
		if room.logfile is not None:
			room.logfile.close()
			room.logfile = None
		self.frame.ChatNotebook.remove_page(room.Main)
		room.destroy()
		del self.joinedrooms[msg.room]
		self.frame.RoomSearchCombo_List.remove(self.frame.searchroomslist[msg.room])
	
	def ConnClose(self):
		self.roomsmodel = None
		self.frame.roomlist.RoomsList.set_model(None)
		
		for room in self.joinedrooms.values():
			room.ConnClose()

		self.autojoin = 1

def TickDialog(parent, default = ""):
	dlg = gtk.Dialog(title = _("Set ticker message"), parent = parent,
		buttons = (gtk.STOCK_OK, gtk.RESPONSE_OK, gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
	dlg.set_default_response(gtk.RESPONSE_OK)
	
	t = 0
	
	dlg.set_border_width(10)
	dlg.vbox.set_spacing(10)
		
	l = gtk.Label(_("Set room ticker message:"))
	l.set_alignment(0, 0.5)
	dlg.vbox.pack_start(l, False, False)
	
	entry = gtk.Entry()
	entry.set_activates_default(True)
	entry.set_text(default)
	dlg.vbox.pack_start(entry, True, True)

	h = gtk.HBox(False, False)
	r1 = gtk.RadioButton()
	r1.set_label(_("Just this time"))
	r1.set_active(True)
	h.pack_start(r1, False, False)
	
	r2 = gtk.RadioButton(r1)
	r2.set_label(_("Always for this channel"))
	h.pack_start(r2, False, False)
	
	r3 = gtk.RadioButton(r1)
	r3.set_label(_("Default for all channels"))
	h.pack_start(r3, False, False)
	
	dlg.vbox.pack_start(h, True, True)
	
	dlg.vbox.show_all()

	result = None
	if dlg.run() == gtk.RESPONSE_OK:
		if r1.get_active():
			t = 0
		elif r2.get_active():
			t = 1
		elif r3.get_active():
			t = 2
		result = entry.get_text()
		
	dlg.destroy()
		
	return [t, result]

class ChatRoom(ChatRoomTab):
	def __init__(self, roomsctrl, room, users):
		ChatRoomTab.__init__(self, False)

		self.roomsctrl = roomsctrl
		self.frame = roomsctrl.frame
		self.room = room
		self.lines = []
		self.logfile = None
		self.leaving = 0
		config = self.frame.np.config.sections
		if not self.frame.np.config.sections["ticker"]["hide"]:
			self.Ticker.show()

		if self.frame.translux:
			self.tlux_roomlog = lambda: self.RoomLog.get_window(gtk.TEXT_WINDOW_TEXT)
			self.tlux_chat = lambda: self.ChatScroll.get_window(gtk.TEXT_WINDOW_TEXT)
			self.frame.translux.subscribe(self.RoomLog, self.tlux_roomlog)
			self.frame.translux.subscribe(self.ChatScroll, self.tlux_chat)
			self.RoomLog.get_parent().get_vadjustment().connect("value-changed", lambda *args: self.RoomLog.queue_draw())
			self.ChatScroll.get_parent().get_vadjustment().connect("value-changed", lambda *args: self.ChatScroll.queue_draw())
			self.ChatScroll.get_parent().get_hadjustment().connect("value-changed", lambda *args: self.ChatScroll.queue_draw())

		self.Elist = {}
		self.encoding, m = EncodingsMenu(self.frame.np, "roomencoding", room)
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
			self.vbox6.remove(self.entry3)
			self.entry3.destroy()
			self.entry3 = sexy.SpellEntry()
			self.entry3.show()
        		self.entry3.connect("activate", self.OnEnter)
        		self.entry3.connect("key_press_event", self.OnKeyPress)
			self.vbox6.pack_start(self.entry3, False, False, 0)
	
		self.Log.set_active(self.frame.np.config.sections["logging"]["chatrooms"])
		
		
		
		if room in self.frame.np.config.sections["server"]["autojoin"]:
			self.AutoJoin.set_active(True)
			
		cols = InitialiseColumns(self.UserList, 
			[_("Status"), 20, "pixbuf"],
			[_("User"), 100, "text", self.frame.CellDataFunc],
			[_("Speed"), 0, "text", self.frame.CellDataFunc],
			[_("Files"), 0, "text", self.frame.CellDataFunc],
		)
		cols[0].set_sort_column_id(4)
		cols[1].set_sort_column_id(1)
		cols[2].set_sort_column_id(5)
		cols[3].set_sort_column_id(6)
		cols[0].get_widget().hide()
		if not config["columns"]["chatrooms"].has_key(room):
			config["columns"]["chatrooms"][room] = [1, 1, 1, 1]
		for i in range (4):
			parent = cols[i].get_widget().get_ancestor(gtk.Button)
			if parent:
				parent.connect('button_press_event', PressHeader)
			# Read Show / Hide column settings from last session
			cols[i].set_visible(config["columns"]["chatrooms"][room][i])
		self.users = {}

		self.usersmodel = gtk.ListStore(gtk.gdk.Pixbuf, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_INT, gobject.TYPE_INT, gobject.TYPE_INT)
		
		
		for user in users.keys():
			img = self.frame.GetStatusImage(users[user].status)
			hspeed = Humanize(users[user].avgspeed)
			hfiles = Humanize(users[user].files)
			iter = self.usersmodel.append([img, user, hspeed, hfiles, users[user].status, users[user].avgspeed, users[user].files])
			self.users[user] = iter
		self.usersmodel.set_sort_column_id(1, gtk.SORT_ASCENDING)
		self.UpdateColours()
		self.UserList.set_model(self.usersmodel)
		self.UserList.set_property("rules-hint", True)
		
		self.popup_menu = popup = PopupMenu(self.frame)
		popup.setup(
			("USER", ""),
			("", None),
			("#" + _("Send _message"), popup.OnSendMessage, gtk.STOCK_EDIT),
			("", None),
			("#" + _("Show IP a_ddress"), popup.OnShowIPaddress, gtk.STOCK_NETWORK),
			("#" + _("Get user i_nfo"), popup.OnGetUserInfo, gtk.STOCK_DIALOG_INFO),
			("#" + _("Brow_se files"), popup.OnBrowseUser, gtk.STOCK_HARDDISK),
			("#" + _("Gi_ve privileges"), popup.OnGivePrivileges, gtk.STOCK_JUMP_TO),
			("", None),
			("$" + _("_Add user to list"), popup.OnAddToList),
			("$" + _("_Ban this user"), popup.OnBanUser),
			("$" + _("_Ignore this user"), popup.OnIgnoreUser),
		)
		self.UserList.connect("button_press_event", self.OnPopupMenu)

		self.entry3.grab_focus()
		self.vbox6.set_focus_child(self.entry3)
		
		self.logpopupmenu = PopupMenu(self.frame).setup(
			("#" + _("Find"), self.OnFindLogWindow, gtk.STOCK_FIND),
			("", None),
			("#" + _("Copy"), self.OnCopyRoomLog, gtk.STOCK_COPY),
			("#" + _("Copy All"), self.OnCopyAllRoomLog, gtk.STOCK_COPY),
			("", None),
			("#" + _("Clear log"), self.OnClearRoomLog, gtk.STOCK_CLEAR),
		)
		self.RoomLog.connect("button-press-event", self.OnPopupRoomLogMenu)
		
		self.chatpopmenu = PopupMenu(self.frame).setup(
			("#" + _("Find"), self.OnFindChatLog, gtk.STOCK_FIND),
			("", None),
			("#" + _("Copy"), self.OnCopyChatLog, gtk.STOCK_COPY),
			("#" + _("Copy All"), self.OnCopyAllChatLog, gtk.STOCK_COPY),
			("", None),
			("#" + _("Clear log"), self.OnClearChatLog, gtk.STOCK_CLEAR),
		)
		self.ChatScroll.connect("button-press-event", self.OnPopupChatRoomMenu)
		
	def OnFindLogWindow(self, widget):

		self.frame.OnFindTextview(widget, self.RoomLog)
		
	def OnFindChatLog(self, widget):
		self.frame.OnFindTextview(widget, self.ChatScroll)
		
	def get_custom_widget(self, id, string1, string2, int1, int2):
		if id == "Ticker":
			t = Ticker()
			return t
		else:
			return ChatRoomTab.get_custom_widget(self, id, string1, string2, int1, int2)
			
	def destroy(self):
		if self.frame.translux:
			self.frame.translux.unsubscribe(self.tlux_roomlog)
			self.frame.translux.unsubscribe(self.tlux_chat)
		self.Main.destroy()

	def OnPopupMenu(self, widget, event):
		items = self.popup_menu.get_children()
		d = self.UserList.get_path_at_pos(int(event.x), int(event.y))
		if not d:
			return
		path, column, x, y = d
		user = self.usersmodel.get_value(self.usersmodel.get_iter(path), 1)
		
		# Double click starts a private message
		if event.button != 3:
			if event.type == gtk.gdk._2BUTTON_PRESS:
				self.frame.privatechats.SendMessage(user, None, 1)
				self.frame.notebook1.set_current_page(1)
			return
		
		self.popup_menu.set_user(user)
		items[9].set_active(user in [i[0] for i in self.frame.np.config.sections["server"]["userlist"]])
		items[10].set_active(user in self.frame.np.config.sections["server"]["banlist"])
		items[11].set_active(user in self.frame.np.config.sections["server"]["ignorelist"])
		self.popup_menu.popup(None, None, None, event.button, event.time)
		
	def TickerSet(self, msg):
		self.Ticker.set_ticker({})
		for m in msg.msgs.keys():
			self.Ticker.add_ticker(m, self.frame.np.decode(msg.msgs[m], self.encoding))

	def TickerAdd(self, msg):
		text = self.frame.np.decode(msg.msg, self.encoding)
		self.Ticker.add_ticker(msg.user, text)

	def TickerRemove(self, msg):
		self.Ticker.remove_ticker(msg.user)
		
	def SayChatRoom(self, msg, text):
		login = self.frame.np.config.sections["server"]["login"]
		user = msg.user
		if user == login:
			tag = self.tag_local
		elif text.upper().find(login.upper()) > -1:
			tag = self.tag_hilite

		else:
			tag = self.tag_remote
		
		if user != login and tag == self.tag_hilite:
			self.frame.ChatNotebook.request_hilite(self.Main)
			self.frame.ChatRequestIcon(1)
			# add hilite to trayicon
			if self.frame.ChatNotebook.get_current_page() != self.frame.ChatNotebook.page_num(self.roomsctrl.joinedrooms[self.room].Main) or self.frame.notebook1.get_current_page() != 0:
				if self.room not in self.frame.TrayApp.tray_status["hilites"]["rooms"]:
					self.frame.Notification("rooms", user, self.room)
			#else:
				#self.MainWindow.set_urgency_hint(False)
				

		else:
			self.frame.ChatNotebook.request_changed(self.Main)
			self.frame.ChatRequestIcon(0)
			
		if text[:4] == "/me ":
			line = "* %s %s" % (user, text[4:])
			tag = self.tag_me
		else:
			line = "[%s] %s" % (user, text)
		
		if len(self.lines) >= 400:
			buffer = self.ChatScroll.get_buffer()
			start = buffer.get_start_iter()
			end = buffer.get_iter_at_line(self.lines[200])
			self.ChatScroll.get_buffer().delete(start, end)
			del self.lines[0:200]

		line = "\n-- ".join(line.split("\n"))
		
		color = self.getUserStatusColor(self.usersmodel.get_value(self.users[user], 4))
		if self.tag_users.has_key(user):
			self.changecolour(self.tag_users[user], color)
		else:
			self.tag_users[user] = self.makecolour(self.ChatScroll.get_buffer(), color, user)
		self.lines.append(AppendLine(self.ChatScroll, self.frame.CensorChat(self.frame.np.decode(line, self.encoding)), tag, username=user, usertag=self.tag_users[user]))
		if self.Log.get_active():
			self.logfile = WriteLog(self.logfile, self.frame.np.config.sections["logging"]["logsdir"], self.room, line)
			


	
	CMDS = ["/alias ", "/unalias ", "/whois ", "/browse ", "/ip ", "/pm ", "/msg ", "/search ", "/usearch ", "/rsearch ",
		"/bsearch ", "/join ", "/leave", "/add ", "/buddy ", "/rem ", "/unbuddy ", "/ban ", "/ignore ", "/unban ", "/unignore ", "/clear", "/part ", "/quit",
		"/rescan", "/tick", "/nsa", "/info"]

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
		if len(s) == 2:
			args = s[1]
		else:
			args = ""

		if cmd in ("/alias", "/al"):
			AppendLine(self.ChatScroll, self.frame.np.config.AddAlias(args), self.tag_remote, "")
		elif cmd in ("/unalias", "/un"):
			AppendLine(self.ChatScroll, self.frame.np.config.Unalias(args), self.tag_remote, "")
		elif cmd in ["/w", "/whois", "/info"]:
			if args:
				self.frame.LocalUserInfoRequest(args)
				self.frame.OnUserInfo(None)
		elif cmd in ["/b", "/browse"]:
			if args:
				self.frame.BrowseUser(args)
				self.frame.OnUserBrowse(None)
		elif cmd == "/nsa":
			if args:
				self.frame.LocalUserInfoRequest(args)
				self.frame.BrowseUser(args)
				self.frame.OnUserInfo(None)
		elif cmd == "/ip":
			if args:
				self.frame.np.queue.put(slskmessages.GetPeerAddress(args))
		elif cmd == "/pm":
			if args:
				self.frame.privatechats.SendMessage(args, None, 1)
				self.frame.OnPrivateChat(None)
		elif cmd in ["/m", "/msg"]:
			if args:
				s = args.split(" ", 1)
				user = s[0]
				if len(s) == 2:
					msg = s[1]
				else:
					msg = None
				self.frame.privatechats.SendMessage(user, msg)
		elif cmd in ["/s", "/search"]:
			if args:
				self.frame.searches.DoSearch(args, 0)
				self.frame.OnSearch(None)
		elif cmd in ["/us", "/usearch"]:
			s = args.split(" ", 1)
			if len(s) == 2:
				self.frame.searches.DoSearch(s[1], 3, [s[0]])
				self.frame.OnSearch(None)
		elif cmd in ["/rs", "/rsearch"]:
			if args:
				self.frame.searches.DoSearch(args, 1)
				self.frame.OnSearch(None)
		elif cmd in ["/bs", "/bsearch"]:
			if args:
				self.frame.searches.DoSearch(args, 2)
				self.frame.OnSearch(None)
		elif cmd in ["/j", "/join"]:
			if args:
				self.frame.np.queue.put(slskmessages.JoinRoom(args))
		elif cmd in ["/l", "/leave", "/p", "/part"]:
			if args:
				self.frame.np.queue.put(slskmessages.LeaveRoom(args))
			else:
				self.frame.np.queue.put(slskmessages.LeaveRoom(self.room))
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
		elif cmd == "/nuke":
			if args:
				self.frame.BanUser(args)
				self.frame.IgnoreUser(args)
		elif cmd == "/unban":
			if args:
				self.frame.UnbanUser(args)
		elif cmd == "/unignore":
			if args:
				self.frame.UnignoreUser(args)
		elif cmd in ["/clear", "/cl"]:
			self.ChatScroll.get_buffer().set_text("")
			self.lines = []
		elif cmd in ["/a", "/away"]:
			self.frame.OnAway(None)
		elif cmd in ["/q", "/quit"]:
			self.frame.OnExit(None)
		elif cmd == "/now":
			np = self.frame.now.DisplayNowPlaying(None)
			if np:
				self.frame.np.queue.put(slskmessages.SayChatroom(self.room, np))	
		elif cmd == "/rescan":
			self.frame.BothRescan()
		elif cmd  in ["/tick", "/t"]:
			self.frame.np.queue.put(slskmessages.RoomTickerSet(self.room, self.frame.np.encode(args, self.encoding)))
		elif cmd and cmd[:1] == "/" and cmd != "/me" and cmd[:2] != "//":
			self.frame.logMessage(_("Command %s is not recognized") % text)
			return
		else:
			if text[:2] == "//":
				text = text[1:]
			self.frame.np.queue.put(slskmessages.SayChatroom(self.room, self.frame.AutoReplace(text)))
		widget.set_text("")

	def UserJoinedRoom(self, username, userdata):
		if self.users.has_key(username):
			return
		AppendLine(self.RoomLog, _("%s joined the room") % username, self.tag_log)
		img = self.frame.GetStatusImage(userdata.status)
		hspeed = Humanize(userdata.avgspeed)
		hfiles = Humanize(userdata.files)
		iter = self.usersmodel.append([img, username, hspeed, hfiles, userdata.status, userdata.avgspeed, userdata.files])
		self.users[username] = iter
		color = self.getUserStatusColor(userdata.status)
		if username in self.tag_users.keys():
			
			self.changecolour(self.tag_users[username], color)
		else:
			self.tag_users[username] = self.makecolour(self.ChatScroll.get_buffer(), color, username=username)
		self.CountUsers()
		
	def UserLeftRoom(self, username):
		if not self.users.has_key(username):
			return
		AppendLine(self.RoomLog, _("%s left the room") % username, self.tag_log)
		self.usersmodel.remove(self.users[username])
		del self.users[username]
		if username in self.tag_users.keys():
			color = self.getUserStatusColor(-1)
			self.changecolour(self.tag_users[username], color)
		self.CountUsers()
		
	def CountUsers(self):
		numusers = len(self.users.keys())
		if numusers > 1:
			self.LabelPeople.show()
			self.LabelPeople.set_text(_("%i people in room") % numusers)
		elif numusers == 1:
			self.LabelPeople.show()
			self.LabelPeople.set_text(_("You are alone"))
		else:
			self.LabelPeople.hide()
		
	def GetUserStats(self, user, avgspeed, files):
		if not self.users.has_key(user):
			return
		self.usersmodel.set(self.users[user], 2, Humanize(avgspeed), 3, Humanize(files), 5, avgspeed, 6, files)
		
	def GetUserStatus(self, user, status):
		if not self.users.has_key(user):
			return
		img = self.frame.GetStatusImage(status)
		if img == self.usersmodel.get_value(self.users[user], 0):
			return
		if status == 1:
			action = _("%s has gone away")
		else:
			action = _("%s has returned")
		AppendLine(self.RoomLog, action % user, self.tag_log)
		if user in self.tag_users.keys():
			color = self.getUserStatusColor(status)
			self.changecolour(self.tag_users[user], color)
		self.usersmodel.set(self.users[user], 0, img, 4, status)
		
	def makecolour(self, buffer, colour, username=None):
		colour = self.frame.np.config.sections["ui"][colour]
		font =  self.frame.np.config.sections["ui"]["chatfont"]
		
		if colour:
			tag = buffer.create_tag(foreground = colour, font=font)
		else:
			tag = buffer.create_tag( font=font)
		if username is not None:
			usernamestyle = self.frame.np.config.sections["ui"]["usernamestyle"]
			
			#tag.set_property("weight",  pango.WEIGHT_BOLD)
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
				
			tag.connect("event", self.UserNameEvent, username)
			tag.last_event_type = -1
		return tag
		
	def UserNameEvent(self, tag, widget, event, iter, user):

		if tag.last_event_type == gtk.gdk.BUTTON_PRESS and event.type == gtk.gdk.BUTTON_RELEASE and event.button in (1, 2):
			self.popup_menu.set_user(user)
			items = self.popup_menu.get_children()
			# Chat, Userlists use the normal popup system
			items[9].set_active(user in [i[0] for i in self.frame.np.config.sections["server"]["userlist"]])
			items[10].set_active(user in self.frame.np.config.sections["server"]["banlist"])
			items[11].set_active(user in self.frame.np.config.sections["server"]["ignorelist"])
			self.popup_menu.popup(None, None, None, event.button, event.time)
		tag.last_event_type = event.type
		
	def UpdateColours(self):

		map = self.ChatScroll.get_style().copy()
		self.backupcolor = map.text[gtk.STATE_NORMAL]
		buffer = self.ChatScroll.get_buffer()
		self.tag_remote = self.makecolour(buffer, "chatremote")
		self.tag_local = self.makecolour(buffer, "chatlocal")
		self.tag_me = self.makecolour(buffer, "chatme")
		self.tag_hilite = self.makecolour(buffer, "chathilite")
		self.tag_users = {}
		for user in self.users:
			status = self.usersmodel.get_value(self.users[user], 4)
			color = self.getUserStatusColor(status)
			if user in self.tag_users.keys():
				self.changecolour(self.tag_users[username], color)
			else:
				self.tag_users[user] = self.makecolour(buffer, color, user)
		logbuffer = self.RoomLog.get_buffer()
		self.tag_log = self.makecolour(logbuffer, "chatremote")
		
		self.frame.SetTextBG(self.ChatScroll)
		self.frame.SetTextBG(self.RoomLog)
		self.frame.SetTextBG(self.UserList)
		
		self.frame.SetTextBG(self.entry3)
		
		
	def getUserStatusColor(self, status):
		if status == 1:
			color = "useraway"
		elif status == 2:
			color = "useronline"
		else:
			color = "useroffline"
		return color
		
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
		# Hotspots
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
		self.changecolour(self.tag_log, "chatremote")

		for user in self.users.keys():
			color = self.getUserStatusColor(self.usersmodel.get_value(self.users[user], 4))
			if user in self.tag_users.keys():
				self.changecolour(self.tag_users[user], color)
			else:
				self.tag_users[user] = self.makecolour(buffer, color, user)
			
		self.frame.SetTextBG(self.ChatScroll)
		self.frame.SetTextBG(self.RoomLog)
		self.frame.SetTextBG(self.UserList)
		self.frame.SetTextBG(self.entry3)
				
	def OnLeave(self, widget = None):
		if self.leaving:
			return
		self.frame.np.queue.put(slskmessages.LeaveRoom(self.room))
		self.Leave.set_sensitive(False)
		self.leaving = 1
		config = self.frame.np.config.sections
		if config["columns"]["chatrooms"].has_key(self.room):
			del config["columns"]["chatrooms"][self.room]
			
	def saveColumns(self):
		columns = []
		for column in self.UserList.get_columns():
			columns.append(column.get_visible())
		self.frame.np.config.sections["columns"]["chatrooms"][self.room] = columns
		
		
	def ConnClose(self):
		AppendLine(self.ChatScroll, _("--- disconnected ---"), self.tag_hilite)
		self.usersmodel.clear()
		self.users = {}
		self.CountUsers()
		config = self.frame.np.config.sections
  		if not self.AutoJoin.get_active() and config["columns"]["chatrooms"].has_key(self.room):
			del config["columns"]["chatrooms"][self.room]
		
	def Rejoined(self, users):
		for user in users.keys():
			if self.users.has_key(user):
				self.usersmodel.remove(self.users[user])
			img = self.frame.GetStatusImage(users[user].status)
			hspeed = Humanize(users[user].avgspeed)
			hfiles = Humanize(users[user].files)
			iter = self.usersmodel.append([img, user, hspeed, hfiles, users[user].status, users[user].avgspeed, users[user].files])
			self.users[user] = iter
		AppendLine(self.ChatScroll, _("--- reconnected ---"), self.tag_hilite)
		self.CountUsers()

	def OnAutojoin(self, widget):
		autojoin = self.frame.np.config.sections["server"]["autojoin"]
		if not widget.get_active():
			if self.room in autojoin:
				autojoin.remove(self.room)
		else:
			if not self.room in autojoin:
				autojoin.append(self.room)
		self.frame.np.config.writeConfig()

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
		list = self.users.keys() + [i[0] for i in self.frame.userlist.userlist] + ["nicotine"]
		if ix == len(text) and text[:1] == "/":
			list += ["/"+k for k in self.frame.np.config.aliases.keys()] + self.CMDS
		completion, single = GetCompletion(text, list)
		if completion:
			if single:
				if ix == len(text) and text[:1] != "/":
					completion += ": "
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
			SaveEncoding(self.frame.np, "roomencoding", self.room, self.encoding)
	
	def OnPopupChatRoomMenu(self, widget, event):
		if event.button != 3:
			return False
		widget.emit_stop_by_name("button-press-event")
		self.chatpopmenu.popup(None, None, None, event.button, event.time)
		return True
	
	def OnPopupRoomLogMenu(self, widget, event):
		if event.button != 3:
			return False
		widget.emit_stop_by_name("button-press-event")
		self.logpopupmenu.popup(None, None, None, event.button, event.time)
		return True
	
	def OnCopyAllRoomLog(self, widget):
		start, end = self.RoomLog.get_buffer().get_bounds()
		log = self.RoomLog.get_buffer().get_text(start, end)
		self.frame.clip.set_text(log)
		
	def OnCopyRoomLog(self, widget):
		bound = self.RoomLog.get_buffer().get_selection_bounds()
		if bound is not None and len(bound) == 2:
			start, end = bound
			log = self.RoomLog.get_buffer().get_text(start, end)
			self.frame.clip.set_text(log)
			
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

	def OnClearRoomLog(self, widget):
		self.RoomLog.get_buffer().set_text("")
	
	def OnTickerClicked(self, widget, event):
		if event.button != 1:
			return False
		if self.Ticker.messages.has_key(self.frame.np.config.sections["server"]["login"]):
			old = self.Ticker.messages[self.frame.np.config.sections["server"]["login"]]
		else:
			old = ""
		t, result = TickDialog(self.frame.MainWindow, old)
		if not result is None:
			if t == 1:
				if not result:
					if self.frame.np.config.sections["ticker"]["rooms"].has_key(self.room):
						del self.frame.np.config.sections["ticker"]["rooms"][self.room]
				else:
					self.frame.np.config.sections["ticker"]["rooms"][self.room] = result
				self.frame.np.config.writeConfig()
			elif t == 2:
				if self.frame.np.config.sections["ticker"]["rooms"].has_key(self.room):
					del self.frame.np.config.sections["ticker"]["rooms"][self.room]
				self.frame.np.config.sections["ticker"]["default"] = result
				self.frame.np.config.writeConfig()
			self.frame.np.queue.put(slskmessages.RoomTickerSet(self.room, self.frame.np.encode(result, self.encoding)))
		return True

	def ShowTicker(self, visible):
		if visible:
			self.Ticker.enable()
			self.Ticker.show()
		else:
			self.Ticker.disable()
			self.Ticker.hide()

class ChatRooms:
	def __init__(self, frame):
		frame.ChatNotebook.popup_enable()
		self.frame = frame
		self.roomsctrl = RoomsControl(frame)

	def ConnClose(self):
		self.roomsctrl.ConnClose()
