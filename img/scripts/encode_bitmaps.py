#!/usr/bin/env python3
# COPYRIGHT (C) 2020 Nicotine+ Team
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2009-2010 Quinox <quinox@users.sf.net>
# COPYRIGHT (C) 2006-2009 Daelstorm <daelstorm@gmail.com>
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
from os.path import isfile

table = [
    ["img/away.png", "away"],
    ["img/online.png", "online"],
    ["img/offline.png", "offline"],
    ["img/empty.png", "empty"],
    ["img/hilite.png", "hilite"],
    ["img/hilite3.png", "hilite3"],
    ["files/org.nicotine_plus.Nicotine.svg", "n"],
    ["files/org.nicotine_plus.Nicotine.svg", "notify"]
]

for name in sorted(os.listdir(os.path.join("img", "tray"))):
    p = os.path.join("img", "tray", name)

    if isfile(p):
        table.append([p, "trayicon_%s" % name[:-4]])

flagtable = []

for name in sorted(os.listdir(os.path.join("img", "flags"))):
    p = os.path.join("img", "flags", name)

    if isfile(p):
        flagtable.append([p, "flag_%s" % name[:2].upper()])

outf = open(os.path.join("pynicotine", "gtkgui", "imagedata.py"), "w")

for image in sorted(table) + flagtable:
    print(image[0])
    f = open(image[0], "rb")
    outf.write("%s = %r\n" % (image[1], f.read()))
    f.close()

outf.close()
