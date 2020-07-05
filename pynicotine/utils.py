# -*- coding: utf-8 -*-
#
# COPYRIGHT (C) 2020 Lene Preuss <lene.preuss@gmail.com>
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2007 Daelstorm <daelstorm@gmail.com>
# COPYRIGHT (C) 2003-2004 Hyriand <hyriand@thegraveyard.org>
# COPYRIGHT (C) 2001-2003 Alexander Kanavin
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
This module contains utility functions.
"""

import gettext
import locale
import os
import sys
from codecs import encode, decode
from subprocess import PIPE
from subprocess import Popen

version = "1.4.3"

log = 0
win32 = sys.platform.startswith("win")

illegalpathchars = []
if win32:
    illegalpathchars += ["?", ":", ">", "<", "|", "*", '"']

illegalfilechars = illegalpathchars + ["\\", "/"]
replacementchar = '_'


def CleanFile(filename):

    for char in illegalfilechars:
        filename = filename.replace(char, replacementchar)

    return filename


def CleanPath(path, absolute=False):

    if win32:

        # Without hacks it is (up to Vista) not possible to have more
        # than 26 drives mounted, so we can assume a '[a-zA-Z]:\' prefix
        # for drives - we shouldn't escape that
        drive = ''
        if absolute and path[1:3] == ':\\' and path[0:1] and path[0].isalpha():
            drive = path[:3]
            path = path[3:]

        for char in illegalpathchars:
            path = path.replace(char, replacementchar)

        path = ''.join([drive, path])

        # Path can never end with a period on Windows machines
        path = path.rstrip('.')

    return path


def GetUserDirectories():
    """Returns a tuple:
    - the config directory
    - the data directory"""
    home = os.path.expanduser("~")

    legacy_dir = os.path.join(home, '.nicotine')

    if os.path.isdir(legacy_dir):
        return legacy_dir, legacy_dir

    def xdgPath(xdg, default):
        path = os.environ.get(xdg)

        path = path.split(':')[0] if path else default

        return os.path.join(path, 'nicotine')

    config_dir = xdgPath('XDG_CONFIG_HOME', os.path.join(home, '.config'))
    data_dir = xdgPath('XDG_DATA_HOME', os.path.join(home, '.local', 'share'))

    return config_dir, data_dir


def GetResultBitrateLength(filesize, attributes):
    """ Used to get the audio bitrate and length of search results and
    user browse files """

    h_bitrate = ""
    h_length = ""

    bitrate = 0

    # If there are 3 entries in the attribute list
    if len(attributes) == 3:

        a = attributes

        # Sometimes the vbr indicator is in third position
        if a[2] == 0 or a[2] == 1:

            if a[2] == 1:
                h_bitrate = " (vbr)"

            bitrate = a[0]
            h_bitrate = str(bitrate) + h_bitrate

            h_length = '%i:%02i' % (a[1] / 60, a[1] % 60)

        # Sometimes the vbr indicator is in second position
        elif a[1] == 0 or a[1] == 1:

            if a[1] == 1:
                h_bitrate = " (vbr)"

            bitrate = a[0]
            h_bitrate = str(bitrate) + h_bitrate

            h_length = '%i:%02i' % (a[2] / 60, a[2] % 60)

        # Lossless audio, length is in first position
        elif a[2] > 1:

            # Bitrate = sample rate (Hz) * word length (bits) * channel count
            # Bitrate = 44100 * 16 * 2
            bitrate = (a[1] * a[2] * 2) / 1000
            h_bitrate = str(bitrate)

            h_length = '%i:%02i' % (a[0] / 60, a[0] % 60)

        else:

            bitrate = a[0]
            h_bitrate = str(bitrate) + h_bitrate

    # If there are 2 entries in the attribute list
    elif len(attributes) == 2:

        a = attributes

        # Sometimes the vbr indicator is in second position
        if a[1] == 0 or a[1] == 1:

            # If it's a vbr file we can't deduce the length
            if a[1] == 1:

                h_bitrate = " (vbr)"

                bitrate = a[0]
                h_bitrate = str(bitrate) + h_bitrate

            # If it's a constant bitrate we can deduce the length
            else:

                bitrate = a[0]
                h_bitrate = str(bitrate) + h_bitrate

                # Dividing the file size by the bitrate in Bytes should give us a good enough approximation
                length = filesize / (bitrate / 8 * 1000)

                h_length = '%i:%02i' % (length / 60, length % 60)

        # Sometimes the bitrate is in first position and the length in second position
        else:

            bitrate = a[0]
            h_bitrate = str(bitrate) + h_bitrate

            h_length = '%i:%02i' % (a[1] / 60, a[1] % 60)

    return h_bitrate, bitrate, h_length


def ApplyTranslation():
    """Function dealing with translations and locales.

    We try to autodetect the language and fix the locale.

    If something goes wrong we fall back to no translation.

    This function also try to find translation files in the project path first:
    $(PROJECT_PATH)/languages/$(LANG)/LC_MESSAGES/nicotine.mo

    If no translations are found we fall back to the system path for locates:
    GNU/Linux: /usr/share/locale/$(LANG)/LC_MESSAGES
    Windows: %PYTHONHOME%\\share\\locale\\$(LANG)\\LC_MESSAGES

    Note: To the best of my knowledge when we are in a python venv
    falling back to the system path does not work."""

    # Package name for gettext
    PACKAGE = 'nicotine'

    # Local path where to find translation (mo) files
    LOCAL_MO_PATH = 'languages'

    # Python 2.7.X is build via Visual Studio 2008 on Windows:
    # https://stackoverflow.com/questions/32037573/load-gtk-glade-translations-in-windows-using-python-pygobject
    # https://docs.python.org/devguide/setup.html#windows
    # The locales table for VS2008 can be found here:
    # https://msdn.microsoft.com/en-us/library/cdax410z(v=vs.90).aspx
    # https://msdn.microsoft.com/en-us/library/39cwe7zf(v=vs.90).aspx
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

    # Locales handling
    if win32:

        # On windows python can get a normalize tuple (language code, encoding)
        locale_win = locale.getdefaultlocale()

        # Build a locale name compatible with gettext
        locale_win_gettext = _build_localename_win(locale_win)

        # Fix environnement variables
        os.environ['LC_ALL'] = locale_win_gettext

    else:
        # Unix locales handling: We let the system handle the locales
        locale.setlocale(locale.LC_ALL, '')

    # Gettext handling
    if gettext.find(PACKAGE, localedir=LOCAL_MO_PATH) is None:

        # Locales are not in the current dir
        # We let gettext handle the situation: if if found them in the system dir
        # the app will be trnaslated, if not it will be untranslated.
        gettext.install(PACKAGE)

    else:

        # Locales are in the current dir: install them
        if win32:

            # On windows we use intl.dll: the core DLL of GNU gettext-runtime on Windows
            import ctypes

            libintl = ctypes.cdll.LoadLibrary("intl.dll")

            libintl.bindtextdomain(PACKAGE, LOCAL_MO_PATH)
            libintl.bind_textdomain_codeset(PACKAGE, "UTF-8")

        else:
            locale.bindtextdomain(PACKAGE, LOCAL_MO_PATH)
            gettext.bindtextdomain(PACKAGE, LOCAL_MO_PATH)

        tr = gettext.translation(PACKAGE, localedir=LOCAL_MO_PATH)
        tr.install()

    gettext.textdomain(PACKAGE)


def displayTraceback(exception=None):

    global log
    import traceback

    if exception is None:
        tb = traceback.format_tb(sys.exc_info()[2])
    else:
        tb = traceback.format_tb(exception)

    if log:
        log("Traceback: " + str(sys.exc_info()[0].__name__) + ": " + str(sys.exc_info()[1]))

    for line in tb:
        if type(line) is tuple:
            xline = ""
            for item in line:
                xline += str(item) + " "
            line = xline

        line = line.strip("\n")
        if log:
            log(line)

    traceback.print_exc()


def unescape(string):
    """Removes quotes from the beginning and end of strings, and unescapes it."""

    string = decode(encode(string, 'latin-1', 'backslashreplace'), 'unicode-escape')

    if (string[0] == string[-1]) and string.startswith(("'", '"')):
        return string[1:-1]
    return string


def executeCommand(command, replacement=None, background=True, returnoutput=False, placeholder='$'):
    """Executes a string with commands, with partial support for bash-style quoting and pipes.

    The different parts of the command should be separated by spaces, a double
    quotation mark can be used to embed spaces in an argument.
    Pipes can be created using the bar symbol (|).

    If background is false the function will wait for all the launched
    processes to end before returning.

    If the 'replacement' argument is given, every occurance of 'placeholder'
    will be replaced by 'replacement'.

    If the command ends with the ampersand symbol background
    will be set to True. This should only be done by the request of the user,
    if you want background to be true set the function argument.

    The only expected error to be thrown is the RuntimeError in case something
    goes wrong while executing the command.

    Example commands:
    * "C:\\Program Files\\WinAmp\\WinAmp.exe" --xforce "--title=My Window Title"
    * mplayer $
    * echo $ | flite -t """

    # Example command: "C:\Program Files\WinAmp\WinAmp.exe" --xforce "--title=My Title" $ | flite -t
    if returnoutput:
        background = False

    command = command.strip()

    if command.endswith("&"):
        command = command[:-1]
        if returnoutput:
            print("Yikes, I was asked to return output but I'm also asked to launch the process in the background. returnoutput gets precedent.")
        else:
            background = True

    unparsed = command
    arguments = []

    while unparsed.count('"') > 1:

        (pre, argument, post) = unparsed.split('"', 2)
        if pre:
            arguments += pre.rstrip(' ').split(' ')

        arguments.append(argument)
        unparsed = post.lstrip(' ')

    if unparsed:
        arguments += unparsed.split(' ')

    # arguments is now: ['C:\Program Files\WinAmp\WinAmp.exe', '--xforce', '--title=My Title', '$', '|', 'flite', '-t']
    subcommands = []
    current = []

    for argument in arguments:
        if argument in ('|',):
            subcommands.append(current)
            current = []
        else:
            current.append(argument)

    subcommands.append(current)

    # subcommands is now: [['C:\Program Files\WinAmp\WinAmp.exe', '--xforce', '--title=My Title', '$'], ['flite', '-t']]
    if replacement:
        for i in range(0, len(subcommands)):
            subcommands[i] = [x.replace(placeholder, replacement) for x in subcommands[i]]

    # Chaining commands...
    finalstdout = None
    if returnoutput:
        finalstdout = PIPE

    procs = []

    try:
        if len(subcommands) == 1:  # no need to fool around with pipes
            procs.append(Popen(subcommands[0], stdout=finalstdout))
        else:
            procs.append(Popen(subcommands[0], stdout=PIPE))
            for subcommand in subcommands[1:-1]:
                procs.append(Popen(subcommand, stdin=procs[-1].stdout, stdout=PIPE))
            procs.append(Popen(subcommands[-1], stdin=procs[-1].stdout, stdout=finalstdout))
        if not background and not returnoutput:
            procs[-1].wait()
    except Exception:
        raise RuntimeError("Problem while executing command %s (%s of %s)" % (subcommands[len(procs)], len(procs) + 1, len(subcommands)))

    if not returnoutput:
        return True

    return procs[-1].communicate()[0]


def findBestEncoding(bytes, encodings, fallback=None):
    """Tries to convert the bytes with the encodings, the first successful conversion is returned.

    If none match the fallback encoding will be used with the 'replace' argument. If no fallback is
    given the first encoding from the list is used."""

    if isinstance(bytes, str):
        return bytes

    for encoding in encodings:
        try:
            return str(bytes, encoding)
        except (UnicodeDecodeError, LookupError) as e:  # noqa: F841
            pass

    # None were successful
    if fallback:
        return str(bytes, fallback, 'replace')
    else:
        return str(bytes, encodings[0], 'replace')


def is_flatpak():
    """Detect if we are running Flatpak"""

    return sys.platform == "linux" and os.path.exists("/.flatpak-info")


def installPrefix():
    """Returns the system prefix where Nicotine+ is installed"""

    prefix = sys.prefix

    if is_flatpak():
        prefix = "/app"

    return prefix


def strace(function):
    """Decorator for debugging"""

    from itertools import chain

    def newfunc(*args, **kwargs):
        name = function.__name__
        print(("%s(%s)" % (name, ", ".join(map(repr, chain(args, list(kwargs.values())))))))
        retvalue = function(*args, **kwargs)
        print(("%s(%s): %s" % (name, ", ".join(map(repr, chain(args, list(kwargs.values())))), repr(retvalue))))
        return retvalue

    return newfunc


def cmp(a, b):
    """Replacement for cmp() which is removed in Python 3"""
    return (a > b) - (a < b)


def debug(*args):
    """
    Prints debugging info.
    TODO: add CLI switch --debug for en-/disabling.
    """
    truncated_args = [arg[:200] if isinstance(arg, str) else arg for arg in args]
    print('*' * 8, truncated_args)
