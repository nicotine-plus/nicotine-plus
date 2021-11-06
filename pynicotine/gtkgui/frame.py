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
import sys
import threading
import time

import gi
from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk

from pynicotine import slskproto
from pynicotine.config import config
from pynicotine.gtkgui.chatrooms import ChatRooms
from pynicotine.gtkgui.downloads import Downloads
from pynicotine.gtkgui.fastconfigure import FastConfigureAssistant
from pynicotine.gtkgui.interests import Interests
from pynicotine.gtkgui.notifications import Notifications
from pynicotine.gtkgui.privatechat import PrivateChats
from pynicotine.gtkgui.search import Searches
from pynicotine.gtkgui.settingswindow import Settings
from pynicotine.gtkgui.statistics import Statistics
from pynicotine.gtkgui.uploads import Uploads
from pynicotine.gtkgui.userbrowse import UserBrowses
from pynicotine.gtkgui.userinfo import UserInfos
from pynicotine.gtkgui.userlist import UserList
from pynicotine.gtkgui.utils import copy_text
from pynicotine.gtkgui.widgets.filechooser import choose_file
from pynicotine.gtkgui.widgets.iconnotebook import IconNotebook
from pynicotine.gtkgui.widgets.iconnotebook import ImageLabel
from pynicotine.gtkgui.widgets.dialogs import dialog_hide
from pynicotine.gtkgui.widgets.dialogs import message_dialog
from pynicotine.gtkgui.widgets.dialogs import option_dialog
from pynicotine.gtkgui.widgets.dialogs import set_dialog_properties
from pynicotine.gtkgui.widgets.popupmenu import PopupMenu
from pynicotine.gtkgui.widgets.textentry import TextSearchBar
from pynicotine.gtkgui.widgets.textview import TextView
from pynicotine.gtkgui.widgets.theme import get_icon
from pynicotine.gtkgui.widgets.theme import load_icons
from pynicotine.gtkgui.widgets.theme import set_dark_mode
from pynicotine.gtkgui.widgets.theme import set_global_font
from pynicotine.gtkgui.widgets.theme import set_global_style
from pynicotine.gtkgui.widgets.theme import set_use_header_bar
from pynicotine.gtkgui.widgets.theme import update_widget_visuals
from pynicotine.gtkgui.widgets.trayicon import TrayIcon
from pynicotine.gtkgui.widgets.ui import UserInterface
from pynicotine.logfacility import log
from pynicotine.utils import get_latest_version
from pynicotine.utils import human_speed
from pynicotine.utils import make_version
from pynicotine.utils import open_file_path
from pynicotine.utils import open_log
from pynicotine.utils import open_uri


