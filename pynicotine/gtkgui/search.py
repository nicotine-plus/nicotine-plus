# -*- coding: utf-8 -*-
#
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

import locale
import os
import random
import re
import sre_constants
from gettext import gettext as _

import gi
from gi.repository import Gdk
from gi.repository import GObject as gobject
from gi.repository import Gtk as gtk

import _thread
from pynicotine import slskmessages
from pynicotine.gtkgui.dirchooser import ChooseDir
from pynicotine.gtkgui.entrydialog import MetaDialog
from pynicotine.gtkgui.utils import Humanize
from pynicotine.gtkgui.utils import HumanSize
from pynicotine.gtkgui.utils import HumanSpeed
from pynicotine.gtkgui.utils import IconNotebook
from pynicotine.gtkgui.utils import InitialiseColumns
from pynicotine.gtkgui.utils import InputDialog
from pynicotine.gtkgui.utils import PopupMenu
from pynicotine.gtkgui.utils import PressHeader
from pynicotine.gtkgui.utils import showCountryTooltip
from pynicotine.logfacility import log
from pynicotine.utils import cmp

gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')


class WishList(gtk.Dialog):

    def __init__(self, frame):

        gtk.Dialog.__init__(self)

        self.set_title(_("Nicotine+ Wishlist"))
        self.set_icon(frame.images["n"])
        self.connect("destroy", self.quit)
        self.connect("destroy-event", self.quit)
        self.connect("delete-event", self.quit)
        self.connect("delete_event", self.quit)

        self.nicotine = frame
        self.set_size_request(600, 600)
        self.mainHbox = gtk.HBox(False, 5)
        self.mainHbox.show()

        self.WishLabel = gtk.Label(_("Search Wishlist"))
        self.WishLabel.set_padding(0, 0)
        self.WishLabel.set_line_wrap(False)
        self.WishLabel.show()
        self.vbox.pack_start(self.WishLabel, False, True, 0)

        self.WishScrollWin = gtk.ScrolledWindow()
        self.WishScrollWin.set_policy(gtk.PolicyType.AUTOMATIC, gtk.PolicyType.AUTOMATIC)
        self.WishScrollWin.show()
        self.WishScrollWin.set_shadow_type(gtk.ShadowType.IN)

        self.WishlistView = gtk.TreeView()
        self.WishlistView.show()
        self.WishlistView.set_headers_visible(False)
        self.WishScrollWin.add(self.WishlistView)

        self.mainHbox.pack_start(self.WishScrollWin, True, True, 0)
        self.mainVbox = gtk.VBox(False, 5)
        self.mainHbox.pack_start(self.mainVbox, False, False, 0)
        self.mainVbox.show()
        self.mainVbox.set_spacing(5)

        self.AddWishButton = self.nicotine.CreateIconButton(gtk.STOCK_ADD, "stock", self.OnAddWish, _("Add..."))
        self.mainVbox.pack_start(self.AddWishButton, False, False, 0)

        self.RemoveWishButton = self.nicotine.CreateIconButton(gtk.STOCK_REMOVE, "stock", self.OnRemoveWish, _("Remove"))
        self.mainVbox.pack_start(self.RemoveWishButton, False, False, 0)

        self.SelectAllWishesButton = self.nicotine.CreateIconButton(gtk.STOCK_DND_MULTIPLE, "stock", self.OnSelectAllWishes, _("Select all"))
        self.mainVbox.pack_start(self.SelectAllWishesButton, False, False, 0)

        self.CloseButton = self.nicotine.CreateIconButton(gtk.STOCK_CLOSE, "stock", self.quit, _("Close"))
        self.mainVbox.pack_end(self.CloseButton, False, False, 0)

        self.vbox.pack_start(self.mainHbox, True, True, 0)

        self.store = gtk.ListStore(gobject.TYPE_STRING)

        column = gtk.TreeViewColumn(_("Wishes"), gtk.CellRendererText(), text=0)
        self.WishlistView.append_column(column)
        self.WishlistView.set_model(self.store)
        self.WishlistView.get_selection().set_mode(gtk.SelectionMode.MULTIPLE)

        column.set_sort_column_id(0)
        self.store.set_sort_column_id(0, gtk.SortType.ASCENDING)
        self.wishes = {}

        for wish in self.nicotine.np.config.sections["server"]["autosearch"]:
            self.wishes[wish] = self.store.append([wish])

    def OnAddWish(self, widget):

        wish = InputDialog(self.vbox.get_toplevel(), _("Add Wish..."), _("Wish:"))

        if wish and wish not in self.wishes:
            self.wishes[wish] = self.store.append([wish])
            self.nicotine.Searches.NewWish(wish)

    def _RemoveWish(self, model, path, iter, l):
        l.append(iter)

    def removeWish(self, wish):

        if wish in self.wishes:
            self.store.remove(self.wishes[wish])
            del self.wishes[wish]

        if wish in self.nicotine.np.config.sections["server"]["autosearch"]:

            self.nicotine.np.config.sections["server"]["autosearch"].remove(wish)

            for number, search in list(self.nicotine.Searches.searches.items()):

                if search[1] == wish and search[4] == 1:

                    search[4] = 0
                    self.nicotine.Searches.searches[number] = search

                    if search[2] is not None:
                        search[2].RememberCheckButton.set_active(False)

                    break

    def addWish(self, wish):
        if wish and wish not in self.wishes:
            self.wishes[wish] = self.store.append([wish])

    def OnRemoveWish(self, widget):

        iters = []
        self.WishlistView.get_selection().selected_foreach(self._RemoveWish, iters)

        for iter in iters:
            wish = self.store.get_value(iter, 0)
            self.removeWish(wish)

    def OnSelectAllWishes(self, widget):
        self.WishlistView.get_selection().select_all()

    def quit(self, w=None, event=None):
        self.hide()
        return True

    def Toggle(self, widget):

        if self.get_property("visible"):
            self.hide()
        else:
            self.show()


