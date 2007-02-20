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

from struct import unpack
import imghdr

from pynicotine import slskmessages

DECIMALSEP = ""

URL_RE = re.compile("(\\w+\\://[\\w\\.].+?)[\\s\\(\\)]|(www\\.\\w+\\.\\w+.*?)[\\s\\(\\)]|(mailto\\:\\w.+?)[\\s\\(\\)]")
PROTOCOL_HANDLERS = {}
CATCH_URLS = 0
HUMANIZE_URLS = 0
USERNAMEHOTSPOTS = 0

def popupWarning(parent, title, warning):
	dlg = gtk.Dialog(title = title, parent = parent,
		buttons = (gtk.STOCK_OK, gtk.RESPONSE_OK))
	dlg.set_default_response(gtk.RESPONSE_OK)
	
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
		elif c[2] == "edit":
			renderer = gtk.CellRendererText()
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
		if len(c) > 3:
			column.set_cell_data_func(renderer, c[3])
		column.set_reorderable(True)
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

def AppendLine(textview, line, tag = None, timestamp = "%H:%M:%S", username=None, usertag=None):
	def _makeurltag(buffer, tag, url):
		props = {}
		if tag is not None:
			color = tag.get_property("foreground_gdk")
			props["foreground_gdk"] = color
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
	if timestamp:
		line = "%s %s\n" % (recode(time.strftime(timestamp)), line)

	match = URL_RE.search(line)
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
			url = url.replace("%20", " ")
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
			self.button.set_size_request(18,18)
			self.pack_start(self.button, False, False)
			self.button.show_all()

	def set_image(self, img):
		self.img = img
		self.image.set_from_pixbuf(img)
	
	def get_image(self):
		return self.img
		
	def set_text(self, lbl):
		self.label.set_text(lbl)
		
	def get_text(self):
		return self.label.get_text()
	
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
		try:
			self.set_tab_reorderable(page, True)
		except:
			# Old PyGTK2
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
				elif item[0][0] == "%":
					menuitem = gtk.ImageMenuItem(item[0][1:])	
					img = gtk.Image()
					img.set_from_pixbuf(item[2])
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
		text = InputDialog(None, "Give privileges", "Give how many days of privileges do you wish to give this user?" )
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
		logfile = open(encode(os.path.join(logsdir, fn.replace(os.sep, "-") + ".log")), 'a', 0)
		os.umask(oldumask)
	logfile.write("%s %s\n" % (recode(time.strftime("%c")), msg))
	logfile.flush()
	return logfile
		
def encode(path):
	try:
		if sys.platform == "win32":
			chars = ["?", "\/", "\"", ":", ">", "<", "|", "*"]
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
				if not self.is_in_user_list(i,self.config.sections["server"]["userlist"]):
					#print [i,'']
					self.config.sections["server"]["userlist"].append([i,''])
		
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
		
		infile = open(fname, 'r')
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
		
		
		infile = open(fname, 'r')
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
		
		infile = open(fname, 'r')
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
		
		infile = open(fname, 'r')
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
		outfile = open(fname, "w")
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

