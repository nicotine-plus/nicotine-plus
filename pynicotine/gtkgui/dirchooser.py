# -*- coding: utf-8 -*-
#
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2008-2010 Quinox <quinox@users.sf.net>
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

import os

import gi
from gi.repository import Gtk as gtk

gi.require_version('Gtk', '3.0')


def ChooseDir(parent=None, initialdir="~", create=False, name=None, title=None):

    dialog = gtk.FileChooserDialog(
        title=title,
        parent=parent,
        action=gtk.FileChooserAction.SELECT_FOLDER,
        buttons=(gtk.STOCK_CANCEL, gtk.ResponseType.REJECT, gtk.STOCK_OK, gtk.ResponseType.ACCEPT)
    )

    if create:
        dialog.set_action(gtk.FileChooserAction.CREATE_FOLDER)
    else:
        dialog.set_action(gtk.FileChooserAction.SELECT_FOLDER)
        dialog.set_select_multiple(True)

    dir = os.path.expanduser(initialdir)

    if os.path.exists(dir):
        dialog.set_current_folder(dir)
    else:
        dialog.set_current_folder(os.path.expanduser("~"))

    if name:
        dialog.set_current_name(name)

    response = dialog.run()

    if response == gtk.ResponseType.ACCEPT:
        res = dialog.get_filenames()
    else:
        res = None

    dialog.destroy()

    return res


def ChooseFile(parent=None, initialdir="~", initialfile="", multiple=False):

    dialog = gtk.FileChooserDialog(
        parent=parent,
        action=gtk.FileChooserAction.OPEN,
        buttons=(gtk.STOCK_CANCEL, gtk.ResponseType.REJECT, gtk.STOCK_OK, gtk.ResponseType.ACCEPT)
    )

    dialog.set_action(gtk.FileChooserAction.OPEN)
    dialog.set_select_multiple(multiple)
    dir = os.path.expanduser(initialdir)

    if os.path.exists(dir):
        dialog.set_current_folder(dir)
    else:
        dialog.set_current_folder(os.path.expanduser("~"))

    response = dialog.run()

    if response == gtk.ResponseType.ACCEPT:
        res = dialog.get_filenames()
    else:
        res = None

    dialog.destroy()

    return res


def SaveFile(parent=None, initialdir="~", initialfile="", title=None):

    dialog = gtk.FileChooserDialog(
        parent=parent,
        action=gtk.FileChooserAction.SAVE,
        buttons=(gtk.STOCK_CANCEL, gtk.ResponseType.REJECT, gtk.STOCK_OK, gtk.ResponseType.ACCEPT)
    )

    dialog.set_action(gtk.FileChooserAction.SAVE)
    dialog.set_select_multiple(False)
    dialog.set_show_hidden(True)

    if title:
        dialog.set_title(title)

    dir = os.path.expanduser(initialdir)

    if os.path.exists(dir):
        dialog.set_current_folder(dir)
    else:
        dialog.set_current_folder(os.path.expanduser("~"))

    response = dialog.run()

    if response == gtk.ResponseType.ACCEPT:
        res = dialog.get_filenames()
    else:
        res = None

    dialog.destroy()

    return res
