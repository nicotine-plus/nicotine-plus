# SPDX-FileCopyrightText: 2026 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

from pynicotine.pluginsystem import BasePlugin


class Plugin(BasePlugin):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.actions = {
            "show_upload_statistics": {
                "label": "Upload Statistics",
                "callback": self.show_upload_statistics
            },
            "export_upload_statistics": {
                "label": "Export Upload Statistics",
                "callback": self.export_upload_statistics
            }
        }

    def show_upload_statistics(self):
        pass

    def export_upload_statistics(self):
        pass

    def enable_export(self):
        self.enable_action("export_upload_statistics")

    def disable_export(self):
        self.disable_action("export_upload_statistics")
