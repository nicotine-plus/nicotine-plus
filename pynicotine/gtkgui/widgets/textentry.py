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

from pynicotine.gtkgui.utils import keyval_to_hardware_keycode


""" Text Entry/View-related """


class TextSearchBar:

    def __init__(self, textview, search_bar, entry):

        self.textview = textview
        self.search_bar = search_bar
        self.entry = entry

        self.search_bar.connect_entry(self.entry)

        self.entry.connect("activate", self.on_search_next_match)
        self.entry.connect("search-changed", self.on_search_changed)

        self.entry.connect("previous-match", self.on_search_previous_match)
        self.entry.connect("next-match", self.on_search_next_match)

        self.textview.connect("key-press-event", self.on_key_press)

    def on_search_match(self, search_type, restarted=False):

        buffer = self.textview.get_buffer()
        query = self.entry.get_text()

        self.textview.emit("select-all", False)

        if search_type == "typing":
            start, end = buffer.get_bounds()
            iterator = start
        else:
            current = buffer.get_mark("insert")
            iterator = buffer.get_iter_at_mark(current)

        if search_type == "previous":
            match = iterator.backward_search(query, Gtk.TextSearchFlags.TEXT_ONLY | Gtk.TextSearchFlags.CASE_INSENSITIVE, limit=None)
        else:
            match = iterator.forward_search(query, Gtk.TextSearchFlags.TEXT_ONLY | Gtk.TextSearchFlags.CASE_INSENSITIVE, limit=None)

        if match is not None and len(match) == 2:
            match_start, match_end = match

            if search_type == "previous":
                buffer.place_cursor(match_start)
                buffer.select_range(match_start, match_end)
            else:
                buffer.place_cursor(match_end)
                buffer.select_range(match_end, match_start)

            self.textview.scroll_to_iter(match_start, 0, False, 0.5, 0.5)

        elif not restarted and search_type != "typing":
            start, end = buffer.get_bounds()

            if search_type == "previous":
                buffer.place_cursor(end)
            elif search_type == "next":
                buffer.place_cursor(start)

            self.on_search_match(search_type, restarted=True)

    def on_search_changed(self, *args):
        self.on_search_match(search_type="typing")

    def on_search_previous_match(self, *args):
        self.on_search_match(search_type="previous")

    def on_search_next_match(self, *args):
        self.on_search_match(search_type="next")

    def on_key_press(self, widget, event):

        if event.get_state() & Gdk.ModifierType.CONTROL_MASK and \
                event.hardware_keycode in keyval_to_hardware_keycode(Gdk.KEY_f):
            self.show_search_bar()

    def show_search_bar(self):
        self.search_bar.set_search_mode(True)
        self.entry.grab_focus_without_selecting()


def clear_entry(entry):

    completion = entry.get_completion()
    entry.set_completion(None)
    entry.set_text("")
    entry.set_completion(completion)
