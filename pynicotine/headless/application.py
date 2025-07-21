# SPDX-FileCopyrightText: 2021-2025 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

import sys
import time

from pynicotine.cli import cli
from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.logfacility import log


class Application:

    def __init__(self):

        sys.excepthook = self.on_critical_error

        for log_level in ("download", "upload"):
            log.add_log_level(log_level, is_permanent=False)

        for event_name, callback in (
            ("confirm-quit", self.on_confirm_quit),
            ("invalid-password", self.on_invalid_password),
            ("invalid-username", self.on_invalid_password),
            ("setup", self.on_setup),
            ("shares-unavailable", self.on_shares_unavailable)
        ):
            events.connect(event_name, callback)

    def run(self):

        core.start()

        if config.sections["server"]["auto_connect_startup"]:
            core.connect()
        else:
            log.add(_("Type %s to connect to Soulseek"), "/connect")

        # Main loop, process events from threads 10 times per second
        while events.process_thread_events():
            time.sleep(0.1)

        # Shut down with exit code 0 (success)
        config.write_configuration()
        return 0

    def on_critical_error(self, _exc_type, exc_value, _exc_traceback):

        sys.excepthook = None

        core.quit()
        events.emit("quit")

        raise exc_value

    def on_confirm_quit_response(self, user_input):
        if user_input.lower().startswith("y"):
            core.quit()

    def on_confirm_quit(self):
        responses = "[y/N] "
        cli.prompt(_("Do you really want to exit? %s") % responses, callback=self.on_confirm_quit_response)

    def on_invalid_password(self, *_args):

        log.add(_("User %s already exists, and the password you entered is invalid."),
                config.sections["server"]["login"])
        log.add(_("Type %s to log in with another username or password."), "/connect")

        config.sections["server"]["passw"] = ""

    def on_setup_password_response(self, user_input):

        config.sections["server"]["passw"] = user_input
        config.write_configuration()

        core.connect()

    def on_setup_username_response(self, user_input):

        if user_input:
            config.sections["server"]["login"] = user_input

        cli.prompt(_("Password: "), callback=self.on_setup_password_response, is_silent=True)

    def on_setup(self):
        log.add(_("To create a new Soulseek account, fill in your desired username and password. If you "
                  "already have an account, fill in your existing login details."))
        cli.prompt(_("Username: "), callback=self.on_setup_username_response)

    def on_shares_unavailable_response(self, user_input):

        user_input = user_input.lower()

        if not user_input or user_input.startswith("y"):
            core.shares.rescan_shares()

        elif user_input.startswith("f"):
            core.shares.rescan_shares(force=True)

    def on_shares_unavailable(self, shares):

        responses = "[Y/n/force] "
        message = _("The following shares are unavailable:") + "\n\n"

        for virtual_name, folder_path in shares:
            message += f'• "{virtual_name}" {folder_path}\n'

        message += "\n" + _("Verify that external disks are mounted and folder permissions are correct.")
        message += "\n" + _("Retry rescan? %s") % responses

        cli.prompt(message, callback=self.on_shares_unavailable_response)
