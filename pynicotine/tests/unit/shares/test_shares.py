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

CURRENT_FOLDER_PATH = os.path.dirname(os.path.realpath(__file__))
SHARES_FOLDER_PATH = os.path.join(CURRENT_FOLDER_PATH, ".sharedfiles")
BUDDY_SHARES_FOLDER_PATH = os.path.join(CURRENT_FOLDER_PATH, ".sharedbuddyfiles")
TRUSTED_SHARES_FOLDER_PATH = os.path.join(CURRENT_FOLDER_PATH, ".sharedtrustedfiles")
INVALID_SHARES_FOLDER_PATH = os.path.join(CURRENT_FOLDER_PATH, ".sharedinvalidfiles")


class SharesTest(TestCase):

    def setUp(self):

        config.data_folder_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "dbs")
        config.config_file_path = os.path.join(config.data_folder_path, "temp_config")

        core.init_components(enabled_components={"shares"})

        config.sections["transfers"]["shared"] = [
            ("Shares", SHARES_FOLDER_PATH, "junk"),                     # Superfluous item in tuple
            ("invalid", os.path.join(SHARES_FOLDER_PATH, "folder2"))    # Resharing subfolder from previous share
        ]
        config.sections["transfers"]["buddyshared"] = [
            ("Secrets", BUDDY_SHARES_FOLDER_PATH),
            ("invalid2", os.path.join(BUDDY_SHARES_FOLDER_PATH, "buddies")),  # Resharing subfolder from previous share
            ("invalid3", os.path.join(BUDDY_SHARES_FOLDER_PATH, "something2", "nothing2")),  # File instead of folder
            ("Shares", INVALID_SHARES_FOLDER_PATH)                      # Duplicate virtual name
        ]
        config.sections["transfers"]["trustedshared"] = [
            ("invalid4", SHARES_FOLDER_PATH),                           # Resharing public folder
            ("Trusted", TRUSTED_SHARES_FOLDER_PATH)
        ]
        core.shares.rescan_shares(rebuild=True, use_thread=False)
        core.shares.load_shares(core.shares.share_dbs, core.shares.share_db_paths)

    def tearDown(self):
        core.quit()
        self.assertIsNone(core.shares)

    def test_shares_scan(self):
        """Test a full shares scan."""

        # Verify that modification times were saved
        public_mtimes = list(core.shares.share_dbs["public_mtimes"])
        buddy_mtimes = list(core.shares.share_dbs["buddy_mtimes"])
        trusted_mtimes = list(core.shares.share_dbs["trusted_mtimes"])

        self.assertIn(os.path.join(SHARES_FOLDER_PATH, "dummy_file"), public_mtimes)
        self.assertIn(os.path.join(SHARES_FOLDER_PATH, "nicotinetestdata.mp3"), public_mtimes)
        self.assertIn(os.path.join(SHARES_FOLDER_PATH, "nicotinevbr.mp3"), public_mtimes)
        self.assertIn(os.path.join(BUDDY_SHARES_FOLDER_PATH, "nicotinevbr2.mp3"), buddy_mtimes)
        self.assertIn(os.path.join(BUDDY_SHARES_FOLDER_PATH, "something2", "nothing2"), buddy_mtimes)
        self.assertIn(os.path.join(TRUSTED_SHARES_FOLDER_PATH, "nicotinetestdata3.ogg"), trusted_mtimes)
        self.assertIn(os.path.join(TRUSTED_SHARES_FOLDER_PATH, "folder", "folder2", "folder3", "folder4", "nothing"),
                      trusted_mtimes)

        # Verify that shared files were added
        public_files = core.shares.share_dbs["public_files"]
        buddy_files = core.shares.share_dbs["buddy_files"]
        trusted_files = core.shares.share_dbs["trusted_files"]

        self.assertEqual(
            ["Shares\\dummy_file", 0, None, None],
            public_files[os.path.join(SHARES_FOLDER_PATH, "dummy_file")]
        )
        self.assertEqual(
            ["Shares\\nicotinetestdata.mp3", 80919, (128, 0, 44100, None), 5],
            public_files[os.path.join(SHARES_FOLDER_PATH, "nicotinetestdata.mp3")]
        )
        self.assertEqual(
            ["Shares\\nicotinevbr.mp3", 36609, (32, 1, 44100, None), 9],
            public_files[os.path.join(SHARES_FOLDER_PATH, "nicotinevbr.mp3")]
        )
        self.assertEqual(
            ["Secrets\\nicotinevbr2.mp3", 36609, (32, 1, 44100, None), 9],
            buddy_files[os.path.join(BUDDY_SHARES_FOLDER_PATH, "nicotinevbr2.mp3")]
        )
        self.assertEqual(
            ["Secrets\\something2\\nothing2", 0, None, None],
            buddy_files[os.path.join(BUDDY_SHARES_FOLDER_PATH, "something2", "nothing2")]
        )
        self.assertEqual(
            ["Trusted\\nicotinetestdata3.ogg", 4567, (112, 0, 44100, None), 5],
            trusted_files[os.path.join(TRUSTED_SHARES_FOLDER_PATH, "nicotinetestdata3.ogg")]
        )

        # Verify that expected folders are empty
        self.assertEqual(core.shares.share_dbs["public_streams"]["Shares\\folder2"], b"\x00\x00\x00\x00")
        self.assertEqual(core.shares.share_dbs["buddy_streams"]["Secrets\\folder3"], b"\x00\x00\x00\x00")
        self.assertEqual(core.shares.share_dbs["trusted_streams"]["Trusted\\folder\\folder2"], b"\x00\x00\x00\x00")

        # Verify that search index was updated
        word_index = core.shares.share_dbs["words"]
        nicotinetestdata_indexes = list(word_index["nicotinetestdata"])
        nicotinetestdata2_indexes = list(word_index["nicotinetestdata2"])
        nicotinetestdata3_indexes = list(word_index["nicotinetestdata3"])
        ogg_indexes = list(word_index["ogg"])

        self.assertEqual(set(word_index), {
            "ogg", "folder2", "nothing2", "mp3", "trusted", "nothing", "folder3", "dummy",
            "test", "file3", "folder", "nicotinevbr", "file", "folder4", "secrets", "test2",
            "something", "nicotinevbr2", "something2", "file2", "nicotinetestdata", "somefile",
            "nicotinetestdata2", "txt", "folder1", "buddies", "nicotinetestdata3", "shares"
        })

        self.assertEqual(len(nicotinetestdata_indexes), 2)
        self.assertEqual(len(nicotinetestdata2_indexes), 2)
        self.assertEqual(len(nicotinetestdata3_indexes), 1)
        self.assertEqual(len(ogg_indexes), 3)

        # File ID associated with word "ogg" should return our nicotinetestdata files
        self.assertIn(ogg_indexes[0], nicotinetestdata_indexes)
        self.assertIn(ogg_indexes[1], nicotinetestdata2_indexes)
        self.assertIn(ogg_indexes[2], nicotinetestdata3_indexes)
        self.assertEqual(
            core.shares.share_dbs["public_files"][core.shares.file_path_index[ogg_indexes[0]]][0],
            "Shares\\nicotinetestdata.ogg"
        )
        self.assertEqual(
            core.shares.share_dbs["buddy_files"][core.shares.file_path_index[ogg_indexes[1]]][0],
            "Secrets\\nicotinetestdata2.ogg"
        )
        self.assertEqual(
            core.shares.share_dbs["trusted_files"][core.shares.file_path_index[ogg_indexes[2]]][0],
            "Trusted\\nicotinetestdata3.ogg"
        )

    def test_hidden_file_folder_scan(self):
        """Test that hidden files and folders are excluded."""

        # Check modification times
        public_mtimes = list(core.shares.share_dbs["public_mtimes"])
        buddy_mtimes = list(core.shares.share_dbs["buddy_mtimes"])
        trusted_mtimes = list(core.shares.share_dbs["trusted_mtimes"])

        self.assertNotIn(os.path.join(SHARES_FOLDER_PATH, ".abc", "nothing"), public_mtimes)
        self.assertNotIn(os.path.join(SHARES_FOLDER_PATH, ".xyz", "nothing"), public_mtimes)
        self.assertIn(os.path.join(SHARES_FOLDER_PATH, "folder1", "nothing"), public_mtimes)
        self.assertIn(os.path.join(SHARES_FOLDER_PATH, "folder2", "test", "nothing"), public_mtimes)
        self.assertNotIn(os.path.join(SHARES_FOLDER_PATH, "folder2", ".poof", "nothing"), public_mtimes)
        self.assertIn(os.path.join(SHARES_FOLDER_PATH, "folder2", "test", "nothing"), public_mtimes)
        self.assertIn(os.path.join(SHARES_FOLDER_PATH, "something", "nothing"), public_mtimes)

        self.assertNotIn(os.path.join(BUDDY_SHARES_FOLDER_PATH, "folder3", ".poof2", "nothing2"), buddy_mtimes)
        self.assertIn(os.path.join(BUDDY_SHARES_FOLDER_PATH, "folder3", "test2", "nothing2"), buddy_mtimes)
        self.assertNotIn(os.path.join(INVALID_SHARES_FOLDER_PATH, "file.txt"), buddy_mtimes)

        self.assertNotIn(os.path.join(TRUSTED_SHARES_FOLDER_PATH, ".hidden_folder", "nothing"), trusted_mtimes)
        self.assertIn(os.path.join(TRUSTED_SHARES_FOLDER_PATH, "folder", "folder2", "folder3", "folder4", "nothing"),
                      trusted_mtimes)

        # Check file data
        public_files = core.shares.share_dbs["public_files"]
        buddy_files = core.shares.share_dbs["buddy_files"]
        trusted_files = core.shares.share_dbs["trusted_files"]

        self.assertNotIn(os.path.join(SHARES_FOLDER_PATH, ".abc_file"), public_files)
        self.assertNotIn(os.path.join(SHARES_FOLDER_PATH, ".hidden_file"), public_files)
        self.assertNotIn(os.path.join(SHARES_FOLDER_PATH, ".xyz_file"), public_files)
        self.assertIn(os.path.join(SHARES_FOLDER_PATH, "dummy_file"), public_files)
        self.assertEqual(len(public_files), 7)

        self.assertNotIn(os.path.join(BUDDY_SHARES_FOLDER_PATH, ".uvw_file"), buddy_files)
        self.assertIn(os.path.join(BUDDY_SHARES_FOLDER_PATH, "dummy_file2"), buddy_files)
        self.assertEqual(len(buddy_files), 8)

        self.assertNotIn(os.path.join(TRUSTED_SHARES_FOLDER_PATH, ".hidden_folder", "nothing"), trusted_files)
        self.assertIn(os.path.join(TRUSTED_SHARES_FOLDER_PATH, "dummy_file3"), trusted_files)
        self.assertEqual(len(trusted_files), 3)
