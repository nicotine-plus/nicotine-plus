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

import gettext
import glob
import locale
import os
import sys

CURRENT_FOLDER = os.path.dirname(os.path.realpath(__file__))
BASE_FOLDER = os.path.normpath(os.path.join(CURRENT_FOLDER, ".."))
TRANSLATION_DOMAIN = "nicotine"


def _set_default_system_language():
    """ Extracts the default system language and applies it on systems that don't
    set the 'LANGUAGE' environment variable by default (Windows, macOS) """

    language = None

    if os.getenv("LANGUAGE") is None:
        if sys.platform == "win32":
            import ctypes
            windll = ctypes.windll.kernel32
            language = locale.windows_locale.get(windll.GetUserDefaultUILanguage())

        elif sys.platform == "darwin":
            try:
                import subprocess
                language_output = subprocess.check_output(("defaults", "read", "-g", "AppleLanguages"))
                languages = language_output.decode("utf-8").strip('()\n" ').split(",")

                if languages:
                    language = languages[0][:2]

            except Exception as error:
                print("Cannot load translations for default system language: %s", error)

    if language is not None:
        os.environ["LANGUAGE"] = language


def get_translation_mo_path():
    """ Retrieves the appropriate path for translation files, based on how Nicotine+ is installed """

    # Running from Git
    local_mo_path = os.path.join(BASE_FOLDER, "mo")

    if gettext.find(TRANSLATION_DOMAIN, localedir=local_mo_path):
        return local_mo_path

    # Windows/macOS builds
    if getattr(sys, 'frozen', False):
        executable_folder = os.path.dirname(sys.executable)

        if sys.platform == "darwin":
            prefix = os.path.abspath(os.path.join(executable_folder, "..", "Resources"))
        else:
            prefix = executable_folder

    # Flatpak
    elif os.path.exists("/.flatpak-info"):
        prefix = "/app"

    # Other Unix-like systems
    else:
        prefix = sys.prefix

    return os.path.join(prefix, "share", "locale")


def apply_translations():

    # Use the same language as the rest of the system
    _set_default_system_language()

    # Install translations for Python
    gettext.install(TRANSLATION_DOMAIN, get_translation_mo_path())


def build_translations():
    """ Builds .mo translation files in the 'mo' folder of the project repository """

    import subprocess
    languages = []

    for po_file in glob.glob(os.path.join(BASE_FOLDER, "po", "*.po")):
        lang = os.path.basename(po_file[:-3])
        languages.append(lang)

        mo_dir = os.path.join("mo", lang, "LC_MESSAGES")
        mo_file = os.path.join(mo_dir, "nicotine.mo")

        if not os.path.exists(mo_dir):
            os.makedirs(mo_dir)

        subprocess.check_call(["msgfmt", "--check", po_file, "-o", mo_file])

    # Merge translations into .desktop and appdata files
    for desktop_file in glob.glob(os.path.join(BASE_FOLDER, "data", "*.desktop.in")):
        subprocess.check_call(["msgfmt", "--desktop", "--template=" + desktop_file, "-d", "po",
                               "-o", desktop_file[:-3]])

    for appdata_file in glob.glob(os.path.join(BASE_FOLDER, "data", "*.appdata.xml.in")):
        subprocess.check_call(["msgfmt", "--xml", "--template=" + appdata_file, "-d", "po", "-o", appdata_file[:-3]])

    return languages


def get_translation_paths():
    """ Returns the target path and current path of built .mo translation files """

    mo_entries = []

    for po_file in glob.glob(os.path.join(BASE_FOLDER, "po", "*.po")):
        lang = os.path.basename(po_file[:-3])

        mo_dir = os.path.join("mo", lang, "LC_MESSAGES")
        mo_file = os.path.join(mo_dir, "nicotine.mo")

        targetpath = os.path.join("share", "locale", lang, "LC_MESSAGES")
        mo_entries.append((targetpath, [mo_file]))

    return mo_entries
