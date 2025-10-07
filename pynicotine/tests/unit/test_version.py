# SPDX-FileCopyrightText: 2020-2023 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

import os

from unittest import skipUnless
from unittest import TestCase

import pynicotine
from pynicotine.core import UpdateChecker


class VersionTest(TestCase):

    def test_dev_version(self):

        # Test a sample dev version to ensure it's older than the stable counterpart
        sample_stable_version = UpdateChecker.create_integer_version("2.1.0")
        sample_dev_version = UpdateChecker.create_integer_version("2.1.0.dev1")
        self.assertGreater(sample_stable_version, sample_dev_version)

    @skipUnless(os.environ.get("NICOTINE_NETWORK_TESTS"), reason="Requires network connection")
    def test_update_check(self):

        # Validate local version
        local_version = UpdateChecker.create_integer_version(pynicotine.__version__)
        self.assertIsInstance(local_version, int)

        # Validate version of latest release
        _h_latest_version, latest_version = UpdateChecker.retrieve_latest_version()
        self.assertIsInstance(latest_version, int)
