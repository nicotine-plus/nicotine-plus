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
from pynicotine.downloads import RequestedFolder
from pynicotine.transfers import TransferStatus
from pynicotine.userbrowse import BrowsedUser


class DownloadsTest(TestCase):

    # pylint: disable=protected-access

    def setUp(self):

        config.data_folder_path = os.path.dirname(os.path.realpath(__file__))
        config.config_file_path = os.path.join(config.data_folder_path, "temp_config")

        core.init_components(enabled_components={"users", "shares", "downloads", "userbrowse", "buddies"})
        config.sections["transfers"]["downloaddir"] = config.data_folder_path

        core.start()
        core.downloads._allow_saving_transfers = False

    def tearDown(self):

        core.quit()

        self.assertIsNone(core.users)
        self.assertIsNone(core.shares)
        self.assertIsNone(core.downloads)
        self.assertIsNone(core.userbrowse)
        self.assertIsNone(core.buddies)

    def test_load_downloads(self):
        """Test loading a downloads.json file."""

        transfers = list(core.downloads.transfers.values())
        self.assertEqual(len(transfers), 17)

        transfer = transfers[16]

        self.assertEqual(transfer.username, "user17")
        self.assertEqual(transfer.virtual_path, "Downloaded\\Song17.mp3")
        self.assertEqual(transfer.status, TransferStatus.USER_LOGGED_OFF)
        self.assertEqual(transfer.size, 0)
        self.assertIsNone(transfer.current_byte_offset)
        self.assertFalse(transfer.file_attributes)

        transfer = transfers[0]

        self.assertEqual(transfer.username, "user1")
        self.assertEqual(transfer.virtual_path, "Downloaded\\Song1.mp3")
        self.assertEqual(transfer.status, TransferStatus.PAUSED)
        self.assertEqual(transfer.size, 10093741)
        self.assertEqual(transfer.current_byte_offset, 5000)
        self.assertEqual(transfer.file_attributes, {
            slskmessages.FileAttribute.BITRATE: 320,
            slskmessages.FileAttribute.DURATION: 252
        })

        # File attribute dictionary represented as string (downgrade from >=3.3.0 to earlier and upgrade again)
        self.assertEqual(transfers[15].file_attributes, {
            slskmessages.FileAttribute.BITRATE: 256,
            slskmessages.FileAttribute.DURATION: 476
        })

        # Legacy bitrate/duration strings (Nicotine+ <3.3.0)
        self.assertEqual(transfers[14].file_attributes, {
            slskmessages.FileAttribute.BITRATE: 128,
            slskmessages.FileAttribute.DURATION: 290
        })

        # Legacy bitrate/duration strings (vbr) (Nicotine+ <3.3.0)
        self.assertEqual(transfers[13].file_attributes, {
            slskmessages.FileAttribute.BITRATE: 238,
            slskmessages.FileAttribute.VBR: 1,
            slskmessages.FileAttribute.DURATION: 173
        })

        # Empty legacy bitrate/duration strings (Nicotine+ <3.3.0)
        self.assertFalse(transfers[12].file_attributes)

    def test_save_downloads(self):
        """Verify that the order of the download list at the end of the session
        is identical to the one we loaded.

        Ignore the last four transfers, since their missing properties
        will be added at the end of the session.
        """

        old_transfers = core.downloads._load_transfers_file(core.downloads.transfers_file_path)[:12]

        saved_transfers = core.downloads._get_transfer_rows()[:12]
        self.assertEqual(old_transfers, saved_transfers)

    def test_queue_download(self):
        """Verify that new downloads are prepended to the list."""

        config.sections["transfers"]["usernamesubfolders"] = False

        core.downloads.enqueue_download("newuser", "Hello\\Path\\File.mp3", "")
        transfer = list(core.downloads.transfers.values())[-1]

        self.assertEqual(transfer.username, "newuser")
        self.assertEqual(transfer.virtual_path, "Hello\\Path\\File.mp3")
        self.assertEqual(transfer.folder_path, config.data_folder_path)

    def test_long_basename(self):
        """Verify that the basename in download paths doesn't exceed 255 bytes.

        The basename can be shorter than 255 bytes when a truncated
        multi-byte character is discarded.
        """

        username = "abc"
        finished_folder_path = os.path.join(os.sep, "path", "to", "somewhere", "downloads")

        # Short file extension
        virtual_path = ("Music\\Test\\片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片"
                        "片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片"
                        "片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片.mp3")
        incomplete_file_path = core.downloads.get_incomplete_download_file_path(username, virtual_path)
        incomplete_basename = os.path.basename(incomplete_file_path)

        self.assertLess(
            len(incomplete_basename.encode("utf-8")),
            core.downloads.get_basename_byte_limit(config.data_folder_path)
        )
        self.assertTrue(incomplete_basename.startswith("INCOMPLETE42d26e9276e024cdaeac645438912b88"))
        self.assertTrue(incomplete_basename.endswith(".mp3"))

        # Long file extension
        virtual_path = ("Music\\Test\\abc123456.片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片"
                        "片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片"
                        "片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片")
        incomplete_file_path = core.downloads.get_incomplete_download_file_path(username, virtual_path)
        incomplete_basename = os.path.basename(incomplete_file_path)

        self.assertLess(
            len(incomplete_basename.encode("utf-8")),
            core.downloads.get_basename_byte_limit(config.data_folder_path)
        )
        self.assertTrue(incomplete_basename.startswith("INCOMPLETEf98e3f07a3fc60e114534045f26707d2."))
        self.assertTrue(incomplete_basename.endswith("片"))

        # Finished download
        basename = ("片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片"
                    "片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片"
                    "片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片.mp3")
        finished_basename = core.downloads.get_download_basename(basename, finished_folder_path)

        self.assertLess(
            len(finished_basename.encode("utf-8")),
            core.downloads.get_basename_byte_limit(config.data_folder_path)
        )
        self.assertTrue(finished_basename.startswith("片"))
        self.assertTrue(finished_basename.endswith(".mp3"))

        basename = ("abc123456.片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片"
                    "片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片"
                    "片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片片")
        finished_basename = core.downloads.get_download_basename(basename, finished_folder_path)

        self.assertLess(
            len(finished_basename.encode("utf-8")),
            core.downloads.get_basename_byte_limit(config.data_folder_path)
        )
        self.assertTrue(finished_basename.startswith(".片"))
        self.assertTrue(finished_basename.endswith("片"))

    def test_download_folder_destination(self):
        """Verify that the correct download destination is used."""

        username = "newuser"
        folder_path = "Hello\\Path"
        config.sections["transfers"]["usernamesubfolders"] = False
        destination_default = core.downloads.get_folder_destination(username, folder_path)

        core.downloads._requested_folders[username][folder_path] = RequestedFolder(
            username=username, folder_path=folder_path, download_folder_path="test"
        )
        destination_custom = core.downloads.get_folder_destination(username, folder_path)
        core.downloads._requested_folders.clear()

        destination_custom_second = core.downloads.get_folder_destination(
            username, folder_path, download_folder_path="test2")

        config.sections["transfers"]["usernamesubfolders"] = True
        destination_user = core.downloads.get_folder_destination(username, folder_path)

        folder_path = "Hello"
        destination_root = core.downloads.get_folder_destination(username, folder_path)

        folder_path = "Hello\\Path\\Depth\\Test"
        destination_depth = core.downloads.get_folder_destination(username, folder_path)

        self.assertEqual(destination_default, os.path.join(config.data_folder_path, "Path"))
        self.assertEqual(destination_custom, os.path.join("test", "Path"))
        self.assertEqual(destination_custom_second, os.path.join("test2", "Path"))
        self.assertEqual(destination_user, os.path.join(config.data_folder_path, "newuser", "Path"))
        self.assertEqual(destination_root, os.path.join(config.data_folder_path, "newuser", "Hello"))
        self.assertEqual(destination_depth, os.path.join(config.data_folder_path, "newuser", "Test"))

    def test_download_subfolders(self):
        """Verify that subfolders are downloaded to the correct location."""

        username = "random"
        browsed_user = core.userbrowse.users[username] = BrowsedUser(username)
        browsed_user.public_folders = dict([
            ("share", [
                (1, "root1.mp3", 1000, "", {})
            ]),
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
            ("share\\Soulseek\\folder1\\sub1", [
                (1, "file4.mp3", 6000000, "", {})
            ]),
            ("share\\Soulseek\\folder2", [
                (1, "file5.mp3", 7000000, "", {})
            ]),
            ("share\\Soulseek\\folder2\\sub2", [
                (1, "file6.mp3", 8000000, "", {})
            ]),
            ("share\\SoulseekSecond", [
                (1, "file7.mp3", 9000000, "", {}),
                (1, "file8.mp3", 10000000, "", {})
            ])
        ])

        # Share root
        target_folder_path = "share"

        core.downloads.transfers.clear()
        core.userbrowse.download_folder(username, target_folder_path, download_folder_path="test", recurse=True)

        transfers = list(core.downloads.transfers.values())
        self.assertEqual(len(transfers), 11)

        self.assertEqual(transfers[10].folder_path, os.path.join("test", "share", "SoulseekSecond"))
        self.assertEqual(transfers[9].folder_path, os.path.join("test", "share", "SoulseekSecond"))
        self.assertEqual(transfers[8].folder_path, os.path.join("test", "share", "Soulseek", "folder2", "sub2"))
        self.assertEqual(transfers[7].folder_path, os.path.join("test", "share", "Soulseek", "folder2"))
        self.assertEqual(transfers[6].folder_path, os.path.join("test", "share", "Soulseek", "folder1", "sub1"))
        self.assertEqual(transfers[5].folder_path, os.path.join("test", "share", "Soulseek", "folder1"))
        self.assertEqual(transfers[4].folder_path, os.path.join("test", "share", "Soulseek"))
        self.assertEqual(transfers[3].folder_path, os.path.join("test", "share", "Soulseek"))
        self.assertEqual(transfers[2].folder_path, os.path.join("test", "share", "Music"))
        self.assertEqual(transfers[1].folder_path, os.path.join("test", "share", "Music"))
        self.assertEqual(transfers[0].folder_path, os.path.join("test", "share"))

        # Share subfolder
        target_folder_path = "share\\Soulseek"

        core.downloads.transfers.clear()
        core.userbrowse.download_folder(username, target_folder_path, download_folder_path="test2", recurse=True)

        transfers = list(core.downloads.transfers.values())
        self.assertEqual(len(transfers), 6)

        self.assertEqual(transfers[5].folder_path, os.path.join("test2", "Soulseek", "folder2", "sub2"))
        self.assertEqual(transfers[4].folder_path, os.path.join("test2", "Soulseek", "folder2"))
        self.assertEqual(transfers[3].folder_path, os.path.join("test2", "Soulseek", "folder1", "sub1"))
        self.assertEqual(transfers[2].folder_path, os.path.join("test2", "Soulseek", "folder1"))
        self.assertEqual(transfers[1].folder_path, os.path.join("test2", "Soulseek"))
        self.assertEqual(transfers[0].folder_path, os.path.join("test2", "Soulseek"))
