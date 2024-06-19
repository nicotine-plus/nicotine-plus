# COPYRIGHT (C) 2020-2024 Nicotine+ Contributors
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

from pynicotine.core import core
from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.widgets import clipboard
from pynicotine.gtkgui.widgets.accelerator import Accelerator
from pynicotine.gtkgui.widgets.theme import update_tag_visuals
from pynicotine.gtkgui.widgets.theme import USER_STATUS_COLORS
from pynicotine.slskmessages import UserStatus
from pynicotine.utils import find_whole_word
from pynicotine.utils import open_uri


class TextView:

    try:
        if GTK_API_VERSION >= 4:
            DEFAULT_CURSOR = Gdk.Cursor(name="default")
            POINTER_CURSOR = Gdk.Cursor(name="pointer")
            TEXT_CURSOR = Gdk.Cursor(name="text")
        else:
            DEFAULT_CURSOR = Gdk.Cursor.new_from_name(Gdk.Display.get_default(), "default")
            POINTER_CURSOR = Gdk.Cursor.new_from_name(Gdk.Display.get_default(), "pointer")
            TEXT_CURSOR = Gdk.Cursor.new_from_name(Gdk.Display.get_default(), "text")

    except TypeError:
        # Broken cursor theme, but what can we do...
        DEFAULT_CURSOR = POINTER_CURSOR = TEXT_CURSOR = None

    MAX_NUM_LINES = 50000
    URL_REGEX = re.compile("(\\w+\\://[^\\s]+)|(www\\.\\w+\\.[^\\s]+)|(mailto\\:[^\\s]+)")

    def __init__(self, parent, auto_scroll=False, parse_urls=True, editable=True,
                 horizontal_margin=12, vertical_margin=8, pixels_above_lines=1, pixels_below_lines=1):

        self.widget = Gtk.TextView(
            accepts_tab=False, editable=editable,
            left_margin=horizontal_margin, right_margin=horizontal_margin,
            top_margin=vertical_margin, bottom_margin=vertical_margin,
            pixels_above_lines=pixels_above_lines, pixels_below_lines=pixels_below_lines,
            wrap_mode=Gtk.WrapMode.WORD_CHAR, visible=True
        )

        if GTK_API_VERSION >= 4:
            parent.set_child(self.widget)  # pylint: disable=no-member
        else:
            parent.add(self.widget)        # pylint: disable=no-member

        self.textbuffer = self.widget.get_buffer()
        self.scrollable = self.widget.get_ancestor(Gtk.ScrolledWindow)
        scrollable_container = self.scrollable.get_ancestor(Gtk.Box)

        self.adjustment = self.scrollable.get_vadjustment()
        self.auto_scroll = auto_scroll
        self.adjustment_bottom = self.adjustment_value = 0
        self.notify_upper_handler = self.adjustment.connect("notify::upper", self.on_adjustment_upper_changed)
        self.notify_value_handler = self.adjustment.connect("notify::value", self.on_adjustment_value_changed)

        self.pressed_x = self.pressed_y = 0
        self.parse_urls = parse_urls

        if GTK_API_VERSION >= 4:
            self.textbuffer.set_enable_undo(editable)

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

    def destroy(self):

        # Prevent updates while destroying widget
        self.adjustment.disconnect(self.notify_upper_handler)
        self.adjustment.disconnect(self.notify_value_handler)

        self.__dict__.clear()

    def scroll_bottom(self):
        self.adjustment_value = (self.adjustment.get_upper() - self.adjustment.get_page_size())
        self.adjustment.set_value(self.adjustment_value)

    def _build_text_line(self, text, tag=None):

        text_line = []

        if self.parse_urls and ("://" in text or "www." in text or "mailto:" in text):
            # Match first url
            match = self.URL_REGEX.search(text)

            while match:
                text_line.append((text[:match.start()], tag))

                url = match.group()
                urltag = self.create_tag("urlcolor", url=url)
                text_line.append((url, urltag))

                # Match remaining url
                text = text[match.end():]
                match = self.URL_REGEX.search(text)

        text_line.append((text, tag))

        return text_line

    def _insert_line(self, text_line, prepend=False):

        line_number = 0 if prepend else self.textbuffer.get_line_count()
        iterator = self.get_iter_at_line(line_number)

        if prepend:
            # Break at end of line to avoid unwanted whitespace
            text_line.append(("\n", None))

        elif line_number > 1 or self.textbuffer.get_char_count() > 0:
            # No tag applied on line breaks to prevent visual glitch where text on the
            # next line has the wrong color
            self._insert_text("\n", None, iterator)

        for text, tag in text_line:
            self._insert_text(text, tag, iterator)

        self._remove_old_lines(line_number)

    def _insert_text(self, text, tag, iterator):

        if tag is not None:
            start_offset = iterator.get_offset()

        self.textbuffer.insert(iterator, text)

        if tag is not None:
            start_iter = self.textbuffer.get_iter_at_offset(start_offset)
            self.textbuffer.apply_tag(tag, start_iter, iterator)

    def _remove_old_lines(self, num_line_count):

        if num_line_count < self.MAX_NUM_LINES:
            # Not counted when prepending line
            return

        # Optimization: remove lines in batches
        start_iter = self.textbuffer.get_start_iter()
        end_line = (num_line_count - (self.MAX_NUM_LINES - 1000))
        end_iter = self.get_iter_at_line(end_line)

        self.textbuffer.delete(start_iter, end_iter)
        self.add_line("--- overflow ---", prepend=True)

    def add_line(self, message, prepend=False, timestamp_format=None):
        """Append or prepend message on a new line."""

        text_line = []

        if timestamp_format:
            # Create new timestamped string (use current localtime)
            text_line.append((time.strftime(timestamp_format, time.localtime()), None))
            text_line.append((" ", None))

        # Highlight urls, if found and tag them
        text_line.extend(self._build_text_line(message))

        self._insert_line(text_line, prepend=prepend)

    def add_text(self, text, tag=None, prepend=False):
        """Append or prepend text without adding line breaks."""

        iterator = self.get_iter_at_line(0 if prepend else -1)

        self._insert_text(text, tag, iterator)

    def get_iter_at_line(self, line_number):

        iterator = self.textbuffer.get_iter_at_line(line_number)

        if GTK_API_VERSION >= 4:
            _position_found, iterator = iterator

        return iterator

    def get_has_selection(self):
        return self.textbuffer.get_has_selection()

    def get_text(self):

        start_iter = self.textbuffer.get_start_iter()
        end_iter = self.textbuffer.get_end_iter()

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

    def grab_focus(self):
        self.widget.grab_focus()

    def place_cursor_at_line(self, line_number):

        iterator = self.get_iter_at_line(line_number)

        self.textbuffer.place_cursor(iterator)

    def set_text(self, text):
        """Sets text without any additional processing, and clears the undo stack."""

        self.textbuffer.set_text(text)

    def update_cursor(self, pos_x, pos_y):

        cursor = self.TEXT_CURSOR

        if self.cursor_window is None:
            self.cursor_window = self.widget.get_window(Gtk.TextWindowType.TEXT)  # pylint: disable=no-member

        for tag in self.get_tags_for_pos(pos_x, pos_y):
            if hasattr(tag, "name"):
                cursor = self.DEFAULT_CURSOR
                break

            if hasattr(tag, "url"):
                cursor = self.POINTER_CURSOR
                break

        if cursor != self.cursor_window.get_cursor():
            self.cursor_window.set_cursor(cursor)

    def clear(self):
        self.set_text("")

    # Text Tags (Roomnames, Usernames, URLs) #

    def create_tag(self, color_id=None, callback=None, name=None, url=None):

        tag = self.textbuffer.create_tag()

        if color_id:
            update_tag_visuals(tag, color_id=color_id)
            tag.color_id = color_id

        if url:
            if url.startswith("www."):
                url = "http://" + url

            tag.url = url

        elif name:
            tag.callback = callback
            tag.name = name

        return tag

    def update_tag(self, tag, color_id=None):

        if color_id is not None:
            tag.color_id = color_id

        update_tag_visuals(tag, color_id=tag.color_id)

    def update_tags(self):
        self.textbuffer.get_tag_table().foreach(self.update_tag)

    # Events #

    def on_released_primary(self, _controller, _num_p, pressed_x, pressed_y):

        self.pressed_x = pressed_x
        self.pressed_y = pressed_y

        if self.textbuffer.get_has_selection():
            return False

        for tag in self.get_tags_for_pos(pressed_x, pressed_y):
            if hasattr(tag, "url"):
                open_uri(tag.url)
                return True

            if hasattr(tag, "name"):
                tag.callback(pressed_x, pressed_y, tag.name)
                return True

        return False

    def on_pressed_secondary(self, _controller, _num_p, pressed_x, pressed_y):

        self.pressed_x = pressed_x
        self.pressed_y = pressed_y

        if self.textbuffer.get_has_selection():
            return False

        for tag in self.get_tags_for_pos(pressed_x, pressed_y):
            if hasattr(tag, "name"):
                tag.callback(pressed_x, pressed_y, tag.name)
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

        if self.auto_scroll and self.adjustment_value >= self.adjustment_bottom:
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

    def __init__(self, *args, chat_entry=None, status_users=None, roomname_event=None, username_event=None, **kwargs):

        super().__init__(*args, **kwargs)

        self.user_tags = self.status_users = {}
        self.chat_entry = chat_entry
        self.num_prepended_lines = 0
        self.roomname_event = roomname_event
        self.username_event = username_event

        if roomname_event is not None:
            # Only used in global room feed
            self._room_tags = {}

        if status_users is not None:
            # In chatrooms, we only want to set the online status for users that are
            # currently in the room, even though we might know their global status
            self.status_users = status_users

        self.type_tags = {
            "remote": self.create_tag("chatremote"),
            "local": self.create_tag("chatlocal"),
            "command": self.create_tag("chatcommand"),
            "action": self.create_tag("chatme"),
            "hilite": self.create_tag("chathilite")
        }

        Accelerator("Down", self.widget, self.on_page_down_accelerator)
        Accelerator("Page_Down", self.widget, self.on_page_down_accelerator)

    def add_line(self, message, prepend=False, timestamp_format=None, message_type=None,
                 timestamp=None, timestamp_string=None, roomname=None, username=None):
        """Append or prepend a new chat message line with name tags and links."""

        # Make a list of tuples [(text, tag),]
        chat_texts = self._build_chat_line(
            message,
            message_type=message_type,
            timestamp_string=timestamp_string,
            timestamp=timestamp,
            timestamp_format=timestamp_format,
            roomname=roomname,
            username=username
        )
        self._insert_line(chat_texts, prepend=prepend)

    def _build_chat_line(self, message, timestamp_format=None, message_type=None,
                         timestamp=None, timestamp_string=None, roomname=None, username=None):

        tag = self.type_tags.get(message_type)
        chat_line = []

        if timestamp_format:
            # Create timestamped string (use current localtime if timestamp is None)
            chat_line.append([time.strftime(timestamp_format, time.localtime(timestamp)), tag])
            chat_line.append((" ", tag))

        elif timestamp_string:
            # Use original timestamp string from log file (plus roomname for global feed)
            chat_line.append((timestamp_string, tag))
            chat_line.append((" ", tag))

        # Tag roomname, only used in global room feed
        roomtag = self._get_room_tag(roomname)

        if roomtag:
            chat_line.append((roomname, roomtag))
            chat_line.append((" | ", tag))

        # Tag username with popup menu creating tag, and away/online/offline colors
        if username:
            usertag = self._get_user_tag(username)
            opener, closer = ("* ", " ") if message_type == "action" else ("[", "] ")

            chat_line.append((opener, tag))
            chat_line.append((username, usertag))
            chat_line.append((closer, tag))

        # Highlight urls, if found and tag them
        chat_line.extend(self._build_text_line(message, tag))

        return chat_line

    def prepend_log_lines(self, log_lines, login_username=None):
        """Insert batch of previously gathered log lines."""

        if not self.num_prepended_lines and log_lines:
            self.add_text(_("--- old messages above ---"), tag=self.type_tags.get("hilite"))

        elif self.MAX_NUM_LINES - self.textbuffer.get_line_count() - len(log_lines) < 1000:
            self.add_line("--- overflow ---", prepend=True, message_type="hilite")
            return

        for decoded_line in self.decode_log_lines(log_lines, login_username=login_username):
            timestamp_string, username, message, message_type = decoded_line

            self.add_line(
                message, prepend=True, message_type=message_type, timestamp_string=timestamp_string, username=username)

        self.num_prepended_lines += len(log_lines)

    @staticmethod
    def decode_log_lines(log_lines, login_username=None):
        """Split encoded text strings into individual elements as
        required when reading raw chat log lines from disk."""

        login_lowercase = login_username.lower()

        for log_line in reversed(log_lines):
            try:
                line = log_line.decode("utf-8")

            except UnicodeDecodeError:
                line = log_lines.decode("latin-1")

            timestamp_string = username = message = message_type = None

            if " [" in line and "] " in line:
                start = line.find(" [") + 2
                end = line.find("] ", start)

                if end > start:
                    timestamp_string = line[:start - 2]
                    username = line[start:end]
                    message = line[end + 2:-1]

                    if username == login_username:
                        message_type = "local"

                    elif login_lowercase and find_whole_word(login_lowercase, message.lower()) > -1:
                        message_type = "hilite"

                    else:
                        message_type = "remote"

            elif " * " in line:
                start = line.find(" * ")

                timestamp_string = line[:start]
                message = line[start + 1:-1]
                message_type = "action"

            if message is None:
                message = line[:-1]

            yield timestamp_string, username, message, message_type

    def clear(self):

        super().clear()
        self.num_prepended_lines = 0
        self.user_tags.clear()

        if self.roomname_event:
            self._room_tags.clear()

    def _get_room_tag(self, roomname):

        if not self.roomname_event or not roomname:
            # Room tags only used in global room feed
            return None

        if roomname not in self._room_tags:
            # Pick a color, any color?
            color = USER_STATUS_COLORS.get(UserStatus.ONLINE)
            self._room_tags[roomname] = self.create_tag(color_id=color, callback=self.roomname_event, name=roomname)

        return self._room_tags[roomname]

    def _get_user_tag(self, username):

        if username not in self.user_tags:
            self.user_tags[username] = self.create_tag(callback=self.username_event, name=username)
            self.update_user_tag(username)

        return self.user_tags[username]

    def update_user_tag(self, username):

        if username not in self.user_tags:
            return

        status = UserStatus.OFFLINE

        if username in self.status_users:
            status = core.users.statuses.get(username, UserStatus.OFFLINE)

        color = USER_STATUS_COLORS.get(status)
        self.update_tag(self.user_tags[username], color)

    def update_user_tags(self):
        for username in self.user_tags:
            self.update_user_tag(username)

    def on_page_down_accelerator(self, *_args):
        """Page_Down, Down: Give focus to text entry if already scrolled at the
        bottom."""

        if self.textbuffer.props.cursor_position >= self.textbuffer.get_char_count():
            # Give focus to text entry upon scrolling down to the bottom
            self.chat_entry.grab_focus_without_selecting()
