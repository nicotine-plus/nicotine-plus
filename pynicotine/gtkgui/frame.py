# COPYRIGHT (C) 2020 Nicotine+ Team
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2016-2018 Mutnick <mutnick@techie.com>
# COPYRIGHT (C) 2008-2011 Quinox <quinox@users.sf.net>
# COPYRIGHT (C) 2006-2009 Daelstorm <daelstorm@gmail.com>
# COPYRIGHT (C) 2009 Hedonist <ak@sensi.org>
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
import re
import sys
import urllib.parse

from gettext import gettext as _

import gi
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk

import _thread
from pynicotine import slskmessages
from pynicotine import slskproto
from pynicotine.gtkgui import imagedata
from pynicotine.gtkgui import utils
from pynicotine.gtkgui.chatrooms import ChatRooms
from pynicotine.gtkgui.checklatest import checklatest
from pynicotine.gtkgui.dirchooser import choose_file
from pynicotine.gtkgui.downloads import Downloads
from pynicotine.gtkgui.dialogs import option_dialog
from pynicotine.gtkgui.fastconfigure import FastConfigureAssistant
from pynicotine.gtkgui.interests import Interests
from pynicotine.gtkgui.notifications import Notifications
from pynicotine.gtkgui.privatechat import PrivateChats
from pynicotine.gtkgui.roomlist import RoomList
from pynicotine.gtkgui.search import Searches
from pynicotine.gtkgui.settingswindow import Settings
from pynicotine.gtkgui.tray import Tray
from pynicotine.gtkgui.uploads import Uploads
from pynicotine.gtkgui.userbrowse import UserBrowse
from pynicotine.gtkgui.userinfo import UserInfo
from pynicotine.gtkgui.userinfo import UserTabs
from pynicotine.gtkgui.userlist import UserList
from pynicotine.gtkgui.utils import append_line
from pynicotine.gtkgui.utils import BuddiesComboBox
from pynicotine.gtkgui.utils import human_speed
from pynicotine.gtkgui.utils import ImageLabel
from pynicotine.gtkgui.utils import load_ui_elements
from pynicotine.gtkgui.utils import open_uri
from pynicotine.gtkgui.utils import PopupMenu
from pynicotine.gtkgui.utils import scroll_bottom
from pynicotine.gtkgui.utils import TextSearchBar
from pynicotine.logfacility import log
from pynicotine.nowplaying import NowPlaying
from pynicotine.pynicotine import NetworkEventProcessor
from pynicotine.upnp import UPnPPortMapping
from pynicotine.utils import unescape
from pynicotine.utils import version


