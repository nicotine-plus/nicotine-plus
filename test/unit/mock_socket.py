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

import pickle
import socket
import select
from unittest.mock import Mock
from pathlib import Path


class MockSocket(Mock):

    def set_data(self, datafile: str) -> None:
        windows_line_ending = b'\r\n'
        unix_line_ending = b'\n'

        file_path = str(Path(__file__).resolve().parent / datafile)

        with open(file_path, 'rb') as open_file:
            content = open_file.read()

        content = content.replace(windows_line_ending, unix_line_ending)
        logs = pickle.loads(content, encoding='bytes')
        self.events = {}

        for mode in b'send', b'recv':
            for time, event in logs[b'transactions'][mode].items():
                self.events[time] = (mode.decode('latin1'), event)

    def send(self, data: bytes) -> None:
        print("sending data {}".format(data))

    def recv(self, bufsize: int) -> bytes:
        print("recving {} data".format(bufsize))
        return b''


def monkeypatch_socket(monkeypatch, datafile: str) -> MockSocket:
    mock_socket = MockSocket()
    mock_socket.set_data(datafile)
    monkeypatch.setattr(socket, 'socket', lambda family, type: mock_socket)
    return mock_socket


def monkeypatch_select(monkeypatch) -> None:
    monkeypatch.setattr(
        select, 'select', lambda rlist, wlist, xlist, timeout=None: (rlist, wlist, xlist)
    )
