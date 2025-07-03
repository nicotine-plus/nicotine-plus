# SPDX-FileCopyrightText: 2023-2025 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

import os

from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Pango

from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.widgets.accelerator import Accelerator
from pynicotine.gtkgui.widgets.theme import add_css_class


class ComboBox:

    def __init__(self, container, label=None, has_entry=False, has_dropdown=True, has_entry_completion=True,
                 entry=None, visible=True, enable_arrow_keys=True, enable_word_completion=False,
                 items=None, item_selected_callback=None):

        self.widget = None
        self.dropdown = None
        self.entry = entry
        self._has_entry_completion = has_entry_completion
        self._enable_arrow_keys = enable_arrow_keys
        self._enable_word_completion = enable_word_completion
        self._item_selected_callback = item_selected_callback

        self._ids = {}
        self._positions = {}
        self._model = None
        self._entry_completion = None
        self._button = None
        self._popover = None
        self._search_entry = None
        self._list_view = None
        self._focus_controller = None
        self._is_popup_visible = False
        self._is_completion_popup_enabled = True
        self._is_updating_entry = False
        self._min_completion_key_length = 1
        self._search_delay = 150
        self._search_delay_timer = None
        self._entry_selection_bound = None
        self._selected_position = None
        self._position_offset = 0

        self._create_combobox(container, label, has_entry, has_entry_completion, has_dropdown)

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

        self.__dict__.clear()

    def _create_combobox_gtk4(self, container, label, has_entry, has_entry_completion, has_dropdown):

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

        list_factory = self.dropdown.get_factory()
        button_factory = None

        if not has_entry:
            button_factory = Gtk.SignalListItemFactory()

            button_factory.connect("setup", self._on_button_factory_setup_gtk4)
            button_factory.connect("bind", self._on_button_factory_bind_gtk4)

        self.dropdown.set_factory(button_factory)
        self.dropdown.set_list_factory(list_factory)

        self._popover = list(self.dropdown)[-1]
        self._popover.connect("notify::visible", self._on_dropdown_visible)

        try:
            scrollable = list(self._popover.get_child())[-1]
            self._list_view = scrollable.get_child()

        except AttributeError:
            pass

        if self._list_view is not None:
            self._list_view.connect("activate", self._on_item_selected)

            for accelerator in ("Tab", "<Shift>Tab"):
                Accelerator(accelerator, self._list_view, self._on_list_tab_accelerator_gtk4)

        if not has_entry:
            self.widget = self.dropdown

            if label:
                label.set_mnemonic_widget(self.widget)

            container.append(self.widget)
            return

        list_factory = Gtk.SignalListItemFactory()

        list_factory.connect("setup", self._on_entry_list_factory_setup_gtk4)
        list_factory.connect("bind", self._on_entry_list_factory_bind_gtk4)

        self.dropdown.set_list_factory(list_factory)

        self.widget = Gtk.Box(valign=Gtk.Align.CENTER, visible=True)
        self._popover.connect("map", self._on_dropdown_map_gtk4)

        if self.entry is None:
            self.entry = Gtk.Entry(hexpand=True, width_chars=8, visible=True)

        if label:
            label.set_mnemonic_widget(self.entry)

        if has_entry_completion:
            entry_buffer = self.entry.get_buffer()
            self.entry.connect("notify::selection-bound", self._on_entry_selection_bound_changed_gtk4)
            entry_buffer.connect("inserted-text", self._on_inserted_text_gtk4)
            entry_buffer.connect_after("deleted-text", self._on_deleted_text_gtk4)

            self._focus_controller = Gtk.EventControllerFocus()
            self._focus_controller.connect("leave", self._on_focus_out_gtk4)
            self.widget.add_controller(self._focus_controller)

            self.dropdown.set_enable_search(True)

            popover_container = self._popover.get_child()
            search_container = next(iter(popover_container))
            self._search_entry = next(iter(search_container))

            search_container.set_visible(False)

            for accelerator in ("Tab", "<Shift>Tab"):
                Accelerator(accelerator, self.entry, self._on_focus_out_gtk4)

            Accelerator("Up", self._list_view, self._on_list_arrow_key_accelerator_gtk4, "up")
            Accelerator("Down", self._list_view, self._on_list_arrow_key_accelerator_gtk4, "down")

        self._button.set_sensitive(False)

        self.widget.append(self.entry)
        self.widget.append(self.dropdown)

        if has_dropdown:
            add_css_class(self.widget, "linked")
        else:
            toggle_button = next(iter(self.dropdown))
            toggle_button.set_visible(False)
            self.dropdown.set_size_request(width=1, height=-1)

        add_css_class(self.dropdown, "entry")
        container.append(self.widget)

    def _create_combobox_gtk3(self, container, label, has_entry, has_entry_completion, has_dropdown):

        self.dropdown = self.widget = Gtk.ComboBoxText(has_entry=has_entry, valign=Gtk.Align.CENTER, visible=True)
        self._model = self.dropdown.get_model()

        self.dropdown.connect("scroll-event", self._on_button_scroll_event_gtk3)
        self.dropdown.connect("notify::active", self._on_item_selected)
        self.dropdown.connect("notify::popup-shown", self._on_dropdown_visible)

        if label:
            label.set_mnemonic_widget(self.widget)

        if not has_entry:
            for cell in self.dropdown.get_cells():
                cell.props.ellipsize = Pango.EllipsizeMode.END

            container.add(self.widget)
            return

        add_css_class(self.dropdown, "dropdown-scrollbar")

        if self.entry is None:
            self.entry = self.dropdown.get_child()
            self.entry.set_width_chars(8)
        else:
            self.dropdown.get_child().destroy()
            self.dropdown.add(self.entry)  # pylint: disable=no-member

        self._button = list(self.entry.get_parent())[-1]
        self._button.set_visible(has_dropdown)
        container.add(self.widget)

        if not has_entry_completion:
            return

        self._entry_completion = Gtk.EntryCompletion(
            inline_completion=not self._enable_word_completion,
            inline_selection=not self._enable_word_completion, popup_single_match=False,
            model=self._model
        )
        self._entry_completion.set_text_column(0)
        self._entry_completion.set_match_func(self._on_entry_completion_find_match_gtk3)
        self._entry_completion.connect("match-selected", self._on_entry_completion_found_match_gtk3)

        self.entry.set_completion(self._entry_completion)

    def _create_combobox(self, container, label, has_entry, has_entry_completion, has_dropdown):

        if GTK_API_VERSION >= 4:
            self._create_combobox_gtk4(container, label, has_entry, has_entry_completion, has_dropdown)
        else:
            self._create_combobox_gtk3(container, label, has_entry, has_entry_completion, has_dropdown)

        if not has_entry:
            return

        Accelerator("Up", self.entry, self._on_entry_arrow_key_accelerator, "up")
        Accelerator("Down", self.entry, self._on_entry_arrow_key_accelerator, "down")

    def _update_item_entry_text(self):
        """Set text entry text to the same value as selected item."""

        if GTK_API_VERSION >= 4:
            item = self.dropdown.get_selected_item()

            if item is None:
                return

            item_text = item.get_string()
            current_text = self.entry.get_text()

            if self._enable_word_completion and " " in current_text:
                position = self.entry.get_position()
                prefix = " ".join(current_text[:position].split(" ")[:-1])
                suffix = " ".join(current_text[position:].split(" "))
                new_text = f"{prefix} {item_text}{suffix}"

                self.entry.set_text(new_text)
                self.entry.set_position(len(prefix) + len(item_text) + 1)
                return

            if current_text != item_text:
                self.entry.set_text(item_text)

        self.entry.set_position(-1)

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

        if GTK_API_VERSION >= 4:
            self.dropdown.set_model(self._model)

    def insert(self, position, item, item_id=None):

        if item_id is None:
            item_id = item

        if item_id in self._positions:
            return

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

        if self._selected_position is not None and position <= self._selected_position:
            self._position_offset += 1

        self._ids[position] = item_id
        self._positions[item_id] = position

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

        if GTK_API_VERSION >= 4:
            self._model.remove(position)
        else:
            self.dropdown.remove(position)

        if self.entry and not self._ids:
            self._button.set_sensitive(False)

        # Update positions for items after the removed one
        self._positions.pop(item_id, None)
        self._update_item_positions(start_position=position)

        if self._selected_position is None:
            return

        if (self._selected_position + self._position_offset) >= len(self._positions):
            self._selected_position = len(self._positions) - 1
            self._position_offset = 0

        elif position < self._selected_position:
            self._position_offset -= 1

    def remove_id(self, item_id):
        position = self._positions.get(item_id)
        self.remove_pos(position)

    def clear(self):

        self._ids.clear()
        self._positions.clear()
        self._selected_position = None
        self._position_offset = 0

        if GTK_API_VERSION >= 4:
            self._model.splice(position=0, n_removals=self._model.get_n_items())
        else:
            self.dropdown.remove_all()

        if self.entry and self._button:
            self._button.set_sensitive(False)

    def grab_focus(self):
        self.entry.grab_focus()

    def set_completion_popup_enabled(self, enabled):

        self._is_completion_popup_enabled = enabled

        if self._entry_completion is not None:
            self._entry_completion.set_popup_completion(enabled)

    def set_completion_min_key_length(self, length):

        self._min_completion_key_length = length

        if self._entry_completion is not None:
            self._entry_completion.set_minimum_key_length(length)

    def set_visible(self, visible):
        self.widget.set_visible(visible)

    # Callbacks #

    def _on_button_scroll_event_gtk3(self, widget, event, *_args):
        """Prevent scrolling and pass scroll event to parent scrollable."""

        scrollable = widget.get_ancestor(Gtk.ScrolledWindow)

        if scrollable is not None:
            scrollable.event(event)

        return True

    def _on_entry_completion_find_match_gtk3(self, _completion, entry_text, iterator):

        if not entry_text:
            return False

        item_text = self._model.get_value(iterator, 0)

        if not item_text:
            return False

        item_text = item_text.lower()
        entry_text = entry_text.lower()

        if self._enable_word_completion:
            # Get word to the left of current position
            if " " in entry_text:
                position = self.entry.get_position()
                split_key = entry_text[:position].split(" ")[-1]
            else:
                split_key = entry_text

            if not split_key or len(split_key) < self._min_completion_key_length:
                return False

            if item_text != split_key and item_text.startswith(split_key):
                return True

        elif item_text != entry_text and item_text.startswith(entry_text):
            return True

        return False

    def _on_entry_completion_found_match_gtk3(self, _completion, _model, iterator):

        if not self._enable_word_completion:
            return False

        completion_value = self._model.get_value(iterator, 0)
        current_text = self.entry.get_text()

        if " " in current_text:
            position = self.entry.get_position()
            prefix = " ".join(current_text[:position].split(" ")[:-1])
            suffix = " ".join(current_text[position:].split(" "))
            new_text = f"{prefix} {completion_value}{suffix}"

            self.entry.set_text(new_text)
            self.entry.set_position(len(prefix) + len(completion_value) + 1)
            return True

        self.entry.set_text(completion_value)
        self.entry.set_position(-1)
        return True

    def _on_button_factory_bind_gtk4(self, _factory, list_item):
        label = list_item.get_child()
        label.set_text(list_item.get_item().get_string())

    def _on_button_factory_setup_gtk4(self, _factory, list_item):
        list_item.set_child(
            Gtk.Label(ellipsize=Pango.EllipsizeMode.END, mnemonic_widget=self.widget, xalign=0))

    def _on_entry_list_factory_bind_gtk4(self, _factory, list_item):
        label = list_item.get_child()
        label.set_text(list_item.get_item().get_string())

    def _on_entry_list_factory_setup_gtk4(self, _factory, list_item):
        list_item.set_child(
            Gtk.Label(ellipsize=Pango.EllipsizeMode.END, xalign=0))

    def _on_list_tab_accelerator_gtk4(self, *_args):
        # Disable focus move with Tab key
        return True

    def _on_changed_text_gtk4(self, position, is_deletion=False):

        if not self._has_entry_completion:
            return

        if self._is_updating_entry:
            self._is_updating_entry = False
            return

        text = self.get_text()
        text_lower = text.lower()
        search_query = text
        matches = []
        show_popover = False

        if text:
            for item in self._ids.values():
                item_lower = item.lower()

                if self._enable_word_completion:
                    # Get word to the left of current position
                    if " " in text:
                        split_key = text[:position].split(" ")[-1]
                    else:
                        split_key = text

                    if not split_key or len(split_key) < self._min_completion_key_length:
                        break

                    if item_lower == split_key or not item_lower.startswith(split_key):
                        continue

                    search_query = split_key
                    show_popover = self._is_completion_popup_enabled

                elif item_lower != text_lower and item_lower.startswith(text_lower):
                    if item.startswith(text):
                        matches.append(item)

                    show_popover = (self._is_completion_popup_enabled and len(text) >= self._min_completion_key_length)

        prefix = os.path.commonprefix(matches)

        if not is_deletion and prefix and prefix != text:
            # Entry completion: fill text entry with common prefix of matches
            self._entry_selection_bound = len(text)
            self._is_updating_entry = True
            self.entry.get_buffer().insert_text(
                position=self._entry_selection_bound, chars=prefix[self._entry_selection_bound:], n_chars=-1)

        if self._search_delay_timer is not None:
            GLib.source_remove(self._search_delay_timer)
            self._search_delay_timer = None

        if show_popover:
            self._search_delay_timer = GLib.timeout_add(
                self._search_delay, self._on_search_changed_gtk4, search_query)
        else:
            self._popover.set_visible(False)

    def _on_inserted_text_gtk4(self, _entry, position, _chars, n_chars):
        self._on_changed_text_gtk4(position + n_chars)

    def _on_deleted_text_gtk4(self, _entry, position, *_args):
        self._on_changed_text_gtk4(position, is_deletion=True)

    def _on_search_changed_gtk4(self, search_query):

        self._search_delay_timer = None

        # Entry completion: reuse Gtk.DropDown's search entry for filtering
        self._search_entry.set_text(search_query)
        self._search_entry.emit("search-changed")

        if self._list_view.get_model().get_n_items() <= 1:
            self._popover.set_visible(False)
            return

        if self._popover.get_visible():
            return

        self._selected_position = None
        self._position_offset = 0

        self._popover.set_autohide(False)
        self._popover.set_visible(True)

    def _on_entry_selection_bound_changed_gtk4(self, *_args):

        if self._entry_selection_bound is not None:
            self.entry.select_region(self._entry_selection_bound, -1)

        self._entry_selection_bound = None

    def _on_focus_out_gtk4(self, *_args):

        is_visible = self._popover.get_visible()
        self._popover.set_visible(False)

        return is_visible

    def _on_list_arrow_key_accelerator_gtk4(self, _list_view, _unused, direction):

        if self._popover.get_autohide():
            return

        # Entry completion: move focus to text entry when reaching beginning/end of list
        list_model = self._list_view.get_model()
        selected_position = list_model.get_selection().get_nth(0)
        target_position = 0 if direction == "up" else list_model.get_n_items() - 1

        if selected_position != target_position:
            return

        self.entry.grab_focus()
        list_model.select_item(0, unselect_rest=True)

    def _on_dropdown_map_gtk4(self, *_args):

        # Align dropdown with entry and button
        popover_content = next(iter(self._popover))
        container_width = self.entry.get_parent().get_width()
        button_width = self._button.get_width()

        self._popover.set_offset(x_offset=-container_width + button_width, y_offset=0)
        popover_content.set_size_request(container_width, height=-1)

    def _on_dropdown_visible_gtk4(self, *_args):

        if self._list_view is None or self._selected_position is None:
            return

        new_position = (self._selected_position + self._position_offset)

        try:
            self._list_view.scroll_to(new_position, Gtk.ListScrollFlags.FOCUS | Gtk.ListScrollFlags.SELECT)

        except AttributeError:
            # Workaround for GTK <4.12 versions without scroll_to()
            direction = Gtk.DirectionType.TAB_FORWARD if self._position_offset >= 0 else Gtk.DirectionType.TAB_BACKWARD

            for _ in range(abs(self._position_offset)):
                self._list_view.child_focus(direction)

            self._list_view.get_model().select_item(new_position, unselect_rest=True)

        self._selected_position = None
        self._position_offset = 0

    def _on_entry_arrow_key_accelerator(self, _entry, _unused, direction):

        # Entry completion: scroll to the first item on arrow down, last item on arrow up
        if GTK_API_VERSION >= 4 and self._popover.get_visible():
            new_position = 0 if direction == "down" else self._list_view.get_model().get_n_items() - 1

            self._popover.child_focus(Gtk.DirectionType.TAB_FORWARD)

            try:
                self._list_view.scroll_to(new_position, Gtk.ListScrollFlags.FOCUS | Gtk.ListScrollFlags.SELECT)

            except AttributeError:
                # Workaround for GTK <4.12 versions without scroll_to()
                for _ in range(new_position):
                    self._list_view.child_focus(Gtk.DirectionType.TAB_FORWARD)

                self._list_view.get_model().select_item(new_position, unselect_rest=True)

            return True

        if not self._enable_arrow_keys:
            return True

        if not self._positions:
            return False

        # Cycle between items when pressing arrow keys inside text entry
        if GTK_API_VERSION >= 4:
            current_position = self._positions.get(self.get_text(), -1)

            if direction == "up":
                new_position = max(0, current_position - 1)
            else:
                new_position = min(current_position + 1, len(self._positions) - 1)

            self.set_selected_pos(new_position)
            self._update_item_entry_text()
            return True

        return False

    def _on_select_callback_status(self, enabled):
        self._is_popup_visible = enabled

    def _on_dropdown_visible(self, widget, param):

        visible = widget.get_property(param.name)

        # Only enable item selection callback when an item is selected from the UI
        GLib.idle_add(self._on_select_callback_status, visible, priority=GLib.PRIORITY_HIGH_IDLE)

        if not visible:
            if self._list_view is not None:
                self._selected_position = self._list_view.get_model().get_selection().get_nth(0)

            if self._popover is not None:
                self._popover.set_autohide(True)

            return

        if self.entry is not None:
            text = self.get_text()

            if text:
                self.set_selected_id(text)

        if GTK_API_VERSION >= 4:
            self._on_dropdown_visible_gtk4()

    def _on_item_selected(self, *_args):

        selected_id = self.get_selected_id()

        if selected_id is None:
            return

        if self.entry is not None:
            # Update text entry with text from the selected item
            self._update_item_entry_text()

        if not self._is_popup_visible:
            return

        if self.entry is not None:
            self.entry.grab_focus_without_selecting()

        if self._item_selected_callback is not None:
            self._item_selected_callback(self, selected_id)
