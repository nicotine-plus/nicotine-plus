# COPYRIGHT (C) 2020 Nicotine+ Team
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

import os

from gettext import gettext as _

from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk

from pynicotine import slskmessages
from pynicotine.gtkgui.utils import initialise_columns
from pynicotine.gtkgui.utils import load_ui_elements
from pynicotine.gtkgui.utils import update_widget_visuals
from pynicotine.logfacility import log


class WishList:

    def __init__(self, frame, searches):

        self.disconnected = False
        self.frame = frame
        self.interval = 0
        self.searches = searches
        self.timer = None
        self.wishes = {}

        load_ui_elements(self, os.path.join(self.frame.gui_dir, "ui", "wishlist.ui"))

        self.WishListDialog.set_transient_for(frame.MainWindow)

        self.WishListDialog.connect("destroy", self.quit)
        self.WishListDialog.connect("destroy-event", self.quit)
        self.WishListDialog.connect("delete-event", self.quit)
        self.WishListDialog.connect("delete_event", self.quit)

        self.store = Gtk.ListStore(GObject.TYPE_STRING)

        cols = initialise_columns(
            self.WishlistView,
            [_("Wishes"), -1, "text"]
        )

        self.WishlistView.set_model(self.store)
        self.WishlistView.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)

        self.store.set_sort_column_id(0, Gtk.SortType.ASCENDING)

        for wish in self.frame.np.config.sections["server"]["autosearch"]:
            self.wishes[wish] = self.store.append([wish])

        renderers = cols[0].get_cells()
        for render in renderers:
            render.set_property('editable', True)
            render.connect('edited', self.cell_edited_callback, self.WishlistView, 0)

        self.frame.WishList.connect("clicked", self.show)

    def cell_edited_callback(self, widget, index, value, treeview, pos):

        store = treeview.get_model()
        iterator = store.get_iter(index)
        old_value = store.get_value(iterator, 0)

        if value != "" and not value.isspace():
            self.remove_wish(old_value)
            self.add_wish(value)

    def on_add_wish(self, widget):

        wish = self.AddWishEntry.get_text()
        self.AddWishEntry.set_text("")

        if self.add_wish(wish):
            self.do_wishlist_search(self.searches.searchid, wish)

    def on_remove_wish(self, widget):

        iters = []
        self.WishlistView.get_selection().selected_foreach(self._remove_wish, iters)

        for iterator in iters:
            wish = self.store.get_value(iterator, 0)
            self.remove_wish(wish)

    def _remove_wish(self, model, path, iterator, line):
        line.append(iterator)

    def on_select_all_wishes(self, widget):
        self.WishlistView.get_selection().select_all()

    def add_wish(self, wish):

        if not wish:
            return False

        if wish not in self.wishes:
            self.wishes[wish] = self.store.append([wish])

        self.searches.searchid += 1
        self.searches.searches[self.searches.searchid] = [self.searches.searchid, wish, None, 0, True, False]

        if wish not in self.frame.np.config.sections["server"]["autosearch"]:
            self.frame.np.config.sections["server"]["autosearch"].append(wish)

        return True

    def remove_wish(self, wish):

        if wish in self.wishes:
            self.store.remove(self.wishes[wish])
            del self.wishes[wish]

        if wish in self.frame.np.config.sections["server"]["autosearch"]:

            self.frame.np.config.sections["server"]["autosearch"].remove(wish)

            for number, search in self.searches.searches.items():

                if search[1] == wish and search[4]:

                    if search[2] is not None and search[2].showtab:  # Tab visible
                        search[4] = False
                        self.searches.searches[number] = search

                        search[2].RememberCheckButton.set_active(False)
                    else:
                        del self.searches.searches[number]

                    break

    def set_interval(self, msg):

        self.interval = msg.seconds

        if not self.disconnected:
            # Create wishlist searches (without tabs)
            for term in self.frame.np.config.sections["server"]["autosearch"]:
                self.searches.searches[self.searches.searchid] = [self.searches.searchid, term, None, 0, True, False]
                self.searches.searchid = (self.searches.searchid + 1) % (2**31)

        self.on_auto_search()
        self.timer = GLib.timeout_add(self.interval * 1000, self.on_auto_search)

    def do_wishlist_search(self, id, text):
        self.frame.np.queue.put(slskmessages.WishlistSearch(id, text))

    def on_auto_search(self, *args):

        # Wishlists supported by server?
        if self.interval == 0:
            log.add_warning(_("The server forbid us from doing wishlist searches."))
            return False

        searches = self.frame.np.config.sections["server"]["autosearch"]

        if not searches:
            return True

        # Search for a maximum of 1 item at each search interval
        term = searches.pop()
        searches.insert(0, term)

        for i in self.searches.searches.values():
            if i[1] == term and i[4]:
                self.do_wishlist_search(i[0], term)
                break

        return True

    def conn_close(self):
        self.disconnected = True

        if self.timer is not None:
            GLib.source_remove(self.timer)
            self.timer = None

    def update_visuals(self):

        for widget in self.__dict__.values():
            update_widget_visuals(widget)

    def show(self, widget):
        self.WishListDialog.show()

    def quit(self, widget, event):
        self.WishListDialog.hide()
        return True
