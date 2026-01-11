# SPDX-FileCopyrightText: 2020-2025 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

import time

from gi.repository import GObject

from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.gtkgui.widgets import ui
from pynicotine.gtkgui.widgets.accelerator import Accelerator
from pynicotine.gtkgui.widgets.dialogs import Dialog
from pynicotine.gtkgui.widgets.dialogs import EntryDialog
from pynicotine.gtkgui.widgets.dialogs import OptionDialog
from pynicotine.gtkgui.widgets.popupmenu import PopupMenu
from pynicotine.gtkgui.widgets.treeview import TreeView
from pynicotine.search import ResultFilterMode


class WishList(Dialog):

    FILTERED_ICON_NAME = "edit-find-replace-symbolic"

    def __init__(self, application):

        (
            self.container,
            self.list_container,
            self.search_entry
        ) = ui.load(scope=self, path="dialogs/wishlist.ui")

        super().__init__(
            parent=application.window,
            modal=False,
            content_box=self.container,
            show_callback=self.on_show,
            title=_("Wishlist"),
            width=600,
            height=600
        )
        application.add_window(self.widget)

        self.application = application
        self.list_view = TreeView(
            application.window, parent=self.list_container, multi_select=True, activate_row_callback=self.on_edit_wish,
            delete_accelerator_callback=self.on_remove_wish,
            search_entry=self.search_entry,
            columns={
                "enabled": {
                    "column_type": "toggle",
                    "title": _("Enabled"),
                    "width": 0,
                    "toggle_callback": self.on_toggle_wish,
                    "hide_header": True
                },
                "wish": {
                    "column_type": "text",
                    "title": _("Search Term"),
                    "width": 200,
                    "expand_column": True,
                    "iterator_key": True,
                    "default_sort_type": "ascending"
                },
                "filtered": {
                    "column_type": "icon",
                    "title": _("Filtered"),
                    "width": 25,
                    "hide_header": True
                },
                "added": {
                    "column_type": "text",
                    "title": _("Added"),
                    "width": 0,
                    "sort_column": "added_data",
                    "tabular": True
                },

                # Hidden data columns
                "added_data": {"data_type": GObject.TYPE_UINT64}
            }
        )
        self.default_text = ""

        self.list_view.freeze()

        for search_item in core.search.wishlist.values():
            self.add_wish(search_item.term, select=False)

        self.list_view.unfreeze()

        self.popup_menu = PopupMenu(application, self.list_view.widget)
        self.popup_menu.add_items(
            ("#" + _("_Edit…"), self.on_edit_wish),
            ("#" + _("Update _Filters…"), self.on_update_filters),
            ("#" + _("_Search for Item"), self.on_search_wish),
            ("", None),
            ("#" + _("Reset Seen Results"), self.on_reset_seen_results),
            ("#" + _("Remove"), self.on_remove_wish)
        )

        Accelerator("<Primary>f", self.widget, self.on_search_accelerator)
        Accelerator("Down", self.search_entry, self.on_focus_list_view_accelerator)

        for event_name, callback in (
            ("add-wish", self.add_wish),
            ("clear-wish-filters", self.clear_wish_filters),
            ("remove-wish", self.remove_wish),
            ("update-wish-filters", self.update_wish_filters)
        ):
            events.connect(event_name, callback)

    def destroy(self):

        self.popup_menu.destroy()
        self.list_view.destroy()

        super().destroy()

    def add_wish(self, wish, select=True):

        search = core.search.wishlist[wish]

        self.list_view.add_row([
            search.auto_search,
            wish,
            self.FILTERED_ICON_NAME if search.filter_mode != ResultFilterMode.NONE else "",
            time.strftime("%x", time.localtime(search.time_added)),
            search.time_added
        ], select_row=select)

    def remove_wish(self, wish):

        iterator = self.list_view.iterators.get(wish)

        if iterator is not None:
            self.list_view.remove_row(iterator)

    def update_wish_filters(self, wish):

        iterator = self.list_view.iterators.get(wish)

        if iterator is not None:
            self.list_view.set_row_value(iterator, "filtered", self.FILTERED_ICON_NAME)

    def clear_wish_filters(self, wish):

        iterator = self.list_view.iterators.get(wish)

        if iterator is not None:
            self.list_view.set_row_value(iterator, "filtered", "")

    def select_wish(self, wish):

        iterator = self.list_view.iterators.get(wish)

        if iterator is not None:
            self.list_view.select_row(iterator)

    def on_toggle_wish(self, list_view, iterator):

        enabled = not list_view.get_row_value(iterator, "enabled")
        wish = list_view.get_row_value(iterator, "wish")
        search = core.search.wishlist.get(wish)

        list_view.set_row_value(iterator, "enabled", enabled)

        if search is not None:
            search.auto_search = enabled

    def on_add_wish_response(self, dialog, _response_id, _data):

        wishes = dialog.get_entry_value().split("\n")
        auto_search = dialog.get_option_value()
        is_first_item = True

        for wish in wishes:
            wish = wish.strip()

            if not wish:
                continue

            core.search.add_wish(wish, auto_search=auto_search)

            if not is_first_item:
                continue

            self.select_wish(wish)
            is_first_item = False

    def on_add_wish(self, *_args):

        EntryDialog(
            parent=self,
            title=_("Add Wishes"),
            message=_("Enter a list of search terms to add to the wishlist:"),
            default=self.default_text,
            action_button_label=_("_Add"),
            option_value=True,
            option_label=_("Enable automatic search"),
            multiline=True,
            callback=self.on_add_wish_response
        ).present()

    def on_edit_wish_response(self, dialog, _response_id, old_wish):

        wish = dialog.get_entry_value().strip()
        enable_filters = (dialog.get_second_entry_value() == _("Custom filters"))
        auto_search = dialog.get_option_value()

        if not wish:
            return

        old_filters = None

        if wish != old_wish:
            old_search = core.search.wishlist[old_wish]
            old_filters = old_search.custom_filters

            core.search.remove_wish(old_wish)
            core.search.add_wish(wish)

        iterator = self.list_view.iterators[wish]
        search = core.search.wishlist[wish]

        search.auto_search = auto_search
        search.filter_mode = ResultFilterMode.CUSTOM if enable_filters else ResultFilterMode.NONE

        if old_filters:
            search.custom_filters = old_filters

        self.list_view.set_row_value(iterator, "enabled", auto_search)
        self.list_view.set_row_value(iterator, "filtered", self.FILTERED_ICON_NAME if enable_filters else "")

        self.select_wish(wish)

    def on_edit_wish(self, *_args):

        _reserved = _("Default filters")

        for iterator in self.list_view.get_selected_rows():
            old_enabled = self.list_view.get_row_value(iterator, "enabled")
            old_wish = self.list_view.get_row_value(iterator, "wish")
            filtered = bool(self.list_view.get_row_value(iterator, "filtered"))

            EntryDialog(
                parent=self,
                title=_("Edit Wish"),
                message=_("Modify the search term '%s':") % old_wish,
                default=old_wish,
                second_default=_("Custom filters") if filtered else _("No filters"),
                second_droplist=[_("No filters"), _("Custom filters")],
                use_second_entry=True,
                second_entry_editable=False,
                action_button_label=_("_Edit"),
                option_value=old_enabled,
                option_label=_("Enable automatic search"),
                callback=self.on_edit_wish_response,
                callback_data=old_wish
            ).present()
            return

    def on_update_filters(self, *_args):

        for iterator in self.list_view.get_selected_rows():
            wish = self.list_view.get_row_value(iterator, "wish")
            search = core.search.wishlist.get(wish)
            old_filter_mode = ResultFilterMode.NONE
            old_filters_visible = config.sections["searches"]["filters_visible"]

            if search is not None:
                old_filter_mode = search.filter_mode
                search.filter_mode = ResultFilterMode.CUSTOM

            config.sections["searches"]["filters_visible"] = True
            core.search.do_search(wish, mode="wishlist")

            if search is not None:
                search.filter_mode = old_filter_mode

            config.sections["searches"]["filters_visible"] = old_filters_visible
            self.close()
            return

    def on_search_wish(self, *_args):

        for iterator in self.list_view.get_selected_rows():
            wish = self.list_view.get_row_value(iterator, "wish")
            core.search.do_search(wish, mode="wishlist")
            return

    def on_reset_seen_results(self, *_args):

        for iterator in self.list_view.get_selected_rows():
            wish = self.list_view.get_row_value(iterator, "wish")
            search = core.search.wishlist.get(wish)

            if search is not None:
                search.ignored_users.clear()

    def on_remove_wish(self, *_args):

        for iterator in reversed(list(self.list_view.get_selected_rows())):
            wish = self.list_view.get_row_value(iterator, "wish")
            core.search.remove_wish(wish)

        return True

    def clear_wishlist_response(self, *_args):
        for wish in self.list_view.iterators.copy():
            core.search.remove_wish(wish)

    def on_clear_wishlist(self, *_args):

        OptionDialog(
            parent=self,
            title=_("Clear Wishlist?"),
            message=_("Do you really want to clear your wishlist?"),
            buttons=[
                ("cancel", _("_Cancel")),
                ("ok", _("Clear All"))
            ],
            destructive_response_id="ok",
            callback=self.clear_wishlist_response
        ).present()

    def on_search_entry_changed(self, *_args):
        self.default_text = self.search_entry.get_text()

    def on_search_list(self, *_args):

        if self.list_view.get_num_selected_rows() > 0:
            self.list_view.grab_focus()
            return

        self.on_add_wish()

    def on_search_accelerator(self, *_args):
        """Ctrl+F - Search wish terms."""

        self.search_entry.grab_focus()
        return True

    def on_focus_list_view_accelerator(self, *_args):
        """Down - Focus list view."""

        self.list_view.grab_focus()
        return True

    def on_show(self, *_args):

        self.search_entry.grab_focus()

        page = self.application.window.search.get_current_page()

        if page is None:
            return

        self.default_text = ""

        for tab in self.application.window.search.pages.values():
            if tab is not None and tab.container == page:
                self.default_text = tab.text
                break

        iterator = self.list_view.iterators.get(self.default_text)

        if iterator is not None:
            # Highlight existing wish row
            self.list_view.select_row(iterator)
        else:
            self.list_view.unselect_all_rows()

        self.search_entry.set_text(self.default_text)
        self.search_entry.select_region(0, -1)
