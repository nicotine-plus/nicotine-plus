# COPYRIGHT (C) 2020-2022 Nicotine+ Contributors
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
import socket

from collections import deque
from time import sleep
from unittest import TestCase
from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import patch

from pynicotine.config import config
from pynicotine.slskproto import SoulseekNetworkThread
from pynicotine.slskmessages import ServerConnect, Login, SetWaitPort
from pynicotine.utils import encode_path

# Time (in s) needed for SoulseekNetworkThread main loop to run at least once
SLSKPROTO_RUN_TIME = 1.5


class MockSocket(Mock):

    def __init__(self):
        super().__init__()
        self.events = None

    def set_data(self, datafile):

        windows_line_ending = b'\r\n'
        unix_line_ending = b'\n'

        file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), datafile)

        with open(encode_path(file_path), 'rb') as file_handle:
            content = file_handle.read()

        content = content.replace(windows_line_ending, unix_line_ending)
        logs = pickle.loads(content, encoding='bytes')
        self.events = {}

        for mode in b'send', b'recv':
            for time, event in logs[b'transactions'][mode].items():
                self.events[time] = (mode.decode('latin1'), event)

    @staticmethod
    def send(data):
        print("sending data {}".format(data))

    @staticmethod
    def recv(bufsize):
        print("recving {} data".format(bufsize))
        return b''


class SoulseekNetworkTest(TestCase):

    def setUp(self):

        # Windows doesn't accept mock_socket in select() calls
        selectors.DefaultSelector = MagicMock()

        self.queue = deque()
        config.sections["server"]["upnp"] = False
        self.protothread = SoulseekNetworkThread(
            callback=Mock(), queue=self.queue, user_addresses={}, interface='', bindip='',
            port=None, port_range=(1024, 65535)
        )
        self.protothread.start()

        # Slight delay to allow the network thread to fully start
        sleep(SLSKPROTO_RUN_TIME / 2)

    def tearDown(self):

        self.protothread.abort()

        sleep(SLSKPROTO_RUN_TIME / 2)
        self.assertIsNone(self.protothread._server_socket)  # pylint: disable=protected-access

    @patch('socket.socket')
    def test_server_conn(self, _mock_socket):

        self.protothread.server_disconnected = False

        self.queue.append(ServerConnect(addr=('0.0.0.0', 0), login=('dummy', 'dummy')))
        sleep(SLSKPROTO_RUN_TIME)

        if hasattr(socket, 'TCP_KEEPIDLE') or hasattr(socket, 'TCP_KEEPALIVE'):
            self.assertEqual(
                self.protothread._server_socket.setsockopt.call_count, 6)  # pylint: disable=no-member,protected-access

        elif hasattr(socket, 'SIO_KEEPALIVE_VALS'):
            self.assertEqual(
                self.protothread._server_socket.ioctl.call_count, 1)       # pylint: disable=no-member,protected-access
            self.assertEqual(
                self.protothread._server_socket.setsockopt.call_count, 3)  # pylint: disable=no-member,protected-access

        self.assertEqual(
            self.protothread._server_socket.setblocking.call_count, 1)     # pylint: disable=no-member,protected-access
        self.assertEqual(
            self.protothread._server_socket.connect_ex.call_count, 1)      # pylint: disable=no-member,protected-access

    def test_login(self):

        self.protothread.server_disconnected = False
        self.queue.append(ServerConnect(addr=('0.0.0.0', 0), login=('username', 'password')))

        sleep(SLSKPROTO_RUN_TIME / 2)

        self.queue.append(Login('username', 'password', 160, 1))
        self.queue.append(SetWaitPort(1))

        sleep(SLSKPROTO_RUN_TIME)
