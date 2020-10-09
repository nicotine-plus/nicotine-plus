# COPYRIGHT (C) 2020 Nicotine+ Team
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

import re
import sys
import time
import types
import urllib.parse
import webbrowser

from gettext import gettext as _

from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Pango

from pynicotine import slskmessages
from pynicotine.geoip.countrycodes import code2name
from pynicotine.gtkgui.dialogs import entry_dialog
from pynicotine.logfacility import log
from pynicotine.utils import execute_command


DECIMALSEP = ""

URL_RE = re.compile("(\\w+\\://[^\\s]+)|(www\\.\\w+\\.\\w+.*?)|(mailto\\:[^\\s]+)")
PROTOCOL_HANDLERS = {}
CATCH_URLS = 0
HUMANIZE_URLS = 0
USERNAMEHOTSPOTS = 0
NICOTINE = None


# we could move this into a new class
previouscountrypath = None


def show_country_tooltip(widget, x, y, tooltip, sourcecolumn, stripprefix='flag_'):

    global previouscountrypath
    try:
        # the returned path of widget.get_path_at_pos is not correct since
        # this function pretends there's no header!
        # This also means we cannot look up the column for the very last user in the list
        # since the y is too big.
        # Therefore we'll use a y-value of 0 on all lookups
        (incorrectpath, column, cx, cy) = widget.get_path_at_pos(x, 0)

        # The return path of this func is okay, but it doesn't return the column -_-
        (path, droppos) = widget.get_dest_row_at_pos(x, y)
    except TypeError:
        # Either function returned None
        return False

    # If the mouse is pointing at a new path destroy the tooltip so it can be recreated next time
    if path != previouscountrypath:
        previouscountrypath = path
        return False

    title = column.get_title()

    if title != _("Country"):
        return False

    model = widget.get_model()
    iterator = model.get_iter(path)
    value = model.get_value(iterator, sourcecolumn)

    # Avoid throwing an error in there's no flag
    if value is None:
        return False

    if not value.startswith(stripprefix):
        tooltip.set_text(_("Unknown"))
        return True

    value = value[len(stripprefix):]
    if value:
        countryname = code2name(value)
    else:
        countryname = "Earth"

    if countryname:
        countryname = _(countryname)
    else:
        countryname = _("Unknown (%(countrycode)s)") % {'countrycode': value}

    tooltip.set_text(countryname)

    return True


def fill_file_grouping_combobox(combobox):
    grouplist = Gtk.ListStore(str)
    groups = [
        "No grouping",
        "Group by folder",
        "Group by user",
    ]

    for group in groups:
        grouplist.append([group])

    combobox.set_model(grouplist)
    renderer_text = Gtk.CellRendererText()
    combobox.pack_start(renderer_text, True)
    combobox.add_attribute(renderer_text, "text", 0)


def select_user_row_iter(fmodel, sel, user_index, selected_user, iterator):
    while iterator is not None:
        user = fmodel.get_value(iterator, user_index)

        if selected_user == user:
            sel.select_path(fmodel.get_path(iterator),)

        child = fmodel.iter_children(iterator)

        select_user_row_iter(fmodel, sel, user_index, selected_user, child)

        iterator = fmodel.iter_next(iterator)


def collapse_treeview(treeview, groupingmode):
    treeview.collapse_all()

    if groupingmode == 1:
        # Group by folder

        model = treeview.get_model()
        iterator = model.get_iter_first()

        while iterator is not None:
            path = model.get_path(iterator)
            treeview.expand_to_path(path)
            iterator = model.iter_next(iterator)


