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

from collections import OrderedDict
from html import escape

from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Pango

from pynicotine import slskmessages
from pynicotine.geoip.countrycodes import code2name
from pynicotine.gtkgui.dialogs import choose_dir
from pynicotine.gtkgui.dialogs import choose_file
from pynicotine.gtkgui.dialogs import choose_image
from pynicotine.gtkgui.dialogs import entry_dialog
from pynicotine.gtkgui.dialogs import option_dialog
from pynicotine.logfacility import log
from pynicotine.utils import clean_file
from pynicotine.utils import execute_command


URL_RE = re.compile("(\\w+\\://[^\\s]+)|(www\\.\\w+\\.\\w+.*?)|(mailto\\:[^\\s]+)")
NICOTINE = None


def load_ui_elements(ui_class, filename):

    try:
        builder = Gtk.Builder()

        builder.set_translation_domain('nicotine')
        builder.add_from_file(filename)

        for i in builder.get_objects():
            try:
                obj_name = Gtk.Buildable.get_name(i)

                if not obj_name.startswith("_"):
                    ui_class.__dict__[obj_name] = i

            except TypeError:
                pass

        builder.connect_signals(ui_class)

    except Exception as e:
        log.add_warning(_("Failed to load ui file %(file)s: %(error)s"), {
            "file": filename,
            "error": e
        })
        sys.exit()


""" Treeview """


def select_user_row_iter(fmodel, sel, user_index, selected_user, iterator):
    while iterator is not None:
        user = fmodel.get_value(iterator, user_index)

        if selected_user == user:
            sel.select_path(fmodel.get_path(iterator),)

        child = fmodel.iter_children(iterator)

        select_user_row_iter(fmodel, sel, user_index, selected_user, child)

        iterator = fmodel.iter_next(iterator)


def collapse_treeview(treeview, grouping_mode):
    treeview.collapse_all()

    if grouping_mode == "folder_grouping":
        # Group by folder

        model = treeview.get_model()
        iterator = model.get_iter_first()

        while iterator is not None:
            path = model.get_path(iterator)
            treeview.expand_to_path(path)
            iterator = model.iter_next(iterator)


def initialise_columns(treeview_name, treeview, *args):

    i = 0
    cols = OrderedDict()
    column_config = None

    for (id, title, width, type, extra) in args:
        if treeview_name:
            try:
                column_config = NICOTINE.np.config.sections["columns"][treeview_name[0]][treeview_name[1]]
            except KeyError:
                column_config = NICOTINE.np.config.sections["columns"][treeview_name]

            try:
                width = column_config[id]["width"]
            except Exception:
                # Invalid value
                pass

        if not isinstance(width, int):
            width = 0

        if type == "text":
            renderer = Gtk.CellRendererText()
            renderer.set_padding(10, 3)

            column = Gtk.TreeViewColumn(id, renderer, text=i)

        elif type == "center":
            renderer = Gtk.CellRendererText()
            renderer.set_property("xalign", 0.5)

            column = Gtk.TreeViewColumn(id, renderer, text=i)

        elif type == "number":
            renderer = Gtk.CellRendererText()
            renderer.set_property("xalign", 0.9)

            column = Gtk.TreeViewColumn(id, renderer, text=i)
            column.set_alignment(0.9)

        elif type == "edit":
            renderer = Gtk.CellRendererText()
            renderer.set_padding(10, 3)
            renderer.set_property('editable', True)
            column = Gtk.TreeViewColumn(id, renderer, text=i)

        elif type == "combo":
            renderer = Gtk.CellRendererCombo()
            renderer.set_padding(10, 3)
            renderer.set_property('text-column', 0)
            renderer.set_property('editable', True)
            column = Gtk.TreeViewColumn(id, renderer, text=i)

        elif type == "progress":
            renderer = Gtk.CellRendererProgress()
            column = Gtk.TreeViewColumn(id, renderer, value=i)

        elif type == "toggle":
            renderer = Gtk.CellRendererToggle()
            column = Gtk.TreeViewColumn(id, renderer, active=i)
            renderer.set_property("xalign", 0.5)

        else:
            renderer = Gtk.CellRendererPixbuf()
            column = Gtk.TreeViewColumn(id, renderer, pixbuf=i)

        if width == -1:
            column.set_resizable(False)
            column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)

        else:
            column.set_resizable(True)
            if width == 0:
                column.set_sizing(Gtk.TreeViewColumnSizing.GROW_ONLY)
            else:
                column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
                column.set_fixed_width(width)
            column.set_min_width(0)

        if isinstance(extra, int):
            column.add_attribute(renderer, "foreground", extra)

        elif callable(extra):
            column.set_cell_data_func(renderer, extra)

        column.set_reorderable(True)
        column.set_min_width(20)

        column.set_widget(Gtk.Label.new(title))
        column.get_widget().set_margin_start(6)
        column.get_widget().show()

        cols[id] = column

        i += 1

    append_columns(treeview, cols, column_config)
    hide_columns(treeview, cols, column_config)

    treeview.connect("columns-changed", set_last_column_autosize)
    treeview.emit("columns-changed")

    return cols


def append_columns(treeview, cols, config):

    # Column order not supported in Python 3.5
    if not config or sys.version_info[:2] <= (3, 5):
        for (column_id, column) in cols.items():
            treeview.append_column(column)
        return

    # Restore column order from config
    for column_id in config:
        try:
            treeview.append_column(cols[column_id])
        except Exception:
            # Invalid column
            continue

    added_columns = treeview.get_columns()

    # If any columns were missing in the config, append them
    pos = 0
    for (column_id, column) in cols.items():
        if column not in added_columns:
            treeview.insert_column(column, pos)

        pos += 1


def set_last_column_autosize(treeview):

    columns = treeview.get_columns()
    col_count = len(columns)

    if col_count == 0:
        return

    prev_index = col_count - 1

    # Make sure the width of the last visible column isn't fixed
    for i in reversed(range(len(columns))):
        prev_index -= 1

        if columns[i].get_visible():
            column = columns[i]
            column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
            column.set_resizable(False)
            column.set_fixed_width(-1)
            break

    """ If the column we toggled the visibility of is now the last visible one,
    the previously last visible column should've resized to fit properly now,
    since it was set to AUTOSIZE. We can now set the previous column to FIXED,
    and make it resizable again. """

    prev_column = columns[prev_index]
    prev_column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
    prev_column.set_resizable(True)


