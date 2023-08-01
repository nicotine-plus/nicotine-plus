# COPYRIGHT (C) 2020-2023 Nicotine+ Contributors
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

import sys

from locale import strxfrm

from gi.repository import Gtk
from gi.repository import Pango

from pynicotine.config import config
from pynicotine.core import core
from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.widgets.accelerator import Accelerator
from pynicotine.gtkgui.widgets.theme import add_css_class
from pynicotine.slskmessages import UserStatus


""" Text Entry-related """


class ChatEntry:
    """ Custom text entry with support for chat commands and completions """

    def __init__(self, application, widget, chat_view, completion, entity, send_message, is_chatroom=False):

        self.application = application
        self.widget = widget
        self.chat_view = chat_view
        self.completion = completion
        self.entity = entity
        self.send_message = send_message
        self.is_chatroom = is_chatroom

        widget.connect("activate", self.on_enter)
        Accelerator("<Shift>Tab", widget, self.on_tab_complete_accelerator, True)
        Accelerator("Tab", widget, self.on_tab_complete_accelerator)
        Accelerator("Down", widget, self.on_page_down_accelerator)
        Accelerator("Page_Down", widget, self.on_page_down_accelerator)
        Accelerator("Page_Up", widget, self.on_page_up_accelerator)

        # Emoji Picker (disable on Windows and macOS for now until we render emoji properly there)
        if sys.platform not in ("win32", "darwin"):
            self.widget.set_property("show-emoji-icon", True)

        # Spell Check
        if config.sections["ui"]["spellcheck"]:
            if not self.application.spell_checker:
                self.application.init_spell_checker()

            if self.application.spell_checker:
                from gi.repository import Gspell  # pylint:disable=no-name-in-module
                spell_buffer = Gspell.EntryBuffer.get_from_gtk_entry_buffer(widget.get_buffer())
                spell_buffer.set_spell_checker(self.application.spell_checker)
                spell_view = Gspell.Entry.get_from_gtk_entry(widget)
                spell_view.set_inline_spell_checking(True)

    def on_enter(self, *_args):

        if core.user_status == UserStatus.OFFLINE:
            return

        text = self.widget.get_text()

        if not text:
            return

        is_double_slash_cmd = text.startswith("//")
        is_single_slash_cmd = (text.startswith("/") and not is_double_slash_cmd)

        if not is_single_slash_cmd:
            # Regular chat message

            self.widget.set_text("")

            if is_double_slash_cmd:
                # Remove first slash and send the rest of the command as plain text
                text = text[1:]

            self.send_message(self.entity, text)
            return

        cmd_split = text.split(maxsplit=1)
        cmd = cmd_split[0]
        args = cmd_split[1] if len(cmd_split) == 2 else ""

        if self.is_chatroom:
            if not core.pluginhandler.trigger_chatroom_command_event(self.entity, cmd[1:], args):
                return

        elif not core.pluginhandler.trigger_private_chat_command_event(self.entity, cmd[1:], args):
            return

        # Clear chat entry
        self.widget.set_text("")

    def on_tab_complete_accelerator(self, widget, state, backwards=False):
        """ Tab and Shift+Tab: tab complete chat """
        return self.completion.on_tab_complete_accelerator(widget, state, backwards)

    def on_page_down_accelerator(self, *_args):
        """ Page_Down, Down: Scroll chat view to bottom, and keep input focus in entry widget """

        if self.completion and self.completion.selecting_completion:
            return False

        self.chat_view.scroll_bottom()
        return True

    def on_page_up_accelerator(self, *_args):
        """ Page_Up: Move up into view to begin scrolling message history """

        if self.completion and self.completion.selecting_completion:
            return False

        self.chat_view.widget.grab_focus()
        return True


