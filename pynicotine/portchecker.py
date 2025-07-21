# SPDX-FileCopyrightText: 2025 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

import threading

import pynicotine
from pynicotine.events import events
from pynicotine.logfacility import log


class PortChecker:
    __slots__ = ("_thread",)

    def __init__(self):
        self._thread = None

    def check_status(self, port):

        threading.Thread(
            target=self._check_status, args=(port,), name="PortChecker", daemon=True
        ).start()

    def _check_status(self, port):

        try:
            is_successful = self._retrieve_status(port)

        except Exception as error:
            log.add_debug("Unable to check status of port %s: %s", (port, error))
            is_successful = None

        events.emit_main_thread("check-port-status", port, is_successful)

    def _retrieve_status(self, port):

        from urllib.request import urlopen

        with urlopen(pynicotine.__port_checker_url__ % port, timeout=5) as response:
            response_body = response.read().lower()

        if f"{port}/tcp open".encode() in response_body:
            is_successful = True

        elif f"{port}/tcp closed".encode() in response_body:
            is_successful = False

        else:
            raise ValueError(f"Unknown response from port checker: {response_body}")

        return is_successful