def hide_columns(treeview, cols, config):

    for (column_id, column) in cols.items():
        parent = column.get_widget().get_ancestor(Gtk.Button)
        if parent:
            parent.connect('button_press_event', press_header)
            parent.connect('touch_event', press_header)

        # Read Show / Hide column settings from last session
        if config:
            try:
                column.set_visible(config[column_id]["visible"])
            except Exception:
                # Invalid value
                pass


def save_columns(treeview_name, columns, subpage=None):

    saved_columns = {}
    column_config = NICOTINE.np.config.sections["columns"]

    for column in columns:
        title = column.get_title()
        width = column.get_width()
        visible = column.get_visible()

        """ A column width of zero should not be saved to the config.
        When a column is hidden, the correct width will be remembered during the
        run it was hidden. Subsequent runs will yield a zero width, so we
        attempt to re-use a previously saved non-zero column width instead. """
        try:
            if width <= 0:
                if not visible:
                    saved_columns[title] = {
                        "visible": visible,
                        "width": column_config[treeview_name][title]["width"]
                    }

                continue

        except KeyError:
            # No previously saved width, going with zero
            pass

        saved_columns[title] = {"visible": visible, "width": width}

    if subpage is not None:
        try:
            column_config[treeview_name]
        except KeyError:
            column_config[treeview_name] = {}

        column_config[treeview_name][subpage] = saved_columns
    else:
        column_config[treeview_name] = saved_columns


def press_header(widget, event):

    if not triggers_context_menu(event):
        return False

    treeview = widget.get_parent()
    columns = treeview.get_columns()
    visible_columns = [column for column in columns if column.get_visible()]
    one_visible_column = len(visible_columns) == 1
    menu = PopupMenu(NICOTINE)
    pos = 1

    for column in columns:
        title = column.get_widget().get_text()

        if title == "":
            title = _("Column #%i") % pos

        item = menu.append_item(("$" + title, None))

        if column in visible_columns:
            item.set_active(True)
            if one_visible_column:
                item.set_sensitive(False)
        else:
            item.set_active(False)

        item.connect('activate', header_toggle, treeview, columns, pos - 1)
        pos += 1

    menu.popup()
    return True


def header_toggle(widget, treeview, columns, index):

    column = columns[index]
    column.set_visible(not column.get_visible())
    set_last_column_autosize(treeview)


def set_treeview_selected_row(treeview, event):
    """Handles row selection when right-clicking in a treeview"""

    if event is None:
        return

    pathinfo = treeview.get_path_at_pos(event.x, event.y)
    selection = treeview.get_selection()

    if pathinfo is not None:
        path, col, cell_x, cell_y = pathinfo

        # Make sure we don't attempt to select a single row if the row is already
        # in a selection of multiple rows, otherwise the other rows will be unselected
        if selection.count_selected_rows() <= 1 or not selection.path_is_selected(path):
            treeview.grab_focus()
            treeview.set_cursor(path, col, False)
    else:
        selection.unselect_all()


def show_country_tooltip(treeview, x, y, tooltip, sourcecolumn, stripprefix='flag_'):

    try:
        bin_x, bin_y = treeview.convert_widget_to_bin_window_coords(x, y)
        path, column, cx, cy = treeview.get_path_at_pos(bin_x, bin_y)

    except TypeError:
        return False

    if column.get_title() != "country":
        return False

    model = treeview.get_model()
    iterator = model.get_iter(path)
    value = model.get_value(iterator, sourcecolumn)

    # Avoid throwing an error in there's no flag
    if value is None:
        return False

    # Update tooltip position
    treeview.set_tooltip_cell(tooltip, path, column, None)

    if not value.startswith(stripprefix):
        tooltip.set_text(_("Unknown"))
        return True

    value = value[len(stripprefix):]
    if value:
        countryname = code2name(value)
    else:
        countryname = _("Earth")

    tooltip.set_text(countryname)
    return True


def show_file_path_tooltip(treeview, x, y, tooltip, sourcecolumn):

    try:
        bin_x, bin_y = treeview.convert_widget_to_bin_window_coords(x, y)
        path, column, cx, cy = treeview.get_path_at_pos(bin_x, bin_y)

    except TypeError:
        return False

    if column.get_title() not in ("folder", "filename"):
        return False

    model = treeview.get_model()
    iterator = model.get_iter(path)
    value = model.get_value(iterator, sourcecolumn)

    if not value:
        return False

    # Update tooltip position
    treeview.set_tooltip_cell(tooltip, path, column, None)

    tooltip.set_text(value)
    return True


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
        log.add_warning(_("Failed to open file path: %s"), str(error))


def open_log(folder, filename):

    try:
        if not os.path.isdir(folder):
            os.makedirs(folder)

        path = os.path.join(folder, clean_file(filename.replace(os.sep, "-")) + ".log")

        if not os.path.exists(path):
            with open(path, "w"):
                # No logs, create empty file
                pass

        open_file_path(path)

    except Exception as e:
        log.add("Failed to open log file: %s", e)


def scroll_bottom(widget):
    va = widget.get_vadjustment()
    try:
        va.set_value(va.get_upper() - va.get_page_size())
    except AttributeError:
        pass
    widget.set_vadjustment(va)
    return False


def url_event(tag, widget, event, iterator, url):
    if tag.last_event_type == Gdk.EventType.BUTTON_PRESS and event.button.type == Gdk.EventType.BUTTON_RELEASE and event.button.button == 1:
        if url[:4] == "www.":
            url = "http://" + url
        open_uri(url, widget.get_toplevel())
    tag.last_event_type = event.button.type


