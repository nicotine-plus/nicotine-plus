# COPYRIGHT (C) 2020-2024 Nicotine+ Contributors
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

import os
import sys

UINT32_LIMIT = 4294967295
UINT64_LIMIT = 18446744073709551615
FILE_SIZE_SUFFIXES = ["B", "KiB", "MiB", "GiB", "TiB", "PiB", "EiB", "ZiB", "YiB"]
PUNCTUATION = [  # ASCII and Unicode punctuation
    "!", '"', "#", "$", "%", "&", "'", "(", ")", "*", "+", ",", "-", ".", "/", ":", ";",
    "<", "=", ">", "?", "@", "[", "\\", "]", "^", "_", "`", "{", "|", "}", "~",
    "\u00A1", "\u00A7", "\u00AB", "\u00B6", "\u00B7", "\u00BB", "\u00BF", "\u037E", "\u0387",
    "\u055A", "\u055B", "\u055C", "\u055D", "\u055E", "\u055F", "\u0589", "\u058A", "\u05BE",
    "\u05C0", "\u05C3", "\u05C6", "\u05F3", "\u05F4", "\u0609", "\u060A", "\u060C", "\u060D",
    "\u061B", "\u061D", "\u061E", "\u061F", "\u066A", "\u066B", "\u066C", "\u066D", "\u06D4",
    "\u0700", "\u0701", "\u0702", "\u0703", "\u0704", "\u0705", "\u0706", "\u0707", "\u0708",
    "\u0709", "\u070A", "\u070B", "\u070C", "\u070D", "\u07F7", "\u07F8", "\u07F9", "\u0830",
    "\u0831", "\u0832", "\u0833", "\u0834", "\u0835", "\u0836", "\u0837", "\u0838", "\u0839",
    "\u083A", "\u083B", "\u083C", "\u083D", "\u083E", "\u085E", "\u0964", "\u0965", "\u0970",
    "\u09FD", "\u0A76", "\u0AF0", "\u0C77", "\u0C84", "\u0DF4", "\u0E4F", "\u0E5A", "\u0E5B",
    "\u0F04", "\u0F05", "\u0F06", "\u0F07", "\u0F08", "\u0F09", "\u0F0A", "\u0F0B", "\u0F0C",
    "\u0F0D", "\u0F0E", "\u0F0F", "\u0F10", "\u0F11", "\u0F12", "\u0F14", "\u0F3A", "\u0F3B",
    "\u0F3C", "\u0F3D", "\u0F85", "\u0FD0", "\u0FD1", "\u0FD2", "\u0FD3", "\u0FD4", "\u0FD9",
    "\u0FDA", "\u104A", "\u104B", "\u104C", "\u104D", "\u104E", "\u104F", "\u10FB", "\u1360",
    "\u1361", "\u1362", "\u1363", "\u1364", "\u1365", "\u1366", "\u1367", "\u1368", "\u1400",
    "\u166E", "\u169B", "\u169C", "\u16EB", "\u16EC", "\u16ED", "\u1735", "\u1736", "\u17D4",
    "\u17D5", "\u17D6", "\u17D8", "\u17D9", "\u17DA", "\u1800", "\u1801", "\u1802", "\u1803",
    "\u1804", "\u1805", "\u1806", "\u1807", "\u1808", "\u1809", "\u180A", "\u1944", "\u1945",
    "\u1A1E", "\u1A1F", "\u1AA0", "\u1AA1", "\u1AA2", "\u1AA3", "\u1AA4", "\u1AA5", "\u1AA6",
    "\u1AA8", "\u1AA9", "\u1AAA", "\u1AAB", "\u1AAC", "\u1AAD", "\u1B5A", "\u1B5B", "\u1B5C",
    "\u1B5D", "\u1B5E", "\u1B5F", "\u1B60", "\u1B7D", "\u1B7E", "\u1BFC", "\u1BFD", "\u1BFE",
    "\u1BFF", "\u1C3B", "\u1C3C", "\u1C3D", "\u1C3E", "\u1C3F", "\u1C7E", "\u1C7F", "\u1CC0",
    "\u1CC1", "\u1CC2", "\u1CC3", "\u1CC4", "\u1CC5", "\u1CC6", "\u1CC7", "\u1CD3", "\u2010",
    "\u2011", "\u2012", "\u2013", "\u2014", "\u2015", "\u2016", "\u2017", "\u2018", "\u2019",
    "\u201A", "\u201B", "\u201C", "\u201D", "\u201E", "\u201F", "\u2020", "\u2021", "\u2022",
    "\u2023", "\u2024", "\u2025", "\u2026", "\u2027", "\u2030", "\u2031", "\u2032", "\u2033",
    "\u2034", "\u2035", "\u2036", "\u2037", "\u2038", "\u2039", "\u203A", "\u203B", "\u203C",
    "\u203D", "\u203E", "\u203F", "\u2040", "\u2041", "\u2042", "\u2043", "\u2045", "\u2046",
    "\u2047", "\u2048", "\u2049", "\u204A", "\u204B", "\u204C", "\u204D", "\u204E", "\u204F",
    "\u2050", "\u2051", "\u2053", "\u2054", "\u2055", "\u2056", "\u2057", "\u2058", "\u2059",
    "\u205A", "\u205B", "\u205C", "\u205D", "\u205E", "\u207D", "\u207E", "\u208D", "\u208E",
    "\u2308", "\u2309", "\u230A", "\u230B", "\u2329", "\u232A", "\u2768", "\u2769", "\u276A",
    "\u276B", "\u276C", "\u276D", "\u276E", "\u276F", "\u2770", "\u2771", "\u2772", "\u2773",
    "\u2774", "\u2775", "\u27C5", "\u27C6", "\u27E6", "\u27E7", "\u27E8", "\u27E9", "\u27EA",
    "\u27EB", "\u27EC", "\u27ED", "\u27EE", "\u27EF", "\u2983", "\u2984", "\u2985", "\u2986",
    "\u2987", "\u2988", "\u2989", "\u298A", "\u298B", "\u298C", "\u298D", "\u298E", "\u298F",
    "\u2990", "\u2991", "\u2992", "\u2993", "\u2994", "\u2995", "\u2996", "\u2997", "\u2998",
    "\u29D8", "\u29D9", "\u29DA", "\u29DB", "\u29FC", "\u29FD", "\u2CF9", "\u2CFA", "\u2CFB",
    "\u2CFC", "\u2CFE", "\u2CFF", "\u2D70", "\u2E00", "\u2E01", "\u2E02", "\u2E03", "\u2E04",
    "\u2E05", "\u2E06", "\u2E07", "\u2E08", "\u2E09", "\u2E0A", "\u2E0B", "\u2E0C", "\u2E0D",
    "\u2E0E", "\u2E0F", "\u2E10", "\u2E11", "\u2E12", "\u2E13", "\u2E14", "\u2E15", "\u2E16",
    "\u2E17", "\u2E18", "\u2E19", "\u2E1A", "\u2E1B", "\u2E1C", "\u2E1D", "\u2E1E", "\u2E1F",
    "\u2E20", "\u2E21", "\u2E22", "\u2E23", "\u2E24", "\u2E25", "\u2E26", "\u2E27", "\u2E28",
    "\u2E29", "\u2E2A", "\u2E2B", "\u2E2C", "\u2E2D", "\u2E2E", "\u2E30", "\u2E31", "\u2E32",
    "\u2E33", "\u2E34", "\u2E35", "\u2E36", "\u2E37", "\u2E38", "\u2E39", "\u2E3A", "\u2E3B",
    "\u2E3C", "\u2E3D", "\u2E3E", "\u2E3F", "\u2E40", "\u2E41", "\u2E42", "\u2E43", "\u2E44",
    "\u2E45", "\u2E46", "\u2E47", "\u2E48", "\u2E49", "\u2E4A", "\u2E4B", "\u2E4C", "\u2E4D",
    "\u2E4E", "\u2E4F", "\u2E52", "\u2E53", "\u2E54", "\u2E55", "\u2E56", "\u2E57", "\u2E58",
    "\u2E59", "\u2E5A", "\u2E5B", "\u2E5C", "\u2E5D", "\u3001", "\u3002", "\u3003", "\u3008",
    "\u3009", "\u300A", "\u300B", "\u300C", "\u300D", "\u300E", "\u300F", "\u3010", "\u3011",
    "\u3014", "\u3015", "\u3016", "\u3017", "\u3018", "\u3019", "\u301A", "\u301B", "\u301C",
    "\u301D", "\u301E", "\u301F", "\u3030", "\u303D", "\u30A0", "\u30FB", "\uA4FE", "\uA4FF",
    "\uA60D", "\uA60E", "\uA60F", "\uA673", "\uA67E", "\uA6F2", "\uA6F3", "\uA6F4", "\uA6F5",
    "\uA6F6", "\uA6F7", "\uA874", "\uA875", "\uA876", "\uA877", "\uA8CE", "\uA8CF", "\uA8F8",
    "\uA8F9", "\uA8FA", "\uA8FC", "\uA92E", "\uA92F", "\uA95F", "\uA9C1", "\uA9C2", "\uA9C3",
    "\uA9C4", "\uA9C5", "\uA9C6", "\uA9C7", "\uA9C8", "\uA9C9", "\uA9CA", "\uA9CB", "\uA9CC",
    "\uA9CD", "\uA9DE", "\uA9DF", "\uAA5C", "\uAA5D", "\uAA5E", "\uAA5F", "\uAADE", "\uAADF",
    "\uAAF0", "\uAAF1", "\uABEB", "\uFD3E", "\uFD3F", "\uFE10", "\uFE11", "\uFE12", "\uFE13",
    "\uFE14", "\uFE15", "\uFE16", "\uFE17", "\uFE18", "\uFE19", "\uFE30", "\uFE31", "\uFE32",
    "\uFE33", "\uFE34", "\uFE35", "\uFE36", "\uFE37", "\uFE38", "\uFE39", "\uFE3A", "\uFE3B",
    "\uFE3C", "\uFE3D", "\uFE3E", "\uFE3F", "\uFE40", "\uFE41", "\uFE42", "\uFE43", "\uFE44",
    "\uFE45", "\uFE46", "\uFE47", "\uFE48", "\uFE49", "\uFE4A", "\uFE4B", "\uFE4C", "\uFE4D",
    "\uFE4E", "\uFE4F", "\uFE50", "\uFE51", "\uFE52", "\uFE54", "\uFE55", "\uFE56", "\uFE57",
    "\uFE58", "\uFE59", "\uFE5A", "\uFE5B", "\uFE5C", "\uFE5D", "\uFE5E", "\uFE5F", "\uFE60",
    "\uFE61", "\uFE62", "\uFE63", "\uFE64", "\uFE65", "\uFE66", "\uFE68", "\uFE6A", "\uFE6B",
    "\uFF01", "\uFF02", "\uFF03", "\uFF05", "\uFF06", "\uFF07", "\uFF08", "\uFF09", "\uFF0A",
    "\uFF0B", "\uFF0C", "\uFF0D", "\uFF0E", "\uFF0F", "\uFF1A", "\uFF1B", "\uFF1C", "\uFF1D",
    "\uFF1E", "\uFF1F", "\uFF20", "\uFF3B", "\uFF3C", "\uFF3D", "\uFF3F", "\uFF5B", "\uFF5C",
    "\uFF5D", "\uFF5E", "\uFF5F", "\uFF60", "\uFF61", "\uFF62", "\uFF63", "\uFF64", "\uFF65",
    "\U00010100", "\U00010101", "\U00010102", "\U0001039F", "\U000103D0", "\U0001056F", "\U00010857",
    "\U0001091F", "\U0001093F", "\U00010A50", "\U00010A51", "\U00010A52", "\U00010A53", "\U00010A54",
    "\U00010A55", "\U00010A56", "\U00010A57", "\U00010A58", "\U00010A7F", "\U00010AF0", "\U00010AF1",
    "\U00010AF2", "\U00010AF3", "\U00010AF4", "\U00010AF5", "\U00010AF6", "\U00010B39", "\U00010B3A",
    "\U00010B3B", "\U00010B3C", "\U00010B3D", "\U00010B3E", "\U00010B3F", "\U00010B99", "\U00010B9A",
    "\U00010B9B", "\U00010B9C", "\U00010EAD", "\U00010F55", "\U00010F56", "\U00010F57", "\U00010F58",
    "\U00010F59", "\U00010F86", "\U00010F87", "\U00010F88", "\U00010F89", "\U00011047", "\U00011048",
    "\U00011049", "\U0001104A", "\U0001104B", "\U0001104C", "\U0001104D", "\U000110BB", "\U000110BC",
    "\U000110BE", "\U000110BF", "\U000110C0", "\U000110C1", "\U00011140", "\U00011141", "\U00011142",
    "\U00011143", "\U00011174", "\U00011175", "\U000111C5", "\U000111C6", "\U000111C7", "\U000111C8",
    "\U000111CD", "\U000111DB", "\U000111DD", "\U000111DE", "\U000111DF", "\U00011238", "\U00011239",
    "\U0001123A", "\U0001123B", "\U0001123C", "\U0001123D", "\U000112A9", "\U0001144B", "\U0001144C",
    "\U0001144D", "\U0001144E", "\U0001144F", "\U0001145A", "\U0001145B", "\U0001145D", "\U000114C6",
    "\U000115C1", "\U000115C2", "\U000115C3", "\U000115C4", "\U000115C5", "\U000115C6", "\U000115C7",
    "\U000115C8", "\U000115C9", "\U000115CA", "\U000115CB", "\U000115CC", "\U000115CD", "\U000115CE",
    "\U000115CF", "\U000115D0", "\U000115D1", "\U000115D2", "\U000115D3", "\U000115D4", "\U000115D5",
    "\U000115D6", "\U000115D7", "\U00011641", "\U00011642", "\U00011643", "\U00011660", "\U00011661",
    "\U00011662", "\U00011663", "\U00011664", "\U00011665", "\U00011666", "\U00011667", "\U00011668",
    "\U00011669", "\U0001166A", "\U0001166B", "\U0001166C", "\U000116B9", "\U0001173C", "\U0001173D",
    "\U0001173E", "\U0001183B", "\U00011944", "\U00011945", "\U00011946", "\U000119E2", "\U00011A3F",
    "\U00011A40", "\U00011A41", "\U00011A42", "\U00011A43", "\U00011A44", "\U00011A45", "\U00011A46",
    "\U00011A9A", "\U00011A9B", "\U00011A9C", "\U00011A9E", "\U00011A9F", "\U00011AA0", "\U00011AA1",
    "\U00011AA2", "\U00011B00", "\U00011B01", "\U00011B02", "\U00011B03", "\U00011B04", "\U00011B05",
    "\U00011B06", "\U00011B07", "\U00011B08", "\U00011B09", "\U00011C41", "\U00011C42", "\U00011C43",
    "\U00011C44", "\U00011C45", "\U00011C70", "\U00011C71", "\U00011EF7", "\U00011EF8", "\U00011F43",
    "\U00011F44", "\U00011F45", "\U00011F46", "\U00011F47", "\U00011F48", "\U00011F49", "\U00011F4A",
    "\U00011F4B", "\U00011F4C", "\U00011F4D", "\U00011F4E", "\U00011F4F", "\U00011FFF", "\U00012470",
    "\U00012471", "\U00012472", "\U00012473", "\U00012474", "\U00012FF1", "\U00012FF2", "\U00016A6E",
    "\U00016A6F", "\U00016AF5", "\U00016B37", "\U00016B38", "\U00016B39", "\U00016B3A", "\U00016B3B",
    "\U00016B44", "\U00016E97", "\U00016E98", "\U00016E99", "\U00016E9A", "\U00016FE2", "\U0001BC9F",
    "\U0001DA87", "\U0001DA88", "\U0001DA89", "\U0001DA8A", "\U0001DA8B", "\U0001E95E", "\U0001E95F"
]
ILLEGALPATHCHARS = [
    # ASCII printable characters
    "?", ":", ">", "<", "|", "*", '"',

    # ASCII control characters
    "\u0000", "\u0001", "\u0002", "\u0003", "\u0004", "\u0005", "\u0006", "\u0007", "\u0008",
    "\u0009", "\u000A", "\u000B", "\u000C", "\u000D", "\u000E", "\u000F", "\u0010", "\u0011",
    "\u0012", "\u0013", "\u0014", "\u0015", "\u0016", "\u0017", "\u0018", "\u0019", "\u001A",
    "\u001B", "\u001C", "\u001D", "\u001E", "\u001F"
]
ILLEGALFILECHARS = ["\\", "/"] + ILLEGALPATHCHARS
LONG_PATH_PREFIX = "\\\\?\\"
REPLACEMENTCHAR = "_"
TRANSLATE_PUNCTUATION = str.maketrans(dict.fromkeys(PUNCTUATION, " "))


