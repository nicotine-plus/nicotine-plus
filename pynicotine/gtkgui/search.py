# COPYRIGHT (C) 2020-2024 Nicotine+ Contributors
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
import os
import re

from itertools import islice

from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk

from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.dialogs.fileproperties import FileProperties
from pynicotine.gtkgui.widgets import clipboard
from pynicotine.gtkgui.widgets import ui
from pynicotine.gtkgui.widgets.accelerator import Accelerator
from pynicotine.gtkgui.widgets.combobox import ComboBox
from pynicotine.gtkgui.widgets.filechooser import FolderChooser
from pynicotine.gtkgui.widgets.iconnotebook import IconNotebook
from pynicotine.gtkgui.widgets.popupmenu import PopupMenu
from pynicotine.gtkgui.widgets.popupmenu import FilePopupMenu
from pynicotine.gtkgui.widgets.popupmenu import UserPopupMenu
from pynicotine.gtkgui.widgets.theme import add_css_class
from pynicotine.gtkgui.widgets.theme import get_file_type_icon_name
from pynicotine.gtkgui.widgets.theme import get_flag_icon_name
from pynicotine.gtkgui.widgets.theme import remove_css_class
from pynicotine.gtkgui.widgets.treeview import TreeView
from pynicotine.gtkgui.widgets.treeview import create_grouping_menu
from pynicotine.logfacility import log
from pynicotine.shares import FileTypes
from pynicotine.slskmessages import FileListMessage
from pynicotine.utils import factorize
from pynicotine.utils import humanize
from pynicotine.utils import human_size
from pynicotine.utils import human_speed


class SearchResultFile:
    __slots__ = ("path", "attributes")

    def __init__(self, path, attributes=None):
        self.path = path
        self.attributes = attributes


class Searches(IconNotebook):

    def __init__(self, window):

        super().__init__(
            window,
            parent=window.search_content,
            parent_page=window.search_page,
            switch_page_callback=self.on_switch_search_page
        )

        self.page = window.search_page
        self.page.id = "search"
        self.toolbar = window.search_toolbar
        self.toolbar_start_content = window.search_title
        self.toolbar_end_content = window.search_end
        self.toolbar_default_widget = window.search_entry

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
        mode_menu.set_menu_button(window.search_mode_button)
        window.search_mode_label.set_label(self.modes["global"])

        if GTK_API_VERSION >= 4:
            inner_button = next(iter(window.search_mode_button))
            add_css_class(inner_button, "arrow-button")

        self.room_search_combobox = ComboBox(
            container=self.window.search_title, has_entry=True, has_entry_completion=True,
            entry=self.window.room_search_entry, visible=False
        )

        self.user_search_combobox = ComboBox(
            container=self.window.search_title, has_entry=True, has_entry_completion=True,
            entry=self.window.user_search_entry, visible=False
        )

        self.search_combobox = ComboBox(
            container=self.window.search_title, has_entry=True, has_entry_completion=True,
            entry=self.window.search_entry
        )

        self.file_properties = None

        for event_name, callback in (
            ("add-search", self.add_search),
            ("add-wish", self.update_wish_button),
            ("file-search-response", self.file_search_response),
            ("quit", self.quit),
            ("remove-search", self.remove_search),
            ("remove-wish", self.update_wish_button),
            ("server-disconnect", self.server_disconnect),
            ("server-login", self.server_login),
            ("show-search", self.show_search)
        ):
            events.connect(event_name, callback)

        self.populate_search_history()

    def quit(self):
        self.freeze()

    def destroy(self):

        self.room_search_combobox.destroy()
        self.user_search_combobox.destroy()
        self.search_combobox.destroy()

        if self.file_properties is not None:
            self.file_properties.destroy()

        super().destroy()

    def on_focus(self, *_args):

        if self.window.current_page_id != self.window.search_page.id:
            return True

        if self.window.search_entry.is_sensitive():
            self.window.search_entry.grab_focus()
            return True

        return False

    def on_restore_removed_page(self, page_args):
        search_term, mode, room, users = page_args
        core.search.do_search(search_term, mode, room=room, users=users)

    def on_remove_all_pages(self, *_args):
        core.search.remove_all_searches()

    def on_switch_search_page(self, _notebook, page, _page_num):

        if self.window.current_page_id != self.window.search_page.id:
            return

        for tab in self.pages.values():
            if tab.container != page:
                continue

            self.window.update_title()
            break

    def on_search_mode(self, action, state):

        action.set_state(state)
        search_mode = state.get_string()

        self.window.search_mode_label.set_label(self.modes[search_mode])

        self.user_search_combobox.set_visible(search_mode == "user")
        self.room_search_combobox.set_visible(search_mode == "rooms")

        # Hide popover after click
        self.window.search_mode_button.get_popover().set_visible(False)

    def on_search(self):

        text = self.window.search_entry.get_text().strip()

        if not text:
            return

        mode = self.window.lookup_action("search-mode").get_state().get_string()
        room = self.room_search_combobox.get_text()
        user = self.user_search_combobox.get_text()
        users = [user] if user else []

        self.window.search_entry.set_text("")
        core.search.do_search(text, mode, room=room, users=users)

    def populate_search_history(self):

        self.search_combobox.freeze()

        if not config.sections["searches"]["enable_history"]:
            self.search_combobox.clear()
        else:
            for term in islice(config.sections["searches"]["history"], core.search.SEARCH_HISTORY_LIMIT):
                self.search_combobox.append(str(term))

        self.search_combobox.unfreeze()

    def add_search_history_item(self, term):

        if not config.sections["searches"]["enable_history"]:
            return

        self.search_combobox.remove_id(term)
        self.search_combobox.prepend(term)

        while self.search_combobox.get_num_items() > core.search.SEARCH_HISTORY_LIMIT:
            self.search_combobox.remove_pos(-1)

    def create_page(self, token, text, mode=None, mode_label=None, room=None, users=None,
                    show_page=True):

        page = self.pages.get(token)

        if page is None:
            self.pages[token] = page = Search(
                self, text=text, token=token, mode=mode, mode_label=mode_label,
                room=room, users=users, show_page=show_page)
        else:
            mode_label = page.mode_label

        if not show_page:
            return page

        if mode_label is not None:
            text = f"({mode_label}) {text}"

        self.append_page(page.container, text, focus_callback=page.on_focus,
                         close_callback=page.on_close)
        page.set_label(self.get_tab_label_inner(page.container))

        return page

    def add_search(self, token, search, switch_page=True):

        mode = search.mode
        mode_label = None
        room = search.room
        users = search.users

        if mode == "rooms":
            mode_label = room.strip()

        elif mode == "user":
            mode_label = ",".join(users)

        elif mode == "buddies":
            mode_label = _("Buddies")

        self.create_page(token, search.term_sanitized, mode, mode_label, room=room, users=users)

        if switch_page:
            self.show_search(token)

        self.add_search_history_item(search.term_sanitized)

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

        if page.show_page:
            mode = page.mode

            if mode == "wishlist":
                # For simplicity's sake, turn wishlist tabs into regular ones when restored
                mode = "global"

            self.remove_page(page.container, page_args=(page.text, mode, page.room, page.searched_users))

        del self.pages[token]
        page.destroy()

    def clear_search_history(self):

        self.search_combobox.freeze()
        self.window.search_entry.set_text("")

        config.sections["searches"]["history"] = []
        config.write_configuration()

        self.search_combobox.clear()
        self.search_combobox.unfreeze()

    def add_filter_history_item(self, filter_id, value):
        for page in self.pages.values():
            page.add_filter_history_item(filter_id, value)

    def clear_filter_history(self):

        # Clear filter history in config
        for filter_id in ("filterin", "filterout", "filtertype", "filtersize", "filterbr", "filterlength", "filtercc"):
            config.sections["searches"][filter_id] = []

        config.write_configuration()

        # Update filters in search tabs
        for page in self.pages.values():
            page.filters_undo = page.FILTERS_EMPTY
            page.populate_filter_history()

    def file_search_response(self, msg):

        page = self.pages.get(msg.token)

        if page is None:
            search_item = core.search.searches.get(msg.token)

            if search_item is None:
                return

            search_term = search_item.term
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

    def server_login(self, *_args):
        self.window.search_title.set_sensitive(True)
        self.on_focus()

    def server_disconnect(self, *_args):
        self.window.search_title.set_sensitive(False)


