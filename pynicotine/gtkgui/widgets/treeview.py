# COPYRIGHT (C) 2020-2022 Nicotine+ Contributors
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2008-2009 quinox <quinox@users.sf.net>
# COPYRIGHT (C) 2006-2009 daelstorm <daelstorm@gmail.com>
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

from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk

from pynicotine.config import config
from pynicotine.geoip import GeoIP
from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.utils import copy_text
from pynicotine.gtkgui.widgets.accelerator import Accelerator
from pynicotine.gtkgui.widgets.popupmenu import PopupMenu
from pynicotine.gtkgui.widgets.theme import FILE_TYPE_ICON_LABELS
from pynicotine.gtkgui.widgets.theme import add_css_class


""" Treeview """


class TreeView:

    def __init__(self, window, parent, columns, multi_select=False, always_select=False,
                 name=None, activate_row_callback=None, select_row_callback=None, tooltip_callback=None):

        self.window = window
        self.widget = Gtk.TreeView(visible=True)
        self.widget_name = name
        self.columns = columns
        self.model = None
        self.iterators = {}
        self._iterator_key_column = 0
        self._iter_keys = {}
        self._column_ids = {}
        self._column_numbers = None
        self._sort_column = None
        self._sort_type = None

        parent.set_property("child", self.widget)
        self.initialise_columns(columns)

        Accelerator("<Primary>c", self.widget, self.on_copy_cell_data_accelerator)
        self.column_menu = self.widget.column_menu = PopupMenu(
            self.window.application, self.widget, callback=self._press_header, connect_events=False)

        if multi_select:
            self.widget.set_rubber_banding(True)
            self.widget.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)

        elif always_select:
            self.widget.get_selection().set_mode(Gtk.SelectionMode.BROWSE)

        if activate_row_callback:
            self.widget.connect("row-activated", self.on_activate_row, activate_row_callback)

        if select_row_callback:
            self.widget.get_selection().connect("changed", self.on_select_row, select_row_callback)

        if tooltip_callback:
            self.widget.set_has_tooltip(True)
            self.widget.connect("query-tooltip", self.on_tooltip, tooltip_callback)

        self.widget.set_fixed_height_mode(True)
        self.widget.set_search_equal_func(self.on_search_match)

        add_css_class(self.widget, "treeview-spacing")

    def _append_columns(self, cols, column_config):

        if not column_config:
            for column in cols.values():
                self.widget.append_column(column)
            return

        # Restore column order from config
        for column_id in column_config:
            column = cols.get(column_id)

            if column is None:
                continue

            self.widget.append_column(column)

        added_columns = self.widget.get_columns()

        # If any columns were missing in the config, append them
        for index, column in enumerate(cols.values()):
            if column not in added_columns:
                self.widget.insert_column(column, index)

    @staticmethod
    def _hide_columns(cols, column_config):

        for column_id, column in cols.items():
            # Read Show / Hide column settings from last session
            if not column_config:
                continue

            try:
                column.set_visible(column_config[column_id]["visible"])
            except Exception:
                # Invalid value
                pass

    def _set_last_column_autosize(self, *_args):

        columns = self.widget.get_columns()
        resizable_set = False

        for column in reversed(columns):
            if not column.get_visible():
                continue

            if not resizable_set:
                # Make sure the last visible column isn't resizable
                column.set_resizable(False)
                column.set_fixed_width(-1)

                resizable_set = True
                continue

            # Make the previously last column resizable again
            column.set_resizable(True)
            break

    def _header_toggle(self, _action, _state, columns, index):

        column = columns[index]
        column.set_visible(not column.get_visible())
        self._set_last_column_autosize()

    def _press_header(self, menu, _treeview):

        columns = self.widget.get_columns()
        visible_columns = [column for column in columns if column.get_visible()]
        menu.clear()

        for column_num, column in enumerate(columns, start=1):
            title = column.get_widget().get_text()

            if title == "":
                title = _("Column #%i") % column_num

            menu.add_items(
                ("$" + title, None)
            )
            menu.update_model()
            menu.actions[title].set_state(GLib.Variant("b", column in visible_columns))

            if column in visible_columns:
                menu.actions[title].set_enabled(len(visible_columns) > 1)

            menu.actions[title].connect("activate", self._header_toggle, columns, column_num - 1)

    def initialise_columns(self, columns):

        default_sort_column = None
        default_sort_type = None
        data_types = []

        for column_index, (column_id, column_data) in enumerate(columns.items()):
            data_type = column_data.get("data_type")

            if not data_type:
                column_type = column_data["column_type"]

                if column_type == "progress":
                    data_type = int

                elif column_type == "toggle":
                    data_type = bool

                else:
                    data_type = str

            data_types.append(data_type)
            self._column_ids[column_id] = column_index

        self.model = Gtk.ListStore(*data_types)
        self._column_numbers = list(self._column_ids.values())

        progress_padding = 1
        height_padding = 4
        width_padding = 10 if GTK_API_VERSION >= 4 else 12

        cols = {}
        num_cols = len(columns)
        column_config = None

        for column_index, (column_id, column_data) in enumerate(columns.items()):
            title = column_data.get("title")

            if title is None:
                # All visible columns processed
                break

            column_type = column_data["column_type"]
            sort_column = column_data.get("sort_column", column_id)
            iterator_key = column_data.get("iterator_key")
            width = column_data.get("width")
            sort_type = column_data.get("default_sort_column")

            if sort_type:
                default_sort_column = sort_column
                default_sort_type = Gtk.SortType.DESCENDING if sort_type == "descending" else Gtk.SortType.ASCENDING

            if iterator_key:
                self._iterator_key_column = column_index

            if self.widget_name:
                try:
                    column_config = config.sections["columns"][self.widget_name[0]][self.widget_name[1]]
                except KeyError:
                    column_config = config.sections["columns"][self.widget_name]

                if column_type != "icon":
                    try:
                        width = column_config[column_id]["width"]
                    except Exception:
                        # Invalid value
                        pass

            if not isinstance(width, int):
                width = None

            xalign = 0.0

            if column_type == "text":
                renderer = Gtk.CellRendererText(single_paragraph_mode=True, xpad=width_padding, ypad=height_padding)
                column = Gtk.TreeViewColumn(column_id, renderer, text=column_index)
                text_underline_column = column_data.get("text_underline_column")
                text_weight_column = column_data.get("text_weight_column")

                if text_underline_column:
                    column.add_attribute(renderer, "underline", self._column_ids[text_underline_column])

                if text_weight_column:
                    column.add_attribute(renderer, "weight", self._column_ids[text_weight_column])

            elif column_type == "number":
                xalign = 1
                renderer = Gtk.CellRendererText(xalign=xalign, xpad=width_padding, ypad=height_padding)
                column = Gtk.TreeViewColumn(column_id, renderer, text=column_index)
                column.set_alignment(xalign)

            elif column_type == "progress":
                renderer = Gtk.CellRendererProgress(ypad=progress_padding)
                column = Gtk.TreeViewColumn(column_id, renderer, value=column_index)

            elif column_type == "toggle":
                xalign = 0.5
                renderer = Gtk.CellRendererToggle(xalign=xalign, xpad=13)
                renderer.connect("toggled", self.on_toggle, column_data["toggle_callback"])

                column = Gtk.TreeViewColumn(column_id, renderer, active=column_index)

            elif column_type == "icon":
                renderer = Gtk.CellRendererPixbuf(xalign=1.0)

                if column_id == "country":
                    if GTK_API_VERSION >= 4:
                        # Custom icon size defined in theme.py
                        renderer.set_property("icon-size", Gtk.IconSize.NORMAL)  # pylint: disable=no-member
                    else:
                        # Use the same size as the original icon
                        renderer.set_property("stock-size", 0)

                column = Gtk.TreeViewColumn(column_id, renderer, icon_name=column_index)

            column_header = column.get_button()

            # Required for fixed height mode
            column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)

            if width is not None:
                column.set_resizable(column_type != "icon")

                if width > 0:
                    column.set_fixed_width(width)

            # Allow individual cells to receive visual focus
            if num_cols > 1:
                renderer.set_property("mode", Gtk.CellRendererMode.ACTIVATABLE)

            column.set_reorderable(True)
            column.set_min_width(24)

            label = Gtk.Label(label=title, margin_start=5, margin_end=5, mnemonic_widget=column_header, visible=True)
            column.set_widget(label)

            if xalign == 1 and GTK_API_VERSION >= 4:
                # Gtk.TreeViewColumn.set_alignment() only changes the sort arrow position in GTK 4
                # Actually align the label to the right here instead
                label.get_parent().set_halign(Gtk.Align.END)

            if column_data.get("hide_header"):
                column.get_widget().set_visible(False)

            if column_data.get("expand_column"):
                column.set_expand(True)

            column.set_sort_column_id(self._column_ids[sort_column])
            cols[column_id] = column

        self._append_columns(cols, column_config)
        self._hide_columns(cols, column_config)

        self.widget.connect("columns-changed", self._set_last_column_autosize)
        self.widget.emit("columns-changed")

        if default_sort_column is not None:
            self.model.set_sort_column_id(self._column_ids[default_sort_column], default_sort_type)

        self.widget.set_model(self.model)

    def save_columns(self, subpage=None):
        """ Save a treeview's column widths and visibilities for the next session """

        saved_columns = {}
        column_config = config.sections["columns"]

        for column in self.widget.get_columns():
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
                            "width": column_config[self.widget_name][title]["width"]
                        }

                    continue

            except KeyError:
                # No previously saved width, going with zero
                pass

            saved_columns[title] = {"visible": visible, "width": width}

        if subpage is not None:
            try:
                column_config[self.widget_name]
            except KeyError:
                column_config[self.widget_name] = {}

            column_config[self.widget_name][subpage] = saved_columns
        else:
            column_config[self.widget_name] = saved_columns

    def disable_sorting(self):

        self._sort_column, self._sort_type = self.model.get_sort_column_id()
        self.model.set_default_sort_func(lambda *args: 0)
        self.model.set_sort_column_id(-1, Gtk.SortType.ASCENDING)

    def enable_sorting(self):
        self.model.set_sort_column_id(self._sort_column, self._sort_type)

    def add_row(self, values, select_row=True, prepend=False):

        position = 0 if prepend else -1
        key = values[self._iterator_key_column]

        self.iterators[key] = iterator = self.model.insert_with_valuesv(position, self._column_numbers, values)
        self._iter_keys[iterator.user_data] = key

        if select_row:
            self.select_row(iterator)

        return iterator

    def get_all_rows(self):

        iterators = []
        iterator = self.model.get_iter_first()

        while iterator is not None:
            iterators.append(iterator)
            iterator = self.model.iter_next(iterator)

        return iterators

    def get_selected_rows(self):

        iterators = []
        model, paths = self.widget.get_selection().get_selected_rows()

        for path in paths:
            iterators.append(model.get_iter(path))

        return iterators

    def get_row_value(self, iterator, column_id):
        return self.model.get_value(iterator, self._column_ids[column_id])

    def set_row_value(self, iterator, column_id, value):
        return self.model.set_value(iterator, self._column_ids[column_id], value)

    def select_row(self, iterator):
        self.widget.set_cursor(self.model.get_path(iterator))

    def remove_row(self, iterator):
        del self.iterators[self._iter_keys[iterator.user_data]]
        self.model.remove(iterator)

    def unselect_all_rows(self):
        self.widget.get_selection().unselect_all()

    def grab_focus(self):
        self.widget.grab_focus()

    def clear(self):

        self.widget.set_model(None)

        self.model.clear()
        self.iterators.clear()

        self.widget.set_model(self.model)

    def set_search_entry(self, entry):
        self.widget.set_search_entry(entry)

    def show_tooltip(self, pos_x, pos_y, tooltip, column_id, column_titles, text_function):

        try:
            bin_x, bin_y = self.widget.convert_widget_to_bin_window_coords(pos_x, pos_y)
            path, column, _cell_x, _cell_y = self.widget.get_path_at_pos(bin_x, bin_y)

        except TypeError:
            return False

        if column.get_title() not in column_titles:
            return False

        iterator = self.model.get_iter(path)
        column_value = self.get_row_value(iterator, column_id)

        # Update tooltip position
        self.widget.set_tooltip_cell(tooltip, path, column)

        text = text_function(column_value)
        if not text:
            return False

        tooltip.set_text(text)
        return True

    @staticmethod
    def get_user_status_tooltip_text(column_value):

        if column_value == 1:
            return _("Away")

        if column_value == 2:
            return _("Online")

        return _("Offline")

    def show_user_status_tooltip(self, pos_x, pos_y, tooltip, column_id):
        return self.show_tooltip(pos_x, pos_y, tooltip, column_id, ("status",), self.get_user_status_tooltip_text)

    @staticmethod
    def get_country_tooltip_text(country_code):

        if country_code:
            country_name = GeoIP.country_code_to_name(country_code)
            return f"{country_name} ({country_code})"

        return _("Earth")

    def show_country_tooltip(self, pos_x, pos_y, tooltip, column_id):
        return self.show_tooltip(pos_x, pos_y, tooltip, column_id, ("country",), get_country_tooltip_text)

    def on_toggle(self, _widget, path, callback):
        callback(self, self.model.get_iter(path))

    def on_activate_row(self, _widget, path, column, callback):
        callback(self, self.model.get_iter(path), column.get_title())

    def on_select_row(self, selection, callback):
        _model, iterator = selection.get_selected()
        callback(self, iterator)

    def on_search_match(self, model, _column, search_term, iterator):

        if not search_term:
            return True

        for column_index in self._column_ids.values():
            if model.get_column_type(column_index) != GObject.TYPE_STRING:
                continue

            column_value = model.get_value(iterator, column_index).lower()

            if column_value.startswith("nplus-"):
                # Ignore icon name columns
                continue

            if search_term.lower() in column_value:
                return False

        return True

    def on_tooltip(self, _widget, pos_x, pos_y, keyboard_mode, tooltip, callback):
        return callback(self, pos_x, pos_y, keyboard_mode, tooltip)

    def on_copy_cell_data_accelerator(self, *_args):
        """ Ctrl+C: copy cell data """

        path, column = self.widget.get_cursor()
        model = self.widget.get_model()

        if path is None:
            return False

        iterator = model.get_iter(path)
        cell_value = str(model.get_value(iterator, column.get_sort_column_id()))

        copy_text(cell_value)
        return True


