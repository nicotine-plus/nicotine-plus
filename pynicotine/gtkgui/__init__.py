# COPYRIGHT (C) 2021-2024 Nicotine+ Contributors
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

from pynicotine.logfacility import log


def get_default_gtk_version():

    if sys.platform in {"darwin", "win32"}:
        return "4"

    try:
        from gi.repository import GLib
        from gi.repository import Gio

        try:
            dbus_proxy = Gio.DBusProxy.new_for_bus_sync(
                bus_type=Gio.BusType.SESSION,
                flags=Gio.DBusProxyFlags.NONE,
                info=None,
                name="org.a11y.Bus",
                object_path="/org/a11y/bus",
                interface_name="org.freedesktop.DBus.Properties"
            )

            # If screen reader is enabled, use GTK 3 until treeviews have been ported to
            # Gtk.ColumnView. Gtk.TreeView doesn't support screen readers in GTK 4.
            if dbus_proxy.Get("(ss)", "org.a11y.Status", "IsEnabled"):
                log.add_debug("Screen reader enabled, using GTK 3 for improved accessibility")
                return "3"

        except GLib.Error:
            # Service not available
            pass

    except ModuleNotFoundError:
        pass

    return "4"


def check_gtk_version(gtk_api_version):

    is_gtk3_supported = sys.platform not in {"darwin", "win32"}

    if gtk_api_version == "3" and not is_gtk3_supported:
        log.add("WARNING: Using GTK 3, which might not work properly on Windows and macOS. "
                "GTK 4 will be required in the future.")

    # Require minor version of GTK
    if gtk_api_version == "4":
        pygobject_version = (3, 42, 1)
    else:
        gtk_api_version = "3"
        pygobject_version = (3, 26, 1)

    try:
        import gi
        gi.check_version(pygobject_version)

    except (ImportError, ValueError):
        if gtk_api_version == "4" and is_gtk3_supported:
            return check_gtk_version(gtk_api_version="3")

        return _("Cannot find %s, please install it.") % ("PyGObject >=" + ".".join(str(x) for x in pygobject_version))

    try:
        gi.require_version("Gtk", f"{gtk_api_version}.0")

    except ValueError:
        if gtk_api_version == "4" and is_gtk3_supported:
            return check_gtk_version(gtk_api_version="3")

        return _("Cannot find %s, please install it.") % f"GTK >={gtk_api_version}"

    from gi.repository import Gtk

    if sys.platform == "win32":
        # Ensure all Windows-specific APIs are available
        gi.require_version("GdkWin32", f"{gtk_api_version}.0")
        from gi.repository import GdkWin32  # noqa: F401  # pylint:disable=no-name-in-module,unused-import

    if hasattr(gi, "_ossighelper"):
        # PyGObject sets up a signal helper that wakes up the GLib mainloop when the application
        # receives OS signals. Disable it, since its use of socketpairs currently causes crashes
        # on Windows while a proxy is enabled. We always keep the loop active anyway
        # (on_process_thread_events in application.py).
        gi._ossighelper._wakeup_fd_is_active = True  # pylint:disable=protected-access

    gtk_version = f"{Gtk.get_major_version()}.{Gtk.get_minor_version()}.{Gtk.get_micro_version()}"
    log.add(_("Loading %(program)s %(version)s"), {"program": "GTK", "version": gtk_version})

    return None


def run(hidden, ci_mode, isolated_mode, multi_instance):
    """Run Nicotine+ GTK GUI."""

    if getattr(sys, "frozen", False):
        # Set up paths for frozen binaries (Windows and macOS)
        executable_folder = os.path.dirname(sys.executable)

        os.environ["GTK_EXE_PREFIX"] = executable_folder
        os.environ["GTK_DATA_PREFIX"] = executable_folder
        os.environ["GTK_PATH"] = executable_folder
        os.environ["XDG_DATA_DIRS"] = os.path.join(executable_folder, "share")
        os.environ["FONTCONFIG_FILE"] = os.path.join(executable_folder, "share", "fonts", "fonts.conf")
        os.environ["FONTCONFIG_PATH"] = os.path.join(executable_folder, "share", "fonts")
        os.environ["GDK_PIXBUF_MODULE_FILE"] = os.path.join(executable_folder, "lib", "pixbuf-loaders.cache")
        os.environ["GI_TYPELIB_PATH"] = os.path.join(executable_folder, "lib", "typelibs")
        os.environ["GSETTINGS_SCHEMA_DIR"] = os.path.join(executable_folder, "lib", "schemas")

    if sys.platform == "win32":
        # 'win32' PangoCairo backend on Windows is too slow, use 'fontconfig' instead
        os.environ["PANGOCAIRO_BACKEND"] = "fontconfig"

        # Disable client-side decorations when header bar is disabled
        os.environ["GTK_CSD"] = "0"

        # Use Cairo software rendering due to flickering issues in the GPU renderer (#2859).
        # Reevaluate when the new GPU renderers are stable:
        # https://blog.gtk.org/2024/01/28/new-renderers-for-gtk/
        os.environ["GDK_DISABLE"] = "gl,vulkan"
        os.environ["GSK_RENDERER"] = "cairo"

    elif sys.platform == "darwin":
        # Older GL renderer is still faster on macOS for now
        os.environ["GSK_RENDERER"] = "gl"

    error = check_gtk_version(gtk_api_version=os.environ.get("NICOTINE_GTK_VERSION", get_default_gtk_version()))

    if error:
        log.add(error)
        return 1

    from gi.repository import Gdk

    if not ci_mode and Gdk.Display.get_default() is None:
        log.add(_("No graphical environment available, using headless (no GUI) mode"))
        return None

    from pynicotine.gtkgui.application import Application
    return Application(hidden, ci_mode, isolated_mode, multi_instance).run()
