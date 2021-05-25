# COPYRIGHT (C) 2020-2021 Nicotine+ Team
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

from gi.repository import Gdk
from gi.repository import Gtk

from pynicotine.config import config
from pynicotine.gtkgui.utils import load_ui_elements
from pynicotine.gtkgui.widgets.dialogs import generic_dialog
from pynicotine.gtkgui.widgets.dialogs import option_dialog
from pynicotine.utils import human_size


class Statistics:

    def __init__(self, frame):

        self.frame = frame

        load_ui_elements(self, os.path.join(self.frame.gui_dir, "ui", "dialogs", "statistics.ui"))

        self.StatisticsDialog = generic_dialog(
            parent=frame.MainWindow,
            content_box=self.Main,
            quit_callback=self.hide,
            title=_("Transfer Statistics"),
            width=450
        )

        # Initialize stats
        for stat_id in config.defaults["statistics"]:
            self.update_stat_value(stat_id, 0)

    def update_stat_value(self, stat_id, session_value):

        total_value = config.sections["statistics"][stat_id]

        if stat_id == "downloaded_size" or stat_id == "uploaded_size":
            session_value = human_size(session_value)
            total_value = human_size(total_value)
        else:
            session_value = str(session_value)
            total_value = str(total_value)

        getattr(self, stat_id + "_session").set_text(session_value)
        getattr(self, stat_id + "_total").set_text(total_value)

    def on_reset_statistics_response(self, dialog, response_id, data):

        dialog.destroy()

        if response_id == Gtk.ResponseType.OK:
            self.frame.np.statistics.reset_stats()

    def on_reset_statistics(self, *args):

        option_dialog(
            parent=self.StatisticsDialog,
            title=_('Reset Transfer Statistics?'),
            message=_('Are you sure you wish to reset transfer statistics?'),
            callback=self.on_reset_statistics_response
        )

    def hide(self, *args):
        self.StatisticsDialog.hide()
        return True

    def show(self):

        self.StatisticsDialog.present_with_time(Gdk.CURRENT_TIME)

        if Gtk.get_major_version() == 3:
            self.StatisticsDialog.get_window().set_functions(
                Gdk.WMFunction.RESIZE | Gdk.WMFunction.MOVE | Gdk.WMFunction.CLOSE
            )
