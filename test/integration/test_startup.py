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
import sys

from unittest import skipIf
from unittest import TestCase

USER_DATA = os.path.dirname(os.path.realpath(__file__))
CONFIG_FILE = os.path.join(USER_DATA, "config")
COMMANDS = (
    ["python3", "-m", "pynicotine", f"--config={CONFIG_FILE}", f"--user-data={USER_DATA}", "--ci-mode"],  # GUI
    ["python3", "-m", "pynicotine", f"--config={CONFIG_FILE}", f"--user-data={USER_DATA}", "--ci-mode", "--headless"]
)


class StartupTest(TestCase):

    def test_startup(self):
        """ Verify that regular startup works """

        for command in COMMANDS:
            # Assume failure by default
            is_success = False

            try:
                subprocess.check_call(command, timeout=5)

            except subprocess.TimeoutExpired:
                # Program was still running, success!
                is_success = True

            self.assertTrue(is_success)

    @skipIf((sys.platform == "win32"), "CLI tests are currently flaky in Windows CI")
    def test_cli(self):
        """ Verify that CLI-exclusive functionality works """

        output = subprocess.check_output(["python3", "-m", "pynicotine", "--help"], timeout=3)
        self.assertIn(b"--help", output)

        # Check for " 0 folders found after rescan" in output. Text strings are translatable,
        # so we can't match them directly.
        output = subprocess.check_output(
            ["python3", "-m", "pynicotine", f"--config={CONFIG_FILE}", f"--user-data={USER_DATA}", "--rescan"],
            timeout=10
        )
        self.assertIn(b" 0 ", output)

        output = subprocess.check_output(["python3", "-m", "pynicotine", "--version"], timeout=3)
        self.assertIn(b"Nicotine+", output)
