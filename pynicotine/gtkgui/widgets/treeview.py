# COPYRIGHT (C) 2020-2021 Nicotine+ Team
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2008-2009 Quinox <quinox@users.sf.net>
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

import random
import string
import sys

from collections import OrderedDict

from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk

from pynicotine.config import config
from pynicotine.geoip.geoip import GeoIP
from pynicotine.gtkgui.widgets.popupmenu import PopupMenu


""" Treeview """


def verify_grouping_mode(mode):

    # Map legacy values
    if mode == "0":
        mode = "ungrouped"

    elif mode == "1":
        mode = "folder_grouping"

    elif mode == "2":
        mode = "user_grouping"

    # Verify mode validity
    elif mode not in ("ungrouped", "folder_grouping", "user_grouping"):
        mode = "folder_grouping"

    return mode


def create_grouping_menu(window, active_mode, callback):

    action_id = "grouping" + ''.join(random.choice(string.digits) for i in range(8))
    menu = Gio.Menu.new()

    menuitem = Gio.MenuItem.new(_("Ungrouped"), "win." + action_id + "::ungrouped")
    menu.append_item(menuitem)

    menuitem = Gio.MenuItem.new(_("Group by Folder"), "win." + action_id + "::folder_grouping")
    menu.append_item(menuitem)

    menuitem = Gio.MenuItem.new(_("Group by User"), "win." + action_id + "::user_grouping")
    menu.append_item(menuitem)

    state = GLib.Variant.new_string(verify_grouping_mode(active_mode))
    action = Gio.SimpleAction.new_stateful(action_id, GLib.VariantType.new("s"), state)
    action.connect("change-state", callback)

    window.add_action(action)
    action.change_state(state)

    return menu


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
                column_config = config.sections["columns"][treeview_name[0]][treeview_name[1]]
            except KeyError:
                column_config = config.sections["columns"][treeview_name]

            try:
                width = column_config[id]["width"]
            except Exception:
                # Invalid value
                pass

        if not isinstance(width, int):
            width = 0

        if Gtk.get_major_version() == 4:
            # GTK 4 rows need more padding to match GTK 3
            height_padding = 5
        else:
            height_padding = 3

        if type == "text":
            renderer = Gtk.CellRendererText()
            renderer.set_padding(10, height_padding)

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
            renderer.set_padding(10, height_padding)
            renderer.set_property('editable', True)
            column = Gtk.TreeViewColumn(id, renderer, text=i)

        elif type == "combo":
            renderer = Gtk.CellRendererCombo()
            renderer.set_padding(10, height_padding)
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
            column.set_expand(True)
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
        column.get_widget().set_margin_start(5)
        column.get_widget().show()

        if Gtk.get_major_version() == 4:
            """ Temporary hack to restore sorting by clicking column headers in GTK 4 """

            button = column.get_button()
            button.set_overflow(Gtk.Overflow.HIDDEN)

            gesture_click = Gtk.GestureClick()
            gesture_click.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
            gesture_click.connect("pressed", lambda controller, *args: controller.set_state(Gtk.EventSequenceState.CLAIMED))
            button.add_controller(gesture_click)

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
        parent = column.get_button()
        if parent:
            PopupMenu(widget=parent, callback=press_header)

        # Read Show / Hide column settings from last session
        if config:
            try:
                column.set_visible(config[column_id]["visible"])
            except Exception:
                # Invalid value
                pass


def save_columns(treeview_name, columns, subpage=None):
    """ Save a treeview's column widths and visibilities for the next session """

    saved_columns = {}
    column_config = config.sections["columns"]

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


def press_header(menu, widget):

    treeview = widget.get_parent()
    columns = treeview.get_columns()
    visible_columns = [column for column in columns if column.get_visible()]
    menu.clear()
    actions = menu.get_actions()
    pos = 1

    for column in columns:
        title = column.get_widget().get_text()

        if title == "":
            title = _("Column #%i") % pos

        menu.setup(
            ("$" + title, None)
        )

        actions[title].set_state(
            GLib.Variant.new_boolean(column in visible_columns)
        )

        if column in visible_columns:
            actions[title].set_enabled(len(visible_columns) > 1)

        actions[title].connect("activate", header_toggle, treeview, columns, pos - 1)
        pos += 1


def header_toggle(action, state, treeview, columns, index):

    column = columns[index]
    column.set_visible(not column.get_visible())
    set_last_column_autosize(treeview)


def set_treeview_selected_row(treeview, bin_x, bin_y):
    """ Handles row selection when right-clicking in a treeview """

    pathinfo = treeview.get_path_at_pos(bin_x, bin_y)
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


def show_tooltip(treeview, x, y, tooltip, sourcecolumn, column_titles, text_function, strip_prefix=""):

    try:
        bin_x, bin_y = treeview.convert_widget_to_bin_window_coords(x, y)
        path, column, cx, cy = treeview.get_path_at_pos(bin_x, bin_y)

    except TypeError:
        return False

    if column.get_title() not in column_titles:
        return False

    model = treeview.get_model()
    iterator = model.get_iter(path)
    column_value = model.get_value(iterator, sourcecolumn)

    # Update tooltip position
    treeview.set_tooltip_cell(tooltip, path, column, None)

    text = text_function(column_value, strip_prefix)
    if not text:
        return False

    tooltip.set_text(text)
    return True


def get_country_tooltip_text(column_value, strip_prefix):

    if not column_value.startswith(strip_prefix):
        return _("Unknown")

    column_value = column_value[len(strip_prefix):]
    if column_value:
        return GeoIP.country_code_to_name(column_value)

    return _("Earth")


def get_file_path_tooltip_text(column_value, strip_prefix):
    return column_value


def get_user_status_tooltip_text(column_value, strip_prefix):

    if column_value == 1:
        return _("Away")

    if column_value == 2:
        return _("Online")

    return _("Offline")


def show_country_tooltip(treeview, x, y, tooltip, sourcecolumn, strip_prefix='flag_'):
    return show_tooltip(treeview, x, y, tooltip, sourcecolumn, ("country",), get_country_tooltip_text, strip_prefix)


def show_file_path_tooltip(treeview, x, y, tooltip, sourcecolumn):
    return show_tooltip(treeview, x, y, tooltip, sourcecolumn, ("folder", "filename"), get_file_path_tooltip_text)


def show_user_status_tooltip(treeview, x, y, tooltip, sourcecolumn):
    return show_tooltip(treeview, x, y, tooltip, sourcecolumn, ("status",), get_user_status_tooltip_text)
