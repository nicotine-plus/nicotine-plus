import os
import sys, string

table = [
	["connect.ico", "connect"],
	["disconnect.ico", "disconnect"],
	["away2.ico", "away2"],
	["hilite2.ico", "hilite2"],
]

outf = open(os.path.join("pynicotine","gtkgui","icondata.py"), "w")
for image in table:
	print image[0]
	f = open(os.path.join("img", image[0]), "rb")
	d = f.read()
	f.close()
	outf.write("%s = %s\n" % (image[1], `d`))
outf.close()
