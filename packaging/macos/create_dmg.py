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

""" Script used to create a macOS DMG package """


def create_dmg():

    current_folder = os.path.dirname(os.path.realpath(__file__))
    target_folder = "dmg"
    output_file = "Nicotine+.dmg"

    if not os.path.exists(target_folder):
        os.mkdir(target_folder)

    os.chdir(target_folder)

    if os.path.exists(output_file):
        os.remove(output_file)

    subprocess.check_call(["create-dmg",
                           "--volname", "Nicotine+",
                           "--window-size", "600", "400",
                           "--app-drop-link", "450", "185",
                           output_file,
                           os.path.join(current_folder, "..", "..", "dist")])


if __name__ == '__main__':
    create_dmg()
