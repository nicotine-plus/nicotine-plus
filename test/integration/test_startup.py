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

import os
import subprocess
import unittest

USER_DATA = os.path.dirname(os.path.realpath(__file__))
CONFIG_FILE = os.path.join(USER_DATA, "temp_config")
COMMANDS = (
    ["python3", "-m", "pynicotine",
        "--config=" + CONFIG_FILE, "--user-data=" + USER_DATA, "--ci-mode"],               # GUI
    ["python3", "-m", "pynicotine",
        "--config=" + CONFIG_FILE, "--user-data=" + USER_DATA, "--ci-mode", "--headless"]  # Headless
)


class StartupTest(unittest.TestCase):

    def test_startup(self):

        for command in COMMANDS:
            # Assume failure by default
            is_success = False

            try:
                subprocess.call(command, timeout=5)

            except subprocess.TimeoutExpired:
                # Program was still running, success!
                is_success = True

            self.assertTrue(is_success)
