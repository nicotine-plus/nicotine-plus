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

""" This script is used to install dependencies in Homebrew """

# Install most dependencies from the main Homebrew repos
brew install \
  adwaita-icon-theme \
  create-dmg \
  flake8 \
  gdk-pixbuf \
  gobject-introspection \
  gspell \
  gtk+3 \
  libnotify \
  librsvg \
  pygobject3 \
  taglib \
  upx

# Use pip for packages not available in Homebrew
pip3 install miniupnpc pep8-naming pyinstaller==3.6 pytaglib pytest
