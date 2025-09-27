# SPDX-FileCopyrightText: 2020-2025 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

import gi
from gi.repository import Gtk

from pynicotine.config import config
from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.widgets.accelerator import Accelerator
from pynicotine.gtkgui.widgets.combobox import ComboBox
from pynicotine.gtkgui.widgets.theme import add_css_class


class ChatEntry:
    """Custom text entry with support for chat commands and completions."""

    def __init__(self, application, send_message_callback, command_callback, enable_spell_check=False):

        self.application = application
        self.container = Gtk.Box(visible=True)
        self.widget = Gtk.Entry(
            hexpand=True, placeholder_text=_("Send message…"), primary_icon_name="mail-send-symbolic",
            sensitive=False, show_emoji_icon=True, width_chars=8, visible=True
        )

        # Create accelerators early to override ComboBox accelerators
        Accelerator("Down", self.widget, self.on_page_down_accelerator)
        Accelerator("Page_Down", self.widget, self.on_page_down_accelerator)
        Accelerator("Up", self.widget, self.on_page_up_accelerator)
        Accelerator("Page_Up", self.widget, self.on_page_up_accelerator)

        self.combobox = ComboBox(
            container=self.container, has_entry=True, has_dropdown=False, entry=self.widget,
            enable_arrow_keys=False, enable_word_completion=True, visible=True
        )

        self.send_message_callback = send_message_callback
        self.command_callback = command_callback
        self.spell_checker = None
        self.entity = None
        self.chat_view = None
        self.unsent_messages = {}
        self.completions = {}
        self.current_completions = []
        self.completion_index = 0
        self.midway_completion = False  # True if the user just used tab completion
        self.is_inserting_completion = False

        self.widget.connect("activate", self.on_send_message)
        self.widget.connect("changed", self.on_changed)
        self.widget.connect("icon-press", self.on_icon_pressed)

        Accelerator("<Shift>Tab", self.widget, self.on_tab_complete_accelerator, True)
        Accelerator("Tab", self.widget, self.on_tab_complete_accelerator)

        self.set_spell_check_enabled(enable_spell_check)

    def destroy(self):

        if self.spell_checker is not None:
            self.spell_checker.destroy()

        self.__dict__.clear()

    def clear_unsent_message(self, entity):
        self.unsent_messages.pop(entity, None)

    def grab_focus(self):
        self.widget.grab_focus()

    def grab_focus_without_selecting(self):
        self.widget.grab_focus_without_selecting()

    def get_buffer(self):
        return self.widget.get_buffer()

    def get_position(self):
        return self.widget.get_position()

    def get_sensitive(self):
        return self.widget.get_sensitive()

    def get_text(self):
        return self.widget.get_text()

    def is_completion_enabled(self):
        return config.sections["words"]["tab"] or config.sections["words"]["dropdown"]

    def insert_text(self, new_text, position):
        self.widget.insert_text(new_text, position)

    def delete_text(self, start_pos, end_pos):
        self.widget.delete_text(start_pos, end_pos)

    def add_completion(self, item):

        if not self.is_completion_enabled():
            return

        if item in self.completions:
            return

        if config.sections["words"]["dropdown"]:
            self.combobox.append(item)

        self.completions[item] = None

    def remove_completion(self, item):

        if not self.is_completion_enabled():
            return

        self.combobox.remove_id(item)

    def set_parent(self, entity=None, container=None, chat_view=None):

        if self.entity:
            self.unsent_messages[self.entity] = self.widget.get_text()

        self.entity = entity
        self.chat_view = chat_view

        parent = self.container.get_parent()

        if parent is not None:
            parent.remove(self.container)

        if container is None:
            return

        unsent_message = self.unsent_messages.get(entity, "")

        if GTK_API_VERSION >= 4:
            container.append(self.container)  # pylint: disable=no-member
        else:
            container.add(self.container)     # pylint: disable=no-member

        self.widget.set_text(unsent_message)
        self.widget.set_position(-1)

    def set_completions(self, completions):

        config_words = config.sections["words"]

        self.combobox.set_completion_popup_enabled(config_words["dropdown"])
        self.combobox.set_completion_min_key_length(config_words["characters"])

        self.combobox.clear()
        self.completions.clear()

        if not self.is_completion_enabled():
            return

        for word in sorted(completions):
            word = str(word)

            if config_words["dropdown"]:
                self.combobox.append(word)

            self.completions[word] = None

    def set_spell_check_enabled(self, enabled):

        if self.spell_checker is not None:
            self.spell_checker.set_enabled(enabled)
            return

        if enabled and SpellChecker.is_available():
            self.spell_checker = SpellChecker(self.widget)

    def set_position(self, position):
        self.widget.set_position(position)

    def set_sensitive(self, sensitive):
        self.widget.set_sensitive(sensitive)

    def set_text(self, text):
        self.widget.set_text(text)

    def set_visible(self, visible):
        self.widget.set_visible(visible)

    def on_send_message(self, *_args):

        text = self.widget.get_text().strip()

        if not text:
            self.chat_view.scroll_bottom()
            return

        is_double_slash_cmd = text.startswith("//")
        is_single_slash_cmd = (text.startswith("/") and not is_double_slash_cmd)

        if not is_single_slash_cmd:
            # Regular chat message

            self.widget.set_text("")

            if is_double_slash_cmd:
                # Remove first slash and send the rest of the command as plain text
                text = text[1:]

            self.send_message_callback(self.entity, text)
            return

        cmd, _separator, args = text.partition(" ")
        args = args.strip()

        if not self.command_callback(self.entity, cmd[1:], args):
            return

        # Clear chat entry
        self.widget.set_text("")

    def on_icon_pressed(self, _entry, icon_pos, *_args):
        if icon_pos == Gtk.EntryIconPosition.PRIMARY:
            self.on_send_message()

    def on_changed(self, *_args):

        # If the entry was modified, and we don't block entry_changed_handler, we're no longer completing
        if not self.is_inserting_completion:
            self.midway_completion = False

    def on_tab_complete_accelerator(self, _widget, _state, backwards=False):
        """Tab and Shift+Tab: tab complete chat."""

        if not config.sections["words"]["tab"]:
            return False

        text = self.widget.get_text()

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

        i = self.widget.get_position()
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
            # We're still completing, block entry_changed_handler to avoid modifying midway_completion value
            self.is_inserting_completion = True
            self.widget.delete_text(i - len(current_word), i)

            direction = -1 if backwards else 1
            self.completion_index = ((self.completion_index + direction) % len(self.current_completions))

            new_word = self.current_completions[self.completion_index]
            self.widget.insert_text(new_word, preix)
            self.widget.set_position(preix + len(new_word))
            self.is_inserting_completion = False

        return True

    def on_page_down_accelerator(self, *_args):
        """Page_Down, Down - Scroll chat view to bottom, and keep input focus in
        entry widget."""

        if self.widget.get_text_length():
            return False

        self.chat_view.scroll_bottom()
        return True

    def on_page_up_accelerator(self, *_args):
        """Page_Up, Up - Move up into view to begin scrolling message history."""

        if self.widget.get_text_length():
            return False

        self.chat_view.grab_focus()
        return True


