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

### This script is used to install core dependencies in MinGW ###
### These are enough to run unit tests and use non-UI code ###

# Install dependencies from the main MinGW repos
pacman --noconfirm -S --needed \
  mingw-w64-$ARCH-cython \
  mingw-w64-$ARCH-gcc \
  mingw-w64-$ARCH-python \
  mingw-w64-$ARCH-python-flake8 \
  mingw-w64-$ARCH-python-pip \
  mingw-w64-$ARCH-python-pytest \
  mingw-w64-$ARCH-taglib

# Install dependencies with pip
pip3 install \
  pep8-naming \
  semidbm

# pytaglib
wget https://github.com/supermihi/pytaglib/archive/v1.4.6.tar.gz
tar -zxvf v1.4.6.tar.gz
cd pytaglib-1.4.6/
sed -i "/is_windows = / s/sys.platform.startswith('win')/False/" setup.py
python setup.py install
cd ..
rm -rf pytaglib-1.4.6/
