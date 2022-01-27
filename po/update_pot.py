#!/usr/bin/env python3
# COPYRIGHT (C) 2021 Nicotine+ Team
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

import glob
import os


def update_pot():
    """ Update .pot translation template """

    # Desktop, Python and GtkBuilder files
    files = (sorted(glob.glob("data/**/*.in", recursive=True), key=os.path.abspath)
             + sorted(glob.glob("pynicotine/**/*.py", recursive=True), key=os.path.abspath)
             + sorted(glob.glob("pynicotine/**/*.ui", recursive=True), key=os.path.abspath))

    os.system("xgettext -o po/nicotine.pot " + " ".join(files))

    # PLUGININFO files
    files = sorted(glob.glob("pynicotine/**/PLUGININFO", recursive=True))
    os.system("xgettext --join-existing -L Python -o po/nicotine.pot " + " ".join(files))


if __name__ == '__main__':
    update_pot()
