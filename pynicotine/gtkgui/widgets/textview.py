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

import re
import time

from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import Gtk

from pynicotine.config import config
from pynicotine.gtkgui.utils import copy_all_text
from pynicotine.gtkgui.utils import copy_text
from pynicotine.gtkgui.widgets.theme import update_tag_visuals
from pynicotine.utils import open_uri


""" Textview """


class TextView:

    def __init__(self, textview, font=None):

        self.textview = textview
        self.textbuffer = textview.get_buffer()
        self.scrollable = textview.get_parent()
        self.font = font
        self.url_regex = re.compile("(\\w+\\://[^\\s]+)|(www\\.\\w+\\.[^\\s]+)|(mailto\\:[^\\s]+)")

        self.tag_urls = []
        self.pressed_x = 0
        self.pressed_y = 0

        if Gtk.get_major_version() == 4:
            self.gesture_click = Gtk.GestureClick()
            self.gesture_click_secondary = Gtk.GestureClick()
            self.scrollable.add_controller(self.gesture_click)
            self.scrollable.add_controller(self.gesture_click_secondary)

        else:
            self.gesture_click = Gtk.GestureMultiPress.new(self.scrollable)
            self.gesture_click_secondary = Gtk.GestureMultiPress.new(self.scrollable)

        self.gesture_click.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        self.gesture_click.connect("pressed", self._callback_pressed)
        self.gesture_click.connect("released", self._callback_released)

        self.gesture_click_secondary.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        self.gesture_click_secondary.connect("pressed", self._callback_pressed)
        self.gesture_click_secondary.set_button(Gdk.BUTTON_SECONDARY)

        self.textview.connect("realize", self.on_realize)

    def scroll_bottom(self):

        if not self.textview.get_realized():
            # Avoid GTK warnings
            return False

        adjustment = self.scrollable.get_vadjustment()
        adjustment.set_value(adjustment.get_upper() - adjustment.get_page_size())
        return False

    def append_line(self, line, tag=None, timestamp=None, showstamp=True, timestamp_format="%H:%M:%S",
                    username=None, usertag=None, scroll=True, find_urls=True):

        def _append(buffer, text, tag):

            iterator = buffer.get_end_iter()

            if tag is not None:
                start_offset = iterator.get_offset()

            buffer.insert(iterator, text)

            if tag is not None:
                start = buffer.get_iter_at_offset(start_offset)
                buffer.apply_tag(tag, start, iterator)

        def _usertag(buffer, section):

            # Tag usernames with popup menu creating tag, and away/online/offline colors
            if (username is not None and usertag is not None and config.sections["ui"]["usernamehotspots"]
                    and username in section):
                start = section.find(username)
                end = start + len(username)

                _append(buffer, section[:start], tag)
                _append(buffer, username, usertag)
                _append(buffer, section[end:], tag)
                return

            _append(buffer, section, tag)

        line = str(line).strip("\n")
        buffer = self.textbuffer
        linenr = buffer.get_line_count()

        if showstamp and timestamp_format:
            if timestamp:
                final_timestamp = time.strftime(timestamp_format, time.localtime(timestamp)) + " "
            else:
                final_timestamp = time.strftime(timestamp_format) + " "

            line = final_timestamp + line

        if buffer.get_char_count() > 0:
            line = "\n" + line

        if find_urls and ("://" in line or "www." in line or "mailto:" in line):
            # Match first url
            match = self.url_regex.search(line)

            # Highlight urls, if found and tag them
            while match:
                _usertag(buffer, line[:match.start()])

                url = match.group()
                urltag = self.create_tag("urlcolor", url=url)
                self.tag_urls.append(urltag)
                _append(buffer, url, urltag)

                # Match remaining url
                line = line[match.end():]
                match = self.url_regex.search(line)

        if line:
            _usertag(buffer, line)

        if scroll:
            alignment = self.scrollable.get_vadjustment()

            # Scroll to bottom if we had scrolled up less than ~2 lines previously
            if (alignment.get_value() + alignment.get_page_size()) >= alignment.get_upper() - 40:
                GLib.idle_add(self.scroll_bottom, priority=GLib.PRIORITY_LOW)

        return linenr

    def get_has_selection(self):
        return self.textbuffer.get_has_selection()

    def get_tags_for_selected_pos(self):

        buf_x, buf_y = self.textview.window_to_buffer_coords(Gtk.TextWindowType.WIDGET,
                                                             self.pressed_x, self.pressed_y)
        _over_text, iterator = self.textview.get_iter_at_location(buf_x, buf_y)
        return iterator.get_tags()

    def get_url_for_selected_pos(self):

        for tag in self.get_tags_for_selected_pos():
            if hasattr(tag, "url"):
                return tag.url

        return ""

    def clear(self):
        self.textbuffer.set_text("")
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
        for tag in self.tag_urls:
            self.update_tag(tag)

    """ Events """

    def _callback_pressed(self, _controller, _num_p, pressed_x, pressed_y):
        self.pressed_x = pressed_x
        self.pressed_y = pressed_y

    def _callback_released(self, _controller, _num_p, pressed_x, pressed_y):

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

    def on_copy_text(self, *_args):
        self.textview.emit("copy-clipboard")

    def on_copy_link(self, *_args):
        copy_text(self.get_url_for_selected_pos())

    def on_copy_all_text(self, *_args):
        copy_all_text(self.textview)

    def on_clear_all_text(self, *_args):
        self.clear()

    def on_realize(self, *_args):
        self.scroll_bottom()