class NicotineFrame(UserInterface):

    def __init__(self, application, network_processor, use_trayicon, start_hidden, bindip, port, ci_mode):

        if not ci_mode:
            # Show errors in the GUI from here on
            sys.excepthook = self.on_critical_error
            threading.excepthook = self.on_critical_error_threading  # Python >= 3.8 only

        self.application = application
        self.np = network_processor
        self.ci_mode = ci_mode
        self.current_page_id = ""
        self.hamburger_menu = None
        self.checking_update = False
        self.autoaway = False
        self.awaytimerid = None
        self.bindip = bindip
        self.port = port

        # Initialize these windows/dialogs later when necessary
        self.fastconfigure = None
        self.settingswindow = None
        self.spell_checker = None

        """ Load UI """

        super().__init__("ui/mainwindow.ui")

        """ Logging """

        self.log_textview = TextView(self.LogWindow)
        TextSearchBar(self.LogWindow, self.LogSearchBar, self.LogSearchEntry)

        self.create_log_context_menu()

        if Gtk.get_major_version() == 4:
            self.MainPaned.set_resize_start_child(True)
            self.NotebooksPane.set_resize_start_child(True)
            self.NotebooksPane.set_shrink_start_child(False)
            self.NotebooksPane.set_resize_end_child(False)
            self.NotebooksPane.set_shrink_end_child(False)
        else:
            self.MainPaned.child_set_property(self.NotebooksPane, "resize", True)
            self.NotebooksPane.child_set_property(self.MainNotebook, "resize", True)
            self.NotebooksPane.child_set_property(self.MainNotebook, "shrink", False)
            self.NotebooksPane.child_set_property(self.DebugLog, "resize", False)
            self.NotebooksPane.child_set_property(self.DebugLog, "shrink", False)

        log.add_listener(self.log_callback)

        """ Configuration """

        try:
            corruptfile = None
            config.load_config()

        except Exception:
            corruptfile = ".".join([config.filename, time.strftime("%Y-%m-%d_%H_%M_%S"), "corrupt"])

            import shutil
            shutil.move(config.filename, corruptfile)

            config.load_config()

        config.gtk_version = "%s.%s.%s" % (Gtk.get_major_version(), Gtk.get_minor_version(), Gtk.get_micro_version())
        log.add("Loading GTK %s", config.gtk_version)

        """ Icons """

        load_icons()

        """ Tray Icon/Notifications """

        # Commonly accessed strings
        self.tray_download_template = _("Downloads: %(speed)s")
        self.tray_upload_template = _("Uploads: %(speed)s")

        self.tray_icon = TrayIcon(self)
        self.tray_icon.load(use_trayicon)

        self.notifications = Notifications(self)
        self.statistics = Statistics(self)

        """ Notebook Tabs """

        # Initialize main notebook
        self.initialize_main_tabs()

        # Initialize other notebooks
        self.interests = Interests(self)
        self.chatrooms = ChatRooms(self)
        self.search = Searches(self)
        self.downloads = Downloads(self)
        self.uploads = Uploads(self)
        self.userlist = UserList(self)
        self.privatechat = self.private = PrivateChats(self)
        self.userinfo = UserInfos(self)
        self.userbrowse = UserBrowses(self)

        """ Actions and Menu """

        self.set_up_actions()
        self.set_up_menu()

        """ Tab Visibility/Order """

        self.set_tab_positions()
        self.set_main_tabs_order()
        self.set_main_tabs_visibility()
        self.set_last_session_tab()

        """ Tab Signals """

        self.MainNotebook.connect("page-reordered", self.on_page_reordered)

        """ Apply UI Customizations """

        set_global_style()
        self.update_visuals()

        """ Window Properties """

        self.application.add_window(self.MainWindow)
        self.MainWindow.set_title(GLib.get_application_name())

        # Set up event controllers
        if Gtk.get_major_version() == 4:
            key_controller = Gtk.EventControllerKey()
            key_controller.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
            key_controller.connect("key-pressed", self.on_disable_auto_away)

            motion_controller = Gtk.EventControllerMotion()
            motion_controller.connect("motion", self.on_disable_auto_away)

            self.MainWindow.add_controller(key_controller)
            self.MainWindow.add_controller(motion_controller)

            self.MainWindow.connect("close-request", self.on_close_request)

        else:
            self.MainWindow.connect("key-press-event", self.on_disable_auto_away)
            self.MainWindow.connect("motion-notify-event", self.on_disable_auto_away)

            self.MainWindow.connect("delete-event", self.on_close_request)

        width = config.sections["ui"]["width"]
        height = config.sections["ui"]["height"]

        if Gtk.get_major_version() == 4:
            self.MainWindow.set_default_size(width, height)
        else:
            self.MainWindow.resize(width, height)

        if Gtk.get_major_version() == 3:
            xpos = config.sections["ui"]["xposition"]
            ypos = config.sections["ui"]["yposition"]

            # According to the pygtk doc this will be ignored my many window managers
            # since the move takes place before we do a show()
            if min(xpos, ypos) < 0:
                self.MainWindow.set_position(Gtk.WindowPosition.CENTER)
            else:
                self.MainWindow.move(xpos, ypos)

        if config.sections["ui"]["maximized"]:
            self.MainWindow.maximize()

        main_icon = get_icon("n")

        if main_icon and Gtk.get_major_version() == 3:
            self.MainWindow.set_default_icon(main_icon)
        else:
            self.MainWindow.set_default_icon_name(GLib.get_prgname())

        """ Show Window """

        # Check command line option and config option
        if not start_hidden and not config.sections["ui"]["startup_hidden"]:
            self.MainWindow.present_with_time(Gdk.CURRENT_TIME)

        if corruptfile:
            short_message = _("Your config file is corrupt")
            long_message = _("We're sorry, but it seems your configuration file is corrupt. Please reconfigure "
                             "Nicotine+.\n\nWe renamed your old configuration file to\n%(corrupt)s\nIf you open "
                             "this file with a text editor you might be able to rescue some of your settings.") % {
                                 'corrupt': corruptfile}

            message_dialog(
                parent=self.MainWindow,
                title=short_message,
                message=long_message
            )

        """ Connect """

        # Disable a few elements until we're logged in (search field, download buttons etc.)
        self.set_widget_online_status(False)

        connect_ready = network_processor.start(self, self.network_callback)

        if not connect_ready:
            self.connect_action.set_enabled(False)

            # Set up fast configure dialog
            self.on_fast_configure()

        elif config.sections["server"]["auto_connect_startup"]:
            self.np.connect()

        self.update_bandwidth()
        self.update_completions()

    """ Window State """

    def on_window_active_changed(self, window, param):

        if not window.get_property(param.name):
            return

        self.chatrooms.clear_notifications()
        self.privatechat.clear_notifications()

        if Gtk.get_major_version() == 3 and window.get_urgency_hint():
            window.set_urgency_hint(False)

    def on_window_visible_changed(self, window, param):
        self.tray_icon.update_show_hide_label()

    def save_window_state(self):

        if Gtk.get_major_version() == 4:
            width, height = self.MainWindow.get_default_size()
        else:
            width, height = self.MainWindow.get_size()
            xpos, ypos = self.MainWindow.get_position()

            config.sections["ui"]["xposition"] = xpos
            config.sections["ui"]["yposition"] = ypos

        config.sections["ui"]["height"] = height
        config.sections["ui"]["width"] = width

        config.sections["ui"]["maximized"] = self.MainWindow.is_maximized()
        config.sections["ui"]["last_tab_id"] = self.current_page_id

        for page in (self.userbrowse, self.userlist, self.chatrooms, self.downloads, self.uploads, self.search):
            page.save_columns()

    """ Init UI """

    def init_spell_checker(self):

        try:
            gi.require_version('Gspell', '1')
            from gi.repository import Gspell
            self.spell_checker = Gspell.Checker.new()

        except (ImportError, ValueError):
            self.spell_checker = False

    def update_visuals(self):
        for widget in list(self.__dict__.values()):
            update_widget_visuals(widget)

    """ Connection """

    def network_callback(self, msgs):
        GLib.idle_add(self.np.network_event, msgs)

    def server_login(self):

        if not self.np.away:
            self.set_user_status(_("Online"))

            autoaway = config.sections["server"]["autoaway"]

            if autoaway > 0:
                self.awaytimerid = GLib.timeout_add(1000 * 60 * autoaway, self.on_auto_away)
            else:
                self.awaytimerid = None
        else:
            self.set_user_status(_("Away"))

        self.set_widget_online_status(True)
        self.tray_icon.set_away(self.np.away)

    def server_disconnect(self):

        if self.awaytimerid is not None:
            self.remove_away_timer(self.awaytimerid)
            self.awaytimerid = None

        if self.autoaway:
            self.autoaway = self.np.away = False

        self.set_widget_online_status(False)
        self.tray_icon.set_connected(False)

        self.set_user_status(_("Offline"))

        # Reset transfer stats (speed, total files/users)
        self.update_bandwidth()

    def invalid_password_response(self, dialog, response_id, data):

        if response_id == Gtk.ResponseType.REJECT:
            self.on_settings(page='Network')

        dialog.destroy()

    def invalid_password(self):

        title = _("Invalid Password")
        msg = _("User %s already exists, and the password you entered is invalid. Please choose another username "
                "if this is your first time logging in.") % config.sections["server"]["login"]

        option_dialog(
            parent=self.application.get_active_window(),
            title=title,
            message=msg,
            third=_("Change Login Details"),
            cancel=False,
            callback=self.invalid_password_response
        )

    def set_widget_online_status(self, status):

        self.connect_action.set_enabled(not status)
        self.disconnect_action.set_enabled(status)
        self.away_action.set_enabled(status)
        self.get_privileges_action.set_enabled(status)

        self.PrivateChatCombo.set_sensitive(status)

        self.UserBrowseCombo.set_sensitive(status)

        if self.current_page_id == self.userbrowse.page_id:
            GLib.idle_add(lambda: self.UserBrowseEntry.grab_focus() == -1)

        self.UserInfoCombo.set_sensitive(status)

        if self.current_page_id == self.userinfo.page_id:
            GLib.idle_add(lambda: self.UserInfoEntry.grab_focus() == -1)

        self.UserSearchCombo.set_sensitive(status)
        self.SearchCombo.set_sensitive(status)

        if self.current_page_id == self.search.page_id:
            GLib.idle_add(lambda: self.SearchEntry.grab_focus() == -1)

        self.interests.RecommendationsButton.set_sensitive(status)
        self.interests.SimilarUsersButton.set_sensitive(status)

        self.downloads.TransferButtons.set_sensitive(status)
        self.uploads.TransferButtons.set_sensitive(status)

        self.ChatroomsEntry.set_sensitive(status)
        self.RoomList.set_sensitive(status)

        self.tray_icon.set_server_actions_sensitive(status)

    """ Action Callbacks """

    # File

    def on_connect(self, *args):
        self.np.connect()

    def on_disconnect(self, *args):
        self.np.disconnect()

    def on_away(self, *args):

        self.np.away = not self.np.away
        config.sections["server"]["away"] = self.np.away
        self._apply_away_state()

    def _apply_away_state(self):

        if not self.np.away:
            self.set_user_status(_("Online"))
            self.on_disable_auto_away()
        else:
            self.set_user_status(_("Away"))

        self.tray_icon.set_away(self.np.away)

        self.np.request_set_status(self.np.away and 1 or 2)
        self.away_action.set_state(GLib.Variant.new_boolean(self.np.away))

    def on_get_privileges(self, *args):

        import urllib.parse

        login = urllib.parse.quote(config.sections["server"]["login"])
        open_uri(config.privileges_url % login)
        self.np.request_check_privileges()

    def on_fast_configure(self, *args, show=True):

        if self.fastconfigure is None:
            self.fastconfigure = FastConfigureAssistant(self)

        if self.settingswindow is not None and self.settingswindow.dialog.get_property("visible"):
            return

        if show:
            self.fastconfigure.show()

    def on_settings(self, *args, page=None):

        if self.settingswindow is None:
            self.settingswindow = Settings(self)

        if self.fastconfigure is not None and self.fastconfigure.FastConfigureDialog.get_property("visible"):
            return

        self.settingswindow.set_settings()

        if page:
            self.settingswindow.set_active_page(page)

        self.settingswindow.show()

    # View

    def on_prefer_dark_mode(self, action, *args):

        state = config.sections["ui"]["dark_mode"]
        set_dark_mode(not state)
        action.set_state(GLib.Variant.new_boolean(not state))

        config.sections["ui"]["dark_mode"] = not state

    def set_show_header_bar(self, show):

        if show:
            self.remove_toolbar()
            self.set_header_bar(self.current_page_id)

        else:
            self.remove_header_bar()
            self.set_toolbar(self.current_page_id)

        set_use_header_bar(show)

    def on_show_header_bar(self, action, *args):

        state = config.sections["ui"]["header_bar"]
        self.set_show_header_bar(not state)
        action.set_state(GLib.Variant.new_boolean(not state))

        config.sections["ui"]["header_bar"] = not state

    def set_show_log(self, show):

        if show:
            self.DebugLog.show()
            self.log_textview.scroll_bottom()
        else:
            self.DebugLog.hide()

    def on_show_log(self, action, *args):

        state = config.sections["logging"]["logcollapsed"]
        self.set_show_log(state)
        action.set_state(GLib.Variant.new_boolean(state))

        config.sections["logging"]["logcollapsed"] = not state

    def set_toggle_buddy_list(self, mode):

        page_id = self.userlist.page_id

        if self.userlist.Main in self.MainPaned.get_children():

            if mode == "always":
                return

            if Gtk.get_major_version() == 4:
                self.MainPaned.set_property("end-child", None)
            else:
                self.MainPaned.remove(self.userlist.Main)

        elif self.userlist.Main in self.ChatroomsPane.get_children():

            if mode == "chatrooms":
                return

            if Gtk.get_major_version() == 4:
                self.ChatroomsPane.set_property("end-child", None)
            else:
                self.ChatroomsPane.remove(self.userlist.Main)

        elif self.userlist.Main in self.userlistvbox.get_children():

            if mode == "tab":
                return

            self.userlistvbox.remove(self.userlist.Main)
            self.hide_tab(page_id)

        if mode == "always":

            if self.userlist.Main not in self.MainPaned.get_children():
                if Gtk.get_major_version() == 4:
                    self.MainPaned.set_end_child(self.userlist.Main)
                    self.MainPaned.set_resize_end_child(False)
                else:
                    self.MainPaned.pack2(self.userlist.Main, False, True)

            self.userlist.BuddiesToolbar.show()
            self.userlist.UserLabel.hide()
            self.userlist.Main.show()
            return

        if mode == "chatrooms":

            if self.userlist.Main not in self.ChatroomsPane.get_children():
                if Gtk.get_major_version() == 4:
                    self.ChatroomsPane.set_end_child(self.userlist.Main)
                    self.ChatroomsPane.set_resize_end_child(False)
                else:
                    self.ChatroomsPane.pack2(self.userlist.Main, False, True)

            self.userlist.BuddiesToolbar.show()
            self.userlist.UserLabel.hide()
            self.userlist.Main.show()
            return

        self.userlistvbox.add(self.userlist.Main)
        self.show_tab(page_id)

        self.userlist.BuddiesToolbar.hide()
        self.userlist.UserLabel.show()
        self.userlist.Main.hide()

    def on_toggle_buddy_list(self, action, state):
        """ Function used to switch around the UI the BuddyList position """

        mode = state.get_string()

        self.set_toggle_buddy_list(mode)
        action.set_state(state)

        config.sections["ui"]["buddylistinchatrooms"] = mode

    # Shares

    def on_configure_shares(self, *args):
        self.on_settings(page='Shares')

    def on_rescan_shares(self, *args):
        self.np.shares.rescan_shares()

    def on_browse_public_shares(self, *args):
        self.np.userbrowse.browse_local_public_shares(new_request=True)

    def on_browse_buddy_shares(self, *args):
        self.np.userbrowse.browse_local_buddy_shares(new_request=True)

    # Help

    def on_keyboard_shortcuts(self, *args):

        if not hasattr(self, "shortcuts"):
            self.shortcuts = UserInterface("ui/dialogs/shortcuts.ui")
            set_dialog_properties(self.shortcuts.dialog, self.MainWindow, quit_callback=self.on_hide)

            if hasattr(Gtk.Entry.props, "show-emoji-icon"):
                # Emoji picker only available in GTK 3.24+
                self.shortcuts.emoji.show()

            # Workaround for off-centered dialog on first run
            self.shortcuts.dialog.present_with_time(Gdk.CURRENT_TIME)
            self.on_hide(self.shortcuts.dialog)

        self.shortcuts.dialog.present_with_time(Gdk.CURRENT_TIME)

    def on_transfer_statistics(self, *args):
        self.statistics.show()

    def on_report_bug(self, *args):
        open_uri(config.issue_tracker_url)

    def on_improve_translations(self, *args):
        open_uri(config.translations_url)

    def _on_check_latest(self):

        try:
            hlatest, latest, date = get_latest_version()
            myversion = int(make_version(config.version))

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

    def on_check_latest(self, *args):

        if not self.checking_update:
            thread = threading.Thread(target=self._on_check_latest)
            thread.name = "UpdateChecker"
            thread.daemon = True
            thread.start()

            self.checking_update = True

    def on_about(self, *args):

        self.about = UserInterface("ui/dialogs/about.ui")
        set_dialog_properties(self.about.dialog, self.MainWindow)

        # Override link handler with our own
        self.about.dialog.connect("activate-link", lambda x, url: open_uri(url))

        logo = get_icon("n")

        if logo:
            if Gtk.get_major_version() == 4:
                logo = Gdk.Texture.new_for_pixbuf(logo)

            self.about.dialog.set_logo(logo)
        else:
            self.about.dialog.set_logo_icon_name(GLib.get_prgname())

        if Gtk.get_major_version() == 4:
            self.about.dialog.connect("close-request", lambda x: x.destroy())
        else:
            self.about.dialog.connect("response", lambda x, y: x.destroy())

        self.about.dialog.set_version(config.version + "  •  GTK " + config.gtk_version)
        self.about.dialog.present_with_time(Gdk.CURRENT_TIME)

    """ Actions """

    def set_up_actions(self):

        # Menu Button

        action = Gio.SimpleAction.new("menu", None)
        action.connect("activate", self.on_menu)
        self.application.add_action(action)

        # File

        self.connect_action = Gio.SimpleAction.new("connect", None)
        self.connect_action.connect("activate", self.on_connect)
        self.application.add_action(self.connect_action)
        self.application.set_accels_for_action("app.connect", ["<Shift><Primary>c"])

        self.disconnect_action = Gio.SimpleAction.new("disconnect", None)
        self.disconnect_action.connect("activate", self.on_disconnect)
        self.application.add_action(self.disconnect_action)
        self.application.set_accels_for_action("app.disconnect", ["<Shift><Primary>d"])

        state = config.sections["server"]["away"]
        self.away_action = Gio.SimpleAction.new_stateful("away", None, GLib.Variant.new_boolean(state))
        self.away_action.connect("change-state", self.on_away)
        self.MainWindow.add_action(self.away_action)
        self.application.set_accels_for_action("win.away", ["<Primary>h"])

        self.get_privileges_action = Gio.SimpleAction.new("getprivileges", None)
        self.get_privileges_action.connect("activate", self.on_get_privileges)
        self.application.add_action(self.get_privileges_action)

        action = Gio.SimpleAction.new("fastconfigure", None)
        action.connect("activate", self.on_fast_configure)
        self.application.add_action(action)

        action = Gio.SimpleAction.new("settings", None)
        action.connect("activate", self.on_settings)
        self.application.add_action(action)
        self.application.set_accels_for_action("app.settings", ["<Primary>comma", "<Primary>p"])

        action = Gio.SimpleAction.new("quit", None)
        action.connect("activate", self.on_quit)
        self.application.add_action(action)
        self.application.set_accels_for_action("app.quit", ["<Primary>q"])

        # View

        state = config.sections["ui"]["dark_mode"]
        self.dark_mode_action = Gio.SimpleAction.new_stateful("preferdarkmode", None, GLib.Variant.new_boolean(state))
        self.dark_mode_action.connect("change-state", self.on_prefer_dark_mode)
        self.MainWindow.add_action(self.dark_mode_action)

        state = config.sections["ui"]["header_bar"]
        action = Gio.SimpleAction.new_stateful("showheaderbar", None, GLib.Variant.new_boolean(state))
        action.set_enabled(sys.platform != "darwin")  # Disable header bar on macOS for now due to GTK 3 perf issues
        action.connect("change-state", self.on_show_header_bar)
        self.MainWindow.add_action(action)

        state = not config.sections["logging"]["logcollapsed"]
        action = Gio.SimpleAction.new_stateful("showlog", None, GLib.Variant.new_boolean(state))
        action.connect("change-state", self.on_show_log)
        self.MainWindow.add_action(action)
        self.application.set_accels_for_action("win.showlog", ["<Primary>l"])
        self.set_show_log(state)

        state = config.sections["ui"]["buddylistinchatrooms"]

        if state not in ("tab", "chatrooms", "always"):
            state = "tab"

        self.toggle_buddy_list_action = Gio.SimpleAction.new_stateful(
            "togglebuddylist", GLib.VariantType.new("s"), GLib.Variant.new_string(state))
        self.toggle_buddy_list_action.connect("change-state", self.on_toggle_buddy_list)
        self.MainWindow.add_action(self.toggle_buddy_list_action)
        self.set_toggle_buddy_list(state)

        # Shares

        action = Gio.SimpleAction.new("configureshares", None)
        action.connect("activate", self.on_configure_shares)
        self.application.add_action(action)

        action = Gio.SimpleAction.new("rescanshares", None)
        action.connect("activate", self.on_rescan_shares)
        self.application.add_action(action)
        self.application.set_accels_for_action("app.rescanshares", ["<Shift><Primary>r"])

        action = Gio.SimpleAction.new("browsepublicshares", None)
        action.connect("activate", self.on_browse_public_shares)
        self.application.add_action(action)

        action = Gio.SimpleAction.new("browsebuddyshares", None)
        action.connect("activate", self.on_browse_buddy_shares)
        self.application.add_action(action)

        # Help

        action = Gio.SimpleAction.new("keyboardshortcuts", None)
        action.connect("activate", self.on_keyboard_shortcuts)
        action.set_enabled(hasattr(Gtk, "ShortcutsWindow"))  # Not supported in Gtk <3.20
        self.application.add_action(action)
        self.application.set_accels_for_action("app.keyboardshortcuts", ["<Primary>question", "F1"])

        action = Gio.SimpleAction.new("transferstatistics", None)
        action.connect("activate", self.on_transfer_statistics)
        self.application.add_action(action)

        action = Gio.SimpleAction.new("reportbug", None)
        action.connect("activate", self.on_report_bug)
        self.application.add_action(action)

        action = Gio.SimpleAction.new("improvetranslations", None)
        action.connect("activate", self.on_improve_translations)
        self.application.add_action(action)

        action = Gio.SimpleAction.new("checklatest", None)
        action.connect("activate", self.on_check_latest)
        self.application.add_action(action)

        action = Gio.SimpleAction.new("about", None)
        action.connect("activate", self.on_about)
        self.application.add_action(action)

        # Wishlist

        action = Gio.SimpleAction.new("wishlist", None)
        action.connect("activate", self.search.wish_list.show)
        self.application.add_action(action)
        self.application.set_accels_for_action("app.wishlist", ["<Shift><Primary>w"])

        # Notebook Tabs

        action = Gio.SimpleAction.new("tabclose", None)
        action.connect("activate", self.on_tab_close)
        self.MainWindow.add_action(action)
        self.application.set_accels_for_action("win.tabclose", ["<Primary>F4", "<Primary>w"])

        action = Gio.SimpleAction.new("tabcycle", None)
        action.connect("activate", self.on_tab_cycle)
        self.MainWindow.add_action(action)
        self.application.set_accels_for_action("win.tabcycle", ["<Primary>Tab"])

        action = Gio.SimpleAction.new("reversetabcycle", None)
        action.connect("activate", self.on_tab_cycle, True)
        self.MainWindow.add_action(action)
        self.application.set_accels_for_action("win.reversetabcycle", ["<Primary><Shift>Tab"])

        for num in range(1, 10):
            action = Gio.SimpleAction.new("primarytab" + str(num), None)
            action.connect("activate", self.on_change_primary_tab, num)
            self.MainWindow.add_action(action)
            self.application.set_accels_for_action("win.primarytab" + str(num),
                                                   ["<Primary>" + str(num), "<Alt>" + str(num)])

        # Logging

        state = ("download" in config.sections["logging"]["debugmodes"])
        action = Gio.SimpleAction.new_stateful("logdownloads", None, GLib.Variant.new_boolean(state))
        action.connect("change-state", self.on_debug_downloads)
        self.MainWindow.add_action(action)

        state = ("upload" in config.sections["logging"]["debugmodes"])
        action = Gio.SimpleAction.new_stateful("loguploads", None, GLib.Variant.new_boolean(state))
        action.connect("change-state", self.on_debug_uploads)
        self.MainWindow.add_action(action)

        state = ("search" in config.sections["logging"]["debugmodes"])
        action = Gio.SimpleAction.new_stateful("logsearches", None, GLib.Variant.new_boolean(state))
        action.connect("change-state", self.on_debug_searches)
        self.MainWindow.add_action(action)

        state = ("chat" in config.sections["logging"]["debugmodes"])
        action = Gio.SimpleAction.new_stateful("logchat", None, GLib.Variant.new_boolean(state))
        action.connect("change-state", self.on_debug_chat)
        self.MainWindow.add_action(action)

        state = ("connection" in config.sections["logging"]["debugmodes"])
        action = Gio.SimpleAction.new_stateful("logconnections", None, GLib.Variant.new_boolean(state))
        action.connect("change-state", self.on_debug_connections)
        self.MainWindow.add_action(action)

        state = ("message" in config.sections["logging"]["debugmodes"])
        action = Gio.SimpleAction.new_stateful("logmessages", None, GLib.Variant.new_boolean(state))
        action.connect("change-state", self.on_debug_messages)
        self.MainWindow.add_action(action)

        state = ("transfer" in config.sections["logging"]["debugmodes"])
        action = Gio.SimpleAction.new_stateful("logtransfers", None, GLib.Variant.new_boolean(state))
        action.connect("change-state", self.on_debug_transfers)
        self.MainWindow.add_action(action)

        state = ("miscellaneous" in config.sections["logging"]["debugmodes"])
        action = Gio.SimpleAction.new_stateful("logmiscellaneous", None, GLib.Variant.new_boolean(state))
        action.connect("change-state", self.on_debug_miscellaneous)
        self.MainWindow.add_action(action)

        # Status Bar

        state = config.sections["transfers"]["usealtlimits"]
        self.alt_speed_action = Gio.SimpleAction.new_stateful("altspeedlimit", None, GLib.Variant.new_boolean(state))
        self.alt_speed_action.connect("change-state", self.on_alternative_speed_limit)
        self.application.add_action(self.alt_speed_action)
        self.update_alternative_speed_icon(state)

    """ Primary Menus """

    def add_connection_section(self, menu):

        menu.setup(
            ("#" + _("_Connect"), "app.connect"),
            ("#" + _("_Disconnect"), "app.disconnect"),
            ("#" + _("_Away"), "win.away"),
            ("#" + _("Soulseek _Privileges"), "app.getprivileges"),
            ("", None)
        )

    def add_preferences_item(self, menu):
        menu.setup(("#" + _("_Preferences"), "app.settings"))

    def add_quit_item(self, menu):
        menu.setup(("#" + _("_Quit"), "app.quit"))

    def create_file_menu(self):

        menu = PopupMenu(self)
        self.add_connection_section(menu)
        self.add_preferences_item(menu)

        menu.setup(("", None))

        self.add_quit_item(menu)

        return menu

    def create_view_menu(self):

        menu = PopupMenu(self)
        menu.setup(
            ("$" + _("Prefer Dark _Mode"), "win.preferdarkmode"),
            ("$" + _("Use _Header Bar"), "win.showheaderbar"),
            ("$" + _("Show _Log History Pane"), "win.showlog"),
            (">" + _("L_og Categories"), self.popup_menu_log_categories),
            ("", None),
            ("O" + _("Buddy List in Separate Tab"), "win.togglebuddylist", "tab"),
            ("O" + _("Buddy List in Chat Rooms"), "win.togglebuddylist", "chatrooms"),
            ("O" + _("Buddy List Always Visible"), "win.togglebuddylist", "always")
        )

        return menu

    def add_configure_shares_section(self, menu):

        menu.setup(
            ("#" + _("_Rescan Shares"), "app.rescanshares"),
            ("#" + _("_Configure Shares"), "app.configureshares"),
            ("", None)
        )

    def add_browse_shares_section(self, menu):

        menu.setup(
            ("#" + _("_Browse Public Shares"), "app.browsepublicshares"),
            ("#" + _("Bro_wse Buddy Shares"), "app.browsebuddyshares"),
            ("", None)
        )

    def create_shares_menu(self):

        menu = PopupMenu(self)
        self.add_configure_shares_section(menu)
        self.add_browse_shares_section(menu)

        return menu

    def create_help_menu(self):

        menu = PopupMenu(self)
        menu.setup(
            ("#" + _("_Keyboard Shortcuts"), "app.keyboardshortcuts"),
            ("#" + _("_Setup Assistant"), "app.fastconfigure"),
            ("#" + _("_Transfer Statistics"), "app.transferstatistics"),
            ("", None),
            ("#" + _("Report a _Bug"), "app.reportbug"),
            ("#" + _("Improve T_ranslations"), "app.improvetranslations"),
            ("#" + _("Check _Latest Version"), "app.checklatest"),
            ("", None),
            ("#" + _("_About Nicotine+"), "app.about")
        )

        return menu

    def create_hamburger_menu(self):
        """ Menu button menu (header bar enabled) """

        menu = PopupMenu(self)
        self.add_connection_section(menu)

        menu.setup(
            (">" + _("_View"), self.create_view_menu()),
            ("", None)
        )

        self.add_configure_shares_section(menu)
        self.add_browse_shares_section(menu)

        menu.setup((">" + _("_Help"), self.create_help_menu()))
        self.add_preferences_item(menu)
        self.add_quit_item(menu)

        return menu

    def create_menu_bar(self):
        """ Classic menu bar (header bar disabled) """

        menu = PopupMenu(self)
        menu.setup(
            (">" + _("_File"), self.create_file_menu()),
            (">" + _("_View"), self.create_view_menu()),
            (">" + _("_Shares"), self.create_shares_menu()),
            (">" + _("_Help"), self.create_help_menu())
        )

        return menu

    def set_up_menu(self):

        menu = self.create_menu_bar()
        self.application.set_menubar(menu)

        self.hamburger_menu = self.create_hamburger_menu()

    def on_menu(self, *args):

        if Gtk.get_major_version() == 4:
            self.header_menu.popup()
        else:
            self.header_menu.set_active(not self.header_menu.get_active())

    """ Headerbar/toolbar """

    def set_header_bar(self, page_id):

        """ Set a 'normal' headerbar for the main window (client side decorations
        enabled) """

        self.MainWindow.set_show_menubar(False)
        self.header_menu.show()

        self.application.set_accels_for_action("app.menu", ["F10"])

        menu_parent = self.header_menu.get_parent()
        if menu_parent is not None:
            menu_parent.remove(self.header_menu)

        header_bar = getattr(self, "header_" + page_id)
        end_widget = getattr(self, page_id + "_end")
        end_widget.add(self.header_menu)

        if Gtk.get_major_version() == 4:
            self.header_menu.set_icon_name("open-menu-symbolic")

            header_bar.set_show_title_buttons(True)

        else:
            self.header_menu.set_image(self.header_menu_icon)

            # Avoid "Untitled window" in certain desktop environments
            header_bar.set_title(self.MainWindow.get_title())

            header_bar.set_has_subtitle(False)
            header_bar.set_show_close_button(True)

        header_bar.remove(end_widget)
        header_bar.pack_end(end_widget)

        # Set menu model after moving menu button to avoid GTK warnings in old GTK versions
        self.header_menu.set_menu_model(self.hamburger_menu)
        self.MainWindow.set_titlebar(header_bar)

    def set_toolbar(self, page_id):

        """ Move the headerbar widgets to a GtkBox "toolbar", and show the regular
        title bar (client side decorations disabled) """

        self.MainWindow.set_show_menubar(True)

        if not hasattr(self, page_id + "_toolbar"):
            # No toolbar needed for this page
            return

        header_bar = getattr(self, "header_" + page_id)
        toolbar = getattr(self, page_id + "_toolbar")
        toolbar_contents = getattr(self, page_id + "_toolbar_contents")

        title_widget = getattr(self, page_id + "_title")
        title_widget.set_hexpand(True)

        try:
            start_widget = getattr(self, page_id + "_start")
            header_bar.remove(start_widget)

        except AttributeError:
            # No start widget
            start_widget = None

        end_widget = getattr(self, page_id + "_end")
        header_bar.remove(end_widget)

        if Gtk.get_major_version() == 4:
            header_bar.set_title_widget(None)
        else:
            header_bar.set_custom_title(None)

        if start_widget:
            toolbar_contents.add(start_widget)

        toolbar_contents.add(title_widget)
        toolbar_contents.add(end_widget)

        toolbar.show()

    def remove_header_bar(self):

        """ Remove the current CSD headerbar, and show the regular titlebar """

        self.header_menu.set_menu_model(None)
        self.header_menu.hide()

        # Don't override builtin accelerator for menu bar
        self.application.set_accels_for_action("app.menu", [])

        self.MainWindow.unrealize()
        self.MainWindow.set_titlebar(None)
        self.MainWindow.map()

    def remove_toolbar(self):

        """ Move the GtkBox toolbar widgets back to the headerbar, and hide
        the toolbar """

        if not hasattr(self, self.current_page_id + "_toolbar"):
            # No toolbar on this page
            return

        header_bar = getattr(self, "header_" + self.current_page_id)
        toolbar = getattr(self, self.current_page_id + "_toolbar")
        toolbar_contents = getattr(self, self.current_page_id + "_toolbar_contents")

        title_widget = getattr(self, self.current_page_id + "_title")
        title_widget.set_hexpand(False)
        toolbar_contents.remove(title_widget)

        if Gtk.get_major_version() == 4:
            header_bar.set_title_widget(title_widget)
            header_bar.add = header_bar.pack_start
        else:
            header_bar.set_custom_title(title_widget)

        try:
            start_widget = getattr(self, self.current_page_id + "_start")
            toolbar_contents.remove(start_widget)
            header_bar.add(start_widget)

        except AttributeError:
            # No start widget
            pass

        end_widget = getattr(self, self.current_page_id + "_end")
        toolbar_contents.remove(end_widget)
        header_bar.pack_end(end_widget)

        toolbar.hide()

    def set_active_header_bar(self, page_id):

        """ Switch out the active headerbar for another one. This is used when
        changing the active notebook tab. """

        if config.sections["ui"]["header_bar"] and sys.platform != "darwin":
            self.set_header_bar(page_id)

        else:
            self.remove_toolbar()
            self.set_toolbar(page_id)

        self.current_page_id = page_id

    """ Main Notebook """

    def initialize_main_tabs(self):

        # Translation for the labels of tabs, icon names
        tab_data = [
            ("search", _("Search Files"), "system-search-symbolic"),
            ("downloads", _("Downloads"), "document-save-symbolic"),
            ("uploads", _("Uploads"), "emblem-shared-symbolic"),
            ("userbrowse", _("Browse Shares"), "folder-symbolic"),
            ("userinfo", _("User Info"), "avatar-default-symbolic"),
            ("private", _("Private Chat"), "mail-send-symbolic"),
            ("userlist", _("Buddies"), "contact-new-symbolic"),
            ("chatrooms", _("Chat Rooms"), "user-available-symbolic"),
            ("interests", _("Interests"), "emblem-default-symbolic")
        ]

        # Initialize tabs labels
        for i in range(self.MainNotebook.get_n_pages()):
            tab_id, tab_text, tab_icon_name = tab_data[i]
            page = self.MainNotebook.get_nth_page(i)
            page.page_id = tab_id

            # Initialize the image label
            tab_label = ImageLabel(
                tab_text,
                show_hilite_image=config.sections["notifications"]["notification_tab_icons"],
                show_status_image=True
            )

            tab_label.set_icon(tab_icon_name)
            tab_label.set_text_color()
            tab_label.show()

            # Apply tab label
            setattr(self, tab_id + "_tab_label", tab_label)
            self.MainNotebook.set_tab_label(page, tab_label)
            self.MainNotebook.set_tab_reorderable(page, True)
            self.set_tab_expand(page)

    def on_switch_page(self, notebook, page, page_num):

        # Hide widgets on previous page for a performance boost
        current_page = notebook.get_nth_page(notebook.get_current_page())

        for child in current_page.get_children():
            child.hide()

        for child in page.get_children():
            child.show()

        self.set_active_header_bar(page.page_id)

        if page == self.chatroomsvbox:
            curr_page_num = self.chatrooms.get_current_page()
            curr_page = self.chatrooms.get_nth_page(curr_page_num)

            if curr_page is not None:
                self.chatrooms.notebook.emit("switch-page", curr_page, curr_page_num)
            else:
                GLib.idle_add(lambda: self.ChatroomsEntry.grab_focus() == -1)

        elif page == self.privatevbox:
            curr_page_num = self.privatechat.get_current_page()
            curr_page = self.privatechat.get_nth_page(curr_page_num)

            if curr_page is not None:
                self.privatechat.notebook.emit("switch-page", curr_page, curr_page_num)
            else:
                GLib.idle_add(lambda: self.PrivateChatEntry.grab_focus() == -1)

        elif page == self.uploadsvbox:
            self.uploads.update(forceupdate=True)
            self.clear_tab_hilite()

            if self.uploads.Main.get_visible():
                GLib.idle_add(lambda: self.uploads.Transfers.grab_focus() == -1)

        elif page == self.downloadsvbox:
            self.downloads.update(forceupdate=True)
            self.clear_tab_hilite()

            if self.downloads.Main.get_visible():
                GLib.idle_add(lambda: self.downloads.Transfers.grab_focus() == -1)

        elif page == self.searchvbox:
            curr_page_num = self.search.get_current_page()
            curr_page = self.search.get_nth_page(curr_page_num)

            if curr_page is not None:
                self.search.notebook.emit("switch-page", curr_page, curr_page_num)

            GLib.idle_add(lambda: self.SearchEntry.grab_focus() == -1)

        elif page == self.userinfovbox:
            curr_page_num = self.userinfo.get_current_page()
            curr_page = self.userinfo.get_nth_page(curr_page_num)

            if curr_page is not None:
                self.userinfo.notebook.emit("switch-page", curr_page, curr_page_num)
            else:
                GLib.idle_add(lambda: self.UserInfoEntry.grab_focus() == -1)

        elif page == self.userbrowsevbox:
            curr_page_num = self.userbrowse.get_current_page()
            curr_page = self.userbrowse.get_nth_page(curr_page_num)

            if curr_page is not None:
                self.userbrowse.notebook.emit("switch-page", curr_page, curr_page_num)
            else:
                GLib.idle_add(lambda: self.UserBrowseEntry.grab_focus() == -1)

        elif page == self.userlistvbox:
            self.userlist.update()

            if self.userlist.Main.get_visible():
                GLib.idle_add(lambda: self.userlist.UserListTree.grab_focus() == -1)

        elif page == self.interestsvbox:
            self.interests.populate_recommendations()
            GLib.idle_add(lambda: self.interests.LikesList.grab_focus() == -1)

    def on_page_reordered(self, main_notebook, child, page_num):

        page_ids = []

        for i in range(self.MainNotebook.get_n_pages()):
            page = self.MainNotebook.get_nth_page(i)
            page_ids.append(page.page_id)

        config.sections["ui"]["modes_order"] = page_ids

    def on_tab_close(self, *args):
        """ Ctrl+W and Ctrl+F4: close current secondary tab """

        notebook_name = self.current_page_id
        notebook = getattr(self, notebook_name)

        if not isinstance(notebook, IconNotebook):
            return False

        page = notebook.get_nth_page(notebook.get_current_page())

        if page is None:
            return False

        tab_label, menu_label = notebook.get_labels(page)
        tab_label.onclose()
        return True

    def on_tab_cycle(self, widget, state, backwards=False):
        """ Ctrl+Tab and Shift+Ctrl+Tab: cycle through secondary tabs """

        notebook_name = self.current_page_id
        notebook = getattr(self, notebook_name)

        if not isinstance(notebook, IconNotebook):
            return False

        num_pages = notebook.get_n_pages()
        current_page = notebook.get_current_page()

        if backwards:
            if current_page == 0:
                notebook.set_current_page(num_pages - 1)
            else:
                notebook.prev_page()

            return True

        if current_page == (num_pages - 1):
            notebook.set_current_page(0)
        else:
            notebook.next_page()

        return True

    def on_change_primary_tab(self, widget, state, tab_num=1):
        """ Alt+1-9 or Ctrl+1-9: change main tab """

        visible_pages = []

        for i in range(self.MainNotebook.get_n_pages()):
            page = self.MainNotebook.get_nth_page(i)

            if page.get_visible():
                visible_pages.append(page)

        if len(visible_pages) < tab_num:
            return False

        page_num = self.MainNotebook.page_num(visible_pages[tab_num - 1])
        self.MainNotebook.set_current_page(page_num)
        return True

    def request_tab_hilite(self, page_id, status=1):

        if self.current_page_id == page_id:
            return

        tab_label = getattr(self, page_id + "_tab_label")

        if status == 1:
            hilite_icon = get_icon("hilite")
        else:
            hilite_icon = get_icon("hilite3")

            if tab_label.get_hilite_image() == get_icon("hilite"):
                # Chat mentions have priority over normal notifications
                return

        if hilite_icon == tab_label.get_hilite_image():
            return

        tab_label.set_hilite_image(hilite_icon)
        tab_label.set_text_color(status + 1)

    def clear_tab_hilite(self):

        tab_label = getattr(self, self.current_page_id + "_tab_label")

        if not tab_label.get_hilite_image():
            return

        tab_label.set_hilite_image(None)
        tab_label.set_text_color(0)

    def change_main_page(self, page_id):

        self.show_tab(page_id)

        try:
            page = getattr(self, page_id + "vbox")
        except AttributeError:
            return

        page_num = self.MainNotebook.page_num(page)
        self.MainNotebook.set_current_page(page_num)

    def show_tab(self, page_id):

        if page_id == self.userlist.page_id:
            self.on_toggle_buddy_list(self.toggle_buddy_list_action, GLib.Variant.new_string("tab"))

        try:
            page = getattr(self, page_id + "vbox")
        except AttributeError:
            return

        config.sections["ui"]["modes_visible"][page_id] = True
        page.show()

        self.MainNotebook.show()

    def hide_tab(self, page_id):

        try:
            page = getattr(self, page_id + "vbox")
        except AttributeError:
            return

        config.sections["ui"]["modes_visible"][page_id] = False
        page.hide()

        if self.MainNotebook.get_n_pages() <= 1:
            self.MainNotebook.hide()

    def set_main_tabs_order(self):

        order = 0

        for name in config.sections["ui"]["modes_order"]:
            try:
                page = getattr(self, name + "vbox")
                self.MainNotebook.reorder_child(page, order)
            except AttributeError:
                pass

            order += 1

    def set_main_tabs_visibility(self):

        for page_id, enabled in config.sections["ui"]["modes_visible"].items():
            if enabled:
                self.show_tab(page_id)
                continue

            self.hide_tab(page_id)

    def set_last_session_tab(self):

        # Ensure we set a header bar, by activating the "switch-page" signal at least once
        default_page = self.MainNotebook.get_nth_page(0)
        self.MainNotebook.emit("switch-page", default_page, 0)

        if not config.sections["ui"]["tab_select_previous"]:
            return

        last_tab_id = config.sections["ui"]["last_tab_id"]

        try:
            page = getattr(self, last_tab_id + "vbox")
        except AttributeError:
            return

        if page.get_visible():
            self.MainNotebook.set_current_page(self.MainNotebook.page_num(page))

    def set_tab_expand(self, page):

        tab_label = self.MainNotebook.get_tab_label(page)
        tab_position = config.sections["ui"]["tabmain"]

        if tab_position in ("Left", "Right"):
            expand = False
        else:
            expand = True

        if Gtk.get_major_version() == 4:
            self.MainNotebook.get_page(page).set_property("tab-expand", expand)
        else:
            self.MainNotebook.child_set_property(page, "tab-expand", expand)

        tab_label.set_centered(expand)

    def set_tab_positions(self):

        default_pos = Gtk.PositionType.TOP
        positions = {
            "Top": Gtk.PositionType.TOP,
            "Bottom": Gtk.PositionType.BOTTOM,
            "Left": Gtk.PositionType.LEFT,
            "Right": Gtk.PositionType.RIGHT
        }

        # Main notebook
        self.MainNotebook.set_tab_pos(positions.get(config.sections["ui"]["tabmain"], default_pos))

        # Other notebooks
        self.chatrooms.set_tab_pos(positions.get(config.sections["ui"]["tabrooms"], default_pos))
        self.privatechat.set_tab_pos(positions.get(config.sections["ui"]["tabprivate"], default_pos))
        self.userinfo.set_tab_pos(positions.get(config.sections["ui"]["tabinfo"], default_pos))
        self.userbrowse.set_tab_pos(positions.get(config.sections["ui"]["tabbrowse"], default_pos))
        self.search.set_tab_pos(positions.get(config.sections["ui"]["tabsearch"], default_pos))

    """ Search """

    def on_settings_searches(self, *args):
        self.on_settings(page='Searches')

    def on_search_method(self, *args):

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

    def on_search(self, *args):
        self.search.on_search()
        self.SearchEntry.set_text("")

    """ User Info """

    def on_settings_userinfo(self, *args):
        self.on_settings(page='UserInfo')

    def on_get_user_info(self, widget, *args):

        username = widget.get_text()

        if not username:
            return

        self.np.userinfo.request_user_info(username)
        widget.set_text("")

    """ Browse Shares """

    def on_get_shares(self, widget, *args):

        username = widget.get_text()

        if not username:
            return

        self.np.userbrowse.browse_user(username)
        widget.set_text("")

    def on_load_from_disk_selected(self, selected, data):

        for filename in selected:
            shares_list = self.np.userbrowse.get_shares_list_from_disk(filename)

            if shares_list is None:
                continue

            username = filename.replace('\\', os.sep).split(os.sep)[-1]
            self.np.userbrowse.load_local_shares_list(username, shares_list)

    def on_load_from_disk(self, *args):

        sharesdir = os.path.join(config.data_dir, "usershares")
        try:
            if not os.path.exists(sharesdir):
                os.makedirs(sharesdir)
        except Exception as msg:
            log.add(_("Can't create directory '%(folder)s', reported error: %(error)s"),
                    {'folder': sharesdir, 'error': msg})

        choose_file(
            parent=self.MainWindow,
            title=_("Select a Saved Shares List File"),
            callback=self.on_load_from_disk_selected,
            initialdir=sharesdir,
            multiple=True
        )

    """ Chat """

    def on_settings_logging(self, *args):
        self.on_settings(page='Logging')

    def on_get_private_chat(self, widget, *args):

        username = widget.get_text()

        if not username:
            return

        self.np.privatechats.show_user(username)
        widget.set_text("")

    def on_create_room_response(self, dialog, response_id, room):

        private = dialog.checkbox.get_active()
        dialog.destroy()

        if response_id == Gtk.ResponseType.OK:
            # Create a new room
            self.np.chatrooms.request_join_room(room, private)

    def on_create_room(self, widget, *args):

        room = widget.get_text()

        if not room:
            return False

        if room not in self.np.chatrooms.server_rooms and room not in self.np.chatrooms.private_rooms:
            option_dialog(
                parent=self.MainWindow,
                title=_('Create New Room?'),
                message=_('Do you really want to create a new room "%s"?') % room,
                checkbox_label=_("Make room private"),
                callback=self.on_create_room_response,
                callback_data=room
            )

        else:
            self.np.chatrooms.request_join_room(room)

        widget.set_text("")
        return True

    def update_completions(self):
        self.np.chatrooms.update_completions()
        self.np.privatechats.update_completions()

    """ Away Timer """

    def remove_away_timer(self, timerid):

        # Check that the away timer hasn't been destroyed already
        # Happens if the timer expires
        context = GLib.MainContext.default()
        if context.find_source_by_id(timerid) is not None:
            GLib.source_remove(timerid)

    def on_auto_away(self):

        if not self.np.away:
            self.autoaway = True
            self.np.away = True
            self._apply_away_state()

        return False

    def on_disable_auto_away(self, *args):

        if self.autoaway:
            self.autoaway = False

            if self.np.away:
                # Disable away mode if not already done
                self.np.away = False
                self._apply_away_state()

        if self.awaytimerid is not None:
            self.remove_away_timer(self.awaytimerid)

            autoaway = config.sections["server"]["autoaway"]
            if autoaway > 0:
                self.awaytimerid = GLib.timeout_add(1000 * 60 * autoaway, self.on_auto_away)
            else:
                self.awaytimerid = None

        return False

    """ User Actions """

    def on_add_user(self, widget, *args):
        self.userlist.on_add_user(widget)

    """ Various """

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

    def on_settings_downloads(self, *args):
        self.on_settings(page='Downloads')

    def on_settings_uploads(self, *args):
        self.on_settings(page='Uploads')

    """ Log Pane """

    def create_log_context_menu(self):

        self.popup_menu_log_categories = PopupMenu(self)
        self.popup_menu_log_categories.setup(
            ("$" + _("Downloads"), "win.logdownloads"),
            ("$" + _("Uploads"), "win.loguploads"),
            ("$" + _("Search"), "win.logsearches"),
            ("$" + _("Chat"), "win.logchat"),
            ("", None),
            ("$" + _("[Debug] Connections"), "win.logconnections"),
            ("$" + _("[Debug] Messages"), "win.logmessages"),
            ("$" + _("[Debug] Transfers"), "win.logtransfers"),
            ("$" + _("[Debug] Miscellaneous"), "win.logmiscellaneous"),
        )

        PopupMenu(self, self.LogWindow, self.on_popup_menu_log).setup(
            ("#" + _("_Find…"), self.on_find_log_window),
            ("", None),
            ("#" + _("_Copy"), self.log_textview.on_copy_text),
            ("#" + _("Copy _All"), self.log_textview.on_copy_all_text),
            ("", None),
            ("#" + _("_Open Log Folder"), self.on_view_debug_logs),
            ("#" + _("Open _Transfer Log"), self.on_view_transfer_log),
            ("", None),
            (">" + _("_Log Categories"), self.popup_menu_log_categories),
            ("", None),
            ("#" + _("Clear Log View"), self.log_textview.on_clear_all_text)
        )

    def log_callback(self, timestamp_format, msg, level):
        GLib.idle_add(self.update_log, msg, level, priority=GLib.PRIORITY_LOW)

    def update_log(self, msg, level):

        if level and level.startswith("important"):
            title = "Information" if level == "important_info" else "Error"
            message_dialog(parent=self.application.get_active_window(), title=title, message=msg)
            return

        # Keep verbose debug messages out of statusbar to make it more useful
        if level not in ("transfer", "connection", "message", "miscellaneous"):
            self.set_status_text(msg)

        self.log_textview.append_line(msg, find_urls=False)
        return False

    def on_popup_menu_log(self, menu, textview):
        actions = menu.get_actions()
        actions[_("_Copy")].set_enabled(self.log_textview.get_has_selection())

    def on_find_log_window(self, *args):
        self.LogSearchBar.set_search_mode(True)

    def on_view_debug_logs(self, *args):

        log_path = config.sections["logging"]["debuglogsdir"]

        try:
            if not os.path.isdir(log_path):
                os.makedirs(log_path)

            open_file_path(config.sections["logging"]["debuglogsdir"])

        except Exception as e:
            log.add("Failed to open debug log folder: %s", e)

    def on_view_transfer_log(self, *args):
        open_log(config.sections["logging"]["transferslogsdir"], "transfers")

    def add_debug_level(self, debug_level):

        if debug_level not in config.sections["logging"]["debugmodes"]:
            config.sections["logging"]["debugmodes"].append(debug_level)

    def remove_debug_level(self, debug_level):

        if debug_level in config.sections["logging"]["debugmodes"]:
            config.sections["logging"]["debugmodes"].remove(debug_level)

    def set_debug_level(self, action, state, level):

        if state.get_boolean():
            self.add_debug_level(level)
        else:
            self.remove_debug_level(level)

        action.set_state(state)

    def on_debug_downloads(self, action, state):
        self.set_debug_level(action, state, "download")

    def on_debug_uploads(self, action, state):
        self.set_debug_level(action, state, "upload")

    def on_debug_searches(self, action, state):
        self.set_debug_level(action, state, "search")

    def on_debug_chat(self, action, state):
        self.set_debug_level(action, state, "chat")

    def on_debug_connections(self, action, state):
        self.set_debug_level(action, state, "connection")

    def on_debug_messages(self, action, state):
        self.set_debug_level(action, state, "message")

    def on_debug_transfers(self, action, state):
        self.set_debug_level(action, state, "transfer")

    def on_debug_miscellaneous(self, action, state):
        self.set_debug_level(action, state, "miscellaneous")

    """ Status Bar """

    def set_status_text(self, msg):
        self.Statusbar.set_text(msg)
        self.Statusbar.set_tooltip_text(msg)

    def set_user_status(self, status):
        self.UserStatus.set_text(status)

    def set_socket_status(self, status):
        self.SocketStatus.set_text("%(current)s/%(limit)s" % {'current': status, 'limit': slskproto.MAXSOCKETS})

    def show_scan_progress(self):

        self.scan_progress_indeterminate = True
        GLib.idle_add(self.SharesProgress.show)

    def set_scan_progress(self, value):

        self.scan_progress_indeterminate = False
        GLib.idle_add(self.SharesProgress.set_fraction, value)

    def set_scan_indeterminate(self):
        GLib.timeout_add(100, self.pulse_scan_progress)

    def pulse_scan_progress(self):

        self.SharesProgress.pulse()

        if self.scan_progress_indeterminate:
            self.set_scan_indeterminate()

    def hide_scan_progress(self):
        GLib.idle_add(self.SharesProgress.hide)

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

        down, active_usersdown = _bandwidth(self.downloads.transfer_list)
        up, active_usersup = _bandwidth(self.uploads.transfer_list)
        total_usersdown, filesdown = _users(self.downloads.transfer_list, self.downloads.users)
        total_usersup, filesup = _users(self.uploads.transfer_list, self.uploads.users)

        self.DownloadUsers.set_text(str(total_usersdown))
        self.UploadUsers.set_text(str(total_usersup))
        self.DownloadFiles.set_text(str(filesdown))
        self.UploadFiles.set_text(str(filesup))

        self.DownStatus.set_text("%(speed)s (%(num)i)" % {'num': active_usersdown, 'speed': down})
        self.UpStatus.set_text("%(speed)s (%(num)i)" % {'num': active_usersup, 'speed': up})

        self.tray_icon.set_transfer_status(self.tray_download_template % {'speed': down},
                                           self.tray_upload_template % {'speed': up})

    def update_alternative_speed_icon(self, active):

        if active:
            icon_name = "media-skip-backward-symbolic"
        else:
            icon_name = "media-seek-backward-symbolic"

        if Gtk.get_major_version() == 4:
            self.AltSpeedButton.set_icon_name(icon_name)
            return

        self.AltSpeedButton.set_image(Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.BUTTON))

    def on_alternative_speed_limit(self, *args):

        state = config.sections["transfers"]["usealtlimits"]
        self.alt_speed_action.set_state(GLib.Variant.new_boolean(not state))

        config.sections["transfers"]["usealtlimits"] = not state

        self.update_alternative_speed_icon(not state)
        self.np.transfers.update_limits()
        self.tray_icon.set_alternative_speed_limit(not state)

    """ Settings """

    def on_settings_updated(self, widget, msg):

        output = self.settingswindow.get_settings()

        if not isinstance(output, tuple):
            return

        needportmap, needrescan, needcolors, needcompletion, need_ip_block, new_config = output

        for key, data in new_config.items():
            config.sections[key].update(data)

        # UPnP
        if not config.sections["server"]["upnp"] and self.np.upnp_timer:
            self.np.upnp_timer.cancel()

        if needportmap:
            self.np.add_upnp_portmapping()

        if need_ip_block:
            self.np.network_filter.close_blocked_ip_connections()

        # Download/upload limits
        self.np.transfers.update_limits()

        # Modify GUI
        self.np.transfers.update_download_filters()
        config.write_configuration()

        if not config.sections["ui"]["trayicon"] and self.tray_icon.is_visible():
            self.tray_icon.hide()

        elif config.sections["ui"]["trayicon"] and not self.tray_icon.is_visible():
            self.tray_icon.load()

        if needcompletion:
            self.update_completions()

        dark_mode_state = config.sections["ui"]["dark_mode"]
        set_dark_mode(dark_mode_state)
        self.dark_mode_action.set_state(GLib.Variant.new_boolean(dark_mode_state))

        if needcolors:
            set_global_font(config.sections["ui"]["globalfont"])

            self.chatrooms.update_visuals()
            self.privatechat.update_visuals()
            self.search.update_visuals()
            self.downloads.update_visuals()
            self.uploads.update_visuals()
            self.userinfo.update_visuals()
            self.userbrowse.update_visuals()
            self.userlist.update_visuals()
            self.interests.update_visuals()

            self.settingswindow.update_visuals()
            self.update_visuals()

        self.chatrooms.toggle_chat_buttons()
        self.search.populate_search_history()

        # Other notebooks
        for w in (self.chatrooms, self.privatechat, self.userinfo, self.userbrowse, self.search):
            w.set_tab_closers(config.sections["ui"]["tabclosers"])
            w.show_hilite_images(config.sections["notifications"]["notification_tab_icons"])
            w.set_text_colors(None)

        for w in (self.privatechat, self.userinfo, self.userbrowse):
            w.show_status_images(config.sections["ui"]["tab_status_icons"])

        # Main notebook
        self.set_tab_positions()
        self.set_main_tabs_visibility()

        for i in range(self.MainNotebook.get_n_pages()):
            page = self.MainNotebook.get_nth_page(i)
            tab_label = self.MainNotebook.get_tab_label(page)

            tab_label.show_hilite_image(config.sections["notifications"]["notification_tab_icons"])
            tab_label.set_text_color(0)
            self.set_tab_expand(page)

        self.np.transfers.check_upload_queue()

        if msg == "ok" and needrescan:
            self.np.shares.rescan_shares()

        if config.need_config():
            self.connect_action.set_enabled(False)
            self.on_fast_configure()

        elif not self.np.active_server_conn:
            self.connect_action.set_enabled(True)

        if msg == "ok" and not config.sections["ui"]["trayicon"]:
            self.MainWindow.present_with_time(Gdk.CURRENT_TIME)

    """ Exit """

    def on_critical_error_response(self, dialog, response_id, data):

        loop, error = data

        if response_id == Gtk.ResponseType.REJECT:
            copy_text(error)
            self.on_report_bug()
            return

        dialog.destroy()
        loop.quit()

        try:
            self.np.quit()
        except Exception:
            """ We attempt a clean shut down, but this may not be possible if
            the program didn't initialize fully. Ignore any additional errors
            in that case. """
            pass

    def on_critical_error(self, exc_type, exc_value, exc_traceback):

        from traceback import format_tb

        # Check if exception occurred in a plugin
        if self.np.pluginhandler is not None:
            traceback = exc_traceback

            while True:
                if not traceback.tb_next:
                    break

                filename = traceback.tb_frame.f_code.co_filename

                for plugin_name in self.np.pluginhandler.enabled_plugins:
                    path = self.np.pluginhandler.findplugin(plugin_name)

                    if filename.startswith(path):
                        self.np.pluginhandler.show_plugin_error(
                            plugin_name, exc_type, exc_value, exc_traceback)
                        return

                traceback = traceback.tb_next

        # Show critical error dialog
        loop = GLib.MainLoop()
        error = ("\n\nNicotine+ Version: %s\nGTK Version: %s\nPython Version: %s\n\n"
                 "Type: %s\nValue: %s\nTraceback: %s" %
                 (config.version, config.gtk_version, config.python_version, exc_type,
                  exc_value, ''.join(format_tb(exc_traceback))))

        option_dialog(
            parent=self.application.get_active_window(),
            title=_("Critical Error"),
            message=_("Nicotine+ has encountered a critical error and needs to exit. "
                      "Please copy the following message and include it in a bug report:") + error,
            third=_("Copy & Report Bug"),
            cancel=False,
            callback=self.on_critical_error_response,
            callback_data=(loop, error)
        )

        # Keep dialog open if error occurs on startup
        loop.run()

        raise exc_value

    def _on_critical_error_threading(self, args):
        raise args.exc_value

    def on_critical_error_threading(self, args):
        """ Exception that originated in a thread.
        Raising an exception here calls sys.excepthook(), which in turn shows an error dialog. """

        GLib.idle_add(self._on_critical_error_threading, args)

    def on_quit_response(self, dialog, response_id, data):

        checkbox = dialog.checkbox.get_active()
        dialog.destroy()

        if response_id == Gtk.ResponseType.OK:
            if checkbox:
                config.sections["ui"]["exitdialog"] = 0

            self.np.quit()

        elif response_id == Gtk.ResponseType.REJECT:
            if checkbox:
                config.sections["ui"]["exitdialog"] = 2

            if self.MainWindow.get_property("visible"):
                self.MainWindow.hide()

    def on_close_request(self, *args):

        if not config.sections["ui"]["exitdialog"]:
            self.np.quit()
            return True

        if config.sections["ui"]["exitdialog"] == 2:
            if self.MainWindow.get_property("visible"):
                self.MainWindow.hide()
            return True

        option_dialog(
            parent=self.MainWindow,
            title=_('Close Nicotine+?'),
            message=_('Do you really want to exit Nicotine+?'),
            third=_("Run in Background"),
            checkbox_label=_("Remember choice"),
            callback=self.on_quit_response
        )
        return True

    def on_hide(self, dialog, *args):
        dialog_hide(dialog)
        return True

    def on_quit(self, *args):
        self.np.quit()

    def quit(self):

        # Explicitly hide tray icon, otherwise it will not disappear on Windows
        self.tray_icon.hide()

        # Save window state (window size, position, columns)
        self.save_window_state()

        config.write_configuration()
        log.remove_listener(self.log_callback)

        # Terminate GtkApplication
        self.application.quit()


