# Copyright (c) 2003-2004 Hyriand. All rights reserved.
#
import gtk
import os
from pynicotine.utils import version
import imagedata

from pynicotine.utils import _

class GenericAboutDialog(gtk.Dialog):
	def __init__(self, parent, title = ""):
		gtk.Dialog.__init__(self, title, parent, gtk.DIALOG_MODAL, (gtk.STOCK_OK, gtk.RESPONSE_OK))
		self.set_resizable(False)
		self.set_position(gtk.WIN_POS_CENTER)
		self.vbox.set_spacing(10)
		self.set_border_width(10)

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

Copyright (c) 2003 Hyriand
http://nicotine.thegraveyard.org/
hyriand@thegraveyard.org

Based on code from the PySoulSeek project
Copyright (c) 2001-2003 Alexander Kanavin

With additions by daelstorm (c) 2006

Released under the GNU Public License

See MAINTAINERS file for the list of contributors""") % version)
		label.set_justify(gtk.JUSTIFY_CENTER)
		vbox = gtk.VBox()
		vbox.pack_start(img, False, False)
		hbox = gtk.HBox()
		hbox.set_spacing(10)
		hbox.pack_start(vbox, True, True)
		hbox.pack_start(label, True, True)
		self.vbox.pack_start(hbox, True, True)
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
		label.set_justify(gtk.JUSTIFY_CENTER)
		self.vbox.pack_start(label)
		self.show_all()

class GenericTableDialog(GenericAboutDialog):
	items = []
	def __init__(self, parent, title = ""):
		GenericAboutDialog.__init__(self, parent, title)
		rows = len(self.items) / 2
		table = gtk.Table(rows, 2)
		table.set_col_spacings(5)
		for i in range(rows):
			l = gtk.Label(self.items[i*2])
			l.set_alignment(0.0, 0.5)
			r = gtk.Label(self.items[i*2+1])
			r.set_alignment(0.0, 0.5)
			table.attach(l, 0, 1, i, i+1, xoptions = gtk.FILL|gtk.EXPAND)
			table.attach(r, 1, 2, i, i+1)
		self.vbox.pack_start(table)
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
	        "/browse /b '" + _("user")+"'", _("Browse files of user 'user'"),
	        "/whois /w '" + _("user")+"'", _("Request user info for user 'user'"),
	        "/ip '" + _("user")+"'", _("Show IP for user 'user'"),
	        "", "",
	        "/alias /al '" + _("command") + "' '" +_("definition")+"'" , _("Add a new alias"),
		"/alias /al '" + _("command") + "' '" +_("definition")+"' |("+_("process")+")", _("Add a new alias that runs a process"),
	        "/unalias /un '" + _("command")+"'", _("Remove an alias"),
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
	        "/browse /b '" + _("user")+"'" , _("Browse files of user 'user'"),
	        "/whois /w '" + _("user")+"'" , _("Request user info for user 'user'"),
	        "/ip '" + _("user")+"'" , _("Show IP for user 'user'"),
	        "", "",
	        "/alias /al '" + _("command") + "' '" +_("definition")+"'" , _("Add a new alias"),
	        "/alias /al '" + _("command") + "' '" +_("definition") + "' |("+_("process")+")", _("Add a new alias that runs a process"),
	        "/unalias /un '" + _("command")+"'", _("Remove an alias"),
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
	        "/rescan", _("Rescan shares"),
	        "/away /a", _("Toggles your away status"),
	        "/quit /q", _("Quit Nicotine"),
	]

	def __init__(self, parent):
		GenericTableDialog.__init__(self, parent, _("About private chat commands"))
