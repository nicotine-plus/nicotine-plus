# SPDX-FileCopyrightText: 2021-2026 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

from pynicotine.pluginsystem import BasePlugin


class Plugin(BasePlugin):
    """File Chooser Example."""

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.settings = {
            "file": "/home/example/file.pdf",
            "folder": "/home/example/folder",
            "image": "/home/example/image.jpg",
        }
        self.metasettings = {
            "file": {
                "description": "Select a file",
                "group": "File Locations",
                "type": "file",
                "chooser": "file"},
            "folder": {
                "description": "Select a folder",
                "group": "File Locations",
                "type": "file",
                "chooser": "folder"},
            "image": {
                "description": "Select an image",
                "group": "File Locations",
                "type": "file",
                "chooser": "image"},
        }
