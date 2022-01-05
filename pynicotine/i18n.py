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
import glob
import locale
import os
import sys

TRANSLATION_DOMAIN = "nicotine"


def apply_translations():
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

    # Local path where to find translation (mo) files
    local_mo_path = 'mo'

    if gettext.find(TRANSLATION_DOMAIN, localedir=local_mo_path):
        if libintl:
            # Tell GtkBuilder where to find our translations (ui files)
            libintl.bindtextdomain(TRANSLATION_DOMAIN, local_mo_path)

        # Locales are in the current dir, use them
        gettext.install(TRANSLATION_DOMAIN, local_mo_path)
        return

    # Locales are not in the current dir
    # We let gettext handle the situation: if found them in the system dir
    # the app will be translated, if not, it will be untranslated
    gettext.install(TRANSLATION_DOMAIN)


def generate_translations():

    current_folder = os.path.dirname(os.path.realpath(__file__))
    base_folder = os.path.normpath(os.path.join(current_folder, ".."))

    mo_entries = []
    languages = []

    for po_file in glob.glob(os.path.join(base_folder, "po", "*.po")):
        lang = os.path.basename(po_file[:-3])
        languages.append(lang)

        mo_dir = os.path.join("mo", lang, "LC_MESSAGES")
        mo_file = os.path.join(mo_dir, "nicotine.mo")

        if not os.path.exists(mo_dir):
            os.makedirs(mo_dir)

        exit_code = os.system("msgfmt --check " + po_file + " -o " + mo_file)

        if exit_code > 0:
            sys.exit(exit_code)

        targetpath = os.path.join("share", "locale", lang, "LC_MESSAGES")
        mo_entries.append((targetpath, [mo_file]))

    # Merge translations into .desktop and metainfo files
    for desktop_file in glob.glob(os.path.join(base_folder, "data", "*.desktop.in")):
        os.system("msgfmt --desktop --template=" + desktop_file + " -d po -o " + desktop_file[:-3])

    for metainfo_file in glob.glob(os.path.join(base_folder, "data", "*.metainfo.xml.in")):
        os.system("msgfmt --xml --template=" + metainfo_file + " -d po -o " + metainfo_file[:-3])

    return mo_entries, languages
