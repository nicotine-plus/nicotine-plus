# -*- coding: utf-8 -*-
#
# COPYRIGHT (c) 2016 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2007 Daelstorm <daelstorm@gmail.com>
# COPYRIGHT (C) 2003-2004 Hyriand
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

from __future__ import division

import string
from UserDict import UserDict
from subprocess import Popen, PIPE
import os
import dircache
import sys
import gobject
import locale
import gettext
import gtk.glade

from libi18n import SetLocaleEnv
from logfacility import log as logfacility

version = "1.3.0git"

log = 0
win32 = sys.platform.startswith("win")

illegalpathchars = []
if win32:
    illegalpathchars += ["?", ":", ">", "<", "|", "*", '"']
illegafilechars = illegalpathchars + ["\\", "/"]
replacementchar = '_'


def CleanFile(filename):
    for char in illegafilechars:
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


def CheckTranslationAvailability(lang):
    """Function that check the availabilty for a specified language"""

    # Package name for gettext
    PACKAGE = 'nicotine'

    # Local path where to find translation (mo) files
    LOCAL_MO_PATH = 'languages'

    # Message to return to the settingswindow if errors are found
    msg_alert = ""

    # We don't need checkr since the user wants the english language
    if lang == "en":
        return

    # We try to find the translation file in the current path
    if gettext.find(PACKAGE,
                    localedir=LOCAL_MO_PATH,
                    languages=[lang]
                    ) is None:

        # We try to find the translation file in the global path
        if gettext.find(PACKAGE, languages=[lang]) is None:

            msg_alert = _("Translation for '%s' not found.") % (lang)

    return msg_alert


def ApplyTranslation(lang=None):
    """Function dealing with translations and locales.

    If no language is specified by the user we try to autodetect it
    and fix the locale.

    If a language is specified by the user we try to load the corresponding
    translation file and fix the locale.

    In both case if something goes wrong we fall back to no translation.

    This function also try to find translation files in the project path first:
    $(PROJECT_PATH)/languages/$(LANG)/LC_MESSAGES/nicotine.mo

    If no translations are found we fall back to the system path for locates:
    GNU/Linux: /usr/share/locale/$(LANG)/LC_MESSAGES
    Windows: %PYTHONHOME%\share\locale\$(LANG)\LC_MESSAGES

    Note: To the best of my knowledge when we are in a python venv
    falling back to the system path does not work."""

    # Package name for gettext
    PACKAGE = 'nicotine'

    # Local path where to find translation (mo) files
    LOCAL_MO_PATH = 'languages'

    # If no lang is provided we try to autodetect it
    if lang is None:

        # Setting up environnement variables for locale handling
        SetLocaleEnv()

        # Current language derived from the locale
        currentlang = locale.getlocale()[0].split('_')[0]

        if currentlang == "en":
            # If the current locale is english we dont translate
            # It can be either that the locale of the user is really english
            # ot we might be in the fallback mode of the locale handling
            gettext.install(PACKAGE)
        else:

            try:
                # We try to find the translation file in the current path first
                tr = gettext.translation(PACKAGE, localedir=LOCAL_MO_PATH)
                tr.install()
            except IOError as e1:

                try:
                    # We try to find the translation file in the global path
                    tr = gettext.translation(PACKAGE)
                    tr.install()
                except IOError as e2:
                    logfacility.addwarning("Translation for '%s' not found, "
                                           "falling back to english" %
                                           (currentlang)
                                           )

                    # If we can't find the translation for the current locale
                    # we fall back to no translation at all
                    gettext.install(PACKAGE)

                    # And we reset locale to english
                    SetLocaleEnv("en")
    else:

        # The user has forced a language to be used
        # Setting up environnement variables for the specified language
        SetLocaleEnv(lang)

        if lang == "en":
            # We don't translate since the user wants the english language
            gettext.install(PACKAGE)
        else:

            try:
                # We try to find the translation file in the current path
                tr = gettext.translation(PACKAGE,
                                         localedir=LOCAL_MO_PATH,
                                         languages=[lang]
                                         )
                tr.install()
            except IOError as e1:

                try:
                    # We try to find the translation file in the global path
                    tr = gettext.translation(PACKAGE, languages=[lang])
                    tr.install()
                except IOError as e2:
                    logfacility.addwarning("Translation for '%s' not found, "
                                           "falling back to english" %
                                           (lang)
                                           )

                    # If we can't find the translation for the specified
                    # language: we fall back to no translation at all
                    gettext.install(PACKAGE)

                    # And we reset locale to english
                    SetLocaleEnv("en")

    # Now we bind glade to the nicotine domain
    # Same method than before, try the local then global path
    if gettext.find(PACKAGE, localedir=LOCAL_MO_PATH) is None:
        gtk.glade.bindtextdomain(PACKAGE)
    else:
        gtk.glade.bindtextdomain(PACKAGE, LOCAL_MO_PATH)

    gtk.glade.textdomain(PACKAGE)


