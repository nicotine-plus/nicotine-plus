# -*- coding: utf-8 -*-
#
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2016 Mutnick <mutnick@techie.com>
# COPYRIGHT (C) 2008-2010 Quinox <quinox@users.sf.net>
# COPYRIGHT (C) 2006-2008 Daelstorm <daelstorm@gmail.com>
# COPYRIGHT (C) 2003-2004 Hyriand <hyriand@thegraveyard.org>
#
# GNU GENERAL PUBLIC LICENSE
#    Version 3, 29 June 2007
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

import sys
from gettext import gettext as _

import gi
from gi.repository import Gtk as gtk
from gi import __version__ as gobject_version

from pynicotine.gtkgui.utils import AppendLine
from pynicotine.utils import version

gi.require_version('Gtk', '3.0')


class GenericAboutDialog(gtk.Dialog):

    def __init__(self, parent, title="", nicotine=None):

        gtk.Dialog.__init__(
            self,
            title,
            parent,
            gtk.DialogFlags.MODAL,
            (gtk.STOCK_OK, gtk.ResponseType.OK)
        )

        if nicotine:
            self.set_icon(nicotine.images["n"])

        self.set_resizable(True)
        self.set_position(gtk.WindowPosition.CENTER)
        self.vbox.set_spacing(10)
        self.set_border_width(5)


