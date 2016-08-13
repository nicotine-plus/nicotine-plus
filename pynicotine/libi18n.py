# -*- coding: utf-8 -*-
#
# COPYRIGHT (c) 2016 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (c) 2008 eL_vErDe <gandalf@le-vert.net>
# COPYRIGHT (C) 2007-2008 Dieter Verfaillie <dieterv@optionexplicit.be>
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

"""
This module is used for fixing environnement variables for locale handling.
"""

import os
import platform
import locale
from logfacility import log

# Python 2.7.X is build via Visual Studio 2010 on Windows:
# https://stackoverflow.com/questions/32037573/load-gtk-glade-translations-in-windows-using-python-pygobject
# The locales table for VS200 can be found here:
# https://msdn.microsoft.com/en-us/goglobal/bb896001.aspx

# For the time being we put into it only the languages
# we have translation for in N+
UNIX_TO_WINDOWS_LOCALES = {
    'da': 'dnk',
    'de': 'deu',
    'en': 'usa',
    'es': 'esp',
    'eu': 'euq',
    'fi': 'fin',
    'fr': 'fra',
    'hu': 'hun',
    'it': 'ita',
    'lt': 'lth',
    'nl': 'nld',
    'pl': 'pol',
    'pt_BR': 'bra',
    'sk': 'svk',
    'sv': 'swe'
}


def _build_localename_win(localetuple):
    """ Builds a locale code from the given tuple (language code, encoding).
        No aliasing or normalizing takes place."""

    language, encoding = localetuple

    if language is None:
        language = 'C'
    if encoding is None:
        return language
    else:
        return language + '.' + encoding


def _putenv_win(name, value):
    """ From python 2.4 on, os.environ changes only work within python
    and no longer apply to low level C stuff on win32.
    Lets force LANG so it works with gtk+ etc"""

    from ctypes import windll, cdll

    kernel32 = windll.kernel32
    result = kernel32.SetEnvironmentVariableW(name, value)
    del kernel32
    if result == 0:
        raise

    msvcrt = cdll.msvcrt
    result = msvcrt._putenv('%s=%s' % (name, value))
    del msvcrt


def SetLocaleEnv(lang=None):
    """Function to set locale used by gettext and glade.

    We try to autodetect the locale if the user don't specify a language
    we can derived the locale from.

    In any case if something goes bad we fall back to english (C)."""

    # Detect if we're running on Windows
    win32 = platform.system().startswith("Win")

    if lang is None:

        # If no lang is provided we just fix LC_ALL to be sure
        if win32:

            # On windows python can get a normalize tuple
            # (language code, encoding)
            locale_win = locale.getdefaultlocale()

            # Build a locale name compatible with gettext
            locale_win_gettext = _build_localename_win(locale_win)

            # Fix environnement variables
            os.environ['LC_ALL'] = locale_win_gettext
            _putenv_win('LC_ALL', locale_win_gettext)

            # Fix the locale
            locale.setlocale(locale.LC_ALL, '')

        else:
            # On UNIX we simply set the current locale
            # or fallback to C.UTF-8
            try:
                locale.setlocale(locale.LC_ALL, '')
            except Exception as e:
                log.addwarning("Cannot set the locale: %s, "
                               "falling back to english" % str(e))

                # Falling back to english
                locale.setlocale(locale.LC_ALL, 'C.UTF-8')
                os.environ['LC_ALL'] = 'C'
    else:
        # If a lang is provided
        if win32:

            # On Windows we normalize the language in unix format
            # for env variables used by glade
            wanted_lang = locale.normalize(lang).split('.')[0]

            # Fix environnement variables
            os.environ['LC_ALL'] = wanted_lang
            _putenv_win('LC_ALL', wanted_lang)

            # We fix the locale using the locales conversion table
            # since VS2010 doesn't support unix format locales
            locale.setlocale(locale.LC_ALL, UNIX_TO_WINDOWS_LOCALES[lang])
        else:

            # On Unix we nomalize it and add UTF-8 encoding
            try:
                locale.setlocale(locale.LC_ALL,
                                 locale.normalize(lang).split('.')[0]+'.UTF-8')
            except Exception as e:
                log.addwarning("Cannot set the locale: %s, "
                               "falling back to english" % str(e))

                # Falling back to english
                locale.setlocale(locale.LC_ALL, 'C.UTF-8')
                os.environ['LC_ALL'] = 'C'
