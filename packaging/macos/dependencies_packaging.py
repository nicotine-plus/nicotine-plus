#!/usr/bin/env python3
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

import subprocess
import sys

""" Script used to install packaging dependencies in Homebrew """


def install_brew():
    """ Install dependencies from the main Homebrew repos """

    packages = ["create-dmg"]
    subprocess.check_call(["brew", "install"] + packages)


def install_pypi():
    """ Install dependencies from PyPi """

    packages = ["pyinstaller==4.3",
                "stdlib_list"]
    subprocess.check_call([sys.executable, "-m", "pip", "install"] + packages)


if __name__ == '__main__':
    install_brew()
    install_pypi()
