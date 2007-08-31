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
import pango
import time
import locale
import os, sys
import string
import re
import types
import urllib
from struct import unpack
import imghdr

from pynicotine import slskmessages
from pynicotine.utils import _

DECIMALSEP = ""

URL_RE = re.compile("(\\w+\\://.+?)[\\s\\(\\)]|(www\\.\\w+\\.\\w+.*?)[\\s\\(\\)]|(mailto\\:\\w.+?)[\\s\\(\\)]")
PROTOCOL_HANDLERS = {}
CATCH_URLS = 0
HUMANIZE_URLS = 0
USERNAMEHOTSPOTS = 0
NICOTINE = None

def popupWarning(parent, title, warning, icon=None):
	dlg = gtk.Dialog(title = title, parent = parent,
		buttons = (gtk.STOCK_OK, gtk.RESPONSE_OK))
	dlg.set_default_response(gtk.RESPONSE_OK)
	dlg.set_icon(icon)
	dlg.set_border_width(10)
	dlg.vbox.set_spacing(10)
	hbox = gtk.HBox(spacing=5)
	hbox.set_border_width(5)
	hbox.show()
	dlg.vbox.pack_start(hbox)
	
	image = gtk.Image()
	image.set_padding(0, 0)
	icon = gtk.STOCK_DIALOG_WARNING
	image.set_from_stock(icon, 4)
	image.show()
	
	hbox.pack_start(image)	
	label = gtk.Label()
	label.set_markup(warning)
	label.set_line_wrap(True)
	hbox.pack_start(label, True, True)

	dlg.vbox.show_all()

	result = None
	if dlg.run() == gtk.RESPONSE_OK:
		dlg.destroy()
		
	return 0
def numfmt(value):
	v = str(float(value)) + '0000'
	i = v.index('.')
	if i < 4:
		return v[:5]
	else:
		return v[:i+2]
	
def HumanizeBytes(size):
	if size is None:
		return None

	try:
		s = int(size)
		if s >= 1000*1024*1024:
			r = _("%s GB") % numfmt(float(s) / 1073741824.0 )
		elif s >= 1000*1024:
			r = _("%s MB") % numfmt(float(s) / 1048576.0)
		elif s >= 1000:
			r = _("%s KB") % numfmt(float(s) / 1024.0)
		else:
			r = _("%s  B") % numfmt(float(s) )
		return r
	except Exception, e:
		Output(e)
		return size
	return str(size)
		
def recode(s):
	try:
		return s.decode(locale.nl_langinfo(locale.CODESET), "replace").encode("utf-8", "replace")
	except:
		return s

def recode2(s):
	try:
		return s.decode("utf-8", "replace").encode(locale.nl_langinfo(locale.CODESET), "replace")
	except:
		return s

		
def InitialiseColumns(treeview, *args):
	i = 0
	cols = []
	for c in args:
		if c[2] == "text":
			renderer = gtk.CellRendererText()
			column = gtk.TreeViewColumn(c[0], renderer, text = i)
		elif c[2] == "colored":
			renderer = gtk.CellRendererText()
			column = gtk.TreeViewColumn(c[0], renderer, text = i, foreground = c[3][0], background = c[3][1])
		elif c[2] == "edit":
			renderer = gtk.CellRendererText()
			renderer.set_property('editable', True)
			column = gtk.TreeViewColumn(c[0], renderer, text = i)
		elif c[2] == "combo":
			renderer = gtk.CellRendererCombo()
			renderer.set_property('text-column', 0)
			renderer.set_property('editable', True)
			column = gtk.TreeViewColumn(c[0], renderer, text = i)
		elif c[2] == "progress":
			renderer = gtk.CellRendererProgress()
			column = gtk.TreeViewColumn(c[0], renderer, value = i)
		elif c[2] == "toggle":
			renderer = gtk.CellRendererToggle()
			column = gtk.TreeViewColumn(c[0], renderer, active = i)
		else:
			renderer = gtk.CellRendererPixbuf()
			column = gtk.TreeViewColumn(c[0], renderer, pixbuf = 0)
		if c[1] == -1:
			column.set_resizable(False)
			column.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
		else:
			column.set_resizable(True)
			if c[1] == 0:
				column.set_sizing(gtk.TREE_VIEW_COLUMN_GROW_ONLY)
			else:
				column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
				column.set_fixed_width(c[1])
			column.set_min_width(0)
		if len(c) > 3 and type(c[3]) is not list:
			column.set_cell_data_func(renderer, c[3])
		column.set_reorderable(True)
		column.set_widget(gtk.Label(c[0]))
		column.get_widget().show()
		treeview.append_column(column)
		cols.append(column)
		i += 1
	return cols
		
def PressHeader(widget, event):
	if event.button != 3:
		return False
	columns = widget.get_parent().get_columns()
	visible_columns = [column for column in columns if column.get_visible()]
	one_visible_column = len(visible_columns) == 1
	menu = gtk.Menu()
	pos = 1
	for column in columns:
		title = column.get_title()
		if title == "":
			title = _("Column #%i") %pos
		item = gtk.CheckMenuItem(title)
		if column in visible_columns:
			item.set_active(True)
			if one_visible_column:
				item.set_sensitive(False)
		else:
			item.set_active(False)
		item.connect('activate', header_toggle, column)
		menu.append(item)
		pos += 1
	menu.show_all()
	menu.popup(None, None, None, event.button, event.time)
	return True

