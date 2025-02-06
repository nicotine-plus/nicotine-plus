# COPYRIGHT (C) 2020-2025 Nicotine+ Contributors
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

        ("<b>Mat (mathiascode)</b>"
         "\n •  Maintainer (2020–present)"
         "\n •  Developer"),

        ("<b>Adam Cécile (eLvErDe)</b>"
         "\n •  Maintainer (2013–2016)"
         "\n •  Domain name administrator"
         "\n •  Source code migration from SVN to GitHub"
         "\n •  Developer"),

        ("<b>Han Boetes</b>"
         "\n •  Tester"
         "\n •  Documentation"
         "\n •  Bug hunting"
         "\n •  Translation management"),

        ("<b>alekksander</b>"
         "\n •  Tester"
         "\n •  Redesign of some graphics"),

        ("<b>slook</b>"
         "\n •  Tester"
         "\n •  Accessibility improvements"),

        ("<b>ketacat</b>"
         "\n •  Tester"),


        "\n<b>Nicotine+ Team (Emeritus)</b>",

        ("<b>daelstorm</b>"
         "\n •  Maintainer (2004–2009)"
         "\n •  Developer"),

        ("<b>quinox</b>"
         "\n •  Maintainer (2009–2012)"
         "\n •  Developer"),

        ("<b>Michael Labouebe (gfarmerfr)</b>"
         "\n •  Maintainer (2016–2017)"
         "\n •  Developer"),

        ("<b>Kip Warner</b>"
         "\n •  Maintainer (2018–2020)"
         "\n •  Developer"
         "\n •  Debianization"),

        ("<b>gallows (aka 'burp O')</b>"
         "\n •  Developer"
         "\n •  Packager"
         "\n •  Submitted Slack.Build file"),

        ("<b>hedonist (formerly known as alexbk)</b>"
         "\n •  OS X Nicotine.app maintainer / developer"
         "\n •  Author of PySoulSeek, used for Nicotine core"),

        ("<b>lee8oi</b>"
         "\n •  Bash commander"
         "\n •  New and updated /alias"),

        ("<b>INMCM</b>"
         "\n •  Nicotine+ topic maintainer on ubuntuforums.org"),

        ("<b>suser-guru</b>"
         "\n •  Suse Linux packager"
         "\n •  Nicotine+ RPM's for Suse 9.1, 9.2, 9.3, 10.0, 10.1"),

        ("<b>osiris</b>"
         "\n •  Handy-man"
         "\n •  Documentation"
         "\n •  Some GNU/Linux packaging"
         "\n •  Nicotine+ on Win32"
         "\n •  Author of Nicotine+ guide"),

        ("<b>Mutnick</b>"
         "\n •  Created Nicotine+ GitHub organization"
         "\n •  Developer"),

        ("<b>Lene Preuss</b>"
         "\n •  Python 3 migration"
         "\n •  Unit and DEP-8 continuous integration testing"),


        "\n<b>Nicotine Team (Emeritus)</b>",

        ("<b>Ingmar K. Steen (Hyriand)</b>"
         "\n •  Maintainer (2003–2004)"),

        ("<b>daelstorm</b>"
         "\n •  Beta tester"
         "\n •  Designer of most of the settings"
         "\n •  Made the Nicotine icons"),

        ("<b>SmackleFunky</b>"
         "\n •  Beta tester"),

        ("<b>Wretched</b>"
         "\n •  Beta tester"
         "\n •  Bringer of great ideas"),

        ("<b>(va)\\*10^3</b>"
         "\n •  Beta tester"
         "\n •  Designer of Nicotine homepage and artwork (logos)"),

        ("<b>sierracat</b>"
         "\n •  MacOSX tester"
         "\n •  soulseeX developer"),

        ("<b>Gustavo J. A. M. Carneiro</b>"
         "\n •  Created the exception dialog"),

        ("<b>SeeSchloss</b>"
         "\n •  Developer"
         "\n •  Created 1.0.8 Win32 installer"
         "\n •  Created Soulfind, open source Soulseek server written in D"),

        ("<b>vasi</b>"
         "\n •  Mac developer"
         "\n •  Packaged Nicotine on OSX PowerPC"),


        "\n<b>PySoulSeek Team (Emeritus)</b>",

        ("<b>Alexander Kanavin</b>"
         "\n •  Maintainer (2001–2003)"),

        ("<b>Nir Arbel</b>"
         "\n •  Helped with many protocol questions, and of course he designed and implemented the whole system"),

        ("<b>Brett W. Thompson (Zip)</b>"
         "\n •  His client code was used to get an initial impression of how the system works"
         "\n •  Supplied the patch for logging chat conversations"),

        ("<b>Josselin Mouette</b>"
         "\n •  Official Debian package maintainer"),

        ("<b>blueboy</b>"
         "\n •  Former unofficial Debian package maintainer"),

        ("<b>Christian Swinehart</b>"
         "\n •  Fink package maintainer"),

        ("<b>Ingmar K. Steen (Hyriand)</b>"
         "\n •  Patches for upload bandwidth management, banning, various UI improvements and more"),

        ("<b>Geert Kloosterman</b>"
         "\n •  A script for importing Windows Soulseek configuration"),

        ("<b>Joe Halliwell</b>"
         "\n •  Submitted a patch for optionally discarding search results after closing a search tab"),

        ("<b>Alexey Vyskubov</b>"
         "\n •  Code cleanups"),

        ("<b>Jason Green (SmackleFunky)</b>"
         "\n •  Ignore list and auto-join checkbox, wishlists")]

    TRANSLATORS = [
        ("<b>Albanian</b>"
         "\n •  W L (2023–2024)"),

        ("<b>Arabic</b>"
         "\n •  ButterflyOfFire (2024)"),

        ("<b>Catalan</b>"
         "\n •  Aniol (2024–2025)"
         "\n •  Maite Guix (2022)"),

        ("<b>Chinese (Simplified)</b>"
         "\n •  Ys413 (2024)"
         "\n •  Bonislaw (2023)"
         "\n •  hylau (2023)"
         "\n •  hadwin (2022)"),

        ("<b>Czech</b>"
         "\n •  slrslr (2024–2025)"
         "\n •  burnmail123 (2021–2023)"),

        ("<b>Danish</b>"
         "\n •  mathsped (2003–2004)"),

        ("<b>Dutch</b>"
         "\n •  Toine Rademacher (toineenzo) (2023–2024)"
         "\n •  Han Boetes (hboetes) (2021–2024)"
         "\n •  Kenny Verstraete (2009)"
         "\n •  nince78 (2007)"
         "\n •  Ingmar K. Steen (Hyriand) (2003–2004)"),

        ("<b>English</b>"
         "\n •  slook (2021–2024)"
         "\n •  Han Boetes (hboetes) (2021–2024)"
         "\n •  Mat (mathiascode) (2020–2024)"
         "\n •  Michael Labouebe (gfarmerfr) (2016)"
         "\n •  daelstorm (2004–2009)"
         "\n •  Ingmar K. Steen (Hyriand) (2003–2004)"),

        ("<b>Esperanto</b>"
         "\n •  phlostically (2021)"),

        ("<b>Estonian</b>"
         "\n •  rimasx (2024)"
         "\n •  PriitUring (2023)"),

        ("<b>Euskara</b>"
         "\n •  Julen (2006–2007)"),

        ("<b>Finnish</b>"
         "\n •  Kari Viittanen (Kalevi) (2006–2007)"),

        ("<b>French</b>"
         "\n •  Saumon (2023)"
         "\n •  subu_versus (2023)"
         "\n •  zniavre (2007–2023)"
         "\n •  Maxime Leroy (Lisapple) (2021–2022)"
         "\n •  Mohamed El Morabity (melmorabity) (2021–2024)"
         "\n •  m-balthazar (2020)"
         "\n •  Michael Labouebe (gfarmerfr) (2016–2017)"
         "\n •  Monsieur Poisson (2009–2010)"
         "\n •  ManWell (2007)"
         "\n •  systr (2006)"
         "\n •  Julien Wajsberg (flashfr) (2003–2004)"),

        ("<b>German</b>"
         "\n •  Han Boetes (hboetes) (2021–2024)"
         "\n •  phelissimo_ (2023)"
         "\n •  Meokater (2007)"
         "\n •  (._.) (2007)"
         "\n •  lippel (2004)"
         "\n •  Ingmar K. Steen (Hyriand) (2003–2004)"),

        ("<b>Hungarian</b>"
         "\n •  Szia Tomi (2022–2024)"
         "\n •  Nils (2009)"
         "\n •  David Balazs (djbaloo) (2006–2020)"),

        ("<b>Italian</b>"
         "\n •  Gabriele (Gabboxl) (2022–2023)"
         "\n •  ms-afk (2023)"
         "\n •  Gianluca Boiano (2020–2023)"
         "\n •  nicola (2007)"
         "\n •  dbazza (2003–2004)"),

        ("<b>Latvian</b>"
         "\n •  Pagal3 (2022–2025)"),

        ("<b>Lithuanian</b>"
         "\n •  mantas (2020)"
         "\n •  Žygimantas Beručka (2006–2009)"),

        ("<b>Norwegian Bokmål</b>"
         "\n •  Allan Nordhøy (comradekingu) (2021)"),

        ("<b>Polish</b>"
         "\n •  Mariusz (mariachini) (2017–2024)"
         "\n •  Amun-Ra (2007)"
         "\n •  thine (2007)"
         "\n •  Wojciech Owczarek (owczi) (2003–2004)"),

        ("<b>Portuguese (Brazil)</b>"
         "\n •  Havokdan (2022–2023)"
         "\n •  Guilherme Santos (2022)"
         "\n •  b1llso (2022)"
         "\n •  Nicolas Abril (2021)"
         "\n •  yyyyyyyan (2020)"
         "\n •  Felipe Nogaroto Gonzalez (Suicide|Solution) (2006)"),

        ("<b>Portuguese (Portugal)</b>"
         "\n •  ssantos (2023)"
         "\n •  Vinícius Soares (2023)"),

        ("<b>Romanian</b>"
         "\n •  Slendi (xslendix) (2023)"),

        ("<b>Russian</b>"
         "\n •  Kirill Feoktistov (SnIPeRSnIPeR) (2022–2024)"
         "\n •  Mehavoid (2021–2023)"
         "\n •  AHOHNMYC (2022)"),

        ("<b>Slovak</b>"
         "\n •  Jozef Říha (2006–2008)"),

        ("<b>Spanish (Chile)</b>"
         "\n •  MELERIX (2021–2023)"
         "\n •  tagomago (2021–2022)"
         "\n •  Strange (2021)"
         "\n •  Silvio Orta (2007)"
         "\n •  Dreslo (2003–2004)"),

        ("<b>Spanish (Spain)</b>"
         "\n •  gallegonovato (2023–2024)"
         "\n •  MELERIX (2021–2023)"
         "\n •  tagomago (2021–2022)"
         "\n •  Strange (2021)"
         "\n •  Silvio Orta (2007)"
         "\n •  Dreslo (2003–2004)"),

        ("<b>Swedish</b>"
         "\n •  mitramai (2021)"
         "\n •  Markus Magnuson (alimony) (2003–2004)"),

        ("<b>Tamil</b>"
         "\n •  தமிழ்நேரம் (2025)"),

        ("<b>Turkish</b>"
         "\n •  Oğuz Ersen (2021–2024)"),

        ("<b>Ukrainian</b>"
         "\n •  Oleg Gritsun (2024–2025)"
         "\n •  uniss2209 (2022)")]

    LICENSE = [
        ("Nicotine+ is licensed under the <a href='https://www.gnu.org/licenses/gpl-3.0.html'>"
         "GNU General Public License v3.0 or later</a>, with the following exceptions:"),

        ("<b><a href='https://github.com/tinytag/tinytag'>tinytag</a> licensed under the MIT License.</b>"
         "\nCopyright (c) 2014-2023 Tom Wallroth, Mat (mathiascode)"
         "\n\nPermission is hereby granted, free of charge, to any person obtaining a copy "
         'of this software and associated documentation files (the "Software"), to deal '
         "in the Software without restriction, including without limitation the rights "
         "to use, copy, modify, merge, publish, distribute, sublicense, and/or sell "
         "copies of the Software, and to permit persons to whom the Software is "
         "furnished to do so, subject to the following conditions: "
         "\n\nThe above copyright notice and this permission notice shall be included in all "
         "copies or substantial portions of the Software."),

        ("<b><a href='https://github.com/madebybowtie/FlagKit'>FlagKit</a> icons licensed "
         "under the MIT License.</b>"
         "\nCopyright (c) 2016 Bowtie AB"
         "\n\nPermission is hereby granted, free of charge, to any person obtaining a copy "
         'of this software and associated documentation files (the "Software"), to deal '
         "in the Software without restriction, including without limitation the rights "
         "to use, copy, modify, merge, publish, distribute, sublicense, and/or sell "
         "copies of the Software, and to permit persons to whom the Software is "
         "furnished to do so, subject to the following conditions: "
         "\n\nThe above copyright notice and this permission notice shall be included in all "
         "copies or substantial portions of the Software."),

        ("<b>IP2Location country data licensed under the "
         "<a href='https://creativecommons.org/licenses/by-sa/4.0/'>CC-BY-SA-4.0 License</a>.</b>"
         "\nCopyright (c) 2001–2024 Hexasoft Development Sdn. Bhd."
         "\nNicotine+ uses the IP2Location LITE database for "
         "<a href='https://lite.ip2location.com'>IP geolocation</a>.")]

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
            show_title=False
        )

        self.is_version_outdated = False

        icon_name = pynicotine.__application_id__
        icon_args = (Gtk.IconSize.BUTTON,) if GTK_API_VERSION == 3 else ()  # pylint: disable=no-member
        website_text = _('Website')
        gtk_version = f"{Gtk.get_major_version()}.{Gtk.get_minor_version()}.{Gtk.get_micro_version()}"

        self.main_icon.set_from_icon_name(icon_name, *icon_args)
        self.website_label.connect("activate-link", self.on_activate_link)

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

                if entries is self.LICENSE:
                    label.connect("activate-link", self.on_activate_link)

                if GTK_API_VERSION >= 4:
                    container.append(label)  # pylint: disable=no-member
                else:
                    container.add(label)     # pylint: disable=no-member

        events.connect("check-latest-version", self.on_check_latest_version)

    def on_activate_link(self, _label, url):
        open_uri(url)
        return True

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
