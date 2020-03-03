import socket
import time
import pickle

class Rocket:
    """
    A recording socket.
    Replace calls to 'socket.socket()' with 'Rocket()' in code to have network
    traffic written to /tmp.
    """

    def __init__(self, family, type):
        self.socket = socket.socket(family, type)
        self._address = None
        self._transactions = {'send': {}, 'recv': {}}

    def logfile(self):
        return '/tmp/socket_{}:{}.log'.format(self._address[0], self._address[1])

    def log_write(self, direction, data):
        self._transactions[direction][time.time()] = data
        with open(self.logfile(), 'wb') as f:
            pickle.dump({'address': self._address, 'transactions': self._transactions}, f)

    def setsockopt(self, level, optname, value):
        self.socket.setsockopt(level, optname, value)

    def setblocking(self, block):
        self.socket.setblocking(block)

    def bind(self, address):
        self._address = address
        self.socket.bind(address)

    def connect_ex(self, address):
        self._address = address
        self.socket.connect_ex(address)

    def listen(self, backlog):
        self.socket.listen(backlog)

    def fileno(self):
        return self.socket.fileno()

    def send(self, data):
        self.log_write('send', data)
        return self.socket.send(data)

    def recv(self, bufsize):
        data = self.socket.recv(bufsize)
        self.log_write('recv', data)
        return data

    def close(self):
        return self.socket.close()