class ChatCompletion:

    def __init__(self):

        self.completions = {}
        self.current_completions = []
        self.completion_index = 0
        self.midway_completion = False  # True if the user just used tab completion
        self.selecting_completion = False  # True if the list box is open with suggestions

        self.entry = None
        self.entry_changed_handler = None
        self.entry_completion = None
        self.model = Gtk.ListStore(str)

        self.column_numbers = list(range(self.model.get_n_columns()))

    def create_entry_completion(self):

        self.entry_completion = Gtk.EntryCompletion(model=self.model, popup_single_match=False)
        self.entry_completion.set_text_column(0)
        self.entry_completion.set_match_func(self.entry_completion_find_match)
        self.entry_completion.connect("match-selected", self.entry_completion_found_match)

    def set_entry(self, entry):

        if self.entry is not None:
            self.entry.set_completion(None)
            self.entry.disconnect(self.entry_changed_handler)

        # Reusing an existing GtkEntryCompletion object after unsetting it doesn't work well
        self.create_entry_completion()
        entry.set_completion(self.entry_completion)

        self.entry = entry
        self.entry_changed_handler = entry.connect("changed", self.on_entry_changed)

    def is_completion_enabled(self):
        return config.sections["words"]["tab"] or config.sections["words"]["dropdown"]

    def add_completion(self, item):

        if not self.is_completion_enabled():
            return

        if item in self.completions:
            return

        if config.sections["words"]["dropdown"]:
            iterator = self.model.insert_with_valuesv(-1, self.column_numbers, [item])
        else:
            iterator = None

        self.completions[item] = iterator

    def remove_completion(self, item):

        if not self.is_completion_enabled():
            return

        iterator = self.completions.pop(item)

        if iterator is not None:
            self.model.remove(iterator)

    def set_completions(self, completions):

        if self.entry_completion is None:
            return

        config_words = config.sections["words"]

        self.entry_completion.set_popup_completion(config_words["dropdown"])
        self.entry_completion.set_minimum_key_length(config_words["characters"])

        self.model.clear()
        self.completions.clear()

        if not self.is_completion_enabled():
            return

        for word in sorted(completions, key=strxfrm):
            word = str(word)

            if config_words["dropdown"]:
                iterator = self.model.insert_with_valuesv(-1, self.column_numbers, [word])
            else:
                iterator = None

            self.completions[word] = iterator

    def entry_completion_find_match(self, _completion, entry_text, iterator):

        if not entry_text:
            return False

        # Get word to the left of current position
        if " " in entry_text:
            i = self.entry.get_position()
            split_key = entry_text[:i].split(" ")[-1]
        else:
            split_key = entry_text

        if not split_key or len(split_key) < config.sections["words"]["characters"]:
            return False

        # Case-insensitive matching
        item_text = self.model.get_value(iterator, 0).lower()

        if item_text.startswith(split_key) and item_text != split_key:
            self.selecting_completion = True
            return True

        return False

    def entry_completion_found_match(self, _completion, model, iterator):

        current_text = self.entry.get_text()
        completion_value = model.get_value(iterator, 0)

        # if more than a word has been typed, we throw away the
        # one to the left of our current position because we want
        # to replace it with the matching word

        if " " in current_text:
            i = self.entry.get_position()
            prefix = " ".join(current_text[:i].split(" ")[:-1])
            suffix = " ".join(current_text[i:].split(" "))

            # add the matching word
            new_text = f"{prefix} {completion_value}{suffix}"
            # set back the whole text
            self.entry.set_text(new_text)
            # move the cursor at the end
            self.entry.set_position(len(prefix) + len(completion_value) + 1)
        else:
            self.entry.set_text(completion_value)
            self.entry.set_position(-1)

        # stop the event propagation
        return True

    def on_entry_changed(self, *_args):
        # If the entry was modified, and we don't block the handler, we're no longer completing
        self.midway_completion = self.selecting_completion = False

    def on_tab_complete_accelerator(self, _widget, _state, backwards=False):
        """ Tab and Shift+Tab: tab complete chat """

        if not config.sections["words"]["tab"]:
            return False

        text = self.entry.get_text()

        if not text:
            return False

        # "Hello there Miss<tab> how are you doing"
        # "0  3  6  9  12 15      18 21 24 27 30 33
        #   1  4  7  10 13      16 19 22 25 28 31
        #    2  5  8  11 14      17 20 23 26 29 32
        #
        # i = 16
        # last_word = Miss
        # preix = 12

        i = self.entry.get_position()
        last_word = text[:i].split(" ")[-1]
        last_word_len = len(last_word)
        preix = i - last_word_len

        if not self.midway_completion:
            if last_word_len < 1:
                return False

            last_word_lower = last_word.lower()
            self.current_completions = [
                x for x in self.completions if x.lower().startswith(last_word_lower) and len(x) >= last_word_len
            ]

            if self.current_completions:
                self.midway_completion = True
                self.completion_index = -1
                current_word = last_word
        else:
            current_word = self.current_completions[self.completion_index]

        if self.midway_completion:
            # We're still completing, block handler to avoid modifying midway_completion value
            with self.entry.handler_block(self.entry_changed_handler):
                self.entry.delete_text(i - len(current_word), i)

                direction = -1 if backwards else 1
                self.completion_index = ((self.completion_index + direction) % len(self.current_completions))

                new_word = self.current_completions[self.completion_index]
                self.entry.insert_text(new_word, preix)
                self.entry.set_position(preix + len(new_word))

        return True