def clean_file(basename):

    for char in ILLEGALFILECHARS:
        if char in basename:
            basename = basename.replace(char, REPLACEMENTCHAR)

    # Filename can never end with a period or space on Windows machines
    basename = basename.rstrip(". ")

    if not basename:
        basename = REPLACEMENTCHAR

    return basename


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
        if char in path:
            path = path.replace(char, REPLACEMENTCHAR)

    path = "".join([drive, path])

    # Path can never end with a period or space on Windows machines
    path = path.rstrip(". ")

    return path


def encode_path(path, prefix=True):
    """Converts a file path to bytes for processing by the system.

    On Windows, also append prefix to enable extended-length path.
    """

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

    for suffix in FILE_SIZE_SUFFIXES:
        if number < 1024:
            if number > 999:
                return f"{number:.4g} {suffix}"

            return f"{number:.3g} {suffix}"

        number /= 1024

    return str(number)


def human_speed(speed):
    return _human_speed_or_size(speed) + "/s"


def human_size(filesize, unit=None):
    return _human_speed_or_size(filesize, unit)


def humanize(number):
    return f"{number:n}"


def factorize(filesize, base=1024):
    """Converts filesize string with a given unit into raw integer size,
    defaults to binary for "k", "m", "g" suffixes (KiB, MiB, GiB)"""

    if not filesize:
        return None, None

    filesize = filesize.lower()

    if filesize.endswith("b"):
        base = 1000  # Byte suffix detected, prepare to use decimal if necessary
        filesize = filesize[:-1]

    if filesize.endswith("i"):
        base = 1024  # Binary requested, stop using decimal
        filesize = filesize[:-1]

    if filesize.endswith("g"):
        factor = pow(base, 3)
        filesize = filesize[:-1]

    elif filesize.endswith("m"):
        factor = pow(base, 2)
        filesize = filesize[:-1]

    elif filesize.endswith("k"):
        factor = base
        filesize = filesize[:-1]

    else:
        factor = 1

    try:
        return int(float(filesize) * factor), factor
    except ValueError:
        return None, factor


