# COPYRIGHT (C) 2025 Nicotine+ Contributors
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
