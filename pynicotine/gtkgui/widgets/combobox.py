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
from pynicotine.gtkgui.widgets.textentry import CompletionEntry
from pynicotine.gtkgui.widgets.theme import add_css_class


class ComboBox:

    def __init__(self, container, label=None, has_entry=False, has_entry_completion=False,
                 entry=None, visible=True, items=None, item_selected_callback=None):

        self.widget = None
        self.dropdown = None
        self.entry = entry
        self.item_selected_callback = item_selected_callback

        self._ids = {}
        self._positions = {}
        self._model = None
        self._button = None
        self._popover = None
        self._entry_completion = None
        self._is_popup_visible = False

        self._create_combobox(container, label, has_entry, has_entry_completion)

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

    def _create_combobox_gtk4(self, container, label, has_entry):

        self._model = Gtk.StringList()
        self.dropdown = self._button = Gtk.DropDown(
            model=self._model, valign=Gtk.Align.CENTER, visible=True
        )

        list_factory = self.dropdown.get_factory()
        button_factory = None

        if not has_entry:
            button_factory = Gtk.SignalListItemFactory()

            button_factory.connect("setup", self._on_button_factory_setup)
            button_factory.connect("bind", self._on_button_factory_bind)

        self.dropdown.set_factory(button_factory)
        self.dropdown.set_list_factory(list_factory)

        self._popover = list(self.dropdown)[-1]
        self._popover.connect("notify::visible", self._on_dropdown_visible)

        try:
            scrollable = list(self._popover.get_child())[-1]
            list_view = scrollable.get_child()
            list_view.connect("activate", self._on_item_selected)

        except AttributeError:
            pass

        if not has_entry:
            self.widget = self.dropdown

            if label:
                label.set_mnemonic_widget(self.widget)

            container.append(self.widget)
            return

        list_factory = Gtk.SignalListItemFactory()

        list_factory.connect("setup", self._on_entry_list_factory_setup)
        list_factory.connect("bind", self._on_entry_list_factory_bind)

        self.dropdown.set_list_factory(list_factory)

        self.widget = Gtk.Box(valign=Gtk.Align.CENTER, visible=True)
        self._popover.connect("map", self._on_dropdown_map)

        if self.entry is None:
            self.entry = Gtk.Entry(hexpand=True, width_chars=8, visible=True)

        if label:
            label.set_mnemonic_widget(self.entry)

        self._button.set_sensitive(False)

        self.widget.append(self.entry)
        self.widget.append(self.dropdown)

        add_css_class(self.widget, "linked")
        add_css_class(self.dropdown, "entry")
        container.append(self.widget)

    def _create_combobox_gtk3(self, container, label, has_entry, has_entry_completion):

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

        if has_entry_completion:
            add_css_class(self.dropdown, "dropdown-scrollbar")

        if self.entry is None:
            self.entry = self.dropdown.get_child()
            self.entry.set_width_chars(8)
        else:
            self.dropdown.get_child().destroy()
            self.dropdown.add(self.entry)  # pylint: disable=no-member

        self._button = list(self.entry.get_parent())[-1]
        container.add(self.widget)

    def _create_combobox(self, container, label, has_entry, has_entry_completion):

        if GTK_API_VERSION >= 4:
            self._create_combobox_gtk4(container, label, has_entry)
        else:
            self._create_combobox_gtk3(container, label, has_entry, has_entry_completion)

        if has_entry:
            Accelerator("Up", self.entry, self._on_arrow_key_accelerator, "up")
            Accelerator("Down", self.entry, self._on_arrow_key_accelerator, "down")

        if has_entry_completion:
            self._entry_completion = CompletionEntry(self.entry)

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

        if self._entry_completion:
            self._entry_completion.add_completion(item)

        self._update_item_positions(start_position=(position + 1), added=True)

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

        if self._entry_completion:
            self._entry_completion.remove_completion(item_id)

        # Update positions for items after the removed one
        self._positions.pop(item_id, None)
        self._update_item_positions(start_position=position)

    def remove_id(self, item_id):
        position = self._positions.get(item_id)
        self.remove_pos(position)

    def clear(self):

        self._ids.clear()
        self._positions.clear()

        if GTK_API_VERSION >= 4:
            self._model.splice(position=0, n_removals=self._model.get_n_items())
        else:
            self.dropdown.remove_all()

        if self.entry and self._button:
            self._button.set_sensitive(False)

        if self._entry_completion:
            self._entry_completion.clear()

    def grab_focus(self):
        self.entry.grab_focus()

    def set_visible(self, visible):
        self.widget.set_visible(visible)

    # Callbacks #

    def _on_button_factory_bind(self, _factory, list_item):
        label = list_item.get_child()
        label.set_text(list_item.get_item().get_string())

    def _on_button_factory_setup(self, _factory, list_item):
        list_item.set_child(
            Gtk.Label(ellipsize=Pango.EllipsizeMode.END, mnemonic_widget=self.widget, xalign=0))

    def _on_entry_list_factory_bind(self, _factory, list_item):
        label = list_item.get_child()
        label.set_text(list_item.get_item().get_string())

    def _on_entry_list_factory_setup(self, _factory, list_item):
        list_item.set_child(
            Gtk.Label(ellipsize=Pango.EllipsizeMode.END, xalign=0))

    def _on_arrow_key_accelerator(self, _widget, _unused, direction):

        if GTK_API_VERSION == 3:
            # Gtk.ComboBox already supports this functionality
            return False

        if not self._positions:
            return False

        if self._entry_completion:
            completion_popover = list(self.entry)[-1]

            if completion_popover.get_visible():
                # Completion popup takes precedence
                return False

        current_position = self._positions.get(self.get_text(), -1)

        if direction == "up":
            new_position = max(0, current_position - 1)
        else:
            new_position = min(current_position + 1, len(self._positions) - 1)

        self.set_selected_pos(new_position)
        self._update_item_entry_text()
        return True

    def _on_button_scroll_event(self, widget, event, *_args):
        """Prevent scrolling and pass scroll event to parent scrollable (GTK 3)"""

        scrollable = widget.get_ancestor(Gtk.ScrolledWindow)

        if scrollable is not None:
            scrollable.event(event)

        return True

    def _on_select_callback_status(self, enabled):
        self._is_popup_visible = enabled

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
        GLib.idle_add(self._on_select_callback_status, visible, priority=GLib.PRIORITY_HIGH_IDLE)

        if self.entry is None:
            return

        if not visible:
            return

        text = self.get_text()

        if text:
            self.set_selected_id(text)

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

        if self.item_selected_callback is not None:
            self.item_selected_callback(self, selected_id)
