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

from pynicotine.gtkgui.application import GTK_API_VERSION


""" File Choosers """


# We need to keep a reference to GtkFileChooserNative, as GTK does not keep it alive
ACTIVE_CHOOSER = None


class FileChooser:

    def __init__(self, parent, callback, callback_data=None, title=_("Select a File"),
                 initial_folder='~', action=Gtk.FileChooserAction.OPEN, buttons=None, multiple=False):

        global ACTIVE_CHOOSER  # pylint:disable=global-statement
        try:
            self.file_chooser = ACTIVE_CHOOSER = Gtk.FileChooserNative(
                transient_for=parent,
                title=title,
                action=action
            )
        except AttributeError:
            self.file_chooser = ACTIVE_CHOOSER = Gtk.FileChooserDialog(
                transient_for=parent,
                title=title,
                action=action
            )

            if not buttons:
                buttons = [(_("_Cancel"), Gtk.ResponseType.CLOSE),
                           (_("_Open"), Gtk.ResponseType.ACCEPT)]

            for button_label, response_type in buttons:
                self.file_chooser.add_button(button_label, response_type)

        self.file_chooser.connect("response", self.on_selected, callback, callback_data)
        self.file_chooser.set_modal(True)
        self.file_chooser.set_select_multiple(multiple)

        initial_folder = os.path.expanduser(initial_folder)

        if not os.path.isdir(initial_folder):
            initial_folder = os.path.expanduser("~")

        if GTK_API_VERSION >= 4:
            initial_folder = Gio.File.new_for_path(initial_folder)

        else:
            # Display network shares
            self.file_chooser.set_local_only(False)  # pylint: disable=no-member

        self.file_chooser.set_current_folder(initial_folder)

    @staticmethod
    def on_selected(dialog, response_id, callback, callback_data):

        if dialog.get_select_multiple():
            selected = [i.get_parse_name() for i in dialog.get_files()]

        else:
            selected_file = dialog.get_file()

            if selected_file:
                selected = selected_file.get_parse_name()

        dialog.destroy()

        if response_id != Gtk.ResponseType.ACCEPT or not selected:
            return

        callback(selected, callback_data)

    def show(self):
        self.file_chooser.show()


class FolderChooser(FileChooser):

    def __init__(self, parent, callback, callback_data=None, title=_("Select a Folder"),
                 initial_folder='~', multiple=False):

        super().__init__(parent, callback, callback_data, title, initial_folder,
                         action=Gtk.FileChooserAction.SELECT_FOLDER, multiple=multiple)


class ImageChooser(FileChooser):

    def __init__(self, parent, callback, callback_data=None, title=_("Select an Image"),
                 initial_folder='~', multiple=False):

        super().__init__(parent, callback, callback_data, title, initial_folder)

        # Only show image files
        file_filter = Gtk.FileFilter()
        file_filter.add_pixbuf_formats()
        self.file_chooser.set_filter(file_filter)

        if GTK_API_VERSION == 3:
            # Image preview
            self.file_chooser.connect("update-preview", self.on_update_image_preview)

            self.preview = Gtk.Image()
            self.file_chooser.set_preview_widget(self.preview)  # pylint: disable=no-member

    def on_update_image_preview(self, chooser):

        path = chooser.get_preview_filename()

        try:
            image_data = GdkPixbuf.Pixbuf.new_from_file(path)

            maxwidth, maxheight = 300.0, 700.0
            width, height = image_data.get_width(), image_data.get_height()
            scale = min(maxwidth / width, maxheight / height)

            if scale < 1:
                width, height = int(width * scale), int(height * scale)
                image_data = image_data.scale_simple(width, height, GdkPixbuf.InterpType.BILINEAR)

            self.preview.set_from_pixbuf(image_data)
            chooser.set_preview_widget_active(True)

        except Exception:
            chooser.set_preview_widget_active(False)


class FileChooserSave(FileChooser):

    def __init__(self, parent, callback, callback_data=None, title=_("Save as…"),
                 initial_folder='~', initial_file='', multiple=False):

        super().__init__(parent, callback, callback_data, title, initial_folder,
                         action=Gtk.FileChooserAction.SAVE, multiple=multiple,
                         buttons=[
                             (_("_Cancel"), Gtk.ResponseType.CANCEL),
                             (_("_Save"), Gtk.ResponseType.ACCEPT)])

        if GTK_API_VERSION == 3:
            # Display hidden files
            self.file_chooser.set_show_hidden(True)                # pylint: disable=no-member
            self.file_chooser.set_do_overwrite_confirmation(True)  # pylint: disable=no-member

        self.file_chooser.set_current_name(initial_file)


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

        self.icon = Gtk.Image(icon_name=icon_name, visible=True)
        self.label = Gtk.Label(label=_("(None)"), ellipsize=Pango.EllipsizeMode.END, width_chars=6,
                               xalign=0, visible=True)

        box = Gtk.Box(spacing=6, visible=True)

        if GTK_API_VERSION >= 4:
            box.append(self.icon)   # pylint: disable=no-member
            box.append(self.label)  # pylint: disable=no-member
        else:
            box.add(self.icon)   # pylint: disable=no-member
            box.add(self.label)  # pylint: disable=no-member

        self.button.set_property("child", box)
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
            FolderChooser(
                parent=self.parent,
                callback=self.open_file_chooser_response,
                initial_folder=self.path
            ).show()
            return

        if self.path:
            folder_path = os.path.dirname(self.path)
        else:
            folder_path = ""

        if self.chooser_type == "image":
            ImageChooser(
                parent=self.parent,
                callback=self.open_file_chooser_response,
                initial_folder=folder_path
            ).show()
            return

        FileChooser(
            parent=self.parent,
            callback=self.open_file_chooser_response,
            initial_folder=folder_path
        ).show()

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