def header_toggle(menuitem, column):
	column.set_visible(not column.get_visible())
	NICOTINE.SaveColumns()

	
def ScrollBottom(widget):
	widget.need_scroll = 1
	va = widget.get_vadjustment()
	va.set_value(va.upper - va.page_size)
	return False

def UrlEvent(tag, widget, event, iter, url):
	if tag.last_event_type == gtk.gdk.BUTTON_PRESS and event.type == gtk.gdk.BUTTON_RELEASE and event.button == 1:
		if url[:4] == "www.":
			url = "http://" + url
		protocol = url[:url.find(":")]
		if protocol in PROTOCOL_HANDLERS:
			if PROTOCOL_HANDLERS[protocol].__class__ is types.MethodType:
				PROTOCOL_HANDLERS[protocol](url.strip())
			else:
				cmd = '%s &' % (PROTOCOL_HANDLERS[protocol] % url)

				os.system( cmd)
		else:
			try:
				import gnomevfs
			except Exception, e:
				try:
					import gnome.vfs
				except:
					pass
				else:
					gnome.url_show(url)
			else:
				try:
					gnomevfs.url_show(url)
				except:
					pass
				
	tag.last_event_type = event.type

def AppendLine(textview, line, tag = None, timestamp = None, showstamp=True, timestamp_format = "%H:%M:%S", username=None, usertag=None, scroll=True):
	def _makeurltag(buffer, tag, url):
		props = {}

		props["foreground_gdk"] = gtk.gdk.color_parse(NICOTINE.np.config.sections["ui"]["urlcolor"])
		props["underline"] = pango.UNDERLINE_SINGLE
		tag = buffer.create_tag(**props)
		tag.last_event_type = -1
		tag.connect("event", UrlEvent, url)
		return tag

	def _append(buffer, text, tag):
		iter = buffer.get_end_iter()

		if tag is not None:
			buffer.insert_with_tags(iter, text, tag)
		else:
			buffer.insert(iter, text)

	scrolledwindow = textview.get_parent()
	va = scrolledwindow.get_vadjustment()
	bottom = va.value >= (va.upper - int(va.page_size*1.5))
		
	buffer = textview.get_buffer()
	linenr = buffer.get_line_count()
	ME = 0
	if line.startswith("* "):
		ME = 1
	if NICOTINE.np.config.sections["logging"]["timestamps"] and showstamp:
		if timestamp_format and not timestamp:
			line = "%s %s\n" % (recode(time.strftime(timestamp_format)), line)
		elif timestamp_format and timestamp:
			line = "%s %s\n" % (recode(time.strftime(timestamp_format, time.localtime(timestamp))), line)
	else:
		line += "\n"
		
	match = URL_RE.search(line)
	# Highlight urls, if found and tag them
	while CATCH_URLS and match:
		start = line[:match.start()]
		url = match.group()[:-1]
		urltag = _makeurltag(buffer, tag, url)
		line = line[match.end()-1:]
		
		if USERNAMEHOTSPOTS and username != None and usertag != None and not ME:
			np = re.compile(re.escape(username))
			match = np.search(start)
			if match != None:
				start2 = start[:match.start()]
				name = match.group()[:]
				start = start[match.end():]
				_append(buffer, start2, tag)
				_append(buffer, name, usertag)
				_append(buffer, start, tag)
			else:
				_append(buffer, start, tag)
		else:
			_append(buffer, start, tag)
		if url.startswith("slsk://") and HUMANIZE_URLS:
			
			url = urllib.url2pathname( url)

		_append(buffer, url, urltag)
		match = URL_RE.search(line)
	
	
	if line:
		
		if USERNAMEHOTSPOTS and username != None and usertag != None and not ME:
			np = re.compile(re.escape(username))
			match = np.search(line)
			if match != None:
				start = line[:match.start()]
				name = match.group()[:]
				line = line[match.end():]
				_append(buffer, start, tag)
				_append(buffer, name, usertag)
				_append(buffer, line, tag)
			else:
				_append(buffer, line, tag)
		else:
			_append(buffer, line, tag)
	
	if not hasattr(scrolledwindow, "need_scroll"):
		scrolledwindow.need_scroll = 1
	if scroll and bottom and scrolledwindow.need_scroll:
		scrolledwindow.need_scroll = 0
		gobject.idle_add(ScrollBottom, scrolledwindow)
	
	return linenr
	
