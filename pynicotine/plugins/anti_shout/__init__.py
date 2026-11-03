# SPDX-FileCopyrightText: 2020-2023 Nicotine+ Contributors
# SPDX-FileCopyrightText: 2009 quinox <quinox@users.sf.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from pynicotine.pluginsystem import BasePlugin


class Plugin(BasePlugin):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.settings = {
            "maxscore": 0.6,
            "minlength": 10
        }
        self.metasettings = {
            "maxscore": {
                "description": "The maximum ratio of capitals before converting",
                "type": "float", "minimum": 0, "maximum": 1, "stepsize": 0.1
            },
            "minlength": {
                "description": "Lines shorter than this will be ignored", "type": "integer",
                "minimum": 0
            }
        }

    @staticmethod
    def capitalize(text):

        # Dont alter words that look like protocol links (fe http://, ftp://)
        if text.find("://") > -1:
            return text

        return text.capitalize()

    def incoming_private_chat_event(self, user, message):
        return user, self.anti_shout(message)

    def incoming_public_chat_event(self, room, user, message):
        return room, user, self.anti_shout(message)

    def anti_shout(self, message):

        lowers = len([x for x in message if x.islower()])
        uppers = len([x for x in message if x.isupper()])
        score = -2  # unknown state (could be: no letters at all)

        if uppers > 0:
            score = -1  # We have at least some upper letters

        if lowers > 0:
            score = uppers / float(lowers)

        new_message = message

        if len(message) > self.settings["minlength"] and (score == -1 or score > self.settings["maxscore"]):
            new_message = ". ".join([self.capitalize(x) for x in message.split(". ")])

        if new_message == message:
            return new_message

        return new_message + " [as]"
