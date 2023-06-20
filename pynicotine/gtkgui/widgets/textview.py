# COPYRIGHT (C) 2020-2023 Nicotine+ Contributors
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

from pynicotine import slskmessages
from pynicotine.config import config
from pynicotine.core import core
from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.widgets import clipboard
from pynicotine.gtkgui.widgets.theme import update_tag_visuals
from pynicotine.gtkgui.widgets.theme import USER_STATUS_COLORS
from pynicotine.utils import open_uri
from pynicotine.utils import PUNCTUATION


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

    def _insert_text(self, text, tag=None, iterator=None):

        if not text:
            return

        if iterator is None:
            iterator = self.textbuffer.get_end_iter()

        if tag is not None:
            start_offset = iterator.get_offset()

        self.textbuffer.insert(iterator, text)

        if tag is not None:
            start_iter = self.textbuffer.get_iter_at_offset(start_offset)
            self.textbuffer.apply_tag(tag, start_iter, iterator)

    def _append_new_line(self, line_data):
        for (text, tag) in line_data:
            self._insert_text(text, tag)

    def _prepend_old_line(self, line_data):
        for (text, tag) in reversed(line_data):
            iterator = self.textbuffer.get_iter_at_line(0)
            self._insert_text(text, tag, iterator)

    def _remove_old_lines(self):

        num_lines = self.textbuffer.get_line_count()

        if num_lines < self.max_num_lines:
            return False

        start_iter = self.textbuffer.get_start_iter()
        end_iter = self.textbuffer.get_iter_at_line(num_lines - self.max_num_lines)

        if GTK_API_VERSION >= 4:
            _position_found, end_iter = end_iter

        self.tag_urls.pop(end_iter, None)
        self.textbuffer.delete(start_iter, end_iter)

        self._prepend_old_line([("--- text buffer full ---\n", None)])
        return True

    def append_line(self, line, text_tag=None, timestamp=None, timestamp_format=None):

        if timestamp_format:
            line = time.strftime(timestamp_format, time.localtime(timestamp)) + " " + line

        if self.textbuffer.get_char_count() > 0:
            line = "\n" + line

        # Highlight urls, if found and tag them
        for text, tag in self.get_hyperlink_tags(line, text_tag):
            self._insert_text(text, tag)

        self._remove_old_lines()

    def get_hyperlink_tags(self, text, text_tag):
        """ Highlight urls, if found in text and tag them """

        tagged_text_data = []

        if self.parse_urls and ("://" in text or "www." in text or "mailto:" in text):
            # Match first url
            match = self.url_regex.search(text)

            while match:
                tagged_text_data.append((text[:match.start()], text_tag))

                url = match.group()
                url_tag = self.create_tag("urlcolor", url=url)
                self.tag_urls[self.textbuffer.get_end_iter()] = url_tag
                tagged_text_data.append((url, url_tag))

                # Match remaining url
                text = text[match.end():]
                match = self.url_regex.search(text)

        # Add remaining text
        tagged_text_data.append((text, text_tag))

        return tagged_text_data

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

            if hasattr(tag, "roomname"):
                cursor = self.DEFAULT_CURSOR
                break

        if cursor != self.cursor_window.get_cursor():
            self.cursor_window.set_cursor(cursor)

    def clear(self):

        start_iter, end_iter = self.textbuffer.get_bounds()

        self.textbuffer.delete(start_iter, end_iter)
        self.tag_urls.clear()

    """ Text Tags (roomnames, usernames, URLs) """

    def create_tag(self, color_id=None, callback=None, roomname=None, username=None, url=None):

        tag = self.textbuffer.create_tag()

        if color_id:
            update_tag_visuals(tag, color_id=color_id)
            tag.color_id = color_id

        if url:
            if url[:4] == "www.":
                url = "http://" + url

            tag.url = url

        if roomname:
            tag.callback = callback
            tag.roomname = roomname

        if username:
            tag.callback = callback
            tag.username = username

        return tag

    def update_tag(self, tag, color_id=None):

        if color_id is not None:
            tag.color_id = color_id

        update_tag_visuals(tag, color_id=tag.color_id)

    def update_url_tags(self):
        for tag in self.tag_urls.values():
            self.update_tag(tag)

    def update_tags(self):
        self.update_url_tags()

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

            if hasattr(tag, "roomname"):
                tag.callback(pressed_x, pressed_y, tag.roomname)
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


