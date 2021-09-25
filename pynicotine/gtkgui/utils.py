# COPYRIGHT (C) 2020-2021 Nicotine+ Team
# COPYRIGHT (C) 2020 Lene Preuss <lene.preuss@gmail.com>
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2016 Mutnick <muhing@yahoo.com>
# COPYRIGHT (C) 2008-2011 Quinox <quinox@users.sf.net>
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

from gi.repository import Gdk
from gi.repository import Gtk


""" Clipboard """


def copy_text(text):

    if Gtk.get_major_version() == 4:
        clipboard = Gdk.Display.get_default().get_clipboard()
        clipboard.set(text)
        return

    clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
    clipboard.set_text(text, -1)


def copy_all_text(textview):

    textbuffer = textview.get_buffer()
    start, end = textbuffer.get_bounds()
    text = textbuffer.get_text(start, end, True)

    copy_text(text)


def copy_file_url(user, path):

    import urllib.parse
    url = "slsk://" + urllib.parse.quote(
        "%s/%s" % (user, path.replace("\\", "/"))
    )

    copy_text(url)


""" Events """


def connect_key_press_event(widget, callback):
    """ Use event controller or legacy 'key-press-event', depending on GTK version """

    if Gtk.get_major_version() == 4:
        controller = Gtk.EventControllerKey()
        controller.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        controller.connect("key-pressed", callback)

        widget.add_controller(controller)

    else:
        controller = None
        widget.connect("key-press-event", callback)

    return controller


def get_key_press_event_args(*args):

    if Gtk.get_major_version() == 4:
        controller, keyval, keycode, state = args
        widget = controller.get_widget()

    else:
        widget, event = args
        keyval = event.keyval
        keycode = event.hardware_keycode
        state = event.state

    return (keyval, keycode, state, widget)


def parse_accelerator(accelerator):

    keys = keycodes = []
    *args, key, mods = Gtk.accelerator_parse(accelerator)

    if not key:
        return keycodes, mods

    if Gtk.get_major_version() == 4:
        valid, keys = Gdk.Display.get_default().map_keyval(key)
    else:
        keymap = Gdk.Keymap.get_for_display(Gdk.Display.get_default())
        valid, keys = keymap.get_entries_for_keyval(key)

    keycodes = [key.keycode for key in keys]
    return keycodes, mods