def open_uri(uri, window):
    """Open a URI in an external (web) browser. The given argument has
    to be a properly formed URI including the scheme (fe. HTTP).
    As of now failures will be silently discarded."""

    # Situation 1, user defined a way of handling the protocol
    protocol = uri[:uri.find(":")]
    protocol_handlers = NICOTINE.np.config.sections["urls"]["protocols"]

    if protocol in protocol_handlers and protocol_handlers[protocol]:
        try:
            execute_command(protocol_handlers[protocol], uri)
            return
        except RuntimeError as e:
            log.add_warning("%s", e)

    if protocol == "slsk":
        on_soul_seek_uri(uri.strip())

    # Situation 2, user did not define a way of handling the protocol
    try:
        if sys.platform == "win32":
            os.startfile(uri)

        elif sys.platform == "darwin":
            execute_command("open $", uri)

        else:
            Gio.AppInfo.launch_default_for_uri(uri)

    except Exception as error:
        log.add_warning(_("Failed to open URL: %s"), str(error))


def on_soul_seek_uri(url):
    import urllib.parse

    try:
        user, file = urllib.parse.unquote(url[7:]).split("/", 1)

        if file[-1] == "/":
            NICOTINE.np.send_message_to_peer(user, slskmessages.FolderContentsRequest(None, file[:-1].replace("/", "\\")))
        else:
            NICOTINE.np.transfers.get_file(user, file.replace("/", "\\"), "")

    except Exception:
        log.add(_("Invalid SoulSeek meta-url: %s"), url)


def append_line(textview, line, tag=None, timestamp=None, showstamp=True, timestamp_format="%H:%M:%S", username=None, usertag=None, scroll=True, find_urls=True):

    if type(line) not in (type(""), type("")):
        line = str(line)  # Error messages are sometimes tuples

    def _makeurltag(buffer, url):
        props = {}

        color = NICOTINE.np.config.sections["ui"]["urlcolor"]

        if color != "":
            props["foreground"] = color

        props["underline"] = Pango.Underline.SINGLE
        tag = buffer.create_tag(**props)
        tag.last_event_type = -1
        tag.connect("event", url_event, url)
        return tag

    def _append(buffer, text, tag):
        iterator = buffer.get_end_iter()

        if tag is not None:
            buffer.insert_with_tags(iterator, text, tag)
        else:
            buffer.insert(iterator, text)

    def _usertag(buffer, section):
        # Tag usernames with popup menu creating tag, and away/online/offline colors
        if NICOTINE.np.config.sections["ui"]["usernamehotspots"] and username is not None and usertag is not None:
            np = re.compile(re.escape(str(username)))
            match = np.search(section)
            if match is not None:
                start2 = section[:match.start()]
                name = match.group()[:]
                start = section[match.end():]
                _append(buffer, start2, tag)
                _append(buffer, name, usertag)
                _append(buffer, start, tag)
            else:
                _append(buffer, section, tag)
        else:
            _append(buffer, section, tag)

    scrolledwindow = textview.get_parent()

    try:
        va = scrolledwindow.get_vadjustment()
    except AttributeError:
        # scrolledwindow may have disappeared already while Nicotine+ was shutting down
        return

    bottom = (va.get_value() + va.get_page_size()) >= va.get_upper()

    buffer = textview.get_buffer()
    text_iter_start, text_iter_end = buffer.get_bounds()
    linenr = buffer.get_line_count()

    final_timestamp = None
    ts = 0

    if showstamp and NICOTINE.np.config.sections["logging"]["timestamps"]:
        if timestamp_format and not timestamp:
            final_timestamp = time.strftime(timestamp_format)
            line = "%s %s" % (final_timestamp, line)
        elif timestamp_format and timestamp:
            final_timestamp = time.strftime(timestamp_format, time.localtime(timestamp))
            line = "%s %s" % (final_timestamp, line)

    # Ensure newlines are in the correct place
    # We want them before the content, to prevent adding an empty line at the end of the TextView
    line = line.strip("\n")
    if text_iter_end.get_offset() > 0:
        line = "\n" + line

    if final_timestamp is not None:
        ts = len("\n") + len(final_timestamp)

    # Append timestamp, if one exists, cut it from remaining line (to avoid matching against username)
    _append(buffer, line[:ts], tag)
    line = line[ts:]

    if find_urls:
        # Match first url
        match = URL_RE.search(line)
        # Highlight urls, if found and tag them
        while NICOTINE.np.config.sections["urls"]["urlcatching"] and match:
            start = line[:match.start()]
            _usertag(buffer, start)
            url = match.group()
            urltag = _makeurltag(buffer, url)
            line = line[match.end():]

            if url.startswith("slsk://") and NICOTINE.np.config.sections["urls"]["humanizeurls"]:
                import urllib.parse
                url = urllib.parse.unquote(url)

            _append(buffer, url, urltag)
            # Match remaining url
            match = URL_RE.search(line)

    if line:
        _usertag(buffer, line)

    if scroll and bottom:
        GLib.idle_add(scroll_bottom, scrolledwindow)

    return linenr


