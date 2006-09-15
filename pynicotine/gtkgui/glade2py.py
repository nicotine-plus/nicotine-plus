#!/usr/bin/python
# Copyright (c) 2003-2004 Hyriand. All rights reserved.
#
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
	["label", lambda w, v: "%s.set_label(_(\"%s\"))" %(w, v.replace("\"", "\\\""))],
	["window_position", lambda w,v: "%s.set_position(%s)" % (w, v.replace("GTK_", "gtk."))],
	["tab_pos", lambda w,v: "%s.set_tab_pos(%s)" % (w, v.replace("GTK_", "gtk."))],
	["has_resize_grip", lambda w,v: "%s.set_has_resize_grip(%s)" % (w,v.capitalize())],
	["text", lambda w,v: "%s.set_text(\"%s\")" % (w, v.replace("\"", "\\\""))],
	["accel_group", lambda w,v: "%s.add_accel_group(%s)" % (w, v)],
	["wrap_mode", lambda w,v: "%s.set_wrap_mode(%s)" % (w, v.replace("GTK_", "gtk."))],
	["wrap", lambda w,v: "%s.set_line_wrap(%s)" % (w, v.capitalize())],
	["cursor_visible", lambda w,v: "%s.set_cursor_visible(%s)" % (w, v.capitalize())],
	["editable", lambda w,v: "%s.set_editable(%s)" % (w, v.capitalize())],
	["scrollable", lambda w,v: "%s.set_scrollable(%s)" % (w, v.capitalize())],
	["can-focus", lambda w,v: "%s.set_property('can-focus', %s)" % (w, v.capitalize())],
	["has-focus", lambda w,v: "%s.set_property('has-focus', %s)" % (w, v.capitalize())],
	["visible", lambda w, v: (v == "True" and ("%s.show()" % w)) or ""],
	["visibility", lambda w, v: (v == "True" and ("%s.set_visibility(True)" % w)) or ("%s.set_visibility(False)" % w)],	
	["headers_visible", lambda w, v: "%s.set_headers_visible(%s)" % (w, v.capitalize())],
	["image", lambda w,v: "%s.set_image(%s)" % (w,v)],
	["spacing", lambda w,v: "%s.set_spacing(%s)" % (w,v)],
	["border_width", lambda w,v: "%s.set_border_width(%s)" % (w,v)],
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

	if widget.attrs.has_key("xpad"):
		x = widget.attrs["xpad"]
		y = widget.attrs["ypad"]
		print indent + "%s.set_padding(%s, %s)" % (widget.id, x, y)
		
	if widget.attrs.has_key("stock"):
		img = "gtk.STOCK_" + widget.attrs["stock"][4:].upper().replace("-", "_")
		sze = widget.attrs["icon_size"]
		print indent + "%s.set_from_stock(%s, %s)" % (widget.id, img, sze)
	
	for i in attrs:
		if widget.attrs.has_key(i[0]):
			v = i[1](widget.id, widget.attrs[i[0]])
			if v:
				print indent + "%s" % v

	for signal in widget.signals.keys():
		callback = widget.signals[signal]
		print indent + "%s.connect(\"%s\", self.%s)" % (widget.id, signal, callback)
		if not callback in signals:
			signals.append(callback)
	
	for accel in widget.accelerators:
		print indent + "%s.add_accelerator(\"%s\", self.accel_group, gtk.gdk.keyval_from_name(\"%s\"), %s, gtk.ACCEL_VISIBLE)" % (widget.id, accel[2], accel[0], accel[1])
		
def write_widget_generic(widget, my_class, *args):
	global signals, indent
	restargs = ""
	for arg in args[0:]:
		if arg[0] == "@":
			try:
				arg = widget.attrs[arg[1:]]
			except:
				arg= "None"
		elif arg[0] == "$":
			s = widget.attrs[arg[1:]].replace("\"", "\\\"")
			if s:
				narg = '_("%s")' % s
			else:
				narg = '""'
			del widget.attrs[arg[1:]]
			arg = narg
		elif arg[0] == "#":
			arg = "%s" % widget.attrs[arg[1:]].capitalize()
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
				f = w.packing["fill"].capitalize()
				p = w.packing["padding"]
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
			r = w.packing["resize"].capitalize()
			s = w.packing["shrink"].capitalize()
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
			la = w.packing["left_attach"]
			ra = w.packing["right_attach"]
			ta = w.packing["top_attach"]
			ba = w.packing["bottom_attach"]
			xopts = "gtk.EXPAND|gtk.FILL"
			yopts = "gtk.EXPAND|gtk.FILL"
			if w.packing.has_key("x_options"):
				if w.packing["x_options"] == "":
					xopts = "0"
				elif w.packing["x_options"] == "fill":
					xopts = "gtk.FILL"
				elif w.packing["x_options"] == "expand":
					xopts = "gtk.EXPAND"
			if w.packing.has_key("y_options"):
				if w.packing["y_options"] == "":
					yopts = "0"
				elif w.packing["y_options"] == "fill":
					yopts = "gtk.FILL"
				elif w.packing["y_options"] == "expand":
					yopts = "gtk.EXPAND"
			print indent + "%s.attach(%s, %s, %s, %s, %s, %s, %s, %s, %s)" % (widget.id, w.id, la, ra, ta, ba, xopts, yopts, "0", "0")
		print
	for wid in widget.internalchildren.keys():
		w = widget.internalchildren[wid]
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
		s1 = "_(\"%s\")" % s1
	else:
		s1 = '""'
	if s2:
		s2 = "_(\"%s\")" % s2
	else:
		s2 = '""'
	print indent + "%s = self.get_custom_widget(\"%s\", %s, %s, %s, %s)" % (widget.id, widget.id[5:], s1, s2, i1, i2)
	write_widget_attrs(widget)

classes = {
	"GtkWindow": [write_widget_container, "Window", PM_NONE, "@type"],
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
	"GtkFontButton": [write_widget_generic, "FontButton"],
	"GtkRadioButton": [write_widget_radiobutton],
	"GtkButton": [write_widget_button],
	"GtkTextView": [write_widget_textview],
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
	print "    def __init__(self, create = True, accel_group = None):"
	print "        if accel_group is None:"
	print "             self.accel_group = gtk.AccelGroup()"
	print "        else:"
	print "             self.accel_group = accel_group"
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
