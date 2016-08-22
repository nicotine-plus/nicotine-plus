# -*- mode: python -*-

block_cipher = None

added_files = [
    ( '../pynicotine/gtkgui/*.glade', 'pynicotine/gtkgui' ),
    ( '../pynicotine/gtkgui/*.ui', 'pynicotine/gtkgui' ),
    ( '../doc', 'doc' ),
    ( '../languages', 'languages' ),
    ( '../files/win32', 'files/win32' ),
    ( '../COPYING', '.' )
]

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
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='Nicotine+',
          debug=False,
          strip=False,
          upx=False,
          console=False,
          icon='files/win32/nicotine-plus-128px.ico')
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=False,
               name='Nicotine+')
