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
from pynicotine.gtkgui.utils import append_line
from pynicotine.gtkgui.utils import auto_replace
from pynicotine.gtkgui.utils import connect_key_press_event
from pynicotine.gtkgui.utils import get_key_press_event_args
from pynicotine.gtkgui.utils import parse_accelerator
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

        entry.connect("activate", self.on_enter)
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
            model.insert_with_valuesv(-1, self.column_numbers, [item])

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
        matches = [x for x in set(list) if x.lower().startswith(lowerpart) and len(x) >= len(part)]
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
        iterator = model.get_iter_first()

        while iterator is not None:
            name = model.get_value(iterator, 0)

            if name == item:
                model.remove(iterator)
                break

            iterator = model.iter_next(iterator)

    def set_completion_list(self, completion_list):

        config_words = config.sections["words"]

        completion = self.entry.get_completion()
        completion.set_popup_single_match(not config_words["onematch"])
        completion.set_minimum_key_length(config_words["characters"])
        completion.set_inline_completion(False)

        model = completion.get_model()
        model.clear()

        if not config_words["tab"]:
            return

        if completion_list is None:
            completion_list = []

        completion.set_popup_completion(False)

        if config_words["dropdown"]:
            for word in completion_list:
                model.insert_with_valuesv(-1, self.column_numbers, [word])

            completion.set_popup_completion(True)

        self.completion_list = completion_list

    def entry_completion_find_match(self, completion, entry_text, iterator):

        entry = completion.get_entry()
        model = completion.get_model()
        item_text = model.get_value(iterator, 0)
        ix = entry.get_position()

        if entry_text is None or entry_text == "" or entry_text.isspace() or item_text is None:
            return False

        # Get word to the left of current position
        if " " in entry_text:
            split_key = entry_text[:ix].split(" ")[-1]
        else:
            split_key = entry_text

        if split_key.isspace() or split_key == "" or len(split_key) < config.sections["words"]["characters"]:
            return False

        # case-insensitive matching
        if item_text.lower().startswith(split_key) and item_text.lower() != split_key:
            return True

        return False

    def entry_completion_found_match(self, completion, model, iterator):

        entry = completion.get_entry()
        current_text = entry.get_text()
        ix = entry.get_position()
        # if more than a word has been typed, we throw away the
        # one to the left of our current position because we want
        # to replace it with the matching word

        if " " in current_text:
            prefix = " ".join(current_text[:ix].split(" ")[:-1])
            suffix = " ".join(current_text[ix:].split(" "))

            # add the matching word
            new_text = "%s %s%s" % (prefix, model[iterator][0], suffix)
            # set back the whole text
            entry.set_text(new_text)
            # move the cursor at the end
            entry.set_position(len(prefix) + len(model[iterator][0]) + 1)
        else:
            new_text = "%s" % (model[iterator][0])
            entry.set_text(new_text)
            entry.set_position(-1)

        # stop the event propagation
        return True

    def on_enter(self, widget):

        text = widget.get_text()

        if not text:
            widget.set_text("")
            return

        if is_alias(text):
            new_text = expand_alias(text)

            if not new_text:
                log.add(_('Alias "%s" returned nothing'), text)
                return

            if new_text[:2] == "//":
                new_text = new_text[1:]

            self.frame.np.queue.append(self.message_class(self.entity, auto_replace(new_text)))
            widget.set_text("")
            return

        s = text.split(" ", 1)
        cmd = s[0]

        # Remove empty items created by split, if command ended with a space, e.g. '/ctcpversion '
        if len([i for i in s if i]) == 2:
            arg_self = args = s[1]
        else:
            if not self.is_chatroom:
                arg_self = self.entity
            else:
                arg_self = ""

            args = ""

        if cmd[:1] == "/" and cmd[:2] != "//" and cmd + " " not in self.command_list:
            log.add(_("Command %s is not recognized"), text)
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
                self.frame.privatechats.send_message(args, show_user=True)
                self.frame.change_main_page("private")

        elif cmd in ("/m", "/msg"):
            if args:
                s = args.split(" ", 1)
                user = s[0]
                if len(s) == 2:
                    msg = s[1]
                else:
                    msg = None
                self.frame.privatechats.send_message(user, msg, show_user=True)
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
                self.frame.userlist.add_to_list(args)

        elif cmd in ("/rem", "/unbuddy"):
            if args:
                self.frame.userlist.remove_from_list(args)

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
                self.frame.privatechats.send_message(
                    arg_self, self.frame.privatechats.CTCP_VERSION, show_user=True, bytestring=True)

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
            self.frame.np.now_playing.display_now_playing(callback=self.send_message)

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

                if config.sections["words"]["commands"]:
                    self.frame.update_completions()

        elif (cmd[:1] == "/" and self.is_chatroom
                and self.frame.np.pluginhandler.trigger_public_command_event(self.entity, cmd[1:], args)):
            pass

        elif (cmd[:1] == "/" and not self.is_chatroom
                and self.frame.np.pluginhandler.trigger_private_command_event(self.entity, cmd[1:], args)):
            pass

        else:
            if text[:2] == "//":
                text = text[1:]

            self.send_message(text)

        self.entry.set_text("")

    def on_key_press_event(self, *args):

        keyval, keycode, state = get_key_press_event_args(*args)
        key, codes, mods = parse_accelerator("Tab")

        if keycode not in codes:
            key, codes_shift_l, mods = parse_accelerator("Shift_L")
            key, codes_shift_r, mods = parse_accelerator("Shift_R")

            if keycode not in codes_shift_l and keycode not in codes_shift_r:
                self.midwaycompletion = False

            return False

        config_words = config.sections["words"]
        if not config_words["tab"]:
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

        if not config_words["cycle"]:
            completion, single = self.get_completion(text, self.completion_list)
            if completion:
                if single and ix == len(text) and text[:1] != "/":
                    completion += ": "
                self.entry.delete_text(preix, ix)
                self.entry.insert_text(completion, preix)
                self.entry.set_position(preix + len(completion))
        else:

            if not self.midwaycompletion:
                self.completions['completions'] = self.get_completions(text, self.completion_list)
                if self.completions['completions']:
                    self.midwaycompletion = True
                    self.completions['currentindex'] = -1
                    currentnick = text
            else:
                currentnick = self.completions['completions'][self.completions['currentindex']]

            if self.midwaycompletion:

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
        key, codes, mods = parse_accelerator("<Primary>f")

        if state & mods and keycode in codes:
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
