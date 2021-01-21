# COPYRIGHT (C) 2020-2021 Nicotine+ Team
# COPYRIGHT (C) 2020 Lene Preuss <lene.preuss@gmail.com>
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

import struct

from pynicotine.slskmessages import FileSearch
from pynicotine.slskproto import SlskProtoThread

# "Magic" values confirmed to work with nicotine+ 1.4.2
SEARCH_ID = 524700074
SEARCH_TEXT = '70 gwen auto'
SEARCH_NETWORK_VALUE = [
    170, 73, 70, 31, 12, 0, 0, 0,  # search id
    55, 48, 32, 103, 119, 101, 110, 32, 97, 117, 116, 111  # search text
]
SEARCH_OUT_MSG = [
    24, 0, 0, 0,  # length of message starting with next byte
    26, 0, 0, 0,  # server code for FileSearch
    170, 73, 70, 31, 12, 0, 0, 0,
    55, 48, 32, 103, 119, 101, 110, 32, 97, 117, 116, 111
]


def test_instantiate_file_search():
    search = FileSearch(requestid=SEARCH_ID, text=SEARCH_TEXT)
    assert search.searchid == SEARCH_ID
    assert search.searchterm == SEARCH_TEXT


def test_make_network_message():
    search = FileSearch(requestid=SEARCH_ID, text=SEARCH_TEXT)
    assert [b for b in search.make_network_message()] == SEARCH_NETWORK_VALUE


def test_sent_out_message():
    search = FileSearch(requestid=SEARCH_ID, text=SEARCH_TEXT)
    msg = search.make_network_message()
    out_msg = struct.pack("<ii", len(msg) + 4, SlskProtoThread.servercodes[search.__class__]) + msg
    assert [b for b in out_msg] == SEARCH_OUT_MSG
