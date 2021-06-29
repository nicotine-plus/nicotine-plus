# COPYRIGHT (C) 2020-2021 Nicotine+ Team
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

import datetime
import socket
import unittest

from pynicotine.config import config
from pynicotine.utils import get_latest_version
from pynicotine.utils import make_version


class VersionTest(unittest.TestCase):

    @staticmethod
    def test_dev_version():

        # Test a sample dev version to ensure it's older than the stable counterpart
        sample_stable_version = make_version("2.1.0")
        sample_dev_version = make_version("2.1.0.dev1")
        assert sample_stable_version > sample_dev_version

    @staticmethod
    def test_update_check():

        # Validate local version
        local_version = make_version(config.version)
        assert isinstance(local_version, int)

        # Validate version of latest release
        try:
            _hlatest_version, latest_version, date = get_latest_version()
            assert isinstance(latest_version, int)

        except socket.gaierror:
            print("No internet access, skipping update check test!")
            return

        # Validate date of latest release
        date_format = "%Y-%m-%dT%H:%M:%S"
        datetime.datetime.strptime(date, date_format)
