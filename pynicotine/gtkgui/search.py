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
import re
import sre_constants

from collections import defaultdict

from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk

from pynicotine.config import config
from pynicotine.gtkgui.fileproperties import FileProperties
from pynicotine.gtkgui.utils import copy_file_url
from pynicotine.gtkgui.utils import copy_text
from pynicotine.gtkgui.utils import setup_accelerator
from pynicotine.gtkgui.widgets.filechooser import choose_dir
from pynicotine.gtkgui.widgets.iconnotebook import IconNotebook
from pynicotine.gtkgui.widgets.popupmenu import PopupMenu
from pynicotine.gtkgui.widgets.textentry import CompletionEntry
from pynicotine.gtkgui.widgets.theme import get_flag_image
from pynicotine.gtkgui.widgets.theme import set_widget_fg_bg_css
from pynicotine.gtkgui.widgets.treeview import collapse_treeview
from pynicotine.gtkgui.widgets.treeview import create_grouping_menu
from pynicotine.gtkgui.widgets.treeview import initialise_columns
from pynicotine.gtkgui.widgets.treeview import save_columns
from pynicotine.gtkgui.widgets.treeview import select_user_row_iter
from pynicotine.gtkgui.widgets.treeview import show_country_tooltip
from pynicotine.gtkgui.widgets.treeview import show_file_path_tooltip
from pynicotine.gtkgui.widgets.theme import update_widget_visuals
from pynicotine.gtkgui.widgets.ui import UserInterface
from pynicotine.gtkgui.wishlist import WishList
from pynicotine.logfacility import log
from pynicotine.utils import get_result_bitrate_length
from pynicotine.utils import humanize
from pynicotine.utils import human_size
from pynicotine.utils import human_speed


