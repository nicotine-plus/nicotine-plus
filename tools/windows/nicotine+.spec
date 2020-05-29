# -*- mode: python -*-

import sys


# Files to be added to the frozen app
added_files = [
    #
    # Application core modules
    #

    # GTK Builder files
    ('../../pynicotine/gtkgui/ui/*.ui', 'pynicotine/gtkgui/ui'),

    # Translation files
    ('../../languages', 'languages'),

    # License file
    ('../../COPYING', '.'),

    # News file
    ('../../NEWS', '.'),

    #
    # Additional dependencies
    #

    # Icon for the resulting Nicotine+.exe file and shortcuts
    ('../../files/win32/nicotine-plus.ico', 'files/win32'),
]

# Analysis pass
a = Analysis(
    ['../../nicotine'],
    pathex=['.'],
    binaries=None,
    datas=added_files,
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None
)

# Removing po files, translation template and translation tools
a.binaries = [
    x for x in a.binaries if not x[0].endswith(('.po', '.pot', 'mergeall', 'msgfmtall.py', 'tr_gen.py'))
]

# Removing the changelog and markdown files
a.binaries = [
    x for x in a.binaries if not x[0].endswith(('CHANGELOG_DOCS', '.md'))
]

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='Nicotine+',
    debug=False,
    strip=False,
    upx=True,
    console=False,
    icon='files/win32/nicotine-plus.ico'
)
