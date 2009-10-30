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
import os, sys
from time import time

from pynicotine.utils import _
from utils import OpenUri
dir_location = os.path.dirname(os.path.realpath(__file__))

class FastConfigureAssistant(object):
	def __init__(self, frame):
		self.frame = frame
		self.initphase = True # don't respond to signals unless False
		self.config = frame.np.config
		builder = gtk.Builder()
		builder.add_from_file(os.path.join(dir_location, "fastconfigure.glade"))
		self.window = builder.get_object("FastConfigureAssistant")
		builder.connect_signals(self)
		self.kids = {}
		for i in builder.get_objects():
			self.kids[i.get_name()] = i
		self.kids['hiddenport'].hide()
		numpages = self.window.get_n_pages()
		for n in xrange(numpages):
			page = self.window.get_nth_page(n)
			template = self.window.get_page_title(page)
			self.window.set_page_title(page, template % {'page':(n+1), 'pages':numpages})
		self.templates = {
				'listenport': self.kids['listenport'].get_text(),
			}
		self.initphase = False
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
		if (time() - self.config.sections["server"]["lastportstatuscheck"]) > (60 * 60 * 24 * 31):
			# More than a month ago since our last port status check
			self.kids['hiddenport'].set_active(True)
		else:
			if self.config.sections["server"]["firewalled"]:
				self.kids['portclosed'].set_active(True)
			else:
				self.kids['portopen'].set_active(True)
		self.kids['listenport'].set_markup(_(self.templates['listenport']) % {'listenport':'<b>'+str(self.frame.np.waitport)+'</b>'})
	def store(self):
		# userpasspage
		self.config.sections["server"]["login"] = self.kids['username'].get_text()
		self.config.sections["server"]["passw"] = self.kids['password'].get_text()
		# portpage
		self.config.sections['server']['firewalled'] = not self.kids['portopen'].get_active()
		self.config.sections['server']['lastportstatuscheck'] = time()
	def OnClose(self, widget):
		self.window.hide()
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
			if self.kids['portopen'].get_active() or self.kids['portclosed'].get_active():
				self.window.set_page_complete(page, True)
		elif name == 'sharepage':
			self.window.set_page_complete(page, True)
	def OnPrepare(self, widget, page):
		self.window.set_page_complete(page, False)
		self.resetcompleteness(page)
	def OnEntryChanged(self, widget, param1 = None, param2 = None, param3 = None):
		name = widget.get_name()
		print "Changed %s, %s" % (widget, name)
		self.updatecompleteness(True)
	def OnButtonPressed(self, widget):
		if self.initphase:
			return
		name = widget.get_name()
		print "Pressed %s" % (name)
		if name == "checkmyport":
			OpenUri('='.join(['http://tools.slsknet.org/porttest.php?port', str(self.frame.np.waitport)]))
		self.updatecompleteness(True)
	def updatecompleteness(self, bool):
		# very pretty -_-
		pageid = self.window.get_current_page()
		page = self.window.get_nth_page(pageid)
		self.window.set_page_complete(page, bool)

