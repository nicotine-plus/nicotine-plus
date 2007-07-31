# Copyright (C) 2007 daelstorm. All rights reserved.
# -*- coding: utf-8 -*-
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
import os, sys
from pynicotine.utils import version
import imagedata

from pynicotine.utils import _
from utils import AppendLine
class GenericAboutDialog(gtk.Dialog):
	def __init__(self, parent, title = "", nicotine=None):
		gtk.Dialog.__init__(self, title, parent, gtk.DIALOG_MODAL, (gtk.STOCK_OK, gtk.RESPONSE_OK))
		if nicotine:
			self.set_icon(nicotine.images["n"])
		
		self.set_resizable(False)
		self.set_position(gtk.WIN_POS_CENTER)
		self.vbox.set_spacing(10)
		self.set_border_width(5)

class AboutDialog(gtk.Dialog):
	def __init__(self, parent, nicotine):
		self.nicotine = nicotine
		gtk.Dialog.__init__(self, "About Nicotine", parent, gtk.DIALOG_MODAL)
		
		self.set_resizable(False)
		self.set_position(gtk.WIN_POS_CENTER)
		self.vbox.set_spacing(10)
		self.set_border_width(5)
		img = gtk.Image()
		img.set_from_pixbuf(self.nicotine.images["nicotinen"])
		
		ScrolledWindow = gtk.ScrolledWindow()
		ScrolledWindow.set_shadow_type(gtk.SHADOW_IN)
		ScrolledWindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		ScrolledWindow.show()
		ScrolledWindow.set_size_request(250, -1)
		TextView = gtk.TextView()
		TextView.set_wrap_mode(gtk.WRAP_WORD)
		TextView.set_cursor_visible(False)
		TextView.set_editable(False)
		TextView.show()
		TextView.set_left_margin(3)
		ScrolledWindow.add(TextView)
		
		text = _("""Nicotine+ %s
Website:
http://nicotine-plus.sourceforge.net
Trac and Wiki:
http://nicotine-plus.org
Sourceforge Project:
http://sourceforge.net/projects/nicotine-plus/

Soulseek: http://www.slsknet.org

Based on code from Nicotine and PySoulSeek""") % version
		AppendLine(TextView, text, None, None)
		vbox = gtk.VBox()
		vbox.pack_start(img, False, True)
		hbox = gtk.HBox()
		hbox.set_spacing(10)
		hbox.pack_start(vbox, False, True)
		hbox.pack_start(ScrolledWindow, True, True)

		
		self.expander = gtk.Expander(_("Dependencies"))
		self.expander.show()
		
		pythonversion = "%d.%d.%d" % (sys.version_info[0], sys.version_info[1], sys.version_info[2])
		
		self.vbox2 = gtk.VBox()
		self.vbox2.set_spacing(5)
		self.vbox2.set_border_width(5)
		self.expander.add(self.vbox2)

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
		self.vbox.pack_start(self.expander, True, True)
		

		self.LicenseButton = self.nicotine.CreateIconButton(gtk.STOCK_ABOUT, "stock", self.license, _("License"))

		self.action_area.pack_start(self.LicenseButton)

		self.CreditsButton = self.nicotine.CreateIconButton(gtk.STOCK_ABOUT, "stock", self.credits, _("Credits"))

		self.action_area.pack_start(self.CreditsButton)
		
		self.CloseButton = self.nicotine.CreateIconButton(gtk.STOCK_CLOSE, "stock", self.click, _("Close"))

		self.CloseButton.set_flags(gtk.CAN_DEFAULT)
		self.action_area.pack_start(self.CloseButton)
		
		self.show_all()
		
	def quit(self, w=None, event=None):
		self.hide()
		self.destroy()
		
	def credits(self, button):
		dlg = AboutCreditsDialog(self, self.nicotine)
		dlg.run()
		dlg.destroy()
		
	def license(self, button):
		dlg = AboutLicenseDialog(self, self.nicotine)
		dlg.run()
		dlg.destroy()
		
	def click(self, button):

		self.quit()
		
