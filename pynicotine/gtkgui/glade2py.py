#!/usr/bin/python
# -*- coding: utf-8 -*-
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

indent = "\t"
class Widget:
	def __init__(self, my_class, id):
		self.my_class = my_class
		self.id = id
		self.attrs = {}
		self.children = []
		self.packing = {}
		self.signals = {}
		self.internalchildren = {}
		self.accelerators = []

attrs = [
	["title", lambda w, v: "%s.set_title(_(\"%s\"))" %(w, v.replace("\"", "\\\""))],
	["active", lambda w, v: "%s.set_active(%s)" % (w, v.capitalize())],
	["label", lambda w, v: "%s.set_label(_(\"%s\"))" %(w, v.replace("\"", "\\\"").replace("\n", "\\n"))],
	["window_position", lambda w,v: "%s.set_position(%s)" % (w, v.replace("none", "gtk.WIN_POS_NONE").replace("center", "gtk.WIN_POS_CENTER").replace("mouse", "gtk.WIN_POS_MOUSE").replace("center-always", "gtk.WIN_POS_CENTER_ALWAYS").replace("center-on-parent", "gtk.WIN_POS_CENTER_ON_PARENT").replace("GTK_", "gtk."))],
	["tab_pos", lambda w,v: "%s.set_tab_pos(%s)" % (w, v.replace("GTK_", "gtk."))],
	["has_resize_grip", lambda w,v: "%s.set_has_resize_grip(%s)" % (w,v.capitalize())],
	["text", lambda w,v: ("%s.set_text(_(\"%s\"))" % (w, v.replace("\"", "\\\""))).replace("_(\"\")", "\"\"")],
	["accel_group", lambda w,v: "%s.add_accel_group(%s)" % (w, v)],
	["wrap_mode", lambda w,v: "%s.set_wrap_mode(%s)" % (w, v.replace("none", "gtk.WRAP_NONE").replace("word-char", "gtk.WRAP_WORD_CHAR").replace("char", "gtk.WRAP_CHAR").replace("word", "gtk.WRAP_WORD").replace("GTK_", "gtk."))],
	["wrap", lambda w,v: "%s.set_line_wrap(%s)" % (w, v.capitalize())],
	["set_markup", lambda w,v: "%s.set_markup(_(\"%s\"))" % (w, v)],
	["cursor_visible", lambda w,v: "%s.set_cursor_visible(%s)" % (w, v.capitalize())],
	["editable", lambda w,v: "%s.set_editable(%s)" % (w, v.capitalize())],
	["scrollable", lambda w,v: "%s.set_scrollable(%s)" % (w, v.capitalize())],
	["can-focus", lambda w,v: "%s.set_property('can-focus', %s)" % (w, v.capitalize())],
	["has-focus", lambda w,v: "%s.set_property('has-focus', %s)" % (w, v.capitalize())],
	["visible", lambda w, v: (v == "True" and ("%s.show()" % w)) or ""],
	["visibility", lambda w, v: (v == "True" and ("%s.set_visibility(True)" % w)) or ("%s.set_visibility(False)" % w)],	
	["headers_visible", lambda w, v: "%s.set_headers_visible(%s)" % (w, v.capitalize())],
	["sensitive", lambda w,v: "%s.set_sensitive(%s)" % (w,v)],
	["image", lambda w,v: "%s.set_image(%s)" % (w,v)],
	["digits", lambda w,v: "%s.set_digits(%s)" % (w,v)],
	["spacing", lambda w,v: "%s.set_spacing(%s)" % (w,v)],
	["border_width", lambda w,v: "%s.set_border_width(%s)" % (w,v)],
	["width_chars", lambda w,v: "%s.set_width_chars(%s)" % (w,v)],
	["row_spacing", lambda w,v: "%s.set_row_spacings(%s)" % (w,v)],
	["column_spacing", lambda w,v: "%s.set_col_spacings(%s)" % (w,v)],
	["layout_style", lambda w,v: "%s.set_layout(%s)" % (w, v.replace("end", "gtk.BUTTONBOX_END").replace("default-style", "gtk.BUTTONBOX_DEFAULT_STYLE").replace("spread", "gtk.BUTTONBOX_SPREAD").replace("edge", "gtk.BUTTONBOX_EDGE").replace("start", "gtk.BUTTONBOX_START").replace("GTK_", "gtk."))],
	["shadow_type", lambda w,v: "%s.set_shadow_type(%s)" % (w, v.replace("in", "gtk.SHADOW_IN").replace("none", "gtk.SHADOW_NONE").replace("etched-in", "gtk.SHADOW_ETCHED_IN").replace("etched-out", "gtk.SHADOW_ETCHED_OUT").replace("out", "gtk.SHADOW_OUT").replace("GTK_", "gtk."))],
	["items", lambda w,v: "for i in [_(\"%s\")]:\n%s\t%s_List.append([i])" % ("\"), _(\"".join(v.replace("\"", "\\\"").split("\n")), indent, w)],
]

