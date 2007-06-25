# Copyright (c) 2003-2004 Hyriand. All rights reserved.
#
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
