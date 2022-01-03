# COPYRIGHT (C) 2020-2022 Nicotine+ Team
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
from gi.repository import Gio
from gi.repository import Gtk
from gi.repository import Pango


""" File Choosers """


# We need to keep a reference to GtkFileChooserNative, as GTK does not keep it alive
ACTIVE_CHOOSER = None


def _on_selected(dialog, response_id, callback, callback_data):

    if dialog.get_select_multiple():
        if Gtk.get_major_version() == 4:
            selected = [i.get_path() for i in dialog.get_files()]
        else:
            selected = dialog.get_filenames()

    else:
        if Gtk.get_major_version() == 4:
            selected_file = dialog.get_file()

            if selected_file:
                selected = selected_file.get_path()
        else:
            selected = dialog.get_filename()

    dialog.destroy()

    if response_id != Gtk.ResponseType.ACCEPT or not selected:
        return

    callback(selected, callback_data)


def _set_filechooser_folder(dialog, folder_path):

    folder_path = os.path.expanduser(folder_path)

    if not os.path.isdir(folder_path):
        folder_path = os.path.expanduser("~")

    if Gtk.get_major_version() == 4:
        folder_path = Gio.File.new_for_path(folder_path)

    dialog.set_current_folder(folder_path)


def choose_dir(parent, callback, callback_data=None, initialdir="~", title=_("Select a Folder"), multichoice=True):

    global ACTIVE_CHOOSER  # pylint:disable=global-statement
    try:
        self = ACTIVE_CHOOSER = Gtk.FileChooserNative(
            transient_for=parent,
            title=title,
            action=Gtk.FileChooserAction.SELECT_FOLDER
        )
    except AttributeError:
        self = ACTIVE_CHOOSER = Gtk.FileChooserDialog(
            transient_for=parent,
            title=title,
            action=Gtk.FileChooserAction.SELECT_FOLDER
        )
        self.add_buttons(_("_Cancel"), Gtk.ResponseType.CANCEL, _("_Open"), Gtk.ResponseType.ACCEPT)

    self.connect("response", _on_selected, callback, callback_data)
    self.set_modal(True)

    if Gtk.get_major_version() == 3:
        # Display network shares
        self.set_local_only(False)

    if multichoice:
        self.set_select_multiple(True)

    _set_filechooser_folder(self, initialdir)
    self.show()


def choose_file(parent, callback, callback_data=None, initialdir="~", title=_("Select a File"), multiple=False):

    global ACTIVE_CHOOSER  # pylint:disable=global-statement
    try:
        self = ACTIVE_CHOOSER = Gtk.FileChooserNative(
            transient_for=parent,
            title=title,
            action=Gtk.FileChooserAction.OPEN
        )
    except AttributeError:
        self = ACTIVE_CHOOSER = Gtk.FileChooserDialog(
            transient_for=parent,
            title=title,
            action=Gtk.FileChooserAction.OPEN
        )
        self.add_buttons(_("_Cancel"), Gtk.ResponseType.CANCEL, _("_Open"), Gtk.ResponseType.ACCEPT)

    self.connect("response", _on_selected, callback, callback_data)
    self.set_modal(True)
    self.set_select_multiple(multiple)

    if Gtk.get_major_version() == 3:
        # Display network shares
        self.set_local_only(False)

    _set_filechooser_folder(self, initialdir)
    self.show()


