# Copyright (c) 2003-2004 Hyriand. All rights reserved.
#
import gtk
import os, sys
from pynicotine.utils import version
import imagedata

from pynicotine.utils import _

class GenericAboutDialog(gtk.Dialog):
	def __init__(self, parent, title = ""):
		gtk.Dialog.__init__(self, title, parent, gtk.DIALOG_MODAL, (gtk.STOCK_OK, gtk.RESPONSE_OK))
		self.set_resizable(False)
		self.set_position(gtk.WIN_POS_CENTER)
		self.vbox.set_spacing(10)
		self.set_border_width(5)

class AboutDialog(GenericAboutDialog):
	def __init__(self, parent):
		GenericAboutDialog.__init__(self, parent, "About Nicotine")
		img = gtk.Image()
		loader = gtk.gdk.PixbufLoader("png")
		loader.write(imagedata.nicotinen, len(imagedata.nicotinen))
		loader.close()
		pixbuf = loader.get_pixbuf()
		img.set_from_pixbuf(pixbuf)
		label = gtk.Label(_("""Nicotine+ %s

Copyright (c) 2007 daelstorm
http://nicotine-plus.sourceforge.net/
daelstorm@gmail.com

Based on code from Nicotine
Copyright (c) 2003 Hyriand
http://nicotine.thegraveyard.org/
hyriand@thegraveyard.org

Based on code from the PySoulSeek project
Copyright (c) 2001-2003 Alexander Kanavin

Released under the GNU Public License

See MAINTAINERS file for the list of contributors""") % version)
		label.set_justify(gtk.JUSTIFY_LEFT)
		vbox = gtk.VBox()
		vbox.pack_start(img, False, False)
		hbox = gtk.HBox()
		hbox.set_spacing(10)
		hbox.pack_start(vbox, True, True)
		hbox.pack_start(label, True, True)
		sys.version_info
		pythonversion = "%d.%d.%d" % (sys.version_info[0], sys.version_info[1], sys.version_info[2])
		
		self.frame1 = gtk.Frame()
		self.frame1.show()
		self.frame1.set_shadow_type(gtk.SHADOW_ETCHED_IN)
		
		
		self.vbox2 = gtk.VBox()
		self.vbox2.set_spacing(5)
		self.vbox2.set_border_width(5)
		self.frame1.add(self.vbox2)
		
		self.label17 = gtk.Label(_("Dependencies"))
		self.label17.set_padding(0, 0)
		self.label17.set_line_wrap(False)
		self.label17.show()
		self.frame1.set_label_widget(self.label17)
		
		hboxpython = gtk.HBox(5)
		hboxpython.show()
		python = gtk.Label("Python:")
		python.set_alignment(0, 0.5)
		python.show()
		
		VersionPython = gtk.Label(pythonversion)
		VersionPython.set_alignment(0, 0.5)
		VersionPython.show()
		
		hboxpython.pack_start(python, True, True)
		hboxpython.pack_start(VersionPython, True, True)
		
		hboxgtk = gtk.HBox(5)
		hboxgtk.show()
		
		gtkversion = "%d.%d.%d" % (gtk.gtk_version[0], gtk.gtk_version[1], gtk.gtk_version[2])
		VersionGTK = gtk.Label(gtkversion)
		
		gtkplus = gtk.Label("GTK+:")
		gtkplus.set_alignment(0, 0.5)
		gtkplus.show()
		
		VersionGTK.set_alignment(0, 0.5)
		VersionGTK.show()
		
		hboxgtk.pack_start(gtkplus, True, True)
		hboxgtk.pack_start(VersionGTK, True, True)
		
		hboxpygtk = gtk.HBox(5)
		hboxpygtk.show()
		
		pygtkversion = "%d.%d.%d" % (gtk.pygtk_version[0], gtk.pygtk_version[1], gtk.pygtk_version[2])
		VersionPyGTK = gtk.Label(pygtkversion)
			
		pygtkplus = gtk.Label("PyGTK+:")
		pygtkplus.set_alignment(0, 0.5)
		pygtkplus.show()
		
		VersionPyGTK.set_alignment(0, 0.5)
		VersionPyGTK.show()
		
		hboxpygtk.pack_start(pygtkplus, True, True)
		hboxpygtk.pack_start(VersionPyGTK, True, True)
		
		self.vbox2.pack_start(hboxpython, True, True)
		self.vbox2.pack_start(hboxgtk, True, True)
		self.vbox2.pack_start(hboxpygtk, True, True)
		
		self.vbox.pack_start(hbox, True, True)
		self.vbox.pack_start(self.frame1, True, True)
		
		
		
		self.show_all()

