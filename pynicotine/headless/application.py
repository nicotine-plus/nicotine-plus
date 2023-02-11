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
import time

from pynicotine.cli import cli
from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.logfacility import log


class Application:

    def __init__(self):

        sys.excepthook = self.exception_hook

        for log_level in ("download", "upload"):
            log.add_log_level(log_level, is_permanent=False)

        for event_name, callback in (
            ("confirm-quit", self.on_confirm_quit),
            ("shares-unavailable", self.on_shares_unavailable)
        ):
            events.connect(event_name, callback)

    def run(self):

        core.start()
        core.connect()

        # Main loop, process events from threads 20 times per second
        while not core.shutdown:
            events.process_thread_events()
            time.sleep(0.05)

        # Shut down with exit code 0 (success)
        config.write_configuration()
        return 0

    def exception_hook(self, _exc_type, exc_value, _exc_traceback):
        core.quit()
        raise exc_value

    def on_confirm_quit_response(self, user_input):
        if user_input.lower().startswith("y"):
            core.quit()

    def on_confirm_quit(self, _remember):
        cli.prompt("Do you really want to quit Nicotine+ (Y/N)?: ", callback=self.on_confirm_quit_response)

    def on_shares_unavailable_response(self, user_input):

        if user_input == "test":
            core.shares.rescan_shares()
            return

        log.add("no")

    def on_shares_unavailable(self, _shares):
        cli.prompt("Enter some text: ", callback=self.on_shares_unavailable_response)
