#!/usr/bin/env python3
# COPYRIGHT (C) 2020-2026 Nicotine+ Contributors
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


def install_conda_forge():
    """Install dependencies from the main conda-forge repos."""

    environment_name = "nicotine-plus"

    # Temporarily install older icu version to force non-icu variant of libsqlite
    pre_packages = ["icu<78",
                    "libsqlite"]

    packages = ["icu",
                "cx_freeze",
                "gobject-introspection",
                "gtk4",
                "libadwaita",
                "pygobject",
                "python-build"]

    subprocess.check_call(["mamba", "install", "-n", environment_name, "-y"] + pre_packages)
    subprocess.check_call(["mamba", "install", "-n", environment_name, "-y"] + packages)


if __name__ == "__main__":
    install_conda_forge()
