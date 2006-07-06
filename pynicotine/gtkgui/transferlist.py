# Copyright (c) 2003-2004 Hyriand. All rights reserved.
#
import gtk
import gobject
from types import StringType
import string

from utils import InitialiseColumns, int_sort_func, float_sort_func

from pynicotine.utils import _

class TransferList:
	def __init__(self, frame, widget):
		self.frame = frame
		self.widget = widget
		self.transfers = []
		self.list = None
		self.selected_transfers = []
		self.selected_users = []
		
		widget.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
		
		columntypes = [gobject.TYPE_STRING for i in range(9)] + [gobject.TYPE_INT, gobject.TYPE_INT]
		self.transfersmodel = gtk.ListStore(*columntypes)
		
		cols = InitialiseColumns(widget,
			[_("Filename"), 250, "text"],
			[_("User"), 100, "text"],
			[_("Status"), 150, "text"],
			[_("Size"), 100, "text"],
			[_("Speed"), 50, "text"],
			[_("Time elapsed"), 70, "text"],
			[_("Time left"), 70, "text"],
			[_("Path"), 1000, "text"],
		)
		cols[0].set_sort_column_id(0)
		cols[1].set_sort_column_id(1)
		cols[2].set_sort_column_id(9)
		cols[3].set_sort_column_id(10)
		cols[4].set_sort_column_id(4)
		cols[5].set_sort_column_id(5)
		cols[6].set_sort_column_id(6)
		cols[7].set_sort_column_id(7)
		self.transfersmodel.set_sort_func(4, float_sort_func, 4)
			
		widget.set_model(self.transfersmodel)
	
	status_tab = [
		_("Waiting for download"),
		_("Requesting file"),
		_("Initializing transfer"),
		_("Cannot connect"),
		_("Waiting for peer to connect"),
		_("Connecting"),
		_("Getting address"),
		_("Getting status"),
		"Queued",
		_("User logged off"),
		_("Aborted"),
		_("Finished"),
	]
	
	def get_status_index(self, val):
		try:
			return int(val)
		except:
			if val in self.status_tab:
				return self.status_tab.index(val)
			else:
				return -len(self.status_tab)
	
	def status_sort_func(self, model, iter1, iter2):
		val1 = self.get_status_index(model.get_value(iter1, 2))
		val2 = self.get_status_index(model.get_value(iter2, 2))
		return cmp(val1, val2)
	
	def InitInterface(self, list):
		self.list = list
		self.update()
		
	def ConnClose(self):
		self.transfersmodel.clear()
		self.list = None
		self.transfers = []
		
	def SelectedTransfersCallback(self, model, path, iter):
		user = model.get_value(iter, 1)
		file = model.get_value(iter, 8)
		for i in self.list:
			if i.user == user and i.filename == file:
				self.selected_transfers.append(i)
				if user not in self.selected_users:
					self.selected_users.append(user)
				break
	
	def Humanize(self, size):
		if size is None:
			return None
		priv = ""
		ispriv = " " + _("(privileged)")
		isfriend = " " + _("(friend)")
		if type(size) is StringType and size[-len(ispriv):] == ispriv:
			size, priv = size[:-len(ispriv)], size[-len(ispriv):]
		elif type(size) is StringType and size[-len(isfriend):] == isfriend:
			size, priv = size[:-len(isfriend)], size[-len(isfriend):]
		try:
			s = int(size)
			if s >= 1000*1024*1024:
				r = _("%.2f GB") % ((float(s) / (1024.0*1024.0*1024.0)))
			elif s >= 1000*1024:
				r = _("%.2f MB") % ((float(s) / (1024.0*1024.0)))
			elif s >= 1000:
				r = _("%.2f KB") % ((float(s) / 1024.0))
			else:
				r = str(size)
			return r + priv
		except:
			return size + priv
	
	def update(self, transfer = None):
		if transfer is not None:
			if not transfer in self.list:
				return
			fn = transfer.filename
			user = transfer.user
			key = [user, fn]
			
			status = self.Humanize(transfer.status)
			istatus = self.get_status_index(transfer.status)
			try:
				size = int(transfer.size)
			except TypeError:
				size = 0
			hsize = self.Humanize(transfer.size)
			try:
				speed = "%.1f" % transfer.speed
			except TypeError:
				speed = str(transfer.speed)
			elap = str(transfer.timeelapsed)
			left = str(transfer.timeleft)
			
			for i in self.transfers:
				if i[0] == key:
					if i[2] != transfer:
						if i[2] in self.list:
							self.list.remove(i[2])
						i[2] = transfer
					self.transfersmodel.set(i[1], 2, status, 3, hsize, 4, speed, 5, elap, 6, left, 9, istatus, 10, size)
					break
			else:
				shortfn = self.frame.np.decode(fn.split("\\")[-1])
				path = self.frame.np.decode(transfer.path)
				iter = self.transfersmodel.append([shortfn, user, status, hsize, speed, elap, left, path, fn, istatus, size])
				self.transfers.append([key, iter, transfer])
			
		elif self.list is not None:
			for i in self.transfers[:]:
				for j in self.list:
					if [j.user, j.filename] == i[0]:
						break
				else:
					self.transfersmodel.remove(i[1])
					self.transfers.remove(i)
			for i in self.list:
				self.update(i)
		self.frame.UpdateBandwidth()
		
	def OnCopyURL(self, widget):
		i = self.selected_transfers[0]
		self.frame.SetClipboardURL(i.user, i.filename)
	
	def OnCopyDirURL(self, widget):
		i = self.selected_transfers[0]
		path = string.join(i.filename.split("\\")[:-1], "\\") + "\\"
		self.frame.SetClipboardURL(i.user, path)
		
	def OnAbortTransfer(self, widget, remove = False, clear = False):
		transfers = self.selected_transfers
		for i in transfers:
			self.frame.np.transfers.AbortTransfer(i, remove)
			i.status = _("Aborted")
			i.req = None
			if clear:
				for t in self.list[:]:
					if i.user == t.user and i.filename == t.filename:
						self.list.remove(t)
			else:
				self.update(i)
		if clear:
			self.update()

	def OnClearTransfer(self, widget):
		self.OnAbortTransfer(widget, False, True)

	def ClearTransfers(self, status):
		for i in self.list[:]:
			if i.status in status:
				if i.transfertimer is not None:
					i.transfertimer.cancel()
				self.list.remove(i)
		self.update()
		
	def OnClearFinished(self, widget):
		self.ClearTransfers([_("Finished")])
	
	def OnClearAborted(self, widget):
		statuslist = [_("Aborted"),_("Connection closed by peer"),"Cancelled", _("Cannot connect")]
		self.ClearTransfers(statuslist)

	def OnClearFinishedAborted(self, widget):
		statuslist = [_("Aborted"),_("Connection closed by peer"),"Cancelled", _("Cannot connect"), _("Finished")]
		self.ClearTransfers(statuslist)

	def OnClearQueued(self, widget):
		self.ClearTransfers(["Queued"])
