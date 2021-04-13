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

import gettext
import locale
import sys


def apply_translation():
    """Function dealing with translations and locales.

    We try to autodetect the language and fix the locale.

    If something goes wrong we fall back to no translation.

    This function also try to find translation files in the project path first:
    $(PROJECT_PATH)/mo/$(LANG)/LC_MESSAGES/nicotine.mo

    If no translations are found we fall back to the system path for locates:
    /usr/share/locale/$(LANG)/LC_MESSAGES

    Note: To the best of my knowledge when we are in a python venv
    falling back to the system path does not work."""

    # Load library for translating non-Python content, e.g. GTK ui files
    if hasattr(locale, 'bindtextdomain') and hasattr(locale, 'textdomain'):
        libintl = locale

    elif sys.platform == "win32":
        import ctypes
        libintl = ctypes.cdll.LoadLibrary('libintl-8.dll')

    else:
        libintl = None

    # Package name for gettext
    package = 'nicotine'

    # Local path where to find translation (mo) files
    local_mo_path = 'mo'

    if libintl:
        # Enable translation support in GtkBuilder (ui files)
        libintl.textdomain(package)

    if gettext.find(package, localedir=local_mo_path):
        if libintl:
            # Tell GtkBuilder where to find our translations (ui files)
            libintl.bindtextdomain(package, local_mo_path)

        # Locales are in the current dir, use them
        gettext.install(package, local_mo_path)
        return

    # Locales are not in the current dir
    # We let gettext handle the situation: if found them in the system dir
    # the app will be translated, if not, it will be untranslated
    gettext.install(package)