def truncate_string_byte(string, byte_limit, encoding="utf-8", ellipsize=False):
    """Truncates a string to fit inside a byte limit."""

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
    """Removes quotes from the beginning and end of strings, and unescapes
    it."""

    string = string.encode("latin-1", "backslashreplace").decode("unicode-escape")

    try:
        if (string[0] == string[-1]) and string.startswith(("'", '"')):
            return string[1:-1]
    except IndexError:
        pass

    return string


def find_whole_word(word, text):
    """Returns start position of a whole word that is not in a subword."""

    if word not in text:
        return -1

    word_boundaries = [" "] + PUNCTUATION
    len_text = len(text)
    len_word = len(word)
    start = after = 0
    whole = False

    while not whole and start > -1:
        start = text.find(word, after)
        after = start + len_word

        whole = ((text[after] if after < len_text else " ") in word_boundaries
                 and (text[start - 1] if start > 0 else " ") in word_boundaries)

    return start if whole else -1


def censor_text(text, censored_patterns, filler="*"):

    for word in censored_patterns:
        word = str(word)
        text = text.replace(word, filler * len(word))

    return text


def execute_command(command, replacement=None, background=True, returnoutput=False,
                    hidden=False, placeholder="$"):
    """Executes a string with commands, with partial support for bash-style
    quoting and pipes.

    The different parts of the command should be separated by spaces, a double
    quotation mark can be used to embed spaces in an argument.
    Pipes can be created using the bar symbol (|).

    If background is false the function will wait for all the launched
    processes to end before returning.

    If hidden is true, any window created by the command will be hidden
    (on Windows).

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
    * echo $ | flite -t
    """

    # pylint: disable=consider-using-with

    from subprocess import PIPE, Popen

    # Example command: "C:\Program Files\WinAmp\WinAmp.exe" --xforce "--title=My Title" $ | flite -t
    if returnoutput:
        background = False

    command = command.strip()
    startupinfo = None

    if hidden and sys.platform == "win32":
        from subprocess import STARTF_USESHOWWINDOW, STARTUPINFO
        # Hide console window on Windows
        startupinfo = STARTUPINFO()
        startupinfo.dwFlags |= STARTF_USESHOWWINDOW

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
        if argument == "|":
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
            procs.append(Popen(subcommands[0], startupinfo=startupinfo, stdout=finalstdout))
        else:
            procs.append(Popen(subcommands[0], startupinfo=startupinfo, stdout=PIPE))

            for subcommand in subcommands[1:-1]:
                procs.append(Popen(subcommand, startupinfo=startupinfo, stdin=procs[-1].stdout,
                                   stdout=PIPE))

            procs.append(Popen(subcommands[-1], startupinfo=startupinfo, stdin=procs[-1].stdout,
                               stdout=finalstdout))

        if not background and not returnoutput:
            procs[-1].wait()

    except Exception as error:
        command = subcommands[len(procs)]
        command_no = len(procs) + 1
        num_commands = len(subcommands)
        raise RuntimeError(
            f"Problem while executing command {command} ({command_no} of "
            f"{num_commands}): {error}") from error

    if not returnoutput:
        return True

    return procs[-1].communicate()[0]