def initialise_columns(treeview, *args):

    i = 0
    cols = []

    for c in args:

        if c[2] == "text":
            renderer = Gtk.CellRendererText()
            renderer.set_padding(10, 3)

            column = Gtk.TreeViewColumn(c[0], renderer, text=i)
        elif c[2] == "center":
            renderer = Gtk.CellRendererText()
            renderer.set_property("xalign", 0.5)

            column = Gtk.TreeViewColumn(c[0], renderer, text=i)
        elif c[2] == "number":
            renderer = Gtk.CellRendererText()
            renderer.set_property("xalign", 0.9)

            column = Gtk.TreeViewColumn(c[0], renderer, text=i)
            column.set_alignment(0.9)
        elif c[2] == "edit":
            renderer = Gtk.CellRendererText()
            renderer.set_padding(10, 3)
            renderer.set_property('editable', True)
            column = Gtk.TreeViewColumn(c[0], renderer, text=i)
        elif c[2] == "combo":
            renderer = Gtk.CellRendererCombo()
            renderer.set_padding(10, 3)
            renderer.set_property('text-column', 0)
            renderer.set_property('editable', True)
            column = Gtk.TreeViewColumn(c[0], renderer, text=i)
        elif c[2] == "progress":
            renderer = Gtk.CellRendererProgress()
            column = Gtk.TreeViewColumn(c[0], renderer, value=i)
        elif c[2] == "toggle":
            renderer = Gtk.CellRendererToggle()
            column = Gtk.TreeViewColumn(c[0], renderer, active=i)
            renderer.set_property("xalign", 0.5)
        else:
            renderer = Gtk.CellRendererPixbuf()
            column = Gtk.TreeViewColumn(c[0], renderer, pixbuf=i)

        if c[1] == -1:
            column.set_resizable(False)
            column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        else:
            column.set_resizable(True)
            if c[1] == 0:
                column.set_sizing(Gtk.TreeViewColumnSizing.GROW_ONLY)
            else:
                column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
                column.set_fixed_width(c[1])
            column.set_min_width(0)

        if len(c) > 3 and not isinstance(c[3], list):
            column.set_cell_data_func(renderer, c[3])

        if len(c) > 4:
            foreground = c[4][0]
            background = c[4][1]

            if foreground == "":
                foreground = None

            if background == "":
                background = None

            renderer.set_property("foreground", foreground)
            renderer.set_property("background", background)

        column.set_reorderable(False)
        column.set_widget(Gtk.Label.new(c[0]))
        column.get_widget().set_margin_start(6)
        column.get_widget().show()

        treeview.append_column(column)

        cols.append(column)

        i += 1

    return cols


def hide_columns(cols, visibility_list):
    try:
        for i in range(len(cols)):

            parent = cols[i].get_widget().get_ancestor(Gtk.Button)
            if parent:
                parent.connect('button_press_event', press_header)

            # Read Show / Hide column settings from last session
            cols[i].set_visible(visibility_list[i])

        # Make sure the width of the last visible column isn't fixed
        for i in reversed(range(len(cols))):

            if cols[i].get_visible():
                column = cols[i]
                column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
                column.set_resizable(False)
                column.set_fixed_width(-1)
                break

    except IndexError:
        # Column count in config is probably incorrect (outdated?), don't crash
        pass


def press_header(widget, event):
    if event.button != 3:
        return False

    columns = widget.get_parent().get_columns()
    visible_columns = [column for column in columns if column.get_visible()]
    one_visible_column = len(visible_columns) == 1
    menu = Gtk.Menu()
    pos = 1

    for column in columns:
        title = column.get_title()

        if title == "":
            title = _("Column #%i") % pos

        item = Gtk.CheckMenuItem(title)

        if column in visible_columns:
            item.set_active(True)
            if one_visible_column:
                item.set_sensitive(False)
        else:
            item.set_active(False)

        item.connect('activate', header_toggle, columns, pos - 1)
        menu.append(item)
        pos += 1

    menu.show_all()
    menu.attach_to_widget(widget.get_toplevel(), None)
    menu.popup(None, None, None, None, event.button, event.time)

    return True


def header_toggle(menuitem, columns, index):
    column = columns[index]
    column.set_visible(not column.get_visible())

    # Make sure the width of the last visible column isn't fixed
    for i in reversed(range(len(columns))):

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

    prev_column = columns[index - 1]
    prev_column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
    prev_column.set_resizable(True)

    NICOTINE.SaveColumns()


