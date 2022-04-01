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

import os
import subprocess
import unittest

USER_DATA = os.path.dirname(os.path.realpath(__file__))
CONFIG_FILE = os.path.join(USER_DATA, "config")
COMMANDS = (
    ["python3", "-m", "pynicotine",
        "--config=" + CONFIG_FILE, "--user-data=" + USER_DATA, "--ci-mode"],               # GUI
    ["python3", "-m", "pynicotine",
        "--config=" + CONFIG_FILE, "--user-data=" + USER_DATA, "--ci-mode", "--headless"]  # Headless
)


class StartupTest(unittest.TestCase):

    def test_startup(self):
        """ Verify that regular startup works """

        for command in COMMANDS:
            # Assume failure by default
            is_success = False

            try:
                subprocess.call(command, timeout=5)

            except subprocess.TimeoutExpired:
                # Program was still running, success!
                is_success = True

            self.assertTrue(is_success)

    def test_cli(self):
        """ Verify that CLI-exclusive functionality works """

        output = subprocess.check_output(["python3", "-m", "pynicotine", "--help"], timeout=3)
        self.assertTrue(str(output).find("--help") > -1)

        # Check for " 0 folders found after rescan" in output. Text strings are translatable,
        # so we can't match them directly.
        output = subprocess.check_output(
            ["python3", "-m", "pynicotine", "--config=" + CONFIG_FILE, "--user-data=" + USER_DATA, "--rescan"],
            timeout=10
        )
        self.assertTrue(str(output).find(" 0 ") > -1)

        output = subprocess.check_output(["python3", "-m", "pynicotine", "--version"], timeout=3)
        self.assertTrue(str(output).find("Nicotine+") > -1)
