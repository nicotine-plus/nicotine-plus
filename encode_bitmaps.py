#!/usr/bin/env python
import os
import sys, string
from os.path import isfile

table = [
	["away.png", "away"],
	["online.png", "online"],
	["offline.png", "offline"],
	["connect.png", "connect"],
	["disconnect.png", "disconnect"],
	["away2.png", "away2"],
	["empty.png", "empty"],
	["hilite.png", "hilite"],
	["hilite2.png", "hilite2"],
	["nicotine+.png", "nicotinen"],
	["n.png", "n"],
	["notify.png", "notify"],
]
flagtable = []
for name in os.listdir(os.path.join("img", "geoip")):
	p = os.path.join("img", "geoip", name)
	if isfile(p):
		flagtable.append((os.path.join("img", "geoip", name), 'flag_%s' % name[:2].upper()))

outf = open(os.path.join("pynicotine","gtkgui","imagedata.py"), "w")
for image in table:
	print image[0]
	f = open(os.path.join("img", image[0]), "rb")
	d = f.read()
	f.close()
	outf.write("%s = %s\n" % (image[1], `d`))
for image in flagtable:
	print image[0]
	f = open(image[0], "rb")
	outf.write("%s = %r\n" % (image[1], f.read()))
	f.close()
outf.close()
