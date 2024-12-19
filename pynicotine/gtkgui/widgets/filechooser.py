# COPYRIGHT (C) 2020-2024 Nicotine+ Contributors
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
import sys

from gi.repository import GdkPixbuf
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Pango

from pynicotine.config import config
from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.widgets.theme import add_css_class
from pynicotine.utils import encode_path
from pynicotine.utils import open_folder_path


class FileChooser:

    active_chooser = None  # Class variable keeping the file chooser object alive

    def __init__(self, parent, callback, callback_data=None, title=_("Select a File"),
                 initial_folder=None, select_multiple=False):

        if initial_folder:
            initial_folder = os.path.normpath(os.path.expandvars(initial_folder))
            initial_folder_encoded = encode_path(initial_folder)

            try:
                if not os.path.exists(initial_folder_encoded):
                    os.makedirs(initial_folder_encoded)

            except OSError:
                pass

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

            if initial_folder:
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
                if initial_folder:
                    self.file_chooser.set_current_folder(Gio.File.new_for_path(initial_folder))
                return

            # Display network shares
            self.file_chooser.set_local_only(False)  # pylint: disable=no-member

            if initial_folder:
                self.file_chooser.set_current_folder(initial_folder)

    def _get_selected_paths(self, selected_file=None, selected_files=None):

        selected = []

        if selected_files:
            for i_file in selected_files:
                path = i_file.get_path()

                if path:
                    selected.append(os.path.normpath(path))

        elif selected_file is not None:
            path = selected_file.get_path()

            if path:
                selected.append(os.path.normpath(path))

        return selected

    def on_finish(self, _dialog, result):

        FileChooser.active_chooser = None

        try:
            selected_result = self.finish_method(result)

        except GLib.GError:
            # Nothing was selected
            self.destroy()
            return

        selected = []

        if self.select_multiple:
            selected = self._get_selected_paths(selected_files=selected_result)
        else:
            selected = self._get_selected_paths(selected_file=selected_result)

        if selected:
            self.callback(selected, self.callback_data)

        self.destroy()

    def on_response(self, _dialog, response_id):

        FileChooser.active_chooser = None
        self.file_chooser.destroy()

        if response_id != Gtk.ResponseType.ACCEPT:
            self.destroy()
            return

        if self.select_multiple:
            selected = self._get_selected_paths(selected_files=self.file_chooser.get_files())
        else:
            selected = self._get_selected_paths(selected_file=self.file_chooser.get_file())

        if selected:
            self.callback(selected, self.callback_data)

        self.destroy()

    def present(self):

        FileChooser.active_chooser = self

        if not self.using_new_api:
            self.file_chooser.show()
            return

        self.select_method(parent=self.parent.widget, callback=self.on_finish)

    def destroy(self):
        self.__dict__.clear()


