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
		self.users = {}
		widget.get_selection().set_mode(gtk.SELECTION_MULTIPLE)

		columntypes = [gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_INT , gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING,  gobject.TYPE_INT, gobject.TYPE_INT, gobject.TYPE_INT, bool]

		self.transfersmodel = gtk.TreeStore(*columntypes)
		self.cols = cols = InitialiseColumns(widget,
			[_("User"), 100, "text", self.CellDataFunc],
			[_("Filename"), 250, "text", self.CellDataFunc],
			[_("Status"), 150, "text", self.CellDataFunc],
			[_("Percent"), 70, "progress"],
			[_("Size"), 100, "text", self.CellDataFunc],
			[_("Speed"), 50, "text", self.CellDataFunc],
			[_("Time elapsed"), 70, "text", self.CellDataFunc],
			[_("Time left"), 70, "text", self.CellDataFunc],
			[_("Path"), 1000, "text", self.CellDataFunc],
		)
		cols[0].set_sort_column_id(0)
		cols[1].set_sort_column_id(1)
		cols[2].set_sort_column_id(9)
		
		# Only view progress renderer on transfers, not user tree parents
		cols[3].set_sort_column_id(3)
		cols[3].set_attributes(cols[3].get_cell_renderers()[0], value=3, visible=13)
		
		cols[4].set_sort_column_id(10)
		cols[5].set_sort_column_id(5)
		cols[6].set_sort_column_id(6)
		cols[7].set_sort_column_id(7)
		cols[8].set_sort_column_id(8)

		self.transfersmodel.set_sort_func(5, float_sort_func, 5)
			
		widget.set_model(self.transfersmodel)
		self.UpdateColours()
		
	def UpdateColours(self):
		self.frame.SetTextBG(self.widget)
		
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
		_("Waiting for upload"),
	]
	
	def CellDataFunc(self, column, cellrenderer, model, iter):
		colour = self.frame.np.config.sections["ui"]["search"]
		if colour == "":
			colour = None
		cellrenderer.set_property("foreground", colour)
		
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
		self.users.clear()
		self.selected_transfers = []
		self.selected_users = []
		
	def SelectedTransfersCallback(self, model, path, iter):
		user = model.get_value(iter, 0)
		file = model.get_value(iter, 9)
		for i in self.list:
			if i.user == user and i.filename == file:
				self.selected_transfers.append(i)
				if user not in self.selected_users:
					self.selected_users.append(user)
				break
	
	def Humanize(self, size, modifier):
		if size is None:
			return None

		if modifier == None:
			modifier = ""
		else: modifier = " " + modifier

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
			return r + modifier
		except:
			return size + modifier
	
	def update(self, transfer = None):
		if transfer is not None:
			if not transfer in self.list:
				return
			fn = transfer.filename
			currentbytes = transfer.currentbytes
			if currentbytes == None:
				currentbytes = 0
			user = transfer.user
			key = [user, fn]
			
			status = self.Humanize(transfer.status, None)
			istatus = self.get_status_index(transfer.status)
			try:
				size = int(transfer.size)
			except TypeError:
				size = 0
			hsize = self.Humanize(transfer.size, transfer.modifier)
			try:
				speed = "%.1f" % transfer.speed
			except TypeError:
				speed = str(transfer.speed)
			elap = str(transfer.timeelapsed)
			left = str(transfer.timeleft)
			
			if speed == "None":
				speed = ""
			if elap == "None":
				elap = ""
			if left == "None":
				left = ""
			try:
                                #print currentbytes
				ist = int(currentbytes)
				if  ist == int(transfer.size):
					percent = 100
				else:
					percent = ((100 * ist)/ int(size))
			except Exception, e:
                                #print e
				percent = 0

			# Modify old transfer
			for i in self.transfers:
				if i[0] != key:
					continue
				if i[2] != transfer:
					if i[2] in self.list:
						self.list.remove(i[2])
					i[2] = transfer
				self.transfersmodel.set(i[1], 2, status, 3, percent, 4, hsize, 5, speed, 6, elap, 7, left, 10, istatus, 11, size, 12, currentbytes)
				break
			else:
				# Create Parent if it doesn't exist
				if not self.users.has_key(user):
					# ProgressRender not visible (last column sets 4th column)
					self.users[user] = self.transfersmodel.append(None, [user, "", "", 0,  "", "", "", "", "", "", 0, 0, 0, False])
				# Add a new transfer
				shortfn = self.frame.np.decode(fn.split("\\")[-1])
				path = self.frame.np.decode(transfer.path)
				iter = self.transfersmodel.append(self.users[user], [user, shortfn, status, percent,  hsize, speed, elap, left, path, fn, istatus, size, currentbytes, True])
				
				# Expand path
				path = self.transfersmodel.get_path(iter)
				if path is not None:
					self.widget.expand_to_path(path)

				self.transfers.append([key, iter, transfer])

		elif self.list is not None:
			for i in self.transfers[:]:
				for j in self.list:
					if [j.user, j.filename] == i[0]:
						break
				else:
					# Remove transfers from treeview that aren't in the transfer list
					self.transfersmodel.remove(i[1])
					self.transfers.remove(i)
			for i in self.list:
				self.update(i)
		# Remove empty parent rows
		for i in self.users.keys()[:]:
			if not self.transfersmodel.iter_has_child(self.users[i]):
				self.transfersmodel.remove(self.users[i])
				del self.users[i]
			else:
				files = self.transfersmodel.iter_n_children(self.users[i])
				totalsize = position = 1
				for f in range(files):
					iter = self.transfersmodel.iter_nth_child(self.users[i], f)
					totalsize += self.transfersmodel.get_value(iter, 11)
					position += self.transfersmodel.get_value(iter, 12)
				percent = ((100 * position)/ int(totalsize))
				
				self.transfersmodel.set(self.users[i], 2, _("%s Files" %  files ), 4, self.Humanize(totalsize, None ))
				if percent:
					self.transfersmodel.set(self.users[i], 3, percent, 13, True)
				else:
					self.transfersmodel.set(self.users[i], 3, percent, 13, False)
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
		statuslist = [_("Aborted"),"Cancelled"]
		self.ClearTransfers(statuslist)

	def OnClearFinishedAborted(self, widget):
		statuslist = [_("Aborted"),"Cancelled", _("Finished"), _("Filtered")]
		self.ClearTransfers(statuslist)

	def OnClearQueued(self, widget):
		self.ClearTransfers(["Queued"])