PM_NONE = 0
PM_PACK = 1
PM_ADD = 2
PM_PACK12 = 3
PM_ATTACH = 4

signals = []

def write_widget_attrs(widget):
	if widget.attrs.has_key("default_width"):
		w = widget.attrs["default_width"]
		h = widget.attrs["default_height"]
		print indent + "%s.set_default_size(%s, %s)" % (widget.id, w, h)

	if widget.attrs.has_key("hscrollbar_policy"):
		h = widget.attrs["hscrollbar_policy"].replace("automatic", "gtk.POLICY_AUTOMATIC").replace("never", "gtk.POLICY_NEVER").replace("always", "gtk.POLICY_ALWAYS").replace("GTK_", "gtk.")
		v = widget.attrs["vscrollbar_policy"].replace("automatic", "gtk.POLICY_AUTOMATIC").replace("never", "gtk.POLICY_NEVER").replace("always", "gtk.POLICY_ALWAYS").replace("GTK_", "gtk.")
		print indent + "%s.set_policy(%s, %s)" % (widget.id, h, v)

	if widget.my_class != "GtkAlignment":
		x, y = "0.50", "0.50"
		if widget.attrs.has_key("xalign"):
			x = widget.attrs["xalign"]
		if widget.attrs.has_key("yalign"):
			y = widget.attrs["yalign"]
		if float(x) != 0.5 or float(y) != 0.5:
			print indent + "%s.set_alignment(%s, %s)" % (widget.id, x, y)
	top_padding = bottom_padding = left_padding = right_padding = 0
	if widget.attrs.has_key("top_padding"):
		top_padding = widget.attrs["top_padding"]
	if widget.attrs.has_key("bottom_padding"):
		bottom_padding = widget.attrs["bottom_padding"]
	if widget.attrs.has_key("left_padding"):
		left_padding = widget.attrs["left_padding"]
	if widget.attrs.has_key("right_padding"):
		right_padding = widget.attrs["right_padding"]
	for i in [top_padding, bottom_padding, left_padding, right_padding]:
		if i != 0:
			print indent + "%s.set_padding(%s, %s, %s, %s)" % (widget.id, top_padding, bottom_padding, left_padding, right_padding)
			break
			
	if widget.attrs.has_key("angle"):
		print indent + "%s.set_angle(%s)" % (widget.id, widget.attrs["angle"])
	w, h = "-1", "-1"
	if widget.attrs.has_key("width_request"):
		w = widget.attrs["width_request"]
	if widget.attrs.has_key("height_request"):
		h = widget.attrs["height_request"]
	if not (w == "-1" and h == "-1"):
		print indent + "%s.set_size_request(%s, %s)" % (widget.id, w, h)
	x = y = 0
	if widget.attrs.has_key("xpad"):
		x = widget.attrs["xpad"]
	if widget.attrs.has_key("ypad"):
		y = widget.attrs["ypad"]
	if x != 0 or y != 0:
		print indent + "%s.set_padding(%s, %s)" % (widget.id, x, y)
		
	if widget.attrs.has_key("stock"):
		img = "gtk.STOCK_" + widget.attrs["stock"][4:].upper().replace("-", "_")
		if widget.attrs.has_key("icon_size"):
			sze = widget.attrs["icon_size"]
		else:
			sze = 4
		print indent + "%s.set_from_stock(%s, %s)" % (widget.id, img, sze)
		
	if widget.attrs.has_key("tooltip"):
		tip = widget.attrs["tooltip"]
		print indent + "self.tooltips.set_tip(%s, _(\"%s\"))" % (widget.id, tip.replace("\"", "\\\""))
		
	if widget.attrs.has_key("expanded"):
		expanded = widget.attrs["expanded"]
		print indent + "%s.set_expanded(%s)" % (widget.id, expanded)
		
		
	for i in attrs:
		if widget.attrs.has_key(i[0]):
			#print widget.attrs[i[0]]
			if i[0] == "width_chars" and widget.attrs[i[0]] == "-1":
				continue
				
			v = i[1](widget.id, widget.attrs[i[0]])
			if v:
				print indent + "%s" % v

	for (signal, callback) in widget.signals.iteritems():
		print indent + "%s.connect(\"%s\", self.%s)" % (widget.id, signal, callback)
		if not callback in signals:
			signals.append(callback)
	
	for accel in widget.accelerators:
		key, modifer, signal = accel[0], accel[1], accel[2]
		if modifer == "" or modifer.isspace():
			modifer = "0"
		print indent + "%s.add_accelerator(\"%s\", self.accel_group, gtk.gdk.keyval_from_name(\"%s\"), %s, gtk.ACCEL_VISIBLE)" % (widget.id, signal, key, modifer)
		
