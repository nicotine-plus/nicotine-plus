# COPYRIGHT (C) 2021 Nicotine+ Team
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

import os
import pytest

from pynicotine.config import Config


@pytest.fixture
def config():
    config = Config()
    config.data_dir = os.path.dirname(os.path.realpath(__file__))
    config.filename = os.path.join(config.data_dir, "config")

    config.load_config()
    return config


def test_load_config(config):
    """ Test loading a config file """

    assert config.defaults["server"]["login"] == ""
    assert config.defaults["server"]["passw"] == ""

    assert config.sections["server"]["login"] == "user123"
    assert config.sections["server"]["passw"] == "pass123"
    assert config.sections["server"]["autoreply"] == "ääääääää"


def test_write_config(config):
    """ Test writing to a config file """

    # Verify that changes are saved
    config.sections["server"]["login"] = "newname"
    config.write_configuration()

    with open(config.filename, encoding="utf-8") as f:
        assert "newname" in f.read()

    # Verify that the backup is valid
    old_config = config.filename + ".old"
    assert os.path.exists(old_config)

    with open(old_config, encoding="utf-8") as f:
        assert "user123" in f.read()

    # Reset
    config.sections["server"]["login"] = "user123"
    config.write_configuration()
