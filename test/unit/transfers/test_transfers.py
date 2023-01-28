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

from unittest import TestCase
from unittest.mock import Mock

from pynicotine.config import config
from pynicotine.core import core


class TransfersTest(TestCase):

    def setUp(self):

        config.data_dir = os.path.dirname(os.path.realpath(__file__))
        config.filename = os.path.join(config.data_dir, "temp_config")

        core.init_components()
        config.sections["transfers"]["downloaddir"] = config.data_dir

        core.transfers._start()  # pylint: disable=protected-access
        core.transfers._server_login(Mock())  # pylint: disable=protected-access
        core.transfers.allow_saving_transfers = False

    def test_load_downloads(self):
        """ Test loading a downloads.json file """

        self.assertEqual(len(core.queue), 0)
        self.assertEqual(len(core.transfers.downloads), 13)

        transfer = core.transfers.downloads[0]

        self.assertEqual(transfer.user, "user13")
        self.assertEqual(transfer.filename, "Downloaded\\Song13.mp3")
        self.assertEqual(transfer.status, "User logged off")
        self.assertEqual(transfer.size, 0)
        self.assertIsNone(transfer.current_byte_offset)
        self.assertIsNone(transfer.bitrate)
        self.assertIsNone(transfer.length)

        transfer = core.transfers.downloads[12]

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

        core.transfers._server_disconnect(Mock())  # pylint: disable=protected-access

        old_transfers = core.transfers.load_transfers_file(core.transfers.downloads_file_name)[:12]

        saved_transfers = core.transfers.get_downloads()[:12]
        self.assertEqual(old_transfers, saved_transfers)

    def test_load_uploads(self):
        """ Test loading a uploads.json file """

        # Only finished uploads are loaded, other types should never be stored
        self.assertEqual(len(core.transfers.uploads), 3)
        self.assertEqual(len(core.queue), 0)

        transfer = core.transfers.uploads[0]

        self.assertEqual(transfer.user, "user5")
        self.assertEqual(transfer.filename, "Junk\\Song5.mp3")
        self.assertEqual(transfer.status, "Finished")
        self.assertEqual(transfer.size, 11733776)
        self.assertEqual(transfer.current_byte_offset, 11733776)
        self.assertIsNone(transfer.bitrate)
        self.assertIsNone(transfer.length)

        transfer = core.transfers.uploads[2]

        self.assertEqual(transfer.user, "user3")
        self.assertEqual(transfer.filename, "Junk\\Song3.flac")
        self.assertEqual(transfer.status, "Finished")
        self.assertEqual(transfer.size, 27231044)
        self.assertEqual(transfer.current_byte_offset, 27231044)
        self.assertEqual(transfer.bitrate, "792")
        self.assertEqual(transfer.length, "4:28")

    def test_queue_download(self):
        """ Verify that new downloads are prepended to the list """

        core.transfers.get_file("newuser", "Hello\\Path\\File.mp3", "")
        transfer = core.transfers.downloads[0]

        self.assertEqual(transfer.user, "newuser")
        self.assertEqual(transfer.filename, "Hello\\Path\\File.mp3")
        self.assertEqual(transfer.path, config.data_dir)

    def test_push_upload(self):
        """ Verify that new uploads are prepended to the list """

        core.transfers.push_file("newuser2", "Hello\\Upload\\File.mp3", 2000, "/home/test")
        core.transfers.push_file("newuser99", "Home\\None.mp3", 100, "/home/more")
        transfer = core.transfers.uploads[1]

        self.assertEqual(transfer.user, "newuser2")
        self.assertEqual(transfer.filename, "Hello\\Upload\\File.mp3")
        self.assertEqual(transfer.path, "/home/test")

    def test_long_basename(self):
        """ Verify that the basename in download paths doesn't exceed 255 bytes.
        The basename can be shorter than 255 bytes when a truncated multi-byte character is discarded. """

        user = "abc"
        finished_folder_path = "/path/to/somewhere/downloads"

        # Short file extension
        virtual_path = ("Music\\Test\\片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片"
                        "片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片"
                        "片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片.mp3")
        incomplete_file_path = core.transfers.get_incomplete_download_file_path(user, virtual_path)
        incomplete_basename = os.path.basename(incomplete_file_path)

        self.assertLess(
            len(incomplete_basename.encode("utf-8")),
            core.transfers.get_basename_byte_limit(config.data_dir)
        )
        self.assertTrue(incomplete_basename.startswith("INCOMPLETE42d26e9276e024cdaeac645438912b88"))
        self.assertTrue(incomplete_basename.endswith(".mp3"))

        # Long file extension
        virtual_path = ("Music\\Test\\abc123456.片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片"
                        "片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片"
                        "片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片")
        incomplete_file_path = core.transfers.get_incomplete_download_file_path(user, virtual_path)
        incomplete_basename = os.path.basename(incomplete_file_path)

        self.assertLess(
            len(incomplete_basename.encode("utf-8")),
            core.transfers.get_basename_byte_limit(config.data_dir)
        )
        self.assertTrue(incomplete_basename.startswith("INCOMPLETEf98e3f07a3fc60e114534045f26707d2."))
        self.assertTrue(incomplete_basename.endswith("片"))

        # Finished download
        basename = ("片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片"
                    "片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片"
                    "片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片.mp3")
        finished_basename = core.transfers.get_download_basename(basename, finished_folder_path)

        self.assertLess(
            len(finished_basename.encode("utf-8")),
            core.transfers.get_basename_byte_limit(config.data_dir)
        )
        self.assertTrue(finished_basename.startswith("片"))
        self.assertTrue(finished_basename.endswith(".mp3"))

        basename = ("abc123456.片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片"
                    "片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片"
                    "片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片")
        finished_basename = core.transfers.get_download_basename(basename, finished_folder_path)

        self.assertLess(
            len(finished_basename.encode("utf-8")),
            core.transfers.get_basename_byte_limit(config.data_dir)
        )
        self.assertTrue(finished_basename.startswith(".片"))
        self.assertTrue(finished_basename.endswith("片"))

    def test_download_folder_destination(self):
        """ Verify that the correct download destination is used """

        user = "newuser"
        folder = "Hello\\Path"
        destination_default = core.transfers.get_folder_destination(user, folder)

        core.transfers.requested_folders[user][folder] = "test"
        destination_custom = core.transfers.get_folder_destination(user, folder)

        config.sections["transfers"]["usernamesubfolders"] = True
        destination_user = core.transfers.get_folder_destination(user, folder)

        folder = "Hello"
        destination_root = core.transfers.get_folder_destination(user, folder)

        folder = "Hello\\Path\\Depth\\Test"
        destination_depth = core.transfers.get_folder_destination(user, folder)

        self.assertEqual(destination_default, os.path.join(config.data_dir, "Path"))
        self.assertEqual(destination_custom, os.path.join("test", "Path"))
        self.assertEqual(destination_user, os.path.join(config.data_dir, "newuser", "Path"))
        self.assertEqual(destination_root, os.path.join(config.data_dir, "newuser", "Hello"))
        self.assertEqual(destination_depth, os.path.join(config.data_dir, "newuser", "Test"))

    def test_download_subfolders(self):
        """ Verify that subfolders are downloaded to the correct location """

        user = "random"
        target_folder = "share\\Soulseek"

        core.userbrowse.user_shares[user] = dict([
            ("share\\Music", [
                (1, "music1.mp3", 1000000, "", {}),
                (1, "music2.mp3", 2000000, "", {})
            ]),
            ("share\\Soulseek", [
                (1, "file1.mp3", 3000000, "", {}),
                (1, "file2.mp3", 4000000, "", {})
            ]),
            ("share\\Soulseek\\folder1", [
                (1, "file3.mp3", 5000000, "", {})
            ]),
            ("share\\Soulseek\\folder1\\folder", [
                (1, "file4.mp3", 6000000, "", {})
            ]),
            ("share\\Soulseek\\folder2", [
                (1, "file5.mp3", 7000000, "", {})
            ]),
            ("share\\Soulseek\\folder2\\folder3", [
                (1, "file6.mp3", 8000000, "", {})
            ])
        ])

        core.transfers.downloads.clear()
        core.userbrowse.download_folder(user, target_folder, prefix="test", recurse=True)

        self.assertEqual(len(core.transfers.downloads), 6)

        self.assertEqual(core.transfers.downloads[0].path, os.path.join("test", "Soulseek", "folder2", "folder3"))
        self.assertEqual(core.transfers.downloads[1].path, os.path.join("test", "Soulseek", "folder2"))
        self.assertEqual(core.transfers.downloads[2].path, os.path.join("test", "Soulseek", "folder1", "folder"))
        self.assertEqual(core.transfers.downloads[3].path, os.path.join("test", "Soulseek", "folder1"))
        self.assertEqual(core.transfers.downloads[4].path, os.path.join("test", "Soulseek"))
        self.assertEqual(core.transfers.downloads[5].path, os.path.join("test", "Soulseek"))
