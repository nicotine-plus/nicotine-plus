# COPYRIGHT (C) 2020-2021 Nicotine+ Team
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
import signal
import sys
import threading
import time

import gi
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk

import _thread
from pynicotine import slskmessages
from pynicotine import slskproto
from pynicotine.gtkgui import utils
from pynicotine.gtkgui.chatrooms import ChatRooms
from pynicotine.gtkgui.downloads import Downloads
from pynicotine.gtkgui.dialogs import choose_file
from pynicotine.gtkgui.dialogs import message_dialog
from pynicotine.gtkgui.dialogs import option_dialog
from pynicotine.gtkgui.fastconfigure import FastConfigureAssistant
from pynicotine.gtkgui.interests import Interests
from pynicotine.gtkgui.notifications import Notifications
from pynicotine.gtkgui.privatechat import PrivateChats
from pynicotine.gtkgui.search import Searches
from pynicotine.gtkgui.settingswindow import Settings
from pynicotine.gtkgui.statistics import Statistics
from pynicotine.gtkgui.tray import Tray
from pynicotine.gtkgui.uploads import Uploads
from pynicotine.gtkgui.userbrowse import UserBrowse
from pynicotine.gtkgui.userinfo import UserInfo
from pynicotine.gtkgui.userinfo import UserTabs
from pynicotine.gtkgui.userlist import UserList
from pynicotine.gtkgui.utils import append_line
from pynicotine.gtkgui.utils import clear_entry
from pynicotine.gtkgui.utils import human_speed
from pynicotine.gtkgui.utils import ImageLabel
from pynicotine.gtkgui.utils import load_ui_elements
from pynicotine.gtkgui.utils import open_file_path
from pynicotine.gtkgui.utils import open_log
from pynicotine.gtkgui.utils import open_uri
from pynicotine.gtkgui.utils import PopupMenu
from pynicotine.gtkgui.utils import scroll_bottom
from pynicotine.gtkgui.utils import TextSearchBar
from pynicotine.gtkgui.utils import triggers_context_menu
from pynicotine.gtkgui.utils import update_widget_visuals
from pynicotine.logfacility import log
from pynicotine.pluginsystem import PluginHandler
from pynicotine.pynicotine import NetworkEventProcessor
from pynicotine.utils import get_latest_version
from pynicotine.utils import make_version
from pynicotine.utils import RestrictedUnpickler
from pynicotine.utils import unescape
from pynicotine.utils import version


