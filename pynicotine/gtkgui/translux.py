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

class Translux:
	def __init__(self, parent, tint = 0x00000000L):
		self.tint = tint
		self.idle_tag = None
		self.subscribers = {}
		self.copied = []
		self.atom0 = gtk.gdk.atom_intern("PIXMAP")
		self.atom1 = gtk.gdk.atom_intern("ESETROOT_PMAP_ID")
		self.atom2 = gtk.gdk.atom_intern("_XROOTPMAP_ID")
		parent.connect("configure-event", self.OnConfigure)

	
	def __del__(self):
		for subscriber in self.subscribers.keys():
			try:
				self.unsubscribe(subscriber)
			except:
				pass

	def subscribe(self, widget, window):
		if window is None:
			window = widget
			widget = None

		if window not in self.subscribers:
			self.subscribers[window] = widget
			if widget is None:
				widget = window
			widget.connect("size-allocate", self.OnChildConfigure)
			widget.connect("map-event", self.OnChildConfigure)
		else:
			print "eek"
	
	def unsubscribe(self, window):
		if window in self.subscribers:
			widget = self.subscribers[window]
			if widget is None:
				widget = window
				_window = widget.window
			else:
				_window = window

			if callable(_window):
				_win = _window()
			else:
				_win = _window

			if _win != None:
				_win.set_back_pixmap(None, False)
				widget.set_style(widget.rc_get_style())
				widget.queue_draw()
			
			del self.subscribers[window]
			
			if window in self.copied:
				self.copied.remove(window)
	
	def get_root_pixmap(self):
		pixmapid = gtk.gdk.get_default_root_window().property_get(self.atom1, self.atom0)
		if not pixmapid:
			pixmapid = gtk.gdk.get_default_root_window().property_get(self.atom2, self.atom0)
		if not pixmapid:
			return None
		if hasattr(gtk.gdk, "gdk_pixmap_foreign_new"):
			pixmap = gtk.gdk.gdk_pixmap_foreign_new(long(pixmapid[2][0]))
		else:
			pixmap = gtk.gdk.pixmap_foreign_new(long(pixmapid[2][0]))
		if (gtk.gdk.screen_width(), gtk.gdk.screen_height()) != pixmap.get_size():
			return None
		return pixmap
		
	def update_window(self, _win, pixmap):
		# find widget
		widget = self.subscribers[_win]
		if widget is None:
			widget = _win
			_win = widget.window
			style = True
		else:
			style = False

		# find window, check if the win is callable
		if callable(_win):
			win = _win()
		else:
			win = _win
		
		# if the window isn't ready / realized yet, bail our
		if win is None:
			return

		# create the destination pixmap
		dw,dh = win.get_size()
		dpixmap = gtk.gdk.Pixmap(win, dw, dh)

		# create GC and copy image
		gc = dpixmap.new_gc()
		x, y = win.get_origin()
		dpixmap.draw_drawable(gc, pixmap, x, y, 0, 0, dw, dh)

		# create the tinting filter
		filter = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, True, 8, dw, dh)
		filter.fill(self.tint)
		#filter.render_to_drawable_alpha(dpixmap, 0, 0, 0, 0, dw, dh, 0, 0, 0, 0, 0)
		#dpixmap.draw_pixbuf(gc, filter, x, y, dw, dh)
		dpixmap.draw_pixbuf(gc, filter, 0, 0, 0, 0, dw, dh)
		# update the style or set the back_pixmap
		if style:
			style = widget.get_style()
			if not widget in self.copied:
				style = style.copy()
				self.copied.append(widget)
			for i in range(len(style.bg_pixmap)):
				style.bg_pixmap[i] = dpixmap
			widget.set_style(style)
		else:
			win.set_back_pixmap(dpixmap, False)

		# Force a redraw on the widget
		widget.queue_draw()
		
		
	def changeTint(self, tint):
		self.tint = tint
		self.update()
		
	def disable(self):
		for sub in self.subscribers.copy().keys():
			self.unsubscribe(sub)

		
		self.idle_tag = None
		return
		
	def update(self):
		pixmap = self.get_root_pixmap()
		if pixmap is None:
			subscribers = self.subscribers.copy()
			for sub in subscribers.keys():
				self.unsubscribe(sub)
			self.subscribers = subscribers
			return
		
		for w in self.subscribers.keys():
			self.update_window(w, pixmap)

		self.idle_tag = None

	def OnConfigure(self, widget, event):
		if self.idle_tag is None:
			self.idle_tag = gobject.idle_add(self.update)

	def OnChildConfigure(self, widget, event):
		windows = [window for window in self.subscribers.keys() if self.subscribers[window] == widget or window == widget]
		if not windows:
			return
		
		pixmap = self.get_root_pixmap()
		if pixmap is None:
			self.update()
			return
		
		for window in windows:
			self.update_window(window, pixmap)

if __name__ == "__main__":
	w = gtk.Window()
	w.connect("delete-event", gtk.main_quit)

	t = Translux(w, 0x80f0ff80L)
	w.set_style(w.get_style().copy())
	
	h = gtk.HBox()
	
	e = gtk.EventBox()
	h.add(e)
	s = gtk.ScrolledWindow()
	e.add(s)
	t.subscribe(e, None)
	usersmodel = gtk.ListStore(gobject.TYPE_STRING)
	trv = gtk.TreeView(usersmodel)
	t.subscribe(trv, lambda: trv.get_root_window())
	h.add(trv)
	renderer = gtk.CellRendererText()
	column=gtk.TreeViewColumn("d", renderer, text = 0)
	trv.append_column(column)
	
	tv = gtk.TextView()
	t.subscribe(tv, lambda: tv.get_window(gtk.TEXT_WINDOW_TEXT))
	h.add(tv)
	
	b = gtk.Button("bla")
	t.subscribe(b, None)
	h.add(b)

	w.add(h)
	w.show_all()
	
	gtk.main()