class CompletionEntry:

    def __init__(self, widget, model=None, column=0):

        self.model = model
        self.column = column
        self.completions = {}

        if model is None:
            self.model = model = Gtk.ListStore(str)
            self.column_numbers = list(range(self.model.get_n_columns()))

        completion = Gtk.EntryCompletion(inline_completion=True, inline_selection=True,
                                         popup_single_match=False, model=model)
        completion.set_text_column(column)
        completion.set_match_func(self.entry_completion_find_match)
        widget.set_completion(completion)

    def add_completion(self, item):
        if item not in self.completions:
            self.completions[item] = self.model.insert_with_valuesv(-1, self.column_numbers, [item])

    def remove_completion(self, item):
        iterator = self.completions.pop(item)
        self.model.remove(iterator)

    def clear(self):
        self.model.clear()

    def entry_completion_find_match(self, _completion, entry_text, iterator):

        if not entry_text:
            return False

        item_text = self.model.get_value(iterator, self.column)

        if not item_text:
            return False

        if item_text.lower().startswith(entry_text.lower()):
            return True

        return False


class ComboBox:

    def __init__(self, container, label=None, has_entry=False, has_entry_completion=False,
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
        self._entry_completion = None
        self._item_selected_handler = None

        self._create_combobox(container, has_entry, has_entry_completion)

        if label:
            label.set_mnemonic_widget(self.widget)

        if items:
            for item, item_id in items:
                self.append(item, item_id)

        self.set_visible(visible)

    def _create_combobox_gtk4(self, container, has_entry):

        factory = self._create_factory(should_bind=not has_entry)
        list_factory = self._create_factory(ellipsize=False)
        self._model = Gtk.StringList()

        self.dropdown = self._button = Gtk.DropDown(
            factory=factory, list_factory=list_factory, model=self._model,
            valign=Gtk.Align.CENTER, visible=True
        )
        self._item_selected_handler = self.dropdown.connect("notify::selected", self._on_item_selected)

        if not has_entry:
            self.widget = self.dropdown
            container.append(self.widget)
            return

        self.widget = Gtk.Box(visible=True)

        if self.entry is None:
            self.entry = Gtk.Entry(hexpand=True, width_chars=8, visible=True)

        popover = self.dropdown.get_last_child()
        popover.connect("notify::visible", self._on_dropdown_visible)

        try:
            # Hide Gtk.DropDown label
            self.dropdown.get_first_child().get_first_child().get_first_child().set_visible(False)
        except AttributeError:
            pass

        self._button.set_sensitive(False)

        self.widget.append(self.entry)
        self.widget.append(self.dropdown)

        add_css_class(self.widget, "linked")
        container.append(self.widget)

    def _create_combobox_gtk3(self, container, has_entry, has_entry_completion):

        self.dropdown = self.widget = Gtk.ComboBoxText(has_entry=has_entry, valign=Gtk.Align.CENTER, visible=True)
        self._model = self.dropdown.get_model()

        self.dropdown.connect("scroll-event", self._on_button_scroll_event)

        if not has_entry:
            for cell in self.dropdown.get_cells():
                cell.set_property("ellipsize", Pango.EllipsizeMode.END)

            container.add(self.widget)
            return

        if has_entry_completion:
            add_css_class(self.dropdown, "dropdown-scrollbar")

        self.dropdown.connect("notify::popup-shown", self._on_dropdown_visible)
        self._item_selected_handler = self.dropdown.connect("notify::active", self._on_item_selected)

        if self.entry is None:
            self.entry = self.dropdown.get_child()
            self.entry.set_width_chars(8)
        else:
            self.dropdown.get_child().destroy()
            self.dropdown.set_property("child", self.entry)

        self._button = self.entry.get_parent().get_children()[-1]
        container.add(self.widget)

    def _create_combobox(self, container, has_entry, has_entry_completion):

        if GTK_API_VERSION >= 4:
            self._create_combobox_gtk4(container, has_entry)
        else:
            self._create_combobox_gtk3(container, has_entry, has_entry_completion)

        if has_entry:
            Accelerator("Up", self.entry, self._on_arrow_key_accelerator, "up")
            Accelerator("Down", self.entry, self._on_arrow_key_accelerator, "down")

        if has_entry_completion:
            self._entry_completion = CompletionEntry(self.entry)

    def _create_factory(self, ellipsize=True, should_bind=True):

        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._on_factory_setup, ellipsize)

        if should_bind:
            factory.connect("bind", self._on_factory_bind)

        return factory

    def _update_item_entry_text(self):
        """ Set text entry text to the same value as selected item """

        if GTK_API_VERSION == 3:
            # Already supported natively in GTK 3
            return

        item = self.dropdown.get_selected_item()

        if item is None:
            return

        item_text = item.get_string()

        if self.get_text() != item_text:
            self.set_text(item_text)

    """ General """

    def append(self, item, item_id=None):

        if item_id is None:
            item_id = item

        if GTK_API_VERSION >= 4:
            position = self._model.get_n_items()

            with self.dropdown.handler_block(self._item_selected_handler):
                self._model.append(item)
                self.set_selected_pos(Gtk.INVALID_LIST_POSITION)
        else:
            position = self._model.iter_n_children()
            self.dropdown.append_text(item)

        if self.entry:
            self._button.set_sensitive(True)

        if self._entry_completion:
            self._entry_completion.add_completion(item)

        self._ids[position] = item_id
        self._positions[item_id] = position

    def get_selected_pos(self):

        if GTK_API_VERSION >= 4:
            return self.dropdown.get_selected()

        return self.dropdown.get_active()

    def get_selected_id(self):
        return self._ids.get(self.get_selected_pos())

    def get_text(self):
        return self.entry.get_text()

    def set_selected_pos(self, position):

        if position is None:
            return

        if GTK_API_VERSION >= 4:
            self.dropdown.set_selected(position)
        else:
            self.dropdown.set_active(position)

    def set_selected_id(self, item_id):
        self.set_selected_pos(self._positions.get(item_id))

    def set_text(self, text):
        self.entry.set_text(text)

    def remove_pos(self, position):

        if GTK_API_VERSION >= 4:
            with self.dropdown.handler_block(self._item_selected_handler):
                self._model.remove(position)
        else:
            self.dropdown.remove(position)

        if self.entry and not self._ids:
            self._button.set_sensitive(False)

        if self._entry_completion:
            self._entry_completion.remove_completion(self._ids[position])

    def remove_id(self, item_id):

        position = self._positions.pop(item_id)
        self.remove_pos(position)

        # Update positions for items after the removed one
        for pos in range(position, len(self._positions)):
            next_item_id = self._ids.pop(pos + 1)

            self._ids[pos] = next_item_id
            self._positions[next_item_id] = pos

    def clear(self):

        self._ids.clear()
        self._positions.clear()

        if GTK_API_VERSION >= 4:
            with self.dropdown.handler_block(self._item_selected_handler):
                self._model.splice(position=0, n_removals=self._model.get_n_items())
        else:
            self.dropdown.remove_all()

        if self.entry:
            self._button.set_sensitive(False)

        if self._entry_completion:
            self._entry_completion.clear()

    def grab_focus(self):
        self.entry.grab_focus()

    def set_row_separator_func(self, func):
        if GTK_API_VERSION == 3:
            self.dropdown.set_row_separator_func(func)

    def set_visible(self, visible):
        self.widget.set_visible(visible)

    """ Callbacks """

    def _on_factory_bind(self, _factory, list_item):

        label = list_item.get_child()
        string_obj = list_item.get_item()

        label.set_text(string_obj.get_string())

    def _on_factory_setup(self, _factory, list_item, ellipsize):

        label = Gtk.Label(xalign=0)

        if ellipsize:
            label.set_ellipsize(Pango.EllipsizeMode.END)

        list_item.set_child(label)

    def _on_arrow_key_accelerator(self, _widget, _unused, direction):

        if not self.enable_arrow_keys:
            return True

        if GTK_API_VERSION == 3:
            # Gtk.ComboBox already supports this functionality
            return False

        current_position = self.get_selected_pos()

        if current_position == Gtk.INVALID_LIST_POSITION:
            current_position = -1

        if direction == "up":
            new_position = max(0, current_position - 1)
        else:
            new_position = min(current_position + 1, len(self._positions) - 1)

        self.set_selected_pos(new_position)
        return True

    def _on_button_scroll_event(self, *_args):
        # Prevent scrolling when up/down arrow keys are disabled
        return not self.enable_arrow_keys

    def _on_dropdown_visible(self, popover, param):

        visible = popover.get_property(param.name)

        if not visible:
            self.entry.grab_focus_without_selecting()
            return

        self.set_selected_id(self.get_text())

        if GTK_API_VERSION == 3:
            return

        # Align dropdown with entry and button
        popover = self.dropdown.get_last_child()
        scrolled_window = popover.get_child()
        container_width = self.entry.get_parent().get_width()
        button_width = self._button.get_width()

        popover.set_offset(x_offset=-container_width + button_width, y_offset=0)
        scrolled_window.set_size_request(container_width, height=-1)

    def _on_item_selected(self, *_args):

        if self.entry is None:
            return

        # Update text entry with text from the selected item
        self._update_item_entry_text()

        # Cursor is normally placed at the beginning, move to the end
        self.entry.set_position(-1)

        if self.item_selected_callback is None:
            return

        selected_id = self.get_selected_id()

        if selected_id is not None:
            self.item_selected_callback(self, selected_id)