def write_widget_adjustment(widget, my_class, *args):
	restargs = ""
	value, min, max, step_incr, page_incr, page_size = widget.attrs["adjustment"].split(" ")
	print value, min, max, step_incr, page_incr, page_size
	print indent + "%s_adj = gtk.Adjustment(value=%s, lower=%s, upper=%s, step_incr=%s, page_incr=%s, page_size=%s)" % (widget.id, value, min, max, step_incr, page_incr, page_size)

def write_widget_spinbutton(widget, my_class, *args):
	global signals, indent
	#{'digits': '0', 'climb_rate': '1', 'update_policy': 'GTK_UPDATE_ALWAYS', 'can_focus': 'True', 'numeric': 'False', 'visible': 'True', 'snap_to_ticks': 'False', 'wrap': 'False', 'adjustment': '0 0 255 1 10 10'}
	value, min, max, step_incr, page_incr, page_size = widget.attrs["adjustment"].split(" ")
	adjustment = "gtk.Adjustment(value=%s, lower=%s, upper=%s, step_incr=%s, page_incr=%s)" % (value, min, max, step_incr, page_incr)
	restargs = ""
	print indent + "%s = gtk.%s(%s)" % (widget.id, my_class, adjustment)
	allowed = ["visible", "width_chars"]
	for i in attrs:
		if i[0] in allowed:
			if widget.attrs.has_key(i[0]):
				if i[0] == "width_chars" and widget.attrs["width_chars"] == -1:
					continue
				v = i[1](widget.id, widget.attrs[i[0]])
				if v:
					print indent + "%s" % v
	for (signal, callback) in widget.signals.iteritems():
		print indent + "%s.connect(\"%s\", self.%s)" % (widget.id, signal, callback)
		if not callback in signals:
			signals.append(callback)
	print 
def write_widget_scale(widget, my_class, *args):
	global signals, indent
	restargs = ""
	if "adjustment" in widget.attrs:
		value, min, max, step_incr, page_incr, page_size = widget.attrs["adjustment"].split(" ")
		adjustment = "gtk.Adjustment(value=%s, lower=%s, upper=%s, step_incr=%s, page_incr=%s, page_size=%s)" % (value, min, max, step_incr, page_incr, page_size)
		restargs = ""
		print indent + "%s = gtk.%s(%s)" % (widget.id, my_class, adjustment)
	else:
		print indent + "%s = gtk.%s(%s)" % (widget.id, my_class, "gtk.Adjustment()")

	write_widget_attrs(widget)
	print 
	
