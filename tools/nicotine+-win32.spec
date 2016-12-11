# -*- mode: python -*-

import sys

GTK2_RUNTIME = sys.prefix + '\\Lib\\site-packages\\gtk-2.0\\runtime\\'

# Files to be added to the frozen app
added_files = [
    #
    # Application core modules
    #

    # Glade files
    ('../pynicotine/gtkgui/*.glade', 'pynicotine/gtkgui'),

    # GTK Builder files
    ('../pynicotine/gtkgui/*.ui', 'pynicotine/gtkgui'),

    # Nicotine+ Guide
    ('../doc/NicotinePlusGuide', 'doc/NicotinePlusGuide'),

    # Translation files
    ('../languages', 'languages'),

    # License file
    ('../COPYING', '.'),

    # Maintainers file
    ('../AUTHORS.md', '.'),

    # News file
    ('../NEWS', '.'),

    #
    # Additional dependencies
    #

    # UPnPc static binary
    ('../files/win32/upnpc', 'files/win32/upnpc'),

    # Icon for the resulting Nicotine+.exe file
    ('../files/win32/nicotine-plus-128px.ico', 'files/win32'),

    # GTK2 rc file for theming
    ( GTK2_RUNTIME + 'etc\\gtk-2.0\\gtkrc', 'etc/gtk-2.0'),

    # GTK2 Tango icon theme
    ( GTK2_RUNTIME + 'share\\icons\\Tango', 'share/icons/Tango'),

    # GTK2 MS-Windows theme
    ( GTK2_RUNTIME + 'share\\themes\\MS-Windows', 'share/themes/MS-Windows'),

    # GTK2 WIMP engine
    ( GTK2_RUNTIME + 'lib\\gtk-2.0\\2.10.0\\engines\\libwimp.dll', 'lib/gtk-2.0/2.10.0/engines'),

    # GTK2 locales for translations of buttons
    ( GTK2_RUNTIME + 'share\\locale', 'share/locale')
]

# Analysis pass
a = Analysis(
    ['../nicotine.py'],
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
