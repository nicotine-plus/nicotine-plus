# SPDX-FileCopyrightText: 2020-2026 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

import gettext
import locale
import os
import sys

CURRENT_PATH = os.path.dirname(os.path.realpath(__file__))
BASE_PATH = os.path.normpath(os.path.join(CURRENT_PATH, ".."))
LOCALE_PATH = os.path.join(CURRENT_PATH, "locale")
TRANSLATION_DOMAIN = "nicotine"
LANGUAGES: tuple[tuple[str, str], ...] = (
    ("ca", "Català"),
    ("cs", "Čeština"),
    ("da", "Dansk"),
    ("de", "Deutsch"),
    ("en", "English"),
    ("es_CL", "Español (Chile)"),
    ("es_ES", "Español (España)"),
    ("et", "Eesti"),
    ("fr", "Français"),
    ("hr", "Hrvatski"),
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
        os.environ["LC_ALL"] = default_locale + ".UTF-8"

    if language:
        os.environ["LANGUAGE"] = language


def bindtextdomain_c(domain, locale_path, set_current=False):

    libintl_path = None
    codeset = "UTF-8"

    if sys.platform == "win32":
        libintl_path = "libintl-8.dll"

    elif sys.platform == "darwin":
        libintl_path = "libintl.8.dylib"

    if libintl_path is not None:
        import ctypes

        if getattr(sys, 'frozen', False):
            # Use absolute path in frozen binaries (cx_Freeze)
            libintl_path = os.path.join(os.path.dirname(sys.executable), "lib", libintl_path)

        try:
            libintl = ctypes.cdll.LoadLibrary(libintl_path)

        except OSError as error:
            print(error)
            return

        libintl.bindtextdomain(domain.encode(), locale_path.encode())
        libintl.bind_textdomain_codeset(domain.encode(), codeset.encode())

        if set_current:
            libintl.textdomain(domain.encode())
        return

    try:
        locale.bindtextdomain(domain, locale_path)
        locale.bind_textdomain_codeset(domain, codeset)

        if set_current:
            locale.textdomain(domain)

    except AttributeError as error:
        print(error)


def apply_translations(language=None):

    # Use the same language as the rest of the system
    _set_system_language(language)

    # Install translations for Python
    gettext.install(TRANSLATION_DOMAIN, LOCALE_PATH, names=["ngettext"])

    # Install translations for C libraries (e.g. GTK)
    bindtextdomain_c(TRANSLATION_DOMAIN, LOCALE_PATH, set_current=True)
