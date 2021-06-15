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

import os
import pickle
import socket
import unittest

from collections import deque
from time import sleep
from unittest.mock import Mock
from unittest.mock import patch

from pynicotine.slskproto import SlskProtoThread
from pynicotine.slskmessages import ServerConn, Login, SetWaitPort

# Time (in s) needed for SlskProtoThread main loop to run at least once
SLSKPROTO_RUN_TIME = 0.5
LOGIN_DATAFILE = 'socket_localhost_22420.log'


class MockSocket(Mock):

    def __init__(self):
        super().__init__()
        self.events = None

    def set_data(self, datafile):

        windows_line_ending = b'\r\n'
        unix_line_ending = b'\n'

        file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), datafile)

        with open(file_path, 'rb') as file_handle:
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


class SlskProtoTest(unittest.TestCase):

    def test_server_conn(self):

        mock_socket = MockSocket()
        queue = deque()
        proto = SlskProtoThread(
            ui_callback=Mock(), queue=queue, interface='', bindip='',
            port=None, port_range=(1, 65535), network_filter=None,
            eventprocessor=Mock()
        )

        with patch('socket.socket') as mock_socket:
            mock_socket.set_data(LOGIN_DATAFILE)
            proto.server_connect()

            queue.append(ServerConn(addr=('0.0.0.0', 0)))
            sleep(SLSKPROTO_RUN_TIME)

            if hasattr(socket, 'TCP_KEEPIDLE'):
                self.assertEqual(proto.server_socket.setsockopt.call_count, 4)

            elif hasattr(socket, 'TCP_KEEPALIVE'):
                self.assertEqual(proto.server_socket.setsockopt.call_count, 3)

            elif hasattr(socket, 'SIO_KEEPALIVE_VALS'):
                self.assertEqual(proto.server_socket.ioctl.call_count, 1)
                self.assertEqual(proto.server_socket.setsockopt.call_count, 1)

            self.assertEqual(proto.server_socket.setblocking.call_count, 2)
            self.assertEqual(proto.server_socket.connect_ex.call_count, 1)

            proto.abort()

            self.assertIsNone(proto.server_socket)

    @staticmethod
    def test_login():

        queue = deque()
        proto = SlskProtoThread(
            ui_callback=Mock(), queue=queue, interface='', bindip='',
            port=None, port_range=(1, 65535), network_filter=None,
            eventprocessor=Mock()
        )
        proto.server_connect()
        queue.append(ServerConn(addr=('0.0.0.0', 0)))

        sleep(SLSKPROTO_RUN_TIME / 2)

        queue.append(Login('username', 'password', 160, 1))
        queue.append(SetWaitPort(1))

        sleep(SLSKPROTO_RUN_TIME)

        proto.abort()
