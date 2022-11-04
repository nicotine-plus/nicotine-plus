# COPYRIGHT (C) 2020-2022 Nicotine+ Contributors
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2016-2018 Mutnick <mutnick@techie.com>
# COPYRIGHT (C) 2008-2011 quinox <quinox@users.sf.net>
# COPYRIGHT (C) 2006-2009 daelstorm <daelstorm@gmail.com>
# COPYRIGHT (C) 2009 hedonist <ak@sensi.org>
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
from pynicotine.gtkgui.widgets.iconnotebook import TabLabel
from pynicotine.gtkgui.widgets.dialogs import MessageDialog
from pynicotine.gtkgui.widgets.dialogs import OptionDialog
from pynicotine.gtkgui.widgets.iconnotebook import IconNotebook
from pynicotine.gtkgui.widgets.notifications import Notifications
from pynicotine.gtkgui.widgets.popupmenu import PopupMenu
from pynicotine.gtkgui.widgets.textentry import TextSearchBar
from pynicotine.gtkgui.widgets.textview import TextView
from pynicotine.gtkgui.widgets.theme import get_status_icon_name
from pynicotine.gtkgui.widgets.theme import load_icons
from pynicotine.gtkgui.widgets.theme import set_dark_mode
from pynicotine.gtkgui.widgets.theme import set_global_style
from pynicotine.gtkgui.widgets.theme import set_use_header_bar
from pynicotine.gtkgui.widgets.theme import update_widget_visuals
from pynicotine.gtkgui.widgets.trayicon import TrayIcon
from pynicotine.gtkgui.widgets.ui import UserInterface
from pynicotine.gtkgui.widgets.window import Window
from pynicotine.logfacility import log
from pynicotine.scheduler import scheduler
from pynicotine.slskmessages import UserStatus
from pynicotine.utils import human_speed
from pynicotine.utils import open_file_path
from pynicotine.utils import open_log
from pynicotine.utils import open_uri


