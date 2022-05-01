# COPYRIGHT (C) 2020-2022 Nicotine+ Contributors
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

import threading

from pynicotine.logfacility import log
from pynicotine.utils import execute_command


class Notifications:

    def __init__(self, config, ui_callback=None):

        self.config = config
        self.ui_callback = None

        self.chat_hilites = {
            "rooms": [],
            "private": []
        }

        self.tts = []
        self.tts_playing = False
        self.continue_playing = False

        if hasattr(ui_callback, "notifications"):
            self.ui_callback = ui_callback.notifications

    """ Chat Hilites """

    def add_hilite_item(self, location, item):

        if not item or item in self.chat_hilites[location]:
            return False

        self.chat_hilites[location].append(item)
        return True

    def remove_hilite_item(self, location, item):

        if item not in self.chat_hilites[location]:
            return False

        self.chat_hilites[location].remove(item)
        return True

    """ Text Notification """

    def new_text_notification(self, message, title=None):

        if self.ui_callback:
            self.ui_callback.new_text_notification(message, title)
            return

        if title:
            message = "%s: %s" % (title, message)

        log.add(message)

    """ TTS """

    def new_tts(self, message, args=None):

        if not self.config.sections["ui"]["speechenabled"]:
            return

        if message in self.tts:
            return

        if args:
            for key, value in args.items():
                args[key] = self.tts_clean_message(value)

            try:
                message = message % args

            except Exception as error:
                log.add(_("Text-to-speech for message failed: %s"), error)
                return

        self.tts.append(message)

        if self.tts_playing:
            # Avoid spinning up useless threads
            self.continue_playing = True
            return

        thread = threading.Thread(target=self.play_tts)
        thread.name = "TTS"
        thread.daemon = True
        thread.start()

    def play_tts(self):

        for message in self.tts[:]:
            self.tts_player(message)

            if message in self.tts:
                self.tts.remove(message)

        self.tts_playing = False
        if self.continue_playing:
            self.continue_playing = False
            self.play_tts()

    @staticmethod
    def tts_clean_message(message):

        for i in ["_", "[", "]", "(", ")"]:
            message = message.replace(i, " ")

        return message

    def tts_player(self, message):

        self.tts_playing = True

        try:
            execute_command(self.config.sections["ui"]["speechcommand"], message, background=False)

        except Exception as error:
            log.add(_("Text-to-speech for message failed: %s"), error)
