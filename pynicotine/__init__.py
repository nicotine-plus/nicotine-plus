# COPYRIGHT (C) 2020-2022 Nicotine+ Contributors
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
import io
import multiprocessing
import os
import sys

from pynicotine.config import config
from pynicotine.core import core
from pynicotine.i18n import LOCALE_PATH
from pynicotine.i18n import apply_translations
from pynicotine.logfacility import log


def check_arguments():
    """ Parse command line arguments specified by the user """

    parser = argparse.ArgumentParser(
        description=_("Graphical client for the Soulseek peer-to-peer network"),
        epilog=_("Website: %s") % config.website_url, add_help=False
    )

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
        help=_("alternative directory for user data and plugins")
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
        "-v", "--version", action="version", version=f"{config.application_name} {config.version}",
        help=_("display version and exit")
    )

    # Disables critical error dialog; used for integration tests
    parser.add_argument("--ci-mode", action="store_true", help=argparse.SUPPRESS)

    args = parser.parse_args()
    multi_instance = False

    if args.config:
        config.filename = args.config

        # Since a custom config was specified, allow another instance of the application to open
        multi_instance = True

    if args.user_data:
        config.data_dir = args.user_data

    core.bindip = args.bindip
    core.port = args.port

    return args.headless, args.hidden, args.ci_mode, args.rescan, multi_instance


def check_python_version():

    # Require minimum Python version
    python_version = (3, 6)

    if sys.version_info < python_version:
        return _("""You are using an unsupported version of Python (%(old_version)s).
You should install Python %(min_version)s or newer.""") % {
            "old_version": ".".join(map(str, sys.version_info[:3])),
            "min_version": ".".join(map(str, python_version))
        }

    return None


def set_up_python():

    is_frozen = getattr(sys, "frozen", False)

    # Always use UTF-8 for print()
    if sys.stdout is not None:
        sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding="utf-8", line_buffering=True)

    if is_frozen:
        # Set up paths for frozen binaries (Windows and macOS)
        executable_folder = os.path.dirname(sys.executable)
        os.environ["SSL_CERT_FILE"] = os.path.join(executable_folder, "lib/cert.pem")

        # Support file scanning process in frozen binaries
        multiprocessing.freeze_support()

    # Frozen binaries only support fork (if not on Windows)
    if sys.platform != "win32" and is_frozen:
        start_method = "fork"
    else:
        start_method = "spawn"

    multiprocessing.set_start_method(start_method)


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
            msg.append(str(i))
        log.add("\n".join(msg))


def rescan_shares():

    error = core.shares.rescan_shares(use_thread=False)

    if error:
        log.add("--------------------------------------------------")
        log.add(_("Failed to scan shares. Please close other Nicotine+ instances and try again."))
        return 1

    return 0


def run():
    """ Run application and return its exit code """

    set_up_python()
    rename_process(b"nicotine")

    headless, hidden, ci_mode, rescan, multi_instance = check_arguments()
    error = check_python_version()

    if error:
        log.add(error)
        return 1

    # Dump tracebacks for C modules (in addition to pure Python code)
    try:
        import faulthandler
        faulthandler.enable()

    except Exception as error:
        log.add(f"Faulthandler module could not be enabled. Error: {error}")

    core.init_components(enable_cli=True)

    if not os.path.isdir(LOCALE_PATH):
        log.add("Translation files (.mo) are unavailable, using default English strings")

    if rescan:
        return rescan_shares()

    # Initialize GTK-based GUI
    if not headless:
        from pynicotine import gtkgui as application
        exit_code = application.run(hidden, ci_mode, multi_instance)

        if exit_code is not None:
            return exit_code

    # Run without a GUI
    from pynicotine import headless as application
    return application.run()


apply_translations()
