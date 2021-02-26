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

import operator
import os
import random
import re
import sre_constants

from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk

from pynicotine import slskmessages
from pynicotine.geoip.countrycodes import code2name
from pynicotine.gtkgui.dialogs import choose_dir
from pynicotine.gtkgui.fileproperties import FileProperties
from pynicotine.gtkgui.utils import collapse_treeview
from pynicotine.gtkgui.utils import humanize
from pynicotine.gtkgui.utils import human_size
from pynicotine.gtkgui.utils import human_speed
from pynicotine.gtkgui.utils import IconNotebook
from pynicotine.gtkgui.utils import initialise_columns
from pynicotine.gtkgui.utils import load_ui_elements
from pynicotine.gtkgui.utils import PopupMenu
from pynicotine.gtkgui.utils import save_columns
from pynicotine.gtkgui.utils import select_user_row_iter
from pynicotine.gtkgui.utils import set_widget_fg_bg_css
from pynicotine.gtkgui.utils import set_treeview_selected_row
from pynicotine.gtkgui.utils import show_country_tooltip
from pynicotine.gtkgui.utils import show_file_path_tooltip
from pynicotine.gtkgui.utils import triggers_context_menu
from pynicotine.gtkgui.utils import update_widget_visuals
from pynicotine.gtkgui.wishlist import WishList
from pynicotine.logfacility import log
from pynicotine.utils import get_result_bitrate_length


