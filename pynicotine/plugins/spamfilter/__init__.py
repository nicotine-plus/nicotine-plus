# SPDX-FileCopyrightText: 2020-2023 Nicotine+ Contributors
# SPDX-FileCopyrightText: 2009 daelstorm <daelstorm@gmail.com>
# SPDX-FileCopyrightText: 2009 quinox <quinox@users.sf.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from pynicotine.pluginsystem import BasePlugin
from pynicotine.pluginsystem import returncode


class Plugin(BasePlugin):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.settings = {
            "minlength": 200,
            "maxlength": 400,
            "maxdiffcharacters": 10,
            "badprivatephrases": []
        }
        self.metasettings = {
            "minlength": {
                "description": "The minimum length of a line before it's considered as ASCII spam",
                "type": "integer"
            },
            "maxdiffcharacters": {
                "description": "The maximum number of different characters that is still considered ASCII spam",
                "type": "integer"
            },
            "maxlength": {
                "description": "The maximum length of a line before it's considered as spam.",
                "type": "integer"
            },
            "badprivatephrases": {
                "description": "Filter chat messages containing phrase:",
                "type": "list string"
            }
        }

    def loaded_notification(self):

        self.log("A line should be at least %s long with a maximum of %s different characters "
                 "before it's considered ASCII spam.",
                 (self.settings["minlength"], self.settings["maxdiffcharacters"]))

    def check_phrases(self, user, line):

        for phrase in self.settings["badprivatephrases"]:
            if line.lower().find(phrase) > -1:
                self.log("Blocked spam from %s: %s", (user, line))
                return returncode["zap"]

        return None

    def incoming_public_chat_event(self, room, user, line):

        if len(line) >= self.settings["minlength"] and len(set(line)) < self.settings["maxdiffcharacters"]:
            self.log('Filtered ASCII spam from "%s" in room "%s"', (user, room))
            return returncode["zap"]

        if len(line) > self.settings["maxlength"]:
            self.log('Filtered really long line (%s characters) from "%s" in room "%s"', (len(line), user, room))
            return returncode["zap"]

        return self.check_phrases(user, line)

    def incoming_private_chat_event(self, user, line):
        return self.check_phrases(user, line)
