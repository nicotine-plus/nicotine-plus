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
from gi.repository import Pango

from pynicotine.config import config
from pynicotine.gtkgui.utils import open_uri


""" Textview """


URL_RE = re.compile("(\\w+\\://[^\\s]+)|(www\\.\\w+\\.\\w+.*?)|(mailto\\:[^\\s]+)")


def scroll_bottom(widget):

    try:
        adjustment = widget.get_vadjustment()
        adjustment.set_value(adjustment.get_upper() - adjustment.get_page_size())

    except AttributeError:
        # Nicotine+ is exiting
        pass


def url_event(tag, widget, event, iterator, url):

    if (tag.last_event_type == Gdk.EventType.BUTTON_PRESS
            and event.button.type == Gdk.EventType.BUTTON_RELEASE and event.button.button == 1):
        if url[:4] == "www.":
            url = "http://" + url
        open_uri(url, widget.get_toplevel())

    tag.last_event_type = event.button.type


def append_line(textview, line, tag=None, timestamp=None, showstamp=True, timestamp_format="%H:%M:%S",
                username=None, usertag=None, scroll=True, find_urls=True):

    def _makeurltag(buffer, url):

        color = config.sections["ui"]["urlcolor"] or None
        tag = buffer.create_tag(foreground=color, underline=Pango.Underline.SINGLE)
        tag.last_event_type = -1

        if Gtk.get_major_version() == 3:
            tag.connect("event", url_event, url)

        return tag

    def _append(buffer, text, tag):

        iterator = buffer.get_end_iter()
        start_offset = iterator.get_offset()
        buffer.insert(iterator, text)

        if tag is not None:
            start = buffer.get_iter_at_offset(start_offset)
            buffer.apply_tag(tag, start, iterator)

    def _usertag(buffer, section):

        # Tag usernames with popup menu creating tag, and away/online/offline colors
        if username is not None and usertag is not None and config.sections["ui"]["usernamehotspots"]:
            np = re.compile(re.escape(str(username)))
            match = np.search(section)

            if match is not None:
                _append(buffer, section[:match.start()], tag)
                _append(buffer, match.group(), usertag)
                _append(buffer, section[match.end():], tag)
                return

        _append(buffer, section, tag)

    line = str(line).strip("\n")
    buffer = textview.get_buffer()
    linenr = buffer.get_line_count()

    if buffer.get_char_count() > 0:
        _append(buffer, "\n", None)

    if showstamp and timestamp_format and config.sections["logging"]["timestamps"]:
        if timestamp:
            final_timestamp = time.strftime(timestamp_format, time.localtime(timestamp)) + " "
        else:
            final_timestamp = time.strftime(timestamp_format) + " "

        _append(buffer, final_timestamp, tag)

    if find_urls and config.sections["urls"]["urlcatching"]:
        # Match first url
        match = URL_RE.search(line)

        # Highlight urls, if found and tag them
        while match:
            _usertag(buffer, line[:match.start()])

            url = match.group()
            urltag = _makeurltag(buffer, url)

            if url.startswith("slsk://") and config.sections["urls"]["humanizeurls"]:
                import urllib.parse
                url = urllib.parse.unquote(url)

            _append(buffer, url, urltag)

            # Match remaining url
            line = line[match.end():]
            match = URL_RE.search(line)

    if line:
        _usertag(buffer, line)

    if scroll:
        scrollable = textview.get_parent()
        va = scrollable.get_vadjustment()

        # Scroll to bottom if we had scrolled up less than ~2 lines previously
        if (va.get_value() + va.get_page_size()) >= va.get_upper() - 40:
            GLib.idle_add(scroll_bottom, scrollable)

    return linenr
