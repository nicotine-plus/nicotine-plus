#!/bin/sh

# COPYRIGHT (C) 2020 Nicotine+ Team
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

""" This script is used to install dependencies in MinGW """

# Install most dependencies from the main MinGW repos
pacman --noconfirm -S --needed \
  git \
  upx \
  mingw-w64-$ARCH-cython \
  mingw-w64-$ARCH-gcc \
  mingw-w64-$ARCH-gspell \
  mingw-w64-$ARCH-gtk3 \
  mingw-w64-$ARCH-miniupnpc \
  mingw-w64-$ARCH-nsis \
  mingw-w64-$ARCH-python3 \
  mingw-w64-$ARCH-python3-gobject \
  mingw-w64-$ARCH-python3-pip \
  mingw-w64-$ARCH-python3-pytest \
  mingw-w64-$ARCH-python3-flake8 \
  mingw-w64-$ARCH-taglib

# Use pip for packages not available in MinGW repos
pip install pep8-naming plyer semidbm

# pyinstaller (we should switch back to pip once PyInstaller 4.1 is released)
wget https://github.com/pyinstaller/pyinstaller/releases/download/v3.6/PyInstaller-3.6.tar.gz
tar -zxvf PyInstaller-3.6.tar.gz
cd PyInstaller-3.6/
python setup.py install
cd ..
rm -rf PyInstaller-3.6/

# pytaglib
wget https://github.com/supermihi/pytaglib/archive/v1.4.6.tar.gz
tar -zxvf v1.4.6.tar.gz
cd pytaglib-1.4.6/
sed -i "/is_windows = / s/sys.platform.startswith('win')/False/" setup.py
PYTAGLIB_CYTHONIZE=1 python setup.py install
cd ..
rm -rf pytaglib-1.4.6/
