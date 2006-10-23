## Generorate win32 excutable for WindowsXP
## Useage: python make_exe.py py2exe -O2
## This file contains snippets from various sources.
## Copyright (C) 2003-2006 Yann Le Boulanger <asterix@lagaule.org>
## Copyright (C) 2005-2006 Nikos Kouremenos <kourem@gmail.com>
## Copyright (C) 2003-2004 Hyriand <hyriand@thegraveyard.org>
## Copyright (C) daelstorm <daelstorm@gmail.com>
## Copyright (C) 2006 Vandy Omall <osiris.contact@gmail.com>
##
##  This program is free software; you can redistribute it and/or modify
##  it under the terms of the GNU General Public License as published by
##  the Free Software Foundation; either version 2 of the License, or
##  (at your option) any later version.
##
##  This program is distributed in the hope that it will be useful,
##  but WITHOUT ANY WARRANTY; without even the implied warranty of
##  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##  GNU General Public License for more details.
##
##  You should have received a copy of the GNU General Public License
##  along with this program; if not, write to the Free Software
##  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import sys
import os
import glob

from distutils.core import setup
if sys.platform.startswith("win"):
  try:
    import py2exe
  except ImportError:
    pass

if __name__ == '__main__' :
    LONG_DESCRIPTION = \
""" Nicotine-Plus is a client for SoulSeek filesharing system, forked from Nicotine. """

    from pynicotine.utils import version

    setup(name                  = "nicotine",
          version               = version,
          license               = "GPL",
          description           = "Client for SoulSeek filesharing system.",
          author                = "daelstorm",
          author_email          = "daelstorm@gmail.com",
          url                   = "http://nicotine-plus.sourceforge.net/",
          packages              = [ 'pynicotine', 'pynicotine.gtkgui' ],
          scripts               = [ 'nicotine'],
          long_description      = LONG_DESCRIPTION,
          windows               = [{'script': 'nicotine', 'icon_resources': [(1, 'nicotine.ico')]}],
          options               = {
    'py2exe': {
        'includes': 'cairo,pango,pangocairo,atk,gobject,psyco,ogg,pywin',
        'dll_excludes': [
            'iconv.dll','intl.dll',
            'libatk-1.0-0.dll',
            'libgdk_pixbuf-2.0-0.dll',
            'libgdk-win32-2.0-0.dll',
            'libglib-2.0-0.dll',
            'libgmodule-2.0-0.dll',
            'libgobject-2.0-0.dll',
            'libgthread-2.0-0.dll',
            'libgtk-win32-2.0-0.dll',
            'libpango-1.0-0.dll',
            'libpangowin32-1.0-0.dll',
            'libpangocairo-1.0-0.dll',
            'libfontconfig-1.dll',
            'libcairo-2.dll',
            'freetype6.dll',
            'libxml2.dll'

            ],}}
          )
