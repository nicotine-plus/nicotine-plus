# COPYRIGHT (C) 2022-2023 Nicotine+ Contributors
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

import os
import sys
import time

from threading import Thread

from pynicotine.events import events


class CLIInputProcessor(Thread):

    def __init__(self):

        super().__init__(name="CLIInputProcessor", daemon=True)

        self.prompt_message = ""
        self.prompt_callback = None

    def run(self):

        while True:
            self._handle_prompt()

            # Small time window to set custom prompt
            time.sleep(0.75)

    def _handle_prompt_callback(self, user_input, callback):

        if not callback:
            return False

        events.emit("thread-callback", callback, user_input)
        return True

    def _handle_prompt_command(self, user_input):

        if not user_input:
            return False

        command, *args = user_input.split(maxsplit=1)

        if command.startswith("/"):
            command = command[1:]

        if args:
            (args,) = args

        events.emit_main_thread("cli-command", command, args)
        return True

    def _handle_prompt(self):

        callback = self.prompt_callback
        user_input = input(self.prompt_message)

        self.prompt_message = ""
        self.prompt_callback = None

        # Check if custom prompt is active
        if self._handle_prompt_callback(user_input, callback):
            return

        # No custom prompt, treat input as command
        self._handle_prompt_command(user_input)


class CLI:

    def __init__(self):
        self._input_processor = CLIInputProcessor()

    def enable(self):
        self._input_processor.start()
        events.connect("log-message", self._log_message)

    def prompt(self, message, callback):
        self._input_processor.prompt_message = message
        self._input_processor.prompt_callback = callback

    def _log_message(self, timestamp_format, msg, _title, _level):

        timestamp = time.strftime(timestamp_format)

        try:
            print(f"[{timestamp}] {msg}", flush=True)

        except OSError:
            # stdout is gone, prevent future errors
            sys.stdout = open(os.devnull, "w", encoding="utf-8")  # pylint: disable=consider-using-with


cli = CLI()
