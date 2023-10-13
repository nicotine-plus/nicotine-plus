# COPYRIGHT (C) 2020-2023 Nicotine+ Contributors
# COPYRIGHT (C) 2016-2018 Mutnick <mutnick@techie.com>
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2008-2011 quinox <quinox@users.sf.net>
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

import random

from itertools import islice
from operator import itemgetter

from pynicotine import slskmessages
from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.logfacility import log
from pynicotine.utils import TRANSLATE_PUNCTUATION


class SearchRequest:

    __slots__ = ("token", "term", "mode", "room", "users", "is_ignored")

    def __init__(self, token=None, term=None, mode="global", room=None, users=None, is_ignored=False):

        self.token = token
        self.term = term
        self.mode = mode
        self.room = room
        self.users = users
        self.is_ignored = is_ignored


class Search:

    SEARCH_HISTORY_LIMIT = 200
    RESULT_FILTER_HISTORY_LIMIT = 50

    def __init__(self):

        self.searches = {}
        self.token = int(random.random() * (2 ** 31 - 1))
        self.wishlist_interval = 0
        self._wishlist_timer_id = None

        # Create wishlist searches
        for term in config.sections["server"]["autosearch"]:
            self.token = slskmessages.increment_token(self.token)
            self.searches[self.token] = SearchRequest(token=self.token, term=term, mode="wishlist", is_ignored=True)

        for event_name, callback in (
            ("file-search-request-distributed", self._file_search_request_distributed),
            ("file-search-request-server", self._file_search_request_server),
            ("file-search-response", self._file_search_response),
            ("quit", self._quit),
            ("server-disconnect", self._server_disconnect),
            ("set-wishlist-interval", self._set_wishlist_interval)
        ):
            events.connect(event_name, callback)

    def _quit(self):
        self.remove_all_searches()

    def _server_disconnect(self, _msg):
        events.cancel_scheduled(self._wishlist_timer_id)
        self.wishlist_interval = 0

    def request_folder_download(self, username, folder_path, visible_files, download_folder_path=None):

        # Ask for the rest of the files in the folder
        core.downloads.get_folder(username, folder_path, download_folder_path=download_folder_path)

        # Queue the visible search results
        destination_folder_path = core.downloads.get_folder_destination(username, folder_path)

        for file_path, size, file_attributes, *_unused in visible_files:
            core.downloads.get_file(
                username, file_path, folder_path=destination_folder_path, size=size, file_attributes=file_attributes)

    # Outgoing Search Requests #

    @staticmethod
    def add_allowed_token(token):
        """Allow parsing search result messages for a search ID."""
        slskmessages.SEARCH_TOKENS_ALLOWED.add(token)

    @staticmethod
    def remove_allowed_token(token):
        """Disallow parsing search result messages for a search ID."""
        slskmessages.SEARCH_TOKENS_ALLOWED.discard(token)

    def add_search(self, term, mode, room=None, users=None, is_ignored=False):

        self.searches[self.token] = search = SearchRequest(
            token=self.token, term=term, mode=mode, room=room, users=users,
            is_ignored=is_ignored
        )
        self.add_allowed_token(self.token)
        return search

    def remove_search(self, token):

        self.remove_allowed_token(token)
        search = self.searches.get(token)

        if search is None:
            return

        if search.term in config.sections["server"]["autosearch"]:
            search.is_ignored = True
        else:
            del self.searches[token]

        events.emit("remove-search", token)

    def remove_all_searches(self):
        for token in self.searches.copy():
            self.remove_search(token)

    def show_search(self, token):
        events.emit("show-search", token)

    def process_search_term(self, search_term, mode, room=None, users=None):

        if mode == "global":
            if core:
                feedback = core.pluginhandler.outgoing_global_search_event(search_term)

                if feedback is not None:
                    search_term = feedback[0]

        elif mode == "rooms":
            if not room:
                room = core.chatrooms.JOINED_ROOMS_NAME

            if core:
                feedback = core.pluginhandler.outgoing_room_search_event(room, search_term)

                if feedback is not None:
                    room, search_term = feedback

        elif mode == "buddies":
            if core:
                feedback = core.pluginhandler.outgoing_buddy_search_event(search_term)

                if feedback is not None:
                    search_term = feedback[0]

        elif mode == "user":
            if core:
                if not users:
                    users = [core.login_username]

                feedback = core.pluginhandler.outgoing_user_search_event(users, search_term)

                if feedback is not None:
                    users, search_term = feedback

        else:
            log.add("Unknown search mode, not using plugin system. Fix me!")

        # Get excluded words (starting with "-")
        search_term_words = search_term.split()
        search_term_words_special = [p for p in search_term_words if p.startswith(("-", "*")) and len(p) > 1]

        # Remove words starting with "-", results containing these are excluded by us later
        search_term_without_special = " ".join(p for p in search_term_words if p not in search_term_words_special)

        if config.sections["searches"]["remove_special_chars"]:
            # Remove special characters from search term
            # SoulseekQt doesn't seem to send search results if special characters are included (July 7, 2020)

            stripped_search_term = " ".join(search_term_without_special.translate(TRANSLATE_PUNCTUATION).split())

            # Only modify search term if string also contains non-special characters
            if stripped_search_term:
                search_term_without_special = stripped_search_term

        # Remove trailing whitespace
        search_term = search_term_without_special.strip()

        # Append excluded words
        for word in search_term_words_special:
            search_term += " " + word

        return search_term, search_term_without_special, room, users

    def do_search(self, search_term, mode, room=None, users=None, switch_page=True):

        # Validate search term and run it through plugins
        search_term, _search_term_without_special, room, users = self.process_search_term(
            search_term, mode, room, users)

        # Get a new search token
        self.token = slskmessages.increment_token(self.token)

        if config.sections["searches"]["enable_history"]:
            items = config.sections["searches"]["history"]

            if search_term in items:
                items.remove(search_term)

            items.insert(0, search_term)

            # Clear old items
            del items[self.SEARCH_HISTORY_LIMIT:]
            config.write_configuration()

        if mode == "global":
            self.do_global_search(search_term)

        elif mode == "rooms":
            self.do_rooms_search(search_term, room)

        elif mode == "buddies":
            self.do_buddies_search(search_term)

        elif mode == "user":
            self.do_peer_search(search_term, users)

        search = self.add_search(search_term, mode, room, users)
        events.emit("add-search", search.token, search, switch_page)

    def do_global_search(self, text):
        core.send_message_to_server(slskmessages.FileSearch(self.token, text))

        # Request a list of related searches from the server.
        # Seemingly non-functional since 2018 (always receiving empty lists).

        # core.send_message_to_server(slskmessages.RelatedSearch(text))

    def do_rooms_search(self, text, room=None):

        if room != core.chatrooms.JOINED_ROOMS_NAME:
            core.send_message_to_server(slskmessages.RoomSearch(room, self.token, text))
            return

        for joined_room in core.chatrooms.joined_rooms:
            core.send_message_to_server(slskmessages.RoomSearch(joined_room, self.token, text))

    def do_buddies_search(self, text):
        for username in core.userlist.buddies:
            core.send_message_to_server(slskmessages.UserSearch(username, self.token, text))

    def do_peer_search(self, text, users):
        for username in users:
            core.send_message_to_server(slskmessages.UserSearch(username, self.token, text))

    def do_wishlist_search(self, token, text):

        text = text.strip()

        if not text:
            return

        log.add_search(_('Searching for wishlist item "%s"'), text)

        self.add_allowed_token(token)
        core.send_message_to_server(slskmessages.WishlistSearch(token, text))

    def do_wishlist_search_interval(self):

        if core.user_status == slskmessages.UserStatus.OFFLINE:
            return

        searches = config.sections["server"]["autosearch"]

        if not searches:
            return

        # Search for a maximum of 1 item at each search interval
        term = searches.pop()
        searches.insert(0, term)

        for search in self.searches.values():
            if search.term == term and search.mode == "wishlist":
                search.is_ignored = False
                self.do_wishlist_search(search.token, term)
                break

    def add_wish(self, wish):

        if not wish:
            return

        # Get a new search token
        self.token = slskmessages.increment_token(self.token)

        if wish not in config.sections["server"]["autosearch"]:
            config.sections["server"]["autosearch"].append(wish)
            config.write_configuration()

        self.add_search(wish, "wishlist", is_ignored=True)
        events.emit("add-wish", wish)

    def remove_wish(self, wish):

        if wish in config.sections["server"]["autosearch"]:
            config.sections["server"]["autosearch"].remove(wish)
            config.write_configuration()

            for search in self.searches.values():
                if search.term == wish and search.mode == "wishlist":
                    del search
                    break

        events.emit("remove-wish", wish)

    def is_wish(self, wish):
        return wish in config.sections["server"]["autosearch"]

    def _set_wishlist_interval(self, msg):
        """Server code 104."""

        self.wishlist_interval = msg.seconds

        if self.wishlist_interval > 0:
            log.add_search(_("Wishlist wait period set to %s seconds"), self.wishlist_interval)

            events.cancel_scheduled(self._wishlist_timer_id)
            self._wishlist_timer_id = events.schedule(
                delay=self.wishlist_interval, callback=self.do_wishlist_search_interval, repeat=True)
        else:
            log.add(_("Server does not permit performing wishlist searches at this time"))

    def _file_search_response(self, msg):
        """Peer code 9."""

        if msg.token not in slskmessages.SEARCH_TOKENS_ALLOWED:
            msg.token = None
            return

        search = self.searches.get(msg.token)

        if search is None or search.is_ignored:
            msg.token = None
            return

        username = msg.init.target_user
        ip_address = msg.init.addr[0]

        if core.network_filter.is_user_ignored(username):
            msg.token = None
            return

        if core.network_filter.is_user_ip_ignored(username, ip_address):
            msg.token = None

    def _file_search_request_server(self, msg):
        """Server code 26, 42 and 120."""

        self._process_search_request(msg.searchterm, msg.user, msg.token, direct=True)
        core.pluginhandler.search_request_notification(msg.searchterm, msg.user, msg.token)

    def _file_search_request_distributed(self, msg):
        """Distrib code 3."""

        self._process_search_request(msg.searchterm, msg.user, msg.token, direct=False)
        core.pluginhandler.distrib_search_notification(msg.searchterm, msg.user, msg.token)

    # Incoming Search Requests #

    @staticmethod
    def _create_file_info_list(results, max_results, permission_level):
        """ Given a list of file indices, retrieve the file information for each index """

        reveal_buddy_shares = config.sections["transfers"]["reveal_buddy_shares"]
        reveal_trusted_shares = config.sections["transfers"]["reveal_trusted_shares"]
        is_buddy = (permission_level == "buddy")
        is_trusted = (permission_level == "trusted")

        fileinfos = []
        private_fileinfos = []
        num_fileinfos = 0

        public_files = core.shares.share_dbs.get("public_files")
        buddy_files = core.shares.share_dbs.get("buddy_files")
        trusted_files = core.shares.share_dbs.get("trusted_files")

        for index in islice(results, min(len(results), max_results)):
            try:
                file_path = core.shares.file_path_index[index]

            except IndexError as error:
                log.add(_("Unable to read shares database. Please rescan your shares. Error: %s"), error)
                break

            fileinfo = public_files.get(file_path)

            if fileinfo is not None:
                fileinfos.append(fileinfo)
                continue

            if is_buddy or reveal_buddy_shares:
                fileinfo = buddy_files.get(file_path)

                if fileinfo is not None:
                    if is_buddy:
                        fileinfos.append(fileinfo)
                    else:
                        private_fileinfos.append(fileinfo)
                    continue

            if is_trusted or reveal_trusted_shares:
                fileinfo = trusted_files.get(file_path)

                if fileinfo is not None:
                    if is_trusted:
                        fileinfos.append(fileinfo)
                    else:
                        private_fileinfos.append(fileinfo)

        results.clear()

        if fileinfos:
            fileinfos.sort(key=itemgetter(1))

        if private_fileinfos:
            private_fileinfos.sort(key=itemgetter(1))

        num_fileinfos = len(fileinfos) + len(private_fileinfos)
        return num_fileinfos, fileinfos, private_fileinfos

    @staticmethod
    def _update_search_results(results, word_indices, excluded=False):
        """Updates the search result list with indices for a new word."""

        if word_indices is None:
            if excluded:
                # We don't care if an excluded word doesn't exist in our DB
                return results

            # Included word does not exist in our DB, no results
            return None

        if results is None:
            if excluded:
                # No results yet, but word is excluded. Bail.
                return set()

            # First match for included word, return results
            return set(word_indices)

        if excluded:
            # Remove results for excluded word
            results.difference_update(word_indices)
        else:
            # Only retain common results for all words so far
            results.intersection_update(word_indices)

        return results

    def _create_search_result_list(self, included_words, excluded_words, partial_words, max_results, word_index):
        """Returns a list of common file indices for each word in a search
        term."""

        results = None

        try:
            # Start with the word with the least results to reduce memory usage
            start_word = min(included_words, key=lambda word: len(word_index[word]), default=None)

        except KeyError:
            # No results
            return results

        has_single_word = (sum(len(words) for words in (included_words, excluded_words, partial_words)) == 1)
        included_words.discard(start_word)

        # Partial search words (e.g. *ello)
        for word in partial_words:
            partial_results = set()
            num_partial_results = 0

            for complete_word in word_index:
                if complete_word.endswith(word):
                    indices = word_index[complete_word]

                    if has_single_word:
                        # Attempt to avoid large memory usage if someone searches for e.g. "*lac"
                        indices = indices[:max_results - num_partial_results]

                    partial_results.update(indices)

                    if not has_single_word:
                        continue

                    num_partial_results = len(partial_results)

                    if num_partial_results >= max_results:
                        break

            if partial_results:
                results = self._update_search_results(results, partial_results)

        # Included search words (e.g. hello)
        start_results = word_index.get(start_word)

        if start_results:
            if has_single_word:
                # Attempt to avoid large memory usage if someone searches for e.g. "flac"
                start_results = start_results[:max_results]

            results = self._update_search_results(results, start_results)

            for word in included_words:
                results = self._update_search_results(results, word_index.get(word))

        # Excluded search words (e.g. -hello)
        if results:
            for word in excluded_words:
                results = self._update_search_results(results, word_index.get(word), excluded=True)

        return results

    def _process_search_request(self, search_term, username, token, direct=False):
        """This section is accessed every time a search request arrives,
        several times per second.

        Please keep it as optimized and memory sparse as possible!
        """

        if not search_term:
            return

        if not config.sections["searches"]["search_results"]:
            # Don't return _any_ results when this option is disabled
            return

        if core.uploads.pending_shutdown:
            # Don't return results when waiting to quit after finishing uploads
            return

        if not direct and username == core.login_username:
            # We shouldn't send a search response if we initiated the search request,
            # unless we're specifically searching our own username
            return

        max_results = config.sections["searches"]["maxresults"]

        if max_results <= 0:
            return

        if len(search_term) < config.sections["searches"]["min_search_chars"]:
            # Don't send search response if search term contains too few characters
            return

        permission_level, _reject_reason = core.network_filter.check_user_permission(username)

        if permission_level == "banned":
            return

        word_index = core.shares.share_dbs.get("words")

        if word_index is None:
            return

        original_search_term = search_term
        search_term = search_term.lower()

        # Extract included/excluded/partial words from search term
        excluded_words = set()
        partial_words = set()

        if "-" in search_term or "*" in search_term:
            for word in search_term.split():
                if len(word) < 1:
                    continue

                if word.startswith("-"):
                    for subword in word.translate(TRANSLATE_PUNCTUATION).split():
                        excluded_words.add(subword)

                elif word.startswith("*"):
                    for subword in word.translate(TRANSLATE_PUNCTUATION).split():
                        partial_words.add(subword)

        # Strip punctuation
        search_term = search_term.translate(TRANSLATE_PUNCTUATION).strip()
        included_words = (set(search_term.split()) - excluded_words - partial_words)

        # Find common file matches for each word in search term
        results = self._create_search_result_list(
            included_words, excluded_words, partial_words, max_results, word_index)

        if not results:
            return

        # Get file information for each file index in result list
        num_results, fileinfos, private_fileinfos = self._create_file_info_list(
            results, max_results, permission_level)

        if not num_results:
            return

        uploadspeed = core.uploads.upload_speed
        queuesize = core.uploads.get_upload_queue_size()
        slotsavail = core.uploads.allow_new_uploads()
        fifoqueue = config.sections["transfers"]["fifoqueue"]

        message = slskmessages.FileSearchResponse(
            None, core.login_username,
            token, fileinfos, slotsavail, uploadspeed, queuesize, fifoqueue,
            private_fileinfos
        )
        core.send_message_to_peer(username, message)

        log.add_search(_('User %(user)s is searching for "%(query)s", found %(num)i results'), {
            "user": username,
            "query": original_search_term,
            "num": num_results
        })
