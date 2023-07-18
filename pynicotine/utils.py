# COPYRIGHT (C) 2020-2023 Nicotine+ Contributors
# COPYRIGHT (C) 2020 Lene Preuss <lene.preuss@gmail.com>
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2007 daelstorm <daelstorm@gmail.com>
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

import os
import pickle
import sys

UINT32_LIMIT = 4294967295
UINT64_LIMIT = 18446744073709551615
FILE_SIZE_SUFFIXES = ["B", "KiB", "MiB", "GiB", "TiB", "PiB", "EiB", "ZiB", "YiB"]
PUNCTUATION = ["!", '"', "#", "$", "%", "&", "'", "(", ")", "*", "+", ",", "-", ".", "/", ":", ";", "<", "=", ">",
               "?", "@", "[", "\\", "]", "^", "_", "`", "{", "|", "}", "~", "–", "—", "‐", "’", "“", "”", "…"]
ILLEGALPATHCHARS = ["?", ":", ">", "<", "|", "*", '"']
ILLEGALFILECHARS = ILLEGALPATHCHARS + ["\\", "/"]
LONG_PATH_PREFIX = "\\\\?\\"
REPLACEMENTCHAR = "_"
TRANSLATE_PUNCTUATION = str.maketrans(dict.fromkeys(PUNCTUATION, " "))


def clean_file(filename):

    for char in ILLEGALFILECHARS:
        filename = filename.replace(char, REPLACEMENTCHAR)

    return filename


def clean_path(path):

    path = os.path.normpath(path)

    # Without hacks it is (up to Vista) not possible to have more
    # than 26 drives mounted, so we can assume a '[a-zA-Z]:\' prefix
    # for drives - we shouldn't escape that
    drive = ""

    if len(path) >= 3 and path[1] == ":" and path[2] == os.sep:
        drive = path[:3]
        path = path[3:]

    for char in ILLEGALPATHCHARS:
        path = path.replace(char, REPLACEMENTCHAR)

    path = "".join([drive, path])

    # Path can never end with a period or space on Windows machines
    path = path.rstrip(". ")

    return path


def encode_path(path, prefix=True):
    """ Converts a file path to bytes for processing by the system.
    On Windows, also append prefix to enable extended-length path. """

    if sys.platform == "win32" and prefix:
        path = path.replace("/", "\\")

        if path.startswith("\\\\"):
            path = "UNC" + path[1:]

        path = LONG_PATH_PREFIX + path

    return path.encode("utf-8")


def human_length(seconds):

    minutes, seconds = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)

    if days > 0:
        return f"{days}:{hours:02d}:{minutes:02d}:{seconds:02d}"

    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"

    return f"{minutes}:{seconds:02d}"


def _human_speed_or_size(number, unit=None):

    if unit == "B":
        return humanize(number)

    try:
        for suffix in FILE_SIZE_SUFFIXES:
            if number < 1024:
                if number > 999:
                    return f"{number:.4g} {suffix}"

                return f"{number:.3g} {suffix}"

            number /= 1024

    except TypeError:
        pass

    return str(number)


def human_speed(speed):
    return _human_speed_or_size(speed) + "/s"


def human_size(filesize, unit=None):
    return _human_speed_or_size(filesize, unit)


def humanize(number):
    return f"{number:n}"


def factorize(filesize, base=1024):
    """ Converts filesize string with a given unit into raw integer size,
        defaults to binary for "k", "m", "g" suffixes (KiB, MiB, GiB) """

    if not filesize:
        return None, None

    if filesize[-1:].lower() == "b":
        base = 1000  # Byte suffix detected, prepare to use decimal if necessary
        filesize = filesize[:-1]

    if filesize[-1:].lower() == "i":
        base = 1024  # Binary requested, stop using decimal
        filesize = filesize[:-1]

    if filesize.lower()[-1:] == "g":
        factor = pow(base, 3)
        filesize = filesize[:-1]

    elif filesize.lower()[-1:] == "m":
        factor = pow(base, 2)
        filesize = filesize[:-1]

    elif filesize.lower()[-1:] == "k":
        factor = base
        filesize = filesize[:-1]

    else:
        factor = 1

    try:
        return int(float(filesize) * factor), factor
    except ValueError:
        return None, factor


