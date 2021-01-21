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
