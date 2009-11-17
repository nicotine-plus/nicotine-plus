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
import gobject

class Ticker(gtk.EventBox):
	def __init__(self):
		gtk.EventBox.__init__(self)
		self.entry = gtk.Entry()
		self.entry.set_editable(False)
		self.entry.set_has_frame(False)
		self.entry.show()
		self.add(self.entry)
		self.messages = {}
		self.sortedmessages = []
		self.ix = 0
		self.source = None
		self.enable()

	def __del__(self):
		gobject.source_remove(self.source)

	def scroll(self, *args):
		if not self.messages:
			self.entry.set_text("")
			return True
		if self.ix >= len(self.messages):
			self.ix = 0
		(user, message) = self.sortedmessages[self.ix]
		self.entry.set_text("[%s]: %s" % (user, message))
		self.ix += 1
		return True
		
	def add_ticker(self, user, message):
		message = message.replace("\n", " ")
		self.messages[user] = message
		self.updatesorted()

	def remove_ticker(self, user):
		try:
			del self.messages[user]
		except KeyError:
			return
		self.updatesorted()

	def updatesorted(self):
		lst = [(user, msg) for user, msg in self.messages.iteritems()]
		lst.sort(cmp=lambda x,y: len(x[1])-len(y[1]))
		self.sortedmessages = lst

	def get_tickers(self):
		return [x for x in self.messages.iteritems()]
	def set_ticker(self, msgs):
		self.messages = msgs
		self.ix = 0
		self.scroll()

	def enable(self):
		if self.source:
			return
		self.source = gobject.timeout_add(2500, self.scroll)

	def disable(self):
		if not self.source:
			return
		gobject.source_remove(self.source)
		#self.entry.set_text("")
		self.source = None
