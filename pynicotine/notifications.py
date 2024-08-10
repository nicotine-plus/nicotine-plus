# COPYRIGHT (C) 2020-2024 Nicotine+ Contributors
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

from pynicotine.config import config
from pynicotine.events import events
from pynicotine.logfacility import log
from pynicotine.utils import execute_command


class Notifications:
    __slots__ = ("tts", "_tts_thread")

    def __init__(self):

        self.tts = deque()
        self._tts_thread = None

        events.connect("quit", self._quit)

    def _quit(self):
        self.tts.clear()

    # Notification Messages #

    def show_notification(self, message, title=None):
        events.emit("show-notification", message, title=title)

    def show_chatroom_notification(self, room, message, title=None, high_priority=False):
        events.emit("show-chatroom-notification", room, message, title=title, high_priority=high_priority)

    def show_download_notification(self, message, title=None, high_priority=False):
        events.emit("show-download-notification", message, title=title, high_priority=high_priority)

    def show_private_chat_notification(self, username, message, title=None):
        events.emit("show-private-chat-notification", username, message, title=title)

    def show_search_notification(self, search_token, message, title=None):
        events.emit("show-search-notification", search_token, message, title=title)

    # TTS #

    def new_tts(self, message, args=None):

        if not config.sections["ui"]["speechenabled"]:
            return

        if args:
            for key, value in args.items():
                args[key] = (value.replace("_", " ").replace("[", " ").replace("]", " ")
                                  .replace("(", " ").replace(")", " "))

            try:
                message %= args

            except Exception as error:
                log.add(_("Text-to-speech for message failed: %s"), error)
                return

        self.tts.append(message)

        if self._tts_thread and self._tts_thread.is_alive():
            return

        self._tts_thread = Thread(target=self.play_tts, name="TTS", daemon=True)
        self._tts_thread.start()

    def play_tts(self):

        while self.tts:
            try:
                message = self.tts.popleft()
                execute_command(config.sections["ui"]["speechcommand"], message, background=False, hidden=True)

            except Exception as error:
                log.add(_("Text-to-speech for message failed: %s"), error)
