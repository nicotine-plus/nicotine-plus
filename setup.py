#!/usr/local/bin/python

"""To use this setup script to install Nicotine:

        python setup.py install

"""

import sys
import os
import glob

from distutils.core import setup
from distutils.sysconfig import get_python_lib

mo_dirs = glob.glob(os.path.join("languages", "*"))
files = []
for mo in mo_dirs:
	p, lang = os.path.split(mo)
	if lang in ("msgfmtall.py", "mergeall", "nicotine.pot"):
		continue
	files.append((os.path.join(sys.prefix, "share", "locale", lang, "LC_MESSAGES"), [os.path.join(mo, "nicotine.mo")]))
sound_dirs = glob.glob(os.path.join("sounds", "*"))
for sounds in sound_dirs:
	p, theme = os.path.split(sounds)
	for file in ["private.ogg", "room_nick.ogg", "details.txt", "license.txt"]:
		files.append((os.path.join(sys.prefix, "share", "nicotine", "sounds", theme), [os.path.join(sounds, file)]))
doc_files = glob.glob(os.path.join("doc", "*"))
for file in doc_files:
	files.append((os.path.join(sys.prefix, "share", "nicotine", "documentation"), [file]))
files.append((os.path.join(sys.prefix, "share", "applications"), ["files/nicotine.desktop"]))
# Manuals
manpages = glob.glob(os.path.join("manpages", "*.1"))
for man in manpages:
	files.append((os.path.join(sys.prefix, "share", "man", "man1"), [man]))
files.append((os.path.join(sys.prefix, "share", "pixmaps"), ["files/nicotine-plus-32px.png"]))
if sys.platform.startswith("win"):
  try:
    import py2exe
  except ImportError:
    pass

if __name__ == '__main__' :
    LONG_DESCRIPTION = \
""" Nicotine-Plus is a client for SoulSeek filesharing system, forked from Nicotine. 
"""

    from pynicotine.utils import version

    setup(name                  = "nicotine",
          version               = version,
          license               = "GPLv3",
          description           = "Client for SoulSeek filesharing system.",
          author                = "daelstorm",
          author_email          = "daelstorm@gmail.com",
          url                   = "http://nicotine-plus.sourceforge.net/",
          packages              = [ 'pynicotine', 'pynicotine.gtkgui' ],
          scripts               = [ 'nicotine','nicotine-import-winconfig'],
          long_description      = LONG_DESCRIPTION,
          data_files		= files
         )