""" Legacy functions (to be removed) """


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

    action_id = "grouping-" + "".join(random.choice(string.digits) for _ in range(8))
    menu = Gio.Menu()

    menuitem = Gio.MenuItem.new(_("Ungrouped"), f"win.{action_id}::ungrouped")
    menu.append_item(menuitem)

    menuitem = Gio.MenuItem.new(_("Group by Folder"), f"win.{action_id}::folder_grouping")
    menu.append_item(menuitem)

    menuitem = Gio.MenuItem.new(_("Group by User"), f"win.{action_id}::user_grouping")
    menu.append_item(menuitem)

    state = GLib.Variant("s", verify_grouping_mode(active_mode))
    action = Gio.SimpleAction(name=action_id, parameter_type=GLib.VariantType("s"), state=state)
    action.connect("change-state", callback)

    window.add_action(action)
    action.change_state(state)

    return menu


def select_user_row_iter(fmodel, sel, user_index, selected_user, iterator):

    while iterator is not None:
        user = fmodel.get_value(iterator, user_index)

        if selected_user == user:
            sel.select_iter(iterator)

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


def initialise_columns(window, treeview_name, treeview, *args):

    cols = {}
    num_cols = len(args)
    column_config = None

    progress_padding = 1
    height_padding = 4
    width_padding = 10 if GTK_API_VERSION >= 4 else 12

    for column_index, (column_id, title, width, column_type, extra) in enumerate(args):
        if treeview_name:
            try:
                column_config = config.sections["columns"][treeview_name[0]][treeview_name[1]]
            except KeyError:
                column_config = config.sections["columns"][treeview_name]

            if column_type != "icon":
                try:
                    width = column_config[column_id]["width"]
                except Exception:
                    # Invalid value
                    pass

        if not isinstance(width, int):
            width = 0

        xalign = 0.0

        if column_type == "text":
            renderer = Gtk.CellRendererText(single_paragraph_mode=True, xpad=width_padding, ypad=height_padding)
            column = Gtk.TreeViewColumn(column_id, renderer, text=column_index)

        elif column_type == "number":
            xalign = 1
            renderer = Gtk.CellRendererText(xalign=xalign, xpad=width_padding, ypad=height_padding)
            column = Gtk.TreeViewColumn(column_id, renderer, text=column_index)
            column.set_alignment(xalign)

        elif column_type == "progress":
            renderer = Gtk.CellRendererProgress(ypad=progress_padding)
            column = Gtk.TreeViewColumn(column_id, renderer, value=column_index)

        elif column_type == "toggle":
            xalign = 0.5
            renderer = Gtk.CellRendererToggle(xalign=xalign, xpad=13)
            column = Gtk.TreeViewColumn(column_id, renderer, active=column_index)

        elif column_type == "icon":
            renderer = Gtk.CellRendererPixbuf(xalign=1.0)

            if GTK_API_VERSION == 3:
                renderer.set_property("xpad", 2)

            if column_id == "country":
                if GTK_API_VERSION >= 4:
                    # Custom icon size defined in theme.py
                    renderer.set_property("icon-size", Gtk.IconSize.NORMAL)  # pylint: disable=no-member
                else:
                    # Use the same size as the original icon
                    renderer.set_property("stock-size", 0)

            column = Gtk.TreeViewColumn(column_id, renderer, icon_name=column_index)

        column_header = column.get_button()

        # Required for fixed height mode
        column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)

        if width == -1:
            column.set_resizable(False)
            column.set_expand(True)
        else:
            column.set_resizable(column_type != "icon")

            if width > 0:
                column.set_fixed_width(width)

        if isinstance(extra, int):
            column.add_attribute(renderer, "sensitive", extra)

        elif isinstance(extra, tuple):
            weight, underline = extra
            column.add_attribute(renderer, "weight", weight)
            column.add_attribute(renderer, "underline", underline)

        # Allow individual cells to receive visual focus
        if num_cols > 1 and column_type != "edit":
            renderer.set_property("mode", Gtk.CellRendererMode.ACTIVATABLE)

        column.set_reorderable(True)
        column.set_min_width(24)

        label = Gtk.Label(label=title, margin_start=5, margin_end=5, mnemonic_widget=column_header, visible=True)
        column.set_widget(label)

        if xalign == 1 and GTK_API_VERSION >= 4:
            # Gtk.TreeViewColumn.set_alignment() only changes the sort arrow position in GTK 4
            # Actually align the label to the right here instead
            label.get_parent().set_halign(Gtk.Align.END)

        cols[column_id] = column

    append_columns(treeview, cols, column_config)
    hide_columns(treeview, cols, column_config)
    treeview.set_fixed_height_mode(True)

    add_css_class(treeview, "treeview-spacing")

    treeview.set_search_equal_func(on_search_match, treeview)
    treeview.connect("columns-changed", set_last_column_autosize)
    treeview.emit("columns-changed")

    Accelerator("<Primary>c", treeview, on_copy_cell_data_accelerator)
    treeview.column_menu = PopupMenu(window.application, treeview, callback=press_header, connect_events=False)

    return cols