def write_widget_generic(widget, my_class, *args):
	global signals, indent
	restargs = ""
	for arg in args[0:]:
		
		if arg[0] == "+":
			name = arg[1:]
			if widget.attrs.has_key(name):
				arg = widget.attrs[arg[1:]]
			else:
				arg= ""
		elif arg[0] == "@":
			name = arg[1:]

			if widget.attrs.has_key(name):
				arg = widget.attrs[name]
			if name in ("xalign", "yalign") and not widget.attrs.has_key(name):
				arg = "0.5"
				#pass
			else:
				arg= "0"
		elif arg[0] == "$":
			
			if not arg[1:] in widget.attrs:
				continue
			s = widget.attrs[arg[1:]].replace("\"", "\\\"").replace("\n", "\\n")
			
			if arg[1:] == "label":
				if widget.attrs.has_key("use_markup") and widget.attrs["use_markup"] == "True":
					widget.attrs["set_markup"] = s
					s = ""
			if s:
				narg = '_("%s")' % s
			else:
				narg = '""'
			del widget.attrs[arg[1:]]
			arg = narg
		elif arg[0] == "#":
			name = arg[1:]
			if widget.attrs.has_key(name):
				arg = "%s" % (widget.attrs[name].capitalize())
			else: arg = "False"
		if arg[:4] == "GTK_":
			arg = "gtk." + arg[4:]
		if restargs:
			restargs += ", "
		restargs += arg
	print indent + "%s = gtk.%s(%s)" % (widget.id, my_class, restargs)
	write_widget_attrs(widget)
	indent = "\t\t"
	
def write_widget_container(widget, my_class, pack, *args):
	write_widget_generic(widget, my_class, *args)
	print
	for w in widget.children:
		if w is None:
			continue
		write_widget(w)
		if pack == PM_PACK:
			if w.packing.has_key("expand"):
				x = w.packing["expand"].capitalize()
				if w.packing.has_key("fill"):
					f = w.packing["fill"].capitalize()
				else:
					f = "True"
				if w.packing.has_key("padding"):
					p = w.packing["padding"]
				else:
					p = "0"
					
				if w.packing.has_key("pack_type"):
					packtype = w.packing["pack_type"]
				else:
					packtype = "GTK_PACK_START"
				if packtype == "GTK_PACK_START":
					pt = "start"
				else:
					pt = "end"
				print indent + "%s.pack_%s(%s, %s, %s, %s)" % (widget.id, pt, w.id, x, f, p)
			else:
				print indent + "%s.pack_start(%s)" % (widget.id, w.id)
		elif pack == PM_PACK12:
			if w.packing.has_key("resize"):
				r = w.packing["resize"].capitalize()
			else:
				r = "True"
			if w.packing.has_key("shrink"):	
				s = w.packing["shrink"].capitalize()
			else:
				s = "True"
			i = widget.children.index(w) + 1
			print indent + "%s.pack%i(%s, %s, %s)" % (widget.id, i, w.id, r, s)
		elif pack == PM_ADD:
			if w.packing.has_key("type"):
				if w.packing["type"] == "label_item":
					print indent + "%s.set_label_widget(%s)" % (widget.id, w.id)
				else:
					stderr.write("Unknown packing type %s for %s" % (w.packing["type"], w.id))
			else:
				print indent + "%s.add(%s)" % (widget.id, w.id)
		elif pack == PM_ATTACH:
			if not w.packing.has_key("left_attach"):
				la = 0
			else:
				la = w.packing["left_attach"]
			if not w.packing.has_key("right_attach"):
				ra = 1
			else:
				ra = w.packing["right_attach"]
			#print w.packing, pack
			if not w.packing.has_key("top_attach"):
				ta = 0
			else:
				ta = w.packing["top_attach"]
			if not w.packing.has_key("bottom_attach"):
				ba = 1
			else:
				ba = w.packing["bottom_attach"]
			xopts = "gtk.EXPAND|gtk.FILL"
			yopts = "gtk.EXPAND|gtk.FILL"
			if w.packing.has_key("x_options"):
				if w.packing["x_options"] == "":
					xopts = "0"
				elif w.packing["x_options"] in ("fill", "GTK_FILL"):
					xopts = "gtk.FILL"
				elif w.packing["x_options"] == "expand":
					xopts = "gtk.EXPAND"
			if w.packing.has_key("y_options"):
				if w.packing["y_options"] == "":
					yopts = "0"
				elif w.packing["y_options"] in ("fill", "GTK_FILL"):
					yopts = "gtk.FILL"
				elif w.packing["y_options"] == "expand":
					yopts = "gtk.EXPAND"
			print indent + "%s.attach(%s, %s, %s, %s, %s, %s, %s, %s, %s)" % (widget.id, w.id, la, ra, ta, ba, xopts, yopts, "0", "0")
		print
	for (wid, w) in widget.internalchildren.iteritems():
		if my_class == "ComboBoxEntry":
			wid = "child"
		print indent + "%s = %s.%s" % (w.id, widget.id, wid)
		write_widget_attrs(w)
		print
		