class Searches(IconNotebook):

    def __init__(self, frame):

        self.frame = frame

        self.searchid = int(random.random() * (2 ** 31 - 1))
        self.searches = {}
        self.usersearches = {}
        self.users = {}
        self.maxdisplayedresults = self.frame.np.config.sections['searches']["max_displayed_results"]
        self.maxstoredresults = self.frame.np.config.sections['searches']["max_stored_results"]

        ui = self.frame.np.config.sections["ui"]

        IconNotebook.__init__(
            self,
            self.frame.images,
            angle=ui["labelsearch"],
            tabclosers=ui["tabclosers"],
            show_hilite_image=self.frame.np.config.sections["notifications"]["notification_tab_icons"],
            reorderable=ui["tab_reorderable"],
            notebookraw=self.frame.SearchNotebookRaw
        )

        self.popup_enable()
        self.load_config()

        self.wish_list = WishList(frame, self)

        self.update_visuals()

    def load_config(self):
        """
        Add search history to SearchCombo later and connect Wishlist,
        after widgets have been created.
        """
        items = self.frame.np.config.sections["searches"]["history"]
        templist = []

        for i in items:
            if not isinstance(i, str):
                continue

            if i not in templist:
                templist.append(i)

        for i in templist:
            self.frame.SearchCombo.append_text(i)

    def on_search(self):

        self.save_columns()

        text = self.frame.SearchEntry.get_text().strip()

        if not text:
            return

        users = []
        room = None
        search_mode = self.frame.SearchMethod.get_active_id()
        feedback = None

        if search_mode == "global":
            feedback = self.frame.np.pluginhandler.outgoing_global_search_event(text)

            if feedback is not None:
                text = feedback[0]

        elif search_mode == "rooms":
            name = self.frame.RoomSearchEntry.get_text()
            # Space after Joined Rooms is important, so it doesn't conflict
            # with any possible real room
            if name != _("Joined Rooms ") and not name.isspace():
                room = name

            feedback = self.frame.np.pluginhandler.outgoing_room_search_event(room, text)

            if feedback is not None:
                (room, text) = feedback

        elif search_mode == "buddies":
            feedback = self.frame.np.pluginhandler.outgoing_buddy_search_event(text)

            if feedback is not None:
                text = feedback[0]

        elif search_mode == "user":
            user = self.frame.UserSearchEntry.get_text().strip()

            if user:
                users = [user]
            else:
                return

            feedback = self.frame.np.pluginhandler.outgoing_user_search_event(users, text)

            if feedback is not None:
                (users, text) = feedback

        else:
            log.add_warning(_("Unknown search mode, not using plugin system. Fix me!"))
            feedback = True

        if feedback is not None:
            self.do_search(text, search_mode, users, room)

    def do_search(self, text, mode, users=[], room=None):

        # Get excluded words (starting with "-")
        searchterm_words = text.split()
        searchterm_words_ignore = (p[1:] for p in searchterm_words if p.startswith('-') and len(p) > 1)

        # Remove words starting with "-", results containing these are excluded by us later
        searchterm_without_excluded = re.sub(r'(\s)-\w+', r'\1', text)

        if self.frame.np.config.sections["searches"]["remove_special_chars"]:
            """
            Remove special characters from search term
            SoulseekQt doesn't seem to send search results if special characters are included (July 7, 2020)
            """
            searchterm_without_excluded = re.sub(r'\W+', ' ', searchterm_without_excluded)

        # Remove trailing whitespace
        searchterm_without_excluded = searchterm_without_excluded.strip()

        # Append excluded words
        searchterm_with_excluded = searchterm_without_excluded

        for word in searchterm_words_ignore:
            searchterm_with_excluded += " -" + word

        items = self.frame.np.config.sections["searches"]["history"]

        if searchterm_with_excluded in items:
            items.remove(searchterm_with_excluded)

        items.insert(0, searchterm_with_excluded)

        # Clear old items
        del items[15:]
        self.frame.np.config.write_configuration()

        # Repopulate the combo list
        self.frame.SearchCombo.remove_all()

        for i in items:
            if not isinstance(i, str):
                continue

            self.frame.SearchCombo.append_text(i)

        if mode == "user" and users != [] and users[0] != '':
            self.usersearches[self.searchid] = users

        search = self.create_tab(self.searchid, searchterm_with_excluded, mode, showtab=True)
        if search["tab"] is not None:
            self.set_current_page(self.page_num(search["tab"].Main))

        if mode == "global":
            self.do_global_search(self.searchid, searchterm_without_excluded)

        elif mode == "rooms":
            self.do_rooms_search(self.searchid, searchterm_without_excluded, room)

        elif mode == "buddies":
            self.do_buddies_search(self.searchid, searchterm_without_excluded)

        elif mode == "user" and users != [] and users[0] != '':
            self.do_peer_search(self.searchid, searchterm_without_excluded, users)

        self.searchid += 1

    def do_global_search(self, id, text):
        self.frame.np.queue.put(slskmessages.FileSearch(id, text))

        """ Request a list of related searches from the server.
        Seemingly non-functional since 2018 (always receiving empty lists). """

        # self.frame.np.queue.put(slskmessages.RelatedSearch(text))

    def do_rooms_search(self, id, text, room=None):
        if room is not None:
            self.frame.np.queue.put(slskmessages.RoomSearch(room, id, text))
        else:
            for room in self.frame.chatrooms.joinedrooms:
                self.frame.np.queue.put(slskmessages.RoomSearch(room, id, text))

    def do_buddies_search(self, id, text):
        for i in self.frame.np.config.sections["server"]["userlist"]:
            user = i[0]
            self.frame.np.queue.put(slskmessages.UserSearch(user, id, text))

    def do_peer_search(self, id, text, users):
        for user in users:
            self.frame.np.send_message_to_peer(user, slskmessages.FileSearchRequest(None, id, text))

    def clear_search_history(self):

        self.frame.SearchEntry.set_text("")

        self.frame.np.config.sections["searches"]["history"] = []
        self.frame.np.config.write_configuration()

        self.frame.SearchCombo.remove_all()

    def clear_filter_history(self):

        # Clear filter history in config
        self.frame.np.config.sections["searches"]["filterin"] = []
        self.frame.np.config.sections["searches"]["filterout"] = []
        self.frame.np.config.sections["searches"]["filtertype"] = []
        self.frame.np.config.sections["searches"]["filtersize"] = []
        self.frame.np.config.sections["searches"]["filterbr"] = []
        self.frame.np.config.sections["searches"]["filtercc"] = []
        self.frame.np.config.write_configuration()

        # Update filters in search tabs
        for id in self.searches.values():
            if id["tab"] is None:
                continue

            id["tab"].populate_filters(set_default_filters=False)

    def get_user_search_name(self, id):

        if id in self.usersearches:

            users = self.usersearches[id]

            if len(users) > 1:
                return _("Users")
            elif len(users) == 1:
                return users[0]

        return _("User")

    def create_tab(self, id, text, mode, remember=False, showtab=True):

        tab = Search(self, text, id, mode, remember, showtab)

        if showtab:
            self.show_tab(tab, id, text, mode)

        ignore = False
        search = {"id": id, "term": text, "tab": tab, "mode": mode, "remember": remember, "ignore": ignore}
        self.searches[id] = search

        return search

    def show_tab(self, tab, id, text, mode):

        length = 25
        template = "(%s) %s"

        if mode == "rooms":
            fulltext = template % (_("Rooms"), text)

        elif mode == "buddies":
            fulltext = template % (_("Buddies"), text)

        elif mode == "wishlist":
            fulltext = template % (_("Wish"), text)

        elif mode == "user":
            fulltext = template % (self.get_user_search_name(id), text)

        else:
            fulltext = text
            length = 20

        label = fulltext[:length]
        self.append_page(tab.Main, label, tab.on_close, fulltext=fulltext)

    def show_result(self, msg, username, country):

        try:
            search = self.searches[msg.token]
        except KeyError:
            return

        if search["ignore"]:
            return

        if search["tab"] is None:
            search = self.create_tab(search["id"], search["term"], search["mode"], search["remember"], showtab=False)

        counter = len(search["tab"].all_data) + 1

        # No more things to add because we've reached the max_stored_results limit
        if counter > self.maxstoredresults:
            return

        search["tab"].add_user_results(msg, username, country)

    def remove_tab(self, tab):

        if tab.id in self.searches:
            search = self.searches[tab.id]

            if tab.text not in self.frame.np.config.sections["server"]["autosearch"]:
                del self.searches[tab.id]
            else:
                search["tab"] = None
                search["ignore"] = True

        self.remove_page(tab.Main)

    def update_visuals(self):

        for id in self.searches.values():
            if id["tab"] is None:
                continue
            id["tab"].update_visuals()

        self.wish_list.update_visuals()

    def save_columns(self):

        page_num = self.get_current_page()

        if page_num is not None:
            page = self.get_nth_page(page_num)

            for search in self.searches.values():
                if search["tab"] is None:
                    continue

                if search["tab"].Main == page:
                    search["tab"].save_columns()
                    break

    def get_search_id(self, child):

        search_id = None
        n = self.page_num(child)
        page = self.get_nth_page(n)

        for search, data in self.searches.items():

            if data["tab"] is None:
                continue
            if data["tab"].Main is page:
                search_id = search
                break

        return search_id

    def on_tab_popup(self, widget, child):

        search_id = self.get_search_id(child)

        if search_id is None:
            log.add_warning(_("Search ID was none when clicking tab"))
            return False

        menu = PopupMenu(self.frame)
        menu.setup(
            ("#" + _("Copy Search Term"), self.searches[search_id]["tab"].on_copy_search_term),
            ("", None),
            ("#" + _("Clear All Results"), self.searches[search_id]["tab"].on_clear),
            ("#" + _("Close All Tabs"), menu.on_close_all_tabs, self),
            ("#" + _("_Close Tab"), self.searches[search_id]["tab"].on_close)
        )

        menu.popup()
        return True

    def on_tab_click(self, widget, event, child):

        search_id = self.get_search_id(child)

        if search_id is None:
            log.add_warning(_("Search ID was none when clicking tab"))
            return False

        if triggers_context_menu(event):
            return self.on_tab_popup(widget, child)

        if event.button == 2:
            self.searches[search_id]["tab"].on_close(widget)
            return True

        return False

    def close_all_tabs(self, dialog, response, data):

        if response == Gtk.ResponseType.OK:
            for search_id in self.searches.copy():
                self.searches[search_id]["tab"].on_close(dialog)

        dialog.destroy()


