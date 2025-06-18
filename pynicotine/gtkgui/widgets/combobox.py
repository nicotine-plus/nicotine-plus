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
        self._enable_arrow_keys = enable_arrow_keys
        self._enable_word_completion = enable_word_completion
        self._item_selected_callback = item_selected_callback

        self._ids = {}
        self._positions = {}
        self._completions = {}
        self._model = None
        self._entry_completion = None
        self._completion_model = None
        self._button = None
        self._popover = None
        self._list_view = None
        self._is_popup_visible = False
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
        self.__dict__.clear()

    def _create_combobox_gtk4(self, container, label, has_entry, has_dropdown):

        self._model = Gtk.StringList()
        self.dropdown = self._button = Gtk.DropDown(
            model=self._model, valign=Gtk.Align.CENTER, visible=True
        )

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

    def _create_combobox_gtk3(self, container, label, has_entry, has_dropdown):

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

    def _create_combobox(self, container, label, has_entry, has_entry_completion, has_dropdown):

        if GTK_API_VERSION >= 4:
            self._create_combobox_gtk4(container, label, has_entry, has_dropdown)
        else:
            self._create_combobox_gtk3(container, label, has_entry, has_dropdown)

        if not has_entry:
            return

        Accelerator("Up", self.entry, self._on_arrow_key_accelerator, "up")
        Accelerator("Down", self.entry, self._on_arrow_key_accelerator, "down")

        if not has_entry_completion:
            return

        self._completion_model = Gtk.ListStore(str)
        self._entry_completion = Gtk.EntryCompletion(
            inline_completion=not self._enable_word_completion,
            inline_selection=not self._enable_word_completion, popup_single_match=False,
            model=self._completion_model
        )
        self._entry_completion.set_text_column(0)
        self._entry_completion.set_match_func(self._entry_completion_find_match)
        self._entry_completion.connect("match-selected", self._entry_completion_found_match)

        self.entry.set_completion(self._entry_completion)
        self.patch_popover_hide_broadway(self.entry)

    def _entry_completion_find_match(self, _completion, entry_text, iterator):

        if not entry_text:
            return False

        item_text = self._completion_model.get_value(iterator, 0)

        if not item_text:
            return False

        if self._enable_word_completion:
            # Get word to the left of current position
            if " " in entry_text:
                i = self.entry.get_position()
                split_key = entry_text[:i].split(" ")[-1]
            else:
                split_key = entry_text

            if not split_key or len(split_key) < self._entry_completion.get_minimum_key_length():
                return False

            # Case-insensitive matching
            item_text = item_text.lower()

            if item_text.startswith(split_key) and item_text != split_key:
                return True

        elif item_text.lower().startswith(entry_text.lower()):
            return True

        return False

    def _entry_completion_found_match(self, _completion, _model, iterator):

        if not self._enable_word_completion:
            return False

        completion_value = self._completion_model.get_value(iterator, 0)
        current_text = self.entry.get_text()

        # if more than a word has been typed, we throw away the
        # one to the left of our current position because we want
        # to replace it with the matching word

        if " " in current_text:
            i = self.entry.get_position()
            prefix = " ".join(current_text[:i].split(" ")[:-1])
            suffix = " ".join(current_text[i:].split(" "))

            # add the matching word
            new_text = f"{prefix} {completion_value}{suffix}"
            print(new_text)
            # set back the whole text
            self.entry.set_text(new_text)
            # move the cursor at the end
            self.entry.set_position(len(prefix) + len(completion_value) + 1)
        else:
            self.entry.set_text(completion_value)
            self.entry.set_position(-1)

        # stop the event propagation
        return True

    @classmethod
    def patch_popover_hide_broadway(cls, entry):

        # Workaround for GTK 4 bug where broadwayd uses a lot of CPU after hiding popover
        if GTK_API_VERSION >= 4 and os.environ.get("GDK_BACKEND") == "broadway":
            completion_popover = list(entry)[-1]
            completion_popover.connect("hide", cls._on_popover_hide_broadway)

    @staticmethod
    def _on_popover_hide_broadway(popover):
        popover.unrealize()

    def _update_item_entry_text(self):
        """Set text entry text to the same value as selected item."""

        if GTK_API_VERSION >= 4:
            item = self.dropdown.get_selected_item()

            if item is None:
                return

            item_text = item.get_string()

            if self.get_text() != item_text:
                self.set_text(item_text)

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

        if self._completion_model:
            self._completions[item] = self._completion_model.insert_with_valuesv(-1, [0], [item])

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

        if self._completion_model:
            iterator = self._completions.pop(item_id, None)

            if iterator is not None:
                self._completion_model.remove(iterator)

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

        if self._completion_model:
            self._completions.clear()
            self._completion_model.clear()

    def grab_focus(self):
        self.entry.grab_focus()

    def set_completion_popup_enabled(self, enabled):
        self._entry_completion.set_popup_completion(enabled)

    def set_completion_min_key_length(self, length):
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

            self._list_view.get_model().select_item(new_position, True)

        self._selected_position = None
        self._position_offset = 0

    def _on_arrow_key_accelerator(self, _widget, _unused, direction):

        if GTK_API_VERSION >= 4 and self._completion_model:
            completion_popover = list(self.entry)[-1]

            if completion_popover.get_visible():
                # Completion popup takes precedence
                return False

        if not self._enable_arrow_keys:
            return True

        if not self._positions:
            return False

        if GTK_API_VERSION == 3:
            return False

        current_position = self._positions.get(self.get_text(), -1)

        if direction == "up":
            new_position = max(0, current_position - 1)
        else:
            new_position = min(current_position + 1, len(self._positions) - 1)

        self.set_selected_pos(new_position)
        self._update_item_entry_text()
        return True

    def _on_select_callback_status(self, enabled):
        self._is_popup_visible = enabled

    def _on_dropdown_visible(self, widget, param):

        visible = widget.get_property(param.name)

        # Only enable item selection callback when an item is selected from the UI
        GLib.idle_add(self._on_select_callback_status, visible, priority=GLib.PRIORITY_HIGH_IDLE)

        if not visible:
            if self._list_view is not None:
                self._selected_position = self._list_view.get_model().get_selection().get_nth(0)
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