class NicotineFrame(Window):

    def __init__(self, application, core, start_hidden, ci_mode):

        self.application = application
        self.core = self.np = core  # pylint:disable=invalid-name
        self.start_hidden = start_hidden
        self.ci_mode = ci_mode
        self.current_page_id = ""
        self.auto_away = False
        self.away_timer_id = None
        self.away_cooldown_time = 0
        self.gesture_click = None
        self.scan_progress_indeterminate = False

        # Initialize these windows/dialogs later when necessary
        self.fast_configure = None
        self.preferences = None
        self.shortcuts = None
        self.spell_checker = None

        """ Load UI """

        ui_template = UserInterface(scope=self, path="mainwindow.ui")
        (
            self.add_buddy_entry,
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
            self.download_files_label,
            self.download_status_label,
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
            self.log_search_bar,
            self.log_search_entry,
            self.log_view,
            self.notebook,
            self.private_end,
            self.private_entry,
            self.private_history_button,
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
            self.search_combobox_button,
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
            self.upload_files_label,
            self.upload_status_label,
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
            self.user_status_icon,
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
        ) = ui_template.widgets
        super().__init__(self.window)

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

        self.log_view = TextView(self.log_view, auto_scroll=True, parse_urls=False)
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

        self.tray_icon = TrayIcon(self, core)
        self.notifications = Notifications(self, core)
        self.statistics = Statistics(self, core)

        """ Notebook Tabs """

        # Initialize main notebook
        self.notebook = IconNotebook(
            self, core,
            widget=self.notebook,
            switch_page_callback=self.on_switch_page,
            reorder_page_callback=self.on_page_reordered
        )
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

    def init_spell_checker(self):

        try:
            gi.require_version('Gspell', '1')
            from gi.repository import Gspell
            self.spell_checker = Gspell.Checker()

        except (ImportError, ValueError):
            self.spell_checker = False

    def update_visuals(self):
        for widget in self.__dict__.values():
            update_widget_visuals(widget)

    """ Window State """

    def on_window_active_changed(self, window, param):

        if not window.get_property(param.name):
            return

        self.chatrooms.clear_notifications()
        self.privatechat.clear_notifications()
        self.on_cancel_auto_away()

        self.notifications.set_urgency_hint(False)

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
        self.tray_icon.update_window_visibility()

    def on_window_hide_unhide(self, *_args):

        if self.window.get_property("visible"):
            self.hide()
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

        focus_widget = None
        self.update_user_status()

        if self.current_page_id == self.userbrowse_page.id:
            focus_widget = self.userbrowse_entry

        if self.current_page_id == self.userinfo_page.id:
            focus_widget = self.userinfo_entry

        if self.current_page_id == self.search_page.id:
            focus_widget = self.search_entry

        if focus_widget is not None:
            GLib.idle_add(lambda: focus_widget.grab_focus() == -1, priority=GLib.PRIORITY_HIGH_IDLE)

    def server_disconnect(self):
        self.update_user_status()

    def invalid_password_response(self, _dialog, response_id, _data):
        if response_id == 2:
            self.on_preferences(page_id="network")

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

    def update_user_status(self):

        status = self.core.user_status
        is_online = (status != UserStatus.OFFLINE)
        is_away = (status == UserStatus.AWAY)

        # Action status
        self.connect_action.set_enabled(not is_online)
        self.disconnect_action.set_enabled(is_online)
        self.soulseek_privileges_action.set_enabled(is_online)
        self.away_accelerator_action.set_enabled(is_online)

        self.user_status_button.set_sensitive(is_online)
        self.tray_icon.update_user_status()

        # Away mode
        if not is_away:
            self.set_auto_away(False)
        else:
            self.remove_away_timer()

        # Status bar
        username = self.core.login_username
        icon_name = get_status_icon_name(status)

        if status == UserStatus.AWAY:
            status_text = _("Away")

        elif status == UserStatus.ONLINE:
            status_text = _("Online")

        else:
            username = None
            status_text = _("Offline")

        if self.user_status_button.get_tooltip_text() != username:
            self.user_status_button.set_tooltip_text(username)

        self.user_status_icon.set_property("icon-name", icon_name)
        self.user_status_label.set_text(status_text)

    """ Action Callbacks """

    # File

    def on_connect(self, *_args):
        self.core.connect()

    def on_disconnect(self, *_args):
        self.core.disconnect()

    def on_soulseek_privileges(self, *_args):

        import urllib.parse

        login = urllib.parse.quote(self.core.login_username)
        open_uri(config.privileges_url % login)
        self.core.request_check_privileges()

    def on_wishlist(self, *_args):
        self.search.wish_list.show()

    def on_fast_configure(self, *_args):
        self.setup()

    def on_preferences(self, *_args, page_id=None):

        if self.preferences is None:
            self.preferences = Preferences(self, self.core)

        self.preferences.set_settings()
        self.preferences.set_active_page(page_id)
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

    def set_show_log_history(self, show):

        self.log_view.auto_scroll = show

        if show:
            GLib.idle_add(self.log_view.scroll_bottom)

    def on_show_log_history(self, action, *_args):

        state = config.sections["logging"]["logcollapsed"]
        self.set_show_log_history(state)
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
        self.on_preferences(page_id="shares")

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

    def on_check_latest_version(self, *_args):
        self.core.update_checker.check()

    def on_about(self, *_args):
        About(self).show()

    """ Actions """

    def set_up_actions(self):

        # Main

        if GTK_API_VERSION == 3:
            action = Gio.SimpleAction(name="menu")
            action.connect("activate", self.on_menu)
            self.application.add_action(action)

        action = Gio.SimpleAction(name="change-focus-view")
        action.connect("activate", self.on_change_focus_view)
        self.window.add_action(action)
        self.application.set_accels_for_action("win.change-focus-view", ["F6"])

        # File

        self.connect_action = Gio.SimpleAction(name="connect")
        self.connect_action.connect("activate", self.on_connect)
        self.application.add_action(self.connect_action)
        self.application.set_accels_for_action("app.connect", ["<Shift><Primary>c"])

        self.disconnect_action = Gio.SimpleAction(name="disconnect", enabled=False)
        self.disconnect_action.connect("activate", self.on_disconnect)
        self.application.add_action(self.disconnect_action)
        self.application.set_accels_for_action("app.disconnect", ["<Shift><Primary>d"])

        self.soulseek_privileges_action = Gio.SimpleAction(name="soulseek-privileges", enabled=False)
        self.soulseek_privileges_action.connect("activate", self.on_soulseek_privileges)
        self.application.add_action(self.soulseek_privileges_action)

        action = Gio.SimpleAction(name="preferences")
        action.connect("activate", self.on_preferences)
        self.application.add_action(action)
        self.application.set_accels_for_action("app.preferences", ["<Primary>comma", "<Primary>p"])

        # View

        state = config.sections["ui"]["dark_mode"]
        self.dark_mode_action = Gio.SimpleAction(name="prefer-dark-mode", state=GLib.Variant("b", state))
        self.dark_mode_action.connect("change-state", self.on_prefer_dark_mode)
        self.window.add_action(self.dark_mode_action)

        state = config.sections["ui"]["header_bar"]
        action = Gio.SimpleAction(name="show-header-bar", state=GLib.Variant("b", state))
        action.connect("change-state", self.on_show_header_bar)
        self.window.add_action(action)

        state = not config.sections["logging"]["logcollapsed"]
        action = Gio.SimpleAction(name="show-log-history", state=GLib.Variant("b", state))
        action.connect("change-state", self.on_show_log_history)
        self.window.add_action(action)
        self.application.set_accels_for_action("win.show-log-history", ["<Primary>l"])
        self.set_show_log_history(state)

        state = config.sections["ui"]["buddylistinchatrooms"]

        if state not in ("tab", "chatrooms", "always"):
            state = "tab"

        self.toggle_buddy_list_action = Gio.SimpleAction(
            name="toggle-buddy-list", parameter_type=GLib.VariantType("s"), state=GLib.Variant("s", state))
        self.toggle_buddy_list_action.connect("change-state", self.on_toggle_buddy_list)
        self.window.add_action(self.toggle_buddy_list_action)
        self.set_toggle_buddy_list(state, force_show=False)

        # Shares

        action = Gio.SimpleAction(name="rescan-shares")
        action.connect("activate", self.on_rescan_shares)
        self.application.add_action(action)
        self.application.set_accels_for_action("app.rescan-shares", ["<Shift><Primary>r"])

        # Help

        action = Gio.SimpleAction(name="keyboard-shortcuts")
        action.connect("activate", self.on_keyboard_shortcuts)
        self.application.add_action(action)
        self.application.set_accels_for_action("app.keyboard-shortcuts", ["<Primary>question", "F1"])

        # Search

        self.search_mode_action = Gio.SimpleAction(
            name="search-mode", parameter_type=GLib.VariantType("s"), state=GLib.Variant("s", "global"))
        self.search_mode_action.connect("change-state", self.search.on_search_mode)
        self.window.add_action(self.search_mode_action)

        action = Gio.SimpleAction(name="wishlist")
        action.connect("activate", self.on_wishlist)
        self.application.add_action(action)
        self.application.set_accels_for_action("app.wishlist", ["<Shift><Primary>w"])

        # Notebook Tabs

        action = Gio.SimpleAction(name="close-tab")
        action.connect("activate", self.on_close_tab)
        self.window.add_action(action)
        self.application.set_accels_for_action("win.close-tab", ["<Primary>F4", "<Primary>w"])

        action = Gio.SimpleAction(name="cycle-tabs")
        action.connect("activate", self.on_cycle_tabs)
        self.window.add_action(action)
        self.application.set_accels_for_action("win.cycle-tabs", ["<Primary>Tab"])

        action = Gio.SimpleAction(name="cycle-tabs-reverse")
        action.connect("activate", self.on_cycle_tabs, True)
        self.window.add_action(action)
        self.application.set_accels_for_action("win.cycle-tabs-reverse", ["<Primary><Shift>Tab"])

        for num in range(1, 10):
            action = Gio.SimpleAction(name="primary-tab-" + str(num))
            action.connect("activate", self.on_change_primary_tab, num)
            self.window.add_action(action)
            self.application.set_accels_for_action("win.primary-tab-" + str(num),
                                                   ["<Primary>" + str(num), "<Alt>" + str(num)])

        # Logging

        state = ("download" in config.sections["logging"]["debugmodes"])
        action = Gio.SimpleAction(name="log-downloads", state=GLib.Variant("b", state))
        action.connect("change-state", self.on_debug_downloads)
        self.window.add_action(action)

        state = ("upload" in config.sections["logging"]["debugmodes"])
        action = Gio.SimpleAction(name="log-uploads", state=GLib.Variant("b", state))
        action.connect("change-state", self.on_debug_uploads)
        self.window.add_action(action)

        state = ("search" in config.sections["logging"]["debugmodes"])
        action = Gio.SimpleAction(name="log-searches", state=GLib.Variant("b", state))
        action.connect("change-state", self.on_debug_searches)
        self.window.add_action(action)

        state = ("chat" in config.sections["logging"]["debugmodes"])
        action = Gio.SimpleAction(name="log-chat", state=GLib.Variant("b", state))
        action.connect("change-state", self.on_debug_chat)
        self.window.add_action(action)

        state = ("connection" in config.sections["logging"]["debugmodes"])
        action = Gio.SimpleAction(name="log-connections", state=GLib.Variant("b", state))
        action.connect("change-state", self.on_debug_connections)
        self.window.add_action(action)

        state = ("message" in config.sections["logging"]["debugmodes"])
        action = Gio.SimpleAction(name="log-messages", state=GLib.Variant("b", state))
        action.connect("change-state", self.on_debug_messages)
        self.window.add_action(action)

        state = ("transfer" in config.sections["logging"]["debugmodes"])
        action = Gio.SimpleAction(name="log-transfers", state=GLib.Variant("b", state))
        action.connect("change-state", self.on_debug_transfers)
        self.window.add_action(action)

        state = ("miscellaneous" in config.sections["logging"]["debugmodes"])
        action = Gio.SimpleAction(name="log-miscellaneous", state=GLib.Variant("b", state))
        action.connect("change-state", self.on_debug_miscellaneous)
        self.window.add_action(action)

        # Status Bar Buttons

        state = config.sections["transfers"]["usealtlimits"]
        self.alt_speed_action = Gio.SimpleAction(name="alternative-speed-limit", state=GLib.Variant("b", state))
        self.alt_speed_action.connect("change-state", self.on_alternative_speed_limit)
        self.application.add_action(self.alt_speed_action)
        self.update_alternative_speed_icon(state)

        # Shortcut Key Actions

        self.away_accelerator_action = Gio.SimpleAction(name="away", enabled=False)
        self.away_accelerator_action.cooldown_time = 0  # needed to prevent server ban
        self.away_accelerator_action.connect("activate", self.on_away_accelerator)
        self.application.add_action(self.away_accelerator_action)
        self.application.set_accels_for_action("app.away", ["<Primary>h"])

        action = Gio.SimpleAction(name="close")  # 'When closing Nicotine+'
        action.connect("activate", self.on_close_request)
        self.application.add_action(action)
        self.application.set_accels_for_action("app.close", ["<Primary>q"])

        action = Gio.SimpleAction(name="force-quit")
        action.connect("activate", self.core.quit)
        self.application.add_action(action)
        self.application.set_accels_for_action("app.force-quit", ["<Primary><Alt>q"])

    """ Primary Menus """

    @staticmethod
    def add_connection_section(menu):

        menu.add_items(
            ("=" + _("_Connect"), "app.connect"),
            ("=" + _("_Disconnect"), "app.disconnect"),
            ("#" + _("Soulseek _Privileges"), "app.soulseek-privileges"),
            ("", None)
        )

    @staticmethod
    def add_preferences_item(menu):
        menu.add_items(("#" + _("_Preferences"), "app.preferences"))

    def add_quit_item(self, menu):

        label = _("_Quit…") if config.sections["ui"]["exitdialog"] else _("_Quit")

        menu.add_items(
            ("", None),
            ("#" + label, self.on_quit)
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
            ("$" + _("Prefer Dark _Mode"), "win.prefer-dark-mode"),
            ("$" + _("Use _Header Bar"), "win.show-header-bar"),
            ("$" + _("Show _Log History Pane"), "win.show-log-history"),
            ("", None),
            ("O" + _("Buddy List in Separate Tab"), "win.toggle-buddy-list", "tab"),
            ("O" + _("Buddy List in Chat Rooms"), "win.toggle-buddy-list", "chatrooms"),
            ("O" + _("Buddy List Always Visible"), "win.toggle-buddy-list", "always")
        )

        return menu

    def add_configure_shares_section(self, menu):

        menu.add_items(
            ("#" + _("_Rescan Shares"), "app.rescan-shares"),
            ("#" + _("_Configure Shares"), self.on_configure_shares),
            ("", None)
        )

    def add_browse_shares_section(self, menu):

        menu.add_items(
            ("#" + _("_Browse Public Shares"), self.on_browse_public_shares),
            ("#" + _("Bro_wse Buddy Shares"), self.on_browse_buddy_shares),
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
            ("#" + _("_Keyboard Shortcuts"), "app.keyboard-shortcuts"),
            ("#" + _("_Setup Assistant"), self.on_fast_configure),
            ("#" + _("_Transfer Statistics"), self.on_transfer_statistics),
            ("", None),
            ("#" + _("Report a _Bug"), self.on_report_bug),
            ("#" + _("Improve T_ranslations"), self.on_improve_translations),
            ("#" + _("Check _Latest Version"), self.on_check_latest_version),
            ("", None),
            ("#" + _("_About Nicotine+"), self.on_about)
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

        if GTK_API_VERSION >= 4:
            # F10 shortcut to open menu
            self.header_menu.set_primary(True)

    def on_menu(self, *_args):
        self.header_menu.set_active(not self.header_menu.get_active())

    """ Headerbar/toolbar """

    def show_header_bar(self, page_id):
        """ Set a headerbar for the main window (client side decorations enabled) """

        if self.window.get_titlebar() != self.header_bar:
            self.window.set_titlebar(self.header_bar)
            self.window.set_show_menubar(False)

            if GTK_API_VERSION == 3:
                self.application.set_accels_for_action("app.menu", ["F10"])

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
            self.header_menu.get_popover().hide()

            if GTK_API_VERSION == 3:
                # Don't override builtin accelerator for menu bar
                self.application.set_accels_for_action("app.menu", [])

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

        if config.sections["ui"]["header_bar"]:
            self.hide_current_header_bar()
            self.show_header_bar(page_id)
        else:
            self.hide_current_toolbar()
            self.show_toolbar(page_id)

        self.current_page_id = page_id

        if self.application.get_active_window():
            config.sections["ui"]["last_tab_id"] = page_id

    def on_change_focus_view(self, *_args):
        """ F6: move focus between header bar/toolbar and main content """

        title_widget = getattr(self, self.current_page_id + "_title")

        # Find the correct widget to focus in the main view
        if title_widget.get_focus_child():
            try:
                # Attempt to focus a widget in a secondary notebook
                notebook = getattr(self, self.current_page_id)
                page = notebook.get_current_page()

                if page is not None:
                    # Found a focusable widget
                    page.focus_callback()
                    return

            except AttributeError:
                # No notebook present, attempt to focus the main content widget
                content_widget = getattr(self, self.current_page_id + "_content")

                if content_widget.child_focus(Gtk.DirectionType.TAB_FORWARD):
                    # Found a focusable widget
                    return

        # Find the correct widget to focus in the header bar/toolbar
        try:
            entry_widget = getattr(self, self.current_page_id + "_entry")
            entry_widget.grab_focus()

        except AttributeError:
            title_widget = getattr(self, self.current_page_id + "_title")
            title_widget.child_focus(Gtk.DirectionType.TAB_FORWARD)

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

            menu_label = TabLabel(tab_text)
            tab_label = TabLabel(tab_text)
            tab_label.set_start_icon_name(tab_icon_name)

            # Apply tab label
            self.notebook.set_labels(page, tab_label, menu_label)
            self.notebook.set_tab_reorderable(page, True)
            self.set_tab_expand(page)

    def on_switch_page(self, _notebook, page, _page_num):

        focus_widget = None
        self.set_active_header_bar(page.id)

        if page == self.chatrooms_page:
            if not self.chatrooms.get_n_pages():
                focus_widget = self.chatrooms_entry

        elif page == self.private_page:
            if not self.privatechat.get_n_pages():
                focus_widget = self.private_entry

        elif page == self.uploads_page:
            self.uploads.update_model(forceupdate=True)
            self.notebook.remove_tab_hilite(self.uploads_page)

            if self.uploads.container.get_visible():
                focus_widget = self.uploads.tree_view

        elif page == self.downloads_page:
            self.downloads.update_model(forceupdate=True)
            self.notebook.remove_tab_hilite(self.downloads_page)

            if self.downloads.container.get_visible():
                focus_widget = self.downloads.tree_view

        elif page == self.search_page:
            focus_widget = self.search_entry

        elif page == self.userinfo_page:
            if not self.userinfo.get_n_pages():
                focus_widget = self.userinfo_entry

        elif page == self.userbrowse_page:
            if not self.userbrowse.get_n_pages():
                focus_widget = self.userbrowse_entry

        elif page == self.userlist_page:
            self.userlist.update()

            if self.userlist.container.get_visible():
                focus_widget = self.userlist.list_view

        elif page == self.interests_page:
            self.interests.populate_recommendations()
            focus_widget = self.interests.recommendations_list_view

        if focus_widget is not None:
            GLib.idle_add(lambda: focus_widget.grab_focus() == -1, priority=GLib.PRIORITY_HIGH_IDLE)

    def on_page_reordered(self, *_args):

        if not self.application.get_active_window():
            # Don't save the tab order until the window is ready
            return

        page_ids = []

        for i in range(self.notebook.get_n_pages()):
            page = self.notebook.get_nth_page(i)
            page_ids.append(page.id)

        config.sections["ui"]["modes_order"] = page_ids

    def on_close_tab(self, *_args):
        """ Ctrl+W and Ctrl+F4: close current secondary tab """

        try:
            notebook = getattr(self, self.current_page_id)
            page = notebook.get_current_page()

        except AttributeError:
            return False

        if page is None:
            return False

        tab_label, _menu_label = notebook.get_labels(page)
        tab_label.close_callback()
        return True

    def on_cycle_tabs(self, _widget, _state, backwards=False):
        """ Ctrl+Tab and Shift+Ctrl+Tab: cycle through secondary tabs """

        try:
            notebook = getattr(self, self.current_page_id)
            num_pages = notebook.get_n_pages()
            current_page_num = notebook.get_current_page_num()

        except AttributeError:
            return False

        if backwards:
            if current_page_num == 0:
                notebook.set_current_page_num(num_pages - 1)
            else:
                notebook.prev_page()

            return True

        if current_page_num == (num_pages - 1):
            notebook.set_current_page_num(0)
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
        self.notebook.set_current_page_num(page_num)
        return True

    def change_main_page(self, page):
        self.show_tab(page)
        self.notebook.set_current_page(page)

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
            self.notebook.set_current_page(page)

    def set_tab_expand(self, page):

        tab_position = config.sections["ui"]["tabmain"]
        expand = tab_position in ("Top", "Bottom")
        self.notebook.set_tab_expand(page, expand)

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

    def on_configure_searches(self, *_args):
        self.on_preferences(page_id="searches")

    def on_search(self, *_args):
        self.search.on_search()

    """ User Info """

    def on_update_user_info(self, *_args):
        self.on_preferences(page_id="user-info")

    def on_get_user_info(self, *_args):
        self.userinfo.on_get_user_info()

    """ Shares """

    def on_get_shares(self, *_args):
        self.userbrowse.on_get_shares()

    def on_load_from_disk(self, *_args):
        self.userbrowse.on_load_from_disk()

    def shares_unavailable_response(self, _dialog, response_id, _data):

        if response_id == 2:  # 'Retry'
            self.core.shares.rescan_shares()

        elif response_id == 3:  # 'Force Rescan'
            self.core.shares.rescan_shares(force=True)

    def shares_unavailable(self, shares):

        shares_list_message = ""

        for virtual_name, folder_path in shares:
            shares_list_message += "• \"%s\" %s\n" % (virtual_name, folder_path)

        def create_dialog():
            OptionDialog(
                parent=self.window,
                title=_("Shares Not Available"),
                message=_("Verify that external disks are mounted and folder permissions are correct."),
                long_message=shares_list_message,
                first_button=_("_Cancel"),
                second_button=_("_Retry"),
                third_button=_("_Force Rescan"),
                callback=self.shares_unavailable_response
            ).show()

        # Avoid dialog appearing deactive if invoked during rescan on startup
        GLib.idle_add(create_dialog)

    """ Chat """

    def on_configure_chats(self, *_args):
        self.on_preferences(page_id="chats")

    def on_get_private_chat(self, *_args):
        self.privatechat.on_get_private_chat()

    def on_create_room(self, *_args):
        self.chatrooms.on_create_room()

    def update_completions(self):
        self.core.chatrooms.update_completions()
        self.core.privatechat.update_completions()

    """ Away Mode """

    def set_away_mode(self, _is_away):
        self.update_user_status()

    def set_auto_away(self, active=True):

        if active:
            self.auto_away = True
            self.away_timer_id = None

            if self.core.user_status != UserStatus.AWAY:
                self.core.set_away_mode(True)

            return

        if self.auto_away:
            self.auto_away = False

            if self.core.user_status == UserStatus.AWAY:
                self.core.set_away_mode(False)

        # Reset away timer
        self.remove_away_timer()
        self.create_away_timer()

    def create_away_timer(self):

        if self.core.user_status != UserStatus.ONLINE:
            return

        away_interval = config.sections["server"]["autoaway"]

        if away_interval > 0:
            self.away_timer_id = scheduler.add(delay=(60 * away_interval), callback=self.set_auto_away)

    def remove_away_timer(self):
        scheduler.cancel(self.away_timer_id)

    def on_cancel_auto_away(self, *_args):

        current_time = time.time()

        if (current_time - self.away_cooldown_time) >= 5:
            self.set_auto_away(False)
            self.away_cooldown_time = current_time

    def on_away_accelerator(self, *_args):
        """ Ctrl+H: Away/Online toggle """

        current_time = time.time()

        if (current_time - self.away_accelerator_action.cooldown_time) >= 1:
            # Prevent rapid key-repeat toggling to avoid server ban
            self.on_away()
            self.away_accelerator_action.cooldown_time = current_time

    def on_away(self, *_args):
        """ Away/Online status button """

        self.core.set_away_mode(self.core.user_status != UserStatus.AWAY, save_state=True)

    """ User Actions """

    def on_add_user(self, *_args):
        self.userlist.on_add_user()

    """ Various """

    def on_configure_downloads(self, *_args):
        self.on_preferences(page_id="downloads")

    def on_configure_uploads(self, *_args):
        self.on_preferences(page_id="uploads")

    """ Log Pane """

    def create_log_context_menu(self):

        popup_menu_log_categories = PopupMenu(self)
        popup_menu_log_categories.add_items(
            ("$" + _("Downloads"), "win.log-downloads"),
            ("$" + _("Uploads"), "win.log-uploads"),
            ("$" + _("Search"), "win.log-searches"),
            ("$" + _("Chat"), "win.log-chat"),
            ("", None),
            ("$" + _("[Debug] Connections"), "win.log-connections"),
            ("$" + _("[Debug] Messages"), "win.log-messages"),
            ("$" + _("[Debug] Transfers"), "win.log-transfers"),
            ("$" + _("[Debug] Miscellaneous"), "win.log-miscellaneous"),
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
            ("#" + _("Clear Log View"), self.on_clear_log_view)
        )

    def log_callback(self, timestamp_format, msg, title, level):
        GLib.idle_add(self.update_log, timestamp_format, msg, title, level, priority=GLib.PRIORITY_LOW)

    def update_log(self, timestamp_format, msg, title, level):

        if title:
            MessageDialog(parent=self.window, title=title, message=msg).show()

        # Keep verbose debug messages out of statusbar to make it more useful
        if level not in ("transfer", "connection", "message", "miscellaneous"):
            self.set_status_text(msg)

        self.log_view.append_line(msg, timestamp_format=timestamp_format)

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

    def on_clear_log_view(self, *_args):
        self.log_view.on_clear_all_text()
        self.set_status_text("")

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

    def set_connection_stats(self, msg):

        total_conns_text = repr(msg.total_conns)
        download_bandwidth = human_speed(msg.download_bandwidth)
        upload_bandwidth = human_speed(msg.upload_bandwidth)
        download_bandwidth_text = "%(speed)s (%(num)i)" % {'num': msg.download_conns, 'speed': download_bandwidth}
        upload_bandwidth_text = "%(speed)s (%(num)i)" % {'num': msg.upload_conns, 'speed': upload_bandwidth}

        if self.connections_label.get_text() != total_conns_text:
            self.connections_label.set_text(total_conns_text)

        if self.download_status_label.get_text() != download_bandwidth_text:
            self.download_status_label.set_text(download_bandwidth_text)
            self.tray_icon.set_download_status(_("Downloads: %(speed)s") % {'speed': download_bandwidth})

        if self.upload_status_label.get_text() != upload_bandwidth_text:
            self.upload_status_label.set_text(upload_bandwidth_text)
            self.tray_icon.set_upload_status(_("Uploads: %(speed)s") % {'speed': upload_bandwidth})

    def show_scan_progress(self):
        GLib.idle_add(self.scan_progress_bar.show)

    def set_scan_progress(self, value):
        self.scan_progress_indeterminate = False
        GLib.idle_add(self.scan_progress_bar.set_fraction, value)

    def set_scan_indeterminate(self):

        self.scan_progress_indeterminate = True

        self.scan_progress_bar.pulse()
        GLib.timeout_add(500, self.pulse_scan_progress)

    def pulse_scan_progress(self):

        if not self.scan_progress_indeterminate:
            return False

        self.scan_progress_bar.pulse()
        return True

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
        self.tray_icon.update_alternative_speed_limit_status()

    """ Exit """

    def on_close_request(self, *_args):

        if config.sections["ui"]["exitdialog"] >= 2:  # 2: 'Run in Background'
            self.hide()
            return True

        self.core.confirm_quit(remember=True)
        return True

    def on_quit(self, *_args):
        self.core.confirm_quit()
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

        # Close any visible dialogs
        for dialog in reversed(Window.active_dialogs):
            dialog.close()

        if not self.tray_icon.is_visible():
            log.add(_("Nicotine+ is running in the background"))

        # Run in Background
        self.window.hide()

        # Save config, incase application is killed later
        config.write_configuration()

    def confirm_quit_response(self, dialog, response_id, _data):

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

    def confirm_quit(self, remember=True):

        OptionDialog(
            parent=self.window,
            title=_('Quit Nicotine+'),
            message=_('Do you really want to exit?'),
            second_button=_("_Quit"),
            third_button=_("_Run in Background") if self.window.get_property("visible") else None,
            option_label=_("Remember choice") if remember else None,
            callback=self.confirm_quit_response
        ).show()

    def quit(self):
        self.application.quit()
