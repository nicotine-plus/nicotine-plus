#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2009 eL_vErDe <gandalf@le-vert.net>
# COPYRIGHT (C) 2009 Quinox <quinox@users.sf.net>
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

import sys
from os import listdir, remove, system
from os.path import isfile, join

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

files["../pynicotine/gtkgui/ui/"] = [
    f for f in sorted(listdir("../pynicotine/gtkgui/ui/"))
    if isfile(join("../pynicotine/gtkgui/ui/", f))
]


def isPythonScript(dir, file):
    if file.rsplit(".")[-1].lower() in ("py"):
        return dir + file
    return None


def isBuilder(dir, file):
    if file.rsplit(".")[-1].lower() in ("ui"):
        return dir + file
    return None

pythonscripts = []
builderscripts = []

for dir, files in list(files.items()):

    for file in files:

        ispy = isPythonScript(dir, file)
        if ispy is not None:
            pythonscripts.append(ispy)

        isbuilder = isBuilder(dir, file)
        if isbuilder is not None:
            builderscripts.append(isbuilder)

blacklist = ["imagedata", "__init__"]

for item in blacklist:
    for path in pythonscripts[:]:
        if item in path:
            pythonscripts.remove(path)

goodpython = ""
for path in pythonscripts[:]:
    goodpython += path + " "

# Add the launcher explicitly since it has no .py extension
print("Generating nicotine-launcher.pot ...\n")

print("xgettext --no-location -L Python -o nicotine-launcher.pot ../nicotine")
r = system("xgettext --no-location -L Python -o nicotine-launcher.pot ../nicotine")

# Add python scripts
print("\nGenerating nicotine-python.pot ...\n")

print("xgettext --no-location -o nicotine-python.pot %s" % goodpython)
r = system("xgettext --no-location -o nicotine-python.pot %s" % goodpython)

# Add builder files
print("\nGenerating nicotine-builder.pot ...\n")

builderstring = ""
for path in builderscripts[:]:
    builderstring += path + " "

print("xgettext --no-location -o nicotine-builder.pot %s" % builderstring)
r = system("xgettext --no-location -o nicotine-builder.pot %s" % builderstring)

# Concat every files
print("\nGenerating nicotine.pot ...\n")

r = system("msgcat nicotine-launcher.pot nicotine-builder.pot nicotine-python.pot -o nicotine.pot")

if r:
    print("Error while creating nicotine.pot")
else:
    remove('nicotine-launcher.pot')
    remove('nicotine-builder.pot')
    remove('nicotine-python.pot')
