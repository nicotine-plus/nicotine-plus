# -*- coding: utf-8 -*-
# coding=utf-8
# Copyright (C) 2009 quinox. All rights reserved.
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

import gtk
import gobject
import os, sys
import thread
from os.path import exists, join
from time import time

from pynicotine.utils import _
from dirchooser import ChooseDir
from utils import OpenUri, InitialiseColumns, recode, HumanSize
dir_location = os.path.dirname(os.path.realpath(__file__))

def dirstats(directory):
	from os.path import join, getsize
	totaldirs = 0
	totalfiles = 0
	totalsize = 0
	extensions = {}
	for root, dirs, files in os.walk(directory):
		totaldirs += len(dirs)
		totalfiles += len(files)
		for f in files:
			try:
				totalsize += getsize(join(root, f))
			except OSError:
				pass
			parts = f.rsplit('.', 1)
			if len(parts) == 2 and len(parts[1]) < 5:
				try:
					extensions[parts[1]] += 1
				except KeyError:
					extensions[parts[1]] = 1
	return totaldirs, totalfiles, totalsize, extensions
def widgetname(widget):
	"""Raises AttributeError if given widget has no name property whatsoever."""
	try:
		return gtk.Buildable.get_name(widget) # New GTK way
	except TypeError:
		return widget.get_name() # Old GTK way
    