def on_search_match(model, _column, search_term, iterator, treeview):

    if not search_term:
        return True

    for i in range(treeview.get_n_columns()):
        if model.get_column_type(i) != GObject.TYPE_STRING:
            continue

        column_value = model.get_value(iterator, i).lower()

        if column_value.startswith("nplus-"):
            # Ignore icon name columns
            continue

        if search_term.lower() in column_value:
            return False

    return True


def on_copy_cell_data_accelerator(treeview, *_args):
    """ Ctrl+C: copy cell data """

    path, column = treeview.get_cursor()
    model = treeview.get_model()

    if path is None:
        return False

    iterator = model.get_iter(path)
    cell_value = str(model.get_value(iterator, column.get_sort_column_id()))

    copy_text(cell_value)
    return True


def append_columns(treeview, cols, column_config):

    if not column_config:
        for column in cols.values():
            treeview.append_column(column)
        return

    # Restore column order from config
    for column_id in column_config:
        column = cols.get(column_id)

        if column is None:
            continue

        treeview.append_column(column)

    added_columns = treeview.get_columns()

    # If any columns were missing in the config, append them
    for column_index, column in enumerate(cols.values()):
        if column not in added_columns:
            treeview.insert_column(column, column_index)


def set_last_column_autosize(treeview):

    columns = treeview.get_columns()
    resizable_set = False

    for column in reversed(columns):
        if not column.get_visible():
            continue

        if not resizable_set:
            # Make sure the last visible column isn't resizable
            column.set_resizable(False)
            column.set_fixed_width(-1)

            resizable_set = True
            continue

        # Make the previously last column resizable again
        column.set_resizable(True)
        break


