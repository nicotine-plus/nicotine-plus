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
    mock_socket.fileno.return_value = 0
    monkeypatch.setattr(socket, 'socket', lambda family, type: mock_socket)
    return mock_socket


def monkeypatch_select(monkeypatch) -> None:
    monkeypatch.setattr(
        select, 'select', lambda rlist, wlist, xlist, timeout=None: (rlist, wlist, xlist)
    )
