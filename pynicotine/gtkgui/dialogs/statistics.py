# COPYRIGHT (C) 2020-2024 Nicotine+ Contributors
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

from pynicotine.core import core
from pynicotine.events import events
from pynicotine.gtkgui.widgets import ui
from pynicotine.gtkgui.widgets.dialogs import Dialog
from pynicotine.gtkgui.widgets.dialogs import OptionDialog
from pynicotine.utils import human_size
from pynicotine.utils import humanize


class Statistics(Dialog):

    def __init__(self, application):

        (
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
            self.uploaded_size_session_label,
            self.uploaded_size_total_label
        ) = ui.load(scope=self, path="dialogs/statistics.ui")

        self.stat_id_labels = {
            "completed_downloads": {
                "session": self.completed_downloads_session_label,
                "total": self.completed_downloads_total_label
            },
            "completed_uploads": {
                "session": self.completed_uploads_session_label,
                "total": self.completed_uploads_total_label
            },
            "downloaded_size": {
                "session": self.downloaded_size_session_label,
                "total": self.downloaded_size_total_label
            },
            "uploaded_size": {
                "session": self.uploaded_size_session_label,
                "total": self.uploaded_size_total_label
            },
            "since_timestamp": {
                "total": self.since_timestamp_total_label
            }
        }

        super().__init__(
            parent=application.window,
            content_box=self.container,
            show_callback=self.on_show,
            title=_("Transfer Statistics"),
            width=425
        )

        events.connect("update-stat", self.update_stat)

    def update_stat(self, stat_id, session_value, total_value):

        current_stat_id_labels = self.stat_id_labels.get(stat_id)

        if not current_stat_id_labels:
            return

        if not self.widget.get_visible():
            return

        if stat_id in {"downloaded_size", "uploaded_size"}:
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
            session_label = current_stat_id_labels["session"]

            if session_label.get_text() != session_value:
                session_label.set_text(session_value)

        if total_value is not None:
            total_label = current_stat_id_labels["total"]

            if total_label.get_text() != total_value:
                total_label.set_text(total_value)

    def on_reset_statistics_response(self, *_args):
        core.statistics.reset_stats()

    def on_reset_statistics(self, *_args):

        OptionDialog(
            parent=self,
            title=_("Reset Transfer Statistics?"),
            message=_("Do you really want to reset transfer statistics?"),
            destructive_response_id="ok",
            callback=self.on_reset_statistics_response
        ).present()

    def on_close(self, *_args):
        self.close()

    def on_show(self, *_args):
        core.statistics.update_stats()
