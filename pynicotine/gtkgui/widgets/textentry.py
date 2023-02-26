# COPYRIGHT (C) 2020-2022 Nicotine+ Contributors
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

from os.path import commonprefix

from gi.repository import Gtk

from pynicotine.config import config
from pynicotine.core import core
from pynicotine.gtkgui.widgets.accelerator import Accelerator
from pynicotine.slskmessages import UserStatus


""" Text Entry-related """


class ChatEntry:
    """ Custom text entry with support for chat commands and completions """

    def __init__(self, application, widget, completion, entity, message_class, send_message, is_chatroom=False):

        self.application = application
        self.widget = widget
        self.completion = completion
        self.entity = entity
        self.message_class = message_class
        self.send_message = send_message
        self.is_chatroom = is_chatroom

        widget.connect("activate", self.on_enter)
        Accelerator("<Shift>Tab", widget, self.on_tab_complete_accelerator, True)
        Accelerator("Tab", widget, self.on_tab_complete_accelerator)

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

        if len(cmd_split) == 2:
            args = arg_self = cmd_split[1]
        else:
            args = ""
            arg_self = "" if self.is_chatroom else self.entity

        if cmd == "/ctcpversion":
            if arg_self:
                core.privatechat.show_user(arg_self)
                core.privatechat.send_message(arg_self, core.privatechat.CTCP_VERSION)

        elif cmd == "/now":
            core.now_playing.display_now_playing(
                callback=lambda np_message: self.send_message(self.entity, np_message))

        elif self.is_chatroom:
            if not core.pluginhandler.trigger_chatroom_command_event(self.entity, cmd[1:], args):
                return

        elif not core.pluginhandler.trigger_private_chat_command_event(self.entity, cmd[1:], args):
            return

        # Clear chat entry
        self.widget.set_text("")

    def on_tab_complete_accelerator(self, widget, state, backwards=False):
        """ Tab and Shift+Tab: tab complete chat """
        return self.completion.on_tab_complete_accelerator(widget, state, backwards)


class ChatCompletion:

    def __init__(self):

        self.completion_list = []
        self.completion_iters = {}

        self.midwaycompletion = False  # True if the user just used tab completion
        self.completions = {}  # Holds temp. information about tab completoin

        self.entry = None
        self.entry_changed_handler = None
        self.entry_completion = None
        self.model = Gtk.ListStore(str)

        self.column_numbers = list(range(self.model.get_n_columns()))

    def create_entry_completion(self):

        self.entry_completion = Gtk.EntryCompletion(model=self.model)
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

    def add_completion(self, item):

        if not config.sections["words"]["tab"]:
            return

        if item in self.completion_list:
            return

        self.completion_list.append(item)

        if config.sections["words"]["dropdown"]:
            self.completion_iters[item] = self.model.insert_with_valuesv(-1, self.column_numbers, [item])

    def get_completion(self, part, completion_list):

        matches = self.get_completions(part, completion_list)

        if not matches:
            return None, 0

        if len(matches) == 1:
            return matches[0], 1

        return commonprefix([x.lower() for x in matches]), 0

    @staticmethod
    def get_completions(part, completion_list):

        lowerpart = part.lower()
        matches = [x for x in completion_list if x.lower().startswith(lowerpart) and len(x) >= len(part)]
        return matches

    def remove_completion(self, item):

        if not config.sections["words"]["tab"]:
            return

        if item not in self.completion_list:
            return

        self.completion_list.remove(item)

        if not config.sections["words"]["dropdown"]:
            return

        iterator = self.completion_iters[item]
        self.model.remove(iterator)
        del self.completion_iters[item]

    def set_completion_list(self, completion_list):

        if self.entry_completion is None:
            return

        config_words = config.sections["words"]

        self.entry_completion.set_popup_single_match(not config_words["onematch"])
        self.entry_completion.set_minimum_key_length(config_words["characters"])
        self.entry_completion.set_inline_completion(False)

        self.model.clear()
        self.completion_iters.clear()

        if not config_words["tab"]:
            return

        if completion_list is None:
            completion_list = []

        self.completion_list = completion_list

        if not config_words["dropdown"]:
            self.entry_completion.set_popup_completion(False)
            return

        for word in completion_list:
            word = str(word)
            self.completion_iters[word] = self.model.insert_with_valuesv(-1, self.column_numbers, [word])

        self.entry_completion.set_popup_completion(True)

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
        self.midwaycompletion = False

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
        # text = Miss
        # preix = 12
        i = self.entry.get_position()
        text = text[:i].split(" ")[-1]
        preix = i - len(text)

        if not config.sections["words"]["cycle"]:
            completion, single = self.get_completion(text, self.completion_list)
            if completion:
                if single and i == len(text) and not text.startswith("/"):
                    completion += ": "
                self.entry.delete_text(preix, i)
                self.entry.insert_text(completion, preix)
                self.entry.set_position(preix + len(completion))

            return True

        if not self.midwaycompletion:
            self.completions["completions"] = self.get_completions(text, self.completion_list)

            if self.completions["completions"]:
                self.midwaycompletion = True
                self.completions["currentindex"] = -1
                currentnick = text
        else:
            currentnick = self.completions["completions"][self.completions["currentindex"]]

        if self.midwaycompletion:
            # We're still completing, block handler to avoid modifying midwaycompletion value
            with self.entry.handler_block(self.entry_changed_handler):
                self.entry.delete_text(i - len(currentnick), i)
                direction = 1  # Forward cycle

                if backwards:
                    direction = -1  # Backward cycle

                self.completions["currentindex"] = ((self.completions["currentindex"] + direction) %
                                                    len(self.completions["completions"]))

                newnick = self.completions["completions"][self.completions["currentindex"]]
                self.entry.insert_text(newnick, preix)
                self.entry.set_position(preix + len(newnick))

        return True


class CompletionEntry:

    def __init__(self, widget, model, column=0):

        self.model = model
        self.column = column

        completion = Gtk.EntryCompletion(inline_completion=True, inline_selection=True,
                                         popup_single_match=False, model=model)
        completion.set_text_column(column)
        completion.set_match_func(self.entry_completion_find_match)
        widget.set_completion(completion)

    def entry_completion_find_match(self, _completion, entry_text, iterator):

        if not entry_text:
            return False

        item_text = self.model.get_value(iterator, self.column)

        if not item_text:
            return False

        if item_text.lower().startswith(entry_text.lower()):
            return True

        return False


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