class AboutDialog(gtk.Dialog):

    def __init__(self, parent, nicotine):

        self.nicotine = nicotine

        gtk.Dialog.__init__(self, _("About Nicotine+"), parent, gtk.DialogFlags.MODAL)

        self.set_resizable(True)
        self.set_position(gtk.WindowPosition.CENTER)
        self.vbox.set_spacing(10)
        self.set_border_width(5)

        img = gtk.Image()
        img.set_from_pixbuf(self.nicotine.images["n"])

        ScrolledWindow = gtk.ScrolledWindow()
        ScrolledWindow.show()
        ScrolledWindow.set_size_request(400, 250)

        TextView = gtk.TextView()
        TextView.set_wrap_mode(gtk.WrapMode.WORD)
        TextView.set_cursor_visible(False)
        TextView.set_editable(False)
        TextView.show()
        TextView.set_left_margin(3)
        ScrolledWindow.add(TextView)

        text = _("""Nicotine+ %s
Website:
https://www.nicotine-plus.org
Bug Tracker & Source Code:
https://github.com/Nicotine-Plus/nicotine-plus

Soulseek: http://www.slsknet.org

Based on code from Nicotine and PySoulSeek""") % version

        AppendLine(TextView, text, None, None, showstamp=False)
        vbox = gtk.VBox()
        vbox.pack_start(img, False, True, 0)
        hbox = gtk.HBox()
        hbox.set_spacing(10)
        hbox.pack_start(vbox, False, True, 0)
        hbox.pack_start(ScrolledWindow, True, True, 0)

        self.expander = gtk.Expander()
        self.expander.show()

        pythonversion = '.'.join(map(str, sys.version_info[:3]))

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

        hboxpython.pack_start(python, True, True, 0)
        hboxpython.pack_start(VersionPython, True, True, 0)

        hboxgtk = gtk.HBox(5)
        hboxgtk.show()

        gtkversion = f'{gtk.get_major_version()}.{gtk.get_minor_version()}.{gtk.get_micro_version()}'

        VersionGTK = gtk.Label(gtkversion)

        gtkplus = gtk.Label("GTK+:")
        gtkplus.set_alignment(0, 0.5)
        gtkplus.show()

        VersionGTK.set_alignment(0, 0.5)
        VersionGTK.show()

        hboxgtk.pack_start(gtkplus, True, True, 0)
        hboxgtk.pack_start(VersionGTK, True, True, 0)

        hboxpygtk = gtk.HBox(5)
        hboxpygtk.show()

        VersionPyGObject = gtk.Label(gobject_version)

        pygtkplus = gtk.Label("PyGObject:")
        pygtkplus.set_alignment(0, 0.5)
        pygtkplus.show()

        VersionPyGObject.set_alignment(0, 0.5)
        VersionPyGObject.show()

        hboxpygtk.pack_start(pygtkplus, True, True, 0)
        hboxpygtk.pack_start(VersionPyGObject, True, True, 0)

        self.vbox2.pack_start(hboxpython, True, True, 0)
        self.vbox2.pack_start(hboxgtk, True, True, 0)
        self.vbox2.pack_start(hboxpygtk, True, True, 0)

        self.vbox.pack_start(hbox, True, True, 0)
        self.vbox.pack_start(self.expander, True, True, 0)

        self.LicenseButton = self.nicotine.CreateIconButton(
            gtk.STOCK_ABOUT,
            "stock",
            self.license, _("License")
        )

        self.action_area.pack_start(self.LicenseButton, True, True, 0)

        self.CreditsButton = self.nicotine.CreateIconButton(
            gtk.STOCK_ABOUT,
            "stock",
            self.credits,
            _("Credits")
        )

        self.action_area.pack_start(self.CreditsButton, True, True, 0)

        self.CloseButton = self.nicotine.CreateIconButton(
            gtk.STOCK_CLOSE,
            "stock",
            self.click,
            _("Close")
        )

        self.action_area.pack_start(self.CloseButton, True, True, 0)

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
        self.DevScrolledWindow.show()

        self.DevTextView = gtk.TextView()
        self.DevTextView.set_wrap_mode(gtk.WrapMode.WORD)
        self.DevTextView.set_cursor_visible(False)
        self.DevTextView.set_editable(False)
        self.DevTextView.show()
        self.DevTextView.set_left_margin(3)
        self.DevScrolledWindow.add(self.DevTextView)

        text = """
# Nicotine+ MAINTAINERS

### Active

Michael Labouebe (aka gfarmerfr)
- Developer
- [gfarmerfr(at)free(dot)fr]

Mutnick
- Created Nicotine+ GitHub Organization
- Developer
- [mutnick(at)techie(dot)com]

eLvErDe
- Provides Nicotine+ Website
- Migrated source code from SVN to Github
- Developer (retired ?)

Kip Warner
- Debianization
- [kip(at)thevertigo(dot)com]

### Retired

daelstorm
- Developer
- [daelstorm(at)gmail(dot)com]

gallows (aka 'burp O')
- Developer, Packager
- [g4ll0ws(at)gmail(dot)com]
- Submitted Slack.Build file

QuinoX
- Developer

hedonist (formerly known as alexbk)
- OS X nicotine.app maintainer / developer
- [ak(at)sensi(dot)org]
- Author of original pyslsk, which is used for nicotine core

lee8oi
- Bash Commander
- [winslaya(at)gmail(dot)com]
- New and updated /alias

INMCM
- Nicotine+ topic maintainer on ubuntuforums.org
- http://ubuntuforums.org/showthread.php?t=196835

suser-guru
- Suse Linux packager
- https://dev-loki.blogspot.fr/
- Nicotine+ RPM's for Suse 9.1, 9.2, 9.3, 10.0, 10.1

osiris
- handy-man, documentation, some GNU/Linux packaging, Nicotine+ on win32
- Author of Nicotine+ Guide
- [osiris.contact(at)gmail(dot)com]

# Nicotine MAINTAINERS

### Retired

Hyriand
- Founder
- [hyriand(at)thegraveyard(dot)org]

osiris
- handy-man
- [osiris.contact(at)gmail(dot)com]

SmackleFunky
- Beta tester

Wretched
- Beta tester
- Bringer of great ideas

(va)\\*10^3
- Beta tester
- Designer of the old nicotine homepage and artwork (logos)

sierracat
- MacOSX tester
- Developed soulseeX

Gustavo
- [gjc(at)inescporto(dot)pt]
- Made the exception dialog

SeeSchloss
- Developer
- Made 1.0.8 win32 installer
- Created Soulfind http://seeschloss.org/soulfind.html,
  opensource Soulseek Server written in D

vasi
- Mac developer
- [djvasi@gmail.com]
- Packaged nicotine on OSX PowerPc

Country flags provided by http://flags.blogpotato.de/,
distributed under a CC BY-SA 3.0 Unported license."""

        AppendLine(self.DevTextView, text, None, None, showstamp=False)

        developersLabel = gtk.Label(_("Developers"))
        developersLabel.show()
        self.notebook.append_page(self.DevScrolledWindow, developersLabel)

        self.TransScrolledWindow = gtk.ScrolledWindow()
        self.TransScrolledWindow.show()

        self.TransTextView = gtk.TextView()
        self.TransTextView.set_wrap_mode(gtk.WrapMode.WORD)
        self.TransTextView.set_cursor_visible(False)
        self.TransTextView.set_editable(False)
        self.TransTextView.set_left_margin(3)
        self.TransTextView.show()
        self.TransScrolledWindow.add(self.TransTextView)

        text = """
Dutch
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
 * Michael Labouebe (2016-2017) <gfarmerfr@free.fr>
 * ManWell (2007)
 * ><((((*> (2007-2009)
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
 * Suicide|Solution (2006) <felipe@bunghole.com.br>

Lithuanian
 * Žygimantas Beručka (2006) <uid0@akl.lt>

Finnish
 * Kalevi <mr_auer@welho.net>

Euskara
 * The Librezale.org Team <librezale@librezale.org>"""

        AppendLine(self.TransTextView, text, None, None, showstamp=False)

        translatorsLabel = gtk.Label(_("Translators"))
        translatorsLabel.show()
        self.notebook.append_page(self.TransScrolledWindow, translatorsLabel)
        self.vbox.pack_start(self.notebook, True, True, 0)


