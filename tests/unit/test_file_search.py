__author__ = 'Lene Preuss <lene.preuss@gmail.com>'

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
    assert [b for b in search.makeNetworkMessage()] == SEARCH_NETWORK_VALUE


def test_sent_out_message():
    search = FileSearch(requestid=SEARCH_ID, text=SEARCH_TEXT)
    msg = search.makeNetworkMessage()
    out_msg = struct.pack("<ii", len(msg) + 4, SlskProtoThread.servercodes[search.__class__]) + msg
    assert [b for b in out_msg] == SEARCH_OUT_MSG
