# Copyright (C) 2007 daelstorm. All rights reserved.
# -*- coding: utf-8 -*-
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Original copyright below
# Copyright (c) 2003-2004 Hyriand. All rights reserved.

from __future__ import division

import gtk
import gobject
from types import StringType
import string
from time import time
from math import ceil

from utils import InitialiseColumns, int_sort_func, float_sort_func

from pynicotine.logfacility import log

class TransferList:
	MINIMUM_GUI_DELAY = 0.3 # in seconds
	MINIMUM_GUI_DELAY_SLEEP = int(ceil(MINIMUM_GUI_DELAY * 2000)) # in ms
	def __init__(self, frame, widget):
		self.frame = frame
		self.widget = widget
		self.transfers = []
		self.list = None
		self.selected_transfers = []
		self.selected_users = []
		self.users = {}
		self.lastupdate = 0
		self.finalupdatetimerid = None
		widget.get_selection().set_mode(gtk.SELECTION_MULTIPLE)

		columntypes = [gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_INT , gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING,  gobject.TYPE_INT, gobject.TYPE_INT, gobject.TYPE_INT, gobject.TYPE_BOOLEAN]

		self.transfersmodel = gtk.TreeStore(*columntypes)
		self.cols = cols = InitialiseColumns(widget,
			[_("User"), 100, "text", self.CellDataFunc],
			[_("Filename"), 250, "text", self.CellDataFunc],
			[_("Status"), 140, "text", self.CellDataFunc],
			[_("Queue Position"), 50, "number", self.CellDataFunc],
			[_("Percent"), 70, "progress"],
			[_("Size"), 170, "text", self.CellDataFunc],
			[_("Speed"), 50, "number", self.CellDataFunc],
			[_("Time elapsed"), 70, "text", self.CellDataFunc],
			[_("Time left"), 70, "text", self.CellDataFunc],
			[_("Path"), 1000, "text", self.CellDataFunc],
		)
		self.col_user, self.col_filename , self.col_status, self.col_position, self.col_percent, self.col_human_size, self.col_human_speed, self.col_time_elapsed, self.col_time_left, self.col_path = cols
		#, self.col_fullpath,  self.col_int_status, self.col_int_speed, self.col_current_size, self.col_visible 
		self.col_user.set_sort_column_id(0)
		self.col_filename.set_sort_column_id(1)
		self.col_status.set_sort_column_id(2)
		
		# Only view progress renderer on transfers, not user tree parents
		self.transfersmodel.set_sort_func(2, self.status_sort_func, 2)
		self.col_position.set_sort_column_id(3)
		self.transfersmodel.set_sort_func(3, int_sort_func, 3)
		self.col_percent.set_sort_column_id(11)
		
		self.col_percent.set_attributes(self.col_percent.get_cell_renderers()[0], value=4, visible=14)
		#self.col_position.set_attributes(self.col_position.get_cell_renderers()[0], visible=14)
		
		self.col_human_size.set_sort_column_id(12)
		self.col_human_speed.set_sort_column_id(6)
		self.col_time_elapsed.set_sort_column_id(7)
		self.col_time_left.set_sort_column_id(8)
		self.col_path.set_sort_column_id(9)
		
		self.transfersmodel.set_sort_func(11, self.progress_sort_func, 4)
		#self.transfersmodel.set_sort_func(11, self.progress_sort_func, 11)
		#self.transfersmodel.set_sort_func(12, self.progress_sort_func, 12)
		#self.transfersmodel.set_sort_func(13, self.progress_sort_func, 13)
		self.transfersmodel.set_sort_func(6, float_sort_func, 6)
		#self.frame.CreateIconButton(gtk.STOCK_INDENT, "stock", self.OnToggleTree, "Group by Users")
		#self.hbox1.pack_end(self.ToggleTree, False, False)
		
		
		widget.set_model(self.transfersmodel)
		self.UpdateColours()
		
	def UpdateColours(self):
		self.frame.SetTextBG(self.widget)
		self.frame.ChangeListFont(self.widget, self.frame.np.config.sections["ui"]["transfersfont"])
		
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
		val1 = self.get_status_index(model.get_value(iter1, column))
		val2 = self.get_status_index(model.get_value(iter2, column))
		return cmp(val1, val2)
	def progress_sort_func(self, model, iter1, iter2, column):
		# We want 0% to be always below anything else,
		# so we have to look up whether we are ascending or descending
		ascending = True
		if model.get_sort_column_id()[1] == gtk.SORT_DESCENDING:
			ascending = False
		val1 = self.get_status_index(model.get_value(iter1, column))
		val2 = self.get_status_index(model.get_value(iter2, column))
		if val1 == 0 and val2 == 0:
			return 0
		if val1 == 0:
			return -1 + (ascending * 2)
		if val2 == 0:
			return 1 - (ascending * 2)
		return cmp(val1, val2)

	def InitInterface(self, list):
		self.list = list
		self.update()
		self.widget.set_sensitive(True)
		
	def ConnClose(self):
		self.widget.set_sensitive(False)
		self.list = None
		self.Clear()
		self.transfersmodel.clear()
		self.transfers = []
		self.users.clear()
		self.selected_transfers = []
		self.selected_users = []
		
	def SelectedTransfersCallback(self, model, path, iter):
		user = model.get_value(iter, 0)
		file = model.get_value(iter, 10)
		for i in self.list:
			if i.user == user and i.filename == file:
				self.selected_transfers.append(i)
				
				break
		if user not in self.selected_users:
			self.selected_users.append(user)
		
	def SelectCurrentRow(self, event, kind):
		# If nothing is selected (first click was right-click?) try to select the 
		# current row
		if self.selected_transfers == [] and self.selected_users == [] and kind == "mouse":
			d = self.widget.get_path_at_pos(int(event.x), int(event.y))
			if d:
				path, column, x, y = d
				iter = self.transfersmodel.get_iter(path)
				user = self.transfersmodel.get_value(iter, 0)
				file = self.transfersmodel.get_value(iter, 10)
				if path is not None:
					sel = self.widget.get_selection()
					sel.unselect_all()
					sel.select_path(path)
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
	
	
	def finalupdate(self, func):
		now = time()
		# I had a logical explanation about why it has to be 3*delay, but I
		# forgot. Something to do with the timeout being 2*delay
		if (now - self.lastupdate) < (3 * self.MINIMUM_GUI_DELAY):
			# The list has been updated recently,
			# trying again later.
			#print "sleeping..."
			return True 
		#print "final update!"
		self.update(forced=True) # delayed updates can never trigger a new timer
		self.finalupdatetimerid = None
		return False # Stopping timeout
	def replace(self, oldtransfer, newtransfer):
		for i in self.transfers:
			if i[2] == oldtransfer:
				i[2] = newtransfer
				self.update_specific(newtransfer)
				return
		else:
			print("WARNING: Could not find transfer %s." % oldtransfer)
	def update(self, transfer = None, forced = False):
		current_page = self.frame.MainNotebook.get_current_page()
		my_page = self.frame.MainNotebook.page_num(self.myvbox)
		if (current_page == my_page):
			self._update(transfer, forced)
		self.frame.UpdateBandwidth()
	def _update(self, transfer = None, forced = True):
		now = time()
		if forced:
			self.lastupdate = time() # ...we're working...
		if transfer is not None:
			self.update_specific(transfer)
		elif self.list is not None:
			# This seems to me to be O(n^2), perhaps constructing a temp. dict
			# from self.list would be better?
			for i in self.transfers[:]:
				for j in self.list:
					if [j.user, j.filename] == i[0]:
						break
				else:
					# Remove transfers from treeview that aren't in the transfer list
					self.transfersmodel.remove(i[1])
					self.transfers.remove(i)
			for i in self.list:
				self.update_specific(i)
		# The rest is just summarizing so it's not too important.
		# It's fairly CPU intensive though, so we only do it if we haven't updated it recently
		if not forced and (now - self.lastupdate) < self.MINIMUM_GUI_DELAY:
			#print "recently updated, not doing it again"
			if not self.finalupdatetimerid:
				self.finalupdatetimerid = True # I'm not sure if gobject returns fast enough
				#print "there's no timeout active, adding one"
				self.finalupdatetimerid = gobject.timeout_add(self.MINIMUM_GUI_DELAY_SLEEP, self.finalupdate, self.update)
			return
		self.lastupdate = time() # ...we're working...
		# Remove empty parent rows
		for (username, user) in [x for x in self.users.iteritems()]:
			if not self.transfersmodel.iter_has_child(user):
				self.transfersmodel.remove(user)
				del self.users[username]
			else:
				files = self.transfersmodel.iter_n_children(user)
				ispeed = 0.0
				percent = totalsize = position = 0
				elapsed = left = ""
				elap = 0
				salientstatus = ""
				extensions = {}
				for f in range(files):
					iter = self.transfersmodel.iter_nth_child(user, f)
					filename = self.transfersmodel.get_value(iter, 10)
					parts = filename.rsplit('.', 1)
					if len(parts) == 2:
						ext = parts[1]
						try:
							extensions[ext.lower()] += 1
						except KeyError:
							extensions[ext.lower()] = 1
					for transfer in self.list:
						if [transfer.user, transfer.filename] == [username, filename] and transfer.timeelapsed is not None:
							elap += transfer.timeelapsed
							break
					totalsize += self.transfersmodel.get_value(iter, 12)
					position += self.transfersmodel.get_value(iter, 13)
					status = self.transfersmodel.get_value(iter, 2)
						
					if status == _("Transferring"):
						str_speed = self.transfersmodel.get_value(iter, 6)
						if str_speed != "":
							ispeed += float(str_speed)
						
						left = self.transfersmodel.get_value(iter, 8)
					if salientstatus in ('',_("Finished")): # we prefer anything over ''/finished
						salientstatus = status
					if status in (_("Transferring"), _("Banned"), _("Getting address"), _("Establishing connection")):
						salientstatus = status
				try:
					speed = "%.1f" % ispeed
				except TypeError:
					speed = str(ispeed)
				if totalsize > 0:
					percent = ((100 * position)/ totalsize)
					
				if ispeed <= 0.0:
					left = "∞"
				else:
					left = self.frame.np.transfers.getTime((totalsize - position)/ispeed/1024)
				elapsed = self.frame.np.transfers.getTime(elap)
				
				if len(extensions) == 0:
					extensions = "Unknown"
				elif len(extensions) == 1:
					extensions = _("All %(ext)s") % {'ext':extensions.keys()[0]}
				else:
					extensionlst = [(extensions[key], key) for key in extensions]
					extensionlst.sort(reverse=True)
					extensions = ", ".join([str(count) + " " + ext for (count, ext) in extensionlst])
				self.transfersmodel.set(user,
						1, _("%(number)2s files ") % {'number':files} + " (" + extensions + ")",
						2, salientstatus,
						4, percent,
						5, "%s / %s" % (self.Humanize(position, None), self.Humanize(totalsize, None )),
						6, speed,
						7, elapsed,
						8, left,
						12, ispeed,
						14, True)
		self.lastupdate = time() # ...and we're done
	def update_specific(self, transfer = None):
		if not transfer in self.list:
			return
		fn = transfer.filename
		user = transfer.user
		shortfn = self.frame.np.transfers.encode(fn.split("\\")[-1], user)
		currentbytes = transfer.currentbytes
		place = transfer.place
		if currentbytes == None:
			currentbytes = 0
		
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

		elap = transfer.timeelapsed
		left = str(transfer.timeleft)
		
		if speed == "None":
			speed = ""
		if elap == None:
			elap = 0
		elap = self.frame.np.transfers.getTime(elap)
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
				continue
			self.transfersmodel.set(i[1], 1, shortfn, 2, status, 3, str(place), 4, percent, 5, str(hsize), 6, speed, 7, elap, 8, left, 9, self.frame.np.decode(transfer.path), 11, istatus, 12, size, 13, currentbytes)
			break
		else:
			newparent = False
			if self.TreeUsers:
				if user not in self.users:
					# Create Parent if it doesn't exist
					# ProgressRender not visible (last column sets 4th column)
					self.users[user] = self.transfersmodel.append(None, [user, "", "", "", 0,  "", "", "", "", "", "", 0, 0, 0,  False])
					newparent = True
					#self.col_position.set_attributes(self.col_position.get_cell_renderers()[0], visible=14)
					
				parent = self.users[user]
			else:
				parent = None
			# Add a new transfer
			
			path = self.frame.np.decode(transfer.path)
			iter = self.transfersmodel.append(parent, [user, shortfn, status, str(place), percent, str(hsize), speed, elap, left, path, fn, istatus, size, icurrentbytes, True])
			
			# Expand path
			path = self.transfersmodel.get_path(iter)
			self.transfers.append([key, iter, transfer])
			if newparent:
				self.expandcollapse(self.transfersmodel.get_path(parent))

	def Clear(self):
		self.users.clear()
		self.transfers = []
		self.selected_transfers = []
		self.selected_users = []
		self.transfersmodel.clear()

	def OnCopyURL(self, widget):
		i = self.selected_transfers[0]
		self.frame.SetClipboardURL(i.user, i.filename)
	
	def OnCopyDirURL(self, widget):
		i = self.selected_transfers[0]
		path = string.join(i.filename.split("\\")[:-1], "\\") + "\\"
		if path[:-1] != "/":
			path += "/"
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
	def OnClearFiltered(self, widget):
		statuslist = ["Filtered"]
		self.ClearTransfers(statuslist)
	def OnClearFailed(self, widget):
		statuslist = ["Cannot connect", 'Connection closed by peer', "Local file error", "Getting address", "Waiting for peer to connect", "Initializing transfer"]
		self.ClearTransfers(statuslist)
	def OnClearPaused(self, widget):
		statuslist = ["Paused"]
		self.ClearTransfers(statuslist)
	def OnClearFinishedAborted(self, widget):
		statuslist = ["Aborted","Cancelled", "Finished", "Filtered"]
		self.ClearTransfers(statuslist)
	def OnClearFinishedErred(self, widget):
		statuslist = ["Aborted", "Cancelled", "Finished", "Filtered", "Cannot connect", 'Connection closed by peer', "Local file error"]
		self.ClearTransfers(statuslist)
	def OnClearQueued(self, widget):
		self.ClearTransfers(["Queued"])