class Searches(IconNotebook):

    def __init__(self, frame):

        self.frame = frame
        self.page_id = "search"
        self.pages = {}

        IconNotebook.__init__(
            self,
            self.frame,
            tabclosers=config.sections["ui"]["tabclosers"],
            show_hilite_image=config.sections["notifications"]["notification_tab_icons"],
            notebookraw=self.frame.search_notebook
        )

        if Gtk.get_major_version() == 3:
            # Workaround to make dropdown menu appear below button
            self.frame.SearchMethod.set_wrap_width(1)

        self.wish_list = WishList(frame, self)

        CompletionEntry(frame.RoomSearchEntry, frame.RoomSearchCombo.get_model())
        CompletionEntry(frame.UserSearchEntry, frame.UserSearchCombo.get_model())
        CompletionEntry(frame.SearchEntry, frame.SearchCombo.get_model())

        self.populate_search_history()
        self.update_visuals()

        self.notebook.connect("switch-page", self.on_switch_search_page)

    def on_switch_search_page(self, notebook, page, page_num):

        if self.frame.current_page_id != self.page_id:
            return

        for tab in self.pages.values():
            if tab.Main == page:
                GLib.idle_add(lambda: tab.ResultsList.grab_focus() == -1)
                return True

    def populate_search_history(self):

        self.frame.SearchCombo.remove_all()

        if not config.sections["searches"]["enable_history"]:
            return

        for term in config.sections["searches"]["history"]:
            self.frame.SearchCombo.append_text(str(term))

    def on_search(self):

        self.save_columns()

        text = self.frame.SearchEntry.get_text().strip()

        if not text:
            return

        mode = self.frame.SearchMethod.get_active_id()
        room = self.frame.RoomSearchEntry.get_text()
        user = self.frame.UserSearchEntry.get_text()

        search_response = self.frame.np.search.do_search(text, mode, room=room, user=user)

        if not search_response:
            return

        search_id, searchterm, _searchterm_without_special = search_response
        mode_label = None

        if mode == "rooms":
            mode_label = room.strip()

        elif mode == "user":
            mode_label = user.strip()

        elif mode == "buddies":
            mode_label = _("Buddies")

        tab = self.create_tab(search_id, searchterm, mode, mode_label)
        self.set_current_page(self.page_num(tab.Main))

        # Repopulate the combo list
        self.populate_search_history()

    def clear_search_history(self):

        self.frame.SearchEntry.set_text("")

        config.sections["searches"]["history"] = []
        config.write_configuration()

        self.frame.SearchCombo.remove_all()

    def clear_filter_history(self):

        # Clear filter history in config
        config.sections["searches"]["filterin"] = []
        config.sections["searches"]["filterout"] = []
        config.sections["searches"]["filtertype"] = []
        config.sections["searches"]["filtersize"] = []
        config.sections["searches"]["filterbr"] = []
        config.sections["searches"]["filtercc"] = []
        config.write_configuration()

        # Update filters in search tabs
        for page in self.pages.values():
            page.populate_filters(set_default_filters=False)

    def create_tab(self, search_id, text, mode, mode_label, showtab=True):

        self.pages[search_id] = tab = Search(self, text, search_id, mode, mode_label, showtab)

        if showtab:
            self.show_tab(tab, search_id, text, mode)

        return tab

    def show_tab(self, tab, search_id, text, mode):

        if tab.mode_label is not None:
            full_text = "(%s) %s" % (tab.mode_label, text)
            length = 25
        else:
            full_text = text
            length = 20

        label = full_text[:length]
        self.append_page(tab.Main, label, tab.on_close, full_text=full_text)
        tab.set_label(self.get_tab_label_inner(tab.Main))

        if self.get_n_pages() > 0:
            self.frame.SearchStatusPage.hide()

    def show_search_result(self, msg, username, country):

        tab = self.pages.get(msg.token)

        if tab is None:
            search_term = self.frame.np.search.searches[msg.token]["term"]
            mode = "wishlist"
            mode_label = _("Wish")
            tab = self.create_tab(msg.token, search_term, mode, mode_label, showtab=False)

        counter = len(tab.all_data) + 1

        # No more things to add because we've reached the result limit
        if counter > config.sections["searches"]["max_displayed_results"]:
            self.frame.np.search.remove_allowed_search_id(msg.token)
            return

        tab.add_user_results(msg, username, country)

    def remove_tab(self, tab):

        self.frame.np.search.remove_search(tab.id)
        self.remove_page(tab.Main)

        if self.get_n_pages() == 0:
            self.frame.SearchStatusPage.show()

    def add_wish(self, wish):
        self.wish_list.add_wish(wish)

    def remove_wish(self, wish):
        self.wish_list.remove_wish(wish)

    def set_wishlist_interval(self, msg):
        self.wish_list.set_interval(msg)

    def update_visuals(self):

        for page in self.pages.values():
            page.update_visuals()

        self.wish_list.update_visuals()

    def server_disconnect(self):
        self.wish_list.server_disconnect()

    def save_columns(self):
        """ Save the treeview state of the currently selected tab """

        current_page = self.get_nth_page(self.get_current_page())

        for tab in self.pages.values():
            if tab.Main == current_page:
                tab.save_columns()
                break


