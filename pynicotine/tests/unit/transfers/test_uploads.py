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

from unittest import TestCase

from pynicotine import slskmessages
from pynicotine.config import config
from pynicotine.core import core
from pynicotine.transfers import TransferStatus


class UploadsTest(TestCase):

    # pylint: disable=protected-access

    def setUp(self):

        config.data_folder_path = os.path.dirname(os.path.realpath(__file__))
        config.config_file_path = os.path.join(config.data_folder_path, "temp_config")

        core.init_components(enabled_components={"users", "shares", "uploads", "userbrowse", "buddies"})

        core.start()
        core.uploads._allow_saving_transfers = False

    def tearDown(self):

        core.quit()

        self.assertIsNone(core.users)
        self.assertIsNone(core.shares)
        self.assertIsNone(core.uploads)
        self.assertIsNone(core.userbrowse)
        self.assertIsNone(core.buddies)

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
            slskmessages.FileAttribute.BITRATE: 792,
            slskmessages.FileAttribute.DURATION: 268
        })

    def test_save_uploads(self):
        """Verify that the order of the upload list at the end of the session
        is identical to the one we loaded.

        Ignore the first two unfinished uploads, since only finished uploads are
        saved to file.
        """

        old_transfers = core.uploads._load_transfers_file(core.uploads.transfers_file_path)[2:]

        saved_transfers = core.uploads._get_transfer_rows()
        self.assertEqual(old_transfers, saved_transfers)

    def test_push_upload(self):
        """Verify that new uploads are prepended to the list."""

        core.uploads.enqueue_upload("newuser2", "Hello\\Upload\\File.mp3", 2000, os.path.join(os.sep, "home", "test"))
        core.uploads.enqueue_upload("newuser99", "Home\\None.mp3", 100, os.path.join(os.sep, "home", "more"))

        transfer = list(core.uploads.transfers.values())[3]

        self.assertEqual(transfer.username, "newuser2")
        self.assertEqual(transfer.virtual_path, "Hello\\Upload\\File.mp3")
        self.assertEqual(transfer.folder_path, os.path.join(os.sep, "home", "test"))
