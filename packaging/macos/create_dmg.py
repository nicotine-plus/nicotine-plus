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

import os
import subprocess

""" Script used to create a macOS DMG package """


def create_dmg():

    current_dir = os.path.dirname(os.path.realpath(__file__))

    os.mkdir("dmg")
    os.chdir("dmg")

    subprocess.check_call(["create-dmg",
                           "--volname", "Nicotine+",
                           "--window-size", "600", "400",
                           "--app-drop-link", "450", "185",
                           "Nicotine+.dmg",
                           os.path.join(current_dir, "..", "..", "dist")])


if __name__ == '__main__':
    create_dmg()