def write_widget_menu(widget, my_class):
	write_widget_generic(widget, my_class)
	print
	for w in widget.children:
		write_widget(w)
		print indent + "%s.append(%s)" % (widget.id, w.id)
		print

def write_widget_menuitem(widget, my_class):
	args = []
	if widget.attrs.has_key("label"):
		label = widget.attrs["label"].replace("\"", "\\\"")
		if label:
			args.append("_(\"%s\")" % label)
		else:
			args.append('""')
		del widget.attrs["label"]
	else:
		label = ""
	write_widget_generic(widget, my_class, *args)
	print
	if widget.children:
		w = widget.children[0]
		write_widget(w)
		print indent + "%s.set_submenu(%s)" % (widget.id, w.id)
		print

def write_widget_radiomenuitem(widget, my_class):
	args = []
	group = "None"
	if widget.attrs.has_key("group"):
		group = "self.%s" % widget.attrs["group"]
		del widget.attrs["group"]
	args.append(group)
	
	if widget.attrs.has_key("label"):
		label = widget.attrs["label"].replace("\"", "\\\"")
		if label:
			args.append("_(\"%s\")" % label)
		else:
			args.append('""')

		del widget.attrs["label"]
	else:
		label = ""
	write_widget_generic(widget, my_class, *args)
	print
	if widget.children:
		w = widget.children[0]
		write_widget(w)
		print indent + "%s.set_submenu(%s)" % (widget.id, w.id)
		print
		

def write_widget_imagemenuitem(widget, my_class):
	args = []
	if widget.attrs.has_key("label"):
		label = widget.attrs["label"].replace("\"", "\\\"")
		if label:
			args.append("_(\"%s\")" % label)
		else:
			args.append('""')
		del widget.attrs["label"]
	else:
		label = ""
	write_widget_generic(widget, my_class, *args)
	print
	if widget.internalchildren:
		if widget.internalchildren["image"].attrs.has_key("stock"):
			stock = widget.internalchildren["image"].attrs["stock"]
			stock = "gtk.STOCK_" + stock[4:].upper().replace("-", "_")
			print indent + "img = gtk.image_new_from_stock(%s, gtk.ICON_SIZE_MENU)" % stock
			print indent + "%s.set_image(img)" % (widget.id)
	if widget.children:
		w = widget.children[0]
		write_widget(w)
		print indent + "%s.set_submenu(%s)" % (widget.id, w.id)
		print

		
def write_widget_notebook(widget):
	write_widget_generic(widget, "Notebook")
	print
	for i in range(len(widget.children) / 2):
		w = widget.children[i * 2]
		if w is None:
			continue
		write_widget(w)
		t = widget.children[i * 2 + 1]
		write_widget(t)
		
	for i in range(len(widget.children) / 2):
		w = widget.children[i * 2]
		t = widget.children[i * 2 + 1]
		print indent + "%s.append_page(%s, %s)" % (widget.id, w.id, t.id)
		print

