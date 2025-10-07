# SPDX-FileCopyrightText: 2021-2023 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

from pynicotine.pluginsystem import BasePlugin


class Plugin(BasePlugin):
    """Radio Button/Dropdown Example."""

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.settings = {
            "player_radio": 2,                # id, starts from 0
            "player_dropdown": "Clementine"   # can be either string or id starting from 0
        }
        self.metasettings = {
            "player_radio": {
                "description": "Choose an audio player",
                "type": "radio",
                "options": (
                    "Exaile",
                    "Audacious",
                    "Clementine"
                )
            },
            "player_dropdown": {
                "description": "Choose an audio player",
                "type": "dropdown",
                "options": (
                    "Exaile",
                    "Audacious",
                    "Clementine"
                )
            }
        }
