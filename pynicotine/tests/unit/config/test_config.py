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
import shutil

from unittest import TestCase

from pynicotine.config import config
from pynicotine.core import core
from pynicotine.utils import encode_path

CURRENT_FOLDER_PATH = os.path.dirname(os.path.realpath(__file__))
DATA_FOLDER_PATH = os.path.join(CURRENT_FOLDER_PATH, "temp_data")


class ConfigTest(TestCase):

    def setUp(self):

        config.set_data_folder(DATA_FOLDER_PATH)
        config.set_config_file(os.path.join(DATA_FOLDER_PATH, "temp_config"))
        default_config_path = os.path.join(CURRENT_FOLDER_PATH, "config")

        if not os.path.exists(DATA_FOLDER_PATH):
            os.makedirs(DATA_FOLDER_PATH)

        shutil.copy(default_config_path, config.config_file_path)

        core.init_components(enabled_components={})

    def tearDown(self):
        core.quit()
        self.assertTrue(config.sections)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(DATA_FOLDER_PATH)

    def test_load_config(self):
        """Test loading a config file."""

        self.assertEqual(config.defaults["server"]["login"], "")
        self.assertEqual(config.defaults["server"]["passw"], "")

        self.assertEqual(config.sections["server"]["login"], "user123")
        self.assertEqual(config.sections["server"]["passw"], "pass123")
        self.assertEqual(config.sections["server"]["autoreply"], "ääääääää")

    def test_write_config(self):
        """Test writing to a config file."""

        # Verify that changes are saved
        config.sections["server"]["login"] = "newname"
        config.write_configuration()

        with open(encode_path(config.config_file_path), encoding="utf-8") as file_handle:
            self.assertIn("newname", file_handle.read())

        # Verify that the backup is valid
        old_config = encode_path(f"{config.config_file_path}.old")
        self.assertTrue(os.path.exists(old_config))

        with open(old_config, encoding="utf-8") as file_handle:
            self.assertIn("user123", file_handle.read())

        # Reset
        config.sections["server"]["login"] = "user123"
        config.write_configuration()
