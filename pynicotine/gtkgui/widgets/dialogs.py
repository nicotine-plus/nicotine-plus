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

from gi.repository import Gdk
from gi.repository import Gtk


""" Dialogs """


def generic_dialog(parent=None, content_box=None, quit_callback=None,
                   title="Dialog", width=400, height=400, modal=True):

    dialog = Gtk.Dialog(
        use_header_bar=Gtk.Settings.get_default().get_property("gtk-dialogs-use-header"),
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
                 option=False, optionmessage="", optionvalue=False, visibility=True,
                 droplist=[]):

    self = Gtk.MessageDialog(
        transient_for=parent,
        message_type=Gtk.MessageType.OTHER,
        buttons=Gtk.ButtonsType.OK_CANCEL,
        text=title,
        secondary_text=message
    )
    self.connect("response", callback, callback_data)
    self.set_size_request(500, -1)
    self.set_destroy_with_parent(True)
    self.set_modal(True)

    if Gtk.get_major_version() == 4:
        label = self.get_message_area().get_last_child()
    else:
        label = self.get_message_area().get_children()[-1]

    label.set_selectable(True)

    if droplist:
        dropdown = Gtk.ComboBoxText.new_with_entry()
        entry = dropdown.get_child()

        for i in droplist:
            dropdown.append_text(i)

        self.get_message_area().add(dropdown)
        dropdown.show()

    else:
        entry = Gtk.Entry()
        self.get_message_area().add(entry)
        entry.show()

    self.get_response_value = entry.get_text
    entry.connect("activate", lambda x: self.response(Gtk.ResponseType.OK))
    entry.set_activates_default(True)
    entry.set_text(default)
    entry.set_visibility(visibility)

    if option:
        self.option = Gtk.CheckButton()
        self.option.set_active(optionvalue)
        self.option.set_label(optionmessage)

        self.get_message_area().add(self.option)
        self.option.show()

        self.get_second_response_value = self.option.get_active

    self.present_with_time(Gdk.CURRENT_TIME)


def message_dialog(parent, title, message, callback=None):

    self = Gtk.MessageDialog(
        transient_for=parent,
        message_type=Gtk.MessageType.INFO,
        buttons=Gtk.ButtonsType.OK,
        text=title,
        secondary_text=message
    )

    if not callback:
        def callback(x, y):
            x.destroy()

    self.connect("response", callback)
    self.set_destroy_with_parent(True)
    self.set_modal(True)

    if Gtk.get_major_version() == 4:
        label = self.get_message_area().get_last_child()
    else:
        label = self.get_message_area().get_children()[-1]

    label.set_selectable(True)

    self.present_with_time(Gdk.CURRENT_TIME)


def option_dialog(parent, title, message, callback, callback_data=None,
                  checkbox_label="", cancel=True, third=""):

    if cancel:
        buttons = Gtk.ButtonsType.OK_CANCEL
    else:
        buttons = Gtk.ButtonsType.OK

    self = Gtk.MessageDialog(
        transient_for=parent,
        message_type=Gtk.MessageType.QUESTION,
        buttons=buttons,
        text=title,
        secondary_text=message
    )
    self.connect("response", callback, callback_data)
    self.set_destroy_with_parent(True)
    self.set_modal(True)

    if Gtk.get_major_version() == 4:
        label = self.get_message_area().get_last_child()
    else:
        label = self.get_message_area().get_children()[-1]

    label.set_selectable(True)

    if checkbox_label:
        self.checkbox = Gtk.CheckButton()
        self.checkbox.set_label(checkbox_label)

        self.get_message_area().add(self.checkbox)
        self.checkbox.show()

    if third:
        self.add_button(third, Gtk.ResponseType.REJECT)

    self.present_with_time(Gdk.CURRENT_TIME)

    """ Custom Dialog (to replace option_dialog) """

def custom_dialog(parent, title, message, callback, callback_data=None, checkbox_label="", checkbox_value=False,
                  id_0="", id_1="", id_2="", id_3="", id_4="", id_5="", id_6="", id_9="", default_button=1,
                  selectable=True, cancel=True, third=""):

    if id_0 or id_1:
        # Use Custom Buttons (0, 1, 2, 3...)
        buttons=Gtk.ButtonsType.NONE
        icon=Gtk.MessageType.QUESTION

    elif cancel and (id_0 == id_1 == ""):
        # Standard option_dialog
        buttons = Gtk.ButtonsType.OK_CANCEL
        icon=Gtk.MessageType.QUESTION
    else:
        # Simple message_dialog
        buttons = Gtk.ButtonsType.OK
        type=Gtk.MessageType.INFO

    self = Gtk.MessageDialog(
        transient_for=parent,
        message_type=icon,  # INFO; WARNING; QUESTION; ERROR; OTHER
        buttons=buttons,
        text=title,
        secondary_text=message or ""
    )
    self.connect("response", callback, callback_data)
    self.set_destroy_with_parent(True)
    self.set_modal(True)

    if Gtk.get_major_version() == 4:
        label = self.get_message_area().get_last_child()
    else:
        label = self.get_message_area().get_children()[-1]

    label.set_selectable(selectable)

    # Checkbox Option
    if checkbox_label:
        self.checkbox = Gtk.CheckButton()
        self.checkbox.set_label(checkbox_label)
        self.checkbox.set_active(checkbox_value)

        self.get_message_area().add(self.checkbox)
        self.checkbox.show()
    else:
        self.checkbox = None  # option can be hidden

    # Custom Buttons (label, response_id)
    if id_0:
        self.add_button(id_0, 0)
    if id_1:
        self.add_button(id_1, 1)

    if third:  # backwards compatable with option_dialog
        self.add_button(third, Gtk.ResponseType.REJECT)

    if id_2:
        self.add_button(id_2, 2)
    if id_3:
        self.add_button(id_3, 3)
    if id_4:
        self.add_button(id_4, 4)
    if id_5:
        self.add_button(id_5, 5)
    if id_6:
        self.add_button(id_6, 6)
    if id_9:
        self.add_button(id_9, 9)

    self.set_default_response(default_button)

    self.present_with_time(Gdk.CURRENT_TIME)
