#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2007 Daelstorm <daelstorm@gmail.com>
#
# GNU GENERAL PUBLIC LICENSE
#    Version 3, 29 June 2007
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from os import getcwd, listdir, system
from os.path import exists, isdir, join

contents = listdir(getcwd())

for lang in contents:
    lc_messages = join(lang, "LC_MESSAGES")
    if isdir(lc_messages):
        pofile = join(lc_messages, "nicotine.po")
        mofile = join(lc_messages, "nicotine.mo")
        if exists(pofile):
            system("msgfmt \"%s\" -o \"%s\" " % (pofile, mofile))
