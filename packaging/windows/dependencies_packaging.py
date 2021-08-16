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

import io
import os
import subprocess
import sys
import urllib.request
import zipfile

""" Script used to install packaging dependencies in MinGW """


ARCH = os.environ.get("ARCH") or "x86_64"


def install_pacman():
    """ Install dependencies from the main MinGW repos """

    prefix = "mingw-w64-" + str(ARCH) + "-"
    packages = [prefix + "nsis",
                prefix + "python-certifi"]

    subprocess.check_call(["pacman", "--noconfirm", "-S", "--needed"] + packages)


def install_pyinstaller():
    """ Install PyInstaller dependency. Use an older version, and rebuild bootloader
    to reduce false positives in anti-malware software. """

    url = "https://github.com/pyinstaller/pyinstaller/archive/refs/tags/v4.1.zip"
    response = urllib.request.urlopen(url)

    with zipfile.ZipFile(io.BytesIO(response.read()), "r") as file_handle:
        file_handle.extractall()

    os.chdir("pyinstaller-4.1/bootloader")
    subprocess.check_call([sys.executable, "./waf", "all",
                           "--target-arch=" + ("32bit" if ARCH == "i686" else "64bit")])
    subprocess.check_call([sys.executable, "-m", "pip", "install", ".."])


if __name__ == '__main__':
    install_pacman()
    install_pyinstaller()
