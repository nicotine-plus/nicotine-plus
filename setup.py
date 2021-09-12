#!/usr/bin/env python3
# COPYRIGHT (C) 2020-2021 Nicotine+ Team
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
    To install Nicotine+ on a GNU/Linux distribution, run:
    pip3 install .
"""

import glob
import os
import sys
import warnings

from distutils.core import setup
from pkgutil import walk_packages

import pynicotine

from pynicotine.config import config


def generate_translations():

    mo_entries = []
    languages = []

    for po_file in glob.glob("po/*.po"):
        lang = os.path.basename(po_file[:-3])
        languages.append(lang)

        mo_dir = os.path.join("mo", lang, "LC_MESSAGES")
        mo_file = os.path.join(mo_dir, "nicotine.mo")

        if not os.path.exists(mo_dir):
            os.makedirs(mo_dir)

        exit_code = os.system("msgfmt --check " + po_file + " -o " + mo_file)

        if exit_code > 0:
            sys.exit(exit)

        targetpath = os.path.join("share", "locale", lang, "LC_MESSAGES")
        mo_entries.append((targetpath, [mo_file]))

    # Merge translations into .desktop and metainfo files
    for desktop_file in glob.glob("data/*.desktop.in"):
        os.system("msgfmt --desktop --template=" + desktop_file + " -d po -o " + desktop_file[:-3])

    for metainfo_file in glob.glob("data/*.metainfo.xml.in"):
        os.system("msgfmt --xml --template=" + metainfo_file + " -d po -o " + metainfo_file[:-3])

    return mo_entries, languages


if __name__ == '__main__':

    # Suppress distutils 'Unknown distribution option' for python_requires and install_requires.
    # The aforementioned options are only used by pip and PyPi, distutils doesn't understand them.
    warnings.filterwarnings("ignore", message="Unknown distribution option")

    # Specify a description for the PyPi project page
    LONG_DESCRIPTION = """Nicotine+ is a graphical client for the Soulseek peer-to-peer
network.

Nicotine+ aims to be a pleasant, Free and Open Source (FOSS)
alternative to the official Soulseek client, providing additional
functionality while keeping current with the Soulseek protocol."""

    # Specify included files
    PACKAGES = ["pynicotine"] + \
        [name for importer, name, ispkg in walk_packages(path=pynicotine.__path__, prefix="pynicotine.") if ispkg]
    PACKAGE_DATA = dict((package, ["*.bin", "*.md", "*.py", "*.svg", "*.ui", "PLUGININFO"]) for package in PACKAGES)

    SCRIPTS = ["nicotine"]

    DATA_FILES = [
        ("share/applications", glob.glob("data/*.desktop")),
        ("share/metainfo", glob.glob("data/*.metainfo.xml")),
        ("share/icons/hicolor/scalable/apps", glob.glob("pynicotine/gtkgui/icons/hicolor/scalable/apps/*.svg")),
        ("share/icons/hicolor/symbolic/apps", glob.glob("pynicotine/gtkgui/icons/hicolor/symbolic/apps/*.svg")),
        ("share/doc/nicotine", glob.glob("[!404.md]*.md") + glob.glob("doc/*.md") + ["COPYING"]),
        ("share/man/man1", glob.glob("data/*.1"))
    ] + generate_translations()[0]

    # Run setup
    setup(
        name="nicotine-plus",
        version=config.version,
        license="GPLv3+",
        description="Graphical client for the Soulseek peer-to-peer network",
        long_description=LONG_DESCRIPTION,
        author="Nicotine+ Team",
        author_email="nicotine-team@lists.launchpad.net",
        url="https://nicotine-plus.org/",
        platforms="any",
        packages=PACKAGES,
        package_data=PACKAGE_DATA,
        scripts=SCRIPTS,
        data_files=DATA_FILES,
        python_requires=">=3.5",
        install_requires=["PyGObject>=3.18"]
    )
