# SPDX-FileCopyrightText: 2023 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

from pynicotine.pluginsystem import BasePlugin


class Plugin(BasePlugin):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.commands = {
            "sample": {
                "description": "Sample command description",
                "disable": ["cli"],
                "aliases": ["demo"],
                "callback": self.sample_command,
                "callback_private_chat": self.sample_command,
                "parameters": ["<choice1|choice2>", "<second argument>", "[something else..]"],
                "parameters_chatroom": ["<choiceA|choiceB>", "<some thing>", "<something else..>"]
            }
        }

    def sample_command(self, args, **_unused):

        one, two, three = self.split_args(args, 3)

        self.output(f"Hello, testing 3 arguments: >{one}<  >{two}<  >{three}<\n")