class Application(Gtk.Application):

    def __init__(self, network_processor, tray_icon, start_hidden, bindip, port, ci_mode, multi_instance):

        application_id = "org.nicotine_plus.Nicotine"

        super().__init__(application_id=application_id)
        GLib.set_application_name("Nicotine+")
        GLib.set_prgname(application_id)

        if multi_instance:
            self.set_flags(Gio.ApplicationFlags.NON_UNIQUE)

        self.network_processor = network_processor
        self.tray_icon = tray_icon
        self.start_hidden = start_hidden
        self.ci_mode = ci_mode
        self.bindip = bindip
        self.port = port

        try:
            Gtk.ListStore.insert_with_valuesv

        except AttributeError:
            # GTK 4 replacement
            Gtk.ListStore.insert_with_valuesv = Gtk.ListStore.insert_with_values

        try:
            Gtk.Box.add
            Gtk.Box.get_children
            Gtk.Paned.get_children

        except AttributeError:
            # GTK 4 replacement
            Gtk.Box.add = Gtk.Box.append
            Gtk.Box.get_children = Gtk.Box.__iter__
            Gtk.Paned.get_children = Gtk.Paned.__iter__

    def do_activate(self):
        if not self.get_windows():
            # Only allow one instance of the main window

            NicotineFrame(
                self,
                self.network_processor,
                self.tray_icon,
                self.start_hidden,
                self.bindip,
                self.port,
                self.ci_mode
            )
            return

        # Show the window of the running Nicotine+ instance
        window = self.get_active_window()
        window.present_with_time(Gdk.CURRENT_TIME)

        if Gtk.get_major_version() == 3:
            window.deiconify()