def write_widget_radiobutton(widget):
	if widget.attrs.has_key("group"):
		write_widget_generic(widget, "RadioButton", "self."+widget.attrs["group"])
	else:
		write_widget_generic(widget, "RadioButton")
	print

def write_widget_textview(widget):
	if widget.attrs.has_key("text"):
		del widget.attrs["text"]
	write_widget_generic(widget, "TextView")

def write_widget_button(widget):
	if widget.attrs.has_key("use_stock"):
		if widget.attrs["use_stock"] == "True":
			stock = "gtk.STOCK_" + widget.attrs["label"][4:].upper().replace("-", "_")
			del widget.attrs["label"]
			write_widget_container(widget, "Button", PM_ADD, "None", stock)
			return
	write_widget_container(widget, "Button", PM_ADD)

def write_widget_filechooserbutton(widget):
	
	if widget.attrs.has_key("title"):
		title = "title=_(\"%s\")" % widget.attrs["title"]
	else:
		"title=\"\""
	del widget.attrs["title"]
	write_widget_container(widget, "FileChooserButton", PM_ADD, title)
	if widget.attrs.has_key("action"):
		#widget.attrs["action"].replace("select-folder", "gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER").replace("-", "_")
		action = widget.attrs["action"]
		if action[:4] != "GTK_":
			action = "gtk.FILE_CHOOSER_ACTION_"+action.upper().replace("-", "_")
		print indent + "%s.set_action(%s)" % (widget.id, action)
	print
	
def write_widget_togglebutton(widget):
	if widget.attrs.has_key("use_stock"):
		if widget.attrs["use_stock"] == "True":
			stock = "gtk.STOCK_" + widget.attrs["label"][4:].upper().replace("-", "_")
			del widget.attrs["label"]
			write_widget_container(widget, "ToggleButton", PM_ADD, "None", stock)
			return
	write_widget_container(widget, "ToggleButton", PM_ADD)
	
def write_widget_combobox(widget):
	print indent + "%s_List = gtk.ListStore(gobject.TYPE_STRING)" % (widget.id)
	write_widget_container(widget, "ComboBox", PM_ADD)
	print indent + "%s.set_model(%s_List)" % (widget.id, widget.id)
	print indent + "cell = gtk.CellRendererText()"
	print indent + "%s.pack_start(cell, True)" % widget.id
	print indent + "%s.add_attribute(cell, 'text', 0)" % widget.id

def write_widget_comboboxentry(widget):
	print indent + "%s_List = gtk.ListStore(gobject.TYPE_STRING)" % (widget.id)
	write_widget_container(widget, "ComboBoxEntry", PM_ADD)
	print indent + "%s.set_model(%s_List)" % (widget.id, widget.id)
	print indent + "%s.set_text_column(0)" % widget.id
		
def write_widget_custom(widget):
	s1, s2, i1, i2 = "", "", "0", "0"
	if widget.attrs.has_key("string1"):
		s1 = widget.attrs["string1"]
	if widget.attrs.has_key("string2"):
		s2 = widget.attrs["string2"]
	if widget.attrs.has_key("int1"):
		i1 = widget.attrs["int1"]
	if widget.attrs.has_key("int2"):
		i2 = widget.attrs["int2"]
	if s1:
		s1 = "\"%s\"" % s1
	else:
		s1 = '""'
	if s2:
		s2 = "_(\"%s\")" % s2
	else:
		s2 = '""'
	print indent + "%s = self.get_custom_widget(\"%s\", %s, %s, %s, %s)" % (widget.id, widget.id[5:], s1, s2, i1, i2)
	write_widget_attrs(widget)