class ImageLabel(gtk.HBox):
	def __init__(self, label = "", image = None, onclose = None, closebutton = False, angle = 0, show_image = True):
		gtk.HBox.__init__(self)
		
		self.closebutton = closebutton
		self.angle = angle
		self._show_image = show_image
		self.notify = 0
		
		self._entered = 0
		self._pressed = 0
		
		self.onclose = onclose
		
		self.label = gtk.Label()
		if NICOTINE.np.config.sections["ui"]["tab_colors"]:
			color = NICOTINE.np.config.sections["ui"]["tab_default"]
		else:
			color = ""
		if not color:
			self.label.set_text("%s" % label)
		else:
			self.label.set_markup("<span foreground=\"%s\">%s</span>" % (color, label))
		self.label.set_alignment(0.0, 0.50)
		self.label.set_angle(angle)
		self.label.show()

		self.image = gtk.Image()
		self.set_image(image)
		
		if self._show_image:
			self.image.show()


		self._pack_children()
		self._order_children()
		
	def _pack_children(self):
		self.set_spacing(0)
		if "Box" in self.__dict__:
			for widget in self.Box.get_children():
				self.Box.remove(widget)
			self.remove(self.Box)
			self.Box.destroy()
			del self.Box

		if self.angle in ( 90, -90):
			self.Box = gtk.VBox()
		else:
			self.angle = 0
			self.Box = gtk.HBox()

		self.Box.set_spacing(2)
		self.add(self.Box)
		self.Box.show()
		
		self.Box.pack_start(self.label, True, True)
		self.Box.pack_start(self.image, False, False)
		if self.closebutton and self.onclose is not None:
			self._add_close_button()
			
	def _order_children(self):

		if self.angle == 90:
			if "button" in self.__dict__ and self.closebutton != 0:
				self.Box.reorder_child(self.button, 0)
				self.Box.reorder_child(self.image, 1)
				self.Box.reorder_child(self.label, 2)
			else:
				self.Box.reorder_child(self.image, 0)
				self.Box.reorder_child(self.label, 1)
		else:
			self.Box.reorder_child(self.label, 0)
			self.Box.reorder_child(self.image, 1)
			if "button" in self.__dict__ and self.closebutton != 0:
				self.Box.reorder_child(self.button, 2)

				
	def set_onclose(self, closebutton):
		self.closebutton = closebutton
		
		if self.closebutton:
			self._add_close_button()
		else:
			self._remove_close_button()
		self._order_children()
		
	def show_image(self, show = True):
		self._show_image = show
		
		if self._show_image:
			self.image.show()
		else:
			self.image.hide()
		
	def set_angle(self, angle):
		self.angle = angle
		self.label.set_angle(self.angle)
		self._remove_close_button()

		self._pack_children()
		self._order_children()
		
	def _add_close_button(self):
		if "button" in self.__dict__:
			return
		self.button = gtk.Button()
		img = gtk.Image()
		img.set_from_stock(gtk.STOCK_CLOSE, gtk.ICON_SIZE_MENU)
		self.button.add(img)
		if self.onclose is not None:
			self.button.connect("clicked", self.onclose)
		self.button.set_relief(gtk.RELIEF_NONE)

		self.button.show_all()
		self.Box.pack_start(self.button, False, False)
		

	def _remove_close_button(self):
		if "button" not in self.__dict__:
			return
		self.Box.remove(self.button)
		self.button.destroy()
		del self.button
		
	def set_text_color(self, notify = None, text = None):
		if notify is None:
			notify = self.notify
		else:
			self.notify = notify
		if NICOTINE.np.config.sections["ui"]["tab_colors"]:
			if notify == 1:
				color = NICOTINE.np.config.sections["ui"]["tab_changed"]
			elif notify == 2:
				color = NICOTINE.np.config.sections["ui"]["tab_hilite"]
			else:
				color = NICOTINE.np.config.sections["ui"]["tab_default"]
				
			try: 
				gtk.gdk.color_parse(color)
			except:
				color = ""
		else:
			color = ""
		if text is None:
			text = self.label.get_text()
		if not color:
			self.label.set_text("%s" % text)
			
		else:
			self.label.set_markup("<span foreground=\"%s\">%s</span>" % (color, text))
			
	def set_image(self, img):
		self.img = img
		self.image.set_from_pixbuf(img)
	
	def get_image(self):
		return self.img
		
	def set_text(self, lbl):
		if NICOTINE.np.config.sections["ui"]["tab_colors"]:
			self.set_text_color( notify = None, text = lbl)
		else:
			self.label.set_text(lbl)
		
	def get_text(self):
		return self.label.get_text()
	
