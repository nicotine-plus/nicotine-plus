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

from pynicotine.config import config
from pynicotine.search import Search

SEARCH_TEXT = '70 gwen "test" -mp3 -nothanks a:b;c+d +++---}[ *ello [[ @@ auto -no yes'
SEARCH_MODE = 'global'


class SearchTest(unittest.TestCase):

    def setUp(self):

        config.data_dir = os.path.dirname(os.path.realpath(__file__))
        config.filename = os.path.join(config.data_dir, "temp_config")

        config.load_config()

        self.search = Search(None, config, deque(), None, None)

    def test_do_search(self):
        """ Test the do_search function, including the outgoing search term and search history """

        old_searchid = self.search.get_current_search_id()

        # Try a search with special characters removed

        config.sections["searches"]["remove_special_chars"] = True
        searchid, searchterm, searchterm_without_special = self.search.do_search(SEARCH_TEXT, SEARCH_MODE)

        self.assertEqual(searchid, self.search.get_current_search_id())
        self.assertEqual(searchid, old_searchid + 1)
        self.assertEqual(searchterm, "70 gwen test a b c d auto yes -mp3 -nothanks *ello -no")
        self.assertEqual(searchterm_without_special, "70 gwen test a b c d auto yes")
        self.assertEqual(config.sections["searches"]["history"][0], searchterm)

        # Try a search without special characters removed

        config.sections["searches"]["remove_special_chars"] = False
        searchid, searchterm, searchterm_without_special = self.search.do_search(SEARCH_TEXT, SEARCH_MODE)

        self.assertEqual(searchterm, '70 gwen "test" a:b;c+d +++---}[ [[ @@ auto yes -mp3 -nothanks *ello -no')
        self.assertEqual(searchterm_without_special, '70 gwen "test" a:b;c+d +++---}[ [[ @@ auto yes')
        self.assertEqual(config.sections["searches"]["history"][0], searchterm)
        self.assertEqual(config.sections["searches"]["history"][1],
                         "70 gwen test a b c d auto yes -mp3 -nothanks *ello -no")

    def test_search_id_increment(self):
        """ Test that search ID increments work properly """

        old_searchid = self.search.get_current_search_id()

        searchid = self.search.increment_search_id()
        self.assertEqual(old_searchid, searchid - 1)
        self.assertEqual(searchid, self.search.get_current_search_id())

    def test_wishlist_add(self):
        """ Test that items are added to the wishlist properly """

        old_searchid = self.search.get_current_search_id()

        # First item

        self.search.add_wish(SEARCH_TEXT)
        self.assertEqual(config.sections["server"]["autosearch"][0], SEARCH_TEXT)
        self.assertEqual(self.search.searchid, old_searchid + 1)
        self.assertEqual(self.search.searchid, self.search.get_current_search_id())

        # Second item

        new_item = SEARCH_TEXT + "1"
        self.search.add_wish(new_item)
        self.assertEqual(config.sections["server"]["autosearch"][0], SEARCH_TEXT)
        self.assertEqual(config.sections["server"]["autosearch"][1], new_item)