class SpellChecker:

    checker = None
    module = None

    def __init__(self, entry):

        self.buffer = None
        self.entry = None

        self._set_entry(entry)

    @classmethod
    def _load_module(cls):

        if GTK_API_VERSION >= 4:
            # No spell checkers available in GTK 4 yet
            return

        if SpellChecker.module is not None:
            return

        try:
            gi.require_version("Gspell", "1")
            from gi.repository import Gspell
            SpellChecker.module = Gspell

        except (ImportError, ValueError):
            pass

    def _set_entry(self, entry):

        if self.entry is not None:
            return

        # Attempt to load spell check module in case it was recently installed
        self._load_module()

        if SpellChecker.module is None:
            return

        if SpellChecker.checker is None:
            SpellChecker.checker = SpellChecker.module.Checker()

        self.buffer = SpellChecker.module.EntryBuffer.get_from_gtk_entry_buffer(entry.get_buffer())
        self.buffer.set_spell_checker(SpellChecker.checker)

        self.entry = SpellChecker.module.Entry.get_from_gtk_entry(entry)
        self.entry.set_inline_spell_checking(True)

    @classmethod
    def is_available(cls):
        cls._load_module()
        return bool(SpellChecker.module)

    def set_enabled(self, enabled):
        self.entry.set_inline_spell_checking(enabled)

    def destroy(self):
        self.__dict__.clear()


