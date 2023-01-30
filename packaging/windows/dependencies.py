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
import sys

""" Script used to install dependencies in MinGW """


def install_pacman():
    """ Install dependencies from the main MinGW repos """

    arch = os.environ.get("ARCH") or "x86_64"
    prefix = f"mingw-w64-{arch}-"
    mingw_type = "mingw32" if arch == "i686" else "mingw64"
    gtk_version = os.environ.get("NICOTINE_GTK_VERSION") or "3"
    use_libadwaita = gtk_version == "4" and os.environ.get("NICOTINE_LIBADWAITA") == "1"

    packages = [f"{prefix}ca-certificates",
                f"{prefix}gettext",
                f"{prefix}gtk{gtk_version}",
                f"{prefix}python-chardet",
                f"{prefix}python-cx-freeze",
                f"{prefix}python-flake8",
                f"{prefix}python-pip",
                f"{prefix}python-pylint",
                f"{prefix}python-gobject"]

    if use_libadwaita:
        packages.append(prefix + "libadwaita")

    subprocess.check_call(["pacman", "--noconfirm", "-S", "--needed"] + packages)

    # Downgrade Cairo for now due to text rendering performance issues
    downgrade_packages = [f"{prefix}cairo-1.17.4-4-any.pkg.tar.zst",
                          f"{prefix}pango-1.50.11-1-any.pkg.tar.zst"]

    for package in downgrade_packages:
        subprocess.check_call(["curl", "-O", f"https://repo.msys2.org/mingw/{mingw_type}/{package}"])

    subprocess.check_call(["pacman", "--noconfirm", "-U"] + downgrade_packages)


def install_pypi():
    """ Install dependencies from PyPi """

    packages = ["semidbm"]
    subprocess.check_call([sys.executable, "-m", "pip", "install"] + packages)


if __name__ == "__main__":
    install_pacman()
    install_pypi()
