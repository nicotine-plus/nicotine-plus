import subprocess


# noinspection PyInterpreter
class nicotine_library:  # noqa
    def __init__(self):
        self._result = None

    def running_nicotine_starts_a_process(self, command, timeout):
        if not isinstance(command, list):
            command = [command]

        # Assume failure by default
        issuccess = False

        try:
            subprocess.call(command, timeout=int(timeout))
        except subprocess.TimeoutExpired:
            # Program was still running, success!
            issuccess = True

        self._result = issuccess

    def result_should_be(self, expected):
        assert self._result == expected
        self._result = None
