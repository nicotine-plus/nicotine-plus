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

    libintl_path = None
    executable_folder = os.path.dirname(sys.executable)
    resources_folder = executable_folder
    _set_default_system_language()

    # Load library for translating non-Python content, e.g. GTK ui files
    if sys.platform == "win32":
        libintl_path = "libintl-8.dll"

        if getattr(sys, 'frozen', False):
            libintl_path = os.path.join(executable_folder, "lib", libintl_path)

    elif sys.platform == "darwin":
        libintl_path = "libintl.8.dylib"

        if getattr(sys, 'frozen', False):
            libintl_path = os.path.join(executable_folder, libintl_path)
            resources_folder = os.path.abspath(os.path.join(executable_folder, "..", "Resources"))

    # Local path where to find translation (mo) files
    local_mo_path = os.path.join(BASE_FOLDER, "mo")
    use_local_path = gettext.find(TRANSLATION_DOMAIN, localedir=local_mo_path)

    if not use_local_path:
        if getattr(sys, 'frozen', False):
            prefix = resources_folder

        elif os.path.exists("/.flatpak-info"):
            prefix = "/app"

        else:
            prefix = sys.prefix

        mo_path = os.path.join(prefix, "share", "locale")

    else:
        mo_path = local_mo_path

    if libintl_path is not None:
        import ctypes
        libintl = ctypes.cdll.LoadLibrary(libintl_path)

        # Arguments need to be encoded, otherwise translations fail
        libintl.bindtextdomain(TRANSLATION_DOMAIN.encode(), mo_path.encode(sys.getfilesystemencoding()))
        libintl.bind_textdomain_codeset(TRANSLATION_DOMAIN.encode(), b"UTF-8")

    elif hasattr(locale, "bindtextdomain") and hasattr(locale, "textdomain"):
        locale.bindtextdomain(TRANSLATION_DOMAIN, mo_path)

    # Install translations for Python
    gettext.install(TRANSLATION_DOMAIN, mo_path)


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
