#!/usr/bin/env python3
# COPYRIGHT (C) 2021-2022 Nicotine+ Contributors
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

import hashlib
import os

""" Generates SHA256 checksums for files placed in the same folder as this script """


def generate_sha256_hashes():

    current_dir = os.path.dirname(os.path.realpath(__file__))
    current_script_name = os.path.basename(os.path.realpath(__file__))

    for entry in os.scandir(current_dir):
        if not entry.is_file():
            continue

        if entry.name == current_script_name:
            continue

        if entry.name.endswith(".sha256"):
            continue

        sha256_hash = hashlib.sha256()

        with open(entry.path, "rb") as file_handle:
            sha256_hash.update(file_handle.read())

        with open(entry.path + ".sha256", "w") as file_handle:
            output = sha256_hash.hexdigest() + "  " + os.path.basename(entry.name)
            file_handle.write(output)


if __name__ == "__main__":
    generate_sha256_hashes()
