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

block_cipher = None

from PyInstaller.utils.hooks import get_gi_typelibs

import glob
import os
import sys

sys.modules['FixTk'] = None
sys.modules['lib2to3'] = None

# HarfBuzz has seemingly been added as a dependency for GTK on Windows (and perhaps MacOS?) recently
# TODO: investigate why this is the case, and potentially check with PyInstaller devs (30 August 2020)
binaries, datas, hiddenimports = get_gi_typelibs('HarfBuzz', '0.0')

# Include CA bundle for update checker
hiddenimports.append('certifi')

if sys.platform == 'win32':
    # Notification support on Windows
    hiddenimports.append('plyer.platforms.win.notification')

elif sys.platform == 'darwin':
    # Notification support on macOS
    hiddenimports.append('plyer.platforms.macosx.notification')

# Files to be added to the frozen app
added_files = [
    #
    # Application core modules
    #

    # About icon
    ('../org.nicotine_plus.Nicotine.svg', 'share/icons/hicolor/scalable/apps'),

    # Tray icons
    ('../../img/tray', 'share/icons/hicolor/32x32/apps'),

    # GTK Builder files, plugins, geoip database
    ('../../pynicotine', 'pynicotine')
]

# Translation
for po_file in glob.glob("po/*.po"):

    lang = os.path.basename(po_file[:-3])

    mo_dir = "mo/" + lang + "/LC_MESSAGES"
    mo_file = mo_dir + "/" + "nicotine.mo"

    if not os.path.exists(mo_dir):
        os.makedirs(mo_dir)

    os.system("msgfmt " + po_file + " -o " + mo_file)

    targetpath = "share/locale/" + lang + "/LC_MESSAGES"

    datas.append(
        (
            "../../" + mo_file,
            targetpath
        )
    )

datas += added_files

a = Analysis(['../../nicotine'],
             pathex=['.'],
             binaries=binaries,
             datas=datas,
             hiddenimports=hiddenimports,
             hookspath=[],
             runtime_hooks=[],
             excludes=['FixTk', 'lib2to3', 'tcl', 'tk', '_tkinter', 'tkinter', 'Tkinter'],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

# Remove unwanted files
for file in a.datas[:]:
    excluded = ('.ani', '.cur', '.md', '.py', '.pyc')

    if file[0].endswith(excluded) or \
        file[0].endswith('.png') and not 'org.nicotine_plus.Nicotine' in file[0] or \
        'share/icons/Adwaita/cursors' in file[0]:
        a.datas.remove(file)

pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

name = 'Nicotine+'
icon = 'nicotine.ico'

if sys.platform == 'darwin':
    icon = 'nicotine.icns'

enable_upx = True

if sys.platform == 'win32' and os.environ['ARCH'] == 'i686':
    # Disable UPX on 32-bit Windows, otherwise Nicotine+ won't start
    enable_upx = False

exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name=name,
          debug=False,
          strip=False,
          upx=enable_upx,
          console=False,
          icon=icon)

coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=enable_upx,
               name=name)

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