def _try_open_uri(uri):

    if sys.platform not in {"darwin", "win32"}:
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


def _open_path(path, is_folder=False, create_folder=False, create_file=False):
    """Currently used to either open a folder or play an audio file.

    Tries to run a user-specified command first, and falls back to the system
    default.
    """

    if path is None:
        return False

    try:
        from pynicotine.config import config

        path = os.path.abspath(path)
        path_encoded = encode_path(path)
        _path, separator, extension = path.rpartition(".")
        protocol_command = None
        protocol_handlers = config.sections["urls"]["protocols"]
        file_manager_command = config.sections["ui"]["filemanager"]

        if separator:
            from pynicotine.shares import FileTypes

            if "." + extension in protocol_handlers:
                protocol = "." + extension

            elif extension in FileTypes.AUDIO:
                protocol = "audio"

            elif extension in FileTypes.IMAGE:
                protocol = "image"

            elif extension in FileTypes.VIDEO:
                protocol = "video"

            elif extension in FileTypes.DOCUMENT:
                protocol = "document"

            elif extension in FileTypes.TEXT:
                protocol = "text"

            elif extension in FileTypes.ARCHIVE:
                protocol = "archive"

            else:
                protocol = None

            protocol_command = protocol_handlers.get(protocol)

        if not os.path.exists(path_encoded):
            if create_folder:
                os.makedirs(path_encoded)

            elif create_file:
                with open(path_encoded, "w", encoding="utf-8"):
                    # Create empty file
                    pass
            else:
                raise FileNotFoundError("File path does not exist")

        if is_folder and "$" in file_manager_command:
            execute_command(file_manager_command, path)

        elif protocol_command:
            execute_command(protocol_command, path)

        elif sys.platform == "win32":
            os.startfile(path_encoded)  # pylint: disable=no-member

        elif sys.platform == "darwin":
            execute_command("open $", path)

        else:
            _try_open_uri("file:///" + path)

    except Exception as error:
        from pynicotine.logfacility import log
        log.add(_("Cannot open file path %(path)s: %(error)s"), {"path": path, "error": error})
        return False

    return True


