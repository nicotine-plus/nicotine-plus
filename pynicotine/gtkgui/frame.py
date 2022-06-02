# COPYRIGHT (C) 2020-2022 Nicotine+ Contributors
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

import sys
import threading
import time

import gi
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk

from pynicotine.config import config
from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.chatrooms import ChatRooms
from pynicotine.gtkgui.dialogs.about import About
from pynicotine.gtkgui.dialogs.fastconfigure import FastConfigure
from pynicotine.gtkgui.dialogs.preferences import Preferences
from pynicotine.gtkgui.dialogs.shortcuts import Shortcuts
from pynicotine.gtkgui.dialogs.statistics import Statistics
from pynicotine.gtkgui.downloads import Downloads
from pynicotine.gtkgui.interests import Interests
from pynicotine.gtkgui.privatechat import PrivateChats
from pynicotine.gtkgui.search import Searches
from pynicotine.gtkgui.uploads import Uploads
from pynicotine.gtkgui.userbrowse import UserBrowses
from pynicotine.gtkgui.userinfo import UserInfos
from pynicotine.gtkgui.userlist import UserList
from pynicotine.gtkgui.utils import copy_text
from pynicotine.gtkgui.widgets.filechooser import FileChooser
from pynicotine.gtkgui.widgets.iconnotebook import TabLabel
from pynicotine.gtkgui.widgets.dialogs import MessageDialog
from pynicotine.gtkgui.widgets.dialogs import OptionDialog
from pynicotine.gtkgui.widgets.notifications import Notifications
from pynicotine.gtkgui.widgets.popupmenu import PopupMenu
from pynicotine.gtkgui.widgets.textentry import TextSearchBar
from pynicotine.gtkgui.widgets.textview import TextView
from pynicotine.gtkgui.widgets.theme import load_icons
from pynicotine.gtkgui.widgets.theme import set_dark_mode
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

    def __init__(self, application, core, use_trayicon, start_hidden, bindip, port, ci_mode):

        if not ci_mode:
            # Show errors in the GUI from here on
            self.init_exception_handler()

        self.application = application
        self.core = self.np = core  # pylint:disable=invalid-name
        self.start_hidden = start_hidden
        self.ci_mode = ci_mode
        self.current_page_id = ""
        self.checking_update = False
        self.auto_away = False
        self.away_timer = None
        self.away_cooldown_time = 0
        self.gesture_click = None
        self.scan_progress_indeterminate = False
        self.bindip = bindip
        self.port = port

        # Initialize these windows/dialogs later when necessary
        self.fast_configure = None
        self.preferences = None
        self.shortcuts = None
        self.spell_checker = None

        """ Load UI """

        super().__init__("ui/mainwindow.ui")
        (
            self.alt_speed_icon,
            self.buddy_list_container,
            self.chatrooms_buddy_list_container,
            self.chatrooms_container,
            self.chatrooms_end,
            self.chatrooms_entry,
            self.chatrooms_notebook,
            self.chatrooms_page,
            self.chatrooms_paned,
            self.chatrooms_title,
            self.chatrooms_toolbar,
            self.chatrooms_toolbar_contents,
            self.connections_label,
            self.download_files_button,
            self.download_files_label,
            self.download_status_label,
            self.download_users_button,
            self.download_users_label,
            self.downloads_content,
            self.downloads_end,
            self.downloads_expand_button,
            self.downloads_expand_icon,
            self.downloads_grouping_button,
            self.downloads_page,
            self.downloads_title,
            self.downloads_toolbar,
            self.downloads_toolbar_contents,
            self.header_bar,
            self.header_end,
            self.header_end_container,
            self.header_menu,
            self.header_title,
            self.horizontal_paned,
            self.interests_container,
            self.interests_end,
            self.interests_page,
            self.interests_title,
            self.interests_toolbar,
            self.interests_toolbar_contents,
            self.log_container,
            self.log_history_button,
            self.log_search_bar,
            self.log_search_entry,
            self.log_view,
            self.notebook,
            self.private_combobox,
            self.private_end,
            self.private_entry,
            self.private_notebook,
            self.private_page,
            self.private_title,
            self.private_toolbar,
            self.private_toolbar_contents,
            self.room_list_button,
            self.room_search_combobox,
            self.room_search_entry,
            self.scan_progress_bar,
            self.search_combobox,
            self.search_end,
            self.search_entry,
            self.search_mode_button,
            self.search_mode_label,
            self.search_notebook,
            self.search_page,
            self.search_title,
            self.search_toolbar,
            self.search_toolbar_contents,
            self.status_label,
            self.upload_files_button,
            self.upload_files_label,
            self.upload_status_label,
            self.upload_users_button,
            self.upload_users_label,
            self.uploads_content,
            self.uploads_end,
            self.uploads_expand_button,
            self.uploads_expand_icon,
            self.uploads_grouping_button,
            self.uploads_page,
            self.uploads_title,
            self.uploads_toolbar,
            self.uploads_toolbar_contents,
            self.user_search_combobox,
            self.user_search_entry,
            self.user_status_button,
            self.user_status_label,
            self.userbrowse_combobox,
            self.userbrowse_end,
            self.userbrowse_entry,
            self.userbrowse_notebook,
            self.userbrowse_page,
            self.userbrowse_title,
            self.userbrowse_toolbar,
            self.userbrowse_toolbar_contents,
            self.userinfo_combobox,
            self.userinfo_end,
            self.userinfo_entry,
            self.userinfo_notebook,
            self.userinfo_page,
            self.userinfo_title,
            self.userinfo_toolbar,
            self.userinfo_toolbar_contents,
            self.userlist_content,
            self.userlist_end,
            self.userlist_page,
            self.userlist_title,
            self.userlist_toolbar,
            self.userlist_toolbar_contents,
            self.vertical_paned,
            self.window
        ) = self.widgets

        self.header_bar.pack_end(self.header_end)

        if GTK_API_VERSION >= 4:
            self.header_bar.set_show_title_buttons(True)

            self.horizontal_paned.set_resize_start_child(True)
            self.horizontal_paned.set_resize_end_child(False)
            self.chatrooms_paned.set_resize_end_child(False)

            self.vertical_paned.set_resize_start_child(True)
            self.vertical_paned.set_shrink_start_child(False)
            self.vertical_paned.set_resize_end_child(False)
            self.vertical_paned.set_shrink_end_child(False)
        else:
            self.header_bar.set_has_subtitle(False)
            self.header_bar.set_show_close_button(True)

            self.horizontal_paned.child_set_property(self.vertical_paned, "resize", True)
            self.horizontal_paned.child_set_property(self.buddy_list_container, "resize", False)
            self.chatrooms_paned.child_set_property(self.chatrooms_buddy_list_container, "resize", False)

            self.vertical_paned.child_set_property(self.notebook, "resize", True)
            self.vertical_paned.child_set_property(self.notebook, "shrink", False)
            self.vertical_paned.child_set_property(self.log_container, "resize", False)
            self.vertical_paned.child_set_property(self.log_container, "shrink", False)

        """ Logging """

        self.log_view = TextView(self.log_view)
        self.log_search_bar = TextSearchBar(self.log_view.textview, self.log_search_bar, self.log_search_entry)

        self.create_log_context_menu()
        log.add_listener(self.log_callback)

        """ Configuration """

        config.load_config()
        config.gtk_version = "%s.%s.%s" % (GTK_API_VERSION, Gtk.get_minor_version(), Gtk.get_micro_version())
        log.add(_("Loading %(program)s %(version)s"), {"program": "GTK", "version": config.gtk_version})

        """ Icons """

        load_icons()

        """ Tray Icon/Notifications """

        self.tray_icon = TrayIcon(self, core, use_trayicon)
        self.notifications = Notifications(self, core)
        self.statistics = Statistics(self, core)

        """ Notebook Tabs """

        # Initialize main notebook
        self.initialize_main_tabs()

        # Initialize other notebooks
        self.interests = Interests(self, core)
        self.chatrooms = ChatRooms(self, core)
        self.search = Searches(self, core)
        self.downloads = Downloads(self, core)
        self.uploads = Uploads(self, core)
        self.userlist = UserList(self, core)
        self.privatechat = self.private = PrivateChats(self, core)
        self.userinfo = UserInfos(self, core)
        self.userbrowse = UserBrowses(self, core)

        """ Actions and Menu """

        self.set_up_actions()
        self.set_up_menu()

        """ Tab Visibility/Order """

        self.set_tab_positions()
        self.set_main_tabs_order()
        self.set_main_tabs_visibility()
        self.set_last_session_tab()

        """ Apply UI Customizations """

        set_global_style()
        self.update_visuals()

    """ Initialize """

    def setup(self):

        if self.preferences is not None and self.preferences.dialog.get_property("visible"):
            return

        if self.fast_configure is None:
            self.fast_configure = FastConfigure(self, self.core)

        self.fast_configure.show()

    def init_window(self):

        # Set main window title and icon
        self.window.set_title(config.application_name)
        self.window.set_default_icon_name(config.application_id)

        # Set main window size
        self.window.set_default_size(width=config.sections["ui"]["width"],
                                     height=config.sections["ui"]["height"])

        # Set main window position
        if GTK_API_VERSION == 3:
            x_pos = config.sections["ui"]["xposition"]
            y_pos = config.sections["ui"]["yposition"]

            if x_pos == -1 and y_pos == -1:
                self.window.set_position(Gtk.WindowPosition.CENTER)
            else:
                self.window.move(x_pos, y_pos)

        # Maximize main window if necessary
        if config.sections["ui"]["maximized"]:
            self.window.maximize()

        # Auto-away mode
        if GTK_API_VERSION >= 4:
            self.gesture_click = Gtk.GestureClick()
            self.window.add_controller(self.gesture_click)

            key_controller = Gtk.EventControllerKey()
            key_controller.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
            key_controller.connect("key-released", self.on_cancel_auto_away)
            self.window.add_controller(key_controller)

        else:
            self.gesture_click = Gtk.GestureMultiPress(widget=self.window)
            self.window.connect("key-release-event", self.on_cancel_auto_away)

        self.gesture_click.set_button(0)
        self.gesture_click.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        self.gesture_click.connect("pressed", self.on_cancel_auto_away)

        # Clear notifications when main window is focused
        self.window.connect("notify::is-active", self.on_window_active_changed)
        self.window.connect("notify::visible", self.on_window_visible_changed)

        # System window close (X) and window state
        if GTK_API_VERSION >= 4:
            self.window.connect("close-request", self.on_close_request)

            self.window.connect("notify::default-width", self.on_window_property_changed, "width")
            self.window.connect("notify::default-height", self.on_window_property_changed, "height")
            self.window.connect("notify::maximized", self.on_window_property_changed, "maximized")

        else:
            self.window.connect("delete-event", self.on_close_request)

            self.window.connect("size-allocate", self.on_window_size_changed)
            self.window.connect("notify::is-maximized", self.on_window_property_changed, "maximized")

        self.application.add_window(self.window)

        # Check command line option and config option
        if not self.start_hidden and not config.sections["ui"]["startup_hidden"]:
            self.show()

    def init_exception_handler(self):

        sys.excepthook = self.on_critical_error

        if hasattr(threading, "excepthook"):
            threading.excepthook = self.on_critical_error_threading
            return

        # Workaround for Python <= 3.7
        init_thread = threading.Thread.__init__

        def init_thread_excepthook(self, *args, **kwargs):

            init_thread(self, *args, **kwargs)
            run_thread = self.run

            def run_with_excepthook(*args2, **kwargs2):
                try:
                    run_thread(*args2, **kwargs2)
                except Exception:
                    GLib.idle_add(sys.excepthook, *sys.exc_info())

            self.run = run_with_excepthook

        threading.Thread.__init__ = init_thread_excepthook

    def init_spell_checker(self):

        try:
            gi.require_version('Gspell', '1')
            from gi.repository import Gspell
            self.spell_checker = Gspell.Checker()

        except (ImportError, ValueError):
            self.spell_checker = False

    def update_visuals(self):
        for widget in list(self.__dict__.values()):
            update_widget_visuals(widget)

    """ Window State """

    def on_window_active_changed(self, window, param):

        if not window.get_property(param.name):
            return

        self.chatrooms.clear_notifications()
        self.privatechat.clear_notifications()
        self.on_cancel_auto_away()

        if GTK_API_VERSION == 3 and window.get_urgency_hint():
            window.set_urgency_hint(False)

    @staticmethod
    def on_window_property_changed(window, param, config_property):
        config.sections["ui"][config_property] = window.get_property(param.name)

    @staticmethod
    def on_window_size_changed(window, _allocation):

        if config.sections["ui"]["maximized"]:
            return

        width, height = window.get_size()

        config.sections["ui"]["width"] = width
        config.sections["ui"]["height"] = height

        x_pos, y_pos = window.get_position()

        config.sections["ui"]["xposition"] = x_pos
        config.sections["ui"]["yposition"] = y_pos

    def on_window_visible_changed(self, *_args):
        self.tray_icon.update_show_hide_label()

    def on_window_hide_unhide(self, *_args):

        if self.window.get_property("visible"):
            self.window.hide()
            return

        self.show()

    def save_columns(self, *_args):
        for page in (self.userlist, self.chatrooms, self.downloads, self.uploads):
            page.save_columns()

    def show(self):

        self.window.present()

        if GTK_API_VERSION == 3:
            # Fix for Windows where minimized window is not shown when unhiding from tray
            self.window.deiconify()

    """ Connection """

    def server_login(self):
        self.set_widget_online_status(True)

    def server_disconnect(self):

        self.remove_away_timer()
        self.set_user_status(_("Offline"))

        self.set_widget_online_status(False)
        self.tray_icon.set_connected(False)

    def invalid_password_response(self, _dialog, response_id, _data):
        if response_id == 2:
            self.on_settings(page='Network')

    def invalid_password(self):

        title = _("Invalid Password")
        msg = _("User %s already exists, and the password you entered is invalid. Please choose another username "
                "if this is your first time logging in.") % config.sections["server"]["login"]

        OptionDialog(
            parent=self.window,
            title=title,
            message=msg,
            first_button=_("_Cancel"),
            second_button=_("Change _Login Details"),
            callback=self.invalid_password_response
        ).show()

    def set_widget_online_status(self, status):

        self.connect_action.set_enabled(not status)
        self.disconnect_action.set_enabled(status)
        self.away_action.set_enabled(status)
        self.get_privileges_action.set_enabled(status)
        self.tray_icon.set_server_actions_sensitive(status)

        if not status:
            return

        if self.current_page_id == self.userbrowse_page.id:
            GLib.idle_add(lambda: self.userbrowse_entry.grab_focus() == -1)

        if self.current_page_id == self.userinfo_page.id:
            GLib.idle_add(lambda: self.userinfo_entry.grab_focus() == -1)

        if self.current_page_id == self.search_page.id:
            GLib.idle_add(lambda: self.search_entry.grab_focus() == -1)

    """ Action Callbacks """

    # File

    def on_connect(self, *_args):
        self.core.connect()

    def on_disconnect(self, *_args):
        self.core.disconnect()

    def on_away(self, *_args):
        self.core.set_away_mode(not self.core.away, save_state=True)

    def on_get_privileges(self, *_args):

        import urllib.parse

        login = urllib.parse.quote(self.core.login_username)
        open_uri(config.privileges_url % login)
        self.core.request_check_privileges()

    def on_fast_configure(self, *_args):
        self.setup()

    def on_settings(self, *_args, page=None):

        if self.preferences is None:
            self.preferences = Preferences(self, self.core)

        if self.fast_configure is not None and self.fast_configure.dialog.get_property("visible"):
            return

        self.preferences.set_settings()
        self.preferences.set_active_page(page)
        self.preferences.show()

    # View

    @staticmethod
    def on_prefer_dark_mode(action, *_args):

        state = config.sections["ui"]["dark_mode"]
        set_dark_mode(not state)
        action.set_state(GLib.Variant("b", not state))

        config.sections["ui"]["dark_mode"] = not state

    def set_show_header_bar(self, show):

        if show:
            self.hide_current_toolbar()
            self.show_header_bar(self.current_page_id)

        else:
            self.hide_current_header_bar()
            self.show_toolbar(self.current_page_id)

        set_use_header_bar(show)

    def on_show_header_bar(self, action, *_args):

        state = config.sections["ui"]["header_bar"]
        self.set_show_header_bar(not state)
        action.set_state(GLib.Variant("b", not state))

        config.sections["ui"]["header_bar"] = not state

    def set_show_log(self, show):

        if show:
            self.log_view.scroll_bottom()

    def on_show_log(self, action, *_args):

        state = config.sections["logging"]["logcollapsed"]
        self.set_show_log(state)
        action.set_state(GLib.Variant("b", state))

        config.sections["logging"]["logcollapsed"] = not state

    def set_toggle_buddy_list(self, mode, force_show=True):

        if self.userlist.container.get_parent() == self.buddy_list_container:

            if mode == "always":
                return

            self.buddy_list_container.remove(self.userlist.container)
            self.buddy_list_container.hide()

        elif self.userlist.container.get_parent() == self.chatrooms_buddy_list_container:

            if mode == "chatrooms":
                return

            self.chatrooms_buddy_list_container.remove(self.userlist.container)
            self.chatrooms_buddy_list_container.hide()

        elif self.userlist.container.get_parent() == self.userlist_content:

            if mode == "tab":
                return

            self.userlist_content.remove(self.userlist.container)
            self.hide_tab(self.userlist_page)

        if mode == "always":

            if GTK_API_VERSION >= 4:
                self.buddy_list_container.append(self.userlist.container)
            else:
                self.buddy_list_container.add(self.userlist.container)

            self.userlist.toolbar.show()
            self.buddy_list_container.show()
            return

        if mode == "chatrooms":

            if GTK_API_VERSION >= 4:
                self.chatrooms_buddy_list_container.append(self.userlist.container)
            else:
                self.chatrooms_buddy_list_container.add(self.userlist.container)

            self.userlist.toolbar.show()
            self.chatrooms_buddy_list_container.show()
            return

        self.userlist.toolbar.hide()

        if GTK_API_VERSION >= 4:
            self.userlist_content.append(self.userlist.container)
        else:
            self.userlist_content.add(self.userlist.container)

        if force_show:
            self.show_tab(self.userlist_page)

    def on_toggle_buddy_list(self, action, state):
        """ Function used to switch around the UI the BuddyList position """

        mode = state.get_string()

        self.set_toggle_buddy_list(mode)
        action.set_state(state)

        config.sections["ui"]["buddylistinchatrooms"] = mode

    # Shares

    def on_configure_shares(self, *_args):
        self.on_settings(page='Shares')

    def on_rescan_shares(self, *_args):
        self.core.shares.rescan_shares()

    def on_browse_public_shares(self, *_args):
        self.core.userbrowse.browse_local_public_shares(new_request=True)

    def on_browse_buddy_shares(self, *_args):
        self.core.userbrowse.browse_local_buddy_shares(new_request=True)

    # Help

    def on_keyboard_shortcuts(self, *_args):

        if self.shortcuts is None:
            self.shortcuts = Shortcuts(self)

        self.shortcuts.show()

    def on_transfer_statistics(self, *_args):
        self.statistics.show()

    @staticmethod
    def on_report_bug(*_args):
        open_uri(config.issue_tracker_url)

    @staticmethod
    def on_improve_translations(*_args):
        open_uri(config.translations_url)

    def _on_check_latest(self):

        def create_dialog(title, message):
            MessageDialog(parent=self.window, title=title, message=message).show()

        try:
            hlatest, latest, date = get_latest_version()
            myversion = int(make_version(config.version))

        except Exception as error:
            GLib.idle_add(create_dialog, _("Error retrieving latest version"), str(error))
            self.checking_update = False
            return

        if latest > myversion:
            version_label = _("Version %s is available") % hlatest

            if date:
                version_label += ", " + _("released on %s") % date

            GLib.idle_add(create_dialog, _("Out of date"), version_label)

        elif myversion > latest:
            GLib.idle_add(create_dialog, _("Up to date"),
                          _("You appear to be using a development version of Nicotine+."))

        else:
            GLib.idle_add(create_dialog, _("Up to date"), _("You are using the latest version of Nicotine+."))

        self.checking_update = False

    def on_check_latest(self, *_args):

        if not self.checking_update:
            thread = threading.Thread(target=self._on_check_latest)
            thread.name = "UpdateChecker"
            thread.daemon = True
            thread.start()

            self.checking_update = True

    def on_about(self, *_args):
        About(self).show()

    """ Actions """

    def set_up_actions(self):

        # Menu Button

        action = Gio.SimpleAction(name="menu")
        action.connect("activate", self.on_menu)
        self.application.add_action(action)

        # File

        self.connect_action = Gio.SimpleAction(name="connect")
        self.connect_action.connect("activate", self.on_connect)
        self.application.add_action(self.connect_action)
        self.application.set_accels_for_action("app.connect", ["<Shift><Primary>c"])

        self.disconnect_action = Gio.SimpleAction(name="disconnect", enabled=False)
        self.disconnect_action.connect("activate", self.on_disconnect)
        self.application.add_action(self.disconnect_action)
        self.application.set_accels_for_action("app.disconnect", ["<Shift><Primary>d"])

        state = config.sections["server"]["away"]
        self.away_action = Gio.SimpleAction(name="away", state=GLib.Variant("b", state), enabled=False)
        self.away_action.connect("change-state", self.on_away)
        self.window.add_action(self.away_action)
        self.application.set_accels_for_action("win.away", ["<Primary>h"])

        self.get_privileges_action = Gio.SimpleAction(name="getprivileges", enabled=False)
        self.get_privileges_action.connect("activate", self.on_get_privileges)
        self.application.add_action(self.get_privileges_action)

        action = Gio.SimpleAction(name="fastconfigure")
        action.connect("activate", self.on_fast_configure)
        self.application.add_action(action)

        action = Gio.SimpleAction(name="settings")
        action.connect("activate", self.on_settings)
        self.application.add_action(action)
        self.application.set_accels_for_action("app.settings", ["<Primary>comma", "<Primary>p"])

        action = Gio.SimpleAction(name="quit")  # Menu 'Quit' always Quits
        action.connect("activate", self.on_quit)
        self.application.add_action(action)

        # View

        state = config.sections["ui"]["dark_mode"]
        self.dark_mode_action = Gio.SimpleAction(name="preferdarkmode", state=GLib.Variant("b", state))
        self.dark_mode_action.connect("change-state", self.on_prefer_dark_mode)
        self.window.add_action(self.dark_mode_action)

        state = config.sections["ui"]["header_bar"]
        action = Gio.SimpleAction(name="showheaderbar", state=GLib.Variant("b", state))
        action.set_enabled(sys.platform != "darwin")  # Disable header bar on macOS for now due to GTK 3 perf issues
        action.connect("change-state", self.on_show_header_bar)
        self.window.add_action(action)

        state = not config.sections["logging"]["logcollapsed"]
        action = Gio.SimpleAction(name="showlog", state=GLib.Variant("b", state))
        action.connect("change-state", self.on_show_log)
        self.window.add_action(action)
        self.application.set_accels_for_action("win.showlog", ["<Primary>l"])
        self.set_show_log(state)

        state = config.sections["ui"]["buddylistinchatrooms"]

        if state not in ("tab", "chatrooms", "always"):
            state = "tab"

        self.toggle_buddy_list_action = Gio.SimpleAction(
            name="togglebuddylist", parameter_type=GLib.VariantType("s"), state=GLib.Variant("s", state))
        self.toggle_buddy_list_action.connect("change-state", self.on_toggle_buddy_list)
        self.window.add_action(self.toggle_buddy_list_action)
        self.set_toggle_buddy_list(state, force_show=False)

        # Shares

        action = Gio.SimpleAction(name="configureshares")
        action.connect("activate", self.on_configure_shares)
        self.application.add_action(action)

        action = Gio.SimpleAction(name="rescanshares")
        action.connect("activate", self.on_rescan_shares)
        self.application.add_action(action)
        self.application.set_accels_for_action("app.rescanshares", ["<Shift><Primary>r"])

        action = Gio.SimpleAction(name="browsepublicshares")
        action.connect("activate", self.on_browse_public_shares)
        self.application.add_action(action)

        action = Gio.SimpleAction(name="browsebuddyshares")
        action.connect("activate", self.on_browse_buddy_shares)
        self.application.add_action(action)

        # Help

        action = Gio.SimpleAction(name="keyboardshortcuts")
        action.connect("activate", self.on_keyboard_shortcuts)
        action.set_enabled(hasattr(Gtk, "ShortcutsWindow"))  # Not supported in Gtk <3.20
        self.application.add_action(action)
        self.application.set_accels_for_action("app.keyboardshortcuts", ["<Primary>question", "F1"])

        action = Gio.SimpleAction(name="transferstatistics")
        action.connect("activate", self.on_transfer_statistics)
        self.application.add_action(action)

        action = Gio.SimpleAction(name="reportbug")
        action.connect("activate", self.on_report_bug)
        self.application.add_action(action)

        action = Gio.SimpleAction(name="improvetranslations")
        action.connect("activate", self.on_improve_translations)
        self.application.add_action(action)

        action = Gio.SimpleAction(name="checklatest")
        action.connect("activate", self.on_check_latest)
        self.application.add_action(action)

        action = Gio.SimpleAction(name="about")
        action.connect("activate", self.on_about)
        self.application.add_action(action)

        # Search

        self.search_mode_action = Gio.SimpleAction(
            name="searchmode", parameter_type=GLib.VariantType("s"), state=GLib.Variant("s", "global"))
        self.search_mode_action.connect("change-state", self.search.on_search_mode)
        self.window.add_action(self.search_mode_action)

        action = Gio.SimpleAction(name="wishlist")
        action.connect("activate", self.search.wish_list.show)
        self.application.add_action(action)
        self.application.set_accels_for_action("app.wishlist", ["<Shift><Primary>w"])

        # Notebook Tabs

        action = Gio.SimpleAction(name="tabclose")
        action.connect("activate", self.on_tab_close)
        self.window.add_action(action)
        self.application.set_accels_for_action("win.tabclose", ["<Primary>F4", "<Primary>w"])

        action = Gio.SimpleAction(name="tabcycle")
        action.connect("activate", self.on_tab_cycle)
        self.window.add_action(action)
        self.application.set_accels_for_action("win.tabcycle", ["<Primary>Tab"])

        action = Gio.SimpleAction(name="reversetabcycle")
        action.connect("activate", self.on_tab_cycle, True)
        self.window.add_action(action)
        self.application.set_accels_for_action("win.reversetabcycle", ["<Primary><Shift>Tab"])

        for num in range(1, 10):
            action = Gio.SimpleAction(name="primarytab" + str(num))
            action.connect("activate", self.on_change_primary_tab, num)
            self.window.add_action(action)
            self.application.set_accels_for_action("win.primarytab" + str(num),
                                                   ["<Primary>" + str(num), "<Alt>" + str(num)])

        # Logging

        state = ("download" in config.sections["logging"]["debugmodes"])
        action = Gio.SimpleAction(name="logdownloads", state=GLib.Variant("b", state))
        action.connect("change-state", self.on_debug_downloads)
        self.window.add_action(action)

        state = ("upload" in config.sections["logging"]["debugmodes"])
        action = Gio.SimpleAction(name="loguploads", state=GLib.Variant("b", state))
        action.connect("change-state", self.on_debug_uploads)
        self.window.add_action(action)

        state = ("search" in config.sections["logging"]["debugmodes"])
        action = Gio.SimpleAction(name="logsearches", state=GLib.Variant("b", state))
        action.connect("change-state", self.on_debug_searches)
        self.window.add_action(action)

        state = ("chat" in config.sections["logging"]["debugmodes"])
        action = Gio.SimpleAction(name="logchat", state=GLib.Variant("b", state))
        action.connect("change-state", self.on_debug_chat)
        self.window.add_action(action)

        state = ("connection" in config.sections["logging"]["debugmodes"])
        action = Gio.SimpleAction(name="logconnections", state=GLib.Variant("b", state))
        action.connect("change-state", self.on_debug_connections)
        self.window.add_action(action)

        state = ("message" in config.sections["logging"]["debugmodes"])
        action = Gio.SimpleAction(name="logmessages", state=GLib.Variant("b", state))
        action.connect("change-state", self.on_debug_messages)
        self.window.add_action(action)

        state = ("transfer" in config.sections["logging"]["debugmodes"])
        action = Gio.SimpleAction(name="logtransfers", state=GLib.Variant("b", state))
        action.connect("change-state", self.on_debug_transfers)
        self.window.add_action(action)

        state = ("miscellaneous" in config.sections["logging"]["debugmodes"])
        action = Gio.SimpleAction(name="logmiscellaneous", state=GLib.Variant("b", state))
        action.connect("change-state", self.on_debug_miscellaneous)
        self.window.add_action(action)

        # Status Bar

        state = config.sections["transfers"]["usealtlimits"]
        self.alt_speed_action = Gio.SimpleAction(name="altspeedlimit", state=GLib.Variant("b", state))
        self.alt_speed_action.connect("change-state", self.on_alternative_speed_limit)
        self.application.add_action(self.alt_speed_action)
        self.update_alternative_speed_icon(state)

        # Window (system menu and events)

        action = Gio.SimpleAction(name="close")  # 'When closing Nicotine+'
        action.connect("activate", self.on_close_request)
        self.application.add_action(action)
        self.application.set_accels_for_action("app.close", ["<Primary>q"])

        action = Gio.SimpleAction(name="force_quit")
        action.connect("activate", self.core.quit)
        self.application.add_action(action)
        self.application.set_accels_for_action("app.force_quit", ["<Primary><Alt>q"])

    """ Primary Menus """

    @staticmethod
    def add_connection_section(menu):

        menu.add_items(
            ("#" + _("_Connect"), "app.connect"),
            ("#" + _("_Disconnect"), "app.disconnect"),
            ("#" + _("_Away"), "win.away"),
            ("#" + _("Soulseek _Privileges"), "app.getprivileges"),
            ("", None)
        )

    @staticmethod
    def add_preferences_item(menu):
        menu.add_items(("#" + _("_Preferences"), "app.settings"))

    @staticmethod
    def add_quit_item(menu):

        label = _("_Quit…") if config.sections["ui"]["exitdialog"] else _("_Quit")

        menu.add_items(
            ("", None),
            ("#" + label, "app.quit")
        )

    def create_file_menu(self):

        menu = PopupMenu(self)
        self.add_connection_section(menu)
        self.add_preferences_item(menu)
        self.add_quit_item(menu)

        return menu

    def create_view_menu(self):

        menu = PopupMenu(self)
        menu.add_items(
            ("$" + _("Prefer Dark _Mode"), "win.preferdarkmode"),
            ("$" + _("Use _Header Bar"), "win.showheaderbar"),
            ("$" + _("Show _Log History Pane"), "win.showlog"),
            ("", None),
            ("O" + _("Buddy List in Separate Tab"), "win.togglebuddylist", "tab"),
            ("O" + _("Buddy List in Chat Rooms"), "win.togglebuddylist", "chatrooms"),
            ("O" + _("Buddy List Always Visible"), "win.togglebuddylist", "always")
        )

        return menu

    @staticmethod
    def add_configure_shares_section(menu):

        menu.add_items(
            ("#" + _("_Rescan Shares"), "app.rescanshares"),
            ("#" + _("_Configure Shares"), "app.configureshares"),
            ("", None)
        )

    @staticmethod
    def add_browse_shares_section(menu):

        menu.add_items(
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
        menu.add_items(
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

        menu.add_items(
            (">" + _("_View"), self.create_view_menu()),
            ("", None)
        )

        self.add_configure_shares_section(menu)
        self.add_browse_shares_section(menu)

        menu.add_items((">" + _("_Help"), self.create_help_menu()))
        self.add_preferences_item(menu)
        self.add_quit_item(menu)

        menu.update_model()
        return menu

    def create_menu_bar(self):
        """ Classic menu bar (header bar disabled) """

        menu = PopupMenu(self)
        menu.add_items(
            (">" + _("_File"), self.create_file_menu()),
            (">" + _("_View"), self.create_view_menu()),
            (">" + _("_Shares"), self.create_shares_menu()),
            (">" + _("_Help"), self.create_help_menu())
        )

        menu.update_model()
        return menu

    def set_up_menu(self):

        menu_bar = self.create_menu_bar()
        self.application.set_menubar(menu_bar.model)

        hamburger_menu = self.create_hamburger_menu()
        self.header_menu.set_menu_model(hamburger_menu.model)

    def on_menu(self, *_args):

        if GTK_API_VERSION >= 4:
            self.header_menu.popup()
        else:
            self.header_menu.set_active(not self.header_menu.get_active())

    """ Headerbar/toolbar """

    def show_header_bar(self, page_id):
        """ Set a headerbar for the main window (client side decorations enabled) """

        if self.window.get_titlebar() != self.header_bar:
            self.window.set_titlebar(self.header_bar)

            self.application.set_accels_for_action("app.menu", ["F10"])
            self.window.set_show_menubar(False)

            if GTK_API_VERSION == 3:
                # Avoid "Untitled window" in certain desktop environments
                self.header_bar.set_title(self.window.get_title())

        title_widget = getattr(self, page_id + "_title")
        title_widget.get_parent().remove(title_widget)

        end_widget = getattr(self, page_id + "_end")
        end_widget.get_parent().remove(end_widget)

        if GTK_API_VERSION >= 4:
            self.header_title.append(title_widget)
            self.header_end_container.append(end_widget)
        else:
            self.header_title.add(title_widget)
            self.header_end_container.add(end_widget)

    def hide_current_header_bar(self):
        """ Hide the current CSD headerbar """

        if not self.current_page_id:
            return

        title_widget = getattr(self, self.current_page_id + "_title")
        end_widget = getattr(self, self.current_page_id + "_end")
        self.header_title.remove(title_widget)
        self.header_end_container.remove(end_widget)

        toolbar = getattr(self, self.current_page_id + "_toolbar_contents")

        if GTK_API_VERSION >= 4:
            toolbar.append(title_widget)
            toolbar.append(end_widget)
        else:
            toolbar.add(title_widget)
            toolbar.add(end_widget)

    def show_toolbar(self, page_id):
        """ Show the non-CSD toolbar """

        if not self.window.get_show_menubar():
            self.window.set_show_menubar(True)

            # Don't override builtin accelerator for menu bar
            self.application.set_accels_for_action("app.menu", [])
            self.header_menu.get_popover().hide()

            if self.window.get_titlebar():
                self.window.unrealize()
                self.window.set_titlebar(None)
                self.window.map()

        toolbar = getattr(self, page_id + "_toolbar")
        toolbar.show()

    def hide_current_toolbar(self):
        """ Hide the current toolbar """

        if not self.current_page_id:
            return

        toolbar = getattr(self, self.current_page_id + "_toolbar")
        toolbar.hide()

    def set_active_header_bar(self, page_id):
        """ Switch out the active headerbar for another one. This is used when
        changing the active notebook tab. """

        if config.sections["ui"]["header_bar"] and sys.platform != "darwin":
            self.hide_current_header_bar()
            self.show_header_bar(page_id)
        else:
            self.hide_current_toolbar()
            self.show_toolbar(page_id)

        self.current_page_id = page_id

        if self.application.get_active_window():
            config.sections["ui"]["last_tab_id"] = page_id

    """ Main Notebook """

    def initialize_main_tabs(self):

        # Translation for the labels of tabs, icon names
        tab_data = [
            ("search", _("Search Files"), "system-search-symbolic"),
            ("downloads", _("Downloads"), "document-save-symbolic"),
            ("uploads", _("Uploads"), "emblem-shared-symbolic"),
            ("userbrowse", _("Browse Shares"), "folder-symbolic"),
            ("userinfo", _("User Info"), "avatar-default-symbolic"),
            ("private", _("Private Chat"), "mail-unread-symbolic"),
            ("userlist", _("Buddies"), "contact-new-symbolic"),
            ("chatrooms", _("Chat Rooms"), "user-available-symbolic"),
            ("interests", _("Interests"), "emblem-default-symbolic")
        ]

        # Initialize tabs labels
        for i in range(self.notebook.get_n_pages()):
            tab_id, tab_text, tab_icon_name = tab_data[i]
            page = self.notebook.get_nth_page(i)
            page.id = tab_id

            tab_label = TabLabel(tab_text)
            tab_label.set_start_icon_name(tab_icon_name)
            tab_label.show()

            # Apply tab label
            self.notebook.set_tab_label(page, tab_label)
            self.notebook.set_tab_reorderable(page, True)
            self.set_tab_expand(page)

    def on_switch_page(self, notebook, page, _page_num):

        current_page = notebook.get_nth_page(notebook.get_current_page())

        # Hide container widget on previous page for a performance boost
        if GTK_API_VERSION >= 4:
            current_page.get_first_child().hide()
            page.get_first_child().show()
        else:
            current_page.get_children()[0].hide()
            page.get_children()[0].show()

        self.set_active_header_bar(page.id)

        if page == self.chatrooms_page:
            curr_page_num = self.chatrooms.get_current_page()
            curr_page = self.chatrooms.get_nth_page(curr_page_num)

            if curr_page is not None:
                self.chatrooms.notebook.emit("switch-page", curr_page, curr_page_num)
            else:
                GLib.idle_add(lambda: self.chatrooms_entry.grab_focus() == -1)

        elif page == self.private_page:
            curr_page_num = self.privatechat.get_current_page()
            curr_page = self.privatechat.get_nth_page(curr_page_num)

            if curr_page is not None:
                self.privatechat.notebook.emit("switch-page", curr_page, curr_page_num)
            else:
                GLib.idle_add(lambda: self.private_entry.grab_focus() == -1)

        elif page == self.uploads_page:
            self.uploads.update_model(forceupdate=True)
            self.remove_tab_hilite(self.uploads_page)

            if self.uploads.container.get_visible():
                GLib.idle_add(lambda: self.uploads.tree_view.grab_focus() == -1)

        elif page == self.downloads_page:
            self.downloads.update_model(forceupdate=True)
            self.remove_tab_hilite(self.downloads_page)

            if self.downloads.container.get_visible():
                GLib.idle_add(lambda: self.downloads.tree_view.grab_focus() == -1)

        elif page == self.search_page:
            curr_page_num = self.search.get_current_page()
            curr_page = self.search.get_nth_page(curr_page_num)

            if curr_page is not None:
                self.search.notebook.emit("switch-page", curr_page, curr_page_num)

            GLib.idle_add(lambda: self.search_entry.grab_focus() == -1)

        elif page == self.userinfo_page:
            curr_page_num = self.userinfo.get_current_page()
            curr_page = self.userinfo.get_nth_page(curr_page_num)

            if curr_page is not None:
                self.userinfo.notebook.emit("switch-page", curr_page, curr_page_num)
            else:
                GLib.idle_add(lambda: self.userinfo_entry.grab_focus() == -1)

        elif page == self.userbrowse_page:
            curr_page_num = self.userbrowse.get_current_page()
            curr_page = self.userbrowse.get_nth_page(curr_page_num)

            if curr_page is not None:
                self.userbrowse.notebook.emit("switch-page", curr_page, curr_page_num)
            else:
                GLib.idle_add(lambda: self.userbrowse_entry.grab_focus() == -1)

        elif page == self.userlist_page:
            self.userlist.update()

            if self.userlist.container.get_visible():
                GLib.idle_add(lambda: self.userlist.list_view.grab_focus() == -1)

        elif page == self.interests_page:
            self.interests.populate_recommendations()
            GLib.idle_add(lambda: self.interests.likes_list_view.grab_focus() == -1)

    def on_page_reordered(self, *_args):

        if not self.application.get_active_window():
            # Don't save the tab order until the window is ready
            return

        page_ids = []

        for i in range(self.notebook.get_n_pages()):
            page = self.notebook.get_nth_page(i)
            page_ids.append(page.id)

        config.sections["ui"]["modes_order"] = page_ids

    def on_tab_close(self, *_args):
        """ Ctrl+W and Ctrl+F4: close current secondary tab """

        try:
            notebook = getattr(self, self.current_page_id + "_notebook")

        except AttributeError:
            return False

        page = notebook.get_nth_page(notebook.get_current_page())

        if page is None:
            return False

        tab_label = notebook.get_tab_label(page)
        tab_label.close_callback()
        return True

    def on_tab_cycle(self, _widget, _state, backwards=False):
        """ Ctrl+Tab and Shift+Ctrl+Tab: cycle through secondary tabs """

        try:
            notebook = getattr(self, self.current_page_id + "_notebook")

        except AttributeError:
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

    def on_change_primary_tab(self, _widget, _state, tab_num=1):
        """ Alt+1-9 or Ctrl+1-9: change main tab """

        visible_pages = []

        for i in range(self.notebook.get_n_pages()):
            page = self.notebook.get_nth_page(i)

            if page.get_visible():
                visible_pages.append(page)

        if len(visible_pages) < tab_num:
            return False

        page_num = self.notebook.page_num(visible_pages[tab_num - 1])
        self.notebook.set_current_page(page_num)
        return True

    def request_tab_hilite(self, page, mentioned=False):
        tab_label = self.notebook.get_tab_label(page)
        tab_label.request_hilite(mentioned)

    def remove_tab_hilite(self, page):
        tab_label = self.notebook.get_tab_label(page)
        tab_label.remove_hilite()

    def change_main_page(self, page):

        self.show_tab(page)

        page_num = self.notebook.page_num(page)
        self.notebook.set_current_page(page_num)

    def show_tab(self, page):

        if page == self.userlist_page:
            self.on_toggle_buddy_list(self.toggle_buddy_list_action, GLib.Variant("s", "tab"))

        config.sections["ui"]["modes_visible"][page.id] = True
        page.show()

        self.notebook.set_show_tabs(True)

    def hide_tab(self, page):

        config.sections["ui"]["modes_visible"][page.id] = False
        page.hide()

        if self.notebook.get_n_pages() <= 1:
            self.notebook.set_show_tabs(False)

    def set_main_tabs_order(self):

        for order, page_id in enumerate(config.sections["ui"]["modes_order"]):
            try:
                page = getattr(self, page_id + "_page")

            except AttributeError:
                continue

            self.notebook.reorder_child(page, order)

    def set_main_tabs_visibility(self):

        visible_tab_found = False

        for i in range(self.notebook.get_n_pages()):
            page = self.notebook.get_nth_page(i)

            if config.sections["ui"]["modes_visible"].get(page.id, True):
                visible_tab_found = True
                self.show_tab(page)
                continue

            self.hide_tab(page)

        if not visible_tab_found:
            # Ensure at least one tab is visible
            self.show_tab(self.search_page)

    def set_last_session_tab(self):

        if not config.sections["ui"]["tab_select_previous"]:
            return

        last_tab_id = config.sections["ui"]["last_tab_id"]

        try:
            page = getattr(self, last_tab_id + "_page")

        except AttributeError:
            return

        if page.get_visible():
            self.notebook.set_current_page(self.notebook.page_num(page))

    def set_tab_expand(self, page):

        tab_label = self.notebook.get_tab_label(page)
        tab_position = config.sections["ui"]["tabmain"]
        expand = tab_position in ("Top", "Bottom")

        if GTK_API_VERSION >= 4:
            self.notebook.get_page(page).set_property("tab-expand", expand)
        else:
            self.notebook.child_set_property(page, "tab-expand", expand)

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
        self.notebook.set_tab_pos(positions.get(config.sections["ui"]["tabmain"], default_pos))

        # Other notebooks
        self.chatrooms.set_tab_pos(positions.get(config.sections["ui"]["tabrooms"], default_pos))
        self.privatechat.set_tab_pos(positions.get(config.sections["ui"]["tabprivate"], default_pos))
        self.userinfo.set_tab_pos(positions.get(config.sections["ui"]["tabinfo"], default_pos))
        self.userbrowse.set_tab_pos(positions.get(config.sections["ui"]["tabbrowse"], default_pos))
        self.search.set_tab_pos(positions.get(config.sections["ui"]["tabsearch"], default_pos))

    """ Search """

    def on_settings_searches(self, *_args):
        self.on_settings(page='Searches')

    def on_search(self, *_args):
        self.search.on_search()
        self.search_entry.set_text("")

    """ User Info """

    def on_settings_userinfo(self, *_args):
        self.on_settings(page='UserInfo')

    def on_get_user_info(self, widget, *_args):

        username = widget.get_text()

        if not username:
            return

        self.core.userinfo.request_user_info(username)
        widget.set_text("")

    """ Browse Shares """

    def on_get_shares(self, widget, *_args):

        entry_text = widget.get_text()

        if not entry_text:
            return

        if entry_text.startswith("slsk://"):
            self.core.userbrowse.open_soulseek_url(entry_text)
        else:
            self.core.userbrowse.browse_user(entry_text)

        widget.set_text("")

    def on_load_from_disk_selected(self, selected, _data):
        for filename in selected:
            self.core.userbrowse.load_shares_list_from_disk(filename)

    def on_load_from_disk(self, *_args):

        shares_folder = self.core.userbrowse.create_user_shares_folder()

        FileChooser(
            parent=self.window,
            title=_("Select a Saved Shares List File"),
            callback=self.on_load_from_disk_selected,
            initial_folder=shares_folder,
            multiple=True
        ).show()

    """ Chat """

    def on_settings_chat(self, *_args):
        self.on_settings(page="Chats")

    def on_get_private_chat(self, widget, *_args):

        username = widget.get_text()

        if not username:
            return

        self.core.privatechats.show_user(username)
        widget.set_text("")

    def on_create_room_response(self, dialog, response_id, room):

        private = dialog.option.get_active()

        if response_id == 2:
            # Create a new room
            self.core.chatrooms.request_join_room(room, private)

    def on_create_room(self, widget, *_args):

        room = widget.get_text()

        if not room:
            return False

        if room not in self.core.chatrooms.server_rooms and room not in self.core.chatrooms.private_rooms:
            OptionDialog(
                parent=self.window,
                title=_('Create New Room?'),
                message=_('Do you really want to create a new room "%s"?') % room,
                option_label=_("Make room private"),
                callback=self.on_create_room_response,
                callback_data=room
            ).show()

        else:
            self.core.chatrooms.request_join_room(room)

        widget.set_text("")
        return True

    def update_completions(self):
        self.core.chatrooms.update_completions()
        self.core.privatechats.update_completions()

    """ Away Mode """

    def set_away_mode(self, is_away):

        if not is_away:
            self.set_user_status(_("Online"))
            self.set_auto_away(False)
        else:
            self.set_user_status(_("Away"))
            self.remove_away_timer()

        self.tray_icon.set_away(is_away)
        self.away_action.set_state(GLib.Variant("b", is_away))

    def set_auto_away(self, active):

        if active:
            self.auto_away = True
            self.away_timer = None

            if not self.core.away:
                self.core.set_away_mode(True)

            return

        if self.auto_away:
            self.auto_away = False

            if self.core.away:
                self.core.set_away_mode(False)

        # Reset away timer
        self.remove_away_timer()
        self.create_away_timer()

    def create_away_timer(self):

        if self.core.away or not self.core.logged_in:
            return

        away_interval = config.sections["server"]["autoaway"]

        if away_interval > 0:
            self.away_timer = GLib.timeout_add_seconds(60 * away_interval, self.set_auto_away, True)

    def remove_away_timer(self):

        if self.away_timer is not None:
            GLib.source_remove(self.away_timer)
            self.away_timer = None

    def on_cancel_auto_away(self, *_args):

        current_time = time.time()

        if (current_time - self.away_cooldown_time) >= 5:
            self.set_auto_away(False)
            self.away_cooldown_time = current_time

        return False

    """ User Actions """

    def on_add_user(self, widget, *_args):
        self.userlist.on_add_user(widget)

    """ Various """

    @staticmethod
    def focus_combobox(button):

        parent = button.get_ancestor(Gtk.ComboBox)
        entry = parent.get_child()

        entry.grab_focus()

    def on_settings_downloads(self, *_args):
        self.on_settings(page='Downloads')

    def on_settings_uploads(self, *_args):
        self.on_settings(page='Uploads')

    """ Log Pane """

    def create_log_context_menu(self):

        popup_menu_log_categories = PopupMenu(self)
        popup_menu_log_categories.add_items(
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

        PopupMenu(self, self.log_view.textview, self.on_popup_menu_log).add_items(
            ("#" + _("_Find…"), self.on_find_log_window),
            ("", None),
            ("#" + _("_Copy"), self.log_view.on_copy_text),
            ("#" + _("Copy _All"), self.log_view.on_copy_all_text),
            ("", None),
            ("#" + _("_Open Log Folder"), self.on_view_debug_logs),
            ("#" + _("Open _Transfer Log"), self.on_view_transfer_log),
            ("", None),
            (">" + _("_Log Categories"), popup_menu_log_categories),
            ("", None),
            ("#" + _("Clear Log View"), self.log_view.on_clear_all_text)
        )

    def log_callback(self, _timestamp_format, msg, level):
        GLib.idle_add(self.update_log, msg, level, priority=GLib.PRIORITY_LOW)

    def update_log(self, msg, level):

        if level and level.startswith("important"):
            parent = self.preferences.dialog if self.preferences.dialog.get_visible() else self.window
            title = "Information" if level == "important_info" else "Error"
            MessageDialog(parent=parent, title=title, message=msg).show()

        # Keep verbose debug messages out of statusbar to make it more useful
        if level not in ("transfer", "connection", "message", "miscellaneous"):
            self.set_status_text(msg)

        self.log_view.append_line(msg, find_urls=False)
        return False

    def on_popup_menu_log(self, menu, _textview):
        menu.actions[_("_Copy")].set_enabled(self.log_view.get_has_selection())

    def on_find_log_window(self, *_args):
        self.log_search_bar.show()

    @staticmethod
    def on_view_debug_logs(*_args):
        open_file_path(config.sections["logging"]["debuglogsdir"], create_folder=True)

    @staticmethod
    def on_view_transfer_log(*_args):
        open_log(config.sections["logging"]["transferslogsdir"], "transfers")

    @staticmethod
    def add_debug_level(debug_level):
        if debug_level not in config.sections["logging"]["debugmodes"]:
            config.sections["logging"]["debugmodes"].append(debug_level)

    @staticmethod
    def remove_debug_level(debug_level):
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
        self.status_label.set_text(msg)
        self.status_label.set_tooltip_text(msg)

    def set_user_status(self, status):
        self.user_status_label.set_text(status)

    def set_connection_stats(self, msg):

        total_conns = repr(msg.total_conns)

        if self.connections_label.get_text() != total_conns:
            self.connections_label.set_text(repr(msg.total_conns))

        download_bandwidth = human_speed(msg.download_bandwidth)
        self.download_status_label.set_text("%(speed)s (%(num)i)" % {
            'num': msg.download_conns, 'speed': download_bandwidth})
        self.tray_icon.set_download_status(_("Downloads: %(speed)s") % {'speed': download_bandwidth})

        upload_bandwidth = human_speed(msg.upload_bandwidth)
        self.upload_status_label.set_text("%(speed)s (%(num)i)" % {
            'num': msg.upload_conns, 'speed': upload_bandwidth})
        self.tray_icon.set_upload_status(_("Uploads: %(speed)s") % {'speed': upload_bandwidth})

    def show_scan_progress(self):
        self.scan_progress_indeterminate = True
        GLib.idle_add(self.scan_progress_bar.show)

    def set_scan_progress(self, value):
        self.scan_progress_indeterminate = False
        GLib.idle_add(self.scan_progress_bar.set_fraction, value)

    def set_scan_indeterminate(self):
        self.scan_progress_bar.pulse()
        GLib.timeout_add(500, self.pulse_scan_progress)

    def pulse_scan_progress(self):
        if self.scan_progress_indeterminate:
            self.set_scan_indeterminate()

    def hide_scan_progress(self):
        self.scan_progress_indeterminate = False
        GLib.idle_add(self.scan_progress_bar.hide)

    def update_alternative_speed_icon(self, active):

        if active:
            icon_name = "media-skip-backward-symbolic"
        else:
            icon_name = "media-seek-backward-symbolic"

        self.alt_speed_icon.set_property("icon-name", icon_name)

    def on_alternative_speed_limit(self, *_args):

        state = config.sections["transfers"]["usealtlimits"]
        self.alt_speed_action.set_state(GLib.Variant("b", not state))

        config.sections["transfers"]["usealtlimits"] = not state

        self.update_alternative_speed_icon(not state)
        self.core.transfers.update_limits()
        self.tray_icon.set_alternative_speed_limit(not state)

    """ Termination """

    def on_critical_error_response(self, _dialog, response_id, data):

        loop, error = data

        if response_id == 2:
            copy_text(error)
            self.on_report_bug()
            return

        loop.quit()
        self.core.quit()

    def on_critical_error(self, exc_type, exc_value, exc_traceback):

        from traceback import format_tb

        # Check if exception occurred in a plugin
        if self.core.pluginhandler is not None:
            traceback = exc_traceback

            while True:
                if not traceback.tb_next:
                    break

                filename = traceback.tb_frame.f_code.co_filename

                for plugin_name in self.core.pluginhandler.enabled_plugins:
                    path = self.core.pluginhandler.get_plugin_path(plugin_name)

                    if filename.startswith(path):
                        self.core.pluginhandler.show_plugin_error(
                            plugin_name, exc_type, exc_value, exc_traceback)
                        return

                traceback = traceback.tb_next

        # Show critical error dialog
        loop = GLib.MainLoop()
        error = ("\n\nNicotine+ Version: %s\nGTK Version: %s\nPython Version: %s\n\n"
                 "Type: %s\nValue: %s\nTraceback: %s" %
                 (config.version, config.gtk_version, config.python_version, exc_type,
                  exc_value, ''.join(format_tb(exc_traceback))))

        OptionDialog(
            parent=self.window,
            title=_("Critical Error"),
            message=_("Nicotine+ has encountered a critical error and needs to exit. "
                      "Please copy the following message and include it in a bug report:") + error,
            first_button=_("_Quit Nicotine+"),
            second_button=_("_Copy & Report Bug"),
            callback=self.on_critical_error_response,
            callback_data=(loop, error)
        ).show()

        # Keep dialog open if error occurs on startup
        loop.run()

        raise exc_value

    @staticmethod
    def _on_critical_error_threading(args):
        raise args.exc_value

    def on_critical_error_threading(self, args):
        """ Exception that originated in a thread.
        Raising an exception here calls sys.excepthook(), which in turn shows an error dialog. """

        GLib.idle_add(self._on_critical_error_threading, args)

    """ Exit """

    def show_exit_dialog_response(self, dialog, response_id, _data):

        remember = dialog.option.get_active()

        if response_id == 2:  # 'Quit'
            if remember:
                config.sections["ui"]["exitdialog"] = 0

            self.core.quit()

        elif response_id == 3:  # 'Run in Background'
            if remember:
                config.sections["ui"]["exitdialog"] = 2

            if self.window.get_property("visible"):
                self.hide()

    def show_exit_dialog(self, remember=True):

        OptionDialog(
            parent=self.window,
            title=_('Quit Nicotine+'),
            message=_('Do you really want to exit?'),
            second_button=_("_Quit"),
            third_button=_("_Run in Background") if self.window.get_property("visible") else None,
            option_label=_("Remember choice") if remember else None,
            callback=self.show_exit_dialog_response
        ).show()

    def on_close_request(self, *_args):

        if config.sections["ui"]["exitdialog"] >= 2:  # 2: 'Run in Background'
            self.hide()
            return True

        return self.on_quit(remember=True)

    def on_quit(self, *_args, remember=False):

        if config.sections["ui"]["exitdialog"] == 0:  # 0: 'Quit program'
            self.core.quit()
            return True

        self.show_exit_dialog(remember)
        return True

    def on_shutdown(self):

        # Explicitly hide tray icon, otherwise it will not disappear on Windows
        self.tray_icon.hide()

        # Save visible columns
        self.save_columns()

        log.remove_listener(self.log_callback)
        config.write_configuration()

    def hide(self):

        if not self.window.get_property("visible"):
            return

        # Save visible columns, incase application is killed later
        self.save_columns()

        if not self.tray_icon.is_visible():
            log.add(_("Nicotine+ is running in the background"))

        # Run in Background
        self.window.hide()

        # Save config, incase application is killed later
        config.write_configuration()

    def quit(self):
        self.application.quit()
