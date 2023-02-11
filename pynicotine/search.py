# COPYRIGHT (C) 2020-2022 Nicotine+ Contributors
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
from pynicotine.slskmessages import increment_token
from pynicotine.utils import TRANSLATE_PUNCTUATION


class Search:

    def __init__(self):

        self.searches = {}
        self.token = int(random.random() * (2 ** 31 - 1))
        self.wishlist_interval = 0
        self._wishlist_timer_id = None

        # Create wishlist searches
        for term in config.sections["server"]["autosearch"]:
            self.token = increment_token(self.token)
            self.searches[self.token] = {"id": self.token, "term": term, "mode": "wishlist", "ignore": True}

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
        self.searches.clear()

    def _server_disconnect(self, _msg):
        events.cancel_scheduled(self._wishlist_timer_id)
        self.wishlist_interval = 0

    def request_folder_download(self, user, folder, visible_files):

        # First queue the visible search results
        visible_files.sort(key=itemgetter(1), reverse=config.sections["transfers"]["reverseorder"])

        for file in visible_files:
            user, fullpath, destination, size, bitrate, length = file

            core.transfers.get_file(
                user, fullpath, destination,
                size=size, bitrate=bitrate, length=length)

        # Ask for the rest of the files in the folder
        core.transfers.get_folder(user, folder)

    """ Outgoing search requests """

    @staticmethod
    def add_allowed_token(token):
        """ Allow parsing search result messages for a search ID """
        slskmessages.SEARCH_TOKENS_ALLOWED.add(token)

    @staticmethod
    def remove_allowed_token(token):
        """ Disallow parsing search result messages for a search ID """
        slskmessages.SEARCH_TOKENS_ALLOWED.discard(token)

    def add_search(self, term, mode, ignore):
        self.searches[self.token] = {"id": self.token, "term": term, "mode": mode, "ignore": ignore}
        self.add_allowed_token(self.token)

    def remove_search(self, token):

        self.remove_allowed_token(token)
        search = self.searches.get(token)

        if search is None:
            return

        if search["term"] in config.sections["server"]["autosearch"]:
            search["ignore"] = True
        else:
            del self.searches[token]

        events.emit("remove-search", token)

    def show_search(self, token):
        events.emit("show-search", token)

    def process_search_term(self, search_term, mode, room=None, user=None):

        users = []

        if mode == "global":
            if core:
                feedback = core.pluginhandler.outgoing_global_search_event(search_term)

                if feedback is not None:
                    search_term = feedback[0]

        elif mode == "rooms":
            if not room:
                room = _("Joined Rooms ")

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
            if user:
                users.append(user)

            if core:
                if not users:
                    users.append(core.login_username)

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
            """
            Remove special characters from search term
            SoulseekQt doesn't seem to send search results if special characters are included (July 7, 2020)
            """
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

    def do_search(self, search_term, mode, room=None, user=None, switch_page=True):

        # Validate search term and run it through plugins
        search_term, _search_term_without_special, room, users = self.process_search_term(search_term, mode, room, user)

        # Get a new search token
        self.token = increment_token(self.token)

        if config.sections["searches"]["enable_history"]:
            items = config.sections["searches"]["history"]

            if search_term in items:
                items.remove(search_term)

            items.insert(0, search_term)

            # Clear old items
            del items[200:]
            config.write_configuration()

        if mode == "global":
            self.do_global_search(search_term)

        elif mode == "rooms":
            self.do_rooms_search(search_term, room)

        elif mode == "buddies":
            self.do_buddies_search(search_term)

        elif mode == "user":
            self.do_peer_search(search_term, users)

        self.add_search(search_term, mode, ignore=False)

        events.emit("do-search", self.token, search_term, mode, room, users, switch_page)

    def do_global_search(self, text):
        core.queue.append(slskmessages.FileSearch(self.token, text))

        """ Request a list of related searches from the server.
        Seemingly non-functional since 2018 (always receiving empty lists). """

        # core.queue.append(slskmessages.RelatedSearch(text))

    def do_rooms_search(self, text, room=None):

        if room != _("Joined Rooms "):
            core.queue.append(slskmessages.RoomSearch(room, self.token, text))
            return

        for joined_room in core.chatrooms.joined_rooms:
            core.queue.append(slskmessages.RoomSearch(joined_room, self.token, text))

    def do_buddies_search(self, text):
        for user in core.userlist.buddies:
            core.queue.append(slskmessages.UserSearch(user, self.token, text))

    def do_peer_search(self, text, users):
        for user in users:
            core.queue.append(slskmessages.UserSearch(user, self.token, text))

    def do_wishlist_search(self, token, text):

        text = text.strip()

        if not text:
            return

        log.add_search(_('Searching for wishlist item "%s"'), text)

        self.add_allowed_token(token)
        core.queue.append(slskmessages.WishlistSearch(token, text))

    def do_wishlist_search_interval(self):

        searches = config.sections["server"]["autosearch"]

        if not searches:
            return

        # Search for a maximum of 1 item at each search interval
        term = searches.pop()
        searches.insert(0, term)

        for search in self.searches.values():
            if search["term"] == term and search["mode"] == "wishlist":
                search["ignore"] = False
                self.do_wishlist_search(search["id"], term)
                break

    def add_wish(self, wish):

        if not wish:
            return

        # Get a new search token
        self.token = increment_token(self.token)

        if wish not in config.sections["server"]["autosearch"]:
            config.sections["server"]["autosearch"].append(wish)
            config.write_configuration()

        self.add_search(wish, "wishlist", ignore=True)

        events.emit("add-wish", wish)

    def remove_wish(self, wish):

        if wish in config.sections["server"]["autosearch"]:
            config.sections["server"]["autosearch"].remove(wish)
            config.write_configuration()

            for search in self.searches.values():
                if search["term"] == wish and search["mode"] == "wishlist":
                    del search
                    break

        events.emit("remove-wish", wish)

    def is_wish(self, wish):
        return wish in config.sections["server"]["autosearch"]

    def _set_wishlist_interval(self, msg):
        """ Server code: 104 """

        self.wishlist_interval = msg.seconds

        if self.wishlist_interval > 0:
            log.add_search(_("Wishlist wait period set to %s seconds"), self.wishlist_interval)

            events.cancel_scheduled(self._wishlist_timer_id)
            self._wishlist_timer_id = events.schedule(
                delay=self.wishlist_interval, callback=self.do_wishlist_search_interval, repeat=True)
        else:
            log.add(_("Server does not permit performing wishlist searches at this time"))

    def _file_search_response(self, msg):
        """ Peer message: 9 """

        if msg.token not in slskmessages.SEARCH_TOKENS_ALLOWED:
            return

        search = self.searches.get(msg.token)

        if search is None or search["ignore"]:
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
        """ Server code: 26, 42 and 120 """

        self.process_search_request(msg.searchterm, msg.user, msg.token, direct=True)
        core.pluginhandler.search_request_notification(msg.searchterm, msg.user, msg.token)

    def _file_search_request_distributed(self, msg):
        """ Distrib code: 3 """

        self.process_search_request(msg.searchterm, msg.user, msg.token, direct=False)
        core.pluginhandler.distrib_search_notification(msg.searchterm, msg.user, msg.token)

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
            num_words = len(words)
            results = None

            for current_index, word in enumerate(words):
                exclude_word = False

                if word in excluded_words:
                    # Excluded search words (e.g. -hello)

                    if results is None and current_index < num_words:
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
            log.add_debug("Error: DB closed during search, perhaps due to rescanning shares or closing the application")
            return None

    def process_search_request(self, searchterm, user, token, direct=False):
        """ Note: since this section is accessed every time a search request arrives several
            times per second, please keep it as optimized and memory sparse as possible! """

        if not searchterm:
            return

        if not config.sections["searches"]["search_results"]:
            # Don't return _any_ results when this option is disabled
            return

        if not direct and user == core.login_username:
            # We shouldn't send a search response if we initiated the search request,
            # unless we're specifically searching our own username
            return

        maxresults = config.sections["searches"]["maxresults"]

        if maxresults == 0:
            return

        # Remember excluded/partial words for later
        excluded_words = []
        partial_words = []

        if "-" in searchterm or "*" in searchterm:
            for word in searchterm.split():
                if len(word) < 1:
                    continue

                if word.startswith("-"):
                    for subword in word.translate(TRANSLATE_PUNCTUATION).split():
                        excluded_words.append(subword)

                elif word.startswith("*"):
                    for subword in word.translate(TRANSLATE_PUNCTUATION).split():
                        partial_words.append(subword)

        # Strip punctuation
        searchterm_old = searchterm
        searchterm = searchterm.lower().translate(TRANSLATE_PUNCTUATION).strip()

        if len(searchterm) < config.sections["searches"]["min_search_chars"]:
            # Don't send search response if search term contains too few characters
            return

        checkuser, _reason = core.network_filter.check_user(user)

        if not checkuser:
            return

        if checkuser == 2:
            wordindex = core.shares.share_dbs.get("buddywordindex")
        else:
            wordindex = core.shares.share_dbs.get("wordindex")

        if wordindex is None:
            return

        # Find common file matches for each word in search term
        resultlist = self.create_search_result_list(searchterm, wordindex, excluded_words, partial_words)

        if not resultlist:
            return

        if checkuser == 2:
            fileindex = core.shares.share_dbs.get("buddyfileindex")
        else:
            fileindex = core.shares.share_dbs.get("fileindex")

        if fileindex is None:
            return

        fileinfos = []
        numresults = min(len(resultlist), maxresults)

        for index in islice(resultlist, numresults):
            fileinfo = fileindex.get(repr(index))

            if fileinfo is not None:
                fileinfos.append(fileinfo)

        if numresults != len(fileinfos):
            log.add_debug(('Error: File index inconsistency while responding to search request "%(query)s". '
                           "Expected %(expected_num)i results, but found %(total_num)i results in database."), {
                "query": searchterm_old,
                "expected_num": numresults,
                "total_num": len(fileinfos)
            })
            numresults = len(fileinfos)

        if not numresults:
            return

        fileinfos.sort(key=itemgetter(1))

        uploadspeed = core.transfers.upload_speed
        queuesize = core.transfers.get_upload_queue_size()
        slotsavail = core.transfers.allow_new_uploads()
        fifoqueue = config.sections["transfers"]["fifoqueue"]

        message = slskmessages.FileSearchResponse(
            None, core.login_username,
            token, fileinfos, slotsavail, uploadspeed, queuesize, fifoqueue)

        core.send_message_to_peer(user, message)

        log.add_search(_('User %(user)s is searching for "%(query)s", found %(num)i results'), {
            "user": user,
            "query": searchterm_old,
            "num": numresults
        })