class Searches(IconNotebook):

    def __init__(self, frame):

        self.frame = frame

        self.interval = 0
        self.searchid = int(random.random() * (2 ** 31 - 1))
        self.searches = {}
        self.usersearches = {}
        self.users = {}
        self.timer = None
        self.disconnected = 0

        ui = self.frame.np.config.sections["ui"]

        IconNotebook.__init__(
            self,
            self.frame.images,
            angle=ui["labelsearch"],
            tabclosers=ui["tabclosers"],
            show_image=ui["tab_icons"],
            reorderable=ui["tab_reorderable"],
            notebookraw=self.frame.SearchNotebookRaw
        )

        self.popup_enable()

        self.WishListDialog = WishList(frame)

        self.UpdateColours()

    def LoadConfig(self):
        """
        Add search history to SearchEntryCombo later and connect Wishlist,
        after widgets have been created.
        """
        items = self.frame.np.config.sections["searches"]["history"]
        templist = []

        for i in items:
            if i not in templist:
                templist.append(i)

        for i in templist:
            self.frame.SearchEntryCombo_List.append([i])

        self.frame.WishList.connect("clicked", self.WishListDialog.Toggle)

    def SetInterval(self, msg):

        self.interval = msg.seconds

        if not self.disconnected:
            # Create wishlist searches (without tabs)
            for term in self.frame.np.config.sections["server"]["autosearch"]:
                self.searches[self.searchid] = [self.searchid, term, None, 0, True]
                self.searchid = (self.searchid + 1) % (2**31)

        self.OnAutoSearch()
        self.timer = gobject.timeout_add(self.interval * 1000, self.OnAutoSearch)

    def ConnClose(self):

        self.disconnected = 1

        if self.timer is not None:
            gobject.source_remove(self.timer)
            self.timer = None

    def OnAutoSearch(self, *args):

        # Wishlists supported by server?
        if self.interval == 0:
            log.addwarning("The server forbid us from doing wishlist searches.")
            return False

        searches = self.frame.np.config.sections["server"]["autosearch"]
        if not searches:
            return True

        # Search for a maximum of 3 items at each search interval
        for term in searches[0:3]:
            for i in list(self.searches.values()):
                if i[1] == term and i[4]:
                    self.DoWishListSearch(i[0], term)
                    oldsearch = searches.pop()
                    searches.insert(0, oldsearch)

        return True

    def OnClearSearchHistory(self):

        self.frame.SearchEntry.set_text("")
        self.frame.np.config.sections["searches"]["history"] = []
        self.frame.np.config.writeConfiguration()
        self.frame.SearchEntryCombo.get_model().clear()
        self.frame.SearchEntryCombo_List.append([""])

    def OnSearch(self):
        self.saveColumns()
        text = self.frame.SearchEntry.get_text().strip()

        if not text:
            return

        users = []
        room = None
        search_mode = self.frame.SearchMethod.get_model().get(self.frame.SearchMethod.get_active_iter(), 0)[0]

        if search_mode == _("Global"):
            mode = 0
        elif search_mode == _("Rooms"):
            mode = 1
            name = self.frame.RoomSearchCombo.get_child().get_text()
            # Space after Joined Rooms is important, so it doesn't conflict
            # with any possible real room
            if name != _("Joined Rooms ") and not name.isspace():
                room = name
        elif search_mode == _("Buddies"):
            mode = 2
        elif search_mode == _("User"):
            mode = 3
            user = self.frame.UserSearchCombo.get_child().get_text().strip()
            if user != "" and not user.isspace():
                users = [user]
            else:
                return
        else:
            mode = 0

        feedback = None

        if mode == 0:
            feedback = self.frame.pluginhandler.OutgoingGlobalSearchEvent(text)
            if feedback is not None:
                text = feedback[0]
        elif mode == 1:
            feedback = self.frame.pluginhandler.OutgoingRoomSearchEvent(room, text)
            if feedback is not None:
                (room, text) = feedback
        elif mode == 2:
            feedback = self.frame.pluginhandler.OutgoingBuddySearchEvent(text)
            if feedback is not None:
                text = feedback[0]
        elif mode == 3:
            feedback = self.frame.pluginhandler.OutgoingUserSearchEvent(users)
            if feedback is not None:
                users = feedback[0]
        else:
            print("Unknown search mode, not using plugin system. Fix me!")
            feedback = True

        if feedback is not None:
            self.DoSearch(text, mode, users, room)
            self.frame.SearchEntry.set_text("")

    def NewWish(self, wish):

        if wish in self.frame.np.config.sections["server"]["autosearch"]:
            return

        self.frame.np.config.sections["server"]["autosearch"].append(wish)

        self.searchid += 1
        self.searches[self.searchid] = [self.searchid, wish, None, 0, True]

        self.DoWishListSearch(self.searchid, wish)

    def DoSearch(self, text, mode, users=[], room=None):

        items = self.frame.np.config.sections["searches"]["history"]

        if text in items:
            items.remove(text)

        items.insert(0, text)

        # Clear old items
        del items[15:]
        self.frame.np.config.writeConfiguration()

        # Repopulate the combo list
        self.frame.SearchEntryCombo.get_model().clear()
        templist = []

        for i in items:
            if i not in templist:
                templist.append(i)

        for i in templist:
            self.frame.SearchEntryCombo_List.append([i])

        if mode == 3 and users != [] and users[0] != '':
            self.usersearches[self.searchid] = users

        search = self.CreateTab(self.searchid, text, mode)
        if search[2] is not None:
            self.set_current_page(self.page_num(search[2].Main))

        # text = self.frame.np.encode(text)
        if mode == 0:
            self.DoGlobalSearch(self.searchid, text)
        elif mode == 1:
            self.DoRoomsSearch(self.searchid, text, room)
        elif mode == 2:
            self.DoBuddiesSearch(self.searchid, text)
        elif mode == 3 and users != [] and users[0] != '':
            self.DoPeerSearch(self.searchid, text, users)

        self.searchid += 1

    def DoGlobalSearch(self, id, text):
        self.frame.np.queue.put(slskmessages.FileSearch(id, text))

    def DoWishListSearch(self, id, text):
        self.frame.np.queue.put(slskmessages.WishlistSearch(id, text))

    def DoRoomsSearch(self, id, text, room=None):
        if room is not None:
            self.frame.np.queue.put(slskmessages.RoomSearch(room, id, text))
        else:
            for room in list(self.frame.chatrooms.roomsctrl.joinedrooms.keys()):
                self.frame.np.queue.put(slskmessages.RoomSearch(room, id, text))

    def DoBuddiesSearch(self, id, text):
        for users in self.frame.userlist.userlist:
            self.frame.np.queue.put(slskmessages.UserSearch(users[0], id, text))

    def DoPeerSearch(self, id, text, users):
        for user in users:
            self.frame.np.ProcessRequestToPeer(user, slskmessages.FileSearchRequest(None, id, text))

    def GetUserSearchName(self, id):

        if id in self.usersearches:

            users = self.usersearches[id]

            if len(users) > 1:
                return _("Users")
            elif len(users) == 1:
                return users[0]

        return _("User")

    def CreateTab(self, id, text, mode, remember=False):

        tab = Search(self, text, id, mode, remember)

        if mode:
            label = "(" + ("", _("Rooms"), _("Buddies"), self.GetUserSearchName(id))[mode] + ") " + text[:15]
        else:
            label = text[:20]

        self.append_page(tab.Main, label, tab.OnClose)

        search = [id, text, tab, mode, remember]
        self.searches[id] = search

        return search

    def ShowResult(self, msg, username, country):

        if msg.token not in self.searches:
            return

        search = self.searches[msg.token]
        if search[2] is None:
            search = self.CreateTab(search[0], search[1], search[3], search[4])

        search[2].AddResult(msg, username, country)

    def RemoveAutoSearch(self, id):

        if id not in self.searches:
            return

        search = self.searches[id]
        if search[1] in self.frame.np.config.sections["server"]["autosearch"]:
            self.frame.np.config.sections["server"]["autosearch"].remove(search[1])
            self.frame.np.config.writeConfiguration()

        search[4] = 0
        self.WishListDialog.removeWish(search[1])

    def RemoveTab(self, tab):

        if tab.id in self.searches:
            search = self.searches[tab.id]
            search[2] = None

        if self.is_tab_detached(tab.Main):
            tab.Main.get_parent_window().destroy()
        else:
            self.remove_page(tab.Main)
            tab.Main.destroy()

    def AutoSearch(self, id):

        if id not in self.searches:
            return

        i = self.searches[id]
        if i[1] in self.frame.np.config.sections["server"]["autosearch"]:
            return

        self.frame.np.config.sections["server"]["autosearch"].append(i[1])
        self.frame.np.config.writeConfiguration()
        i[4] = 1
        self.WishListDialog.addWish(i[1])

    def UpdateColours(self):

        for id in list(self.searches.values()):
            if id[2] is None:
                continue
            id[2].ChangeColours()

        self.frame.SetTextBG(self.WishListDialog.WishlistView)

    def saveColumns(self):

        page_num = self.get_current_page()

        if page_num is not None:

            page = self.get_nth_page(page_num)

            for name, search in list(self.searches.items()):

                if search[2] is None:
                    continue
                if search[2].Main == page:
                    search[2].saveColumns()
                    break

    def GetUserStatus(self, msg):

        for number, search in list(self.searches.items()):

            if search[2] is None:
                continue

            search[2].GetUserStatus(msg)

    def NonExistantUser(self, user):

        for number, search in list(self.searches.items()):

            if search[2] is None:
                continue

            search[2].NonExistantUser(user)

    def TabPopup(self, id):

        popup = PopupMenu(self.frame)
        popup.setup(
            ("#" + _("Detach this tab"), self.searches[id][2].Detach),
            ("#" + _("Close this tab"), self.searches[id][2].OnClose)
        )
        items = popup.get_children()  # noqa: F841

        return popup

    def on_tab_click(self, widget, event, child):

        if event.type == Gdk.EventType.BUTTON_PRESS:

            id = None
            n = self.page_num(child)
            page = self.get_nth_page(n)

            for search, data in list(self.searches.items()):

                if data[2] is None:
                    continue
                if data[2].Main is page:
                    id = search
                    break

            if id is None:
                print("ID is none")
                return

            if event.button == 2:
                self.searches[id][2].OnClose(widget)
                return True

            if event.button == 3:
                menu = self.TabPopup(id)
                menu.popup(None, None, None, None, event.button, event.time)
                return True

        return False


