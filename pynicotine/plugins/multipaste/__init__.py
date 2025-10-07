# SPDX-FileCopyrightText: 2020-2023 Nicotine+ Contributors
# SPDX-FileCopyrightText: 2009 daelstorm <daelstorm@gmail.com>
# SPDX-FileCopyrightText: 2008 quinox <quinox@users.sf.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from pynicotine.pluginsystem import BasePlugin
from pynicotine.pluginsystem import returncode


class Plugin(BasePlugin):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.settings = {
            "maxpubliclines": 4,
            "maxprivatelines": 8
        }
        self.metasettings = {
            "maxpubliclines": {
                "description": "The maximum number of lines that will be pasted in public",
                "type": "int"
            },
            "maxprivatelines": {
                "description": "The maximum number of lines that will be pasted in private",
                "type": "int"
            }
        }

    def outgoing_private_chat_event(self, user, line):

        lines = [x for x in line.splitlines() if x]

        if len(lines) > 1:
            if len(lines) > self.settings["maxprivatelines"]:
                self.log("Posting %s of %s lines.", (self.settings["maxprivatelines"], len(lines)))
            else:
                self.log("Splitting lines.")
            for split_line in lines[:self.settings["maxprivatelines"]]:
                self.send_private(user, split_line)

            return returncode["zap"]

        return None

    def outgoing_public_chat_event(self, room, line):

        lines = [x for x in line.splitlines() if x]

        if len(lines) > 1:
            if len(lines) > self.settings["maxpubliclines"]:
                self.log("Posting %s of %s lines.", (self.settings["maxpubliclines"], len(lines)))
            else:
                self.log("Splitting lines.")
            for split_line in lines[:self.settings["maxpubliclines"]]:
                self.send_public(room, split_line)

            return returncode["zap"]

        return None
