# COPYRIGHT (C) 2021 Nicotine+ Team
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


def check_gui_dependencies():

    # Require GTK+ >= 3.18
    try:
        import gi

    except ImportError:
        return _("Cannot find %s, please install it.") % "pygobject"

    else:
        try:
            version = '4.0' if os.getenv("NICOTINE_GTK_VERSION") == '4' else '3.0'
            gi.require_version('Gtk', version)

        except ValueError:
            return _("""You are using an unsupported version of GTK.
You should install GTK %s or newer.""") % "3.18"

    try:
        from gi.repository import Gtk  # noqa: F401

    except ImportError:
        return _("Cannot import the Gtk module. Bad install of the python-gobject module?")

    return None


def run_gui(network_processor, trayicon, hidden, bindip, port, ci_mode, multi_instance):
    """ Run Nicotine+ GTK GUI """

    error = check_gui_dependencies()

    if error:
        print(error)
        return 1

    from pynicotine.gtkgui.frame import Application
    return Application(network_processor, trayicon, hidden, bindip, port, ci_mode, multi_instance).run()
