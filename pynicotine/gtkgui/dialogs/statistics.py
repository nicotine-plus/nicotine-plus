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

from pynicotine.config import config
from pynicotine.gtkgui.widgets.dialogs import dialog_hide
from pynicotine.gtkgui.widgets.dialogs import dialog_show
from pynicotine.gtkgui.widgets.dialogs import generic_dialog
from pynicotine.gtkgui.widgets.dialogs import OptionDialog
from pynicotine.gtkgui.widgets.ui import UserInterface
from pynicotine.utils import human_size


class Statistics(UserInterface):

    def __init__(self, frame, core):

        super().__init__("ui/dialogs/statistics.ui")

        self.frame = frame
        self.core = core
        self.dialog = generic_dialog(
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

        if stat_id in ("downloaded_size", "uploaded_size"):
            session_value = human_size(session_value)
            total_value = human_size(total_value)
        else:
            session_value = str(session_value)
            total_value = str(total_value)

        getattr(self, stat_id + "_session").set_text(session_value)
        getattr(self, stat_id + "_total").set_text(total_value)

    def on_reset_statistics_response(self, dialog, response_id, _data):

        dialog.destroy()

        if response_id == 2:
            self.core.statistics.reset_stats()

    def on_reset_statistics(self, *_args):

        OptionDialog(
            parent=self.dialog,
            title=_('Reset Transfer Statistics?'),
            message=_('Do you really want to reset transfer statistics?'),
            callback=self.on_reset_statistics_response
        ).show()

    def hide(self, *_args):
        dialog_hide(self.dialog)
        return True

    def show(self):
        dialog_show(self.dialog)