class Search:

    def __init__(self, Searches, text, id, mode, remember):

        self.Searches = Searches
        self.frame = Searches.frame

        # Build the window
        builder = gtk.Builder()

        builder.set_translation_domain('nicotine')
        builder.add_from_file(os.path.join(os.path.dirname(os.path.realpath(__file__)), "ui", "search.ui"))

        self.SearchTab = builder.get_object("SearchTab")

        for i in builder.get_objects():
            try:
                self.__dict__[gtk.Buildable.get_name(i)] = i
            except TypeError:
                pass

        self.SearchTab.remove(self.Main)
        self.SearchTab.destroy()

        builder.connect_signals(self)

        self.FilterBitrate_List = gtk.ListStore(gobject.TYPE_STRING)
        self.FilterBitrate.set_model(self.FilterBitrate_List)
        self.FilterBitrate.set_entry_text_column(0)

        self.FilterSize_List = gtk.ListStore(gobject.TYPE_STRING)
        self.FilterSize.set_model(self.FilterSize_List)
        self.FilterSize.set_entry_text_column(0)

        self.FilterCountry_List = gtk.ListStore(gobject.TYPE_STRING)
        self.FilterCountry.set_model(self.FilterCountry_List)
        self.FilterCountry.set_entry_text_column(0)

        self.FilterIn_List = gtk.ListStore(gobject.TYPE_STRING)
        self.FilterIn.set_model(self.FilterIn_List)
        self.FilterIn.set_entry_text_column(0)

        self.FilterOut_List = gtk.ListStore(gobject.TYPE_STRING)
        self.FilterOut.set_model(self.FilterOut_List)
        self.FilterOut.set_entry_text_column(0)

        self.text = text
        self.id = id
        self.mode = mode
        self.remember = remember
        self.usersiters = {}
        self.users = []
        self.resultslimit = 2000
        self.QueryLabel.set_text(text)

        self.all_data = []
        self.filters = None
        self.COLUMN_TYPES = [
            int,  # num
            str,  # user
            str,  # filename
            str,  # h_size
            str,  # h_speed
            str,  # h_queue
            str,  # immediatedl
            str,  # h_bitrate
            str,  # length
            gobject.TYPE_OBJECT,  # self.get_flag(user, country)
            str,  # directory
            int,  # bitrate
            str,  # fullpath
            str,  # country
            gobject.TYPE_UINT64,  # size
            int,  # speed
            int,  # queue
            int   # status
        ]

        self.resultsmodel = gtk.TreeStore(* self.COLUMN_TYPES)

        if mode > 0:
            self.RememberCheckButton.set_sensitive(False)

        self.RememberCheckButton.set_active(remember)

        self.PopulateFilters()

        self.FilterSize.clear()
        sizecell = gtk.CellRendererText()
        sizecell.set_property("xalign", 1)
        self.FilterSize.pack_start(sizecell, True)
        self.FilterSize.add_attribute(sizecell, "text", 0)

        self.FilterBitrate.clear()
        bit_cell = gtk.CellRendererText()
        bit_cell.set_property("xalign", 1)
        self.FilterBitrate.pack_start(bit_cell, True)
        self.FilterBitrate.add_attribute(bit_cell, "text", 0)

        self.FilterIn.connect("changed", self.OnFilterChanged)
        self.FilterOut.connect("changed", self.OnFilterChanged)
        self.FilterSize.connect("changed", self.OnFilterChanged)
        self.FilterBitrate.connect("changed", self.OnFilterChanged)
        self.FilterCountry.connect("changed", self.OnFilterChanged)

        self.FilterIn.get_child().connect("activate", self.OnRefilter)
        self.FilterOut.get_child().connect("activate", self.OnRefilter)
        self.FilterSize.get_child().connect("activate", self.OnRefilter)
        self.FilterBitrate.get_child().connect("activate", self.OnRefilter)
        self.FilterCountry.get_child().connect("activate", self.OnRefilter)

        self.selected_results = []
        self.selected_users = []

        self.ResultsList.get_selection().set_mode(gtk.SelectionMode.MULTIPLE)
        self.ResultsList.set_property("show-expanders", False)
        self.ResultsList.set_property("rules-hint", True)
        widths = self.frame.np.config.sections["columns"]["search_widths"]
        cols = InitialiseColumns(
            self.ResultsList,
            [_("Number"), widths[0], "text", self.CellDataFunc],
            [_("User"), widths[1], "text", self.CellDataFunc],
            [_("Filename"), widths[2], "text", self.CellDataFunc],
            [_("Size"), widths[3], "text", self.CellDataFunc],
            [_("Speed"), widths[4], "text", self.CellDataFunc],
            [_("In queue"), widths[5], "text", self.CellDataFunc],
            [_("Immediate Download"), widths[6], "text", self.CellDataFunc],
            [_("Bitrate"), widths[7], "text", self.CellDataFunc],
            [_("Length"), widths[8], "text", self.CellDataFunc],
            [_("Country"), widths[9], "pixbuf"],
            [_("Directory"), widths[10], "text", self.CellDataFunc]
        )

        self.col_num, self.col_user, self.col_file, self.col_size, self.col_speed, self.col_queue, self.col_immediate, self.col_bitrate, self.col_length, self.col_country, self.col_directory = cols
        cols[0].get_widget().hide()

        for i in range(10):

            parent = cols[i].get_widget().get_ancestor(gtk.Button)
            if parent:
                parent.connect('button_press_event', PressHeader)

            # Read Show / Hide column settings from last session
            cols[i].set_visible(self.frame.np.config.sections["columns"]["search"][i])

        self.ResultsList.set_model(self.resultsmodel)

        self.col_num.set_sort_column_id(0)
        self.col_user.set_sort_column_id(1)
        self.col_file.set_sort_column_id(2)
        self.col_size.set_sort_column_id(14)
        self.col_speed.set_sort_column_id(15)
        self.col_queue.set_sort_column_id(16)
        self.col_immediate.set_sort_column_id(6)
        self.col_bitrate.set_sort_column_id(11)
        self.col_length.set_sort_column_id(8)
        self.col_country.set_sort_column_id(13)
        self.col_directory.set_sort_column_id(10)

        self.ResultsList.set_enable_tree_lines(True)
        self.ResultsList.set_headers_clickable(True)

        self.popup_menu_users = PopupMenu(self.frame)
        self.popup_menu = popup = PopupMenu(self.frame)
        popup.setup(
            ("#" + _("_Download file(s)"), self.OnDownloadFiles),
            ("#" + _("Download file(s) _to..."), self.OnDownloadFilesTo),
            ("#" + _("Download containing _folder(s)"), self.OnDownloadFolders),
            ("#" + _("Download containing f_older(s) to..."), self.OnDownloadFoldersTo),
            ("#" + _("View Metadata of file(s)"), self.OnSearchMeta),
            ("", None),
            ("#" + _("Copy _URL"), self.OnCopyURL),
            ("#" + _("Copy folder U_RL"), self.OnCopyDirURL),
            ("", None),
            (1, _("User(s)"), self.popup_menu_users, self.OnPopupMenuUsers)
        )

        self.ResultsList.connect("button_press_event", self.OnListClicked)

        self.ChangeColours()

    def OnTooltip(self, widget, x, y, keyboard_mode, tooltip):
        return showCountryTooltip(widget, x, y, tooltip, 13, stripprefix='')

    def OnFilterChanged(self, widget):

        model = widget.get_model()  # noqa: F841
        iter = widget.get_active_iter()

        if iter:
            self.OnRefilter(None)

    def PopulateFilters(self):

        if self.frame.np.config.sections["searches"]["enablefilters"]:

            filter = self.frame.np.config.sections["searches"]["defilter"]

            self.FilterIn.get_child().set_text(filter[0])
            self.FilterOut.get_child().set_text(filter[1])
            self.FilterSize.get_child().set_text(filter[2])
            self.FilterBitrate.get_child().set_text(filter[3])
            self.FilterFreeSlot.set_active(filter[4])

            if(len(filter) > 5):
                self.FilterCountry.get_child().set_text(filter[5])

            self.filtersCheck.set_active(1)

        for i in ['0', '128', '160', '192', '256', '320']:
            self.FilterBitrate.get_model().append([i])

        for i in [">10MiB", "<10MiB", "<5MiB", "<1MiB", ">0"]:
            self.FilterSize.get_model().append([i])

        s_config = self.frame.np.config.sections["searches"]

        for i in s_config["filterin"]:
            self.AddCombo(self.FilterIn, i, True)

        for i in s_config["filterout"]:
            self.AddCombo(self.FilterOut, i, True)

        for i in s_config["filtersize"]:
            self.AddCombo(self.FilterSize, i, True)

        for i in s_config["filterbr"]:
            self.AddCombo(self.FilterBitrate, i, True)

        for i in s_config["filtercc"]:
            self.AddCombo(self.FilterCountry, i, True)

    def AddCombo(self, Combobox, text, list=False):

        text = text.strip()
        if not text:
            return False

        model = Combobox.get_model()
        iter = model.get_iter_first()
        match = False

        while iter is not None:

            value = model.get_value(iter, 0)

            if value.strip() == text:
                match = True

            iter = model.iter_next(iter)

        if not match:
            if list:
                model.append([text])
            else:
                model.prepend([text])

    def Attach(self, widget=None):
        self.Searches.attach_tab(self.Main)

    def Detach(self, widget=None):
        self.Searches.detach_tab(
            self.Main,
            _("Nicotine+ %(mode)s Search: %(term)s") % {
                'mode': [_("Global"), _("Rooms"), _("Buddies"), self.Searches.GetUserSearchName(self.id)][self.mode],
                'term': self.text
            }
        )

    def AddResult(self, msg, user, country):

        if user in self.users:
            return

        if user not in self.Searches.users:

            if user in self.frame.np.users and self.frame.np.users[user].status is not None:
                self.Searches.users[user] = self.frame.np.users[user].status
            else:
                self.Searches.users[user] = 0
                self.frame.np.queue.put(slskmessages.AddUser(user))

            if user == self.frame.np.config.sections["server"]["login"]:
                self.Searches.users[user] = 1

        self.users.append(user)

        results = []

        if msg.freeulslots:
            imdl = "Y"
        else:
            imdl = "N"

        decode = self.frame.np.decode  # noqa: F841

        for result in msg.list:

            name = result[1].split('\\')[-1]
            dir = result[1][:-len(name)]

            bitrate = ""
            length = ""

            br = 0

            # If there are 3 entries in the last column
            if len(result[4]) == 3:

                a = result[4]

                # Sometimes the vbr indicator is in third position
                if a[2] == 0 or a[2] == 1:

                    if a[2] == 1:
                        bitrate = " (vbr)"

                    bitrate = str(a[0]) + bitrate
                    br = a[0]

                    length = '%i:%02i' % (a[1] / 60, a[1] % 60)

                # Sometimes the vbr indicator is in second position
                elif a[1] == 0 or a[1] == 1:

                    if a[1] == 1:
                        bitrate = " (vbr)"

                    bitrate = str(a[0]) + bitrate
                    br = a[0]

                    length = '%i:%02i' % (a[2] / 60, a[2] % 60)

                # But one thing for sure the bitrate is always on first position
                else:

                    bitrate = str(a[0]) + bitrate
                    br = a[0]

            # If there are 2 entries in the last column
            elif len(result[4]) == 2:

                a = result[4]

                # Sometimes the vbr indicator is in second position
                if a[1] == 0 or a[1] == 1:

                    # If it's a vbr file we can't deduce the length
                    if a[1] == 1:

                        bitrate = " (vbr)"
                        bitrate = str(a[0]) + bitrate
                        br = a[0]

                    # If it's a constant bitrate we can deduce the length
                    else:

                        bitrate = str(a[0]) + bitrate
                        br = a[0]

                        # Dividing the file size by the bitrate in Bytes should give us a good enough approximation
                        l = result[2] / (br / 8 * 1000)  # noqa: E741

                        length = '%i:%02i' % (l / 60, l % 60)

                # Sometimes the bitrate is in first position and the length in second position
                else:

                    bitrate = str(a[0]) + bitrate
                    br = a[0]

                    length = '%i:%02i' % (a[1] / 60, a[1] % 60)

            results.append([user, name, result[2], msg.ulspeed, msg.inqueue, imdl, bitrate, length, dir, br, result[1], country, self.Searches.users[user]])

        if results:

            # Start a thread to display the user results
            _thread.start_new_thread(self._realaddresults, (results, ))

    def _realaddresults(self, results):

        counter = len(self.all_data) + 1

        # No more things to add because we've reached the max_stored_results limit
        if counter > self.frame.np.config.sections['searches']["max_stored_results"]:
            return

        # Append the data
        self.append(results)

        # Update the displayed count
        gobject.idle_add(self.CountResults)

        # Update tab notification
        self.frame.Searches.request_changed(self.Main)
        if self.frame.MainNotebook.get_current_page() != self.frame.MainNotebook.page_num(self.frame.searchvbox):
            self.frame.SearchTabLabel.get_child().set_image(self.frame.images["online"])

    def get_flag(self, user, flag=None):

        if flag is not None:
            flag = "flag_" + flag
            self.frame.flag_users[user] = flag
        else:
            flag = self.frame.GetUserFlag(user)

        return self.frame.GetFlagImage(flag)

    def append(self, results):

        counter = len(self.all_data) + 1

        encode = self.frame.np.encodeuser

        for r in results:

            user, filename, size, speed, queue, immediatedl, h_bitrate, length, directory, bitrate, fullpath, country, status = r

            if user in self.Searches.users and status != self.Searches.users[user]:
                status = self.Searches.users[user]

            if status is None:
                status = 0

            h_size = HumanSize(int(size))
            h_speed = HumanSpeed(speed)
            h_queue = Humanize(queue)

            if self.usersGroup.get_active() and user not in self.usersiters:
                self.usersiters[user] = self.resultsmodel.append(
                    None,
                    [0, user, "", "", h_speed, h_queue, immediatedl, "", "", self.get_flag(user, country), "", 0, "", country, 0, speed, queue, status]
                )

            row = [
                counter, user, filename, h_size, h_speed, h_queue, immediatedl, h_bitrate, length,
                directory, bitrate, fullpath, country, size, speed, queue, status
            ]

            self.all_data.append(row)

            # No more things to add because we've reached the max_stored_results limit
            if counter >= self.frame.np.config.sections['searches']["max_stored_results"]:
                break

            if (counter <= self.frame.np.config.sections['searches']["max_displayed_results"]) and (not self.filters or self.check_filter(row)):

                encoded_row = [
                    counter, user, encode(filename, user), h_size, h_speed, h_queue, immediatedl, h_bitrate, length,
                    self.get_flag(user, country), encode(directory, user), bitrate, encode(fullpath, user), country, size, speed, queue, status
                ]

                gobject.idle_add(self._add_to_model, user, encoded_row)

            counter += 1

    def _add_to_model(self, user, encoded_row):

        try:
            if user in self.usersiters:
                iter = self.resultsmodel.append(self.usersiters[user], encoded_row)
            else:
                iter = self.resultsmodel.append(None, encoded_row)
        except Exception as e:
            types = []
            for i in encoded_row:
                types.append(type(i))
            print("Search row error:", e, encoded_row)
            iter = None

        path = None

        if iter is not None:
            path = self.resultsmodel.get_path(iter)

        if path is not None:
            if self.usersGroup.get_active() and self.ExpandButton.get_active():
                self.ResultsList.expand_to_path(path)

    def updateStatus(self, user, status):

        self.Searches.users[user] = status
        pos = 0

        for r in self.all_data:
            if user == r[1]:
                self.all_data[pos][16] = status
            pos += 1

        iter = self.resultsmodel.get_iter_first()

        while iter is not None:

            selected_user = self.resultsmodel.get_value(iter, 1)

            if selected_user == user:
                self.resultsmodel.set_value(iter, 17, status)

            if self.resultsmodel.iter_has_child(iter):

                child = self.resultsmodel.iter_children(iter)

                while child is not None:

                    selected_user = self.resultsmodel.get_value(child, 1)
                    if selected_user == user:
                        self.resultsmodel.set_value(child, 17, status)

                    child = self.resultsmodel.iter_next(child)

            iter = self.resultsmodel.iter_next(iter)

    def sort(self):

        col = self.sort_col
        order = self.sort_order

        if col == 3:
            col = 14
        elif col == 4:
            col = 15
        elif col == 5:
            col = 16

        if self.COLUMN_TYPES[col] == gobject.TYPE_STRING:
            compare = locale.strcoll
        else:
            compare = cmp

        if order == gtk.SortType.ASCENDING:
            self.all_data.sort(lambda r1, r2: compare(r1[col], r2[col]))
        else:
            self.all_data.sort(lambda r2, r1: compare(r1[col], r2[col]))

    def checkDigit(self, filter, value, factorize=True):

        op = ">="
        if filter[:1] in (">", "<", "="):
            op, filter = filter[:1] + "=", filter[1:]

        if not filter:
            return True

        factor = 1
        if factorize:
            base = 1024
            if filter[-1:].lower() == 'b':
                filter = filter[:-1]  # stripping off the b, we always assume it means bytes
            if filter[-1:].lower() == 'i':
                base = 1000
                filter = filter[:-1]
            if filter.lower()[-1:] == "g":
                factor = pow(base, 3)
                filter = filter[:-1]
            elif filter.lower()[-1:] == "m":
                factor = pow(base, 2)
                filter = filter[:-1]
            elif filter.lower()[-1:] == "k":
                factor = base
                filter = filter[:-1]

        if not filter:
            return True

        try:
            filter = int(filter) * factor
        except TypeError:
            return True

        if eval(str(value) + op + str(filter), {}):
            return True

        return False

    def check_filter(self, row):

        filters = self.filters
        if not self.filtersCheck.get_active():
            return True

        if filters[0] and not filters[0].search(row[2].lower()):
            return False

        if filters[1] and filters[1].search(row[2].lower()):
            return False

        if filters[2] and not self.checkDigit(filters[2], row[13]):
            return False

        if filters[3] and not self.checkDigit(filters[3], row[10], False):
            return False

        if filters[4] and row[6] != "Y":
            return False

        if filters[5]:
            for cc in filters[5]:
                if not cc:
                    continue
                if row[12] is None:
                    return False

                if cc[0] == "-":
                    if row[12].upper() == cc[1:].upper():
                        return False
                elif cc.upper() != row[12].upper():
                    return False

        return True

    def set_filters(self, enable, f_in, f_out, size, bitrate, freeslot, country):

        if self.frame.np.transfers is None:
            encode = self.frame.np.encode
        else:
            encode = self.frame.np.transfers.encode

        self.filters = [None, None, None, None, freeslot, None]

        if f_in:
            try:
                f_in = re.compile(f_in.lower())
                self.filters[0] = f_in
            except sre_constants.error:
                self.frame.SetTextBG(self.FilterIn.get_child(), "red", "white")
            else:
                self.frame.SetTextBG(self.FilterIn.get_child())

        if f_out:
            try:
                f_out = re.compile(f_out.lower())
                self.filters[1] = f_out
            except sre_constants.error:
                self.frame.SetTextBG(self.FilterOut.get_child(), "red", "white")
            else:
                self.frame.SetTextBG(self.FilterOut.get_child())

        if size:
            self.filters[2] = size

        if bitrate:
            self.filters[3] = bitrate

        if country:
            self.filters[5] = country.upper().split(" ")

        self.usersiters.clear()
        self.resultsmodel.clear()

        displaycounter = 0
        for row in self.all_data:

            if self.check_filter(row):

                ix, user, filename, h_size, h_speed, h_queue, immediatedl, h_bitrate, length, directory, bitrate, fullpath, country, size, speed, queue, status = row

                if user in self.Searches.users and status != self.Searches.users[user]:
                    status = self.Searches.users[user]

                if self.usersGroup.get_active() and user not in self.usersiters:
                    self.usersiters[user] = self.resultsmodel.append(
                        None,
                        [0, user, "", "", h_speed, h_queue, immediatedl, "", "", self.get_flag(user, country), "", 0, "", country, 0, speed, queue, status]
                    )

                encoded_row = [
                    ix, user, encode(filename, user), h_size, h_speed, h_queue, immediatedl, h_bitrate, length,
                    self.get_flag(user, country), encode(directory, user), bitrate, encode(fullpath, user), country, size, speed, queue, status
                ]

                try:
                    if user in self.usersiters:
                        iter = self.resultsmodel.append(self.usersiters[user], encoded_row)
                    else:
                        iter = self.resultsmodel.append(None, encoded_row)  # noqa: F841
                except Exception as e:
                    print("Filters: Search row error:", e)
                    for i in encoded_row:
                        print(i, type(i), end=' ')

                displaycounter += 1

            if displaycounter >= self.frame.np.config.sections['searches']["max_displayed_results"]:
                break

        self.CountResults()

    def CountResults(self):

        if self.usersGroup.get_active():

            iter_count = 0
            user_count = self.resultsmodel.iter_n_children(None)

            for i in range(user_count):
                iters = self.resultsmodel.iter_nth_child(None, i)
                iter_count += self.resultsmodel.iter_n_children(iters)

            self.Counter.set_text("Results: %d/%d" % (iter_count, len(self.all_data)))
        else:
            self.Counter.set_text("Results: %d/%d" % (self.resultsmodel.iter_n_children(None), len(self.all_data)))

    def OnPopupMenuUsers(self, widget):

        self.select_results()

        self.popup_menu_users.clear()

        if len(self.selected_users) > 0:

            items = []
            self.selected_users.sort(key=str.lower)

            for user in self.selected_users:
                popup = PopupMenu(self.frame)
                popup.setup(
                    ("#" + _("Send _message"), popup.OnSendMessage),
                    ("#" + _("Show IP a_ddress"), popup.OnShowIPaddress),
                    ("#" + _("Get user i_nfo"), popup.OnGetUserInfo),
                    ("#" + _("Brow_se files"), popup.OnBrowseUser),
                    ("#" + _("Gi_ve privileges"), popup.OnGivePrivileges),
                    ("", None),
                    ("$" + _("_Add user to list"), popup.OnAddToList),
                    ("$" + _("_Ban this user"), popup.OnBanUser),
                    ("$" + _("_Ignore this user"), popup.OnIgnoreUser),
                    ("#" + _("Select User's Results"), self.OnSelectUserResults)
                )
                popup.set_user(user)

                items.append((1, user, popup, self.OnPopupMenuUser, popup))

            self.popup_menu_users.setup(*items)

        return True

    def OnPopupMenuUser(self, widget, popup=None):

        if popup is None:
            return

        menu = popup
        user = menu.user
        items = menu.get_children()

        act = False
        if len(self.selected_users) >= 1:
            act = True

        items[0].set_sensitive(act)
        items[1].set_sensitive(act)
        items[2].set_sensitive(act)
        items[3].set_sensitive(act)

        items[6].set_active(user in [i[0] for i in self.frame.np.config.sections["server"]["userlist"]])
        items[7].set_active(user in self.frame.np.config.sections["server"]["banlist"])
        items[8].set_active(user in self.frame.np.config.sections["server"]["ignorelist"])

        for i in range(4, 9):
            items[i].set_sensitive(act)

        return True

    def OnSelectUserResults(self, widget):

        if len(self.selected_users) == 0:
            return

        selected_user = widget.parent.user

        sel = self.ResultsList.get_selection()
        fmodel = self.ResultsList.get_model()
        sel.unselect_all()
        iter = self.resultsmodel.get_iter_first()

        while iter is not None:

            user = self.resultsmodel.get_value(iter, 1)

            if selected_user == user:

                fn = self.resultsmodel.get_value(iter, 11)

                if fn == "" or self.resultsmodel.iter_has_child(iter):

                    child = self.resultsmodel.iter_children(iter)

                    while child is not None:

                        user = self.resultsmodel.get_value(child, 1)

                        if selected_user == user:
                            sel.select_path(fmodel.get_path(child),)

                        child = self.resultsmodel.iter_next(child)
                else:
                    ix = fmodel.get_path(iter)
                    sel.select_path(ix,)

            iter = self.resultsmodel.iter_next(iter)

        self.select_results()

    def select_results(self):

        self.selected_results = []
        self.selected_users = []

        self.ResultsList.get_selection().selected_foreach(self.SelectedResultsCallback)

    def ChangeColours(self):

        self.frame.SetTextBG(self.ResultsList)
        self.frame.SetTextBG(self.FilterIn.get_child())
        self.frame.SetTextBG(self.FilterOut.get_child())
        self.frame.SetTextBG(self.FilterSize.get_child())
        self.frame.SetTextBG(self.FilterBitrate.get_child())
        self.frame.SetTextBG(self.FilterCountry.get_child())
        self.frame.SetTextBG(self.RememberCheckButton)
        self.frame.SetTextBG(self.FilterFreeSlot)

        font = self.frame.np.config.sections["ui"]["searchfont"]

        self.frame.ChangeListFont(self.ResultsList, font)

    def GetUserStatus(self, msg):

        if msg.user not in self.users:
            return

        self.updateStatus(msg.user, msg.status)

    def NonExistantUser(self, user):

        if user not in self.users:
            return

        self.updateStatus(user, -1)

    def saveColumns(self):

        columns = []
        widths = []
        for column in self.ResultsList.get_columns():
            columns.append(column.get_visible())
            widths.append(column.get_width())

        self.frame.np.config.sections["columns"]["search"] = columns
        self.frame.np.config.sections["columns"]["search_widths"] = widths

    def SelectedResultsCallback(self, model, path, iter):

        num = model.get_value(iter, 0)
        user = model.get_value(iter, 1)
        fn = None

        for r in self.all_data:

            if num != r[0] or user != r[1]:
                continue

            fn = r[11]
            size = r[13]
            bitrate = r[7]
            length = r[8]
            break

        if user is None:
            return

        if user not in self.selected_users:
            self.selected_users.append(user)

        if fn is None or fn == "":
            return

        self.selected_results.append((user, fn, size, bitrate, length))

    def OnListClicked(self, widget, event):

        if event.button == 1 and event.type == Gdk.EventType._2BUTTON_PRESS:
            self.select_results()
            self.OnDownloadFiles(widget)
            self.ResultsList.get_selection().unselect_all()
            return True
        elif event.button == 3:
            return self.OnPopupMenu(widget, event)

        return False

    def OnPopupMenu(self, widget, event):

        if event.button != 3:
            return False

        self.select_results()

        items = self.popup_menu.get_children()
        users = len(self.selected_users) > 0
        files = len(self.selected_results) > 0

        for i in range(0, 5):
            items[i].set_sensitive(files)

        items[6].set_sensitive(files)
        items[7].set_sensitive(files)
        items[8].set_sensitive(users)

        widget.emit_stop_by_name("button_press_event")
        self.popup_menu.popup(None, None, None, None, event.button, event.time)

        return True

    def CellDataFunc(self, column, cellrenderer, model, iter, dummy="dummy"):

        status = model.get_value(iter, 17)
        imdl = model.get_value(iter, 6)
        color = imdl == "Y" and "search" or "searchq"
        colour = None

        if status == 0:
            colour = self.frame.np.config.sections["ui"]["searchoffline"]
            cellrenderer.set_property("background", None)
        elif status == -1:
            colour = "#ffffff"
            cellrenderer.set_property("background", "#ff0000")
        else:
            colour = self.frame.np.config.sections["ui"][color] or None
            cellrenderer.set_property("background", None)

        cellrenderer.set_property("foreground", colour)

    def MetaBox(self, title="Meta Data", message="", data=None, modal=True):

        win = MetaDialog(self.frame, message, data, modal)
        win.set_title(title)
        win.set_icon(self.frame.images["n"])
        win.show()
        gtk.main()

        return win.ret

    def SelectedResultsAllData(self, model, path, iter, data):

        num = model.get_value(iter, 0)
        filename = model.get_value(iter, 2)
        user = model.get_value(iter, 1)
        size = model.get_value(iter, 3)
        speed = model.get_value(iter, 4)
        queue = model.get_value(iter, 5)
        immediate = model.get_value(iter, 6)
        bitratestr = model.get_value(iter, 7)
        length = model.get_value(iter, 8)
        directory = model.get_value(iter, 10)
        fn = model.get_value(iter, 12)
        country = model.get_value(iter, 13)

        data[len(data)] = {
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
        }

    def OnSearchMeta(self, widget):

        if not self.frame.np.transfers:
            return

        data = {}
        self.ResultsList.get_selection().selected_foreach(self.SelectedResultsAllData, data)

        if data != {}:
            self.MetaBox(title=_("Nicotine+: Search Results"), message=_("<b>Metadata</b> for Search Query: <i>%s</i>") % self.text, data=data, modal=True)

    def OnDownloadFiles(self, widget, prefix=""):

        if not self.frame.np.transfers:
            return

        for file in self.selected_results:
            self.frame.np.transfers.getFile(file[0], file[1], prefix, size=file[2], bitrate=file[3], length=file[4])

    def OnDownloadFilesTo(self, widget):

        subdir = None
        for file in self.selected_results:
            subdir = file[1].rsplit("\\", 1)[0].rsplit("\\", 1)[1]
            break

        dir = ChooseDir(self.frame.MainWindow, self.frame.np.config.sections["transfers"]["downloaddir"], create=True, name=subdir)

        if dir is None:
            return

        for dirs in dir:
            self.OnDownloadFiles(widget, dirs)
            break

    def OnDownloadFolders(self, widget):

        folders = []

        for i in self.selected_results:

            user = i[0]
            dir = "\\".join(i[1].split("\\")[:-1])

            if (user, dir) in folders:
                continue

            self.frame.np.ProcessRequestToPeer(user, slskmessages.FolderContentsRequest(None, dir))
            folders.append((user, dir))

            if user not in self.frame.np.requestedFolders:
                continue

            if dir in self.frame.np.requestedFolders[user]:
                del self.frame.np.requestedFolders[user][dir]

    def OnDownloadFoldersTo(self, widget):

        subdir = None
        folders = []
        directories = ChooseDir(self.frame.MainWindow, self.frame.np.config.sections["transfers"]["downloaddir"], create=True, name=subdir)

        if directories is None or directories == []:
            return

        destination = directories[0]
        for i in self.selected_results:

            user = i[0]
            dir = "\\".join(i[1].split("\\")[:-1]) + "\\"

            if (user, dir) in folders:
                continue

            folders.append((user, dir))

        for tup in folders:

            user, dir = tup

            if user not in self.frame.np.requestedFolders:
                self.frame.np.requestedFolders[user] = {}

            self.frame.np.requestedFolders[user][dir] = destination
            self.frame.np.ProcessRequestToPeer(user, slskmessages.FolderContentsRequest(None, dir))

    def OnCopyURL(self, widget):
        user, path = self.selected_results[0][:2]
        self.frame.SetClipboardURL(user, path)

    def OnCopyDirURL(self, widget):

        user, path = self.selected_results[0][:2]
        path = "\\".join(path.split("\\")[:-1]) + "\\"

        if path[:-1] != "/":
            path += "/"

        self.frame.SetClipboardURL(user, path)

    def OnGroup(self, widget):

        self.OnRefilter(widget)

        self.ResultsList.set_property("show-expanders", widget.get_active())

        if widget.get_active():
            self.ResultsList.get_columns()[0].set_visible(False)
            self.ExpandButton.show()
        else:
            self.ResultsList.get_columns()[0].set_visible(True)
            self.ExpandButton.hide()

    def OnToggleExpandAll(self, widget):

        if self.ExpandButton.get_active():
            self.ResultsList.expand_all()
            self.expandImage.set_from_stock(gtk.STOCK_REMOVE, 4)
        else:
            self.ResultsList.collapse_all()
            self.expandImage.set_from_stock(gtk.STOCK_ADD, 4)

    def OnToggleFilters(self, widget):

        if widget.get_active():
            self.Filters.show()
            self.OnRefilter(None)
        else:
            self.Filters.hide()
            self.ResultsList.set_model(None)
            self.set_filters(0, None, None, None, None, None, "")
            self.ResultsList.set_model(self.resultsmodel)

        if self.usersGroup.get_active():
            if self.ExpandButton.get_active():
                self.ResultsList.expand_all()
            else:
                self.ResultsList.collapse_all()

    def OnIgnore(self, widget):

        try:
            del self.Searches.searches[self.id]
        except KeyError:
            pass

        self.Searches.WishListDialog.removeWish(self.text)
        widget.set_sensitive(False)

    def OnClear(self, widget):
        self.all_data = []
        self.usersiters.clear()
        self.resultsmodel.clear()

    def OnClose(self, widget):

        if not self.frame.np.config.sections["searches"]["reopen_tabs"]:
            if self.text not in self.frame.np.config.sections["server"]["autosearch"]:
                self.OnIgnore(widget)

        self.Searches.RemoveTab(self)

    def OnToggleRemember(self, widget):

        self.remember = widget.get_active()

        if not self.remember:
            self.Searches.RemoveAutoSearch(self.id)
        else:
            self.Searches.AutoSearch(self.id)

    def PushHistory(self, widget, title):

        text = widget.get_child().get_text()
        if not text.strip():
            return None

        text = text.strip()
        history = self.frame.np.config.sections["searches"][title]
        self.frame.np.config.pushHistory(history, text, 5)

        self.AddCombo(widget, text)
        widget.get_child().set_text(text)

        return text

    def OnRefilter(self, widget):

        f_in = self.PushHistory(self.FilterIn, "filterin")
        f_out = self.PushHistory(self.FilterOut, "filterout")
        f_size = self.PushHistory(self.FilterSize, "filtersize")
        f_br = self.PushHistory(self.FilterBitrate, "filterbr")
        f_free = self.FilterFreeSlot.get_active()
        f_country = self.PushHistory(self.FilterCountry, "filtercc")

        self.ResultsList.set_model(None)
        self.set_filters(1, f_in, f_out, f_size, f_br, f_free, f_country)
        self.ResultsList.set_model(self.resultsmodel)

        if self.usersGroup.get_active():
            if self.ExpandButton.get_active():
                self.ResultsList.expand_all()
            else:
                self.ResultsList.collapse_all()
