# COPYRIGHT (C) 2020-2022 Nicotine+ Contributors
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
from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.widgets.dialogs import Dialog
from pynicotine.utils import open_uri


class About(Dialog):

    AUTHORS = """Nicotine+ Team
–––––––––––––––––––––––––––––––––––––––>

> Mat (mathiascode)
   - Maintainer (2020–present)
   - Developer

> eLvErDe
   - Maintainer (2013–2016)
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


Inactive

> daelstorm
   - Maintainer (2004–2009)
   - Developer

> QuinoX
   - Maintainer (2009–2012)
   - Developer

> Michael Labouebe (gfarmerfr)
   - Maintainer (2016–2017)
   - Developer

> Kip Warner
   - Maintainer (2018–2020)
   - Developer
   - Debianization

> gallows (aka 'burp O')
   - Developer
   - Packager
   - Submitted Slack.Build file

> hedonist (formerly known as alexbk)
   - OS X Nicotine.app maintainer / developer
   - Author of PySoulSeek, used for Nicotine core

> lee8oi
   - Bash commander
   - New and updated /alias

> INMCM
   - Nicotine+ topic maintainer on ubuntuforums.org

> suser-guru
   - Suse Linux packager
   - Nicotine+ RPM's for Suse 9.1, 9.2, 9.3, 10.0, 10.1

> osiris
   - Handy-man
   - Documentation
   - Some GNU/Linux packaging
   - Nicotine+ on Win32
   - Author of Nicotine+ guide

> Mutnick
   - Created Nicotine+ GitHub organization
   - Developer

> Lene Preuss
   - Python 3 migration
   - Unit and DEP-8 continuous integration testing


Nicotine Team
–––––––––––––––––––––––––––––––––––––––>

> Ingmar K. Steen (Hyriand)
   - Maintainer (2003–2004)

> daelstorm
   - Beta tester
   - Designer of most of the settings
   - Made the Nicotine icons

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

> Gustavo J. A. M. Carneiro
   - Created the exception dialog

> SeeSchloss
   - Developer
   - Created 1.0.8 Win32 installer
   - Created Soulfind,
     open source Soulseek server written in D

> vasi
   - Mac developer
   - Packaged Nicotine on OSX PowerPC


PySoulSeek Contributors
–––––––––––––––––––––––––––––––––––––––>

> Alexander Kanavin
   - Maintainer (2001–2003)

> Nir Arbel
   - Helped with many protocol questions I had, and
     of course he designed and implemented the whole
     system.

> Brett W. Thompson (Zip)
   - I used his client code to get an initial
     impression of how the system works.
   - Supplied the patch for logging chat conversations.

> Josselin Mouette
   - Official Debian package maintainer

> blueboy
   - Former unofficial Debian package maintainer

> Christian Swinehart
   - Fink package maintainer

> Ingmar K. Steen (Hyriand)
   - Patches for upload bandwidth management,
     banning, various UI improvements and more

> Geert Kloosterman
   - A script for importing Windows Soulseek
     configuration

> Joe Halliwell
   - Submitted a patch for optionally discarding search
     results after closing a search tab

> Alexey Vyskubov
   - Code cleanups

> Jason Green (SmackleFunky)
   - Ignore list and auto-join checkbox, wishlists


Third-Party Attributions
–––––––––––––––––––––––––––––––––––––––>

- This program includes IP2Location LITE data
  available from:
  https://lite.ip2location.com

- Country flags licensed under the MIT License.
  Copyright (c) 2016–2017 Bowtie AB
  Copyright (c) 2018–2020 Jack Marsh
  https://github.com/jackiboy/flagpack

- tinytag licensed under the MIT License.
  Copyright (c) 2014–2022 Tom Wallroth
  https://github.com/devsnd/tinytag/


"""

    TRANSLATORS = """Nicotine+ Translators
–––––––––––––––––––––––––––––––––––––––>

Catalan
 - Maite Guix (2022)

Chinese (Simplified)
 - hadwin (2022)

Czech
 - burnmail123 (2021)

Danish
 - mathsped (2003–2004)

Dutch
 - Han Boetes (hboetes) (2021–2022)
 - Kenny Verstraete (2009)
 - nince78 (2007)
 - Ingmar K. Steen (Hyriand) (2003–2004)

English
 - slook (2021–2022)
 - Han Boetes (hboetes) (2021–2022)
 - Mat (mathiascode) (2020–2022)
 - Michael Labouebe (gfarmerfr) (2016)
 - daelstorm (2004–2009)
 - Ingmar K. Steen (Hyriand) (2003–2004)

Euskara
 - Julen (2006–2007)

Finnish
 - Kari Viittanen (Kalevi) (2006–2007)

French
 - Lisapple (2021–2022)
 - melmorabity (2021–2022)
 - m-balthazar (2020)
 - Michael Labouebe (gfarmerfr) (2016–2017)
 - Monsieur Poisson (2009–2010)
 - ManWell (2007)
 - zniavre (2007–2022)
 - systr (2006)
 - Julien Wajsberg (flashfr) (2003–2004)

German
 - Han Boetes (hboetes) (2021–2022)
 - Meokater (2007)
 - (._.) (2007)
 - lippel (2004)
 - Ingmar K. Steen (Hyriand) (2003–2004)

Hungarian
 - Szia Tomi (2022)
 - Nils (2009)
 - David Balazs (djbaloo) (2006–2020)

Italian
 - Gabboxl (2022)
 - Gianluca Boiano (2020–2022)
 - nicola (2007)
 - dbazza (2003–2004)

Lithuanian
 - mantas (2020)
 - Žygimantas Beručka (2006–2009)

Norwegian Bokmål
 - Allan Nordhøy (comradekingu) (2021)

Polish
 - mariachini (2017–2022)
 - Amun-Ra (2007)
 - thine (2007)
 - Wojciech Owczarek (owczi) (2003–2004)

Portuguese (Brazil)
 - Guilherme Santos (2022)
 - b1llso (2022)
 - Nicolas Abril (2021)
 - yyyyyyyan (2020)
 - Felipe Nogaroto Gonzalez (Suicide|Solution) (2006)

Russian
 - SnIPeRSnIPeR (2022)
 - Mehavoid (2021–2022)

Slovak
 - Jozef Říha (2006-2008)

Spanish (Chile)
 - MELERIX (2021–2022)
 - tagomago (2021–2022)
 - Strange (2021)
 - Silvio Orta (2007)
 - Dreslo (2003–2004)

Spanish (Spain)
 - MELERIX (2021)
 - tagomago (2021–2022)
 - Strange (2021)
 - Silvio Orta (2007)
 - Dreslo (2003–2004)

Swedish
 - mitramai (2021)
 - Markus Magnuson (alimony) (2003–2004)

Turkish
 - Oğuz Ersen (2021–2022)

Ukrainian
 - uniss2209 (2022)

"""

    def __init__(self, frame):

        dialog = Gtk.AboutDialog(
            logo_icon_name=config.application_id,
            comments=config.summary,
            copyright=config.copyright,
            license_type=Gtk.License.GPL_3_0,
            version=config.version + "  •  GTK " + config.gtk_version,
            website=config.website_url,
            authors=self.AUTHORS.splitlines(),
            translator_credits=self.TRANSLATORS + config.translations_url
        )
        super().__init__(dialog=dialog, parent=frame.window)

        # Override link handler with our own
        dialog.connect("activate-link", lambda x, url: open_uri(url))

        if GTK_API_VERSION == 3:
            dialog.connect("response", lambda x, _y: x.destroy())
