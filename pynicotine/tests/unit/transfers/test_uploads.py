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
from pynicotine.slskmessages import FileAttribute
from pynicotine.transfers import TransferStatus

CURRENT_FOLDER_PATH = os.path.dirname(os.path.realpath(__file__))
DATA_FOLDER_PATH = os.path.join(CURRENT_FOLDER_PATH, "temp_data")
TRANSFERS_BASENAME = "uploads.json"
TRANSFERS_FILE_PATH = os.path.join(CURRENT_FOLDER_PATH, TRANSFERS_BASENAME)
SAVED_TRANSFERS_FILE_PATH = os.path.join(DATA_FOLDER_PATH, TRANSFERS_BASENAME)


class UploadsTest(TestCase):

    # pylint: disable=protected-access

    def setUp(self):

        config.set_data_folder(DATA_FOLDER_PATH)
        config.set_config_file(os.path.join(DATA_FOLDER_PATH, "temp_config"))

        if not os.path.exists(DATA_FOLDER_PATH):
            os.makedirs(DATA_FOLDER_PATH)

        shutil.copy(TRANSFERS_FILE_PATH, os.path.join(DATA_FOLDER_PATH, TRANSFERS_BASENAME))

        core.init_components(enabled_components={"users", "shares", "uploads", "buddies"})
        core.start()

    def tearDown(self):
        core.quit()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(DATA_FOLDER_PATH)

    def test_load_uploads(self):
        """Test loading a uploads.json file."""

        transfers = list(core.uploads.transfers.values())

        # Only finished uploads are loaded, other types should never be stored
        self.assertEqual(len(transfers), 3)

        transfer = transfers[2]

        self.assertEqual(transfer.username, "user5")
        self.assertEqual(transfer.virtual_path, "Junk\\Song5.mp3")
        self.assertEqual(transfer.status, TransferStatus.FINISHED)
        self.assertEqual(transfer.size, 11733776)
        self.assertEqual(transfer.current_byte_offset, 11733776)
        self.assertFalse(transfer.file_attributes)

        transfer = transfers[0]

        self.assertEqual(transfer.username, "user3")
        self.assertEqual(transfer.virtual_path, "Junk\\Song3.flac")
        self.assertEqual(transfer.status, TransferStatus.FINISHED)
        self.assertEqual(transfer.size, 27231044)
        self.assertEqual(transfer.current_byte_offset, 27231044)
        self.assertEqual(transfer.file_attributes, {
            FileAttribute.BITRATE: 792,
            FileAttribute.DURATION: 268
        })

    def test_save_uploads(self):
        """Verify that the order of the upload list at the end of the session
        is identical to the one we loaded.

        Ignore the first two unfinished uploads, since only finished uploads are
        saved to file.
        """

        old_transfers = core.uploads._load_transfers_file(TRANSFERS_FILE_PATH)[2:]
        core.uploads._save_transfers()
        saved_transfers = core.uploads._load_transfers_file(SAVED_TRANSFERS_FILE_PATH)

        self.assertEqual(old_transfers, saved_transfers)

    def test_push_upload(self):
        """Verify that non-existent files are not added to the list."""

        core.uploads.enqueue_upload("newuser2", "Hello\\Upload\\File.mp3")
        core.uploads.enqueue_upload("newuser99", "Home\\None.mp3")

        self.assertEqual(len(core.uploads.transfers.values()), 3)
