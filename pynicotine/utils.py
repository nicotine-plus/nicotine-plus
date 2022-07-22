# COPYRIGHT (C) 2020-2022 Nicotine+ Contributors
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

import json
import os
import pickle
import sys
import webbrowser

from pynicotine.config import config
from pynicotine.logfacility import log
from pynicotine.slskmessages import FileAttribute
from pynicotine.slskmessages import UINT_LIMIT

FILE_SIZE_SUFFIXES = ['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB']
PUNCTUATION = ['!', '"', '#', '$', '%', '&', '\'', '(', ')', '*', '+', ',', '-', '.', '/', ':', ';', '<', '=', '>',
               '?', '@', '[', '\\', ']', '^', '_', '`', '{', '|', '}', '~', '–', '—', '‐', '’', '“', '”', '…']
ILLEGALPATHCHARS = ['?', ':', '>', '<', '|', '*', '"']
ILLEGALFILECHARS = ILLEGALPATHCHARS + ['\\', '/']
LONG_PATH_PREFIX = "\\\\?\\"
REPLACEMENTCHAR = '_'
OPEN_SOULSEEK_URL = None


def rename_process(new_name, debug_info=False):

    errors = []

    # Renaming ourselves for pkill et al.
    try:
        import ctypes
        # GNU/Linux style
        libc = ctypes.CDLL(None)
        libc.prctl(15, new_name, 0, 0, 0)

    except Exception as error:
        errors.append(error)
        errors.append("Failed GNU/Linux style")

        try:
            import ctypes
            # BSD style
            libc = ctypes.CDLL(None)
            libc.setproctitle(new_name)

        except Exception as second_error:
            errors.append(second_error)
            errors.append("Failed BSD style")

    if debug_info and errors:
        msg = ["Errors occurred while trying to change process name:"]
        for i in errors:
            msg.append("%s" % (i,))
        log.add('\n'.join(msg))


def clean_file(filename):

    for char in ILLEGALFILECHARS:
        filename = filename.replace(char, REPLACEMENTCHAR)

    return filename


def clean_path(path, absolute=False):

    # Without hacks it is (up to Vista) not possible to have more
    # than 26 drives mounted, so we can assume a '[a-zA-Z]:\' prefix
    # for drives - we shouldn't escape that
    drive = ''
    if absolute and path[1:3] == ':\\' and path[0:1] and path[0].isalpha():
        drive = path[:3]
        path = path[3:]

    for char in ILLEGALPATHCHARS:
        path = path.replace(char, REPLACEMENTCHAR)

    path = ''.join([drive, path])

    # Path can never end with a period or space on Windows machines
    path = path.rstrip('. ')

    return path


def encode_path(path, prefix=True):
    """ Converts a file path to bytes for processing by the system.
    On Windows, also append prefix to enable extended-length path. """

    if sys.platform == "win32" and prefix:
        path = path.replace('/', '\\')

        if path.startswith('\\\\'):
            path = "UNC" + path[1:]

        path = LONG_PATH_PREFIX + path

    return path.encode("utf-8")


def _try_open_uri(uri):

    if sys.platform not in ("darwin", "win32"):
        try:
            from gi.repository import Gio  # pylint: disable=import-error
            Gio.AppInfo.launch_default_for_uri(uri)
            return

        except Exception:
            # Fall back to webbrowser module
            pass

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
        log.add(_("Failed to open file path: %s"), error)
        return False

    return True


def open_uri(uri):
    """ Open a URI in an external (web) browser. The given argument has
    to be a properly formed URI including the scheme (fe. HTTP). """

    try:
        # Situation 1, user defined a way of handling the protocol
        protocol = uri[:uri.find(":")]
        protocol_handlers = config.sections["urls"]["protocols"]

        if protocol in protocol_handlers and protocol_handlers[protocol]:
            execute_command(protocol_handlers[protocol], uri)
            return True

        if protocol == "slsk":
            OPEN_SOULSEEK_URL(uri.strip())  # pylint:disable=not-callable
            return True

        # Situation 2, user did not define a way of handling the protocol
        _try_open_uri(uri)

        return True

    except Exception as error:
        log.add(_("Failed to open URL: %s"), error)

    return False


