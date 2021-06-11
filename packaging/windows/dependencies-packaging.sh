#!/bin/sh

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

### This script is used to install packaging dependencies in MinGW ###

# Install dependencies from the main MinGW repos
pacman --noconfirm -S --needed \
  unzip \
  mingw-w64-$ARCH-nsis \
  mingw-w64-$ARCH-python-certifi

# Install PyInstaller dependency
# Rebuild bootloader to reduce false positives in anti-malware software
wget https://github.com/pyinstaller/pyinstaller/archive/refs/tags/v4.1.zip
unzip v4.1.zip
cd pyinstaller-4.1/bootloader/

if [ $ARCH == "i686" ]; then
  python3 ./waf all --target-arch=32bit
else
  python3 ./waf all --target-arch=64bit
fi

pip3 install ..
