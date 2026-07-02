#!/usr/bin/env python3
# COPYRIGHT (C) 2026 Nicotine+ Contributors
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
import sys

BASE_PATH = os.path.normpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", ".."))
NEWS_FILE_PATH = os.path.join(BASE_PATH, "NEWS.md")


def extract_release_notes():
    """Extracts release notes for the specified version from NEWS.md."""

    if len(sys.argv) < 2:
        print("No version provided")
        sys.exit(1)

    output = bytearray()
    version = sys.argv[1]
    reading_notes = False

    with open(NEWS_FILE_PATH, "rb") as file_handle:
        for line in file_handle:
            if reading_notes:
                if line.startswith(b"## "):
                    break

                output += line
                continue

            if line.startswith(f"## Version {version} ".encode()):
                reading_notes = True

    print(output.decode().strip())


if __name__ == "__main__":
    extract_release_notes()
