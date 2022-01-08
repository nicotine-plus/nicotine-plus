# COPYRIGHT (C) 2020-2021 Nicotine+ Team
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

from gi.repository import Gtk

from pynicotine.config import config
from pynicotine.gtkgui.widgets.dialogs import dialog_show
from pynicotine.gtkgui.widgets.dialogs import set_dialog_properties
from pynicotine.gtkgui.widgets.theme import get_icon
from pynicotine.gtkgui.widgets.theme import ICON_THEME
from pynicotine.utils import open_uri


class About:

    AUTHORS = """Nicotine+ Contributors [active]

> Mat (mathiascode)
   - Maintainer (2020-present)
   - Developer

> Kip Warner
   - Maintainer (2018-2020)
   - Developer
   - Debianization
   - [kip(at)thevertigo(dot)com]

> eLvErDe
   - Maintainer (2013-2016)
   - Domain name administrator
   - Source code migration from SVN to GitHub
   - Developer

> Han Boetes
   - Tester
   - Documentation
   - Bug hunting
   - Translation management

> alekksander
   - Tester
   - Redesign of some graphics

> slook
   - Tester
   - Accessibility improvements

Nicotine+ Contributors [retired]

> daelstorm
   - Maintainer (2004-2009)
   - Developer
   - [daelstorm(at)gmail(dot)com]

> QuinoX
   - Maintainer (2009-2012)
   - Developer

> Michael Labouebe (aka gfarmerfr)
   - Maintainer (2016-2017)
   - Developer
   - [gfarmerfr(at)free(dot)fr]

> gallows (aka &apos;burp O&apos;)
   - Developer
   - Packager
   - Submitted Slack.Build file
   - [g4ll0ws(at)gmail(dot)com]

> hedonist (formerly known as alexbk)
   - OS X Nicotine.app maintainer / developer
   - Author of PySoulSeek, used for Nicotine core
   - [ak(at)sensi(dot)org]

> lee8oi
   - Bash commander
   - New and updated /alias
   - [winslaya(at)gmail(dot)com]

> INMCM
   - Nicotine+ topic maintainer on ubuntuforums.org
     https://ubuntuforums.org/showthread.php?t=196835

> suser-guru
   - Suse Linux packager
     https://dev-loki.blogspot.fr/
   - Nicotine+ RPM&apos;s for Suse 9.1, 9.2, 9.3, 10.0, 10.1

> osiris
   - Handy-man
   - Documentation
   - Some GNU/Linux packaging
   - Nicotine+ on Win32
   - Author of Nicotine+ guide
   - [osiris.contact(at)gmail(dot)com]

> Mutnick
   - Created Nicotine+ GitHub organization
   - Developer
   - [muhing(at)yahoo(dot)com]

> Lene Preuss
   - Python 3 migration
   - Unit and DEP-8 continuous integration testing
   - [lene.preuss(at)here(dot)com]


Nicotine Contributors [retired]

> Hyriand
   - Maintainer (2003-2004)
   - [hyriand(at)thegraveyard(dot)org]

> osiris
   - Handy-man
   - [osiris.contact(at)gmail(dot)com]

> SmackleFunky
   - Beta tester

> Wretched
   - Beta tester
   - Bringer of great ideas

> (va)\\*10^3
   - Beta tester
   - Designer of Nicotine homepage and artwork (logos)

> sierracat
   - MacOSX tester
   - soulseeX developer

> Gustavo
   - Created the exception dialog
   - [gjc(at)inescporto(dot)pt]

> SeeSchloss
   - Developer
   - Created 1.0.8 Win32 installer
   - Created Soulfind,
     open source Soulseek server written in D
     https://github.com/seeschloss/soulfind

> vasi
   - Mac developer
   - Packaged Nicotine on OSX PowerPC
   - [djvasi(at)gmail(dot)com]


PySoulSeek Contributors [retired]

> Alexander Kanavin
   - Maintainer (2001-2005)
   - [ak(at)sensi(dot)org]

> Nir Arbel
   - Helped with many protocol questions I had, and
     of course he designed and implemented the whole
     system.
   - [nir(at)slsk(dot)org]

> Zip (Brett W. Thompson)
   - I used his client code to get an initial
     impression of how the system works.
   - Supplied the patch for logging chat conversations.
   - [brettt(at)tfn(dot)net]

> Josselin Mouette
   - Official Debian package maintainer
   - [joss(at)debian(dot)org]

> blueboy
   - Former unofficial Debian package maintainer
   - [bluegeek(at)eresmas(dot)com]

> Christian Swinehart
   - Fink package maintainer
   - [cswinehart(at)users(dot)sourceforge(dot)net]

> Hyriand
   - Patches for upload bandwidth management,
     banning, various UI improvements and more
   - [hyriand(at)thegraveyard(dot)org]

> Geert Kloosterman
   - A script for importing Windows Soulseek
     configuration
   - [geertk(at)ai(dot)rug(dot)nl]

> Joe Halliwell
   - Submitted a patch for optionally discarding search
     results after closing a search tab
   - [s9900164(at)sms(dot)ed(dot)ac(dot)uk]

> Alexey Vyskubov
   - Code cleanups
   - [alexey(dot)vyskubov(at)nokia(dot)com]

> Jason Green
   - Ignore list and auto-join checkbox, wishlists
   - [smacklefunky(at)optusnet(dot)com(dot)au]


Attributions

- This product includes IP2Location LITE data
  available from:
  https://lite.ip2location.com

- Country flags licensed under the MIT License.
  Copyright (c) 2016 Bowtie AB
  Copyright (c) 2018 Jack Marsh
  https://github.com/jackiboy/flagpack

- tinytag licensed under the MIT License.
  Copyright (c) 2014-2018 Tom Wallroth
  https://github.com/devsnd/tinytag/

"""

    TRANSLATORS = """Dutch
 - hboetes (2021-2022)
 - nince78 (2007)
 - hyriand

English
 - mathiascode (2020-2022)
 - Michael Labouebe (2016)
 - hyriand
 - daelstorm

Euskara
 - The Librezale.org Team

Finnish
 - Kalevi

French
 - Lisapple (2021-2022)
 - zniavre (2007-2022)
 - melmorabity (2021-2022)
 - m-balthazar (2020)
 - Michael Labouebe (2016-2017)
 - ManWell (2007)
 - flashfr
 - systr

German
 - hboetes (2021-2022)
 - Meokater (2007)
 - (._.) (2007)
 - lippel (2004)
 - hyriand (2003)

Hungarian
 - djbaloo

Italian
 - Gianluca Boiano (2020-2022)
 - Nicola (2007)
 - dbazza

Lithuanian
 - mantas (2020)
 - Žygimantas Beručka (2006)

Polish
 - mariachini (2021-2022)
 - Amun-Ra (2007)
 - thine (2007)
 - owczi

Portuguese Brazilian
 - yyyyyyyan (2020)
 - Suicide|Solution (2006)

Russian
 - SnIPeRSnIPeR (2022)
 - Mehavoid (2021-2022)

Slovak
 - Josef Riha (2006)

Spanish
 - tagomago (2021-2022)
 - Strange (2021)
 - Silvio Orta (2007)
 - Dreslo

Swedish
 - mitramai (2021)
 - alimony

Turkish
 - Oğuz Ersen (2021-2022)"""

    def __init__(self, frame):

        self.frame = frame
        self.dialog = Gtk.AboutDialog(
            comments=config.summary,
            copyright=config.copyright,
            license_type=Gtk.License.GPL_3_0,
            version=config.version + "  •  GTK " + config.gtk_version,
            website=config.website_url,
            authors=self.AUTHORS.splitlines(),
            translator_credits=self.TRANSLATORS
        )
        set_dialog_properties(self.dialog, frame.MainWindow)
        main_icon = get_icon("n")

        if not main_icon:
            self.dialog.set_logo_icon_name(config.application_id)

        if Gtk.get_major_version() == 4:
            self.dialog.connect("close-request", lambda x: x.destroy())

            if main_icon:
                icon_data = ICON_THEME.lookup_by_gicon(main_icon, 128, 2, 0, 0)
                self.dialog.set_logo(icon_data)
        else:
            self.dialog.connect("response", lambda x, _y: x.destroy())

        # Override link handler with our own
        self.dialog.connect("activate-link", lambda x, url: open_uri(url))

    def show(self):
        dialog_show(self.dialog)