class IconNotebook(gtk.Notebook):
	def __init__(self, images, angle = 0, tabclosers = False, show_image = True):
		self.tabclosers = tabclosers
		gtk.Notebook.__init__(self)
		self.images = images
		self._show_image = show_image
		self.pages = []
		self.detached_tabs = []
		self.connect("switch-page", self.dismiss_icon)
		self.connect("key_press_event", self.OnKeyPress)
		self.set_scrollable(True)
		self.angle = angle
		
	def set_tab_closers(self, closers):

		self.tabclosers = closers
		for data in self.pages:
			page, label_tab, status, label_tab_menu = data
			label_tab.set_onclose(self.tabclosers)
			
	def show_images(self, show_image = True):
		self._show_image = show_image
		for data in self.pages:
			page, label_tab, status, label_tab_menu = data
			label_tab.show_image(self._show_image)
		
	def set_tab_angle(self, angle):
		if angle == self.angle:
			return
		self.angle = angle
		for data in self.pages:
			page, label_tab, status, label_tab_menu = data
			label_tab.set_angle(angle)
			
	def OnKeyPress(self, widget, event):
		if event.state & (gtk.gdk.MOD1_MASK | gtk.gdk.CONTROL_MASK) != gtk.gdk.MOD1_MASK:
			return False
		if event.keyval in [gtk.gdk.keyval_from_name("Up"), gtk.gdk.keyval_from_name("Left")]:
			self.prev_page()
		elif event.keyval in [gtk.gdk.keyval_from_name("Down"), gtk.gdk.keyval_from_name("Right")]:
			self.next_page()
		else:
			return False
		widget.emit_stop_by_name("key_press_event")
		return True
	
	def append_page(self, page, label, onclose = None, angle = 0):
		self.set_tab_angle(angle)
		closebutton = self.tabclosers

		label_tab = ImageLabel(label, self.images["empty"], onclose, closebutton = closebutton, angle = angle, show_image = self._show_image)
		# menu for all tabs
		label_tab_menu = ImageLabel(label, self.images["empty"])
		self.pages.append([page, label_tab, 0, label_tab_menu])
		eventbox = gtk.EventBox()
		label_tab.show()
		eventbox.add(label_tab)
		eventbox.show()
		eventbox.set_events(gtk.gdk.BUTTON_PRESS_MASK)
		eventbox.connect('button_press_event', self.on_tab_click, page)
		gtk.Notebook.append_page_menu(self, page, eventbox, label_tab_menu)
		try:
			self.set_tab_reorderable(page, True)
			#self.set_tab_detachable(page, True)
		except:
			# Old PyGTK2
			pass
		
	def OnTabWindowDestroy(self, widget, page):
		if self.is_tab_detached(page):
			self.attach_tab(page, destroying=True)
			
	def detach_tab(self, page, title=_("Nicotine+")):
		label = None
		if self.is_tab_detached(page):
			return
		for i in self.pages[:]:
			if i[0] == page:
				pagewidget, label_tab, status, label_tab_menu = i
				label = label_tab.label.get_text()
				label_tab.get_parent().remove(label_tab)
				
				break

		if label is None:
			return
		for i in self.detached_tabs:
			if i[0] == label or i[1] is page:
				return
		gtk.Notebook.remove_page(self, self.page_num(page))
			
		window = gtk.Window()
		window.set_title(title)
		#window.add_accel_group(self.accel_group)
		window.set_icon(NICOTINE.images["n"])
		window.resize(600, 400)
		vbox = gtk.VBox(False, spacing=5)
		vbox.set_border_width(5)
		vbox.pack_start(page)
		vbox.show()
		window.add(vbox)
		window.connect("destroy", self.OnTabWindowDestroy, page)
		window.connect("focus_in_event", self.OnFocusIn)
		window.connect("focus_out_event", self.OnFocusOut)
		
		self.detached_tabs.append([page, label, window, False])
		window.show()
		
	def OnFocusIn(self, widget, event):
		widget.set_icon(NICOTINE.images["n"])
		for item in self.detached_tabs:
			if item[2] == widget:
				item[3] = True
				self.Focused(item[0], True)
				
	def OnFocusOut(self, widget, event):
		for item in self.detached_tabs:
			if item[2] == widget:
				item[3] = False
				self.Focused(item[0], False)

	def Focused(self, page, focused):
		pass
	
	def attach_tab(self, page, destroying=False):
		pagewidget = label_tab = label_tab_menu = label = None

		for item in self.detached_tabs:
			if item[0] is page:
				label = item[1]
				window = item[2]
				break
		if label is None or window is None:
			return
		for i in self.pages[:]:
			if i[0] == page:
				label = i[1].label.get_text()
				pagewidget, label_tab, status, label_tab_menu = i
				break
		for i in (pagewidget, label_tab, label_tab_menu, label, status):
			if i is None:
				return
		window.get_child().remove(pagewidget)
		
		#self.pages.append([page, label_tab, status, label_tab_menu])
		eventbox = gtk.EventBox()
		label_tab.show()
		eventbox.add(label_tab)
		eventbox.show()
		eventbox.set_events(gtk.gdk.BUTTON_PRESS_MASK)
		eventbox.connect('button_press_event', self.on_tab_click, page)
		gtk.Notebook.append_page_menu(self, pagewidget, eventbox, label_tab_menu)
		try:
			self.set_tab_reorderable(page, True)
		except:
			# Old PyGTK2
			pass
		self.detached_tabs.remove(item)
		if not destroying:
			window.destroy()
		
	def is_tab_detached(self, page):
		for item in self.detached_tabs:
			if item[0] is page:
				return True
		return False

	def is_detached_tab_focused(self, page):
		for item in self.detached_tabs:
			if item[0] is page:
				return item[3]
		return False
	
	def set_detached_icon(self, page, status):
		image = self.images[("empty", "online", "hilite")[status]]
		for item in self.detached_tabs:
			if item[0] is page:
				window = item[2]
				window.set_icon(image)
				
	def set_detached_tab_title(self, page, title):
		for item in self.detached_tabs:
			if item[0] is page:
				window = item[2]
				window.set_title(title)
				
	def on_tab_click(self, widget, event, child):
		pass
	
	def set_image(self, page, status):
		image = self.images[("empty", "online", "hilite")[status]]
		for i in self.pages:
			if page == i[0]:
				if status == 1 and i[2] == 2:
					return
				if i[2] != status:
					i[1].set_image(image)
					i[3].set_image(image)
					i[2] = status
				return
	
	def set_text(self, page, label):
		for i in self.pages:
			if i[0] == page:
				i[1].set_text(label)
				i[3].set_text(label)
				return
	
	def set_text_colors(self, color = None):
		for i in self.pages:
			i[1].set_text_color(color)
			
	def set_text_color(self, page, color = None):
		for i in self.pages:
			if i[0] == page:
				i[1].set_text_color(color)
				return
			
	def dismiss_icon(self, notebook, page, page_num):
		page = self.get_nth_page(page_num)
		self.set_image(page, 0)
		
		self.set_text_color(page, 0)

	def request_hilite(self, page):
		if self.is_tab_detached(page):
			if self.is_detached_tab_focused(page):
				return
			self.set_detached_icon(page, 2)
		current = self.get_nth_page(self.get_current_page())
		if current == page:
			return
		self.set_image(page, 2)
		self.set_text_color(page, 2)

	def request_changed(self, page):
		if self.is_tab_detached(page):
			if self.is_detached_tab_focused(page):
				return
			self.set_detached_icon(page, 1)
		current = self.get_nth_page(self.get_current_page())
		if current == page:
			return
		self.set_image(page, 1)
		self.set_text_color(page, 1)
	
	def remove_page(self, page):
		for i in self.pages[:]:
			if i[0] == page:
				gtk.Notebook.remove_page(self, self.page_num(page))
				i[1].destroy()
				i[3].destroy()
				self.pages.remove(i)
				return

