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
		
		self.usersmodel = gtk.ListStore(gtk.gdk.Pixbuf, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_INT, gobject.TYPE_INT, gobject.TYPE_INT)
		cols = InitialiseColumns(self.frame.UserList,
			["", -1, "pixbuf"],
			[_("User"), 100, "text"],
			[_("Speed"), 0, "text"],
			[_("Files"), 0, "text"],
			[_("Comments"), -1, "text"]
		)
		cols[0].set_sort_column_id(5)
		cols[1].set_sort_column_id(1)
		cols[2].set_sort_column_id(6)
		cols[3].set_sort_column_id(7)
		cols[4].set_sort_column_id(4)
		
		self.frame.UserList.set_model(self.usersmodel)
		
		self.privileged = []
		self.notify = []
		for user in self.frame.np.config.sections["server"]["userlist"]:
			row = [self.frame.GetStatusImage(0), user[0], "0", "0", user[1], 0, 0, 0]
			if len(user) > 2:
				if user[2]:
					self.notify.append(user[0])
				if user[3]:
					self.privileged.append(user[0])
			iter = self.usersmodel.append(row)
			self.userlist.append([user[0], user[1], iter])

		self.popup_menu = popup = PopupMenu(frame)
		popup.setup(
			(_("Send _message"), popup.OnSendMessage),
			(_("Show IP a_ddress"), popup.OnShowIPaddress),
			(_("Get user i_nfo"), popup.OnGetUserInfo),
			(_("Brow_se files"), popup.OnBrowseUser),
			(_("_Give privileges"), popup.OnGivePrivileges),
			("$" + _("_Ban this user"), popup.OnBanUser),
			("$" + _("_Ignore this user"), popup.OnIgnoreUser),
			("", None),
			("$" + _("_Online notify"), self.OnNotify),
			("$" + _("_Privileged"), self.OnPrivileged),
			("", None),
			(_("Edit _comments"), self.OnEditComments),
			(_("_Remove"), self.OnRemoveUser),
		)
		self.frame.UserList.connect("button_press_event", self.OnPopupMenu)
	
	def ConnClose(self):
		for user in self.userlist:
			self.usersmodel.set(user[2], 0, self.frame.GetStatusImage(0), 2, "0", 3, "0", 5, 0, 6, 0, 7, 0)
	
	def OnPopupMenu(self, widget, event):
		model, iter = self.frame.UserList.get_selection().get_selected()
		if not iter:
			return

		user = model.get_value(iter, 1)
		
		if event.button != 3:
			if event.type == gtk.gdk._2BUTTON_PRESS:
				self.frame.privatechats.SendMessage(user, None, 1)
				self.frame.notebook1.set_current_page(1)
			return
		

		self.popup_menu.set_user(user)
		
		items = self.popup_menu.get_children()
		
		items[5].set_active(user in self.frame.np.config.sections["server"]["banlist"])
		items[6].set_active(user in self.frame.np.config.sections["server"]["ignorelist"])
		items[8].set_active(user in self.notify)
		items[9].set_active(user in self.privileged)
		
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
		if msg.status == self.usersmodel.get_value(iter, 5):
			return
		if msg.user in self.notify:
			status = [_("User %s is offline"), _("User %s is away"), _("User %s is online")][msg.status]
			self.frame.logMessage(status % msg.user)
		img = self.frame.GetStatusImage(msg.status)
		self.usersmodel.set(iter, 0, img, 5, msg.status)

	def GetUserStats(self, msg):
		iter = self.GetIter(msg.user)
		if iter is None:
			return
		hspeed = Humanize(msg.avgspeed)
		hfiles = Humanize(msg.files)
		self.usersmodel.set(iter, 2, hspeed, 3, hfiles, 6, msg.avgspeed, 7, msg.files)

	def AddToList(self, user):
		if user in [i[0] for i in self.userlist]:
			return
		
		row = [self.frame.GetStatusImage(0), user, "0", "0", "", 0, 0, 0]
		iter = self.usersmodel.append(row)
		self.userlist.append([user, "", iter])
		
		self.SaveUserList()
		
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
					self.usersmodel.set(i[2], 4, comments)
					break
			self.SaveUserList()

	def SaveUserList(self):
		l = []
		for i in self.userlist:
			l.append([i[0], i[1], (i[0] in self.notify), (i[0] in self.privileged)])
		self.frame.np.config.sections["server"]["userlist"] = l
		self.frame.np.config.writeConfig()

	def RemoveFromList(self, user):
		if user in self.notify:
			self.notify.remove(user)
		if user in self.privileged:
			self.privileged.remove(user)
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