def choose_image(parent, callback, callback_data=None, initialdir="~", title=_("Select an Image"), multiple=False):

    def on_update_image_preview(chooser):
        path = chooser.get_preview_filename()

        try:
            image_data = GdkPixbuf.Pixbuf.new_from_file(path)

            maxwidth, maxheight = 300.0, 700.0
            width, height = image_data.get_width(), image_data.get_height()
            scale = min(maxwidth / width, maxheight / height)

            if scale < 1:
                width, height = int(width * scale), int(height * scale)
                image_data = image_data.scale_simple(width, height, GdkPixbuf.InterpType.BILINEAR)

            preview.set_from_pixbuf(image_data)
            chooser.set_preview_widget_active(True)

        except Exception:
            chooser.set_preview_widget_active(False)

    global ACTIVE_CHOOSER  # pylint:disable=global-statement
    try:
        self = ACTIVE_CHOOSER = Gtk.FileChooserNative(
            transient_for=parent,
            title=title,
            action=Gtk.FileChooserAction.OPEN
        )
    except AttributeError:
        self = ACTIVE_CHOOSER = Gtk.FileChooserDialog(
            transient_for=parent,
            title=title,
            action=Gtk.FileChooserAction.OPEN
        )
        self.add_buttons(_("_Cancel"), Gtk.ResponseType.CANCEL, _("_Open"), Gtk.ResponseType.ACCEPT)

    self.connect("response", _on_selected, callback, callback_data)
    self.set_modal(True)

    if Gtk.get_major_version() == 3:
        # Display network shares
        self.set_local_only(False)

        # Image preview
        self.connect("update-preview", on_update_image_preview)

        preview = Gtk.Image()
        self.set_preview_widget(preview)

    self.set_select_multiple(multiple)

    _set_filechooser_folder(self, initialdir)
    self.show()


def save_file(parent, callback, callback_data=None, initialdir="~", initialfile="", title=None):

    global ACTIVE_CHOOSER  # pylint:disable=global-statement
    try:
        self = ACTIVE_CHOOSER = Gtk.FileChooserNative(
            transient_for=parent,
            title=title,
            action=Gtk.FileChooserAction.SAVE
        )
    except AttributeError:
        self = ACTIVE_CHOOSER = Gtk.FileChooserDialog(
            transient_for=parent,
            title=title,
            action=Gtk.FileChooserAction.SAVE
        )
        self.add_buttons(_("_Cancel"), Gtk.ResponseType.CANCEL, _("_Save"), Gtk.ResponseType.ACCEPT)

    self.connect("response", _on_selected, callback, callback_data)
    self.set_modal(True)
    self.set_select_multiple(False)

    if Gtk.get_major_version() == 3:
        # Display network shares
        self.set_local_only(False)

        # Display hidden files
        self.set_show_hidden(True)

    _set_filechooser_folder(self, initialdir)
    self.set_current_name(initialfile)
    self.show()


class FileChooserButton:
    """ This class expands the functionality of a GtkButton to open a file
    chooser and display the name of a selected folder or file """

    def __init__(self, button, parent, chooser_type="file", selected_function=None):

        self.parent = parent
        self.button = button
        self.chooser_type = chooser_type
        self.selected_function = selected_function
        self.path = ""

        if chooser_type == "folder":
            icon_name = "folder-symbolic"

        elif chooser_type == "image":
            icon_name = "image-x-generic-symbolic"

        else:
            icon_name = "text-x-generic-symbolic"

        self.icon = Gtk.Image(icon_name=icon_name)
        self.label = Gtk.Label(label=_("(None)"), ellipsize=Pango.EllipsizeMode.END, width_chars=6, xalign=0)

        box = Gtk.Box(spacing=6)
        box.add(self.icon)
        box.add(self.label)

        if Gtk.get_major_version() == 4:
            self.button.set_child(box)
        else:
            self.button.add(box)
            self.button.show_all()

        self.button.connect("clicked", self.open_file_chooser)

    def open_file_chooser_response(self, selected, _data):

        self.set_path(selected)

        try:
            self.selected_function()

        except TypeError:
            # No function defined
            return

    def open_file_chooser(self, *_args):

        if self.chooser_type == "folder":
            choose_dir(
                parent=self.parent,
                callback=self.open_file_chooser_response,
                initialdir=self.path,
                multichoice=False
            )
            return

        if self.path:
            folder_path = os.path.dirname(self.path)
        else:
            folder_path = ""

        if self.chooser_type == "image":
            choose_image(
                parent=self.parent,
                callback=self.open_file_chooser_response,
                initialdir=folder_path
            )
            return

        choose_file(
            parent=self.parent,
            callback=self.open_file_chooser_response,
            initialdir=folder_path
        )

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
