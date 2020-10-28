# COPYRIGHT (C) 2020 Nicotine+ Team
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

from gettext import gettext as _

from gi.repository import Gtk


def choose_dir(parent=None, initialdir="~", title=None, multichoice=True):
    try:
        dialog = Gtk.FileChooserNative.new(
            title,
            parent,
            Gtk.FileChooserAction.SELECT_FOLDER,
            _("_Open"),
            _("_Cancel")
        )
    except AttributeError:
        dialog = Gtk.FileChooserDialog(
            title,
            parent,
            Gtk.FileChooserAction.SELECT_FOLDER
        )
        dialog.add_buttons(_("_Cancel"), Gtk.ResponseType.CANCEL, _("_Open"), Gtk.ResponseType.ACCEPT)

    if multichoice:
        dialog.set_select_multiple(True)

    folder = os.path.expanduser(initialdir)

    if os.path.exists(folder):
        dialog.set_current_folder(folder)
    else:
        dialog.set_current_folder(os.path.expanduser("~"))

    response = dialog.run()

    if response == Gtk.ResponseType.ACCEPT:
        res = dialog.get_filenames()
    else:
        res = None

    dialog.destroy()

    return res


def choose_file(parent=None, initialdir="~", initialfile="", multiple=False):
    try:
        dialog = Gtk.FileChooserNative.new(
            None,
            parent,
            Gtk.FileChooserAction.OPEN,
            _("_Open"),
            _("_Cancel")
        )
    except AttributeError:
        dialog = Gtk.FileChooserDialog(
            None,
            parent,
            Gtk.FileChooserAction.OPEN
        )
        dialog.add_buttons(_("_Cancel"), Gtk.ResponseType.CANCEL, _("_Open"), Gtk.ResponseType.ACCEPT)

    dialog.set_select_multiple(multiple)
    folder = os.path.expanduser(initialdir)

    if os.path.exists(folder):
        dialog.set_current_folder(folder)
    else:
        dialog.set_current_folder(os.path.expanduser("~"))

    response = dialog.run()

    if response == Gtk.ResponseType.ACCEPT:
        res = dialog.get_filenames()
    else:
        res = None

    dialog.destroy()

    return res


def save_file(parent=None, initialdir="~", initialfile="", title=None):
    try:
        dialog = Gtk.FileChooserNative.new(
            title,
            parent,
            Gtk.FileChooserAction.SAVE,
            _("_Save"),
            _("_Cancel")
        )
    except AttributeError:
        dialog = Gtk.FileChooserDialog(
            title,
            parent,
            Gtk.FileChooserAction.SAVE
        )
        dialog.add_buttons(_("_Cancel"), Gtk.ResponseType.CANCEL, _("_Save"), Gtk.ResponseType.ACCEPT)

    dialog.set_select_multiple(False)
    dialog.set_show_hidden(True)

    folder = os.path.expanduser(initialdir)

    if os.path.exists(folder):
        dialog.set_current_folder(folder)
    else:
        dialog.set_current_folder(os.path.expanduser("~"))

    dialog.set_current_name(initialfile)

    response = dialog.run()

    if response == Gtk.ResponseType.ACCEPT:
        res = dialog.get_filenames()
    else:
        res = None

    dialog.destroy()

    return res
