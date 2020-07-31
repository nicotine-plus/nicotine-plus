# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

import sys
sys.modules['FixTk'] = None
sys.modules['lib2to3'] = None

# Files to be added to the frozen app
added_files = [
    #
    # Application core modules
    #

    # About icon
    ('../org.nicotine_plus.Nicotine.svg', 'share/icons/hicolor/scalable/apps'),

    # GTK Builder files, plugins, geoip database
    ('../../pynicotine', 'pynicotine'),

    # Translation files
    ('../../languages', 'languages'),
]

a = Analysis(['../../nicotine'],
             pathex=['.'],
             binaries=[],
             datas=added_files,
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=['FixTk', 'lib2to3', 'tcl', 'tk', '_tkinter', 'tkinter', 'Tkinter'],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

# Removing po files, translation template and translation tools
a.binaries = [
    x for x in a.binaries if not x[0].endswith(('.po', '.pot', 'merge_all', 'msgfmtall.py', 'remove_fuzzy', 'remove_mo', 'update_pot.py'))
]

pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='Nicotine+',
          debug=False,
          strip=False,
          upx=True,
          console=False,
          icon='nicotine-plus.ico')
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='Nicotine+')
