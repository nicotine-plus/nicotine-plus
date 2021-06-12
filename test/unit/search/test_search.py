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
import pytest

from collections import deque

from pynicotine.config import Config
from pynicotine.search import Search

SEARCH_TEXT = '70 gwen "test" -mp3 -nothanks a:b;c+d +++---}[ [[ @@ auto -no yes'
SEARCH_MODE = 'global'


@pytest.fixture
def config():
    config = Config()
    config.data_dir = os.path.dirname(os.path.realpath(__file__))
    config.filename = os.path.join(config.data_dir, "temp_config")

    config.load_config()
    return config


@pytest.fixture
def search(config):
    return Search(None, config, deque(), None)


def test_do_search(config, search):
    """ Test the do_search function, including the outgoing search term and search history """

    old_searchid = search.get_current_search_id()

    # Try a search with special characters removed

    config.sections["searches"]["remove_special_chars"] = True
    searchid, searchterm_with_excluded, searchterm_without_excluded = search.do_search(SEARCH_TEXT, SEARCH_MODE)

    assert searchid == search.get_current_search_id()
    assert searchid == old_searchid + 1
    assert searchterm_with_excluded == "70 gwen test a b c d auto yes -mp3 -nothanks -no"
    assert searchterm_without_excluded == "70 gwen test a b c d auto yes"
    assert config.sections["searches"]["history"][0] == searchterm_with_excluded

    # Try a search without special characters removed

    config.sections["searches"]["remove_special_chars"] = False
    searchid, searchterm_with_excluded, searchterm_without_excluded = search.do_search(SEARCH_TEXT, SEARCH_MODE)

    assert searchterm_with_excluded == '70 gwen "test" a:b;c+d +++---}[ [[ @@ auto yes -mp3 -nothanks -no'
    assert searchterm_without_excluded == '70 gwen "test" a:b;c+d +++---}[ [[ @@ auto yes'
    assert config.sections["searches"]["history"][0] == searchterm_with_excluded
    assert config.sections["searches"]["history"][1] == "70 gwen test a b c d auto yes -mp3 -nothanks -no"


def test_search_id_increment(config, search):
    """ Test that search ID increments work properly """

    old_searchid = search.get_current_search_id()

    searchid = search.increment_search_id()
    assert old_searchid == searchid - 1
    assert searchid == search.get_current_search_id()


def test_wishlist_add(config, search):
    """ Test that items are added to the wishlist properly """

    old_searchid = search.get_current_search_id()

    # First item

    searchid = search.add_wish(SEARCH_TEXT)
    assert config.sections["server"]["autosearch"][0] == SEARCH_TEXT
    assert searchid == old_searchid + 1
    assert searchid == search.get_current_search_id()

    # Second item

    new_item = SEARCH_TEXT + "1"
    search.add_wish(new_item)
    assert config.sections["server"]["autosearch"][0] == SEARCH_TEXT
    assert config.sections["server"]["autosearch"][1] == new_item
