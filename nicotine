#!/usr/bin/env python3
# COPYRIGHT (C) 2020 Lene Preuss <lene.preuss@gmail.com>
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2008-2011 Quinox <quinox@users.sf.net>
# COPYRIGHT (C) 2006-2008 eL_vErDe <gandalf@le-vert.net>
# COPYRIGHT (C) 2006-2009 Daelstorm <daelstorm@gmail.com>
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
Nicotine+ Launcher.
"""

import platform
import sys
from gettext import gettext as _

from pynicotine.logfacility import log
from pynicotine.utils import ApplyTranslation
from pynicotine.utils import GetUserDirectories

# Setting gettext and locale
ApplyTranslation()

# Detect if we're running on Windows
win32 = platform.system().startswith("Win")


def checkenv():

    # Require Python 3.6 or newer
    try:
        assert sys.version_info[:2] >= (3, 6), '.'.join(
            map(str, sys.version_info[:3])
        )
    except AssertionError as e:
        return _("""You're using an unsupported version of Python (%s).
You should install Python 3.7 or newer.""") % (e)

    # Require GTK+ >= 3
    try:
        import gi
    except ModuleNotFoundError:
        return _("Cannot find pygobject, please install it.")
    else:
        try:
            gi.require_version('Gtk', '3.0')
        except ValueError as e:
            return _("""You're using an unsupported version of GTK (%s).
You should install GTK 3.0 or newer.""") % e

    # Require PyGTK
    try:
        from gi.repository import Gtk  # noqa: F401
    except ModuleNotFoundError:
        return _("Cannot import the Gtk module. Bad install of the python-gobject module?")

    # Require pynicotine
    try:
        import pynicotine  # noqa: F401
    except ImportError as e:  # noqa: F841
        return _("""Can not find Nicotine+ modules.
Perhaps they're installed in a directory which is not
in an interpreter's module search path.
(there could be a version mismatch between
what version of python was used to build the Nicotine
binary package and what you try to run Nicotine+ with).""")

    # Check for optionnal GeoIP
    try:
        import GeoIP  # noqa: F401
    except ImportError:
        try:
            import _GeoIP  # noqa: F401
        except ImportError:
            msg = _("""Nicotine+ supports a country code blocker.
This requires a (GPL'ed) library called GeoIP. You can find it here:
C library:       http://www.maxmind.com/app/c
Python bindings: http://www.maxmind.com/app/python
(the python bindings require the C library)""")
            log.addwarning(msg)

    # Windows specific checks
    if win32:

        # dbhash might be a good choice
        try:
            import dbm.bsd  # noqa: F401
        except Exception:
            log.addwarning(
                _("Warning: the Berkeley DB module, dbhash, " +
                  "could not be loaded."))

        # win32file is used to handle hidden files
        try:
            import win32file  # noqa: F401
        except Exception:
            msg = _("""Nicotine+ supports hidden files attributes on windows.
This requires a python module called pypiwin32. You can find it here:
https://pypi.python.org/pypi/pypiwin32""")
            log.addwarning(msg)

    return None


def version():
    try:
        import pynicotine.utils
        print((_("Nicotine+ version %s" % pynicotine.utils.version)))
    except ImportError:
        print(_("Cannot find the pynicotine.utils module."))


def usage():
    print((_("""Nicotine+ is a Soulseek client.
Usage: nicotine [OPTION]...
  -c file, --config=file      Use non-default configuration file
  -p dir,  --plugins=dir      Use non-default directory for plugins
  -t,      --enable-trayicon  Enable the tray icon
  -d,      --disable-trayicon Disable the tray icon
  -h,      --help             Show help and exit
  -s,      --hidden           Start the program hidden so only the tray icon is shown
  -b ip,   --bindip=ip        Bind sockets to the given IP (useful for VPN)
  -l port, --port=port        Listen on the given port. Overrides the portrange configuration
  -v,      --version          Display version and exit""")))


def renameprocess(newname, debug=False):

    errors = []

    # Renaming ourselves for ps et al.
    try:
        import procname
        procname.setprocname(newname)
    except Exception:
        errors.append("Failed procname module")

    # Renaming ourselves for pkill et al.
    try:
        import ctypes
        # GNU/Linux style
        libc = ctypes.CDLL('libc.so.6')
        libc.prctl(15, newname, 0, 0, 0)
    except Exception:
        errors.append("Failed GNU/Linux style")

    try:
        import dl
        # FreeBSD style
        libc = dl.open('/lib/libc.so.6')
        libc.call('setproctitle', newname + '\0')
    except Exception:
        errors.append("Failed FreeBSD style")

    if debug and errors:
        msg = [_("Errors occured while trying to change process name:")]
        for i in errors:
            msg.append("%s" % (i,))
        log.addwarning('\n'.join(msg))


def run():

    renameprocess('nicotine')

    import getopt
    import os.path
    try:
        opts, args = getopt.getopt(sys.argv[1:],
                                   "hc:p:tdvswb:",
                                   [
                                        "help",  # noqa: E126
                                        "config=",
                                        "plugins=",
                                        "profile",
                                        "enable-trayicon",
                                        "disable-trayicon",
                                        "version",
                                        "hidden",
                                        "bindip=",
                                        "port="
                                   ]  # noqa: E126
                                   )
    except getopt.GetoptError:
        # print help information and exit
        usage()
        sys.exit(2)

    if win32:
        try:
            data_dir = os.path.join(os.environ['APPDATA'], 'nicotine')
        except KeyError:
            data_dir, x = os.path.split(sys.argv[0])

        config = os.path.join(data_dir, "config", "config")
    else:
        config_dir, data_dir = GetUserDirectories()
        config = os.path.join(config_dir, 'config')

    plugins = os.path.join(data_dir, 'plugins')

    profile = 0
    trayicon = 1
    hidden = False
    bindip = None
    port = None

    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
            sys.exit()
        if o in ("-c", "--config"):
            config = a
        if o in ("-p", "--plugins"):
            plugins = a
        if o in ("-b", "--bindip"):
            bindip = a
        if o in ("-l", "--port"):
            port = a
        if o == "--profile":
            profile = 1
        if o in ("-t", "--enable-trayicon"):
            trayicon = 1
        if o in ("-d", "--disable-trayicon"):
            trayicon = 0
        if o in ('-s', '--hidden'):
            hidden = True
        if o in ("-v", "--version"):
            version()
            sys.exit()

    result = checkenv()

    if result is None:
        from pynicotine.gtkgui import frame

        app = frame.MainApp(data_dir, config, plugins, trayicon, hidden, bindip, port)

        if profile:

            import cProfile

            dumpfile = os.path.expanduser(config) + ".profile"
            profiler = cProfile.Profile()

            log.add(_("Starting using the profiler (saving dump to %s)") % dumpfile)

            profiler.enable()
            app.MainLoop()
            profiler.disable()

            profiler.dump_stats(dumpfile)
        else:
            app.MainLoop()
    else:
        print(result)


if __name__ == '__main__':
    try:
        run()
    except SystemExit:
        raise
    except Exception:
        import traceback
        traceback.print_exc()