class ImageLabel(Gtk.Box):

    def __init__(self, label="", onclose=None, closebutton=False, angle=0, hilite_image=None, show_hilite_image=True, status_image=None, show_status_image=False):

        Gtk.Box.__init__(self)
        self.set_hexpand(False)

        self.closebutton = closebutton
        self.angle = angle
        self.centered = False

        self.onclose = onclose

        self.label = Gtk.Label()
        self.label.set_angle(angle)
        self.label.set_halign(Gtk.Align.START)
        self.label.set_hexpand(True)
        self.label.show()

        self.text = label
        self.set_text(self.text)

        self.status_image = Gtk.Image()
        self.status_pixbuf = None

        if show_status_image:
            self.set_status_image(status_image)
            self.status_image.show()

        self.hilite_image = Gtk.Image()
        self.hilite_pixbuf = None

        if show_hilite_image:
            self.set_hilite_image(hilite_image)

        self._pack_children()
        self._order_children()

    def _pack_children(self):

        if hasattr(self, "box"):
            for widget in self.box.get_children():
                self.box.remove(widget)

            self.eventbox.remove(self.box)

        self.eventbox = Gtk.EventBox()
        self.eventbox.show()
        self.add(self.eventbox)

        self.box = Gtk.Box()
        self.box.set_spacing(2)
        self.eventbox.add(self.box)

        if self.angle in (90, -90):
            self.set_orientation(Gtk.Orientation.VERTICAL)
        else:
            self.set_orientation(Gtk.Orientation.HORIZONTAL)

        if self.centered:
            self.set_halign(Gtk.Align.CENTER)
        else:
            self.set_halign(Gtk.Align.FILL)

        self.status_image.set_margin_end(5)
        self.hilite_image.set_margin_start(5)

        self.box.add(self.status_image)
        self.box.add(self.label)
        self.box.add(self.hilite_image)
        self.box.show()

        if self.closebutton and self.onclose is not None:
            self._add_close_button()

    def _order_children(self):

        if self.angle == 90:
            self.box.reorder_child(self.hilite_image, 0)
            self.box.reorder_child(self.label, 1)
            self.box.reorder_child(self.status_image, 2)

            if hasattr(self, "button"):
                self.reorder_child(self.button, 0)

        else:
            self.box.reorder_child(self.status_image, 0)
            self.box.reorder_child(self.label, 1)
            self.box.reorder_child(self.hilite_image, 2)

            if hasattr(self, "button"):
                self.reorder_child(self.button, 1)

    def _add_close_button(self):

        if hasattr(self, "button"):
            return

        close_image = Gtk.Image()
        close_image.set_from_icon_name("window-close-symbolic", Gtk.IconSize.MENU)

        self.button = Gtk.Button()
        self.button.add(close_image)
        self.button.set_relief(Gtk.ReliefStyle.NONE)
        self.button.show_all()

        if self.onclose is not None:
            self.button.connect("clicked", self.onclose)

        self.add(self.button)

    def _remove_close_button(self):

        if not hasattr(self, "button"):
            return

        self.remove(self.button)
        del self.button

    def set_onclose(self, closebutton):
        self.closebutton = closebutton

        if self.closebutton:
            self._add_close_button()
        else:
            self._remove_close_button()

        self._order_children()

    def show_hilite_image(self, show=True):
        if show and self.get_hilite_image() is not None:
            self.hilite_image.show()
        else:
            self.hilite_image.hide()

    def set_angle(self, angle):
        self.angle = angle
        self.label.set_angle(self.angle)
        self._remove_close_button()

        self._pack_children()
        self._order_children()

    def set_centered(self, centered):
        self.centered = centered

        self._pack_children()
        self._order_children()

    def set_text_color(self, notify=None, text=None):

        color = NICOTINE.np.config.sections["ui"]["tab_default"]

        if NICOTINE.np.config.sections["notifications"]["notification_tab_colors"]:
            if notify == 1:
                color = NICOTINE.np.config.sections["ui"]["tab_changed"]
            elif notify == 2:
                color = NICOTINE.np.config.sections["ui"]["tab_hilite"]

        try:
            rgba = Gdk.RGBA()
            rgba.parse(color)
        except Exception:
            color = ""

        if text is not None:
            self.text = text

        if not color:
            self.label.set_text("%s" % self.text)
        else:
            self.label.set_markup("<span foreground=\"%s\">%s</span>" % (color, escape(self.text)))

    def set_hilite_image(self, pixbuf):
        self.hilite_pixbuf = pixbuf
        self.hilite_image.set_from_pixbuf(pixbuf)

        self.show_hilite_image()

    def get_hilite_image(self):
        return self.hilite_pixbuf

    def set_status_image(self, pixbuf):
        if pixbuf is self.status_pixbuf:
            return

        if NICOTINE.np.config.sections["ui"]["tab_status_icons"]:
            self.status_image.show()
        else:
            self.status_image.hide()

        self.status_pixbuf = pixbuf
        self.status_image.set_from_pixbuf(pixbuf)

    def get_status_image(self):
        return self.status_pixbuf

    def set_icon(self, icon_name):
        self.status_image.set_from_icon_name(icon_name, Gtk.IconSize.BUTTON)

    def set_text(self, lbl):
        self.set_text_color(notify=None, text=lbl)

    def get_text(self):
        return self.label.get_text()


