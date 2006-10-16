import os
import sys, string

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
]

outf = open(os.path.join("pynicotine","gtkgui","imagedata.py"), "w")
for image in table:
	print image[0]
	f = open(os.path.join("img", image[0]), "rb")
	d = f.read()
	f.close()
	outf.write("%s = %s\n" % (image[1], `d`))
outf.close()