class AboutFiltersDialog(GenericAboutDialog):
	def __init__(self, parent):
		GenericAboutDialog.__init__(self, parent, _("About search filters"))
		label = gtk.Label(_("""Search filtering

You can use this to refine which results are displayed. The full results
from the server are always available if you clear all the search terms.

You can filter by:

Included text: Files are shown if they contain this text. Case is insensitive,
but word order is important. 'Spears Brittany' will not show any 'Brittany Spears'

Excluded text: As above, but files will not be displayed if the text matches

Size: Shows results based on size. use > and < to find files larger or smaller.
Files exactly the same as this term will always match. Use = to specify an exact
match. Use k or m to specify kilo or megabytes. >10M will find files larger than
10 megabytes. <4000k will find files smaller than 4000k.

Bitrate: Find files based on bitrate. Use < and > to find lower or higher. >192
finds 192 and higher, <192 finds 192 or lower. =192 only finds 192. for VBR, the
average bitrate is used.

Free slot: Show only those results from users which have at least one upload slot
free.

To set the filter, press Enter. This will apply to any existing results, and any
more that are returned. To filter in a different way, just set the relevant terms.
You do not need to do another search to apply a different filter."""))
		label.set_justify(gtk.JUSTIFY_LEFT)
		self.vbox.pack_start(label)
		self.show_all()

class GenericTableDialog(GenericAboutDialog):
	items = []
	def __init__(self, parent, title = ""):
		GenericAboutDialog.__init__(self, parent, title)
		self.set_resizable(True)
		ScrolledWindow = gtk.ScrolledWindow()
		ScrolledWindow.set_shadow_type(gtk.SHADOW_IN)
		ScrolledWindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		ScrolledWindow.show()
		self.resize(650, 500)
		vbox2 = gtk.VBox()
		vbox2.show()
		rows = len(self.items) / 2
		self.table = table = gtk.Table(rows, 2)
		table.set_col_spacings(5)
		table.set_row_spacings(2)
		for i in range(rows):
			l = gtk.Label()
			l.set_markup(self.items[i*2])
			l.set_alignment(0.0, 0.5)
			l.set_selectable(True)
			r = gtk.Label()
			r.set_markup(self.items[i*2+1])
			r.set_alignment(0.0, 0.5)
			r.set_line_wrap(True)
			r.set_selectable(True)
			table.attach(l, 0, 1, i, i+1, xoptions = gtk.FILL)

			table.attach(r, 1, 2, i, i+1, xoptions = gtk.FILL|gtk.EXPAND)
		vbox2.pack_start(table, False, False)
		vbox2.pack_start(gtk.Label(), True, True)
		ScrolledWindow.add_with_viewport(vbox2)
		self.vbox.pack_start(ScrolledWindow)
		self.show_all()

class AboutRoomsDialog(GenericTableDialog):
	items = [
	        "/join /j '" + _("room")+"'", _("Join room 'room'"),
	        "/leave /l '" + _("room") + "'", _("Leave room 'room'"),
	        "/part /p '" + _("room") + "'", _("Leave room 'room'"),
	        "/clear /cl", _("Clear the chat window"),
		"/tick /t", _("Set your personal ticker"),
	        "", "",
	        "/add /ad '" + _("user")+"'", _("Add user 'user' to your user list"),
		"/rem /unbuddy '" + _("user")+"'", _("Remove user 'user' from your user list"),
	        "/browse /b '" + _("user")+"'", _("Browse files of user 'user'"),
	        "/whois /w '" + _("user")+"'", _("Request user info for user 'user'"),
	        "/ip '" + _("user")+"'", _("Show IP for user 'user'"),
	        "", "",
	        "/alias /al '" + _("command") + "' '" +_("definition")+"'" , _("Add a new alias"),
		"/alias /al '" + _("command") + "' '" +_("definition")+"' |("+_("process")+")", _("Add a new alias that runs a process"),
	        "/unalias /un '" + _("command")+"'", _("Remove an alias"),
		"/now '", _("Display the Now Playing script's output"),
	        "", "",
	        "/ban '" + _("user")+"'", _("Add user 'user' to your ban list"),
	        "/unban '" + _("user")+"'", _("Remove user 'user' from your ban list"),
	        "/ignore '" + _("user")+"'", _("Add user 'user' to your ignore list"),
	        "/unignore '" + _("user")+"'", _("Remove user 'user' from your ignore list"),
	        "", "",
	        "/msg '" + _("user") + "' '" + _("message")+"'", _("Send message 'message' to user 'user'"),
	        "/pm '" + _("user")+"'", _("Open private chat window for user 'user'"),
	        "", "",
	        "/search /s '" + _("query")+"'", _("Start a new search for 'query'"),
	        "/rsearch /rs '" + _("query")+"'", _("Search the joined roms for 'query'"),
	        "/bsearch /bs '" + _("query")+"'", _("Search the buddy list for 'query'"),
	        "/usearch /us '" + _("user")+"' '" + _("query")+"'", _("Search a user's shares for 'query'"),
	        "", "",
	        "/rescan", _("Rescan shares"),
	        "/away /a", _("Toggles your away status"),
	        "/quit /q", _("Quit Nicotine"),
	]

	def __init__(self, parent):
		GenericTableDialog.__init__(self, parent, _("About chat room commands"))