def open_log(folder, filename):
    _handle_log(folder, filename, open_log_callback)


def delete_log(folder, filename):
    _handle_log(folder, filename, delete_log_callback)


def _handle_log(folder, filename, callback):

    folder_encoded = encode_path(folder)
    path = os.path.join(folder, clean_file(filename) + ".log")

    try:
        if not os.path.isdir(folder_encoded):
            os.makedirs(folder_encoded)

        callback(path)

    except Exception as error:
        log.add("Failed to process log file: %s", error)


def open_log_callback(path):
    open_file_path(path, create_file=True)


def delete_log_callback(path):
    os.remove(encode_path(path))


def get_latest_version():

    response = http_request(
        "https", "pypi.org", "/pypi/nicotine-plus/json",
        headers={"User-Agent": config.application_name}
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

    major, minor, patch = version.split(".")[:3]
    stable = 1

    if "dev" in version or "rc" in version:
        # Example: 2.0.1.dev1
        # A dev version will be one less than a stable version
        stable = 0

    return (int(major) << 24) + (int(minor) << 16) + (int(patch.split("rc", 1)[0]) << 8) + stable


def human_length(seconds):

    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)

    if days > 0:
        ret = '%i:%02i:%02i:%02i' % (days, hours, minutes, seconds)
    elif hours > 0:
        ret = '%i:%02i:%02i' % (hours, minutes, seconds)
    else:
        ret = '%i:%02i' % (minutes, seconds)

    return ret


def get_file_attributes(attributes):

    try:
        bitrate = attributes.get(str(FileAttribute.BITRATE))
        length = attributes.get(str(FileAttribute.DURATION))
        vbr = attributes.get(str(FileAttribute.VBR))
        sample_rate = attributes.get(str(FileAttribute.SAMPLE_RATE))
        bit_depth = attributes.get(str(FileAttribute.BIT_DEPTH))

    except AttributeError:
        # Legacy attribute list format used for shares lists saved in Nicotine+ 3.2.2 and earlier
        bitrate = length = vbr = sample_rate = bit_depth = None

        if len(attributes) == 3:
            attribute1, attribute2, attribute3 = attributes

            if attribute3 in (0, 1):
                bitrate = attribute1
                length = attribute2
                vbr = attribute3

            elif attribute3 > 1:
                length = attribute1
                sample_rate = attribute2
                bit_depth = attribute3

        elif len(attributes) == 2:
            attribute1, attribute2 = attributes

            if attribute2 in (0, 1):
                bitrate = attribute1
                vbr = attribute2

            elif attribute1 >= 8000 and attribute2 <= 64:
                sample_rate = attribute1
                bit_depth = attribute2

            else:
                bitrate = attribute1
                length = attribute2

    return bitrate, length, vbr, sample_rate, bit_depth


def get_result_bitrate_length(filesize, attributes):
    """ Used to get the audio bitrate and length of search results and
    user browse files """

    bitrate, length, vbr, sample_rate, bit_depth = get_file_attributes(attributes)

    if bitrate is None:
        if sample_rate and bit_depth:
            # Bitrate = sample rate (Hz) * word length (bits) * channel count
            # Bitrate = 44100 * 16 * 2
            bitrate = (sample_rate * bit_depth * 2) // 1000

        else:
            bitrate = -1

    if length is None:
        if bitrate > 0:
            # Dividing the file size by the bitrate in Bytes should give us a good enough approximation
            length = filesize / (bitrate * 125)

        else:
            length = -1

    # Ignore invalid values
    if bitrate <= 0 or bitrate > UINT_LIMIT:
        bitrate = 0
        h_bitrate = ""

    else:
        h_bitrate = str(bitrate)

        if vbr == 1:
            h_bitrate += " (vbr)"

    if length < 0 or length > UINT_LIMIT:
        length = 0
        h_length = ""

    else:
        h_length = human_length(length)

    return h_bitrate, bitrate, h_length, length