def set_treeview_selected_row(treeview, event):
    """Handles row selection when right-clicking in a treeview"""

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
    if protocol in PROTOCOL_HANDLERS:
        if isinstance(PROTOCOL_HANDLERS[protocol], types.MethodType):
            PROTOCOL_HANDLERS[protocol](uri.strip())
            return
        if PROTOCOL_HANDLERS[protocol]:
            try:
                execute_command(PROTOCOL_HANDLERS[protocol], uri)
                return
            except RuntimeError as e:
                log.add_warning("%s", e)

    # Situation 2, user did not define a way of handling the protocol
    if sys.platform == "win32" and webbrowser:
        webbrowser.open(uri)
        return

    try:
        Gtk.show_uri_on_window(window, uri, Gdk.CURRENT_TIME)
    except AttributeError:
        screen = window.get_screen()
        Gtk.show_uri(screen, uri, Gdk.CURRENT_TIME)


def append_line(textview, line, tag=None, timestamp=None, showstamp=True, timestamp_format="%H:%M:%S", username=None, usertag=None, scroll=True):

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
        if USERNAMEHOTSPOTS and username is not None and usertag is not None:
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
    # Match first url
    match = URL_RE.search(line)
    # Highlight urls, if found and tag them
    while CATCH_URLS and match:
        start = line[:match.start()]
        _usertag(buffer, start)
        url = match.group()
        urltag = _makeurltag(buffer, url)
        line = line[match.end():]

        if url.startswith("slsk://") and HUMANIZE_URLS:
            url = urllib.parse.unquote(url)

        _append(buffer, url, urltag)
        # Match remaining url
        match = URL_RE.search(line)

    if line:
        _usertag(buffer, line)

    if scroll and bottom:
        GLib.idle_add(scroll_bottom, scrolledwindow)

    return linenr


class BuddiesComboBox:

    def __init__(self, frame, combo_box):

        self.frame = frame

        self.items = {}

        self.combobox = combo_box

        self.store = Gtk.ListStore(GObject.TYPE_STRING)
        self.combobox.set_model(self.store)
        self.combobox.set_entry_text_column(0)

        self.store.set_default_sort_func(lambda *args: -1)
        self.store.set_sort_column_id(-1, Gtk.SortType.ASCENDING)

        self.combobox.show()

    def fill(self):

        self.items.clear()
        self.store.clear()

        self.items[""] = self.store.append([""])

        for user in self.frame.np.config.sections["server"]["userlist"]:
            self.items[user[0]] = self.store.append([user[0]])

        self.store.set_sort_column_id(0, Gtk.SortType.ASCENDING)

    def append(self, item):

        if item in self.items:
            return

        self.items[item] = self.combobox.get_model().append([item])

    def remove(self, item):

        if item in self.items:
            self.combobox.get_model().remove(self.items[item])
            del self.items[item]