class AboutPrivateDialog(GenericTableDialog):
	items = [
	        "/close /c", _("Close the current private chat"),
	        "/clear /cl", _("Clear the chat window"),
	        "", "",
	        "/add /ad '" + _("user")+"'" , _("Add user 'user' to your user list"),
		"/rem /unbuddy '" + _("user")+"'", _("Remove user 'user' from your user list"),
	        "/browse /b '" + _("user")+"'" , _("Browse files of user 'user'"),
	        "/whois /w '" + _("user")+"'" , _("Request user info for user 'user'"),
	        "/ip '" + _("user")+"'" , _("Show IP for user 'user'"),
	        "", "",
	        "/alias /al '" + _("command") + "' '" +_("definition")+"'" , _("Add a new alias"),
	        "/alias /al '" + _("command") + "' '" +_("definition") + "' |("+_("process")+")", _("Add a new alias that runs a process"),
	        "/unalias /un '" + _("command")+"'", _("Remove an alias"),
		"/now '", _("Display the Now Playing script's output"),
	        "", "",
	        "/ban '" + _("user")+"'" , _("Add user 'user' to your ban list"),
	        "/unban '" + _("user")+"'" , _("Remove user 'user' from your ban list"),
	        "/ignore '" + _("user")+"'" , _("Add user 'user' to your ignore list"),
	        "/unignore '" + _("user")+"'" , _("Remove user 'user' from your ignore list"),
	        "", "",
	        "/search /s '" + _("query")+"'", _("Start a new search for 'query'"),
	        "/rsearch /rs '" + _("query")+"'", _("Search the joined roms for 'query'"),
	        "/bsearch /bs '" + _("query")+"'", _("Search the buddy list for 'query'"),
	        "/usearch /us '" + _("query")+"'", _("Search a user's shares for 'query'"),
	        "", "",
		"/join /j '" + _("room")+"'", _("Join room 'room'"),
		"", "",
	        "/rescan", _("Rescan shares"),
	        "/away /a", _("Toggles your away status"),
	        "/quit /q", _("Quit Nicotine"),
	]

	def __init__(self, parent):
		GenericTableDialog.__init__(self, parent, _("About private chat commands"))

class AboutDependenciesDialog(GenericTableDialog):
	items = [
	        "<b>%s</b>" % _("Sound Effects"), "<i>%s</i>" % _("Gstreamer-python, gstreamer")+"\n"+ _("Website:")+" "+ "http://gstreamer.freedesktop.org/modules/gst-python.html" +"\n"+ "<i>%s</i>" % _("SoX")+"\n"+_("Website:")+" "+"http://sox.sourceforge.net/"+"\n"+ "<i>%s</i>" % _("Any other command-executable OGG player"),
		"", "",
		"<b>%s</b>" %_("Spell Checking"), "<i>%s</i>" % _("Libsexy, sexy-python") +"\n"+ _("Website:")+" "+"http://www.chipx86.com/wiki/Libsexy",
		"<b>%s</b>" %_("Speed Up"), "<i>%s</i>" % _("Psyco")+"\n"+_("Website:")+" "+"http://psyco.sourceforge.net/",
	        "<b>%s</b>" %_("IP Address Geolocation"), "<i>%s</i>" % _("GeoIP-Python")+"\n"+_("Website:")+" "+"http://www.maxmind.com/app/python",
		"<b>%s</b>" %_("OGG Metadata"), "<i>%s</i>" % _("PyVorbis") +" "+ _("(Warning: May be unstable)")+"\n"+_("Website:")+" "+ "http://ekyo.nerim.net/software/pyogg/",
	        "<b>%s</b>" %_("Download Notifications"), "<i>%s</i>" % _("notification-daemon, notify-python, libnotify") +"\n"+_("Website:")+" "+"http://www.galago-project.org/downloads.php",

	]

	def __init__(self, parent):
		GenericTableDialog.__init__(self, parent, _("About optional dependencies"))
		self.table.set_row_spacings(5)