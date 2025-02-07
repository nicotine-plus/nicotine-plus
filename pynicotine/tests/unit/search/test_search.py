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

from collections import UserDict
from unittest import TestCase

from pynicotine.config import config
from pynicotine.core import core
from pynicotine.shares import PermissionLevel
from pynicotine.slskmessages import increment_token

DATA_FOLDER_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), "temp_data")
SEARCH_TEXT = '70 - * Gwen "test" "" -mp3 "what\'s up" don\'t -nothanks a:::b;c+d +++---}[ *ello [[ @@ auto -No yes'
SEARCH_MODE = "global"


class SearchTest(TestCase):

    # pylint: disable=protected-access

    def setUp(self):

        config.set_data_folder(DATA_FOLDER_PATH)
        config.set_config_file(os.path.join(DATA_FOLDER_PATH, "temp_config"))

        core.init_components(enabled_components={"pluginhandler", "search", "shares"})

    def tearDown(self):
        core.quit()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(DATA_FOLDER_PATH)

    def test_do_search(self):
        """Test the do_search function, including the outgoing search term and
        search history."""

        old_token = core.search.token
        core.search.do_search(SEARCH_TEXT, SEARCH_MODE)
        search = core.search.searches[core.search.token]

        self.assertEqual(core.search.token, old_token + 1)
        self.assertEqual(search.term, SEARCH_TEXT)
        self.assertEqual(
            search.term_sanitized, '70 Gwen "test" -mp3 "what\'s up" don t -nothanks a b c d *ello auto -No yes'
        )
        self.assertEqual(
            search.term_transmitted, '70 Gwen test -mp3 what s up don t -nothanks a b c d *ello auto -No yes'
        )
        self.assertEqual(config.sections["searches"]["history"][0], search.term_sanitized)
        self.assertIn("ello", search.included_words)
        self.assertIn("gwen", search.included_words)
        self.assertIn("what's up", search.included_words)
        self.assertIn("don", search.included_words)
        self.assertIn("t", search.included_words)
        self.assertIn("no", search.excluded_words)
        self.assertIn("mp3", search.excluded_words)

    def test_search_token_increment(self):
        """Test that search token increments work properly."""

        old_token = core.search.token

        core.search.token = increment_token(core.search.token)
        self.assertEqual(old_token, core.search.token - 1)

    def test_wishlist_add(self):
        """Test that items are added to the wishlist properly."""

        old_token = core.search.token

        # First item

        core.search.add_wish(SEARCH_TEXT)
        search = core.search.searches[core.search.token]

        self.assertEqual(config.sections["server"]["autosearch"][0], SEARCH_TEXT)
        self.assertEqual(core.search.token, old_token + 1)
        self.assertEqual(core.search.token, core.search.token)
        self.assertEqual(search.term, SEARCH_TEXT)
        self.assertEqual(search.mode, "wishlist")
        self.assertTrue(search.is_ignored)

        # Second item

        new_item = f"{SEARCH_TEXT}1"
        core.search.add_wish(new_item)
        search = core.search.searches[core.search.token]

        self.assertEqual(config.sections["server"]["autosearch"][0], SEARCH_TEXT)
        self.assertEqual(config.sections["server"]["autosearch"][1], new_item)
        self.assertEqual(search.term, new_item)
        self.assertEqual(search.mode, "wishlist")
        self.assertTrue(search.is_ignored)

    def test_create_search_result_list(self):
        """Test creating search result lists from the word index."""

        max_results = 1500
        word_index = {
            "iso": [34, 35, 36, 37, 38],
            "lts": [63, 68, 73],
            "system": [37, 38],
            "linux": [35, 36]
        }

        included_words = {"iso"}
        excluded_words = {"linux", "game"}
        partial_words = {"stem"}

        results = core.search._create_search_result_list(
            included_words, excluded_words, partial_words, max_results, word_index)
        self.assertEqual(results, {37, 38})

        included_words = {"lts", "iso"}
        excluded_words = {"linux", "game", "music", "cd"}
        partial_words = set()

        results = core.search._create_search_result_list(
            included_words, excluded_words, partial_words, max_results, word_index)
        self.assertIsNone(results)

        included_words = {"iso"}
        excluded_words = {"system"}
        partial_words = {"ibberish"}

        results = core.search._create_search_result_list(
            included_words, excluded_words, partial_words, max_results, word_index)
        self.assertIsNone(results)

    def test_exclude_server_phrases(self):
        """Verify that results containing excluded phrases are not included."""

        core.search.excluded_phrases = ["linux distro", "netbsd"]
        results = {0, 1, 2, 3, 4, 5}
        public_share_db = core.shares.share_dbs["public_files"] = UserDict({
            "real\\isos\\freebsd.iso": ["virtual\\isos\\freebsd.iso", 1000, None, None],
            "real\\isos\\linux.iso": ["virtual\\isos\\linux.iso", 2000, None, None],
            "real\\isos\\linux distro.iso": ["virtual\\isos\\linux distro.iso", 3000, None, None],
            "real\\isos\\Linux Distro.iso": ["virtual\\isos\\Linux Distro.iso", 4000, None, None],
            "real\\isos\\NetBSD.iso": ["virtual\\isos\\NetBSD.iso", 5000, None, None],
            "real\\isos\\openbsd.iso": ["virtual\\isos\\openbsd.iso", 6000, None, None]
        })
        core.shares.share_dbs["buddy_files"] = core.shares.share_dbs["trusted_files"] = UserDict()
        core.shares.file_path_index = list(public_share_db)

        for share_db in core.shares.share_dbs.values():
            share_db.close = lambda: None

        num_results, fileinfos, private_fileinfos = core.search._create_file_info_list(
            results, max_results=100, permission_level=PermissionLevel.PUBLIC
        )
        self.assertEqual(num_results, 3)
        self.assertEqual(fileinfos, [
            ["virtual\\isos\\freebsd.iso", 1000, None, None],
            ["virtual\\isos\\linux.iso", 2000, None, None],
            ["virtual\\isos\\openbsd.iso", 6000, None, None]
        ])
        self.assertEqual(private_fileinfos, [])
