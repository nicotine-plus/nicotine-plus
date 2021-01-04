# COPYRIGHT (C) 2020 Nicotine+ Team
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

from pynicotine.gtkgui.utils import human_size
from pynicotine.gtkgui.utils import load_ui_elements


class Statistics:

    def __init__(self, frame, config):

        self.frame = frame
        self.config = config

        load_ui_elements(self, os.path.join(self.frame.gui_dir, "ui", "dialogs", "statistics.ui"))

        self.StatisticsDialog.set_transient_for(frame.MainWindow)

        self.StatisticsDialog.connect("destroy", self.hide)
        self.StatisticsDialog.connect("destroy-event", self.hide)
        self.StatisticsDialog.connect("delete-event", self.hide)
        self.StatisticsDialog.connect("delete_event", self.hide)

        # Initialize stats
        for stat_id in self.config.defaults["statistics"]:
            self.update_stat_value(stat_id, 0)

    def update_stat_value(self, stat_id, session_value):

        total_value = self.config.sections["statistics"][stat_id]

        if stat_id == "downloaded_size" or stat_id == "uploaded_size":
            session_value = human_size(session_value)
            total_value = human_size(total_value)
        else:
            session_value = str(session_value)
            total_value = str(total_value)

        self.__dict__[stat_id + "_session"].set_text(session_value)
        self.__dict__[stat_id + "_total"].set_text(total_value)

    def on_clear_statistics(self, *args):
        self.frame.np.statistics.clear_stats()

    def hide(self, w=None, event=None):
        self.StatisticsDialog.hide()
        return True

    def show(self):
        self.StatisticsDialog.show()
