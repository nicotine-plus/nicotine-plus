# COPYRIGHT (C) 2021-2022 Nicotine+ Team
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

import time

from pynicotine.config import config
from pynicotine.logfacility import log


class Application:

    def __init__(self, core, ci_mode):

        self.core = core
        self.ci_mode = ci_mode

        config.load_config()
        log.log_levels = set(["download", "upload"] + config.sections["logging"]["debugmodes"])

    def run(self):

        connect_ready = self.core.start(self)

        if not connect_ready and not self.ci_mode:
            return 1

        connect_success = self.core.connect()

        if not connect_success and not self.ci_mode:
            return 1

        while not self.core.shutdown:
            time.sleep(0.2)

        config.write_configuration()

    def show_scan_progress(self):
        pass

    def set_scan_progress(self, value):
        pass

    def set_scan_indeterminate(self):
        pass

    def hide_scan_progress(self):
        pass

    def invalid_password(self):
        pass

    def server_login(self):
        pass

    def set_away_mode(self, is_away):
        pass

    def set_connection_stats(self, msg):
        pass

    def server_disconnect(self):
        pass

    def quit(self):
        pass
