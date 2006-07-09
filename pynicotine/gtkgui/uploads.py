# Copyright (c) 2003-2004 Hyriand. All rights reserved.
#
import gtk

from transferlist import TransferList
from utils import PopupMenu
import string, os
from pynicotine.utils import _

class Uploads(TransferList):
	def __init__(self, frame):
		TransferList.__init__(self, frame, frame.UploadList)
		self.frame = frame
		self.frame.UploadList.set_property("rules-hint", True)
		self.popup_menu2 = popup2 = PopupMenu(frame)
		popup2.setup( 
		        (_("Clear finished/aborted"), self.OnClearFinishedAborted),
			(_("Clear finished"), self.OnClearFinished),
			(_("Clear aborted"), self.OnClearAborted),
			(_("Clear queued"), self.OnClearQueued),
		)
		self.popup_menu_users = popup3 = PopupMenu(frame)
		popup3.setup( 
			(_("Send _message"), popup3.OnSendMessage),
			(_("Show IP a_ddress"), popup3.OnShowIPaddress),
			(_("Get user i_nfo"), popup3.OnGetUserInfo),
			(_("Brow_se files"), popup3.OnBrowseUser),
			(_("Gi_ve privileges"), popup3.OnGivePrivileges),
			("", None),
			("$" + _("_Add user to list"), popup3.OnAddToList),
			("$" + _("_Ban this user"), popup3.OnBanUser),
			("$" + _("_Ignore this user"), popup3.OnIgnoreUser),
		)
		
			
		self.popup_menu = popup = PopupMenu(frame)
		popup.setup(
			(_("Copy _URL"), self.OnCopyURL),
			(_("Copy folder URL"), self.OnCopyDirURL),
			(_("Send to _player"), self.OnPlayFiles),
			(1, _("User"), self.popup_menu_users, self.OnPopupMenuUsers),
			("", None),
			(_("Abor_t"), self.OnAbortTransfer),
			(_("_Clear"), self.OnClearTransfer),
			("", None),
			(1, _("Clear Groups"), self.popup_menu2, None),
		)
		frame.UploadList.connect("button_press_event", self.OnPopupMenu, "mouse")
 		frame.UploadList.connect("key-press-event", self.on_key_press_event)
		frame.clearUploadFinishedAbortedButton.connect("clicked", self.OnClearFinishedAborted)
		frame.clearUploadQueueButton.connect("clicked", self.OnClearQueued)
		frame.abortUploadButton.connect("clicked", self.OnAbortTransfer)
		frame.abortUserUploadButton.connect("clicked", self.OnAbortUser)
		frame.banUploadButton.connect("clicked", self.OnBan)

	def select_transfers(self):
		self.selected_transfers = []
		self.selected_users = []
		self.widget.get_selection().selected_foreach(self.SelectedTransfersCallback)
		
	def OnBan(self, widget):
		self.select_transfers()
		for user in self.selected_users:
			self.frame.BanUser(user)
			
	def OnAbortUser(self, widget):
		self.select_transfers()
		for user in self.selected_users:
			for i in self.list[:]:
				if i.user == user:
					if i not in self.selected_transfers:
						self.selected_transfers.append(i)
					
		TransferList.OnAbortTransfer(self, widget, False, False)
		self.frame.np.transfers.calcUploadQueueSizes()
		self.frame.np.transfers.checkUploadQueue()


	def on_key_press_event(self, widget, event):
		key = gtk.gdk.keyval_name(event.keyval)

 		if key in ( "P", "p"):
 			self.OnPopupMenu(widget, event, "keyboard")
		else:
			self.selected_transfers = []
			self.selected_users = []
			self.widget.get_selection().selected_foreach(self.SelectedTransfersCallback)
			
			if key in ( "T", "t"):
				self.OnAbortTransfer(widget)
			elif key == "Delete":
				self.OnAbortTransfer(widget, False, True)

	def OnPlayFiles(self, widget, prefix = ""):
		for fn in self.selected_transfers:
			s = fn.filename.replace("\\", "/")
			if os.path.exists(s):
				os.system("%s \"%s\" &" %(self.frame.np.config.sections["players"]["default"], s) )

	def OnPopupMenuUsers(self, widget):
		
		self.selected_transfers = []
		self.selected_users = []
		self.widget.get_selection().selected_foreach(self.SelectedTransfersCallback)

		items = self.popup_menu_users.get_children()

		if len(self.selected_users) == 0:
			items[0].set_sensitive(False)
		else:
			items[0].set_sensitive(True)
		
		act = False
		if len(self.selected_users) == 1:
			act = True
		items[1].set_sensitive(act)
		items[2].set_sensitive(act)
		items[3].set_sensitive(act)

		act = False
		if len(self.selected_users) == 1:
			user = self.selected_users[0]
			self.popup_menu_users.set_user(user)
			
			act = True
			items[6].set_active(user in [i[0] for i in self.frame.np.config.sections["server"]["userlist"]])
			items[7].set_active(user in self.frame.np.config.sections["server"]["banlist"])
			items[8].set_active(user in self.frame.np.config.sections["server"]["ignorelist"])
		
		for i in range(4, 9):
			items[i].set_sensitive(act)

		return True
		
	def OnPopupMenu(self, widget, event, kind):
		if kind == "mouse":
			if event.button != 3:
				return False
		
		self.selected_transfers = []
		self.selected_users = []
		self.widget.get_selection().selected_foreach(self.SelectedTransfersCallback)

		#items = self.popup_menu.get_children()

		#act = False
		#if len(self.selected_transfers) == 1:
			#act = True
		#items[0].set_sensitive(act)
		#items[1].set_sensitive(act)

		#act = False
		#if len(self.selected_users) == 1:
			#user = self.selected_users[0]
			#self.popup_menu.set_user(user)
			#act = True
			#items[8].set_active(user in [i[0] for i in self.frame.np.config.sections["server"]["userlist"]])
			#items[9].set_active(user in self.frame.np.config.sections["server"]["banlist"])
			#items[10].set_active(user in self.frame.np.config.sections["server"]["ignorelist"])

		#for i in range(3, 9):
			#items[i].set_sensitive(act)
		
		#act = len(self.selected_transfers) and True or False
		#for i in range(10, 12):
			#items[i].set_sensitive(act)
		
		items = self.popup_menu.get_children()
		if len(self.selected_users) == 0:
			act = False
		else:
			act = True
		items[2].set_sensitive(act)
		items[3].set_sensitive(act)
		for i in range(4, 8):
			items[i].set_sensitive(act)
			
		act = False
		if len(self.selected_transfers) == 1:
			act = True
		items[0].set_sensitive(act)
		items[1].set_sensitive(act)
		
				
		self.popup_menu.popup(None, None, None, 3, event.time)
		if kind == "keyboard":
			widget.emit_stop_by_name("key_press_event")
		elif kind == "mouse":
 			widget.emit_stop_by_name("button_press_event")
		return True
		
	def ClearByUser(self, user):
		for i in self.list[:]:
			if i.user == user:
				if i.transfertimer is not None:
					i.transfertimer.cancel()
				self.list.remove(i)
		self.frame.np.transfers.calcUploadQueueSizes()
		self.frame.np.transfers.checkUploadQueue()
		self.update()

	def OnAbortTransfer(self, widget, remove = False, clear = False):
		self.select_transfers()
		TransferList.OnAbortTransfer(self, widget, remove, clear)
		self.frame.np.transfers.calcUploadQueueSizes()
		self.frame.np.transfers.checkUploadQueue()

	def OnClearQueued(self, widget):
		self.select_transfers()
		TransferList.OnClearQueued(self, widget)
		self.frame.np.transfers.calcUploadQueueSizes()
