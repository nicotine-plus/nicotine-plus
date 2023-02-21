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

import operator
import re

from collections import defaultdict

from gi.repository import GObject
from gi.repository import Gtk

from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.dialogs.fileproperties import FileProperties
from pynicotine.gtkgui.utils import copy_text
from pynicotine.gtkgui.widgets.accelerator import Accelerator
from pynicotine.gtkgui.widgets.filechooser import FolderChooser
from pynicotine.gtkgui.widgets.iconnotebook import IconNotebook
from pynicotine.gtkgui.widgets.popupmenu import PopupMenu
from pynicotine.gtkgui.widgets.popupmenu import FilePopupMenu
from pynicotine.gtkgui.widgets.popupmenu import UserPopupMenu
from pynicotine.gtkgui.widgets.textentry import CompletionEntry
from pynicotine.gtkgui.widgets.theme import add_css_class
from pynicotine.gtkgui.widgets.theme import get_file_type_icon_name
from pynicotine.gtkgui.widgets.theme import get_flag_icon_name
from pynicotine.gtkgui.widgets.theme import remove_css_class
from pynicotine.gtkgui.widgets.treeview import collapse_treeview
from pynicotine.gtkgui.widgets.treeview import create_grouping_menu
from pynicotine.gtkgui.widgets.treeview import initialise_columns
from pynicotine.gtkgui.widgets.treeview import save_columns
from pynicotine.gtkgui.widgets.treeview import select_user_row_iter
from pynicotine.gtkgui.widgets.treeview import show_country_tooltip
from pynicotine.gtkgui.widgets.treeview import show_file_path_tooltip
from pynicotine.gtkgui.widgets.treeview import show_file_type_tooltip
from pynicotine.gtkgui.widgets.ui import UserInterface
from pynicotine.logfacility import log
from pynicotine.shares import FileTypes
from pynicotine.slskmessages import SEARCH_TOKENS_ALLOWED
from pynicotine.slskmessages import FileListMessage
from pynicotine.utils import factorize
from pynicotine.utils import humanize
from pynicotine.utils import human_size
from pynicotine.utils import human_speed


class Searches(IconNotebook):

    def __init__(self, window):

        super().__init__(
            window,
            parent=window.search_content,
            parent_page=window.search_page,
            switch_page_callback=self.on_switch_search_page
        )

        self.modes = {
            "global": _("_Global"),
            "buddies": _("_Buddies"),
            "rooms": _("_Rooms"),
            "user": _("_User")
        }

        mode_menu = PopupMenu(window.application)
        mode_menu.add_items(
            ("O" + self.modes["global"], "win.search-mode", "global"),
            ("O" + self.modes["buddies"], "win.search-mode", "buddies"),
            ("O" + self.modes["rooms"], "win.search-mode", "rooms"),
            ("O" + self.modes["user"], "win.search-mode", "user")
        )
        mode_menu.update_model()
        window.search_mode_button.set_menu_model(mode_menu.model)
        window.search_mode_label.set_label(self.modes["global"])

        if GTK_API_VERSION >= 4:
            add_css_class(window.search_mode_button.get_first_child(), "arrow-button")

        CompletionEntry(window.room_search_entry, window.room_search_combobox.get_model())
        CompletionEntry(window.search_entry, window.search_combobox.get_model())

        self.file_properties = None

        for event_name, callback in (
            ("add-wish", self.update_wish_button),
            ("do-search", self.do_search),
            ("file-search-response", self.file_search_response),
            ("remove-search", self.remove_search),
            ("remove-wish", self.update_wish_button),
            ("show-search", self.show_search)
        ):
            events.connect(event_name, callback)

        self.populate_search_history()

    def on_switch_search_page(self, _notebook, page, _page_num):

        if self.window.current_page_id != self.window.search_page.id:
            return

        for tab in self.pages.values():
            if tab.container != page:
                continue

            tab.update_filter_comboboxes()
            break

    def on_search_mode(self, action, state):

        action.set_state(state)
        search_mode = state.get_string()

        self.window.search_mode_label.set_label(self.modes[search_mode])

        self.window.user_search_combobox.set_visible(search_mode == "user")
        self.window.room_search_combobox.set_visible(search_mode == "rooms")

        # Hide popover after click
        self.window.search_mode_button.get_popover().set_visible(False)

    def on_search(self):

        text = self.window.search_entry.get_text().strip()

        if not text:
            return

        mode = self.window.lookup_action("search-mode").get_state().get_string()
        room = self.window.room_search_entry.get_text()
        user = self.window.user_search_entry.get_text()

        self.window.search_entry.set_text("")
        core.search.do_search(text, mode, room=room, user=user)

    def populate_search_history(self):

        should_enable_history = config.sections["searches"]["enable_history"]

        self.window.search_combobox.remove_all()
        self.window.search_combobox_button.set_visible(should_enable_history)

        if not should_enable_history:
            return

        for term in config.sections["searches"]["history"]:
            self.window.search_combobox.append_text(str(term))

    def create_page(self, token, text, mode=None, mode_label=None, show_page=True):

        page = self.pages.get(token)

        if page is None:
            self.pages[token] = page = Search(self, text, token, mode, mode_label, show_page)
        else:
            mode_label = page.mode_label

        if not show_page:
            return page

        if mode_label is not None:
            full_text = f"({mode_label}) {text}"
            length = 25
        else:
            full_text = text
            length = 20

        label = full_text[:length]
        self.append_page(page.container, label, focus_callback=page.on_focus,
                         close_callback=page.on_close, full_text=full_text)
        page.set_label(self.get_tab_label_inner(page.container))

        return page

    def do_search(self, token, search_term, mode, room=None, users=None, switch_page=True):

        mode_label = None

        if mode == "rooms":
            mode_label = room.strip()

        elif mode == "user":
            mode_label = ",".join(users)

        elif mode == "buddies":
            mode_label = _("Buddies")

        self.create_page(token, search_term, mode, mode_label)

        if switch_page:
            self.show_search(token)

        # Repopulate the combo list
        self.populate_search_history()

    def show_search(self, token):

        page = self.pages.get(token)

        if page is None:
            return

        self.set_current_page(page.container)
        self.window.change_main_page(self.window.search_page)

    def remove_search(self, token):

        page = self.pages.get(token)

        if page is None:
            return

        page.clear()
        self.remove_page(page.container)
        del self.pages[token]

    def clear_search_history(self):

        self.window.search_entry.set_text("")

        config.sections["searches"]["history"] = []
        config.write_configuration()

        self.window.search_combobox.remove_all()

    def clear_filter_history(self):

        # Clear filter history in config
        for filter_id in ("filterin", "filterout", "filtertype", "filtersize", "filterbr", "filterlength", "filtercc"):
            config.sections["searches"][filter_id] = []

        config.write_configuration()

        # Update filters in search tabs
        for page in self.pages.values():
            page.update_filter_comboboxes()

    def file_search_response(self, msg):

        if msg.token not in SEARCH_TOKENS_ALLOWED:
            return

        page = self.pages.get(msg.token)

        if page is None:
            search_item = core.search.searches.get(msg.token)

            if search_item is None:
                return

            search_term = search_item["term"]
            mode = "wishlist"
            mode_label = _("Wish")
            page = self.create_page(msg.token, search_term, mode, mode_label, show_page=False)

        # No more things to add because we've reached the result limit
        if page.num_results_found >= page.max_limit:
            core.search.remove_allowed_token(msg.token)
            page.max_limited = True
            page.update_result_counter()
            return

        page.file_search_response(msg)

    def update_wish_button(self, wish):

        for page in self.pages.values():
            if page.text == wish:
                page.update_wish_button()


