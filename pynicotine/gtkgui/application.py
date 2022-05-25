# COPYRIGHT (C) 2020-2022 Nicotine+ Team
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


class Application(Gtk.Application):

    def __init__(self, core, tray_icon, start_hidden, bindip, port, ci_mode, multi_instance):

        super().__init__(application_id=config.application_id)
        GLib.set_application_name(config.application_name)
        GLib.set_prgname(config.application_id)

        if multi_instance:
            self.set_flags(Gio.ApplicationFlags.NON_UNIQUE)

        self.core = core
        self.frame = None
        self.tray_icon = tray_icon
        self.start_hidden = start_hidden
        self.bindip = bindip
        self.port = port
        self.ci_mode = ci_mode

        try:
            Gtk.ListStore.insert_with_valuesv

        except AttributeError:
            # GTK 4 replacement
            Gtk.ListStore.insert_with_valuesv = Gtk.ListStore.insert_with_values  # pylint: disable=no-member

    def network_callback(self, msgs):
        # High priority to ensure there are no delays
        GLib.idle_add(self.core.network_event, msgs, priority=GLib.PRIORITY_HIGH_IDLE)

    def do_startup(self):  # pylint:disable=arguments-differ

        Gtk.Application.do_startup(self)

        from pynicotine.gtkgui.frame import NicotineFrame
        self.frame = NicotineFrame(self, self.core, self.tray_icon, self.start_hidden,
                                   self.bindip, self.port, self.ci_mode)

        self.core.start(ui_callback=self.frame, network_callback=self.network_callback)

    def do_activate(self):  # pylint:disable=arguments-differ

        active_window = self.get_active_window()

        if active_window:
            # Show the window of the running application instance
            active_window.present()
            return

        if self.frame:
            self.frame.init_window()

        if config.sections["server"]["auto_connect_startup"]:
            self.core.connect()

    def do_shutdown(self):  # pylint:disable=arguments-differ

        if self.frame:
            self.frame.on_shutdown()

        Gtk.Application.do_shutdown(self)