def getServerList(url):
    """ Parse server text file from http://www.slsk.org and
    return a list of servers """
    import urllib
    try:
        f = urllib.urlopen(url)
        list = [string.strip(i) for i in f.readlines()]
    except:
        return []
    try:
        list = list[list.index("--servers")+1:]
    except:
        return []
    list = [string.split(i, ":", 2) for i in list]
    try:
        return [[i[0], i[2]] for i in list]
    except:
        return []


def displayTraceback(exception=None):
    global log
    import traceback
    if exception is None:
        tb = traceback.format_tb(sys.exc_info()[2])
    else:
        tb = traceback.format_tb(exception)
    if log: log("Traceback: " + str(sys.exc_info()[0].__name__) + ": " + str(sys.exc_info()[1]))
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


# Dictionary that's sorted alphabetically
# @param UserDict dictionary to be alphabetized
class SortedDict(UserDict):
    # Constructor
    # @param self SortedDict
    def __init__(self):
        self.__keys__ = []
        self.__sorted__ = True
        UserDict.__init__(self)

    # Set key
    # @param self SortedDict
    # @param key dict key
    # @param value dict value
    def __setitem__(self, key, value):
        if not self.__dict__.has_key(key):
            self.__keys__.append(key)
            self.__sorted__ = False
        UserDict.__setitem__(self, key, value)

    # Delete key
    # @param self SortedDict
    # @param key dict key
    def __delitem__(self, key):
        self.__keys__.remove(key)
        UserDict.__delitem__(self, key)

    # Get keys
    # @param self SortedDict
    # @return __keys__
    def keys(self):
        if not self.__sorted__:
            self.__keys__.sort()
            self.__sorted__ = True
        return self.__keys__

    # Get items
    # @param self SortedDict
    # @return list of keys and items
    def items(self):
        if not self.__sorted__:
            self.__keys__.sort()
            self.__sorted__ = True
        for key in self.__keys__:
            yield key, self[key]


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
    * "C:\Program Files\WinAmp\WinAmp.exe" --xforce "--title=My Window Title"
    * mplayer $
    * echo $ | flite -t """

    # Example command: "C:\Program Files\WinAmp\WinAmp.exe" --xforce "--title=My Title" $ | flite -t
    if returnoutput:
        background = False
    command = command.strip()
    if command.endswith("&"):
        command = command[:-1]
        if returnoutput:
            print "Yikes, I was asked to return output but I'm also asked to launch the process in the background. returnoutput gets precedent."
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
        for i in xrange(0, len(subcommands)):
            subcommands[i] = [x.replace(placeholder, replacement) for x in subcommands[i]]
    # Chaining commands...
    finalstdout = None
    if returnoutput:
        finalstdout = PIPE
    procs = []
    try:
        if len(subcommands) == 1: # no need to fool around with pipes
            procs.append(Popen(subcommands[0], stdout=finalstdout))
        else:
            procs.append(Popen(subcommands[0], stdout=PIPE))
            for subcommand in subcommands[1:-1]:
                procs.append(Popen(subcommand, stdin=procs[-1].stdout, stdout=PIPE))
            procs.append(Popen(subcommands[-1], stdin=procs[-1].stdout, stdout=finalstdout))
        if not background and not returnoutput:
            procs[-1].wait()
    except:
        raise RuntimeError("Problem while executing command %s (%s of %s)" % (subcommands[len(procs)], len(procs)+1, len(subcommands)))
    if not returnoutput:
        return True
    return procs[-1].communicate()[0]


def findBestEncoding(bytes, encodings, fallback=None):
    """Tries to convert the bytes with the encodings, the first successful conversion is returned.

    If none match the fallback encoding will be used with the 'replace' argument. If no fallback is
    given the first encoding from the list is used."""
    for encoding in encodings:
        try:
            return unicode(bytes, encoding)
        except (UnicodeDecodeError, LookupError), e:
            pass
    # None were successful
    if fallback:
        return unicode(bytes, fallback, 'replace')
    else:
        return unicode(bytes, encodings[0], 'replace')


def strace(function):
    """Decorator for debugging"""
    from itertools import chain
    def newfunc(*args, **kwargs):
        name = function.__name__
        print("%s(%s)" % (name, ", ".join(map(repr, chain(args, kwargs.values())))))
        retvalue = function(*args, **kwargs)
        print("%s(%s): %s" % (name, ", ".join(map(repr, chain(args, kwargs.values()))), repr(retvalue)))
        return retvalue
    return newfunc
