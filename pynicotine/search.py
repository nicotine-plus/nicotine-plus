# COPYRIGHT (C) 2020-2021 Nicotine+ Team
# COPYRIGHT (C) 2016-2018 Mutnick <mutnick@techie.com>
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2008-2011 Quinox <quinox@users.sf.net>
# COPYRIGHT (C) 2006-2009 Daelstorm <daelstorm@gmail.com>
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

from pynicotine import slskmessages
from pynicotine.logfacility import log
from pynicotine.utils import PUNCTUATION


class Search:

    def __init__(self, core, config, queue, share_dbs, geoip, ui_callback=None):

        self.core = core
        self.config = config
        self.queue = queue
        self.ui_callback = None
        self.searches = {}
        self.searchid = int(random.random() * (2 ** 31 - 1))
        self.wishlist_interval = 0
        self.share_dbs = share_dbs
        self.geoip = geoip
        self.translatepunctuation = str.maketrans(dict.fromkeys(PUNCTUATION, ' '))

        # Create wishlist searches
        for term in config.sections["server"]["autosearch"]:
            search_id = self.increment_search_id()
            self.searches[search_id] = {"id": search_id, "term": term, "mode": "wishlist", "ignore": True}

        if hasattr(ui_callback, "search"):
            self.ui_callback = ui_callback.search

    def server_disconnect(self):

        self.wishlist_interval = 0

        if self.ui_callback:
            self.ui_callback.server_disconnect()

    def request_folder_download(self, user, folder, visible_files):

        # First queue the visible search results
        if self.config.sections["transfers"]["reverseorder"]:
            visible_files.sort(key=lambda x: x[1], reverse=True)

        for file in visible_files:
            user, fullpath, destination, size, bitrate, length = file

            self.core.transfers.get_file(
                user, fullpath, destination,
                size=size, bitrate=bitrate, length=length)

        # Ask for the rest of the files in the folder
        self.core.transfers.get_folder(user, folder)

    """ Outgoing search requests """

    @staticmethod
    def add_allowed_search_id(search_id):
        """ Allow parsing search result messages for a search ID """
        slskmessages.SEARCH_TOKENS_ALLOWED.add(search_id)

    @staticmethod
    def remove_allowed_search_id(search_id):
        """ Disallow parsing search result messages for a search ID """
        slskmessages.SEARCH_TOKENS_ALLOWED.discard(search_id)

    def add_search(self, search_id, term, mode, ignore):
        self.searches[search_id] = {"id": search_id, "term": term, "mode": mode, "ignore": ignore}
        self.add_allowed_search_id(search_id)

    def remove_search(self, search_id):

        self.remove_allowed_search_id(search_id)
        search = self.searches.get(search_id)

        if search is None:
            return

        if search["term"] in self.config.sections["server"]["autosearch"]:
            search["ignore"] = True
            return

        del self.searches[search_id]

    def process_search_term(self, text, mode, room, user):

        users = []
        feedback = None

        if mode == "global":
            if self.core:
                feedback = self.core.pluginhandler.outgoing_global_search_event(text)

                if feedback is not None:
                    text = feedback[0]

        elif mode == "rooms":
            # Space after Joined Rooms is important, so it doesn't conflict
            # with any possible real room
            if room == _("Joined Rooms ") or room.isspace():
                room = None

            if self.core:
                feedback = self.core.pluginhandler.outgoing_room_search_event(room, text)

                if feedback is not None:
                    room, text = feedback

        elif mode == "buddies" and self.core:
            feedback = self.core.pluginhandler.outgoing_buddy_search_event(text)

            if feedback is not None:
                text = feedback[0]

        elif mode == "user":
            if user:
                users = [user]
            else:
                return None

            if self.core:
                feedback = self.core.pluginhandler.outgoing_user_search_event(users, text)

                if feedback is not None:
                    users, text = feedback

        else:
            log.add("Unknown search mode, not using plugin system. Fix me!")

        return text, room, users

    def do_search(self, text, mode, room=None, user=None):

        # Validate search term and run it through plugins
        processed_search = self.process_search_term(text, mode, room, user)

        if not processed_search:
            return None

        text, room, users = processed_search

        # Get a new search ID
        self.increment_search_id()

        # Get excluded words (starting with "-")
        searchterm_words = text.split()
        searchterm_words_special = (p for p in searchterm_words if p.startswith(('-', '*')) and len(p) > 1)

        # Remove words starting with "-", results containing these are excluded by us later
        searchterm_without_special = ' '.join(p for p in searchterm_words if not p.startswith(('-', '*')))

        if self.config.sections["searches"]["remove_special_chars"]:
            """
            Remove special characters from search term
            SoulseekQt doesn't seem to send search results if special characters are included (July 7, 2020)
            """
            stripped_searchterm = ' '.join(searchterm_without_special.translate(self.translatepunctuation).split())

            # Only modify search term if string also contains non-special characters
            if stripped_searchterm:
                searchterm_without_special = stripped_searchterm

        # Remove trailing whitespace
        searchterm = searchterm_without_special.strip()

        # Append excluded words
        for word in searchterm_words_special:
            searchterm += " " + word

        if self.config.sections["searches"]["enable_history"]:
            items = self.config.sections["searches"]["history"]

            if searchterm in items:
                items.remove(searchterm)

            items.insert(0, searchterm)

            # Clear old items
            del items[15:]
            self.config.write_configuration()

        if mode == "global":
            self.do_global_search(self.searchid, searchterm)

        elif mode == "rooms":
            self.do_rooms_search(self.searchid, searchterm, room)

        elif mode == "buddies":
            self.do_buddies_search(self.searchid, searchterm)

        elif mode == "user":
            self.do_peer_search(self.searchid, searchterm, users)

        self.add_search(self.searchid, searchterm, mode, ignore=False)
        return (self.searchid, searchterm, searchterm_without_special)

    def do_global_search(self, search_id, text):
        self.queue.append(slskmessages.FileSearch(search_id, text))

        """ Request a list of related searches from the server.
        Seemingly non-functional since 2018 (always receiving empty lists). """

        # self.queue.append(slskmessages.RelatedSearch(text))

    def do_rooms_search(self, search_id, text, room=None):

        if room is not None:
            self.queue.append(slskmessages.RoomSearch(room, search_id, text))

        elif self.core.chatrooms.ui_callback is not None:
            for joined_room in self.core.chatrooms.ui_callback.pages:
                self.queue.append(slskmessages.RoomSearch(joined_room, search_id, text))

    def do_buddies_search(self, search_id, text):

        for row in self.config.sections["server"]["userlist"]:
            if row and isinstance(row, list):
                user = str(row[0])
                self.queue.append(slskmessages.UserSearch(user, search_id, text))

    def do_peer_search(self, search_id, text, users):
        for user in users:
            self.queue.append(slskmessages.UserSearch(user, search_id, text))

    def do_wishlist_search(self, search_id, text):
        self.add_allowed_search_id(search_id)
        self.queue.append(slskmessages.WishlistSearch(search_id, text))

    def do_wishlist_search_interval(self):

        if self.wishlist_interval == 0:
            log.add(_("The server forbid us from doing wishlist searches."))
            return False

        searches = self.config.sections["server"]["autosearch"]

        if not searches:
            return True

        # Search for a maximum of 1 item at each search interval
        term = searches.pop()
        searches.insert(0, term)

        for search in self.searches.values():
            if search["term"] == term and search["mode"] == "wishlist":
                search["ignore"] = False
                self.do_wishlist_search(search["id"], term)
                break

        return True

    def get_current_search_id(self):
        return self.searchid

    def increment_search_id(self):
        self.searchid += 1
        return self.searchid

    def add_wish(self, wish):

        if not wish:
            return None

        # Get a new search ID
        self.increment_search_id()

        if wish not in self.config.sections["server"]["autosearch"]:
            self.config.sections["server"]["autosearch"].append(wish)

        self.add_search(self.searchid, wish, "wishlist", ignore=True)
        return self.searchid

    def remove_wish(self, wish):

        if wish in self.config.sections["server"]["autosearch"]:
            self.config.sections["server"]["autosearch"].remove(wish)

            for search in self.searches.values():
                if search["term"] == wish and search["mode"] == "wishlist":
                    del search
                    break

    def set_wishlist_interval(self, msg):

        self.wishlist_interval = msg.seconds

        if self.ui_callback:
            self.ui_callback.set_wishlist_interval(msg)

        log.add_search(_("Wishlist wait period set to %s seconds"), msg.seconds)

    def file_search_result(self, msg):

        if not self.ui_callback or msg.token not in slskmessages.SEARCH_TOKENS_ALLOWED:
            return

        search = self.searches.get(msg.token)

        if search is None or search["ignore"]:
            return

        conn = msg.conn
        username = conn.init.target_user
        addr = conn.addr

        if addr:
            country = self.geoip.get_country_code(addr[0])
        else:
            country = ""

        if country == "-":
            country = ""

        self.ui_callback.show_search_result(msg, username, country)

    """ Incoming search requests """

    @staticmethod
    def update_search_results(results, word_indices, exclude_word=False):
        """ Updates the search result list with indices for a new word """

        if word_indices is None:
            if exclude_word:
                # We don't care if an excluded word doesn't exist in our DB
                return results

            # Included word does not exist in our DB, no results
            return None

        if results is None:
            if exclude_word:
                # No results yet, but word is excluded. Bail.
                return set()

            # First match for included word, return results
            return set(word_indices)

        if exclude_word:
            # Remove results for excluded word
            results.difference_update(word_indices)
        else:
            # Only retain common results for all words so far
            results.intersection_update(word_indices)

        return results

    def create_search_result_list(self, searchterm, wordindex, excluded_words, partial_words):
        """ Returns a list of common file indices for each word in a search term """

        try:
            words = searchterm.split()
            original_length = len(words)
            results = None
            i = 0

            while i < len(words):
                word = words[i]
                exclude_word = False
                i += 1

                if word in excluded_words:
                    # Excluded search words (e.g. -hello)

                    if results is None and i < original_length:
                        # Re-append the word so we can re-process it once we've found a match
                        words.append(word)
                        continue

                    exclude_word = True

                elif word in partial_words:
                    # Partial search words (e.g. *ello)

                    partial_results = set()

                    for complete_word, indices in wordindex.items():
                        if complete_word.endswith(word):
                            partial_results.update(indices)

                    if partial_results:
                        results = self.update_search_results(results, partial_results)
                        continue

                results = self.update_search_results(results, wordindex.get(word), exclude_word)

                if results is None:
                    # No matches found
                    break

            return results

        except ValueError:
            # DB is closed, perhaps due to rescanning shares or closing Nicotine+
            return None

    def process_search_request(self, searchterm, user, searchid, direct=False):
        """ Note: since this section is accessed every time a search request arrives,
        several times a second, please keep it as optimized and memory
        sparse as possible! """

        if not searchterm:
            return

        if not self.config.sections["searches"]["search_results"]:
            # Don't return _any_ results when this option is disabled
            return

        if not direct and user == self.config.sections["server"]["login"]:
            # We shouldn't send a search response if we initiated the search request,
            # unless we're specifically searching our own username
            return

        maxresults = self.config.sections["searches"]["maxresults"]

        if maxresults == 0:
            return

        # Remember excluded/partial words for later
        excluded_words = []
        partial_words = []

        if '-' in searchterm or '*' in searchterm:
            for word in searchterm.split():
                if len(word) < 1:
                    continue

                if word.startswith('-'):
                    for subword in word.translate(self.translatepunctuation).split():
                        excluded_words.append(subword)

                elif word.startswith('*'):
                    for subword in word.translate(self.translatepunctuation).split():
                        partial_words.append(subword)

        # Strip punctuation
        searchterm_old = searchterm
        searchterm = searchterm.lower().translate(self.translatepunctuation).strip()

        if len(searchterm) < self.config.sections["searches"]["min_search_chars"]:
            # Don't send search response if search term contains too few characters
            return

        checkuser, _reason = self.core.network_filter.check_user(user, None)

        if not checkuser:
            return

        if checkuser == 2:
            wordindex = self.share_dbs.get("buddywordindex")
        else:
            wordindex = self.share_dbs.get("wordindex")

        if wordindex is None:
            return

        # Find common file matches for each word in search term
        resultlist = self.create_search_result_list(searchterm, wordindex, excluded_words, partial_words)

        if not resultlist:
            return

        numresults = min(len(resultlist), maxresults)
        uploadspeed = self.core.transfers.upload_speed
        queuesize = self.core.transfers.get_upload_queue_size()
        slotsavail = self.core.transfers.allow_new_uploads()

        if checkuser == 2:
            fileindex = self.share_dbs.get("buddyfileindex")
        else:
            fileindex = self.share_dbs.get("fileindex")

        if fileindex is None:
            return

        fifoqueue = self.config.sections["transfers"]["fifoqueue"]

        message = slskmessages.FileSearchResult(
            None,
            self.config.sections["server"]["login"],
            searchid, sorted(resultlist), fileindex, slotsavail,
            uploadspeed, queuesize, fifoqueue, numresults
        )

        self.core.send_message_to_peer(user, message)

        if direct:
            log.add_search(
                _("User %(user)s is directly searching for \"%(query)s\", returning %(num)i results"), {
                    'user': user,
                    'query': searchterm_old,
                    'num': numresults
                })
        else:
            log.add_search(
                _("User %(user)s is searching for \"%(query)s\", returning %(num)i results"), {
                    'user': user,
                    'query': searchterm_old,
                    'num': numresults
                })
