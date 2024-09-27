#!/usr/bin/env python3
# COPYRIGHT (C) 2020-2024 Nicotine+ Contributors
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


def install_pacman():
    """Install dependencies from the main MinGW repos."""

    arch = os.environ.get("ARCH", "x86_64")
    prefix = "mingw-w64-clang-"

    if arch == "arm64":
        prefix += "aarch64"
        mingw_type = "clangarm64"
    else:
        prefix += "x86_64"
        mingw_type = "clang64"

    packages = [f"{prefix}-ca-certificates",
                f"{prefix}-gettext-tools",
                f"{prefix}-gtk4",
                f"{prefix}-libadwaita",
                f"{prefix}-python-build",
                f"{prefix}-python-cx-freeze",
                f"{prefix}-python-pycodestyle",
                f"{prefix}-python-pylint",
                f"{prefix}-python-gobject"]

    subprocess.check_call(["pacman", "--noconfirm", "-S", "--needed"] + packages)

    # Downgrade libadwaita for now due to dark mode not being applied on startup
    # https://gitlab.gnome.org/GNOME/libadwaita/-/issues/932
    downgrade_packages = [f"{prefix}-libadwaita-1.5.3-1-any.pkg.tar.zst"]

    for package in downgrade_packages:
        subprocess.check_call(["curl", "-O", f"https://repo.msys2.org/mingw/{mingw_type}/{package}"])

    subprocess.check_call(["pacman", "--noconfirm", "-U"] + downgrade_packages)


if __name__ == "__main__":
    install_pacman()
