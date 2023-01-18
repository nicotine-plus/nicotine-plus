# COPYRIGHT (C) 2020-2022 Nicotine+ Contributors
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
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Pango

from pynicotine.gtkgui.application import GTK_API_VERSION


""" File Choosers """


class FileChooser:

    active_chooser = None  # Class variable keeping the file chooser object alive

    def __init__(self, parent, callback, callback_data=None, title=_("Select a File"),
                 initial_folder=None, select_multiple=False):

        if not initial_folder:
            initial_folder = os.path.expanduser("~")

        self.parent = parent
        self.callback = callback
        self.callback_data = callback_data
        self.select_multiple = select_multiple

        try:
            # GTK >= 4.10
            self.using_new_api = True
            self.file_chooser = Gtk.FileDialog(title=title, modal=True)

            if select_multiple:
                self.select_method = self.file_chooser.open_multiple
                self.finish_method = self.file_chooser.open_multiple_finish
            else:
                self.select_method = self.file_chooser.open
                self.finish_method = self.file_chooser.open_finish

            self.file_chooser.set_initial_folder(Gio.File.new_for_path(initial_folder))

        except AttributeError:
            # GTK < 4.10
            self.using_new_api = False
            self.file_chooser = Gtk.FileChooserNative(
                transient_for=parent.widget,
                title=title,
                select_multiple=select_multiple,
                modal=True,
                action=Gtk.FileChooserAction.OPEN
            )
            self.file_chooser.connect("response", self.on_response)

            if GTK_API_VERSION >= 4:
                self.file_chooser.set_current_folder(Gio.File.new_for_path(initial_folder))
                return

            # Display network shares
            self.file_chooser.set_local_only(False)  # pylint: disable=no-member
            self.file_chooser.set_current_folder(initial_folder)

    def on_finish(self, _dialog, result):

        FileChooser.active_chooser = None

        try:
            selected_result = self.finish_method(result)

        except GLib.GError:
            # Nothing was selected
            return

        if self.select_multiple:
            selected = [i.get_path() for i in selected_result]
        else:
            selected = selected_result.get_path()

        if selected:
            self.callback(selected, self.callback_data)

    def on_response(self, _dialog, response_id):

        FileChooser.active_chooser = None
        self.file_chooser.destroy()

        if response_id != Gtk.ResponseType.ACCEPT:
            return

        if self.select_multiple:
            selected = [i.get_path() for i in self.file_chooser.get_files()]
        else:
            selected_file = self.file_chooser.get_file()
            selected = selected_file.get_path() if selected_file else None

        if selected:
            self.callback(selected, self.callback_data)

    def show(self):

        FileChooser.active_chooser = self

        if not self.using_new_api:
            self.file_chooser.show()
            return

        self.select_method(parent=self.parent.widget, callback=self.on_finish)


class FolderChooser(FileChooser):

    def __init__(self, parent, callback, callback_data=None, title=_("Select a Folder"),
                 initial_folder=None, select_multiple=False):

        super().__init__(parent, callback, callback_data, title, initial_folder, select_multiple=select_multiple)

        if not self.using_new_api:
            self.file_chooser.set_action(Gtk.FileChooserAction.SELECT_FOLDER)
            return

        if select_multiple:
            self.select_method = self.file_chooser.select_multiple_folders
            self.finish_method = self.file_chooser.select_multiple_folders_finish
            return

        self.select_method = self.file_chooser.select_folder
        self.finish_method = self.file_chooser.select_folder_finish


class ImageChooser(FileChooser):

    def __init__(self, parent, callback, callback_data=None, title=_("Select an Image"),
                 initial_folder=None, select_multiple=False):

        super().__init__(parent, callback, callback_data, title, initial_folder, select_multiple=select_multiple)

        # Only show image files
        file_filter = Gtk.FileFilter()
        file_filter.set_name(_("All images"))
        file_filter.add_pixbuf_formats()

        if self.using_new_api:
            self.file_chooser.set_default_filter(file_filter)
            return

        self.file_chooser.set_filter(file_filter)

        if GTK_API_VERSION == 3:
            # Image preview
            self.file_chooser.connect("update-preview", self.on_update_image_preview)

            self.preview = Gtk.Image()
            self.file_chooser.set_preview_widget(self.preview)  # pylint: disable=no-member

    def on_update_image_preview(self, chooser):

        path = chooser.get_preview_filename()

        try:
            image_data = GdkPixbuf.Pixbuf.new_from_file_at_size(path, width=300, height=700)
            self.preview.set_from_pixbuf(image_data)
            chooser.set_preview_widget_active(True)

        except Exception:
            chooser.set_preview_widget_active(False)


class FileChooserSave(FileChooser):

    def __init__(self, parent, callback, callback_data=None, title=_("Save as…"),
                 initial_folder=None, initial_file=""):

        super().__init__(parent, callback, callback_data, title, initial_folder)

        if GTK_API_VERSION == 3:
            # Display hidden files
            self.file_chooser.set_show_hidden(True)                # pylint: disable=no-member
            self.file_chooser.set_do_overwrite_confirmation(True)  # pylint: disable=no-member

        if not self.using_new_api:
            self.file_chooser.set_action(Gtk.FileChooserAction.SAVE)
            self.file_chooser.set_current_name(initial_file)
            return

        self.select_method = self.file_chooser.save
        self.finish_method = self.file_chooser.save_finish

        self.file_chooser.set_initial_name(initial_file)


class FileChooserButton:
    """ This class expands the functionality of a GtkButton to open a file
    chooser and display the name of a selected folder or file """

    def __init__(self, button, parent, chooser_type="file", selected_function=None):

        self.parent = parent
        self.button = button
        self.chooser_type = chooser_type
        self.selected_function = selected_function
        self.path = None

        if chooser_type == "folder":
            icon_name = "folder-symbolic"

        elif chooser_type == "image":
            icon_name = "image-x-generic-symbolic"

        else:
            icon_name = "text-x-generic-symbolic"

        self.icon = Gtk.Image(icon_name=icon_name, visible=True)
        self.label = Gtk.Label(label=_("(None)"), ellipsize=Pango.EllipsizeMode.END, width_chars=6,
                               mnemonic_widget=button, xalign=0, visible=True)

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

        folder_path = os.path.dirname(self.path) if self.path else None

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
        self.button.set_tooltip_text(path)
        self.label.set_label(os.path.basename(path))

    def clear(self):

        self.path = None
        self.button.set_tooltip_text(None)
        self.label.set_label(_("(None)"))
