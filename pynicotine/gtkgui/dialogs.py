# COPYRIGHT (C) 2020-2021 Nicotine+ Team
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2008-2009 Quinox <quinox@users.sf.net>
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

from gi.repository import GdkPixbuf
from gi.repository import Gtk


""" General Dialogs """


def activate(self, dialog):
    dialog.response(Gtk.ResponseType.OK)


def combo_box_dialog(parent, title, message, default_text="",
                     option=False, optionmessage="",
                     optionvalue=False, droplist=[]):

    self = Gtk.MessageDialog(
        transient_for=parent,
        flags=0,
        message_type=Gtk.MessageType.QUESTION,
        buttons=Gtk.ButtonsType.OK_CANCEL,
        text=title
    )
    self.set_default_size(500, -1)
    self.set_modal(True)
    self.format_secondary_text(message)

    self.gotoption = option

    self.combo = Gtk.ComboBoxText.new_with_entry()

    for i in droplist:
        self.combo.append_text(i)

    self.combo.get_child().connect("activate", activate, self)
    self.combo.get_child().set_text(default_text)

    self.get_message_area().add(self.combo)

    self.combo.show()
    self.combo.grab_focus()

    if self.gotoption:

        self.option = Gtk.CheckButton()
        self.option.set_active(optionvalue)
        self.option.set_label(optionmessage)
        self.option.show()

        self.get_message_area().add(self.option)

    result = None
    if self.run() == Gtk.ResponseType.OK:
        if self.gotoption:
            result = [self.combo.get_child().get_text(), self.option.get_active()]
        else:
            result = self.combo.get_child().get_text()

    self.destroy()

    return result


def entry_dialog(parent, title, message, default=""):

    self = Gtk.MessageDialog(
        transient_for=parent,
        flags=0,
        message_type=Gtk.MessageType.QUESTION,
        buttons=Gtk.ButtonsType.OK_CANCEL,
        text=title
    )
    self.set_default_size(500, -1)
    self.set_modal(True)
    self.format_secondary_text(message)

    entry = Gtk.Entry()
    entry.connect("activate", activate, self)
    entry.set_activates_default(True)
    entry.set_text(default)
    self.get_message_area().add(entry)
    entry.show()

    result = None
    if self.run() == Gtk.ResponseType.OK:
        result = entry.get_text()

    self.destroy()

    return result


def message_dialog(parent, title, message):

    self = Gtk.MessageDialog(
        transient_for=parent,
        flags=0,
        message_type=Gtk.MessageType.INFO,
        buttons=Gtk.ButtonsType.OK,
        text=title
    )
    self.set_modal(True)
    self.format_secondary_text(message)

    self.run()
    self.destroy()


def option_dialog(parent, title, message, callback, callback_data=None, checkbox_label="", third=""):

    self = Gtk.MessageDialog(
        transient_for=parent,
        flags=0,
        message_type=Gtk.MessageType.QUESTION,
        buttons=Gtk.ButtonsType.OK_CANCEL,
        text=title
    )
    self.connect("response", callback, callback_data)
    self.set_modal(True)
    self.format_secondary_text(message)

    if checkbox_label:
        self.checkbox = Gtk.CheckButton()
        self.checkbox.set_label(checkbox_label)
        self.get_message_area().add(self.checkbox)
        self.checkbox.show()

    if third:
        self.add_button(third, Gtk.ResponseType.REJECT)

    self.show()


""" File Chooser Dialogs """


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
