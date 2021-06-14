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

### This script is used to install core dependencies in MinGW ###

# Install dependencies from the main MinGW repos
pacman --noconfirm -S --needed \
  mingw-w64-$ARCH-gspell \
  mingw-w64-$ARCH-gtk$NICOTINE_GTK_VERSION \
  mingw-w64-$ARCH-python \
  mingw-w64-$ARCH-python-flake8 \
  mingw-w64-$ARCH-python-pip \
  mingw-w64-$ARCH-python-pylint \
  mingw-w64-$ARCH-python-pytest \
  mingw-w64-$ARCH-python-gobject \
  mingw-w64-$ARCH-python-setuptools

# Install dependencies with pip
pip3 install \
  pep8-naming \
  semidbm
