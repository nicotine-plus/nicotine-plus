# COPYRIGHT (C) 2020-2024 Nicotine+ Contributors
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

from gi.repository import Gtk

import pynicotine
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.widgets import ui
from pynicotine.gtkgui.widgets.dialogs import Dialog
from pynicotine.gtkgui.widgets.theme import add_css_class
from pynicotine.gtkgui.widgets.theme import remove_css_class
from pynicotine.utils import open_uri


class About(Dialog):

    AUTHORS = [
        "<b>Nicotine+ Team</b>",

        """<b>Mat (mathiascode)</b>
 •  Maintainer (2020–present)
 •  Developer""",

        """<b>eLvErDe</b>
 •  Maintainer (2013–2016)
 •  Domain name administrator
 •  Source code migration from SVN to GitHub
 •  Developer""",

        """<b>Han Boetes</b>
 •  Tester
 •  Documentation
 •  Bug hunting
 •  Translation management""",

        """<b>alekksander</b>
 •  Tester
 •  Redesign of some graphics""",

        """<b>slook</b>
 •  Tester
 •  Accessibility improvements""",


        "\nInactive",

        """<b>daelstorm</b>
 •  Maintainer (2004–2009)
 •  Developer""",

        """<b>quinox</b>
 •  Maintainer (2009–2012)
 •  Developer""",

        """<b>Michael Labouebe (gfarmerfr)</b>
 •  Maintainer (2016–2017)
 •  Developer""",

        """<b>Kip Warner</b>
 •  Maintainer (2018–2020)
 •  Developer
 •  Debianization""",

        """<b>gallows (aka 'burp O')</b>
 •  Developer
 •  Packager
 •  Submitted Slack.Build file""",

        """<b>hedonist (formerly known as alexbk)</b>
 •  OS X Nicotine.app maintainer / developer
 •  Author of PySoulSeek, used for Nicotine core""",

        """<b>lee8oi</b>
 •  Bash commander
 •  New and updated /alias""",

        """<b>INMCM</b>
 •  Nicotine+ topic maintainer on ubuntuforums.org""",

        """<b>suser-guru</b>
 •  Suse Linux packager
 •  Nicotine+ RPM's for Suse 9.1, 9.2, 9.3, 10.0, 10.1""",

        """<b>osiris</b>
 •  Handy-man
 •  Documentation
 •  Some GNU/Linux packaging
 •  Nicotine+ on Win32
 •  Author of Nicotine+ guide""",

        """<b>Mutnick</b>
 •  Created Nicotine+ GitHub organization
 •  Developer""",

        """<b>Lene Preuss</b>
 •  Python 3 migration
 •  Unit and DEP-8 continuous integration testing""",


        "\n<b>Nicotine Team</b>",

        """<b>Ingmar K. Steen (Hyriand)</b>
 •  Maintainer (2003–2004)""",

        """<b>daelstorm</b>
 •  Beta tester
 •  Designer of most of the settings
 •  Made the Nicotine icons""",

        """<b>SmackleFunky</b>
 •  Beta tester""",

        """<b>Wretched</b>
 •  Beta tester
 •  Bringer of great ideas""",

        """<b>(va)\\*10^3</b>
 •  Beta tester
 •  Designer of Nicotine homepage and artwork (logos)""",

        """<b>sierracat</b>
 •  MacOSX tester
 •  soulseeX developer""",

        """<b>Gustavo J. A. M. Carneiro</b>
 •  Created the exception dialog""",

        """<b>SeeSchloss</b>
 •  Developer
 •  Created 1.0.8 Win32 installer
 •  Created Soulfind, open source Soulseek server written in D""",

        """<b>vasi</b>
 •  Mac developer
 •  Packaged Nicotine on OSX PowerPC""",


        "\n<b>PySoulSeek Contributors</b>",

        """<b>Alexander Kanavin</b>
 •  Maintainer (2001–2003)""",

        """<b>Nir Arbel</b>
 •  Helped with many protocol questions, and of course he designed and implemented the whole system""",

        """<b>Brett W. Thompson (Zip)</b>
 •  His client code was used to get an initial impression of how the system works
 •  Supplied the patch for logging chat conversations""",

        """<b>Josselin Mouette</b>
 •  Official Debian package maintainer""",

        """<b>blueboy</b>
 •  Former unofficial Debian package maintainer""",

        """<b>Christian Swinehart</b>
 •  Fink package maintainer""",

        """<b>Ingmar K. Steen (Hyriand)</b>
 •  Patches for upload bandwidth management, banning, various UI improvements and more""",

        """<b>Geert Kloosterman</b>
 •  A script for importing Windows Soulseek configuration""",

        """<b>Joe Halliwell</b>
 •  Submitted a patch for optionally discarding search results after closing a search tab""",

        """<b>Alexey Vyskubov</b>
 •  Code cleanups""",

        """<b>Jason Green (SmackleFunky)</b>
 •  Ignore list and auto-join checkbox, wishlists"""]

    TRANSLATORS = [
        "<b>Nicotine+ Translators</b>",

        """<b>Albanian</b>
 •  W L (2023)""",

        """<b>Arabic</b>
 •  ButterflyOfFire (2024)""",

        """<b>Catalan</b>
 •  Maite Guix (2022)""",

        """<b>Chinese (Simplified)</b>
 •  Bonislaw (2023)
 •  hylau (2023)
 •  hadwin (2022)""",

        """<b>Czech</b>
 •  burnmail123 (2021-2023)""",

        """<b>Danish</b>
 •  mathsped (2003–2004)""",

        """<b>Dutch</b>
 •  Han Boetes (hboetes) (2021–2023)
 •  Kenny Verstraete (2009)
 •  nince78 (2007)
 •  Ingmar K. Steen (Hyriand) (2003–2004)""",

        """<b>English</b>
 •  slook (2021–2023)
 •  Han Boetes (hboetes) (2021–2023)
 •  Mat (mathiascode) (2020–2023)
 •  Michael Labouebe (gfarmerfr) (2016)
 •  daelstorm (2004–2009)
 •  Ingmar K. Steen (Hyriand) (2003–2004)""",

        """<b>Esperanto</b>
 •  phlostically (2021)""",

        """<b>Estonian</b>
 •  PriitUring (2023)""",

        """<b>Euskara</b>
 •  Julen (2006–2007)""",

        """<b>Finnish</b>
 •  Kari Viittanen (Kalevi) (2006–2007)""",

        """<b>French</b>
 •  Saumon (2023)
 •  subu_versus (2023)
 •  zniavre (2007–2023)
 •  Lisapple (2021–2022)
 •  melmorabity (2021–2022)
 •  m-balthazar (2020)
 •  Michael Labouebe (gfarmerfr) (2016–2017)
 •  Monsieur Poisson (2009–2010)
 •  ManWell (2007)
 •  systr (2006)
 •  Julien Wajsberg (flashfr) (2003–2004)""",

        """<b>German</b>
 •  Han Boetes (hboetes) (2021–2023)
 •  phelissimo_ (2023)
 •  Meokater (2007)
 •  (._.) (2007)
 •  lippel (2004)
 •  Ingmar K. Steen (Hyriand) (2003–2004)""",

        """<b>Hungarian</b>
 •  Szia Tomi (2022–2023)
 •  Nils (2009)
 •  David Balazs (djbaloo) (2006–2020)""",

        """<b>Italian</b>
 •  Gabboxl (2022–2023)
 •  ms-afk (2023)
 •  Gianluca Boiano (2020–2022)
 •  nicola (2007)
 •  dbazza (2003–2004)""",

        """<b>Latvian</b>
 •  Pagal3 (2022–2023)""",

        """<b>Lithuanian</b>
 •  mantas (2020)
 •  Žygimantas Beručka (2006–2009)""",

        """<b>Norwegian Bokmål</b>
 •  Allan Nordhøy (comradekingu) (2021)""",

        """<b>Polish</b>
 •  Mariusz (mariachini) (2017–2023)
 •  Amun-Ra (2007)
 •  thine (2007)
 •  Wojciech Owczarek (owczi) (2003–2004)""",

        """<b>Portuguese</b>
 •  ssantos (2023)
 •  Vinícius Soares (2023)""",

        """<b>Portuguese (Brazil)</b>
 •  Havokdan (2022–2023)
 •  Guilherme Santos (2022)
 •  b1llso (2022)
 •  Nicolas Abril (2021)
 •  yyyyyyyan (2020)
 •  Felipe Nogaroto Gonzalez (Suicide|Solution) (2006)""",

        """<b>Romanian</b>
 •  xslendix (2023)""",

        """<b>Russian</b>
 •  Kirill Feoktistov (SnIPeRSnIPeR) (2022–2023)
 •  Mehavoid (2021–2023)
 •  AHOHNMYC (2022)""",

        """<b>Slovak</b>
 •  Jozef Říha (2006–2008)""",

        """<b>Spanish (Chile)</b>
 •  MELERIX (2021–2023)
 •  tagomago (2021–2022)
 •  Strange (2021)
 •  Silvio Orta (2007)
 •  Dreslo (2003–2004)""",

        """<b>Spanish (Spain)</b>
 •  gallegonovato (2023)
 •  MELERIX (2021–2023)
 •  tagomago (2021–2022)
 •  Strange (2021)
 •  Silvio Orta (2007)
 •  Dreslo (2003–2004)""",

        """<b>Swedish</b>
 •  mitramai (2021)
 •  Markus Magnuson (alimony) (2003–2004)""",

        """<b>Turkish</b>
 •  Oğuz Ersen (2021–2023)""",

        """<b>Ukrainian</b>
 •  uniss2209 (2022)"""]

    LICENSE = [
        """Nicotine+ is licensed under the <a href="https://www.gnu.org/licenses/gpl-3.0.html">
GNU General Public License v3.0 or later</a>, with the following exceptions:""",

        """<b>tinytag licensed under the MIT License.</b>
Copyright (c) 2014–2023 Tom Wallroth
Copyright (c) 2021-2023 Mat (mathiascode)
<a href="https://github.com/devsnd/tinytag">https://github.com/devsnd/tinytag</a>""",

        """<b>Country flags licensed under the MIT License.</b>
Copyright (c) 2016–2021 Bowtie AB
<a href="https://github.com/madebybowtie/FlagKit">https://github.com/madebybowtie/FlagKit</a>""",

        """<b>Country database licensed under the CC-BY-SA-4.0 License.</b>
Copyright (c) 2001–2024 Hexasoft Development Sdn. Bhd.
This program includes IP2Location LITE data available from:
<a href="https://lite.ip2location.com">https://lite.ip2location.com</a>""",

        """<b>Country database reader licensed under the MIT License.</b>
Copyright (c) 2017 IP2Location.com
<a href="https://github.com/chrislim2888/IP2Location-Python">https://github.com/chrislim2888/IP2Location-Python</a>"""]

    def __init__(self, application):

        (
            self.application_version_label,
            self.authors_container,
            self.container,
            self.copyright_label,
            self.dependency_versions_label,
            self.license_container,
            self.main_icon,
            self.status_container,
            self.status_icon,
            self.status_label,
            self.status_spinner,
            self.translators_container,
            self.website_label
        ) = ui.load(scope=self, path="dialogs/about.ui")

        super().__init__(
            parent=application.window,
            content_box=self.container,
            show_callback=self.on_show,
            close_callback=self.on_close,
            title=_("About"),
            width=425,
            height=540,
            resizable=False,
            show_title=False
        )

        self.is_version_outdated = False

        icon_name = pynicotine.__application_id__
        icon_args = (Gtk.IconSize.BUTTON,) if GTK_API_VERSION == 3 else ()  # pylint: disable=no-member
        website_text = _('Website')
        gtk_version = f"{Gtk.get_major_version()}.{Gtk.get_minor_version()}.{Gtk.get_micro_version()}"

        self.main_icon.set_from_icon_name(icon_name, *icon_args)
        self.website_label.connect("activate-link", lambda x, url: open_uri(url))

        for label_widget, text in (
            (self.application_version_label, f"{pynicotine.__application_name__} {pynicotine.__version__}"),
            (self.dependency_versions_label, (f"GTK {gtk_version}   •   Python {sys.version.split()[0]}")),
            (self.website_label, (f"<a href='{pynicotine.__website_url__}' title='{pynicotine.__website_url__}'>"
                                  f"{website_text}</a>")),
            (self.copyright_label, f"<small>{pynicotine.__copyright__}</small>")
        ):
            label_widget.set_markup(text)

        for entries, container in (
            (self.AUTHORS, self.authors_container),
            (self.TRANSLATORS, self.translators_container),
            (self.LICENSE, self.license_container)
        ):
            for text in entries:
                label = Gtk.Label(label=text, use_markup=True, selectable=True, wrap=True, xalign=0, visible=True)

                if GTK_API_VERSION >= 4:
                    container.append(label)  # pylint: disable=no-member
                else:
                    container.add(label)     # pylint: disable=no-member

        events.connect("check-latest-version", self.on_check_latest_version)

    def on_check_latest_version(self, latest_version, is_outdated, error):

        if error:
            icon_name = "emblem-important-symbolic"
            css_class = "error"
            message = _("Error checking latest version: %s") % error

        elif is_outdated:
            icon_name = "dialog-warning-symbolic"
            css_class = "warning"
            message = _("New release available: %s") % latest_version

        else:
            icon_name = "object-select-symbolic"
            css_class = "success"
            message = _("Up to date")

        self.is_version_outdated = is_outdated
        icon_args = (Gtk.IconSize.BUTTON,) if GTK_API_VERSION == 3 else ()  # pylint: disable=no-member

        self.status_label.set_label(message)

        self.status_icon.set_from_icon_name(icon_name, *icon_args)
        self.status_spinner.set_visible(False)
        self.status_spinner.stop()

        add_css_class(self.status_container, css_class)

    def on_show(self, *_args):

        if core.update_checker is None:
            # Update checker is not loaded
            return

        if self.is_version_outdated:
            # No need to check latest version again
            return

        if not self.is_visible():
            return

        for css_class in ("error", "warning", "success"):
            remove_css_class(self.status_container, css_class)

        self.status_label.set_label(_("Checking latest version…"))
        self.status_spinner.set_visible(True)
        self.status_spinner.start()
        self.status_container.set_visible(True)

        core.update_checker.check()

    def on_close(self, *_args):

        self.main_icon.grab_focus()
        self.status_spinner.stop()
        self.container.get_vadjustment().set_value(0)
