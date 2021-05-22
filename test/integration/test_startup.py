# COPYRIGHT (C) 2020-2021 Nicotine+ Team
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

import pytest
import subprocess


commands = (
    ["python3", "nicotine", "--config=temp_config", "--ci-mode"],  # GUI
    ["python3", "nicotine", "--config=temp_config", "--headless"]  # Headless
)


@pytest.mark.parametrize("command", commands)
def test_startup(command):

    # Assume failure by default
    is_success = False

    try:
        subprocess.call(command, timeout=5)

    except subprocess.TimeoutExpired:
        # Program was still running, success!
        is_success = True

    assert is_success is True
