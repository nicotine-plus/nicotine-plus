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
		self.accel_group = gtk.AccelGroup()
		self.popup_menu = popup = PopupMenu(frame)
		popup.setup(
			(_("Get place in _queue"), self.OnGetPlaceInQueue),
			("", None),
			(_("Copy _URL"), self.OnCopyURL),
			(_("Copy folder URL"), self.OnCopyDirURL),
			(_("Send to _player"), self.OnPlayFiles),
			(_("Send _message"), popup.OnSendMessage),
			(_("Show IP a_ddress"), popup.OnShowIPaddress),
			(_("Get user i_nfo"), popup.OnGetUserInfo),
			(_("Brow_se files"), popup.OnBrowseUser),
			(_("Gi_ve privileges"), popup.OnGivePrivileges),
			("$" + _("_Add user to list"), popup.OnAddToList),
			("$" + _("_Ban this user"), popup.OnBanUser),
			("$" + _("_Ignore this user"), popup.OnIgnoreUser),
			("", None),
			(_("Abor_t"), self.OnAbortTransfer),
			(_("Abort and remove _file(s)"), self.OnAbortRemoveTransfer),
			(_("_Retry"), self.OnRetryTransfer),
			(_("_Clear"), self.OnClearTransfer),
			("", None),
			(_("Clear finished/aborted"), self.OnClearFinishedAborted),
			(_("Clear finished"), self.OnClearFinished),
			(_("Clear aborted"), self.OnClearAborted),
			(_("Clear queued"), self.OnClearQueued),
		)
		frame.DownloadList.connect("button_press_event", self.OnPopupMenu, "mouse")
 		frame.DownloadList.connect("key-press-event", self.on_key_press_event)
		frame.clearFinishedAbortedButton.connect("clicked", self.OnClearFinishedAborted)
		frame.clearQueuedButton.connect("clicked", self.OnClearQueued)
		frame.retryTransferButton.connect("clicked", self.OnRetryTransfer)
		frame.abortTransferButton.connect("clicked", self.OnSelectAbortTransfer)
		frame.deleteTransferButton.connect("clicked", self.OnAbortRemoveTransfer)
		frame.banDownloadButton.connect("clicked", self.OnBan)

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
# 		print key

	def OnPlayFiles(self, widget, prefix = ""):
		for fn in self.selected_transfers:
			if fn.file is not None:
				if os.path.exists(fn.file.name):
					os.system("%s \"%s\" &" %(self.frame.np.config.sections["players"]["default"], fn.file.name) )
					continue
				basename = string.split(fn.filename,'\\')[-1]
				if os.path.exists(self.frame.np.config.sections["transfers"]["downloaddir"]+"/"+basename):
					os.system("%s \"%s\" &" %(self.frame.np.config.sections["players"]["default"], self.frame.np.config.sections["transfers"]["downloaddir"]+"/"+basename ) )

			
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
		else:
			items[0].set_sensitive(True)
		
		act = False
		if len(self.selected_transfers) == 1:
			act = True
		items[2].set_sensitive(act)
		items[3].set_sensitive(act)

		act = False
		if len(self.selected_users) == 1:
			user = self.selected_users[0]
			self.popup_menu.set_user(user)
			act = True
			items[10].set_active(user in [i[0] for i in self.frame.np.config.sections["server"]["userlist"]])
			items[11].set_active(user in self.frame.np.config.sections["server"]["banlist"])
			items[12].set_active(user in self.frame.np.config.sections["server"]["ignorelist"])
			
		for i in range(5, 12):
			items[i].set_sensitive(act)
		
		act = len(self.selected_transfers) and True or False
		for i in range(13, 17):
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
			if i.status != "Queued":
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
