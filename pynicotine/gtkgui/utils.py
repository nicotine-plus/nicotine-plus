# COPYRIGHT (C) 2020-2022 Nicotine+ Team
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


""" Accelerators """


def _parse_accelerator(accelerator):

    keys = keycodes = []
    *_args, key, mods = Gtk.accelerator_parse(accelerator)

    if not key:
        return keycodes, mods

    keymap = Gdk.Keymap.get_for_display(Gdk.Display.get_default())
    _valid, keys = keymap.get_entries_for_keyval(key)

    keycodes = set(key.keycode for key in keys)
    return keycodes, mods


if Gtk.get_major_version() != 4:
    ALL_MODIFIERS = (_parse_accelerator("<Primary>")[1] | _parse_accelerator("<Shift>")[1]
                     | _parse_accelerator("<Alt>")[1])


def _activate_accelerator(widget, event, keycodes, required_mods, callback, user_data=None):

    activated_mods = event.state
    excluded_mods = ALL_MODIFIERS & ~required_mods

    if required_mods & ~activated_mods != 0:
        # Missing required modifiers
        return False

    if activated_mods & excluded_mods:
        # Too many/irrelevant modifiers
        return False

    if event.hardware_keycode not in keycodes:
        # Invalid key
        return False

    return callback(widget, None, user_data)


def setup_accelerator(accelerator, widget, callback, user_data=None):

    if Gtk.get_major_version() == 4:
        shortcut_controller = Gtk.ShortcutController()
        shortcut_controller.set_scope(Gtk.ShortcutScope.LOCAL)
        shortcut_controller.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        shortcut_controller.add_shortcut(
            Gtk.Shortcut(
                trigger=Gtk.ShortcutTrigger.parse_string(accelerator),
                action=Gtk.CallbackAction.new(callback, user_data),
            )
        )
        widget.add_controller(shortcut_controller)
        return

    # GTK 3 replacement for Gtk.ShortcutController
    keycodes, required_mods = _parse_accelerator(accelerator)
    widget.connect("key-press-event", _activate_accelerator, keycodes, required_mods, callback, user_data)


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
