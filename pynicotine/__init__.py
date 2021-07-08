# COPYRIGHT (C) 2020-2021 Nicotine+ Team
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

import argparse
import importlib.util
import sys

from pynicotine.i18n import apply_translation


def check_arguments():
    """ Parse command line arguments specified by the user """

    from pynicotine.config import config
    parser = argparse.ArgumentParser(description=_("Nicotine+ is a Soulseek client"), add_help=False)

    # Visible arguments
    parser.add_argument(
        "-h", "--help", action="help",
        help=_("show this help message and exit")
    )
    parser.add_argument(
        "-c", "--config", metavar=_("file"),
        help=_("use non-default configuration file")
    )
    parser.add_argument(
        "-u", "--user-data", metavar=_("dir"),
        help=_("use non-default user data directory for e.g. list of downloads")
    )
    parser.add_argument(
        "-p", "--plugins", metavar=_("dir"),
        help=_("use non-default directory for plugins")
    )
    parser.add_argument(
        "-t", "--enable-trayicon", action="store_true",
        help=_("enable the tray icon")
    )
    parser.add_argument(
        "-d", "--disable-trayicon", action="store_true",
        help=_("disable the tray icon")
    )
    parser.add_argument(
        "-s", "--hidden", action="store_true",
        help=_("start the program without showing window")
    )
    parser.add_argument(
        "-b", "--bindip", metavar=_("ip"),
        help=_("bind sockets to the given IP (useful for VPN)")
    )
    parser.add_argument(
        "-l", "--port", metavar=_("port"), type=int,
        help=_("listen on the given port")
    )
    parser.add_argument(
        "-r", "--rescan", action="store_true",
        help=_("rescan shared files")
    )
    parser.add_argument(
        "-n", "--headless", action="store_true",
        help=_("start the program in headless mode (no GUI)")
    )
    parser.add_argument(
        "-v", "--version", action="version", version="Nicotine+ %s" % config.version,
        help=_("display version and exit")
    )

    # Disables critical error dialog; used for integration tests
    parser.add_argument("--ci-mode", action="store_true", help=argparse.SUPPRESS)

    args = parser.parse_args()
    trayicon = None
    multi_instance = False

    if args.config:
        config.filename = args.config

        # Since a custom config was specified, allow another instance of Nicotine+ to open
        multi_instance = True

    if args.user_data:
        config.data_dir = args.user_data

    if args.plugins:
        config.plugin_dir = args.plugins

    if args.enable_trayicon:
        trayicon = True

    if args.disable_trayicon:
        trayicon = False

    return trayicon, args.headless, args.hidden, args.bindip, args.port, args.ci_mode, args.rescan, multi_instance


def check_core_dependencies():

    # Require Python >= 3.6
    try:
        assert sys.version_info[:2] >= (3, 6), '.'.join(
            map(str, sys.version_info[:3])
        )

    except AssertionError as error:
        return _("""You are using an unsupported version of Python (%(old_version)s).
You should install Python %(min_version)s or newer.""") % {
            "old_version": error,
            "min_version": "3.6"
        }

    # Require gdbm or semidbm, for faster loading of shelves
    if not importlib.util.find_spec("_gdbm") and \
            not importlib.util.find_spec("semidbm"):
        return _("Cannot find %(option1)s or %(option2)s, please install either one.") % {
            "option1": "gdbm",
            "option2": "semidbm"
        }

    return None


def rescan_shares():

    from collections import deque

    from pynicotine.config import config
    from pynicotine.shares import Shares

    config.load_config()

    shares = Shares(None, config, deque())
    error = shares.rescan_public_shares(thread=False)

    if config.sections["transfers"]["enablebuddyshares"]:
        error = shares.rescan_buddy_shares(thread=False)

    if error:
        print("--------------------------------------------------")
        print(_("Failed to scan shares. If Nicotine+ is currently running, please close the program before scanning."))
        return 1

    return 0


def run_headless(core, ci_mode):
    """ Run Nicotine+ in headless (no GUI) mode """

    import signal
    import time

    from pynicotine.config import config
    from pynicotine.logfacility import log

    config.load_config()
    log.log_levels = set(["download", "upload"] + config.sections["logging"]["debugmodes"])

    for signal_type in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signal_type, core.quit)

    connect_ready = core.start()

    if not connect_ready and not ci_mode:
        return 1

    connect_success = core.connect()

    if not connect_success and not ci_mode:
        return 1

    while not core.shutdown:
        time.sleep(0.2)

    config.write_configuration()
    return 0


def run():
    """ Run Nicotine+ and return its exit code """

    # Support file scanning process in frozen Windows and macOS binaries
    if getattr(sys, 'frozen', False):
        import multiprocessing
        multiprocessing.freeze_support()

    # Require pynicotine module
    if not importlib.util.find_spec("pynicotine"):
        print("""Cannot find Nicotine+ modules.
Perhaps they're installed in a directory which is not
in an interpreter's module search path.
(there could be a version mismatch between
what version of Python was used to build the Nicotine
binary package and what you try to run Nicotine+ with).""")
        return 1

    from pynicotine.utils import rename_process
    rename_process(b'nicotine')

    trayicon, headless, hidden, bindip, port, ci_mode, rescan, multi_instance = check_arguments()
    error = check_core_dependencies()

    if error:
        print(error)
        return 1

    if rescan:
        return rescan_shares()

    # Initialize core
    from pynicotine.pynicotine import NicotineCore
    core = NicotineCore(bindip, port)

    # Run without a GUI
    if headless:
        return run_headless(core, ci_mode)

    # Initialize GTK-based GUI
    from pynicotine.gtkgui import run_gui
    return run_gui(core, trayicon, hidden, bindip, port, ci_mode, multi_instance)


apply_translation()
