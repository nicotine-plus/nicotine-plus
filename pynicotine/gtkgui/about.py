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

from gettext import gettext as _

import gi
from gi.repository import Gtk as gtk

from pynicotine.utils import version

gi.require_version('Gtk', '3.0')


class AboutDialog(gtk.AboutDialog):

    def __init__(self, parent):

        gtk.AboutDialog.__init__(
            self,
            _("About Nicotine+"),
            parent,
            gtk.DialogFlags.MODAL
        )
        self.set_logo_icon_name("org.nicotine_plus.Nicotine")
        self.set_program_name(_("Nicotine+"))
        self.set_version(version)
        self.set_comments(
            _("""A graphical client for the Soulseek peer-to-peer system
Based on code from Nicotine and PySoulSeek

This product includes IP2Location LITE data, available from:
https://www.ip2location.com""")
        )
        self.set_website("https://nicotine-plus.org")
        self.set_license_type(gtk.License.GPL_3_0_ONLY)
        self.set_authors(
            ["# Nicotine+ MAINTAINERS",
                """
### Active

Mutnick
- Created Nicotine+ GitHub Organization
- Developer
- [mutnick(at)techie(dot)com]

eLvErDe
- Provides Nicotine+ Website
- Migrated source code from SVN to Github
- python3-miniupnpc bindings
- Developer

Kip Warner
- Developer
- Debianization
- [kip(at)thevertigo(dot)com]

Lene Preuss
- Python3 migration
- Unit and DEP-8 continuous integration testing
- [lene.preuss(at)here(dot)com]

mathiascode
- Developer
- [mail(at)mathias(dot)is]

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
- ubuntuforums.org/showthread.php?t=196835

suser-guru
- Suse Linux packager
- dev-loki.blogspot.fr
- Nicotine+ RPM's for Suse 9.1, 9.2, 9.3, 10.0, 10.1

osiris
- handy-man
- documentation
- some GNU/Linux packaging
- Nicotine+ on win32
- Author of Nicotine+ Guide
- [osiris.contact(at)gmail(dot)com]

Michael Labouebe (aka gfarmerfr)
- Developer
- [gfarmerfr(at)free(dot)fr]
""",
                "# Nicotine MAINTAINERS",
                """
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
- Designer of the old nicotine homepage and artwork

sierracat
- MacOSX tester
- Developed soulseeX

Gustavo
- [gjc(at)inescporto(dot)pt]
- Made the exception dialog

SeeSchloss
- Developer
- Made 1.0.8 win32 installer
- Created Soulfind seeschloss.org/soulfind.html,
  opensource Soulseek Server written in D

vasi
- Mac developer
- [djvasi@gmail.com]
- Packaged nicotine on OSX PowerPc

Country flags provided by flags.blogpotato.de,
distributed under a CC BY-SA 3.0 Unported license.
"""]
        )
        self.set_translator_credits(
            """Dutch
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
        )
        self.show_all()


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
        self.set_border_width(10)


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

        label.set_justify(gtk.Justification.LEFT)
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
        rows = int(len(self.items) / 2)
        self.table = table = gtk.Table(rows, 2)
        table.set_col_spacings(5)
        table.set_row_spacings(2)

        for i in range(rows):
            l = gtk.Label()  # noqa: E741
            l.set_markup(self.items[i * 2])
            l.set_alignment(0.0, 0.0)
            l.set_selectable(True)
            r = gtk.Label()
            r.set_markup(self.items[i * 2 + 1])
            r.set_alignment(0.0, 0.0)
            r.set_line_wrap(True)
            r.set_selectable(True)
            table.attach(l, 0, 1, i, i + 1, xoptions=gtk.AttachOptions.FILL)
            table.attach(r, 1, 2, i, i + 1, xoptions=gtk.AttachOptions.FILL | gtk.AttachOptions.EXPAND)

        ScrolledWindow.add_with_viewport(table)
        ScrolledWindow.set_vadjustment(gtk.Adjustment(value=0))
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