def hide_columns(_treeview, cols, column_config):

    for column_id, column in cols.items():
        # Read Show / Hide column settings from last session
        if not column_config:
            continue

        try:
            column.set_visible(column_config[column_id]["visible"])
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


def press_header(menu, treeview):

    columns = treeview.get_columns()
    visible_columns = [column for column in columns if column.get_visible()]
    menu.clear()

    for column_num, column in enumerate(columns, start=1):
        title = column.get_widget().get_text()

        if title == "":
            title = _("Column #%i") % column_num

        menu.add_items(
            ("$" + title, None)
        )
        menu.update_model()
        menu.actions[title].set_state(GLib.Variant("b", column in visible_columns))

        if column in visible_columns:
            menu.actions[title].set_enabled(len(visible_columns) > 1)

        menu.actions[title].connect("activate", header_toggle, treeview, columns, column_num - 1)


def header_toggle(_action, _state, treeview, columns, index):

    column = columns[index]
    column.set_visible(not column.get_visible())
    set_last_column_autosize(treeview)


def set_treeview_selected_row(treeview, bin_x, bin_y):
    """ Handles row selection when right-clicking in a treeview """

    pathinfo = treeview.get_path_at_pos(bin_x, bin_y)
    selection = treeview.get_selection()

    if pathinfo is not None:
        path, column, _cell_x, _cell_y = pathinfo

        # Make sure we don't attempt to select a single row if the row is already
        # in a selection of multiple rows, otherwise the other rows will be unselected
        if selection.count_selected_rows() <= 1 or not selection.path_is_selected(path):
            treeview.grab_focus()
            treeview.set_cursor(path, column, False)
    else:
        selection.unselect_all()


