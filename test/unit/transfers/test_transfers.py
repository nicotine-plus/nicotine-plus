# COPYRIGHT (C) 2021-2022 Nicotine+ Contributors
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
from collections import OrderedDict
from unittest.mock import MagicMock
from unittest.mock import Mock

from pynicotine.config import config
from pynicotine.userbrowse import UserBrowse
from pynicotine.transfers import Transfers


class TransfersTest(unittest.TestCase):

    def setUp(self):

        config.data_dir = os.path.dirname(os.path.realpath(__file__))
        config.filename = os.path.join(config.data_dir, "temp_config")

        config.load_config()
        config.sections["transfers"]["downloaddir"] = config.data_dir

        self.transfers = Transfers(MagicMock(), config, deque(), Mock())
        self.transfers.init_transfers()
        self.transfers.server_login()
        self.transfers.allow_saving_transfers = False

        self.userbrowse = UserBrowse(MagicMock(), config, Mock())
        self.userbrowse.core.transfers = self.transfers

    def test_load_downloads(self):
        """ Test loading a downloads.json file """

        self.assertEqual(len(self.transfers.queue), 2)
        self.assertEqual(len(self.transfers.downloads), 13)

        transfer = self.transfers.downloads[0]

        self.assertEqual(transfer.user, "user13")
        self.assertEqual(transfer.filename, "Downloaded\\Song13.mp3")
        self.assertEqual(transfer.status, "User logged off")
        self.assertEqual(transfer.size, 0)
        self.assertIsNone(transfer.current_byte_offset)
        self.assertIsNone(transfer.bitrate)
        self.assertIsNone(transfer.length)

        transfer = self.transfers.downloads[12]

        self.assertEqual(transfer.user, "user1")
        self.assertEqual(transfer.filename, "Downloaded\\Song1.mp3")
        self.assertEqual(transfer.status, "Paused")
        self.assertEqual(transfer.size, 10093741)
        self.assertEqual(transfer.current_byte_offset, 5000)
        self.assertEqual(transfer.bitrate, "320")
        self.assertEqual(transfer.length, "4:12")

    def test_save_downloads(self):
        """ Verify that the order of the download list at the end of the session
        is identical to the one we loaded. Ignore transfer 13, since its missing
        properties will be added at the end of the session. """

        self.transfers.abort_transfers()

        old_transfers = self.transfers.load_transfers_file(self.transfers.downloads_file_name)[:12]

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
        self.assertEqual(transfer.current_byte_offset, 11733776)
        self.assertIsNone(transfer.bitrate)
        self.assertIsNone(transfer.length)

        transfer = self.transfers.uploads[2]

        self.assertEqual(transfer.user, "user3")
        self.assertEqual(transfer.filename, "Junk\\Song3.flac")
        self.assertEqual(transfer.status, "Finished")
        self.assertEqual(transfer.size, 27231044)
        self.assertEqual(transfer.current_byte_offset, 27231044)
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

        self.transfers.push_file("newuser2", "Hello\\Upload\\File.mp3", 2000, "/home/test")
        self.transfers.push_file("newuser99", "Home\\None.mp3", 100, "/home/more")
        transfer = self.transfers.uploads[1]

        self.assertEqual(transfer.user, "newuser2")
        self.assertEqual(transfer.filename, "Hello\\Upload\\File.mp3")
        self.assertEqual(transfer.path, "/home/test")

    def test_incomplete_download_path(self):
        """ Verify that the basename in incomplete download paths doesn't exceed 255 bytes.
        The basename can be shorter than 255 bytes when a truncated multi-byte character is discarded. """

        user = "abc"
        incomplete_folder = "incomplete_downloads"

        # Short file extension
        virtual_path = ("Music\\Test\\片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片"
                        + "片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片.mp3")
        incomplete_path = self.transfers.get_incomplete_file_path(incomplete_folder, user, virtual_path)

        self.assertEqual(len(os.path.basename(incomplete_path).encode('utf-8')), 253)
        self.assertEqual(
            incomplete_path,
            os.path.join(
                incomplete_folder,
                ("INCOMPLETEeded5d7eb6768cac99e7575549a45126片片片片片片片片片片片片片片片片片片片片片片片片"
                 "片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片.mp3")
            )
        )

        # Long file extension
        virtual_path = ("Music\\Test\\abc123456.片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片"
                        + "片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片")
        incomplete_path = self.transfers.get_incomplete_file_path(incomplete_folder, user, virtual_path)

        self.assertEqual(len(os.path.basename(incomplete_path).encode('utf-8')), 253)
        self.assertEqual(
            incomplete_path,
            os.path.join(
                incomplete_folder,
                ("INCOMPLETEcc5054eeb2a488b3a0287fda4c938ef2.片片片片片片片片片片片片片片片片片片片片片片片"
                 "片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片")
            )
        )

    def test_download_folder_destination(self):
        """ Verify that the correct download destination is used """

        user = "newuser"
        folder = "Hello\\Path"
        destination_default = self.transfers.get_folder_destination(user, folder)

        self.transfers.requested_folders[user][folder] = "test"
        destination_custom = self.transfers.get_folder_destination(user, folder)

        config.sections["transfers"]["usernamesubfolders"] = True
        destination_user = self.transfers.get_folder_destination(user, folder)

        folder = "Hello"
        destination_root = self.transfers.get_folder_destination(user, folder)

        folder = "Hello\\Path\\Depth\\Test"
        destination_depth = self.transfers.get_folder_destination(user, folder)

        self.assertEqual(destination_default, os.path.join(config.data_dir, "Path"))
        self.assertEqual(destination_custom, os.path.join("test", "Path"))
        self.assertEqual(destination_user, os.path.join(config.data_dir, "newuser", "Path"))
        self.assertEqual(destination_root, os.path.join(config.data_dir, "newuser", "Hello"))
        self.assertEqual(destination_depth, os.path.join(config.data_dir, "newuser", "Test"))

    def test_download_subfolders(self):
        """ Verify that subfolders are downloaded to the correct location """

        user = "random"
        target_folder = "share\\Soulseek"

        shares_list = OrderedDict([
            ('share\\Music', [
                (1, 'music1.mp3', 1000000, '', {}),
                (1, 'music2.mp3', 2000000, '', {})
            ]),
            ('share\\Soulseek', [
                (1, 'file1.mp3', 3000000, '', {}),
                (1, 'file2.mp3', 4000000, '', {})
            ]),
            ('share\\Soulseek\\folder1', [
                (1, 'file3.mp3', 5000000, '', {})
            ]),
            ('share\\Soulseek\\folder1\\folder', [
                (1, 'file4.mp3', 6000000, '', {})
            ]),
            ('share\\Soulseek\\folder2', [
                (1, 'file5.mp3', 7000000, '', {})
            ]),
            ('share\\Soulseek\\folder2\\folder3', [
                (1, 'file6.mp3', 8000000, '', {})
            ])
        ])

        self.transfers.downloads.clear()
        self.userbrowse.download_folder(user, target_folder, shares_list, prefix="test", recurse=True)

        self.assertEqual(len(self.transfers.downloads), 6)

        self.assertEqual(self.transfers.downloads[0].path, os.path.join("test", "Soulseek", "folder2", "folder3"))
        self.assertEqual(self.transfers.downloads[1].path, os.path.join("test", "Soulseek", "folder2"))
        self.assertEqual(self.transfers.downloads[2].path, os.path.join("test", "Soulseek", "folder1", "folder"))
        self.assertEqual(self.transfers.downloads[3].path, os.path.join("test", "Soulseek", "folder1"))
        self.assertEqual(self.transfers.downloads[4].path, os.path.join("test", "Soulseek"))
        self.assertEqual(self.transfers.downloads[5].path, os.path.join("test", "Soulseek"))
