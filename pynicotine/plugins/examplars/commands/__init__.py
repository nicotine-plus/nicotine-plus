# SPDX-FileCopyrightText: 2023 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

from pynicotine.pluginsystem import BasePlugin


class Plugin(BasePlugin):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.commands = {
            "sample": {
                "aliases": ["demo"],
                "description": "Sample command description",
                "disable": ["private_chat"],
                "callback": self.sample_command,
                "callback_private_chat": self.sample_command,
                "parameters": ["<choice1|choice2>", "<something..>"],
                "parameters_chatroom": ["<choice55|choice2>"]
            }
        }

    def sample_command(self, _args, **_unused):
        self.output("Hello")
