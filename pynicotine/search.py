# SPDX-FileCopyrightText: 2020-2025 Nicotine+ Contributors
# SPDX-FileCopyrightText: 2016-2018 Mutnick <mutnick@techie.com>
# SPDX-FileCopyrightText: 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# SPDX-FileCopyrightText: 2008-2011 quinox <quinox@users.sf.net>
# SPDX-FileCopyrightText: 2006-2009 daelstorm <daelstorm@gmail.com>
# SPDX-FileCopyrightText: 2003-2004 Hyriand <hyriand@thegraveyard.org>
# SPDX-License-Identifier: GPL-3.0-or-later

from itertools import islice
from operator import itemgetter
from shlex import shlex

from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.logfacility import log
from pynicotine.shares import PermissionLevel
from pynicotine.slskmessages import FileSearch
from pynicotine.slskmessages import FileSearchResponse
from pynicotine.slskmessages import increment_token
from pynicotine.slskmessages import initial_token
from pynicotine.slskmessages import RoomSearch
from pynicotine.slskmessages import SEARCH_TOKENS_ALLOWED
from pynicotine.slskmessages import UserSearch
from pynicotine.slskmessages import WishlistSearch
from pynicotine.utils import TRANSLATE_PUNCTUATION


class SearchRequest:
    __slots__ = ("token", "term", "term_sanitized", "term_transmitted", "included_words", "excluded_words",
                 "mode", "room", "users", "is_ignored")

    def __init__(self, token=None, term=None, term_sanitized=None, term_transmitted=None, included_words=None,
                 excluded_words=None, mode="global", room=None, users=None, is_ignored=False):

        self.token = token
        self.term = term
        self.term_sanitized = term_sanitized
        self.term_transmitted = term_transmitted
        self.included_words = included_words
        self.excluded_words = excluded_words
        self.mode = mode
        self.room = room
        self.users = users
        self.is_ignored = is_ignored


