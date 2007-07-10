# Copyright (C) 2007 daelstorm. All rights reserved.
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
#
# Original copyright below
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
	elif version.find("svn") >= 0:
		ix = version.find("svn")
		#build = int(version[ix+3:])
		version = version[:ix]
	elif version.find("rc") >= 0:
		ix = version.find("rc")
		build = int(version[ix+2:]) + 0x80
		version = version[:ix]
	s = version.split(".")
	if len(s) >= 4:
		major, minor, micro, milli = [int(i) for i in s[:4]]
	else:
		major, minor, micro = [int(i) for i in s[:3]]
		milli = 0
	return (major << 24) + (minor << 16) + (micro << 8) + milli + build 

def checklatest(frame):
	try:
		url = urllib.urlopen(latesturl)
		data = url.read().split("\n")[0]
		url.close()
		latest = makeversion(data)
	except Exception, m:
		dlg = gtk.MessageDialog(frame, 0, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, _("Could not retrieve version information!\nError: %s") % m)
		dlg.set_title(_("Check Latest Version"))
		dlg.run()
		dlg.destroy()
		return
	myversion = makeversion(version)
	if latest > myversion:
		dlg = gtk.MessageDialog(frame, 0, gtk.MESSAGE_WARNING, gtk.BUTTONS_OK, _("A newer version ('%s') is available. Check\nthe Nicotine+ homepage, ( http://nicotine-plus.sourceforge.net ) for the latest version.") % data)
		
	elif myversion > latest:
		dlg = gtk.MessageDialog(frame, 0, gtk.MESSAGE_WARNING, gtk.BUTTONS_OK, _("You appear to be using a development version of Nicotine+.\nCheck out the latest version from the Subversion repository at http://nicotine-plus.org"))
	else:
		dlg = gtk.MessageDialog(frame, 0, gtk.MESSAGE_INFO, gtk.BUTTONS_OK, _("You are using the latest version of Nicotine+."))
	dlg.set_title(_("Check Latest Version"))
	dlg.run()
	dlg.destroy()

if __name__ == "__main__":
	checklatest(None)
