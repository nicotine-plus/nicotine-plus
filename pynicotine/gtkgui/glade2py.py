#!/usr/bin/python
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

indent = "        "
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
	["window_position", lambda w,v: "%s.set_position(%s)" % (w, v.replace("GTK_", "gtk."))],
	["tab_pos", lambda w,v: "%s.set_tab_pos(%s)" % (w, v.replace("GTK_", "gtk."))],
	["has_resize_grip", lambda w,v: "%s.set_has_resize_grip(%s)" % (w,v.capitalize())],
	["text", lambda w,v: ("%s.set_text(_(\"%s\"))" % (w, v.replace("\"", "\\\""))).replace("_(\"\")", "\"\"")],
	["accel_group", lambda w,v: "%s.add_accel_group(%s)" % (w, v)],
	["wrap_mode", lambda w,v: "%s.set_wrap_mode(%s)" % (w, v.replace("GTK_", "gtk."))],
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
	["layout_style", lambda w,v: "%s.set_layout(%s)" % (w, v.replace("GTK_", "gtk."))],
	["shadow_type", lambda w,v: "%s.set_shadow_type(%s)" % (w, v.replace("GTK_", "gtk."))],
	["items", lambda w,v: "%s_List.append([\"%s\"])" % (w, v.replace("\"", "\\\""))],
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
		h = widget.attrs["hscrollbar_policy"].replace("GTK_", "gtk.")
		v = widget.attrs["vscrollbar_policy"].replace("GTK_", "gtk.")
		print indent + "%s.set_policy(%s, %s)" % (widget.id, h, v)

	if widget.my_class != "GtkAlignment":
		x, y = "0.50", "0.50"
		if widget.attrs.has_key("xalign"):
			x = widget.attrs["xalign"]
		if widget.attrs.has_key("yalign"):
			y = widget.attrs["yalign"]
		if float(x) != 0.5 or float(y) != 0.5:
			print indent + "%s.set_alignment(%s, %s)" % (widget.id, x, y)
	
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
		print indent + "self.tooltips.set_tip(%s, _(\"%s\"))" % (widget.id, tip)
		
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

	for signal in widget.signals.keys():
		callback = widget.signals[signal]
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
	adjustment = "gtk.Adjustment(value=%s, lower=%s, upper=%s, step_incr=%s, page_incr=%s, page_size=%s)" % (value, min, max, step_incr, page_incr, page_size)
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
	for signal in widget.signals.keys():
		callback = widget.signals[signal]
		print indent + "%s.connect(\"%s\", self.%s)" % (widget.id, signal, callback)
		if not callback in signals:
			signals.append(callback)
	print 
def write_widget_scale(widget, my_class, *args):
	global signals, indent
	restargs = ""
	#print indent + "%s_adj = gtk.%s(%s)" % (widget.id, my_class, restargs)
	#print 
	value, min, max, step_incr, page_incr, page_size = widget.attrs["adjustment"].split(" ")
	adjustment = "gtk.Adjustment(value=%s, lower=%s, upper=%s, step_incr=%s, page_incr=%s, page_size=%s)" % (value, min, max, step_incr, page_incr, page_size)
	restargs = ""
	print indent + "%s = gtk.%s(%s)" % (widget.id, my_class, adjustment)
	allowed = ["visible", "digits"]
	for i in attrs:
		if i[0] in allowed:
			if widget.attrs.has_key("visible"):
				v = i[1](widget.id, widget.attrs[i[0]])
				if v:
					print indent + "%s" % v
	for signal in widget.signals.keys():
		callback = widget.signals[signal]
		print indent + "%s.connect(\"%s\", self.%s)" % (widget.id, signal, callback)
		if not callback in signals:
			signals.append(callback)
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
				arg = widget.attrs[arg[1:]]
			if arg in ("@xalign", "@yalign"):
				arg = "0.5"
			else:
				arg= "0"
		elif arg[0] == "$":
			
			if not arg[1:] in widget.attrs.keys():
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
	indent = "        "
	
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
	for wid in widget.internalchildren.keys():
		w = widget.internalchildren[wid]
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
	"GtkOptionMenu": [write_widget_container, "OptionMenu", PM_NONE],
	"GtkVBox": [write_widget_container, "VBox", PM_PACK, "#homogeneous", "@spacing"],
	"GtkHBox": [write_widget_container, "HBox", PM_PACK, "#homogeneous", "@spacing"],
	"GtkMenuBar": [write_widget_menu, "MenuBar"],
	"GtkMenuItem": [write_widget_menuitem, "MenuItem"],
	"GtkImageMenuItem": [write_widget_imagemenuitem, "ImageMenuItem"],
	"GtkSeparatorMenuItem": [write_widget_menuitem, "MenuItem"],
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
	"GtkComboBoxEntry": [write_widget_comboboxentry],
	"GtkComboBoxEntryChild": [write_widget_generic, "child"],
	"GtkCheckButton": [write_widget_generic, "CheckButton"],
	"GtkToggleButton": [write_widget_generic, "ToggleButton"],
	"GtkFontButton": [write_widget_generic, "FontButton"],
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
	m = str(child.attributes["modifiers"].nodeValue).replace("GDK_", "gtk.gdk.")
	s = str(child.attributes["signal"].nodeValue)
	return k, m, s
		
def write_main(w):
	global signals, indent
	w.attrs["accel_group"] = "self.accel_group"
	print "class %s:" % w.id[5:]
	print "    def __init__(self, create = True, accel_group = None, tooltips = None):"
	print "        if accel_group is None:"
	print "             self.accel_group = gtk.AccelGroup()"
	print "        else:"
	print "             self.accel_group = accel_group"
	print "        if tooltips is None:"
	print "             self.tooltips = gtk.Tooltips()"
	print "        else:"
	print "             self.tooltips = tooltips"
	print "        self.tooltips.enable()"
	print "        if create:"
	indent = "            "
	write_widget(w)
	if w.my_class == "GtkWindow":
		print "        if create:"
		print "            %s.add(%s)" % (w.id, w.children[0].id)
	print
	for s in signals:
		print "    def %s(self, widget):" % s
		print "        pass"
		print
	signals = []
	print "    def get_custom_widget(self, id, string1, string2, int1, int2):"
	print "        w = gtk.Label(_(\"(custom widget: %s)\") % id)"
	print "        return w"
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
print "from pynicotine.utils import _"
print
process_interface(dom.getElementsByTagName("glade-interface")[0])
