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

		columntypes = [gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_INT , gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING,  gobject.TYPE_INT, gobject.TYPE_INT, gobject.TYPE_INT, gobject.TYPE_BOOLEAN]

		self.transfersmodel = gtk.TreeStore(*columntypes)
		self.cols = cols = InitialiseColumns(widget,
			[_("User"), 100, "text", self.CellDataFunc],
			[_("Filename"), 250, "text", self.CellDataFunc],
			[_("Status"), 140, "text", self.CellDataFunc],
			[_("Percent"), 70, "progress"],
			[_("Size"), 170, "text", self.CellDataFunc],
			[_("Speed"), 50, "text", self.CellDataFunc],
			[_("Time elapsed"), 70, "text", self.CellDataFunc],
			[_("Time left"), 70, "text", self.CellDataFunc],
			[_("Path"), 1000, "text", self.CellDataFunc],
		)
		cols[0].set_sort_column_id(0)
		cols[1].set_sort_column_id(1)
		cols[2].set_sort_column_id(2)
		
		# Only view progress renderer on transfers, not user tree parents
		self.transfersmodel.set_sort_func(2, self.status_sort_func, 2)
		cols[3].set_sort_column_id(10)
		
		cols[3].set_attributes(cols[3].get_cell_renderers()[0], value=3, visible=13)
		
		cols[4].set_sort_column_id(11)
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
		_("Getting status"),
		_("Waiting for download"),
		_("Waiting for upload"),
		_("Getting address"),
		_("Connecting"),
		_("Waiting for peer to connect"),
		_("Cannot connect"),
		_("User logged off"),
		_("Requesting file"),
		_("Initializing transfer"),
		_('Filtered'),
		_("Download directory error"),
		_("Local file error"),
		_("File not shared"),
		_("Aborted"),
		_('Paused'),
		_("Queued"),
		_("Transferring"),
		_("Finished"),

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
	
	def status_sort_func(self, model, iter1, iter2, column):
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
				
				break
		if user not in self.selected_users:
			self.selected_users.append(user)
	
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
			
	def TranslateStatus(self, status):
		if status == "Waiting for download":
			newstatus = _("Waiting for download")
		elif status == "Waiting for upload":
			newstatus = _("Waiting for upload")
		elif status == "Requesting file":
			newstatus = _("Requesting file")
		elif status == "Initializing transfer":
			newstatus = _("Initializing transfer")
		elif status == "Cannot connect":
			newstatus = _("Cannot connect")
		elif status == "Waiting for peer to connect":
			newstatus = _("Waiting for peer to connect")
		elif status == "Connecting":
			newstatus = _("Connecting")
		elif status == "Getting address":
			newstatus = _("Getting address")
		elif status == "Getting status":
			newstatus = _("Getting status")
		elif status == "Queued":
			newstatus = _("Queued")
		elif status == "User logged off":
			newstatus = _("User logged off")
		elif status == "Aborted":
			newstatus =  _("Aborted")
		elif status == "Finished":
			newstatus = _("Finished")
		elif status == 'Paused':
			newstatus = _("Paused")
		elif status == 'Transferring':
			newstatus = _("Transferring")
		elif status == 'Filtered':
			newstatus = _('Filtered')
		elif status == 'Connection closed by peer':
			newstatus = _('Connection closed by peer')
		elif status == "File not shared":
			newstatus = _("File not shared")
		elif status == "Establishing connection":
			newstatus = _("Establishing connection")
		elif status == "Download directory error":
			newstatus = _("Download directory error")
		elif status == "Local file error":
			newstatus = _("Local file error")
		else:
			newstatus = status
		return newstatus
		
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
			
			status = self.Humanize(self.TranslateStatus(transfer.status), None)
			istatus = self.get_status_index(transfer.status)
			try:
				size = int(transfer.size)
			except TypeError:
				size = 0
			hsize = "%s / %s" % (self.Humanize(currentbytes, None), self.Humanize(size, transfer.modifier ))
			#self.Humanize(transfer.size, transfer.modifier)
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
				icurrentbytes = int(currentbytes)
				if  icurrentbytes == int(transfer.size):
					percent = 100
				else:
					percent = ((100 * icurrentbytes)/ int(size))
			except Exception, e:
                                #print e
				icurrentbytes = 0
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
					self.users[user] = self.transfersmodel.append(None, [user, "", "", 0,  "", "", "", "", "", "", 0, 0, 0,  False])
				# Add a new transfer
				shortfn = self.frame.np.decode(fn.split("\\")[-1])
				path = self.frame.np.decode(transfer.path)
				iter = self.transfersmodel.append(self.users[user], [user, shortfn, status, percent,  hsize, speed, elap, left, path, fn, istatus, size, icurrentbytes, True])
				
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
				ispeed = 0.0
				percent = totalsize = position = 0
				elapsed = left = ""
				for f in range(files):
					iter = self.transfersmodel.iter_nth_child(self.users[i], f)
					totalsize += self.transfersmodel.get_value(iter, 11)
					position += self.transfersmodel.get_value(iter, 12)
					status = self.transfersmodel.get_value(iter, 2)
					if status == _("Transferring"):
						str_speed = self.transfersmodel.get_value(iter, 5)
						if str_speed != "":
							ispeed += float(str_speed)
						elapsed = self.transfersmodel.get_value(iter, 6)
						left = self.transfersmodel.get_value(iter, 7)
					
				try:
					speed = "%.1f" % ispeed
				except TypeError:
					speed = str(ispeed)
				if totalsize > 0:
					percent = ((100 * position)/ totalsize)
				
				self.transfersmodel.set(self.users[i], 2, _("%s Files") % files , 3, percent, 4, "%s / %s" % (self.Humanize(position, None), self.Humanize(totalsize, None )), 5, speed, 6, elapsed, 7, left, 11, ispeed, 13, True)
				#self.transfersmodel.set(self.users[i],  )
				
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
			i.status = "Aborted"
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
		self.ClearTransfers(["Finished"])
	
	def OnClearAborted(self, widget):
		statuslist = ["Aborted","Cancelled"]
		self.ClearTransfers(statuslist)

	def OnClearFinishedAborted(self, widget):
		statuslist = ["Aborted","Cancelled", "Finished", "Filtered"]
		self.ClearTransfers(statuslist)

	def OnClearQueued(self, widget):
		self.ClearTransfers(["Queued"])