class FastConfigureAssistant(object):
	def __init__(self, frame):
		self.frame = frame
		self.initphase = True # don't respond to signals unless False
		self.config = frame.np.config
		builder = gtk.Builder()
		builder.add_from_file(join(dir_location, "fastconfigure.glade"))
		self.window = builder.get_object("FastConfigureAssistant")
		builder.connect_signals(self)
		self.kids = {}
		for i in builder.get_objects():
			try:
				self.kids[widgetname(i)] = i
			except AttributeError:
				pass
		numpages = self.window.get_n_pages()
		for n in xrange(numpages):
			page = self.window.get_nth_page(n)
			template = self.window.get_page_title(page)
			self.window.set_page_title(page, template % {'page':(n+1), 'pages':numpages})
		self.templates = {
				'listenport': self.kids['listenport'].get_text(),
			}
		# Page specific, sharepage
		# column -1 is the raw byte/unicode object for the folder (not shown)
		self.sharelist = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING)
		columns = InitialiseColumns(self.kids['shareddirectoriestree'],
			[_("Directory"), 0, "text"],
			[_("Size"), 0, "text"],
			[_("Files"), 0, "text"],
			[_("Dirs"), 0, "text"],
			[_("File types"), 0, "text"],
		)
		self.kids['shareddirectoriestree'].set_model(self.sharelist)
		self.kids['shareddirectoriestree'].get_selection().set_mode(gtk.SELECTION_MULTIPLE)
		self.initphase = False
		#self.show() # DEBUG
		#self.window.set_current_page(3) # DEBUG
	def show(self):
		self.initphase = True
		self._populate()
		self.initphase = False
		self.window.show()
	def _populate(self):
		# userpasspage
		self.kids['username'].set_text(self.config.sections["server"]["login"])
		self.kids['password'].set_text(self.config.sections["server"]["passw"])
		# portpage
		self.kids['advancedports'].set_expanded(self.config.sections["server"]["upnp"])
		if (time() - self.config.sections["server"]["lastportstatuscheck"]) > (60 * 60 * 24 * 31) or self.config.sections["server"]["upnp"]:
			# More than a month ago since our last port status check
			self.kids['portopen'].set_active(False)
			self.kids['portclosed'].set_active(False)
			self.kids['porthidden'].set_active(True)
		else:
			if self.config.sections["server"]["firewalled"]:
				self.kids['portclosed'].set_active(True)
			else:
				self.kids['portopen'].set_active(True)
		self.kids['lowerport'].set_value(self.config.sections["server"]["portrange"][0])
		self.kids['upperport'].set_value(self.config.sections["server"]["portrange"][1])
		self.kids['useupnp'].set_active(self.config.sections["server"]["upnp"])
		# sharepage
		if self.config.sections['transfers']['downloaddir']:
			self.kids['downloaddir'].set_current_folder(self.config.sections['transfers']['downloaddir'])
		self.sharelist.clear()
		if self.config.sections["transfers"]["friendsonly"] and self.config.sections["transfers"]["enablebuddyshares"]: 
			for directory in self.config.sections["transfers"]["buddyshared"]: 
				self.addshareddir(directory) 
		else: 
			for directory in self.config.sections["transfers"]["shared"]: 
				self.addshareddir(directory) 
		self.kids['onlysharewithfriends'].set_active(self.config.sections["transfers"]["friendsonly"])
		# If the user has a public share and a buddy share we cannot update this from FastConfigure (we only have 1 list of dirs)
		self.caneditshare = (not self.config.sections["transfers"]["enablebuddyshares"] or self.config.sections["transfers"]["friendsonly"])
		self.kids['onlysharewithfriends'].set_sensitive(self.caneditshare)
		self.kids['addshare'].set_sensitive(self.caneditshare)
		self.kids['removeshares'].set_sensitive(self.caneditshare)
		self.kids['shareddirectoriestree'].set_sensitive(self.caneditshare)
	def store(self):
		# userpasspage
		self.config.sections["server"]["login"] = self.kids['username'].get_text()
		self.config.sections["server"]["passw"] = self.kids['password'].get_text()
		# portpage
		self.config.sections['server']['firewalled'] = not self.kids['portopen'].get_active()
		self.config.sections['server']['lastportstatuscheck'] = time()
		# sharepage
		self.config.sections['transfers']['downloaddir'] = self.kids['downloaddir'].get_current_folder()
		if self.caneditshare:
			self.config.sections["transfers"]["friendsonly"] = self.kids['onlysharewithfriends'].get_active()
			if self.config.sections["transfers"]["friendsonly"] and self.config.sections["transfers"]["enablebuddyshares"]:
				self.config.sections["transfers"]["buddyshared"] = self.getshareddirs()
			else:
				self.config.sections["transfers"]["shared"] = self.getshareddirs()
	def OnClose(self, widget):
		self.window.hide()
	def OnApply(self, widget):
		self.store()
		self.window.hide()
		if not self.frame.np.serverconn:
			self.frame.OnFirstConnect(-1)
	def OnCancel(self, widget):
		self.window.hide()
	def updatepage(self, page):
		"""Updates information on the given page with. Use _populate if possible"""
		if not page:
			return
		name = widgetname(page)
		if name == 'portpage':
			self.kids['listenport'].set_markup(_(self.templates['listenport']) % {'listenport':'<b>'+str(self.frame.np.waitport)+'</b>'})
		#else:
		#	print "Unknown page %s" % (name,)
	def resetcompleteness(self, page = None):
		"""Turns on the complete flag if everything required is filled in."""
		# Never use self.config.sections here, only self.kids. 
		complete = False
		if not page:
			pageid = self.window.get_current_page()
			page = self.window.get_nth_page(pageid)
			if not page:
				return
		name = widgetname(page)
		if name == 'welcomepage':
			complete = True
		elif name == 'userpasspage':
			if (len(self.kids['username'].get_text()) > 0 and
				len(self.kids['password'].get_text()) > 0):
				complete = True
		elif name == 'portpage':
			if self.kids['useupnp'].get_active():
				complete = True
			else:
				if self.kids['portopen'].get_active() or self.kids['portclosed'].get_active():
					complete = True
		elif name == 'sharepage':
			if exists(self.kids['downloaddir'].get_filename()):
				complete = True
		elif name == 'summarypage':
			complete = True
			showcpwarning = (self.kids['portclosed'].get_active() and not self.kids['useupnp'].get_active())
			if showcpwarning:
				self.kids['labelclosedport'].show()
				self.kids['warningclosedport'].show()
			else:
				self.kids['labelclosedport'].hide()
				self.kids['warningclosedport'].hide()
			shownfwarning = (self.kids['onlysharewithfriends'].get_active() or len(self.getshareddirs()) == 0)
			if shownfwarning:
				self.kids['labelnoshare'].show()
				self.kids['warningnoshare'].show()
			else:
				self.kids['labelnoshare'].hide()
				self.kids['warningnoshare'].hide()
		#else:
		#	print "Unknown page with name " + name
		self.window.set_page_complete(page, complete)
	def OnPrepare(self, widget, page):
		self.window.set_page_complete(page, False)
		self.updatepage(page)
		self.resetcompleteness(page)
	def OnEntryChanged(self, widget, param1 = None, param2 = None, param3 = None):
		name = widgetname(widget)
		#print "Changed %s, %s" % (widget, name)
		self.resetcompleteness()
	def getshareddirs(self):
		iter = self.sharelist.get_iter_root()
		dirs = []
		while iter is not None:
			dirs.append(self.sharelist.get_value(iter, 5))
			iter = self.sharelist.iter_next(iter)
		return dirs
	def addshareddir(self, directory):
		iter = self.sharelist.get_iter_root()
		while iter is not None:
			if directory == self.sharelist.get_value(iter, 5):
				return
			iter = self.sharelist.iter_next(iter)
		self.sharelist.append([recode(directory), "", "", "", _("Counting files..."), directory])
		thread.start_new_thread(self._addsharedir, (directory,))
	def _addsharedir(self, directory):
		subdirs, files, size, extensions = dirstats(directory)
		exts = []
		for ext, count in extensions.iteritems():
			exts.append((count, ext))
		exts.sort(reverse=True)
		extstring = ", ".join(["%s %s" % (count, ext) for count, ext in exts[:5]])
		if len(exts) > 5:
			extstring += ", ..."
		gobject.idle_add(self._updatedirstats, directory, recode(directory), HumanSize(size), files, subdirs, extstring)
	def _updatedirstats(self, directory, directorystring, size, files, subdirs, extensions):
		iter = self.sharelist.get_iter_root()
		while iter is not None:
			if directory == self.sharelist.get_value(iter, 5):
				self.sharelist.insert_after(iter, [recode(directory), HumanSize(size), files, subdirs, extensions, directory])
				self.sharelist.remove(iter)
				return
			iter = self.sharelist.iter_next(iter)
	def OnButtonPressed(self, widget):
		if self.initphase:
			return
		name = widgetname(widget)
		#print "Pressed %s" % (name)
		if name == "checkmyport":
			OpenUri('='.join(['http://tools.slsknet.org/porttest.php?port', str(self.frame.np.waitport)]))
		if name == "addshare":
			selected = ChooseDir(self.window.get_toplevel(), title=_("Nicotine+")+": "+_("Add a shared directory"))
			if selected:
				for directory in selected:
					self.addshareddir(directory)
		if name == "removeshares":
			model, paths = self.kids['shareddirectoriestree'].get_selection().get_selected_rows()
			refs = [gtk.TreeRowReference(model, x) for x in paths]
			for i in refs:
				self.sharelist.remove(self.sharelist.get_iter(i.get_path()))
		self.resetcompleteness()
	def OnToggled(self, widget):
		name = widgetname(widget)
		if name == 'useupnp':
			# Setting active state
			if widget.get_active():
				self.kids['portopen'].set_inconsistent(True)
				self.kids['portclosed'].set_inconsistent(True)
			else:
				self.kids['portopen'].set_inconsistent(False)
				self.kids['portclosed'].set_inconsistent(False)
			# Setting sensitive state
			inverse = not widget.get_active()
			self.kids['portopen'].set_sensitive(inverse)
			self.kids['portclosed'].set_sensitive(inverse)
			self.kids['checkmyport'].set_sensitive(inverse)
			self.resetcompleteness()
		if self.initphase:
			return
		# Setting changing
		#print "toggled on " + name
		self.resetcompleteness()
	def OnSpinbuttonChangeValue(self, widget, scrolltype):
		if self.initphase:
			return
		name = widgetname(widget)
		#print "pre spinval on " + name
		self.resetcompleteness()
	def OnSpinbuttonValueChanged(self, widget):
		if self.initphase:
			return
		name = widgetname(widget)
		#print "post spinval on " + name
		if name == "lowerport":
			if widget.get_value() > self.kids['upperport'].get_value():
				self.kids['upperport'].set_value(widget.get_value())
		if name == "upperport":
			if widget.get_value() < self.kids['lowerport'].get_value():
				self.kids['lowerport'].set_value(widget.get_value())
		self.resetcompleteness()
	def OnKeyPress(self, widget, event):
		if event.keyval == gtk.gdk.keyval_from_name("Esc"):
			self.OnCancel(None)
