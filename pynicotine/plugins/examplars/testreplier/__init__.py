# SPDX-FileCopyrightText: 2020-2023 Nicotine+ Contributors
# SPDX-FileCopyrightText: 2008-2010 quinox <quinox@users.sf.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from random import choice
from pynicotine.pluginsystem import BasePlugin, ResponseThrottle


class Plugin(BasePlugin):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.settings = {
            "replies": ["Test failed."]
        }
        self.metasettings = {
            "replies": {
                "description": "Replies:",
                "type": "list string"
            }
        }

        self.throttle = ResponseThrottle(self.core, self.human_name)

    def incoming_public_chat_event(self, room, user, line):

        if line.lower() != "test":
            return

        if self.throttle.ok_to_respond(room, user, line):
            self.throttle.responded()
            self.send_public(room, choice(self.settings["replies"]).lstrip("!"))
