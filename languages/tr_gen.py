#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# COPYRIGHT (c) 2016 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (c) 2009 eL_vErDe <gandalf@le-vert.net>
# COPYRIGHT (c) 2009 Quinox <quinox@users.sf.net>
# COPYRIGHT (c) 2006-2009 Daelstorm <daelstorm@gmail.com>
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

import sys
from os import listdir, system
from os.path import isfile, join

print "Generating nicotine.pot …"

files = {}

files["../"] = [
    f for f in sorted(listdir("../")) if isfile(join("../", f))
]

files["../pynicotine/"] = [
    f for f in sorted(listdir("../pynicotine/"))
    if isfile(join("../pynicotine/", f))
]

files["../pynicotine/gtkgui/"] = [
    f for f in sorted(listdir("../pynicotine/gtkgui/"))
    if isfile(join("../pynicotine/gtkgui/", f))
]


def isPythonScript(dir, file):
    if file.rsplit(".")[-1].lower() in ("py"):
        return dir + file
    return None


def isGlade(dir, file):
    if file.rsplit(".")[-1].lower() in ("glade"):
        return dir + file
    return None

pythonscripts = []
gladescripts = []

for dir, files in files.items():
    for file in files:
        ispy = isPythonScript(dir, file)
        if ispy is not None:
            pythonscripts.append(ispy)
        isglade = isGlade(dir, file)
        if isglade is not None:
            gladescripts.append(isglade)

blacklist = ["icondata", "imagedata", "__init__"]

for item in blacklist:
    for path in pythonscripts[:]:
        if item in path:
            pythonscripts.remove(path)

goodpython = ""
for path in pythonscripts[:]:
    goodpython += path + " "

print "xgettext --no-location -o nicotine-python.pot %s" % goodpython
r = system("xgettext --no-location -o nicotine-python.pot %s" % goodpython)

gladestring = ""
for path in gladescripts[:]:
    gladestring += path + " "

print "xgettext --no-location -L Glade -o nicotine-glade.pot %s" % gladestring
r = system(
    "xgettext --no-location -L Glade -o nicotine-glade.pot %s" % gladestring)

r = system("msgcat nicotine-glade.pot nicotine-python.pot -o nicotine.pot")

if r:
    print "Error while creating nicotine.pot"
else:
    print "You can remove nicotine-glade.pot nicotine-python.pot files"
