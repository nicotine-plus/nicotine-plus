# -*- mode: python ; coding: utf-8 -*-
 
block_cipher = None
 
 
# Files to be added to the frozen app
added_files = [
    #
    # Application core modules
    #
 
    # GTK Builder files
    ('../../pynicotine/gtkgui/ui/*.ui', 'pynicotine/gtkgui/ui'),

    # GeoIP database
    ('../../pynicotine/geoip/ipcountrydb.bin', 'pynicotine/geoip'),
    
    # Icon
    ('../../files/org.nicotine_plus.Nicotine.svg', 'share/icons/hicolor/scalable/apps'),
 
    # Translation files
    ('../../languages', 'languages'),

    # Plugins
    ('../../plugins', 'share/nicotine/plugins'),

    # Sounds
    ('../../sounds', 'share/nicotine/sounds'),

    # License file
    ('../../COPYING', '.'),
 
    # News file
    ('../../NEWS', '.'),
]
 
a = Analysis(['../../nicotine'],
             pathex=['.'],
             binaries=[],
             datas=added_files,
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
 
# Removing po files, translation template and translation tools
a.binaries = [
    x for x in a.binaries if not x[0].endswith(('.po', '.pot', 'mergeall', 'msgfmtall.py', 'tr_gen.py'))
]
 
# Removing the changelog and markdown files
a.binaries = [
    x for x in a.binaries if not x[0].endswith(('CHANGELOG_DOCS', '.md'))
]
 
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='Nicotine+',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False,
          icon='../../files/windows/nicotine-plus.ico')
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='Nicotine+')
