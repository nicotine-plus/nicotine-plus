#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
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
import sys
import string
from os.path import isfile

table = [
    ["away.png", "away"],
    ["online.png", "online"],
    ["offline.png", "offline"],
    ["trayicon_away.png", "trayicon_away"],
    ["trayicon_connect.png", "trayicon_connect"],
    ["trayicon_disconnect.png", "trayicon_disconnect"],
    ["trayicon_msg.png", "trayicon_msg"],
    ["empty.png", "empty"],
    ["hilite.png", "hilite"],
    ["hilite3.png", "hilite3"],
    ["plugin.png", "plugin"],
    ["n.png", "n"],
    ["notify.png", "notify"]
]

flagtable = []
for name in sorted(os.listdir(os.path.join("img", "geoip"))):
    p = os.path.join("img", "geoip", name)
    if isfile(p):
        flagtable.append((os.path.join("img", "geoip", name), 'flag_%s' % name[:2].upper()))

missing = os.path.join("img", "missingflag.png")
if isfile(missing):
    flagtable.append(((missing), 'flag_'))

outf = open(os.path.join("pynicotine", "gtkgui", "imagedata.py"), "w")

for image in sorted(table):
    print(image[0])
    f = open(os.path.join("img", image[0]), "rb")
    outf.write("%s = %r\n" % (image[1], f.read()))
    f.close()

for image in flagtable:
    print(image[0])
    f = open(image[0], "rb")
    outf.write("%s = %r\n" % (image[1], f.read()))
    f.close()

outf.close()
