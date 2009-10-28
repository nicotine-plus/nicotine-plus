# -*- coding: utf-8 -*-
# coding=utf-8
# Copyright (C) 2007 daelstorm. All rights reserved.
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

import gtk
import os, sys
dir_location = os.path.dirname(os.path.realpath(__file__))

class FastConfigureAssistant(object):
	def __init__(self, frame):
		self.config = frame.np.config
		builder = gtk.Builder()
		builder.add_from_file(os.path.join(dir_location, "fastconfigure.glade"))
		self.window = builder.get_object("FastConfigureAssistant")
		builder.connect_signals(self)
		self.kids = {}
		for i in builder.get_objects():
			self.kids[i.get_name()] = i
		self.populate()
	def populate(self):
		self.kids['username'].set_text(self.config.sections["server"]["login"])
		self.kids['password'].set_text(self.config.sections["server"]["passw"])
	def store(self):
		self.config.sections["server"]["login"] = self.kids['username'].get_text()
		self.config.sections["server"]["passw"] = self.kids['password'].get_text()
	def OnApply(self, widget):
		self.store()
		self.window.hide()
	def OnCancel(self, widget):
		self.window.hide()
	def resetcompleteness(self, page):
		"""Turns on the complete flag if everything required is filled in."""
		name = page.get_name()
		if name in ('welcomepage', 'summarypage'):
			self.window.set_page_complete(page, True)
		elif name == 'userpasspage':
			if (len(self.kids['username'].get_text()) > 0 and
				len(self.kids['password'].get_text()) > 0):
				self.window.set_page_complete(page, True)
		elif name == 'portpage':
			self.window.set_page_complete(page, True)
		elif name == 'sharepage':
			self.window.set_page_complete(page, True)
	def OnPrepare(self, widget, page):
		self.window.set_page_complete(page, False)
		self.resetcompleteness(page)
	def OnEntryChanged(self, widget, param1 = None, param2 = None, param3 = None):
		name = widget.get_name()
		print "Changed %s, %s" % (widget, name)
		if name == "usernameentry":
			self.updatecompleteness(True)
		if name == "passwordentry":
			self.updatecompleteness(True)
	def updatecompleteness(self, bool):
		# very pretty -_-
		pageid = self.window.get_current_page()
		page = self.window.get_nth_page(pageid)
		self.window.set_page_complete(page, bool)

