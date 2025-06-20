# SPDX-FileCopyrightText: 2021-2025 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

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
