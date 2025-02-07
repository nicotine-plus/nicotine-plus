# COPYRIGHT (C) 2020-2024 Nicotine+ Contributors
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
import struct
import wave

from unittest import TestCase

from pynicotine.config import config
from pynicotine.core import core

CURRENT_FOLDER_PATH = os.path.dirname(os.path.realpath(__file__))
DATA_FOLDER_PATH = os.path.join(CURRENT_FOLDER_PATH, "temp_data")
SHARES_FOLDER_PATH = os.path.join(CURRENT_FOLDER_PATH, ".sharedfiles")
BUDDY_SHARES_FOLDER_PATH = os.path.join(CURRENT_FOLDER_PATH, ".sharedbuddyfiles")
TRUSTED_SHARES_FOLDER_PATH = os.path.join(CURRENT_FOLDER_PATH, ".sharedtrustedfiles")
INVALID_SHARES_FOLDER_PATH = os.path.join(CURRENT_FOLDER_PATH, ".sharedinvalidfiles")
AUDIO_FILES = (
    (SHARES_FOLDER_PATH, "audiofile.wav", 50000),
    (BUDDY_SHARES_FOLDER_PATH, "audiofile2.wav", 150000),
    (TRUSTED_SHARES_FOLDER_PATH, "audiofile3.wav", 200000)
)


class SharesTest(TestCase):

    def setUp(self):

        config.set_data_folder(DATA_FOLDER_PATH)
        config.set_config_file(os.path.join(DATA_FOLDER_PATH, "temp_config"))

        core.init_components(enabled_components={"shares"})

        # Prepare shares
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

        # Prepare audio files
        for folder_path, basename, num_frames in AUDIO_FILES:
            with wave.open(os.path.join(folder_path, basename), "wb") as audio_file:
                # pylint: disable=no-member
                audio_file.setnchannels(1)
                audio_file.setsampwidth(2)
                audio_file.setframerate(44100)
                audio_file.writeframes(struct.pack("h", 0) * num_frames)

            self.addCleanup(os.remove, os.path.join(folder_path, basename))

        # Rescan shares
        core.shares.rescan_shares(rebuild=True, use_thread=False)
        core.shares.load_shares(core.shares.share_dbs, core.shares.share_db_paths)

    def tearDown(self):
        core.quit()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(DATA_FOLDER_PATH)

    def test_shares_scan(self):
        """Test a full shares scan."""

        # Verify that modification times were saved
        public_mtimes = list(core.shares.share_dbs["public_mtimes"])
        buddy_mtimes = list(core.shares.share_dbs["buddy_mtimes"])
        trusted_mtimes = list(core.shares.share_dbs["trusted_mtimes"])

        self.assertIn(os.path.join(SHARES_FOLDER_PATH, "dummy_file"), public_mtimes)
        self.assertIn(os.path.join(SHARES_FOLDER_PATH, "audiofile.wav"), public_mtimes)
        self.assertIn(os.path.join(BUDDY_SHARES_FOLDER_PATH, "audiofile2.wav"), buddy_mtimes)
        self.assertIn(os.path.join(BUDDY_SHARES_FOLDER_PATH, "something2", "nothing2"), buddy_mtimes)
        self.assertIn(os.path.join(TRUSTED_SHARES_FOLDER_PATH, "audiofile3.wav"), trusted_mtimes)
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
            ["Shares\\audiofile.wav", 100044, (706, 0, 44100, 16), 1],
            public_files[os.path.join(SHARES_FOLDER_PATH, "audiofile.wav")]
        )
        self.assertEqual(
            ["Secrets\\audiofile2.wav", 300044, (706, 0, 44100, 16), 3],
            buddy_files[os.path.join(BUDDY_SHARES_FOLDER_PATH, "audiofile2.wav")]
        )
        self.assertEqual(
            ["Secrets\\something2\\nothing2", 0, None, None],
            buddy_files[os.path.join(BUDDY_SHARES_FOLDER_PATH, "something2", "nothing2")]
        )
        self.assertEqual(
            ["Trusted\\audiofile3.wav", 400044, (706, 0, 44100, 16), 4],
            trusted_files[os.path.join(TRUSTED_SHARES_FOLDER_PATH, "audiofile3.wav")]
        )

        # Verify that expected folders are empty
        self.assertEqual(core.shares.share_dbs["public_streams"]["Shares\\folder2"], b"\x00\x00\x00\x00")
        self.assertEqual(core.shares.share_dbs["buddy_streams"]["Secrets\\folder3"], b"\x00\x00\x00\x00")
        self.assertEqual(core.shares.share_dbs["trusted_streams"]["Trusted\\folder\\folder2"], b"\x00\x00\x00\x00")

        # Verify that search index was updated
        word_index = core.shares.share_dbs["words"]
        audiofile_indexes = list(word_index["audiofile"])
        audiofile2_indexes = list(word_index["audiofile2"])
        audiofile3_indexes = list(word_index["audiofile3"])
        wav_indexes = list(word_index["wav"])

        self.assertEqual(set(word_index), {
            "wav", "folder2", "nothing2", "trusted", "nothing", "folder3", "dummy",
            "test", "file3", "folder", "file", "folder4", "secrets", "test2",
            "something", "something2", "file2", "audiofile", "somefile",
            "audiofile2", "txt", "folder1", "buddies", "audiofile3", "shares"
        })

        self.assertEqual(len(audiofile_indexes), 1)
        self.assertEqual(len(audiofile2_indexes), 1)
        self.assertEqual(len(audiofile3_indexes), 1)
        self.assertEqual(len(wav_indexes), 3)

        # File ID associated with word "wav" should return our audiofile files
        self.assertIn(wav_indexes[0], audiofile_indexes)
        self.assertIn(wav_indexes[1], audiofile2_indexes)
        self.assertIn(wav_indexes[2], audiofile3_indexes)
        self.assertEqual(
            core.shares.share_dbs["public_files"][core.shares.file_path_index[wav_indexes[0]]][0],
            "Shares\\audiofile.wav"
        )
        self.assertEqual(
            core.shares.share_dbs["buddy_files"][core.shares.file_path_index[wav_indexes[1]]][0],
            "Secrets\\audiofile2.wav"
        )
        self.assertEqual(
            core.shares.share_dbs["trusted_files"][core.shares.file_path_index[wav_indexes[2]]][0],
            "Trusted\\audiofile3.wav"
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
        self.assertEqual(len(public_files), 5)

        self.assertNotIn(os.path.join(BUDDY_SHARES_FOLDER_PATH, ".uvw_file"), buddy_files)
        self.assertIn(os.path.join(BUDDY_SHARES_FOLDER_PATH, "dummy_file2"), buddy_files)
        self.assertEqual(len(buddy_files), 6)

        self.assertNotIn(os.path.join(TRUSTED_SHARES_FOLDER_PATH, ".hidden_folder", "nothing"), trusted_files)
        self.assertIn(os.path.join(TRUSTED_SHARES_FOLDER_PATH, "dummy_file3"), trusted_files)
        self.assertEqual(len(trusted_files), 3)