class Search(UserInterface):

    def __init__(self, searches, text, id, mode, mode_label, showtab):

        super().__init__("ui/search.ui")

        self.searches = searches
        self.frame = searches.frame

        self.filter_help = UserInterface("ui/popovers/searchfilters.ui")

        if Gtk.get_major_version() == 4:
            self.ResultGrouping.set_icon_name("view-list-symbolic")
        else:
            self.ResultGrouping.set_image(Gtk.Image.new_from_icon_name("view-list-symbolic", Gtk.IconSize.BUTTON))

        setup_accelerator("Escape", self.FiltersContainer, self.on_close_filter_bar_accelerator)
        setup_accelerator("<Primary>f", self.ResultsList, self.on_show_filter_bar_accelerator)
        setup_accelerator("<Alt>Return", self.ResultsList, self.on_file_properties_accelerator)

        self.text = text
        self.searchterm_words_include = []
        self.searchterm_words_ignore = []

        for word in text.lower().split():
            if word.startswith('*'):
                if len(word) > 1:
                    self.searchterm_words_include.append(word[1:])

            elif word.startswith('-'):
                if len(word) > 1:
                    self.searchterm_words_ignore.append(word[1:])

            else:
                self.searchterm_words_include.append(word)

        self.id = id
        self.mode = mode
        self.mode_label = mode_label
        self.showtab = showtab
        self.usersiters = {}
        self.directoryiters = {}
        self.users = set()
        self.all_data = []
        self.filters = None
        self.clearing_filters = False
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

        """ Columns """

        self.resultsmodel = Gtk.TreeStore(
            GObject.TYPE_UINT64,  # (0)  num
            str,                  # (1)  user
            GObject.TYPE_OBJECT,  # (2)  flag
            str,                  # (3)  h_speed
            str,                  # (4)  h_queue
            str,                  # (5)  directory
            str,                  # (6)  filename
            str,                  # (7)  h_size
            str,                  # (8)  h_bitrate
            str,                  # (9)  h_length
            GObject.TYPE_UINT64,  # (10) bitrate
            str,                  # (11) fullpath
            str,                  # (12) country
            GObject.TYPE_UINT64,  # (13) size
            GObject.TYPE_UINT64,  # (14) speed
            GObject.TYPE_UINT64,  # (15) queue
            GObject.TYPE_UINT64,  # (16) length
            str                   # (17) color
        )

        self.column_numbers = list(range(self.resultsmodel.get_n_columns()))
        color_col = 17
        self.cols = cols = initialise_columns(
            "file_search", self.ResultsList,
            ["id", _("ID"), 50, "text", color_col],
            ["user", _("User"), 200, "text", color_col],
            ["country", _("Country"), 25, "pixbuf", None],
            ["speed", _("Speed"), 100, "number", color_col],
            ["in_queue", _("In Queue"), 90, "center", color_col],
            ["folder", _("Folder"), 400, "text", color_col],
            ["filename", _("Filename"), 400, "text", color_col],
            ["size", _("Size"), 100, "number", color_col],
            ["bitrate", _("Bitrate"), 100, "number", color_col],
            ["length", _("Length"), 100, "number", color_col]
        )

        cols["id"].set_sort_column_id(0)
        cols["user"].set_sort_column_id(1)
        cols["country"].set_sort_column_id(12)
        cols["speed"].set_sort_column_id(14)
        cols["in_queue"].set_sort_column_id(15)
        cols["folder"].set_sort_column_id(5)
        cols["filename"].set_sort_column_id(6)
        cols["size"].set_sort_column_id(13)
        cols["bitrate"].set_sort_column_id(10)
        cols["length"].set_sort_column_id(16)

        cols["country"].get_widget().hide()

        self.ResultsList.set_model(self.resultsmodel)

        self.update_visuals()

        """ Popup """

        self.popup_menu_users = PopupMenu(self.frame)

        self.popup_menu = PopupMenu(self.frame, self.ResultsList, self.on_popup_menu)
        self.popup_menu.setup(
            ("#" + "selected_files", None),
            ("", None),
            ("#" + _("_Download File(s)"), self.on_download_files),
            ("#" + _("Download File(s) _To..."), self.on_download_files_to),
            ("#" + _("Download _Folder(s)"), self.on_download_folders),
            ("#" + _("Download F_older(s) To..."), self.on_download_folders_to),
            ("", None),
            ("#" + _("_Browse Folder(s)"), self.on_browse_folder),
            ("#" + _("F_ile Properties"), self.on_file_properties),
            ("", None),
            ("#" + _("Copy _File Path"), self.on_copy_file_path),
            ("#" + _("Copy _URL"), self.on_copy_url),
            ("#" + _("Copy Folder U_RL"), self.on_copy_dir_url),
            ("", None),
            (">" + _("User(s)"), self.popup_menu_users)
        )

        self.tab_menu = PopupMenu(self.frame)
        self.tab_menu.setup(
            ("#" + _("Copy Search Term"), self.on_copy_search_term),
            ("", None),
            ("#" + _("Clear All Results"), self.on_clear),
            ("#" + _("Close All Tabs..."), self.on_close_all_tabs),
            ("#" + _("_Close Tab"), self.on_close)
        )

        """ Grouping """

        menu = create_grouping_menu(self.frame.MainWindow, config.sections["searches"]["group_searches"], self.on_group)
        self.ResultGrouping.set_menu_model(menu)

        self.ExpandButton.set_active(config.sections["searches"]["expand_searches"])

        """ Filters """

        self.ShowFilters.set_active(config.sections["searches"]["filters_visible"])
        self.populate_filters()

        """ Wishlist """

        self.update_wish_button()

    def set_label(self, label):
        self.tab_menu.set_widget(label)

    def on_tooltip(self, widget, x, y, keyboard_mode, tooltip):

        country_tooltip = show_country_tooltip(widget, x, y, tooltip, 12, strip_prefix="")
        file_path_tooltip = show_file_path_tooltip(widget, x, y, tooltip, 11)

        if country_tooltip:
            return country_tooltip

        elif file_path_tooltip:
            return file_path_tooltip

    def populate_filters(self, set_default_filters=True):

        for combobox in (self.FilterIn, self.FilterOut, self.FilterType, self.FilterSize,
                         self.FilterBitrate, self.FilterCountry):
            combobox.remove_all()

        if set_default_filters and config.sections["searches"]["enablefilters"]:

            sfilter = config.sections["searches"]["defilter"]

            self.FilterInEntry.set_text(str(sfilter[0]))
            self.FilterOutEntry.set_text(str(sfilter[1]))
            self.FilterSizeEntry.set_text(str(sfilter[2]))
            self.FilterBitrateEntry.set_text(str(sfilter[3]))
            self.FilterFreeSlot.set_active(sfilter[4])

            if len(sfilter) > 5:
                self.FilterCountryEntry.set_text(str(sfilter[5]))

            if len(sfilter) > 6:
                self.FilterTypeEntry.set_text(str(sfilter[6]))

            self.on_refilter()

        for i in ['0', '128', '160', '192', '256', '320']:
            self.FilterBitrate.append_text(i)

        for i in [">10MiB", "<10MiB", "<5MiB", "<1MiB", ">0"]:
            self.FilterSize.append_text(i)

        for i in ['flac|wav|ape|aiff|wv|cue', 'mp3|m4a|aac|ogg|opus|wma', '!mp3']:
            self.FilterType.append_text(i)

        for i in config.sections["searches"]["filterin"]:
            self.add_combo(self.FilterIn, i, True)

        for i in config.sections["searches"]["filterout"]:
            self.add_combo(self.FilterOut, i, True)

        for i in config.sections["searches"]["filtersize"]:
            self.add_combo(self.FilterSize, i, True)

        for i in config.sections["searches"]["filterbr"]:
            self.add_combo(self.FilterBitrate, i, True)

        for i in config.sections["searches"]["filtercc"]:
            self.add_combo(self.FilterCountry, i, True)

        for i in config.sections["searches"]["filtertype"]:
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

    def add_result_list(self, result_list, counter, user, country, inqueue, ulspeed, h_speed,
                        h_queue, color, private=False):
        """ Adds a list of search results to the treeview. Lists can either contain publicly or
        privately shared files. """

        update_ui = False
        max_results = config.sections["searches"]["max_displayed_results"]

        for result in result_list:
            if counter > max_results:
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

            fullpath_split = fullpath.split('\\')

            if config.sections["ui"]["reverse_file_paths"]:
                # Reverse file path, file name is the first item. next() retrieves the name and removes
                # it from the iterator.
                fullpath_split = reversed(fullpath_split)
                name = next(fullpath_split)

            else:
                # Regular file path, file name is the last item. Retrieve it and remove it from the list.
                name = fullpath_split.pop()

            # Join the resulting items into a folder path
            directory = '\\'.join(fullpath_split)

            size = result[2]
            h_size = human_size(size)
            h_bitrate, bitrate, h_length, length = get_result_bitrate_length(size, result[4])

            if private:
                name = "[PRIVATE FILE]  " + name

            is_result_visible = self.append(
                [
                    GObject.Value(GObject.TYPE_UINT64, counter),
                    user,
                    GObject.Value(GObject.TYPE_OBJECT, get_flag_image(country)),
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

        return update_ui, counter

    def add_user_results(self, msg, user, country):

        if user in self.users:
            return

        self.users.add(user)

        counter = len(self.all_data) + 1

        if msg.freeulslots:
            inqueue = 0
            h_queue = ""
        else:
            inqueue = msg.inqueue or 1  # Ensure value is always >= 1
            h_queue = humanize(inqueue)

        h_speed = ""
        ulspeed = msg.ulspeed

        if ulspeed > 0:
            h_speed = human_speed(ulspeed)

        color_id = (msg.freeulslots and "search" or "searchq")
        color = config.sections["ui"][color_id] or None

        update_ui, counter = self.add_result_list(
            msg.list, counter, user, country, inqueue, ulspeed, h_speed, h_queue, color)

        if msg.privatelist:
            update_ui_private, counter = self.add_result_list(
                msg.privatelist, counter, user, country, inqueue, ulspeed, h_speed, h_queue, color, private=True)

            if not update_ui and update_ui_private:
                update_ui = True

        if update_ui:
            # If this search wasn't initiated by us (e.g. wishlist), and the results aren't spoofed, show tab
            if not self.showtab:
                self.searches.show_tab(self, self.id, self.text, self.mode)
                self.showtab = True

            # Update number of results
            self.update_result_counter()

            # Update tab notification
            self.searches.request_changed(self.Main)
            self.frame.request_tab_hilite(self.searches.page_id)

    def append(self, row):

        self.all_data.append(row)

        if not self.check_filter(row):
            return False

        iterator = self.add_row_to_model(row)

        if self.grouping_mode != "ungrouped":
            # Group by folder or user

            if self.ExpandButton.get_active():
                path = None

                if iterator is not None:
                    path = self.resultsmodel.get_path(iterator)

                if path is not None:
                    self.ResultsList.expand_to_path(path)
            else:
                collapse_treeview(self.ResultsList, self.grouping_mode)

        return True

    def add_row_to_model(self, row):
        (counter, user, flag, h_speed, h_queue, directory, filename, h_size, h_bitrate,
            h_length, bitrate, fullpath, country, size, speed, queue, length, color) = row

        if self.grouping_mode != "ungrouped":
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

            if self.grouping_mode == "folder_grouping":
                # Group by folder

                user_directory = user + directory

                if user_directory not in self.directoryiters:
                    self.directoryiters[user_directory] = self.resultsmodel.insert_with_values(
                        self.usersiters[user], -1, self.column_numbers,
                        [
                            empty_int,
                            user,
                            flag,
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
                row[5] = ""  # Directory not visible for file row if "group by folder" is enabled

                parent = self.directoryiters[user_directory]
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

            log.add("Search row error: %(exception)s %(row)s", {'exception': e, 'row': row})
            iterator = None

        return iterator

    def check_digit(self, sfilter, value, factorize=True):

        op = ">="
        if sfilter.startswith((">", "<", "=")):
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

        # "Included text"-filter, check full file path (located at index 11 in row)
        if filters["include"] and not filters["include"].search(row[11].lower()):
            return False

        # "Excluded text"-filter, check full file path (located at index 11 in row)
        if filters["exclude"] and filters["exclude"].search(row[11].lower()):
            return False

        if filters["size"] and not self.check_digit(filters["size"], row[13].get_uint64()):
            return False

        if filters["bitrate"] and not self.check_digit(filters["bitrate"], row[10].get_uint64(), False):
            return False

        if filters["freeslot"] and row[15].get_uint64() > 0:
            return False

        if filters["country"] and not self.check_country(filters["country"], row[12]):
            return False

        if filters["type"] and not self.check_file_type(filters["type"], row[11]):
            return False

        return True

    def update_filter_counter(self, count):

        if count > 0:
            self.FilterLabel.set_label(_("_Result Filters [%d]") % count)
        else:
            self.FilterLabel.set_label(_("_Result Filters"))

        self.FilterLabel.set_tooltip_text("%d active filter(s)" % count)

    def update_results_model(self):

        self.ResultsList.set_model(None)

        self.usersiters.clear()
        self.directoryiters.clear()
        self.resultsmodel.clear()
        self.numvisibleresults = 0

        for row in self.all_data:
            if self.check_filter(row):
                self.add_row_to_model(row)

        # Update number of visible results
        self.update_result_counter()
        self.update_filter_counter(self.active_filter_count)

        self.ResultsList.set_model(self.resultsmodel)

        if self.grouping_mode != "ungrouped":
            # Group by folder or user

            if self.ExpandButton.get_active():
                self.ResultsList.expand_all()
            else:
                collapse_treeview(self.ResultsList, self.grouping_mode)

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
                set_widget_fg_bg_css(self.FilterInEntry, bg_color="#e04f5e", fg_color="white")
            else:
                update_widget_visuals(self.FilterInEntry)

            self.active_filter_count += 1

        if f_out:
            try:
                f_out = re.compile(f_out.lower())
                self.filters["exclude"] = f_out
            except sre_constants.error:
                set_widget_fg_bg_css(self.FilterOutEntry, bg_color="#e04f5e", fg_color="white")
            else:
                update_widget_visuals(self.FilterOutEntry)

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

        self.update_results_model()

    def update_wish_button(self):

        if self.mode not in ("global", "wishlist"):
            self.AddWish.hide()
            return

        if not self.frame.np.search.is_wish(self.text):
            self.AddWishIcon.set_property("icon-name", "list-add-symbolic")
            self.AddWishLabel.set_label(_("Add Wi_sh"))
            return

        self.AddWishIcon.set_property("icon-name", "list-remove-symbolic")
        self.AddWishLabel.set_label(_("Remove Wi_sh"))

    def on_add_wish(self, *args):

        if self.frame.np.search.is_wish(self.text):
            self.frame.np.search.remove_wish(self.text)
        else:
            self.frame.np.search.add_wish(self.text)

    def add_popup_menu_user(self, popup, user):

        popup.setup_user_menu(user)
        popup.setup(
            ("", None),
            ("#" + _("Select User's Transfers"), self.on_select_user_results, user)
        )

        popup.toggle_user_items()

    def populate_popup_menu_users(self):

        self.popup_menu_users.clear()

        if not self.selected_users:
            return

        # Multiple users, create submenus for each user
        if len(self.selected_users) > 1:
            for user in self.selected_users:
                popup = PopupMenu(self.frame)
                self.add_popup_menu_user(popup, user)
                self.popup_menu_users.setup(
                    (">" + user, popup)
                )
            return

        # Single user, add items directly to "User(s)" submenu
        self.add_popup_menu_user(self.popup_menu_users, self.selected_users[0])

    def on_close_filter_bar_accelerator(self, *args):
        """ Escape: hide filter bar """

        self.ShowFilters.set_active(False)
        return True

    def on_show_filter_bar_accelerator(self, *args):
        """ Ctrl+F: show filter bar """

        self.ShowFilters.set_active(True)
        self.FilterIn.grab_focus()
        return True

    def on_file_properties_accelerator(self, *args):
        """ Alt+Return: show file properties dialog """

        self.on_file_properties()
        return True

    def on_select_user_results(self, *args):

        if not self.selected_users:
            return

        selected_user = args[-1]

        sel = self.ResultsList.get_selection()
        fmodel = self.ResultsList.get_model()
        sel.unselect_all()

        iterator = fmodel.get_iter_first()

        select_user_row_iter(fmodel, sel, 1, selected_user, iterator)

        self.select_results()

    def select_results(self):

        self.selected_results = []
        self.selected_users = []
        self.selected_files_count = 0

        model, paths = self.ResultsList.get_selection().get_selected_rows()

        for path in paths:
            iterator = model.get_iter(path)
            user = model.get_value(iterator, 1)

            if user is None:
                continue

            if user not in self.selected_users:
                self.selected_users.append(user)

            filepath = model.get_value(iterator, 11)

            if not filepath:
                # Result is not a file or directory, don't add it
                continue

            bitrate = model.get_value(iterator, 8)
            length = model.get_value(iterator, 9)
            size = model.get_value(iterator, 13)

            self.selected_results.append((user, filepath, size, bitrate, length))

            filename = model.get_value(iterator, 6)

            if filename:
                self.selected_files_count += 1

    def update_result_counter(self):
        self.Counter.set_text(str(self.numvisibleresults))

    def update_visuals(self):

        for widget in list(self.__dict__.values()):
            update_widget_visuals(widget, list_font_target="searchfont")

    def save_columns(self):
        save_columns("file_search", self.ResultsList.get_columns())

    def on_row_activated(self, treeview, path, column):

        self.select_results()

        if self.selected_files_count:
            self.on_download_files()
        else:
            self.on_download_folders()

        treeview.get_selection().unselect_all()

    def on_popup_menu(self, menu, widget):

        self.select_results()

        actions = menu.get_actions()
        users = len(self.selected_users) > 0
        files = len(self.selected_results) > 0

        for i in (_("_Download File(s)"), _("Download File(s) _To..."), _("F_ile Properties"),
                  _("Copy _URL")):
            actions[i].set_enabled(False)

        for i in (_("Download _Folder(s)"), _("Download F_older(s) To..."), _("_Browse Folder(s)"),
                  _("Copy _File Path"), _("Copy Folder U_RL")):
            actions[i].set_enabled(files)

        actions[_("User(s)")].set_enabled(users)
        self.populate_popup_menu_users()

        if self.selected_files_count:
            # At least one selected result is a file, activate file-related items

            for i in (_("_Download File(s)"), _("Download File(s) _To..."), _("F_ile Properties"),
                      _("Copy _URL")):
                actions[i].set_enabled(True)

        menu.set_num_selected_files(self.selected_files_count)

    def on_browse_folder(self, *args):

        requested_users = set()
        requested_folders = set()

        for file in self.selected_results:
            user = file[0]
            folder = file[1].rsplit('\\', 1)[0]

            if user not in requested_users and folder not in requested_folders:
                self.frame.np.userbrowse.browse_user(user, folder=folder)

                requested_users.add(user)
                requested_folders.add(folder)

    def on_file_properties(self, *args):

        data = []
        model, paths = self.ResultsList.get_selection().get_selected_rows()

        for path in paths:
            iterator = model.get_iter(path)
            filename = model.get_value(iterator, 6)

            # We only want to see the metadata of files, not directories
            if not filename:
                continue

            num = model.get_value(iterator, 0)
            user = model.get_value(iterator, 1)
            speed = model.get_value(iterator, 3)
            queue = model.get_value(iterator, 4)
            size = model.get_value(iterator, 7)
            bitratestr = model.get_value(iterator, 8)
            length = model.get_value(iterator, 9)
            fn = model.get_value(iterator, 11)
            directory, filename = fn.rsplit('\\', 1)
            cc = model.get_value(iterator, 12)
            country = "%s / %s" % (cc, self.frame.np.geoip.country_code_to_name(cc))

            data.append({
                "user": user,
                "fn": fn,
                "position": num,
                "filename": filename,
                "directory": directory,
                "size": size,
                "speed": speed,
                "queue": queue,
                "bitrate": bitratestr,
                "length": length,
                "country": country
            })

        if data:
            FileProperties(self.frame, data).show()

    def on_download_files(self, *args, prefix=""):

        for file in self.selected_results:
            # Make sure the selected result is not a directory
            if not file[1].endswith('\\'):
                self.frame.np.transfers.get_file(
                    file[0], file[1], prefix, size=file[2], bitrate=file[3], length=file[4])

    def on_download_files_to_selected(self, selected, data):
        self.on_download_files(prefix=selected)

    def on_download_files_to(self, *args):

        choose_dir(
            parent=self.frame.MainWindow,
            callback=self.on_download_files_to_selected,
            initialdir=config.sections["transfers"]["downloaddir"],
            multichoice=False
        )

    def on_download_folders(self, *args, download_location=""):

        if download_location:
            """ Custom download location specified, remember it when peer sends a folder
            contents reply """

            requested_folders = self.frame.np.transfers.requested_folders
        else:
            requested_folders = defaultdict(dict)

        for i in self.selected_results:
            user = i[0]
            folder = i[1].rsplit('\\', 1)[0]

            if folder in requested_folders[user]:
                """ Ensure we don't send folder content requests for a folder more than once,
                e.g. when several selected resuls belong to the same folder. """
                continue

            requested_folders[user][folder] = download_location

            visible_files = []
            for row in self.all_data:

                # Find the wanted directory
                if folder != row[11].rsplit('\\', 1)[0]:
                    continue

                destination = self.frame.np.transfers.get_folder_destination(user, folder)
                (counter, user, flag, h_speed, h_queue, directory, filename,
                    h_size, h_bitrate, h_length, bitrate, fullpath, country, size, speed,
                    queue, length, color) = row
                visible_files.append(
                    (user, fullpath, destination, size.get_uint64(), bitrate.get_uint64(), length.get_uint64()))

            self.frame.np.search.request_folder_download(user, folder, visible_files)

    def on_download_folders_to_selected(self, selected, data):
        self.on_download_folders(download_location=selected)

    def on_download_folders_to(self, *args):

        choose_dir(
            parent=self.frame.MainWindow,
            callback=self.on_download_folders_to_selected,
            initialdir=config.sections["transfers"]["downloaddir"],
            multichoice=False
        )

    def on_copy_file_path(self, *args):

        if self.selected_results:
            user, path = self.selected_results[0][:2]
            copy_text(path)

    def on_copy_url(self, *args):

        if self.selected_results:
            user, path = self.selected_results[0][:2]
            copy_file_url(user, path)

    def on_copy_dir_url(self, *args):

        if self.selected_results:
            user, path = self.selected_results[0][:2]
            copy_file_url(user, path.rsplit('\\', 1)[0] + '\\')

    def on_search_settings(self, *args):
        self.frame.on_settings(page='Searches')

    def on_group(self, action, state):

        mode = state.get_string()
        active = mode != "ungrouped"

        config.sections["searches"]["group_searches"] = mode
        self.cols["id"].set_visible(not active)
        self.ResultsList.set_show_expanders(active)
        self.ExpandButton.set_visible(active)

        self.grouping_mode = mode
        self.update_results_model()

        action.set_state(state)

    def on_toggle_expand_all(self, widget):

        active = self.ExpandButton.get_active()

        if active:
            self.ResultsList.expand_all()
            self.expand.set_property("icon-name", "go-up-symbolic")
        else:
            collapse_treeview(self.ResultsList, self.grouping_mode)
            self.expand.set_property("icon-name", "go-down-symbolic")

        config.sections["searches"]["expand_searches"] = active

    def on_toggle_filters(self, widget):

        visible = widget.get_active()
        self.FiltersContainer.set_reveal_child(visible)
        config.sections["searches"]["filters_visible"] = visible

        if visible:
            self.FilterIn.grab_focus()
            return

        self.ResultsList.grab_focus()

    def on_copy_search_term(self, *args):
        copy_text(self.text)

    def push_history(self, widget, title):

        text = widget.get_active_text()
        if not text.strip():
            return None

        text = text.strip()
        history = config.sections["searches"][title]

        if text in history:
            history.remove(text)

        elif len(history) >= 5:
            del history[-1]

        history.insert(0, text)
        config.write_configuration()

        self.add_combo(widget, text)
        return text

    def on_refilter(self, *args):

        if self.clearing_filters:
            return

        f_in = self.push_history(self.FilterIn, "filterin")
        f_out = self.push_history(self.FilterOut, "filterout")
        f_size = self.push_history(self.FilterSize, "filtersize")
        f_br = self.push_history(self.FilterBitrate, "filterbr")
        f_free = self.FilterFreeSlot.get_active()
        f_country = self.push_history(self.FilterCountry, "filtercc")
        f_type = self.push_history(self.FilterType, "filtertype")

        self.set_filters(1, f_in, f_out, f_size, f_br, f_free, f_country, f_type)

    def on_filter_entry_changed(self, widget):
        if not widget.get_text():
            self.on_refilter()

    def on_clear_filters(self, *args):

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
        self.on_refilter()

    def on_clear(self, *args):

        self.all_data = []
        self.usersiters.clear()
        self.directoryiters.clear()
        self.resultsmodel.clear()
        self.numvisibleresults = 0

        # Allow parsing search result messages again
        self.frame.np.search.add_allowed_search_id(self.id)

        # Update number of visible results
        self.update_result_counter()

    def on_close(self, *args):
        self.searches.remove_tab(self)

    def on_close_all_tabs(self, *args):
        self.searches.remove_all_pages()
