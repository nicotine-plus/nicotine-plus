#!/usr/bin/env python3
# COPYRIGHT (C) 2023 Nicotine+ Contributors
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

from setuptools import setup  # pylint: disable=import-error

from pynicotine.i18n import build_translations


if __name__ == "__main__":
    build_translations()
    setup(
        data_files=[
            ("share/applications", ["data/org.nicotine_plus.Nicotine.desktop"]),
            ("share/metainfo", ["data/org.nicotine_plus.Nicotine.appdata.xml"]),
            ("share/man/man1", ["data/nicotine.1"]),
            ("share/icons/hicolor/16x16/apps",
                ["pynicotine/gtkgui/icons/hicolor/16x16/apps/org.nicotine_plus.Nicotine.png"]),
            ("share/icons/hicolor/24x24/apps",
                ["pynicotine/gtkgui/icons/hicolor/24x24/apps/org.nicotine_plus.Nicotine.png"]),
            ("share/icons/hicolor/32x32/apps",
                ["pynicotine/gtkgui/icons/hicolor/32x32/apps/org.nicotine_plus.Nicotine.png"]),
            ("share/icons/hicolor/48x48/apps",
                ["pynicotine/gtkgui/icons/hicolor/48x48/apps/org.nicotine_plus.Nicotine.png"]),
            ("share/icons/hicolor/64x64/apps",
                ["pynicotine/gtkgui/icons/hicolor/64x64/apps/org.nicotine_plus.Nicotine.png"]),
            ("share/icons/hicolor/128x128/apps",
                ["pynicotine/gtkgui/icons/hicolor/128x128/apps/org.nicotine_plus.Nicotine.png"]),
            ("share/icons/hicolor/256x256/apps",
                ["pynicotine/gtkgui/icons/hicolor/256x256/apps/org.nicotine_plus.Nicotine.png"]),
            ("share/icons/hicolor/scalable/apps",
                ["pynicotine/gtkgui/icons/hicolor/scalable/apps/org.nicotine_plus.Nicotine.svg"]),
            ("share/icons/hicolor/scalable/apps",
                ["pynicotine/gtkgui/icons/hicolor/scalable/apps/org.nicotine_plus.Nicotine-away.svg"]),
            ("share/icons/hicolor/scalable/apps",
                ["pynicotine/gtkgui/icons/hicolor/scalable/apps/org.nicotine_plus.Nicotine-connect.svg"]),
            ("share/icons/hicolor/scalable/apps",
                ["pynicotine/gtkgui/icons/hicolor/scalable/apps/org.nicotine_plus.Nicotine-disconnect.svg"]),
            ("share/icons/hicolor/scalable/apps",
                ["pynicotine/gtkgui/icons/hicolor/scalable/apps/org.nicotine_plus.Nicotine-msg.svg"]),
            ("share/icons/hicolor/symbolic/apps",
                ["pynicotine/gtkgui/icons/hicolor/symbolic/apps/org.nicotine_plus.Nicotine-symbolic.svg"])
        ]
    )