def truncate_string_byte(string, byte_limit, encoding="utf-8", ellipsize=False):
    """ Truncates a string to fit inside a byte limit """

    string_bytes = string.encode(encoding)

    if len(string_bytes) <= byte_limit:
        # Nothing to do, return original string
        return string

    if ellipsize:
        ellipsis_char = "…".encode(encoding)
        string_bytes = string_bytes[:max(byte_limit - len(ellipsis_char), 0)].rstrip() + ellipsis_char
    else:
        string_bytes = string_bytes[:byte_limit]

    return string_bytes.decode(encoding, "ignore")


def unescape(string):
    """Removes quotes from the beginning and end of strings, and unescapes it."""

    string = string.encode("latin-1", "backslashreplace").decode("unicode-escape")

    try:
        if (string[0] == string[-1]) and string.startswith(("'", '"')):
            return string[1:-1]
    except IndexError:
        pass

    return string


def execute_command(command, replacement=None, background=True, returnoutput=False, placeholder="$"):
    """Executes a string with commands, with partial support for bash-style quoting and pipes.

    The different parts of the command should be separated by spaces, a double
    quotation mark can be used to embed spaces in an argument.
    Pipes can be created using the bar symbol (|).

    If background is false the function will wait for all the launched
    processes to end before returning.

    If the 'replacement' argument is given, every occurrence of 'placeholder'
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
            from pynicotine.logfacility import log
            log.add("Yikes, I was asked to return output but I'm also asked to launch "
                    "the process in the background. returnoutput gets precedent.")
        else:
            background = True

    unparsed = command
    arguments = []

    while unparsed.count('"') > 1:

        (pre, argument, post) = unparsed.split('"', 2)
        if pre:
            arguments += pre.rstrip(" ").split(" ")

        arguments.append(argument)
        unparsed = post.lstrip(" ")

    if unparsed:
        arguments += unparsed.split(" ")

    # arguments is now: ['C:\Program Files\WinAmp\WinAmp.exe', '--xforce', '--title=My Title', '$', '|', 'flite', '-t']
    subcommands = []
    current = []

    for argument in arguments:
        if argument in ("|",):
            subcommands.append(current)
            current = []
        else:
            current.append(argument)

    subcommands.append(current)

    # subcommands is now: [['C:\Program Files\WinAmp\WinAmp.exe', '--xforce', '--title=My Title', '$'], ['flite', '-t']]
    if replacement:
        for i, _ in enumerate(subcommands):
            subcommands[i] = [x.replace(placeholder, replacement) for x in subcommands[i]]

    # Chaining commands...
    finalstdout = None
    if returnoutput:
        finalstdout = PIPE

    procs = []

    try:
        if len(subcommands) == 1:  # no need to fool around with pipes
            procs.append(Popen(subcommands[0], stdout=finalstdout))      # pylint: disable=consider-using-with
        else:
            procs.append(Popen(subcommands[0], stdout=PIPE))             # pylint: disable=consider-using-with

            for subcommand in subcommands[1:-1]:
                procs.append(Popen(subcommand, stdin=procs[-1].stdout,   # pylint: disable=consider-using-with
                                   stdout=PIPE))

            procs.append(Popen(subcommands[-1], stdin=procs[-1].stdout,  # pylint: disable=consider-using-with
                               stdout=finalstdout))

        if not background and not returnoutput:
            procs[-1].wait()

    except Exception as error:
        command = subcommands[len(procs)]
        command_no = len(procs) + 1
        num_commands = len(subcommands)
        raise RuntimeError(f"Problem while executing command {command} ({command_no} of {num_commands}") from error

    if not returnoutput:
        return True

    return procs[-1].communicate()[0]


def _try_open_uri(uri):

    if sys.platform not in ("darwin", "win32"):
        try:
            from gi.repository import Gio  # pylint: disable=import-error
            Gio.AppInfo.launch_default_for_uri(uri)
            return

        except Exception:
            # Fall back to webbrowser module
            pass

    import webbrowser

    if not webbrowser.open(uri):
        raise webbrowser.Error("No known URI provider available")


def open_file_path(file_path, command=None, create_folder=False, create_file=False):
    """ Currently used to either open a folder or play an audio file
    Tries to run a user-specified command first, and falls back to
    the system default. """

    if file_path is None:
        return False

    try:
        file_path = os.path.normpath(file_path)
        file_path_encoded = encode_path(file_path)

        if not os.path.exists(file_path_encoded):
            if create_folder:
                os.makedirs(file_path_encoded)

            elif create_file:
                with open(file_path_encoded, "w", encoding="utf-8"):
                    # Create empty file
                    pass
            else:
                raise FileNotFoundError("File path does not exist")

        if command and "$" in command:
            execute_command(command, file_path)

        elif sys.platform == "win32":
            os.startfile(file_path_encoded)  # pylint: disable=no-member

        elif sys.platform == "darwin":
            execute_command("open $", file_path)

        else:
            _try_open_uri("file:///" + file_path)

    except Exception as error:
        from pynicotine.logfacility import log
        log.add(_("Cannot open file path %(path)s: %(error)s"), {"path": file_path, "error": error})
        return False

    return True


def open_uri(uri):
    """ Open a URI in an external (web) browser. The given argument has
    to be a properly formed URI including the scheme (fe. HTTP). """

    from pynicotine.config import config

    try:
        # Situation 1, user defined a way of handling the protocol
        protocol = uri[:uri.find(":")]
        protocol_handlers = config.sections["urls"]["protocols"]

        if protocol in protocol_handlers and protocol_handlers[protocol]:
            execute_command(protocol_handlers[protocol], uri)
            return True

        if protocol == "slsk":
            from pynicotine.core import core
            core.userbrowse.open_soulseek_url(uri.strip())
            return True

        # Situation 2, user did not define a way of handling the protocol
        _try_open_uri(uri)

        return True

    except Exception as error:
        from pynicotine.logfacility import log
        log.add(_("Cannot open URL %(url)s: %(error)s"), {"url": uri, "error": error})

    return False


def load_file(path, load_func, use_old_file=False):

    try:
        if use_old_file:
            path = f"{path}.old"

        elif os.path.isfile(encode_path(f"{path}.old")):
            path_encoded = encode_path(path)

            if not os.path.isfile(path_encoded):
                raise OSError("*.old file is present but main file is missing")

            if os.path.getsize(path_encoded) == 0:
                # Empty files should be considered broken/corrupted
                raise OSError("*.old file is present but main file is empty")

        return load_func(path)

    except Exception as error:
        from pynicotine.logfacility import log
        log.add(_("Something went wrong while reading file %(filename)s: %(error)s"),
                {"filename": path, "error": error})

        if not use_old_file:
            # Attempt to load data from .old file
            log.add(_("Attempting to load backup of file %s"), path)
            return load_file(path, load_func, use_old_file=True)

    return None


def write_file_and_backup(path, callback, protect=False):

    path_encoded = encode_path(path)
    path_old_encoded = encode_path(f"{path}.old")

    # Back up old file to path.old
    try:
        if os.path.exists(path_encoded) and os.stat(path_encoded).st_size > 0:
            os.replace(path_encoded, path_old_encoded)

            if protect:
                os.chmod(path_old_encoded, 0o600)

    except Exception as error:
        from pynicotine.logfacility import log
        log.add(_("Unable to back up file %(path)s: %(error)s"), {
            "path": path,
            "error": error
        })
        return

    # Save new file
    if protect:
        oldumask = os.umask(0o077)

    try:
        with open(path_encoded, "w", encoding="utf-8") as file_handle:
            callback(file_handle)

            # Force write to file immediately in case of hard shutdown
            file_handle.flush()
            os.fsync(file_handle.fileno())

    except Exception as error:
        from pynicotine.logfacility import log
        log.add(_("Unable to save file %(path)s: %(error)s"), {
            "path": path,
            "error": error
        })

        # Attempt to restore file
        try:
            if os.path.exists(path_old_encoded):
                os.replace(path_old_encoded, path_encoded)

        except Exception as second_error:
            log.add(_("Unable to restore previous file %(path)s: %(error)s"), {
                "path": path,
                "error": second_error
            })

    if protect:
        os.umask(oldumask)


class RestrictedUnpickler(pickle.Unpickler):
    """
    Don't allow code execution from pickles
    """

    def find_class(self, module, name):
        # Forbid all globals
        raise pickle.UnpicklingError(f"global '{module}.{name}' is forbidden")


""" Debugging """


def debug(*args):
    """ Prints debugging info. """

    from pynicotine.logfacility import log

    truncated_args = [arg[:200] if isinstance(arg, str) else arg for arg in args]
    log.add("*" * 8, truncated_args)


def strace(function):
    """ Decorator for debugging """

    from itertools import chain
    from pynicotine.logfacility import log

    def newfunc(*args, **kwargs):
        name = function.__name__
        log.add(f"{name}({', '.join(map(repr, chain(args, list(kwargs.values()))))})")
        retvalue = function(*args, **kwargs)
        log.add(f"{name}({', '.join(map(repr, chain(args, list(kwargs.values()))))}): {repr(retvalue)}")
        return retvalue

    return newfunc
