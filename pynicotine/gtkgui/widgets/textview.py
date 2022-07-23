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
from gi.repository import GLib
from gi.repository import Gtk

from pynicotine.config import config
from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.utils import copy_text
from pynicotine.gtkgui.widgets.theme import update_tag_visuals
from pynicotine.utils import open_uri


""" Textview """


class TextView:

    def __init__(self, textview, font=None, auto_scroll=False):

        self.textview = textview
        self.textbuffer = textview.get_buffer()
        self.scrollable = textview.get_ancestor(Gtk.ScrolledWindow)
        self.adjustment = self.scrollable.get_vadjustment()
        scrollable_container = self.scrollable.get_ancestor(Gtk.Box)
        self.font = font
        self.url_regex = re.compile("(\\w+\\://[^\\s]+)|(www\\.\\w+\\.[^\\s]+)|(mailto\\:[^\\s]+)")

        self.tag_urls = {}
        self.pressed_x = 0
        self.pressed_y = 0
        self.max_num_lines = 50000

        self.auto_scroll = self.should_auto_scroll = auto_scroll

        self.adjustment.connect("notify::upper", self.on_adjustment_changed)
        self.adjustment.connect("notify::value", self.on_adjustment_changed, True)

        if GTK_API_VERSION >= 4:
            self.gesture_click_primary = Gtk.GestureClick()
            scrollable_container.add_controller(self.gesture_click_primary)

            self.gesture_click_secondary = Gtk.GestureClick()
            scrollable_container.add_controller(self.gesture_click_secondary)
        else:
            self.gesture_click_primary = Gtk.GestureMultiPress(widget=scrollable_container)
            self.gesture_click_secondary = Gtk.GestureMultiPress(widget=scrollable_container)

        self.gesture_click_primary.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        self.gesture_click_primary.connect("pressed", self._callback_pressed_primary)
        self.gesture_click_primary.connect("released", self._callback_released_primary)

        self.gesture_click_secondary.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        self.gesture_click_secondary.set_button(Gdk.BUTTON_SECONDARY)
        self.gesture_click_secondary.connect("pressed", self._callback_pressed_secondary)

    def scroll_bottom(self, *_args):

        if not self.textview.get_realized():
            # Avoid GTK warnings
            return

        self.adjustment.set_value(self.adjustment.get_upper() - self.adjustment.get_page_size())

    def append_line(self, line, tag=None, timestamp=None, timestamp_format=None, username=None,
                    usertag=None, find_urls=True):

        def _append(buffer, text, tag):

            iterator = buffer.get_end_iter()

            if tag is not None:
                start_offset = iterator.get_offset()

            buffer.insert(iterator, text)

            if tag is not None:
                start_iter = buffer.get_iter_at_offset(start_offset)
                buffer.apply_tag(tag, start_iter, iterator)

        def _usertag(buffer, section):

            # Tag usernames with popup menu creating tag, and away/online/offline colors
            if (username is not None and usertag is not None and config.sections["ui"]["usernamehotspots"]
                    and username in section):
                start = section.find(username)
                end = start + len(username)

                _append(buffer, section[:start], tag)
                _append(buffer, username, usertag)
                return section[end:]

            _append(buffer, section, tag)
            return ""

        line = str(line).strip("\n")
        buffer = self.textbuffer
        num_lines = buffer.get_line_count()

        if timestamp_format:
            if timestamp:
                final_timestamp = time.strftime(timestamp_format, time.localtime(timestamp)) + " "
            else:
                final_timestamp = time.strftime(timestamp_format) + " "

            line = final_timestamp + line

        if buffer.get_char_count() > 0:
            line = "\n" + line

        if line:
            line = _usertag(buffer, line)

        if find_urls and ("://" in line or "www." in line or "mailto:" in line):
            # Match first url
            match = self.url_regex.search(line)

            # Highlight urls, if found and tag them
            while match:
                _usertag(buffer, line[:match.start()])

                url = match.group()
                urltag = self.create_tag("urlcolor", url=url)
                self.tag_urls[buffer.get_end_iter()] = urltag
                _append(buffer, url, urltag)

                # Match remaining url
                line = line[match.end():]
                match = self.url_regex.search(line)

        if line:
            _append(buffer, line, tag)

        if num_lines >= self.max_num_lines:
            # Limit number of lines in textview
            start_iter = buffer.get_start_iter()
            end_iter = buffer.get_iter_at_line(num_lines - self.max_num_lines)

            if GTK_API_VERSION >= 4:
                _position_found, end_iter = end_iter

            self.tag_urls.pop(end_iter, None)
            buffer.delete(start_iter, end_iter)

        return num_lines

    def get_has_selection(self):
        return self.textbuffer.get_has_selection()

    def get_tags_for_selected_pos(self):

        buf_x, buf_y = self.textview.window_to_buffer_coords(Gtk.TextWindowType.WIDGET,
                                                             self.pressed_x, self.pressed_y)
        over_text, iterator, _trailing = self.textview.get_iter_at_position(buf_x, buf_y)

        if not over_text:
            # Iterators are returned for whitespace after the last character, avoid accidental URL clicks
            return []

        return iterator.get_tags()

    def get_url_for_selected_pos(self):

        for tag in self.get_tags_for_selected_pos():
            if hasattr(tag, "url"):
                return tag.url

        return ""

    def clear(self):

        start_iter, end_iter = self.textbuffer.get_bounds()

        self.textbuffer.delete(start_iter, end_iter)
        self.tag_urls.clear()

    """ Text Tags (usernames, URLs) """

    def create_tag(self, color=None, callback=None, username=None, url=None):

        tag = self.textbuffer.create_tag()

        if color:
            update_tag_visuals(tag, color=color)
            tag.color = color

        if self.font:
            update_tag_visuals(tag, font=self.font)

        if url:
            if url[:4] == "www.":
                url = "http://" + url

            tag.url = url

        if username:
            tag.callback = callback
            tag.username = username

        return tag

    def update_tag(self, tag, color=None):

        if color is not None:
            tag.color = color

        update_tag_visuals(tag, tag.color, self.font)

    def update_tags(self):
        for tag in self.tag_urls.values():
            self.update_tag(tag)

    """ Events """

    def _callback_pressed_primary(self, _controller, _num_p, pressed_x, pressed_y):
        self.pressed_x = pressed_x
        self.pressed_y = pressed_y

    def _callback_released_primary(self, _controller, _num_p, pressed_x, pressed_y):

        if pressed_x != self.pressed_x or pressed_y != self.pressed_y:
            return False

        for tag in self.get_tags_for_selected_pos():
            if hasattr(tag, "url"):
                open_uri(tag.url)
                return True

            if hasattr(tag, "username"):
                tag.callback(pressed_x, pressed_y, tag.username)
                return True

        return False

    def _callback_pressed_secondary(self, _controller, _num_p, pressed_x, pressed_y):

        self.pressed_x = pressed_x
        self.pressed_y = pressed_y

        for tag in self.get_tags_for_selected_pos():
            if hasattr(tag, "username"):
                tag.callback(pressed_x, pressed_y, tag.username)
                return True

        return False

    def on_copy_text(self, *_args):
        self.textview.emit("copy-clipboard")

    def on_copy_link(self, *_args):
        copy_text(self.get_url_for_selected_pos())

    def on_copy_all_text(self, *_args):

        textbuffer = self.textview.get_buffer()
        start_iter, end_iter = textbuffer.get_bounds()
        text = textbuffer.get_text(start_iter, end_iter, True)

        copy_text(text)

    def on_clear_all_text(self, *_args):
        self.clear()

    def on_adjustment_changed(self, adjustment, _param, force_scroll=False):

        if not self.auto_scroll:
            return

        if force_scroll or not self.should_auto_scroll:
            # Scroll to bottom if we were at the bottom previously
            bottom = adjustment.get_upper() - adjustment.get_page_size()
            self.should_auto_scroll = (bottom - adjustment.get_value() <= 0)

        if self.should_auto_scroll:
            GLib.idle_add(self.scroll_bottom, priority=GLib.PRIORITY_LOW)