class AboutLicenseDialog(GenericAboutDialog):

    def __init__(self, parent, nicotine):
        self.nicotine = nicotine
        GenericAboutDialog.__init__(self, parent, _("License"), self.nicotine)
        self.set_resizable(True)
        self.resize(550, 450)
        self.ScrolledWindow = gtk.ScrolledWindow()
        self.ScrolledWindow.show()

        self.TextView = gtk.TextView()
        self.TextView.set_cursor_visible(False)
        self.TextView.set_editable(False)
        self.TextView.set_left_margin(3)
        self.TextView.show()
        self.ScrolledWindow.add(self.TextView)

        text = """GNU General Public License version 3 notice

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
along with this program.  If not, see < http://www.gnu.org/licenses/ >."""

        AppendLine(self.TextView, text, None, None, showstamp=False)
        self.vbox.pack_start(self.ScrolledWindow, True, True, 0)
        self.show_all()


class AboutFiltersDialog(GenericAboutDialog):

    def __init__(self, parent):

        GenericAboutDialog.__init__(self, parent, _("About search filters"))

        label = gtk.Label(_("""Search filtering

You can use this to refine which results are displayed. The full results
from the server are always available if you clear all the search terms.

You can filter by:

Included text: Files are shown if they contain this text.
Case is insensitive, but word order is important.
'Spears Brittany' will not show any 'Brittany Spears'

Excluded text: As above, but files will not be displayed if the text matches

Size: Shows results based on size. use > and < to find files larger or smaller.
Files exactly the same as this term will always match.
Use = to specify an exact match. Use k or m to specify kilo or megabytes.
>10M will find files larger than 10 megabytes.
<4000k will find files smaller than 4000k.

Bitrate: Find files based on bitrate. Use < and > to find lower or higher.
>192 finds 192 and higher, <192 finds 192 or lower.
=192 only finds 192.
For VBR, the average bitrate is used.

Free slot: Show only those results from users which have at least
one upload slot free.

To set the filter, press Enter.
This will apply to any existing results, and any more that are returned.
To filter in a different way, just set the relevant terms.
You do not need to do another search to apply a different filter."""))

        label.set_justify(gtk.JUSTIFY_LEFT)
        label.set_selectable(True)
        self.vbox.pack_start(label, True, True, 0)
        self.show_all()


