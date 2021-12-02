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
from pynicotine.gtkgui.dialogs.fileproperties import FileProperties
from pynicotine.gtkgui.dialogs.wishlist import WishList
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

        IconNotebook.__init__(self, self.frame, self.frame.search_notebook)
        self.notebook.connect("switch-page", self.on_switch_search_page)

        self.modes = {
            "global": _("_Global"),
            "buddies": _("_Buddies"),
            "rooms": _("_Rooms"),
            "user": _("_User")
        }

        mode_menu = PopupMenu(self.frame)
        mode_menu.setup(
            ("O" + self.modes["global"], "win.searchmode", "global"),
            ("O" + self.modes["buddies"], "win.searchmode", "buddies"),
            ("O" + self.modes["rooms"], "win.searchmode", "rooms"),
            ("O" + self.modes["user"], "win.searchmode", "user")
        )
        frame.SearchMode.set_menu_model(mode_menu.model)

        if Gtk.get_major_version() == 4:
            frame.SearchMode.set_use_underline(True)
            frame.SearchMode.set_label(self.modes["global"])
        else:
            frame.SearchModeLabel.set_label(self.modes["global"])
            frame.SearchMode.add(frame.SearchModeLabelBox)

        CompletionEntry(frame.RoomSearchEntry, frame.RoomSearchCombo.get_model())
        CompletionEntry(frame.UserSearchEntry, frame.UserSearchCombo.get_model())
        CompletionEntry(frame.SearchEntry, frame.SearchCombo.get_model())

        self.wish_list = WishList(frame, self)
        self.populate_search_history()
        self.update_visuals()

    def on_switch_search_page(self, _notebook, page, _page_num):

        if self.frame.current_page_id != self.page_id:
            return

        for tab in self.pages.values():
            if tab.Main == page:
                tab.update_filter_comboboxes()
                GLib.idle_add(lambda: tab.ResultsList.grab_focus() == -1)  # pylint:disable=cell-var-from-loop
                break

    def on_search_mode(self, action, state):

        action.set_state(state)
        search_mode = state.get_string()

        if Gtk.get_major_version() == 4:
            self.frame.SearchMode.set_label(self.modes[search_mode])
        else:
            self.frame.SearchModeLabel.set_label(self.modes[search_mode])

        self.frame.UserSearchCombo.set_visible(search_mode == "user")
        self.frame.RoomSearchCombo.set_visible(search_mode == "rooms")

        # Hide popover after click
        self.frame.SearchMode.get_popover().hide()

    def on_search(self):

        text = self.frame.SearchEntry.get_text().strip()

        if not text:
            return

        mode = self.frame.search_mode_action.get_state().get_string()
        room = self.frame.RoomSearchEntry.get_text()
        user = self.frame.UserSearchEntry.get_text()

        self.frame.np.search.do_search(text, mode, room=room, user=user)

    def populate_search_history(self):

        self.frame.SearchCombo.remove_all()

        if not config.sections["searches"]["enable_history"]:
            return

        for term in config.sections["searches"]["history"]:
            self.frame.SearchCombo.append_text(str(term))

    def do_search(self, search_id, search_term, mode, room=None, user=None):

        mode_label = None

        if mode == "rooms":
            mode_label = room.strip()

        elif mode == "user":
            mode_label = user.strip()

        elif mode == "buddies":
            mode_label = _("Buddies")

        tab = self.create_tab(search_id, search_term, mode, mode_label)
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
            page.update_filter_comboboxes()

    def create_tab(self, search_id, text, mode, mode_label, showtab=True):

        self.pages[search_id] = tab = Search(self, text, search_id, mode, mode_label, showtab)

        if showtab:
            self.show_tab(tab, text)

        return tab

    def show_tab(self, tab, text):

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
            self.frame.search_status_page.hide()

    def show_search_result(self, msg, username, country):

        tab = self.pages.get(msg.token)

        if tab is None:
            search_term = self.frame.np.search.searches[msg.token]["term"]
            mode = "wishlist"
            mode_label = _("Wish")
            tab = self.create_tab(msg.token, search_term, mode, mode_label, showtab=False)

        # No more things to add because we've reached the result limit
        if tab.num_results_found >= tab.max_limit:
            self.frame.np.search.remove_allowed_search_id(msg.token)
            tab.max_limited = True
            tab.update_result_counter()
            return

        tab.add_user_results(msg, username, country)

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


