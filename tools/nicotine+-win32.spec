# -*- mode: python -*-

block_cipher = None

# Files to be added to the frozen app
added_files = [
    ( '../pynicotine/gtkgui/*.glade', 'pynicotine/gtkgui' ),
    ( '../pynicotine/gtkgui/*.ui', 'pynicotine/gtkgui' ),
    ( '../doc/NicotinePlusGuide', 'doc/NicotinePlusGuide' ),
    ( '../languages', 'languages' ),
    ( '../files/win32/upnpc', 'files/win32/upnpc' ),
    ( '../files/win32/nicotine-plus-128px.ico', 'files/win32' ),
    ( '../COPYING', '.' )
]

# Analysis pass
a = Analysis(['../nicotine.py'],
             pathex=['.'],
             binaries=None,
             datas=added_files,
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)

# Removing po files, translation template and translation tools
a.binaries = [
    x for x in a.binaries if not x[0].endswith(('.po', '.pot', 'mergeall', 'msgfmtall.py', 'tr_gen.py'))
]

# Removing the changelog and markdown files
a.binaries = [
    x for x in a.binaries if not x[0].endswith(('CHANGELOG_DOCS', '.md'))
]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name='Nicotine+',
    debug=False,
    strip=False,
    upx=False,
    console=False,
    icon='files/win32/nicotine-plus-128px.ico'
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name='Nicotine+'
)
