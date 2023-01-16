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

import time

from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.gtkgui.widgets.dialogs import Dialog
from pynicotine.gtkgui.widgets.dialogs import OptionDialog
from pynicotine.gtkgui.widgets.ui import UserInterface
from pynicotine.utils import human_size
from pynicotine.utils import humanize


class Statistics(Dialog):

    def __init__(self, application):

        ui_template = UserInterface(scope=self, path="dialogs/statistics.ui")
        (
            self.close_button,
            self.completed_downloads_session_label,
            self.completed_downloads_total_label,
            self.completed_uploads_session_label,
            self.completed_uploads_total_label,
            self.container,
            self.current_session_label,
            self.downloaded_size_session_label,
            self.downloaded_size_total_label,
            self.reset_button,
            self.since_timestamp_total_label,
            self.started_downloads_session_label,
            self.started_downloads_total_label,
            self.started_uploads_session_label,
            self.started_uploads_total_label,
            self.uploaded_size_session_label,
            self.uploaded_size_total_label
        ) = ui_template.widgets

        super().__init__(
            parent=application.window,
            content_box=self.container,
            buttons_start=(self.close_button,),
            buttons_end=(self.reset_button,),
            default_button=self.close_button,
            title=_("Transfer Statistics"),
            width=450,
            resizable=False,
            close_destroy=False,
            show_title_buttons=False
        )

        events.connect("update-stat-value", self.update_stat_value)

        for stat_id in config.defaults["statistics"]:
            core.statistics.update_ui(stat_id)

    def update_stat_value(self, stat_id, session_value, total_value):

        if stat_id in ("downloaded_size", "uploaded_size"):
            session_value = human_size(session_value)
            total_value = human_size(total_value)

        elif stat_id == "since_timestamp":
            session_value = None
            total_value = (_("Total Since %(date)s") % {
                "date": time.strftime("%x", time.localtime(total_value))} if total_value > 0 else None)

        else:
            session_value = humanize(session_value)
            total_value = humanize(total_value)

        if session_value is not None:
            getattr(self, f"{stat_id}_session_label").set_text(session_value)

        if total_value is not None:
            getattr(self, f"{stat_id}_total_label").set_text(total_value)

    def on_reset_statistics_response(self, _dialog, response_id, _data):
        if response_id == 2:
            core.statistics.reset_stats()

    def on_reset_statistics(self, *_args):

        OptionDialog(
            parent=self,
            title=_("Reset Transfer Statistics?"),
            message=_("Do you really want to reset transfer statistics?"),
            callback=self.on_reset_statistics_response
        ).show()

    def on_close(self, *_args):
        self.close()
