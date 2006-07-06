import os
import sys, string

table = [
	["away.gif", "away"],
	["online.gif", "online"],
	["offline.gif", "offline"],
	["empty.gif", "empty"],
	["hilite.gif", "hilite"],
	["nicotine-n.png", "nicotinen"],
]

outf = open(os.path.join("pynicotine","gtkgui","imagedata.py"), "w")
for image in table:
	print image[0]
	f = open(os.path.join("img", image[0]), "r")
	d = f.read()
	f.close()
	outf.write("%s = %s\n" % (image[1], `d`))
outf.close()
