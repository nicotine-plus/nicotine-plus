import pickle
import socket
import select
from unittest.mock import Mock
from pathlib import Path


class MockSocket(Mock):

    def set_data(self, datafile: str) -> None:
        with open(Path(__file__).resolve().parent / datafile, 'rb') as file:
            logs = pickle.load(file, encoding='bytes')
        self.events = {}
        for mode in b'send', b'recv':
            for time, event in logs[b'transactions'][mode].items():
                self.events[time] = (mode.decode('latin1'), event)

    def send(self, data: bytes) -> None:
        print(f"sending data {data}")

    def recv(self, bufsize: int) -> bytes:
        print(f"recving {bufsize} data")
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