class PopupMenu(gtk.Menu):
	def __init__(self, frame = None):
		gtk.Menu.__init__(self)
		self.frame = frame
		self.user = None
		self.useritem = None
		self.handlers = {}
		
	def setup(self, *items):
		for item in items:
			if item[0] == "":
				menuitem = gtk.MenuItem()
			elif item[0] == "USER":
				menuitem = gtk.MenuItem(item[1])
				self.useritem = menuitem
				menuitem.set_sensitive(False)
			elif item[0] == 1:
				menuitem = gtk.MenuItem(item[1])
				menuitem.set_submenu(item[2])
				if len(item) == 5 and item[4] is not None and item[3] is not None:
					self.handlers[menuitem] = menuitem.connect("activate", item[3], item[4])
				elif item[3] is not None:
					self.handlers[menuitem] = menuitem.connect("activate", item[3])
			elif item[0] == "USERMENU":
				menuitem = gtk.MenuItem(item[1])
				menuitem.set_submenu(item[2])
				if item[3] is not None:
					self.handlers[menuitem] = menuitem.connect("activate", item[3])
				self.useritem = menuitem
			elif item[0] == 2:
				menuitem = gtk.ImageMenuItem(item[1])
				menuitem.set_submenu(item[2])
				if item[3] is not None:
					self.handlers[menuitem] = menuitem.connect("activate", item[3])
				img = gtk.image_new_from_stock(item[4], gtk.ICON_SIZE_MENU)
				menuitem.set_image(img)
			else:
				if item[0][0] == "$":
					menuitem = gtk.CheckMenuItem(item[0][1:])
				elif item[0][0] == "#":
					menuitem = gtk.ImageMenuItem(item[0][1:])
					img = gtk.image_new_from_stock(item[2], gtk.ICON_SIZE_MENU)
					menuitem.set_image(img)
				elif item[0][0] == "%":
					menuitem = gtk.ImageMenuItem(item[0][1:])	
					img = gtk.Image()
					img.set_from_pixbuf(item[2])
					menuitem.set_image(img)
				else:
					menuitem = gtk.MenuItem(item[0])
				if item[1] is not None:
					self.handlers[menuitem] = menuitem.connect("activate", item[1])
			self.append(menuitem)
			menuitem.show()
		return self
				
	def clear(self):
		for widget in self.handlers.keys():
			widget.disconnect(self.handlers[widget])
			
		self.handlers.clear()
		for widget in self.get_children():
			self.remove(widget)
			widget.destroy()
		if self.useritem is not None:
			self.useritem.destroy()
			self.useritem = None

	def set_user(self, user):
		self.user = user
		if self.useritem:
			self.useritem.get_child().set_text(user)

	def get_user(self):
		return self.user
	
	def OnSearchUser(self, widget):
		self.frame.SearchMethod.set_active_iter(self.frame.searchmethods[_("User")])
		self.frame.UserSearchCombo.child.set_text(self.user)
		self.frame.MainNotebook.set_current_page(4)
		
	def OnSendMessage(self, widget):
		self.frame.privatechats.SendMessage(self.user, None, 1)
		self.frame.MainNotebook.set_current_page(1)
	
	def OnShowIPaddress(self, widget):
		self.frame.np.queue.put(slskmessages.GetPeerAddress(self.user))
	
	def OnGetUserInfo(self, widget):
		self.frame.LocalUserInfoRequest(self.user)
	
	def OnBrowseUser(self, widget):
		self.frame.BrowseUser(self.user)
	
	def OnAddToList(self, widget):
		if widget.get_active():
			self.frame.userlist.AddToList(self.user)
		else:
			self.frame.userlist.RemoveFromList(self.user)
	
	def OnBanUser(self, widget):
		if widget.get_active():
			self.frame.BanUser(self.user)
		else:
			self.frame.UnbanUser(self.user)
	
	def OnIgnoreUser(self, widget):
		if widget.get_active():
			self.frame.IgnoreUser(self.user)
		else:
			self.frame.UnignoreUser(self.user)
			
	def OnVersion(self, widget):
		self.frame.privatechats.SendMessage(self.user, "\x01VERSION\x01")
		
	def OnGivePrivileges(self, widget):
		text = InputDialog(None, _("Give privileges"), _("Give how many days of global privileges to this user?") )
		if text:
			try:
				days = int(text)
				self.frame.GivePrivileges(self.user, days)
			except Exception, e:
				print e


