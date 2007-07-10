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
		self.label = gtk.Label()
		self.label.set_alignment(0, 0.50)
		self.label.show()
		self.add(self.label)
		self.messages = {}
		self.ix = 0
		self.source = None
		self.enable()

	def __del__(self):
		gobject.source_remove(self.source)

	def scroll(self, *args):
		if not self.messages:
			self.label.set_text("")
			return True
		if self.ix >= len(self.messages):
			self.ix = 0
		user = self.messages.keys()[self.ix]
		message = self.messages[user]
		self.label.set_text("[%s]: %s" % (user, message))
		self.ix += 1
		return True
		
	def add_ticker(self, user, message):
		message = message.replace("\n", " ")
		self.messages[user] = message

	def remove_ticker(self, user):
		del self.messages[user]

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
		self.label.set_text("")
		self.source = None