class ImageLabel(Gtk.Box):

    def __init__(self, label="", image=None, onclose=None, closebutton=False, angle=0, show_image=True, statusimage=None, show_status_image=False):

        Gtk.Box.__init__(self)

        self.closebutton = closebutton
        self.angle = angle
        self._show_image = show_image
        self._show_status_image = show_status_image
        self.notify = 0

        self._entered = 0
        self._pressed = 0

        self.onclose = onclose
        self.status_img = None
        self.statusimage = Gtk.Image()
        self.label = Gtk.Label()
        self.text = label

        self.set_text(self.text)

        self.label.set_angle(angle)
        self.label.show()

        if self._show_status_image:
            self.set_status_image(statusimage)
            self.statusimage.show()

        self.image = Gtk.Image()
        self.set_image(image)

        if self._show_image:
            self.image.show()

        self._pack_children()
        self._order_children()

    def _pack_children(self):
        self.set_spacing(0)

        if "box" in self.__dict__:
            for widget in self.box.get_children():
                self.box.remove(widget)

            self.remove(self.box)
            self.box.destroy()
            del self.box

        self.box = Gtk.Box()

        if self.angle in (90, -90):
            self.box.set_orientation(Gtk.Orientation.VERTICAL)
        else:
            self.angle = 0

        self.box.set_spacing(2)
        self.add(self.box)
        self.box.show()

        self.box.pack_start(self.statusimage, False, False, 0)
        self.box.pack_start(self.label, True, True, 0)
        self.box.pack_start(self.image, False, False, 0)

        if self.closebutton and self.onclose is not None:
            self._add_close_button()

    def _order_children(self):

        if self.angle == 90:
            if "button" in self.__dict__ and self.closebutton != 0:
                self.box.reorder_child(self.button, 0)
                self.box.reorder_child(self.image, 1)
                self.box.reorder_child(self.label, 2)
                self.box.reorder_child(self.statusimage, 3)
            else:
                self.box.reorder_child(self.image, 0)
                self.box.reorder_child(self.label, 1)
                self.box.reorder_child(self.statusimage, 2)
        else:
            self.box.reorder_child(self.statusimage, 0)
            self.box.reorder_child(self.label, 1)
            self.box.reorder_child(self.image, 2)

            if "button" in self.__dict__ and self.closebutton != 0:
                self.box.reorder_child(self.button, 3)

    def set_onclose(self, closebutton):
        self.closebutton = closebutton

        if self.closebutton:
            self._add_close_button()
        else:
            self._remove_close_button()

        self._order_children()

    def show_image(self, show=True):
        self._show_image = show

        if self._show_image:
            self.image.show()
        else:
            self.image.hide()

    def set_angle(self, angle):
        self.angle = angle
        self.label.set_angle(self.angle)
        self._remove_close_button()

        self._pack_children()
        self._order_children()

    def _add_close_button(self):
        if "button" in self.__dict__:
            return

        self.button = Gtk.Button()
        img = Gtk.Image()
        img.set_from_icon_name("window-close-symbolic", Gtk.IconSize.MENU)
        self.button.add(img)

        if self.onclose is not None:
            self.button.connect("clicked", self.onclose)

        self.button.set_relief(Gtk.ReliefStyle.NONE)

        self.button.show_all()
        self.box.pack_start(self.button, False, False, 0)

    def _remove_close_button(self):
        if "button" not in self.__dict__:
            return

        self.box.remove(self.button)
        self.button.destroy()
        del self.button

    def set_text_color(self, notify=None, text=None):
        if notify is None:
            notify = self.notify
        else:
            self.notify = notify

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
            self.label.set_markup("<span foreground=\"%s\">%s</span>" % (color, self.text.replace("<", "&lt;").replace(">", "&gt;").replace("&", "&amp;")))

    def set_image(self, img):
        self.img = img
        self.image.set_from_pixbuf(img)

    def get_image(self):
        return self.img

    def set_status_image(self, img):
        if img is self.status_img:
            return

        if NICOTINE:
            if NICOTINE.np.config.sections["ui"]["tab_status_icons"]:
                self.statusimage.show()
            else:
                self.statusimage.hide()

        self.status_img = img
        self.statusimage.set_from_pixbuf(img)

    def get_status_image(self):
        return self.status_img

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

    def __init__(self, images, angle=0, tabclosers=False, show_image=True, reorderable=True, show_status_image=False, notebookraw=None):

        # We store the real Gtk.Notebook object
        self.notebook = notebookraw
        self.notebook.set_show_border(True)

        self.tabclosers = tabclosers
        self.reorderable = reorderable

        self.images = images
        self._show_image = show_image
        self._show_status_image = show_status_image

        self.pages = []

        self.notebook.connect("switch-page", self.dismiss_icon)
        self.notebook.connect("key_press_event", self.on_key_press)

        self.angle = angle

    def set_reorderable(self, reorderable):

        self.reorderable = reorderable

        for data in self.pages:
            page, label_tab, status, label_tab_menu = data
            try:
                self.notebook.set_tab_reorderable(page, self.reorderable)
            except Exception:
                pass

    def set_tab_closers(self, closers):

        self.tabclosers = closers

        for data in self.pages:
            page, label_tab, status, label_tab_menu = data
            label_tab.set_onclose(self.tabclosers)

    def show_images(self, show_image=True):

        self._show_image = show_image

        for data in self.pages:
            page, label_tab, status, label_tab_menu = data
            label_tab.show_image(self._show_image)

    def set_tab_angle(self, angle):

        if angle == self.angle:
            return

        self.angle = angle

        for data in self.pages:
            page, label_tab, status, label_tab_menu = data
            label_tab.set_angle(angle)

    def set_tab_pos(self, pos):
        self.notebook.set_tab_pos(pos)

    def on_key_press(self, widget, event):

        if event.state & (Gdk.ModifierType.MOD1_MASK | Gdk.ModifierType.CONTROL_MASK) != Gdk.ModifierType.MOD1_MASK:
            return False

        if event.keyval in [Gdk.keyval_from_name("Up"), Gdk.keyval_from_name("Left")]:
            self.prev_page()
        elif event.keyval in [Gdk.keyval_from_name("Down"), Gdk.keyval_from_name("Right")]:
            self.next_page()
        else:
            return False

        widget.stop_emission_by_name("key_press_event")

        return True

    def append_page(self, page, label, onclose=None, angle=0, fulltext=None):

        self.set_tab_angle(angle)
        closebutton = self.tabclosers

        label_tab = ImageLabel(
            label, self.images["empty"], onclose, closebutton=closebutton,
            angle=angle, show_image=self._show_image, statusimage=None,
            show_status_image=self._show_status_image
        )

        if fulltext is None:
            fulltext = label

        label_tab.set_tooltip_text(fulltext)

        # menu for all tabs
        label_tab_menu = ImageLabel(label, self.images["empty"])

        self.pages.append([page, label_tab, 0, label_tab_menu])

        eventbox = Gtk.EventBox()
        eventbox.set_visible_window(False)

        label_tab.show()

        eventbox.add(label_tab)
        eventbox.show()
        eventbox.set_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        eventbox.connect('button_press_event', self.on_tab_click, page)

        Gtk.Notebook.append_page_menu(self.notebook, page, eventbox, label_tab_menu)

        self.notebook.set_tab_reorderable(page, self.reorderable)
        self.notebook.set_show_tabs(True)

    def remove_page(self, page):

        for i in self.pages[:]:
            if i[0] == page:
                Gtk.Notebook.remove_page(self.notebook, self.page_num(page))
                i[1].destroy()
                i[3].destroy()
                self.pages.remove(i)

                break

        if self.notebook.get_n_pages() == 0:
            self.notebook.set_show_tabs(False)

    def on_focused(self, item):
        self.frame.notifications.clear_page(self, item)

    def on_tab_click(self, widget, event, child):
        # Dummy implementation
        pass

    def set_status_image(self, page, status):

        image = self.images[("offline", "away", "online")[status]]

        for i in self.pages:
            if page == i[0]:
                i[1].set_status_image(image)
                i[3].set_status_image(image)
                return

    def set_image(self, page, status):

        image = self.images[("empty", "hilite3", "hilite")[status]]

        for i in self.pages:
            if page == i[0]:

                if status == 1 and i[2] == 2:
                    return

                if i[2] != status:
                    i[1].set_image(image)
                    i[3].set_image(image)
                    i[2] = status

                return

    def set_text(self, page, label):

        for i in self.pages:
            if i[0] == page:
                i[1].set_text(label)
                i[3].set_text(label)
                return

    def set_text_colors(self, color=None):

        for i in self.pages:
            i[1].set_text_color(color)

    def set_text_color(self, page, color=None):

        for i in self.pages:
            if i[0] == page:
                i[1].set_text_color(color)
                return

    def dismiss_icon(self, notebook, page, page_num):

        self.set_image(page, 0)
        self.set_text_color(page, 0)

    def request_hilite(self, page):

        current = self.get_nth_page(self.get_current_page())
        if current == page:
            return

        self.set_image(page, 2)
        self.set_text_color(page, 2)

    def request_changed(self, page):

        current = self.get_nth_page(self.get_current_page())
        if current == page:
            return

        self.set_image(page, 1)
        self.set_text_color(page, 1)

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