class Search:

    def __init__(self, searches, text, id, mode, remember, showtab):

        self.searches = searches
        self.frame = searches.frame

        # Build the window
        load_ui_elements(self, os.path.join(self.frame.gui_dir, "ui", "search.ui"))

        self.text = text
        self.searchterm_words_include = [p for p in text.lower().split() if not p.startswith('-')]
        self.searchterm_words_ignore = [p[1:] for p in text.lower().split() if p.startswith('-') and len(p) > 1]

        self.id = id
        self.mode = mode
        self.remember = remember
        self.showtab = showtab
        self.usersiters = {}
        self.directoryiters = {}
        self.users = set()
        self.all_data = []
        self.filters = None
        self.clearing_filters = False
        self.resultslimit = 2000
        self.numvisibleresults = 0
        self.active_filter_count = 0

        self.operators = {
            '<': operator.lt,
            '<=': operator.le,
            '==': operator.eq,
            '!=': operator.ne,
            '>=': operator.ge,
            '>': operator.gt
        }

        if mode not in ("global", "wishlist"):
            self.RememberCheckButton.hide()

        self.RememberCheckButton.set_active(remember)

        """ Columns """

        self.resultsmodel = Gtk.TreeStore(
            GObject.TYPE_UINT64,  # (0)  num
            str,                  # (1)  user
            GObject.TYPE_OBJECT,  # (2)  flag
            str,                  # (3)  immediatedl
            str,                  # (4)  h_speed
            str,                  # (5)  h_queue
            str,                  # (6)  directory
            str,                  # (7)  filename
            str,                  # (8)  h_size
            str,                  # (9)  h_bitrate
            str,                  # (10) h_length
            GObject.TYPE_UINT64,  # (11) bitrate
            str,                  # (12) fullpath
            str,                  # (13) country
            GObject.TYPE_UINT64,  # (14) size
            GObject.TYPE_UINT64,  # (15) speed
            GObject.TYPE_UINT64,  # (16) queue
            GObject.TYPE_UINT64,  # (17) length
            str                   # (18) color
        )

        self.column_numbers = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18]
        color_col = 18
        self.cols = cols = initialise_columns(
            "file_search",
            self.ResultsList,
            ["id", _("ID"), 50, "text", color_col],
            ["user", _("User"), 200, "text", color_col],
            ["country", _("Country"), 25, "pixbuf", None],
            ["immediate_download", _("Immediate Download"), 50, "center", color_col],
            ["speed", _("Speed"), 90, "number", color_col],
            ["in_queue", _("In Queue"), 90, "center", color_col],
            ["folder", _("Folder"), 400, "text", color_col],
            ["filename", _("Filename"), 400, "text", color_col],
            ["size", _("Size"), 100, "number", color_col],
            ["bitrate", _("Bitrate"), 100, "number", color_col],
            ["length", _("Length"), 100, "number", color_col]
        )

        cols["id"].set_sort_column_id(0)
        cols["user"].set_sort_column_id(1)
        cols["country"].set_sort_column_id(13)
        cols["immediate_download"].set_sort_column_id(3)
        cols["speed"].set_sort_column_id(15)
        cols["in_queue"].set_sort_column_id(16)
        cols["folder"].set_sort_column_id(6)
        cols["filename"].set_sort_column_id(7)
        cols["size"].set_sort_column_id(14)
        cols["bitrate"].set_sort_column_id(11)
        cols["length"].set_sort_column_id(17)

        cols["country"].get_widget().hide()

        self.ResultsList.set_model(self.resultsmodel)

        self.update_visuals()

        """ Filters """

        self.ShowFilters.set_active(self.frame.np.config.sections["searches"]["filters_visible"])
        self.populate_filters()

        """ Popup """

        self.popup_menu_users = PopupMenu(self.frame, False)
        self.popup_menu = popup = PopupMenu(self.frame)
        popup.setup(
            ("#" + "selected_files", None),
            ("", None),
            ("#" + _("_Download File(s)"), self.on_download_files),
            ("#" + _("Download File(s) _To..."), self.on_download_files_to),
            ("#" + _("Download _Folder(s)"), self.on_download_folders),
            ("#" + _("Download F_older(s) To..."), self.on_download_folders_to),
            ("#" + _("_Browse Folder"), self.on_browse_folder),
            ("#" + _("File _Properties"), self.on_file_properties),
            ("", None),
            ("#" + _("Copy _File Path"), self.on_copy_file_path),
            ("#" + _("Copy _URL"), self.on_copy_url),
            ("#" + _("Copy Folder U_RL"), self.on_copy_dir_url),
            ("", None),
            (1, _("User(s)"), self.popup_menu_users, self.on_popup_menu_users)
        )

        """ Grouping """

        self.ResultGrouping.set_active(self.frame.np.config.sections["searches"]["group_searches"])
        self.ExpandButton.set_active(self.frame.np.config.sections["searches"]["expand_searches"])

    def on_tooltip(self, widget, x, y, keyboard_mode, tooltip):

        country_tooltip = show_country_tooltip(widget, x, y, tooltip, 13, stripprefix='')
        file_path_tooltip = show_file_path_tooltip(widget, x, y, tooltip, 12)

        if country_tooltip:
            return country_tooltip

        elif file_path_tooltip:
            return file_path_tooltip

    def populate_filters(self, set_default_filters=True):

        for combobox in (self.FilterIn, self.FilterOut, self.FilterType, self.FilterSize,
                         self.FilterBitrate, self.FilterCountry):
            combobox.remove_all()

        if set_default_filters and self.frame.np.config.sections["searches"]["enablefilters"]:

            sfilter = self.frame.np.config.sections["searches"]["defilter"]

            self.FilterInEntry.set_text(str(sfilter[0]))
            self.FilterOutEntry.set_text(str(sfilter[1]))
            self.FilterSizeEntry.set_text(str(sfilter[2]))
            self.FilterBitrateEntry.set_text(str(sfilter[3]))
            self.FilterFreeSlot.set_active(str(sfilter[4]))

            if(len(sfilter) > 5):
                self.FilterCountryEntry.set_text(str(sfilter[5]))

            if(len(sfilter) > 6):
                self.FilterTypeEntry.set_text(str(sfilter[6]))

            self.on_refilter(None)

        for i in ['0', '128', '160', '192', '256', '320']:
            self.FilterBitrate.append_text(i)

        for i in [">10MiB", "<10MiB", "<5MiB", "<1MiB", ">0"]:
            self.FilterSize.append_text(i)

        for i in ['flac|wav|ape|aiff|wv|cue', 'mp3|m4a|aac|ogg|opus|wma', '!mp3']:
            self.FilterType.append_text(i)

        s_config = self.frame.np.config.sections["searches"]

        for i in s_config["filterin"]:
            self.add_combo(self.FilterIn, i, True)

        for i in s_config["filterout"]:
            self.add_combo(self.FilterOut, i, True)

        for i in s_config["filtersize"]:
            self.add_combo(self.FilterSize, i, True)

        for i in s_config["filterbr"]:
            self.add_combo(self.FilterBitrate, i, True)

        for i in s_config["filtercc"]:
            self.add_combo(self.FilterCountry, i, True)

        for i in s_config["filtertype"]:
            self.add_combo(self.FilterType, i, True)

    def focus_combobox(self, button):

        # We have the button of a combobox, find the entry
        parent = button.get_parent()

        if parent is None:
            return

        if isinstance(parent, Gtk.ComboBox):
            entry = parent.get_child()
            entry.grab_focus()
            GLib.idle_add(entry.emit, "activate")
            return

        self.focus_combobox(parent)

    def add_combo(self, combobox, text, list=False):

        text = str(text).strip()
        if not text:
            return False

        model = combobox.get_model()
        iterator = model.get_iter_first()
        match = False

        while iterator is not None:

            value = model.get_value(iterator, 0)

            if value.strip() == text:
                match = True

            iterator = model.iter_next(iterator)

        if not match:
            if list:
                combobox.append_text(text)
            else:
                combobox.prepend_text(text)

    def add_user_results(self, msg, user, country):

        if user in self.users:
            return

        self.users.add(user)

        counter = len(self.all_data) + 1

        inqueue = msg.inqueue
        ulspeed = msg.ulspeed
        h_speed = human_speed(ulspeed)

        if msg.freeulslots:
            imdl = "Y"
            inqueue = 0
        else:
            imdl = "N"

        color_id = (imdl == "Y" and "search" or "searchq")
        color = self.frame.np.config.sections["ui"][color_id] or None

        h_queue = humanize(inqueue)

        update_ui = False
        maxstoredresults = self.searches.maxstoredresults

        for result in msg.list:

            if counter > maxstoredresults:
                break

            fullpath = result[1]
            fullpath_lower = fullpath.lower()

            if any(word in fullpath_lower for word in self.searchterm_words_ignore):
                """ Filter out results with filtered words (e.g. nicotine -music) """
                log.add_search(_("Filtered out excluded search result " + fullpath + " from user " + user))
                continue

            if not any(word in fullpath_lower for word in self.searchterm_words_include):
                """ Some users may send us wrong results, filter out such ones """
                log.add_search(_("Filtered out inexact or incorrect search result " + fullpath + " from user " + user))
                continue

            fullpath_split = reversed(fullpath.split('\\'))
            name = next(fullpath_split)
            directory = '\\'.join(fullpath_split)

            size = result[2]
            h_size = human_size(size)
            h_bitrate, bitrate, h_length, length = get_result_bitrate_length(size, result[4])

            is_result_visible = self.append(
                [
                    GObject.Value(GObject.TYPE_UINT64, counter),
                    user,
                    GObject.Value(GObject.TYPE_OBJECT, self.frame.get_flag_image(country)),
                    imdl,
                    h_speed,
                    h_queue,
                    directory,
                    name,
                    h_size,
                    h_bitrate,
                    h_length,
                    GObject.Value(GObject.TYPE_UINT64, bitrate),
                    fullpath,
                    country,
                    GObject.Value(GObject.TYPE_UINT64, size),
                    GObject.Value(GObject.TYPE_UINT64, ulspeed),
                    GObject.Value(GObject.TYPE_UINT64, inqueue),
                    GObject.Value(GObject.TYPE_UINT64, length),
                    GObject.Value(GObject.TYPE_STRING, color)
                ]
            )

            if is_result_visible:
                update_ui = True

            counter += 1

        if update_ui:
            # If this search wasn't initiated by us (e.g. wishlist), and the results aren't spoofed, show tab
            if not self.showtab:
                self.searches.show_tab(self, self.id, self.text, self.mode)
                self.showtab = True

            # Update number of results
            self.update_result_counter()

            # Update tab notification
            self.frame.searches.request_changed(self.Main)
            self.frame.request_tab_icon(self.frame.SearchTabLabel)

    def append(self, row):

        self.all_data.append(row)

        if self.numvisibleresults >= self.searches.maxdisplayedresults:
            return False

        if not self.check_filter(row):
            return False

        iterator = self.add_row_to_model(row)

        if self.ResultGrouping.get_active_id() != "ungrouped":
            # Group by folder or user

            if self.ExpandButton.get_active():
                path = None

                if iterator is not None:
                    path = self.resultsmodel.get_path(iterator)

                if path is not None:
                    self.ResultsList.expand_to_path(path)
            else:
                collapse_treeview(self.ResultsList, self.ResultGrouping.get_active_id())

        return True

    def add_row_to_model(self, row):
        counter, user, flag, immediatedl, h_speed, h_queue, directory, filename, h_size, h_bitrate, h_length, bitrate, fullpath, country, size, speed, queue, length, color = row

        if self.ResultGrouping.get_active_id() != "ungrouped":
            # Group by folder or user

            empty_int = 0
            empty_str = ""

            if user not in self.usersiters:
                self.usersiters[user] = self.resultsmodel.insert_with_values(
                    None, -1, self.column_numbers,
                    [
                        empty_int,
                        user,
                        flag,
                        immediatedl,
                        h_speed,
                        h_queue,
                        empty_str,
                        empty_str,
                        empty_str,
                        empty_str,
                        empty_str,
                        empty_int,
                        empty_str,
                        country,
                        empty_int,
                        speed,
                        queue,
                        empty_int,
                        color
                    ]
                )

            parent = self.usersiters[user]

            if self.ResultGrouping.get_active_id() == "folder_grouping":
                # Group by folder

                if directory not in self.directoryiters:
                    self.directoryiters[directory] = self.resultsmodel.insert_with_values(
                        self.usersiters[user], -1, self.column_numbers,
                        [
                            empty_int,
                            user,
                            flag,
                            immediatedl,
                            h_speed,
                            h_queue,
                            directory,
                            empty_str,
                            empty_str,
                            empty_str,
                            empty_str,
                            empty_int,
                            fullpath.rsplit('\\', 1)[0] + '\\',
                            country,
                            empty_int,
                            speed,
                            queue,
                            empty_int,
                            color
                        ]
                    )

                row = row[:]
                row[6] = ""  # Directory not visible for file row if "group by folder" is enabled

                parent = self.directoryiters[directory]
        else:
            parent = None

        try:
            """ Note that we use insert_with_values instead of append, as this reduces
            overhead by bypassing useless row conversion to GObject.Value in PyGObject. """

            iterator = self.resultsmodel.insert_with_values(parent, -1, self.column_numbers, row)

            self.numvisibleresults += 1

        except Exception as e:
            types = []
            for i in row:
                types.append(type(i))
            log.add_warning(_("Search row error: %(exception)s %(row)s"), {'exception': e, 'row': row})
            iterator = None

        return iterator

    def check_digit(self, sfilter, value, factorize=True):

        op = ">="
        if sfilter[:1] in (">", "<", "="):
            op, sfilter = sfilter[:1] + "=", sfilter[1:]

        if not sfilter:
            return True

        factor = 1
        if factorize:
            base = 1024  # Default to binary for "k", "m", "g" suffixes
            if sfilter[-1:].lower() == 'b':
                base = 1000  # Byte suffix detected, prepare to use decimal if necessary
                sfilter = sfilter[:-1]
            if sfilter[-1:].lower() == 'i':
                base = 1024  # Binary requested, stop using decimal
                sfilter = sfilter[:-1]
            if sfilter.lower()[-1:] == "g":
                factor = pow(base, 3)
                sfilter = sfilter[:-1]
            elif sfilter.lower()[-1:] == "m":
                factor = pow(base, 2)
                sfilter = sfilter[:-1]
            elif sfilter.lower()[-1:] == "k":
                factor = base
                sfilter = sfilter[:-1]

        if not sfilter:
            return True

        try:
            sfilter = int(sfilter) * factor
        except ValueError:
            return True

        operation = self.operators.get(op)
        return operation(value, sfilter)

    def check_country(self, sfilter, value):

        if not isinstance(value, str):
            return False

        value = value.upper()
        allowed = False

        for cc in sfilter.split("|"):
            if cc == value:
                allowed = True

            elif cc.startswith("!") and cc[1:] != value:
                allowed = True

            elif cc.startswith("!") and cc[1:] == value:
                return False

        return allowed

    def check_file_type(self, sfilter, value):

        if not isinstance(value, str):
            return False

        value = value.lower()
        allowed = False

        for ext in sfilter.split("|"):
            exclude_ext = None

            if ext.startswith("!"):
                exclude_ext = ext[1:]

                if not exclude_ext.startswith("."):
                    exclude_ext = "." + exclude_ext

            elif not ext.startswith("."):
                ext = "." + ext

            if not ext.startswith("!") and value.endswith(ext):
                allowed = True

            elif ext.startswith("!") and not value.endswith(exclude_ext):
                allowed = True

            elif ext.startswith("!") and value.endswith(exclude_ext):
                return False

        return allowed

    def check_filter(self, row):

        filters = self.filters
        if self.active_filter_count == 0:
            return True

        # "Included text"-filter, check full file path (located at index 12 in row)
        if filters["include"] and not filters["include"].search(row[12].lower()):
            return False

        # "Excluded text"-filter, check full file path (located at index 12 in row)
        if filters["exclude"] and filters["exclude"].search(row[12].lower()):
            return False

        if filters["size"] and not self.check_digit(filters["size"], row[14].get_uint64()):
            return False

        if filters["bitrate"] and not self.check_digit(filters["bitrate"], row[11].get_uint64(), False):
            return False

        if filters["freeslot"] and row[3] != "Y":
            return False

        if filters["country"] and not self.check_country(filters["country"], row[13]):
            return False

        if filters["type"] and not self.check_file_type(filters["type"], row[12]):
            return False

        return True

    def set_filters(self, enable, f_in, f_out, size, bitrate, freeslot, country, f_type):

        self.filters = {
            "include": None,
            "exclude": None,
            "size": None,
            "bitrate": None,
            "freeslot": freeslot,
            "country": None,
            "type": None
        }

        self.active_filter_count = 0

        if f_in:
            try:
                f_in = re.compile(f_in.lower())
                self.filters["include"] = f_in
            except sre_constants.error:
                set_widget_fg_bg_css(self.FilterInEntry, "red", "white")
            else:
                set_widget_fg_bg_css(self.FilterInEntry)

            self.active_filter_count += 1

        if f_out:
            try:
                f_out = re.compile(f_out.lower())
                self.filters["exclude"] = f_out
            except sre_constants.error:
                set_widget_fg_bg_css(self.FilterOutEntry, "red", "white")
            else:
                set_widget_fg_bg_css(self.FilterOutEntry)

            self.active_filter_count += 1

        if size:
            self.filters["size"] = size
            self.active_filter_count += 1

        if bitrate:
            self.filters["bitrate"] = bitrate
            self.active_filter_count += 1

        if country:
            self.filters["country"] = country.upper()
            self.active_filter_count += 1

        if f_type:
            self.filters["type"] = f_type.lower()
            self.active_filter_count += 1

        if freeslot:
            self.active_filter_count += 1

        self.usersiters.clear()
        self.directoryiters.clear()
        self.resultsmodel.clear()
        self.numvisibleresults = 0

        for row in self.all_data:
            if self.numvisibleresults >= self.searches.maxdisplayedresults:
                break

            if self.check_filter(row):
                self.add_row_to_model(row)

        # Update number of visible results
        self.update_result_counter()
        self.update_filter_counter(self.active_filter_count)

    def on_popup_menu_users(self, widget):

        self.select_results()

        self.popup_menu_users.clear()

        if len(self.selected_users) > 0:

            items = []

            for user in self.selected_users:
                popup = PopupMenu(self.frame, False)
                popup.setup_user_menu(user)
                popup.append_item(("", None))
                popup.append_item(("#" + _("Select User's Transfers"), self.on_select_user_results))

                items.append((1, user, popup, self.on_popup_menu_user, popup))

            self.popup_menu_users.setup(*items)

        return True

    def on_popup_menu_user(self, widget, popup=None):

        if popup is None:
            return

        popup.toggle_user_items()
        return True

    def on_select_user_results(self, widget):

        if len(self.selected_users) == 0:
            return

        selected_user = widget.get_parent().user

        sel = self.ResultsList.get_selection()
        fmodel = self.ResultsList.get_model()
        sel.unselect_all()

        iterator = fmodel.get_iter_first()

        select_user_row_iter(fmodel, sel, 1, selected_user, iterator)

        self.select_results()

    def select_results(self):

        self.selected_results = set()
        self.selected_users = set()
        self.selected_files_count = 0

        self.ResultsList.get_selection().selected_foreach(self.selected_results_callback)

    def update_result_counter(self):
        self.Counter.set_text(str(self.numvisibleresults))

    def update_visuals(self):

        for widget in self.__dict__.values():
            update_widget_visuals(widget, list_font_target="searchfont")

    def save_columns(self):
        save_columns("file_search", self.ResultsList.get_columns())

    def selected_results_callback(self, model, path, iterator):

        user = model.get_value(iterator, 1)

        if user is None:
            return

        self.selected_users.add(user)

        filepath = model.get_value(iterator, 12)

        if filepath == "":
            # Result is not a file or directory, don't add it
            return

        bitrate = model.get_value(iterator, 9)
        length = model.get_value(iterator, 10)
        size = model.get_value(iterator, 14)

        self.selected_results.add((user, filepath, size, bitrate, length))

        filename = model.get_value(iterator, 7)

        if filename:
            self.selected_files_count += 1

    def on_list_clicked(self, widget, event):

        if triggers_context_menu(event):
            set_treeview_selected_row(widget, event)
            return self.on_popup_menu(widget)

        pathinfo = widget.get_path_at_pos(event.x, event.y)

        if pathinfo is None:
            widget.get_selection().unselect_all()

        elif event.button == 1 and event.type == Gdk.EventType._2BUTTON_PRESS:
            self.select_results()
            self.on_download_files(widget)
            self.ResultsList.get_selection().unselect_all()
            return True

        return False

    def on_key_press_event(self, widget, event):

        key = Gdk.keyval_name(event.keyval)
        self.select_results()

        if key in ("C", "c") and event.state in (Gdk.ModifierType.CONTROL_MASK, Gdk.ModifierType.LOCK_MASK | Gdk.ModifierType.CONTROL_MASK):
            self.on_copy_file_path(widget)
        else:
            # No key match, continue event
            return False

        widget.stop_emission_by_name("key_press_event")
        return True

    def on_popup_menu(self, widget):

        self.select_results()

        items = self.popup_menu.get_items()
        users = len(self.selected_users) > 0
        files = len(self.selected_results) > 0

        for i in (_("_Download File(s)"), _("Download File(s) _To..."), _("File _Properties"),
                  _("Copy _URL")):
            items[i].set_sensitive(False)

        for i in (_("Download _Folder(s)"), _("Download F_older(s) To..."), _("_Browse Folder"),
                  _("Copy _File Path"), _("Copy Folder U_RL")):
            items[i].set_sensitive(files)

        items[_("User(s)")].set_sensitive(users)

        for result in self.selected_results:
            if not result[1].endswith('\\'):
                # At least one selected result is a file, activate file-related items

                for i in (_("_Download File(s)"), _("Download File(s) _To..."), _("File _Properties"),
                          _("Copy _URL")):
                    items[i].set_sensitive(True)

                break

        items["selected_files"].set_sensitive(False)
        items["selected_files"].set_label(_("%s File(s) Selected") % self.selected_files_count)

        self.popup_menu.popup()
        return True

    def on_browse_folder(self, widget):

        requested_folders = set()

        for file in self.selected_results:
            user = file[0]
            folder = file[1].rsplit('\\', 1)[0]

            if folder not in requested_folders:
                self.frame.browse_user(user, folder)
                requested_folders.add(folder)

    def selected_results_all_data(self, model, path, iterator, data):

        filename = model.get_value(iterator, 7)

        # We only want to see the metadata of files, not directories
        if filename != "":
            num = model.get_value(iterator, 0)
            user = model.get_value(iterator, 1)
            immediate = model.get_value(iterator, 3)
            speed = model.get_value(iterator, 4)
            queue = model.get_value(iterator, 5)
            size = model.get_value(iterator, 8)
            bitratestr = model.get_value(iterator, 9)
            length = model.get_value(iterator, 10)
            fn = model.get_value(iterator, 12)
            directory = fn.rsplit('\\', 1)[0]
            cc = model.get_value(iterator, 13)
            country = "%s / %s" % (cc, code2name(cc))

            data.append({
                "user": user,
                "fn": fn,
                "position": num,
                "filename": filename,
                "directory": directory,
                "size": size,
                "speed": speed,
                "queue": queue,
                "immediate": immediate,
                "bitrate": bitratestr,
                "length": length,
                "country": country
            })

    def on_file_properties(self, widget):

        if not self.frame.np.transfers:
            return

        data = []
        self.ResultsList.get_selection().selected_foreach(self.selected_results_all_data, data)

        if data:
            FileProperties(self.frame, data).show()

    def on_download_files(self, widget, prefix=""):

        if not self.frame.np.transfers:
            return

        for file in self.selected_results:
            # Make sure the selected result is not a directory
            if not file[1].endswith('\\'):
                self.frame.np.transfers.get_file(file[0], file[1], prefix, size=file[2], bitrate=file[3], length=file[4], checkduplicate=True)

    def on_download_files_to(self, widget):

        folder = choose_dir(self.frame.MainWindow, self.frame.np.config.sections["transfers"]["downloaddir"], multichoice=False)

        if folder is None:
            return

        for folders in folder:
            self.on_download_files(widget, folders)
            break

    def on_download_folders(self, widget):

        requested_folders = {}

        for i in self.selected_results:

            user = i[0]
            folder = i[1].rsplit('\\', 1)[0]

            if user not in requested_folders:
                requested_folders[user] = []

            if folder not in requested_folders[user]:
                """ Ensure we don't send folder content requests for a folder more than once,
                e.g. when several selected resuls belong to the same folder. """

                self.frame.np.send_message_to_peer(user, slskmessages.FolderContentsRequest(None, folder))
                requested_folders[user].append(folder)

    def on_download_folders_to(self, widget):

        directories = choose_dir(self.frame.MainWindow, self.frame.np.config.sections["transfers"]["downloaddir"], multichoice=False)

        if directories is None or directories == []:
            return

        destination = directories[0]

        for i in self.selected_results:

            user = i[0]
            folder = i[1].rsplit('\\', 1)[0]

            if user not in self.frame.np.requested_folders:
                self.frame.np.requested_folders[user] = {}

            if folder not in self.frame.np.requested_folders[user]:
                """ Ensure we don't send folder content requests for a folder more than once,
                e.g. when several selected resuls belong to the same folder. """

                self.frame.np.requested_folders[user][folder] = destination
                self.frame.np.send_message_to_peer(user, slskmessages.FolderContentsRequest(None, folder))

    def on_copy_file_path(self, widget):

        if not self.selected_results:
            return

        user, path = next(iter(self.selected_results))[:2]
        self.frame.clip.set_text(path, -1)

    def on_copy_url(self, widget):
        user, path = next(iter(self.selected_results))[:2]
        self.frame.set_clipboard_url(user, path)

    def on_copy_dir_url(self, widget):

        user, path = next(iter(self.selected_results))[:2]
        path = "\\".join(path.split("\\")[:-1])

        if path[:-1] != "/":
            path += "/"

        self.frame.set_clipboard_url(user, path)

    def on_group(self, widget):

        self.on_refilter(widget)

        self.ResultsList.set_show_expanders(widget.get_active())

        self.frame.np.config.sections["searches"]["group_searches"] = widget.get_active()

        if widget.get_active():
            self.cols["id"].set_visible(False)
            self.ExpandButton.show()
        else:
            self.cols["id"].set_visible(True)
            self.ExpandButton.hide()

    def on_toggle_expand_all(self, widget):

        active = self.ExpandButton.get_active()

        if active:
            self.ResultsList.expand_all()
            self.expand.set_from_icon_name("go-up-symbolic", Gtk.IconSize.BUTTON)
        else:
            collapse_treeview(self.ResultsList, self.ResultGrouping.get_active_id())
            self.expand.set_from_icon_name("go-down-symbolic", Gtk.IconSize.BUTTON)

        self.frame.np.config.sections["searches"]["expand_searches"] = active

    def on_toggle_filters(self, widget):

        visible = widget.get_active()
        self.FiltersContainer.set_visible(visible)
        self.frame.np.config.sections["searches"]["filters_visible"] = visible

    def on_clear(self, widget):
        self.all_data = []
        self.usersiters.clear()
        self.directoryiters.clear()
        self.resultsmodel.clear()
        self.numvisibleresults = 0

        # Update number of visible results
        self.update_result_counter()

    def on_close(self, widget):
        self.searches.remove_tab(self)

    def on_copy_search_term(self, widget):
        self.frame.clip.set_text(self.text, -1)

    def on_toggle_remember(self, widget):

        self.remember = widget.get_active()
        search = self.searches.searches[self.id]

        if not self.remember:
            self.searches.wish_list.remove_wish(search["term"])
        else:
            self.searches.wish_list.add_wish(search["term"])

    def push_history(self, widget, title):

        text = widget.get_active_text()
        if not text.strip():
            return None

        text = text.strip()
        history = self.frame.np.config.sections["searches"][title]

        if text in history:
            history.remove(text)
        elif len(history) >= 5:
            del history[-1]

        history.insert(0, text)
        self.frame.np.config.write_configuration()

        self.add_combo(widget, text)
        widget.get_child().set_text(text)

        return text

    def on_refilter(self, widget, *args):

        if self.clearing_filters:
            return

        f_in = self.push_history(self.FilterIn, "filterin")
        f_out = self.push_history(self.FilterOut, "filterout")
        f_size = self.push_history(self.FilterSize, "filtersize")
        f_br = self.push_history(self.FilterBitrate, "filterbr")
        f_free = self.FilterFreeSlot.get_active()
        f_country = self.push_history(self.FilterCountry, "filtercc")
        f_type = self.push_history(self.FilterType, "filtertype")

        self.ResultsList.set_model(None)
        self.set_filters(1, f_in, f_out, f_size, f_br, f_free, f_country, f_type)
        self.ResultsList.set_model(self.resultsmodel)

        if self.ResultGrouping.get_active_id() != "ungrouped":
            # Group by folder or user

            if self.ExpandButton.get_active():
                self.ResultsList.expand_all()
            else:
                collapse_treeview(self.ResultsList, self.ResultGrouping.get_active_id())

    def on_clear_filters(self, widget):

        self.clearing_filters = True

        self.FilterInEntry.set_text("")
        self.FilterOutEntry.set_text("")
        self.FilterSizeEntry.set_text("")
        self.FilterBitrateEntry.set_text("")
        self.FilterCountryEntry.set_text("")
        self.FilterTypeEntry.set_text("")
        self.FilterFreeSlot.set_active(False)

        self.clearing_filters = False
        self.FilterInEntry.grab_focus()
        self.on_refilter(widget)

    def on_about_filters(self, widget):

        if not hasattr(self, "AboutSearchFiltersPopover"):
            load_ui_elements(self, os.path.join(self.frame.gui_dir, "ui", "popovers", "searchfilters.ui"))
            self.AboutSearchFiltersPopover.set_relative_to(self.ShowChatHelp)

        try:
            self.AboutSearchFiltersPopover.popup()

        except AttributeError:
            # GTK <3.22 support
            self.AboutSearchFiltersPopover.set_transitions_enabled(True)
            self.AboutSearchFiltersPopover.show()

    def update_filter_counter(self, count):

        if count > 0:
            self.FilterLabel.set_text(_("Result Filters") + " *")
        else:
            self.FilterLabel.set_text(_("Result Filters"))

        self.FilterLabel.set_tooltip_text("%d active filter(s)" % count)
