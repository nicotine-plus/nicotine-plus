# SPDX-FileCopyrightText: 2022-2025 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

import sys
import time

from collections import deque
from getpass import getpass
from threading import Thread

from pynicotine.events import events
from pynicotine.logfacility import log


class CLIInputProcessor(Thread):
    __slots__ = ("has_custom_prompt", "prompt_message", "prompt_callback", "prompt_silent")

    def __init__(self):

        super().__init__(name="CLIInputProcessor", daemon=True)

        try:
            # Enable line editing and history
            import readline  # noqa: F401  # pylint:disable=unused-import

        except ImportError:
            # Readline is not available on this OS
            pass

        self.has_custom_prompt = False
        self.prompt_message = ""
        self.prompt_callback = None
        self.prompt_silent = False

    def run(self):

        while True:
            # Small time window to set custom prompt
            time.sleep(0.25)

            try:
                self._handle_prompt()

            except Exception as error:
                log.add_debug("CLI input prompt is no longer available: %s", error)
                return

    def _handle_prompt_callback(self, user_input, callback):

        if not callback:
            return False

        events.invoke_main_thread(callback, user_input)
        return True

    def _handle_prompt_command(self, user_input):

        if not user_input:
            return False

        command, _separator, args = user_input.strip().partition(" ")
        args = args.strip()

        if command.startswith("/"):
            command = command[1:]

        events.emit_main_thread("cli-command", command, args)
        return True

    def _handle_prompt(self):

        callback = self.prompt_callback
        input_func = getpass if self.prompt_silent else input
        self.has_custom_prompt = (callback is not None)

        user_input = input_func(self.prompt_message)

        self.has_custom_prompt = False
        self.prompt_message = ""
        self.prompt_callback = None
        self.prompt_silent = False

        events.emit("cli-prompt-finished")

        # Check if custom prompt is active
        if self._handle_prompt_callback(user_input, callback):
            return

        # No custom prompt, treat input as command
        self._handle_prompt_command(user_input)


class CLI:
    __slots__ = ("_input_processor", "_log_message_queue", "_tty_attributes")

    def __init__(self):

        self._input_processor = CLIInputProcessor()
        self._log_message_queue = deque(maxlen=1000)
        self._tty_attributes = None

        events.connect("quit", self._quit)

    def enable_prompt(self):

        try:
            import termios  # pylint: disable=import-error
            self._tty_attributes = termios.tcgetattr(sys.stdin)

        except Exception:
            # Not a terminal, or using Windows
            pass

        self._input_processor.start()

    def enable_logging(self):

        for event_name, callback in (
            ("cli-prompt-finished", self._cli_prompt_finished),
            ("log-message", self._log_message)
        ):
            events.connect(event_name, callback)

    def prompt(self, message, callback, is_silent=False):

        self._input_processor.prompt_message = message
        self._input_processor.prompt_callback = callback
        self._input_processor.prompt_silent = is_silent

    def _print_log_message(self, log_message):

        try:
            print(log_message, flush=True)

        except OSError:
            # stdout is gone, prevent future errors
            events.disconnect("log-message", self._log_message)
            self._log_message_queue.clear()

    def _cli_prompt_finished(self):
        while self._log_message_queue:
            self._print_log_message(self._log_message_queue.popleft())

    def _log_message(self, timestamp_format, msg, _title, _level):

        if timestamp_format:
            timestamp = time.strftime(timestamp_format)
            log_message = f"[{timestamp}] {msg}"
        else:
            log_message = msg

        if self._input_processor.has_custom_prompt:
            # Don't print log messages while custom prompt is active
            self._log_message_queue.append(log_message)
            return

        self._print_log_message(log_message)

    def _quit(self):
        """Restores TTY attributes and re-enables echo on quit."""

        if self._tty_attributes is None:
            return

        import termios  # pylint: disable=import-error

        try:
            termios.tcsetattr(sys.stdin, termios.TCSANOW, self._tty_attributes)

        except termios.error:
            # stdin is gone
            pass

        self._tty_attributes = None


cli = CLI()