class FolderChooser(FileChooser):

    def __init__(self, parent, callback, callback_data=None, title=_("Select a Folder"),
                 initial_folder=None, select_multiple=False):

        super().__init__(parent, callback, callback_data, title, initial_folder, select_multiple=select_multiple)

        self.file_chooser.set_accept_label(_("_Select"))

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

        for pattern in ("*.png", "*.jpg", "*.jpeg", "*.bmp", "*.tiff", "*.gif"):
            file_filter.add_pattern(pattern)

        if self.using_new_api:
            filters = Gio.ListStore(item_type=Gtk.FileFilter)
            filters.append(file_filter)

            self.file_chooser.set_filters(filters)
            self.file_chooser.set_default_filter(file_filter)
            return

        self.file_chooser.add_filter(file_filter)
        self.file_chooser.set_filter(file_filter)

        if GTK_API_VERSION == 3 and sys.platform not in {"win32", "darwin"}:
            # Image preview
            self.file_chooser.connect("update-preview", self.on_update_image_preview)

            self.preview = Gtk.Image()
            self.file_chooser.set_preview_widget(self.preview)  # pylint: disable=no-member

    def on_update_image_preview(self, chooser):

        file_path = chooser.get_preview_filename()

        try:
            image_data = GdkPixbuf.Pixbuf.new_from_file_at_size(file_path, width=300, height=700)
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

    def __init__(self, container, window, label=None, end_button=None, chooser_type="file",
                 is_flat=False, show_open_external_button=True, selected_function=None):

        self.window = window
        self.chooser_type = chooser_type
        self.selected_function = selected_function
        self.show_open_external_button = show_open_external_button
        self.path = ""

        widget = Gtk.Box(visible=True)

        self.chooser_button = Gtk.Button(hexpand=True, valign=Gtk.Align.CENTER, visible=True)
        self.chooser_button.connect("clicked", self.on_open_file_chooser)

        if label:
            label.set_mnemonic_widget(self.chooser_button)

        icon_names = {
            "file": "folder-documents-symbolic",
            "folder": "folder-symbolic",
            "image": "folder-pictures-symbolic"
        }

        label_container = Gtk.Box(spacing=6, visible=True)
        self.icon = Gtk.Image(icon_name=icon_names.get(chooser_type), visible=True)
        self.label = Gtk.Label(label=_("(None)"), ellipsize=Pango.EllipsizeMode.END, width_chars=3,
                               mnemonic_widget=self.chooser_button, xalign=0, visible=True)

        self.open_folder_button = Gtk.Button(
            tooltip_text=_("Open in File Manager"), valign=Gtk.Align.CENTER, visible=False)

        if GTK_API_VERSION >= 4:
            container.append(widget)                        # pylint: disable=no-member
            widget.append(self.chooser_button)              # pylint: disable=no-member
            widget.append(self.open_folder_button)          # pylint: disable=no-member
            label_container.append(self.icon)               # pylint: disable=no-member
            label_container.append(self.label)              # pylint: disable=no-member
            self.chooser_button.set_child(label_container)  # pylint: disable=no-member

            self.open_folder_button.set_icon_name("external-link-symbolic")  # pylint: disable=no-member

            if end_button:
                widget.append(end_button)                   # pylint: disable=no-member
        else:
            container.add(widget)                           # pylint: disable=no-member
            widget.add(self.chooser_button)                 # pylint: disable=no-member
            widget.add(self.open_folder_button)             # pylint: disable=no-member
            label_container.add(self.icon)                  # pylint: disable=no-member
            label_container.add(self.label)                 # pylint: disable=no-member
            self.chooser_button.add(label_container)        # pylint: disable=no-member

            self.open_folder_button.set_image(              # pylint: disable=no-member
                Gtk.Image(icon_name="external-link-symbolic"))

            if end_button:
                widget.add(end_button)                      # pylint: disable=no-member

        if is_flat:
            widget.set_spacing(6)

            for button in (self.chooser_button, self.open_folder_button):
                add_css_class(button, "flat")
        else:
            add_css_class(widget, "linked")

        self.open_folder_button.connect("clicked", self.on_open_folder)

    def destroy(self):
        self.__dict__.clear()

    def on_open_file_chooser_response(self, selected, _data):

        selected_path = next(iter(selected), None)

        if not selected_path:
            return

        self.set_path(selected_path)

        try:
            self.selected_function()

        except TypeError:
            # No function defined
            pass

    def on_open_file_chooser(self, *_args):

        if self.chooser_type == "folder":
            FolderChooser(
                parent=self.window,
                callback=self.on_open_file_chooser_response,
                initial_folder=self.path
            ).present()
            return

        folder_path = os.path.dirname(self.path) if self.path else None

        if self.chooser_type == "image":
            ImageChooser(
                parent=self.window,
                callback=self.on_open_file_chooser_response,
                initial_folder=folder_path
            ).present()
            return

        FileChooser(
            parent=self.window,
            callback=self.on_open_file_chooser_response,
            initial_folder=folder_path
        ).present()

    def on_open_folder(self, *_args):

        path = os.path.expandvars(self.path)
        folder_path = os.path.expandvars(path if self.chooser_type == "folder" else os.path.dirname(path))

        open_folder_path(folder_path, create_folder=True)

    def get_path(self, dynamic=True):

        if dynamic and self.path.startswith(config.data_folder_path):
            # Use a dynamic path that can be expanded with os.path.expandvars()
            return self.path.replace(config.data_folder_path, "${NICOTINE_DATA_HOME}", 1)

        return self.path

    def set_path(self, path):

        if not path:
            return

        self.path = path = os.path.normpath(path)

        self.chooser_button.set_tooltip_text(os.path.expandvars(path))  # Show path without env variables
        self.label.set_label(os.path.basename(path))
        self.open_folder_button.set_visible(self.show_open_external_button)

    def clear(self):

        self.path = ""

        self.chooser_button.set_tooltip_text(None)
        self.label.set_label(_("(None)"))
        self.open_folder_button.set_visible(False)
