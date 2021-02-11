# COPYRIGHT (C) 2020-2021 Nicotine+ Team
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
import pickle
import sys
import time

version = "3.0.0"

win32 = sys.platform.startswith("win")

illegalpathchars = []
if win32:
    illegalpathchars += ["?", ":", ">", "<", "|", "*", '"']

illegalfilechars = illegalpathchars + ["\\", "/"]
replacementchar = '_'


def clean_file(filename):

    if win32:
        for char in illegalfilechars:
            filename = filename.replace(char, replacementchar)

    return filename


def clean_path(path, absolute=False):

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


def get_latest_version():

    import json

    response = http_request(
        "https", "pypi.org", "/pypi/nicotine-plus/json",
        headers={"User-Agent": "Nicotine+"}
    )
    data = json.loads(response)

    hlatest = data['info']['version']
    latest = int(make_version(hlatest))

    try:
        date = data['releases'][hlatest][0]['upload_time']
    except Exception:
        date = None

    return hlatest, latest, date


def make_version(version):

    s = version.split(".")
    major, minor, patch = (int(i) for i in s[:3])
    stable = 1

    if "dev" in version or \
            "rc" in version:
        # Example: 2.0.1.dev1
        # A dev version will be one less than a stable version
        stable = 0

    return (major << 24) + (minor << 16) + (patch << 8) + stable


def get_user_directories():
    """Returns a tuple:
    - the config directory
    - the data directory"""

    if win32:
        try:
            data_dir = os.path.join(os.environ['APPDATA'], 'nicotine')
        except KeyError:
            data_dir, x = os.path.split(sys.argv[0])

        config_dir = os.path.join(data_dir, "config")
        return config_dir, data_dir

    home = os.path.expanduser("~")

    legacy_dir = os.path.join(home, '.nicotine')

    if os.path.isdir(legacy_dir):
        return legacy_dir, legacy_dir

    def xdg_path(xdg, default):
        path = os.environ.get(xdg)

        path = path.split(':')[0] if path else default

        return os.path.join(path, 'nicotine')

    config_dir = xdg_path('XDG_CONFIG_HOME', os.path.join(home, '.config'))
    data_dir = xdg_path('XDG_DATA_HOME', os.path.join(home, '.local', 'share'))

    return config_dir, data_dir


def get_result_bitrate_length(filesize, attributes):
    """ Used to get the audio bitrate and length of search results and
    user browse files """

    h_bitrate = ""
    h_length = ""

    bitrate = 0
    length = 0

    # If there are 3 entries in the attribute list
    if len(attributes) == 3:

        first = attributes[0]
        second = attributes[1]
        third = attributes[2]

        # Sometimes the vbr indicator is in third position
        if third == 0 or third == 1:

            if third == 1:
                h_bitrate = " (vbr)"

            bitrate = first
            h_bitrate = str(bitrate) + h_bitrate

            length = second
            h_length = '%i:%02i' % (second / 60, second % 60)

        # Sometimes the vbr indicator is in second position
        elif second == 0 or second == 1:

            if second == 1:
                h_bitrate = " (vbr)"

            bitrate = first
            h_bitrate = str(bitrate) + h_bitrate

            length = third
            h_length = '%i:%02i' % (third / 60, third % 60)

        # Lossless audio, length is in first position
        elif third > 1:

            # Bitrate = sample rate (Hz) * word length (bits) * channel count
            # Bitrate = 44100 * 16 * 2
            bitrate = (second * third * 2) / 1000
            h_bitrate = str(bitrate)

            length = first
            h_length = '%i:%02i' % (first / 60, first % 60)

        else:

            bitrate = first
            h_bitrate = str(bitrate) + h_bitrate

    # If there are 2 entries in the attribute list
    elif len(attributes) == 2:

        first = attributes[0]
        second = attributes[1]

        # Sometimes the vbr indicator is in second position
        if second == 0 or second == 1:

            # If it's a vbr file we can't deduce the length
            if second == 1:

                h_bitrate = " (vbr)"

                bitrate = first
                h_bitrate = str(bitrate) + h_bitrate

            # If it's a constant bitrate we can deduce the length
            else:

                bitrate = first
                h_bitrate = str(bitrate) + h_bitrate

                if bitrate <= 0:
                    length = 0
                else:
                    # Dividing the file size by the bitrate in Bytes should give us a good enough approximation
                    length = filesize / (bitrate / 8 * 1000)

                h_length = '%i:%02i' % (length / 60, length % 60)

        # Sometimes the bitrate is in first position and the length in second position
        else:

            bitrate = first
            h_bitrate = str(bitrate) + h_bitrate

            length = second
            h_length = '%i:%02i' % (second / 60, second % 60)

    return h_bitrate, bitrate, h_length, length


