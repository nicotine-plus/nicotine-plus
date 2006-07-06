# Copyright (c) 2003-2004 Hyriand. All rights reserved.

import gtk
import urllib

from pynicotine.utils import version, latesturl, _

def makeversion(version):
	build = 255
	if version.find("pre") >= 0:
		ix = version.find("pre")
		build = int(version[ix+3:])
		version = version[:ix]
	elif version.find("rc") >= 0:
		ix = version.find("rc")
		build = int(version[ix+2:]) + 0x80
		version = version[:ix]
	s = version.split(".")
	major, minor, micro = [int(i) for i in s[:3]]
	return (major << 24) + (minor << 16) + (micro << 8) + build

def checklatest(frame):
	try:
		url = urllib.urlopen(latesturl)
		data = url.read().split("\n")[0]
		url.close()
		latest = makeversion(data)
	except Exception, m:
		dlg = gtk.MessageDialog(frame, 0, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, _("Could not retrieve version information!\nError: %s") % m)
		dlg.run()
		dlg.destroy()
		return
	myversion = makeversion(version)
	if latest > myversion:
		dlg = gtk.MessageDialog(frame, 0, gtk.MESSAGE_WARNING, gtk.BUTTONS_OK, _("A newer version ('%s') is available. Check\nthe Nicotine+ homepage, ( http://thegraveyard.org/daelstorm/nicotine-plus.php ) for the latest version.") % data)
	else:
		dlg = gtk.MessageDialog(frame, 0, gtk.MESSAGE_INFO, gtk.BUTTONS_OK, _("You are using the latest version of Nicotine."))
	dlg.run()
	dlg.destroy()

if __name__ == "__main__":
	checklatest(None)
