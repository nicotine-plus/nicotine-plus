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

from gi.repository import Gdk
from gi.repository import Gtk

from pynicotine.config import config
from pynicotine.gtkgui.application import GTK_API_VERSION

""" Dialogs """


def generic_dialog(parent=None, content_box=None, buttons=None, quit_callback=None,
                   title="Dialog", width=400, height=400, modal=True):

    dialog = Gtk.Dialog(
        use_header_bar=config.sections["ui"]["header_bar"],
        title=title,
        default_width=width,
        default_height=height
    )
    dialog.get_style_context().add_class("generic-dialog")

    if content_box:
        if GTK_API_VERSION >= 4:
            dialog.get_content_area().append(content_box)
        else:
            dialog.get_content_area().add(content_box)

    if buttons:
        for button, response_type in buttons:
            dialog.add_action_widget(button, response_type)

    set_dialog_properties(dialog, parent, quit_callback, modal)
    return dialog


def set_dialog_properties(dialog, parent, quit_callback=None, modal=True):

    if GTK_API_VERSION >= 4:
        if quit_callback:
            dialog.connect("close-request", quit_callback)
    else:
        dialog.set_property("window-position", Gtk.WindowPosition.CENTER_ON_PARENT)
        dialog.set_type_hint(Gdk.WindowTypeHint.DIALOG)

        if quit_callback:
            dialog.connect("delete-event", quit_callback)

        if isinstance(dialog, Gtk.Dialog):
            content_area = dialog.get_content_area()
            content_area.set_border_width(0)

    dialog.set_modal(modal)
    dialog.set_transient_for(parent)


def dialog_show(dialog):

    parent = dialog.get_transient_for()

    # Shrink the dialog if it's larger than the main window
    if GTK_API_VERSION >= 4:
        main_window_width = parent.get_width()
        main_window_height = parent.get_height()
        dialog_width, dialog_height = dialog.get_default_size()
    else:
        main_window_width, main_window_height = parent.get_size()
        dialog_width, dialog_height = dialog.get_size()

    if dialog_width > main_window_width:
        dialog_width = main_window_width - 30

    if dialog_height > main_window_height:
        dialog_height = main_window_height - 30

    if dialog_width > 0 and dialog_height > 0:
        if GTK_API_VERSION >= 4:
            dialog.set_default_size(dialog_width, dialog_height)
        else:
            dialog.resize(dialog_width, dialog_height)

    # Show the dialog
    dialog.present()

    if GTK_API_VERSION == 3:
        dialog.get_window().set_functions(
            Gdk.WMFunction.RESIZE | Gdk.WMFunction.MOVE | Gdk.WMFunction.CLOSE
        )


def dialog_hide(dialog):

    # Hide the dialog
    dialog.hide()

    # "Soft-delete" the dialog. This is necessary to prevent the dialog from
    # appearing in window peek on Windows
    dialog.unrealize()


""" Message Dialogs """


class MessageDialog:

    def __init__(self, parent, title, message, callback=None, callback_data=None,
                 message_type=Gtk.MessageType.OTHER, buttons=None, width=-1):

        self.dialog = Gtk.MessageDialog(
            transient_for=parent, destroy_with_parent=True, modal=True,
            message_type=message_type, default_width=width,
            text=title, secondary_text=message
        )
        self.container = self.dialog.get_message_area()

        if not callback:
            def callback(dialog, *_args):
                dialog.destroy()

        self.callback = callback
        self.callback_data = callback_data

        self.dialog.connect("response", self.on_response)

        if not buttons:
            buttons = [(_("Close"), Gtk.ResponseType.CLOSE)]

        for button_label, response_type in buttons:
            self.dialog.add_button(button_label, response_type)

        if GTK_API_VERSION >= 4:
            label = self.container.get_last_child()
        else:
            label = self.container.get_children()[-1]

        label.set_selectable(True)

    def on_response(self, _dialog, response_id):
        self.callback(self, response_id, self.callback_data)

    def show(self):
        self.dialog.present()

    def destroy(self):
        self.dialog.destroy()


class EntryDialog(MessageDialog):

    def __init__(self, parent, title, callback, message=None, callback_data=None, default="", use_second_entry=False,
                 second_default="", option_label="", option_value=False, visibility=True,
                 droplist=None, second_droplist=None):

        super().__init__(parent=parent, title=title, message=message, message_type=Gtk.MessageType.OTHER,
                         callback=callback, callback_data=callback_data, width=500,
                         buttons=[
                             (_("Cancel"), Gtk.ResponseType.CANCEL),
                             (_("OK"), Gtk.ResponseType.OK)])

        if droplist:
            self.entry = self._add_combobox(droplist, visibility)
        else:
            self.entry = self._add_entry(visibility)

        self.entry.connect("activate", lambda x: self.dialog.response(Gtk.ResponseType.OK))
        self.entry.set_text(default)

        if use_second_entry:
            if second_droplist:
                self.second_entry = self._add_combobox(second_droplist, visibility)
            else:
                self.second_entry = self._add_entry(visibility)

            self.second_entry.connect("activate", lambda x: self.dialog.response(Gtk.ResponseType.OK))
            self.second_entry.set_text(second_default)

        self.option = Gtk.CheckButton(label=option_label, active=option_value, visible=bool(option_label))

        if option_label:
            if GTK_API_VERSION >= 4:
                self.container.append(self.option)
            else:
                self.container.add(self.option)

    def _add_combobox(self, items, visibility=True):

        dropdown = Gtk.ComboBoxText(has_entry=True, visible=True)
        entry = dropdown.get_child()
        entry.set_visibility(visibility)

        for item in items:
            dropdown.append_text(item)

        if GTK_API_VERSION >= 4:
            self.container.append(dropdown)
        else:
            self.container.add(dropdown)

        return entry

    def _add_entry(self, visibility=True):

        if GTK_API_VERSION >= 4 and not visibility:
            entry = Gtk.PasswordEntry(show_peek_icon=True, visible=True)
        else:
            entry = Gtk.Entry(visibility=visibility, visible=True)

        if GTK_API_VERSION >= 4:
            self.container.append(entry)
        else:
            self.container.add(entry)

        return entry

    def get_entry_value(self):
        return self.entry.get_text()

    def get_second_entry_value(self):
        return self.second_entry.get_text()

    def get_option_value(self):
        return self.option.get_active()


class OptionDialog(MessageDialog):

    def __init__(self, parent, title, message, callback, callback_data=None, option_label="", option_value=False,
                 first_button=_("_No"), second_button=_("_Yes"), third_button=""):

        buttons = []

        if first_button:
            buttons.append((first_button, 1))

        if second_button:
            buttons.append((second_button, 2))

        if third_button:
            buttons.append((third_button, 3))

        super().__init__(parent=parent, title=title, message=message, message_type=Gtk.MessageType.OTHER,
                         callback=callback, callback_data=callback_data, buttons=buttons)

        self.option = Gtk.CheckButton(label=option_label, active=option_value, visible=bool(option_label))

        if option_label:
            if GTK_API_VERSION >= 4:
                self.container.append(self.option)
            else:
                self.container.add(self.option)