def _human_speed_or_size(unit):

    template = "%.3g %s"
    try:
        for suffix in FILE_SIZE_SUFFIXES:
            if unit < 1024:
                if unit > 999:
                    template = "%.4g %s"

                return template % (unit, suffix)

            unit /= 1024

    except TypeError:
        pass

    return str(unit)


def human_speed(speed):
    return _human_speed_or_size(speed) + "/s"


def human_size(filesize):
    return _human_speed_or_size(filesize)


def humanize(number):
    return "{:n}".format(number)


def truncate_string_byte(string, byte_limit, encoding='utf-8'):
    """ Truncates a string to fit inside a byte limit """

    return string.encode(encoding)[:max(byte_limit, 0)].decode(encoding, 'ignore')


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
            log.add("Yikes, I was asked to return output but I'm also asked to launch "
                    "the process in the background. returnoutput gets precedent.")
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
        raise RuntimeError("Problem while executing command %s (%s of %s)" %
                           (subcommands[len(procs)], len(procs) + 1, len(subcommands))) from error

    if not returnoutput:
        return True

    return procs[-1].communicate()[0]


def load_file(path, load_func, use_old_file=False):

    try:
        if use_old_file:
            path = path + ".old"

        elif os.path.isfile(encode_path(path + ".old")):
            path_encoded = encode_path(path)

            if not os.path.isfile(path_encoded):
                raise OSError("*.old file is present but main file is missing")

            if os.path.getsize(path_encoded) == 0:
                # Empty files should be considered broken/corrupted
                raise OSError("*.old file is present but main file is empty")

        return load_func(path)

    except Exception as error:
        log.add(_("Something went wrong while reading file %(filename)s: %(error)s"),
                {"filename": path, "error": error})

        if not use_old_file:
            # Attempt to load data from .old file
            log.add(_("Attempting to load backup of file %s"), path)
            return load_file(path, load_func, use_old_file=True)

    return None


def write_file_and_backup(path, callback, protect=False):

    path_encoded = encode_path(path)
    path_old_encoded = encode_path(path + ".old")

    # Back up old file to path.old
    try:
        if os.path.exists(path_encoded):
            from shutil import copy2
            copy2(path, path_old_encoded)

            if protect:
                os.chmod(path_old_encoded, 0o600)

    except Exception as error:
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

    except Exception as error:
        log.add(_("Unable to save file %(path)s: %(error)s"), {
            "path": path,
            "error": error
        })

        # Attempt to restore file
        try:
            if os.path.exists(path_old_encoded):
                os.replace(path_old_encoded, path)

        except Exception as second_error:
            log.add(_("Unable to restore previous file %(path)s: %(error)s"), {
                "path": path,
                "error": second_error
            })

    if protect:
        os.umask(oldumask)


def http_request(url_scheme, base_url, path, request_type="GET", body="", headers=None, timeout=10, redirect_depth=0):

    if headers is None:
        headers = {}

    import http.client

    if redirect_depth > 15:
        raise http.client.HTTPException("Redirected too many times, giving up")

    if url_scheme == "https":
        conn = http.client.HTTPSConnection(base_url, timeout=timeout)
    else:
        conn = http.client.HTTPConnection(base_url, timeout=timeout)

    try:
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

    finally:
        # Always close connection, even when errors occur
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


""" Command Aliases """


