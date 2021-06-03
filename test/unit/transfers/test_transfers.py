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
from pynicotine.i18n import apply_translation
from pynicotine.pynicotine import NetworkEventProcessor
from pynicotine.transfers import Transfers


@pytest.fixture(scope="module", autouse=True)
def setup():
    # Setting gettext and locale
    apply_translation()


@pytest.fixture
def config():
    config = Config()
    config.data_dir = os.path.dirname(os.path.realpath(__file__))
    config.filename = os.path.join(config.data_dir, "temp_config")

    config.load_config()
    return config


@pytest.fixture
def transfers(config):
    network_processor = NetworkEventProcessor("0.0.0.0", 0)
    network_processor.start()
    return Transfers(config, None, deque(), network_processor, {}, network_processor.network_callback)


def test_load_downloads(transfers):
    """ Test loading a downloads.json file """

    assert len(transfers.queue) == 2
    assert len(transfers.downloads) == 13

    transfer = transfers.downloads[0]

    assert transfer.user == "user13"
    assert transfer.filename == "Downloaded\\Song13.mp3"
    assert transfer.status == "Getting status"
    assert transfer.size is None
    assert transfer.currentbytes is None
    assert transfer.bitrate is None
    assert transfer.length is None

    transfer = transfers.downloads[12]

    assert transfer.user == "user1"
    assert transfer.filename == "Downloaded\\Song1.mp3"
    assert transfer.status == "Aborted"
    assert transfer.size == 10093741
    assert transfer.currentbytes == 5000
    assert transfer.bitrate == "320"
    assert transfer.length == "4:12"


def test_load_uploads(transfers):
    """ Test loading a uploads.json file """

    # Only finished uploads are loaded, other types should never be stored
    assert len(transfers.uploads) == 3
    assert len(transfers.queue) == 2

    transfer = transfers.uploads[0]

    assert transfer.user == "user5"
    assert transfer.filename == "Junk\\Song5.mp3"
    assert transfer.status == "Finished"
    assert transfer.size == 11733776
    assert transfer.currentbytes == 11733776
    assert transfer.bitrate == "319"
    assert transfer.length == "4:53"

    transfer = transfers.uploads[2]

    assert transfer.user == "user3"
    assert transfer.filename == "Junk\\Song3.flac"
    assert transfer.status == "Finished"
    assert transfer.size == 27231044
    assert transfer.currentbytes == 27231044
    assert transfer.bitrate == "792"
    assert transfer.length == "4:28"


def test_queue_download(transfers):
    """ Verify that new downloads are prepended to the list """

    transfers.get_file("newuser", "Hello\\Path\\File.mp3", "")
    transfer = transfers.downloads[0]

    assert transfer.user == "newuser"
    assert transfer.filename == "Hello\\Path\\File.mp3"
    assert transfer.path == ""


def test_push_upload(transfers):
    """ Verify that new uploads are prepended to the list """

    transfers.push_file("newuser2", "Hello\\Upload\\File.mp3", "/home/test")
    transfers.push_file("newuser99", "Home\\None.mp3", "")
    transfer = transfers.uploads[1]

    assert transfer.user == "newuser2"
    assert transfer.filename == "Hello\\Upload\\File.mp3"
    assert transfer.path == "/home/test"
