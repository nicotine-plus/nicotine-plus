# Copyright (c) 2003-2004 Hyriand. All rights reserved.
#
import gtk
import gobject

from pynicotine import slskmessages
from utils import InitialiseColumns, PopupMenu, InputDialog, Humanize

from pynicotine.utils import _

class UserList:
	def __init__(self, frame):
		self.frame = frame
		self.userlist = []
		
		self.usersmodel = gtk.ListStore(gtk.gdk.Pixbuf, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_BOOLEAN, gobject.TYPE_STRING, gobject.TYPE_INT, gobject.TYPE_INT, gobject.TYPE_INT)
		cols = InitialiseColumns(self.frame.UserList,
			["", 20, "pixbuf"],
			[_("User"), 100, "text", self.CellDataFunc],
			[_("Speed"), 0, "text", self.CellDataFunc],
			[_("Files"), 0, "text", self.CellDataFunc],
			[_("Trusted"), 0, "toggle"],
			[_("Comments"), -1, "edit", self.CellDataFunc],
		)
		cols[0].set_sort_column_id(6)
		cols[1].set_sort_column_id(1)
		cols[2].set_sort_column_id(7)
		cols[3].set_sort_column_id(8)
		cols[4].set_sort_column_id(4)
		cols[5].set_sort_column_id(5)
		renderers = cols[4].get_cell_renderers()
		for render in renderers:
			render.connect('toggled', self.cell_toggle_callback, self.frame.UserList, 4)
		renderers = cols[5].get_cell_renderers()
		for render in renderers:
			render.connect('edited', self.cell_edited_callback, self.frame.UserList, 5)
		self.frame.UserList.set_model(self.usersmodel)
		self.frame.UserList.set_property("rules-hint", True)
		self.privileged = []
		self.notify = []
		self.trusted = []
		for user in self.frame.np.config.sections["server"]["userlist"]:
			if len(user) > 4:
				trusted = user[4]
			else:
				trusted = 0
			row = [self.frame.GetStatusImage(0), user[0], "0", "0", trusted, user[1], 0, 0, 0]
			if len(user) > 2:
				if user[2]:
					self.notify.append(user[0])
				if user[3]:
					self.privileged.append(user[0])
				if trusted:
					self.trusted.append(user[0])
			iter = self.usersmodel.append(row)
			self.userlist.append([user[0], user[1], iter])

		self.popup_menu = popup = PopupMenu(frame)
		popup.setup(
			("#" + _("Send _message"), popup.OnSendMessage, gtk.STOCK_EDIT),
			("", None),
			("#" + _("Show IP a_ddress"), popup.OnShowIPaddress, gtk.STOCK_NETWORK),
			("#" + _("Get user i_nfo"), popup.OnGetUserInfo, gtk.STOCK_DIALOG_INFO),
			("#" + _("Brow_se files"), popup.OnBrowseUser, gtk.STOCK_HARDDISK),
			("#" + _("Gi_ve privileges"), popup.OnGivePrivileges, gtk.STOCK_JUMP_TO),
			("$" + _("_Ban this user"), popup.OnBanUser),
			("$" + _("_Ignore this user"), popup.OnIgnoreUser),
			("", None),
			("$" + _("_Online notify"), self.OnNotify),
			("$" + _("_Privileged"), self.OnPrivileged),
			("$" + _("_Trusted"), self.OnTrusted),
			("", None),
			("#" + _("Edit _comments"), self.OnEditComments, gtk.STOCK_EDIT),
			("#" + _("_Remove"), self.OnRemoveUser, gtk.STOCK_CANCEL),
		)
		self.frame.UserList.connect("button_press_event", self.OnPopupMenu)
	
	def CellDataFunc(self, column, cellrenderer, model, iter):
		colour = self.frame.np.config.sections["ui"]["search"]
		if colour == "":
			colour = None
		cellrenderer.set_property("foreground", colour)
		
	def cell_toggle_callback(self, widget, index, treeview, pos):
	
		iter = self.usersmodel.get_iter(index)
		user = self.usersmodel.get_value(iter, 1)
		value = self.usersmodel.get_value(iter, pos)
		self.usersmodel.set(iter, pos, not value)
		if user in self.trusted:
			self.trusted.remove(user)
		else:
			if not user in self.trusted:
				self.trusted.append(user)
		self.SaveUserList()
		
	def cell_edited_callback(self, widget, index, value, treeview, pos):
		
		store = treeview.get_model()
		iter = store.get_iter(index)
		if pos == 5:
			self.SetComment(iter, store, value)
		
			
	def SetComment(self, iter, store, comments=None):
		user = store.get_value(iter, 1)
		if comments is not None:
			for i in self.userlist:
				if i[0] == user:
					i[1] = comments
					self.usersmodel.set(i[2], 5, comments)
					break
			self.SaveUserList()
			
	def ConnClose(self):
		for user in self.userlist:
			self.usersmodel.set(user[2], 0, self.frame.GetStatusImage(0), 2, "0", 3, "0", 6, 0, 7, 0, 8, 0)
	
	def OnPopupMenu(self, widget, event):
		items = self.popup_menu.get_children()
		d = self.frame.UserList.get_path_at_pos(int(event.x), int(event.y))

		if d:
			path, column, x, y = d
			user = self.frame.UserList.get_model().get_value(self.frame.UserList.get_model().get_iter(path), 1)
			
			if event.button != 3:
				if event.type == gtk.gdk._2BUTTON_PRESS:
					self.frame.privatechats.SendMessage(user, None, 1)
					self.frame.notebook1.set_current_page(1)
				return
			
			self.popup_menu.set_user(user)
			
			items = self.popup_menu.get_children()
			
			items[6].set_active(user in self.frame.np.config.sections["server"]["banlist"])
			items[7].set_active(user in self.frame.np.config.sections["server"]["ignorelist"])
			items[9].set_active(user in self.notify)
			items[10].set_active(user in self.privileged)
			items[11].set_active(user in self.trusted)
			
			self.popup_menu.popup(None, None, None, event.button, event.time)
		
	def GetIter(self, user):
		iters = [i[2] for i in self.userlist if i[0] == user]
		if iters:
			return iters[0]
		else:
			return None
			
	def GetUserStatus(self, msg):
		iter = self.GetIter(msg.user)
		if iter is None:
			return
		if msg.status == self.usersmodel.get_value(iter, 6):
			return
		if msg.user in self.notify:
			status = [_("User %s is offline"), _("User %s is away"), _("User %s is online")][msg.status]
			self.frame.logMessage(status % msg.user)
		img = self.frame.GetStatusImage(msg.status)
		self.usersmodel.set(iter, 0, img, 6, msg.status)

	def GetUserStats(self, msg):
		iter = self.GetIter(msg.user)
		if iter is None:
			return
		hspeed = Humanize(msg.avgspeed)
		hfiles = Humanize(msg.files)
		self.usersmodel.set(iter, 2, hspeed, 3, hfiles, 7, msg.avgspeed, 8, msg.files)

	def AddToList(self, user):
		if user in [i[0] for i in self.userlist]:
			return
		
		row = [self.frame.GetStatusImage(0), user, "0", "0", False, "", 0, 0, 0]
		iter = self.usersmodel.append(row)
		self.userlist.append([user, "", iter])
		
		self.SaveUserList()
		self.frame.np.queue.put(slskmessages.AddUser(user))
		self.frame.np.queue.put(slskmessages.GetUserStatus(user))
		self.frame.np.queue.put(slskmessages.GetUserStats(user))

	def OnEditComments(self, widget):
		user = self.popup_menu.get_user()
		for i in self.userlist:
			if i[0] == user:
				comments = i[1]
				break
		else:
			comments = ""
		
		comments = InputDialog(self.frame.MainWindow, _("Edit comments")+"...", _("Comments")+":", comments)
		
		if comments is not None:
			for i in self.userlist:
				if i[0] == user:
					i[1] = comments
					self.usersmodel.set(i[2], 5, comments)
					break
			self.SaveUserList()

	def SaveUserList(self):
		l = []
		for i in self.userlist:
			l.append([i[0], i[1], (i[0] in self.notify), (i[0] in self.privileged), (i[0] in self.trusted)])
		self.frame.np.config.sections["server"]["userlist"] = l
		self.frame.np.config.writeConfig()

	def RemoveFromList(self, user):
		if user in self.notify:
			self.notify.remove(user)
		if user in self.privileged:
			self.privileged.remove(user)
		if user in self.trusted:
			self.trusted.remove(user)
		for i in self.userlist:
			if i[0] == user:
				self.userlist.remove(i)
				self.usersmodel.remove(i[2])
				break
		self.SaveUserList()

	def OnRemoveUser(self, widget):
		self.RemoveFromList(self.popup_menu.get_user())

	def OnNotify(self, widget):
		user = self.popup_menu.get_user()
		if not widget.get_active():
			if user in self.notify:
				self.notify.remove(user)
		else:
			if not user in self.notify:
				self.notify.append(user)
		self.SaveUserList()

	def OnPrivileged(self, widget):
		user = self.popup_menu.get_user()
		if not widget.get_active():
			if user in self.privileged:
				self.privileged.remove(user)
		else:
			if not user in self.privileged:
				self.privileged.append(user)
		self.SaveUserList()
		
	def OnTrusted(self, widget):
		user = self.popup_menu.get_user()
		if not widget.get_active():
			if user in self.trusted:
				self.trusted.remove(user)
		else:
			if not user in self.trusted:
				self.trusted.append(user)
		for i in self.userlist:
			if i[0] == user:
				self.usersmodel.set(i[2], 4, (user in self.trusted))
		self.SaveUserList()
		
