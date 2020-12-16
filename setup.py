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

import glob
import os
import pynicotine

from distutils.core import setup
from pkgutil import walk_packages
from pynicotine.utils import version

packages = ["pynicotine"] + \
    [name for importer, name, ispkg in walk_packages(path=pynicotine.__path__, prefix="pynicotine.") if ispkg]

package_data = dict((package, ["*.bin", "*.md", "*.py", "*.svg", "*.ui", "PLUGININFO"]) for package in packages)

data_files = []

# Program icon
data_files.append(
    (
        "share/icons/hicolor/scalable/apps",
        ["files/org.nicotine_plus.Nicotine.svg"]
    )
)

data_files.append(
    (
        "share/icons/hicolor/symbolic/apps",
        ["files/org.nicotine_plus.Nicotine-symbolic.svg"]
    )
)

# Tray icons
tray_icons = glob.glob(os.path.join("files", "icons", "tray", "*"))

for icon_name in tray_icons:
    data_files.append(
        (
            "share/icons/hicolor/scalable/apps",
            [icon_name]
        )
    )

# Desktop file
data_files.append(
    (
        "share/applications",
        ["files/org.nicotine_plus.Nicotine.desktop"]
    )
)

# AppStream metainfo
data_files.append(
    (
        "share/metainfo",
        ["files/org.nicotine_plus.Nicotine.metainfo.xml"]
    )
)

# Documentation
doc_files = glob.glob("[!404.md]*.md") + glob.glob(os.path.join("doc", "*.md"))

for doc in doc_files:
    data_files.append(
        (
            "share/doc/nicotine",
            [doc]
        )
    )

data_files.append(
    (
        "share/doc/nicotine",
        ["files/icons/CREDITS.md"]
    )
)

manpages = glob.glob(os.path.join("files", "*.1"))

for man in manpages:
    data_files.append(
        (
            "share/man/man1",
            [man]
        )
    )

# Translation
for po_file in glob.glob(os.path.join("po", "*.po")):
    lang = os.path.basename(po_file[:-3])

    mo_dir = os.path.join("mo", lang, "LC_MESSAGES")
    mo_file = os.path.join(mo_dir, "nicotine.mo")

    if not os.path.exists(mo_dir):
        os.makedirs(mo_dir)

    os.system("msgfmt " + po_file + " -o " + mo_file)

    targetpath = os.path.join("share", "locale", lang, "LC_MESSAGES")
    data_files.append(
        (
            targetpath,
            [mo_file]
        )
    )

if __name__ == '__main__':

    LONG_DESCRIPTION = """Nicotine+ is a graphical client for the Soulseek peer-to-peer
file sharing network.

Nicotine+ aims to be a pleasant, Free and Open Source (FOSS)
alternative to the official Soulseek client, providing additional
functionality while keeping current with the Soulseek protocol."""

    setup(
        name="nicotine-plus",
        version=version,
        license="GPLv3",
        description="Graphical client for the Soulseek file sharing network",
        long_description=LONG_DESCRIPTION,
        author="Nicotine+ Team",
        author_email="nicotine-team@lists.launchpad.net",
        url="https://nicotine-plus.org/",
        platforms="any",
        packages=packages,
        package_data=package_data,
        scripts=["nicotine"],
        data_files=data_files,
        python_requires='>=3.5',
        install_requires=['PyGObject>=3.18']
    )
