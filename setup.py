#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2009-2010 Quinox <quinox@users.sf.net>
# COPYRIGHT (C) 2009 Hedonist <ak@sensi.org>
# COPYRIGHT (C) 2006-2009 Daelstorm <daelstorm@gmail.com>
# COPYRIGHT (C) 2008-2009 eL_vErDe <gandalf@le-vert.net>
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

"""
    To install Nicotine+ on a GNU/Linux distribution run:
    sudo python setup.py install
"""

import sys
import os
import glob

from os.path import isdir
from distutils.core import setup

# Compute data_files
files = []

# Manuals
manpages = glob.glob(os.path.join("manpages", "*.1"))

for man in manpages:
    files.append(
        (
            os.path.join(sys.prefix, "share/man/man1"),
            [man]
        )
    )

# Icons with fixed size
for sizeicons in ["16x16", "32x32", "48x48", "64x64", "96x96"]:
    files.append(
        (
            os.path.join(sys.prefix, "share/icons/hicolor", sizeicons, "apps"),
            ["files/icons/" + sizeicons + "/nicotine-plus.png"]
        )
    )

# Scalable icons
files.append(
    (
        os.path.join(sys.prefix, "share/icons/hicolor/scalable/apps"),
        ["files/icons/scalable/nicotine-plus.svg"]
    )
)

# Desktop file
files.append(
    (
        os.path.join(sys.prefix, "share/applications"),
        ["files/nicotine.desktop"]
    )
)

# Translation files
mo_dirs = [x for x in glob.glob(os.path.join("languages", "*")) if isdir(x)]

for mo in mo_dirs:

    p, lang = os.path.split(mo)
    lc_messages_path = os.path.join(mo, "LC_MESSAGES")

    if lang in ("msgfmtall.py", "tr_gen.py", "mergeall", "nicotine.pot"):
        continue

    files.append(
        (
            os.path.join(sys.prefix, "share/locale", lang, "LC_MESSAGES"),
            [os.path.join(lc_messages_path, "nicotine.mo")]
        )
    )

# Sounds
sound_dirs = glob.glob(os.path.join("sounds", "*"))

for sounds in sound_dirs:
    p, theme = os.path.split(sounds)
    for file in ["private.ogg", "room_nick.ogg", "details.txt", "license.txt"]:
        files.append(
            (
                os.path.join(sys.prefix, "share/nicotine/sounds", theme),
                [os.path.join(sounds, file)]
            )
        )

# Documentation
for (path, dirs, docfiles) in os.walk("doc"):

    dst_path = os.sep.join(path.split("/")[1:])

    for f in docfiles:
        files.append(
            (
                os.path.join(sys.prefix, "share/doc/nicotine", dst_path),
                [os.path.join(path, f)]
            )
        )


if __name__ == '__main__':

    from pynicotine.utils import version
    LONG_DESCRIPTION = """Nicotine+ is a client for the SoulSeek filesharing network, forked from Nicotine."""

    setup(
        name="nicotine",
        version=version,
        license="GPLv3",
        description="Nicotine+, a client for the SoulSeek filesharing network.",
        author="Michael Labouebe",
        author_email="gfarmerfr@free.fr",
        url="https://www.nicotine-plus.org/",
        packages=['pynicotine', 'pynicotine.gtkgui', 'pynicotine.gtkgui.ui'],
        package_dir={'pynicotine.gtkgui': 'pynicotine/gtkgui'},
        package_data={
            'pynicotine.gtkgui.ui': ["*.ui"]
        },
        scripts=['nicotine'],
        long_description=LONG_DESCRIPTION,
        data_files=files
    )

