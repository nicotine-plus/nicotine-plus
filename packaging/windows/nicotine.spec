# -*- mode: python ; coding: utf-8 -*-

# COPYRIGHT (C) 2020 Nicotine+ Team
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

import glob
import os
import sys

from ctypes.util import find_library
from pkgutil import walk_packages

# Provide access to the pynicotine module
sys.path.append('.')

import pynicotine.plugins


""" Add Contents """


binaries = []
hiddenimports = []
added_files = []


# Files to be added to the frozen app
added_files += [

    # About icon
    ('../../files/org.nicotine_plus.Nicotine.svg', 'share/icons/hicolor/scalable/apps'),

    # Tray icons
    ('../../files/icons/tray', 'share/icons/hicolor/scalable/apps'),

    # GTK Builder files, plugins, geoip database
    ('../../pynicotine', 'pynicotine')
]


# Include plugins
hiddenimports += [name for importer, name, ispkg in walk_packages(path=pynicotine.plugins.__path__, prefix="pynicotine.plugins.") if ispkg]


# SSL support
hiddenimports.append('certifi')

if sys.platform == 'win32':
    # SSL support
    for i in ("libcrypto-1_1", "libssl-1_1", "libcrypto-1_1-x64", "libssl-1_1-x64"):
        lib = find_library(i)

        if lib is not None:
            binaries.append((lib, '.'))

    if not binaries:
        raise Exception("No SSL libraries found")


# Translations
languages = set()

for po_file in glob.glob("po/*.po"):
    lang = os.path.basename(po_file[:-3])
    languages.add(lang)

    mo_dir = "mo/" + lang + "/LC_MESSAGES"
    mo_file = mo_dir + "/" + "nicotine.mo"

    if not os.path.exists(mo_dir):
        os.makedirs(mo_dir)

    os.system("msgfmt " + po_file + " -o " + mo_file)

    targetpath = "share/locale/" + lang + "/LC_MESSAGES"

    added_files.append(
        (
            "../../" + mo_file,
            targetpath
        )
    )


# Analyze required files
a = Analysis(['../../nicotine'],
             pathex=['.'],
             binaries=binaries,
             datas=added_files,
             hiddenimports=hiddenimports,
             hookspath=[],
             runtime_hooks=[],
             excludes=['FixTk', 'lib2to3', 'tcl', 'tk', '_tkinter', 'tkinter', 'Tkinter'],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=None,
             noarchive=False)


# Remove unwanted files added in previous step
for file in a.datas[:]:
    excluded = ('.ani', '.cur', '.md', '.png', '.py', '.pyc')

    if file[0].endswith(excluded):
        a.datas.remove(file)

    elif 'share/icons' in file[0] or \
            'share/themes' in file[0]:
        theme = file[0].split('/')[2]

        # Remove unwanted themes
        if theme not in ('Adwaita', 'hicolor', 'win32'):
            a.datas.remove(file)

        elif 'Adwaita/cursors' in file[0]:
            a.datas.remove(file)

    elif 'share/locale' in file[0]:
        lang = file[0].split('/')[2]

        # Remove system translations for unsupported languages
        if lang not in languages:
            a.datas.remove(file)


""" Archive """


pyz = PYZ(a.pure, a.zipped_data,
             cipher=None)


""" Freeze Application """


name = 'Nicotine+'
icon = 'nicotine.ico'

if sys.platform == 'darwin':
    icon = 'nicotine.icns'

exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name=name,
          debug=False,
          strip=False,
          upx=False,
          console=False,
          icon=icon)


coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=False,
               name=name)


""" Create macOS .app """


if sys.platform == 'darwin':

    info_plist = {
        "CFBundleDisplayName": name,
        "NSHighResolutionCapable": True,
    }

    app = BUNDLE(coll,
             name=name + '.app',
             icon=icon,
             info_plist=info_plist,
             bundle_identifier='org.nicotine_plus.Nicotine')