def InputDialog(parent, title, message, default = ""):
	dlg = gtk.Dialog(title = title, parent = parent,
		buttons = (gtk.STOCK_OK, gtk.RESPONSE_OK, gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
	dlg.set_default_response(gtk.RESPONSE_OK)
	
	dlg.set_border_width(10)
	dlg.vbox.set_spacing(10)
		
	l = gtk.Label(message)
	l.set_alignment(0, 0.5)
	dlg.vbox.pack_start(l, False, False)
		
	entry = gtk.Entry()
	entry.set_activates_default(True)
	entry.set_text(default)
	dlg.vbox.pack_start(entry, True, True)

	dlg.vbox.show_all()

	result = None
	if dlg.run() == gtk.RESPONSE_OK:
		result = entry.get_text()
		
	dlg.destroy()
		
	return result

class FastListModel(gtk.GenericTreeModel):
	COLUMNS = 1
	COLUMN_TYPES = [gobject.TYPE_STRING]
	
	def __init__(self):
		gtk.GenericTreeModel.__init__(self)
		self.data = []
	
	def on_get_flags(self):
		'''returns the GtkTreeModelFlags for this particular type of model'''
		return gtk.TREE_MODEL_LIST_ONLY
    
	def on_get_n_columns(self):
		'''returns the number of columns in the model'''
		return self.COLUMNS
    
	def on_get_column_type(self, index):
		'''returns the type of a column in the model'''
		return self.COLUMN_TYPES[index]
    
	def on_get_path(self, iter):
		'''returns the tree path (a tuple of indices at the various
		levels) for a particular node.'''
		return (iter,)
    
	def on_get_iter(self, path):
		'''returns the node corresponding to the given path.  In our
	        case, the node is the path'''
		if path[0] < len(self.data):
			return path[0]
		else:
			return None

	def on_get_value(self, iter, column):
		'''returns the value stored in a particular column for the node'''
		return self.data[iter][column]

	def on_iter_next(self, iter):
		'''returns the next node at this level of the tree'''
		if iter + 1 < len(self.data):
			return iter + 1
		else:
			return None
    
	def on_iter_children(self, iter):
		'''returns the first child of this node'''
		return 0

	def on_iter_has_child(self, iter):
		'''returns true if this node has children'''
		return False
    
	def on_iter_n_children(self, iter):
		'''returns the number of children of this node'''
		return len(self.data)
	
	def on_iter_nth_child(self, iter, n):
		'''returns the nth child of this node'''
		return n

	def on_iter_parent(self, iter):
		'''returns the parent of this node'''
		return None

def string_sort_func(model, iter1, iter2, column):
	val1 = model.get_value(iter1, column)
	val2 = model.get_value(iter2, column)
	if val1 is None:
		val1 = ""
	return locale.strcoll(val1, val2)

def int_sort_func(model, iter1, iter2, column):
	try:
		val1 = int(model.get_value(iter1, column))
	except:
		val1 = 0
	try:
		val2 = int(model.get_value(iter2, column))
	except:
		val2 = 0
	return cmp(val1, val2)

def float_sort_func(model, iter1, iter2, column):
	try:
		val1 = float(model.get_value(iter1, column))
	except:
		val1 = 0.0
	try:
		val2 = float(model.get_value(iter2, column))
	except:
		val2 = 0.0
	return cmp(val1, val2)

def WriteLog(logfile, logsdir, fn, msg):
	if logfile is None:
		oldumask = os.umask(0077)
		if not os.path.exists(logsdir):
			os.makedirs(logsdir)
		logfile = open(os.path.join(logsdir, fixpath(fn.replace(os.sep, "-")) + ".log"), 'a', 0)
		os.umask(oldumask)
	
	logfile.write("%s %s\n" % (recode(time.strftime(NICOTINE.np.config.sections["logging"]["log_timestamp"])), msg))
	logfile.flush()
	return logfile
		
def fixpath(path):
	try:
		if sys.platform == "win32":
			chars = ["?", "/", "\\", "\"", ":", ">", "<", "|", "*"]
			for char in chars:
				path = path.replace(char, "_")
		return path
	except:
		return path
		
def Humanize(number):
	fashion = DECIMALSEP
	if fashion == "" or fashion == "<None>":
		return str(number)
	elif fashion == "<space>":
		fashion = " "
	number = str(number)
	if number[0] == "-":
		neg = "-"
		number = number[1:]
	else:
		neg = ""
	ret = ""
	while number[-3:]:
		part, number = number[-3:], number[:-3]
		ret = "%s%s%s" % (part, fashion, ret)
	return neg + ret[:-1]

def is_alias(aliases, cmd):
	if not cmd:
		return False
	if cmd[0] != "/":
		return False
	cmd = cmd[1:].split(" ")
	if cmd[0] in aliases:
		return True
	return False

def expand_alias(aliases, cmd):
	def getpart(line):
		if line[0] != "(":
			return ""
		ix = 1
		ret = ""
		level = 0
		while ix < len(line):
			if line[ix] == "(":
				level = level + 1
			if line[ix] == ")":
				if level == 0:
					return ret
				else:
					level = level - 1
			ret = ret + line[ix]
			ix = ix + 1
		return ""

	if not is_alias(aliases, cmd):
		return None
	try:
		cmd = cmd[1:].split(" ")
		alias = aliases[cmd[0]]
		ret = ""
		i = 0
		while i < len(alias):
			if alias[i:i+2] == "$(":
				arg=getpart(alias[i+1:])
				if not arg:
					ret = ret + "$"
					i = i + 1
					continue
				i = i + len(arg) + 3
				args = arg.split("=",1)
				if len(args) > 1:
					default = args[1]
				else:
					default = ""
				args = args[0].split(":")
				if len(args) == 1:
					first = last = int(args[0])
				else:
					if args[0]:
						first = int(args[0])
					else:
						first = 1
					if args[1]:
						last = int(args[1])
					else:
						last = len(cmd)
				v = string.join(cmd[first:last+1])
				if not v: v = default
				ret = ret + v
			elif alias[i:i+2] == "|(":
				arg = getpart(alias[i+1:])
				if not arg:
					ret = ret + "|"
					i = i + 1
					continue
				i = i + len(arg) + 3
				for j in range(len(cmd)-1, -1, -1):
					arg = arg.replace("$%i" % j, cmd[j])
				arg = arg.replace("$@", string.join(cmd[1:], " "))
				version = sys.version_info
				if version[0] == 3 or (version[0] >= 2 and version[1] >= 4):
					import subprocess
	
					p = subprocess.Popen(arg, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, close_fds=(not sys.platform.startswith("win")))
					exit = p.wait()

					(stdout, stdin) = (p.stdout, p.stdin)
					v = stdout.read().split("\n")
					r = ""
					for l in v:
						l = l.strip()
						if l:
							r = r + l + "\n"
					ret = ret + r.strip()
					stdin.close()
					stdout.close()
				
				else:
					stdin, stdout = os.popen2(arg)
					v = stdout.read().split("\n")
					r = ""
					for l in v:
						l = l.strip()
						if l:
							r = r + l + "\n"
					ret = ret + r.strip()
					stdin.close()
					stdout.close()
					try:
						os.wait()
					except OSError, error:
						pass
					except Exception, error:
						pass
			else:
				ret = ret + alias[i]
				i = i + 1
		return ret
	except Exception, error:
		print error
		pass
	return ""

def EncodingsMenu(np, section = None, entry = None):
	if section and entry and entry in np.config.sections["server"][section]:
		encoding = np.config.sections["server"][section][entry]
	else:
		encoding = np.config.sections["server"]["enc"]

	z = []
	for enc in np.getencodings():
		z.append(enc)

	return encoding, z

def SaveEncoding(np, section, entry, encoding):
	if encoding != np.config.sections["server"]["enc"]:
		np.config.sections["server"][section][entry] = encoding
	elif entry in np.config.sections["server"][section]:
		del np.config.sections["server"][section][entry]
	np.config.writeConfig()
	
class ImportWinSlskConfig:
	def __init__(self, config, Path, Queue, Login, Rooms, BuddyList, BanList, IgnoreList, UserInfo, UserImage):
		self.config = config
		self.Path = Path
		self.Queue = Queue
		self.Login = Login
		self.Rooms = Rooms
		self.BuddyList = BuddyList
		self.BanList = BanList
		self.IgnoreList = IgnoreList
		self.UserInfo = UserInfo
		self.UserImage = UserImage
		
	def Run(self):
		if not self.check_slskdir():
			return 0
		if not self.Queue and not self.Login and not self.Rooms and not self.BuddyList and not self.IgnoreList and not self.BanList and not self.UserInfo and not self.UserImage:
			return 2

		if self.Queue:
			# Get download queue
			windownloads = self.get_downloads(self.winpath('queue2.cfg'))
		
			for i in windownloads:
				if not i in self.config.sections["transfers"]["downloads"]:
					#print i
					self.config.sections["transfers"]["downloads"].append(i)
			
		if self.BuddyList:
			# Getting userlist
			users = self.get_basic_config(self.winpath('hotlist.cfg'))
		
			for i in users:
				if not self.is_in_user_list(i, self.config.sections["server"]["userlist"]):
					#print [i,'']
					self.config.sections["server"]["userlist"].append([i, ''])
		
		if self.Login:
			# Get login and password
			(login,passw) = self.get_user_and_pass(self.winpath('login.cfg'))
			self.config.sections["server"]["login"] = login
			self.config.sections["server"]["passw"] = passw
		
		if self.Rooms:
			# Get the list of autojoined chatrooms
			chatrooms = self.get_basic_config(self.winpath('chatrooms.cfg'))
			chatrooms.append('nicotine')
		
			for i in chatrooms:
				if i not in self.config.sections["server"]["autojoin"]:
					self.config.sections["server"]["autojoin"].append(i)
		
		if self.BanList:
			# Get the list of banned users
			banlist = self.get_basic_config(self.winpath('dlbans.cfg'))
		
			for i in banlist:
				if i not in self.config.sections["server"]["banlist"]:
					self.config.sections["server"]["banlist"].append(i)
		
		if self.IgnoreList:
			# Get the list of ignored users
			ignorelist = self.get_basic_config(self.winpath('ignores.cfg'))
		
			for i in ignorelist:
				if i not in self.config.sections["server"]["ignorelist"]:
					self.config.sections["server"]["ignorelist"].append(i)
		if self.UserInfo:
			# Get userinfo and image
			(descr, imgdata) = self.get_userinfo(self.winpath('userinfo.cfg'))
			if descr:
				self.config.sections["userinfo"]['descr'] = descr.__repr__()
		if self.UserImage:
			(descr, imgdata) = self.get_userinfo(self.winpath('userinfo.cfg'))
			if imgdata:
				img = self.save_image(imgdata)
				if img != "":
					self.config.sections["userinfo"]['pic'] = img
		return 1
  
	def check_slskdir(self):
		# we check if the file queue2.cfg exists under the slsk dir
		queue2path = os.path.join(self.Path, 'queue2.cfg')
		
		if not os.access(queue2path, os.F_OK):
			return 0
		return 1


	def winpath(self, file):
		return os.path.join(self.Path, file)


	def get_downloads(self, fname):
		"""Returns the list of downloads in the queue2.cnf file
		
		The windows slsk queue2.cnf file format:
		
		- little-endian, wordsize=4
		- The file starts with 3 ints (4bytes per int).
		- First 2 ints are unknown
		- The 3rd one is the number of entries in the file
		
		Then for each download entry:
		
		- The length of the username, followed by the username
		- The length of the remote filename, followed by the remote filename
		- The length of the local dir, followed by the local dir
		
		The file can contain some unknown stuff at the end."""
		
		infile = open(fname, 'rb')
		intsize = 4
		downloads = []
		
		str = infile.read(3*intsize)
		
		i1, i2, n_entries = unpack("iii", str)
		
		for i in range(n_entries):
			length = unpack("i", infile.read(intsize))[0]
			uname = infile.read(length)
			length = unpack("i", infile.read(intsize))[0]
			remfile = infile.read(length)
			length = unpack("i", infile.read(intsize))[0]
			localdir = infile.read(length)
			downloads.append([uname, remfile, localdir])
			
		infile.close()
		return downloads
    

	def get_user_and_pass(self, fname):
		"""Returns a (user,passwd) tuple. 
		
		File format of login.cfg (see also get_downloads):
		
		- two unknown ints at the beginning
		- the number of bytes of the username, followed by the username
		- the number of bytes from the passwd, followed by the passwd
		- followed by some undetermined bytes"""
		
		
		infile = open(fname, 'rb')
		intsize = 4
		downloads = []
		
		str = infile.read(3*intsize)
		
		i1, i2, length = unpack("iii", str)
		
		user = infile.read(length)
		length = unpack("i", infile.read(intsize))[0]
		passwd = infile.read(length)
			
		infile.close()
		return (user, passwd)


	def get_basic_config(self, fname):
		"""Works for userlist, chatrooms, dlbans, etc.
		
		
		The hotlist.cnf file format (see get_downloads for more info):
		
		- The file starts with an int: the number of users in the list
		
		Then for each user:
		
		- The length of the username, followed by the username"""
		
		infile = open(fname, 'rb')
		intsize = 4
		users = []
		
		str = infile.read(1*intsize)
		
		n_entries = unpack("i", str)[0]
		for i in range(n_entries):
			length = unpack("i", infile.read(intsize))[0]
			user = infile.read(length)
			users.append(user)
			
		infile.close()
		return users


	def get_userinfo(self, fname):
		"""The userinfo file format:
		
		- an int with the size of the text part, followed by the text part
		- one byte, an indication for an image. 0 is no image, 1 is image
		- an int with the image size, followed by the image data """
		
		infile = open(fname, 'rb')
		intsize = 4
		
		imgdata = None
		
		str = infile.read(intsize)
		length = unpack("i", str)[0]
		descr = infile.read(length)
		descr = string.replace(descr, "\r", "")
		has_image = unpack("b",infile.read(1))[0]
		if has_image:
			length = unpack("i", infile.read(intsize))[0]
			imgdata = infile.read(length)
			
		infile.close()
		return (descr, imgdata)


	def save_image(self, imgdata):
		"""Save IMGDATA to file and return the filename or None."""
		if not imgdata:
			print "No image data.  No image saved."
			return ""
		
		extension = imghdr.what(None, imgdata)
		if not extension:
			# how to print to stderr in python?  (no real problem here)
			print "Could not determine image type.  Image not saved."
			return ""
		
		fname = os.path.abspath(self.config.filename + '-userinfo.' + extension)
		outfile = open(fname, "wb")
		outfile.write(imgdata)
		outfile.close()
		print "Wrote image to \"%s\"" % (fname)
		return fname


	def is_in_user_list(self, user, user_list):
		"""Checks if USER is in USER_LIST, ignoring the comment field"""
		for i in user_list:
			if type(i) == type(''):
				sys.stderr.write("\nError: The nicotine userlist is in an old pyslsk format.\n" +
				"Please run Nicotine once before running this script.\n" +
				"Config file not updated.\n")
				break
			if user == i[0]:
				return 1
		return 0

