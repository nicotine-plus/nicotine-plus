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

from gi.repository import Gdk
from gi.repository import Gtk

from pynicotine.config import config

""" Dialogs """


def generic_dialog(parent=None, content_box=None, quit_callback=None,
                   title="Dialog", width=400, height=400, modal=True):

    dialog = Gtk.Dialog(
        use_header_bar=config.sections["ui"]["header_bar"],
        title=title,
        default_width=width,
        default_height=height
    )

    if content_box:
        dialog.get_content_area().add(content_box)

    set_dialog_properties(dialog, parent, quit_callback, modal)
    return dialog


def set_dialog_properties(dialog, parent, quit_callback=None, modal=True):

    if Gtk.get_major_version() == 4:
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
    if Gtk.get_major_version() == 4:
        main_width = parent.get_width()
        main_height = parent.get_height()
    else:
        main_width, main_height = parent.get_size()

    new_width = dialog_width = dialog.get_property("default-width")
    new_height = dialog_height = dialog.get_property("default-height")

    if dialog_width > main_width:
        new_width = main_width - 30

    if dialog_height > main_height:
        new_height = main_height - 30

    if new_width > 0 and new_height > 0:
        if Gtk.get_major_version() == 4:
            dialog.set_default_size(new_width, new_height)
        else:
            dialog.resize(new_width, new_height)

    # Show the dialog
    dialog.present_with_time(Gdk.CURRENT_TIME)

    if Gtk.get_major_version() == 3:
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


def entry_dialog(parent, title, message, callback, callback_data=None, default="",
                 optionmessage="", optionvalue=False, visibility=True, droplist=None):

    self = Gtk.MessageDialog(
        transient_for=parent,
        default_width=500,
        message_type=Gtk.MessageType.OTHER,
        buttons=Gtk.ButtonsType.OK_CANCEL,
        destroy_with_parent=True,
        modal=True,
        text=title,
        secondary_text=message
    )
    self.connect("response", callback, callback_data)

    if Gtk.get_major_version() == 4:
        label = self.get_message_area().get_last_child()
    else:
        label = self.get_message_area().get_children()[-1]

    label.set_selectable(True)

    if droplist:
        dropdown = Gtk.ComboBoxText(has_entry=True, visible=True)
        entry = dropdown.get_child()

        for i in droplist:
            dropdown.append_text(i)

        self.get_message_area().add(dropdown)
    else:
        entry = Gtk.Entry(visible=True)
        self.get_message_area().add(entry)

    self.get_response_value = entry.get_text
    entry.connect("activate", lambda x: self.response(Gtk.ResponseType.OK))
    entry.set_activates_default(True)
    entry.set_text(default)
    entry.set_visibility(visibility)

    if optionmessage:
        self.option = Gtk.CheckButton(label=optionmessage, active=optionvalue, visible=True)
        self.get_message_area().add(self.option)
        self.get_second_response_value = self.option.get_active

    self.present_with_time(Gdk.CURRENT_TIME)


def message_dialog(parent, title, message, callback=None):

    self = Gtk.MessageDialog(
        transient_for=parent,
        message_type=Gtk.MessageType.INFO,
        buttons=Gtk.ButtonsType.OK,
        destroy_with_parent=True,
        modal=True,
        text=title,
        secondary_text=message
    )

    if not callback:
        def callback(dialog, *_args):
            dialog.destroy()

    self.connect("response", callback)

    if Gtk.get_major_version() == 4:
        label = self.get_message_area().get_last_child()
    else:
        label = self.get_message_area().get_children()[-1]

    label.set_selectable(True)

    self.present_with_time(Gdk.CURRENT_TIME)


def option_dialog(parent, title, message, callback, callback_data=None, checkbox_label="",
                  first_button=_("_No"), second_button=_("_Yes"), third_button=""):

    self = Gtk.MessageDialog(
        transient_for=parent,
        message_type=Gtk.MessageType.QUESTION,
        destroy_with_parent=True,
        modal=True,
        text=title,
        secondary_text=message
    )
    self.connect("response", callback, callback_data)

    if Gtk.get_major_version() == 4:
        label = self.get_message_area().get_last_child()
    else:
        label = self.get_message_area().get_children()[-1]

    label.set_selectable(True)

    self.checkbox = Gtk.CheckButton(label=checkbox_label, visible=bool(checkbox_label))

    if checkbox_label:
        self.get_message_area().add(self.checkbox)

    if first_button:
        self.add_button(first_button, 1)

    if second_button:
        self.add_button(second_button, 2)

    if third_button:
        self.add_button(third_button, 3)

    self.present_with_time(Gdk.CURRENT_TIME)
