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
translations = []
for mo in mo_dirs:
	p, lang = os.path.split(mo)
	if lang == "nicotine.pot":
		continue
	translations.append((os.path.join(sys.prefix, "share", "locale", lang, "LC_MESSAGES"), [os.path.join(mo, "nicotine.mo")]))
	
if sys.platform.startswith("win"):
  try:
    import py2exe
  except ImportError:
    pass

if __name__ == '__main__' :
    LONG_DESCRIPTION = \
""" Nicotine is a client for SoulSeek filesharing system. 
"""

    from pynicotine.utils import version

    setup(name                  = "nicotine",
          version               = version,
          license               = "GPL",
          description           = "Client for SoulSeek filesharing system.",
          author                = "Hyriand",
          author_email          = "hyriand@thegraveyard.org",
          url                   = "http://nicotine.thegraveyard.org/",
          packages              = [ 'pynicotine', 'pynicotine.gtkgui' ],
          scripts               = [ 'nicotine','nicotine-import-winconfig'],
          long_description      = LONG_DESCRIPTION,
          data_files		= translations
         )

