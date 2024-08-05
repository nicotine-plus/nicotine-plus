# COPYRIGHT (C) 2023-2024 Nicotine+ Contributors
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

from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Pango

from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.widgets.accelerator import Accelerator
from pynicotine.gtkgui.widgets.theme import add_css_class


class ComboBox:

    def __init__(self, container, label=None, has_entry=False, has_dropdown=True,
                 enable_arrow_keys=True, entry=None, visible=True, items=None,
                 item_selected_callback=None):

        self.widget = None
        self.dropdown = None
        self.entry = entry
        self.enable_arrow_keys = enable_arrow_keys
        self.item_selected_callback = item_selected_callback

        self._ids = {}
        self._positions = {}
        self._model = None
        self._button = None
        self._entry_buffer = None
        self._popover = None
        self._focus_controller = None
        self._search_entry = None
        self._search_delay = 150
        self._search_delay_timer = None
        self._selection_bound = None
        self._is_updating_entry = False
        self._is_updating_items = False
        self._is_select_callback_enabled = False

        self._create_combobox(container, label, has_entry, has_dropdown)

        if items:
            self.freeze()

            for provided_item in items:
                if isinstance(provided_item, str):
                    item = provided_item
                    item_id = None
                else:
                    item, item_id = provided_item

                self.append(item, item_id)

            self.unfreeze()

        self.set_visible(visible)

    def destroy(self):

        if self._search_delay_timer is not None:
            GLib.source_remove(self._search_delay_timer)
            self._search_delay_timer = None

        if self._focus_controller is not None:
            self.widget.remove_controller(self._focus_controller)

        self.freeze()
        self.clear()
        self.unfreeze()

        self.__dict__.clear()

    def _create_combobox_gtk4(self, container, label, has_entry, has_dropdown):

        self._model = Gtk.StringList()

        # Workaround for using GtkExpression in old PyGObject versions
        builder = Gtk.Builder.new_from_string("""<interface>
  <object class="GtkDropDown" id="dropdown">
    <property name="expression">
      <lookup type="GtkStringObject" name="string" />
    </property>
  </object>
</interface>""", -1)
        self.dropdown = self._button = builder.get_object("dropdown")
        self.dropdown.set_model(self._model)

        default_factory = self.dropdown.get_factory()
        button_factory = None

        if not has_entry:
            button_factory = Gtk.SignalListItemFactory()

            button_factory.connect("setup", self._on_factory_setup)
            button_factory.connect("bind", self._on_factory_bind)

        self.dropdown.set_factory(button_factory)
        self.dropdown.set_list_factory(default_factory)

        self.dropdown.connect("notify::selected", self._on_item_selected)

        self._popover = list(self.dropdown)[-1]
        self._popover.connect("notify::visible", self._on_dropdown_visible)

        if not has_entry:
            self.widget = self.dropdown
            self.dropdown.set_valign(Gtk.Align.CENTER)

            if label:
                label.set_mnemonic_widget(self.widget)

            container.append(self.widget)
            return

        self.widget = Gtk.Box(valign=Gtk.Align.CENTER, visible=True)
        self._popover.connect("map", self._on_dropdown_map)

        if self.entry is None:
            self.entry = Gtk.Entry(hexpand=True, width_chars=8, visible=True)

        if label:
            label.set_mnemonic_widget(self.entry)

        self._entry_buffer = self.entry.get_buffer()
        self.entry.connect("notify::selection-bound", self._on_selection_bound_changed)
        self._entry_buffer.connect("inserted-text", self._on_inserted_text)
        self._entry_buffer.connect_after("deleted-text", self._on_deleted_text)

        self._focus_controller = Gtk.EventControllerFocus()
        self._focus_controller.connect("leave", self._on_focus_out)
        self.widget.add_controller(self._focus_controller)

        self.dropdown.set_enable_search(True)

        popover_container = self._popover.get_child()
        search_container = next(iter(popover_container))
        self._search_entry = next(iter(search_container))

        try:
            self._search_delay = self._search_entry.get_search_delay()

        except AttributeError:
            pass

        search_container.set_visible(False)
        self._button.set_sensitive(False)

        self.widget.append(self.entry)
        self.widget.append(self.dropdown)

        if has_dropdown:
            add_css_class(self.widget, "linked")
        else:
            toggle_button = next(iter(self.dropdown))
            toggle_button.set_visible(False)
            self.dropdown.set_size_request(width=1, height=-1)

        Accelerator("Escape", self.entry, self._on_escape_accelerator)

        add_css_class(self.dropdown, "entry")
        container.append(self.widget)

    def _create_combobox_gtk3(self, container, label, has_entry, has_dropdown):

        self.dropdown = self.widget = Gtk.ComboBoxText(has_entry=has_entry, valign=Gtk.Align.CENTER, visible=True)
        self._model = self.dropdown.get_model()

        self.dropdown.connect("scroll-event", self._on_button_scroll_event)
        self.dropdown.connect("notify::active", self._on_item_selected)
        self.dropdown.connect("notify::popup-shown", self._on_dropdown_visible)

        if label:
            label.set_mnemonic_widget(self.widget)

        if not has_entry:
            for cell in self.dropdown.get_cells():
                cell.props.ellipsize = Pango.EllipsizeMode.END

            container.add(self.widget)
            return

        if self.entry is None:
            self.entry = self.dropdown.get_child()
            self.entry.set_width_chars(8)
        else:
            self.dropdown.get_child().destroy()
            self.dropdown.add(self.entry)  # pylint: disable=no-member

        add_css_class(self.dropdown, "dropdown-scrollbar")
        completion = Gtk.EntryCompletion(inline_completion=True, inline_selection=True,
                                         popup_single_match=False, model=self._model)
        completion.set_text_column(0)
        self.entry.set_completion(completion)

        self._button = list(self.entry.get_parent())[-1]
        self._button.set_visible(has_dropdown)
        container.add(self.widget)

    def _create_combobox(self, container, label, has_entry, has_dropdown):

        if GTK_API_VERSION >= 4:
            self._create_combobox_gtk4(container, label, has_entry, has_dropdown)
        else:
            self._create_combobox_gtk3(container, label, has_entry, has_dropdown)

        if has_entry:
            Accelerator("Up", self.entry, self._on_arrow_key_accelerator, "up")
            Accelerator("Down", self.entry, self._on_arrow_key_accelerator, "down")

    def _update_item_entry_text(self):
        """Set text entry text to the same value as selected item."""

        if GTK_API_VERSION == 3:
            # Already supported natively in GTK 3
            return

        item = self.dropdown.get_selected_item()

        if item is None:
            return

        item_text = item.get_string()

        if self.get_text() != item_text:
            self.set_text(item_text)

        self.set_selected_pos(Gtk.INVALID_LIST_POSITION)

    def _update_item_positions(self, start_position, added=False):

        if added:
            end_position = self.get_num_items() + 1
        else:
            end_position = self.get_num_items()

        new_ids = {}

        for position in range(start_position, end_position):
            if added:
                item_id = self._ids[position - 1]
            else:
                item_id = self._ids.pop(position + 1)

            new_ids[position] = item_id
            self._positions[item_id] = position

        self._ids.update(new_ids)

    # General #

    def freeze(self):
        """Called before inserting/deleting items, to avoid redundant UI updates."""

        if GTK_API_VERSION >= 4:
            self.dropdown.set_model(None)

    def unfreeze(self):
        """Called after items have been inserted/deleted, to enable UI updates."""

        if GTK_API_VERSION == 3:
            return

        self._is_updating_items = True

        self.dropdown.set_model(self._model)
        self.set_selected_pos(Gtk.INVALID_LIST_POSITION)

        self._is_updating_items = False

    def insert(self, position, item, item_id=None):

        if item_id is None:
            item_id = item

        if item_id in self._positions:
            return

        self._is_updating_items = True

        last_position = self.get_num_items()

        if position == -1:
            position = last_position

        if GTK_API_VERSION >= 4:
            if last_position == position:
                self._model.append(item)
            else:
                num_removals = (last_position - position)
                inserted_items = [item] + [self._model.get_string(i) for i in range(position, last_position)]
                self._model.splice(position, num_removals, inserted_items)
        else:
            self.dropdown.insert_text(position, item)

        if self.entry and not self._positions:
            self._button.set_sensitive(True)

        self._update_item_positions(start_position=(position + 1), added=True)

        if GTK_API_VERSION >= 4:
            self.set_selected_pos(Gtk.INVALID_LIST_POSITION)

        self._ids[position] = item_id
        self._positions[item_id] = position

        self._is_updating_items = False

    def append(self, item, item_id=None):
        self.insert(position=-1, item=item, item_id=item_id)

    def prepend(self, item, item_id=None):
        self.insert(position=0, item=item, item_id=item_id)

    def get_num_items(self):
        return len(self._positions)

    def get_selected_pos(self):

        if GTK_API_VERSION >= 4:
            return self.dropdown.get_selected()

        return self.dropdown.get_active()

    def get_selected_id(self):
        return self._ids.get(self.get_selected_pos())

    def get_text(self):

        if self.entry:
            return self.entry.get_text()

        return self.get_selected_id()

    def set_selected_pos(self, position):

        if position is None:
            return

        if self.get_selected_pos() == position:
            return

        if GTK_API_VERSION >= 4:
            self.dropdown.set_selected(position)
        else:
            self.dropdown.set_active(position)

    def set_selected_id(self, item_id):
        self.set_selected_pos(self._positions.get(item_id))

    def set_text(self, text):

        if self.entry:
            self._is_updating_entry = True
            self.entry.set_text(text)
            return

        self.set_selected_id(text)

    def remove_pos(self, position):

        if position == -1:
            position = (self.get_num_items() - 1)

        item_id = self._ids.pop(position, None)

        if item_id is None:
            return

        self._is_updating_items = True

        if GTK_API_VERSION >= 4:
            self._model.remove(position)
        else:
            self.dropdown.remove(position)

        if self.entry and not self._ids:
            self._button.set_sensitive(False)

        # Update positions for items after the removed one
        self._positions.pop(item_id, None)
        self._update_item_positions(start_position=position)

        self._is_updating_items = False

    def remove_id(self, item_id):
        position = self._positions.get(item_id)
        self.remove_pos(position)

    def clear(self):

        self._is_updating_items = True

        self._ids.clear()
        self._positions.clear()

        if GTK_API_VERSION >= 4:
            self._model.splice(position=0, n_removals=self._model.get_n_items())
        else:
            self.dropdown.remove_all()

        if self.entry and self._button:
            self._button.set_sensitive(False)

        self._is_updating_items = False

        self._is_updating_items = False

    def grab_focus(self):
        self.entry.grab_focus()

    def set_row_separator_func(self, func):
        if GTK_API_VERSION == 3:
            self.dropdown.set_row_separator_func(func)

    def set_visible(self, visible):
        self.widget.set_visible(visible)

    # Callbacks #

    def _on_factory_bind(self, _factory, list_item):
        label = list_item.get_child()
        label.set_text(list_item.get_item().get_string())

    def _on_factory_setup(self, _factory, list_item):
        list_item.set_child(
            Gtk.Label(ellipsize=Pango.EllipsizeMode.END, mnemonic_widget=self.widget, xalign=0))

    def _on_escape_accelerator(self, *_args):
        self._popover.set_visible(False)
        self._popover.set_autohide(True)

    def _on_arrow_key_accelerator(self, _entry, _unused, direction):

        if not self.enable_arrow_keys:
            return True

        if GTK_API_VERSION == 3:
            # Gtk.ComboBox already supports this functionality
            return False

        if self._popover.get_visible():
            self._popover.child_focus(Gtk.DirectionType.TAB_FORWARD)
            return True

        if not self._positions:
            return False

        current_position = self._positions.get(self.get_text(), -1)

        if direction == "up":
            new_position = max(0, current_position - 1)
        else:
            new_position = min(current_position + 1, len(self._positions) - 1)

        self.set_selected_pos(new_position)
        return True

    def _on_changed_text(self, is_deletion=False):

        if self._is_updating_entry:
            self._is_updating_entry = False
            return

        text = self.get_text()
        text_lower = text.lower()
        match = None
        show_popover = False

        if text:
            for item in self._ids.values():
                if not item.lower().startswith(text_lower):
                    continue

                if match is not None:
                    show_popover = True
                    break

                match = item

        if not is_deletion and match is not None and match != text:
            self._selection_bound = len(text)
            self._is_updating_entry = True
            self._entry_buffer.insert_text(self._selection_bound, match[self._selection_bound:], -1)

        if self._search_delay_timer is not None:
            GLib.source_remove(self._search_delay_timer)
            self._search_delay_timer = None

        if show_popover:
            self._search_delay_timer = GLib.timeout_add(self._search_delay, self._on_search_changed, text)

        elif self._popover.get_visible():
            self._popover.set_visible(False)
            self._popover.set_autohide(True)

    def _on_inserted_text(self, _entry, *_args):
        self._on_changed_text()

    def _on_deleted_text(self, _entry, *_args):
        self._on_changed_text(is_deletion=True)

    def _on_search_changed(self, text):

        self._search_delay_timer = None

        self._search_entry.set_text(text)
        self._search_entry.emit("search-changed")

        if self._popover.get_visible():
            return

        selection_bounds = self.entry.get_selection_bounds()

        if selection_bounds:
            self._selection_bound, _end_pos = selection_bounds

        self._popover.set_autohide(False)
        self._popover.set_visible(True)

    def _on_selection_bound_changed(self, *_args):

        if self._selection_bound is not None:
            self.entry.select_region(self._selection_bound, -1)

        self._selection_bound = None

    def _on_focus_out(self, *_args):
        self._popover.set_visible(False)

    def _on_button_scroll_event(self, dropdown, event, *_args):
        """Prevent scrolling and pass scroll event to parent scrollable (GTK 3)"""

        scrollable = dropdown.get_ancestor(Gtk.ScrolledWindow)

        if scrollable is not None:
            scrollable.event(event)

        return True

    def _on_select_callback_status(self, enabled):
        self._is_select_callback_enabled = enabled

    def _on_dropdown_map(self, *_args):

        # Align dropdown with entry and button
        popover_content = next(iter(self._popover))
        container_width = self.entry.get_parent().get_width()
        button_width = self._button.get_width()

        self._popover.set_offset(x_offset=-container_width + button_width, y_offset=0)
        popover_content.set_size_request(container_width, height=-1)

    def _on_dropdown_visible(self, widget, param):

        visible = widget.get_property(param.name)

        # Only enable item selection callback when an item is selected from the UI
        GLib.idle_add(self._on_select_callback_status, visible)

        if self.entry is None:
            return

        if not visible:
            if self._popover is None or self._popover.get_autohide():
                self.entry.grab_focus_without_selecting()
            return

        self.set_selected_id(self.get_text())

    def _on_item_selected(self, *_args):

        if self._is_updating_items:
            return

        selected_id = self.get_selected_id()

        if selected_id is None:
            return

        if self.entry is not None:
            # Update text entry with text from the selected item
            self._update_item_entry_text()

            # Cursor is normally placed at the beginning, move to the end
            self.entry.set_position(-1)

        if self._is_select_callback_enabled and self.item_selected_callback is not None:
            self.item_selected_callback(self, selected_id)
