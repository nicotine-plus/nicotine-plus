# COPYRIGHT (C) 2021 Nicotine+ Team
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
import unittest

from collections import deque
from unittest.mock import Mock

from pynicotine.config import Config
from pynicotine.transfers import Transfers


class TransfersTest(unittest.TestCase):

    def setUp(self):

        self.config = Config()
        self.config.data_dir = os.path.dirname(os.path.realpath(__file__))
        self.config.filename = os.path.join(self.config.data_dir, "temp_config")

        self.config.load_config()

        self.transfers = Transfers(Mock(), self.config, Mock(), deque(), {}, Mock())

    def test_load_downloads(self):
        """ Test loading a downloads.json file """

        self.assertEqual(len(self.transfers.queue), 2)
        self.assertEqual(len(self.transfers.downloads), 13)

        transfer = self.transfers.downloads[0]

        self.assertEqual(transfer.user, "user13")
        self.assertEqual(transfer.filename, "Downloaded\\Song13.mp3")
        self.assertEqual(transfer.status, "Getting status")
        self.assertIsNone(transfer.size)
        self.assertIsNone(transfer.currentbytes)
        self.assertIsNone(transfer.bitrate)
        self.assertIsNone(transfer.length)

        transfer = self.transfers.downloads[12]

        self.assertEqual(transfer.user, "user1")
        self.assertEqual(transfer.filename, "Downloaded\\Song1.mp3")
        self.assertEqual(transfer.status, "Aborted")
        self.assertEqual(transfer.size, 10093741)
        self.assertEqual(transfer.currentbytes, 5000)
        self.assertEqual(transfer.bitrate, "320")
        self.assertEqual(transfer.length, "4:12")

    def test_save_downloads(self):
        """ Verify that the order of the download list at the end of the sesson
        is identical to the one we loaded. Ignore transfer 13, since its missing
        properties will be added at the end of the session. """

        self.transfers.abort_transfers()

        old_transfers = self.transfers.load_current_transfers_format(
            self.transfers.downloads_file_name)[:12]

        saved_transfers = self.transfers.get_downloads()[:12]
        self.assertEqual(old_transfers, saved_transfers)

    def test_load_uploads(self):
        """ Test loading a uploads.json file """

        # Only finished uploads are loaded, other types should never be stored
        self.assertEqual(len(self.transfers.uploads), 3)
        self.assertEqual(len(self.transfers.queue), 2)

        transfer = self.transfers.uploads[0]

        self.assertEqual(transfer.user, "user5")
        self.assertEqual(transfer.filename, "Junk\\Song5.mp3")
        self.assertEqual(transfer.status, "Finished")
        self.assertEqual(transfer.size, 11733776)
        self.assertEqual(transfer.currentbytes, 11733776)
        self.assertEqual(transfer.bitrate, "319")
        self.assertEqual(transfer.length, "4:53")

        transfer = self.transfers.uploads[2]

        self.assertEqual(transfer.user, "user3")
        self.assertEqual(transfer.filename, "Junk\\Song3.flac")
        self.assertEqual(transfer.status, "Finished")
        self.assertEqual(transfer.size, 27231044)
        self.assertEqual(transfer.currentbytes, 27231044)
        self.assertEqual(transfer.bitrate, "792")
        self.assertEqual(transfer.length, "4:28")

    def test_queue_download(self):
        """ Verify that new downloads are prepended to the list """

        self.transfers.get_file("newuser", "Hello\\Path\\File.mp3", "")
        transfer = self.transfers.downloads[0]

        self.assertEqual(transfer.user, "newuser")
        self.assertEqual(transfer.filename, "Hello\\Path\\File.mp3")
        self.assertEqual(transfer.path, "")

    def test_push_upload(self):
        """ Verify that new uploads are prepended to the list """

        self.transfers.push_file("newuser2", "Hello\\Upload\\File.mp3", "/home/test")
        self.transfers.push_file("newuser99", "Home\\None.mp3", "")
        transfer = self.transfers.uploads[1]

        self.assertEqual(transfer.user, "newuser2")
        self.assertEqual(transfer.filename, "Hello\\Upload\\File.mp3")
        self.assertEqual(transfer.path, "/home/test")
