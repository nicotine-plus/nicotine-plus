# COPYRIGHT (C) 2020-2024 Nicotine+ Contributors
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

import os
import pickle
import selectors
import shutil
import socket
import sys

from time import sleep
from unittest import TestCase
from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import patch

from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.slskmessages import ServerConnect, SetWaitPort
from pynicotine.utils import encode_path

DATA_FOLDER_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), "temp_data")
SLSKPROTO_RUN_TIME = 1.5  # Time (in s) needed for SoulseekNetworkThread main loop to run at least once


class MockSocket(Mock):

    def __init__(self):
        super().__init__()
        self.events = None

    def set_data(self, datafile):

        windows_line_ending = b"\r\n"
        unix_line_ending = b"\n"

        file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), datafile)

        with open(encode_path(file_path), "rb") as file_handle:
            content = file_handle.read()

        content = content.replace(windows_line_ending, unix_line_ending)
        logs = pickle.loads(content, encoding="bytes")
        self.events = {}

        for mode in b"send", b"recv":
            for time, event in logs[b"transactions"][mode].items():
                self.events[time] = (mode.decode("latin1"), event)

    @staticmethod
    def send(data):
        print(f"sending data {data}")

    @staticmethod
    def recv(bufsize):
        print(f"recving {bufsize} data")
        return b""


class SoulseekNetworkTest(TestCase):

    def setUp(self):

        # Windows doesn't accept mock_socket in select() calls
        selectors.DefaultSelector = MagicMock()

        config.set_data_folder(DATA_FOLDER_PATH)
        config.set_config_file(os.path.join(DATA_FOLDER_PATH, "temp_config"))

        core.init_components(enabled_components={"network_thread"})

        config.sections["server"]["upnp"] = False
        core.start()
        events.emit("enable-message-queue")

        # Slight delay to allow the network thread to fully start
        sleep(SLSKPROTO_RUN_TIME / 2)

    def tearDown(self):

        core.quit()

        sleep(SLSKPROTO_RUN_TIME / 2)

        events.process_thread_events()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(DATA_FOLDER_PATH)

    @patch("socket.socket")
    def test_server_conn(self, _mock_socket):

        core.send_message_to_network_thread(
            ServerConnect(addr=("0.0.0.0", 0), login=("dummy", "dummy"), listen_port=65525)
        )
        sleep(SLSKPROTO_RUN_TIME)

        # pylint: disable=no-member,protected-access
        sock = core._network_thread._server_conn.sock

        if hasattr(socket, "TCP_KEEPIDLE") or hasattr(socket, "TCP_KEEPALIVE"):
            if sys.platform == "win32":
                self.assertEqual(sock.setsockopt.call_count, 5)

            elif hasattr(socket, "TCP_USER_TIMEOUT"):
                self.assertEqual(sock.setsockopt.call_count, 7)

            else:
                self.assertEqual(sock.setsockopt.call_count, 6)

        elif hasattr(socket, "SIO_KEEPALIVE_VALS"):
            self.assertEqual(sock.ioctl.call_count, 1)
            self.assertEqual(sock.setsockopt.call_count, 2)

        self.assertEqual(sock.setblocking.call_count, 2)
        self.assertEqual(sock.connect_ex.call_count, 1)

    def test_login(self):

        core.send_message_to_network_thread(
            ServerConnect(addr=("0.0.0.0", 0), login=("dummy", "dummy"), listen_port=65525)
        )
        sleep(SLSKPROTO_RUN_TIME / 2)

        core.send_message_to_server(SetWaitPort(1))

        sleep(SLSKPROTO_RUN_TIME)
