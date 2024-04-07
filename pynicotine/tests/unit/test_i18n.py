# COPYRIGHT (C) 2021-2024 Nicotine+ Contributors
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

from unittest import TestCase

from pynicotine.i18n import BASE_PATH


class I18nTest(TestCase):

    def test_po_files(self):
        """Verify that translation files don't contain errors."""

        po_file_found = False

        with os.scandir(os.path.join(BASE_PATH, "po")) as entries:
            for entry in entries:
                if not entry.is_file() or not entry.name.endswith(".po"):
                    continue

                po_file_found = True
                error_output = subprocess.check_output(
                    ["msgfmt", "--check", entry.path, "-o", "/dev/null"], stderr=subprocess.STDOUT)

                self.assertFalse(error_output)

        self.assertTrue(po_file_found)
