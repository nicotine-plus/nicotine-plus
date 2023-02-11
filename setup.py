#!/usr/bin/env python3
# COPYRIGHT (C) 2020-2022 Nicotine+ Contributors
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2009-2010 quinox <quinox@users.sf.net>
# COPYRIGHT (C) 2009 hedonist <ak@sensi.org>
# COPYRIGHT (C) 2006-2009 daelstorm <daelstorm@gmail.com>
# COPYRIGHT (C) 2008-2009 eLvErDe <gandalf@le-vert.net>
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
from pynicotine.i18n import LOCALE_PATH
from pynicotine.i18n import build_translations


class BuildPyCommand(build_py):

    def run(self):
        build_translations()
        build_py.run(self)


if __name__ == "__main__":

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
        package_data={"": ["*.bin", "*.ui", "PLUGININFO"] + glob.glob(LOCALE_PATH + "/**/*.mo", recursive=True)},
        scripts=["nicotine"],
        data_files=[
            ("share/applications", ["data/%s.desktop" % config.application_id]),
            ("share/metainfo", ["data/%s.appdata.xml" % config.application_id]),
            ("share/man/man1", ["data/nicotine.1"]),
            ("share/icons/hicolor/16x16/apps",
                ["pynicotine/gtkgui/icons/hicolor/16x16/apps/%s.png" % config.application_id]),
            ("share/icons/hicolor/24x24/apps",
                ["pynicotine/gtkgui/icons/hicolor/24x24/apps/%s.png" % config.application_id]),
            ("share/icons/hicolor/32x32/apps",
                ["pynicotine/gtkgui/icons/hicolor/32x32/apps/%s.png" % config.application_id]),
            ("share/icons/hicolor/48x48/apps",
                ["pynicotine/gtkgui/icons/hicolor/48x48/apps/%s.png" % config.application_id]),
            ("share/icons/hicolor/64x64/apps",
                ["pynicotine/gtkgui/icons/hicolor/64x64/apps/%s.png" % config.application_id]),
            ("share/icons/hicolor/128x128/apps",
                ["pynicotine/gtkgui/icons/hicolor/128x128/apps/%s.png" % config.application_id]),
            ("share/icons/hicolor/256x256/apps",
                ["pynicotine/gtkgui/icons/hicolor/256x256/apps/%s.png" % config.application_id]),
            ("share/icons/hicolor/scalable/apps",
                ["pynicotine/gtkgui/icons/hicolor/scalable/apps/%s.svg" % config.application_id]),
            ("share/icons/hicolor/symbolic/apps",
                ["pynicotine/gtkgui/icons/hicolor/symbolic/apps/%s-symbolic.svg" % config.application_id]),
            ("share/icons/hicolor/scalable/intl", glob.glob("pynicotine/gtkgui/icons/hicolor/scalable/intl/*.svg")),
            ("share/icons/hicolor/scalable/status", glob.glob("pynicotine/gtkgui/icons/hicolor/scalable/status/*.svg"))
        ],
        python_requires=">=3.6",
        install_requires=["PyGObject>=3.22"],
        extras_require={"test": ["flake8", "pylint"]},
        cmdclass={"build_py": BuildPyCommand}
    )
