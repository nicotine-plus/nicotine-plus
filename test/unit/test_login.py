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

import socket

from collections import deque
from time import sleep
from unittest.mock import Mock

import pytest

from pynicotine.slskproto import SlskProtoThread
from pynicotine.slskmessages import ServerConn, Login, SetWaitPort
from test.unit.mock_socket import monkeypatch_socket, monkeypatch_select

# Time (in s) needed for SlskProtoThread main loop to run at least once
SLSKPROTO_RUN_TIME = 0.5
LOGIN_DATAFILE = 'data/login/socket_localhost_22420.log'


def test_instantiate_proto() -> None:
    proto = SlskProtoThread(
        ui_callback=Mock(), queue=deque(), bindip='',
        port=None, port_range=(1, 2), network_filter=None,
        eventprocessor=Mock()
    )
    proto.server_connect()
    proto.abort()


def test_server_conn(monkeypatch) -> None:
    mock_socket = monkeypatch_socket(monkeypatch, LOGIN_DATAFILE)
    monkeypatch_select(monkeypatch)
    proto = SlskProtoThread(
        ui_callback=Mock(), queue=deque(), bindip='',
        port=None, port_range=(1, 2), network_filter=None,
        eventprocessor=Mock()
    )
    proto.server_connect()
    proto._queue.append(ServerConn())

    sleep(SLSKPROTO_RUN_TIME)

    proto.abort()

    if hasattr(socket, 'TCP_KEEPIDLE'):
        assert mock_socket.setsockopt.call_count == 5

    elif hasattr(socket, 'TCP_KEEPALIVE'):
        assert mock_socket.setsockopt.call_count == 3

    elif hasattr(socket, 'SIO_KEEPALIVE_VALS'):
        assert mock_socket.ioctl.call_count == 1
        assert mock_socket.setsockopt.call_count == 2

    assert mock_socket.setblocking.call_count == 2
    assert mock_socket.bind.call_count == 1
    assert mock_socket.connect_ex.call_count == 1
    assert mock_socket.listen.call_count == 1

    sleep(SLSKPROTO_RUN_TIME)

    assert mock_socket.close.call_count == 1


def test_login(monkeypatch) -> None:
    monkeypatch_select(monkeypatch)
    proto = SlskProtoThread(
        ui_callback=Mock(), queue=deque(), bindip='',
        port=None, port_range=(1, 2), network_filter=None,
        eventprocessor=Mock()
    )
    proto.server_connect()
    proto._queue.append(ServerConn())

    sleep(SLSKPROTO_RUN_TIME / 2)

    proto._queue.append(Login('username', 'password', 157))
    proto._queue.append(SetWaitPort(1))

    sleep(SLSKPROTO_RUN_TIME)

    proto.abort()
    pytest.skip('Login succeeded, actual test TBD')