class AboutCreditsDialog(GenericAboutDialog):
	def __init__(self, parent, nicotine):
		self.nicotine = nicotine
		GenericAboutDialog.__init__(self, parent, _("Credits"), self.nicotine)
		self.set_resizable(True)
		self.resize(450, 300)
		self.notebook = gtk.Notebook()
		self.notebook.show()
		self.DevScrolledWindow = gtk.ScrolledWindow()
		self.DevScrolledWindow.set_shadow_type(gtk.SHADOW_IN)
		self.DevScrolledWindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		self.DevScrolledWindow.show()
		
		self.DevTextView = gtk.TextView()
		self.DevTextView.set_wrap_mode(gtk.WRAP_WORD)
		self.DevTextView.set_cursor_visible(False)
		self.DevTextView.set_editable(False)
		self.DevTextView.show()
		self.DevTextView.set_left_margin(3)
		self.DevScrolledWindow.add(self.DevTextView)
		

		text = _("""daelstorm
\t(Lead developer)
\t<daelstorm@gmail.com>
\thttp://thegraveyard.org/daelstorm/
gallows
\t(Developer, packager)
\t<g4ll0ws@gmail.com>
\thttp://perticone.homelinux.net/~sergio/
hyriand
\t(Former lead developer, contributer, author of Nicotine)
\t<iksteen@gmail.com>
\thttp://www.thegraveyard.org
Le Vert
\t(Webhosting, packager)
\t<gandalf@le-vert.net>
\thttp://www.le-vert.net
QuinoX
\t(Code contributer)
\thttp://index.qtea.nl
infinito
\t(Code contributer)
\t<code@infinicode.org>
\thttp://infinicode.org
suser-guru
\t(SUSE Packager)
\thttp://linux01.gwdg.de/~pbleser/
osiris
\t(Documentation, old Win32 installers)
\t<osiris.contact@gmail.com>
Alexander Kanavin
\t(PySoulSeek developer) Nicotine and Nicotine+ are based on PySoulSeek
\thttp://sensi.org/~ak/
""")
		AppendLine(self.DevTextView, text, None, None)
		
		developersLabel = gtk.Label(_("Developers"))
		developersLabel.show()
		self.notebook.append_page(self.DevScrolledWindow, developersLabel)

		self.TransScrolledWindow = gtk.ScrolledWindow()
		self.TransScrolledWindow.set_shadow_type(gtk.SHADOW_IN)
		self.TransScrolledWindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		self.TransScrolledWindow.show()
		
		self.TransTextView = gtk.TextView()
		self.TransTextView.set_wrap_mode(gtk.WRAP_WORD)
		self.TransTextView.set_cursor_visible(False)
		self.TransTextView.set_editable(False)
		self.TransTextView.set_left_margin(3)
		self.TransTextView.show()
		self.TransScrolledWindow.add(self.TransTextView)
	
		text = _("""Dutch
 * nince78 (2007)
 * hyriand
German
 * Meokater (2007)
 * (._.) (2007)
 * lippel (2004)
 * hyriand (2003)
Spanish
 * Silvio Orta (2007)
 * Dreslo
French
 * ManWell (2007)
 * ><((((*> (2007)
 * flashfr
 * systr
Italian
 * Nicola (2007) <info@nicoladimaria.info>
 * dbazza
Polish
 * Amun-Ra (2007)
 * thine (2007)
 * owczi
Swedish
 * alimony <markus@samsonrourke.com>
Hungarian
 * djbaloo <dj_baloo@freemail.hu>
Slovak 
 * Josef Riha (2006) <jose1711@gmail.com>
Portuguese Brazilian
 * Suicide|Solution <felipe@bunghole.com.br> (2006) http://suicide.bunghole.com.br
Lithuanian
 * Žygimantas Beručka (2006) <uid0@akl.lt>
Finnish
 * Kalevi <mr_auer@welho.net>
Euskara
 * The Librezale.org Team <librezale@librezale.org> http://librezale.org
 """)
 		AppendLine(self.TransTextView, text, None, None)
		
		translatorsLabel = gtk.Label(_("Translators"))
		translatorsLabel.show()
		self.notebook.append_page(self.TransScrolledWindow, translatorsLabel)
		self.vbox.pack_start(self.notebook)
		
class AboutLicenseDialog(GenericAboutDialog):
	def __init__(self, parent, nicotine):
		self.nicotine = nicotine
		GenericAboutDialog.__init__(self, parent, _("License"), self.nicotine)
		label = gtk.Label(_("""GNU General Public License version 3 notice

Copyright (C) 2007 daelstorm. All rights reserved.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>."""))
		label.set_justify(gtk.JUSTIFY_LEFT)
		label.set_selectable(True)
		self.vbox.pack_start(label)
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
		label.set_selectable(True)
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
			"/me " + _("message")+"", _("Say something in the third-person"),
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
		"/now", _("Display the Now Playing script's output"),
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