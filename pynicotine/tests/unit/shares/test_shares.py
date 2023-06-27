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

from unittest import TestCase

from pynicotine.config import config
from pynicotine.core import core

SHARES_FOLDER_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), ".sharedfiles")


class SharesTest(TestCase):

    def setUp(self):

        config.data_folder_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "dbs")
        config.config_file_path = os.path.join(config.data_folder_path, "temp_config")

        core.init_components(enabled_components={"shares"})

        config.sections["transfers"]["shared"] = [("Shares", SHARES_FOLDER_PATH)]
        core.shares.rescan_shares(use_thread=False)
        core.shares.load_shares_instance(
            core.shares.share_dbs, core.shares.share_db_paths + core.shares.scanner_share_db_paths
        )

    def tearDown(self):
        core.quit()
        self.assertIsNone(core.shares)

    def test_shares_scan(self):
        """Test a full shares scan."""

        # Verify that modification times were saved
        mtimes = list(core.shares.share_dbs["mtimes"])

        self.assertIn(os.path.join(SHARES_FOLDER_PATH, "dummy_file"), mtimes)
        self.assertIn(os.path.join(SHARES_FOLDER_PATH, "nicotinetestdata.mp3"), mtimes)
        self.assertIn(os.path.join(SHARES_FOLDER_PATH, "nicotinevbr.mp3"), mtimes)

        # Verify that shared files were added
        files = core.shares.share_dbs["files"]

        self.assertEqual(
            ["Shares\\dummy_file", 0, None, None],
            files[os.path.join(SHARES_FOLDER_PATH, "dummy_file")]
        )
        self.assertEqual(
            ["Shares\\nicotinetestdata.mp3", 80919, (128, 0, 44100, None), 5],
            files[os.path.join(SHARES_FOLDER_PATH, "nicotinetestdata.mp3")]
        )
        self.assertEqual(
            ["Shares\\nicotinevbr.mp3", 36609, (32, 1, 44100, None), 9],
            files[os.path.join(SHARES_FOLDER_PATH, "nicotinevbr.mp3")]
        )

        # Verify that expected folder is empty
        self.assertEqual(core.shares.share_dbs["streams"]["Shares\\folder2"], b"\x00\x00\x00\x00")

        # Verify that search index was updated
        word_index = core.shares.share_dbs["wordindex"]
        nicotinetestdata_indexes = list(word_index["nicotinetestdata"])
        ogg_indexes = list(word_index["ogg"])

        self.assertEqual(set(word_index), set(
            ["nicotinetestdata", "ogg", "mp3", "shares", "file", "dummy", "folder1",
             "folder2", "nothing", "something", "test", "nicotinevbr"]
        ))
        self.assertEqual(len(nicotinetestdata_indexes), 2)
        self.assertEqual(len(ogg_indexes), 1)

        # File ID associated with word "ogg" should return our nicotinetestdata.ogg file
        self.assertIn(ogg_indexes[0], nicotinetestdata_indexes)
        self.assertEqual(
            core.shares.share_dbs["files"][core.shares.file_path_index[ogg_indexes[0]]][0],
            "Shares\\nicotinetestdata.ogg"
        )

    def test_hidden_file_folder_scan(self):
        """Test that hidden files and folders are excluded."""

        # Check modification times
        mtimes = list(core.shares.share_dbs["mtimes"])

        self.assertNotIn(os.path.join(SHARES_FOLDER_PATH, ".abc", "nothing"), mtimes)
        self.assertNotIn(os.path.join(SHARES_FOLDER_PATH, ".xyz", "nothing"), mtimes)
        self.assertIn(os.path.join(SHARES_FOLDER_PATH, "folder1", "nothing"), mtimes)
        self.assertIn(os.path.join(SHARES_FOLDER_PATH, "folder2", "test", "nothing"), mtimes)
        self.assertNotIn(os.path.join(SHARES_FOLDER_PATH, "folder2", ".poof", "nothing"), mtimes)
        self.assertIn(os.path.join(SHARES_FOLDER_PATH, "folder2", "test", "nothing"), mtimes)
        self.assertIn(os.path.join(SHARES_FOLDER_PATH, "something", "nothing"), mtimes)

        # Check file data
        files = core.shares.share_dbs["files"]

        self.assertNotIn(os.path.join(SHARES_FOLDER_PATH, ".abc_file"), files)
        self.assertNotIn(os.path.join(SHARES_FOLDER_PATH, ".hidden_file"), files)
        self.assertNotIn(os.path.join(SHARES_FOLDER_PATH, ".xyz_file"), files)
        self.assertIn(os.path.join(SHARES_FOLDER_PATH, "dummy_file"), files)
        self.assertEqual(len(files), 7)
