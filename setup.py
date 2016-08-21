#!/usr/bin/python

"""To use this setup script to install Nicotine:

    # Install Nicotine+ in regular *nix directories
    python setup.py install

    # Create exe files for windows in dist subdir
    python setup.py py2exe
"""

import sys
import os
import glob

from os import listdir
from os.path import isdir

from distutils.core import setup
from distutils.sysconfig import get_python_lib

# Are we running windows ?
if sys.platform.startswith("win"):
    is_windows = True
else:
    is_windows = False

# If we're on windows, try to load py2exe and detects GTK+ path
if is_windows:
    import _winreg
    try:
        import py2exe
    except ImportError:
        print "Py2exe is required to build Windows binaries."
        print "Please go to: http://www.py2exe.org/"
        sys.exit(1)
    try:
        k = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, "Software\\GTK\\2.0")
    except EnvironmentError:
        print "You must install the Gtk+ Runtime Environment to create Windows binaries."
        print "Please go to: http://sourceforge.net/projects/gtk-win/"
        sys.exit(1)

# Compute data_files (GTK for windows, man and stuff for *nix)
files = []

if is_windows:
    # Get Gtk+ path (we need to copy lib, share and etc subdir to binary path
    gtkdir = _winreg.QueryValueEx(k, "Path")[0].strip(os.sep)
    langdir = os.path.join(gtkdir, 'share', 'locale')
    langs = [x for x in listdir('languages') if isdir(os.path.join('languages', x))]
    for gtksubdir in ["lib", "share", "etc"]:
        gtkdirfull = os.path.join(gtkdir, gtksubdir)
        skip = len(gtkdirfull)+1
        for varroot, vardirs, varfiles in os.walk(gtkdirfull, topdown=True):
            relativepath = os.path.join(gtksubdir, varroot[skip:])
            absolutefiles = [os.path.join(varroot, x) for x in varfiles]
            if varroot == langdir:
                junk = []
                for d in vardirs:
                    if d not in langs:
                        print "We don't have a language file for " + d + ", removing from list."
                        junk.append(d)
                for j in junk:
                    vardirs.remove(j)
            if absolutefiles:
                files.append((relativepath, absolutefiles))
    # We need to include libjpeg
    files.append(("", ([os.path.join(gtkdir, 'bin', 'jpeg62.dll')])))
else:
    # Manuals
    manpages = glob.glob(os.path.join("manpages", "*.1"))
    for man in manpages:
        files.append((os.path.join(sys.prefix, "share", "man", "man1"), [man]))

    # Icons with fixed size
    for sizeicons in ["16x16", "32x32", "48x48", "64x64", "96x96"]:
        files.append(
            (
                os.path.join(sys.prefix, "share", "icons", "hicolor", sizeicons, "apps"),
                ["files/icons/" + sizeicons + "/nicotine-plus.png"]
            )
        )

    # Scalable icons
    files.append(
        (
            os.path.join(sys.prefix, "share", "icons", "hicolor", "scalable", "apps"),
            ["files/icons/scalable/nicotine-plus.svg"]
        )
    )

    # Desktop file
    files.append((os.path.join(sys.prefix, "share", "applications"), ["files/nicotine.desktop"]))


# Translation files
mo_dirs = [x for x in glob.glob(os.path.join("languages", "*")) if isdir(x)]

for mo in mo_dirs:

    p, lang = os.path.split(mo)
    lc_messages_path = os.path.join(mo, "LC_MESSAGES")

    if lang in ("msgfmtall.py", "tr_gen.py", "mergeall", "nicotine.pot"):
        continue

    if is_windows:
        files.append(
            (
                os.path.join("share", "locale", lang, "LC_MESSAGES"),
                [os.path.join(lc_messages_path, "nicotine.mo")]
            )
        )
    else:
        files.append(
            (
                os.path.join(sys.prefix, "share", "locale", lang, "LC_MESSAGES"),
                [os.path.join(lc_messages_path, "nicotine.mo")]
            )
        )

# Sounds
sound_dirs = glob.glob(os.path.join("sounds", "*"))

for sounds in sound_dirs:
    p, theme = os.path.split(sounds)
    for file in ["private.ogg", "room_nick.ogg", "details.txt", "license.txt"]:
        if is_windows:
            files.append((os.path.join("share", "nicotine", "sounds", theme), [os.path.join(sounds, file)]))
        else:
            files.append((os.path.join(sys.prefix, "share", "nicotine", "sounds", theme), [os.path.join(sounds, file)]))

# Documentation on GNU/Linux
if not is_windows:

    for (path, dirs, docfiles) in os.walk("doc"):

        dst_path = os.sep.join(path.split("/")[1:])

        for f in docfiles:
            files.append(
                (
                    os.path.join(sys.prefix, "share", "nicotine", "documentation", dst_path),
                    [os.path.join(path, f)]
                )
            )


if __name__ == '__main__':

    from pynicotine.utils import version
    LONG_DESCRIPTION = """Nicotine+ is a client for SoulSeek filesharing system, forked from Nicotine."""

    if is_windows:
        setup(
            name="nicotine",
            version=version,
            license="GPLv3",
            description="Nicotine+, a client for the SoulSeek filesharing network.",
            author="daelstorm",
            author_email="daelstorm@gmail.com",
            url="http://www.nicotine-plus.org/",
            packages=['pynicotine', 'pynicotine.gtkgui'],
            package_dir={'pynicotine.gtkgui': 'pynicotine/gtkgui'},
            package_data={'pynicotine.gtkgui': ["*.py", "*.glade", "*.ui"]},
            scripts=['nicotine.py'],
            long_description=LONG_DESCRIPTION,
            data_files=files,
            windows=[
                {
                    "script": "nicotine.py",
                    "icon_resources": [(0, "img/ico/nicotine-plus-48x48.ico")]
                }
            ],
            options={
                'py2exe': {
                    'skip_archive': True,
                    'packages': 'encodings',
                    'includes': 'cairo, pango, pangocairo, atk, gobject, dbhash, mutagen'
                }
            }
        )
    else:
        setup(
            name="nicotine",
            version=version,
            license="GPLv3",
            description="Nicotine+, a client for the SoulSeek filesharing network.",
            author="daelstorm",
            author_email="daelstorm@gmail.com",
            url="http://www.nicotine-plus.org/",
            packages=['pynicotine', 'pynicotine.gtkgui'],
            package_dir={'pynicotine.gtkgui': 'pynicotine/gtkgui'},
            package_data={'pynicotine.gtkgui': ["*.py", "*.glade", "*.ui"]},
            scripts=['nicotine.py'],
            long_description=LONG_DESCRIPTION,
            data_files=files
        )