classes = {
	"GtkWindow": [write_widget_container, "Window", PM_NONE, "+type"],
	"GtkDialog": [write_widget_container, "Dialog", PM_NONE],
	"GtkAboutDialog": [write_widget_container, "AboutDialog", PM_NONE],
	"GtkOptionMenu": [write_widget_container, "OptionMenu", PM_NONE],
	"GtkVBox": [write_widget_container, "VBox", PM_PACK, "#homogeneous", "@spacing"],
	"GtkHBox": [write_widget_container, "HBox", PM_PACK, "#homogeneous", "@spacing"],
	"GtkMenuBar": [write_widget_menu, "MenuBar"],
	"GtkMenuItem": [write_widget_menuitem, "MenuItem"],
	"GtkImageMenuItem": [write_widget_imagemenuitem, "ImageMenuItem"],
	"GtkSeparatorMenuItem": [write_widget_menuitem, "MenuItem"],
	"GtkRadioMenuItem": [write_widget_radiomenuitem, "RadioMenuItem"],
	"GtkCheckMenuItem": [write_widget_menuitem, "CheckMenuItem"],
	"GtkMenu": [write_widget_menu, "Menu"],
	"GtkVPaned": [write_widget_container, "VPaned", PM_PACK12],
	"GtkHPaned": [write_widget_container, "HPaned", PM_PACK12],
	"GtkNotebook": [write_widget_notebook],
	"GtkScrolledWindow": [write_widget_container, "ScrolledWindow", PM_ADD],
	"GtkViewport": [write_widget_container, "Viewport", PM_ADD],
	"GtkLabel": [write_widget_generic, "Label", "$label"],
	"GtkExpander": [write_widget_container, "Expander", PM_ADD],
	"GtkCombo": [write_widget_container, "Combo", PM_NONE],
	"GtkComboBox": [write_widget_combobox],
	"GtkDrawingArea": [write_widget_container, "DrawingArea", PM_NONE],
	"GtkComboBoxEntry": [write_widget_comboboxentry],
	"GtkComboBoxEntryChild": [write_widget_generic, "child"],
	"GtkCheckButton": [write_widget_container, "CheckButton", PM_ADD],
	"GtkToggleButton": [write_widget_togglebutton],
	"GtkFontButton": [write_widget_generic, "FontButton"],
	"GtkIconView": [write_widget_generic, "IconView"],
	"GtkFileChooserButton": [write_widget_filechooserbutton],
	"GtkRadioButton": [write_widget_radiobutton],
	"GtkButton": [write_widget_button],
	"GtkTextView": [write_widget_textview],
	"GtkSpinButton": [write_widget_spinbutton, "SpinButton"],
	"GtkHScale": [write_widget_scale, "HScale"],
	"GtkVScale": [write_widget_scale, "VScale"],
	"GtkAdjustment": [write_widget_adjustment, "Adjustment"],
	"GtkStatusbar": [write_widget_generic, "Statusbar"],
	"GtkEntry": [write_widget_generic, "Entry"],
	"GtkList": [write_widget_generic, "List"],
	"GtkTreeView": [write_widget_generic, "TreeView"],
	"GtkTable": [write_widget_container, "Table", PM_ATTACH],
	"GtkFrame": [write_widget_container, "Frame", PM_ADD],
	"GtkProgressBar": [write_widget_generic, "ProgressBar"],
	"GtkImage": [write_widget_generic, "Image"],
	"GtkVSeparator": [write_widget_generic, "VSeparator"],
	"GtkHSeparator": [write_widget_generic, "HSeparator"],
	"GtkHButtonBox": [write_widget_container, "HButtonBox", PM_PACK],
	"GtkEventBox" : [write_widget_container, "EventBox", PM_ADD],
	"GtkAlignment": [write_widget_container, "Alignment", PM_ADD, "@xalign", "@yalign", "@xscale", "@yscale"],
	"Custom": [write_widget_custom],
}

def write_widget(w):
	if w is None:
		return
	if not w.my_class in classes:
		sys.stderr.write("oops... widget class %s not found!\n" % w.my_class)
		print indent + "# %s of %s should be here" % (w.id, w.my_class)
		return
	c = classes[w.my_class]
	c[0](w, *c[1:])
	
