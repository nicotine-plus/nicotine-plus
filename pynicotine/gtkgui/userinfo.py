# Copyright (c) 2003-2004 Hyriand. All rights reserved.
#
import os
import gtk
import tempfile
import gobject

from nicotine_glade import UserInfoTab
from utils import IconNotebook, PopupMenu, EncodingsMenu, SaveEncoding,  Humanize
from pynicotine import slskmessages

from pynicotine.utils import _

class UserTabs(IconNotebook):
	def __init__(self, frame, subwindow):
		IconNotebook.__init__(self, frame.images)
		self.popup_enable()
		self.set_tab_pos(gtk.POS_TOP)
		self.subwindow = subwindow
		self.frame = frame
		self.users = {}
		self.mytab = None

	def SetTabLabel(self, mytab):
		self.mytab = mytab
		
			
	def GetUserStats(self, msg):
		if self.users.has_key(msg.user):
			tab = self.users[msg.user]
			tab.speed.set_text(_("Speed: %s") %  Humanize(msg.avgspeed))
			tab.filesshared.set_text(_("Files Shared: %s") % Humanize(msg.files))
			tab.dirsshared.set_text(_("Dirs Shared: %s") % Humanize(msg.dirs))

	def GetUserStatus(self, msg):
		
		if self.users.has_key(msg.user):
			tab = self.users[msg.user]
			status = [_("Offline"), _("Away"), _("Online")][msg.status]
			self.set_text(tab.Main, "%s (%s)" % (msg.user[:15], status))

	def InitWindow(self, user, conn):
		if self.users.has_key(user):
			self.users[user].conn = conn
			self.frame.np.queue.put(slskmessages.GetUserStats(user))
		else:
			w = self.subwindow(self, user, conn)
			self.append_page(w.Main, user[:15], w.OnClose)
			self.users[user] = w
			self.frame.np.queue.put(slskmessages.GetUserStatus(user))
			self.frame.np.queue.put(slskmessages.GetUserStats(user))
			
	def ShowLocalInfo(self, user, descr, has_pic, pic, totalupl, queuesize, slotsavail):
		if self.users.has_key(user):
			self.users[user].conn = user+str(1234)
			self.frame.np.queue.put(slskmessages.GetUserStats(user))
		else:
			w = self.subwindow(self, user, user+str(1234))
			self.append_page(w.Main, user[:15], w.OnClose)
			self.users[user] = w
			self.frame.np.queue.put(slskmessages.GetUserStatus(user))
			self.frame.np.queue.put(slskmessages.GetUserStats(user))
			
		self.users[user].ShowLocalInfo(user, descr, has_pic, pic, totalupl, queuesize, slotsavail)
		self.request_changed(self.users[user].Main)
		if self.mytab is not None:
			self.frame.RequestIcon(self.mytab)
			
	def ShowInfo(self, user, msg):
		self.InitWindow(user, msg.conn)
		self.users[user].ShowInfo(msg)
		self.request_changed(self.users[user].Main)
		if self.mytab is not None:
			self.frame.RequestIcon(self.mytab)
	
	def UpdateGauge(self, msg):
		for i in self.users.values():
			if i.conn == msg.conn.conn:
				i.UpdateGauge(msg)

class UserInfo(UserInfoTab):
	def __init__(self, userinfos, user, conn):
		UserInfoTab.__init__(self, False)
		
		self.userinfos = userinfos
		self.frame = userinfos.frame
		self.user = user
		self.conn = conn
		self._descr = ""
		
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


	def ShowLocalInfo(self, user, descr, has_pic, pic, totalupl, queuesize, slotsavail):
		self.conn = None
		self._descr = descr
		
		buffer = self.descr.get_buffer()
		buffer.set_text(self.frame.np.decode(descr, self.encoding))
		
		self.uploads.set_text(_("Total uploads allowed: %i") % totalupl)
		self.queuesize.set_text(_("Queue size: %i") % queuesize)
		self.slotsavail.set_text(_("Slots available: %i") % slotsavail)

		if has_pic and pic is not None:
			try:
				loader = gtk.gdk.PixbufLoader()
				loader.write(pic)
				loader.close()
				self.image.set_from_pixbuf(loader.get_pixbuf())
			except TypeError:
				name = tempfile.mktemp()
				f = open(name,"w")
				f.write(pic)
				f.close()
				self.image.set_from_file(name)
				os.remove(name)
			except:
				self.image.set_from_pixbuf(None)
		else:
			self.image.set_from_pixbuf(None)
			

	def ShowInfo(self, msg):
		self.conn = None
		self._descr = msg.descr
		
		buffer = self.descr.get_buffer()
		buffer.set_text(self.frame.np.decode(msg.descr, self.encoding))
		
		self.uploads.set_text(_("Total uploads allowed: %i") % msg.totalupl)
		self.queuesize.set_text(_("Queue size: %i") % msg.queuesize)
		self.slotsavail.set_text(_("Slots available: %i") % msg.slotsavail)

		if msg.has_pic and msg.pic is not None:
			try:
				loader = gtk.gdk.PixbufLoader()
				loader.write(msg.pic)
				loader.close()
				self.image.set_from_pixbuf(loader.get_pixbuf())
			except TypeError:
				name = tempfile.mktemp()
				f = open(name,"w")
				f.write(msg.pic)
				f.close()
				self.image.set_from_file(name)
				os.remove(name)
			except:
				self.image.set_from_pixbuf(None)
		else:
			self.image.set_from_pixbuf(None)
		
	def UpdateGauge(self, msg):
		if msg.total == 0 or msg.bytes == 0:
			fraction = 0.0
		elif msg.bytes >= msg.total:
			fraction = 1.0
		else:
			fraction = float(msg.bytes) / msg.total
		self.progressbar.set_fraction(fraction)

	def OnSendMessage(self, widget):
		self.frame.privatechats.SendMessage(self.user)
	
	def OnShowIPaddress(self, widget):
		self.frame.np.queue.put(slskmessages.GetPeerAddress(self.user))
	
	def OnRefresh(self, widget):
		self.frame.LocalUserInfoRequest(self.user)
	
	def OnBrowseUser(self, widget):
		self.frame.BrowseUser(self.user)
	
	def OnAddToList(self, widget):
		self.frame.np.userlist.AddToList(self.user)
	
	def OnBanUser(self, widget):
		self.frame.BanUser(self.user)
	
	def OnIgnoreUser(self, widget):
		self.frame.IgnoreUser(self.user)

	def OnClose(self, widget):
		self.userinfos.remove_page(self.Main)
		del self.userinfos.users[self.user]
		self.Main.destroy()

	def OnSavePicture(self, widget):
		if self.image is None:
			return
		pixbuf = self.image.get_pixbuf()
		name = os.path.join(self.frame.np.config.sections["transfers"]["downloaddir"],self.user) + ".jpg"
		pixbuf.save(name, "jpeg", {"quality": "100"})
		self.frame.logMessage("Picture saved to " + name)

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
			buffer = self.descr.get_buffer()
			buffer.set_text(self.frame.np.decode(self._descr, self.encoding))
			SaveEncoding(self.frame.np, "userencoding", self.user, self.encoding)
