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

import os
import re
import sys
import time

from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Pango

from pynicotine import slskmessages
from pynicotine.config import config
from pynicotine.logfacility import log
from pynicotine.utils import execute_command
from pynicotine.utils import get_path


URL_RE = re.compile("(\\w+\\://[^\\s]+)|(www\\.\\w+\\.\\w+.*?)|(mailto\\:[^\\s]+)")
NICOTINE = None


def load_ui_elements(ui_class, filename):

    try:
        builder = Gtk.Builder()
        builder.set_translation_domain('nicotine')
        builder.add_from_file(filename)

        for obj in builder.get_objects():
            try:
                obj_name = Gtk.Buildable.get_name(obj)

                if not obj_name.startswith("_"):
                    setattr(ui_class, obj_name, obj)

            except TypeError:
                pass

        builder.connect_signals(ui_class)

    except Exception as e:
        log.add(_("Failed to load ui file %(file)s: %(error)s"), {
            "file": filename,
            "error": e
        })
        sys.exit()


def open_file_path(file_path, command=None):
    """ Currently used to either open a folder or play an audio file
    Tries to run a user-specified command first, and falls back to
    the system default. """

    try:
        file_path = os.path.normpath(file_path)

        if command and "$" in command:
            execute_command(command, file_path)

        elif sys.platform == "win32":
            os.startfile(file_path)

        elif sys.platform == "darwin":
            execute_command("open $", file_path)

        else:
            Gio.AppInfo.launch_default_for_uri("file:///" + file_path.lstrip("/"))

    except Exception as error:
        log.add(_("Failed to open file path: %s"), str(error))


def open_log(folder, filename):
    _handle_log(folder, filename, open_log_callback)


def delete_log(folder, filename):
    _handle_log(folder, filename, delete_log_callback)


def _handle_log(folder, filename, callback):

    try:
        if not os.path.isdir(folder):
            os.makedirs(folder)

        filename = filename.replace(os.sep, "-") + ".log"
        get_path(folder, filename, callback)

    except Exception as e:
        log.add("Failed to process log file: %s", e)


def open_log_callback(path, data):

    if not os.path.exists(path):
        with open(path, "w"):
            # No logs, create empty file
            pass

    open_file_path(path)


def delete_log_callback(path, data):

    with open(path, "w"):
        # Check if path should contain special characters
        pass

    os.remove(path)


def open_uri(uri, window):
    """Open a URI in an external (web) browser. The given argument has
    to be a properly formed URI including the scheme (fe. HTTP).
    As of now failures will be silently discarded."""

    # Situation 1, user defined a way of handling the protocol
    protocol = uri[:uri.find(":")]
    protocol_handlers = config.sections["urls"]["protocols"]

    if protocol in protocol_handlers and protocol_handlers[protocol]:
        try:
            execute_command(protocol_handlers[protocol], uri)
            return
        except RuntimeError as e:
            log.add("%s", e)

    if protocol == "slsk":
        on_soul_seek_uri(uri.strip())
        return

    # Situation 2, user did not define a way of handling the protocol
    try:
        if sys.platform == "win32":
            os.startfile(uri)

        elif sys.platform == "darwin":
            execute_command("open $", uri)

        else:
            Gio.AppInfo.launch_default_for_uri(uri)

    except Exception as error:
        log.add(_("Failed to open URL: %s"), str(error))


def on_soul_seek_uri(url):
    import urllib.parse

    try:
        user, file = urllib.parse.unquote(url[7:]).split("/", 1)

        if file[-1] == "/":
            NICOTINE.np.send_message_to_peer(user, slskmessages.FolderContentsRequest(None, file[:-1].replace("/", "\\")))
        else:
            NICOTINE.np.transfers.get_file(user, file.replace("/", "\\"), "")

        NICOTINE.change_main_page("downloads")

    except Exception:
        log.add(_("Invalid SoulSeek meta-url: %s"), url)


def scroll_bottom(widget):

    try:
        adjustment = widget.get_vadjustment()
        adjustment.set_value(adjustment.get_upper() - adjustment.get_page_size())

    except AttributeError:
        # Nicotine+ is exiting
        pass


def url_event(tag, widget, event, iterator, url):

    if tag.last_event_type == Gdk.EventType.BUTTON_PRESS and event.button.type == Gdk.EventType.BUTTON_RELEASE and event.button.button == 1:
        if url[:4] == "www.":
            url = "http://" + url
        open_uri(url, widget.get_toplevel())

    tag.last_event_type = event.button.type


def append_line(textview, line, tag=None, timestamp=None, showstamp=True, timestamp_format="%H:%M:%S", username=None, usertag=None, scroll=True, find_urls=True):

    def _makeurltag(buffer, url):

        color = config.sections["ui"]["urlcolor"] or None
        tag = buffer.create_tag(foreground=color, underline=Pango.Underline.SINGLE)
        tag.last_event_type = -1
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


""" Clipboard """


def copy_all_text(textview, clipboard):

    textbuffer = textview.get_buffer()
    start, end = textbuffer.get_bounds()
    text = textbuffer.get_text(start, end, True)

    clipboard.set_text(text, -1)


def copy_file_url(user, path, clipboard):

    import urllib.parse
    url = "slsk://" + urllib.parse.quote(
        "%s/%s" % (user, path.replace("\\", "/"))
    )

    clipboard.set_text(url, -1)


""" Chat """


def auto_replace(message):

    if config.sections["words"]["replacewords"]:
        autoreplaced = config.sections["words"]["autoreplaced"]

        for word, replacement in autoreplaced.items():
            message = message.replace(str(word), str(replacement))

    return message


def censor_chat(message):

    if config.sections["words"]["censorwords"]:
        filler = config.sections["words"]["censorfill"]
        censored = config.sections["words"]["censored"]

        for word in censored:
            word = str(word)
            message = message.replace(word, filler * len(word))

    return message


""" Events """


event_touch_started = False
event_time_prev = 0


def triggers_context_menu(event):
    """ Check if a context menu should be allowed to appear """

    global event_touch_started
    global event_time_prev

    if event.type in (Gdk.EventType.KEY_PRESS, Gdk.EventType.KEY_RELEASE):
        return True

    elif event.type in (Gdk.EventType.BUTTON_PRESS, Gdk.EventType._2BUTTON_PRESS,
                        Gdk.EventType._3BUTTON_PRESS, Gdk.EventType.BUTTON_RELEASE):
        return event.triggers_context_menu()

    elif event.type == Gdk.EventType.TOUCH_BEGIN:
        event_touch_started = True
        event_time_prev = event.time
        return False

    elif not event_touch_started and event.type == Gdk.EventType.TOUCH_END or \
            event_touch_started and (event.time - event_time_prev) < 300:
        # Require a 300 ms press before context menu can be revealed
        event_time_prev = event.time
        return False

    event_touch_started = False
    return True


def connect_context_menu_event(widget, callback_press, callback_popup):

    widget.connect("button-press-event", callback_press)
    widget.connect("popup-menu", callback_popup)
    widget.connect("touch-event", callback_press)


def connect_key_press_event(widget, callback):
    """ Use event controller or legacy 'key-press-event', depending on GTK version """

    try:
        controller = Gtk.EventControllerKey.new(widget)
        controller.connect("key-pressed", callback)

    except AttributeError:
        # GTK <3.24
        controller = None
        widget.connect("key-press-event", callback)

    return controller


def get_key_press_event_args(*args):

    try:
        controller, keyval, keycode, state = args

    except ValueError:
        # GTK <3.24
        widget, event = args
        keyval = event.keyval
        state = event.state

    return (keyval, keycode, state)