class IconNotebook:
    """ This class implements a pseudo Gtk.Notebook
    On top of what a Gtk.Notebook provides:
    - You can have icons on the notebook tab.
    - You can choose the label orientation (angle).
    """

    def __init__(self, images, angle=0, tabclosers=False, show_hilite_image=True, reorderable=True, show_status_image=False, notebookraw=None):

        # We store the real Gtk.Notebook object
        self.notebook = notebookraw
        self.notebook.set_show_border(False)

        self.tabclosers = tabclosers
        self.reorderable = reorderable

        self.images = images
        self._show_hilite_image = show_hilite_image
        self._show_status_image = show_status_image

        self.notebook.connect("key-press-event", self.on_key_press_event)
        self.notebook.connect("switch-page", self.on_switch_page)

        self.angle = angle

    def get_labels(self, page):
        tab_label = self.notebook.get_tab_label(page)
        menu_label = self.notebook.get_menu_label(page)

        return tab_label, menu_label

    def set_reorderable(self, reorderable):

        self.reorderable = reorderable

        for i in range(self.notebook.get_n_pages()):
            page = self.notebook.get_nth_page(i)
            self.notebook.set_tab_reorderable(page, self.reorderable)

    def set_tab_closers(self, closers):

        self.tabclosers = closers

        for i in range(self.notebook.get_n_pages()):
            page = self.notebook.get_nth_page(i)
            tab_label, menu_label = self.get_labels(page)

            tab_label.set_onclose(self.tabclosers)

    def show_hilite_images(self, show_image=True):

        self._show_hilite_image = show_image

        for i in range(self.notebook.get_n_pages()):
            page = self.notebook.get_nth_page(i)
            tab_label, menu_label = self.get_labels(page)

            tab_label.show_hilite_image(self._show_hilite_image)

    def show_status_images(self, show_image=True):

        self._show_status_image = show_image

    def set_tab_angle(self, angle):

        if angle == self.angle:
            return

        self.angle = angle

        for i in range(self.notebook.get_n_pages()):
            page = self.notebook.get_nth_page(i)
            tab_label, menu_label = self.get_labels(page)

            tab_label.set_angle(angle)

    def set_tab_pos(self, pos):
        self.notebook.set_tab_pos(pos)

    def append_page(self, page, label, onclose=None, angle=0, fulltext=None, status=None):

        self.set_tab_angle(angle)
        closebutton = self.tabclosers

        label_tab = ImageLabel(
            label, onclose, closebutton=closebutton, angle=angle,
            show_hilite_image=self._show_hilite_image,
            status_image=self.images["offline"],
            show_status_image=self._show_status_image
        )

        if fulltext is None:
            fulltext = label

        label_tab.set_tooltip_text(fulltext)

        # menu for all tabs
        label_tab_menu = ImageLabel(label)
        label_tab.connect('button_press_event', self.on_tab_click, page)
        label_tab.connect('popup_menu', self.on_tab_popup, page)
        label_tab.connect('touch_event', self.on_tab_click, page)
        label_tab.show()

        Gtk.Notebook.append_page_menu(self.notebook, page, label_tab, label_tab_menu)

        if status:
            self.set_user_status(page, label, status)

        self.notebook.set_tab_reorderable(page, self.reorderable)
        self.notebook.set_show_tabs(True)

    def remove_page(self, page):

        Gtk.Notebook.remove_page(self.notebook, self.page_num(page))

        if self.notebook.get_n_pages() == 0:
            self.notebook.set_show_tabs(False)

    def get_page_owner(self, page, items):

        n = self.page_num(page)
        page = self.get_nth_page(n)

        return next(owner for owner, tab in items.items() if tab.Main is page)

    def on_tab_popup(self, widget, page):
        # Dummy implementation
        pass

    def on_tab_click(self, widget, event, child):
        # Dummy implementation
        pass

    def set_status_image(self, page, status):

        tab_label, menu_label = self.get_labels(page)

        if status == 1:
            image_name = "away"
        elif status == 2:
            image_name = "online"
        else:
            image_name = "offline"

        image = self.images[image_name]

        tab_label.set_status_image(image)
        menu_label.set_status_image(image)

    def set_user_status(self, page, user, status):

        if status == 1:
            status_text = _("Away")
        elif status == 2:
            status_text = _("Online")
        else:
            status_text = _("Offline")

        if not NICOTINE.np.config.sections["ui"]["tab_status_icons"]:
            self.set_text(page, "%s (%s)" % (user[:15], status_text))
        else:
            self.set_text(page, user)

        self.set_status_image(page, status)

    def set_hilite_image(self, page, status):

        tab_label, menu_label = self.get_labels(page)
        image = None

        if status > 0:
            image = self.images[("hilite3", "hilite")[status - 1]]

        if status == 1 and tab_label.get_hilite_image() == self.images["hilite"]:
            # Chat mentions have priority over normal notifications
            return

        tab_label.set_hilite_image(image)
        menu_label.set_hilite_image(image)

    def set_text(self, page, label):

        tab_label, menu_label = self.get_labels(page)

        tab_label.set_text(label)
        menu_label.set_text(label)

    def set_text_colors(self, status):

        for i in range(self.notebook.get_n_pages()):
            page = self.notebook.get_nth_page(i)
            self.set_text_color(page, status)

    def set_text_color(self, page, status):

        tab_label, menu_label = self.get_labels(page)
        tab_label.set_text_color(status)

    def request_hilite(self, page):

        current = self.get_nth_page(self.get_current_page())
        if current == page:
            return

        self.set_hilite_image(page, status=2)
        self.set_text_color(page, status=2)

    def request_changed(self, page):

        current = self.get_nth_page(self.get_current_page())
        if current == page:
            return

        self.set_hilite_image(page, status=1)
        self.set_text_color(page, status=1)

    def get_current_page(self):
        return self.notebook.get_current_page()

    def set_current_page(self, page_num):
        return self.notebook.set_current_page(page_num)

    def get_nth_page(self, page_num):
        return self.notebook.get_nth_page(page_num)

    def page_num(self, page):
        return self.notebook.page_num(page)

    def popup_enable(self):
        self.notebook.popup_enable()

    def popup_disable(self):
        self.notebook.popup_disable()

    def show(self):
        self.notebook.show()

    def on_key_press_event(self, widget, event):

        key = Gdk.keyval_name(event.keyval)

        if event.state in (Gdk.ModifierType.CONTROL_MASK, Gdk.ModifierType.LOCK_MASK | Gdk.ModifierType.CONTROL_MASK):
            if key in ("W", "w") or key == "F4":
                # Ctrl+W and Ctrl+F4: close current tab

                page = self.get_nth_page(self.get_current_page())
                tab_label, menu_label = self.get_labels(page)
                tab_label.onclose(widget)
                return True

        return False

    def on_switch_page(self, notebook, new_page, page_num):

        # Hide widgets on previous page for a performance boost
        current_page = self.get_nth_page(self.get_current_page())

        for child in current_page.get_children():
            child.hide()

        for child in new_page.get_children():
            child.show()

        # Dismiss tab notification
        self.set_hilite_image(new_page, status=0)
        self.set_text_color(new_page, status=0)


class InfoBar:
    """ Wrapper for setting up a GtkInfoBar """

    def __init__(self, info_bar, message_type):

        self.info_bar = info_bar
        self.info_bar.set_message_type(message_type)
        self.info_bar.set_show_close_button(True)
        self.info_bar.connect("response", self._hide)

        self.set_visible(False)

    def _hide(self, *args):
        self.set_visible(False)

    def set_visible(self, visible):

        self.info_bar.set_visible(visible)

        try:
            self.info_bar.set_revealed(visible)

        except AttributeError:
            # Old GTK version
            pass

    def show_message(self, message):

        label = self.info_bar.get_content_area().get_children()[0]
        label.set_text(message)

        self.set_visible(True)