def add_alias(rest):

    aliases = config.sections["server"]["command_aliases"]

    if rest:
        args = rest.split(" ", 1)

        if len(args) == 2:
            if args[0] in ("alias", "unalias"):
                return "I will not alias that!\n"

            aliases[args[0]] = args[1]

        if args[0] in aliases:
            return "Alias %s: %s\n" % (args[0], aliases[args[0]])

        return _("No such alias (%s)") % rest + "\n"

    msg = "\n" + _("Aliases:") + "\n"

    for key, value in aliases.items():
        msg = msg + "%s: %s\n" % (key, value)

    return msg + "\n"


def unalias(rest):

    aliases = config.sections["server"]["command_aliases"]

    if rest and rest in aliases:
        action = aliases[rest]
        del aliases[rest]

        return _("Removed alias %(alias)s: %(action)s\n") % {'alias': rest, 'action': action}

    return _("No such alias (%(alias)s)\n") % {'alias': rest}


def is_alias(command):

    if not command.startswith("/"):
        return False

    base_command = command[1:].split(" ")[0]

    if base_command in config.sections["server"]["command_aliases"]:
        return True

    return False


def get_alias(command):

    def getpart(line):

        if line[0] != "(":
            return ""

        i = 1
        ret = ""
        level = 0

        while i < len(line):
            if line[i] == "(":
                level = level + 1

            if line[i] == ")":
                if level == 0:
                    return ret

                level = level - 1

            ret = ret + line[i]
            i = i + 1

        return ""

    try:
        command = command[1:].split(" ")
        alias = config.sections["server"]["command_aliases"][command[0]]
        param_string_found = False
        ret = ""
        i = 0

        while i < len(alias):
            if alias[i:i + 2] == "$(":
                arg = getpart(alias[i + 1:])

                if not arg:
                    ret = ret + "$"
                    i = i + 1
                    continue

                i = i + len(arg) + 3
                args = arg.split("=", 1)

                if len(args) > 1:
                    default = args[1]
                else:
                    default = ""

                args = args[0].split(":")

                if len(args) == 1:
                    first = last = int(args[0])
                else:
                    if args[0]:
                        first = int(args[0])
                    else:
                        first = 1

                    if args[1]:
                        last = int(args[1])
                    else:
                        last = len(command)

                value = " ".join(command[first:last + 1])

                if not value:
                    value = default

                ret = ret + value
                param_string_found = True

            else:
                ret = ret + alias[i]
                i = i + 1

                if not param_string_found and i == len(alias) and alias.startswith("/"):
                    # Reached the end of alias contents, append potential arguments passed to the command
                    args = " ".join(command[1:])

                    if args:
                        ret = ret + " " + args

        return ret

    except Exception as error:
        log.add("%s", error)

    return ""


""" Chat Completion """


def get_completion_list(commands, rooms):

    config_words = config.sections["words"]

    if not config_words["tab"]:
        return []

    completion_list = [config.sections["server"]["login"], "nicotine"]

    if config_words["roomnames"]:
        completion_list += rooms

    if config_words["buddies"]:
        for i in config.sections["server"]["userlist"]:
            if i and isinstance(i, list):
                user = str(i[0])
                completion_list.append(user)

    if config_words["aliases"]:
        for k in config.sections["server"]["command_aliases"]:
            completion_list.append("/" + str(k))

    if config_words["commands"]:
        completion_list += commands

    return completion_list


""" Debugging """


def debug(*args):
    """ Prints debugging info. """

    truncated_args = [arg[:200] if isinstance(arg, str) else arg for arg in args]
    log.add('*' * 8, truncated_args)


def strace(function):
    """ Decorator for debugging """

    from itertools import chain

    def newfunc(*args, **kwargs):
        name = function.__name__
        log.add("%s(%s)" % (name, ", ".join(map(repr, chain(args, list(kwargs.values()))))))
        retvalue = function(*args, **kwargs)
        log.add("%s(%s): %s" % (name, ", ".join(map(repr, chain(args, list(kwargs.values())))), repr(retvalue)))
        return retvalue

    return newfunc