class ChatView(TextView):

    def __init__(self, *args, username_event=None, roomname_event=None, timestamp_format=None, **kwargs):

        super().__init__(*args, **kwargs)

        self.roomname_event = roomname_event
        self.username_event = username_event

        self.tag_remote = self.create_tag("chatremote")
        self.tag_local = self.create_tag("chatlocal")
        self.tag_command = self.create_tag("chatcommand")
        self.tag_action = self.create_tag("chatme")
        self.tag_highlight = self.create_tag("chathilite")

        self.tag_users = {}

        if roomname_event is not None:
            # This is Public global room feed
            self.tag_rooms = {}

        self.timestamp_format = timestamp_format

    @staticmethod
    def find_whole_word(word, text):
        """ Returns start position of a whole word that is not in a subword """

        if word not in text:
            return -1

        word_boundaries = [" "] + PUNCTUATION
        whole = False
        start = after = 0

        while not whole and start > -1:
            start = text.find(word, after)
            after = start + len(word)

            whole = ((text[after] if after < len(text) else " ") in word_boundaries
                     and (text[start - 1] if start > 0 else " ") in word_boundaries)

        return start if whole else -1

    def prepend_log_lines(self, logged_chat_lines, is_global=False):

        if not logged_chat_lines:
            return

        self.insert_new_line(_("--- old messages above ---"), tag=self.tag_highlight, prepend=True)

        for [timestamp, roomname, username, text, is_action] in reversed(logged_chat_lines):
            tag = self.tag_action if is_action else self.get_text_tag(text, username)

            self.insert_new_line(text, tag, username, roomname, timestamp, is_global, prepend=True)

    def insert_new_line(self, text, tag=None, username=None, roomname=None, timestamp=None, is_global=False,
                        prepend=False):
        """ Add a rich-text chat line using raw data to tag it before textbuffer insertion """

        if self._remove_old_lines() and prepend:
            return

        eol = "\n"
        space = " "
        space_tag = None  # TODO: full-row select hotzone

        tagged_line = []
        tagged_line.append((eol, None))

        if tag != self.tag_command:
            if not isinstance(timestamp, str):
                # Message sent while offline (server time) or normal newmessage (local time)
                time_tag = self.tag_remote if timestamp else self.tag_local
                timestamp = time.strftime(self.timestamp_format, time.localtime(timestamp))
            else:
                # Old logged message from local file, already have saved timestamp as string
                time_tag = self.tag_local
                text = text.rstrip(eol)

            tagged_line.append((timestamp, time_tag))

        if is_global and roomname:
            # This is Public global room feed
            room_tag = self.get_room_tag(roomname)

            tagged_line.append((" ", space_tag))
            tagged_line.append((roomname, room_tag))
            tagged_line.append((" |", space_tag))

        type_tag = self.get_type_tag(username)
        user_tag = self.get_user_tag(username)

        # Tag usernames with popup menu creating tag, and away/online/offline colors
        if tag == self.tag_action:
            tagged_line.append((" * ", self.tag_action))

            if username:
                tagged_line.append((username, user_tag))
                tagged_line.append((space, space_tag))

                text = text[4:]  # "/me "

        elif username:
            tagged_line.append((" [", type_tag))  # [ buddy user type highlight
            tagged_line.append((username, user_tag))
            tagged_line.append(("] ", type_tag))  # ] buddy user type highlight

        elif timestamp:
            tagged_line.append((space, space_tag))

        # Highlight urls, if found and tag them, add remaining text
        tagged_line += self.get_hyperlink_tags(text, tag)

        if prepend:
            self._prepend_old_line(tagged_line)
        else:
            self._append_new_line(tagged_line)

    def get_room_tag(self, roomname):

        if roomname not in self.tag_rooms:
            self.update_room_tag(roomname)

        return self.tag_rooms[roomname]

    def get_text_tag(self, text, user=None, login_username=None):

        if text.startswith("/me "):
            return self.tag_action

        if login_username is None:
            login_username = config.sections["server"]["login"]

        if not user or user == login_username:
            return self.tag_local

        if login_username and self.find_whole_word(login_username.lower(), text.lower()) > -1:
            return self.tag_highlight

        return self.tag_remote

    def get_type_tag(self, user):

        if user in core.userlist.buddies:
            return self.tag_highlight

        return self.tag_local

    def get_user_tag(self, username):

        if username not in self.tag_users:
            self.update_user_tag(username)

        return self.tag_users[username]

    def update_tags(self):

        super().update_tags()
        self.update_room_tags()
        self.update_user_tags()

        for tag in (
            self.tag_remote,
            self.tag_local,
            self.tag_command,
            self.tag_action,
            self.tag_highlight
        ):
            self.update_tag(tag)

    def update_room_tag(self, roomname):

        if not self.roomname_event:
            # Not Public global room feed
            return

        if roomname not in self.tag_rooms:
            self.tag_rooms[roomname] = self.create_tag(callback=self.roomname_event, roomname=roomname)

        color = "tab_changed" if roomname in core.chatrooms.joined_rooms else "searchq"
        self.update_tag(self.tag_rooms[roomname], color)

    def update_room_tags(self):

        if not self.roomname_event:
            # Not Public global room feed
            return

        for roomname in self.tag_rooms:
            self.update_room_tag(roomname)

    def update_user_tag(self, username):

        if username not in self.tag_users:
            self.tag_users[username] = self.create_tag(callback=self.username_event, username=username)

        status = core.user_statuses.get(username, slskmessages.UserStatus.OFFLINE)
        color = USER_STATUS_COLORS.get(status)
        self.update_tag(self.tag_users[username], color)

    def update_user_tags(self):
        for username in self.tag_users:
            self.update_user_tag(username)
