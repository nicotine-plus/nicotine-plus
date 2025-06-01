# SPDX-FileCopyrightText: 2021-2023 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

from gi.repository import Gdk
from gi.repository import GObject
from gi.repository import Gtk

from pynicotine.gtkgui.application import GTK_API_VERSION


# Clipboard #


if GTK_API_VERSION >= 4:
    _clipboard = Gdk.Display.get_default().get_clipboard()
else:
    _clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)  # pylint: disable=c-extension-no-member


def copy_text(text):

    if GTK_API_VERSION >= 4:
        _clipboard.set(GObject.Value(str, text))
    else:
        _clipboard.set_text(text, -1)


def copy_image(image_data):

    if GTK_API_VERSION >= 4:
        _clipboard.set(GObject.Value(Gdk.Texture, image_data))
    else:
        _clipboard.set_image(image_data)
