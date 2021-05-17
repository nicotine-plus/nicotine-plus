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

# Install depencency to upload release
pip3 install setuptools twine

# Prepare source distribution and wheel
python3 -c "import setuptools; exec(open('setup.py').read())" sdist
python3 -c "import setuptools; exec(open('setup.py').read())" bdist_wheel

# Upload release to PyPI
python3 -m twine upload dist/*
