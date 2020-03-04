import socket
import select
from typing import Tuple
from unittest.mock import Mock


class MockSocket(Mock):
    def send(self, data: bytes) -> None:
        print(f"sending data {data}")

    def recv(self, bufsize: int) -> bytes:
        print(f"recving {bufsize} data")
        return b''


def monkeypatch_socket(monkeypatch):
    mock_socket = MockSocket()
    mock_socket.fileno.return_value = 0
    monkeypatch.setattr(socket, 'socket', lambda family, type: mock_socket)
    return mock_socket


def monkeypatch_select(monkeypatch):
    monkeypatch.setattr(
        select, 'select', lambda rlist, wlist, xlist, timeout=None: (rlist, wlist, xlist)
    )
