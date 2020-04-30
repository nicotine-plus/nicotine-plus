__author__ = 'Lene Preuss <lene.preuss@gmail.com>'

from queue import Queue
from time import sleep
from unittest.mock import Mock, MagicMock

import pytest

from pynicotine.slskproto import SlskProtoThread
from pynicotine.slskmessages import ServerConn, Login, SetWaitPort
from pynicotine.utils import ApplyTranslation
from tests.unit.mock_socket import monkeypatch_socket, monkeypatch_select

# Time (in s) needed for SlskProtoThread main loop to run at least once
SLSKPROTO_RUN_TIME = 0.5
LOGIN_DATAFILE = 'data/login/socket_localhost:22420.log'


@pytest.fixture(scope="module", autouse=True)
def apply_translations():
    ApplyTranslation()


@pytest.fixture
def config():
    config = MagicMock()
    config.sections = {'server': {'portrange': (1, 2)}, 'transfers': {'downloadlimit': 10}}
    return config


def test_instantiate_proto(config) -> None:
    proto = SlskProtoThread(
        ui_callback=Mock(), queue=Mock(), bindip='',
        port=None, config=config, eventprocessor=Mock()
    )
    proto.abort()


def test_server_conn(config, monkeypatch) -> None:
    mock_socket = monkeypatch_socket(monkeypatch, LOGIN_DATAFILE)
    monkeypatch_select(monkeypatch)
    proto = SlskProtoThread(
        ui_callback=Mock(), queue=Queue(0), bindip='',
        port=None, config=config, eventprocessor=Mock()
    )
    proto._queue.put(ServerConn())
    sleep(SLSKPROTO_RUN_TIME)
    proto.abort()
    assert mock_socket.setsockopt.call_count == 1
    assert mock_socket.setblocking.call_count == 2
    assert mock_socket.bind.call_count == 1
    assert mock_socket.connect_ex.call_count == 1
    assert mock_socket.listen.call_count == 1
    assert mock_socket.close.call_count == 1


def test_login(config, monkeypatch) -> None:
    mock_socket = monkeypatch_socket(monkeypatch, LOGIN_DATAFILE)
    monkeypatch_select(monkeypatch)
    proto = SlskProtoThread(
        ui_callback=Mock(), queue=Queue(0), bindip='',
        port=None, config=config, eventprocessor=Mock()
    )
    proto._queue.put(ServerConn())
    sleep(SLSKPROTO_RUN_TIME / 2)
    proto._queue.put(Login('username', 'password', 157))
    proto._queue.put(SetWaitPort(1))
    sleep(SLSKPROTO_RUN_TIME)
    proto.abort()
    pytest.skip('Login succeeded, actual test TBD')
