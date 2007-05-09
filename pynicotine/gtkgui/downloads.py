# Copyright (c) 2003-2004 Hyriand. All rights reserved.
#
import gtk

from transferlist import TransferList
from utils import PopupMenu
from pynicotine import slskmessages
import string, os
from pynicotine.utils import _
from entrydialog import *

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
			("#" + _("View Metadata of file(s)"), self.OnDownloadMeta, gtk.STOCK_PROPERTIES),
			("#" + _("Open Directory"), self.OnOpenDirectory, gtk.STOCK_OPEN),
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
		self.frame.ToggleTreeDownloads.set_active(self.frame.np.config.sections["transfers"]["groupdownloads"])
		frame.ToggleTreeDownloads.connect("toggled", self.OnToggleTree)
		self.OnToggleTree(None)

	def OnToggleTree(self, widget):
		self.TreeUsers = self.frame.ToggleTreeDownloads.get_active()
		self.frame.np.config.sections["transfers"]["groupdownloads"] = self.TreeUsers
		self.RebuildTransfers()

	def MetaBox(self, title="Meta Data", message="", data=None, modal= True, Search=False):
		win = MetaDialog( self.frame, message,  data, modal, Search=Search)
		win.set_title(title)
		win.set_icon(self.frame.images["n"])
		win.set_default_size(300, 100)
		win.show()
		gtk.main()
		return win.ret
	
	def SelectedResultsAllData(self, model, path, iter, data):
		if iter in self.selected_users:
			return

		user = model.get_value(iter, 0)
		filename = model.get_value(iter, 1)
		fullname = model.get_value(iter, 9)
		size = speed = "0"
		length = bitrate = None
		queue = immediate = num = country = ""
		for transfer in self.frame.np.transfers.downloads:
			if transfer.user == user and fullname == transfer.filename:
				size = self.Humanize(transfer.size, None)
				try:
					speed = str(int(transfer.speed))
					speed += _(" KB/s")
				except: pass
				bitratestr = str(transfer.bitrate)
				length = str(transfer.length)
		directory = fullname.rsplit("\\", 1)[0]

		data[len(data)] = {"user":user, "fn": fullname, "position":num, "filename":filename, "directory":directory, "size":size, "speed":speed, "queue":queue, "immediate":immediate, "bitrate":bitratestr, "length":length, "country":country}

		
	def OnDownloadMeta(self, widget):
		if not self.frame.np.transfers:
			return
		data = {}
		self.widget.get_selection().selected_foreach(self.SelectedResultsAllData, data)

		if data != {}:	
			self.MetaBox(title=_("Nicotine+:")+" "+_("Downloads Metadata"), message=_("<b>Metadata</b> for Downloads"), data=data, modal=True, Search=False)
			
	def OnOpenDirectory(self, widget):

		downloaddir =  self.frame.np.config.sections["transfers"]["downloaddir"]
		incompletedir = self.frame.np.config.sections["transfers"]["incompletedir"]
		if incompletedir == "":
			incompletedir = downloaddir
		filemanager_config = self.frame.np.config.sections["ui"]["filemanager"]
		transfer = self.selected_transfers[0]

		filemanager = filemanager_config.split()[0]
		filemanager_args = filemanager_config.split(filemanager)[1]
                arg = filemanager_args.split('$')[0].strip()
		complete_path = os.path.join(downloaddir, transfer.path)
		arg_list = []
		arg_list.append(filemanager)

		for i in arg.split():
			arg_list.append(i)

		if transfer.path is "":
			if transfer.status is "Finished":
				arg_list.append(downloaddir)
			else:
				arg_list.append(incompletedir)
		elif os.path.exists(complete_path): # and tranfer.status is "Finished"
			arg_list.append(complete_path)
		else:
			arg_list.append(incompletedir)

		os.spawnvp(os.P_WAIT, filemanager, arg_list)
	
	def RebuildTransfers(self):
		if self.frame.np.transfers is None:
			return
		self.Clear()
		for transfer in self.frame.np.transfers.downloads:
			self.update(transfer)
			
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
		executable = self.frame.np.config.sections["players"]["default"]
		downloaddir = self.frame.np.config.sections["transfers"]["downloaddir"]
		if "$" not in executable:
			return
		commandargs = executable.split(" ")
		pos = commandargs.index("$")
		for fn in self.selected_transfers:
			if fn.file is None:
				continue
			command = commandargs
			if os.path.exists(fn.file.name):
				command[pos] = fn.file.name
			else:
				basename = string.split(fn.filename, '\\')[-1]
				path = os.sep.join([downloaddir, basename])
				if os.path.exists(path):
					command[pos] = path
			if command[pos] == "$":
				continue
			os.spawnlp(os.P_NOWAIT, command[0], *command)


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
		
		
		self.SelectCurrentRow(event, kind)
		
		items = self.popup_menu.get_children()
		if len(self.selected_users) != 1:
			items[6].set_sensitive(False) # Users Menu
		else:
			items[6].set_sensitive(True) # Users Menu
		if len(self.selected_transfers) == 0:
			act = False
		else:
			act = True
		items[0].set_sensitive(act) # Place
		items[4].set_sensitive(act) # Send to player
		items[5].set_sensitive(act) # View Meta
		
			
		
		act = False
		if len(self.selected_transfers) == 1:
			act = True
		items[2].set_sensitive(act) # Copy URL
		items[3].set_sensitive(act) # Copy Folder URL
		
		
		if len(self.selected_users) == 0 or len(self.selected_transfers) == 0:
			# Disable options
			# Abort, Abort and Remove, retry, clear
			act = False
			for i in range(7, 13):
				items[i].set_sensitive(act)
		else:
			act = True
			for i in range(7, 13):
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
