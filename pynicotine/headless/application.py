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

from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.logfacility import log


class Application:

    def __init__(self):

        sys.excepthook = self.exception_hook

        for log_level in ("download", "upload"):
            log.add_log_level(log_level, is_permanent=False)

    def run(self):

        core.start()
        core.connect()

        # Main loop, process events from threads
        while not core.shutdown:
            events.process_thread_events()
            time.sleep(1 / 60)

        # Shut down with exit code 0 (success)
        config.write_configuration()
        return 0

    def exception_hook(self, _exc_type, exc_value, _exc_traceback, *_unused):
        core.quit()
        raise exc_value
