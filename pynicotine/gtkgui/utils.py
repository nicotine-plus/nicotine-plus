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
import sys

from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import Gtk

from pynicotine.config import config
from pynicotine.logfacility import log
from pynicotine.utils import execute_command
from pynicotine.utils import get_path


NICOTINE = None


def load_ui_elements(ui_class, filename):

    try:
        with open(filename, "r", encoding="utf-8") as f:
            if Gtk.get_major_version() == 4:
                builder = Gtk.Builder(ui_class)
                builder.add_from_string(
                    f.read()
                    .replace("GtkRadioButton", "GtkCheckButton")
                )
                Gtk.Buildable.get_name = Gtk.Buildable.get_buildable_id
            else:
                builder = Gtk.Builder()
                builder.add_from_string(
                    f.read()
                    .replace("<child type=\"center\">", "<child>")
                    .replace("<child type=\"end\">", "<child>")
                    .replace("<property name=\"focusable\">0</property>",
                             "<property name=\"can-focus\">0</property>")
                )
                builder.connect_signals(ui_class)

        for obj in builder.get_objects():
            try:
                obj_name = Gtk.Buildable.get_name(obj)

                if not obj_name.startswith("_"):
                    setattr(ui_class, obj_name, obj)

            except TypeError:
                pass

    except Exception as e:
        log.add(_("Failed to load ui file %(file)s: %(error)s"), {
            "file": filename,
            "error": e
        })
        sys.exit()


def grab_widget_focus(widget):
    """ Workaround for GTK 4 where a direct call to Gtk.Widget.grab_focus in GLib.idle_add
    results in endless focus grab attempts and 100% CPU usage """

    widget.grab_focus()


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
            NICOTINE.np.transfers.get_folder(user, file[:-1].replace("/", "\\"))
        else:
            NICOTINE.np.transfers.get_file(user, file.replace("/", "\\"), "")

        NICOTINE.change_main_page("downloads")

    except Exception:
        log.add(_("Invalid SoulSeek meta-url: %s"), url)


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


""" Events """


def connect_key_press_event(widget, callback):
    """ Use event controller or legacy 'key-press-event', depending on GTK version """

    if Gtk.get_major_version() == 4:
        controller = Gtk.EventControllerKey()
        controller.connect("key-pressed", callback)

        widget.add_controller(controller)

    else:
        controller = None
        widget.connect("key-press-event", callback)

    return controller


def get_key_press_event_args(*args):

    if Gtk.get_major_version() == 4:
        controller, keyval, keycode, state = args
        widget = controller.get_widget()

    else:
        widget, event = args
        keyval = event.keyval
        keycode = event.hardware_keycode
        state = event.state

    return (keyval, keycode, state, widget)


def parse_accelerator(accelerator):

    keys = keycodes = []
    *args, key, mods = Gtk.accelerator_parse(accelerator)

    if not key:
        return keycodes, mods

    if Gtk.get_major_version() == 4:
        valid, keys = Gdk.Display.get_default().map_keyval(key)
    else:
        keymap = Gdk.Keymap.get_for_display(Gdk.Display.get_default())
        valid, keys = keymap.get_entries_for_keyval(key)

    keycodes = [key.keycode for key in keys]
    return keycodes, mods
