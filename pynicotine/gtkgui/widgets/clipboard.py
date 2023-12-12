# COPYRIGHT (C) 2021-2023 Nicotine+ Contributors
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
from gi.repository import GObject
from gi.repository import Gtk

from pynicotine.gtkgui.application import GTK_API_VERSION


# Clipboard #


if GTK_API_VERSION >= 4:
    _clipboard = Gdk.Display.get_default().get_clipboard()
else:
    _clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)


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
