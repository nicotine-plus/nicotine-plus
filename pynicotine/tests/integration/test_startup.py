# COPYRIGHT (C) 2020-2023 Nicotine+ Contributors
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

from unittest import TestCase

USER_DATA = os.path.dirname(os.path.realpath(__file__))
CONFIG_FILE = os.path.join(USER_DATA, "temp_config")


class StartupTest(TestCase):

    def test_gui_startup(self):
        """Verify that regular GUI startup works."""

        command = ["python3", "-m", "pynicotine", f"--config={CONFIG_FILE}", f"--user-data={USER_DATA}", "--ci-mode"]
        broadway_display = ":1000"
        broadway_process = None
        is_success = False

        if sys.platform not in {"darwin", "win32"}:
            # Display server is required, use GDK's Broadway backend if available.
            # If not available, leave it up to the user to run the tests with e.g. xvfb-run.

            # pylint: disable=consider-using-with
            try:
                broadway_process = subprocess.Popen(["gtk4-broadwayd", broadway_display])

            except Exception:
                try:
                    broadway_process = subprocess.Popen(["broadwayd", broadway_display])

                except Exception:
                    pass

        if broadway_process is not None:
            os.environ["GDK_BACKEND"] = "broadway"
            os.environ["BROADWAY_DISPLAY"] = broadway_display

        with subprocess.Popen(command) as process:
            try:
                process.wait(timeout=5)

            except subprocess.TimeoutExpired:
                is_success = True
                process.terminate()

        if broadway_process is not None:
            broadway_process.terminate()
            broadway_process.wait()

        self.assertTrue(is_success)

    def test_cli_startup(self):
        """Verify that regular CLI startup works."""

        command = ["python3", "-m", "pynicotine", f"--config={CONFIG_FILE}", f"--user-data={USER_DATA}",
                   "--ci-mode", "--headless"]
        is_success = False

        with subprocess.Popen(command) as process:
            try:
                process.wait(timeout=5)

            except subprocess.TimeoutExpired:
                is_success = True
                process.terminate()

        self.assertTrue(is_success)

    def test_cli(self):
        """Verify that CLI-exclusive functionality works."""

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