class PopupMenu(Gtk.Menu):

    def __init__(self, frame=None, shouldattach=True):

        Gtk.Menu.__init__(self)

        self.frame = frame
        self.user = None
        self.useritem = None
        self.handlers = {}
        self.items = {}
        self.editing = False

        # If the menu is not a submenu, it needs to be attached
        # to the main window, otherwise it has no parent
        if shouldattach and hasattr(self.frame, 'MainWindow'):
            self.attach_to_widget(self.frame.MainWindow, None)

    def create_item(self, item):

        if item[0] == "":
            label = "separator"
            menuitem = Gtk.SeparatorMenuItem()

        elif item[0] == "USER":

            label = item[1]
            menuitem = Gtk.MenuItem.new_with_label(label)
            self.useritem = menuitem

            if len(item) >= 3:
                self.handlers[menuitem] = menuitem.connect("activate", item[2])
            else:
                menuitem.set_sensitive(False)

        elif item[0] == 1:

            label = item[1]
            menuitem = Gtk.MenuItem.new_with_label(label)
            menuitem.set_submenu(item[2])

            if len(item) == 5 and item[4] is not None and item[3] is not None:
                self.handlers[menuitem] = menuitem.connect("activate", item[3], item[4])
            elif item[3] is not None:
                self.handlers[menuitem] = menuitem.connect("activate", item[3])

        elif item[0] == "USERMENU":

            label = item[1]
            menuitem = Gtk.MenuItem.new_with_label(label)
            menuitem.set_submenu(item[2])

            if item[3] is not None:
                self.handlers[menuitem] = menuitem.connect("activate", item[3])

            self.useritem = menuitem

        else:

            if item[0][0] == "$":
                label = item[0][1:]
                menuitem = Gtk.CheckMenuItem.new_with_label(label)

            elif item[0][0] == "#":
                label = item[0][1:]
                menuitem = Gtk.MenuItem.new_with_label(label)

            else:
                label = item[0]
                menuitem = Gtk.MenuItem.new_with_label(label)

            if len(item) >= 3 and item[2] is not None and item[1] is not None:
                self.handlers[menuitem] = menuitem.connect("activate", item[1], item[2])
            elif item[1] is not None:
                self.handlers[menuitem] = menuitem.connect("activate", item[1])

        if item[0] != "":
            menuitem.set_use_underline(True)

        menuitem.show()

        self.items[label] = menuitem
        return menuitem

    def append_item(self, item):

        menuitem = self.create_item(item)
        self.append(menuitem)

        return menuitem

    def get_items(self):
        return self.items

    def setup(self, *items):
        for item in items:
            self.append_item(item)

    def setup_user_menu(self, user=None):

        self.setup(
            ("USER", "", self.on_copy_user),
            ("", None),
            ("#" + _("Send _Message"), self.on_send_message),
            ("#" + _("Show User I_nfo"), self.on_get_user_info),
            ("#" + _("Brow_se Files"), self.on_browse_user),
            ("#" + _("Gi_ve Privileges"), self.on_give_privileges),
            ("", None),
            ("#" + _("Show IP A_ddress"), self.on_show_ip_address),
            ("#" + _("Client Version"), self.on_version),
            ("", None),
            ("$" + _("_Add User To List"), self.on_add_to_list),
            ("$" + _("_Ban User"), self.on_ban_user),
            ("$" + _("_Ignore User"), self.on_ignore_user),
            ("$" + _("B_lock User's IP Address"), self.on_block_user),
            ("$" + _("Ignore User's IP Address"), self.on_ignore_ip),
        )

        if user is not None:
            self.set_user(user)

    def toggle_user_items(self):

        self.editing = True

        self.items[_("_Add User To List")].set_active(self.user in (i[0] for i in self.frame.np.config.sections["server"]["userlist"]))
        self.items[_("_Ban User")].set_active(self.user in self.frame.np.config.sections["server"]["banlist"])
        self.items[_("_Ignore User")].set_active(self.user in self.frame.np.config.sections["server"]["ignorelist"])
        self.items[_("B_lock User's IP Address")].set_active(self.frame.user_ip_is_blocked(self.user))
        self.items[_("Ignore User's IP Address")].set_active(self.frame.user_ip_is_ignored(self.user))

        self.editing = False

    def clear(self):

        for (w, widget) in self.handlers.items():
            w.disconnect(widget)

        self.handlers.clear()

        for widget in self.get_children():
            self.remove(widget)
            widget.destroy()

        if self.useritem is not None:
            self.useritem.destroy()
            self.useritem = None

    def popup(self, button=3, use_legacy=False):

        try:
            if use_legacy:
                raise AttributeError("Falling back to legacy popup method")

            self.popup_at_pointer()

        except AttributeError:
            time = Gtk.get_current_event_time()
            Gtk.Menu.popup(self, None, None, None, None, button, time)

    def set_user(self, user):

        self.user = user

        if self.useritem:
            self.useritem.get_child().set_text(user)

    def get_user(self):
        return self.user

    def on_search_user(self, widget):
        self.frame.SearchMethod.set_active_id("user")
        self.frame.UserSearchEntry.set_text(self.user)
        self.frame.change_main_page("search")

    def on_send_message(self, widget):
        self.frame.privatechats.send_message(self.user, show_user=True)
        self.frame.change_main_page("private")

    def on_show_ip_address(self, widget):

        self.frame.np.ip_requested.add(self.user)
        self.frame.np.queue.put(slskmessages.GetPeerAddress(self.user))

    def on_get_user_info(self, widget):
        self.frame.local_user_info_request(self.user)

    def on_browse_user(self, widget):
        self.frame.browse_user(self.user)

    def on_private_room_add_user(self, widget, room):
        self.frame.np.queue.put(slskmessages.PrivateRoomAddUser(room, self.user))

    def on_private_room_remove_user(self, widget, room):
        self.frame.np.queue.put(slskmessages.PrivateRoomRemoveUser(room, self.user))

    def on_private_room_add_operator(self, widget, room):
        self.frame.np.queue.put(slskmessages.PrivateRoomAddOperator(room, self.user))

    def on_private_room_remove_operator(self, widget, room):
        self.frame.np.queue.put(slskmessages.PrivateRoomRemoveOperator(room, self.user))

    def on_add_to_list(self, widget):

        if self.editing:
            return

        if widget.get_active():
            self.frame.userlist.add_to_list(self.user)
        else:
            self.frame.userlist.remove_from_list(self.user)

    def on_ban_user(self, widget):

        if self.editing:
            return

        if widget.get_active():
            self.frame.ban_user(self.user)
        else:
            self.frame.unban_user(self.user)

    def on_block_user(self, widget):

        if self.editing:
            return

        if widget.get_active():
            self.frame.on_block_user(self.user)
        else:
            self.frame.on_un_block_user(self.user)

    def on_ignore_ip(self, widget):

        if self.editing:
            return

        if widget.get_active():
            self.frame.on_ignore_ip(self.user)
        else:
            self.frame.on_un_ignore_ip(self.user)

    def on_ignore_user(self, widget):

        if self.editing:
            return

        if widget.get_active():
            self.frame.ignore_user(self.user)
        else:
            self.frame.unignore_user(self.user)

    def on_version(self, widget):
        self.frame.privatechats.send_message(self.user, "\x01VERSION\x01", bytestring=True)

    def on_copy_user(self, widget):
        self.frame.clip.set_text(self.user, -1)

    def on_give_privileges(self, widget, error=None):

        self.frame.np.queue.put(slskmessages.CheckPrivileges())

        if self.frame.np.privileges_left is None:
            days = _("Unknown")
        else:
            days = self.frame.np.privileges_left // 60 // 60 // 24

        message = _("Give how many days of global privileges to this user?") + " (" + _("%(days)s days left") % {'days': days} + ")"

        if error:
            message += "\n\n" + error

        days = entry_dialog(
            self.frame.MainWindow,
            _("Give privileges") + " " + _("to %(user)s") % {"user": self.user},
            message
        )

        if days:
            try:
                days = int(days)
                self.frame.np.queue.put(slskmessages.GivePrivileges(self.user, days))

            except ValueError:
                self.on_give_privileges(widget, error=_("Please enter a whole number!"))

    def on_private_rooms(self, widget, popup):

        if self.user is None or self.user == self.frame.np.config.sections["server"]["login"]:
            return False

        items = []
        popup.clear()
        popup.set_user(self.user)

        for room in self.frame.chatrooms.private_rooms:

            if not self.frame.chatrooms.roomlist.is_private_room_owned(room) or \
                    self.frame.chatrooms.roomlist.is_private_room_operator(room):
                continue

            if self.user in self.frame.chatrooms.private_rooms[room]["users"]:
                items.append(("#" + _("Remove from private room %s") % room, popup.on_private_room_remove_user, room))
            else:
                items.append(("#" + _("Add to private room %s") % room, popup.on_private_room_add_user, room))

            if self.frame.chatrooms.roomlist.is_private_room_owned(room):

                if self.user in self.frame.chatrooms.private_rooms[room]["operators"]:
                    items.append(("#" + _("Remove as operator of %s") % room, popup.on_private_room_remove_operator, room))
                else:
                    items.append(("#" + _("Add as operator of %s") % room, popup.on_private_room_add_operator, room))

        popup.setup(*items)
        return True

    def on_close_all_tabs(self, widget, caller):

        option_dialog(
            parent=self.frame.MainWindow,
            title=_('Close All Tabs?'),
            message=_('Are you sure you wish to close all tabs?'),
            callback=caller.close_all_tabs
        )


