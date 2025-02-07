# COPYRIGHT (C) 2020-2025 Nicotine+ Contributors
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

__application_name__ = "Nicotine+"
__application_id__ = "org.nicotine_plus.Nicotine"
__version__ = "3.3.8rc2"
__author__ = "Nicotine+ Team"
__copyright__ = """© 2004–2025 Nicotine+ Contributors
© 2003–2004 Nicotine Contributors
© 2001–2003 PySoulSeek Contributors"""
__website_url__ = "https://nicotine-plus.org"
__privileges_url__ = "https://www.slsknet.org/qtlogin.php?username=%s"
__port_checker_url__ = "https://www.slsknet.org/porttest.php?port=%s"
__issue_tracker_url__ = "https://github.com/nicotine-plus/nicotine-plus/issues"
__translations_url__ = "https://nicotine-plus.org/doc/TRANSLATIONS"

import io
import os
import sys

from pynicotine.config import config
from pynicotine.core import core
from pynicotine.i18n import LOCALE_PATH
from pynicotine.i18n import apply_translations
from pynicotine.logfacility import log


def check_arguments():
    """Parse command line arguments specified by the user."""

    import argparse

    parser = argparse.ArgumentParser(
        prog="nicotine", description=_("Graphical client for the Soulseek peer-to-peer network"),
        epilog=_("Website: %s") % __website_url__, add_help=False
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
        "-v", "--version", action="version", version=f"{__application_name__} {__version__}",
        help=_("display version and exit")
    )

    # Disables critical error dialog; used for integration tests
    parser.add_argument("--ci-mode", action="store_true", help=argparse.SUPPRESS)

    # Disables features that require external applications, useful for e.g. Docker containers
    parser.add_argument("--isolated", action="store_true", help=argparse.SUPPRESS)

    args = parser.parse_args()
    multi_instance = False

    if args.config:
        config.set_config_file(args.config)

        # Since a custom config was specified, allow another instance of the application to open
        multi_instance = True

    if args.user_data:
        config.set_data_folder(args.user_data)

    core.cli_interface_address = args.bindip
    core.cli_listen_port = args.port

    return args.headless, args.hidden, args.ci_mode, args.isolated, args.rescan, multi_instance


def check_python_version():

    # Require minimum Python version
    python_version = (3, 6)

    if sys.version_info < python_version:
        return _("""You are using an unsupported version of Python (%(old_version)s).
You should install Python %(min_version)s or newer.""") % {
            "old_version": ".".join(str(x) for x in sys.version_info[:3]),
            "min_version": ".".join(str(x) for x in python_version)
        }

    return None


def set_up_python():

    is_frozen = getattr(sys, "frozen", False)

    # Always use UTF-8 for print()
    if sys.stdout is not None:
        sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding="utf-8", line_buffering=True)

    if is_frozen:
        import multiprocessing

        # Set up paths for frozen binaries (Windows and macOS)
        executable_folder = os.path.dirname(sys.executable)
        os.environ["SSL_CERT_FILE"] = os.path.join(executable_folder, "lib/cert.pem")

        # Support file scanning process in frozen binaries
        multiprocessing.freeze_support()

        # Prioritize dlls in the 'lib' subfolder over system dlls, to avoid issues with conflicting dlls
        if sys.platform == "win32":
            import ctypes
            ctypes.windll.kernel32.SetDllDirectoryW(os.path.join(executable_folder, "lib"))


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

    exit_code = 0

    if not core.shares.rescan_shares(use_thread=False):
        log.add("--------------------------------------------------")
        log.add(_("Failed to scan shares. Please close other Nicotine+ instances and try again."))

        exit_code = 1

    core.quit()
    return exit_code


def run():
    """Run application and return its exit code."""

    set_up_python()
    rename_process(b"nicotine")

    headless, hidden, ci_mode, isolated_mode, rescan, multi_instance = check_arguments()
    error = check_python_version()

    if error:
        print(error)
        return 1

    core.init_components(
        enabled_components={"cli", "shares"} if rescan else None,
        isolated_mode=isolated_mode
    )

    # Dump tracebacks for C modules (in addition to pure Python code)
    try:
        import faulthandler
        faulthandler.enable()

    except Exception as error:
        log.add(f"Faulthandler module could not be enabled. Error: {error}")

    if not os.path.isdir(LOCALE_PATH):
        log.add("Translation files (.mo) are unavailable, using default English strings")

    if rescan:
        return rescan_shares()

    # Initialize GTK-based GUI
    if not headless:
        from pynicotine import gtkgui as application
        exit_code = application.run(hidden, ci_mode, isolated_mode, multi_instance)

        if exit_code is not None:
            return exit_code

    # Run without a GUI
    from pynicotine import headless as application
    return application.run()


apply_translations()
