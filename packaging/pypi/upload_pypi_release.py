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

""" Script used to create new Nicotine+ releases on PyPi """


def install_dependencies():
    """ Install dependencies required to upload release """

    packages = ["setuptools",
                "twine"]
    subprocess.check_call([sys.executable, "-m", "pip", "install"] + packages)


def create_packages():
    """ Prepare source distribution and wheel """

    setuptools_wrapper = "import setuptools; exec(open('setup.py').read())"

    for target in ("sdist", "bdist_wheel"):
        subprocess.check_call([sys.executable, "-c", setuptools_wrapper, target])


def upload_packages():
    """ Upload release to PyPI """

    subprocess.check_call([sys.executable, "-m", "twine", "upload", "dist/*"])


if __name__ == '__main__':
    install_dependencies()
    create_packages()
    upload_packages()
