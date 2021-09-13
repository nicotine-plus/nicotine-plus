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
from pynicotine.gtkgui.widgets.dialogs import option_dialog
from pynicotine.gtkgui.widgets.theme import update_widget_visuals
from pynicotine.gtkgui.widgets.treeview import initialise_columns
from pynicotine.gtkgui.widgets.ui import UserInterface
from pynicotine.logfacility import log


class WishList(UserInterface):

    def __init__(self, frame, searches):

        super().__init__("ui/popovers/wishlist.ui")

        self.disconnected = False
        self.frame = frame
        self.interval = 0
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

        if Gtk.get_major_version() == 4:
            button = frame.WishList.get_first_child()
            button.connect("clicked", self.on_show)
            button.set_child(frame.WishListLabel)
        else:
            frame.WishList.add(frame.WishListLabel)
            frame.WishList.connect("clicked", self.on_show)

        frame.WishList.set_popover(self.popover)

    def cell_edited_callback(self, widget, index, value, treeview, pos):

        store = treeview.get_model()
        iterator = store.get_iter(index)
        old_value = store.get_value(iterator, 0)

        if value and not value.isspace():
            self.remove_wish(old_value)
            self.add_wish(value)

    def on_add_wish(self, *args):

        wish = self.wish_entry.get_text()
        self.wish_entry.set_text("")

        self.add_wish(wish)

    def on_remove_wish(self, *args):

        model, paths = self.list_view.get_selection().get_selected_rows()

        for path in reversed(paths):
            iterator = model.get_iter(path)
            wish = model.get_value(iterator, 0)
            self.remove_wish(wish)

    def clear_wishlist_response(self, dialog, response_id, data):

        dialog.destroy()

        if response_id == Gtk.ResponseType.OK:
            for wish in self.wishes.copy():
                self.remove_wish(wish)

    def on_clear_wishlist(self, *args):

        option_dialog(
            parent=self.frame.MainWindow,
            title=_('Clear Wishlist?'),
            message=_('Are you sure you wish to clear your wishlist?'),
            callback=self.clear_wishlist_response
        )

    def add_wish(self, wish):

        search_id = self.frame.np.search.add_wish(wish)

        if not search_id:
            return None

        if wish not in self.wishes:
            self.wishes[wish] = self.store.insert_with_valuesv(-1, self.column_numbers, [wish])

        self.searches.searches[search_id] = {
            "id": search_id,
            "term": wish,
            "tab": None,
            "mode": "wishlist",
            "remember": True,
            "ignore": True
        }

    def remove_wish(self, wish):

        if wish in self.wishes:
            self.store.remove(self.wishes[wish])
            del self.wishes[wish]

        if wish in config.sections["server"]["autosearch"]:

            config.sections["server"]["autosearch"].remove(wish)

            for number, search in self.searches.searches.items():

                if search["term"] == wish and search["remember"]:

                    if search["tab"] is not None and search["tab"].showtab:  # Tab visible
                        search["remember"] = False
                        self.searches.searches[number] = search

                    else:
                        del self.searches.searches[number]

                    break

    def set_interval(self, msg):

        self.interval = msg.seconds

        if not self.disconnected:
            # Create wishlist searches (without tabs)
            for term in config.sections["server"]["autosearch"]:
                search_id = self.frame.np.search.increment_search_id()

                self.searches.searches[search_id] = {
                    "id": search_id,
                    "term": term,
                    "tab": None,
                    "mode": "wishlist",
                    "remember": True,
                    "ignore": True
                }

        self.on_auto_search()
        self.timer = GLib.timeout_add(self.interval * 1000, self.on_auto_search)

    def on_auto_search(self, *args):

        # Wishlists supported by server?
        if self.interval == 0:
            log.add(_("The server forbid us from doing wishlist searches."))
            return False

        searches = config.sections["server"]["autosearch"]

        if not searches:
            return True

        # Search for a maximum of 1 item at each search interval
        term = searches.pop()
        searches.insert(0, term)

        for i in self.searches.searches.values():
            if i["term"] == term and i["remember"]:
                i["ignore"] = False

                self.frame.np.search.do_wishlist_search(i["id"], term)
                break

        return True

    def server_disconnect(self):

        self.disconnected = True
        self.interval = 0

        if self.timer is not None:
            GLib.source_remove(self.timer)
            self.timer = None

    def update_visuals(self):

        for widget in list(self.__dict__.values()):
            update_widget_visuals(widget)

    def on_show(self, *args):

        page = self.searches.get_nth_page(self.searches.get_current_page())

        if page is None:
            return

        text = self.searches.notebook.get_tab_label(page).get_text()

        if text in self.wishes:
            # Highlight existing wish row

            iterator = self.wishes[text]
            self.list_view.set_cursor(self.store.get_path(iterator))
            self.list_view.grab_focus()
            return

        # Pre-fill text field with search term from active search tab
        self.wish_entry.set_text(text)
        self.wish_entry.grab_focus()