class Search:

    FILTER_GENERIC_FILE_TYPES = (
        ("audio", FileTypes.AUDIO),
        ("executable", FileTypes.EXECUTABLE),
        ("image", FileTypes.IMAGE),
        ("video", FileTypes.VIDEO),
        ("document", FileTypes.DOCUMENT),
        ("text", FileTypes.TEXT),
        ("archive", FileTypes.ARCHIVE)
    )
    FILTER_PRESETS = {
        "filterbr": ("!0", "128 <=192", ">192 <320", "=320", ">320"),
        "filtersize": (">50MiB", ">20MiB <=50MiB", ">10MiB <=20MiB", ">5MiB <=10MiB", "<=5MiB"),
        "filtertype": ("audio", "image", "video", "document", "text", "archive", "!executable", "audio image text"),
        "filterlength": (">15:00", ">8:00 <=15:00", ">5:00 <=8:00", ">2:00 <=5:00", "<=2:00")
    }
    FILTER_SPLIT_DIGIT_PATTERN = re.compile(r"(?:[|&\s])+(?<![<>!=]\s)")  # [pipe, ampersand, space]
    FILTER_SPLIT_TEXT_PATTERN = re.compile(r"(?:[|&,;\s])+(?<!!\s)")      # [pipe, ampersand, comma, semicolon, space]
    FILTERS_EMPTY = {
        "filterin": (None, ""),
        "filterout": (None, ""),
        "filtersize": (None, ""),
        "filterbr": (None, ""),
        "filterslot": (False, False),
        "filtercc": (None, ""),
        "filtertype": (None, ""),
        "filterlength": (None, "")
    }

    def __init__(self, searches, text, token, mode, mode_label, room, users, show_page):

        (
            self.add_wish_button,
            self.add_wish_icon,
            self.add_wish_label,
            self.clear_undo_filters_button,
            self.clear_undo_filters_icon,
            self.container,
            self.expand_button,
            self.expand_icon,
            self.filter_bitrate_container,
            self.filter_bitrate_entry,
            self.filter_country_container,
            self.filter_country_entry,
            self.filter_exclude_container,
            self.filter_exclude_entry,
            self.filter_file_size_container,
            self.filter_file_size_entry,
            self.filter_file_type_container,
            self.filter_file_type_entry,
            self.filter_free_slot_button,
            self.filter_include_container,
            self.filter_include_entry,
            self.filter_length_container,
            self.filter_length_entry,
            self.filters_button,
            self.filters_container,
            self.filters_label,
            self.grouping_button,
            self.results_button,
            self.results_label,
            self.tree_container
        ) = ui.load(scope=self, path="search.ui")

        self.searches = searches
        self.window = searches.window

        self.text = text
        self.token = token
        self.mode = mode
        self.mode_label = mode_label
        self.room = room
        self.searched_users = users
        self.show_page = show_page
        self.initialized = False
        self.users = {}
        self.folders = {}
        self.all_data = []
        self.grouping_mode = None
        self.row_id = 0
        self.filters = {}
        self.filters_undo = self.FILTERS_EMPTY
        self.populating_filters = False
        self.refiltering = False
        self.active_filter_count = 0
        self.num_results_found = 0
        self.num_results_visible = 0
        self.max_limit = config.sections["searches"]["max_displayed_results"]
        self.max_limited = False

        # Use dict instead of list for faster membership checks
        self.selected_users = {}
        self.selected_results = {}

        # Combo boxes
        self.filter_include_combobox = ComboBox(
            container=self.filter_include_container, has_entry=True,
            entry=self.filter_include_entry, item_selected_callback=self.on_refilter)

        self.filter_exclude_combobox = ComboBox(
            container=self.filter_exclude_container, has_entry=True,
            entry=self.filter_exclude_entry, item_selected_callback=self.on_refilter)

        self.filter_file_type_combobox = ComboBox(
            container=self.filter_file_type_container, has_entry=True,
            entry=self.filter_file_type_entry, item_selected_callback=self.on_refilter)

        self.filter_file_size_combobox = ComboBox(
            container=self.filter_file_size_container, has_entry=True,
            entry=self.filter_file_size_entry, item_selected_callback=self.on_refilter)

        self.filter_bitrate_combobox = ComboBox(
            container=self.filter_bitrate_container, has_entry=True,
            entry=self.filter_bitrate_entry, item_selected_callback=self.on_refilter)

        self.filter_length_combobox = ComboBox(
            container=self.filter_length_container, has_entry=True,
            entry=self.filter_length_entry, item_selected_callback=self.on_refilter)

        self.filter_country_combobox = ComboBox(
            container=self.filter_country_container, has_entry=True,
            entry=self.filter_country_entry, item_selected_callback=self.on_refilter)

        self.tree_view = TreeView(
            self.window, parent=self.tree_container, name="file_search", persistent_sort=True,
            multi_select=True, activate_row_callback=self.on_row_activated, focus_in_callback=self.on_refilter,
            columns={
                # Visible columns
                "user": {
                    "column_type": "text",
                    "title": _("User"),
                    "width": 200,
                    "sensitive_column": "free_slot_data"
                },
                "country": {
                    "column_type": "icon",
                    "title": _("Country"),
                    "width": 30,
                    "hide_header": True
                },
                "speed": {
                    "column_type": "number",
                    "title": _("Speed"),
                    "width": 120,
                    "sort_column": "speed_data",
                    "sensitive_column": "free_slot_data"
                },
                "in_queue": {
                    "column_type": "number",
                    "title": _("In Queue"),
                    "width": 110,
                    "sort_column": "in_queue_data",
                    "sensitive_column": "free_slot_data"
                },
                "folder": {
                    "column_type": "text",
                    "title": _("Folder"),
                    "width": 200,
                    "expand_column": True,
                    "sensitive_column": "free_slot_data",
                    "tooltip_callback": self.on_file_path_tooltip
                },
                "file_type": {
                    "column_type": "icon",
                    "title": _("File Type"),
                    "width": 40,
                    "hide_header": True,
                    "sensitive_column": "free_slot_data"
                },
                "filename": {
                    "column_type": "text",
                    "title": _("Filename"),
                    "width": 200,
                    "expand_column": True,
                    "sensitive_column": "free_slot_data",
                    "tooltip_callback": self.on_file_path_tooltip
                },
                "size": {
                    "column_type": "number",
                    "title": _("Size"),
                    "width": 180,
                    "sort_column": "size_data",
                    "sensitive_column": "free_slot_data"
                },
                "quality": {
                    "column_type": "number",
                    "title": _("Quality"),
                    "width": 150,
                    "sort_column": "bitrate_data",
                    "sensitive_column": "free_slot_data"
                },
                "length": {
                    "column_type": "number",
                    "title": _("Duration"),
                    "width": 100,
                    "sort_column": "length_data",
                    "sensitive_column": "free_slot_data"
                },

                # Hidden data columns
                "speed_data": {"data_type": GObject.TYPE_UINT},
                "in_queue_data": {"data_type": GObject.TYPE_UINT},
                "size_data": {"data_type": GObject.TYPE_UINT64},
                "bitrate_data": {"data_type": GObject.TYPE_UINT},
                "length_data": {"data_type": GObject.TYPE_UINT},
                "free_slot_data": {"data_type": GObject.TYPE_BOOLEAN},
                "file_data": {"data_type": GObject.TYPE_PYOBJECT},
                "id_data": {
                    "data_type": GObject.TYPE_INT,
                    "default_sort_type": "ascending",
                    "iterator_key": True
                }
            }
        )

        # Popup menus
        self.popup_menu_users = UserPopupMenu(self.window.application, tab_name="search")

        self.popup_menu_copy = PopupMenu(self.window.application)
        self.popup_menu_copy.add_items(
            ("#" + _("Copy _File Path"), self.on_copy_file_path),
            ("#" + _("Copy _URL"), self.on_copy_url),
            ("#" + _("Copy Folder U_RL"), self.on_copy_folder_url)
        )

        self.popup_menu = FilePopupMenu(
            self.window.application, parent=self.tree_view.widget, callback=self.on_popup_menu
        )
        self.popup_menu.add_items(
            ("#" + _("_Download File(s)"), self.on_download_files),
            ("#" + _("Download File(s) _To…"), self.on_download_files_to),
            ("", None),
            ("#" + _("Download _Folder(s)"), self.on_download_folders),
            ("#" + _("Download F_older(s) To…"), self.on_download_folders_to),
            ("", None),
            ("#" + _("View User _Profile"), self.on_user_profile),
            ("#" + _("_Browse Folder"), self.on_browse_folder),
            ("#" + _("F_ile Properties"), self.on_file_properties),
            ("", None),
            (">" + _("Copy"), self.popup_menu_copy),
            (">" + _("User Actions"), self.popup_menu_users)
        )

        self.tab_menu = PopupMenu(self.window.application)
        self.tab_menu.add_items(
            ("#" + _("Edit…"), self.on_edit_search),
            ("#" + _("Copy Search Term"), self.on_copy_search_term),
            ("", None),
            ("#" + _("Clear All Results"), self.on_clear),
            ("#" + _("Close All Tabs…"), self.on_close_all_tabs),
            ("#" + _("_Close Tab"), self.on_close)
        )

        self.popup_menus = (
            self.popup_menu, self.popup_menu_users, self.popup_menu_copy, self.tab_menu
        )

        # Key bindings
        for widget in (self.container, self.tree_view.widget):
            Accelerator("<Primary>f", widget, self.on_show_filter_bar_accelerator)

        Accelerator("Escape", self.filters_container, self.on_close_filter_bar_accelerator)
        Accelerator("<Alt>Return", self.tree_view.widget, self.on_file_properties_accelerator)

        # Grouping
        menu = create_grouping_menu(self.window, config.sections["searches"]["group_searches"], self.on_group)
        self.grouping_button.set_menu_model(menu)

        if GTK_API_VERSION >= 4:
            inner_button = next(iter(self.grouping_button))
            add_css_class(widget=inner_button, css_class="image-button")

        # Workaround for GTK bug where clicks stop working after clicking inside popover once
        if GTK_API_VERSION >= 4 and os.environ.get("GDK_BACKEND") == "broadway":
            popover = list(self.grouping_button)[-1]
            popover.set_has_arrow(False)

        self.expand_button.set_active(config.sections["searches"]["expand_searches"])

        # Filter button widgets
        self.filter_buttons = {
            "filterslot": self.filter_free_slot_button
        }

        # Filter combobox widgets
        self.filter_comboboxes = {
            "filterin": self.filter_include_combobox,
            "filterout": self.filter_exclude_combobox,
            "filtersize": self.filter_file_size_combobox,
            "filterbr": self.filter_bitrate_combobox,
            "filtercc": self.filter_country_combobox,
            "filtertype": self.filter_file_type_combobox,
            "filterlength": self.filter_length_combobox
        }

        # Filter text entry widgets
        for filter_id, combobox in self.filter_comboboxes.items():
            combobox.entry.filter_id = filter_id

            buffer = combobox.entry.get_buffer()
            buffer.connect_after("deleted-text", self.on_filter_entry_deleted_text)

            if GTK_API_VERSION == 3:
                add_css_class(combobox.dropdown, "dropdown-scrollbar")

        self.filters_button.set_active(config.sections["searches"]["filters_visible"])
        self.populate_filter_history()
        self.populate_default_filters()

        # Wishlist
        self.update_wish_button()

    def clear(self):
        self.clear_model(stored_results=True)

    def destroy(self):

        for menu in self.popup_menus:
            menu.destroy()

        for combobox in self.filter_comboboxes.values():
            combobox.destroy()

        self.tree_view.destroy()
        self.window.update_title()
        self.__dict__.clear()

    def set_label(self, label):
        self.tab_menu.set_parent(label)

    def update_filter_widgets(self):

        self.update_filter_counter(self.active_filter_count)

        if self.filters_undo == self.FILTERS_EMPTY:
            tooltip_text = _("Clear Filters")
            icon_name = "edit-clear-symbolic"
        else:
            tooltip_text = _("Restore Filters")
            icon_name = "edit-undo-symbolic"

        if self.clear_undo_filters_icon.get_icon_name() == icon_name:
            return

        icon_args = (Gtk.IconSize.BUTTON,) if GTK_API_VERSION == 3 else ()  # pylint: disable=no-member
        self.clear_undo_filters_button.set_tooltip_text(tooltip_text)
        self.clear_undo_filters_icon.set_from_icon_name(icon_name, *icon_args)

    def populate_filter_history(self):

        for filter_id, widget in self.filter_comboboxes.items():
            widget.freeze()
            widget.clear()

            presets = self.FILTER_PRESETS.get(filter_id)
            filter_history = config.sections["searches"][filter_id]

            if presets:
                for index, value in enumerate(presets):
                    widget.append(value, item_id=f"preset_{index}")

                if filter_history:
                    widget.append("")  # Separator

            for value in islice(filter_history, core.search.RESULT_FILTER_HISTORY_LIMIT):
                widget.append(value)

            widget.unfreeze()

    def populate_default_filters(self):

        if not config.sections["searches"]["enablefilters"]:
            return

        sfilter = config.sections["searches"]["defilter"]
        num_filters = len(sfilter)
        stored_filters = self.FILTERS_EMPTY.copy()

        # Convert from list to dict
        for i, filter_id in enumerate(stored_filters):
            if i >= num_filters:
                break

            if filter_id in self.filter_buttons:
                stored_filters[filter_id] = (False, bool(sfilter[i]))

            elif filter_id in self.filter_comboboxes:
                stored_filters[filter_id] = (None, str(sfilter[i]))

        self.set_filters(stored_filters)

    def set_filters(self, stored_filters):
        """Recall result filter values from a dict."""

        self.populating_filters = True

        for filter_id, button in self.filter_buttons.items():
            _value, h_value = stored_filters.get(filter_id, (False, False))
            button.set_active(h_value)

        for filter_id, combobox in self.filter_comboboxes.items():
            _value, h_value = stored_filters.get(filter_id, (None, ""))
            combobox.set_text(h_value)

        self.populating_filters = False

        self.on_refilter()

    def add_result_list(self, result_list, user, country_code, inqueue, ulspeed, h_speed,
                        h_queue, has_free_slots, private=False):
        """Adds a list of search results to the treeview.

        Lists can either contain publicly or privately shared files.
        """

        update_ui = False
        search = core.search.searches[self.token]
        row_id = 0

        for _code, file_path, size, _ext, file_attributes, *_unused in result_list:
            if self.num_results_found >= self.max_limit:
                self.max_limited = True
                break

            file_path_lower = file_path.lower()

            if any(word in file_path_lower for word in search.excluded_words):
                # Filter out results with filtered words (e.g. nicotine -music)
                log.add_debug(("Filtered out excluded search result %s from user %s for "
                               'search term "%s"'), (file_path, user, self.text))
                continue

            if not all(word in file_path_lower for word in search.included_words):
                # Certain users may send us wrong results, filter out such ones
                continue

            self.num_results_found += 1
            file_path_split = file_path.split("\\")

            if config.sections["ui"]["reverse_file_paths"]:
                # Reverse file path, file name is the first item. next() retrieves the name and removes
                # it from the iterator.
                file_path_split = reversed(file_path_split)
                name = next(file_path_split)

            else:
                # Regular file path, file name is the last item. Retrieve it and remove it from the list.
                name = file_path_split.pop()

            # Join the resulting items into a folder path
            folder_path = "\\".join(file_path_split)

            h_size = human_size(size, config.sections["ui"]["file_size_unit"])
            h_quality, bitrate, h_length, length = FileListMessage.parse_audio_quality_length(size, file_attributes)

            if private:
                name = _("[PRIVATE]  %s") % name

            is_result_visible = self.append(
                [
                    user,
                    get_flag_icon_name(country_code),
                    h_speed,
                    h_queue,
                    folder_path,
                    get_file_type_icon_name(name),
                    name,
                    h_size,
                    h_quality,
                    h_length,
                    ulspeed,
                    inqueue,
                    size,
                    bitrate,
                    length,
                    has_free_slots,
                    SearchResultFile(file_path, file_attributes),
                    row_id
                ]
            )

            if is_result_visible:
                update_ui = True

        return update_ui

    def file_search_response(self, msg):

        user = msg.username

        if user in self.users:
            return

        self.initialized = True

        ip_address, _port = msg.addr
        country_code = (
            core.network_filter.get_country_code(ip_address)
            or core.users.countries.get(user)
        )
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

        if msg.privatelist and config.sections["searches"]["private_search_results"]:
            update_ui_private = self.add_result_list(
                msg.privatelist, user, country_code, inqueue, ulspeed, h_speed, h_queue,
                has_free_slots, private=True
            )

            if not update_ui and update_ui_private:
                update_ui = True

        if update_ui:
            # If this search wasn't initiated by us (e.g. wishlist), and the results aren't spoofed, show tab
            is_wish = (self.mode == "wishlist")

            if not self.show_page:
                self.searches.create_page(self.token, self.text)
                self.show_page = True

            tab_changed = self.searches.request_tab_changed(self.container, is_important=is_wish)

            if tab_changed and is_wish:
                self.window.update_title()

                if config.sections["notifications"]["notification_popup_wish"]:
                    core.notifications.show_search_notification(
                        str(self.token), self.text,
                        title=_("Wishlist Results Found")
                    )

        # Update number of results, even if they are all filtered
        self.update_result_counter()

    def append(self, row):

        self.all_data.append(row)

        if not self.check_filter(row):
            return False

        self.add_row_to_model(row)
        return True

    def add_row_to_model(self, row):

        (user, flag, h_speed, h_queue, folder_path, _unused, _unused, _unused, _unused,
            _unused, speed, queue, _unused, _unused, _unused, has_free_slots,
            file_data, _unused) = row

        expand_allowed = self.initialized
        expand_user = False
        expand_folder = False
        parent_iterator = None
        user_child_iterators = None
        user_folder_child_iterators = None

        if self.grouping_mode != "ungrouped":
            # Group by folder or user

            empty_int = 0
            empty_str = ""

            if user not in self.users:
                iterator = self.tree_view.add_row(
                    [
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
                        speed,
                        queue,
                        empty_int,
                        empty_int,
                        empty_int,
                        has_free_slots,
                        None,
                        self.row_id
                    ], select_row=False
                )

                if expand_allowed:
                    expand_user = self.grouping_mode == "folder_grouping" or self.expand_button.get_active()

                self.row_id += 1
                self.users[user] = (iterator, [])

            user_iterator, user_child_iterators = self.users[user]

            if self.grouping_mode == "folder_grouping":
                # Group by folder

                user_folder_path = user + folder_path

                if user_folder_path not in self.folders:
                    iterator = self.tree_view.add_row(
                        [
                            user,
                            flag,
                            h_speed,
                            h_queue,
                            folder_path,
                            empty_str,
                            empty_str,
                            empty_str,
                            empty_str,
                            empty_str,
                            speed,
                            queue,
                            empty_int,
                            empty_int,
                            empty_int,
                            has_free_slots,
                            SearchResultFile(file_data.path.rpartition("\\")[0]),
                            self.row_id
                        ], select_row=False, parent_iterator=user_iterator
                    )
                    user_child_iterators.append(iterator)
                    expand_folder = expand_allowed and self.expand_button.get_active()
                    self.row_id += 1
                    self.folders[user_folder_path] = (iterator, [])

                row = row[:]
                row[4] = ""  # Folder not visible for file row if "group by folder" is enabled

                user_folder_iterator, user_folder_child_iterators = self.folders[user_folder_path]
                parent_iterator = user_folder_iterator

            else:
                parent_iterator = user_iterator

        else:
            if user not in self.users:
                self.users[user] = (None, [])

            user_iterator, user_child_iterators = self.users[user]

        row[17] = self.row_id
        iterator = self.tree_view.add_row(row, select_row=False, parent_iterator=parent_iterator)
        self.row_id += 1

        if user_folder_child_iterators is not None:
            user_folder_child_iterators.append(iterator)
        else:
            user_child_iterators.append(iterator)

        if expand_user:
            self.tree_view.expand_row(user_iterator)

        if expand_folder:
            self.tree_view.expand_row(user_folder_iterator)

        self.num_results_visible += 1
        return iterator

    # Result Filters #

    def add_filter_history_item(self, filter_id, value):

        combobox = self.filter_comboboxes[filter_id]
        position = len(self.FILTER_PRESETS.get(filter_id, ()))

        combobox.freeze()

        if position:
            # Separator item
            if position == combobox.get_num_items():
                combobox.append("")

            position += 1

        num_items_limit = core.search.RESULT_FILTER_HISTORY_LIMIT + position

        combobox.remove_id(value)
        combobox.insert(position=position, item=value)

        while combobox.get_num_items() > num_items_limit:
            combobox.remove_pos(-1)

        combobox.unfreeze()

    def push_history(self, filter_id, value):

        if not value:
            return

        history = config.sections["searches"].get(filter_id)

        if history is None:
            # Button filters do not store history
            return

        if history and history[0] == value:
            # Most recent item selected, nothing to do
            return

        if value in history:
            history.remove(value)

        elif len(history) >= core.search.RESULT_FILTER_HISTORY_LIMIT:
            del history[-1]

        history.insert(0, value)
        config.write_configuration()

        self.searches.add_filter_history_item(filter_id, value)

    @staticmethod
    def _split_operator(condition):
        """Returns (operation, digit)"""

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
        """Check if any conditions in result_filter match value."""

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

        if self.active_filter_count <= 0:
            return True

        for filter_id, (filter_value, _h_filter_value) in self.filters.items():
            if not filter_value:
                continue

            if filter_id == "filtertype" and not self.check_file_type(filter_value, row[16].path.lower()):
                return False

            if filter_id == "filtercc" and not self.check_country(filter_value, row[1][-2:].upper()):
                return False

            if filter_id == "filterin" and not filter_value.search(row[16].path) and not filter_value.fullmatch(row[0]):
                return False

            if filter_id == "filterout" and (filter_value.search(row[16].path) or filter_value.fullmatch(row[0])):
                return False

            if filter_id == "filterslot" and row[11] > 0:
                return False

            if filter_id == "filtersize" and not self.check_digit(filter_value, row[12], file_size=True):
                return False

            if filter_id == "filterbr" and not self.check_digit(filter_value, row[13]):
                return False

            if filter_id == "filterlength" and not self.check_digit(filter_value, row[14]):
                return False

        return True

    def update_filter_counter(self, count):

        if count > 0:
            self.filters_label.set_label(_("_Result Filters [%d]") % count)
        else:
            self.filters_label.set_label(_("_Result Filters"))

        self.filters_label.set_tooltip_text(_("%d active filter(s)") % count)

    def clear_model(self, stored_results=False):

        self.initialized = False

        if stored_results:
            self.all_data.clear()
            self.num_results_found = 0
            self.max_limited = False
            self.max_limit = config.sections["searches"]["max_displayed_results"]

        self.users.clear()
        self.folders.clear()
        self.tree_view.clear()
        self.row_id = 0
        self.num_results_visible = 0

    def update_model(self):

        self.tree_view.freeze()

        for row in self.all_data:
            if self.check_filter(row):
                self.add_row_to_model(row)

        # Update number of results
        self.update_result_counter()

        self.tree_view.unfreeze()

        if self.grouping_mode != "ungrouped":
            # Group by folder or user

            if self.expand_button.get_active():
                self.tree_view.expand_all_rows()
            else:
                self.tree_view.collapse_all_rows()

                if self.grouping_mode == "folder_grouping":
                    self.tree_view.expand_root_rows()

        self.initialized = True

    def update_wish_button(self):

        if self.mode not in {"global", "wishlist"}:
            self.add_wish_button.set_visible(False)
            return

        if not core.search.is_wish(self.text):
            icon_name = "list-add-symbolic"
            label = _("Add Wi_sh")
        else:
            icon_name = "list-remove-symbolic"
            label = _("Remove Wi_sh")

        icon_args = (Gtk.IconSize.BUTTON,) if GTK_API_VERSION == 3 else ()  # pylint: disable=no-member
        self.add_wish_icon.set_from_icon_name(icon_name, *icon_args)
        self.add_wish_label.set_label(label)

    def on_add_wish(self, *_args):

        if core.search.is_wish(self.text):
            core.search.remove_wish(self.text)
        else:
            core.search.add_wish(self.text)

    def add_popup_menu_user(self, popup, user):

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

        # Multiple users, create submenus for some of them
        if len(self.selected_users) > 1:
            for user in islice(self.selected_users, 20):
                popup = UserPopupMenu(self.window.application, username=user, tab_name="search")
                self.add_popup_menu_user(popup, user)
                self.popup_menu_users.add_items((">" + user, popup))
                self.popup_menu_users.update_model()
            return

        # Single user, add items directly to "User Actions" submenu
        user = next(iter(self.selected_users), None)
        self.popup_menu_users.setup_user_menu(user)
        self.add_popup_menu_user(self.popup_menu_users, user)

    def on_close_filter_bar_accelerator(self, *_args):
        """Escape - hide filter bar."""

        self.filters_button.set_active(False)
        return True

    def on_show_filter_bar_accelerator(self, *_args):
        """Ctrl+F - show filter bar."""

        self.filters_button.set_active(True)
        self.filter_include_combobox.grab_focus()
        return True

    def on_file_properties_accelerator(self, *_args):
        """Alt+Return - show file properties dialog."""

        self.select_results()
        self.on_file_properties()
        return True

    def on_select_user_results(self, _action, _parameter, selected_user):

        if not self.selected_users:
            return

        _user_iterator, user_child_iterators = self.users[selected_user]

        self.tree_view.unselect_all_rows()

        for iterator in user_child_iterators:
            if self.tree_view.get_row_value(iterator, "filename"):
                self.tree_view.select_row(iterator, should_scroll=False)
                continue

            user_folder_path = selected_user + self.tree_view.get_row_value(iterator, "folder")
            user_folder_data = self.folders.get(user_folder_path)

            if not user_folder_data:
                continue

            _user_folder_iter, user_folder_child_iterators = user_folder_data

            for i_iterator in user_folder_child_iterators:
                self.tree_view.select_row(i_iterator, should_scroll=False)

    def select_result(self, iterator):

        user = self.tree_view.get_row_value(iterator, "user")

        if user not in self.selected_users:
            self.selected_users[user] = None

        if self.tree_view.get_row_value(iterator, "filename"):
            row_id = self.tree_view.get_row_value(iterator, "id_data")

            if row_id not in self.selected_results:
                self.selected_results[row_id] = iterator

            return

        self.select_child_results(iterator, user)

    def select_child_results(self, iterator, user):

        folder_path = self.tree_view.get_row_value(iterator, "folder")

        if folder_path:
            user_folder_path = user + folder_path
            row_data = self.folders[user_folder_path]
        else:
            row_data = self.users[user]

        _row_iter, child_transfers = row_data

        for i_iterator in child_transfers:
            self.select_result(i_iterator)

    def select_results(self):

        self.selected_results.clear()
        self.selected_users.clear()

        for iterator in self.tree_view.get_selected_rows():
            self.select_result(iterator)

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
        else:
            str_plus = ""
            tooltip_text = _("Results")

            if self.results_button.get_tooltip_text() != tooltip_text:
                self.results_button.set_tooltip_text(tooltip_text)

        self.results_label.set_text(humanize(self.num_results_visible) + str_plus)

    def on_file_path_tooltip(self, treeview, iterator):

        file_data = treeview.get_row_value(iterator, "file_data")

        if not file_data:
            return None

        return file_data.path

    def on_row_activated(self, treeview, iterator, _column):

        self.select_results()

        folder_path = treeview.get_row_value(iterator, "folder")
        basename = treeview.get_row_value(iterator, "filename")

        if not folder_path and not basename:
            # Don't activate user rows
            return

        if not basename:
            self.on_download_folders()
        else:
            self.on_download_files()

        treeview.unselect_all_rows()

    def on_popup_menu(self, menu, _widget):

        self.select_results()
        self.populate_popup_menu_users()
        menu.set_num_selected_files(len(self.selected_results))

    def on_browse_folder(self, *_args):

        iterator = next(iter(self.selected_results.values()), None)

        if iterator is None:
            return

        user = self.tree_view.get_row_value(iterator, "user")
        path = self.tree_view.get_row_value(iterator, "file_data").path

        core.userbrowse.browse_user(user, path=path)

    def on_user_profile(self, *_args):

        iterator = next(iter(self.selected_results.values()), None)

        if iterator is None:
            return

        user = self.tree_view.get_row_value(iterator, "user")
        core.userinfo.show_user(user)

    def on_file_properties(self, *_args):

        data = []
        selected_size = 0
        selected_length = 0

        for iterator in self.selected_results.values():
            file_data = self.tree_view.get_row_value(iterator, "file_data")
            file_path = file_data.path
            file_size = self.tree_view.get_row_value(iterator, "size_data")
            selected_size += file_size
            selected_length += self.tree_view.get_row_value(iterator, "length_data")
            country_code = self.tree_view.get_row_value(iterator, "country")[-2:].upper()
            folder_path, _separator, basename = file_path.rpartition("\\")

            data.append({
                "user": self.tree_view.get_row_value(iterator, "user"),
                "file_path": file_path,
                "basename": basename,
                "virtual_folder_path": folder_path,
                "size": file_size,
                "speed": self.tree_view.get_row_value(iterator, "speed_data"),
                "queue_position": self.tree_view.get_row_value(iterator, "in_queue_data"),
                "file_attributes": file_data.attributes,
                "country_code": country_code
            })

        if data:
            if self.searches.file_properties is None:
                self.searches.file_properties = FileProperties(self.window.application)

            self.searches.file_properties.update_properties(data, selected_size, selected_length)
            self.searches.file_properties.present()

    def on_download_files(self, *_args, download_folder_path=None):

        for iterator in self.selected_results.values():
            user = self.tree_view.get_row_value(iterator, "user")
            file_data = self.tree_view.get_row_value(iterator, "file_data")
            file_path = file_data.path
            size = self.tree_view.get_row_value(iterator, "size_data")

            core.downloads.enqueue_download(
                user, file_path, folder_path=download_folder_path, size=size,
                file_attributes=file_data.attributes)

    def on_download_files_to_selected(self, selected_folder_paths, _data):
        self.on_download_files(download_folder_path=next(iter(selected_folder_paths), None))

    def on_download_files_to(self, *_args):

        FolderChooser(
            parent=self.window,
            title=_("Select Destination Folder for File(s)"),
            callback=self.on_download_files_to_selected,
            initial_folder=core.downloads.get_default_download_folder()
        ).present()

    def on_download_folders(self, *_args, download_folder_path=None):

        requested_folders = set()

        for iterator in self.selected_results.values():
            user = self.tree_view.get_row_value(iterator, "user")
            folder_path = self.tree_view.get_row_value(iterator, "file_data").path.rpartition("\\")[0]
            user_folder_key = user + folder_path

            if user_folder_key in requested_folders:
                # Ensure we don't send folder content requests for a folder more than once,
                # e.g. when several selected results belong to the same folder
                continue

            visible_files = []
            for row in self.all_data:
                # Find the wanted folder
                if folder_path != row[16].path.rpartition("\\")[0]:
                    continue

                (_unused, _unused, _unused, _unused, _unused, _unused, _unused, _unused, _unused,
                    _unused, _unused, _unused, size, _unused, _unused, _unused, file_data,
                    _unused) = row

                visible_files.append((file_data.path, size, file_data.attributes))

            core.search.request_folder_download(
                user, folder_path, visible_files, download_folder_path=download_folder_path
            )
            requested_folders.add(user_folder_key)

    def on_download_folders_to_selected(self, selected_folder_paths, _data):
        self.on_download_folders(download_folder_path=next(iter(selected_folder_paths), None))

    def on_download_folders_to(self, *_args):

        FolderChooser(
            parent=self.window,
            title=_("Select Destination Folder"),
            callback=self.on_download_folders_to_selected,
            initial_folder=core.downloads.get_default_download_folder()
        ).present()

    def on_copy_file_path(self, *_args):

        iterator = next(iter(self.selected_results.values()), None)

        if iterator is None:
            return

        file_path = self.tree_view.get_row_value(iterator, "file_data").path
        clipboard.copy_text(file_path)

    def on_copy_url(self, *_args):

        iterator = next(iter(self.selected_results.values()), None)

        if iterator is None:
            return

        user = self.tree_view.get_row_value(iterator, "user")
        file_path = self.tree_view.get_row_value(iterator, "file_data").path
        url = core.userbrowse.get_soulseek_url(user, file_path)
        clipboard.copy_text(url)

    def on_copy_folder_url(self, *_args):

        iterator = next(iter(self.selected_results.values()), None)

        if iterator is None:
            return

        user = self.tree_view.get_row_value(iterator, "user")
        file_path = self.tree_view.get_row_value(iterator, "file_data").path
        folder_path, separator, _basename = file_path.rpartition("\\")
        url = core.userbrowse.get_soulseek_url(user, folder_path + separator)

        clipboard.copy_text(url)

    def on_counter_button(self, *_args):

        if self.num_results_found > self.num_results_visible:
            self.on_clear_undo_filters()
        else:
            self.window.application.lookup_action("configure-searches").activate()

    def on_group(self, action, state):

        mode = state.get_string()
        active = mode != "ungrouped"
        popover = self.grouping_button.get_popover()

        if popover is not None:
            popover.set_visible(False)

        if GTK_API_VERSION >= 4:
            self.grouping_button.set_has_frame(active)
        else:
            self.grouping_button.set_relief(
                Gtk.ReliefStyle.NORMAL if active else Gtk.ReliefStyle.NONE
            )

        config.sections["searches"]["group_searches"] = mode
        self.tree_view.set_show_expanders(active)
        self.expand_button.set_visible(active)

        self.grouping_mode = mode

        self.clear_model()
        self.tree_view.has_tree = active
        self.tree_view.create_model()
        self.update_model()

        action.set_state(state)

    def on_toggle_expand_all(self, *_args):

        active = self.expand_button.get_active()

        if active:
            icon_name = "view-restore-symbolic"
            self.tree_view.expand_all_rows()
        else:
            icon_name = "view-fullscreen-symbolic"
            self.tree_view.collapse_all_rows()

            if self.grouping_mode == "folder_grouping":
                self.tree_view.expand_root_rows()

        icon_args = (Gtk.IconSize.BUTTON,) if GTK_API_VERSION == 3 else ()  # pylint: disable=no-member
        self.expand_icon.set_from_icon_name(icon_name, *icon_args)

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
        clipboard.copy_text(self.text)

    def on_edit_search(self, *_args):

        if self.mode == "wishlist":
            self.window.application.lookup_action("wishlist").activate()
            return

        self.window.lookup_action("search-mode").change_state(GLib.Variant.new_string(self.mode))

        if self.mode == "room":
            self.window.room_search_entry.set_text(self.room)

        elif self.mode == "user":
            self.window.user_search_entry.set_text(self.searched_users[0])

        self.window.search_entry.set_text(self.text)
        self.window.search_entry.set_position(-1)
        self.window.search_entry.grab_focus_without_selecting()

    def on_refilter(self, *_args):

        if self.populating_filters:
            return

        self.refiltering = True

        filter_in = filter_out = filter_size = filter_bitrate = filter_country = filter_file_type = filter_length = None
        filter_in_str = self.filter_include_combobox.get_text().strip()
        filter_out_str = self.filter_exclude_combobox.get_text().strip()
        filter_size_str = self.filter_file_size_combobox.get_text().strip()
        filter_bitrate_str = self.filter_bitrate_combobox.get_text().strip()
        filter_country_str = self.filter_country_combobox.get_text().strip()
        filter_file_type_str = self.filter_file_type_combobox.get_text().strip()
        filter_length_str = self.filter_length_combobox.get_text().strip()
        filter_free_slot = self.filter_free_slot_button.get_active()

        # Include/exclude text
        error_entries = set()

        if filter_in_str:
            try:
                filter_in = re.compile(filter_in_str, flags=re.IGNORECASE)
            except re.error:
                error_entries.add(self.filter_include_entry)

        if filter_out_str:
            try:
                filter_out = re.compile(filter_out_str, flags=re.IGNORECASE)
            except re.error:
                error_entries.add(self.filter_exclude_entry)

        for entry in (self.filter_include_entry, self.filter_exclude_entry):
            # Set red background if invalid regex pattern is detected
            css_class_function = add_css_class if entry in error_entries else remove_css_class
            css_class_function(entry, "error")

        # Split at | pipes ampersands & space(s) but don't split <>=! math operators spaced before digit condition
        seperator_pattern = self.FILTER_SPLIT_DIGIT_PATTERN

        if filter_size_str:
            filter_size = seperator_pattern.split(filter_size_str)

        if filter_bitrate_str:
            filter_bitrate = seperator_pattern.split(filter_bitrate_str)

        if filter_length_str:
            filter_length = seperator_pattern.split(filter_length_str)

        # Split at commas, in addition to | pipes ampersands & space(s) but don't split ! not operator before condition
        seperator_pattern = self.FILTER_SPLIT_TEXT_PATTERN

        if filter_country_str:
            filter_country = seperator_pattern.split(filter_country_str.upper())

        if filter_file_type_str:
            filter_file_type = seperator_pattern.split(filter_file_type_str.lower())

            # Replace generic file type filters with real file extensions
            for filter_name, file_extensions in self.FILTER_GENERIC_FILE_TYPES:
                excluded_filter_name = f"!{filter_name}"

                if filter_name in filter_file_type:
                    filter_file_type.remove(filter_name)
                    filter_file_type += list(file_extensions)

                elif excluded_filter_name in filter_file_type:
                    filter_file_type.remove(excluded_filter_name)
                    filter_file_type += ["!" + x for x in file_extensions]

        filters = {
            "filterin": (filter_in, filter_in_str),
            "filterout": (filter_out, filter_out_str),
            "filtersize": (filter_size, filter_size_str),
            "filterbr": (filter_bitrate, filter_bitrate_str),
            "filterslot": (filter_free_slot, filter_free_slot),
            "filtercc": (filter_country, filter_country_str),
            "filtertype": (filter_file_type, filter_file_type_str),
            "filterlength": (filter_length, filter_length_str),
        }

        if self.filters == filters:
            # Filters have not changed, no need to refilter
            self.refiltering = False
            return

        if self.filters and filters == self.FILTERS_EMPTY:
            # Filters cleared, enable Restore Filters
            self.filters_undo = self.filters
        else:
            # Filters active, enable Clear Filters
            self.filters_undo = self.FILTERS_EMPTY

        self.active_filter_count = 0

        # Add filters to history
        for filter_id, (_value, h_value) in filters.items():
            if not h_value:
                continue

            self.push_history(filter_id, h_value)
            self.active_filter_count += 1

        # Apply the new filters
        self.filters = filters
        self.update_filter_widgets()
        self.clear_model()
        self.update_model()

        self.refiltering = False

    def on_filter_entry_deleted_text(self, buffer, *_args):
        if not self.refiltering and buffer.get_length() <= 0:
            self.on_refilter()

    def on_filter_entry_icon_press(self, entry, *_args):

        entry_text = entry.get_text()
        filter_id = entry.filter_id
        _filter_value, h_filter_value = self.filters.get(filter_id)

        if not entry_text:
            # Recall last filter
            history = config.sections["searches"].get(filter_id)
            recall_text = history[0] if history else ""

            entry.set_text(recall_text)
            entry.set_position(-1)
            entry.grab_focus_without_selecting()

        elif entry_text == h_filter_value:
            # Clear Filter
            entry.set_text("")
            return

        # Activate new, edited or recalled filter
        self.on_refilter()

    def on_clear_undo_filters(self, *_args):

        self.set_filters(self.filters_undo)

        if not self.filters_button.get_active():
            self.tree_view.grab_focus()

    def on_clear(self, *_args):

        self.clear_model(stored_results=True)

        # Allow parsing search result messages again
        core.search.add_allowed_token(self.token)

        # Update number of results widget
        self.update_result_counter()

    def on_focus(self, *_args):

        if not self.window.search_entry.get_text():
            # Only focus treeview if we're not entering a new search term
            self.tree_view.grab_focus()

        return True

    def on_close(self, *_args):
        core.search.remove_search(self.token)

    def on_close_all_tabs(self, *_args):
        self.searches.remove_all_pages()
