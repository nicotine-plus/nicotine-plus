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

from gi.repository import GLib
from gi.repository import Gtk

from pynicotine.config import config
from pynicotine.gtkgui.utils import setup_accelerator
from pynicotine.gtkgui.widgets.dialogs import option_dialog
from pynicotine.gtkgui.widgets.textentry import CompletionEntry
from pynicotine.gtkgui.widgets.theme import update_widget_visuals
from pynicotine.gtkgui.widgets.treeview import initialise_columns
from pynicotine.gtkgui.widgets.ui import UserInterface


class WishList(UserInterface):

    def __init__(self, frame, searches):

        super().__init__("ui/popovers/wishlist.ui")

        self.frame = frame
        self.searches = searches
        self.timer = None
        self.wishes = {}

        self.store = Gtk.ListStore(str)

        self.column_numbers = list(range(self.store.get_n_columns()))
        cols = initialise_columns(
            None, self.list_view,
            ["wishes", _("Wishes"), -1, "text", None]
        )

        self.list_view.set_model(self.store)

        self.store.set_sort_column_id(0, Gtk.SortType.ASCENDING)

        for wish in config.sections["server"]["autosearch"]:
            wish = str(wish)
            self.wishes[wish] = self.store.insert_with_valuesv(-1, self.column_numbers, [wish])

        renderers = cols["wishes"].get_cells()
        for render in renderers:
            render.set_property('editable', True)
            render.connect('edited', self.cell_edited_callback, self.list_view, 0)

        CompletionEntry(self.wish_entry, self.store)

        setup_accelerator("<Shift>Delete", self.main, self.on_remove_wish_accelerator)
        setup_accelerator("<Shift>Delete", self.wish_entry, self.on_remove_wish_accelerator)
        setup_accelerator("<Shift>Tab", self.list_view, self.on_list_focus_entry_accelerator)  # skip column header

        if Gtk.get_major_version() == 4:
            button = frame.WishList.get_first_child()
            button.connect("clicked", self.on_show)
            button.set_child(frame.WishListLabel)
            button.get_style_context().add_class("image-text-button")
            button.get_style_context().remove_class("image-button")
        else:
            frame.WishList.add(frame.WishListLabel)
            frame.WishList.connect("clicked", self.on_show)

        frame.WishList.set_popover(self.popover)

    def cell_edited_callback(self, widget, index, value, treeview, pos):

        store = treeview.get_model()
        iterator = store.get_iter(index)
        old_value = store.get_value(iterator, 0)

        if value and not value.isspace():
            self.frame.np.search.remove_wish(old_value)
            self.frame.np.search.add_wish(value)
            self.select_wish(value)

    def on_add_wish(self, *args):

        wish = self.wish_entry.get_text()
        wish_exists = (wish in self.wishes)
        self.wish_entry.set_text("")

        self.frame.np.search.add_wish(wish)

        if not wish_exists:
            return

        self.select_wish(wish)

    def on_remove_wish(self, *args):

        model, paths = self.list_view.get_selection().get_selected_rows()

        for path in reversed(paths):
            iterator = model.get_iter(path)
            wish = model.get_value(iterator, 0)
            self.frame.np.search.remove_wish(wish)

        self.list_view.get_selection().unselect_all()
        self.wish_entry.grab_focus()

    def on_remove_wish_accelerator(self, *args):
        """ Shift+Delete: Remove Wish """

        self.on_remove_wish()
        return True

    def clear_wishlist_response(self, dialog, response_id, data):

        dialog.destroy()

        if response_id == Gtk.ResponseType.OK:
            for wish in self.wishes.copy():
                self.frame.np.search.remove_wish(wish)

        self.wish_entry.grab_focus()

    def on_clear_wishlist(self, *args):

        option_dialog(
            parent=self.frame.MainWindow,
            title=_('Clear Wishlist?'),
            message=_('Do you really want to clear your wishlist?'),
            callback=self.clear_wishlist_response
        )

    def add_wish(self, wish):

        if wish not in self.wishes:
            self.wishes[wish] = self.store.insert_with_valuesv(-1, self.column_numbers, [wish])

        self.update_wish_button(wish)

    def remove_wish(self, wish):

        if wish in self.wishes:
            self.store.remove(self.wishes[wish])
            del self.wishes[wish]

        self.update_wish_button(wish)

    def select_wish(self, wish):

        wish_iterator = self.wishes.get(wish)
        if wish_iterator is None:
            return

        self.list_view.set_cursor(self.store.get_path(wish_iterator))
        self.list_view.grab_focus()

    def set_interval(self, msg):
        self.frame.np.search.do_wishlist_search_interval()
        self.timer = GLib.timeout_add(msg.seconds * 1000, self.frame.np.search.do_wishlist_search_interval)

    def server_disconnect(self):

        if self.timer is not None:
            GLib.source_remove(self.timer)
            self.timer = None

    def update_wish_button(self, wish):

        for page in self.searches.pages.values():
            if page.text == wish:
                page.update_wish_button()

    def update_visuals(self):

        for widget in list(self.__dict__.values()):
            update_widget_visuals(widget)

    def on_list_focus_entry_accelerator(self, *args):
        self.wish_entry.grab_focus()
        return True

    def on_show(self, *args):

        page = self.searches.get_nth_page(self.searches.get_current_page())

        if page is None:
            return

        text = None

        for tab in self.searches.pages.values():
            if tab is not None and tab.Main == page:
                text = tab.text
                break

        if not text:
            self.list_view.get_selection().unselect_all()
            return

        if text in self.wishes:
            # Highlight existing wish row

            iterator = self.wishes[text]
            self.list_view.set_cursor(self.store.get_path(iterator))
            self.wish_entry.set_text("")
            self.list_view.grab_focus()
            return

        # Pre-fill text field with search term from active search tab
        self.list_view.get_selection().unselect_all()
        self.wish_entry.set_text(text)
        self.wish_entry.grab_focus()
