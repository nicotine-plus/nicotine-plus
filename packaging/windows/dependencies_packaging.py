#!/usr/bin/env python3
# COPYRIGHT (C) 2020-2022 Nicotine+ Contributors
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
import subprocess

""" Script used to install packaging dependencies in MinGW """


ARCH = os.environ.get("ARCH") or "x86_64"
CURRENT_PATH = os.path.dirname(os.path.abspath(__file__))


def install_pacman():
    """ Install dependencies from the main MinGW repos """

    prefix = "mingw-w64-" + ARCH + "-"
    packages = [prefix + "python-packaging"]
    packages_local = [os.path.join(CURRENT_PATH, prefix + "python-cx-freeze-6.12.0.dev0-1-any.pkg.tar.zst")]

    subprocess.check_call(["pacman", "--noconfirm", "-S", "--needed"] + packages)
    subprocess.check_call(["pacman", "--noconfirm", "-U", "--needed"] + packages_local)


if __name__ == '__main__':
    install_pacman()