def open_file_path(file_path, create_file=False):
    return _open_path(path=file_path, create_file=create_file)


def open_folder_path(folder_path, create_folder=False):
    return _open_path(path=folder_path, is_folder=True, create_folder=create_folder)


def open_uri(uri):
    """Open a URI in an external (web) browser.

    The given argument has to be a properly formed URI including the
    scheme (fe. HTTP).
    """

    from pynicotine.config import config

    try:
        # Situation 1, user defined a way of handling the protocol
        protocol = uri[:uri.find(":")]

        if not protocol.startswith(".") and protocol not in {"audio", "image", "video", "document", "text", "archive"}:
            protocol_handlers = config.sections["urls"]["protocols"]
            protocol_command = protocol_handlers.get(protocol + "://") or protocol_handlers.get(protocol)

            if protocol_command:
                execute_command(protocol_command, uri)
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


def load_file(file_path, load_func, use_old_file=False):

    try:
        if use_old_file:
            file_path = f"{file_path}.old"

        elif os.path.isfile(encode_path(f"{file_path}.old")):
            file_path_encoded = encode_path(file_path)

            if not os.path.isfile(file_path_encoded):
                raise OSError("*.old file is present but main file is missing")

            if os.path.getsize(file_path_encoded) <= 0:
                # Empty files should be considered broken/corrupted
                raise OSError("*.old file is present but main file is empty")

        return load_func(file_path)

    except Exception as error:
        from pynicotine.logfacility import log
        log.add(_("Something went wrong while reading file %(filename)s: %(error)s"),
                {"filename": file_path, "error": error})

        if not use_old_file:
            # Attempt to load data from .old file
            log.add(_("Attempting to load backup of file %s"), file_path)
            return load_file(file_path, load_func, use_old_file=True)

    return None