class GenericTableDialog(GenericAboutDialog):

    items = []

    def __init__(self, parent, title=""):

        GenericAboutDialog.__init__(self, parent, title)
        self.set_resizable(True)
        ScrolledWindow = gtk.ScrolledWindow()
        ScrolledWindow.show()
        self.resize(650, 500)
        vbox2 = gtk.VBox()
        vbox2.show()
        rows = len(self.items) / 2
        self.table = table = gtk.Table(rows, 2)
        table.set_col_spacings(5)
        table.set_row_spacings(2)

        for i in range(rows):
            l = gtk.Label()  # noqa: E741
            l.set_markup(self.items[i * 2])
            l.set_alignment(0.0, 0.5)
            l.set_selectable(True)
            r = gtk.Label()
            r.set_markup(self.items[i * 2 + 1])
            r.set_alignment(0.0, 0.5)
            r.set_line_wrap(True)
            r.set_selectable(True)
            table.attach(l, 0, 1, i, i + 1, xoptions=gtk.FILL)
            table.attach(r, 1, 2, i, i + 1, xoptions=gtk.FILL | gtk.EXPAND)

        vbox2.pack_start(table, False, False, 0)
        vbox2.pack_start(gtk.Label(), True, True, 0)
        ScrolledWindow.add_with_viewport(vbox2)
        self.vbox.pack_start(ScrolledWindow, True, True, 0)
        self.show_all()


class AboutRoomsDialog(GenericTableDialog):

    items = [
        "/join /j '%s'" % _("room"), _("Join room 'room'"),
        "/leave /l /part /p '%s'" % _("room"), _("Leave room 'room'"),
        "/clear /cl", _("Clear the chat window"),
        "/tick /t", _("Set your personal ticker"),
        "/tickers", _("Show all the tickers"),
        "/attach", _("Reattach a chat window to the notebook"),
        "/detach", _("Detach a chat tab from the notebook"),
        "", "",
        "/me %s" % _("message"), _("Say something in the third-person"),
        "/now", _("Display the Now Playing script's output"),
        "", "",
        "<b>%s</b>" % _("Users"), "",
        "/add /ad '%s'" % _("user"), _("Add user 'user' to your user list"),
        "/rem /unbuddy '%s'" % _("user"), _("Remove user 'user' from your user list"),
        "/ban '%s'" % _("user"), _("Add user 'user' to your ban list"),
        "/unban '%s'" % _("user"), _("Remove user 'user' from your ban list"),
        "/ignore '%s'" % _("user"), _("Add user 'user' to your ignore list"),
        "/unignore '%s'" % _("user"), _("Remove user 'user' from your ignore list"),
        "", "",
        "/browse /b '%s'" % _("user"), _("Browse files of user 'user'"),
        "/whois /w '%s'" % _("user"), _("Request user info for user 'user'"),
        "/ip '%s'" % _("user"), _("Show IP for user 'user'"),
        "", "",
        "<b>%s</b>" % _("Aliases"), "",
        "/alias /al '%s' '%s'" % (_("command"), _("definition")), _("Add a new alias"),
        "/alias /al '%s' '%s' |(%s)" % (_("command"), _("definition"), _("process")), _("Add a new alias that runs a process"),
        "/unalias /un '%s'" % _("command"), _("Remove an alias"),
        "", "",
        "<b>%s</b>" % _("Search"), "",
        "/search /s '%s'" % _("query"), _("Start a new search for 'query'"),
        "/rsearch /rs '%s'" % _("query"), _("Search the joined rooms for 'query'"),
        "/bsearch /bs '%s'" % _("query"), _("Search the buddy list for 'query'"),
        "/usearch /us '%s' '%s'" % (_("user"), _("query")), _("Search a user's shares for 'query'"),
        "", "",
        "<b>%s</b>" % _("Private Chat"), "",
        "/msg '%s' '%s'" % (_("user"), _("message")), _("Send message 'message' to user 'user'"),
        "/pm '%s'" % _("user"), _("Open private chat window for user 'user'"),
        "", "",
        "/away /a", _("Toggles your away status"),
        "/rescan", _("Rescan shares"),
        "/quit /q /exit", _("Quit Nicotine+")
    ]

    def __init__(self, parent):
        GenericTableDialog.__init__(
            self,
            parent,
            _("About chat room commands")
        )


