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

import re
import time

from gi.repository import Gdk
from gi.repository import Gtk

from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.widgets import clipboard
from pynicotine.gtkgui.widgets.theme import update_tag_visuals
from pynicotine.utils import open_uri


""" Textview """


class TextView:

    if GTK_API_VERSION >= 4:
        DEFAULT_CURSOR = Gdk.Cursor(name="default")
        POINTER_CURSOR = Gdk.Cursor(name="pointer")
        TEXT_CURSOR = Gdk.Cursor(name="text")
    else:
        DEFAULT_CURSOR = Gdk.Cursor.new_from_name(Gdk.Display.get_default(), "default")
        POINTER_CURSOR = Gdk.Cursor.new_from_name(Gdk.Display.get_default(), "pointer")
        TEXT_CURSOR = Gdk.Cursor.new_from_name(Gdk.Display.get_default(), "text")

    def __init__(self, parent, auto_scroll=False, parse_urls=True, editable=True,
                 horizontal_margin=12, vertical_margin=8, pixels_above_lines=1, pixels_below_lines=1):

        self.widget = Gtk.TextView(
            accepts_tab=False, cursor_visible=editable, editable=editable,
            left_margin=horizontal_margin, right_margin=horizontal_margin,
            top_margin=vertical_margin, bottom_margin=vertical_margin,
            pixels_above_lines=pixels_above_lines, pixels_below_lines=pixels_below_lines,
            wrap_mode=Gtk.WrapMode.WORD_CHAR, visible=True
        )
        parent.set_property("child", self.widget)

        self.textbuffer = self.widget.get_buffer()
        self.scrollable = self.widget.get_ancestor(Gtk.ScrolledWindow)
        scrollable_container = self.scrollable.get_ancestor(Gtk.Box)

        self.adjustment = self.scrollable.get_vadjustment()
        self.auto_scroll = auto_scroll
        self.adjustment_bottom = self.adjustment_value = 0
        self.adjustment.connect("notify::upper", self.on_adjustment_upper_changed)
        self.adjustment.connect("notify::value", self.on_adjustment_value_changed)

        self.pressed_x = self.pressed_y = 0
        self.max_num_lines = 50000
        self.parse_urls = parse_urls
        self.tag_urls = {}
        self.url_regex = re.compile("(\\w+\\://[^\\s]+)|(www\\.\\w+\\.[^\\s]+)|(mailto\\:[^\\s]+)")

        if GTK_API_VERSION >= 4:
            self.gesture_click_primary = Gtk.GestureClick()
            scrollable_container.add_controller(self.gesture_click_primary)

            self.gesture_click_secondary = Gtk.GestureClick()
            scrollable_container.add_controller(self.gesture_click_secondary)

            self.cursor_window = self.widget

            self.motion_controller = Gtk.EventControllerMotion()
            self.motion_controller.connect("motion", self.on_move_cursor)
            self.widget.add_controller(self.motion_controller)  # pylint: disable=no-member
        else:
            self.gesture_click_primary = Gtk.GestureMultiPress(widget=scrollable_container)
            self.gesture_click_secondary = Gtk.GestureMultiPress(widget=scrollable_container)

            self.cursor_window = None

            self.widget.connect("motion-notify-event", self.on_move_cursor_event)

        self.gesture_click_primary.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        self.gesture_click_primary.connect("released", self.on_released_primary)

        self.gesture_click_secondary.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        self.gesture_click_secondary.set_button(Gdk.BUTTON_SECONDARY)
        self.gesture_click_secondary.connect("pressed", self.on_pressed_secondary)

    def scroll_bottom(self):
        self.adjustment_value = (self.adjustment.get_upper() - self.adjustment.get_page_size())
        self.adjustment.set_value(self.adjustment_value)

    def _insert_text(self, text, tag=None):

        if not text:
            return

        iterator = self.textbuffer.get_end_iter()

        if tag is not None:
            start_offset = iterator.get_offset()

        self.textbuffer.insert(iterator, text)

        if tag is not None:
            start_iter = self.textbuffer.get_iter_at_offset(start_offset)
            self.textbuffer.apply_tag(tag, start_iter, iterator)

    def _remove_old_lines(self, num_lines):

        if num_lines < self.max_num_lines:
            return

        start_iter = self.textbuffer.get_start_iter()
        end_iter = self.textbuffer.get_iter_at_line(num_lines - self.max_num_lines)

        if GTK_API_VERSION >= 4:
            _position_found, end_iter = end_iter

        self.tag_urls.pop(end_iter, None)
        self.textbuffer.delete(start_iter, end_iter)

    def append_line(self, line, tag=None, timestamp=None, timestamp_format=None, username=None, usertag=None):

        num_lines = self.textbuffer.get_line_count()
        line = str(line).strip("\n")

        if timestamp_format:
            line = time.strftime(timestamp_format, time.localtime(timestamp)) + " " + line

        if self.textbuffer.get_char_count() > 0:
            line = "\n" + line

        # Tag usernames with popup menu creating tag, and away/online/offline colors
        if username and username in line:
            start = line.find(username)

            self._insert_text(line[:start], tag)
            self._insert_text(username, usertag)

            line = line[start + len(username):]

        # Highlight urls, if found and tag them
        if self.parse_urls and ("://" in line or "www." in line or "mailto:" in line):
            # Match first url
            match = self.url_regex.search(line)

            while match:
                self._insert_text(line[:match.start()], tag)

                url = match.group()
                urltag = self.create_tag("urlcolor", url=url)
                self.tag_urls[self.textbuffer.get_end_iter()] = urltag
                self._insert_text(url, urltag)

                # Match remaining url
                line = line[match.end():]
                match = self.url_regex.search(line)

        self._insert_text(line, tag)
        self._remove_old_lines(num_lines)

        return num_lines

    def get_has_selection(self):
        return self.textbuffer.get_has_selection()

    def get_text(self):
        start_iter, end_iter = self.textbuffer.get_bounds()
        return self.textbuffer.get_text(start_iter, end_iter, include_hidden_chars=True)

    def get_tags_for_pos(self, pos_x, pos_y):

        buf_x, buf_y = self.widget.window_to_buffer_coords(Gtk.TextWindowType.WIDGET, pos_x, pos_y)
        over_text, iterator, _trailing = self.widget.get_iter_at_position(buf_x, buf_y)

        if not over_text:
            # Iterators are returned for whitespace after the last character, avoid accidental URL clicks
            return []

        return iterator.get_tags()

    def get_url_for_current_pos(self):

        for tag in self.get_tags_for_pos(self.pressed_x, self.pressed_y):
            if hasattr(tag, "url"):
                return tag.url

        return ""

    def update_cursor(self, pos_x, pos_y):

        cursor = self.TEXT_CURSOR

        if self.cursor_window is None:
            self.cursor_window = self.widget.get_window(Gtk.TextWindowType.TEXT)  # pylint: disable=no-member

        for tag in self.get_tags_for_pos(pos_x, pos_y):
            if hasattr(tag, "username"):
                cursor = self.DEFAULT_CURSOR
                break

            if hasattr(tag, "url"):
                cursor = self.POINTER_CURSOR
                break

        if cursor != self.cursor_window.get_cursor():
            self.cursor_window.set_cursor(cursor)

    def clear(self):

        start_iter, end_iter = self.textbuffer.get_bounds()

        self.textbuffer.delete(start_iter, end_iter)
        self.tag_urls.clear()

    """ Text Tags (usernames, URLs) """

    def create_tag(self, color_id=None, callback=None, username=None, url=None):

        tag = self.textbuffer.create_tag()

        if color_id:
            update_tag_visuals(tag, color_id=color_id)
            tag.color_id = color_id

        if url:
            if url[:4] == "www.":
                url = "http://" + url

            tag.url = url

        if username:
            tag.callback = callback
            tag.username = username

        return tag

    def update_tag(self, tag, color_id=None):

        if color_id is not None:
            tag.color_id = color_id

        update_tag_visuals(tag, color_id=tag.color_id)

    def update_tags(self):
        for tag in self.tag_urls.values():
            self.update_tag(tag)

    """ Events """

    def on_released_primary(self, _controller, _num_p, pressed_x, pressed_y):

        self.pressed_x = pressed_x
        self.pressed_y = pressed_y

        if self.textbuffer.get_has_selection():
            return False

        for tag in self.get_tags_for_pos(pressed_x, pressed_y):
            if hasattr(tag, "url"):
                open_uri(tag.url)
                return True

            if hasattr(tag, "username"):
                tag.callback(pressed_x, pressed_y, tag.username)
                return True

        return False

    def on_pressed_secondary(self, _controller, _num_p, pressed_x, pressed_y):

        self.pressed_x = pressed_x
        self.pressed_y = pressed_y

        if self.textbuffer.get_has_selection():
            return False

        for tag in self.get_tags_for_pos(pressed_x, pressed_y):
            if hasattr(tag, "username"):
                tag.callback(pressed_x, pressed_y, tag.username)
                return True

        return False

    def on_move_cursor(self, _controller, pos_x, pos_y):
        self.update_cursor(pos_x, pos_y)

    def on_move_cursor_event(self, _widget, event):
        self.update_cursor(event.x, event.y)

    def on_copy_text(self, *_args):
        self.widget.emit("copy-clipboard")

    def on_copy_link(self, *_args):
        clipboard.copy_text(self.get_url_for_current_pos())

    def on_copy_all_text(self, *_args):
        clipboard.copy_text(self.get_text())

    def on_clear_all_text(self, *_args):
        self.clear()

    def on_adjustment_upper_changed(self, *_args):

        new_adjustment_bottom = (self.adjustment.get_upper() - self.adjustment.get_page_size())

        if self.auto_scroll and (self.adjustment_bottom - self.adjustment_value) <= 0:
            # Scroll to bottom if we were at the bottom previously
            self.scroll_bottom()

        self.adjustment_bottom = new_adjustment_bottom

    def on_adjustment_value_changed(self, *_args):

        new_value = self.adjustment.get_value()

        if new_value.is_integer() and (0 < new_value < self.adjustment_bottom):
            # The textview scrolls up on its own sometimes. Ignore these garbage values.
            return

        self.adjustment_value = new_value