class Search(UserInterface):

    def __init__(self, searches, text, search_id, mode, mode_label, showtab):

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

        self.search_id = search_id
        self.mode = mode
        self.mode_label = mode_label
        self.showtab = showtab
        self.usersiters = {}
        self.directoryiters = {}
        self.users = set()
        self.all_data = []
        self.selected_results = []
        self.selected_users = []
        self.selected_files_count = 0
        self.grouping_mode = None
        self.filters = None
        self.clearing_filters = False
        self.active_filter_count = 0
        self.num_results_found = 0
        self.num_results_visible = 0
        self.max_limit = config.sections["searches"]["max_displayed_results"]
        self.max_limited = False

        self.operators = {
            '<': operator.lt,
            '<=': operator.le,
            '==': operator.eq,
            '!=': operator.ne,
            '>=': operator.ge,
            '>': operator.gt
        }

        """ Columns """

        self.treeview_name = "file_search"
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

        self.column_offsets = {}
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

        for column in self.ResultsList.get_columns():
            self.column_offsets[column.get_title()] = 0
            column.connect("notify::x-offset", self.on_column_position_changed)

        self.update_visuals()

        """ Popup """

        self.popup_menu_users = PopupMenu(self.frame)

        self.popup_menu_copy = PopupMenu(self.frame)
        self.popup_menu_copy.setup(
            ("#" + _("Copy _File Path"), self.on_copy_file_path),
            ("#" + _("Copy _URL"), self.on_copy_url),
            ("#" + _("Copy Folder U_RL"), self.on_copy_dir_url)
        )

        self.popup_menu = PopupMenu(self.frame, self.ResultsList, self.on_popup_menu)
        self.popup_menu.setup(
            ("#" + "selected_files", None),
            ("", None),
            ("#" + _("_Download File(s)"), self.on_download_files),
            ("#" + _("Download File(s) _To…"), self.on_download_files_to),
            ("#" + _("Download _Folder(s)"), self.on_download_folders),
            ("#" + _("Download F_older(s) To…"), self.on_download_folders_to),
            ("", None),
            ("#" + _("_Browse Folder(s)"), self.on_browse_folder),
            ("#" + _("F_ile Properties"), self.on_file_properties),
            ("", None),
            (">" + _("Copy"), self.popup_menu_copy),
            (">" + _("User(s)"), self.popup_menu_users)
        )

        self.tab_menu = PopupMenu(self.frame)
        self.tab_menu.setup(
            ("#" + _("Copy Search Term"), self.on_copy_search_term),
            ("", None),
            ("#" + _("Clear All Results"), self.on_clear),
            ("#" + _("Close All Tabs…"), self.on_close_all_tabs),
            ("#" + _("_Close Tab"), self.on_close)
        )

        """ Grouping """

        menu = create_grouping_menu(self.frame.MainWindow, config.sections["searches"]["group_searches"], self.on_group)
        self.ResultGrouping.set_menu_model(menu)

        self.ExpandButton.set_active(config.sections["searches"]["expand_searches"])

        """ Filters """

        self.filter_widgets = {
            "filterin": self.FilterIn,
            "filterout": self.FilterOut,
            "filtersize": self.FilterSize,
            "filterbr": self.FilterBitrate,
            "filterslot": self.FilterFreeSlot,
            "filtercc": self.FilterCountry,
            "filtertype": self.FilterType
        }

        self.ShowFilters.set_active(config.sections["searches"]["filters_visible"])
        self.populate_filters()

        """ Wishlist """

        self.update_wish_button()

    def set_label(self, label):
        self.tab_menu.set_widget(label)

    @staticmethod
    def on_tooltip(widget, pos_x, pos_y, _keyboard_mode, tooltip):

        country_tooltip = show_country_tooltip(widget, pos_x, pos_y, tooltip, 12, strip_prefix="")
        file_path_tooltip = show_file_path_tooltip(widget, pos_x, pos_y, tooltip, 11)

        if country_tooltip:
            return country_tooltip

        if file_path_tooltip:
            return file_path_tooltip

        return False

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

    def update_filter_comboboxes(self):

        for filter_id, widget in self.filter_widgets.items():
            if not isinstance(widget, Gtk.ComboBoxText):
                continue

            presets = ""
            widget.remove_all()

            if filter_id == "filterbr":
                presets = ("0", "128", "160", "192", "256", "320")

            elif filter_id == "filtersize":
                presets = (">10MiB", "<10MiB", "<5MiB", "<1MiB", ">0")

            elif filter_id == "filtertype":
                presets = ("flac|wav|ape|aiff|wv|cue", "mp3|m4a|aac|ogg|opus|wma", "!mp3")

            for value in presets:
                widget.append_text(value)

            for value in config.sections["searches"][filter_id]:
                if value not in presets:
                    widget.append_text(value)

    def populate_filters(self):

        if not config.sections["searches"]["enablefilters"]:
            return

        sfilter = config.sections["searches"]["defilter"]
        num_filters = len(sfilter)

        if num_filters > 0:
            self.FilterIn.get_child().set_text(str(sfilter[0]))

        if num_filters > 1:
            self.FilterOut.get_child().set_text(str(sfilter[1]))

        if num_filters > 2:
            self.FilterSize.get_child().set_text(str(sfilter[2]))

        if num_filters > 3:
            self.FilterBitrate.get_child().set_text(str(sfilter[3]))

        if num_filters > 4:
            self.FilterFreeSlot.set_active(bool(sfilter[4]))

        if num_filters > 5:
            self.FilterCountry.get_child().set_text(str(sfilter[5]))

        if num_filters > 6:
            self.FilterType.get_child().set_text(str(sfilter[6]))

        self.on_refilter()

    def add_result_list(self, result_list, user, country, inqueue, ulspeed, h_speed,
                        h_queue, color, private=False):
        """ Adds a list of search results to the treeview. Lists can either contain publicly or
        privately shared files. """

        update_ui = False

        for result in result_list:
            if self.num_results_found >= self.max_limit:
                self.max_limited = True
                break

            fullpath = result[1]
            fullpath_lower = fullpath.lower()

            if any(word in fullpath_lower for word in self.searchterm_words_ignore):
                # Filter out results with filtered words (e.g. nicotine -music)
                log.add_debug(("Filtered out excluded search result %(filepath)s from user %(user)s for "
                               "search term \"%(query)s\""), {
                    "filepath": fullpath,
                    "user": user,
                    "query": self.text
                })
                continue

            if not any(word in fullpath_lower for word in self.searchterm_words_include):
                # Certain users may send us wrong results, filter out such ones
                log.add_search(_("Filtered out incorrect search result %(filepath)s from user %(user)s for "
                                 "search query \"%(query)s\""), {
                    "filepath": fullpath,
                    "user": user,
                    "query": self.text
                })
                continue

            self.num_results_found += 1
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
                    GObject.Value(GObject.TYPE_UINT64, self.num_results_found),
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

        return update_ui

    def add_user_results(self, msg, user, country):

        if user in self.users:
            return

        self.users.add(user)

        if msg.freeulslots:
            inqueue = 0
            h_queue = ""
        else:
            inqueue = msg.inqueue or 1  # Ensure value is always >= 1
            h_queue = humanize(inqueue)

        h_speed = ""
        ulspeed = msg.ulspeed or 0

        if ulspeed > 0:
            h_speed = human_speed(ulspeed)

        color_id = "search" if msg.freeulslots else "searchq"
        color = config.sections["ui"][color_id] or None

        update_ui = self.add_result_list(msg.list, user, country, inqueue, ulspeed, h_speed, h_queue, color)

        if msg.privatelist:
            update_ui_private = self.add_result_list(
                msg.privatelist, user, country, inqueue, ulspeed, h_speed, h_queue, color, private=True)

            if not update_ui and update_ui_private:
                update_ui = True

        if update_ui:
            # If this search wasn't initiated by us (e.g. wishlist), and the results aren't spoofed, show tab
            if not self.showtab:
                self.searches.show_tab(self, self.text)
                self.showtab = True

            # Update tab notification
            self.searches.request_changed(self.Main)
            self.frame.request_tab_hilite(self.searches.page_id)

        # Update number of results, even if they are all filtered
        self.update_result_counter()

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
        (_counter, user, flag, h_speed, h_queue, directory, _filename, _h_size, _h_bitrate,
            _h_length, _bitrate, fullpath, country, _size, speed, queue, _length, color) = row

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

            self.num_results_visible += 1

        except Exception as error:
            types = []

            for i in row:
                types.append(type(i))

            log.add("Search row error: %(exception)s %(row)s", {'exception': error, 'row': row})
            iterator = None

        return iterator

    def check_digit(self, sfilter, value, factorize=True):

        used_operator = ">="
        if sfilter.startswith((">", "<", "=")):
            used_operator, sfilter = sfilter[:1] + "=", sfilter[1:]

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

        operation = self.operators.get(used_operator)
        return operation(value, sfilter)

    @staticmethod
    def check_country(sfilter, value):

        if not isinstance(value, str):
            return False

        value = value.upper()
        allowed = False

        for country_code in sfilter.split("|"):
            if country_code == value:
                allowed = True

            elif country_code.startswith("!") and country_code[1:] != value:
                allowed = True

            elif country_code.startswith("!") and country_code[1:] == value:
                return False

        return allowed

    @staticmethod
    def check_file_type(sfilter, value):

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

        if self.active_filter_count == 0:
            return True

        filters = self.filters

        # "Included text"-filter, check full file path (located at index 11 in row)
        if filters["filterin"] and not filters["filterin"].search(row[11].lower()):
            return False

        # "Excluded text"-filter, check full file path (located at index 11 in row)
        if filters["filterout"] and filters["filterout"].search(row[11].lower()):
            return False

        if filters["filtersize"] and not self.check_digit(filters["filtersize"], row[13].get_uint64()):
            return False

        if filters["filterbr"] and not self.check_digit(filters["filterbr"], row[10].get_uint64(), False):
            return False

        if filters["filterslot"] and row[15].get_uint64() > 0:
            return False

        if filters["filtercc"] and not self.check_country(filters["filtercc"], row[12]):
            return False

        if filters["filtertype"] and not self.check_file_type(filters["filtertype"], row[11]):
            return False

        return True

    def update_filter_counter(self, count):

        if count > 0:
            self.FilterLabel.set_label(_("_Result Filters [%d]") % count)
        else:
            self.FilterLabel.set_label(_("_Result Filters"))

        self.FilterLabel.set_tooltip_text("%d active filter(s)" % count)

    def update_results_model(self):

        # Temporarily disable sorting for increased performance
        sort_column, sort_type = self.resultsmodel.get_sort_column_id()
        self.resultsmodel.set_default_sort_func(lambda *_args: 0)
        self.resultsmodel.set_sort_column_id(-1, Gtk.SortType.ASCENDING)

        self.usersiters.clear()
        self.directoryiters.clear()
        self.resultsmodel.clear()
        self.num_results_visible = 0

        for row in self.all_data:
            if self.check_filter(row):
                self.add_row_to_model(row)

        # Update number of results
        self.update_result_counter()
        self.update_filter_counter(self.active_filter_count)

        if sort_column is not None and sort_type is not None:
            self.resultsmodel.set_sort_column_id(sort_column, sort_type)

        if self.grouping_mode != "ungrouped":
            # Group by folder or user

            if self.ExpandButton.get_active():
                self.ResultsList.expand_all()
            else:
                collapse_treeview(self.ResultsList, self.grouping_mode)

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

    def on_add_wish(self, *_args):

        if self.frame.np.search.is_wish(self.text):
            self.frame.np.search.remove_wish(self.text)
        else:
            self.frame.np.search.add_wish(self.text)

    def add_popup_menu_user(self, popup, user):

        popup.setup_user_menu(user)
        popup.setup(
            ("", None),
            ("#" + _("Select User's Results"), self.on_select_user_results, user)
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

    def on_close_filter_bar_accelerator(self, *_args):
        """ Escape: hide filter bar """

        self.ShowFilters.set_active(False)
        return True

    def on_show_filter_bar_accelerator(self, *_args):
        """ Ctrl+F: show filter bar """

        self.ShowFilters.set_active(True)
        self.FilterIn.grab_focus()
        return True

    def on_file_properties_accelerator(self, *_args):
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

    def select_result(self, model, iterator):

        user = model.get_value(iterator, 1)

        if user not in self.selected_users:
            self.selected_users.append(user)

        filename = model.get_value(iterator, 6)

        if filename:
            self.selected_files_count += 1
            self.selected_results.append(iterator)

    def select_child_results(self, model, iterator):

        while iterator is not None:
            self.select_result(model, iterator)
            self.select_child_results(model, model.iter_children(iterator))

            iterator = model.iter_next(iterator)

    def select_results(self):

        self.selected_results.clear()
        self.selected_users.clear()
        self.selected_files_count = 0

        model, paths = self.ResultsList.get_selection().get_selected_rows()

        for path in paths:
            iterator = model.get_iter(path)
            self.select_result(model, iterator)
            self.select_child_results(model, model.iter_children(iterator))

    def update_result_counter(self):

        if self.max_limited or self.num_results_found > self.num_results_visible:
            # Append plus symbol "+" if Results are Filtered and/or reached 'Maximum per search'
            str_plus = "+"

            # Display total results on the tooltip, but only if we know the exact number of results
            if self.max_limited:
                total = "> " + str(self.max_limit) + "+"
            else:
                total = self.num_results_found

            self.CounterButton.set_tooltip_text(_("Total: %s") % total)

        else:  # Hide the tooltip if there are no hidden results
            str_plus = ""
            self.CounterButton.set_has_tooltip(False)

        self.Counter.set_text(str(self.num_results_visible) + str_plus)

    def update_visuals(self):

        for widget in list(self.__dict__.values()):
            update_widget_visuals(widget, list_font_target="searchfont")

    def on_column_position_changed(self, column, _param):
        """ Save column position and width to config """

        col_title = column.get_title()
        offset = column.get_x_offset()

        if self.column_offsets[col_title] == offset:
            return

        self.column_offsets[col_title] = offset
        save_columns(self.treeview_name, self.ResultsList.get_columns())

    def on_row_activated(self, treeview, _path, _column):

        self.select_results()

        self.on_download_files()
        treeview.get_selection().unselect_all()

    def on_popup_menu(self, menu, _widget):

        self.select_results()
        self.populate_popup_menu_users()
        menu.set_num_selected_files(self.selected_files_count)

    def on_browse_folder(self, *_args):

        requested_users = set()
        requested_folders = set()

        for iterator in self.selected_results:
            user = self.resultsmodel.get_value(iterator, 1)
            folder = self.resultsmodel.get_value(iterator, 11).rsplit('\\', 1)[0]

            if user not in requested_users and folder not in requested_folders:
                self.frame.np.userbrowse.browse_user(user, folder=folder)

                requested_users.add(user)
                requested_folders.add(folder)

    def on_file_properties(self, *_args):

        data = []

        for iterator in self.selected_results:
            num = self.resultsmodel.get_value(iterator, 0)
            user = self.resultsmodel.get_value(iterator, 1)
            speed = self.resultsmodel.get_value(iterator, 3)
            queue = self.resultsmodel.get_value(iterator, 4)
            filename = self.resultsmodel.get_value(iterator, 6)
            size = self.resultsmodel.get_value(iterator, 7)
            bitratestr = self.resultsmodel.get_value(iterator, 8)
            length = self.resultsmodel.get_value(iterator, 9)
            virtual_path = self.resultsmodel.get_value(iterator, 11)
            directory, filename = virtual_path.rsplit('\\', 1)
            country_code = self.resultsmodel.get_value(iterator, 12)
            country = "%s / %s" % (country_code, self.frame.np.geoip.country_code_to_name(country_code))

            data.append({
                "user": user,
                "fn": virtual_path,
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

    def on_download_files(self, *_args, prefix=""):

        for iterator in self.selected_results:
            user = self.resultsmodel.get_value(iterator, 1)
            filepath = self.resultsmodel.get_value(iterator, 11)
            size = self.resultsmodel.get_value(iterator, 13)
            bitrate = self.resultsmodel.get_value(iterator, 8)
            length = self.resultsmodel.get_value(iterator, 9)

            self.frame.np.transfers.get_file(
                user, filepath, prefix, size=size, bitrate=bitrate, length=length)

    def on_download_files_to_selected(self, selected, _data):
        self.on_download_files(prefix=selected)

    def on_download_files_to(self, *_args):

        choose_dir(
            parent=self.frame.MainWindow,
            title=_("Select Destination Folder for File(s)"),
            callback=self.on_download_files_to_selected,
            initialdir=config.sections["transfers"]["downloaddir"],
            multichoice=False
        )

    def on_download_folders(self, *_args, download_location=""):

        if download_location:
            """ Custom download location specified, remember it when peer sends a folder
            contents reply """

            requested_folders = self.frame.np.transfers.requested_folders
        else:
            requested_folders = defaultdict(dict)

        for iterator in self.selected_results:
            user = self.resultsmodel.get_value(iterator, 1)
            folder = self.resultsmodel.get_value(iterator, 11).rsplit('\\', 1)[0]

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
                (_counter, user, _flag, _h_speed, _h_queue, _directory, _filename,
                    _h_size, _h_bitrate, _h_length, bitrate, fullpath, _country, size, _speed,
                    _queue, length, _color) = row
                visible_files.append(
                    (user, fullpath, destination, size.get_uint64(), bitrate.get_uint64(), length.get_uint64()))

            self.frame.np.search.request_folder_download(user, folder, visible_files)

    def on_download_folders_to_selected(self, selected, _data):
        self.on_download_folders(download_location=selected)

    def on_download_folders_to(self, *_args):

        choose_dir(
            parent=self.frame.MainWindow,
            title=_("Select Destination Folder"),
            callback=self.on_download_folders_to_selected,
            initialdir=config.sections["transfers"]["downloaddir"],
            multichoice=False
        )

    def on_copy_file_path(self, *_args):

        for iterator in self.selected_results:
            filepath = self.resultsmodel.get_value(iterator, 11)
            copy_text(filepath)
            return

    def on_copy_url(self, *_args):

        for iterator in self.selected_results:
            user = self.resultsmodel.get_value(iterator, 1)
            filepath = self.resultsmodel.get_value(iterator, 11)
            copy_file_url(user, filepath)
            return

    def on_copy_dir_url(self, *_args):

        for iterator in self.selected_results:
            user = self.resultsmodel.get_value(iterator, 1)
            filepath = self.resultsmodel.get_value(iterator, 11)
            copy_file_url(user, filepath.rsplit('\\', 1)[0] + '\\')
            return

    def on_counter_button(self, *_args):

        if self.num_results_found > self.num_results_visible:
            self.on_clear_filters()
        else:
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

    def on_toggle_expand_all(self, *_args):

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

    def on_copy_search_term(self, *_args):
        copy_text(self.text)

    @staticmethod
    def push_history(filter_id, value):

        if not value:
            return

        history = config.sections["searches"].get(filter_id)

        if history is None:
            return

        if value in history:
            history.remove(value)

        elif len(history) >= 5:
            del history[-1]

        history.insert(0, value)
        config.write_configuration()

    def on_refilter(self, *_args):

        if self.clearing_filters:
            return

        filter_in = self.FilterIn.get_active_text().strip().lower()
        filter_out = self.FilterOut.get_active_text().strip().lower()

        if filter_in:
            try:
                filter_in = re.compile(filter_in)
            except sre_constants.error:
                filter_in = None

        if filter_out:
            try:
                filter_out = re.compile(filter_out)
            except sre_constants.error:
                filter_out = None

        filters = {
            "filterin": filter_in,
            "filterout": filter_out,
            "filtersize": self.FilterSize.get_active_text().strip(),
            "filterbr": self.FilterBitrate.get_active_text().strip(),
            "filterslot": self.FilterFreeSlot.get_active(),
            "filtercc": self.FilterCountry.get_active_text().strip().upper(),
            "filtertype": self.FilterType.get_active_text().strip().lower()
        }

        if self.filters == filters:
            # Filters have not changed, no need to refilter
            return

        self.active_filter_count = 0

        # Set red background if invalid regex pattern is detected
        if filter_in is None:
            set_widget_fg_bg_css(self.FilterIn.get_child(), bg_color="#e04f5e", fg_color="white")
        else:
            update_widget_visuals(self.FilterIn.get_child())

        if filter_out is None:
            set_widget_fg_bg_css(self.FilterOut.get_child(), bg_color="#e04f5e", fg_color="white")
        else:
            update_widget_visuals(self.FilterOut.get_child())

        # Add filters to history
        for filter_id, value in filters.items():
            try:
                value = value.pattern
            except AttributeError:
                pass

            if not value:
                continue

            self.push_history(filter_id, value)
            self.active_filter_count += 1

        # Apply the new filters
        self.filters = filters
        self.update_filter_comboboxes()
        self.update_results_model()

    def on_filter_entry_changed(self, widget):
        if not widget.get_text():
            self.on_refilter()

    def on_clear_filters(self, *_args):

        self.clearing_filters = True

        for widget in self.filter_widgets.values():
            if isinstance(widget, Gtk.ComboBoxText):
                widget.get_child().set_text("")

        self.FilterFreeSlot.set_active(False)

        self.clearing_filters = False
        self.FilterIn.get_child().grab_focus()
        self.on_refilter()

    def on_clear(self, *_args):

        self.all_data = []
        self.usersiters.clear()
        self.directoryiters.clear()
        self.resultsmodel.clear()
        self.num_results_found = 0
        self.num_results_visible = 0
        self.max_limited = False
        self.max_limit = config.sections["searches"]["max_displayed_results"]

        # Allow parsing search result messages again
        self.frame.np.search.add_allowed_search_id(self.search_id)

        # Update number of results widget
        self.update_result_counter()

    def on_close(self, *_args):

        del self.searches.pages[self.search_id]
        self.frame.np.search.remove_search(self.search_id)
        self.searches.remove_page(self.Main)

        if self.searches.get_n_pages() == 0:
            self.frame.search_status_page.show()

    def on_close_all_tabs(self, *_args):
        self.searches.remove_all_pages()
