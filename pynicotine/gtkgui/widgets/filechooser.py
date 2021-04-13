# COPYRIGHT (C) 2020-2021 Nicotine+ Team
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

from gi.repository import GdkPixbuf
from gi.repository import Gtk


""" File Choosers """


def choose_dir(parent=None, initialdir="~", title=_("Select a Folder"), multichoice=True):
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

    if os.path.isdir(folder):
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


def choose_file(parent=None, initialdir="~", title=_("Select a File"), multiple=False):
    try:
        dialog = Gtk.FileChooserNative.new(
            title,
            parent,
            Gtk.FileChooserAction.OPEN,
            _("_Open"),
            _("_Cancel")
        )
    except AttributeError:
        dialog = Gtk.FileChooserDialog(
            title,
            parent,
            Gtk.FileChooserAction.OPEN
        )
        dialog.add_buttons(_("_Cancel"), Gtk.ResponseType.CANCEL, _("_Open"), Gtk.ResponseType.ACCEPT)

    dialog.set_select_multiple(multiple)
    folder = os.path.expanduser(initialdir)

    if os.path.isdir(folder):
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


def choose_image(parent=None, initialdir="~", title=_("Select an Image"), multiple=False):
    try:
        dialog = Gtk.FileChooserNative.new(
            title,
            parent,
            Gtk.FileChooserAction.OPEN,
            _("_Open"),
            _("_Cancel")
        )
    except AttributeError:
        dialog = Gtk.FileChooserDialog(
            title,
            parent,
            Gtk.FileChooserAction.OPEN
        )
        dialog.add_buttons(_("_Cancel"), Gtk.ResponseType.CANCEL, _("_Open"), Gtk.ResponseType.ACCEPT)

    preview = Gtk.Image()
    dialog.set_preview_widget(preview)

    def on_update_image_preview(chooser):
        path = chooser.get_preview_filename()

        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(path)

            maxwidth, maxheight = 300.0, 700.0
            width, height = pixbuf.get_width(), pixbuf.get_height()
            scale = min(maxwidth / width, maxheight / height)

            if scale < 1:
                width, height = int(width * scale), int(height * scale)
                pixbuf = pixbuf.scale_simple(width, height, GdkPixbuf.InterpType.BILINEAR)

            preview.set_from_pixbuf(pixbuf)
            chooser.set_preview_widget_active(True)

        except Exception:
            chooser.set_preview_widget_active(False)

    dialog.connect("update-preview", on_update_image_preview)

    dialog.set_select_multiple(multiple)
    folder = os.path.expanduser(initialdir)

    if os.path.isdir(folder):
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

    if os.path.isdir(folder):
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


class FileChooserButton:
    """ This class expands the functionality of a GtkButton to open a file
    chooser and display the name of a selected folder or file """

    def __init__(self, button, parent, chooser_type="file", selected_function=None):

        self.parent = parent
        self.button = button
        self.chooser_type = chooser_type
        self.selected_function = selected_function
        self.path = ""

        box = Gtk.Box()
        box.set_spacing(6)
        self.icon = Gtk.Image.new()

        if chooser_type == "folder":
            self.icon.set_from_icon_name("folder-symbolic", Gtk.IconSize.BUTTON)

        elif chooser_type == "image":
            self.icon.set_from_icon_name("image-x-generic-symbolic", Gtk.IconSize.BUTTON)

        else:
            self.icon.set_from_icon_name("text-x-generic-symbolic", Gtk.IconSize.BUTTON)

        self.label = Gtk.Label.new(_("(None)"))

        box.add(self.icon)
        box.add(self.label)

        self.button.add(box)
        self.button.show_all()

        self.button.connect("clicked", self.open_file_chooser)

    def open_file_chooser(self, *args):

        if self.chooser_type == "folder":
            selected = choose_dir(self.parent, self.path, multichoice=False)

        else:
            if self.path:
                folder_path = os.path.dirname(self.path)
            else:
                folder_path = ""

            if self.chooser_type == "image":
                selected = choose_image(self.parent, folder_path)
            else:
                selected = choose_file(self.parent, folder_path)

        if selected:
            self.set_path(selected[0])

            try:
                self.selected_function()

            except TypeError:
                # No fucntion defined
                return

    def get_path(self):
        return self.path

    def set_path(self, path):

        if not path:
            return

        self.path = path
        self.label.set_label(os.path.basename(path))

    def clear(self):
        self.path = ""
        self.label.set_label(_("(None)"))
