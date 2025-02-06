# COPYRIGHT (C) 2020-2024 Nicotine+ Contributors
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

import time

import gi.module

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
from pynicotine.gtkgui.widgets.theme import USER_STATUS_ICON_LABELS
from pynicotine.gtkgui.widgets.theme import add_css_class


class TreeView:

    def __init__(self, window, parent, columns, has_tree=False, multi_select=False,
                 persistent_sort=False, name=None, secondary_name=None, activate_row_callback=None,
                 focus_in_callback=None, select_row_callback=None, delete_accelerator_callback=None,
                 search_entry=None):

        self.window = window
        self.widget = Gtk.TreeView(fixed_height_mode=True, has_tooltip=True, visible=True)
        self.model = None
        self.multi_select = multi_select
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
        self._column_gvalues = {}
        self._column_gesture_controllers = []
        self._column_numbers = None
        self._default_sort_column = None
        self._default_sort_type = Gtk.SortType.ASCENDING
        self._sort_column = None
        self._sort_type = None
        self._persistent_sort = persistent_sort
        self._columns_changed_handler = None
        self._last_redraw_time = 0
        self._selection = self.widget.get_selection()
        self._h_adjustment = parent.get_hadjustment()
        self._v_adjustment = parent.get_vadjustment()
        self._v_adjustment_upper = 0
        self._v_adjustment_value = 0
        self._is_scrolling_to_row = False
        self.notify_value_handler = self._v_adjustment.connect("notify::value", self.on_v_adjustment_value)

        if GTK_API_VERSION >= 4:
            parent.set_child(self.widget)  # pylint: disable=no-member
        else:
            parent.add(self.widget)        # pylint: disable=no-member

        self._initialise_columns(columns)

        Accelerator("<Primary>c", self.widget, self.on_copy_cell_data_accelerator)
        Accelerator("<Primary>f", self.widget, self.on_start_search)

        Accelerator("Left", self.widget, self.on_collapse_row_accelerator)
        Accelerator("minus", self.widget, self.on_collapse_row_blocked_accelerator)
        Accelerator("Right", self.widget, self.on_expand_row_accelerator)
        Accelerator("plus", self.widget, self.on_expand_row_blocked_accelerator)
        Accelerator("equal", self.widget, self.on_expand_row_blocked_accelerator)
        Accelerator("backslash", self.widget, self.on_expand_row_level_accelerator)

        self._column_menu = self.widget.column_menu = PopupMenu(
            self.window.application, self.widget, callback=self.on_column_header_menu, connect_events=False)

        if multi_select:
            self.widget.set_rubber_banding(True)
            self._selection.set_mode(Gtk.SelectionMode.MULTIPLE)

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

        self._query_tooltip_handler = self.widget.connect("query-tooltip", self.on_tooltip)
        self.widget.connect("move-cursor", self.on_key_move_cursor)
        self.widget.set_search_equal_func(self.on_search_match)

        add_css_class(self.widget, "treeview-spacing")

    def destroy(self):

        # Prevent updates while destroying widget
        self.widget.disconnect(self._columns_changed_handler)
        self.widget.disconnect(self._query_tooltip_handler)
        self._v_adjustment.disconnect(self.notify_value_handler)

        self._column_menu.destroy()
        self.__dict__.clear()

    def create_model(self):

        # Bypass Tree/ListStore overrides for improved performance in set_value()
        gtk_module = gi.module.get_introspection_module("Gtk")
        model_class = gtk_module.TreeStore if self.has_tree else gtk_module.ListStore

        if hasattr(gtk_module.ListStore, "insert_with_valuesv"):
            gtk_module.ListStore.insert_with_values = gtk_module.ListStore.insert_with_valuesv

        self.model = model_class()
        self.model.set_column_types(self._data_types)

        if self._sort_column is not None and self._sort_type is not None:
            self.model.set_sort_column_id(self._sort_column, self._sort_type)

        self.widget.set_model(self.model)
        return self.model

    def redraw(self):
        """Workaround for GTK 3 issue where GtkTreeView doesn't refresh changed
        values if horizontal scrolling is present while fixed-height mode is
        enabled."""

        if GTK_API_VERSION != 3 or self._h_adjustment.get_value() <= 0:
            return

        current_time = time.monotonic()

        if (current_time - self._last_redraw_time) < 1:
            return

        self._last_redraw_time = current_time
        self.widget.queue_draw()

    def _append_columns(self, cols, column_config):

        # Restore column order from config
        for column_id in column_config:
            column = cols.get(column_id)

            if column is not None:
                self.widget.append_column(column)

        added_columns = self.widget.get_columns()

        # If any columns were missing in the config, append them
        for index, column in enumerate(cols.values()):
            if column not in added_columns:
                self.widget.insert_column(column, index)

        # Read Show / Hide column settings from last session
        for column_id, column in cols.items():
            column.set_visible(bool(column_config.get(column_id, {}).get("visible", True)))

    def _update_column_properties(self, *_args):

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

        # Set first non-icon column as the expander column
        for column in columns:
            if column.type != "icon" and column.get_visible():
                self.widget.set_expander_column(column)
                break

    def _initialise_column_ids(self, columns):

        self._data_types = []
        int_types = {GObject.TYPE_UINT, GObject.TYPE_UINT64}

        for column_index, (column_id, column_data) in enumerate(columns.items()):
            data_type = column_data.get("data_type")

            if not data_type:
                column_type = column_data.get("column_type")

                if column_type == "progress":
                    data_type = GObject.TYPE_INT

                elif column_type == "toggle":
                    data_type = GObject.TYPE_BOOLEAN

                else:
                    data_type = GObject.TYPE_STRING

            self._column_ids[column_id] = column_index
            self._data_types.append(data_type)

            if data_type not in int_types:
                continue

            self._column_gvalues[column_index] = value = GObject.Value(data_type)

            # Optimization: bypass PyGObject's set_value override
            value.set_value = value.set_uint if data_type == GObject.TYPE_UINT else value.set_uint64

        self._column_numbers = list(self._column_ids.values())

    def _initialise_columns(self, columns):

        self._initialise_column_ids(columns)
        self.model = self.create_model()

        progress_padding = 1
        height_padding = 4
        width_padding = 10 if GTK_API_VERSION >= 4 else 12

        column_widgets = {}
        column_config = {}
        has_visible_column_header = False

        for column_index, (column_id, column_data) in enumerate(columns.items()):
            title = column_data.get("title")
            iterator_key = column_data.get("iterator_key")
            sort_data_column = column_data.get("sort_column", column_id)
            sort_column_id = self._column_ids[sort_data_column]
            default_sort_type = column_data.get("default_sort_type")

            if iterator_key:
                # Use values from this column as keys for iterator mapping
                self._iterator_key_column = column_index

            if default_sort_type:
                # Sort treeview by values in this column by default
                self._default_sort_column = sort_column_id
                self._default_sort_type = (Gtk.SortType.DESCENDING if default_sort_type == "descending"
                                           else Gtk.SortType.ASCENDING)

                if self._sort_column is None and self._sort_type is None:
                    self._sort_column = self._default_sort_column
                    self._sort_type = self._default_sort_type

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

                column_properties = column_config.get(column_id, {})
                column_sort_type = column_properties.get("sort")

                # Restore saved column width if the column size is fixed. For expandable
                # columns, the width becomes the minimum width, so use the default value in those cases.
                if not should_expand_column and column_type != "icon":
                    width = column_properties.get("width", width)

                if column_sort_type and self._persistent_sort:
                    # Sort treeview by values in this column by default
                    self._sort_column = sort_column_id
                    self._sort_type = (Gtk.SortType.DESCENDING if column_sort_type == "descending"
                                       else Gtk.SortType.ASCENDING)
                    self.model.set_sort_column_id(self._sort_column, self._sort_type)

            # Allow individual cells to receive visual focus
            mode = Gtk.CellRendererMode.ACTIVATABLE if len(columns) > 1 else Gtk.CellRendererMode.INERT
            xalign = 0.0

            if column_type == "text":
                renderer = Gtk.CellRendererText(
                    mode=mode, single_paragraph_mode=True, xpad=width_padding, ypad=height_padding
                )
                column = Gtk.TreeViewColumn(title=title, cell_renderer=renderer, text=column_index)
                text_underline_column = column_data.get("text_underline_column")
                text_weight_column = column_data.get("text_weight_column")

                if text_underline_column:
                    column.add_attribute(renderer, "underline", self._column_ids[text_underline_column])

                if text_weight_column:
                    column.add_attribute(renderer, "weight", self._column_ids[text_weight_column])

            elif column_type == "number":
                xalign = 1
                renderer = Gtk.CellRendererText(mode=mode, xalign=xalign, xpad=width_padding, ypad=height_padding)
                column = Gtk.TreeViewColumn(title=title, cell_renderer=renderer, text=column_index)
                column.set_alignment(xalign)

            elif column_type == "progress":
                xalign = 1
                renderer = Gtk.CellRendererProgress(mode=mode, ypad=progress_padding)
                column = Gtk.TreeViewColumn(title=title, cell_renderer=renderer, value=column_index)
                column.set_alignment(xalign)

            elif column_type == "toggle":
                xalign = 0.5
                renderer = Gtk.CellRendererToggle(mode=mode, xalign=xalign, xpad=13)
                renderer.connect("toggled", self.on_toggle, column_data["toggle_callback"])

                column = Gtk.TreeViewColumn(title=title, cell_renderer=renderer, active=column_index)

            elif column_type == "icon":
                icon_args = {}

                if column_id == "country":
                    if GTK_API_VERSION >= 4:
                        # Custom icon size defined in theme.py
                        icon_args["icon_size"] = Gtk.IconSize.NORMAL  # pylint: disable=no-member
                    else:
                        # Use the same size as the original icon
                        icon_args["stock_size"] = 0

                renderer = Gtk.CellRendererPixbuf(mode=mode, xalign=1.0, **icon_args)
                column = Gtk.TreeViewColumn(title=title, cell_renderer=renderer, icon_name=column_index)

            column_header = column.get_button()

            if GTK_API_VERSION >= 4:
                gesture_click = Gtk.GestureClick()
                column_header.add_controller(gesture_click)  # pylint: disable=no-member
            else:
                gesture_click = Gtk.GestureMultiPress(widget=column_header)

            gesture_click.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
            gesture_click.connect("released", self.on_column_header_pressed, column_id, sort_column_id)
            self._column_gesture_controllers.append(gesture_click)

            title_container = next(iter(column_header))
            title_widget = next(iter(title_container)) if xalign < 1 else list(title_container)[-1]

            if column_data.get("hide_header"):
                title_widget.set_visible(False)
            else:
                has_visible_column_header = True

            # Required for fixed height mode
            column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)

            if width is not None:
                column.set_resizable(column_type != "icon")

            if isinstance(width, int) and width > 0:
                column.set_fixed_width(width)

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

            column.set_sort_column_id(sort_column_id)
            column_widgets[column_id] = column

        self.widget.set_headers_visible(has_visible_column_header)

        self._append_columns(column_widgets, column_config)

        self._columns_changed_handler = self.widget.connect("columns-changed", self._update_column_properties)
        self.widget.emit("columns-changed")

    def save_columns(self):
        """Save a treeview's column widths and visibilities for the next
        session."""

        if not self._widget_name:
            return

        saved_columns = {}
        column_config = config.sections["columns"]

        for column in self.widget.get_columns():
            title = column.id
            width = column.get_width()
            visible = column.get_visible()
            sort_column_id = column.get_sort_column_id()

            # A column width of zero should not be saved to the config.
            # When a column is hidden, the correct width will be remembered during the
            # run it was hidden. Subsequent runs will yield a zero width, so we
            # attempt to re-use a previously saved non-zero column width instead.
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

            saved_columns[title] = columns = {"visible": visible, "width": width}

            if not self._persistent_sort:
                continue

            if sort_column_id == self._sort_column and sort_column_id != self._default_sort_column:
                columns["sort"] = "descending" if self._sort_type == Gtk.SortType.DESCENDING else "ascending"

        if self._secondary_name is not None:
            if self._widget_name not in column_config:
                column_config[self._widget_name] = {}

            column_config[self._widget_name][self._secondary_name] = saved_columns
        else:
            column_config[self._widget_name] = saved_columns

    def freeze(self):
        self.model.set_sort_column_id(Gtk.TREE_SORTABLE_UNSORTED_SORT_COLUMN_ID, Gtk.SortType.ASCENDING)

    def unfreeze(self):
        if self._sort_column is not None and self._sort_type is not None:
            self.model.set_sort_column_id(self._sort_column, self._sort_type)

    def set_show_expanders(self, show):
        self.widget.set_show_expanders(show)

    def add_row(self, values, select_row=True, parent_iterator=None):

        key = values[self._iterator_key_column]

        if key in self.iterators:
            return None

        position = 0  # Insert at the beginning for large performance improvement
        value_columns = []
        included_values = []

        for index, value in enumerate(values):
            if not value and index is not self._sort_column:
                # Skip empty values if not active sort column to avoid unnecessary work
                continue

            if index in self._column_gvalues:
                # Need gvalue conversion for large integers
                gvalue = self._column_gvalues[index]
                gvalue.set_value(value or 0)
                value = gvalue

            value_columns.append(index)
            included_values.append(value)

        if self.has_tree:
            self.iterators[key] = iterator = self.model.insert_with_values(
                parent_iterator, position, value_columns, included_values
            )
        else:
            self.iterators[key] = iterator = self.model.insert_with_values(
                position, value_columns, included_values
            )

        self._iterator_keys[iterator] = key

        if select_row:
            self.select_row(iterator)

        return iterator

    def get_selected_rows(self):

        _model, paths = self._selection.get_selected_rows()

        for path in paths:
            yield self.model.get_iter(path)

    def get_num_selected_rows(self):
        return self._selection.count_selected_rows()

    def get_focused_row(self):

        path, _column = self.widget.get_cursor()

        if path is None:
            return None

        return self.model.get_iter(path)

    def get_row_value(self, iterator, column_id):
        return self.model.get_value(iterator, self._column_ids[column_id])

    def set_row_value(self, iterator, column_id, value):

        column_index = self._column_ids[column_id]

        if column_index in self._column_gvalues:
            # Need gvalue conversion for large integers
            gvalue = self._column_gvalues[column_index]
            gvalue.set_value(value)
            value = gvalue

        return self.model.set_value(iterator, column_index, value)

    def set_row_values(self, iterator, column_ids, values):

        value_columns = []

        for index, column_id in enumerate(column_ids):
            column_index = self._column_ids[column_id]

            if column_index in self._column_gvalues:
                # Need gvalue conversion for large integers
                gvalue = self._column_gvalues[column_index]
                gvalue.set_value(values[index])
                values[index] = gvalue

            value_columns.append(column_index)

        return self.model.set(iterator, value_columns, values)

    def remove_row(self, iterator):
        del self.iterators[self._iterator_keys[iterator]]
        self.model.remove(iterator)

    def select_row(self, iterator=None, expand_rows=True, should_scroll=True):

        if iterator is None:
            # Select first row if available
            iterator = self.model.get_iter_first()

            if iterator is None:
                return

        if should_scroll:
            path = self.model.get_path(iterator)

            if expand_rows:
                self.widget.expand_to_path(path)

            self._is_scrolling_to_row = True
            self.widget.set_cursor(path)
            self.widget.scroll_to_cell(path, column=None, use_align=True, row_align=0.5, col_align=0.5)
            return

        self._selection.select_iter(iterator)

    def select_all_rows(self):
        self._selection.select_all()

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

        for column in self.widget.get_columns():
            if column.get_visible():
                yield column.id

    def is_empty(self):
        return not self.iterators

    def is_selection_empty(self):
        return self._selection.count_selected_rows() <= 0

    def is_row_expanded(self, iterator):
        path = self.model.get_path(iterator)
        return self.widget.row_expanded(path)

    def is_row_selected(self, iterator):
        return self._selection.iter_is_selected(iterator)

    def grab_focus(self):
        self.widget.grab_focus()

    def clear(self):

        self.widget.set_model(None)
        self.freeze()

        self.model.clear()
        self.iterators.clear()
        self._iterator_keys.clear()

        self.unfreeze()
        self.widget.set_model(self.model)

    @staticmethod
    def get_icon_label(column, icon_name, is_short_country_label=False):

        if column.id == "country":
            country_code = icon_name[-2:].upper()

            if is_short_country_label:
                return country_code

            country_name = core.network_filter.COUNTRIES.get(country_code, _("Unknown"))
            return f"{country_name} ({country_code})"

        if column.id == "status":
            return USER_STATUS_ICON_LABELS[icon_name]

        if column.id == "file_type":
            return FILE_TYPE_ICON_LABELS[icon_name]

        return icon_name

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

        iterator = None

        if self.multi_select:
            iterator = next(self.get_selected_rows(), None)
        else:
            _model, iterator = selection.get_selected()

        callback(self, iterator)

    def on_delete_accelerator(self, _treeview, _state, callback):
        callback(self)

    def on_column_header_pressed(self, controller, _num_p, _pos_x, _pos_y, column_id, sort_column_id):
        """Reset sorting when column header has been pressed three times."""

        self._sort_column, self._sort_type = self.model.get_sort_column_id()

        if self._default_sort_column is None:
            # No default sort column for treeview, keep standard GTK behavior
            self.save_columns()
            return False

        if self._data_types[sort_column_id] == GObject.TYPE_STRING or column_id in {"in_queue", "queue_position"}:
            # String value (or queue position column): ascending sort by default
            first_sort_type = Gtk.SortType.ASCENDING
            second_sort_type = Gtk.SortType.DESCENDING
        else:
            # Numerical value: descending sort by default
            first_sort_type = Gtk.SortType.DESCENDING
            second_sort_type = Gtk.SortType.ASCENDING

        if self._sort_column != sort_column_id:
            self._sort_column = sort_column_id
            self._sort_type = first_sort_type

        elif self._sort_type == first_sort_type:
            self._sort_type = second_sort_type

        elif self._sort_type == second_sort_type:
            # Reset treeview to default state
            self._sort_column = self._default_sort_column
            self._sort_type = self._default_sort_type

        self.model.set_sort_column_id(self._sort_column, self._sort_type)
        self.save_columns()

        controller.set_state(Gtk.EventSequenceState.CLAIMED)
        return True

    def on_column_header_toggled(self, _action, _state, column):
        column.set_visible(not column.get_visible())
        self._update_column_properties()

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
            menu.actions[title].set_state(GLib.Variant.new_boolean(column in visible_columns))

            if column in visible_columns:
                menu.actions[title].set_enabled(len(visible_columns) > 1)

            menu.actions[title].connect("activate", self.on_column_header_toggled, column)

    def on_column_position_changed(self, column, _param):
        """Save column position and width to config."""

        column_id = column.id
        offset = column.get_x_offset()

        if self._column_offsets.get(column_id) == offset:
            return

        self._column_offsets[column_id] = offset
        self.save_columns()

    def on_key_move_cursor(self, _widget, step, *_args):

        if step != Gtk.MovementStep.BUFFER_ENDS:
            return

        # We are scrolling to the end using the End key. Disable the
        # auto-scroll workaround to actually change the scroll adjustment value.
        self._is_scrolling_to_row = True

    def on_v_adjustment_value(self, *_args):

        upper = self._v_adjustment.get_upper()

        if not self._is_scrolling_to_row and upper != self._v_adjustment_upper and self._v_adjustment_value <= 0:
            # When new rows are added while sorting is enabled, treeviews
            # auto-scroll to the new position of the currently visible row.
            # Disable this behavior while we're at the top to prevent jumping
            # to random positions as rows are populated.
            self._v_adjustment.set_value(0)
        else:
            self._v_adjustment_value = self._v_adjustment.get_value()

        self._v_adjustment_upper = upper
        self._is_scrolling_to_row = False

    def on_search_match(self, model, _column, search_term, iterator):

        if not search_term:
            return True

        accepted_column_types = {"text", "number"}

        for column_index, column_data in enumerate(self._columns.values()):
            if "column_type" not in column_data:
                continue

            if column_data["column_type"] not in accepted_column_types:
                continue

            column_value = model.get_value(iterator, column_index)

            if column_value and search_term.lower() in column_value.lower():
                return False

        return True

    def on_tooltip(self, _widget, pos_x, pos_y, _keyboard_mode, tooltip):

        bin_x, bin_y = self.widget.convert_widget_to_bin_window_coords(pos_x, pos_y)
        is_blank, path, column, _cell_x, _cell_y = self.widget.is_blank_at_pos(bin_x, bin_y)

        if is_blank:
            return False

        iterator = self.model.get_iter(path)

        if column.tooltip_callback:
            value = column.tooltip_callback(self, iterator)
        else:
            value = self.get_row_value(iterator, column.id)

        if not value:
            return False

        if not isinstance(value, str):
            return False

        if column.type == "icon":
            value = self.get_icon_label(column, value)

        # Update tooltip position
        self.widget.set_tooltip_cell(tooltip, path, column)

        tooltip.set_text(value)
        return True

    def on_copy_cell_data_accelerator(self, *_args):
        """Ctrl+C: copy cell data."""

        path, column = self.widget.get_cursor()

        if path is None:
            return False

        iterator = self.model.get_iter(path)
        value = str(self.model.get_value(iterator, column.get_sort_column_id()))

        if not value:
            return False

        if column.type == "icon":
            value = self.get_icon_label(column, value, is_short_country_label=True)

        clipboard.copy_text(value)
        return True

    def on_start_search(self, *_args):
        """Ctrl+F: start search."""

        self.widget.emit("start-interactive-search")

    def on_collapse_row_accelerator(self, *_args):
        """Left: collapse row."""

        iterator = self.get_focused_row()

        if iterator is None:
            return False

        return self.collapse_row(iterator)

    def on_collapse_row_blocked_accelerator(self, *_args):
        """minus: collapse row (block search)."""

        self.on_collapse_row_accelerator()
        return True

    def on_expand_row_accelerator(self, *_args):
        """Right: expand row."""

        iterator = self.get_focused_row()

        if iterator is None:
            return False

        return self.expand_row(iterator)

    def on_expand_row_blocked_accelerator(self, *_args):
        """plus, equal: expand row (block search)."""

        self.on_expand_row_accelerator()
        return True

    def on_expand_row_level_accelerator(self, *_args):
        """\backslash: collapse or expand to show subs."""

        iterator = self.get_focused_row()

        if iterator is None:
            return False

        self.collapse_row(iterator)  # show 2nd level
        self.expand_row(iterator)
        return True


# Legacy Functions (to be removed) #


def create_grouping_menu(window, active_mode, callback):

    action_id = f"grouping-{GLib.uuid_string_random()}"
    menu = Gio.Menu()

    menuitem = Gio.MenuItem.new(_("Ungrouped"), f"win.{action_id}::ungrouped")
    menu.append_item(menuitem)

    menuitem = Gio.MenuItem.new(_("Group by Folder"), f"win.{action_id}::folder_grouping")
    menu.append_item(menuitem)

    menuitem = Gio.MenuItem.new(_("Group by User"), f"win.{action_id}::user_grouping")
    menu.append_item(menuitem)

    state = GLib.Variant.new_string(active_mode)
    action = Gio.SimpleAction(name=action_id, parameter_type=state.get_type(), state=state)
    action.connect("change-state", callback)

    window.add_action(action)
    action.change_state(state)

    return menu


def set_treeview_selected_row(treeview, bin_x, bin_y):
    """Handles row selection when right-clicking in a treeview."""

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
