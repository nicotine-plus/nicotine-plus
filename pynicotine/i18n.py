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
LOCALE_PATH = os.path.join(CURRENT_FOLDER, "locale")
TRANSLATION_DOMAIN = "nicotine"
LANGUAGES = (
    ("ca", "Català"),
    ("da", "Dansk"),
    ("de", "Deutsch"),
    ("en", "English"),
    ("es_CL", "Español (Chile)"),
    ("es_ES", "Español (España)"),
    ("eu", "Euskara"),
    ("fi", "Suomi"),
    ("fr", "Français"),
    ("hu", "Magyar"),
    ("it", "Italiano"),
    ("lt", "Lietuvių"),
    ("lv", "Latviešu"),
    ("nb_NO", "Norsk bokmål"),
    ("nl", "Nederlands"),
    ("pl", "Polski"),
    ("pt_BR", "Português (Brasil)"),
    ("ru", "Русский"),
    ("sk", "Slovenčina"),
    ("sv", "Svenska"),
    ("tr", "Türkçe"),
    ("uk", "Українська"),
    ("zh_CN", "汉语")
)


def _set_system_language(language=None):
    """ Extracts the default system language and applies it on systems that don't
    set the 'LANGUAGE' environment variable by default (Windows, macOS) """

    if not language and os.getenv("LANGUAGE") is None:
        if sys.platform == "win32":
            import ctypes
            windll = ctypes.windll.kernel32
            language = locale.windows_locale.get(windll.GetUserDefaultUILanguage())

        elif sys.platform == "darwin":
            try:
                import subprocess
                language_output = subprocess.check_output(("defaults", "read", "-g", "AppleLanguages"))
                languages = language_output.decode("utf-8").strip('()\n" ').split(",")
                language = next(iter(languages), None)

            except Exception as error:
                print("Cannot load translations for default system language: %s", error)

    if language:
        os.environ["LANGUAGE"] = language


def apply_translations(language=None):

    # Use the same language as the rest of the system
    _set_system_language(language)

    # Install translations for Python
    gettext.install(TRANSLATION_DOMAIN, LOCALE_PATH)


def build_translations():
    """ Builds .mo translation files in the 'mo' folder of the project repository """

    import subprocess

    for language_code, _language_name in LANGUAGES:
        if language_code == "en":
            continue

        lc_messages_dir = os.path.join(LOCALE_PATH, language_code, "LC_MESSAGES")
        po_file = os.path.join(BASE_FOLDER, "po", f"{language_code}.po")
        mo_file = os.path.join(lc_messages_dir, "nicotine.mo")

        if not os.path.exists(lc_messages_dir):
            os.makedirs(lc_messages_dir)

        subprocess.check_call(["msgfmt", "--check", po_file, "-o", mo_file])

    # Merge translations into .desktop and appdata files
    for desktop_file in glob.glob(os.path.join(BASE_FOLDER, "data", "*.desktop.in")):
        subprocess.check_call(["msgfmt", "--desktop", f"--template={desktop_file}", "-d", "po",
                               "-o", desktop_file[:-3]])

    for appdata_file in glob.glob(os.path.join(BASE_FOLDER, "data", "*.appdata.xml.in")):
        subprocess.check_call(["msgfmt", "--xml", f"--template={appdata_file}", "-d", "po", "-o", appdata_file[:-3]])
