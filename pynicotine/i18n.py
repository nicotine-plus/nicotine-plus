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
    ("cs", "Čeština"),
    ("de", "Deutsch"),
    ("en", "English"),
    ("es_CL", "Español (Chile)"),
    ("es_ES", "Español (España)"),
    ("et", "Eesti"),
    ("fr", "Français"),
    ("hu", "Magyar"),
    ("it", "Italiano"),
    ("lv", "Latviešu"),
    ("nl", "Nederlands"),
    ("pl", "Polski"),
    ("pt_BR", "Português (Brasil)"),
    ("pt_PT", "Português (Portugal)"),
    ("ru", "Русский"),
    ("ta", "தமிழ்"),
    ("tr", "Türkçe"),
    ("uk", "Українська"),
    ("zh_CN", "汉语")
)


def _set_system_language(language=None):
    """Extracts the default system locale/language and applies it on systems that
    don't set the 'LC_ALL/LANGUAGE' environment variables by default (Windows,
    macOS)"""

    default_locale = None

    if sys.platform == "win32":
        import ctypes
        windll = ctypes.windll.kernel32

        if not default_locale:
            default_locale = locale.windows_locale.get(windll.GetUserDefaultLCID())

        if not language and "LANGUAGE" not in os.environ:
            language = locale.windows_locale.get(windll.GetUserDefaultUILanguage())

    elif sys.platform == "darwin":
        import plistlib
        os_preferences_path = os.path.join(
            os.path.expanduser("~"), "Library", "Preferences", ".GlobalPreferences.plist")

        try:
            with open(os_preferences_path, "rb") as file_handle:
                os_preferences = plistlib.load(file_handle)

        except Exception as error:
            os_preferences = {}
            print(f"Cannot load global preferences: {error}")

        # macOS provides locales with additional @ specifiers, e.g. en_GB@rg=US (region).
        # Remove them, since they are not supported.
        default_locale = next(iter(os_preferences.get("AppleLocale", "").split("@", maxsplit=1)))

        if default_locale.endswith("_ES"):
            # *_ES locale is currently broken on macOS (crashes when sorting strings).
            # Disable it for now.
            default_locale = "pt_PT"

        if not language and "LANGUAGE" not in os.environ:
            languages = os_preferences.get("AppleLanguages", [""])
            language = next(iter(languages)).replace("-", "_")

    if default_locale:
        os.environ["LC_ALL"] = default_locale

    if language:
        os.environ["LANGUAGE"] = language


def apply_translations(language=None):

    # Use the same language as the rest of the system
    _set_system_language(language)

    # Install translations for Python
    gettext.install(TRANSLATION_DOMAIN, LOCALE_PATH)
