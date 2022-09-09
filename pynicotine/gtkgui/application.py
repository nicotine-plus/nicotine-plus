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
import sys
import threading

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

        # Show errors in the GUI from here on
        self.init_exception_handler()

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

    def run(self):
        return self.instance.run()

    def network_callback(self, msgs):
        # High priority to ensure there are no delays
        GLib.idle_add(self.core.network_event, msgs[:], priority=GLib.PRIORITY_HIGH_IDLE)

    def init_exception_handler(self):

        sys.excepthook = self.on_critical_error

        if hasattr(threading, "excepthook"):
            threading.excepthook = self.on_critical_error_threading
            return

        # Workaround for Python <= 3.7
        init_thread = threading.Thread.__init__

        def init_thread_excepthook(self, *args, **kwargs):

            init_thread(self, *args, **kwargs)
            run_thread = self.run

            def run_with_excepthook(*args2, **kwargs2):
                try:
                    run_thread(*args2, **kwargs2)
                except Exception:
                    GLib.idle_add(sys.excepthook, *sys.exc_info())

            self.run = run_with_excepthook

        threading.Thread.__init__ = init_thread_excepthook

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

    def on_critical_error_response(self, _dialog, response_id, data):

        loop, error = data

        if response_id == 2:
            from pynicotine.gtkgui.utils import copy_text
            from pynicotine.utils import open_uri

            copy_text(error)
            open_uri(config.issue_tracker_url)
            return

        loop.quit()
        self.core.quit()

    def on_critical_error(self, exc_type, exc_value, exc_traceback):

        if self.ci_mode:
            self.core.quit()
            raise exc_value

        from traceback import format_tb

        # Check if exception occurred in a plugin
        if self.core.pluginhandler is not None:
            traceback = exc_traceback

            while True:
                if not traceback.tb_next:
                    break

                filename = traceback.tb_frame.f_code.co_filename

                for plugin_name in self.core.pluginhandler.enabled_plugins:
                    path = self.core.pluginhandler.get_plugin_path(plugin_name)

                    if filename.startswith(path):
                        self.core.pluginhandler.show_plugin_error(
                            plugin_name, exc_type, exc_value, exc_traceback)
                        return

                traceback = traceback.tb_next

        # Show critical error dialog
        from pynicotine.gtkgui.widgets.dialogs import OptionDialog

        loop = GLib.MainLoop()
        error = ("\n\nNicotine+ Version: %s\nGTK Version: %s\nPython Version: %s\n\n"
                 "Type: %s\nValue: %s\nTraceback: %s" %
                 (config.version, config.gtk_version, config.python_version, exc_type,
                  exc_value, ''.join(format_tb(exc_traceback))))

        OptionDialog(
            parent=self.instance.get_active_window(),
            title=_("Critical Error"),
            message=_("Nicotine+ has encountered a critical error and needs to exit. "
                      "Please copy the following message and include it in a bug report:") + error,
            first_button=_("_Quit Nicotine+"),
            second_button=_("_Copy & Report Bug"),
            callback=self.on_critical_error_response,
            callback_data=(loop, error)
        ).show()

        # Keep dialog open if error occurs on startup
        loop.run()

        raise exc_value

    @staticmethod
    def _on_critical_error_threading(args):
        raise args.exc_value

    def on_critical_error_threading(self, args):
        """ Exception that originated in a thread.
        Raising an exception here calls sys.excepthook(), which in turn shows an error dialog. """

        GLib.idle_add(self._on_critical_error_threading, args)

    def on_shutdown(self, *_args):
        if self.frame is not None:
            self.frame.on_shutdown()
