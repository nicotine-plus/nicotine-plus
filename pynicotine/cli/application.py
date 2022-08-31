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

import sys
import threading
import time

from collections import deque

from pynicotine.config import config
from pynicotine.logfacility import log


class Application:

    def __init__(self, core, ci_mode):

        self.init_exception_handler()

        self.core = core
        self.ci_mode = ci_mode
        self.network_msgs = deque()

        config.load_config()
        log.log_levels = set(["download", "upload"] + config.sections["logging"]["debugmodes"])

    def run(self):

        self.core.start(self, self.network_callback)
        connect_success = self.core.connect()

        if not connect_success and not self.ci_mode:
            # Network error, exit code 1
            return 1

        # Main loop, process messages from networking thread
        while not self.core.shutdown:
            if self.network_msgs:
                msgs = []

                while self.network_msgs:
                    msgs.append(self.network_msgs.popleft())

                self.core.network_event(msgs)

            time.sleep(1 / 60)

        # Shut down with exit code 0 (success)
        config.write_configuration()
        return 0

    def network_callback(self, msgs):
        self.network_msgs.extend(msgs)

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
                    sys.excepthook(*sys.exc_info())

            self.run = run_with_excepthook

        threading.Thread.__init__ = init_thread_excepthook

    def on_critical_error(self, _exc_type, exc_value, _exc_traceback):
        self.core.quit()
        raise exc_value

    @staticmethod
    def on_critical_error_threading(args):
        raise args.exc_value

    def show_scan_progress(self):
        # Not implemented
        pass

    def set_scan_progress(self, value):
        # Not implemented
        pass

    def set_scan_indeterminate(self):
        # Not implemented
        pass

    def hide_scan_progress(self):
        # Not implemented
        pass

    def invalid_password(self):
        # Not implemented
        pass

    def server_login(self):
        # Not implemented
        pass

    def set_away_mode(self, is_away):
        # Not implemented
        pass

    def set_connection_stats(self, msg):
        # Not implemented
        pass

    def server_disconnect(self):
        # Not implemented
        pass

    def setup(self):
        # Not implemented
        pass

    def quit(self):
        # Not implemented
        pass
