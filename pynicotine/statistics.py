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

import time

from pynicotine.config import config
from pynicotine.events import events


class Statistics:

    def __init__(self):
        self.session_stats = {}
        events.connect("start", self._start)

    def _start(self):

        # Only populate total since date on first run
        if (not config.sections["statistics"]["since_timestamp"]
                and config.sections["statistics"] == config.defaults["statistics"]):
            config.sections["statistics"]["since_timestamp"] = int(time.time())

        for stat_id in config.defaults["statistics"]:
            self.session_stats[stat_id] = 0 if stat_id != "since_timestamp" else int(time.time())

        for stat_id in config.defaults["statistics"]:
            self.update_ui(stat_id)

    def append_stat_value(self, stat_id, stat_value):

        self.session_stats[stat_id] += stat_value
        config.sections["statistics"][stat_id] += stat_value
        self.update_ui(stat_id)

    def update_ui(self, stat_id):

        session_stat_value = self.session_stats[stat_id]
        total_stat_value = config.sections["statistics"][stat_id]

        events.emit("update-stat-value", stat_id, session_stat_value, total_stat_value)

    def reset_stats(self):

        for stat_id in config.defaults["statistics"]:
            stat_value = 0 if stat_id != "since_timestamp" else int(time.time())
            self.session_stats[stat_id] = config.sections["statistics"][stat_id] = stat_value

            self.update_ui(stat_id)