class PopupMenu(Gtk.Menu):

    def __init__(self, frame=None, shouldattach=True):

        Gtk.Menu.__init__(self)

        self.frame = frame
        self.user = None
        self.useritem = None
        self.handlers = {}
        self.editing = False

        # If the menu is not a submenu, it needs to be attached
        # to the main window, otherwise it has no parent
        if shouldattach and hasattr(self.frame, 'MainWindow'):
            self.attach_to_widget(self.frame.MainWindow, None)

    def setup(self, *items):

        for item in items:

            if item[0] == "":
                menuitem = Gtk.SeparatorMenuItem()

            elif item[0] == "USER":

                menuitem = Gtk.MenuItem.new_with_label(item[1])
                self.useritem = menuitem

                if len(item) >= 3:
                    self.handlers[menuitem] = menuitem.connect("activate", item[2])
                else:
                    menuitem.set_sensitive(False)

            elif item[0] == 1:

                menuitem = Gtk.MenuItem.new_with_label(item[1])
                menuitem.set_submenu(item[2])

                if len(item) == 5 and item[4] is not None and item[3] is not None:
                    self.handlers[menuitem] = menuitem.connect("activate", item[3], item[4])
                elif item[3] is not None:
                    self.handlers[menuitem] = menuitem.connect("activate", item[3])

            elif item[0] == "USERMENU":

                menuitem = Gtk.MenuItem.new_with_label(item[1])
                menuitem.set_submenu(item[2])

                if item[3] is not None:
                    self.handlers[menuitem] = menuitem.connect("activate", item[3])

                self.useritem = menuitem

            else:

                if item[0][0] == "$":
                    menuitem = Gtk.CheckMenuItem.new_with_label(item[0][1:])
                elif item[0][0] == "#":
                    menuitem = Gtk.MenuItem.new_with_label(item[0][1:])
                else:
                    menuitem = Gtk.MenuItem.new_with_label(item[0])

                if len(item) >= 3 and item[2] is not None and item[1] is not None:
                    self.handlers[menuitem] = menuitem.connect("activate", item[1], item[2])
                elif item[1] is not None:
                    self.handlers[menuitem] = menuitem.connect("activate", item[1])

            self.append(menuitem)

            if item[0] != "":
                menuitem.set_use_underline(True)

            menuitem.show()

        return self

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

    def set_user(self, user):
        self.user = user
        if self.useritem:
            self.useritem.get_child().set_text(user)

    def get_user(self):
        return self.user

    def on_search_user(self, widget):
        self.frame.SearchMethod.set_active_iter(self.frame.searchmethods[_("User")])
        self.frame.UserSearchCombo.get_child().set_text(self.user)
        self.frame.change_main_page(None, "search")

    def on_send_message(self, widget):
        self.frame.privatechats.send_message(self.user, None, 1)
        self.frame.change_main_page(None, "private")

    def on_show_ip_address(self, widget):

        if self.user not in self.frame.np.ip_requested:
            self.frame.np.ip_requested.append(self.user)

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

    def on_give_privileges(self, widget):

        self.frame.np.queue.put(slskmessages.CheckPrivileges())

        if self.frame.np.privileges_left is None:
            days = _("Unknown")
        else:
            days = self.frame.np.privileges_left // 60 // 60 // 24

        text = entry_dialog(
            self.frame.MainWindow,
            _("Give privileges") + " " + _("to %(user)s") % {"user": self.user},
            _("Give how many days of global privileges to this user?") + " (" + _("%(days)s days left") % {'days': days} + ")"
        )

        if text:
            try:
                days = int(text)
                self.frame.np.queue.put(slskmessages.GivePrivileges(self.user, days))
            except Exception as e:
                log.add_warning("%s", e)

    def on_private_rooms(self, widget, popup):

        if self.user is None or self.user == self.frame.np.config.sections["server"]["login"]:
            return False

        items = []
        popup.clear()
        popup.set_user(self.user)

        for room in self.frame.chatrooms.roomsctrl.private_rooms:

            if not (self.frame.chatrooms.roomsctrl.is_private_room_owned(room) or self.frame.chatrooms.roomsctrl.is_private_room_operator(room)):
                continue

            if self.user in self.frame.chatrooms.roomsctrl.private_rooms[room]["users"]:
                items.append(("#" + _("Remove from private room %s") % room, popup.on_private_room_remove_user, room))
            else:
                items.append(("#" + _("Add to private room %s") % room, popup.on_private_room_add_user, room))

            if self.frame.chatrooms.roomsctrl.is_private_room_owned(room):

                if self.user in self.frame.chatrooms.roomsctrl.private_rooms[room]["operators"]:
                    items.append(("#" + _("Remove as operator of %s") % room, popup.on_private_room_remove_operator, room))
                else:
                    items.append(("#" + _("Add as operator of %s") % room, popup.on_private_room_add_operator, room))

        popup.setup(*items)

        return True


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

    def on_search_changed(self, widget):

        buffer = self.textview.get_buffer()
        start, end = buffer.get_bounds()
        query = self.entry.get_text()

        self.textview.emit("select-all", False)

        iterator = start
        match = iterator.forward_search(query, Gtk.TextSearchFlags.TEXT_ONLY | Gtk.TextSearchFlags.CASE_INSENSITIVE, limit=None)

        if match is not None and len(match) == 2:
            match_start, match_end = match
            buffer.place_cursor(match_end)
            buffer.select_range(match_end, match_start)
            self.textview.scroll_to_iter(match_start, 0, False, 0.5, 0.5)

    def on_search_previous_match(self, widget):

        buffer = self.textview.get_buffer()
        query = self.entry.get_text()

        self.textview.emit("select-all", False)

        current = buffer.get_mark("insert")
        iterator = buffer.get_iter_at_mark(current)
        match = iterator.backward_search(query, Gtk.TextSearchFlags.TEXT_ONLY | Gtk.TextSearchFlags.CASE_INSENSITIVE, limit=None)

        if match is not None and len(match) == 2:
            match_start, match_end = match
            buffer.place_cursor(match_start)
            buffer.select_range(match_start, match_end)
            self.textview.scroll_to_iter(match_start, 0, False, 0.5, 0.5)
        else:
            start, end = buffer.get_bounds()
            buffer.place_cursor(end)
            self.on_search_previous_match(widget)

    def on_search_next_match(self, widget):

        buffer = self.textview.get_buffer()
        query = self.entry.get_text()

        self.textview.emit("select-all", False)

        current = buffer.get_mark("insert")
        iterator = buffer.get_iter_at_mark(current)
        match = iterator.forward_search(query, Gtk.TextSearchFlags.TEXT_ONLY | Gtk.TextSearchFlags.CASE_INSENSITIVE, limit=None)

        if match is not None and len(match) == 2:
            match_start, match_end = match
            buffer.place_cursor(match_end)
            buffer.select_range(match_end, match_start)
            self.textview.scroll_to_iter(match_start, 0, False, 0.5, 0.5)
        else:
            start, end = buffer.get_bounds()
            buffer.place_cursor(start)
            self.on_search_next_match(widget)

    def on_key_press(self, widget, event):
        key = Gdk.keyval_name(event.keyval)

        # Match against capslock + control and control
        if key in ("f", "F") and event.state in (Gdk.ModifierType.CONTROL_MASK, Gdk.ModifierType.LOCK_MASK | Gdk.ModifierType.CONTROL_MASK):
            self.show_search_bar()

    def show_search_bar(self):
        self.search_bar.set_search_mode(True)
        self.entry.grab_focus_without_selecting()


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
    fashion = DECIMALSEP
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


def is_alias(aliases, cmd):
    if not cmd:
        return False
    if cmd[0] != "/":
        return False
    cmd = cmd[1:].split(" ")
    if cmd[0] in aliases:
        return True
    return False


def expand_alias(aliases, cmd):
    output = _expand_alias(aliases, cmd)
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

    if not is_alias(aliases, cmd):
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
