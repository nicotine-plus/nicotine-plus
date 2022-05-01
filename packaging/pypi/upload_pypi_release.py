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

import subprocess
import sys

""" Script used to create new Nicotine+ releases on PyPi """


def create_packages():
    """ Prepare source distribution and wheel """

    for target in ("sdist", "bdist_wheel"):
        subprocess.check_call([sys.executable, "setup.py", target])


def upload_packages():
    """ Upload release to PyPI """

    subprocess.check_call([sys.executable, "-m", "twine", "upload", "dist/*"])


if __name__ == '__main__':
    create_packages()
    upload_packages()