class NicotineFrame:

    def __init__(self, application, data_dir, config, plugins, use_trayicon, bindip=None, port=None):

        self.application = application
        self.clip = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        self.clip_data = ""
        self.data_dir = data_dir
        self.current_tab = 0
        self.rescanning = False
        self.brescanning = False
        self.needrescan = False
        self.away = False
        self.autoaway = False
        self.awaytimerid = None
        self.bindip = bindip
        self.port = port
        self.got_focus = False

        # Initialize these windows/dialogs later when necessary
        self.fastconfigure = None
        self.settingswindow = None

        # Commonly accessed strings
        self.users_template = _("Users: %s")
        self.files_template = _("Files: %s")
        self.down_template = _("Down: %(num)i users, %(speed)s")
        self.up_template = _("Up: %(num)i users, %(speed)s")
        self.tray_download_template = _("Downloads: %(speed)s")
        self.tray_upload_template = _("Uploads: %(speed)s")

        try:
            # Spell checking support
            gi.require_version('Gspell', '1')
            from gi.repository import Gspell
            self.spell_checker = Gspell.Checker.new()
        except (ImportError, ValueError):
            self.spell_checker = None

        self.np = NetworkEventProcessor(
            self,
            self.network_callback,
            self.set_status_text,
            self.bindip,
            self.port,
            data_dir,
            config,
            plugins
        )

        self.load_icons()

        config = self.np.config.sections

        # Dark mode
        dark_mode_state = config["ui"]["dark_mode"]
        Gtk.Settings.get_default().set_property("gtk-application-prefer-dark-theme", dark_mode_state)

        utils.DECIMALSEP = config["ui"]["decimalsep"]
        utils.CATCH_URLS = config["urls"]["urlcatching"]
        utils.HUMANIZE_URLS = config["urls"]["humanizeurls"]
        utils.PROTOCOL_HANDLERS = config["urls"]["protocols"].copy()
        utils.PROTOCOL_HANDLERS["slsk"] = self.on_soul_seek
        utils.USERNAMEHOTSPOTS = config["ui"]["usernamehotspots"]
        utils.NICOTINE = self

        log.add_listener(self.log_callback)

        # Import GtkBuilder widgets
        load_ui_elements(self, os.path.join(os.path.dirname(os.path.realpath(__file__)), "ui", "mainwindow.ui"))

        self.status_context_id = self.Statusbar.get_context_id("")
        self.socket_context_id = self.SocketStatus.get_context_id("")
        self.socket_template = _("%(current)s/%(limit)s Connections")
        self.user_context_id = self.UserStatus.get_context_id("")
        self.down_context_id = self.DownStatus.get_context_id("")
        self.up_context_id = self.UpStatus.get_context_id("")

        self.MainWindow.set_title("Nicotine+" + " " + version)
        self.MainWindow.set_default_icon(self.images["n"])

        self.MainWindow.connect("focus_in_event", self.on_focus_in)
        self.MainWindow.connect("focus_out_event", self.on_focus_out)
        self.MainWindow.connect("configure_event", self.on_window_change)

        width = self.np.config.sections["ui"]["width"]
        height = self.np.config.sections["ui"]["height"]

        self.MainWindow.resize(width, height)

        xpos = self.np.config.sections["ui"]["xposition"]
        ypos = self.np.config.sections["ui"]["yposition"]

        # According to the pygtk doc this will be ignored my many window managers since the move takes place before we do a show()
        if min(xpos, ypos) < 0:
            self.MainWindow.set_position(Gtk.WindowPosition.CENTER)
        else:
            self.MainWindow.move(xpos, ypos)

        maximized = self.np.config.sections["ui"]["maximized"]

        if maximized:
            self.MainWindow.maximize()

        self.MainWindow.connect("delete-event", self.on_delete_event)
        self.MainWindow.connect("destroy", self.on_destroy)
        self.MainWindow.connect("key_press_event", self.on_key_press)
        self.MainWindow.connect("motion-notify-event", self.on_disable_auto_away)

        # Set up actions for menubar
        self.set_up_actions()

        self.roomlist = RoomList(self)
        self.interests = Interests(self, self.np)
        self.interestsvbox.pack_start(self.interests.Main, True, True, 0)

        """ Tray/notifications """

        self.tray = Tray(self)
        self.notifications = Notifications(self)

        self.hilites = {
            "rooms": [],
            "private": []
        }

        # Create the trayicon if needed
        # Tray icons don't work as expected on macOS
        if sys.platform != "darwin" and \
                use_trayicon and config["ui"]["trayicon"]:
            self.tray.create()

        """ Disable elements """

        # Disable a few elements until we're logged in (search field, download buttons etc.)
        self.set_widget_online_status(False)

        """ Log """

        # Popup menu on the log windows
        self.logpopupmenu = PopupMenu(self).setup(
            ("#" + _("Find"), self.on_find_log_window),
            ("", None),
            ("#" + _("Copy"), self.on_copy_log_window),
            ("#" + _("Copy All"), self.on_copy_all_log_window),
            ("", None),
            ("#" + _("Clear log"), self.on_clear_log_window)
        )

        # Debug
        self.debugWarnings.set_active((1 in config["logging"]["debugmodes"]))
        self.debugSearches.set_active((2 in config["logging"]["debugmodes"]))
        self.debugConnections.set_active((3 in config["logging"]["debugmodes"]))
        self.debugMessages.set_active((4 in config["logging"]["debugmodes"]))
        self.debugTransfers.set_active((5 in config["logging"]["debugmodes"]))
        self.debugStatistics.set_active((6 in config["logging"]["debugmodes"]))

        # Text Search
        TextSearchBar(self.LogWindow, self.LogSearchBar, self.LogSearchEntry)

        """ Scanning """

        if config["transfers"]["rescanonstartup"]:

            # Rescan public shares if needed
            if not self.np.config.sections["transfers"]["friendsonly"] and self.np.config.sections["transfers"]["shared"]:
                self.on_rescan()

            # Rescan buddy shares if needed
            if self.np.config.sections["transfers"]["enablebuddyshares"]:
                self.on_buddy_rescan()

        # Deactivate public shares related menu entries if we don't use them
        if self.np.config.sections["transfers"]["friendsonly"] or not self.np.config.sections["transfers"]["shared"]:
            self.rescan_public_action.set_enabled(False)
            self.browse_public_shares_action.set_enabled(False)

        # Deactivate buddy shares related menu entries if we don't use them
        if not self.np.config.sections["transfers"]["enablebuddyshares"]:
            self.rescan_buddy_action.set_enabled(False)
            self.browse_buddy_shares_action.set_enabled(False)

        """ Notebooks """

        self.hidden_tabs = {}

        # Initialise main notebook
        for tab in self.MainNotebook.get_children():
            self.MainNotebook.set_tab_reorderable(tab, config["ui"]["tab_reorderable"])

        # Translation for the labels of tabs
        translated_tablabels = {
            self.ChatTabLabel: _("Chat rooms"),
            self.PrivateChatTabLabel: _("Private chat"),
            self.SearchTabLabel: _("Search files"),
            self.UserInfoTabLabel: _("User info"),
            self.DownloadsTabLabel: _("Downloads"),
            self.UploadsTabLabel: _("Uploads"),
            self.UserBrowseTabLabel: _("User browse"),
            self.InterestsTabLabel: _("Interests")
        }

        # Mapping between the pseudo tabs and their vbox/hbox
        map_tablabels_to_box = {
            self.ChatTabLabel: "chathbox",
            self.PrivateChatTabLabel: "privatevbox",
            self.SearchTabLabel: "searchvbox",
            self.UserInfoTabLabel: "userinfovbox",
            self.DownloadsTabLabel: "downloadsvbox",
            self.UploadsTabLabel: "uploadsvbox",
            self.UserBrowseTabLabel: "userbrowsevbox",
            self.InterestsTabLabel: "interestsvbox"
        }

        hide_tab_template = _("Hide %(tab)s")

        # Initialize tabs labels
        for page in self.MainNotebook.get_children():
            tab_label = self.MainNotebook.get_tab_label(page)

            # Initialize the image label
            img_label = ImageLabel(
                translated_tablabels[tab_label], angle=config["ui"]["labelmain"],
                show_hilite_image=config["notifications"]["notification_tab_icons"]
            )

            # Set tab text color
            img_label.set_text_color(0)
            img_label.show()

            # Add it to the eventbox
            tab_label.add(img_label)

            # Set the menu to hide the tab
            eventbox_name = Gtk.Buildable.get_name(tab_label)

            tab_label.connect('button_press_event', self.on_tab_click, eventbox_name + "Menu", map_tablabels_to_box[tab_label])

            self.__dict__[eventbox_name + "Menu"] = popup = PopupMenu(self).setup(
                (
                    "#" + hide_tab_template % {"tab": translated_tablabels[tab_label]}, self.hide_tab, [tab_label, map_tablabels_to_box[tab_label]]
                )
            )

            popup.set_user(map_tablabels_to_box[tab_label])

        # Initialise other notebooks
        self.chat_notebook = ChatRooms(self)
        self.privatechat_notebook = PrivateChats(self)
        self.user_info_notebook = UserTabs(self, UserInfo, self.UserInfoNotebookRaw)
        self.user_browse_notebook = UserTabs(self, UserBrowse, self.UserBrowseNotebookRaw)
        self.search_notebook = Searches(self)

        self.chatrooms = self.chat_notebook
        self.chatrooms.show()

        # Create Search combo ListStores
        self.search_entry_combo_model = Gtk.ListStore(GObject.TYPE_STRING)
        self.SearchEntryCombo.set_model(self.search_entry_combo_model)
        self.SearchEntryCombo.set_entry_text_column(0)

        self.search_entry = self.SearchEntryCombo.get_child()
        self.search_entry.connect("activate", self.on_search)

        self.room_search_combo_model = Gtk.ListStore(GObject.TYPE_STRING)
        self.RoomSearchCombo.set_model(self.room_search_combo_model)
        self.RoomSearchCombo.set_entry_text_column(0)

        self.search_method_model = Gtk.ListStore(GObject.TYPE_STRING)
        self.SearchMethod.set_model(self.search_method_model)
        renderer_text = Gtk.CellRendererText()
        self.SearchMethod.pack_start(renderer_text, True)
        self.SearchMethod.add_attribute(renderer_text, "text", 0)

        self.searches = self.search_notebook
        self.searches.show()
        self.searches.load_config()

        self.downloads = Downloads(self)
        self.uploads = Uploads(self)
        self.userlist = UserList(self)

        self.privatechats = self.privatechat_notebook
        self.sPrivateChatButton.connect("clicked", self.on_get_private_chat)
        self.UserPrivateCombo.get_child().connect("activate", self.on_get_private_chat)
        self.privatechats.show()

        self.userinfo = self.user_info_notebook
        self.sUserinfoButton.connect("clicked", self.on_get_user_info)
        self.UserInfoCombo.get_child().connect("activate", self.on_get_user_info)
        self.userinfo.show()

        self.userbrowse = self.user_browse_notebook
        self.sSharesButton.connect("clicked", self.on_get_shares)
        self.UserBrowseCombo.get_child().connect("activate", self.on_get_shares)
        self.userbrowse.show()

        # For tab notifications
        self.userinfo.set_tab_label(self.UserInfoTabLabel)
        self.userbrowse.set_tab_label(self.UserBrowseTabLabel)

        self.update_colours(1)

        """ Now Playing """

        self.now_playing = NowPlaying(self.np.config)

        """ Connect """

        # Test if we want to do a port mapping
        if self.np.config.sections["server"]["upnp"]:

            # Initialise a UPnPPortMapping object
            upnp = UPnPPortMapping()

            # Check if we can do a port mapping
            (self.upnppossible, errors) = upnp.is_possible()

            # Test if we are able to do a port mapping
            if self.upnppossible:
                # Do the port mapping
                _thread.start_new_thread(upnp.add_port_mapping, (self.np,))
            else:
                # Display errors
                if errors is not None:
                    for err in errors:
                        log.add_warning(err)

        config_unset = self.np.config.need_config()
        if config_unset:
            if config_unset > 1:
                self.connect_action.set_enabled(False)
                self.rescan_public_action.set_enabled(True)

                # Set up fast configure dialog
                self.on_fast_configure(show=False)
            else:
                # Connect anyway
                self.on_connect(getmessage=False)
        else:
            self.on_connect(getmessage=False)

        self.update_bandwidth()

        """ Element Visibility """

        self.set_show_log(not config["logging"]["logcollapsed"])
        self.set_show_debug(config["logging"]["debug"])
        self.set_show_room_list(not config["ui"]["roomlistcollapsed"])
        self.set_show_flags(not config["columns"]["hideflags"])
        self.set_show_transfer_buttons(config["transfers"]["enabletransferbuttons"])
        self.set_toggle_buddy_list(config["ui"]["buddylistinchatrooms"])

        """ Combo Boxes """

        # Search Methods
        self.searchroomslist = {}
        self.searchmethods = {}

        # Create a list of objects of the BuddiesComboBox class
        # This add a few methods to add/remove entries on all combobox at once
        self.buddies_combo_entries = [
            BuddiesComboBox(self, self.UserSearchCombo),
            BuddiesComboBox(self, self.UserPrivateCombo),
            BuddiesComboBox(self, self.UserInfoCombo),
            BuddiesComboBox(self, self.UserBrowseCombo)
        ]

        # Initial filling of the buddies combobox
        _thread.start_new_thread(self.buddies_combos_fill, ("",))

        self.search_method_model.clear()

        # Space after Joined Rooms is important, so it doesn't conflict
        # with any possible real room, but if it's not translated with the space
        # nothing awful will happen
        joined_rooms = _("Joined Rooms ")
        self.searchroomslist[joined_rooms] = self.room_search_combo_model.append([joined_rooms])
        self.RoomSearchCombo.set_active_iter(self.searchroomslist[joined_rooms])

        """ Search """

        for method in [_("Global"), _("Buddies"), _("Rooms"), _("User")]:
            self.searchmethods[method] = self.search_method_model.append([method])

        self.SearchMethod.set_active_iter(self.searchmethods[_("Global")])
        self.SearchMethod.connect("changed", self.on_search_method)

        self.UserSearchCombo.hide()
        self.RoomSearchCombo.hide()

        self.update_download_filters()

        """ Tab Reordering """

        self.set_tab_positions()
        self.set_main_tabs_order()
        self.set_main_tabs_visibility()
        self.set_last_session_tab()

        self.page_removed_signal = self.MainNotebook.connect("page-removed", self.on_page_removed)
        self.MainNotebook.connect("page-reordered", self.on_page_reordered)
        self.MainNotebook.connect("page-added", self.on_page_added)

    """ Window """

    def on_focus_in(self, widget, event):
        self.MainWindow.set_icon(self.images["n"])
        self.got_focus = True
        if self.MainWindow.get_urgency_hint():
            self.MainWindow.set_urgency_hint(False)

    def on_focus_out(self, widget, event):
        self.got_focus = False

    def on_window_change(self, widget, blag):
        (width, height) = self.MainWindow.get_size()

        self.np.config.sections["ui"]["height"] = height
        self.np.config.sections["ui"]["width"] = width

        (xpos, ypos) = self.MainWindow.get_position()

        self.np.config.sections["ui"]["xposition"] = xpos
        self.np.config.sections["ui"]["yposition"] = ypos

    """ Init UI """

    def init_interface(self, msg):

        if not self.away:
            self.set_user_status(_("Online"))

            autoaway = self.np.config.sections["server"]["autoaway"]

            if autoaway > 0:
                self.awaytimerid = GLib.timeout_add(1000 * 60 * autoaway, self.on_auto_away)
            else:
                self.awaytimerid = None
        else:
            self.set_user_status(_("Away"))

        self.set_widget_online_status(True)
        self.tray.set_away(self.away)

        self.uploads.init_interface(self.np.transfers.uploads)
        self.downloads.init_interface(self.np.transfers.downloads)

        for i in self.np.config.sections["server"]["userlist"]:
            user = i[0]
            self.np.queue.put(slskmessages.AddUser(user))

        if msg.banner != "":
            append_line(self.LogWindow, msg.banner, self.tag_log)

        return self.privatechats, self.chatrooms, self.userinfo, self.userbrowse, self.searches, self.downloads, self.uploads, self.userlist, self.interests

    def load_icons(self):
        self.images = {}
        self.icons = {}
        self.flag_images = {}
        self.flag_users = {}
        scale = None

        def load_static(name):
            loader = GdkPixbuf.PixbufLoader()
            data = getattr(imagedata, "%s" % (name,))
            loader.write(data)
            loader.close()
            pixbuf = loader.get_pixbuf()
            if scale:
                w, h = pixbuf.get_width(), pixbuf.get_height()
                if w == h:
                    pixbuf = pixbuf.scale_simple(scale, scale, Gdk.INTERP_BILINEAR)
            return pixbuf

        names = [
            "away",
            "online",
            "offline",
            "hilite",
            "hilite3",
            "trayicon_away",
            "trayicon_connect",
            "trayicon_disconnect",
            "trayicon_msg",
            "n",
            "notify"
        ]

        if self.np.config.sections["ui"].get("icontheme"):
            extensions = ["jpg", "jpeg", "bmp", "png", "svg"]
            for name in names:
                path = None
                exts = extensions[:]
                loaded = False
                while not path or (exts and not loaded):
                    path = os.path.expanduser(os.path.join(self.np.config.sections["ui"]["icontheme"], "%s.%s" % (name, exts.pop())))
                    if os.path.exists(path):
                        data = open(path, 'rb')
                        s = data.read()
                        data.close()
                        loader = GdkPixbuf.PixbufLoader()
                        try:
                            loader.write(s)
                            loader.close()
                            pixbuf = loader.get_pixbuf()
                            if scale:
                                w, h = pixbuf.get_width(), pixbuf.get_height()
                                if w == h:
                                    pixbuf = pixbuf.scale_simple(scale, scale, Gdk.INTERP_BILINEAR)
                            self.images[name] = pixbuf
                            loaded = True
                        except GObject.GError:
                            pass
                        del loader
                        del s
                if name not in self.images:
                    self.images[name] = load_static(name)
        else:
            for name in names:
                self.images[name] = load_static(name)

    """ Connection """

    def on_network_event(self, msgs):
        for i in msgs:
            if i.__class__ in self.np.events:
                self.np.events[i.__class__](i)
            else:
                log.add("No handler for class %s %s", (i.__class__, dir(i)))

    def network_callback(self, msgs):
        if len(msgs) > 0:
            GLib.idle_add(self.on_network_event, msgs)

    def conn_close(self, conn, addr):

        if self.awaytimerid is not None:
            self.remove_away_timer(self.awaytimerid)
            self.awaytimerid = None

        if self.autoaway:
            self.autoaway = self.away = False

        self.set_widget_online_status(False)
        self.tray.set_connected(False)

        self.set_user_status(_("Offline"))

        self.searches.wish_list.interval = 0
        self.chatrooms.conn_close()
        self.privatechats.conn_close()
        self.searches.wish_list.conn_close()
        self.uploads.conn_close()
        self.downloads.conn_close()
        self.userlist.conn_close()
        self.userinfo.conn_close()
        self.userbrowse.conn_close()

    def set_widget_online_status(self, status):

        self.connect_action.set_enabled(not status)
        self.disconnect_action.set_enabled(status)
        self.away_action.set_enabled(status)
        self.check_privileges_action.set_enabled(status)
        self.get_privileges_action.set_enabled(status)

        self.roomlist.RoomsList.set_sensitive(status)
        self.roomlist.SearchRooms.set_sensitive(status)
        self.roomlist.RefreshButton.set_sensitive(status)
        self.roomlist.AcceptPrivateRoom.set_sensitive(status)
        self.UserPrivateCombo.set_sensitive(status)
        self.sPrivateChatButton.set_sensitive(status)
        self.UserBrowseCombo.set_sensitive(status)
        self.sSharesButton.set_sensitive(status)
        self.UserInfoCombo.set_sensitive(status)
        self.sUserinfoButton.set_sensitive(status)

        self.UserSearchCombo.set_sensitive(status)
        self.SearchEntryCombo.set_sensitive(status)

        self.SearchButton.set_sensitive(status)
        self.interests.SimilarUsersButton.set_sensitive(status)
        self.interests.GlobalRecommendationsButton.set_sensitive(status)
        self.interests.RecommendationsButton.set_sensitive(status)

        self.DownloadButtons.set_sensitive(status)
        self.UploadButtons.set_sensitive(status)

        self.tray.set_server_actions_sensitive(status)

    def connect_error(self, conn):

        self.set_widget_online_status(False)
        self.tray.set_connected(False)

        self.set_user_status(_("Offline"))

        self.uploads.conn_close()
        self.downloads.conn_close()

    """ Menu Bar """

    def set_up_actions(self):

        # File

        self.connect_action = Gio.SimpleAction.new("connect", None)
        self.connect_action.connect("activate", self.on_connect)
        self.application.add_action(self.connect_action)

        self.disconnect_action = Gio.SimpleAction.new("disconnect", None)
        self.disconnect_action.connect("activate", self.on_disconnect)
        self.application.add_action(self.disconnect_action)

        self.away_action = Gio.SimpleAction.new_stateful("away", None, GLib.Variant.new_boolean(False))
        self.away_action.connect("change-state", self.on_away)
        self.application.add_action(self.away_action)

        self.check_privileges_action = Gio.SimpleAction.new("checkprivileges", None)
        self.check_privileges_action.connect("activate", self.on_check_privileges)
        self.application.add_action(self.check_privileges_action)

        self.get_privileges_action = Gio.SimpleAction.new("getprivileges", None)
        self.get_privileges_action.connect("activate", self.on_get_privileges)
        self.application.add_action(self.get_privileges_action)

        action = Gio.SimpleAction.new("fastconfigure", None)
        action.connect("activate", self.on_fast_configure)
        self.application.add_action(action)

        action = Gio.SimpleAction.new("settings", None)
        action.connect("activate", self.on_settings)
        self.application.add_action(action)

        action = Gio.SimpleAction.new("quit", None)
        action.connect("activate", self.on_quit)
        self.application.add_action(action)

        # View

        state = not self.np.config.sections["logging"]["logcollapsed"]
        action = Gio.SimpleAction.new_stateful("showlog", None, GLib.Variant.new_boolean(state))
        action.connect("change-state", self.on_show_log)
        self.MainWindow.add_action(action)

        state = self.np.config.sections["logging"]["debug"]
        action = Gio.SimpleAction.new_stateful("showdebug", None, GLib.Variant.new_boolean(state))
        action.connect("change-state", self.on_show_debug)
        self.MainWindow.add_action(action)

        state = not self.np.config.sections["ui"]["roomlistcollapsed"]
        self.show_room_list_action = Gio.SimpleAction.new_stateful("showroomlist", None, GLib.Variant.new_boolean(state))
        self.show_room_list_action.connect("change-state", self.on_show_room_list)
        self.MainWindow.add_action(self.show_room_list_action)

        state = not self.np.config.sections["columns"]["hideflags"]
        action = Gio.SimpleAction.new_stateful("showflags", None, GLib.Variant.new_boolean(state))
        action.connect("change-state", self.on_show_flags)
        self.MainWindow.add_action(action)

        state = self.np.config.sections["transfers"]["enabletransferbuttons"]
        action = Gio.SimpleAction.new_stateful("showtransferbuttons", None, GLib.Variant.new_boolean(state))
        action.connect("change-state", self.on_show_transfer_buttons)
        self.MainWindow.add_action(action)

        state = self.np.config.sections["ui"]["buddylistinchatrooms"]
        self.toggle_buddy_list_action = Gio.SimpleAction.new_stateful("togglebuddylist", GLib.VariantType.new("s"), GLib.Variant.new_string(str(state)))
        self.toggle_buddy_list_action.connect("activate", self.on_toggle_buddy_list)
        self.MainWindow.add_action(self.toggle_buddy_list_action)

        # Shares

        action = Gio.SimpleAction.new("configureshares", None)
        action.connect("activate", self.on_configure_shares)
        self.application.add_action(action)

        self.rescan_public_action = Gio.SimpleAction.new("publicrescan", None)
        self.rescan_public_action.connect("activate", self.on_rescan)
        self.application.add_action(self.rescan_public_action)

        self.rescan_buddy_action = Gio.SimpleAction.new("buddyrescan", None)
        self.rescan_buddy_action.connect("activate", self.on_buddy_rescan)
        self.application.add_action(self.rescan_buddy_action)

        self.browse_public_shares_action = Gio.SimpleAction.new("browsepublicshares", None)
        self.browse_public_shares_action.connect("activate", self.on_browse_public_shares)
        self.application.add_action(self.browse_public_shares_action)

        self.browse_buddy_shares_action = Gio.SimpleAction.new("browsebuddyshares", None)
        self.browse_buddy_shares_action.connect("activate", self.on_browse_buddy_shares)
        self.application.add_action(self.browse_buddy_shares_action)

        # Modes

        action = Gio.SimpleAction.new("chatrooms", None)
        action.connect("activate", self.on_chat_rooms)
        self.MainWindow.add_action(action)

        action = Gio.SimpleAction.new("privatechat", None)
        action.connect("activate", self.on_private_chat)
        self.MainWindow.add_action(action)

        action = Gio.SimpleAction.new("downloads", None)
        action.connect("activate", self.on_downloads)
        self.MainWindow.add_action(action)

        action = Gio.SimpleAction.new("uploads", None)
        action.connect("activate", self.on_uploads)
        self.MainWindow.add_action(action)

        action = Gio.SimpleAction.new("searchfiles", None)
        action.connect("activate", self.on_search_files)
        self.MainWindow.add_action(action)

        action = Gio.SimpleAction.new("userinfo", None)
        action.connect("activate", self.on_user_info)
        self.MainWindow.add_action(action)

        action = Gio.SimpleAction.new("userbrowse", None)
        action.connect("activate", self.on_user_browse)
        self.MainWindow.add_action(action)

        action = Gio.SimpleAction.new("interests", None)
        action.connect("activate", self.on_interests)
        self.MainWindow.add_action(action)

        action = Gio.SimpleAction.new("buddylist", None)
        action.connect("activate", self.on_buddy_list)
        self.MainWindow.add_action(action)

        # Help

        action = Gio.SimpleAction.new("aboutchatroomcommands", None)
        action.connect("activate", self.on_about_chatroom_commands)
        self.application.add_action(action)

        action = Gio.SimpleAction.new("aboutprivatechatcommands", None)
        action.connect("activate", self.on_about_private_chat_commands)
        self.application.add_action(action)

        action = Gio.SimpleAction.new("aboutfilters", None)
        action.connect("activate", self.on_about_filters)
        self.application.add_action(action)

        action = Gio.SimpleAction.new("checklatest", None)
        action.connect("activate", self.on_check_latest)
        self.application.add_action(action)

        action = Gio.SimpleAction.new("reportbug", None)
        action.connect("activate", self.on_report_bug)
        self.application.add_action(action)

        action = Gio.SimpleAction.new("about", None)
        action.connect("activate", self.on_about)
        self.application.add_action(action)

    # File

    def on_connect(self, *args, getmessage=True):

        self.tray.set_connected(True)

        if self.np.active_server_conn is not None:
            return

        if getmessage:
            while not self.np.queue.empty():
                self.np.queue.get(0)

        self.set_user_status("...")
        server = self.np.config.sections["server"]["server"]
        self.set_status_text(_("Connecting to %(host)s:%(port)s"), {'host': server[0], 'port': server[1]})
        self.np.queue.put(slskmessages.ServerConn(None, server))

        if self.np.servertimer is not None:
            self.np.servertimer.cancel()
            self.np.servertimer = None

    def on_disconnect(self, *args):
        self.disconnect_action.set_enabled(False)
        self.np.manualdisconnect = True
        self.np.queue.put(slskmessages.ConnClose(self.np.active_server_conn))

    def on_away(self, *args):

        self.away = not self.away

        if not self.away:
            self.set_user_status(_("Online"))
            self.on_disable_auto_away()
        else:
            self.set_user_status(_("Away"))

        self.tray.set_away(self.away)

        self.np.queue.put(slskmessages.SetStatus(self.away and 1 or 2))
        self.away_action.set_state(GLib.Variant.new_boolean(self.away))
        self.privatechats.update_colours()

    def on_check_privileges(self, *args):
        self.np.queue.put(slskmessages.CheckPrivileges())

    def on_get_privileges(self, *args):
        url = "%(url)s" % {
            'url': 'https://www.slsknet.org/userlogin.php?username=' + urllib.parse.quote(self.np.config.sections["server"]["login"])
        }
        open_uri(url, self.MainWindow)

    def on_fast_configure(self, *args, show=True):
        if self.fastconfigure is None:
            self.fastconfigure = FastConfigureAssistant(self)

        if self.settingswindow is not None and self.settingswindow.SettingsWindow.get_property("visible"):
            return

        if show:
            self.fastconfigure.show()

    def on_settings(self, *args, page=None):
        if self.settingswindow is None:
            self.settingswindow = Settings(self)
            self.settingswindow.SettingsWindow.connect("settings-closed", self.on_settings_closed)

        if self.fastconfigure is not None and self.fastconfigure.FastConfigureAssistant.get_property("visible"):
            return

        self.settingswindow.set_settings(self.np.config.sections)

        if page:
            self.settingswindow.switch_to_page(page)

        self.settingswindow.SettingsWindow.show()
        self.settingswindow.SettingsWindow.deiconify()

    def on_quit(self, *args):
        self.MainWindow.destroy()

    # View

    def set_show_log(self, show):
        if show:
            self.debugLogBox.show()
            scroll_bottom(self.LogScrolledWindow)
        else:
            self.debugLogBox.hide()

    def on_show_log(self, action, *args):

        state = self.np.config.sections["logging"]["logcollapsed"]
        self.set_show_log(state)
        action.set_state(GLib.Variant.new_boolean(state))

        self.np.config.sections["logging"]["logcollapsed"] = not state
        self.np.config.write_configuration()

    def set_show_debug(self, show):
        if show:
            self.debugButtonsBox.show()
        else:
            self.debugButtonsBox.hide()

    def on_show_debug(self, action, *args):

        state = self.np.config.sections["logging"]["debug"]
        self.set_show_debug(not state)
        action.set_state(GLib.Variant.new_boolean(not state))

        self.np.config.sections["logging"]["debug"] = not state
        self.np.config.write_configuration()

    def set_show_room_list(self, show):
        if show:
            if self.roomlist.vbox2 not in self.vpaned3.get_children():
                self.vpaned3.pack2(self.roomlist.vbox2, True, True)
                self.vpaned3.show()
        else:
            if self.roomlist.vbox2 in self.vpaned3.get_children():
                self.vpaned3.remove(self.roomlist.vbox2)

            if self.userlist.userlistvbox not in self.vpaned3.get_children():
                self.vpaned3.hide()

    def on_show_room_list(self, action, *args):

        state = self.np.config.sections["ui"]["roomlistcollapsed"]
        self.set_show_room_list(state)
        action.set_state(GLib.Variant.new_boolean(state))

        self.np.config.sections["ui"]["roomlistcollapsed"] = not state
        self.np.config.write_configuration()

    def set_show_flags(self, state):
        for room in self.chatrooms.roomsctrl.joinedrooms:
            self.chatrooms.roomsctrl.joinedrooms[room].cols[1].set_visible(state)
            self.np.config.sections["columns"]["chatrooms"][room][1] = int(state)

        self.userlist.cols[1].set_visible(state)
        self.np.config.sections["columns"]["userlist"][1] = int(state)
        self.np.config.write_configuration()

    def on_show_flags(self, action, *args):

        state = self.np.config.sections["columns"]["hideflags"]
        self.set_show_flags(state)
        action.set_state(GLib.Variant.new_boolean(state))

        self.np.config.sections["columns"]["hideflags"] = not state
        self.np.config.write_configuration()

    def set_show_transfer_buttons(self, show):
        if show:
            self.DownloadButtons.show()
            self.UploadButtons.show()
        else:
            self.UploadButtons.hide()
            self.DownloadButtons.hide()

    def on_show_transfer_buttons(self, action, *args):

        state = self.np.config.sections["transfers"]["enabletransferbuttons"]
        self.set_show_transfer_buttons(not state)
        action.set_state(GLib.Variant.new_boolean(not state))

        self.np.config.sections["transfers"]["enabletransferbuttons"] = not state
        self.np.config.write_configuration()

    def set_toggle_buddy_list(self, state):

        tab = always = chatrooms = False

        if state == 0:
            tab = True
        if state == 1:
            chatrooms = True
        if state == 2:
            always = True

        if self.userlist.userlistvbox in self.MainNotebook.get_children():
            if tab:
                return
            self.MainNotebook.remove_page(self.MainNotebook.page_num(self.userlist.userlistvbox))

        if self.userlist.userlistvbox in self.vpanedm.get_children():
            if always:
                return
            self.vpanedm.remove(self.userlist.userlistvbox)

        if self.userlist.userlistvbox in self.vpaned3.get_children():
            if chatrooms:
                return
            self.vpaned3.remove(self.userlist.userlistvbox)

        if not self.show_room_list_action.get_enabled():
            if not chatrooms:
                self.vpaned3.hide()

        if tab:
            self.buddies_tab_label = ImageLabel(_("Buddy list"))
            self.buddies_tab_label.show()

            if self.userlist.userlistvbox not in self.MainNotebook.get_children():
                self.MainNotebook.append_page(self.userlist.userlistvbox, self.buddies_tab_label)

            if self.userlist.userlistvbox in self.MainNotebook.get_children():
                self.MainNotebook.set_tab_reorderable(self.userlist.userlistvbox, self.np.config.sections["ui"]["tab_reorderable"])

            self.userlist.BuddiesLabel.hide()

        if chatrooms:
            self.vpaned3.show()
            if self.userlist.userlistvbox not in self.vpaned3.get_children():
                self.vpaned3.pack1(self.userlist.userlistvbox, True, True)

            self.userlist.BuddiesLabel.show()

        if always:
            self.vpanedm.show()
            if self.userlist.userlistvbox not in self.vpanedm.get_children():
                self.vpanedm.pack2(self.userlist.userlistvbox, True, True)

            self.userlist.BuddiesLabel.show()
        else:
            self.vpanedm.hide()

    def on_toggle_buddy_list(self, action, state=0):
        """ Function used to switch around the UI the BuddyList position """

        if not isinstance(state, int):
            state = int(state.get_string())

        self.set_toggle_buddy_list(state)
        action.set_state(GLib.Variant.new_string(str(state)))

        self.np.config.sections["ui"]["buddylistinchatrooms"] = state
        self.np.config.write_configuration()

    # Shares

    def on_configure_shares(self, *args):
        self.on_settings(page='Shares')

    def on_rescan(self, *args, rebuild=False):

        if self.rescanning:
            return

        self.rescanning = True

        self.rescan_public_action.set_enabled(False)
        self.browse_public_shares_action.set_enabled(False)

        log.add(_("Rescanning started"))

        _thread.start_new_thread(self.np.shares.rescan_shares, (rebuild,))

    def on_buddy_rescan(self, *args, rebuild=False):

        if self.brescanning:
            return

        self.brescanning = True

        self.rescan_buddy_action.set_enabled(False)
        self.browse_buddy_shares_action.set_enabled(False)

        log.add(_("Rescanning Buddy Shares started"))

        _thread.start_new_thread(self.np.shares.rescan_buddy_shares, (rebuild,))

    def on_browse_public_shares(self, *args):
        """ Browse your own public shares """

        login = self.np.config.sections["server"]["login"]

        # Deactivate if we only share with buddies
        if self.np.config.sections["transfers"]["friendsonly"]:
            msg = slskmessages.SharedFileList(None, {})
        else:
            msg = slskmessages.SharedFileList(None, self.np.config.sections["transfers"]["sharedfilesstreams"])

        msg.parse_network_message(msg.make_network_message(nozlib=1), nozlib=1)
        self.userbrowse.show_user(login, msg.conn, msg)

    def on_browse_buddy_shares(self, *args):
        """ Browse your own buddy shares """

        login = self.np.config.sections["server"]["login"]

        # Show public shares if we don't have specific shares for buddies
        if not self.np.config.sections["transfers"]["enablebuddyshares"]:
            msg = slskmessages.SharedFileList(None, self.np.config.sections["transfers"]["sharedfilesstreams"])
        else:
            msg = slskmessages.SharedFileList(None, self.np.config.sections["transfers"]["bsharedfilesstreams"])

        msg.parse_network_message(msg.make_network_message(nozlib=1), nozlib=1)
        self.userbrowse.show_user(login, msg.conn, msg)

    # Modes

    def on_chat_rooms(self, *args):
        self.change_main_page("chatrooms")

    def on_private_chat(self, *args):
        self.change_main_page("private")

    def on_downloads(self, *args):
        self.change_main_page("downloads")

    def on_uploads(self, *args):
        self.change_main_page("uploads")

    def on_search_files(self, *args):
        self.change_main_page("search")

    def on_user_info(self, *args):
        self.change_main_page("userinfo")

    def on_user_browse(self, *args):
        self.change_main_page("userbrowse")

    def on_interests(self, *args):
        self.change_main_page("interests")

    def on_buddy_list(self, *args):
        self.on_toggle_buddy_list(self.toggle_buddy_list_action)
        self.change_main_page("userlist")

    # Help

    def on_about_chatroom_commands(self, *args):
        builder = Gtk.Builder()
        builder.set_translation_domain('nicotine')
        builder.add_from_file(os.path.join(os.path.dirname(os.path.realpath(__file__)), "ui", "about", "chatroomcommands.ui"))

        self.about_chatroom_commands = builder.get_object("AboutChatRoomCommands")
        self.about_chatroom_commands.set_transient_for(self.MainWindow)
        self.about_chatroom_commands.show()

    def on_about_private_chat_commands(self, *args):
        builder = Gtk.Builder()
        builder.set_translation_domain('nicotine')
        builder.add_from_file(os.path.join(os.path.dirname(os.path.realpath(__file__)), "ui", "about", "privatechatcommands.ui"))

        self.about_private_chat_commands = builder.get_object("AboutPrivateChatCommands")
        self.about_private_chat_commands.set_transient_for(self.MainWindow)
        self.about_private_chat_commands.show()

    def on_about_filters(self, *args):
        builder = Gtk.Builder()
        builder.set_translation_domain('nicotine')
        builder.add_from_file(os.path.join(os.path.dirname(os.path.realpath(__file__)), "ui", "about", "searchfilters.ui"))

        self.about_search_filters = builder.get_object("AboutSearchFilters")
        self.about_search_filters.set_transient_for(self.MainWindow)
        self.about_search_filters.show()

    def on_check_latest(self, *args):
        checklatest(self.MainWindow)

    def on_report_bug(self, *args):
        url = "https://github.com/Nicotine-Plus/nicotine-plus/issues"
        open_uri(url, self.MainWindow)

    def on_about(self, *args):
        builder = Gtk.Builder()
        builder.set_translation_domain('nicotine')
        builder.add_from_file(os.path.join(os.path.dirname(os.path.realpath(__file__)), "ui", "about", "about.ui"))

        self.about = builder.get_object("About")

        # Remove non-functional close button added by GTK
        buttons = self.about.get_action_area().get_children()
        if buttons:
            buttons[-1].destroy()

        # Override link handler with our own
        self.about.connect("activate-link", self.on_about_uri)

        self.about.set_transient_for(self.MainWindow)
        self.about.set_version(version)
        self.about.show()

    def on_about_uri(self, widget, uri):
        open_uri(uri, self.MainWindow)
        return True

    """ Main Notebook """

    def get_tab_label(self, tab_label):

        try:
            return tab_label.get_child()
        except AttributeError:
            return tab_label

    def chat_request_icon(self, status=0, widget=None):

        if status == 1 and not self.got_focus:
            self.MainWindow.set_icon(self.images["hilite"])

        if self.MainNotebook.get_current_page() == self.MainNotebook.page_num(self.chathbox):
            return

        tablabel = self.get_tab_label(self.ChatTabLabel)

        if not tablabel:
            return

        if status == 0:
            if tablabel.get_hilite_image() == self.images["hilite"]:
                return

        tablabel.set_hilite_image(status == 1 and self.images["hilite"] or self.images["hilite3"])
        tablabel.set_text_color(status + 1)

    def request_icon(self, tab_label, widget=None):

        if tab_label == self.PrivateChatTabLabel and not self.got_focus:
            self.MainWindow.set_icon(self.images["hilite"])

        tablabel = self.get_tab_label(tab_label)

        if not tablabel:
            return

        if self.current_tab != tab_label:
            tablabel.set_hilite_image(self.images["hilite"])
            tablabel.set_text_color(2)

    def on_switch_page(self, notebook, page, page_num):

        label = self.MainNotebook.get_tab_label(page)
        self.current_tab = label

        if label is not None:
            try:
                label.set_hilite_image(None)
                label.set_text_color(0)
            except AttributeError:
                label.get_child().set_hilite_image(None)
                label.get_child().set_text_color(0)

        if page_num == self.MainNotebook.page_num(self.chathbox):
            curr_page_num = self.chat_notebook.get_current_page()
            curr_page = self.chat_notebook.get_nth_page(curr_page_num)
            self.chatrooms.roomsctrl.on_switch_page(self.chat_notebook.notebook, curr_page, curr_page_num, forceupdate=True)

        elif page_num == self.MainNotebook.page_num(self.privatevbox):
            curr_page_num = self.privatechat_notebook.get_current_page()
            curr_page = self.privatechat_notebook.get_nth_page(curr_page_num)
            self.privatechats.on_switch_page(self.privatechat_notebook.notebook, curr_page, curr_page_num, forceupdate=True)

        elif page_num == self.MainNotebook.page_num(self.uploadsvbox):
            self.uploads.update(forceupdate=True)

        elif page_num == self.MainNotebook.page_num(self.downloadsvbox):
            self.downloads.update(forceupdate=True)

    def on_page_removed(self, main_notebook, child, page_num):

        name = self.match_main_notebox(child)
        self.np.config.sections["ui"]["modes_visible"][name] = 0
        self.on_page_reordered(main_notebook, child, page_num)

    def on_page_added(self, main_notebook, child, page_num):

        name = self.match_main_notebox(child)
        self.np.config.sections["ui"]["modes_visible"][name] = 1
        self.on_page_reordered(main_notebook, child, page_num)

    def on_page_reordered(self, main_notebook, child, page_num):

        tabs = []
        for children in self.MainNotebook.get_children():
            tabs.append(self.match_main_notebox(children))

        self.np.config.sections["ui"]["modes_order"] = tabs

        if main_notebook.get_n_pages() == 0:
            main_notebook.set_show_tabs(False)
        else:
            main_notebook.set_show_tabs(True)

    def on_key_press(self, widget, event):
        self.on_disable_auto_away()

        if event.state & (Gdk.ModifierType.MOD1_MASK | Gdk.ModifierType.CONTROL_MASK) != Gdk.ModifierType.MOD1_MASK:
            return False

        for i in range(1, 10):
            if event.keyval == Gdk.keyval_from_name(str(i)):
                self.MainNotebook.set_current_page(i - 1)
                widget.stop_emission_by_name("key_press_event")
                return True

        return False

    def set_main_tabs_order(self):
        tabs = self.np.config.sections["ui"]["modes_order"]
        order = 0

        for name in tabs:
            tab = self.match_main_name_page(name)

            # Ensure that the tab exists (Buddy List tab may be hidden)
            if tab is None or self.MainNotebook.page_num(tab) == -1:
                continue

            self.MainNotebook.reorder_child(tab, order)
            order += 1

    def set_main_tabs_visibility(self):
        visible = self.np.config.sections["ui"]["modes_visible"]

        for name in visible:
            tab = self.match_main_name_page(name)
            if tab is None:
                continue

            if not visible[name]:
                if tab not in self.MainNotebook.get_children():
                    continue

                if tab in self.hidden_tabs:
                    continue

                self.hidden_tabs[tab] = self.MainNotebook.get_tab_label(tab)
                num = self.MainNotebook.page_num(tab)
                self.MainNotebook.remove_page(num)

        if self.MainNotebook.get_n_pages() == 0:
            self.MainNotebook.set_show_tabs(False)

    def set_last_session_tab(self):
        try:
            if self.np.config.sections["ui"]["tab_select_previous"]:
                lasttabid = int(self.np.config.sections["ui"]["last_tab_id"])

                if 0 <= lasttabid <= self.MainNotebook.get_n_pages():
                    self.MainNotebook.set_current_page(lasttabid)
                    return
        except Exception:
            pass

        self.MainNotebook.set_current_page(0)

    def hide_tab(self, widget, lista):
        eventbox, child = lista
        tab = self.__dict__[child]

        if tab not in self.MainNotebook.get_children():
            return

        if tab in self.hidden_tabs:
            return

        self.hidden_tabs[tab] = eventbox

        num = self.MainNotebook.page_num(tab)
        self.MainNotebook.remove_page(num)

    def show_tab(self, lista):
        name, child = lista

        if child in self.MainNotebook.get_children():
            return

        if child not in self.hidden_tabs:
            return

        eventbox = self.hidden_tabs[child]

        self.MainNotebook.append_page(child, eventbox)
        self.MainNotebook.set_tab_reorderable(child, self.np.config.sections["ui"]["tab_reorderable"])

        del self.hidden_tabs[child]

    def on_tab_click(self, widget, event, id, child):
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3:
            self.__dict__[id].popup(None, None, None, None, event.button, event.time)

    def get_tab_position(self, string):
        if string in ("Top", "top", _("Top")):
            position = Gtk.PositionType.TOP
        elif string in ("Bottom", "bottom", _("Bottom")):
            position = Gtk.PositionType.BOTTOM
        elif string in ("Left", "left", _("Left")):
            position = Gtk.PositionType.LEFT
        elif string in ("Right", "right", _("Right")):
            position = Gtk.PositionType.RIGHT
        else:
            position = Gtk.PositionType.TOP
        return position

    def set_tab_positions(self):

        ui = self.np.config.sections["ui"]

        # Main notebook
        self.MainNotebook.set_tab_pos(self.get_tab_position(ui["tabmain"]))

        for page in self.MainNotebook.get_children():
            tab_label = self.MainNotebook.get_tab_label(page)

            try:
                tab_label.set_angle(ui["labelmain"])
            except AttributeError:
                tab_label.get_child().set_angle(ui["labelmain"])

        # Other notebooks
        self.chat_notebook.set_tab_pos(self.get_tab_position(ui["tabrooms"]))
        self.chat_notebook.set_tab_angle(ui["labelrooms"])
        self.privatechat_notebook.set_tab_pos(self.get_tab_position(ui["tabprivate"]))
        self.privatechat_notebook.set_tab_angle(ui["labelprivate"])
        self.user_info_notebook.set_tab_pos(self.get_tab_position(ui["tabinfo"]))
        self.user_info_notebook.set_tab_angle(ui["labelinfo"])
        self.user_browse_notebook.set_tab_pos(self.get_tab_position(ui["tabbrowse"]))
        self.user_browse_notebook.set_tab_angle(ui["labelbrowse"])
        self.search_notebook.set_tab_pos(self.get_tab_position(ui["tabsearch"]))
        self.search_notebook.set_tab_angle(ui["labelsearch"])

    def match_main_notebox(self, tab):

        if tab == self.chathbox:
            name = "chatrooms"  # Chatrooms
        elif tab == self.privatevbox:
            name = "private"  # Private rooms
        elif tab == self.downloadsvbox:
            name = "downloads"  # Downloads
        elif tab == self.uploadsvbox:
            name = "uploads"  # Uploads
        elif tab == self.searchvbox:
            name = "search"  # Searches
        elif tab == self.userinfovbox:
            name = "userinfo"  # Userinfo
        elif tab == self.userbrowsevbox:
            name = "userbrowse"  # User browse
        elif tab == self.interestsvbox:
            name = "interests"   # Interests
        elif tab == self.userlist.userlistvbox:
            name = "userlist"   # Buddy list
        else:
            # this should never happen, unless you've renamed a widget
            return

        return name

    def match_main_name_page(self, tab):

        if tab == "chatrooms":
            child = self.chathbox  # Chatrooms
        elif tab == "private":
            child = self.privatevbox  # Private rooms
        elif tab == "downloads":
            child = self.downloadsvbox  # Downloads
        elif tab == "uploads":
            child = self.uploadsvbox  # Uploads
        elif tab == "search":
            child = self.searchvbox  # Searches
        elif tab == "userinfo":
            child = self.userinfovbox  # Userinfo
        elif tab == "userbrowse":
            child = self.userbrowsevbox  # User browse
        elif tab == "interests":
            child = self.interestsvbox  # Interests
        elif tab == "userlist":
            child = self.userlist.userlistvbox  # Buddy list
        else:
            # this should never happen, unless you've renamed a widget
            return
        return child

    def change_main_page(self, tab):

        page_num = self.MainNotebook.page_num
        child = self.match_main_name_page(tab)

        if child in self.MainNotebook.get_children():
            self.MainNotebook.set_current_page(page_num(child))
        else:
            self.show_tab([tab, child])

    """ Fonts and Colors """

    def cell_data_func(self, column, cellrenderer, model, iterator, dummy="dummy"):
        colour = self.np.config.sections["ui"]["search"]

        if colour == "":
            colour = None

        cellrenderer.set_property("foreground", colour)

    def change_list_font(self, listview, font):
        for c in listview.get_columns():
            for r in c.get_cells():
                if isinstance(r, (Gtk.CellRendererText, Gtk.CellRendererCombo)):
                    r.set_property("font", font)

    def update_colours(self, first=0):
        if first:
            self.tag_log = self.LogWindow.get_buffer().create_tag()

        color = self.np.config.sections["ui"]["chatremote"]

        if color == "":
            color = None

        self.tag_log.set_property("foreground", color)

        font = self.np.config.sections["ui"]["chatfont"]
        self.tag_log.set_property("font", font)

        for listview in [
            self.userlist.UserListTree,
            self.interests.RecommendationsList,
            self.interests.UnrecommendationsList,
            self.interests.RecommendationUsersList,
            self.interests.LikesList,
            self.interests.DislikesList,
            self.roomlist.RoomsList
        ]:
            self.change_list_font(listview, self.np.config.sections["ui"]["listfont"])

        self.set_text_bg(self.UserPrivateCombo.get_child())
        self.set_text_bg(self.UserInfoCombo.get_child())
        self.set_text_bg(self.UserBrowseCombo.get_child())
        self.set_text_bg(self.search_entry)
        self.set_text_bg(self.interests.AddLikeEntry)
        self.set_text_bg(self.interests.AddDislikeEntry)

    def set_text_bg(self, widget, bgcolor="", fgcolor=""):
        if bgcolor == "" and self.np.config.sections["ui"]["textbg"] == "":
            rgba = None
        else:
            if bgcolor == "":
                bgcolor = self.np.config.sections["ui"]["textbg"]
            rgba = Gdk.RGBA()
            rgba.parse(bgcolor)

        widget.override_background_color(Gtk.StateFlags.NORMAL, rgba)

        if isinstance(widget, Gtk.Entry):
            if fgcolor != "":
                rgba = Gdk.RGBA()
                rgba.parse(fgcolor)
            elif fgcolor == "" and self.np.config.sections["ui"]["inputcolor"] == "":
                rgba = None
            elif fgcolor == "" and self.np.config.sections["ui"]["inputcolor"] != "":
                fgcolor = self.np.config.sections["ui"]["inputcolor"]
                rgba = Gdk.RGBA()
                rgba.parse(fgcolor)

            widget.override_color(Gtk.StateFlags.NORMAL, rgba)

        if isinstance(widget, Gtk.TreeView):
            colour = self.np.config.sections["ui"]["search"]
            if colour == "":
                colour = None
            for c in widget.get_columns():
                for r in c.get_cells():
                    if isinstance(r, (Gtk.CellRendererText, Gtk.CellRendererCombo)):
                        r.set_property("foreground", colour)

    """ Dialogs
    TODO: move to dialogs.py what's possible """

    def popup_message(self, popup):
        dialog = Gtk.MessageDialog(type=Gtk.MessageType.WARNING, buttons=Gtk.ButtonsType.OK, message_format=popup.title)
        dialog.format_secondary_text(popup.message)
        dialog.connect('response', lambda dialog, response: dialog.destroy())
        dialog.show()

    """ Scanning """

    def rescan_finished(self, type):
        if type == "buddy":
            GLib.idle_add(self._buddy_rescan_finished)
        elif type == "normal":
            GLib.idle_add(self._rescan_finished)

    def _buddy_rescan_finished(self):

        if self.np.config.sections["transfers"]["enablebuddyshares"]:
            self.rescan_buddy_action.set_enabled(True)
            self.browse_buddy_shares_action.set_enabled(True)

        self.brescanning = False
        log.add(_("Rescanning Buddy Shares finished"))

        self.BuddySharesProgress.hide()

    def _rescan_finished(self):

        if self.np.config.sections["transfers"]["shared"]:
            self.rescan_public_action.set_enabled(True)
            self.browse_public_shares_action.set_enabled(True)

        self.rescanning = False
        log.add(_("Rescanning finished"))

        self.SharesProgress.hide()

    """ Search """

    def on_settings_searches(self, widget):
        self.on_settings(page='Searches')

    def on_search_method(self, widget):

        act = False
        search_mode = self.SearchMethod.get_model().get(self.SearchMethod.get_active_iter(), 0)[0]

        if search_mode == _("User"):
            self.UserSearchCombo.show()
            act = True
        else:
            self.UserSearchCombo.hide()

        self.UserSearchCombo.set_sensitive(act)

        act = False
        if search_mode == _("Rooms"):
            act = True
            self.RoomSearchCombo.show()
        else:
            self.RoomSearchCombo.hide()

        self.RoomSearchCombo.set_sensitive(act)

    def update_download_filters(self):
        proccessedfilters = []
        outfilter = "(\\\\("
        failed = {}
        df = sorted(self.np.config.sections["transfers"]["downloadfilters"])
        # Get Filters from config file and check their escaped status
        # Test if they are valid regular expressions and save error messages

        for item in df:
            dfilter, escaped = item
            if escaped:
                dfilter = re.escape(dfilter)
                dfilter = dfilter.replace("\\*", ".*")

            try:
                re.compile("(" + dfilter + ")")
                outfilter += dfilter
                proccessedfilters.append(dfilter)
            except Exception as e:
                failed[dfilter] = e

            proccessedfilters.append(dfilter)

            if item is not df[-1]:
                outfilter += "|"

        # Crop trailing pipes
        while outfilter[-1] == "|":
            outfilter = outfilter[:-1]

        outfilter += ")$)"
        try:
            re.compile(outfilter)
            self.np.config.sections["transfers"]["downloadregexp"] = outfilter
            # Send error messages for each failed filter to log window
            if len(failed) >= 1:
                errors = ""

                for dfilter, error in failed.items():
                    errors += "Filter: %s Error: %s " % (dfilter, error)

                error = _("Error: %(num)d Download filters failed! %(error)s ", {'num': len(failed), 'error': errors})
                log.add(error)

        except Exception as e:
            # Strange that individual filters _and_ the composite filter both fail
            log.add(_("Error: Download Filter failed! Verify your filters. Reason: %s", e))
            self.np.config.sections["transfers"]["downloadregexp"] = ""

    def on_search(self, widget):
        self.searches.on_search()

    def on_clear_search_history(self, widget):
        self.searches.on_clear_search_history()

    """ User Info """

    def on_settings_userinfo(self, widget):
        self.on_settings(page='User Info')

    def on_get_user_info(self, widget):
        text = self.UserInfoCombo.get_child().get_text()
        if not text:
            return
        self.local_user_info_request(text)
        self.UserInfoCombo.get_child().set_text("")

    def local_user_info_request(self, user):
        msg = slskmessages.UserInfoRequest(None)

        # Hack for local userinfo requests, for extra security
        if user == self.np.config.sections["server"]["login"]:
            try:
                if self.np.config.sections["userinfo"]["pic"] != "":
                    userpic = self.np.config.sections["userinfo"]["pic"]
                    if os.path.exists(userpic):
                        msg.has_pic = True
                        with open(userpic, 'rb') as f:
                            msg.pic = f.read()
                    else:
                        msg.has_pic = False
                        msg.pic = None
                else:
                    msg.has_pic = False
                    msg.pic = None
            except Exception:
                msg.pic = None

            msg.descr = unescape(self.np.config.sections["userinfo"]["descr"])

            if self.np.transfers is not None:

                msg.totalupl = self.np.transfers.get_total_uploads_allowed()
                msg.queuesize = self.np.transfers.get_upload_queue_sizes()[0]
                msg.slotsavail = self.np.transfers.allow_new_uploads()
                ua = self.np.config.sections["transfers"]["remotedownloads"]
                if ua:
                    msg.uploadallowed = self.np.config.sections["transfers"]["uploadallowed"]
                else:
                    msg.uploadallowed = ua

                self.userinfo.show_user(user, msg=msg)

        else:
            self.userinfo.show_user(user)
            self.np.process_request_to_peer(user, msg, self.userinfo)

    """ User Browse """

    def browse_user(self, user):
        """ Browse a user shares """

        login = self.np.config.sections["server"]["login"]

        if user is not None:
            if user == login:
                self.on_browse_public_shares(None)
            else:
                self.userbrowse.show_user(user)
                self.np.process_request_to_peer(user, slskmessages.GetSharedFileList(None), self.userbrowse)

    def on_get_shares(self, widget):
        text = self.UserBrowseCombo.get_child().get_text()
        if not text:
            return
        self.browse_user(text)
        self.UserBrowseCombo.get_child().set_text("")

    def on_load_from_disk(self, widget):
        sharesdir = os.path.join(self.data_dir, "usershares")
        try:
            if not os.path.exists(sharesdir):
                os.makedirs(sharesdir)
        except Exception as msg:
            log.add_warning(_("Can't create directory '%(folder)s', reported error: %(error)s"), {'folder': sharesdir, 'error': msg})

        shares = choose_file(self.MainWindow.get_toplevel(), sharesdir, multiple=True)
        if shares is None:
            return
        for share in shares:
            try:
                import pickle as mypickle
                import bz2

                sharefile = bz2.BZ2File(share)
                mylist = mypickle.load(sharefile)
                sharefile.close()

                if not isinstance(mylist, (list, dict)):
                    raise TypeError("Bad data in file %(sharesdb)s" % {'sharesdb': share})

                username = share.replace('\\', os.sep).split(os.sep)[-1]
                self.userbrowse.show_user(username)

                if username in self.userbrowse.users:
                    self.userbrowse.users[username].load_shares(mylist)

            except Exception as msg:
                log.add_warning(_("Loading Shares from disk failed: %(error)s"), {'error': msg})

    """ Private Chat """

    def on_settings_logging(self, widget):
        self.on_settings(page='Logging')

    def on_get_private_chat(self, widget):
        text = self.UserPrivateCombo.get_child().get_text()
        if not text:
            return
        self.privatechats.send_message(text, show_user=True)
        self.UserPrivateCombo.get_child().set_text("")

    """ Chat """

    def auto_replace(self, message):
        if self.np.config.sections["words"]["replacewords"]:
            autoreplaced = self.np.config.sections["words"]["autoreplaced"]
            for word, replacement in autoreplaced.items():
                message = message.replace(word, replacement)

        return message

    def censor_chat(self, message):
        if self.np.config.sections["words"]["censorwords"]:
            filler = self.np.config.sections["words"]["censorfill"]
            censored = self.np.config.sections["words"]["censored"]
            for word in censored:
                message = message.replace(word, filler * len(word))

        return message

    def entry_completion_find_match(self, completion, entry_text, iterator, widget):
        model = completion.get_model()
        item_text = model.get_value(iterator, 0)
        ix = widget.get_position()
        config = self.np.config.sections["words"]

        if entry_text is None or entry_text == "" or entry_text.isspace() or item_text is None:
            return False

        # Get word to the left of current position
        if " " in entry_text:
            split_key = entry_text[:ix].split(" ")[-1]
        else:
            split_key = entry_text

        if split_key.isspace() or split_key == "" or len(split_key) < config["characters"]:
            return False

        # case-insensitive matching
        if item_text.lower().startswith(split_key) and item_text.lower() != split_key:
            return True

        return False

    def entry_completion_found_match(self, completion, model, iterator, widget):
        current_text = widget.get_text()
        ix = widget.get_position()
        # if more than a word has been typed, we throw away the
        # one to the left of our current position because we want
        # to replace it with the matching word

        if " " in current_text:
            prefix = " ".join(current_text[:ix].split(" ")[:-1])
            suffix = " ".join(current_text[ix:].split(" "))

            # add the matching word
            new_text = "%s %s%s" % (prefix, model[iterator][0], suffix)
            # set back the whole text
            widget.set_text(new_text)
            # move the cursor at the end
            widget.set_position(len(prefix) + len(model[iterator][0]) + 1)
        else:
            new_text = "%s" % (model[iterator][0])
            widget.set_text(new_text)
            widget.set_position(-1)
        # stop the event propagation
        return True

    def on_show_chat_buttons(self, widget=None):

        if widget is not None:
            show = widget.get_active()
            self.np.config.sections["ui"]["chat_hidebuttons"] = (not show)

        for room in self.chatrooms.roomsctrl.joinedrooms.values():
            room.on_show_chat_buttons(not self.np.config.sections["ui"]["chat_hidebuttons"])

        self.np.config.write_configuration()

    """ Away Timer """

    def remove_away_timer(self, timerid):
        # Check that the away timer hasn't been destroyed already
        # Happens if the timer expires
        context = GLib.MainContext.default()
        if context.find_source_by_id(timerid) is not None:
            GLib.source_remove(timerid)

    def on_auto_away(self):
        if not self.away:
            self.autoaway = True
            self.on_away()

        return False

    def on_disable_auto_away(self, *args):
        if self.autoaway:
            self.autoaway = False

            if self.away:
                # Disable away mode if not already done
                self.on_away()

        if self.awaytimerid is not None:
            self.remove_away_timer(self.awaytimerid)

            autoaway = self.np.config.sections["server"]["autoaway"]
            if autoaway > 0:
                self.awaytimerid = GLib.timeout_add(1000 * 60 * autoaway, self.on_auto_away)
            else:
                self.awaytimerid = None

    """ User Actions """

    def on_settings_ban_ignore(self, widget):
        self.on_settings(page='Ban List')

    def ban_user(self, user):
        if self.np.transfers is not None:
            self.np.transfers.ban_user(user)

    def user_ip_is_blocked(self, user):
        for ip, username in self.np.config.sections["server"]["ipblocklist"].items():
            if user == username:
                return True
        return False

    def blocked_user_ip(self, user):
        for ip, username in self.np.config.sections["server"]["ipblocklist"].items():
            if user == username:
                return ip
        return None

    def user_ip_is_ignored(self, user):
        for ip, username in self.np.config.sections["server"]["ipignorelist"].items():
            if user == username:
                return True
        return False

    def ignored_user_ip(self, user):
        for ip, username in self.np.config.sections["server"]["ipignorelist"].items():
            if user == username:
                return ip
        return None

    def ignore_ip(self, ip):
        if ip is None or ip == "" or ip.count(".") != 3:
            return

        ipignorelist = self.np.config.sections["server"]["ipignorelist"]

        if ip not in ipignorelist:
            ipignorelist[ip] = ""
            self.np.config.write_configuration()

            if self.settingswindow is not None:
                self.settingswindow.pages["Ignore List"].set_settings(self.np.config.sections)

    def on_ignore_ip(self, user):
        if user not in self.np.users or not isinstance(self.np.users[user].addr, tuple):
            if user not in self.np.ipignore_requested:
                self.np.ipignore_requested[user] = 0

            self.np.queue.put(slskmessages.GetPeerAddress(user))
            return

        ipignorelist = self.np.config.sections["server"]["ipignorelist"]
        ip, port = self.np.users[user].addr

        if ip not in ipignorelist or self.np.config.sections["server"]["ipignorelist"][ip] != user:
            self.np.config.sections["server"]["ipignorelist"][ip] = user
            self.np.config.write_configuration()

            if self.settingswindow is not None:
                self.settingswindow.pages["Ignore List"].set_settings(self.np.config.sections)

    def on_un_ignore_ip(self, user):
        ipignorelist = self.np.config.sections["server"]["ipignorelist"]

        if self.user_ip_is_ignored(user):
            ip = self.ignored_user_ip(user)

            if ip is not None:
                del ipignorelist[ip]
                self.np.config.write_configuration()

                if self.settingswindow is not None:
                    self.settingswindow.pages["Ignore List"].set_settings(self.np.config.sections)
                return True

        if user not in self.np.users:
            if user not in self.np.ipignore_requested:
                self.np.ipignore_requested[user] = 1
            self.np.queue.put(slskmessages.GetPeerAddress(user))
            return

        if not isinstance(self.np.users[user].addr, tuple):
            return

        ip, port = self.np.users[user].addr
        if ip in ipignorelist:
            del ipignorelist[ip]
            self.np.config.write_configuration()

            if self.settingswindow is not None:
                self.settingswindow.pages["Ignore List"].set_settings(self.np.config.sections)

    def on_block_user(self, user):
        if user not in self.np.users or not isinstance(self.np.users[user].addr, tuple):
            if user not in self.np.ipblock_requested:
                self.np.ipblock_requested[user] = 0

            self.np.queue.put(slskmessages.GetPeerAddress(user))
            return

        ip, port = self.np.users[user].addr
        if ip not in self.np.config.sections["server"]["ipblocklist"] or self.np.config.sections["server"]["ipblocklist"][ip] != user:
            self.np.config.sections["server"]["ipblocklist"][ip] = user
            self.np.config.write_configuration()

            if self.settingswindow is not None:
                self.settingswindow.pages["Ban List"].set_settings(self.np.config.sections)

    def on_un_block_user(self, user):
        if self.user_ip_is_blocked(user):
            ip = self.blocked_user_ip(user)

            if ip is not None:
                del self.np.config.sections["server"]["ipblocklist"][ip]
                self.np.config.write_configuration()

                if self.settingswindow is not None:
                    self.settingswindow.pages["Ban List"].set_settings(self.np.config.sections)
                return True

        if user not in self.np.users:
            if user not in self.np.ipblock_requested:
                self.np.ipblock_requested[user] = 1

            self.np.queue.put(slskmessages.GetPeerAddress(user))
            return

        if not isinstance(self.np.users[user].addr, tuple):
            return

        ip, port = self.np.users[user].addr
        if ip in self.np.config.sections["server"]["ipblocklist"]:
            del self.np.config.sections["server"]["ipblocklist"][ip]
            self.np.config.write_configuration()

            if self.settingswindow is not None:
                self.settingswindow.pages["Ban List"].set_settings(self.np.config.sections)

    def unban_user(self, user):
        if user in self.np.config.sections["server"]["banlist"]:
            self.np.config.sections["server"]["banlist"].remove(user)
            self.np.config.write_configuration()

    def ignore_user(self, user):
        if user not in self.np.config.sections["server"]["ignorelist"]:
            self.np.config.sections["server"]["ignorelist"].append(user)
            self.np.config.write_configuration()

    def unignore_user(self, user):
        if user in self.np.config.sections["server"]["ignorelist"]:
            self.np.config.sections["server"]["ignorelist"].remove(user)
            self.np.config.write_configuration()

    """ Various """

    def buddies_combos_fill(self, nothing):
        for widget in self.buddies_combo_entries:
            GLib.idle_add(widget.fill)

    def get_status_image(self, status):
        if status == 1:
            return self.images["away"]
        elif status == 2:
            return self.images["online"]
        else:
            return self.images["offline"]

    def has_user_flag(self, user, flag):
        if flag.lower() not in self.flag_images:
            self.get_flag_image(flag)

        if flag.lower() not in self.flag_images:
            return

        self.flag_users[user] = flag
        self.chatrooms.roomsctrl.set_user_flag(user, flag)
        self.userlist.set_user_flag(user, flag)

    def get_user_flag(self, user):
        if user not in self.flag_users:
            for i in self.np.config.sections["server"]["userlist"]:
                if user == i[0] and i[6] is not None:
                    return i[6]
            return "flag_"
        else:
            return self.flag_users[user]

    def get_flag_image(self, flag):

        if flag is None:
            return

        flag = flag.lower()

        if flag not in self.flag_images:
            if hasattr(imagedata, flag):
                img = None
                try:
                    loader = GdkPixbuf.PixbufLoader()
                    data = getattr(imagedata, flag)
                    loader.write(data)
                    loader.close()
                    img = loader.get_pixbuf()
                except Exception as e:
                    log.add_warning(_("Error loading image for %(flag)s: %(error)s"), {'flag': flag, 'error': e})
                self.flag_images[flag] = img
                return img
            else:
                return None
        else:
            return self.flag_images[flag]

    def on_settings_downloads(self, widget):
        self.on_settings(page='Downloads')

    def on_settings_uploads(self, widget):
        self.on_settings(page='Uploads')

    def on_soul_seek(self, url):
        try:
            user, file = urllib.parse.unquote(url[7:]).split("/", 1)

            if file[-1] == "/":
                self.np.process_request_to_peer(user, slskmessages.FolderContentsRequest(None, file[:-1].replace("/", "\\")))
            else:
                self.np.transfers.get_file(user, file.replace("/", "\\"), "")

        except Exception:
            log.add(_("Invalid SoulSeek meta-url: %s"), url)

    def set_clipboard_url(self, user, path):
        self.clip.set_text("slsk://" + urllib.parse.quote("%s/%s" % (user, path.replace("\\", "/"))), -1)
        self.clip_data = "slsk://" + urllib.parse.quote("%s/%s" % (user, path.replace("\\", "/")))

    """ Log Window """

    def log_callback(self, timestamp_format, debug_level, msg):
        GLib.idle_add(self.update_log, msg, debug_level, priority=GLib.PRIORITY_DEFAULT)

    def update_log(self, msg, debug_level=None):
        '''For information about debug levels see
        pydoc pynicotine.logfacility.logger.add
        '''

        if self.np.config.sections["logging"]["logcollapsed"]:
            # Make sure we don't attempt to scroll in the log window
            # if it's hidden, to prevent those nasty GTK warnings :)

            should_scroll = False
            self.set_status_text(msg, should_log=False)
        else:
            should_scroll = True

        append_line(self.LogWindow, msg, self.tag_log, scroll=should_scroll)

        return False

    def on_popup_log_menu(self, widget, event):
        if event.button != 3:
            return False

        widget.stop_emission_by_name("button-press-event")
        self.logpopupmenu.popup(None, None, None, None, event.button, event.time)
        return True

    def on_find_log_window(self, widget):
        self.LogSearchBar.set_search_mode(True)

    def on_copy_log_window(self, widget):

        bound = self.LogWindow.get_buffer().get_selection_bounds()

        if bound is not None and len(bound) == 2:
            start, end = bound
            log = self.LogWindow.get_buffer().get_text(start, end, True)
            self.clip.set_text(log, -1)

    def on_copy_all_log_window(self, widget):

        start, end = self.LogWindow.get_buffer().get_bounds()
        log = self.LogWindow.get_buffer().get_text(start, end, True)
        self.clip.set_text(log, -1)

    def on_clear_log_window(self, widget):
        self.LogWindow.get_buffer().set_text("")

    def add_debug_level(self, debug_level):

        if debug_level not in self.np.config.sections["logging"]["debugmodes"]:
            self.np.config.sections["logging"]["debugmodes"].append(debug_level)
            log.set_log_levels(self.np.config.sections["logging"]["debugmodes"])

    def remove_debug_level(self, debug_level):

        if debug_level in self.np.config.sections["logging"]["debugmodes"]:
            self.np.config.sections["logging"]["debugmodes"].remove(debug_level)
            log.set_log_levels(self.np.config.sections["logging"]["debugmodes"])

    def on_debug_warnings(self, widget):

        if widget.get_active():
            self.add_debug_level(1)
        else:
            self.remove_debug_level(1)

    def on_debug_searches(self, widget):

        if widget.get_active():
            self.add_debug_level(2)
        else:
            self.remove_debug_level(2)

    def on_debug_connections(self, widget):

        if widget.get_active():
            self.add_debug_level(3)
        else:
            self.remove_debug_level(3)

    def on_debug_messages(self, widget):

        if widget.get_active():
            self.add_debug_level(4)
        else:
            self.remove_debug_level(4)

    def on_debug_transfers(self, widget):

        if widget.get_active():
            self.add_debug_level(5)
        else:
            self.remove_debug_level(5)

    def on_debug_statistics(self, widget):

        if widget.get_active():
            self.add_debug_level(6)
        else:
            self.remove_debug_level(6)

    """ Status Bar """

    def set_status_text(self, msg, msg_args=None, should_log=True):
        orig_msg = msg

        if msg_args:
            msg = msg % msg_args

        self.Statusbar.pop(self.status_context_id)
        self.Statusbar.push(self.status_context_id, msg)
        self.Statusbar.set_tooltip_text(msg)

        if orig_msg and should_log:
            log.add(orig_msg, msg_args)

    def set_user_status(self, status):
        self.UserStatus.pop(self.user_context_id)
        self.UserStatus.push(self.user_context_id, status)

    def set_socket_status(self, status):
        self.SocketStatus.pop(self.socket_context_id)
        self.SocketStatus.push(self.socket_context_id, self.socket_template % {'current': status, 'limit': slskproto.MAXSOCKETS})

    def show_scan_progress(self, sharestype):
        if sharestype == "normal":
            GLib.idle_add(self.SharesProgress.show)
        else:
            GLib.idle_add(self.BuddySharesProgress.show)

    def set_scan_progress(self, sharestype, value):
        if sharestype == "normal":
            GLib.idle_add(self.SharesProgress.set_fraction, value)
        else:
            GLib.idle_add(self.BuddySharesProgress.set_fraction, value)

    def hide_scan_progress(self, sharestype):
        if sharestype == "normal":
            GLib.idle_add(self.SharesProgress.hide)
        else:
            GLib.idle_add(self.BuddySharesProgress.hide)

    def update_bandwidth(self):

        def _bandwidth(line):
            bandwidth = 0.0

            for i in line:
                speed = i.speed
                if speed is not None:
                    bandwidth = bandwidth + speed

            return human_speed(bandwidth)

        def _users(transfers, users):
            return len(users), len(transfers)

        if self.np.transfers is not None:
            down = _bandwidth(self.np.transfers.downloads)
            up = _bandwidth(self.np.transfers.uploads)
            total_usersdown, filesdown = _users(self.np.transfers.downloads, self.downloads.users)
            total_usersup, filesup = _users(self.np.transfers.uploads, self.uploads.users)
        else:
            down = up = human_speed(0.0)
            filesup = filesdown = total_usersdown = total_usersup = 0

        self.DownloadUsers.set_text(self.users_template % total_usersdown)
        self.UploadUsers.set_text(self.users_template % total_usersup)
        self.DownloadFiles.set_text(self.files_template % filesdown)
        self.UploadFiles.set_text(self.files_template % filesup)

        self.DownStatus.pop(self.down_context_id)
        self.UpStatus.pop(self.up_context_id)
        self.DownStatus.push(self.down_context_id, self.down_template % {'num': total_usersdown, 'speed': down})
        self.UpStatus.push(self.up_context_id, self.up_template % {'num': total_usersup, 'speed': up})

        self.tray.set_transfer_status(self.tray_download_template % {'speed': down}, self.tray_upload_template % {'speed': up})

    """ Exit """

    def on_settings_closed(self, widget, msg):

        if msg == "cancel":
            self.settingswindow.SettingsWindow.hide()
            return

        output = self.settingswindow.get_settings()

        if not isinstance(output, tuple):
            return

        if msg == "ok":
            self.settingswindow.SettingsWindow.hide()

        needrescan, needcolors, needcompletion, config = output

        for key, data in config.items():
            self.np.config.sections[key].update(data)

        config = self.np.config.sections

        self.np.update_debug_log_options()

        # Write utils.py options
        utils.DECIMALSEP = config["ui"]["decimalsep"]
        utils.CATCH_URLS = config["urls"]["urlcatching"]
        utils.HUMANIZE_URLS = config["urls"]["humanizeurls"]
        utils.PROTOCOL_HANDLERS = config["urls"]["protocols"].copy()
        utils.PROTOCOL_HANDLERS["slsk"] = self.on_soul_seek
        utils.USERNAMEHOTSPOTS = config["ui"]["usernamehotspots"]
        uselimit = config["transfers"]["uselimit"]
        uploadlimit = config["transfers"]["uploadlimit"]
        limitby = config["transfers"]["limitby"]

        if config["transfers"]["geoblock"]:
            panic = config["transfers"]["geopanic"]
            cc = config["transfers"]["geoblockcc"]
            self.np.queue.put(slskmessages.SetGeoBlock([panic, cc]))
        else:
            self.np.queue.put(slskmessages.SetGeoBlock(None))

        self.np.queue.put(slskmessages.SetUploadLimit(uselimit, uploadlimit, limitby))
        self.np.queue.put(slskmessages.SetDownloadLimit(config["transfers"]["downloadlimit"]))

        if self.search_notebook:
            self.search_notebook.maxdisplayedresults = config["searches"]["max_displayed_results"]
            self.search_notebook.maxstoredresults = config["searches"]["max_stored_results"]

        # Modify GUI
        self.update_download_filters()
        self.np.config.write_configuration()

        if not config["ui"]["trayicon"] and self.tray.is_tray_icon_visible():
            self.tray.hide()
        elif config["ui"]["trayicon"] and not self.tray.is_tray_icon_visible():
            self.tray.create()

        if needcompletion:
            self.chatrooms.roomsctrl.update_completions()
            self.privatechats.update_completions()

        dark_mode_state = config["ui"]["dark_mode"]
        Gtk.Settings.get_default().set_property("gtk-application-prefer-dark-theme", dark_mode_state)

        if needcolors:
            self.chatrooms.roomsctrl.update_colours()
            self.privatechats.update_colours()
            self.searches.update_colours()
            self.downloads.update_colours()
            self.uploads.update_colours()
            self.userinfo.update_colours()
            self.userbrowse.update_colours()
            self.settingswindow.update_colours()
            self.userlist.update_colours()
            self.update_colours()

        self.on_show_chat_buttons()

        # Other notebooks
        for w in [self.chat_notebook, self.privatechat_notebook, self.user_info_notebook, self.user_browse_notebook, self.search_notebook]:
            w.set_tab_closers(config["ui"]["tabclosers"])
            w.set_reorderable(config["ui"]["tab_reorderable"])
            w.show_hilite_images(config["notifications"]["notification_tab_icons"])
            w.set_text_colors(None)

        # Main notebook
        for page in self.MainNotebook.get_children():
            tab_label = self.MainNotebook.get_tab_label(page)

            try:
                tab_label.show_hilite_image(config["notifications"]["notification_tab_icons"])
                tab_label.set_text_color(0)
            except AttributeError:
                tab_label.get_child().show_hilite_image(config["notifications"]["notification_tab_icons"])
                tab_label.get_child().set_text_color(0)

            self.MainNotebook.set_tab_reorderable(page, config["ui"]["tab_reorderable"])

        self.set_tab_positions()

        if self.np.transfers is not None:
            self.np.transfers.check_upload_queue()

        if needrescan:
            self.needrescan = True

        if msg == "ok" and self.needrescan:

            self.needrescan = False

            # Rescan public shares if needed
            if not self.np.config.sections["transfers"]["friendsonly"]:
                self.on_rescan()

            # Rescan buddy shares if needed
            if self.np.config.sections["transfers"]["enablebuddyshares"]:
                self.on_buddy_rescan()

        config_unset = self.np.config.need_config()

        if config_unset > 1:
            if self.np.transfers is not None:
                self.connect_action.set_enabled(False)
            self.on_fast_configure()
        else:
            if self.np.transfers is None:
                self.connect_action.set_enabled(True)

    def on_delete_event(self, widget, event):

        if not self.np.config.sections["ui"]["exitdialog"]:
            return False

        if self.tray.is_tray_icon_visible() and self.np.config.sections["ui"]["exitdialog"] == 2:
            if self.MainWindow.get_property("visible"):
                self.MainWindow.hide()
            return True

        if self.tray.is_tray_icon_visible():
            option_dialog(
                parent=self.MainWindow,
                title=_('Close Nicotine+?'),
                message=_('Are you sure you wish to exit Nicotine+ at this time?'),
                third=_("Send to tray"),
                checkbox_label=_("Remember choice"),
                callback=self.on_quit_response
            )
        else:
            option_dialog(
                parent=self.MainWindow,
                title=_('Close Nicotine+?'),
                message=_('Are you sure you wish to exit Nicotine+ at this time?'),
                checkbox_label=_("Remember choice"),
                callback=self.on_quit_response
            )

        return True

    def on_quit_response(self, dialog, response, data):
        checkbox = dialog.checkbox.get_active()

        if response == Gtk.ResponseType.OK:

            if checkbox:
                self.np.config.sections["ui"]["exitdialog"] = 0

            self.MainWindow.destroy()

        elif response == Gtk.ResponseType.REJECT:
            if checkbox:
                self.np.config.sections["ui"]["exitdialog"] = 2
            if self.MainWindow.get_property("visible"):
                self.MainWindow.hide()

        dialog.destroy()

    def on_destroy(self, widget):

        # Prevent triggering the page removal event, which sets the tab visibility to false
        self.MainNotebook.disconnect(self.page_removed_signal)

        self.np.config.sections["ui"]["maximized"] = self.MainWindow.is_maximized()
        self.np.config.sections["ui"]["last_tab_id"] = self.MainNotebook.get_current_page()
        self.np.config.sections["privatechat"]["users"] = list(self.privatechats.users.keys())

        self.np.protothread.abort()
        self.np.stop_timers()

        if not self.np.manualdisconnect:
            self.on_disconnect(None)

        self.save_columns()

        if self.np.transfers is not None:
            self.np.transfers.save_downloads()

        # Closing up all shelves db
        self.np.shares.close_shares()

    def save_columns(self):
        for i in [self.userbrowse, self.userlist, self.chatrooms.roomsctrl, self.downloads, self.uploads, self.searches]:
            i.save_columns()

        self.np.config.write_configuration()


class MainApp(Gtk.Application):

    def __init__(self, data_dir, config, plugins, trayicon, start_hidden, bindip, port):
        Gtk.Application.__init__(self, application_id="org.nicotine_plus.Nicotine",
                                 flags=Gio.ApplicationFlags.FLAGS_NONE)

        self.data_dir = data_dir
        self.config = config
        self.plugins = plugins
        self.trayicon = trayicon
        self.start_hidden = start_hidden
        self.bindip = bindip
        self.port = port

    def do_activate(self):
        if not self.get_windows():
            # Only allow one instance of the main window

            self.frame = NicotineFrame(
                self,
                self.data_dir,
                self.config,
                self.plugins,
                self.trayicon,
                self.bindip,
                self.port
            )

            builder = Gtk.Builder().new_from_file(os.path.join(os.path.dirname(os.path.realpath(__file__)), "ui", "menus", "menubar.ui"))
            self.set_menubar(builder.get_object("menubar"))

            self.add_window(self.frame.MainWindow)

        if not self.start_hidden:
            self.frame.MainWindow.show()

            if self.frame.fastconfigure is not None:
                self.frame.fastconfigure.show()
