#!/usr/bin/env python3
# COPYRIGHT (C) 2020-2023 Nicotine+ Contributors
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

""" Script used to install dependencies in Homebrew """


def install_brew():
    """Install dependencies from the main Homebrew repos."""

    gtk_version = os.environ.get("NICOTINE_GTK_VERSION") or "3"
    use_libadwaita = gtk_version == "4" and os.environ.get("NICOTINE_LIBADWAITA") == "1"

    packages = ["adwaita-icon-theme",
                "gettext",
                "gobject-introspection",
                f"gtk+{gtk_version}"]

    if use_libadwaita:
        packages.append("libadwaita")

    subprocess.check_call(["brew", "install"] + packages)


def install_pypi():
    """Install dependencies from PyPi."""

    subprocess.check_call([sys.executable, "-m", "pip", "install", "--no-binary", "cx_Freeze",
                           "-e", ".[packaging,tests]", "build", "semidbm"])


if __name__ == "__main__":
    install_brew()
    install_pypi()
