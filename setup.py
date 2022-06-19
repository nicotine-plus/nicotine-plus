#!/usr/bin/env python3
# COPYRIGHT (C) 2020-2022 Nicotine+ Contributors
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

from setuptools import find_packages
from setuptools import setup
from setuptools.command.build_py import build_py

from pynicotine.config import config
from pynicotine.i18n import build_translations
from pynicotine.i18n import get_translation_paths


class BuildPyCommand(build_py):

    def run(self):
        build_translations()
        build_py.run(self)


if __name__ == '__main__':

    setup(
        name="nicotine-plus",
        version=config.version,
        license="GPLv3+",
        description="Graphical client for the Soulseek peer-to-peer network",
        long_description="""Nicotine+ is a graphical client for the Soulseek peer-to-peer
network.

Nicotine+ aims to be a pleasant, free and open source (FOSS)
alternative to the official Soulseek client, providing additional
functionality while keeping current with the Soulseek protocol.""",
        author=config.author,
        author_email="nicotine-team@lists.launchpad.net",
        url=config.website_url,
        platforms="any",
        classifiers=[
            "Development Status :: 5 - Production/Stable",
            "Environment :: X11 Applications :: GTK",
            "Intended Audience :: End Users/Desktop",
            "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
            "Operating System :: OS Independent",
            "Programming Language :: Python",
            "Topic :: Communications :: Chat",
            "Topic :: Communications :: File Sharing",
            "Topic :: Internet",
            "Topic :: System :: Networking"
        ],
        packages=find_packages(include=["pynicotine", "pynicotine.*"]),
        package_data={"": ["*.bin", "*.ui", "PLUGININFO"]},
        scripts=["nicotine"],
        data_files=[
            ("share/applications", glob.glob("data/*.desktop")),
            ("share/metainfo", glob.glob("data/*.appdata.xml")),
            ("share/icons/hicolor/scalable/apps", glob.glob("pynicotine/gtkgui/icons/hicolor/scalable/apps/*.svg")),
            ("share/icons/hicolor/scalable/intl", glob.glob("pynicotine/gtkgui/icons/hicolor/scalable/intl/*.svg")),
            ("share/icons/hicolor/scalable/status", glob.glob("pynicotine/gtkgui/icons/hicolor/scalable/status/*.svg")),
            ("share/icons/hicolor/symbolic/apps", glob.glob("pynicotine/gtkgui/icons/hicolor/symbolic/apps/*.svg")),
            ("share/man/man1", glob.glob("data/*.1"))
        ] + get_translation_paths(),
        python_requires=">=3.5",
        install_requires=["PyGObject>=3.18"],
        cmdclass={"build_py": BuildPyCommand}
    )
