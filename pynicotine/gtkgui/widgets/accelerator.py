# COPYRIGHT (C) 2021-2022 Nicotine+ Contributors
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


""" Accelerator """


class Accelerator:

    def __init__(self, accelerator, widget, callback, user_data=None):

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
        self.keycodes, self.required_mods = self.parse_accelerator(accelerator)
        self.callback = callback
        self.user_data = user_data

        widget.connect("key-press-event", self._activate_accelerator)

    @staticmethod
    def parse_accelerator(accelerator):

        keys = keycodes = []
        *_args, key, mods = Gtk.accelerator_parse(accelerator)

        if not key:
            return keycodes, mods

        if Gtk.get_major_version() == 4:
            _valid, keys = Gdk.Display.get_default().map_keyval(key)
        else:
            keymap = Gdk.Keymap.get_for_display(Gdk.Display.get_default())
            _valid, keys = keymap.get_entries_for_keyval(key)

        keycodes = {key.keycode for key in keys}
        return keycodes, mods

    def _activate_accelerator(self, widget, event):

        activated_mods = event.state
        required_mods = self.required_mods
        excluded_mods = ALL_MODIFIERS & ~required_mods

        if required_mods & ~activated_mods != 0:
            # Missing required modifiers
            return False

        if activated_mods & excluded_mods:
            # Too many/irrelevant modifiers
            return False

        if event.hardware_keycode not in self.keycodes:
            # Invalid key
            return False

        return self.callback(widget, None, self.user_data)


if Gtk.get_major_version() != 4:
    ALL_MODIFIERS = (Accelerator.parse_accelerator("<Primary>")[1]
                     | Accelerator.parse_accelerator("<Shift>")[1]
                     | Accelerator.parse_accelerator("<Alt>")[1])
