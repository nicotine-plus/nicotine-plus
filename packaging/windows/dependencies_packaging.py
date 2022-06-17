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


def install_pacman():
    """ Install dependencies from the main MinGW repos """

    variant = "mingw64" if ARCH == "x86_64" else "mingw32"
    prefix = "mingw-w64-" + ARCH
    packages = ["https://repo.msys2.org/mingw/%s/%s-python-cx-freeze-6.10-1-any.pkg.tar.zst" % (variant, prefix)]

    subprocess.check_call(["pacman", "--noconfirm", "-U", "--needed"] + packages)


if __name__ == '__main__':
    install_pacman()
