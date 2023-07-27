# COPYRIGHT (C) 2020-2023 Nicotine+ Contributors
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
import time

from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk

from pynicotine.config import config
from pynicotine.core import core
from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.widgets import clipboard
from pynicotine.gtkgui.widgets.accelerator import Accelerator
from pynicotine.gtkgui.widgets.popupmenu import PopupMenu
from pynicotine.gtkgui.widgets.theme import FILE_TYPE_ICON_LABELS
from pynicotine.gtkgui.widgets.theme import USER_STATUS_ICON_NAMES
from pynicotine.gtkgui.widgets.theme import add_css_class
from pynicotine.slskmessages import UserStatus


""" Treeview """


class TreeView:

    def __init__(self, window, parent, columns, has_tree=False, multi_select=False, always_select=False,
                 name=None, secondary_name=None, activate_row_callback=None, focus_in_callback=None,
                 select_row_callback=None, delete_accelerator_callback=None, search_entry=None):

        self.window = window
        self.widget = Gtk.TreeView(enable_tree_lines=True, fixed_height_mode=True, has_tooltip=True, visible=True)
        self.model = None
        self.iterators = {}
        self.has_tree = has_tree
        self._widget_name = name
        self._secondary_name = secondary_name
        self._columns = columns
        self._data_types = []
        self._iterator_keys = {}
        self._iterator_key_column = 0
        self._column_ids = {}
        self._column_offsets = {}
        self._column_gvalues = []
        self._column_numbers = None
        self._default_sort_column = None
        self._default_sort_type = Gtk.SortType.ASCENDING
        self._sort_column = None
        self._sort_type = None
        self._clicked_column_reset_sort = None
        self._last_redraw_time = 0
        self._selection = self.widget.get_selection()

        parent.set_property("child", self.widget)
        self._h_adjustment = self.widget.get_parent().get_hadjustment()
        self.initialise_columns(columns)

        Accelerator("<Primary>c", self.widget, self.on_copy_cell_data_accelerator)
        self.column_menu = self.widget.column_menu = PopupMenu(
            self.window.application, self.widget, callback=self.on_column_header_menu, connect_events=False)

        if multi_select:
            self.widget.set_rubber_banding(True)
            self._selection.set_mode(Gtk.SelectionMode.MULTIPLE)

        elif always_select:
            self._selection.set_mode(Gtk.SelectionMode.BROWSE)

        if activate_row_callback:
            self.widget.connect("row-activated", self.on_activate_row, activate_row_callback)

        if focus_in_callback:
            if GTK_API_VERSION >= 4:
                focus_controller = Gtk.EventControllerFocus()
                focus_controller.connect("enter", self.on_focus_in, focus_in_callback)
                self.widget.add_controller(focus_controller)  # pylint: disable=no-member
            else:
                self.widget.connect("focus-in-event", self.on_focus_in, focus_in_callback)

        if select_row_callback:
            self._selection.connect("changed", self.on_select_row, select_row_callback)

        if delete_accelerator_callback:
            Accelerator("Delete", self.widget, self.on_delete_accelerator, delete_accelerator_callback)

        if search_entry:
            self.widget.set_search_entry(search_entry)

        self.widget.connect("query-tooltip", self.on_tooltip)
        self.widget.set_search_equal_func(self.on_search_match)

        add_css_class(self.widget, "treeview-spacing")

    def create_model(self):

        model_class = Gtk.TreeStore if self.has_tree else Gtk.ListStore
        self.model = model_class(*self._data_types)

        self.widget.set_model(self.model)
        return self.model

    def redraw(self):
        """ Workaround for GTK 3 issue where GtkTreeView doesn't refresh changed values
        if horizontal scrolling is present while fixed-height mode is enabled """

        if GTK_API_VERSION != 3 or self._h_adjustment.get_value() <= 0:
            return

        current_time = time.time()

        if (current_time - self._last_redraw_time) < 1:
            return

        self._last_redraw_time = current_time
        self.widget.queue_draw()

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

    def initialise_columns(self, columns):

        self._data_types = data_types = []

        for column_index, (column_id, column_data) in enumerate(columns.items()):
            data_type = column_data.get("data_type")

            if not data_type:
                column_type = column_data.get("column_type")

                if column_type == "progress":
                    data_type = int

                elif column_type == "toggle":
                    data_type = bool

                else:
                    data_type = str

            gvalue = GObject.Value(data_type)

            data_types.append(data_type)
            self._column_gvalues.append(gvalue)
            self._column_ids[column_id] = column_index

        self.model = self.create_model()
        self._column_numbers = list(self._column_ids.values())

        progress_padding = 1
        height_padding = 4
        width_padding = 10 if GTK_API_VERSION >= 4 else 12

        column_widgets = {}
        column_config = None
        has_visible_column_header = False

        for column_index, (column_id, column_data) in enumerate(columns.items()):
            title = column_data.get("title")
            iterator_key = column_data.get("iterator_key")
            sort_data_column = column_data.get("sort_column", column_id)
            default_sort_type = column_data.get("default_sort_type")

            if iterator_key:
                # Use values from this column as keys for iterator mapping
                self._iterator_key_column = column_index

            if default_sort_type:
                # Sort treeview by values in this column by default
                self._default_sort_column = self._column_ids[sort_data_column]
                self._default_sort_type = (Gtk.SortType.DESCENDING if default_sort_type == "descending"
                                           else Gtk.SortType.ASCENDING)
                self.model.set_sort_column_id(self._default_sort_column, self._default_sort_type)

            if title is None:
                # Hidden data column
                continue

            column_type = column_data["column_type"]
            width = column_data.get("width")
            should_expand_column = column_data.get("expand_column")
            sensitive_column = column_data.get("sensitive_column")

            if self._widget_name:
                try:
                    column_config = config.sections["columns"][self._widget_name][self._secondary_name]
                except KeyError:
                    column_config = config.sections["columns"][self._widget_name]

                # Restore saved column width if the column size is fixed. For expandable
                # columns, the width becomes the minimum width, so use the default value in those cases.
                if not should_expand_column and column_type != "icon":
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
                column = Gtk.TreeViewColumn(title=title, cell_renderer=renderer, text=column_index)
                text_underline_column = column_data.get("text_underline_column")
                text_weight_column = column_data.get("text_weight_column")

                if text_underline_column:
                    column.add_attribute(renderer, "underline", self._column_ids[text_underline_column])

                if text_weight_column:
                    column.add_attribute(renderer, "weight", self._column_ids[text_weight_column])

            elif column_type == "number":
                xalign = 1
                renderer = Gtk.CellRendererText(xalign=xalign, xpad=width_padding, ypad=height_padding)
                column = Gtk.TreeViewColumn(title=title, cell_renderer=renderer, text=column_index)
                column.set_alignment(xalign)

            elif column_type == "progress":
                renderer = Gtk.CellRendererProgress(ypad=progress_padding)
                column = Gtk.TreeViewColumn(title=title, cell_renderer=renderer, value=column_index)

            elif column_type == "toggle":
                xalign = 0.5
                renderer = Gtk.CellRendererToggle(xalign=xalign, xpad=13)
                renderer.connect("toggled", self.on_toggle, column_data["toggle_callback"])

                column = Gtk.TreeViewColumn(title=title, cell_renderer=renderer, active=column_index)

            elif column_type == "icon":
                renderer = Gtk.CellRendererPixbuf(xalign=1.0)

                if column_id == "country":
                    if GTK_API_VERSION >= 4:
                        # Custom icon size defined in theme.py
                        renderer.set_property("icon-size", Gtk.IconSize.NORMAL)  # pylint: disable=no-member
                    else:
                        # Use the same size as the original icon
                        renderer.set_property("stock-size", 0)

                column = Gtk.TreeViewColumn(title=title, cell_renderer=renderer, icon_name=column_index)

            column_header = column.get_button()
            column_header.connect("clicked", self.on_column_header_pressed, column)

            if GTK_API_VERSION >= 4:
                title_container = column_header.get_first_child()
                title_widget = title_container.get_first_child() if xalign < 1 else title_container.get_last_child()
            else:
                title_container = column_header.get_children()[0]
                title_widget = title_container.get_children()[0] if xalign < 1 else title_container.get_children()[-1]

            if column_data.get("hide_header"):
                title_widget.set_visible(False)
            else:
                has_visible_column_header = True

            # Required for fixed height mode
            column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)

            if width is not None:
                column.set_resizable(column_type != "icon")

                if width > 0:
                    column.set_fixed_width(width)

            # Allow individual cells to receive visual focus
            if len(columns) > 1:
                renderer.set_property("mode", Gtk.CellRendererMode.ACTIVATABLE)

            column.set_reorderable(True)
            column.set_min_width(24)

            if xalign == 1 and GTK_API_VERSION >= 4:
                # Gtk.TreeViewColumn.set_alignment() only changes the sort arrow position in GTK 4
                # Actually align the label to the right here instead
                title_widget.set_halign(Gtk.Align.END)

            if sensitive_column:
                column.add_attribute(renderer, "sensitive", self._column_ids[sensitive_column])

            if should_expand_column:
                column.set_expand(True)

            if self._widget_name:
                column.connect("notify::x-offset", self.on_column_position_changed)

            column.id = column_id
            column.type = column_type
            column.tooltip_callback = column_data.get("tooltip_callback")

            column.set_sort_column_id(self._column_ids[sort_data_column])
            column_widgets[column_id] = column

        self.widget.set_headers_visible(has_visible_column_header)

        self._append_columns(column_widgets, column_config)
        self._hide_columns(column_widgets, column_config)

        self.widget.connect("columns-changed", self._set_last_column_autosize)
        self.widget.emit("columns-changed")

    def save_columns(self):
        """ Save a treeview's column widths and visibilities for the next session """

        saved_columns = {}
        column_config = config.sections["columns"]

        for column in self.widget.get_columns():
            title = column.id
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
                            "width": column_config[self._widget_name][title]["width"]
                        }

                    continue

            except KeyError:
                # No previously saved width, going with zero
                pass

            saved_columns[title] = {"visible": visible, "width": width}

        if self._secondary_name is not None:
            try:
                column_config[self._widget_name]
            except KeyError:
                column_config[self._widget_name] = {}

            column_config[self._widget_name][self._secondary_name] = saved_columns
        else:
            column_config[self._widget_name] = saved_columns

    def disable_sorting(self):
        self._sort_column, self._sort_type = self.model.get_sort_column_id()
        self.model.set_sort_column_id(Gtk.TREE_SORTABLE_UNSORTED_SORT_COLUMN_ID, Gtk.SortType.ASCENDING)

    def enable_sorting(self):
        if self._sort_column is not None and self._sort_type is not None:
            self.model.set_sort_column_id(self._sort_column, self._sort_type)

    def set_show_expanders(self, show):
        self.widget.set_show_expanders(show)

    def add_row(self, values, select_row=True, prepend=False, parent_iterator=None):

        position = 0 if prepend else -1
        values = values[:]
        key = values[self._iterator_key_column]

        for i, value in enumerate(values):
            gvalue = self._column_gvalues[i]
            gvalue.set_value(value)
            values[i] = gvalue

        if self.has_tree:
            self.iterators[key] = iterator = self.model.insert_with_values(  # pylint: disable=no-member
                parent_iterator, position, self._column_numbers, values
            )
        else:
            self.iterators[key] = iterator = self.model.insert_with_valuesv(position, self._column_numbers, values)

        self._iterator_keys[iterator.user_data] = key

        if select_row:
            self.select_row(iterator)

        return iterator

    def get_selected_rows(self):

        _model, paths = self._selection.get_selected_rows()
        iterators = [self.model.get_iter(path) for path in paths]

        return iterators

    def get_focused_row(self):

        path, _column = self.widget.get_cursor()

        if path is None:
            return None

        return self.model.get_iter(path)

    def get_row_value(self, iterator, column_id):
        return self.model.get_value(iterator, self._column_ids[column_id])

    def set_row_value(self, iterator, column_id, value):

        column_index = self._column_ids[column_id]
        gvalue = self._column_gvalues[column_index]
        gvalue.set_value(value)

        return self.model.set_value(iterator, column_index, gvalue)

    def remove_row(self, iterator):
        del self.iterators[self._iterator_keys[iterator.user_data]]
        self.model.remove(iterator)

    def select_row(self, iterator=None, should_scroll=True):

        if iterator is None:
            # Select first row if available
            iterator = self.model.get_iter_first()

            if iterator is None:
                return

        if should_scroll:
            path = self.model.get_path(iterator)

            self.widget.expand_to_path(path)
            self.widget.set_cursor(path)
            self.widget.scroll_to_cell(path, column=None, use_align=True, row_align=0.5, col_align=0.5)
            return

        self._selection.select_iter(iterator)

    def unselect_all_rows(self):
        self._selection.unselect_all()

    def expand_row(self, iterator):
        path = self.model.get_path(iterator)
        return self.widget.expand_row(path, open_all=False)

    def collapse_row(self, iterator):
        path = self.model.get_path(iterator)
        return self.widget.collapse_row(path)

    def expand_all_rows(self):
        self.widget.expand_all()

    def collapse_all_rows(self):
        self.widget.collapse_all()

    def expand_root_rows(self):

        model = self.model
        iterator = model.get_iter_first()

        while iterator:
            path = model.get_path(iterator)
            self.widget.expand_row(path, open_all=False)
            iterator = model.iter_next(iterator)

    def get_focused_column(self):
        _path, column = self.widget.get_cursor()
        return column.id

    def get_visible_columns(self):
        return [column.id for column in self.widget.get_columns() if column.get_visible()]

    def is_empty(self):
        return not self.iterators

    def is_selection_empty(self):
        return self._selection.count_selected_rows() == 0

    def is_row_expanded(self, iterator):
        path = self.model.get_path(iterator)
        return self.widget.row_expanded(path)

    def grab_focus(self):
        self.widget.grab_focus()

    def clear(self):

        self.widget.set_model(None)

        self.model.clear()
        self.iterators.clear()
        self._iterator_keys.clear()

        self.widget.set_model(self.model)

    @staticmethod
    def get_user_status_tooltip_text(icon_name):

        if icon_name == USER_STATUS_ICON_NAMES[UserStatus.AWAY]:
            return _("Away")

        if icon_name == USER_STATUS_ICON_NAMES[UserStatus.ONLINE]:
            return _("Online")

        return _("Offline")

    @staticmethod
    def get_country_tooltip_text(icon_name):

        country_code = icon_name[-2:].upper()
        country_name = core.network_filter.COUNTRIES.get(country_code, _("Unknown"))
        return f"{country_name} ({country_code})"

    @staticmethod
    def get_file_type_tooltip_text(icon_name):
        return FILE_TYPE_ICON_LABELS.get(icon_name, _("Unknown"))

    def on_toggle(self, _widget, path, callback):
        callback(self, self.model.get_iter(path))

    def on_activate_row(self, _widget, path, column, callback):
        callback(self, self.model.get_iter(path), column.id)

    def on_focus_in(self, *args):

        if GTK_API_VERSION >= 4:
            _widget, callback = args
        else:
            _widget, _controller, callback = args

        callback(self)

    def on_select_row(self, selection, callback):
        _model, iterator = selection.get_selected()
        callback(self, iterator)

    def on_delete_accelerator(self, _treeview, _state, callback):
        callback(self)

    def on_column_header_pressed(self, _treeview, column):
        """ Reset sorting when column header has been pressed three times """

        if self._default_sort_column is None:
            # No default sort column for treeview, keep standard GTK behavior
            return

        if column.get_sort_order() == Gtk.SortType.DESCENDING:
            # If this column is clicked again, we reset to the default sorted state of treeview
            self._clicked_column_reset_sort = column
            return

        if column == self._clicked_column_reset_sort:
            # Reset treeview to default state
            self.model.set_sort_column_id(self._default_sort_column, self._default_sort_type)

        self._clicked_column_reset_sort = None

    def on_column_header_toggled(self, _action, _state, columns, index):

        column = columns[index]
        column.set_visible(not column.get_visible())
        self._set_last_column_autosize()

    def on_column_header_menu(self, menu, _treeview):

        columns = self.widget.get_columns()
        visible_columns = [column for column in columns if column.get_visible()]
        menu.clear()

        for column_num, column in enumerate(columns, start=1):
            title = column.get_title()

            if not title:
                title = _("Column #%i") % column_num

            menu.add_items(
                ("$" + title, None)
            )
            menu.update_model()
            menu.actions[title].set_state(GLib.Variant("b", column in visible_columns))

            if column in visible_columns:
                menu.actions[title].set_enabled(len(visible_columns) > 1)

            menu.actions[title].connect("activate", self.on_column_header_toggled, columns, column_num - 1)

    def on_column_position_changed(self, column, _param):
        """ Save column position and width to config """

        column_id = column.id
        offset = column.get_x_offset()

        if self._column_offsets.get(column_id) == offset:
            return

        self._column_offsets[column_id] = offset
        self.save_columns()

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

    def on_tooltip(self, _widget, pos_x, pos_y, _keyboard_mode, tooltip):

        try:
            bin_x, bin_y = self.widget.convert_widget_to_bin_window_coords(pos_x, pos_y)
            is_blank, path, column, _cell_x, _cell_y = self.widget.is_blank_at_pos(bin_x, bin_y)

        except TypeError:
            return False

        if is_blank:
            return False

        column_id = column.id
        iterator = self.model.get_iter(path)

        if column.tooltip_callback:
            value = column.tooltip_callback(self, iterator)
        else:
            value = self.get_row_value(iterator, column_id)

        if not value:
            return False

        if not isinstance(value, str):
            return False

        if column.type == "icon":
            if column_id == "country":
                value = self.get_country_tooltip_text(value)

            elif column_id == "status":
                value = self.get_user_status_tooltip_text(value)

            elif column_id == "file_type":
                value = self.get_file_type_tooltip_text(value)

        # Update tooltip position
        self.widget.set_tooltip_cell(tooltip, path, column)

        tooltip.set_text(value)
        return True

    def on_copy_cell_data_accelerator(self, *_args):
        """ Ctrl+C: copy cell data """

        path, column = self.widget.get_cursor()

        if path is None:
            return False

        iterator = self.model.get_iter(path)
        cell_value = str(self.model.get_value(iterator, column.get_sort_column_id()))

        clipboard.copy_text(cell_value)
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
