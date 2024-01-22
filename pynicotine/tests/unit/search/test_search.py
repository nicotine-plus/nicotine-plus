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

from pynicotine.config import config
from pynicotine.core import core
from pynicotine.slskmessages import increment_token

SEARCH_TEXT = '70 - * Gwen "test" "" -mp3 "what\'s up" don\'t -nothanks a:::b;c+d +++---}[ *ello [[ @@ auto -No yes'
SEARCH_MODE = "global"


class SearchTest(TestCase):

    def setUp(self):

        config.data_folder_path = os.path.dirname(os.path.realpath(__file__))
        config.config_file_path = os.path.join(config.data_folder_path, "temp_config")

        core.init_components(enabled_components={"pluginhandler", "search"})

    def tearDown(self):

        core.quit()

        self.assertIsNone(core.pluginhandler)
        self.assertIsNone(core.search)

    def test_do_search(self):
        """Test the do_search function, including the outgoing search term and
        search history."""

        old_token = core.search.token
        search_term, search_term_no_quotes, included_words, excluded_words = core.search.sanitize_search_term(
            SEARCH_TEXT
        )
        core.search.do_search(SEARCH_TEXT, SEARCH_MODE)

        self.assertEqual(core.search.token, old_token + 1)
        self.assertEqual(search_term, '70 Gwen "test" -mp3 "what\'s up" don t -nothanks a b c d *ello auto -No yes')
        self.assertEqual(
            search_term_no_quotes, '70 Gwen test -mp3 what s up don t -nothanks a b c d *ello auto -No yes'
        )
        self.assertEqual(config.sections["searches"]["history"][0], search_term)
        self.assertIn("ello", included_words)
        self.assertIn("gwen", included_words)
        self.assertIn("what's up", included_words)
        self.assertIn("don", included_words)
        self.assertIn("t", included_words)
        self.assertIn("no", excluded_words)
        self.assertIn("mp3", excluded_words)

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
        self.assertEqual(config.sections["server"]["autosearch"][0], SEARCH_TEXT)
        self.assertEqual(core.search.token, old_token + 1)
        self.assertEqual(core.search.token, core.search.token)

        # Second item

        new_item = f"{SEARCH_TEXT}1"
        core.search.add_wish(new_item)
        self.assertEqual(config.sections["server"]["autosearch"][0], SEARCH_TEXT)
        self.assertEqual(config.sections["server"]["autosearch"][1], new_item)

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

        results = core.search._create_search_result_list(  # pylint: disable=protected-access
            included_words, excluded_words, partial_words, max_results, word_index)
        self.assertEqual(results, {37, 38})

        included_words = {"lts", "iso"}
        excluded_words = {"linux", "game", "music", "cd"}
        partial_words = set()

        results = core.search._create_search_result_list(  # pylint: disable=protected-access
            included_words, excluded_words, partial_words, max_results, word_index)
        self.assertEqual(results, set())

        included_words = {"iso"}
        excluded_words = {"system"}
        partial_words = {"ibberish"}

        results = core.search._create_search_result_list(  # pylint: disable=protected-access
            included_words, excluded_words, partial_words, max_results, word_index)
        self.assertEqual(results, set())