class AboutPrivateDialog(GenericTableDialog):

    items = [
        "/close /c", _("Close the current private chat"),
        "/clear /cl", _("Clear the chat window"),
        "/detach", _("Detach a chat tab from the notebook"),
        "/attach", _("Reattach a chat window to the notebook"),
        "", "",
        "/me %s" % _("message"), _("Say something in the third-person"),
        "/now", _("Display the Now Playing script's output"),
        "", "",
        "/toggle %s" % _("plugin"), _("Toggle plugin on/off state"),
        "", "",
        "<b>%s</b>" % _("Users"), "",
        "/add /ad '%s'" % _("user"), _("Add user 'user' to your user list"),
        "/rem /unbuddy '%s'" % _("user"), _("Remove user 'user' from your user list"),
        "/ban '%s'" % _("user"), _("Add user 'user' to your ban list"),
        "/unban '%s'" % _("user"), _("Remove user 'user' from your ban list"),
        "/ignore '%s'" % _("user"), _("Add user 'user' to your ignore list"),
        "/unignore '%s'" % _("user"), _("Remove user 'user' from your ignore list"),
        "", "",
        "/browse /b '%s'" % _("user"), _("Browse files of user 'user'"),
        "/whois /w '%s'" % _("user"), _("Request user info for user 'user'"),
        "/ip '%s'" % _("user"), _("Show IP for user 'user'"),
        "", "",
        "<b>%s</b>" % _("Aliases"), "",
        "/alias /al '%s' '%s'" % (_("command"), _("definition")), _("Add a new alias"),
        "/alias /al '%s' '%s' |(%s)" % (_("command"), _("definition"), _("process")), _("Add a new alias that runs a process"),
        "/unalias /un '%s'" % _("command"), _("Remove an alias"),
        "", "",
        "<b>%s</b>" % _("Search"), "",
        "/search /s '%s'" % _("query"), _("Start a new search for 'query'"),
        "/rsearch /rs '%s'" % _("query"), _("Search the joined rooms for 'query'"),
        "/bsearch /bs '%s'" % _("query"), _("Search the buddy list for 'query'"),
        "/usearch /us '%s'" % _("query"), _("Search a user's shares for 'query'"),
        "", "",
        "<b>%s</b>" % _("Chat Rooms"), "",
        "/join /j '%s'" % _("room"), _("Join room 'room'"),
        "", "",
        "/away /a", _("Toggles your away status"),
        "/rescan", _("Rescan shares"),
        "/quit /q /exit", _("Quit Nicotine+")
    ]

    def __init__(self, parent):
        GenericTableDialog.__init__(
            self,
            parent,
            _("About private chat commands")
        )


class AboutDependenciesDialog(GenericTableDialog):

    items = [
        "<b>%s</b>" % _("Sound Effects"),
        "<i>%s</i>\n%s: %s" % (
            "Gstreamer-python, gstreamer",
            _("Website"),
            "http://gstreamer.freedesktop.org/modules/gst-python.html"
        ),
        "<b>%s</b>" % _("Spell Checking"),
        "<i>%s</i>\n%s: %s" % (
            "Libsexy, sexy-python",
            _("Website"),
            "http://www.chipx86.com/wiki/Libsexy"
        ),
        "<b>%s</b>" % _("IP Address Geolocation"),
        "<i>%s</i>\n%s: %s" % (
            "GeoIP-Python",
            _("Website"),
            "http://www.maxmind.com/app/python"
        ),
        "<b>%s</b>" % _("Download Notifications"),
        "<i>%s</i>\n%s: %s" % (
            "notification-daemon, notify-python, libnotify",
            _("Website"),
            "http://www.galago-project.org/downloads.php"
        )
    ]

    def __init__(self, parent):
        GenericTableDialog.__init__(
            self,
            parent,
            _("About optional dependencies")
        )
        self.table.set_row_spacings(5)
