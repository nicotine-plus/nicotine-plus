# COPYRIGHT (C) 2020-2022 Nicotine+ Contributors
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

from pynicotine.config import config
from pynicotine.gtkgui.widgets.accelerator import Accelerator
from pynicotine.gtkgui.widgets.dialogs import Dialog
from pynicotine.gtkgui.widgets.dialogs import EntryDialog
from pynicotine.gtkgui.widgets.dialogs import OptionDialog
from pynicotine.gtkgui.widgets.textentry import CompletionEntry
from pynicotine.gtkgui.widgets.theme import update_widget_visuals
from pynicotine.gtkgui.widgets.treeview import TreeView
from pynicotine.gtkgui.widgets.ui import UserInterface


class WishList(Dialog):

    def __init__(self, frame, core, searches):

        self.core = core
        self.searches = searches

        ui_template = UserInterface(scope=self, path="dialogs/wishlist.ui")
        (
            self.container,
            self.list_container,
            self.wish_entry
        ) = ui_template.widgets

        super().__init__(
            parent=frame.window,
            modal=False,
            content_box=self.container,
            show_callback=self.on_show,
            title=_("Wishlist"),
            width=600,
            height=600,
            close_destroy=False
        )

        self.list_view = TreeView(
            frame, parent=self.list_container, multi_select=True, activate_row_callback=self.on_edit_wish,
            columns=[
                {"column_id": "wish", "column_type": "text", "title": _("Wish"), "sort_column": 0,
                 "default_sort_column": "ascending"}
            ]
        )

        for wish in config.sections["server"]["autosearch"]:
            wish = str(wish)
            self.list_view.add_row([wish], select_row=False)

        CompletionEntry(self.wish_entry, self.list_view.model)

        Accelerator("Delete", self.list_view.widget, self.on_remove_wish)
        Accelerator("<Shift>Tab", self.list_view.widget, self.on_list_focus_entry_accelerator)  # skip column header

    def on_list_focus_entry_accelerator(self, *_args):
        self.wish_entry.grab_focus()
        return True

    def on_add_wish(self, *_args):

        wish = self.wish_entry.get_text().strip()

        if not wish:
            return

        wish_exists = (wish in self.list_view.iterators)
        self.wish_entry.set_text("")

        self.core.search.add_wish(wish)

        if not wish_exists:
            return

        self.select_wish(wish)

    def on_edit_wish_response(self, dialog, _response_id, old_wish):

        wish = dialog.get_entry_value().strip()

        if not wish:
            return

        self.core.search.remove_wish(old_wish)
        self.core.search.add_wish(wish)
        self.select_wish(wish)

    def on_edit_wish(self, *_args):

        for iterator in self.list_view.get_selected_rows():
            old_wish = self.list_view.get_row_value(iterator, 0)

            EntryDialog(
                parent=self.dialog,
                title=_("Edit Wish"),
                message=_("Enter new value for wish '%s':") % old_wish,
                default=old_wish,
                callback=self.on_edit_wish_response,
                callback_data=old_wish
            ).show()
            return

    def on_remove_wish(self, *_args):

        for iterator in reversed(self.list_view.get_selected_rows()):
            wish = self.list_view.get_row_value(iterator, 0)
            self.core.search.remove_wish(wish)

        self.wish_entry.grab_focus()
        return True

    def clear_wishlist_response(self, _dialog, response_id, _data):

        if response_id == 2:
            for wish in self.list_view.iterators.copy():
                self.core.search.remove_wish(wish)

        self.wish_entry.grab_focus()

    def on_clear_wishlist(self, *_args):

        OptionDialog(
            parent=self.dialog,
            title=_('Clear Wishlist?'),
            message=_('Do you really want to clear your wishlist?'),
            callback=self.clear_wishlist_response
        ).show()

    def add_wish(self, wish):

        if wish not in self.list_view.iterators:
            self.list_view.add_row([wish])

        self.update_wish_button(wish)

    def remove_wish(self, wish):

        iterator = self.list_view.iterators.get(wish)

        if iterator is not None:
            self.list_view.remove_row(iterator)

        self.update_wish_button(wish)

    def select_wish(self, wish):

        iterator = self.list_view.iterators.get(wish)

        if iterator is not None:
            self.list_view.select_row(iterator)

    def set_interval(self, msg):
        # Not used
        pass

    def update_wish_button(self, wish):

        for page in self.searches.pages.values():
            if page.text == wish:
                page.update_wish_button()

    def update_visuals(self):

        for widget in self.__dict__.values():
            update_widget_visuals(widget)

    def on_show(self, *_args):

        page = self.searches.get_current_page()

        if page is None:
            return

        text = None

        for tab in self.searches.pages.values():
            if tab is not None and tab.container == page:
                text = tab.text
                break

        if not text:
            self.list_view.unselect_all_rows()
            return

        iterator = self.list_view.iterators.get(text)

        if iterator is not None:
            # Highlight existing wish row

            self.list_view.select_row(iterator)
            self.wish_entry.set_text("")
            return

        # Pre-fill text field with search term from active search tab
        self.list_view.unselect_all_rows()
        self.wish_entry.set_text(text)
        self.wish_entry.grab_focus()
