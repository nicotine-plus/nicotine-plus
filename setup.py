#!/usr/bin/env python3
# COPYRIGHT (C) 2020 Nicotine+ Team
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

import os
import glob

from pynicotine.utils import version
from setuptools import find_packages, setup

# Compute data_files
files = []

# Program icon
files.append(
    (
        "share/icons/hicolor/scalable/apps",
        ["files/org.nicotine_plus.Nicotine.svg"]
    )
)

# Tray icons
tray_icons = glob.glob(os.path.join("img", "tray", "*"))

for icon_name in tray_icons:
    files.append(
        (
            "share/icons/hicolor/32x32/apps",
            [icon_name]
        )
    )

# Desktop file
files.append(
    (
        "share/applications",
        ["files/org.nicotine_plus.Nicotine.desktop"]
    )
)

# AppStream metainfo
files.append(
    (
        "share/metainfo",
        ["files/appdata/org.nicotine_plus.Nicotine.appdata.xml"]
    )
)

# Documentation
docfiles = glob.glob("[!404.md]*.md") + glob.glob(os.path.join("doc", "*.md"))

for doc in docfiles:
    files.append(
        (
            "share/doc/nicotine",
            [doc]
        )
    )

files.append(
    (
        "share/doc/nicotine",
        ["img/CREDITS.md"]
    )
)

manpages = glob.glob(os.path.join("files", "*.1"))

for man in manpages:
    files.append(
        (
            "share/man/man1",
            [man]
        )
    )

# Translation
for po_file in glob.glob(os.path.join("po", "*.po")):
    lang = os.path.basename(po_file[:-3])

    mo_dir = os.path.join("build", "mo", lang, "LC_MESSAGES")
    mo_file = os.path.join(mo_dir, "nicotine.mo")

    if not os.path.exists(mo_dir):
        os.makedirs(mo_dir)

    os.system("msgfmt " + po_file + " -o " + mo_file)

    targetpath = os.path.join("share/locale", lang, "LC_MESSAGES")
    files.append(
        (
            targetpath,
            [mo_file]
        )
    )

if __name__ == '__main__':

    setup(
        name="nicotine",
        version=version,
        license="GPLv3",
        description="Nicotine+ is a graphical client for the Soulseek file sharing network",
        author="Nicotine+ Team",
        url="https://nicotine-plus.org/",
        packages=find_packages(exclude=['*test*']),
        include_package_data=True,
        scripts=['nicotine'],
        data_files=files
    )
