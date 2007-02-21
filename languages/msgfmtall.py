#!/usr/bin/python

import os, sys
import dircache


contents = dircache.listdir("./")

for filename in contents:
	if os.path.isdir(filename):
		pofile = os.path.join(filename, "nicotine.po")
		mofile = os.path.join(filename, "nicotine.mo")
		if os.path.exists(pofile):
			os.system("msgfmt \"%s\" -o \"%s\" " % (pofile, mofile)) 