class FileChooserButton:
    """ This class expands the functionality of a GtkButton to open a file
    chooser and display the name of a selected folder or file """

    def __init__(self, button, parent, chooser_type="file", selected_function=None):

        self.parent = parent
        self.button = button
        self.chooser_type = chooser_type
        self.selected_function = selected_function
        self.path = ""

        box = Gtk.Box()
        box.set_spacing(6)
        self.icon = Gtk.Image.new()

        if chooser_type == "folder":
            self.icon.set_from_icon_name("folder-symbolic", Gtk.IconSize.BUTTON)

        elif chooser_type == "image":
            self.icon.set_from_icon_name("image-x-generic-symbolic", Gtk.IconSize.BUTTON)

        else:
            self.icon.set_from_icon_name("text-x-generic-symbolic", Gtk.IconSize.BUTTON)

        self.label = Gtk.Label.new(_("(None)"))

        box.add(self.icon)
        box.add(self.label)

        self.button.add(box)
        self.button.show_all()

        self.button.connect("clicked", self.open_file_chooser)

    def open_file_chooser(self, widget):

        if self.chooser_type == "folder":
            selected = choose_dir(self.parent, self.path, multichoice=False)

        else:
            if self.path:
                folder_path = os.path.dirname(self.path)
            else:
                folder_path = ""

            if self.chooser_type == "image":
                selected = choose_image(self.parent, folder_path)
            else:
                selected = choose_file(self.parent, folder_path)

        if selected:
            self.set_path(selected[0])

            try:
                self.selected_function()

            except TypeError:
                # No fucntion defined
                return

    def get_path(self):
        return self.path

    def set_path(self, path):

        if not path:
            return

        self.path = path
        self.label.set_label(os.path.basename(path))

    def clear(self):
        self.path = ""
        self.label.set_label(_("(None)"))


""" Entry """


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

    def on_search_changed(self, widget):
        self.on_search_match(search_type="typing")

    def on_search_previous_match(self, widget):
        self.on_search_match(search_type="previous")

    def on_search_next_match(self, widget):
        self.on_search_match(search_type="next")

    def on_key_press(self, widget, event):
        key = Gdk.keyval_name(event.keyval)

        # Match against capslock + control and control
        if key in ("f", "F") and event.state in (Gdk.ModifierType.CONTROL_MASK, Gdk.ModifierType.LOCK_MASK | Gdk.ModifierType.CONTROL_MASK):
            self.show_search_bar()

    def show_search_bar(self):
        self.search_bar.set_search_mode(True)
        self.entry.grab_focus_without_selecting()


def clear_entry(entry):

    completion = entry.get_completion()
    entry.set_completion(None)
    entry.set_text("")
    entry.set_completion(completion)


size_suffixes = ['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB']


def human_size(filesize):
    try:
        step_unit = 1024.0

        for i in size_suffixes:
            if filesize < step_unit:
                return "%3.1f %s" % (filesize, i)

            filesize /= step_unit
    except TypeError:
        return filesize


speed_suffixes = ['B/s', 'KiB/s', 'MiB/s', 'GiB/s', 'TiB/s', 'PiB/s', 'EiB/s', 'ZiB/s', 'YiB/s']


def human_speed(filesize):
    try:
        step_unit = 1024.0

        for i in speed_suffixes:
            if filesize < step_unit:
                return "%3.1f %s" % (filesize, i)

            filesize /= step_unit
    except TypeError:
        return filesize


