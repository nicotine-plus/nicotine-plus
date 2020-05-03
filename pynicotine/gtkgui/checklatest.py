# -*- coding: utf-8 -*-
#
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

import gi
from gi.repository import Gtk as gtk

from pynicotine.utils import version

gi.require_version('Gtk', '3.0')


def makeversion(version):

    if version.find("git") >= 0:
        ix = version.find("git")
        version = version[:ix]
    elif version.find("rc") >= 0:
        ix = version.find("rc")
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
        latest = makeversion(data['name'])
    except Exception as m:
        dlg = gtk.MessageDialog(
            frame,
            0,
            gtk.MESSAGE_ERROR,
            gtk.BUTTONS_OK,
            _("Could not retrieve version information!\nError: %s") % m
        )
        dlg.set_title(_("Check Latest Version"))
        dlg.run()
        dlg.destroy()
        return

    myversion = makeversion(version)

    if latest > myversion:
        dlg = gtk.MessageDialog(
            frame,
            0,
            gtk.MESSAGE_WARNING,
            gtk.BUTTONS_OK,
            _("A newer version ('%s') is available. Check Nicotine+ releases page\n(https://github.com/Nicotine-Plus/nicotine-plus/releases) for the latest version.") % data
        )
    elif myversion > latest:
        dlg = gtk.MessageDialog(
            frame,
            0,
            gtk.MESSAGE_WARNING,
            gtk.BUTTONS_OK,
            _("You appear to be using a development version of Nicotine+.\nCheck out the latest version from the Git repository at https://github.com/Nicotine-Plus/nicotine-plus/")
        )
    else:
        dlg = gtk.MessageDialog(
            frame,
            0,
            gtk.MESSAGE_INFO,
            gtk.BUTTONS_OK,
            _("You are using the latest version of Nicotine+.")
        )

    dlg.set_title(_("Check Latest Version"))
    dlg.run()
    dlg.destroy()
