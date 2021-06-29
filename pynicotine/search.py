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
import re
import string

from pynicotine import slskmessages
from pynicotine.logfacility import log


class Search:

    def __init__(self, core, config, queue, share_dbs, ui_callback=None):

        self.core = core
        self.config = config
        self.queue = queue
        self.ui_callback = None
        self.searchid = int(random.random() * (2 ** 31 - 1))
        self.share_dbs = share_dbs
        self.translatepunctuation = str.maketrans(dict.fromkeys(string.punctuation, ' '))

        if hasattr(ui_callback, "searches"):
            self.ui_callback = ui_callback.searches

    def request_folder_download(self, user, folder, visible_files):

        # First queue the visible search results
        if self.config.sections["transfers"]["reverseorder"]:
            visible_files.sort(key=lambda x: x[1], reverse=True)

        for file in visible_files:
            user, fullpath, destination, size, bitrate, length = file

            self.core.transfers.get_file(
                user, fullpath, destination,
                size=size, bitrate=bitrate, length=length, checkduplicate=True
            )

        # Ask for the rest of the files in the folder
        self.core.transfers.get_folder(user, folder)

    """ Outgoing search requests """

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
        searchterm_words_ignore = (p[1:] for p in searchterm_words if p.startswith('-') and len(p) > 1)

        # Remove words starting with "-", results containing these are excluded by us later
        searchterm_without_excluded = ' '.join(p for p in searchterm_words if not p.startswith('-'))

        if self.config.sections["searches"]["remove_special_chars"]:
            """
            Remove special characters from search term
            SoulseekQt doesn't seem to send search results if special characters are included (July 7, 2020)
            """
            stripped_searchterm = re.sub(r'\W+', ' ', searchterm_without_excluded)

            # Only modify search term if string also contains non-special characters
            if stripped_searchterm:
                searchterm_without_excluded = stripped_searchterm

        # Remove trailing whitespace
        searchterm_without_excluded = searchterm_without_excluded.strip()

        # Append excluded words
        searchterm_with_excluded = searchterm_without_excluded

        for word in searchterm_words_ignore:
            searchterm_with_excluded += " -" + word

        items = self.config.sections["searches"]["history"]

        if searchterm_with_excluded in items:
            items.remove(searchterm_with_excluded)

        items.insert(0, searchterm_with_excluded)

        # Clear old items
        del items[15:]
        self.config.write_configuration()

        if mode == "global":
            self.do_global_search(self.searchid, searchterm_without_excluded)

        elif mode == "rooms":
            self.do_rooms_search(self.searchid, searchterm_without_excluded, room)

        elif mode == "buddies":
            self.do_buddies_search(self.searchid, searchterm_without_excluded)

        elif mode == "user":
            self.do_peer_search(self.searchid, searchterm_without_excluded, users)

        return (self.searchid, searchterm_with_excluded, searchterm_without_excluded)

    def do_global_search(self, search_id, text):
        self.queue.append(slskmessages.FileSearch(search_id, text))

        """ Request a list of related searches from the server.
        Seemingly non-functional since 2018 (always receiving empty lists). """

        # self.queue.append(slskmessages.RelatedSearch(text))

    def do_rooms_search(self, search_id, text, room=None):

        if room is not None:
            self.queue.append(slskmessages.RoomSearch(room, search_id, text))
        else:
            for joined_room in self.core.chatrooms.joinedrooms:
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
        self.queue.append(slskmessages.WishlistSearch(search_id, text))

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

        return self.searchid

    def set_wishlist_interval(self, msg):

        if self.ui_callback:
            self.ui_callback.set_wishlist_interval(msg)

        log.add_search(_("Wishlist wait period set to %s seconds"), msg.seconds)

    def show_search_result(self, msg, username, country):
        if self.ui_callback:
            self.ui_callback.show_search_result(msg, username, country)

    """ Incoming search requests """

    @staticmethod
    def create_search_result_list(searchterm, wordindex):

        try:
            """ Stage 1: Check if each word in the search term is included in our word index.
            If this is the case, we select the word that has the most file matches in our
            word index. If not, exit, since we don't have relevant results. """

            largest = 0
            words = searchterm.split()

            for word in words:
                if word not in wordindex:
                    return None

                list_size = len(wordindex[word])

                if list_size > largest:
                    largest = list_size
                    largest_key = word

            """ Stage 2: Start with the word that has the most file matches, which we selected
            in the previous step, and gradually remove matches that other words in the search
            term don't have. Return the remaining matches, if any. """

            results = wordindex[largest_key]
            words.remove(largest_key)

            for word in words:
                results = set(results).intersection(wordindex[word])

            return results

        except ValueError:
            # DB is closed, perhaps when rescanning share or closing Nicotine+
            return None

    def process_search_request(self, searchterm, user, searchid, direct=False):
        """ Note: since this section is accessed every time a search request arrives,
        several times a second, please keep it as optimized and memory
        sparse as possible! """

        if not self.config.sections["searches"]["search_results"]:
            # Don't return _any_ results when this option is disabled
            return

        if searchterm is None:
            return

        if not direct and user == self.config.sections["server"]["login"]:
            # We shouldn't send a search response if we initiated the search request,
            # unless we're specifically searching our own username
            return

        maxresults = self.config.sections["searches"]["maxresults"]

        if maxresults == 0:
            return

        # Don't count excluded words as matches (words starting with -)
        if '-' in searchterm:
            searchterm = re.sub(r'(\s)-\w+', '', searchterm)

        # Strip punctuation
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
        resultlist = self.create_search_result_list(searchterm, wordindex)

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
            searchid, resultlist, fileindex, slotsavail,
            uploadspeed, queuesize, fifoqueue, numresults
        )

        self.core.send_message_to_peer(user, message)

        if direct:
            log.add_search(
                _("User %(user)s is directly searching for \"%(query)s\", returning %(num)i results"), {
                    'user': user,
                    'query': searchterm,
                    'num': numresults
                })
        else:
            log.add_search(
                _("User %(user)s is searching for \"%(query)s\", returning %(num)i results"), {
                    'user': user,
                    'query': searchterm,
                    'num': numresults
                })
