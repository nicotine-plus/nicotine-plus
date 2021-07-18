# COPYRIGHT (C) 2020-2021 Nicotine+ Team
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

from os.path import commonprefix

from gi.repository import Gdk
from gi.repository import Gtk

from pynicotine import slskmessages
from pynicotine.config import config
from pynicotine.gtkgui.utils import connect_key_press_event
from pynicotine.gtkgui.utils import get_key_press_event_args
from pynicotine.gtkgui.utils import parse_accelerator
from pynicotine.gtkgui.widgets.textview import append_line
from pynicotine.logfacility import log
from pynicotine.utils import add_alias
from pynicotine.utils import expand_alias
from pynicotine.utils import is_alias
from pynicotine.utils import unalias


""" Text Entry/View-related """


class ChatEntry:
    """ Custom text entry with support for chat commands and completions """

    def __init__(self, frame, entry, entity, message_class, send_message, command_list, textview, is_chatroom=False):

        self.frame = frame
        self.entry = entry
        self.entity = entity
        self.message_class = message_class
        self.send_message = send_message
        self.command_list = command_list
        self.textview = textview
        self.is_chatroom = is_chatroom

        self.completion_list = None
        self.completion_iters = {}

        entry.connect("activate", self.on_enter)
        self.entry_changed_handler = entry.connect("changed", self.on_entry_changed)
        self.key_controller = connect_key_press_event(entry, self.on_key_press_event)

        # Spell Check
        if config.sections["ui"]["spellcheck"]:
            if not self.frame.spell_checker:
                self.frame.init_spell_checker()

            if self.frame.spell_checker:
                from gi.repository import Gspell
                spell_buffer = Gspell.EntryBuffer.get_from_gtk_entry_buffer(entry.get_buffer())
                spell_buffer.set_spell_checker(self.frame.spell_checker)
                spell_view = Gspell.Entry.get_from_gtk_entry(entry)
                spell_view.set_inline_spell_checking(True)

        self.midwaycompletion = False  # True if the user just used tab completion
        self.completions = {}  # Holds temp. information about tab completoin

        completion = Gtk.EntryCompletion()
        list_store = Gtk.ListStore(str)
        completion.set_model(list_store)
        completion.set_text_column(0)
        completion.set_match_func(self.entry_completion_find_match)
        completion.connect("match-selected", self.entry_completion_found_match)

        entry.set_completion(completion)
        self.column_numbers = list(range(list_store.get_n_columns()))

    def add_completion(self, item):

        if not config.sections["words"]["tab"]:
            return

        if item in self.completion_list:
            return

        self.completion_list.append(item)

        if config.sections["words"]["dropdown"]:
            model = self.entry.get_completion().get_model()
            self.completion_iters[item] = model.insert_with_valuesv(-1, self.column_numbers, [item])

    def get_completion(self, part, list):

        matches = self.get_completions(part, list)

        if not matches:
            return None, 0

        if len(matches) == 1:
            return matches[0], 1
        else:
            return commonprefix([x.lower() for x in matches]), 0

    def get_completions(self, part, list):

        lowerpart = part.lower()
        matches = [x for x in list if x.lower().startswith(lowerpart) and len(x) >= len(part)]
        return matches

    def remove_completion(self, item):

        if not config.sections["words"]["tab"]:
            return

        if item not in self.completion_list:
            return

        self.completion_list.remove(item)

        if not config.sections["words"]["dropdown"]:
            return

        model = self.entry.get_completion().get_model()
        iterator = self.completion_iters[item]
        model.remove(iterator)
        del self.completion_iters[item]

    def set_completion_list(self, completion_list):

        config_words = config.sections["words"]

        completion = self.entry.get_completion()
        completion.set_popup_single_match(not config_words["onematch"])
        completion.set_minimum_key_length(config_words["characters"])
        completion.set_inline_completion(False)

        model = completion.get_model()
        model.clear()
        self.completion_iters.clear()

        if not config_words["tab"]:
            return

        if completion_list is None:
            completion_list = []

        self.completion_list = completion_list

        if not config_words["dropdown"]:
            completion.set_popup_completion(False)
            return

        for word in completion_list:
            word = str(word)
            self.completion_iters[word] = model.insert_with_valuesv(-1, self.column_numbers, [word])

        completion.set_popup_completion(True)

    def entry_completion_find_match(self, completion, entry_text, iterator):

        if not entry_text:
            return False

        # Get word to the left of current position
        if " " in entry_text:
            ix = self.entry.get_position()
            split_key = entry_text[:ix].split(" ")[-1]
        else:
            split_key = entry_text

        if not split_key or len(split_key) < config.sections["words"]["characters"]:
            return False

        # Case-insensitive matching
        item_text = completion.get_model().get_value(iterator, 0).lower()

        if item_text.startswith(split_key) and item_text != split_key:
            return True

        return False

    def entry_completion_found_match(self, completion, model, iterator):

        current_text = self.entry.get_text()
        completion_value = model.get_value(iterator, 0)

        # if more than a word has been typed, we throw away the
        # one to the left of our current position because we want
        # to replace it with the matching word

        if " " in current_text:
            ix = self.entry.get_position()
            prefix = " ".join(current_text[:ix].split(" ")[:-1])
            suffix = " ".join(current_text[ix:].split(" "))

            # add the matching word
            new_text = "%s %s%s" % (prefix, completion_value, suffix)
            # set back the whole text
            self.entry.set_text(new_text)
            # move the cursor at the end
            self.entry.set_position(len(prefix) + len(completion_value) + 1)
        else:
            self.entry.set_text(completion_value)
            self.entry.set_position(-1)

        # stop the event propagation
        return True

    def on_enter(self, widget):

        text = self.entry.get_text()

        if not text:
            return

        if is_alias(text):
            alias_text = expand_alias(text)

            if not alias_text:
                log.add(_('Alias "%s" returned nothing'), text)
                return

            text = alias_text

        split = text.split(" ", 1)
        cmd = split[0]
        is_double_slash_cmd = cmd.startswith("//")
        is_single_slash_cmd = (cmd.startswith("/") and not is_double_slash_cmd)

        # Remove empty items created by split, if command ended with a space, e.g. '/ctcpversion '
        if len([i for i in split if i]) == 2:
            arg_self = args = split[1]
        else:
            if not self.is_chatroom:
                arg_self = self.entity
            else:
                arg_self = ""

            args = ""

        if is_single_slash_cmd and cmd + " " not in self.command_list:
            log.add(_("Command %s is not recognized"), text)
            return

        # Clear chat entry
        self.entry.set_text("")

        if not is_single_slash_cmd or cmd == "/me":
            # Regular chat message (/me is sent as plain text)

            if is_double_slash_cmd:
                # Remove first slash and send the rest of the command as plain text
                text = text[1:]

            self.send_message(self.entity, text)
            return

        if cmd in ("/alias", "/al"):
            append_line(self.textview, add_alias(args), None, "")

            if config.sections["words"]["aliases"]:
                self.frame.update_completions()

        elif cmd in ("/unalias", "/un"):
            append_line(self.textview, unalias(args), None, "")

            if config.sections["words"]["aliases"]:
                self.frame.update_completions()

        elif cmd in ("/w", "/whois", "/info"):
            if arg_self:
                self.frame.np.userinfo.request_user_info(arg_self)
                self.frame.change_main_page("userinfo")

        elif cmd in ("/b", "/browse"):
            if arg_self:
                self.frame.np.userbrowse.browse_user(arg_self)
                self.frame.change_main_page("userbrowse")

        elif cmd == "/ip":
            if arg_self:
                self.frame.np.request_ip_address(arg_self)

        elif cmd == "/pm":
            if args:
                self.frame.np.privatechats.show_user(args)
                self.frame.change_main_page("private")

        elif cmd in ("/m", "/msg"):
            if args:
                s = args.split(" ", 1)
                user = s[0]
                if len(s) == 2:
                    msg = s[1]
                else:
                    msg = None
                self.frame.np.privatechats.show_user(args)
                self.frame.np.privatechats.send_message(user, msg)
                self.frame.change_main_page("private")

        elif cmd in ("/s", "/search"):
            if args:
                self.frame.SearchMethod.set_active(0)
                self.frame.SearchEntry.set_text(args)
                self.frame.on_search(self.frame.SearchEntry)
                self.frame.change_main_page("search")

        elif cmd in ("/us", "/usearch"):
            s = args.split(" ", 1)
            if len(s) == 2:
                self.frame.SearchMethod.set_active(3)
                self.frame.SearchEntry.set_text(s[1])
                self.frame.UserSearchEntry.set_text(s[0])
                self.frame.on_search(self.frame.SearchEntry)
                self.frame.change_main_page("search")

        elif cmd in ("/rs", "/rsearch"):
            if args:
                self.frame.SearchMethod.set_active(2)
                self.frame.SearchEntry.set_text(args)
                self.frame.on_search(self.frame.SearchEntry)
                self.frame.change_main_page("search")

        elif cmd in ("/bs", "/bsearch"):
            if args:
                self.frame.SearchMethod.set_active(1)
                self.frame.SearchEntry.set_text(args)
                self.frame.on_search(self.frame.SearchEntry)
                self.frame.change_main_page("search")

        elif cmd in ("/j", "/join"):
            if args:
                self.frame.np.queue.append(slskmessages.JoinRoom(args))

        elif cmd in ("/l", "/leave", "/p", "/part"):
            if args:
                self.frame.np.queue.append(slskmessages.LeaveRoom(args))
            else:
                self.frame.np.queue.append(slskmessages.LeaveRoom(self.entity))

        elif cmd in ("/ad", "/add", "/buddy"):
            if args:
                self.frame.np.userlist.add_user(args)

        elif cmd in ("/rem", "/unbuddy"):
            if args:
                self.frame.np.userlist.remove_user(args)

        elif cmd == "/ban":
            if args:
                self.frame.np.network_filter.ban_user(args)

        elif cmd == "/ignore":
            if args:
                self.frame.np.network_filter.ignore_user(args)

        elif cmd == "/ignoreip":
            if args:
                self.frame.np.network_filter.ignore_ip(args)

        elif cmd == "/unban":
            if args:
                self.frame.np.network_filter.unban_user(args)

        elif cmd == "/unignore":
            if args:
                self.frame.np.network_filter.unignore_user(args)

        elif cmd == "/ctcpversion":
            if arg_self:
                self.frame.np.privatechats.show_user(arg_self)
                self.frame.np.privatechats.send_message(
                    arg_self, self.frame.privatechats.CTCP_VERSION, bytestring=True)

        elif cmd in ("/clear", "/cl"):
            self.textview.get_buffer().set_text("")

        elif cmd in ("/a", "/away"):
            self.frame.on_away()

        elif cmd in ("/q", "/quit", "/exit"):
            self.frame.on_quit()
            return  # Avoid gsignal warning

        elif cmd in ("/c", "/close"):
            self.frame.privatechats.users[self.entity].on_close()

        elif cmd == "/now":
            self.frame.np.now_playing.display_now_playing(
                callback=lambda np_message: self.send_message(self.entity, np_message))

        elif cmd == "/rescan":
            # Rescan public shares if needed
            if not config.sections["transfers"]["friendsonly"] and config.sections["transfers"]["shared"]:
                self.frame.on_rescan()

            # Rescan buddy shares if needed
            if config.sections["transfers"]["enablebuddyshares"]:
                self.frame.on_buddy_rescan()

        elif cmd in ("/tick", "/t"):
            self.frame.np.queue.append(slskmessages.RoomTickerSet(self.entity, args))

        elif cmd == "/tickers":
            self.frame.chatrooms.joinedrooms[self.entity].show_tickers()

        elif cmd == "/toggle":
            if args:
                self.frame.np.pluginhandler.toggle_plugin(args)

        elif self.is_chatroom:
            self.frame.np.pluginhandler.trigger_public_command_event(self.entity, cmd[1:], args)

        elif not self.is_chatroom:
            self.frame.np.pluginhandler.trigger_private_command_event(self.entity, cmd[1:], args)

    def on_entry_changed(self, *args):
        # If the entry was modified, and we don't block the handler, we're no longer completing
        self.midwaycompletion = False

    def on_key_press_event(self, *args):

        keyval, keycode, state = get_key_press_event_args(*args)
        keycodes, mods = parse_accelerator("Tab")

        if keycode not in keycodes:
            return False

        if not config.sections["words"]["tab"]:
            return False

        # "Hello there Miss<tab> how are you doing"
        # "0  3  6  9  12 15      18 21 24 27 30 33
        #   1  4  7  10 13      16 19 22 25 28 31
        #    2  5  8  11 14      17 20 23 26 29 32
        #
        # ix = 16
        # text = Miss
        # preix = 12
        ix = self.entry.get_position()
        text = self.entry.get_text()[:ix].split(" ")[-1]
        preix = ix - len(text)

        if not config.sections["words"]["cycle"]:
            completion, single = self.get_completion(text, self.completion_list)
            if completion:
                if single and ix == len(text) and not text.startswith("/"):
                    completion += ": "
                self.entry.delete_text(preix, ix)
                self.entry.insert_text(completion, preix)
                self.entry.set_position(preix + len(completion))

            return True

        if not self.midwaycompletion:
            self.completions['completions'] = self.get_completions(text, self.completion_list)

            if self.completions['completions']:
                self.midwaycompletion = True
                self.completions['currentindex'] = -1
                currentnick = text
        else:
            currentnick = self.completions['completions'][self.completions['currentindex']]

        if self.midwaycompletion:
            # We're still completing, block handler to avoid modifying midwaycompletion value
            with self.entry.handler_block(self.entry_changed_handler):
                self.entry.delete_text(ix - len(currentnick), ix)
                direction = 1  # Forward cycle

                if state & Gdk.ModifierType.SHIFT_MASK:
                    direction = -1  # Backward cycle

                self.completions['currentindex'] = ((self.completions['currentindex'] + direction) %
                                                    len(self.completions['completions']))

                newnick = self.completions['completions'][self.completions['currentindex']]
                self.entry.insert_text(newnick, preix)
                self.entry.set_position(preix + len(newnick))

        return True


