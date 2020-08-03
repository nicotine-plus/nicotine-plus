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
for iconname in ["trayicon_away.png", "trayicon_connect.png", "trayicon_disconnect.png", "trayicon_msg.png"]:
    files.append(
        (
            "share/nicotine/trayicons",
            [os.path.join("img", iconname)]
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
mo_dirs = [x for x in glob.glob(os.path.join("languages", "*")) if os.path.isdir(x)]

for mo in mo_dirs:

    p, lang = os.path.split(mo)
    lc_messages_path = os.path.join(mo, "LC_MESSAGES")

    if lang in ("msgfmtall.py", "tr_gen.py", "mergeall", "nicotine.pot"):
        continue

    files.append(
        (
            os.path.join("share/locale", lang, "LC_MESSAGES"),
            [os.path.join(lc_messages_path, "nicotine.mo")]
        )
    )


if __name__ == '__main__':

    setup(
        name="nicotine",
        version=version,
        license="GPLv3",
        description="Nicotine+, a client for the Soulseek file sharing network.",
        author="Nicotine+ Contributors",
        url="https://nicotine-plus.org/",
        packages=find_packages(exclude=['*test*']),
        include_package_data=True,
        scripts=['nicotine'],
        data_files=files
    )
