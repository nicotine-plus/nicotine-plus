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
import sys

""" Script used to create a Windows installer with NSIS """


def create_nsis_installer():

    arch = os.environ.get("ARCH") or "x86_64"
    current_dir = os.path.dirname(os.path.realpath(__file__))
    version = subprocess.check_output([sys.executable,
                                     os.path.join(current_dir, "..", "..", "setup.py"),
                                     "--version"])

    subprocess.check_call(["makensis", "-DARCH=" + str(arch), "-DPRODUCT_VERSION=" + str(version),
                           os.path.join(current_dir, "nicotine.nsi")])


if __name__ == '__main__':
    create_nsis_installer()