class TextSearchBar:

    def __init__(self, textview, search_bar, entry):

        self.textview = textview
        self.search_bar = search_bar
        self.entry = entry

        self.search_bar.connect_entry(self.entry)

        self.entry.connect("activate", self.on_search_next_match)
        self.entry.connect("search-changed", self.on_search_changed)

        self.entry.connect("previous-match", self.on_search_previous_match)
        self.entry.connect("next-match", self.on_search_next_match)

        self.key_controller = connect_key_press_event(self.textview, self.on_key_press_event)

    def on_search_match(self, search_type, restarted=False):

        buffer = self.textview.get_buffer()
        query = self.entry.get_text()

        self.textview.emit("select-all", False)

        if search_type == "typing":
            start, end = buffer.get_bounds()
            iterator = start
        else:
            current = buffer.get_mark("insert")
            iterator = buffer.get_iter_at_mark(current)

        if search_type == "previous":
            match = iterator.backward_search(
                query, Gtk.TextSearchFlags.TEXT_ONLY | Gtk.TextSearchFlags.CASE_INSENSITIVE, limit=None)
        else:
            match = iterator.forward_search(
                query, Gtk.TextSearchFlags.TEXT_ONLY | Gtk.TextSearchFlags.CASE_INSENSITIVE, limit=None)

        if match is not None and len(match) == 2:
            match_start, match_end = match

            if search_type == "previous":
                buffer.place_cursor(match_start)
                buffer.select_range(match_start, match_end)
            else:
                buffer.place_cursor(match_end)
                buffer.select_range(match_end, match_start)

            self.textview.scroll_to_iter(match_start, 0, False, 0.5, 0.5)

        elif not restarted and search_type != "typing":
            start, end = buffer.get_bounds()

            if search_type == "previous":
                buffer.place_cursor(end)
            elif search_type == "next":
                buffer.place_cursor(start)

            self.on_search_match(search_type, restarted=True)

    def on_search_changed(self, *args):
        self.on_search_match(search_type="typing")

    def on_search_previous_match(self, *args):
        self.on_search_match(search_type="previous")

    def on_search_next_match(self, *args):
        self.on_search_match(search_type="next")

    def on_key_press_event(self, *args):

        keyval, keycode, state = get_key_press_event_args(*args)
        keycodes, mods = parse_accelerator("<Primary>f")

        if state & mods and keycode in keycodes:
            self.show_search_bar()
            return True

        return False

    def show_search_bar(self):
        self.search_bar.set_search_mode(True)
        self.entry.grab_focus()


def clear_entry(entry):

    if Gtk.get_major_version() == 4:
        completion = entry.get_completion()
        completion.set_minimum_key_length(1)
        entry.set_text("")
        completion.set_minimum_key_length(0)

    else:
        completion = entry.get_completion()
        entry.set_completion(None)
        entry.set_text("")
        entry.set_completion(completion)
