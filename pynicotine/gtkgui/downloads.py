# Copyright (c) 2003-2004 Hyriand. All rights reserved.
#
import gtk

from transferlist import TransferList
from utils import PopupMenu
from pynicotine import slskmessages
import string, os
from pynicotine.utils import _

class Downloads(TransferList):
	def __init__(self, frame):
		TransferList.__init__(self, frame, frame.DownloadList)
		self.frame.DownloadList.set_property("rules-hint", True)
		self.accel_group = gtk.AccelGroup()
		
		
		self.popup_menu2 = popup2 = PopupMenu(frame)
		popup2.setup( 
		        ("#" + _("Clear finished/aborted"), self.OnClearFinishedAborted, gtk.STOCK_CLEAR),
			("#" + _("Clear finished"), self.OnClearFinished, gtk.STOCK_CLEAR),
			("#" + _("Clear aborted"), self.OnClearAborted, gtk.STOCK_CLEAR),
			("#" + _("Clear queued"), self.OnClearQueued, gtk.STOCK_CLEAR),
		)
		self.popup_menu_users = popup3 = PopupMenu(frame)
		popup3.setup( 
			("#" + _("Send _message"), popup3.OnSendMessage, gtk.STOCK_EDIT),
			("#" + _("Show IP a_ddress"), popup3.OnShowIPaddress, gtk.STOCK_NETWORK),
			("#" + _("Get user i_nfo"), popup3.OnGetUserInfo, gtk.STOCK_DIALOG_INFO),
			("#" + _("Brow_se files"), popup3.OnBrowseUser, gtk.STOCK_HARDDISK),
			("#" + _("Gi_ve privileges"), popup3.OnGivePrivileges, gtk.STOCK_JUMP_TO),
			("", None),
			("$" + _("_Add user to list"), popup3.OnAddToList),
			("$" + _("_Ban this user"), popup3.OnBanUser),
			("$" + _("_Ignore this user"), popup3.OnIgnoreUser),
			("#" + _("Select User's Transfers"), self.OnSelectUserTransfer, gtk.STOCK_INDEX),
		)
		self.popup_menu = popup = PopupMenu(frame)
		popup.setup(
			("#" + _("Get place in _queue"), self.OnGetPlaceInQueue, gtk.STOCK_INDEX),
			("", None),
			("#" + _("Copy _URL"), self.OnCopyURL, gtk.STOCK_COPY),
			("#" + _("Copy folder URL"), self.OnCopyDirURL, gtk.STOCK_COPY),
			("#" + _("Send to _player"), self.OnPlayFiles, gtk.STOCK_MEDIA_PLAY),
			(1, _("User"), self.popup_menu_users, self.OnPopupMenuUsers),
			("", None),
			("#" + _("_Retry"), self.OnRetryTransfer, gtk.STOCK_REDO),
			("", None),
			("#" + _("Abor_t"), self.OnAbortTransfer, gtk.STOCK_CANCEL),
			("#" + _("Abort and remove _file(s)"), self.OnAbortRemoveTransfer, gtk.STOCK_DELETE),
			("#" + _("_Clear"), self.OnClearTransfer, gtk.STOCK_CLEAR),
			("", None),
			(1, _("Clear Groups"), self.popup_menu2, None),
		)
		frame.DownloadList.connect("button_press_event", self.OnPopupMenu, "mouse")
		frame.DownloadList.connect("key-press-event", self.on_key_press_event)
		frame.clearFinishedAbortedButton.connect("clicked", self.OnClearFinishedAborted)
		frame.clearQueuedButton.connect("clicked", self.OnClearQueued)
		frame.retryTransferButton.connect("clicked", self.OnRetryTransfer)
		frame.abortTransferButton.connect("clicked", self.OnSelectAbortTransfer)
		frame.deleteTransferButton.connect("clicked", self.OnAbortRemoveTransfer)
		frame.banDownloadButton.connect("clicked", self.OnBan)
		frame.DownloadList.expand_all()

	def select_transfers(self):
		self.selected_transfers = []
		self.selected_users = []
		self.widget.get_selection().selected_foreach(self.SelectedTransfersCallback)
		
	def OnBan(self, widgets):
		self.select_transfers()
		for user in self.selected_users:
			self.frame.BanUser(user)
			
	def OnSelectAbortTransfer(self, widget):
		self.select_transfers()
		self.OnAbortTransfer(widget, False)
		
	def OnSelectUserTransfer(self, widet):
		if len(self.selected_users) != 1:
			return
		selected_user = self.selected_users[0]
		
		sel = self.frame.DownloadList.get_selection()
		fmodel = self.frame.DownloadList.get_model()
		sel.unselect_all()
		
		for item in self.transfers:
			user_file, iter, transfer = item
			user, filepath = user_file
			if selected_user == user:
				ix = fmodel.get_path(iter)
				sel.select_path(ix,)
					
		self.select_transfers()
	
	
	def on_key_press_event(self, widget, event):
		key = gtk.gdk.keyval_name(event.keyval)

		if key in ( "P", "p"):
			self.OnPopupMenu(widget, event, "keyboard")
		else:
			self.select_transfers()
			
			if key in ( "T", "t"):
				self.OnAbortTransfer(widget)
			elif key in ( "R", "r"):
				self.OnRetryTransfer(widget)
			elif key == "Delete":
				self.OnAbortTransfer(widget, True, True)

	def OnPlayFiles(self, widget, prefix = ""):
		for fn in self.selected_transfers:
			if fn.file is None:
				continue
			if os.path.exists(fn.file.name):
				os.system("%s \"%s\" &" %(self.frame.np.config.sections["players"]["default"], fn.file.name) )
				continue
			basename = string.split(fn.filename,'\\')[-1]
			if os.path.exists(self.frame.np.config.sections["transfers"]["downloaddir"]+os.sep+basename):
				os.system("%s \"%s\" &" %(self.frame.np.config.sections["players"]["default"], self.frame.np.config.sections["transfers"]["downloaddir"]+os.sep+basename ) )

	def OnPopupMenuUsers(self, widget):
		
		self.selected_transfers = []
		self.selected_users = []
		self.widget.get_selection().selected_foreach(self.SelectedTransfersCallback)

		items = self.popup_menu_users.get_children()
		
		act = False
		if len(self.selected_users) == 1:
			act = True
		items[0].set_sensitive(act)
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

		items = self.popup_menu.get_children()
		if len(self.selected_users) == 0:
			items[0].set_sensitive(False)
			items[4].set_sensitive(False)
			items[5].set_sensitive(False)
		else:
			items[0].set_sensitive(True)
			items[4].set_sensitive(True)
			items[5].set_sensitive(True)
		
		act = False
		if len(self.selected_transfers) == 1:
			act = True
		items[2].set_sensitive(act)
		items[3].set_sensitive(act)
		
		
		if len(self.selected_users) == 0:
			act = False
			for i in range(7, 12):
				items[i].set_sensitive(act)
		else:
			act = True
			for i in range(7, 12):
				items[i].set_sensitive(act)

		
		self.popup_menu.popup(None, None, None, 3, event.time)
		if kind == "keyboard":
			widget.emit_stop_by_name("key_press_event")
		elif kind == "mouse":
			widget.emit_stop_by_name("button_press_event")

		return True
		
	def update(self, transfer = None):
		TransferList.update(self, transfer)
		if transfer is None and self.frame.np.transfers is not None:
			self.frame.np.transfers.SaveDownloads()

	def OnGetPlaceInQueue(self, widget):
		self.select_transfers()
		for i in self.selected_transfers:
			if i.status != _("Queued"):
				continue
			self.frame.np.ProcessRequestToPeer(i.user, slskmessages.PlaceInQueueRequest(None, i.filename))

	def OnRetryTransfer(self, widget):
		self.select_transfers()
		for transfer in self.selected_transfers:
			if transfer.status in ["Finished", "Old"]:
				continue
			self.frame.np.transfers.AbortTransfer(transfer)
			transfer.req = None
			self.frame.np.transfers.getFile(transfer.user, transfer.filename, transfer.path, transfer)
		self.frame.np.transfers.SaveDownloads()

	def OnAbortRemoveTransfer(self, widget):
		self.select_transfers()
		self.OnAbortTransfer(widget, True)