def process_property(property):
	n = str(property.attributes["name"].nodeValue)
	try:
		v = str(property.childNodes[0].nodeValue)
	except:
		v = ""
	return n, v

def process_packing(packing):
	data = {}
	for node in packing.childNodes:
		if node.nodeName == "property":
			n, v = process_property(node)
			data[n] = v
	return data
	
def process_child(child):
	w = None
	for node in child.childNodes:
		if node.nodeName == "widget":
			w = process_widget(node)
		elif node.nodeName == "packing":
			#print node.nodeName, process_packing(node)
			if w is not None:
				w.packing.update(process_packing(node))
	return w
	
def process_signal(child):
	s = str(child.attributes["name"].nodeValue)
	h = str(child.attributes["handler"].nodeValue)
	for i in "(/\-=+[]{}:;><,.":
		h = h.replace(i, "_")
	return s, h

def process_accelerator(child):
	k = str(child.attributes["key"].nodeValue)
	if "modifiers" in child.attributes:
		m = str(child.attributes["modifiers"].nodeValue).replace("GDK_", "gtk.gdk.")
	else:
		m = ""
	s = str(child.attributes["signal"].nodeValue)
	return k, m, s
		
def write_main(w):
	global signals, indent
	indent = "\t"
	w.attrs["accel_group"] = "self.accel_group"
	print "class %s:" % w.id[5:]
	print indent + "def __init__(self, create = True, accel_group = None, tooltips = None):"
	print indent + indent + "if accel_group is None:"
	print indent + indent + indent + "self.accel_group = gtk.AccelGroup()"
	print indent + indent + "else:"
	print indent + indent + indent + "self.accel_group = accel_group"
	print indent + indent + "if tooltips is None:"
	print indent + indent + indent + "self.tooltips = gtk.Tooltips()"
	print indent + indent + "else:"
	print indent + indent + indent + "self.tooltips = tooltips"
	print indent + indent + "self.tooltips.enable()"
	print indent + indent + "if create:"
	indent = "\t\t\t"
	write_widget(w)
	indent = "\t"
	if w.my_class == "GtkWindow":
		print indent + indent + "if create:"
		print indent + indent + indent + "%s.add(%s)" % (w.id, w.children[0].id)
	print
	for s in signals:
		print indent + "def %s(self, widget):" % s
		print indent + indent + "pass"
		print
	signals = []
	print indent + "def get_custom_widget(self, id, string1, string2, int1, int2):"
	print indent + indent + "w = gtk.Label(_(\"(custom widget: %s)\") % id)"
	print indent + indent + "return w"
	print

def process_widget(widget):
	my_class = widget.attributes["class"].nodeValue
	id = widget.attributes["id"].nodeValue
	for i in "(/\-=+[]{}:;><,.":
		id = id.replace(i, "_")
	id = "self." + id
	w = Widget(my_class, id)
	if widget.hasChildNodes():
		for child in widget.childNodes:
			if child.nodeName == "child":
				childw = process_child(child)
				if child.attributes.has_key("internal-child"):
					v = child.attributes["internal-child"].nodeValue
					w.internalchildren[v] = childw
				else:
					w.children.append(childw)
			elif child.nodeName == "property":
				n, v = process_property(child)
				w.attrs[n] = v
			elif child.nodeName == "signal":
				s, h = process_signal(child)
				w.signals[s] = h
			elif child.nodeName == "accelerator":
				k, m, s = process_accelerator(child)
				w.accelerators.append([k, m, s])
			elif child.nodeName == "image":
				childw = process_child(child)
				if child.attributes.has_key("internal-child"):
					v = child.attributes["internal-child"].nodeValue
					w.internalchildren[v] = childw
				else:
					w.children.append(childw)
	return w
	
def process_interface(dom):
	for child in dom.childNodes:
		if child.nodeName == "widget":
			w = process_widget(child)
			write_main(w)

from xml.dom.minidom import parse
import sys
dom = parse(sys.argv[1])

print "import gtk, gobject"
print
process_interface(dom.getElementsByTagName("glade-interface")[0])