def write_file_and_backup(path, callback, protect=False):

    from pynicotine.logfacility import log

    path_encoded = encode_path(path)
    path_old_encoded = encode_path(f"{path}.old")

    # Back up old file to path.old
    try:
        if os.path.exists(path_encoded) and os.stat(path_encoded).st_size > 0:
            os.replace(path_encoded, path_old_encoded)

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

            # Force write to file immediately in case of hard shutdown
            file_handle.flush()
            os.fsync(file_handle.fileno())

        log.add_debug("Backed up and saved file %s", path)

    except Exception as error:
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


# Debugging #


def debug(*args):
    """Prints debugging info."""

    from pynicotine.logfacility import log

    truncated_args = [arg[:200] if isinstance(arg, str) else arg for arg in args]
    log.add("*" * 8, truncated_args)


def strace(function):
    """Decorator for debugging."""

    from itertools import chain
    from pynicotine.logfacility import log

    def newfunc(*args, **kwargs):
        name = function.__name__
        log.add(f"{name}({', '.join(repr(x) for x in chain(args, list(kwargs.values())))})")
        retvalue = function(*args, **kwargs)
        log.add(f"{name}({', '.join(repr(x) for x in chain(args, list(kwargs.values())))}): {repr(retvalue)}")
        return retvalue

    return newfunc
