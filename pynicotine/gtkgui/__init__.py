# COPYRIGHT (C) 2021-2022 Nicotine+ Contributors
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


def check_gui_dependencies():

    # Defaults for different operating systems
    components = {
        "gtk": {"win32": '3', "darwin": '3'},
        "libadwaita": {"win32": '0', "darwin": '0'}
    }

    if os.getenv("NICOTINE_GTK_VERSION") is None:
        os.environ["NICOTINE_GTK_VERSION"] = components.get("gtk").get(sys.platform, '3')

    if os.getenv("NICOTINE_LIBADWAITA") is None:
        os.environ["NICOTINE_LIBADWAITA"] = components.get("libadwaita").get(sys.platform, '0')

    # Require minor version of GTK
    if os.getenv("NICOTINE_GTK_VERSION") == '4':
        gtk_version = (4, 6, 6)
        pygobject_version = (3, 40, 0)
    else:
        gtk_version = pygobject_version = (3, 18, 0)

    try:
        import gi
        gi.check_version(pygobject_version)

    except (ImportError, ValueError):
        return _("Cannot find %s, please install it.") % ("pygobject >= " + '.'.join(map(str, pygobject_version)))

    try:
        api_version = (gtk_version[0], 0)
        gi.require_version('Gtk', '.'.join(map(str, api_version)))

    except ValueError:
        return _("Cannot find %s, please install it.") % ("GTK " + str(gtk_version[0]))

    try:
        from gi.repository import Gtk

    except ImportError:
        return _("Cannot import the Gtk module. Bad install of the python-gobject module?")

    if Gtk.check_version(*gtk_version):
        return _("You are using an unsupported version of GTK %(major_version)s. You should install "
                 "GTK %(complete_version)s or newer.") % {
            "major_version": gtk_version[0],
            "complete_version": '.'.join(map(str, gtk_version))}

    try:
        if gtk_version[0] == 4 and os.getenv("NICOTINE_LIBADWAITA") == '1':
            gi.require_version('Adw', '1')

            from gi.repository import Adw
            Adw.init()

    except (ImportError, ValueError):
        pass

    return None


def run_gui(core, trayicon, hidden, bindip, port, ci_mode, multi_instance):
    """ Run Nicotine+ GTK GUI """

    if getattr(sys, 'frozen', False):
        # Set up paths for frozen binaries (Windows and macOS)
        executable_folder = os.path.dirname(sys.executable)
        resources_folder = executable_folder

        if sys.platform == "darwin":
            resources_folder = os.path.abspath(os.path.join(executable_folder, "..", "Resources"))

        os.environ["XDG_DATA_DIRS"] = os.path.join(resources_folder, "share")
        os.environ["FONTCONFIG_FILE"] = os.path.join(resources_folder, "share/fonts/fonts.conf")
        os.environ["FONTCONFIG_PATH"] = os.path.join(resources_folder, "share/fonts")
        os.environ["GDK_PIXBUF_MODULE_FILE"] = os.path.join(executable_folder, "lib/pixbuf-loaders.cache")
        os.environ["GI_TYPELIB_PATH"] = os.path.join(executable_folder, "lib/typelibs")
        os.environ["GSETTINGS_SCHEMA_DIR"] = os.path.join(executable_folder, "lib/schemas")

    if sys.platform == "win32":
        # 'win32' PangoCairo backend on Windows is too slow, use 'fontconfig' instead
        os.environ["PANGOCAIRO_BACKEND"] = "fontconfig"

    from pynicotine.logfacility import log
    error = check_gui_dependencies()

    if error:
        log.add(error)
        return 1

    from gi.repository import Gdk

    if not ci_mode and Gdk.Display.get_default() is None:
        log.add(_("No graphical environment available, using headless (no GUI) mode"))
        return None

    from pynicotine.gtkgui.application import Application
    return Application(core, trayicon, hidden, bindip, port, ci_mode, multi_instance).run()
