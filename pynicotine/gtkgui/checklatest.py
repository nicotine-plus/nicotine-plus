# COPYRIGHT (C) 2020 Nicotine+ Team
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2006-2009 Daelstorm <daelstorm@gmail.com>
# COPYRIGHT (C) 2003-2004 Hyriand <hyriand@thegraveyard.org>
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

import json
import urllib.error
import urllib.parse
import urllib.request

from gettext import gettext as _

from gi.repository import Gtk as gtk

from pynicotine.utils import version


def makeversion(version):

    if version.find("dev") >= 0:
        # Example: 2.0.1.dev1

        ix = version.find("dev") - 1
        version = version[:ix]
    elif version.find("rc") >= 0:
        # Example: 2.0.1.rc1

        ix = version.find("rc") - 1
        version = version[:ix]

    s = version.split(".")

    if len(s) >= 4:
        major, minor, micro, milli = [int(i) for i in s[:4]]
    else:
        major, minor, micro = [int(i) for i in s[:3]]
        milli = 0

    return (major << 24) + (minor << 16) + (micro << 8) + milli


def checklatest(frame):

    latesturl = 'https://api.github.com/repos/Nicotine-Plus/nicotine-plus/releases/latest'

    try:
        response = urllib.request.urlopen(latesturl)
        data = json.loads(response.read())
        response.close()
        hlatest = data['name']
        latest = makeversion(hlatest)
        date = data['created_at']
    except Exception as m:
        dlg = gtk.MessageDialog(
            transient_for=frame,
            flags=0,
            type=gtk.MessageType.ERROR,
            buttons=gtk.ButtonsType.OK,
            text=_("Could not retrieve version information!\nError: %s") % m
        )
    else:
        myversion = makeversion(version)

        if latest > myversion:
            dlg = gtk.MessageDialog(
                transient_for=frame,
                flags=0,
                type=gtk.MessageType.INFO,
                buttons=gtk.ButtonsType.OK,
                text=_("A newer version %s is available, released on %s.") % (hlatest, date)
            )
        elif myversion > latest:
            dlg = gtk.MessageDialog(
                transient_for=frame,
                flags=0,
                type=gtk.MessageType.INFO,
                buttons=gtk.ButtonsType.OK,
                text=_("You appear to be using a development version of Nicotine+.")
            )
        else:
            dlg = gtk.MessageDialog(
                transient_for=frame,
                flags=0,
                type=gtk.MessageType.INFO,
                buttons=gtk.ButtonsType.OK,
                text=_("You are using the latest version of Nicotine+.")
            )

    dlg.run()
    dlg.destroy()
