# COPYRIGHT (C) 2020-2023 Nicotine+ Contributors
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
import os
import sys

CURRENT_PATH = os.path.dirname(os.path.realpath(__file__))
BASE_PATH = os.path.normpath(os.path.join(CURRENT_PATH, ".."))
LOCALE_PATH = os.path.join(CURRENT_PATH, "locale")
TRANSLATION_DOMAIN = "nicotine"
LANGUAGES = (
    ("ca", "Català"),
    ("de", "Deutsch"),
    ("en", "English"),
    ("es_CL", "Español (Chile)"),
    ("es_ES", "Español (España)"),
    ("fr", "Français"),
    ("hu", "Magyar"),
    ("it", "Italiano"),
    ("lv", "Latviešu"),
    ("nl", "Nederlands"),
    ("pl", "Polski"),
    ("pt_BR", "Português (Brasil)"),
    ("ru", "Русский"),
    ("tr", "Türkçe"),
    ("uk", "Українська"),
    ("zh_CN", "汉语")
)


def _set_system_language(language=None):
    """Extracts the default system language and applies it on systems that
    don't set the 'LANGUAGE' environment variable by default (Windows,
    macOS)"""

    if not language and "LANGUAGE" not in os.environ:
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
    """Builds .mo translation files in the 'mo' folder of the project
    repository."""

    import glob
    import subprocess

    for language_code, _language_name in LANGUAGES:
        if language_code == "en":
            continue

        lc_messages_folder_path = os.path.join(LOCALE_PATH, language_code, "LC_MESSAGES")
        po_file_path = os.path.join(BASE_PATH, "po", f"{language_code}.po")
        mo_file_path = os.path.join(lc_messages_folder_path, "nicotine.mo")

        if not os.path.exists(lc_messages_folder_path):
            os.makedirs(lc_messages_folder_path)

        subprocess.check_call(["msgfmt", "--check", po_file_path, "-o", mo_file_path])

    # Merge translations into .desktop and appdata files
    for desktop_file_path in glob.glob(os.path.join(BASE_PATH, "data", "*.desktop.in")):
        subprocess.check_call(["msgfmt", "--desktop", f"--template={desktop_file_path}", "-d", "po",
                               "-o", desktop_file_path[:-3]])

    for appdata_file_path in glob.glob(os.path.join(BASE_PATH, "data", "*.appdata.xml.in")):
        subprocess.check_call(["msgfmt", "--xml", f"--template={appdata_file_path}", "-d", "po",
                               "-o", appdata_file_path[:-3]])
