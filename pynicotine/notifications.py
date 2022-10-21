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

from collections import deque
from threading import Thread

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

        self.tts = deque()
        self.tts_thread = None
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

        if args:
            for key, value in args.items():
                args[key] = (value.replace("_", " ").replace("[", " ").replace("]", " ")
                                  .replace("(", " ").replace(")", " "))

            try:
                message = message % args

            except Exception as error:
                log.add(_("Text-to-speech for message failed: %s"), error)
                return

        self.tts.append(message)

        if self.tts_thread and self.tts_thread.is_alive():
            return

        self.tts_thread = Thread(target=self.play_tts, name="TTS", daemon=True)
        self.tts_thread.start()

    def play_tts(self):

        while self.tts:
            try:
                message = self.tts.popleft()
                execute_command(self.config.sections["ui"]["speechcommand"], message, background=False)

            except Exception as error:
                log.add(_("Text-to-speech for message failed: %s"), error)
