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

from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk

from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.chatrooms import ChatRooms
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
from pynicotine.gtkgui.widgets.iconnotebook import IconNotebook
from pynicotine.gtkgui.widgets.popupmenu import PopupMenu
from pynicotine.gtkgui.widgets.textentry import TextSearchBar
from pynicotine.gtkgui.widgets.textview import TextView
from pynicotine.gtkgui.widgets.theme import get_status_icon_name
from pynicotine.gtkgui.widgets.theme import load_icons
from pynicotine.gtkgui.widgets.theme import set_global_style
from pynicotine.gtkgui.widgets.theme import set_use_header_bar
from pynicotine.gtkgui.widgets.theme import update_widget_visuals
from pynicotine.gtkgui.widgets.ui import UserInterface
from pynicotine.gtkgui.widgets.window import Window
from pynicotine.scheduler import scheduler
from pynicotine.slskmessages import UserStatus
from pynicotine.utils import human_speed
from pynicotine.utils import open_file_path
from pynicotine.utils import open_log


class MainWindow(Window):

    def __init__(self, application, start_hidden):

        self.application = application
        self.start_hidden = start_hidden
        self.current_page_id = ""
        self.auto_away = False
        self.away_timer_id = None
        self.away_cooldown_time = 0
        self.gesture_click = None
        self.scan_progress_indeterminate = False

        application.connect("shutdown", self.on_shutdown)

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
        events.connect("log-message", self.log_callback)

        """ Icons """

        load_icons()

        """ Notebook Tabs """

        # Initialize main notebook
        self.notebook = IconNotebook(
            self,
            widget=self.notebook,
            switch_page_callback=self.on_switch_page,
            reorder_page_callback=self.on_page_reordered
        )
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

        """ Events """

        for event_name, callback in (
            ("hide-scan-progress", self.hide_scan_progress),
            ("server-login", self.server_login),
            ("server-disconnect", self.server_disconnect),
            ("set-away-mode", self.set_away_mode),
            ("set-connection-stats", self.set_connection_stats),
            ("set-scan-indeterminate", self.set_scan_indeterminate),
            ("set-scan-progress", self.set_scan_progress),
            ("show-scan-progress", self.show_scan_progress)
        ):
            events.connect(event_name, callback)

        """ Apply UI Customizations """

        set_global_style()
        self.update_visuals()

    """ Initialize """

    def init_window(self):

        # Set main window title and icon
        self.set_title(config.application_name)
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

    def set_help_overlay(self, help_overlay):
        self.window.set_help_overlay(help_overlay)

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

        self.application.notifications.set_urgency_hint(False)

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
        self.application.tray_icon.update_window_visibility()

    def save_columns(self, *_args):
        for page in (self.userlist, self.chatrooms, self.downloads, self.uploads):
            page.save_columns()

    def show(self):

        self.window.present()

        if GTK_API_VERSION == 3:
            # Fix for Windows where minimized window is not shown when unhiding from tray
            self.window.deiconify()

    """ Connection """

    def server_login(self, msg):

        if not msg.success:
            return

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

    def server_disconnect(self, _msg):
        self.update_user_status()

    def update_user_status(self):

        status = core.user_status
        is_online = (status != UserStatus.OFFLINE)
        is_away = (status == UserStatus.AWAY)

        # Action status
        self.application.lookup_action("connect").set_enabled(not is_online)
        self.application.lookup_action("disconnect").set_enabled(is_online)
        self.application.lookup_action("soulseek-privileges").set_enabled(is_online)
        self.application.lookup_action("away-accel").set_enabled(is_online)
        self.application.lookup_action("away").set_enabled(is_online)

        self.user_status_button.set_sensitive(is_online)
        self.application.tray_icon.update_user_status()

        # Away mode
        if not is_away:
            self.set_auto_away(False)
        else:
            self.remove_away_timer()

        # Status bar
        username = core.login_username
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

    # View

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

    """ Actions """

    def add_action(self, action):
        self.window.add_action(action)

    def lookup_action(self, action_name):
        return self.window.lookup_action(action_name)

    def set_up_actions(self):

        # Main

        if GTK_API_VERSION == 3:
            action = Gio.SimpleAction(name="menu")
            action.connect("activate", self.on_menu)
            self.add_action(action)

        action = Gio.SimpleAction(name="change-focus-view")
        action.connect("activate", self.on_change_focus_view)
        self.add_action(action)
        self.application.set_accels_for_action("win.change-focus-view", ["F6"])

        # View

        state = config.sections["ui"]["header_bar"]
        action = Gio.SimpleAction(name="show-header-bar", state=GLib.Variant("b", state))
        action.connect("change-state", self.on_show_header_bar)
        self.add_action(action)

        state = not config.sections["logging"]["logcollapsed"]
        action = Gio.SimpleAction(name="show-log-history", state=GLib.Variant("b", state))
        action.connect("change-state", self.on_show_log_history)
        self.add_action(action)
        self.application.set_accels_for_action("win.show-log-history", ["<Primary>l"])
        self.set_show_log_history(state)

        state = config.sections["ui"]["buddylistinchatrooms"]

        if state not in ("tab", "chatrooms", "always"):
            state = "tab"

        action = Gio.SimpleAction(
            name="toggle-buddy-list", parameter_type=GLib.VariantType("s"), state=GLib.Variant("s", state))
        action.connect("change-state", self.on_toggle_buddy_list)
        self.add_action(action)
        self.set_toggle_buddy_list(state, force_show=False)

        # Search

        action = Gio.SimpleAction(
            name="search-mode", parameter_type=GLib.VariantType("s"), state=GLib.Variant("s", "global"))
        action.connect("change-state", self.search.on_search_mode)
        self.add_action(action)

        # Notebook Tabs

        action = Gio.SimpleAction(name="close-tab")
        action.connect("activate", self.on_close_tab)
        self.add_action(action)
        self.application.set_accels_for_action("win.close-tab", ["<Primary>F4", "<Primary>w"])

        action = Gio.SimpleAction(name="cycle-tabs")
        action.connect("activate", self.on_cycle_tabs)
        self.add_action(action)
        self.application.set_accels_for_action("win.cycle-tabs", ["<Primary>Tab"])

        action = Gio.SimpleAction(name="cycle-tabs-reverse")
        action.connect("activate", self.on_cycle_tabs, True)
        self.add_action(action)
        self.application.set_accels_for_action("win.cycle-tabs-reverse", ["<Primary><Shift>Tab"])

        for num in range(1, 10):
            action = Gio.SimpleAction(name="primary-tab-" + str(num))
            action.connect("activate", self.on_change_primary_tab, num)
            self.add_action(action)
            self.application.set_accels_for_action("win.primary-tab-" + str(num),
                                                   ["<Primary>" + str(num), "<Alt>" + str(num)])

        action = Gio.SimpleAction(name="close")  # 'When closing Nicotine+'
        action.connect("activate", self.on_close_request)
        self.add_action(action)
        self.application.set_accels_for_action("win.close", ["<Primary>q"])

        self.update_alternative_speed_icon(config.sections["transfers"]["usealtlimits"])

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
            ("#" + label, "app.quit")
        )

    def create_file_menu(self):

        menu = PopupMenu(self.application)
        self.add_connection_section(menu)
        self.add_preferences_item(menu)
        self.add_quit_item(menu)

        return menu

    def create_view_menu(self):

        menu = PopupMenu(self.application)
        menu.add_items(
            ("$" + _("Prefer Dark _Mode"), "app.prefer-dark-mode"),
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
            ("#" + _("_Configure Shares"), "app.configure-shares"),
            ("", None)
        )

    def add_browse_shares_section(self, menu):

        menu.add_items(
            ("#" + _("_Browse Public Shares"), "app.browse-public-shares"),
            ("#" + _("Bro_wse Buddy Shares"), "app.browse-buddy-shares"),
            ("", None)
        )

    def create_shares_menu(self):

        menu = PopupMenu(self.application)
        self.add_configure_shares_section(menu)
        self.add_browse_shares_section(menu)

        return menu

    def create_help_menu(self):

        menu = PopupMenu(self.application)
        menu.add_items(
            ("#" + _("_Keyboard Shortcuts"), "app.keyboard-shortcuts"),
            ("#" + _("_Setup Assistant"), "app.setup-assistant"),
            ("#" + _("_Transfer Statistics"), "app.transfer-statistics"),
            ("", None),
            ("#" + _("Report a _Bug"), "app.report-bug"),
            ("#" + _("Improve T_ranslations"), "app.improve-translations"),
            ("#" + _("Check _Latest Version"), "app.check-latest-version"),
            ("", None),
            ("#" + _("_About Nicotine+"), "app.about")
        )

        return menu

    def create_hamburger_menu(self):
        """ Menu button menu (header bar enabled) """

        menu = PopupMenu(self.application)
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

        menu = PopupMenu(self.application)
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
                self.application.set_accels_for_action("win.menu", ["F10"])

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
                self.application.set_accels_for_action("win.menu", [])

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
            self.userlist.update_visible()

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
            self.lookup_action("toggle-buddy-list").emit("activate", GLib.Variant("s", "tab"))

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

    def on_search(self, *_args):
        self.search.on_search()

    """ User Info """

    def on_get_user_info(self, *_args):
        self.userinfo.on_get_user_info()

    """ Shares """

    def on_get_shares(self, *_args):
        self.userbrowse.on_get_shares()

    """ Chat """

    def on_get_private_chat(self, *_args):
        self.privatechat.on_get_private_chat()

    def on_create_room(self, *_args):
        self.chatrooms.on_create_room()

    """ Away Mode """

    def set_away_mode(self, _is_away):
        self.update_user_status()

    def set_auto_away(self, active=True):

        if active:
            self.auto_away = True
            self.away_timer_id = None

            if core.user_status != UserStatus.AWAY:
                core.set_away_mode(True)

            return

        if self.auto_away:
            self.auto_away = False

            if core.user_status == UserStatus.AWAY:
                core.set_away_mode(False)

        # Reset away timer
        self.remove_away_timer()
        self.create_away_timer()

    def create_away_timer(self):

        if core.user_status != UserStatus.ONLINE:
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

    """ User Actions """

    def on_add_buddy(self, *_args):
        self.userlist.on_add_buddy()

    """ Log Pane """

    def create_log_context_menu(self):

        popup_menu_log_categories = PopupMenu(self.application)
        popup_menu_log_categories.add_items(
            ("$" + _("Downloads"), "app.log-downloads"),
            ("$" + _("Uploads"), "app.log-uploads"),
            ("$" + _("Search"), "app.log-searches"),
            ("$" + _("Chat"), "app.log-chat"),
            ("", None),
            ("$" + _("[Debug] Connections"), "app.log-connections"),
            ("$" + _("[Debug] Messages"), "app.log-messages"),
            ("$" + _("[Debug] Transfers"), "app.log-transfers"),
            ("$" + _("[Debug] Miscellaneous"), "app.log-miscellaneous"),
        )

        PopupMenu(self.application, self.log_view.textview, self.on_popup_menu_log).add_items(
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
            MessageDialog(parent=self, title=title, message=msg).show()

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
            self.application.tray_icon.set_download_status(_("Downloads: %(speed)s") % {'speed': download_bandwidth})

        if self.upload_status_label.get_text() != upload_bandwidth_text:
            self.upload_status_label.set_text(upload_bandwidth_text)
            self.application.tray_icon.set_upload_status(_("Uploads: %(speed)s") % {'speed': upload_bandwidth})

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

    """ Exit """

    def on_close_request(self, *_args):

        if config.sections["ui"]["exitdialog"] >= 2:  # 2: 'Run in Background'
            self.hide()
            return True

        core.confirm_quit(remember=True)
        return True

    def on_shutdown(self, *_args):

        # Save visible columns
        self.save_columns()
        config.write_configuration()

    def hide(self):

        if not self.is_visible():
            return

        # Save visible columns, in case application is killed later
        self.save_columns()

        # Close any visible dialogs
        for dialog in reversed(Window.active_dialogs):
            dialog.close()

        # Run in Background
        self.window.hide()

        # Save config, in case application is killed later
        config.write_configuration()