class TextSearchBar:

    def __init__(self, textview, search_bar, controller_widget=None, focus_widget=None,
                 placeholder_text=None):

        self.textview = textview
        self.search_bar = search_bar
        self.focus_widget = focus_widget

        container = Gtk.Box(spacing=6, visible=True)
        self.entry = Gtk.SearchEntry(
            max_width_chars=75, placeholder_text=placeholder_text, width_chars=24, visible=True
        )
        self.previous_button = Gtk.Button(tooltip_text=_("Find Previous Match"), visible=True)
        self.next_button = Gtk.Button(tooltip_text=_("Find Next Match"), visible=True)

        if GTK_API_VERSION >= 4:
            self.previous_button.set_icon_name("go-up-symbolic")                   # pylint: disable=no-member
            self.next_button.set_icon_name("go-down-symbolic")                     # pylint: disable=no-member

            container.append(self.entry)                                           # pylint: disable=no-member
            container.append(self.previous_button)                                 # pylint: disable=no-member
            container.append(self.next_button)                                     # pylint: disable=no-member
            self.search_bar.set_child(container)                                   # pylint: disable=no-member
        else:
            self.previous_button.set_image(Gtk.Image(icon_name="go-up-symbolic"))  # pylint: disable=no-member
            self.next_button.set_image(Gtk.Image(icon_name="go-down-symbolic"))    # pylint: disable=no-member

            container.add(self.entry)                                              # pylint: disable=no-member
            container.add(self.previous_button)                                    # pylint: disable=no-member
            container.add(self.next_button)                                        # pylint: disable=no-member
            self.search_bar.add(container)                                         # pylint: disable=no-member

        if not controller_widget:
            controller_widget = textview

        for button in (self.previous_button, self.next_button):
            add_css_class(button, "flat")

        self.search_bar.connect_entry(self.entry)

        self.entry.connect("activate", self.on_search_next_match)
        self.entry.connect("search-changed", self.on_search_changed)
        self.entry.connect("stop-search", self.on_hide_search_accelerator)

        self.entry.connect("previous-match", self.on_search_previous_match)
        self.entry.connect("next-match", self.on_search_next_match)
        self.previous_button.connect("clicked", self.on_search_previous_match)
        self.next_button.connect("clicked", self.on_search_next_match)

        Accelerator("Up", self.entry, self.on_search_previous_match)
        Accelerator("Down", self.entry, self.on_search_next_match)
        Accelerator("<Primary>f", controller_widget, self.on_show_search_accelerator)
        Accelerator("Escape", controller_widget, self.on_hide_search_accelerator)

        for accelerator in ("<Primary>g", "F3"):
            Accelerator(accelerator, controller_widget, self.on_search_next_match)

        for accelerator in ("<Shift><Primary>g", "<Shift>F3"):
            Accelerator(accelerator, controller_widget, self.on_search_previous_match)

    def destroy(self):
        self.__dict__.clear()

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
        return True

    def on_search_next_match(self, *_args):
        self.on_search_match(search_type="next")
        return True

    def on_hide_search_accelerator(self, *_args):
        """Escape - hide search bar."""

        self.set_visible(False)
        return True

    def on_show_search_accelerator(self, *_args):
        """Ctrl+F - show search bar."""

        self.set_visible(True)
        return True

    def set_visible(self, visible):

        self.search_bar.set_search_mode(visible)

        if visible:
            text_buffer = self.textview.get_buffer()
            selection_bounds = text_buffer.get_selection_bounds()

            if selection_bounds:
                selection_start, selection_end = selection_bounds
                selection_content = text_buffer.get_text(
                    selection_start, selection_end, include_hidden_chars=True)

                if self.entry.get_text().lower() != selection_content.lower():
                    self.entry.set_text(selection_content)

            self.entry.grab_focus()
            self.entry.set_position(-1)
            return

        if self.focus_widget is not None and self.focus_widget.get_sensitive():
            self.focus_widget.grab_focus()
            return

        self.textview.grab_focus()