def humanize(number):

    fashion = NICOTINE.np.config.sections["ui"]["decimalsep"]

    if fashion == "" or fashion == "<None>":
        return str(number)

    elif fashion == "<space>":
        fashion = " "

    number = str(number)

    if number[0] == "-":
        neg = "-"
        number = number[1:]
    else:
        neg = ""

    ret = ""

    while number[-3:]:
        part, number = number[-3:], number[:-3]
        ret = "%s%s%s" % (part, fashion, ret)

    return neg + ret[:-1]


""" Command Aliases """


def add_alias(rest):

    aliases = NICOTINE.np.config.sections["server"]["command_aliases"]

    if rest:
        args = rest.split(" ", 1)

        if len(args) == 2:
            if args[0] in ("alias", "unalias"):
                return "I will not alias that!\n"

            aliases[args[0]] = args[1]

        if args[0] in aliases:
            return "Alias %s: %s\n" % (args[0], aliases[args[0]])
        else:
            return _("No such alias (%s)") % rest + "\n"

    else:
        m = "\n" + _("Aliases:") + "\n"

        for (key, value) in aliases.items():
            m = m + "%s: %s\n" % (key, value)

        return m + "\n"


def unalias(rest):

    aliases = NICOTINE.np.config.sections["server"]["command_aliases"]

    if rest and rest in aliases:
        x = aliases[rest]
        del aliases[rest]

        return _("Removed alias %(alias)s: %(action)s\n") % {'alias': rest, 'action': x}

    else:
        return _("No such alias (%(alias)s)\n") % {'alias': rest}


def is_alias(cmd):

    if not cmd:
        return False

    if cmd[0] != "/":
        return False

    cmd = cmd[1:].split(" ")

    if cmd[0] in NICOTINE.np.config.sections["server"]["command_aliases"]:
        return True

    return False


def expand_alias(cmd):
    output = _expand_alias(NICOTINE.np.config.sections["server"]["command_aliases"], cmd)
    return output


def _expand_alias(aliases, cmd):

    def getpart(line):
        if line[0] != "(":
            return ""
        ix = 1
        ret = ""
        level = 0
        while ix < len(line):
            if line[ix] == "(":
                level = level + 1
            if line[ix] == ")":
                if level == 0:
                    return ret
                else:
                    level = level - 1
            ret = ret + line[ix]
            ix = ix + 1
        return ""

    if not is_alias(cmd):
        return None
    try:
        cmd = cmd[1:].split(" ")
        alias = aliases[cmd[0]]
        ret = ""
        i = 0
        while i < len(alias):
            if alias[i:i + 2] == "$(":
                arg = getpart(alias[i + 1:])
                if not arg:
                    ret = ret + "$"
                    i = i + 1
                    continue
                i = i + len(arg) + 3
                args = arg.split("=", 1)
                if len(args) > 1:
                    default = args[1]
                else:
                    default = ""
                args = args[0].split(":")
                if len(args) == 1:
                    first = last = int(args[0])
                else:
                    if args[0]:
                        first = int(args[0])
                    else:
                        first = 1
                    if args[1]:
                        last = int(args[1])
                    else:
                        last = len(cmd)
                v = " ".join(cmd[first:last + 1])
                if not v:
                    v = default
                ret = ret + v
            else:
                ret = ret + alias[i]
                i = i + 1
        return ret
    except Exception as error:
        log.add_warning("%s", error)

    return ""


""" Fonts and Colors """


def parse_color_string(color_string):
    """ Take a color string, e.g. BLUE, and return a HEX color code """

    if color_string:
        color_rgba = Gdk.RGBA()

        if color_rgba.parse(color_string):
            color_hex = "#%02X%02X%02X" % (round(color_rgba.red * 255), round(color_rgba.green * 255), round(color_rgba.blue * 255))
            return color_hex

    return None


def set_list_color(listview, color):

    for c in listview.get_columns():
        for r in c.get_cells():
            if isinstance(r, (Gtk.CellRendererText, Gtk.CellRendererCombo)):
                set_widget_color(r, color)


def set_list_font(listview, font):

    for c in listview.get_columns():
        for r in c.get_cells():
            if isinstance(r, (Gtk.CellRendererText, Gtk.CellRendererCombo)):
                set_widget_font(r, font)


def set_widget_color(widget, color):

    if color:
        widget.set_property("foreground", color)
    else:
        widget.set_property("foreground-set", False)


css_providers = {}


def set_widget_fg_bg_css(widget, bg_color=None, fg_color=None):

    class_name = "widget_custom_color"
    css = "." + class_name + " {"

    bg_color_hex = parse_color_string(bg_color)
    fg_color_hex = parse_color_string(fg_color)

    if bg_color_hex is not None:
        css += "background: " + bg_color_hex + ";"

    if fg_color_hex is not None:
        css += "color: " + fg_color_hex + ";"

    css += "}"

    context = widget.get_style_context()

    if widget not in css_providers:
        css_providers[widget] = Gtk.CssProvider()
        context.add_provider(css_providers[widget], Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        context.add_class(class_name)

    css_providers[widget].load_from_data(css.encode('utf-8'))


def set_widget_font(widget, font):
    widget.set_property("font", font)


def update_widget_visuals(widget, list_font_target="listfont", update_text_tags=True):

    if isinstance(widget, Gtk.ComboBox) and widget.get_has_entry() or \
            isinstance(widget, Gtk.Entry):
        if isinstance(widget, Gtk.ComboBox):
            widget = widget.get_child()

        set_widget_fg_bg_css(
            widget,
            bg_color=NICOTINE.np.config.sections["ui"]["textbg"],
            fg_color=NICOTINE.np.config.sections["ui"]["inputcolor"]
        )

    elif update_text_tags and isinstance(widget, Gtk.TextTag):
        # Chat rooms and private chats have their own code for this

        set_widget_color(widget, NICOTINE.np.config.sections["ui"]["chatremote"])
        set_widget_font(widget, NICOTINE.np.config.sections["ui"]["chatfont"])

    elif isinstance(widget, Gtk.TreeView):
        set_list_color(widget, NICOTINE.np.config.sections["ui"]["search"])
        set_list_font(widget, NICOTINE.np.config.sections["ui"][list_font_target])


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
