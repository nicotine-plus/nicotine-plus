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

import os

from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk

from pynicotine.config import config

GTK_API_VERSION = Gtk.get_major_version()
GTK_GUI_DIR = os.path.normpath(os.path.dirname(os.path.realpath(__file__)))


class Application:

    def __init__(self, core, start_hidden, ci_mode, multi_instance):

        self.instance = Gtk.Application(application_id=config.application_id)
        GLib.set_application_name(config.application_name)
        GLib.set_prgname(config.application_id)

        if multi_instance:
            self.instance.set_flags(Gio.ApplicationFlags.NON_UNIQUE)

        self.core = core
        self.frame = None
        self.start_hidden = start_hidden
        self.ci_mode = ci_mode

        self.instance.connect("activate", self.on_activate)
        self.instance.connect("shutdown", self.on_shutdown)

        try:
            Gtk.ListStore.insert_with_valuesv

        except AttributeError:
            # GTK 4 replacement
            Gtk.ListStore.insert_with_valuesv = Gtk.ListStore.insert_with_values  # pylint: disable=no-member

    def network_callback(self, msgs):
        # High priority to ensure there are no delays
        GLib.idle_add(self.core.network_event, msgs[:], priority=GLib.PRIORITY_HIGH_IDLE)

    def run(self):
        return self.instance.run()

    def on_activate(self, *_args):

        active_window = self.instance.get_active_window()

        if active_window:
            # Show the window of the running application instance
            active_window.present()
            return

        from pynicotine.gtkgui.frame import NicotineFrame

        self.frame = NicotineFrame(self.instance, self.core, self.start_hidden, self.ci_mode)
        self.core.start(ui_callback=self.frame, network_callback=self.network_callback)
        self.frame.init_window()

        if config.sections["server"]["auto_connect_startup"]:
            self.core.connect()

    def on_shutdown(self, *_args):
        if self.frame is not None:
            self.frame.on_shutdown()