class NicotineFrame:

    def __init__(self, application, data_dir, config, plugins, use_trayicon, start_hidden, bindip=None, port=None):

        self.application = application
        self.clip = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        self.clip_data = ""
        self.data_dir = data_dir
        self.gui_dir = os.path.dirname(os.path.realpath(__file__))
        self.current_tab_label = None
        self.checking_update = False
        self.rescanning = False
        self.brescanning = False
        self.needrescan = False
        self.autoaway = False
        self.awaytimerid = None
        self.shutdown = False
        self.bindip = bindip
        self.port = port
        utils.NICOTINE = self

        # Initialize these windows/dialogs later when necessary
        self.fastconfigure = None
        self.settingswindow = None
        self.spell_checker = None

        """ Logging """

        log.add_listener(self.log_callback)

        """ Network Event Processor """

        self.np = NetworkEventProcessor(
            self,
            self.network_callback,
            self.set_status_text,
            self.bindip,
            self.port,
            data_dir,
            config
        )

        config = self.np.config.sections

        """ Previous away state """

        self.away = config["server"]["away"]

        """ GTK Settings """

        dark_mode = config["ui"]["dark_mode"]
        global_font = config["ui"]["globalfont"]

        if dark_mode or global_font:
            gtk_settings = Gtk.Settings.get_default()

        if dark_mode:
            gtk_settings.set_property("gtk-application-prefer-dark-theme", dark_mode)

        if global_font and global_font != "Normal":
            gtk_settings.set_property("gtk-font-name", global_font)

        """ Main Window UI """

        load_ui_elements(self, os.path.join(self.gui_dir, "ui", "mainwindow.ui"))
        self.current_page_id = "Default"

        Gtk.Settings.get_default().set_property("gtk-dialogs-use-header", config["ui"]["header_bar"])

        """ Menu """

        self.set_up_actions()
        self.set_up_menu()

        self.accel_group = Gtk.AccelGroup()
        self.MainWindow.add_accel_group(self.accel_group)

        """ Icons """

        self.load_icons()

        if self.images["n"]:
            self.MainWindow.set_default_icon(self.images["n"])
        else:
            self.MainWindow.set_default_icon_name(GLib.get_prgname())

        """ Window Properties """

        self.application.add_window(self.MainWindow)

        # Handle Ctrl+C exit gracefully
        signal.signal(signal.SIGINT, self.on_quit)

        self.MainWindow.resize(
            config["ui"]["width"],
            config["ui"]["height"]
        )

        xpos = config["ui"]["xposition"]
        ypos = config["ui"]["yposition"]

        # According to the pygtk doc this will be ignored my many window managers since the move takes place before we do a show()
        if min(xpos, ypos) < 0:
            self.MainWindow.set_position(Gtk.WindowPosition.CENTER)
        else:
            self.MainWindow.move(xpos, ypos)

        if config["ui"]["maximized"]:
            self.MainWindow.maximize()

        """ Notebooks """

        # Initialise main notebook

        self.hidden_tabs = {}

        # Translation for the labels of tabs
        translated_tablabels = {
            self.SearchTabLabel: _("Search Files"),
            self.DownloadsTabLabel: _("Downloads"),
            self.UploadsTabLabel: _("Uploads"),
            self.UserBrowseTabLabel: _("User Browse"),
            self.UserInfoTabLabel: _("User Info"),
            self.PrivateChatTabLabel: _("Private Chat"),
            self.UserListTabLabel: _("Buddy List"),
            self.ChatTabLabel: _("Chat Rooms"),
            self.InterestsTabLabel: _("Interests")
        }

        hide_tab_template = _("Hide %(tab)s")

        # Initialize tabs labels
        for i in range(self.MainNotebook.get_n_pages()):
            tab_box = self.MainNotebook.get_nth_page(i)
            placehold_tab_label = self.MainNotebook.get_tab_label(tab_box)
            eventbox_name = Gtk.Buildable.get_name(placehold_tab_label)

            # Initialize the image label
            tab_label = ImageLabel(
                translated_tablabels[placehold_tab_label], angle=config["ui"]["labelmain"],
                show_hilite_image=config["notifications"]["notification_tab_icons"],
                show_status_image=True
            )

            # Set tab text color
            tab_label.set_text_color(0)
            tab_label.show()

            self.__dict__[eventbox_name] = tab_label

            # Add it to the eventbox
            self.MainNotebook.set_tab_label(tab_box, tab_label)

            # Set the menu to hide the tab
            popup_id = eventbox_name + "Menu"
            tab_label.connect('button_press_event', self.on_tab_click, popup_id)
            tab_label.connect('popup_menu', self.on_tab_popup, popup_id)
            tab_label.connect('touch_event', self.on_tab_click, popup_id)

            self.__dict__[eventbox_name + "Menu"] = popup = PopupMenu(self)
            popup.setup(
                (
                    "#" + hide_tab_template % {"tab": translated_tablabels[placehold_tab_label]}, self.hide_tab, [tab_label, tab_box]
                )
            )

        # Tab icons
        self.SearchTabLabel.set_icon("system-search-symbolic")
        self.DownloadsTabLabel.set_icon("document-save-symbolic")
        self.UploadsTabLabel.set_icon("emblem-shared-symbolic")
        self.UserBrowseTabLabel.set_icon("folder-symbolic")
        self.UserInfoTabLabel.set_icon("avatar-default-symbolic")
        self.PrivateChatTabLabel.set_icon("mail-send-symbolic")
        self.UserListTabLabel.set_icon("contact-new-symbolic")
        self.ChatTabLabel.set_icon("user-available-symbolic")
        self.InterestsTabLabel.set_icon("emblem-default-symbolic")

        # Initialise other notebooks
        self.interests = Interests(self, self.np)
        self.chatrooms = ChatRooms(self)
        self.searches = Searches(self)
        self.downloads = Downloads(self, self.DownloadsTabLabel)
        self.uploads = Uploads(self, self.UploadsTabLabel)
        self.userlist = UserList(self)
        self.privatechats = PrivateChats(self)
        self.userinfo = UserTabs(self, UserInfo, self.UserInfoNotebookRaw, self.UserInfoTabLabel, "userinfo")
        self.userbrowse = UserTabs(self, UserBrowse, self.UserBrowseNotebookRaw, self.UserBrowseTabLabel, "userbrowse")

        self.update_visuals()

        """ Entry Completion """

        for entry_name in ("RoomSearch", "UserSearch", "Search", "PrivateChat", "UserInfo", "UserBrowse"):
            completion = self.__dict__[entry_name + "Completion"]
            model = self.__dict__[entry_name + "Combo"].get_model()

            completion.set_model(model)
            completion.set_text_column(0)

        """ Tray/Notifications """

        # Commonly accessed strings
        self.tray_download_template = _("Downloads: %(speed)s")
        self.tray_upload_template = _("Uploads: %(speed)s")

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
            self.tray.load()

        """ Element Visibility """

        self.set_show_log(not config["logging"]["logcollapsed"])
        self.set_show_debug(config["logging"]["debug"])
        self.set_show_flags(not config["columns"]["hideflags"])
        self.set_show_transfer_buttons(config["transfers"]["enabletransferbuttons"])
        self.set_toggle_buddy_list(config["ui"]["buddylistinchatrooms"])

        """ Tab Visibility/Order """

        self.set_tab_positions()
        self.set_main_tabs_reorderable()
        self.set_main_tabs_order()
        self.set_main_tabs_visibility()
        self.set_last_session_tab()

        """ Disable elements """

        # Disable a few elements until we're logged in (search field, download buttons etc.)
        self.set_widget_online_status(False)

        """ Log """

        # Popup menu on the log windows
        self.logpopupmenu = PopupMenu(self)
        self.logpopupmenu.setup(
            ("#" + _("Find"), self.on_find_log_window),
            ("", None),
            ("#" + _("Copy"), self.on_copy_log_window),
            ("#" + _("Copy All"), self.on_copy_all_log_window),
            ("", None),
            ("#" + _("View Debug Logs"), self.on_view_debug_logs),
            ("#" + _("View Transfer Log"), self.on_view_transfer_log),
            ("", None),
            ("#" + _("Clear Log View"), self.on_clear_log_window)
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

        # Slight delay to prevent minor performance hit when compressing large file share
        timer = threading.Timer(2.0, self.rescan_startup)
        timer.setName("RescanSharesTimer")
        timer.setDaemon(True)
        timer.start()

        # Deactivate public shares related menu entries if we don't use them
        if config["transfers"]["friendsonly"] or not config["transfers"]["shared"]:
            self.rescan_public_action.set_enabled(False)
            self.browse_public_shares_action.set_enabled(False)

        # Deactivate buddy shares related menu entries if we don't use them
        if not config["transfers"]["enablebuddyshares"]:
            self.rescan_buddy_action.set_enabled(False)
            self.browse_buddy_shares_action.set_enabled(False)

        """ Transfer Statistics """

        self.statistics = Statistics(self, self.np.config)

        """ Tab Signals """

        self.page_removed_signal = self.MainNotebook.connect("page-removed", self.on_page_removed)
        self.MainNotebook.connect("page-reordered", self.on_page_reordered)
        self.MainNotebook.connect("page-added", self.on_page_added)

        """ Show Window """

        # Check command line option and config option
        if not start_hidden and not config["ui"]["startup_hidden"]:
            self.MainWindow.present_with_time(Gdk.CURRENT_TIME)

        """ Plugins: loaded here to ensure all requirements are initialized """

        self.np.pluginhandler = PluginHandler(self, plugins, self.np.config)

        """ Connect """

        if self.np.config.need_config():
            self.connect_action.set_enabled(False)
            self.rescan_public_action.set_enabled(True)

            # Set up fast configure dialog
            self.on_fast_configure()

        elif config["server"]["auto_connect_startup"]:
            self.on_connect()

        self.update_bandwidth()

    """ Window """

    def on_focus_in(self, widget, event):
        if self.MainWindow.get_urgency_hint():
            self.MainWindow.set_urgency_hint(False)

    def on_window_change(self, widget, blag):
        width, height = self.MainWindow.get_size()

        self.np.config.sections["ui"]["height"] = height
        self.np.config.sections["ui"]["width"] = width

        xpos, ypos = self.MainWindow.get_position()

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

        if msg.banner != "":
            log.add(msg.banner)

        return self.privatechats, self.chatrooms, self.userinfo, self.userbrowse, self.searches, self.downloads, self.uploads, self.userlist, self.interests

    def init_spell_checker(self):

        try:
            gi.require_version('Gspell', '1')
            from gi.repository import Gspell
            self.spell_checker = Gspell.Checker.new()
        except (ImportError, ValueError):
            self.spell_checker = False

    def get_flag_image(self, country):

        if not country:
            return None

        country = country.lower().replace("flag_", "")

        try:
            if country not in self.flag_images:
                self.flag_images[country] = GdkPixbuf.Pixbuf.new_from_file(
                    os.path.join(self.gui_dir, "icons", "flags", country + ".svg")
                )

        except Exception:
            return None

        return self.flag_images[country]

    def load_ui_icon(self, name):
        """ Load icon required by the UI """

        try:
            return GdkPixbuf.Pixbuf.new_from_file(
                os.path.join(self.gui_dir, "icons", name + ".svg")
            )

        except Exception:
            return None

    def load_custom_icons(self, names):
        """ Load custom icon theme if one is selected """

        if self.np.config.sections["ui"].get("icontheme"):
            log.add_debug("Loading custom icons when available")
            extensions = ["jpg", "jpeg", "bmp", "png", "svg"]

            for name in names:
                path = None
                exts = extensions[:]
                loaded = False

                while not path or (exts and not loaded):
                    path = os.path.expanduser(os.path.join(self.np.config.sections["ui"]["icontheme"], "%s.%s" % (name, exts.pop())))

                    if os.path.isfile(path):
                        try:
                            self.images[name] = GdkPixbuf.Pixbuf.new_from_file(path)
                            loaded = True

                        except Exception as e:
                            log.add(_("Error loading custom icon %(path)s: %(error)s") % {"path": path, "error": str(e)})

                if name not in self.images:
                    self.images[name] = self.load_ui_icon(name)

            return True

        return False

    def load_local_icons(self):
        """ Attempt to load local window, notification and tray icons.
        If not found, system-wide icons will be used instead. """

        app_id = GLib.get_prgname()

        if hasattr(sys, "real_prefix") or sys.base_prefix != sys.prefix:
            # Virtual environment
            icon_path = os.path.join(sys.prefix, "share", "icons", "hicolor", "scalable", "apps")
        else:
            # Git folder
            icon_path = os.path.abspath(os.path.join(self.gui_dir, "..", "..", "files"))

        log.add_debug("Loading local icons, using path %s", icon_path)

        # Window and notification icons
        try:
            scandir = os.scandir(icon_path)

            for entry in scandir:
                if entry.is_file() and entry.name == app_id + ".svg":
                    log.add_debug("Detected Nicotine+ icon: %s", entry.name)

                    try:
                        scandir.close()
                    except AttributeError:
                        # Python 3.5 compatibility
                        pass

                    for name in ("n", "notify"):
                        self.images[name] = GdkPixbuf.Pixbuf.new_from_file(entry.path)

        except FileNotFoundError:
            pass

        # Tray icons
        if icon_path.endswith("files"):
            icon_path = os.path.join(icon_path, "icons", "tray")

        for name in ("away", "connect", "disconnect", "msg"):
            try:
                scandir = os.scandir(icon_path)

                for entry in scandir:
                    if entry.is_file() and entry.name == app_id + "-" + name + ".svg":
                        log.add_debug("Detected tray icon: %s", entry.name)

                        try:
                            scandir.close()
                        except AttributeError:
                            # Python 3.5 compatibility
                            pass

                        self.images["trayicon_" + name] = GdkPixbuf.Pixbuf.new_from_file(entry.path)

            except FileNotFoundError:
                pass

    def load_icons(self):
        """ Load custom icons necessary for Nicotine+ to function """

        self.images = {}
        self.flag_images = {}

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

        """ Load custom icon theme if available """

        if self.load_custom_icons(names):
            return

        """ Load icons required by Nicotine+, such as status icons """

        for name in names:
            self.images[name] = self.load_ui_icon(name)

        """ Load local icons, if available """

        self.load_local_icons()

    def update_visuals(self):

        if not hasattr(self, "global_css_provider"):

            screen = Gdk.Screen.get_default()
            self.global_css_provider = Gtk.CssProvider()
            self.global_css_provider.load_from_data(
                b".toolbar { border-bottom: 1px solid @borders; }"
            )
            Gtk.StyleContext.add_provider_for_screen(
                screen, self.global_css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )

        for widget in self.__dict__.values():
            update_widget_visuals(widget)

    """ Connection """

    def on_network_event(self, msgs):

        for i in msgs:
            if self.shutdown:
                return
            elif i.__class__ in self.np.events:
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

        self.uploads.conn_close()
        self.downloads.conn_close()
        self.searches.wish_list.conn_close()
        self.userlist.conn_close()

        if self.shutdown:
            # Application is shutting down, stop here
            return

        self.set_widget_online_status(False)
        self.tray.set_connected(False)

        self.set_user_status(_("Offline"))

        self.searches.wish_list.interval = 0
        self.chatrooms.conn_close()
        self.privatechats.conn_close()
        self.userinfo.conn_close()
        self.userbrowse.conn_close()

        # Reset transfer stats (speed, total files/users)
        self.update_bandwidth()

    def set_widget_online_status(self, status):

        self.connect_action.set_enabled(not status)
        self.disconnect_action.set_enabled(status)
        self.away_action.set_enabled(status)
        self.check_privileges_action.set_enabled(status)
        self.get_privileges_action.set_enabled(status)

        self.PrivateChatCombo.set_sensitive(status)

        self.UserBrowseCombo.set_sensitive(status)

        if self.current_tab_label == self.UserBrowseTabLabel:
            GLib.idle_add(self.UserBrowseEntry.grab_focus)

        self.UserInfoCombo.set_sensitive(status)

        if self.current_tab_label == self.UserInfoTabLabel:
            GLib.idle_add(self.UserInfoEntry.grab_focus)

        self.UserSearchCombo.set_sensitive(status)
        self.SearchCombo.set_sensitive(status)

        if self.current_tab_label == self.SearchTabLabel:
            GLib.idle_add(self.SearchEntry.grab_focus)

        self.interests.SimilarUsersButton.set_sensitive(status)
        self.interests.GlobalRecommendationsButton.set_sensitive(status)
        self.interests.RecommendationsButton.set_sensitive(status)

        self.downloads.DownloadButtons.set_sensitive(status)
        self.uploads.UploadButtons.set_sensitive(status)

        self.RoomType.set_sensitive(status)
        self.JoinRoomEntry.set_sensitive(status)
        self.RoomList.set_sensitive(status)

        self.tray.set_server_actions_sensitive(status)

    def connect_error(self, conn):

        self.set_widget_online_status(False)
        self.tray.set_connected(False)

        self.set_user_status(_("Offline"))

        self.uploads.conn_close()
        self.downloads.conn_close()

    """ Menu """

    def set_up_actions(self):

        # File

        self.connect_action = Gio.SimpleAction.new("connect", None)
        self.connect_action.connect("activate", self.on_connect)
        self.application.add_action(self.connect_action)

        self.disconnect_action = Gio.SimpleAction.new("disconnect", None)
        self.disconnect_action.connect("activate", self.on_disconnect)
        self.application.add_action(self.disconnect_action)

        state = self.np.config.sections["server"]["away"]
        self.away_action = Gio.SimpleAction.new_stateful("away", None, GLib.Variant.new_boolean(state))
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

        state = self.np.config.sections["ui"]["header_bar"]
        action = Gio.SimpleAction.new_stateful("showheaderbar", None, GLib.Variant.new_boolean(state))
        action.connect("change-state", self.on_show_header_bar)
        self.MainWindow.add_action(action)

        state = not self.np.config.sections["logging"]["logcollapsed"]
        action = Gio.SimpleAction.new_stateful("showlog", None, GLib.Variant.new_boolean(state))
        action.connect("change-state", self.on_show_log)
        self.MainWindow.add_action(action)

        state = self.np.config.sections["logging"]["debug"]
        action = Gio.SimpleAction.new_stateful("showdebug", None, GLib.Variant.new_boolean(state))
        action.connect("change-state", self.on_show_debug)
        self.MainWindow.add_action(action)

        state = not self.np.config.sections["columns"]["hideflags"]
        action = Gio.SimpleAction.new_stateful("showflags", None, GLib.Variant.new_boolean(state))
        action.connect("change-state", self.on_show_flags)
        self.MainWindow.add_action(action)

        state = self.np.config.sections["transfers"]["enabletransferbuttons"]
        action = Gio.SimpleAction.new_stateful("showtransferbuttons", None, GLib.Variant.new_boolean(state))
        action.connect("change-state", self.on_show_transfer_buttons)
        self.MainWindow.add_action(action)

        state = self.verify_buddy_list_mode(self.np.config.sections["ui"]["buddylistinchatrooms"])
        self.toggle_buddy_list_action = Gio.SimpleAction.new_stateful("togglebuddylist", GLib.VariantType.new("s"), GLib.Variant.new_string(state))
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

        action = Gio.SimpleAction.new("keyboardshortcuts", None)
        action.connect("activate", self.on_keyboard_shortcuts)
        action.set_enabled(hasattr(Gtk, "ShortcutsWindow"))  # Not supported in Gtk <3.20
        self.application.add_action(action)

        action = Gio.SimpleAction.new("transferstatistics", None)
        action.connect("activate", self.on_transfer_statistics)
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

    def set_up_menu(self):

        builder = Gtk.Builder()
        builder.set_translation_domain('nicotine')
        builder.add_from_file(os.path.join(self.gui_dir, "ui", "menus", "mainmenu.ui"))

        self.HeaderMenu.set_menu_model(builder.get_object("mainmenu"))

        builder = Gtk.Builder()
        builder.set_translation_domain('nicotine')
        builder.add_from_file(os.path.join(self.gui_dir, "ui", "menus", "menubar.ui"))

        self.application.set_menubar(builder.get_object("menubar"))

    # File

    def on_connect(self, *args):

        self.tray.set_connected(True)
        self.np.protothread.server_connect()

        if self.np.active_server_conn is not None:
            return

        # Clear any potential messages queued up to this point (should not happen)
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
        self.np.config.sections["server"]["away"] = self.away
        self._apply_away_state()

    def _apply_away_state(self):
        if not self.away:
            self.set_user_status(_("Online"))
            self.on_disable_auto_away()
        else:
            self.set_user_status(_("Away"))

        self.tray.set_away(self.away)

        self.np.queue.put(slskmessages.SetStatus(self.away and 1 or 2))
        self.away_action.set_state(GLib.Variant.new_boolean(self.away))
        self.privatechats.update_visuals()

    def on_check_privileges(self, *args):
        self.np.queue.put(slskmessages.CheckPrivileges())

    def on_get_privileges(self, *args):
        import urllib.parse

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

        if self.fastconfigure is not None and \
                self.fastconfigure.FastConfigureDialog.get_property("visible"):
            return

        self.settingswindow.set_settings(self.np.config.sections)

        if page:
            self.settingswindow.set_active_page(page)

        self.settingswindow.SettingsWindow.show()
        self.settingswindow.SettingsWindow.deiconify()

    # View

    def set_show_header_bar(self, show):

        if show:
            self.remove_toolbar()
            self.set_header_bar(self.current_page_id)

        else:
            self.remove_header_bar()
            self.set_toolbar(self.current_page_id)

        Gtk.Settings.get_default().set_property("gtk-dialogs-use-header", show)

    def on_show_header_bar(self, action, *args):

        state = self.np.config.sections["ui"]["header_bar"]
        self.set_show_header_bar(not state)
        action.set_state(GLib.Variant.new_boolean(not state))

        self.np.config.sections["ui"]["header_bar"] = not state

    def set_show_log(self, show):
        if show:
            self.set_status_text("")
            self.debugLogBox.show()
            scroll_bottom(self.LogScrolledWindow)
        else:
            self.debugLogBox.hide()

    def on_show_log(self, action, *args):

        state = self.np.config.sections["logging"]["logcollapsed"]
        self.set_show_log(state)
        action.set_state(GLib.Variant.new_boolean(state))

        self.np.config.sections["logging"]["logcollapsed"] = not state

    def set_show_debug(self, show):
        self.debugButtonsBox.set_visible(show)

    def on_show_debug(self, action, *args):

        state = self.np.config.sections["logging"]["debug"]
        self.set_show_debug(not state)
        action.set_state(GLib.Variant.new_boolean(not state))

        self.np.config.sections["logging"]["debug"] = not state

    def set_show_flags(self, state):
        for room in self.chatrooms.joinedrooms:
            self.chatrooms.joinedrooms[room].cols["country"].set_visible(state)
            self.np.config.sections["columns"]["chat_room"][room][1] = int(state)

        self.userlist.cols["country"].set_visible(state)
        self.np.config.sections["columns"]["buddy_list"][1] = int(state)

    def on_show_flags(self, action, *args):

        state = self.np.config.sections["columns"]["hideflags"]
        self.set_show_flags(state)
        action.set_state(GLib.Variant.new_boolean(state))

        self.np.config.sections["columns"]["hideflags"] = not state

    def set_show_transfer_buttons(self, show):
        self.downloads.DownloadButtons.set_visible(show)
        self.uploads.UploadButtons.set_visible(show)

    def on_show_transfer_buttons(self, action, *args):

        state = self.np.config.sections["transfers"]["enabletransferbuttons"]
        self.set_show_transfer_buttons(not state)
        action.set_state(GLib.Variant.new_boolean(not state))

        self.np.config.sections["transfers"]["enabletransferbuttons"] = not state

    def set_toggle_buddy_list(self, mode):

        mode = self.verify_buddy_list_mode(mode)

        if self.userlist.Main in self.NotebooksPane.get_children():

            if mode == "always":
                return

            self.NotebooksPane.remove(self.userlist.Main)

        elif self.userlist.Main in self.ChatroomsPane.get_children():

            if mode == "chatrooms":
                return

            self.ChatroomsPane.remove(self.userlist.Main)

        elif self.userlist.Main in self.userlistvbox.get_children():

            if mode == "tab":
                return

            self.userlistvbox.remove(self.userlist.Main)
            self.hide_tab(None, [self.UserListTabLabel, self.userlistvbox])

        if mode == "always":

            if self.userlist.Main not in self.NotebooksPane.get_children():
                self.NotebooksPane.pack2(self.userlist.Main, False, True)

            self.userlist.BuddiesToolbar.show()
            self.userlist.UserLabel.hide()

        elif mode == "chatrooms":

            if self.userlist.Main not in self.ChatroomsPane.get_children():
                self.ChatroomsPane.pack2(self.userlist.Main, False, True)

            self.userlist.BuddiesToolbar.show()
            self.userlist.UserLabel.hide()

        elif mode == "tab":

            self.userlistvbox.add(self.userlist.Main)
            self.show_tab(self.userlistvbox)

            self.userlist.BuddiesToolbar.hide()
            self.userlist.UserLabel.show()

    def on_toggle_buddy_list(self, action, state):
        """ Function used to switch around the UI the BuddyList position """

        mode = str(state).replace("'", "")

        self.set_toggle_buddy_list(mode)
        action.set_state(state)

        self.np.config.sections["ui"]["buddylistinchatrooms"] = mode

    # Shares

    def on_configure_shares(self, *args):
        self.on_settings(page='Shares')

    def on_rescan(self, *args, rebuild=False):

        if self.rescanning:
            return

        self.rescanning = True

        self.rescan_public_action.set_enabled(False)
        self.browse_public_shares_action.set_enabled(False)

        self.np.shares.rescan_public_shares(rebuild)

    def on_buddy_rescan(self, *args, rebuild=False):

        if self.brescanning:
            return

        self.brescanning = True

        self.rescan_buddy_action.set_enabled(False)
        self.browse_buddy_shares_action.set_enabled(False)

        self.np.shares.rescan_buddy_shares(rebuild)

    def on_browse_public_shares(self, *args, folder=None):
        """ Browse your own public shares """

        login = self.np.config.sections["server"]["login"]

        # Deactivate if we only share with buddies
        if self.np.config.sections["transfers"]["friendsonly"]:
            msg = slskmessages.SharedFileList(None, {})
        else:
            msg = self.np.shares.compressed_shares_normal

        _thread.start_new_thread(self.parse_local_shares, (login, msg, folder, "normal"))
        self.userbrowse.show_user(login, indeterminate_progress=True)

    def on_browse_buddy_shares(self, *args, folder=None):
        """ Browse your own buddy shares """

        login = self.np.config.sections["server"]["login"]

        # Show public shares if we don't have specific shares for buddies
        if not self.np.config.sections["transfers"]["enablebuddyshares"]:
            msg = self.np.shares.compressed_shares_normal
        else:
            msg = self.np.shares.compressed_shares_buddy

        _thread.start_new_thread(self.parse_local_shares, (login, msg, folder, "buddy"))
        self.userbrowse.show_user(login, indeterminate_progress=True)

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
        self.on_toggle_buddy_list(self.toggle_buddy_list_action, GLib.Variant.new_string("tab"))
        self.change_main_page("userlist")

    # Help

    def on_keyboard_shortcuts(self, *args):

        if not hasattr(self, "KeyboardShortcutsDialog"):
            load_ui_elements(self, os.path.join(self.gui_dir, "ui", "dialogs", "shortcuts.ui"))
            self.KeyboardShortcutsDialog.set_transient_for(self.MainWindow)

        self.KeyboardShortcutsDialog.show()

    def on_transfer_statistics(self, *args):
        self.statistics.show()

    def on_check_latest(self, *args):

        if not self.checking_update:
            _thread.start_new_thread(self._on_check_latest, ())
            self.checking_update = True

    def _on_check_latest(self):

        try:
            hlatest, latest, date = get_latest_version()
            myversion = int(make_version(version))

        except Exception as m:
            GLib.idle_add(
                message_dialog,
                self.MainWindow,
                _("Error retrieving latest version"),
                str(m)
            )
            self.checking_update = False
            return

        if latest > myversion:
            version_label = _("Version %s is available") % hlatest

            if date:
                version_label += ", " + _("released on %s") % date

            GLib.idle_add(
                message_dialog,
                self.MainWindow,
                _("Out of date"),
                version_label
            )

        elif myversion > latest:
            GLib.idle_add(
                message_dialog,
                self.MainWindow,
                _("Up to date"),
                _("You appear to be using a development version of Nicotine+.")
            )

        else:
            GLib.idle_add(
                message_dialog,
                self.MainWindow,
                _("Up to date"),
                _("You are using the latest version of Nicotine+.")
            )

        self.checking_update = False

    def on_report_bug(self, *args):
        url = "https://github.com/Nicotine-Plus/nicotine-plus/issues"
        open_uri(url, self.MainWindow)

    def on_about(self, *args):

        load_ui_elements(self, os.path.join(self.gui_dir, "ui", "dialogs", "about.ui"))

        # Override link handler with our own
        self.AboutDialog.connect("activate-link", self.on_about_uri)

        if self.images["n"]:
            self.AboutDialog.set_logo(self.images["n"])
        else:
            self.AboutDialog.set_logo_icon_name(GLib.get_prgname())

        self.AboutDialog.set_transient_for(self.MainWindow)
        self.AboutDialog.set_version(version)

        self.AboutDialog.run()
        self.AboutDialog.destroy()

    def on_about_uri(self, widget, uri):
        open_uri(uri, self.MainWindow)
        return True

    """ Headerbar/toolbar """

    def set_header_bar(self, page_id):

        """ Set a 'normal' headerbar for the main window (client side decorations
        enabled) """

        self.MainWindow.set_show_menubar(False)
        self.HeaderMenu.show()

        menu_parent = self.HeaderMenu.get_parent()
        if menu_parent is not None:
            menu_parent.remove(self.HeaderMenu)

        end_widget = self.__dict__[page_id + "End"]
        end_widget.add(self.HeaderMenu)

        key, mod = Gtk.accelerator_parse("F10")
        self.HeaderMenu.add_accelerator("clicked", self.accel_group, key, mod, Gtk.AccelFlags.VISIBLE)

        header_bar = self.__dict__["Header" + page_id]
        header_bar.set_title(GLib.get_application_name())
        self.MainWindow.set_titlebar(header_bar)

    def set_toolbar(self, page_id):

        """ Move the headerbar widgets to a GtkBox "toolbar", and show the regular
        title bar (client side decorations disabled) """

        self.MainWindow.set_show_menubar(True)
        self.HeaderMenu.hide()

        if page_id == "Default":
            # No toolbar needed for this page
            return

        header_bar = self.__dict__["Header" + page_id]
        toolbar = self.__dict__[page_id + "Toolbar"]
        toolbar_contents = self.__dict__[page_id + "ToolbarContents"]

        title_widget = self.__dict__[page_id + "Title"]
        title_widget.set_hexpand(True)
        header_bar.set_custom_title(None)
        toolbar_contents.add(title_widget)

        try:
            start_widget = self.__dict__[page_id + "Start"]
            header_bar.remove(start_widget)
            toolbar_contents.add(start_widget)

        except KeyError:
            # No start widget
            pass

        end_widget = self.__dict__[page_id + "End"]
        header_bar.remove(end_widget)
        toolbar_contents.add(end_widget)

        toolbar.show()

    def remove_header_bar(self):

        """ Remove the current CSD headerbar, and show the regular titlebar """

        key, mod = Gtk.accelerator_parse("F10")
        self.HeaderMenu.remove_accelerator(self.accel_group, key, mod)

        self.MainWindow.unrealize()
        self.MainWindow.set_titlebar(None)
        self.MainWindow.map()

    def remove_toolbar(self):

        """ Move the GtkBox toolbar widgets back to the headerbar, and hide
        the toolbar """

        if self.current_page_id == "Default":
            # No toolbar on this page
            return

        header_bar = self.__dict__["Header" + self.current_page_id]
        toolbar = self.__dict__[self.current_page_id + "Toolbar"]
        toolbar_contents = self.__dict__[self.current_page_id + "ToolbarContents"]

        title_widget = self.__dict__[self.current_page_id + "Title"]
        title_widget.set_hexpand(False)
        toolbar_contents.remove(title_widget)
        header_bar.set_custom_title(title_widget)

        try:
            start_widget = self.__dict__[self.current_page_id + "Start"]
            toolbar_contents.remove(start_widget)
            header_bar.add(start_widget)

        except KeyError:
            # No start widget
            pass

        end_widget = self.__dict__[self.current_page_id + "End"]
        toolbar_contents.remove(end_widget)
        header_bar.pack_end(end_widget)

        toolbar.hide()

    def set_active_header_bar(self, page_id):

        """ Switch out the active headerbar for another one. This is used when
        changing the active notebook tab. """

        if self.np.config.sections["ui"]["header_bar"]:
            self.set_header_bar(page_id)

        else:
            self.remove_toolbar()
            self.set_toolbar(page_id)

        self.current_page_id = page_id

    """ Main Notebook """

    def request_tab_icon(self, tab_label, status=1):

        if self.current_tab_label == tab_label:
            return

        if not tab_label:
            return

        if status == 1:
            hilite_icon = self.images["hilite"]
        else:
            hilite_icon = self.images["hilite3"]

            if tab_label.get_hilite_image() == self.images["hilite"]:
                # Chat mentions have priority over normal notifications
                return

        if hilite_icon == tab_label.get_hilite_image():
            return

        tab_label.set_hilite_image(hilite_icon)
        tab_label.set_text_color(status + 1)

    def on_switch_page(self, notebook, page, page_num):

        GLib.idle_add(notebook.grab_focus)

        tab_label = notebook.get_tab_label(page)
        self.current_tab_label = tab_label

        if tab_label is not None:
            # Defaults
            tab_label.set_hilite_image(None)
            tab_label.set_text_color(0)

        if tab_label == self.ChatTabLabel:
            self.set_active_header_bar("Chatrooms")

            curr_page_num = self.chatrooms.get_current_page()
            curr_page = self.chatrooms.get_nth_page(curr_page_num)
            self.chatrooms.on_switch_chat(self.chatrooms.notebook, curr_page, curr_page_num, forceupdate=True)

        elif tab_label == self.PrivateChatTabLabel:
            self.set_active_header_bar("PrivateChat")

            curr_page_num = self.privatechats.get_current_page()
            curr_page = self.privatechats.get_nth_page(curr_page_num)
            self.privatechats.on_switch_chat(self.privatechats.notebook, curr_page, curr_page_num, forceupdate=True)

        elif tab_label == self.UploadsTabLabel:
            self.set_active_header_bar("Uploads")
            self.uploads.update(forceupdate=True)

        elif tab_label == self.DownloadsTabLabel:
            self.set_active_header_bar("Downloads")
            self.downloads.update(forceupdate=True)

        elif tab_label == self.SearchTabLabel:
            self.set_active_header_bar("Search")
            GLib.idle_add(self.SearchEntry.grab_focus)

        elif tab_label == self.UserInfoTabLabel:
            self.set_active_header_bar("UserInfo")

        elif tab_label == self.UserBrowseTabLabel:
            self.set_active_header_bar("UserBrowse")

        elif tab_label == self.UserListTabLabel:
            self.set_active_header_bar("UserList")

        else:
            self.set_active_header_bar("Default")

    def on_page_removed(self, main_notebook, child, page_num):

        name = self.match_main_notebox(child)
        self.np.config.sections["ui"]["modes_visible"][name] = False

        self.on_page_reordered(main_notebook, child, page_num)

    def on_page_added(self, main_notebook, child, page_num):

        name = self.match_main_notebox(child)
        self.np.config.sections["ui"]["modes_visible"][name] = True

        self.on_page_reordered(main_notebook, child, page_num)

    def on_page_reordered(self, main_notebook, child, page_num):

        tab_names = []

        for i in range(self.MainNotebook.get_n_pages()):
            tab_box = self.MainNotebook.get_nth_page(i)
            tab_names.append(self.match_main_notebox(tab_box))

        self.np.config.sections["ui"]["modes_order"] = tab_names

        if main_notebook.get_n_pages() <= 1:
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

    def set_main_tabs_reorderable(self):

        reorderable = self.np.config.sections["ui"]["tab_reorderable"]

        for i in range(self.MainNotebook.get_n_pages()):
            tab_box = self.MainNotebook.get_nth_page(i)
            self.MainNotebook.set_tab_reorderable(tab_box, reorderable)

    def set_main_tabs_order(self):

        tab_names = self.np.config.sections["ui"]["modes_order"]
        order = 0

        for name in tab_names:
            tab_box = self.match_main_name_page(name)
            self.MainNotebook.reorder_child(tab_box, order)
            order += 1

    def set_main_tabs_visibility(self):

        tab_names = self.np.config.sections["ui"]["modes_visible"]

        for name in tab_names:
            if tab_names[name]:
                # Tab is visible
                continue

            tab_box = self.match_main_name_page(name)
            num = self.MainNotebook.page_num(tab_box)

            self.hidden_tabs[tab_box] = self.MainNotebook.get_tab_label(tab_box)
            self.MainNotebook.remove_page(num)

        if self.MainNotebook.get_n_pages() <= 1:
            self.MainNotebook.set_show_tabs(False)

    def set_last_session_tab(self):

        # Ensure we set a header bar, by activating the "switch-page" signal at least once
        default_page = self.MainNotebook.get_nth_page(0)
        self.MainNotebook.emit("switch-page", default_page, 0)

        if not self.np.config.sections["ui"]["tab_select_previous"]:
            return

        last_tab_id = int(self.np.config.sections["ui"]["last_tab_id"])

        if 0 <= last_tab_id <= self.MainNotebook.get_n_pages():
            self.MainNotebook.set_current_page(last_tab_id)

    def hide_tab(self, widget, lista):

        event_box, tab_box = lista

        if tab_box not in (self.MainNotebook.get_nth_page(i) for i in range(self.MainNotebook.get_n_pages())):
            return

        if tab_box in self.hidden_tabs:
            return

        self.hidden_tabs[tab_box] = event_box

        num = self.MainNotebook.page_num(tab_box)
        self.MainNotebook.remove_page(num)

    def show_tab(self, tab_box):

        if tab_box in (self.MainNotebook.get_nth_page(i) for i in range(self.MainNotebook.get_n_pages())):
            return

        if tab_box not in self.hidden_tabs:
            return

        event_box = self.hidden_tabs[tab_box]

        self.MainNotebook.append_page(tab_box, event_box)
        self.set_tab_expand(tab_box)
        self.MainNotebook.set_tab_reorderable(tab_box, self.np.config.sections["ui"]["tab_reorderable"])

        del self.hidden_tabs[tab_box]

    def on_tab_popup(self, widget, popup_id):
        self.__dict__[popup_id].popup()

    def on_tab_click(self, widget, event, popup_id):

        if not triggers_context_menu(event):
            return False

        self.on_tab_popup(widget, popup_id)
        return True

    def set_tab_expand(self, tab_box):

        tab_label = self.MainNotebook.get_tab_label(tab_box)
        tab_position = self.np.config.sections["ui"]["tabmain"]

        if tab_position in ("Left", "left", _("Left")) or \
                tab_position in ("Right", "right", _("Right")):
            expand = False
        else:
            expand = True

        self.MainNotebook.child_set_property(tab_box, "tab-expand", expand)
        tab_label.set_centered(expand)

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
        tab_position = ui["tabmain"]
        self.MainNotebook.set_tab_pos(self.get_tab_position(tab_position))

        for i in range(self.MainNotebook.get_n_pages()):
            tab_box = self.MainNotebook.get_nth_page(i)
            tab_label = self.MainNotebook.get_tab_label(tab_box)

            self.set_tab_expand(tab_box)
            tab_label.set_angle(ui["labelmain"])

        # Other notebooks
        self.chatrooms.set_tab_pos(self.get_tab_position(ui["tabrooms"]))
        self.chatrooms.set_tab_angle(ui["labelrooms"])

        self.privatechats.set_tab_pos(self.get_tab_position(ui["tabprivate"]))
        self.privatechats.set_tab_angle(ui["labelprivate"])

        self.userinfo.set_tab_pos(self.get_tab_position(ui["tabinfo"]))
        self.userinfo.set_tab_angle(ui["labelinfo"])

        self.userbrowse.set_tab_pos(self.get_tab_position(ui["tabbrowse"]))
        self.userbrowse.set_tab_angle(ui["labelbrowse"])

        self.searches.set_tab_pos(self.get_tab_position(ui["tabsearch"]))
        self.searches.set_tab_angle(ui["labelsearch"])

    def match_main_notebox(self, tab):

        if tab == self.chatroomsvbox:
            name = "chatrooms"   # Chatrooms
        elif tab == self.privatechatvbox:
            name = "private"     # Private rooms
        elif tab == self.downloadsvbox:
            name = "downloads"   # Downloads
        elif tab == self.uploadsvbox:
            name = "uploads"     # Uploads
        elif tab == self.searchvbox:
            name = "search"      # Searches
        elif tab == self.userinfovbox:
            name = "userinfo"    # Userinfo
        elif tab == self.userbrowsevbox:
            name = "userbrowse"  # User browse
        elif tab == self.interestsvbox:
            name = "interests"   # Interests
        elif tab == self.userlistvbox:
            name = "userlist"    # Buddy list
        else:
            # this should never happen, unless you've renamed a widget
            return

        return name

    def match_main_name_page(self, tab):

        if tab == "chatrooms":
            child = self.chatroomsvbox          # Chatrooms
        elif tab == "private":
            child = self.privatechatvbox        # Private rooms
        elif tab == "downloads":
            child = self.downloadsvbox          # Downloads
        elif tab == "uploads":
            child = self.uploadsvbox            # Uploads
        elif tab == "search":
            child = self.searchvbox             # Searches
        elif tab == "userinfo":
            child = self.userinfovbox           # Userinfo
        elif tab == "userbrowse":
            child = self.userbrowsevbox         # User browse
        elif tab == "interests":
            child = self.interestsvbox          # Interests
        elif tab == "userlist":
            child = self.userlistvbox           # Buddy list
        else:
            # this should never happen, unless you've renamed a widget
            return

        return child

    def change_main_page(self, tab_name):

        tab_box = self.match_main_name_page(tab_name)

        if tab_box in (self.MainNotebook.get_nth_page(i) for i in range(self.MainNotebook.get_n_pages())):
            page_num = self.MainNotebook.page_num
            self.MainNotebook.set_current_page(page_num(tab_box))
        else:
            self.show_tab(tab_box)

    """ Scanning """

    def rescan_startup(self):

        if self.rescanning:
            return

        if self.np.config.sections["transfers"]["rescanonstartup"]:

            # Rescan public shares if needed
            if not self.np.config.sections["transfers"]["friendsonly"] and \
                    self.np.config.sections["transfers"]["shared"]:
                GLib.idle_add(self.on_rescan)

            # Rescan buddy shares if needed
            if self.np.config.sections["transfers"]["enablebuddyshares"]:
                GLib.idle_add(self.on_buddy_rescan)

        else:
            if not self.np.config.sections["transfers"]["friendsonly"]:
                self.np.shares.compress_shares("normal")

            if self.np.config.sections["transfers"]["enablebuddyshares"]:
                self.np.shares.compress_shares("buddy")

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
        self.BuddySharesProgress.hide()

    def _rescan_finished(self):

        if self.np.config.sections["transfers"]["shared"]:
            self.rescan_public_action.set_enabled(True)
            self.browse_public_shares_action.set_enabled(True)

        self.rescanning = False
        self.SharesProgress.hide()

    """ Transfer Statistics """

    def update_stat_value(self, stat_id, stat_value):
        self.statistics.update_stat_value(stat_id, stat_value)

    """ Search """

    def on_settings_searches(self, widget):
        self.on_settings(page='Searches')

    def on_search_method(self, widget):

        act = False
        search_mode = self.SearchMethod.get_active_id()

        if search_mode == "user":
            self.UserSearchCombo.show()
            act = True
        else:
            self.UserSearchCombo.hide()

        self.UserSearchCombo.set_sensitive(act)

        act = False
        if search_mode == "rooms":
            act = True
            self.RoomSearchCombo.show()
        else:
            self.RoomSearchCombo.hide()

        self.RoomSearchCombo.set_sensitive(act)

    def on_search(self, widget, *args):
        self.searches.on_search()
        clear_entry(widget)

    """ User Info """

    def on_settings_userinfo(self, widget):
        self.on_settings(page='UserInfo')

    def on_get_user_info(self, widget, *args):

        text = widget.get_text()

        if not text:
            return

        self.local_user_info_request(text)
        clear_entry(widget)

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
            self.np.send_message_to_peer(user, msg)

    """ User Browse """

    def browse_user(self, user, folder=None, local_shares_type=None):
        """ Browse a user shares """

        login = self.np.config.sections["server"]["login"]

        if user is not None:
            if user == login:
                if local_shares_type == "normal" or not self.np.config.sections["transfers"]["enablebuddyshares"]:
                    self.on_browse_public_shares(folder=folder)
                else:
                    self.on_browse_buddy_shares(folder=folder)
            else:
                self.userbrowse.show_user(user, folder=folder)

                if self.userbrowse.is_new_request(user):
                    self.np.send_message_to_peer(user, slskmessages.GetSharedFileList(None))

    def parse_local_shares(self, username, msg, folder=None, shares_type="normal"):
        """ Parse our local shares list and show it in the UI """

        built = msg.make_network_message(nozlib=0)
        msg.parse_network_message(built)

        indeterminate_progress = change_page = False
        GLib.idle_add(self.userbrowse.show_user, username, msg.conn, msg, indeterminate_progress, change_page, folder, shares_type)

    def on_get_shares(self, widget, *args):

        text = widget.get_text()

        if not text:
            return

        self.browse_user(text)
        clear_entry(widget)

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
                try:
                    # Try legacy format first
                    import bz2

                    with bz2.BZ2File(share) as sharefile:
                        mylist = RestrictedUnpickler(sharefile, encoding='utf-8').load()

                except Exception:
                    # Try new format

                    with open(share, encoding="utf-8") as sharefile:
                        import json
                        mylist = json.load(sharefile)

                if not isinstance(mylist, (list, dict)):
                    raise TypeError("Bad data in file %(sharesdb)s" % {'sharesdb': share})

                username = share.replace('\\', os.sep).split(os.sep)[-1]
                self.userbrowse.show_user(username)

                if username in self.userbrowse.users:
                    self.userbrowse.users[username].load_shares(mylist)

            except Exception as msg:
                log.add(_("Loading Shares from disk failed: %(error)s"), {'error': msg})

    """ Buddy List """

    def verify_buddy_list_mode(self, mode):

        if mode not in ("always", "chatrooms", "tab"):
            return "tab"

        return mode

    """ Private Chat """

    def on_settings_logging(self, widget):
        self.on_settings(page='Logging')

    def on_get_private_chat(self, widget, *args):

        text = widget.get_text()

        if not text:
            return

        self.privatechats.send_message(text, show_user=True)
        clear_entry(widget)

    """ Chat """

    def auto_replace(self, message):
        if self.np.config.sections["words"]["replacewords"]:
            autoreplaced = self.np.config.sections["words"]["autoreplaced"]
            for word, replacement in autoreplaced.items():
                message = message.replace(str(word), str(replacement))

        return message

    def censor_chat(self, message):
        if self.np.config.sections["words"]["censorwords"]:
            filler = self.np.config.sections["words"]["censorfill"]
            censored = self.np.config.sections["words"]["censored"]
            for word in censored:
                word = str(word)
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

    def on_create_room(self, widget, *args):

        room = widget.get_text()
        private = self.RoomType.get_active()

        self.np.queue.put(slskmessages.JoinRoom(room, private))
        widget.set_text("")

    def on_show_chat_buttons(self, widget=None):

        if widget is not None:
            show = widget.get_active()
            self.np.config.sections["ui"]["chat_hidebuttons"] = (not show)

        for room in self.chatrooms.joinedrooms.values():
            room.on_show_chat_buttons(not self.np.config.sections["ui"]["chat_hidebuttons"])

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
            self.away = True
            self._apply_away_state()

        return False

    def on_disable_auto_away(self, *args):
        if self.autoaway:
            self.autoaway = False

            if self.away:
                # Disable away mode if not already done
                self.away = False
                self._apply_away_state()

        if self.awaytimerid is not None:
            self.remove_away_timer(self.awaytimerid)

            autoaway = self.np.config.sections["server"]["autoaway"]
            if autoaway > 0:
                self.awaytimerid = GLib.timeout_add(1000 * 60 * autoaway, self.on_auto_away)
            else:
                self.awaytimerid = None

    """ User Actions """

    def on_add_user(self, widget, *args):
        self.userlist.on_add_user(widget)

    def on_settings_ban_ignore(self, widget):
        self.on_settings(page='BanList')

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
                self.settingswindow.pages["IgnoreList"].set_settings(self.np.config.sections)

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
                self.settingswindow.pages["IgnoreList"].set_settings(self.np.config.sections)

    def on_un_ignore_ip(self, user):
        ipignorelist = self.np.config.sections["server"]["ipignorelist"]

        if self.user_ip_is_ignored(user):
            ip = self.ignored_user_ip(user)

            if ip is not None:
                del ipignorelist[ip]
                self.np.config.write_configuration()

                if self.settingswindow is not None:
                    self.settingswindow.pages["IgnoreList"].set_settings(self.np.config.sections)
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
                self.settingswindow.pages["IgnoreList"].set_settings(self.np.config.sections)

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
                self.settingswindow.pages["BanList"].set_settings(self.np.config.sections)

    def on_un_block_user(self, user):
        if self.user_ip_is_blocked(user):
            ip = self.blocked_user_ip(user)

            if ip is not None:
                del self.np.config.sections["server"]["ipblocklist"][ip]
                self.np.config.write_configuration()

                if self.settingswindow is not None:
                    self.settingswindow.pages["BanList"].set_settings(self.np.config.sections)
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
                self.settingswindow.pages["BanList"].set_settings(self.np.config.sections)

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

    def popup_message(self, popup):
        dialog = Gtk.MessageDialog(type=Gtk.MessageType.WARNING, buttons=Gtk.ButtonsType.OK, message_format=popup.title)
        dialog.format_secondary_text(popup.message)
        dialog.connect('response', lambda dialog, response: dialog.destroy())
        dialog.show()

    def focus_combobox(self, button):

        # We have the button of a combobox, find the entry
        parent = button.get_parent()

        if parent is None:
            return

        if isinstance(parent, Gtk.ComboBox):
            entry = parent.get_child()
            entry.grab_focus()
            return

        self.focus_combobox(parent)

    def get_status_image(self, status):
        if status == 1:
            return self.images["away"]
        elif status == 2:
            return self.images["online"]
        else:
            return self.images["offline"]

    def has_user_flag(self, user, country):

        if not self.get_flag_image(country):
            return

        self.chatrooms.set_user_flag(user, country)
        self.userlist.set_user_flag(user, country)

    def on_settings_downloads(self, widget):
        self.on_settings(page='Downloads')

    def on_settings_uploads(self, widget):
        self.on_settings(page='Uploads')

    def set_clipboard_url(self, user, path):
        import urllib.parse
        self.clip.set_text("slsk://" + urllib.parse.quote("%s/%s" % (user, path.replace("\\", "/"))), -1)
        self.clip_data = "slsk://" + urllib.parse.quote("%s/%s" % (user, path.replace("\\", "/")))

    """ Log Window """

    def log_callback(self, timestamp_format, debug_level, msg):

        if not self.shutdown:
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

        append_line(self.LogWindow, msg, scroll=should_scroll, find_urls=False)

        return False

    def on_log_window_clicked(self, widget, event):

        if triggers_context_menu(event):
            return self.on_popup_log_menu(widget)

        return False

    def on_popup_log_menu(self, widget):
        self.logpopupmenu.popup()
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

    def on_view_debug_logs(self, widget):

        log_path = self.np.config.sections["logging"]["debuglogsdir"]

        try:
            if not os.path.isdir(log_path):
                os.makedirs(log_path)

            open_file_path(self.np.config.sections["logging"]["debuglogsdir"])

        except Exception as e:
            log.add("Failed to open debug log folder: %s", e)

    def on_view_transfer_log(self, widget):
        open_log(self.np.config.sections["logging"]["transferslogsdir"], "transfers")

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

        self.Statusbar.set_text(msg)
        self.Statusbar.set_tooltip_text(msg)

        if orig_msg and should_log:
            log.add(orig_msg, msg_args)

    def set_user_status(self, status):
        self.UserStatus.set_text(status)

    def set_socket_status(self, status):
        self.SocketStatus.set_text("%(current)s/%(limit)s" % {'current': status, 'limit': slskproto.MAXSOCKETS})

    def show_scan_progress(self, sharestype):

        self.scan_progress_indeterminate = True

        if sharestype == "normal":
            GLib.idle_add(self.SharesProgress.show)
        else:
            GLib.idle_add(self.BuddySharesProgress.show)

    def set_scan_progress(self, sharestype, value):

        self.scan_progress_indeterminate = False

        if sharestype == "normal":
            GLib.idle_add(self.SharesProgress.set_fraction, value)
        else:
            GLib.idle_add(self.BuddySharesProgress.set_fraction, value)

    def set_scan_indeterminate(self, sharestype):
        _thread.start_new_thread(self._set_scan_indeterminate, (sharestype,))

    def _set_scan_indeterminate(self, sharestype):

        while self.scan_progress_indeterminate:
            if sharestype == "normal":
                GLib.idle_add(self.SharesProgress.pulse)
            else:
                GLib.idle_add(self.BuddySharesProgress.pulse)

            time.sleep(0.2)

    def hide_scan_progress(self, sharestype):

        if sharestype == "normal":
            GLib.idle_add(self.SharesProgress.hide)
        else:
            GLib.idle_add(self.BuddySharesProgress.hide)

    def update_bandwidth(self):

        def _bandwidth(line):
            bandwidth = 0.0
            num_active_users = 0

            for i in line:
                speed = i.speed
                if speed is not None:
                    bandwidth = bandwidth + speed
                    num_active_users += 1

            return human_speed(bandwidth), num_active_users

        def _users(transfers, users):
            return len(users), len(transfers)

        if self.np.transfers is not None:
            down, active_usersdown = _bandwidth(self.np.transfers.downloads)
            up, active_usersup = _bandwidth(self.np.transfers.uploads)
            total_usersdown, filesdown = _users(self.np.transfers.downloads, self.downloads.users)
            total_usersup, filesup = _users(self.np.transfers.uploads, self.uploads.users)
        else:
            down = up = human_speed(0.0)
            filesup = filesdown = total_usersdown = total_usersup = active_usersdown = active_usersup = 0

        self.DownloadUsers.set_text(str(total_usersdown))
        self.UploadUsers.set_text(str(total_usersup))
        self.DownloadFiles.set_text(str(filesdown))
        self.UploadFiles.set_text(str(filesup))

        self.DownStatus.set_text("%(speed)s (%(num)i)" % {'num': active_usersdown, 'speed': down})
        self.UpStatus.set_text("%(speed)s (%(num)i)" % {'num': active_usersup, 'speed': up})

        self.tray.set_transfer_status(self.tray_download_template % {'speed': down}, self.tray_upload_template % {'speed': up})

    """ Settings """

    def on_settings_updated(self, widget, msg):

        output = self.settingswindow.get_settings()

        if not isinstance(output, tuple):
            return

        needportmap, needrescan, needcolors, needcompletion, config = output

        for key, data in config.items():
            self.np.config.sections[key].update(data)

        config = self.np.config.sections

        self.np.update_debug_log_options()

        # UPnP
        if (not config["server"]["upnp"] or needportmap) and self.np.upnp_timer:
            self.np.upnp_timer.cancel()

        if needportmap:
            self.np.upnp_interval = config["server"]["upnp_interval"]
            _thread.start_new_thread(self.np.add_upnp_portmapping, ())

        # Download/upload limits
        if self.np.transfers:
            self.np.transfers.update_limits()

        # Search
        if self.searches:
            self.searches.maxdisplayedresults = config["searches"]["max_displayed_results"]
            self.searches.maxstoredresults = config["searches"]["max_stored_results"]

        # Modify GUI
        self.downloads.update_download_filters()
        self.np.config.write_configuration()

        if not config["ui"]["trayicon"] and self.tray.is_tray_icon_visible():
            self.tray.hide()

        elif config["ui"]["trayicon"] and not self.tray.is_tray_icon_visible():
            self.tray.load()

        if needcompletion:
            self.chatrooms.update_completions()
            self.privatechats.update_completions()

        dark_mode_state = config["ui"]["dark_mode"]
        Gtk.Settings.get_default().set_property("gtk-application-prefer-dark-theme", dark_mode_state)

        if needcolors:
            global_font = config["ui"]["globalfont"]

            if global_font == "Normal":
                Gtk.Settings.get_default().reset_property("gtk-font-name")
            else:
                Gtk.Settings.get_default().set_property("gtk-font-name", global_font)

            self.chatrooms.update_visuals()
            self.privatechats.update_visuals()
            self.searches.update_visuals()
            self.downloads.update_visuals()
            self.uploads.update_visuals()
            self.userinfo.update_visuals()
            self.userbrowse.update_visuals()
            self.userlist.update_visuals()
            self.interests.update_visuals()

            self.settingswindow.update_visuals()
            self.update_visuals()

        self.on_show_chat_buttons()

        # Other notebooks
        for w in (self.chatrooms, self.privatechats, self.userinfo, self.userbrowse, self.searches):
            w.set_tab_closers(config["ui"]["tabclosers"])
            w.set_reorderable(config["ui"]["tab_reorderable"])
            w.show_hilite_images(config["notifications"]["notification_tab_icons"])
            w.set_text_colors(None)

        for w in (self.privatechats, self.userinfo, self.userbrowse):
            w.show_status_images(config["ui"]["tab_status_icons"])

        # Main notebook
        for i in range(self.MainNotebook.get_n_pages()):
            tab_box = self.MainNotebook.get_nth_page(i)
            tab_label = self.MainNotebook.get_tab_label(tab_box)

            tab_label.show_hilite_image(config["notifications"]["notification_tab_icons"])
            tab_label.set_text_color(0)

            self.MainNotebook.set_tab_reorderable(tab_box, config["ui"]["tab_reorderable"])

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

        if self.np.config.need_config():
            if self.np.transfers is not None:
                self.connect_action.set_enabled(False)

            self.on_fast_configure()

        else:
            if self.np.transfers is None:
                self.connect_action.set_enabled(True)

        if msg == "ok" and not self.np.config.sections["ui"]["trayicon"]:
            self.MainWindow.present_with_time(Gdk.CURRENT_TIME)

    """ Exit """

    def on_delete_event(self, widget, event):

        if not self.np.config.sections["ui"]["exitdialog"]:
            self.save_state()
            return False

        if self.np.config.sections["ui"]["exitdialog"] == 2:
            if self.MainWindow.get_property("visible"):
                self.MainWindow.hide()
            return True

        option_dialog(
            parent=self.MainWindow,
            title=_('Close Nicotine+?'),
            message=_('Are you sure you wish to exit Nicotine+ at this time?'),
            third=_("Run in Background"),
            checkbox_label=_("Remember choice"),
            callback=self.on_quit_response
        )

        return True

    def on_hide(self, widget, event):
        widget.hide()
        return True

    def on_quit(self, *args):
        self.save_state()
        self.application.quit()

    def on_quit_response(self, dialog, response, data):
        checkbox = dialog.checkbox.get_active()

        if response == Gtk.ResponseType.OK:

            if checkbox:
                self.np.config.sections["ui"]["exitdialog"] = 0

            self.on_quit()

        elif response == Gtk.ResponseType.REJECT:
            if checkbox:
                self.np.config.sections["ui"]["exitdialog"] = 2
            if self.MainWindow.get_property("visible"):
                self.MainWindow.hide()

        dialog.destroy()

    def save_state(self):

        # Indicate that a shutdown has started, to prevent UI callbacks from networking thread
        self.shutdown = True
        self.np.manualdisconnect = True

        # Notify plugins
        self.np.pluginhandler.shutdown_notification()

        # Disable plugins
        for plugin in self.np.pluginhandler.list_installed_plugins():
            self.np.pluginhandler.disable_plugin(plugin)

        # Shut down networking thread
        server_conn = self.np.active_server_conn

        if server_conn:
            self.np.closed_connection(server_conn, server_conn.getsockname())

        self.np.protothread.abort()
        self.np.stop_timers()

        # Prevent triggering the page removal event, which sets the tab visibility to false
        self.MainNotebook.disconnect(self.page_removed_signal)

        self.np.config.sections["ui"]["maximized"] = self.MainWindow.is_maximized()
        self.np.config.sections["ui"]["last_tab_id"] = self.MainNotebook.get_current_page()

        # Explicitly hide tray icon, otherwise it will not disappear on Windows
        self.tray.hide()

        self.save_columns()

        self.np.config.write_configuration()

        # Closing up all shelves db
        self.np.shares.close_shares("normal")
        self.np.shares.close_shares("buddy")

    def save_columns(self):
        for i in (self.userbrowse, self.userlist, self.chatrooms, self.downloads, self.uploads, self.searches):
            i.save_columns()


class MainApp(Gtk.Application):

    def __init__(self, data_dir, config, plugins, trayicon, start_hidden, bindip, port):

        application_id = "org.nicotine_plus.Nicotine"

        super().__init__(application_id=application_id)
        GLib.set_application_name("Nicotine+")
        GLib.set_prgname(application_id)

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

            NicotineFrame(
                self,
                self.data_dir,
                self.config,
                self.plugins,
                self.trayicon,
                self.start_hidden,
                self.bindip,
                self.port
            )
            return

        # Show the window of the running Nicotine+ instance
        self.get_active_window().present_with_time(Gdk.CURRENT_TIME)