class Search:

    FILTER_GENERIC_FILE_TYPES = (
        ("audio", FileTypes.AUDIO),
        ("executable", FileTypes.EXECUTABLE),
        ("image", FileTypes.IMAGE),
        ("video", FileTypes.VIDEO),
        ("text", FileTypes.DOCUMENT_TEXT),
        ("archive", FileTypes.ARCHIVE)
    )
    FILTER_PRESETS = {
        "filterbr": ("!0", "128 <=192", ">192 <320", "=320", ">320"),
        "filtersize": (">50MiB", ">20MiB <=50MiB", ">10MiB <=20MiB", ">5MiB <=10MiB", "<=5MiB"),
        "filtertype": ("audio", "image", "video", "text", "archive", "!executable", "audio image text"),
        "filterlength": (">15:00", ">8:00 <=15:00", ">5:00 <=8:00", ">2:00 <=5:00", "<=2:00")
    }
    FILTER_SPLIT_DIGIT_PATTERN = re.compile(r"(?:[|&\s])+(?<![<>!=]\s)")  # [pipe, ampersand, space]
    FILTER_SPLIT_TEXT_PATTERN = re.compile(r"(?:[|&,;\s])+(?<![!]\s)")    # [pipe, ampersand, comma, semicolon, space]

    def __init__(self, searches, text, token, mode, mode_label, show_page):

        ui_template = UserInterface(scope=self, path="search.ui")
        (
            self.add_wish_button,
            self.add_wish_icon,
            self.add_wish_label,
            self.container,
            self.expand_button,
            self.expand_icon,
            self.filter_bitrate_combobox,
            self.filter_country_combobox,
            self.filter_exclude_combobox,
            self.filter_file_size_combobox,
            self.filter_file_type_combobox,
            self.filter_free_slot_button,
            self.filter_include_combobox,
            self.filter_length_combobox,
            self.filters_button,
            self.filters_container,
            self.filters_label,
            self.grouping_button,
            self.results_button,
            self.results_label,
            self.tree_view
        ) = ui_template.widgets

        self.searches = searches
        self.window = searches.window

        self.text = text
        self.searchterm_words_include = []
        self.searchterm_words_ignore = []

        for word in text.lower().split():
            if word.startswith("*"):
                if len(word) > 1:
                    self.searchterm_words_include.append(word[1:])

            elif word.startswith("-"):
                if len(word) > 1:
                    self.searchterm_words_ignore.append(word[1:])

            else:
                self.searchterm_words_include.append(word)

        self.token = token
        self.mode = mode
        self.mode_label = mode_label
        self.show_page = show_page
        self.usersiters = {}
        self.directoryiters = {}
        self.users = set()
        self.all_data = []
        self.grouping_mode = None
        self.filters = None
        self.clearing_filters = False
        self.active_filter_count = 0
        self.num_results_found = 0
        self.num_results_visible = 0
        self.max_limit = config.sections["searches"]["max_displayed_results"]
        self.max_limited = False

        # Use dict instead of list for faster membership checks
        self.selected_users = {}
        self.selected_results = {}

        # Columns
        self.treeview_name = "file_search"
        self.create_model()

        self.column_offsets = {}
        self.column_numbers = list(range(self.resultsmodel.get_n_columns()))
        has_free_slots_col = 18
        self.cols = cols = initialise_columns(
            self.window, "file_search", self.tree_view,
            ["id", _("ID"), 50, "number", has_free_slots_col],
            ["user", _("User"), 200, "text", has_free_slots_col],
            ["country", _("Country"), 30, "icon", None],
            ["speed", _("Speed"), 120, "number", has_free_slots_col],
            ["in_queue", _("In Queue"), 110, "number", has_free_slots_col],
            ["folder", _("Folder"), 400, "text", has_free_slots_col],
            ["file_type", _("File Type"), 40, "icon", has_free_slots_col],
            ["filename", _("Filename"), 400, "text", has_free_slots_col],
            ["size", _("Size"), 100, "number", has_free_slots_col],
            ["bitrate", _("Bitrate"), 100, "number", has_free_slots_col],
            ["length", _("Duration"), 100, "number", has_free_slots_col]
        )

        cols["id"].set_sort_column_id(0)
        cols["user"].set_sort_column_id(1)
        cols["country"].set_sort_column_id(13)
        cols["speed"].set_sort_column_id(15)
        cols["in_queue"].set_sort_column_id(16)
        cols["folder"].set_sort_column_id(5)
        cols["file_type"].set_sort_column_id(6)
        cols["filename"].set_sort_column_id(7)
        cols["size"].set_sort_column_id(14)
        cols["bitrate"].set_sort_column_id(11)
        cols["length"].set_sort_column_id(17)

        cols["country"].get_widget().set_visible(False)
        cols["file_type"].get_widget().set_visible(False)

        for column in self.tree_view.get_columns():
            self.column_offsets[column.get_title()] = 0
            column.connect("notify::x-offset", self.on_column_position_changed)

        if GTK_API_VERSION >= 4:
            focus_controller = Gtk.EventControllerFocus()
            focus_controller.connect("enter", self.on_refilter)
            self.tree_view.add_controller(focus_controller)
        else:
            self.tree_view.connect("focus-in-event", self.on_refilter)

        # Popup menus
        self.popup_menu_users = UserPopupMenu(self.window.application)

        self.popup_menu_copy = PopupMenu(self.window.application)
        self.popup_menu_copy.add_items(
            ("#" + _("Copy _File Path"), self.on_copy_file_path),
            ("#" + _("Copy _URL"), self.on_copy_url),
            ("#" + _("Copy Folder U_RL"), self.on_copy_dir_url)
        )

        self.popup_menu = FilePopupMenu(self.window.application, self.tree_view, self.on_popup_menu)
        self.popup_menu.add_items(
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
            (">" + _("User Actions"), self.popup_menu_users)
        )

        self.tab_menu = PopupMenu(self.window.application)
        self.tab_menu.add_items(
            ("#" + _("Copy Search Term"), self.on_copy_search_term),
            ("", None),
            ("#" + _("Clear All Results"), self.on_clear),
            ("#" + _("Close All Tabs…"), self.on_close_all_tabs),
            ("#" + _("_Close Tab"), self.on_close)
        )

        # Key bindings
        for widget in (self.container, self.tree_view):
            Accelerator("<Primary>f", widget, self.on_show_filter_bar_accelerator)

        Accelerator("Escape", self.filters_container, self.on_close_filter_bar_accelerator)
        Accelerator("<Alt>Return", self.tree_view, self.on_file_properties_accelerator)

        # Grouping
        menu = create_grouping_menu(self.window, config.sections["searches"]["group_searches"], self.on_group)
        self.grouping_button.set_menu_model(menu)

        self.expand_button.set_active(config.sections["searches"]["expand_searches"])

        # Filters
        self.filter_comboboxes = {
            "filterin": self.filter_include_combobox,
            "filterout": self.filter_exclude_combobox,
            "filtersize": self.filter_file_size_combobox,
            "filterbr": self.filter_bitrate_combobox,
            "filtercc": self.filter_country_combobox,
            "filtertype": self.filter_file_type_combobox,
            "filterlength": self.filter_length_combobox
        }

        self.filters_button.set_active(config.sections["searches"]["filters_visible"])
        self.populate_filters()

        # Wishlist
        self.update_wish_button()

    def create_model(self):
        """ Create a tree model based on the grouping mode. Scrolling performance of Gtk.TreeStore
        is bad with large plain lists, so use Gtk.ListStore in ungrouped mode where no tree structure
        is necessary. """

        tree_model_class = Gtk.ListStore if self.grouping_mode == "ungrouped" else Gtk.TreeStore
        self.resultsmodel = tree_model_class(
            int,                  # (0)  num
            str,                  # (1)  user
            str,                  # (2)  flag
            str,                  # (3)  h_speed
            str,                  # (4)  h_queue
            str,                  # (5)  directory
            str,                  # (6)  file type icon
            str,                  # (7)  filename
            str,                  # (8)  h_size
            str,                  # (9)  h_bitrate
            str,                  # (10) h_length
            GObject.TYPE_UINT,    # (11) bitrate
            str,                  # (12) fullpath
            str,                  # (13) country
            GObject.TYPE_UINT64,  # (14) size
            GObject.TYPE_UINT,    # (15) speed
            GObject.TYPE_UINT,    # (16) queue
            GObject.TYPE_UINT,    # (17) length
            bool                  # (18) free slots
        )

        if self.grouping_mode is not None:
            self.tree_view.set_model(self.resultsmodel)

    def clear(self):

        self.clear_model(stored_results=True)

        for menu in (self.popup_menu_users, self.popup_menu_copy, self.popup_menu, self.tab_menu,
                     self.tree_view.column_menu):
            menu.clear()

    def set_label(self, label):
        self.tab_menu.set_parent(label)

    @staticmethod
    def on_tooltip(widget, pos_x, pos_y, _keyboard_mode, tooltip):

        country_tooltip = show_country_tooltip(widget, pos_x, pos_y, tooltip, 13)

        if country_tooltip:
            return country_tooltip

        file_path_tooltip = show_file_path_tooltip(widget, pos_x, pos_y, tooltip, 12)

        if file_path_tooltip:
            return file_path_tooltip

        return show_file_type_tooltip(widget, pos_x, pos_y, tooltip, 6)

    def on_combobox_popup_shown(self, combobox, _param):
        entry = combobox.get_child()
        entry.emit("activate")

    def on_combobox_check_separator(self, model, iterator):
        # Render empty value as separator
        return not model.get_value(iterator, 0)

    def update_filter_comboboxes(self):

        for filter_id, widget in self.filter_comboboxes.items():
            widget.set_row_separator_func(lambda *_args: 0)
            widget.remove_all()

            presets = self.FILTER_PRESETS.get(filter_id)

            if presets:
                for value in presets:
                    widget.append_text(value)

                widget.append_text("")  # Separator

            for value in config.sections["searches"][filter_id]:
                widget.append_text(value)

            if presets:
                widget.set_row_separator_func(self.on_combobox_check_separator)

    def populate_filters(self):

        if not config.sections["searches"]["enablefilters"]:
            return

        sfilter = config.sections["searches"]["defilter"]
        num_filters = len(sfilter)

        if num_filters > 0:
            self.filter_include_combobox.get_child().set_text(str(sfilter[0]))

        if num_filters > 1:
            self.filter_exclude_combobox.get_child().set_text(str(sfilter[1]))

        if num_filters > 2:
            self.filter_file_size_combobox.get_child().set_text(str(sfilter[2]))

        if num_filters > 3:
            self.filter_bitrate_combobox.get_child().set_text(str(sfilter[3]))

        if num_filters > 4:
            self.filter_free_slot_button.set_active(bool(sfilter[4]))

        if num_filters > 5:
            self.filter_country_combobox.get_child().set_text(str(sfilter[5]))

        if num_filters > 6:
            self.filter_file_type_combobox.get_child().set_text(str(sfilter[6]))

        if num_filters > 7:
            self.filter_length_combobox.get_child().set_text(str(sfilter[7]))

        self.on_refilter()

    def add_result_list(self, result_list, user, country_code, inqueue, ulspeed, h_speed,
                        h_queue, has_free_slots, private=False):
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
                               'search term "%(query)s"'), {
                    "filepath": fullpath,
                    "user": user,
                    "query": self.text
                })
                continue

            if not any(word in fullpath_lower for word in self.searchterm_words_include):
                # Certain users may send us wrong results, filter out such ones
                log.add_search(_("Filtered out incorrect search result %(filepath)s from user %(user)s for "
                                 'search query "%(query)s"'), {
                    "filepath": fullpath,
                    "user": user,
                    "query": self.text
                })
                continue

            self.num_results_found += 1
            fullpath_split = fullpath.split("\\")

            if config.sections["ui"]["reverse_file_paths"]:
                # Reverse file path, file name is the first item. next() retrieves the name and removes
                # it from the iterator.
                fullpath_split = reversed(fullpath_split)
                name = next(fullpath_split)

            else:
                # Regular file path, file name is the last item. Retrieve it and remove it from the list.
                name = fullpath_split.pop()

            # Join the resulting items into a folder path
            directory = "\\".join(fullpath_split)

            size = result[2]
            h_size = humanize(size) if config.sections["ui"]["exact_file_sizes"] else human_size(size)
            h_bitrate, bitrate, h_length, length = FileListMessage.parse_result_bitrate_length(size, result[4])

            if private:
                name = _("[PRIVATE]  %s") % name

            is_result_visible = self.append(
                [
                    self.num_results_found,
                    user,
                    get_flag_icon_name(country_code),
                    h_speed,
                    h_queue,
                    directory,
                    get_file_type_icon_name(name),
                    name,
                    h_size,
                    h_bitrate,
                    h_length,
                    GObject.Value(GObject.TYPE_UINT, bitrate),
                    fullpath,
                    country_code,
                    GObject.Value(GObject.TYPE_UINT64, size),
                    GObject.Value(GObject.TYPE_UINT, ulspeed),
                    GObject.Value(GObject.TYPE_UINT, inqueue),
                    GObject.Value(GObject.TYPE_UINT, length),
                    has_free_slots
                ]
            )

            if is_result_visible:
                update_ui = True

        return update_ui

    def file_search_response(self, msg):

        user = msg.init.target_user

        if user in self.users:
            return

        self.users.add(user)
        ip_address = msg.init.addr[0]
        country_code = core.geoip.get_country_code(ip_address)
        has_free_slots = msg.freeulslots

        if has_free_slots:
            inqueue = 0
            h_queue = ""
        else:
            inqueue = msg.inqueue or 1  # Ensure value is always >= 1
            h_queue = humanize(inqueue)

        h_speed = ""
        ulspeed = msg.ulspeed or 0

        if ulspeed > 0:
            h_speed = human_speed(ulspeed)

        update_ui = self.add_result_list(msg.list, user, country_code, inqueue, ulspeed, h_speed,
                                         h_queue, has_free_slots)

        if msg.privatelist:
            update_ui_private = self.add_result_list(
                msg.privatelist, user, country_code, inqueue, ulspeed, h_speed, h_queue,
                has_free_slots, private=True
            )

            if not update_ui and update_ui_private:
                update_ui = True

        if update_ui:
            # If this search wasn't initiated by us (e.g. wishlist), and the results aren't spoofed, show tab
            if not self.show_page:
                self.searches.create_page(self.token, self.text)
                self.show_page = True

                if self.mode == "wishlist" and config.sections["notifications"]["notification_popup_wish"]:
                    core.notifications.show_search_notification(
                        str(self.token), self.text,
                        title=_("Wishlist Results Found")
                    )

            self.searches.request_tab_changed(self.container)

        # Update number of results, even if they are all filtered
        self.update_result_counter()

    def append(self, row):

        self.all_data.append(row)

        if not self.check_filter(row):
            return False

        self.add_row_to_model(row)
        return True

    def add_row_to_model(self, row):
        (_counter, user, flag, h_speed, h_queue, directory, _file_type, _filename, _h_size, _h_bitrate,
            _h_length, _bitrate, fullpath, country_code, _size, speed, queue, _length, has_free_slots) = row

        expand_user = False
        expand_folder = False

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
                        empty_str,
                        empty_int,
                        empty_str,
                        country_code,
                        empty_int,
                        speed,
                        queue,
                        empty_int,
                        has_free_slots
                    ]
                )

                if self.grouping_mode == "folder_grouping":
                    expand_user = True
                else:
                    expand_user = self.expand_button.get_active()

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
                            empty_str,
                            empty_int,
                            fullpath.rsplit("\\", 1)[0] + "\\",
                            country_code,
                            empty_int,
                            speed,
                            queue,
                            empty_int,
                            has_free_slots
                        ]
                    )
                    expand_folder = self.expand_button.get_active()

                row = row[:]
                row[5] = ""  # Directory not visible for file row if "group by folder" is enabled

                parent = self.directoryiters[user_directory]
        else:
            parent = None

        # Note that we use insert_with_values instead of append, as this reduces
        # overhead by bypassing useless row conversion to GObject.Value in PyGObject.

        if parent is None:
            iterator = self.resultsmodel.insert_with_valuesv(-1, self.column_numbers, row)
        else:
            iterator = self.resultsmodel.insert_with_values(parent, -1, self.column_numbers, row)

        if expand_user:
            self.tree_view.expand_row(self.resultsmodel.get_path(self.usersiters[user]), False)

        if expand_folder:
            self.tree_view.expand_row(self.resultsmodel.get_path(self.directoryiters[user_directory]), False)

        self.num_results_visible += 1
        return iterator

    """ Result Filters """

    @staticmethod
    def _split_operator(condition):
        """ Returns: (operation, digit) """

        operators = {
            "<": operator.lt,
            "<=": operator.le,
            "==": operator.eq,
            "!=": operator.ne,
            ">=": operator.ge,
            ">": operator.gt
        }

        if condition.startswith((">=", "<=", "==", "!=")):
            return operators.get(condition[:2]), condition[2:]

        if condition.startswith((">", "<")):
            return operators.get(condition[:1]), condition[1:]

        if condition.startswith(("=", "!")):
            return operators.get(condition[:1] + "="), condition[1:]

        return operator.ge, condition

    def check_digit(self, result_filter, value, file_size=False):
        """ Check if any conditions in result_filter match value """

        allowed = blocked = False

        for condition in result_filter:
            operation, digit = self._split_operator(condition)

            if file_size:
                digit, factor = factorize(digit)

                if digit is None:
                    # Invalid Size unit
                    continue

                # Exact match unlikely, approximate to within +/- 0.1 MiB (or 1 MiB if over 100 MiB)
                adjust = factor / 8 if factor > 1024 and digit < 104857600 else factor  # TODO: GiB

            else:
                adjust = 0

                try:
                    # Bitrate in Kb/s or Duration in seconds
                    digit = int(digit)
                except ValueError:
                    if ":" not in digit:
                        # Invalid syntax
                        continue

                    try:
                        # Duration: Convert string from HH:MM:SS or MM:SS into Seconds as integer
                        digit = sum(x * int(t) for x, t in zip([1, 60, 3600], reversed(digit.split(":"))))
                    except ValueError:
                        # Invalid Duration unit
                        continue

            if (digit - adjust) <= value <= (digit + adjust):
                if operation is operator.eq:
                    return True

                if operation is operator.ne:
                    return False

            if value and operation(value, digit) and not blocked:
                allowed = True
                continue

            blocked = True

        return False if blocked else allowed

    @staticmethod
    def check_country(result_filter, value):

        allowed = False

        for country_code in result_filter:
            if country_code == value:
                allowed = True

            elif country_code.startswith("!") and country_code[1:] != value:
                allowed = True

            elif country_code.startswith("!") and country_code[1:] == value:
                return False

        return allowed

    @staticmethod
    def check_file_type(result_filter, value):

        allowed = False
        found_inclusive = False

        for ext in result_filter:
            exclude_ext = None

            if ext.startswith("!"):
                exclude_ext = ext[1:]

                if not exclude_ext.startswith("."):
                    exclude_ext = "." + exclude_ext

            elif not ext.startswith("."):
                ext = "." + ext

            if ext.startswith("!") and value.endswith(exclude_ext):
                return False

            if not ext.startswith("!"):
                found_inclusive = True

                if value.endswith(ext):
                    allowed = True

        if not found_inclusive:
            allowed = True

        return allowed

    def check_filter(self, row):

        if self.active_filter_count == 0:
            return True

        for filter_id, filter_value in self.filters.items():
            if not filter_value:
                continue

            if filter_id == "filtertype" and not self.check_file_type(filter_value, row[12].lower()):
                return False

            if filter_id == "filtercc" and not self.check_country(filter_value, row[13].upper()):
                return False

            if filter_id == "filterin" and not filter_value.search(row[12]) and not filter_value.fullmatch(row[1]):
                return False

            if filter_id == "filterout" and (filter_value.search(row[12]) or filter_value.fullmatch(row[1])):
                return False

            if filter_id == "filterslot" and row[16].get_value() > 0:
                return False

            if filter_id == "filtersize" and not self.check_digit(filter_value, row[14].get_value(), file_size=True):
                return False

            if filter_id == "filterbr" and not self.check_digit(filter_value, row[11].get_value()):
                return False

            if filter_id == "filterlength" and not self.check_digit(filter_value, row[17].get_value()):
                return False

        return True

    def update_filter_counter(self, count):

        if count > 0:
            self.filters_label.set_label(_("_Result Filters [%d]") % count)
        else:
            self.filters_label.set_label(_("_Result Filters"))

        self.filters_label.set_tooltip_text(_("%d active filter(s)") % count)

    def clear_model(self, stored_results=False):

        if stored_results:
            self.all_data.clear()
            self.num_results_found = 0
            self.max_limited = False
            self.max_limit = config.sections["searches"]["max_displayed_results"]

        self.tree_view.set_model(None)

        self.usersiters.clear()
        self.directoryiters.clear()
        self.resultsmodel.clear()
        self.num_results_visible = 0

        self.tree_view.set_model(self.resultsmodel)

    def update_model(self):

        # Temporarily disable sorting for increased performance
        sort_column, sort_type = self.resultsmodel.get_sort_column_id()
        self.resultsmodel.set_default_sort_func(lambda *_args: 0)
        self.resultsmodel.set_sort_column_id(-1, Gtk.SortType.ASCENDING)

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

            if self.expand_button.get_active():
                self.tree_view.expand_all()
            else:
                collapse_treeview(self.tree_view, self.grouping_mode)

    def update_wish_button(self):

        if self.mode not in ("global", "wishlist"):
            self.add_wish_button.set_visible(False)
            return

        if not core.search.is_wish(self.text):
            self.add_wish_icon.set_property("icon-name", "list-add-symbolic")
            self.add_wish_label.set_label(_("Add Wi_sh"))
            return

        self.add_wish_icon.set_property("icon-name", "list-remove-symbolic")
        self.add_wish_label.set_label(_("Remove Wi_sh"))

    def on_add_wish(self, *_args):

        if core.search.is_wish(self.text):
            core.search.remove_wish(self.text)
        else:
            core.search.add_wish(self.text)

    def add_popup_menu_user(self, popup, user):

        popup.setup_user_menu(user)
        popup.add_items(
            ("", None),
            ("#" + _("Select User's Results"), self.on_select_user_results, user)
        )
        popup.update_model()
        popup.toggle_user_items()

    def populate_popup_menu_users(self):

        self.popup_menu_users.clear()

        if not self.selected_users:
            return

        # Multiple users, create submenus for each user
        if len(self.selected_users) > 1:
            for user in self.selected_users:
                popup = UserPopupMenu(self.window.application)
                self.add_popup_menu_user(popup, user)
                self.popup_menu_users.add_items((">" + user, popup))
                self.popup_menu_users.update_model()
            return

        # Single user, add items directly to "User Actions" submenu
        user = next(iter(self.selected_users), None)
        self.add_popup_menu_user(self.popup_menu_users, user)

    def on_close_filter_bar_accelerator(self, *_args):
        """ Escape: hide filter bar """

        self.filters_button.set_active(False)
        return True

    def on_show_filter_bar_accelerator(self, *_args):
        """ Ctrl+F: show filter bar """

        self.filters_button.set_active(True)
        self.filter_include_combobox.grab_focus()
        return True

    def on_file_properties_accelerator(self, *_args):
        """ Alt+Return: show file properties dialog """

        self.on_file_properties()
        return True

    def on_select_user_results(self, *args):

        if not self.selected_users:
            return

        selected_user = args[-1]

        sel = self.tree_view.get_selection()
        fmodel = self.tree_view.get_model()
        sel.unselect_all()

        iterator = fmodel.get_iter_first()

        select_user_row_iter(fmodel, sel, 1, selected_user, iterator)

        self.select_results()

    def select_result(self, model, iterator):

        user = model.get_value(iterator, 1)

        if user not in self.selected_users:
            self.selected_users[user] = None

        filename = model.get_value(iterator, 7)

        if not filename:
            return

        iter_key = iterator.user_data

        if iter_key not in self.selected_results:
            self.selected_results[iter_key] = iterator

    def select_child_results(self, model, iterator):

        while iterator is not None:
            self.select_result(model, iterator)
            self.select_child_results(model, model.iter_children(iterator))

            iterator = model.iter_next(iterator)

    def select_results(self):

        self.selected_results.clear()
        self.selected_users.clear()

        model, paths = self.tree_view.get_selection().get_selected_rows()

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
                total = f"> {self.max_limit}+"
            else:
                total = self.num_results_found

            self.results_button.set_tooltip_text(_("Total: %s") % total)

        else:  # Hide the tooltip if there are no hidden results
            str_plus = ""
            self.results_button.set_has_tooltip(False)

        self.results_label.set_text(humanize(self.num_results_visible) + str_plus)

    def on_column_position_changed(self, column, _param):
        """ Save column position and width to config """

        col_title = column.get_title()
        offset = column.get_x_offset()

        if self.column_offsets[col_title] == offset:
            return

        self.column_offsets[col_title] = offset
        save_columns(self.treeview_name, self.tree_view.get_columns())

    def on_row_activated(self, treeview, path, _column):

        self.select_results()

        iterator = self.resultsmodel.get_iter(path)
        folder = self.resultsmodel.get_value(iterator, 5)
        filename = self.resultsmodel.get_value(iterator, 7)

        if not folder and not filename:
            # Don't activate user rows
            return

        if not filename:
            self.on_download_folders()
        else:
            self.on_download_files()

        treeview.get_selection().unselect_all()

    def on_popup_menu(self, menu, _widget):

        self.select_results()
        self.populate_popup_menu_users()
        menu.set_num_selected_files(len(self.selected_results))

    def on_browse_folder(self, *_args):

        requested_users = set()
        requested_folders = set()

        for iterator in self.selected_results.values():
            user = self.resultsmodel.get_value(iterator, 1)
            folder = self.resultsmodel.get_value(iterator, 12).rsplit("\\", 1)[0] + "\\"

            if user not in requested_users and folder not in requested_folders:
                core.userbrowse.browse_user(user, path=folder)

                requested_users.add(user)
                requested_folders.add(folder)

    def on_file_properties(self, *_args):

        data = []
        selected_size = 0
        selected_length = 0

        for iterator in self.selected_results.values():
            virtual_path = self.resultsmodel.get_value(iterator, 11)
            directory, filename = virtual_path.rsplit("\\", 1)
            file_size = self.resultsmodel.get_value(iterator, 14)
            selected_size += file_size
            selected_length += self.resultsmodel.get_value(iterator, 17)
            country_code = self.resultsmodel.get_value(iterator, 13)
            country_name = core.geoip.country_code_to_name(country_code)
            country = f"{country_name} ({country_code})"

            data.append({
                "user": self.resultsmodel.get_value(iterator, 1),
                "fn": virtual_path,
                "filename": filename,
                "directory": directory,
                "size": file_size,
                "speed": self.resultsmodel.get_value(iterator, 15),
                "queue_position": self.resultsmodel.get_value(iterator, 16),
                "bitrate": self.resultsmodel.get_value(iterator, 9),
                "length": self.resultsmodel.get_value(iterator, 10),
                "country": country
            })

        if data:
            if self.searches.file_properties is None:
                self.searches.file_properties = FileProperties(self.window.application, core)

            self.searches.file_properties.update_properties(data, selected_size, selected_length)
            self.searches.file_properties.show()

    def on_download_files(self, *_args, prefix=""):

        for iterator in self.selected_results.values():
            user = self.resultsmodel.get_value(iterator, 1)
            filepath = self.resultsmodel.get_value(iterator, 12)
            size = self.resultsmodel.get_value(iterator, 14)
            bitrate = self.resultsmodel.get_value(iterator, 9)
            length = self.resultsmodel.get_value(iterator, 10)

            core.transfers.get_file(
                user, filepath, prefix, size=size, bitrate=bitrate, length=length)

    def on_download_files_to_selected(self, selected, _data):
        self.on_download_files(prefix=selected)

    def on_download_files_to(self, *_args):

        FolderChooser(
            parent=self.window,
            title=_("Select Destination Folder for File(s)"),
            callback=self.on_download_files_to_selected,
            initial_folder=config.sections["transfers"]["downloaddir"]
        ).show()

    def on_download_folders(self, *_args, download_location=""):

        if download_location:
            """ Custom download location specified, remember it when peer sends a folder
            contents reply """

            requested_folders = core.transfers.requested_folders
        else:
            requested_folders = defaultdict(dict)

        for iterator in self.selected_results.values():
            user = self.resultsmodel.get_value(iterator, 1)
            folder = self.resultsmodel.get_value(iterator, 12).rsplit("\\", 1)[0]

            if folder in requested_folders[user]:
                """ Ensure we don't send folder content requests for a folder more than once,
                e.g. when several selected resuls belong to the same folder. """
                continue

            requested_folders[user][folder] = download_location

            visible_files = []
            for row in self.all_data:

                # Find the wanted directory
                if folder != row[12].rsplit("\\", 1)[0]:
                    continue

                # remove_destination is False because we need the destination for the full folder
                # contents response later
                destination = core.transfers.get_folder_destination(user, folder, remove_destination=False)

                (_counter, user, _flag, _h_speed, _h_queue, _directory, _file_type, _filename,
                    _h_size, h_bitrate, h_length, _bitrate, fullpath, _country_code, size, _speed,
                    _queue, _length, _has_free_slots) = row
                visible_files.append(
                    (user, fullpath, destination, size.get_value(), h_bitrate, h_length))

            core.search.request_folder_download(user, folder, visible_files)

    def on_download_folders_to_selected(self, selected, _data):
        self.on_download_folders(download_location=selected)

    def on_download_folders_to(self, *_args):

        FolderChooser(
            parent=self.window,
            title=_("Select Destination Folder"),
            callback=self.on_download_folders_to_selected,
            initial_folder=config.sections["transfers"]["downloaddir"]
        ).show()

    def on_copy_file_path(self, *_args):

        for iterator in self.selected_results.values():
            filepath = self.resultsmodel.get_value(iterator, 12)
            copy_text(filepath)
            return

    def on_copy_url(self, *_args):

        for iterator in self.selected_results.values():
            user = self.resultsmodel.get_value(iterator, 1)
            filepath = self.resultsmodel.get_value(iterator, 12)
            url = core.userbrowse.get_soulseek_url(user, filepath)
            copy_text(url)
            return

    def on_copy_dir_url(self, *_args):

        for iterator in self.selected_results.values():
            user = self.resultsmodel.get_value(iterator, 1)
            filepath = self.resultsmodel.get_value(iterator, 12)
            url = core.userbrowse.get_soulseek_url(user, filepath.rsplit("\\", 1)[0] + "\\")
            copy_text(url)
            return

    def on_counter_button(self, *_args):

        if self.num_results_found > self.num_results_visible:
            self.on_clear_filters()
        else:
            self.window.application.lookup_action("configure-searches").activate()

    def on_group(self, action, state):

        mode = state.get_string()
        active = mode != "ungrouped"
        popover = self.grouping_button.get_popover()

        if popover is not None:
            popover.set_visible(False)

        config.sections["searches"]["group_searches"] = mode
        self.cols["id"].set_visible(not active)
        self.tree_view.set_show_expanders(active)
        self.expand_button.set_visible(active)

        self.grouping_mode = mode

        self.clear_model()
        self.create_model()
        self.update_model()

        action.set_state(state)

    def on_toggle_expand_all(self, *_args):

        active = self.expand_button.get_active()

        if active:
            self.tree_view.expand_all()
            self.expand_icon.set_property("icon-name", "go-up-symbolic")
        else:
            collapse_treeview(self.tree_view, self.grouping_mode)
            self.expand_icon.set_property("icon-name", "go-down-symbolic")

        config.sections["searches"]["expand_searches"] = active

    def on_toggle_filters(self, *_args):

        visible = self.filters_button.get_active()
        self.filters_container.set_reveal_child(visible)
        config.sections["searches"]["filters_visible"] = visible

        if visible:
            self.filter_include_combobox.grab_focus()
            return

        self.tree_view.grab_focus()

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

        elif len(history) >= 50:
            del history[-1]

        history.insert(0, value)
        config.write_configuration()

    def on_refilter(self, *_args):

        if self.clearing_filters:
            return

        filter_in = self.filter_include_combobox.get_active_text().strip()
        filter_out = self.filter_exclude_combobox.get_active_text().strip()
        filter_size = self.filter_file_size_combobox.get_active_text().strip()
        filter_bitrate = self.filter_bitrate_combobox.get_active_text().strip()
        filter_country = self.filter_country_combobox.get_active_text().strip()
        filter_file_type = self.filter_file_type_combobox.get_active_text().strip()
        filter_length = self.filter_length_combobox.get_active_text().strip()
        filter_free_slot = self.filter_free_slot_button.get_active()

        if filter_in:
            try:
                filter_in = re.compile(filter_in, flags=re.IGNORECASE)
            except re.error:
                filter_in = None

        if filter_out:
            try:
                filter_out = re.compile(filter_out, flags=re.IGNORECASE)
            except re.error:
                filter_out = None

        # Split at | pipes ampersands & space(s) but don't split <>=! math operators spaced before digit condition
        seperator_pattern = self.FILTER_SPLIT_DIGIT_PATTERN

        if filter_size:
            filter_size = seperator_pattern.split(filter_size)

        if filter_bitrate:
            filter_bitrate = seperator_pattern.split(filter_bitrate)

        if filter_length:
            filter_length = seperator_pattern.split(filter_length)

        # Split at commas, in addition to | pipes ampersands & space(s) but don't split ! not operator before condition
        seperator_pattern = self.FILTER_SPLIT_TEXT_PATTERN

        if filter_country:
            filter_country = seperator_pattern.split(filter_country.upper())

        if filter_file_type:
            filter_file_type = seperator_pattern.split(filter_file_type.lower())

        filters = {
            "filterin": filter_in,
            "filterout": filter_out,
            "filtersize": filter_size,
            "filterbr": filter_bitrate,
            "filterslot": filter_free_slot,
            "filtercc": filter_country,
            "filtertype": filter_file_type,
            "filterlength": filter_length,
        }

        if self.filters == filters:
            # Filters have not changed, no need to refilter
            return

        self.active_filter_count = 0

        # Set red background if invalid regex pattern is detected
        filter_include_entry = self.filter_include_combobox.get_child()
        filter_exclude_entry = self.filter_exclude_combobox.get_child()

        for filter_regex, entry in (
            (filter_in, filter_include_entry),
            (filter_out, filter_exclude_entry)
        ):
            css_class_function = add_css_class if filter_regex is None else remove_css_class
            css_class_function(entry, "error")

        # Add filters to history
        for filter_id, value in filters.items():
            if not value:
                continue

            if filter_id in ("filterin", "filterout"):
                value = value.pattern

            elif filter_id in ("filtersize", "filterbr", "filtercc", "filtertype", "filterlength"):
                value = " ".join(value)

            self.push_history(filter_id, value)
            self.active_filter_count += 1

        # Replace generic file type filters with real file extensions
        file_type_filters = filters["filtertype"]

        for filter_name, file_extensions in self.FILTER_GENERIC_FILE_TYPES:
            excluded_filter_name = f"!{filter_name}"

            if filter_name in file_type_filters:
                file_type_filters.remove(filter_name)
                file_type_filters += list(file_extensions)

            elif excluded_filter_name in file_type_filters:
                file_type_filters.remove(excluded_filter_name)
                file_type_filters += ["!" + x for x in file_extensions]

        # Apply the new filters
        self.filters = filters
        self.update_filter_comboboxes()
        self.clear_model()
        self.update_model()

    def on_filter_entry_changed(self, widget):
        if not widget.get_text():
            self.on_refilter()

    def on_clear_filters(self, *_args):

        self.clearing_filters = True

        for widget in self.filter_comboboxes.values():
            widget.get_child().set_text("")

        self.filter_free_slot_button.set_active(False)

        if self.filters_button.get_active():
            self.filter_include_combobox.get_child().grab_focus()
        else:
            self.tree_view.grab_focus()

        self.clearing_filters = False
        self.on_refilter()

    def on_clear(self, *_args):

        self.clear_model(stored_results=True)

        # Allow parsing search result messages again
        core.search.add_allowed_token(self.token)

        # Update number of results widget
        self.update_result_counter()

    def on_focus(self, *_args):

        if self.window.search_entry.get_text():
            # Search entry contains text, let it grab focus instead
            return

        self.tree_view.grab_focus()

    def on_close(self, *_args):
        core.search.remove_search(self.token)

    def on_close_all_tabs(self, *_args):
        self.searches.remove_all_pages()
