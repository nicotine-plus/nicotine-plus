# Copyright (c) 2003-2004 Hyriand. All rights reserved.
#
import gtk
import gobject
import pango
import time
import locale
import os
import string
import re
import types

from pynicotine import slskmessages

DECIMALSEP = ""

URL_RE = re.compile("(\\w+\\://[\\w\\.].+?)[\\s\\(\\)]|(www\\.\\w+\\.\\w+.*?)[\\s\\(\\)]|(mailto\\:\\w.+?)[\\s\\(\\)]")
PROTOCOL_HANDLERS = {}
CATCH_URLS = 0
HUMANIZE_URLS = 0

def popupWarning(parent, title, warning):
	dlg = gtk.Dialog(title = title, parent = parent,
		buttons = (gtk.STOCK_OK, gtk.RESPONSE_OK, gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
	dlg.set_default_response(gtk.RESPONSE_OK)
	
	dlg.set_border_width(10)
	dlg.vbox.set_spacing(10)
		
	label = gtk.Label()
	label.set_text(warning)
	dlg.vbox.pack_start(label, True, True)

	dlg.vbox.show_all()

	result = None
	if dlg.run() == gtk.RESPONSE_OK:
		dlg.destroy()
		
	return 0
	
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
		elif c[2] == "progress":
			renderer = gtk.CellRendererProgress()
			column = gtk.TreeViewColumn(c[0], renderer, value = i)
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
		if len(c) > 3:
			column.set_cell_data_func(renderer, c[3])
		treeview.append_column(column)
		cols.append(column)
		i += 1
	return cols

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
		if PROTOCOL_HANDLERS.has_key(protocol):
			if PROTOCOL_HANDLERS[protocol].__class__ is types.MethodType:
				PROTOCOL_HANDLERS[protocol](url)
			else:
				cmd = PROTOCOL_HANDLERS[protocol] % url
				os.system(cmd)
		else:
			try:
				import gnome.vfs
				gnome.url_show(url)
			except:
				pass
	tag.last_event_type = event.type

def AppendLine(textview, line, tag = None, timestamp = "%H:%M:%S"):
	def _makeurltag(buffer, tag, url):
		props = {}
		#if tag is not None:
			#color = tag.get_property("foreground_gdk")
			#props["foreground_gdk"] = color
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
	
	if timestamp:
		line = "%s %s\n" % (recode(time.strftime(timestamp)), line)

	match = URL_RE.search(line)
	while CATCH_URLS and match:
		start = line[:match.start()]
		url = match.group()[:-1]
		urltag = _makeurltag(buffer, tag, url)
		line = line[match.end()-1:]
		_append(buffer, start, tag)
		if url.startswith("slsk://") and HUMANIZE_URLS:
			url = url.replace("%20", " ")
		_append(buffer, url, urltag)
		match = URL_RE.search(line)
	
	if line:
		_append(buffer, line, tag)
	
	if not hasattr(scrolledwindow, "need_scroll"):
		scrolledwindow.need_scroll = 1
	if bottom and scrolledwindow.need_scroll:
		scrolledwindow.need_scroll = 0
		gobject.idle_add(ScrollBottom, scrolledwindow)
	
	return linenr
	
class ImageLabel(gtk.HBox):
	def __init__(self, label = "", image = None, onclose = None):
		gtk.HBox.__init__(self)
		self.set_spacing(2)

		self._entered = 0
		self._pressed = 0
		self.onclose = onclose

		self.label = gtk.Label(label)
		self.label.set_alignment(0.0, 0.50)
		self.pack_start(self.label, True, True)
		self.label.show()

		self.image = gtk.Image()
		self.set_image(image)
		self.pack_start(self.image, False, False)
		self.image.show()

		if onclose is not None:
			self.button = gtk.Button()
			img = gtk.Image()
			img.set_from_stock(gtk.STOCK_CLOSE, gtk.ICON_SIZE_MENU)
			self.button.add(img)
			self.button.connect("clicked", onclose)
			self.button.set_relief(gtk.RELIEF_NONE)
			self.button.set_size_request(16,16)
			self.pack_start(self.button, False, False)
			self.button.show_all()

	def set_image(self, img):
		self.img = img
		self.image.set_from_pixbuf(img)
	
	def get_image(self):
		return self.img
		
	def set_text(self, lbl):
		self.label.set_text(lbl)
	
class IconNotebook(gtk.Notebook):
	def __init__(self, images):
		self.tabclosers = 0
		gtk.Notebook.__init__(self)
		self.images = images
		self.pages = []
		self.connect("switch-page", self.dismiss_icon)
		self.connect("key_press_event", self.OnKeyPress)
		self.set_scrollable(True)
		
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
	
	def append_page(self, page, label, onclose = None):
		if not self.tabclosers:
			onclose = None
		l = ImageLabel(label, self.images["empty"], onclose)
		l2 = ImageLabel(label, self.images["empty"])
		self.pages.append([page, l, 0, l2])
		gtk.Notebook.append_page_menu(self, page, l, l2)
	
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
				
	def dismiss_icon(self, notebook, page, page_num):
		page = self.get_nth_page(page_num)
		self.set_image(page, 0)

	def request_hilite(self, page):
		current = self.get_nth_page(self.get_current_page())
		if current == page:
			return
		self.set_image(page, 2)

	def request_changed(self, page):
		current = self.get_nth_page(self.get_current_page())
		if current == page:
			return
		self.set_image(page, 1)
	
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
		
	def setup(self, *items):
		for item in items:
			if item[0] == "":
				menuitem = gtk.MenuItem()
			elif item[0] == 1:
				menuitem = gtk.MenuItem()
				menuitem = gtk.MenuItem(item[1])
				menuitem.set_submenu(item[2])
				if item[3] is not None:
					menuitem.connect("activate", item[3])
			else:
				if item[0][0] == "$":
					menuitem = gtk.CheckMenuItem(item[0][1:])
				elif item[0][0] == "#":
					menuitem = gtk.ImageMenuItem(item[0][1:])
					img = gtk.image_new_from_stock(item[2], gtk.ICON_SIZE_MENU)
        				menuitem.set_image(img)
				else:
					menuitem = gtk.MenuItem(item[0])
				if item[1] is not None:
					menuitem.connect("activate", item[1])
			self.append(menuitem)
			menuitem.show()
		return self

	def set_user(self, user):
		self.user = user
	
	def get_user(self):
		return self.user
		
	def OnSendMessage(self, widget):
		self.frame.privatechats.SendMessage(self.user, None, 1)
		self.frame.notebook1.set_current_page(1)
	
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
		text = InputDialog(None, _("Give privileges"), _("Give how many days of privileges do you wish to give this user?"))
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
		logfile = open(os.path.join(logsdir, fn.replace(os.sep, "-") + ".log"), 'a', 0)
		os.umask(oldumask)
	logfile.write("%s %s\n" % (recode(time.strftime("%c")), msg))
	logfile.flush()
	return logfile

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

    if not cmd:
        return None
    if cmd[0] != "/":
        return None
    cmd = cmd[1:].split(" ")
    if not aliases.has_key(cmd[0]):
        return None
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
            os.wait()
        else:
            ret = ret + alias[i]
            i = i + 1
    return ret

def EncodingsMenu(np, section = None, entry = None):
	if section and entry and np.config.sections["server"][section].has_key(entry):
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
	elif np.config.sections["server"][section].has_key(entry):
		del np.config.sections["server"][section][entry]
	np.config.writeConfig()
