# SPDX-FileCopyrightText: 2024-2025 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import shutil

from unittest import TestCase

from pynicotine.config import config
from pynicotine.core import core

DATA_FOLDER_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), "temp_data")
MAX_IPV4_RANGE = 4294967295


class CountryTest(TestCase):

    # pylint: disable=protected-access

    def setUp(self):

        config.set_data_folder(DATA_FOLDER_PATH)
        config.set_config_file(os.path.join(DATA_FOLDER_PATH, "temp_config"))

        core.init_components(enabled_components={"network_filter"})
        core.network_filter._populate_ip_country_data()

    def tearDown(self):
        core.quit()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(DATA_FOLDER_PATH)

    def test_ip_country_data_structure(self):
        """Verify that IP country data structure is valid."""

        self.assertTrue(core.network_filter._ip_range_countries)
        self.assertTrue(core.network_filter._ip_range_values)

        self.assertEqual(len(core.network_filter._ip_range_countries), len(core.network_filter._ip_range_values))

        self.assertTrue(all(isinstance(item, str) for item in core.network_filter._ip_range_countries))
        self.assertTrue(all(len(item) == 2 or not item for item in core.network_filter._ip_range_countries))

        self.assertTrue(all(isinstance(item, int) for item in core.network_filter._ip_range_values))
        self.assertTrue(all(0 <= item <= MAX_IPV4_RANGE for item in core.network_filter._ip_range_values))

    def test_read_ip_country(self):
        """Test reading country codes at IP range boundaries."""

        for ip_address, country_code in (
            ("0.255.255.255", ""),
            ("1.0.0.0", "AU"),
            ("1.0.0.255", "AU"),
            ("1.0.1.0", "CN"),
            ("1.255.255.255", "KR"),
            ("2.0.0.0", "US"),
            ("4.255.255.255", "US"),
            ("5.0.0.0", "SY"),
            ("9.255.255.255", "US"),
            ("10.0.0.0", ""),
            ("13.255.255.255", "US"),
            ("14.0.0.0", "CN")
        ):
            self.assertEqual(core.network_filter.get_country_code(ip_address), country_code)