class TextSearchBar:

    def __init__(self, textview, search_bar, entry, controller_widget=None, focus_widget=None):

        self.textview = textview
        self.search_bar = search_bar
        self.entry = entry
        self.focus_widget = focus_widget or textview

        self.search_bar.connect_entry(self.entry)

        self.entry.connect("activate", self.on_search_next_match)
        self.entry.connect("search-changed", self.on_search_changed)
        self.entry.connect("stop-search", self.on_hide_search_accelerator)

        self.entry.connect("previous-match", self.on_search_previous_match)
        self.entry.connect("next-match", self.on_search_next_match)

        if not controller_widget:
            controller_widget = textview

        Accelerator("<Primary>f", controller_widget, self.on_show_search_accelerator)
        Accelerator("Escape", controller_widget, self.on_hide_search_accelerator)
        Accelerator("<Primary>g", controller_widget, self.on_search_next_match)
        Accelerator("<Shift><Primary>g", controller_widget, self.on_search_previous_match)

    def on_search_match(self, search_type, restarted=False):

        if not self.search_bar.get_search_mode():
            return

        text_buffer = self.textview.get_buffer()
        query = self.entry.get_text()

        self.textview.emit("select-all", False)

        if search_type == "typing":
            start, end = text_buffer.get_bounds()
            iterator = start
        else:
            current = text_buffer.get_mark("insert")
            iterator = text_buffer.get_iter_at_mark(current)

        if search_type == "previous":
            match = iterator.backward_search(
                query, Gtk.TextSearchFlags.TEXT_ONLY | Gtk.TextSearchFlags.CASE_INSENSITIVE, limit=None)
        else:
            match = iterator.forward_search(
                query, Gtk.TextSearchFlags.TEXT_ONLY | Gtk.TextSearchFlags.CASE_INSENSITIVE, limit=None)

        if match is not None and len(match) == 2:
            match_start, match_end = match

            if search_type == "previous":
                text_buffer.place_cursor(match_start)
                text_buffer.select_range(match_start, match_end)
            else:
                text_buffer.place_cursor(match_end)
                text_buffer.select_range(match_end, match_start)

            self.textview.scroll_to_iter(match_start, 0, False, 0.5, 0.5)

        elif not restarted and search_type != "typing":
            start, end = text_buffer.get_bounds()

            if search_type == "previous":
                text_buffer.place_cursor(end)
            elif search_type == "next":
                text_buffer.place_cursor(start)

            self.on_search_match(search_type, restarted=True)

    def on_search_changed(self, *_args):
        self.on_search_match(search_type="typing")

    def on_search_previous_match(self, *_args):
        self.on_search_match(search_type="previous")

    def on_search_next_match(self, *_args):
        self.on_search_match(search_type="next")

    def on_hide_search_accelerator(self, *_args):
        """ Escape: hide search bar """

        self.set_visible(False)
        return True

    def on_show_search_accelerator(self, *_args):
        """ Ctrl+F: show search bar """

        self.set_visible(True)
        return True

    def set_visible(self, visible):

        if visible:
            self.search_bar.set_search_mode(True)
            self.entry.grab_focus()
            return

        self.search_bar.set_search_mode(False)
        self.focus_widget.grab_focus()