def show_tooltip(treeview, pos_x, pos_y, tooltip, sourcecolumn, column_titles, text_function):

    try:
        bin_x, bin_y = treeview.convert_widget_to_bin_window_coords(pos_x, pos_y)
        path, column, _cell_x, _cell_y = treeview.get_path_at_pos(bin_x, bin_y)

    except TypeError:
        return False

    if column.get_title() not in column_titles:
        return False

    model = treeview.get_model()
    iterator = model.get_iter(path)
    column_value = model.get_value(iterator, sourcecolumn)

    # Update tooltip position
    treeview.set_tooltip_cell(tooltip, path, column)

    text = text_function(column_value)
    if not text:
        return False

    tooltip.set_text(text)
    return True


def get_country_tooltip_text(country_code):

    if country_code:
        country_name = GeoIP.country_code_to_name(country_code)
        return f"{country_name} ({country_code})"

    return _("Earth")


def get_file_path_tooltip_text(column_value):
    return column_value


def get_file_type_tooltip_text(column_value):
    return FILE_TYPE_ICON_LABELS.get(column_value, _("Unknown"))


def get_transfer_file_path_tooltip_text(column_value):
    return column_value.filename or column_value.path


def get_user_status_tooltip_text(column_value):

    if column_value == 1:
        return _("Away")

    if column_value == 2:
        return _("Online")

    return _("Offline")


def show_country_tooltip(treeview, pos_x, pos_y, tooltip, sourcecolumn):
    return show_tooltip(treeview, pos_x, pos_y, tooltip, sourcecolumn,
                        ("country",), get_country_tooltip_text)


def show_file_path_tooltip(treeview, pos_x, pos_y, tooltip, sourcecolumn, transfer=False):

    func = get_file_path_tooltip_text if not transfer else get_transfer_file_path_tooltip_text

    return show_tooltip(treeview, pos_x, pos_y, tooltip, sourcecolumn,
                        ("folder", "filename", "path"), func)


def show_file_type_tooltip(treeview, pos_x, pos_y, tooltip, sourcecolumn):
    return show_tooltip(treeview, pos_x, pos_y, tooltip, sourcecolumn,
                        ("file_type"), get_file_type_tooltip_text)


def show_user_status_tooltip(treeview, pos_x, pos_y, tooltip, sourcecolumn):
    return show_tooltip(treeview, pos_x, pos_y, tooltip, sourcecolumn, ("status",), get_user_status_tooltip_text)
