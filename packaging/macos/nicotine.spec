# -*- mode: python ; coding: utf-8 -*-

# COPYRIGHT (C) 2020-2022 Nicotine+ Team
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
import ssl
import sys

# Provide access to the pynicotine module
sys.path.append(os.path.abspath(os.path.join(SPECPATH, "..", "..")))

from ctypes.util import find_library
from pkgutil import walk_packages

import pynicotine.plugins

from pynicotine.config import config
from pynicotine.i18n import build_translations
from pynicotine.i18n import get_translation_paths
from stdlib_list import stdlib_list


""" Add Contents """


binaries = []

# Add plugins and standard modules (for plugins)
hiddenimports = ["certifi"] + list(stdlib_list()) + \
    [name for importer, name, ispkg in walk_packages(path=pynicotine.plugins.__path__, prefix="pynicotine.plugins.") if ispkg]


# GTK Builder files, plugins, geoip database, translations
datas = [("../../pynicotine", "pynicotine")]
languages = build_translations()
mo_entries = get_translation_paths()

for target_path, mo_files in mo_entries:
    datas.append(("../../" + mo_files[0], target_path))


# Analyze required files
a = Analysis(['../../nicotine'],
             pathex=['.'],
             binaries=binaries,
             datas=datas,
             hiddenimports=hiddenimports,
             hookspath=[],
             runtime_hooks=[],
             hooksconfig={
                 "gi": {
                     "icons": ["Adwaita", "hicolor"],
                     "themes": ["Adwaita", "Mac"],
                     "languages": languages
                 }
             },
             excludes=['FixTk', 'idlelib', 'lib2to3', 'tcl', 'tk', '_tkinter', 'tkinter', 'Tkinter'],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=None,
             noarchive=False)


# Remove unwanted files added in previous step
excluded = ('.ani', '.cur', '.md', '.png', '.py', '.pyc')

for file in a.datas[:]:
    target_path = file[0]

    if target_path.endswith(excluded):
        a.datas.remove(file)


""" Archive """


pyz = PYZ(a.pure, a.zipped_data,
          cipher=None)


""" Freeze Application """


name = 'Nicotine+'

exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name=name,
          debug=False,
          strip=False,
          upx=False,
          console=False)


coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=False,
               name=name)


""" Create macOS .app """


app = BUNDLE(coll,
             name=name + '.app',
             icon='nicotine.icns',
             bundle_identifier='org.nicotine_plus.Nicotine',
             version=config.version)