def apply_translation():
    """Function dealing with translations and locales.

    We try to autodetect the language and fix the locale.

    If something goes wrong we fall back to no translation.

    This function also try to find translation files in the project path first:
    $(PROJECT_PATH)/mo/$(LANG)/LC_MESSAGES/nicotine.mo

    If no translations are found we fall back to the system path for locates:
    GNU/Linux: /usr/share/locale/$(LANG)/LC_MESSAGES
    Windows: %PYTHONHOME%\\share\\locale\\$(LANG)\\LC_MESSAGES

    Note: To the best of my knowledge when we are in a python venv
    falling back to the system path does not work."""

    # Locales handling: We let the system handle the locales
    try:
        locale.setlocale(locale.LC_ALL, '')

    except Exception as e:
        print("Error while attempting to set locale: %s" % e)

    # package name for gettext
    package = 'nicotine'

    # Local path where to find translation (mo) files
    local_mo_path = 'mo'

    # Gettext handling
    if gettext.find(package, localedir=local_mo_path) is None:

        # Locales are not in the current dir
        # We let gettext handle the situation: if if found them in the system dir
        # the app will be trnaslated, if not it will be untranslated.
        gettext.install(package)

    else:

        # Locales are in the current dir: install them
        gettext.bindtextdomain(package, local_mo_path)
        gettext.install(package, local_mo_path)

    gettext.textdomain(package)


def unescape(string):
    """Removes quotes from the beginning and end of strings, and unescapes it."""

    string = string.encode('latin-1', 'backslashreplace').decode('unicode-escape')

    try:
        if (string[0] == string[-1]) and string.startswith(("'", '"')):
            return string[1:-1]
    except IndexError:
        pass

    return string


def execute_command(command, replacement=None, background=True, returnoutput=False, placeholder='$'):
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

    from subprocess import PIPE
    from subprocess import Popen

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


def write_log(logsdir, fn, msg, timestamp_format="%Y-%m-%d %H:%M:%S"):

    try:
        oldumask = os.umask(0o077)
        if not os.path.exists(logsdir):
            os.makedirs(logsdir)

        with open(os.path.join(logsdir, clean_file(fn.replace(os.sep, "-")) + ".log"), 'ab', 0) as logfile:
            os.umask(oldumask)

            text = "%s %s\n" % (time.strftime(timestamp_format), msg)
            logfile.write(text.encode('utf-8', 'replace'))

    except Exception as error:
        print(_("Couldn't write to log file \"%s\": %s") % (fn, error))


def http_request(url_scheme, base_url, path, request_type="GET", body="", headers={}, timeout=10, redirect_depth=0):

    if redirect_depth > 15:
        raise Exception("Redirected too many times, giving up")

    import http.client

    if url_scheme == "https":
        conn = http.client.HTTPSConnection(base_url, timeout=timeout)
    else:
        conn = http.client.HTTPConnection(base_url, timeout=timeout)

    conn.request(request_type, path, body=body, headers=headers)
    response = conn.getresponse()
    redirect = response.getheader('Location')

    if redirect:
        from urllib.parse import urlparse
        parsed_url = urlparse(redirect)
        redirect_depth += 1

        return http_request(
            parsed_url.scheme, parsed_url.netloc, parsed_url.path,
            request_type, body, headers, timeout, redirect_depth
        )

    contents = response.read().decode("utf-8")
    conn.close()

    return contents


class RestrictedUnpickler(pickle.Unpickler):
    """
    Don't allow code execution from pickles
    """

    def find_class(self, module, name):
        # Forbid all globals
        raise pickle.UnpicklingError("global '%s.%s' is forbidden" %
                                     (module, name))


""" Debugging """


def debug(*args):
    """ Prints debugging info. """

    truncated_args = [arg[:200] if isinstance(arg, str) else arg for arg in args]
    print('*' * 8, truncated_args)


def strace(function):
    """ Decorator for debugging """

    from itertools import chain

    def newfunc(*args, **kwargs):
        name = function.__name__
        print(("%s(%s)" % (name, ", ".join(map(repr, chain(args, list(kwargs.values())))))))
        retvalue = function(*args, **kwargs)
        print(("%s(%s): %s" % (name, ", ".join(map(repr, chain(args, list(kwargs.values())))), repr(retvalue))))
        return retvalue

    return newfunc
