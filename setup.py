#!/usr/bin/env python3
# COPYRIGHT (C) 2023-2024 Nicotine+ Contributors
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

import os
import subprocess

from setuptools import setup  # pylint: disable=import-error


def build_translations():
    """Builds .mo translation files in the 'locale' folder of the package."""

    base_path = os.path.dirname(os.path.realpath(__file__))
    locale_path = os.path.join(base_path, "pynicotine", "locale")

    with open(os.path.join(base_path, "po", "LINGUAS"), encoding="utf-8") as file_handle:
        languages = file_handle.read().splitlines()

    for language_code in languages:
        lang_folder_path = os.path.join(locale_path, language_code)
        lc_messages_folder_path = os.path.join(lang_folder_path, "LC_MESSAGES")
        po_file_path = os.path.join(base_path, "po", f"{language_code}.po")
        mo_file_path = os.path.join(lc_messages_folder_path, "nicotine.mo")

        if not os.path.exists(lc_messages_folder_path):
            os.makedirs(lc_messages_folder_path)

        for path in (locale_path, lang_folder_path, lc_messages_folder_path):
            with open(os.path.join(path, "__init__.py"), "wb") as file_handle:
                # Create empty file
                pass

        subprocess.check_call(["msgfmt", "--check", po_file_path, "-o", mo_file_path])

    # Merge translations into .desktop and appdata files
    with os.scandir(os.path.join(base_path, "data")) as entries:
        for entry in entries:
            if entry.name.endswith(".desktop.in"):
                subprocess.check_call(["msgfmt", "--desktop", f"--template={entry.path}", "-d", "po",
                                       "-o", entry.path[:-3]])

            elif entry.name.endswith(".appdata.xml.in"):
                subprocess.check_call(["msgfmt", "--xml", f"--template={entry.path}", "-d", "po",
                                       "-o", entry.path[:-3]])


def convert_icons():
    """Converts vector application icons to raster format."""

    for icon_size in (
        "16x16", "24x24", "32x32", "48x48", "64x64", "128x128", "256x256",
        "16x16@2", "24x24@2", "32x32@2", "48x48@2", "64x64@2", "128x128@2", "256x256@2"
    ):
        input_file_path = os.path.join(
            "pynicotine", "gtkgui", "icons", "hicolor", icon_size, "apps", "org.nicotine_plus.Nicotine.svg"
        )
        output_folder_path = os.path.join("build", "icons", icon_size)
        output_file_path = os.path.join(output_folder_path, "org.nicotine_plus.Nicotine.png")

        os.makedirs(output_folder_path, exist_ok=True)
        subprocess.check_call(["rsvg-convert", input_file_path, "-o", output_file_path])


if __name__ == "__main__":
    build_translations()
    convert_icons()
    setup(
        data_files=[
            ("share/applications", ["data/org.nicotine_plus.Nicotine.desktop"]),
            ("share/metainfo", ["data/org.nicotine_plus.Nicotine.appdata.xml"]),
            ("share/man/man1", ["data/nicotine.1"]),
            ("share/icons/hicolor/16x16/apps",
                ["build/icons/16x16/org.nicotine_plus.Nicotine.png"]),
            ("share/icons/hicolor/16x16@2/apps",
                ["build/icons/16x16@2/org.nicotine_plus.Nicotine.png"]),
            ("share/icons/hicolor/24x24/apps",
                ["build/icons/24x24/org.nicotine_plus.Nicotine.png"]),
            ("share/icons/hicolor/24x24@2/apps",
                ["build/icons/24x24@2/org.nicotine_plus.Nicotine.png"]),
            ("share/icons/hicolor/32x32/apps",
                ["build/icons/32x32/org.nicotine_plus.Nicotine.png"]),
            ("share/icons/hicolor/32x32@2/apps",
                ["build/icons/32x32@2/org.nicotine_plus.Nicotine.png"]),
            ("share/icons/hicolor/48x48/apps",
                ["build/icons/48x48/org.nicotine_plus.Nicotine.png"]),
            ("share/icons/hicolor/48x48@2/apps",
                ["build/icons/48x48@2/org.nicotine_plus.Nicotine.png"]),
            ("share/icons/hicolor/64x64/apps",
                ["build/icons/64x64/org.nicotine_plus.Nicotine.png"]),
            ("share/icons/hicolor/64x64@2/apps",
                ["build/icons/64x64@2/org.nicotine_plus.Nicotine.png"]),
            ("share/icons/hicolor/128x128/apps",
                ["build/icons/128x128/org.nicotine_plus.Nicotine.png"]),
            ("share/icons/hicolor/128x128@2/apps",
                ["build/icons/128x128@2/org.nicotine_plus.Nicotine.png"]),
            ("share/icons/hicolor/256x256/apps",
                ["build/icons/256x256/org.nicotine_plus.Nicotine.png"]),
            ("share/icons/hicolor/256x256@2/apps",
                ["build/icons/256x256@2/org.nicotine_plus.Nicotine.png"]),
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
