import os
import signal
from subprocess import Popen
from time import sleep


# noinspection PyInterpreter
class nicotine_library:  # noqa
    def __init__(self):
        self._result = None

    def running_nicotine_starts_a_process(self, command, timeout):
        if not isinstance(command, list):
            command = [command]
        proc = Popen(command)
        sleep(int(timeout))
        self._result = bool(proc.pid)
        os.kill(proc.pid, signal.SIGTERM)
        sleep(1)

    def result_should_be(self, expected):
        assert self._result == expected
        self._result = None