class Search:
    __slots__ = ("searches", "excluded_phrases", "token", "wishlist_interval", "_own_tokens",
                 "_wishlist_timer_id")

    SEARCH_HISTORY_LIMIT = 200
    RESULT_FILTER_HISTORY_LIMIT = 50
    REMOVED_SEARCH_CHARACTERS = [
        "!", '"', "#", "$", "%", "&", "'", "(", ")", "*", "+", ",", "-", ".", "/", ":", ";",
        "<", "=", ">", "?", "@", "[", "\\", "]", "^", "_", "`", "{", "|", "}", "~", "–", "—",
        "‐", "’", "“", "”", "…"
    ]
    TRANSLATE_REMOVED_SEARCH_CHARACTERS = str.maketrans(dict.fromkeys(REMOVED_SEARCH_CHARACTERS, " "))

    def __init__(self):

        self.searches = {}
        self.excluded_phrases = []
        self.token = initial_token()
        self.wishlist_interval = 0
        self._own_tokens = set()
        self._wishlist_timer_id = None

        for event_name, callback in (
            ("excluded-search-phrases", self._excluded_search_phrases),
            ("file-search-request-distributed", self._file_search_request_distributed),
            ("file-search-request-server", self._file_search_request_server),
            ("file-search-response", self._file_search_response),
            ("quit", self._quit),
            ("server-disconnect", self._server_disconnect),
            ("server-login", self._server_login),
            ("set-wishlist-interval", self._set_wishlist_interval),
            ("start", self._start)
        ):
            events.connect(event_name, callback)

    def _start(self):

        # Create wishlist searches
        for search_term in config.sections["server"]["autosearch"]:
            self.token = increment_token(self.token)
            self._add_search(self.token, search_term, mode="wishlist", is_ignored=True)

    def _quit(self):
        self.remove_all_searches()

    def _server_login(self, msg):

        if not msg.success:
            return

        if not config.sections["searches"]["search_results"]:
            log.add_search(("Search responses disabled in preferences, ignoring search "
                            "requests from other users"))

    def _server_disconnect(self, _msg):

        self.excluded_phrases.clear()
        self._own_tokens.clear()

        events.cancel_scheduled(self._wishlist_timer_id)
        self.wishlist_interval = 0

    # Outgoing Search Requests #

    @staticmethod
    def add_allowed_token(token):
        """Allow parsing search result messages for a search ID."""
        SEARCH_TOKENS_ALLOWED.add(token)

    @staticmethod
    def remove_allowed_token(token):
        """Disallow parsing search result messages for a search ID."""
        SEARCH_TOKENS_ALLOWED.discard(token)

    def do_search(self, search_term, mode, room=None, users=None, switch_page=True):

        # Validate search term and run it through plugins
        search_term, room, users = self._process_search_term(search_term, mode, room, users)

        # Get a new search token
        self.token = increment_token(self.token)
        search = self._add_search(self.token, search_term, mode, room, users)

        if config.sections["searches"]["enable_history"]:
            items = config.sections["searches"]["history"]

            if search.term_sanitized in items:
                items.remove(search.term_sanitized)

            items.insert(0, search.term_sanitized)

            # Clear old items
            del items[self.SEARCH_HISTORY_LIMIT:]
            config.write_configuration()

        self.send_search_request(search.token)
        events.emit("add-search", search.token, search, switch_page)

    def send_search_request(self, token):

        search = self.searches.get(token)

        if search is None:
            return

        self.add_allowed_token(token)

        if search.mode in {"global", "wishlist"}:
            self._send_global_search_request(search)

        elif search.mode == "rooms":
            self._send_rooms_search_request(search)

        elif search.mode == "buddies":
            self._send_buddies_search_request(search)

        elif search.mode == "user":
            self._send_peer_search_request(search)

    def remove_search(self, token):

        self.remove_allowed_token(token)
        search = self.searches.get(token)

        if search is None:
            return

        if search.mode == "wishlist" and search.term in config.sections["server"]["autosearch"]:
            search.is_ignored = True
        else:
            del self.searches[token]

        events.emit("remove-search", token)

    def remove_all_searches(self):
        for token in self.searches.copy():
            self.remove_search(token)

    def show_search(self, token):
        events.emit("show-search", token)

    def add_wish(self, wish):

        if not wish:
            return

        if wish not in config.sections["server"]["autosearch"]:
            config.sections["server"]["autosearch"].append(wish)
            config.write_configuration()

        if not any(search.term == wish and search.mode == "wishlist" for search in self.searches.values()):
            # Get a new search token
            self.token = increment_token(self.token)
            self._add_search(self.token, wish, mode="wishlist", is_ignored=True)

        events.emit("add-wish", wish)

    def remove_wish(self, wish):

        if wish not in config.sections["server"]["autosearch"]:
            return

        config.sections["server"]["autosearch"].remove(wish)
        config.write_configuration()

        for token, search in self.searches.items():
            if search.term != wish or search.mode != "wishlist":
                continue

            if search.is_ignored:
                del self.searches[token]

            break

        events.emit("remove-wish", wish)

    def is_wish(self, wish):
        return wish in config.sections["server"]["autosearch"]

    def _add_search(self, token, search_term, mode, room=None, users=None, is_ignored=False):

        term_sanitized, term_transmitted, included_words, excluded_words = self._sanitize_search_term(search_term)

        self.searches[token] = search = SearchRequest(
            token=token, term=search_term, term_sanitized=term_sanitized, term_transmitted=term_transmitted,
            included_words=included_words, excluded_words=excluded_words, mode=mode, room=room, users=users,
            is_ignored=is_ignored
        )

        return search

    def _sanitize_search_term(self, search_term):

        included_words = []
        excluded_words = []
        search_term = search_term_transmitted = search_term.strip()

        try:
            lex = shlex(search_term)
            lex.quotes = '"'
            lex.whitespace_split = True
            lex.commenters = ""

            search_term_words = list(lex)

        except ValueError:
            search_term_words = search_term.split()

        # Remove certain special characters from search term
        # SoulseekQt doesn't seem to send search results if such characters are included (July 7, 2020)
        search_term_words_transmitted = []

        excluded_char = "-"
        partial_char = "*"
        quotation_char = '"'

        for index, word in enumerate(search_term_words):
            if not word:
                continue

            first_char = word[0]

            if first_char == partial_char and len(word) > 1:
                # Partial word (*erm)
                included_words.append(word[1:].lower())

            elif first_char == excluded_char and len(word) > 1:
                # Excluded word (-word)
                excluded_words.append(word[1:].lower())

            elif first_char == quotation_char and word[-1] == quotation_char and len(word) > 2:
                # Phrase "some words here"
                word = word[1:-1]
                included_words.append(word.lower())

                # Remove problematic characters before appending to outgoing search term
                for inner_word in word.translate(self.TRANSLATE_REMOVED_SEARCH_CHARACTERS).strip().split():
                    search_term_words_transmitted.append(inner_word)

                continue

            else:
                # Remove problematic characters before appending to outgoing search term
                subwords = word.translate(self.TRANSLATE_REMOVED_SEARCH_CHARACTERS).strip().split()
                word = search_term_words[index] = " ".join(x for x in subwords if x)

                if not subwords:
                    continue

                for subword in word.translate(TRANSLATE_PUNCTUATION).strip().split():
                    included_words.append(subword.lower())

            search_term_words_transmitted.append(word)

        sanitized_search_term_transmitted = " ".join(x for x in search_term_words_transmitted).strip()

        # Only modify search term if string also contains non-special characters
        if sanitized_search_term_transmitted:
            search_term = " ".join(x for x in search_term_words if x).strip()
            search_term_transmitted = sanitized_search_term_transmitted

        return search_term, search_term_transmitted, included_words, excluded_words

    def _process_search_term(self, search_term, mode, room=None, users=None):

        search_term = search_term.strip()

        if mode == "global":
            feedback = core.pluginhandler.outgoing_global_search_event(search_term)

            if feedback is not None:
                search_term = feedback[0]

        elif mode == "rooms":
            if not room:
                room = next(iter(config.defaults["server"]["autojoin"]), None)

            feedback = core.pluginhandler.outgoing_room_search_event(room, search_term)

            if feedback is not None:
                room, search_term = feedback

        elif mode == "buddies":
            feedback = core.pluginhandler.outgoing_buddy_search_event(search_term)

            if feedback is not None:
                search_term = feedback[0]

        elif mode == "user":
            if not users:
                users = [core.users.login_username or config.sections["server"]["login"]]

            feedback = core.pluginhandler.outgoing_user_search_event(users, search_term)

            if feedback is not None:
                users, search_term = feedback

        elif mode == "wishlist":
            feedback = core.pluginhandler.outgoing_wishlist_search_event(search_term)

            if feedback is not None:
                search_term = feedback[0]

        else:
            log.add("Unknown search mode, not using plugin system. Fix me!")

        return search_term, room, users

    def _send_global_search_request(self, search):
        core.send_message_to_server(FileSearch(search.token, search.term_transmitted))

    def _send_rooms_search_request(self, search):
        core.send_message_to_server(RoomSearch(search.room, search.token, search.term_transmitted))

    def _send_buddies_search_request(self, search):
        for username in core.buddies.users:
            core.send_message_to_server(UserSearch(username, search.token, search.term_transmitted))

    def _send_peer_search_request(self, search):

        for username in search.users:
            if username == core.users.login_username:
                self._own_tokens.add(self.token)

            core.send_message_to_server(UserSearch(username, search.token, search.term_transmitted))

    def _do_wishlist_search(self, search):

        text, _room, _users = self._process_search_term(search.term_transmitted, mode="wishlist")

        if not text:
            return

        log.add_search(_('Searching for wishlist item "%s"'), text)

        self.add_allowed_token(search.token)
        core.send_message_to_server(WishlistSearch(search.token, text))

    def _do_next_wishlist_search(self):

        searches = config.sections["server"]["autosearch"]

        if not searches:
            return

        # Search for a maximum of 1 item at each search interval
        term = searches.pop()
        searches.insert(0, term)

        for search in self.searches.values():
            if search.term == term and search.mode == "wishlist":
                search.is_ignored = False
                self._do_wishlist_search(search)
                break

    def _set_wishlist_interval(self, msg):
        """Server code 104."""

        self.wishlist_interval = msg.seconds

        if self.wishlist_interval > 0:
            log.add_search(_("Wishlist wait period set to %s seconds"), self.wishlist_interval)

            events.cancel_scheduled(self._wishlist_timer_id)
            self._wishlist_timer_id = events.schedule(
                delay=self.wishlist_interval, callback=self._do_next_wishlist_search, repeat=True)

    def _excluded_search_phrases(self, msg):
        """Server code 160."""

        if self.excluded_phrases and self.excluded_phrases != msg.phrases:
            log.add_search("Previous list of excluded search phrases: %s", self.excluded_phrases)

        self.excluded_phrases = msg.phrases
        log.add_search("Server provided %(num_phrases)s excluded search phrase(s): %(phrases)s", {
            "num_phrases": len(msg.phrases),
            "phrases": str(msg.phrases)
        })

    def _file_search_response(self, msg):
        """Peer code 9."""

        if msg.token not in SEARCH_TOKENS_ALLOWED:
            msg.token = None
            return

        search = self.searches.get(msg.token)

        if search is None or search.is_ignored:
            msg.token = None
            return

        username = msg.username
        ip_address, _port = msg.addr

        if core.network_filter.is_user_ignored(username):
            msg.token = None
            return

        if core.network_filter.is_user_ip_ignored(username, ip_address):
            msg.token = None

    def _file_search_request_server(self, msg):
        """Server code 26."""

        self._process_search_request(msg.searchterm, msg.search_username, msg.token)
        core.pluginhandler.search_request_notification(msg.searchterm, msg.search_username, msg.token)

    def _file_search_request_distributed(self, msg):
        """Distrib code 3."""

        self._process_search_request(msg.searchterm, msg.search_username, msg.token)
        core.pluginhandler.distrib_search_notification(msg.searchterm, msg.search_username, msg.token)

    # Incoming Search Requests #

    def _append_file_info(self, file_list, fileinfo):

        file_path, *_unused = fileinfo
        file_path_lower = file_path.lower()
        excluded_phrase = next((phrase for phrase in self.excluded_phrases if phrase in file_path_lower), None)

        # Check if file path contains phrase excluded from the search network
        if excluded_phrase:
            log.add_search(('Excluding file %(file)s from search response because server '
                            'disallowed phrase "%(phrase)s"'), {
                "file": file_path,
                "phrase": excluded_phrase
            })
            return

        file_list.append(fileinfo)

    def _create_file_info_list(self, results, max_results, permission_level):
        """Given a list of file indices, retrieve the file information for each index."""

        reveal_buddy_shares = config.sections["transfers"]["reveal_buddy_shares"]
        reveal_trusted_shares = config.sections["transfers"]["reveal_trusted_shares"]
        is_buddy = (permission_level == PermissionLevel.BUDDY)
        is_trusted = (permission_level == PermissionLevel.TRUSTED)

        fileinfos = []
        private_fileinfos = []
        num_fileinfos = 0

        public_files = core.shares.share_dbs["public_files"]
        buddy_files = core.shares.share_dbs["buddy_files"]
        trusted_files = core.shares.share_dbs["trusted_files"]

        for index in islice(results, min(len(results), max_results)):
            file_path = core.shares.file_path_index[index]

            if file_path in public_files:
                self._append_file_info(fileinfos, public_files[file_path])
                continue

            if (is_buddy or reveal_buddy_shares) and file_path in buddy_files:
                fileinfo = buddy_files[file_path]

                if is_buddy:
                    self._append_file_info(fileinfos, fileinfo)
                else:
                    self._append_file_info(private_fileinfos, fileinfo)
                continue

            if (is_trusted or reveal_trusted_shares) and file_path in trusted_files:
                fileinfo = trusted_files[file_path]

                if is_trusted:
                    self._append_file_info(fileinfos, fileinfo)
                else:
                    self._append_file_info(private_fileinfos, fileinfo)

        results.clear()

        if fileinfos:
            fileinfos.sort(key=itemgetter(0))

        if private_fileinfos:
            private_fileinfos.sort(key=itemgetter(0))

        num_fileinfos = len(fileinfos) + len(private_fileinfos)
        return num_fileinfos, fileinfos, private_fileinfos

    @staticmethod
    def _update_search_results(results, word_indices, excluded=False):
        """Updates the search result list with indices for a new word."""

        if not word_indices:
            if excluded:
                # We don't care if an excluded word doesn't exist in our DB
                return results

            # Included word does not exist in our DB, no results
            return set()

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

        for word in included_words:
            if word not in word_index:
                # No results
                return results

        start_word = next(iter(included_words), None)
        has_single_word = (sum(len(words) for words in (included_words, excluded_words, partial_words)) == 1)
        included_words.discard(start_word)

        # Partial search words (e.g. *ello)
        for partial_word in partial_words:
            partial_word_len = len(partial_word)
            partial_results = set()
            num_partial_results = 0

            for complete_word in word_index:
                if len(complete_word) < partial_word_len or not complete_word.endswith(partial_word):
                    continue

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

            if not partial_results:
                return None

            results = self._update_search_results(results, partial_results)

        # Included search words (e.g. hello)
        if start_word:
            start_results = word_index[start_word]

            if has_single_word:
                # Attempt to avoid large memory usage if someone searches for e.g. "flac"
                start_results = start_results[:max_results]

            results = self._update_search_results(results, start_results)

            for included_word in included_words:
                if included_word not in word_index:
                    return None

                results = self._update_search_results(results, word_index[included_word])

        # Excluded search words (e.g. -hello)
        if results:
            for excluded_word in excluded_words:
                if excluded_word not in word_index:
                    continue

                results = self._update_search_results(results, word_index[excluded_word], excluded=True)

        if not results:
            return None

        return results

    def _process_search_request(self, search_term, username, token):
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

        local_username = core.users.login_username

        if username == local_username:
            if token not in self._own_tokens:
                # We shouldn't send a search response if we initiated the search
                # request, unless we're specifically searching our own username
                return

            self._own_tokens.discard(token)

        max_results = config.sections["searches"]["maxresults"]

        if max_results <= 0:
            return

        if len(search_term) < config.sections["searches"]["min_search_chars"]:
            # Don't send search response if search term contains too few characters
            return

        permission_level, _reject_reason = core.shares.check_user_permission(username)

        if permission_level == PermissionLevel.BANNED:
            return

        if "words" not in core.shares.share_dbs:
            return

        word_index = core.shares.share_dbs["words"]
        original_search_term = search_term
        search_term = search_term.lower()

        # Extract included/excluded/partial words from search term
        excluded_words = set()
        partial_words = set()

        excluded_char = "-"
        partial_char = "*"

        if excluded_char in search_term or partial_char in search_term:
            for word in search_term.split():
                if not word:
                    continue

                first_char = word[0]

                if first_char == excluded_char:
                    for subword in word.translate(TRANSLATE_PUNCTUATION).split():
                        excluded_words.add(subword)

                elif first_char == partial_char:
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

        core.send_message_to_peer(username, FileSearchResponse(
            search_username=local_username,
            token=token,
            shares=fileinfos,
            freeulslots=core.uploads.is_new_upload_accepted(),
            ulspeed=core.uploads.upload_speed,
            inqueue=core.uploads.get_upload_queue_size(username),
            private_shares=private_fileinfos
        ))

        log.add_search(_('User %(user)s is searching for "%(query)s", found %(num)i results'), {
            "user": username,
            "query": original_search_term,
            "num": num_results
        })
