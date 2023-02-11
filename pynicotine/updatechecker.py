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

import json

from threading import Thread

from pynicotine.config import config
from pynicotine.logfacility import log


class UpdateChecker:

    def __init__(self):
        self._thread = None

    def check(self):

        if self._thread and self._thread.is_alive():
            return

        self._thread = Thread(target=self._check, name="UpdateChecker", daemon=True)
        self._thread.start()

    def _check(self):

        try:
            h_latest_version, latest_version, date = self.retrieve_latest_version()
            version = self.create_integer_version(config.version)
            title = _("Up to Date")

            if latest_version > version:
                title = _("Out of Date")
                message = _("Version %(version)s is available, released on %(date)s") % {
                    "version": h_latest_version,
                    "date": date
                }

            elif version > latest_version:
                message = _("You are using a development version of %s") % config.application_name

            else:
                message = _("You are using the latest version of %s") % config.application_name

        except Exception as error:
            title = _("Latest Version Unknown")
            message = _("Cannot retrieve latest version: %s") % error

        log.add(message, title=title)

    @staticmethod
    def create_integer_version(version):

        major, minor, patch = version.split(".")[:3]
        stable = 1

        if "dev" in version or "rc" in version:
            # Example: 2.0.1.dev1
            # A dev version will be one less than a stable version
            stable = 0

        return (int(major) << 24) + (int(minor) << 16) + (int(patch.split("rc", 1)[0]) << 8) + stable

    @classmethod
    def retrieve_latest_version(cls):

        from urllib.request import urlopen
        with urlopen("https://pypi.org/pypi/nicotine-plus/json", timeout=5) as response:
            response_body = response.read().decode("utf-8")

        data = json.loads(response_body)
        h_latest_version = data["info"]["version"]
        latest_version = cls.create_integer_version(h_latest_version)

        try:
            date = data["releases"][h_latest_version][0]["upload_time"]
        except Exception:
            date = None

        return h_latest_version, latest_version, date
