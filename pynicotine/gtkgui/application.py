# COPYRIGHT (C) 2020-2024 Nicotine+ Contributors
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

import pynicotine
from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.logfacility import log
from pynicotine.shares import PermissionLevel
from pynicotine.slskmessages import UserStatus
from pynicotine.utils import open_uri

GTK_API_VERSION = Gtk.get_major_version()
GTK_MINOR_VERSION = Gtk.get_minor_version()
GTK_MICRO_VERSION = Gtk.get_micro_version()
GTK_GUI_FOLDER_PATH = os.path.normpath(os.path.dirname(os.path.realpath(__file__)))
LIBADWAITA_API_VERSION = 0

if GTK_API_VERSION >= 4:
    try:
        if "NICOTINE_LIBADWAITA" not in os.environ:
            # Only attempt to use libadwaita in a standard GNOME session or Ubuntu's
            # GNOME session (identified as 'GNOME' and 'ubuntu:GNOME'). Filter out
            # other desktop environments that specify GNOME as a fallback, such as
            # Budgie (identified as 'Budgie:GNOME').
            current_desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()

            os.environ["NICOTINE_LIBADWAITA"] = str(int(
                sys.platform in {"win32", "darwin"}
                or current_desktop == "gnome"
                or ("ubuntu" in current_desktop and "gnome" in current_desktop)
            ))

        if os.environ.get("NICOTINE_LIBADWAITA") == "1":
            gi.require_version("Adw", "1")

            from gi.repository import Adw  # pylint: disable=ungrouped-imports
            LIBADWAITA_API_VERSION = Adw.MAJOR_VERSION

    except (ImportError, ValueError):
        pass


class Application:

    def __init__(self, start_hidden, ci_mode, isolated_mode, multi_instance):

        self._instance = Gtk.Application(application_id=pynicotine.__application_id__)
        GLib.set_application_name(pynicotine.__application_name__)
        GLib.set_prgname(pynicotine.__application_id__)

        if multi_instance:
            self._instance.set_flags(Gio.ApplicationFlags.NON_UNIQUE)

        self.start_hidden = start_hidden
        self.ci_mode = ci_mode
        self.isolated_mode = isolated_mode

        self.window = None
        self.about = None
        self.fast_configure = None
        self.preferences = None
        self.file_properties = None
        self.shortcuts = None
        self.statistics = None
        self.wishlist = None
        self.tray_icon = None
        self.spell_checker = None

        # Show errors in the GUI from here on
        sys.excepthook = self.on_critical_error

        self._instance.connect("activate", self.on_activate)
        self._instance.connect("shutdown", self.on_shutdown)

        for event_name, callback in (
            ("confirm-quit", self.on_confirm_quit),
            ("invalid-password", self.on_invalid_password),
            ("invalid-username", self.on_invalid_password),
            ("quit", self._instance.quit),
            ("server-login", self._update_user_status),
            ("server-disconnect", self._update_user_status),
            ("setup", self.on_fast_configure),
            ("shares-unavailable", self.on_shares_unavailable),
            ("show-notification", self._show_notification),
            ("show-chatroom-notification", self._show_chatroom_notification),
            ("show-download-notification", self._show_download_notification),
            ("show-private-chat-notification", self._show_private_chat_notification),
            ("show-search-notification", self._show_search_notification),
            ("user-status", self.on_user_status)
        ):
            events.connect(event_name, callback)

    def run(self):
        return self._instance.run()

    def add_action(self, action):
        self._instance.add_action(action)

    def lookup_action(self, action_name):
        return self._instance.lookup_action(action_name)

    def remove_action(self, action):
        self._instance.remove_action(action)

    def add_window(self, window):
        self._instance.add_window(window)

    def _set_up_actions(self):

        # Regular actions

        for action_name, callback, parameter_type, is_enabled in (
            # General
            ("disabled", None, None, False),
            ("connect", self.on_connect, None, True),
            ("disconnect", self.on_disconnect, None, False),
            ("soulseek-privileges", self.on_soulseek_privileges, None, False),
            ("away", self.on_away, None, True),
            ("away-accel", self.on_away_accelerator, None, False),
            ("message-downloading-users", self.on_message_downloading_users, None, False),
            ("message-buddies", self.on_message_buddies, None, False),
            ("wishlist", self.on_wishlist, None, True),
            ("confirm-quit", self.on_confirm_quit_request, None, True),
            ("force-quit", self.on_force_quit_request, None, True),
            ("quit", self.on_quit_request, None, True),

            # Shares
            ("rescan-shares", self.on_rescan_shares, None, True),
            ("browse-public-shares", self.on_browse_public_shares, None, True),
            ("browse-buddy-shares", self.on_browse_buddy_shares, None, True),
            ("browse-trusted-shares", self.on_browse_trusted_shares, None, True),
            ("load-shares-from-disk", self.on_load_shares_from_disk, None, True),

            # Configuration

            ("preferences", self.on_preferences, None, True),
            ("configure-shares", self.on_configure_shares, None, True),
            ("configure-downloads", self.on_configure_downloads, None, True),
            ("configure-uploads", self.on_configure_uploads, None, True),
            ("configure-chats", self.on_configure_chats, None, True),
            ("configure-searches", self.on_configure_searches, None, True),
            ("configure-ignored-users", self.on_configure_ignored_users, None, True),
            ("configure-account", self.on_configure_account, None, True),
            ("configure-user-profile", self.on_configure_user_profile, None, True),
            ("personal-profile", self.on_personal_profile, None, True),

            # Notifications
            ("chatroom-notification-activated", self.on_chatroom_notification_activated, "s", True),
            ("download-notification-activated", self.on_downloads, None, True),
            ("private-chat-notification-activated", self.on_private_chat_notification_activated, "s", True),
            ("search-notification-activated", self.on_search_notification_activated, "s", True),

            # Help
            ("keyboard-shortcuts", self.on_keyboard_shortcuts, None, True),
            ("setup-assistant", self.on_fast_configure, None, True),
            ("transfer-statistics", self.on_transfer_statistics, None, True),
            ("report-bug", self.on_report_bug, None, True),
            ("improve-translations", self.on_improve_translations, None, True),
            ("about", self.on_about, None, True)
        ):
            if parameter_type:
                parameter_type = GLib.VariantType(parameter_type)

            action = Gio.SimpleAction(name=action_name, parameter_type=parameter_type, enabled=is_enabled)

            if callback:
                action.connect("activate", callback)

            self.add_action(action)

        self.lookup_action("away-accel").cooldown_time = 0  # needed to prevent server ban

        # Stateful actions

        enabled_logs = config.sections["logging"]["debugmodes"]

        for action_name, callback, state in (
            # Logging
            ("log-downloads", self.on_debug_downloads, ("download" in enabled_logs)),
            ("log-uploads", self.on_debug_uploads, ("upload" in enabled_logs)),
            ("log-searches", self.on_debug_searches, ("search" in enabled_logs)),
            ("log-chat", self.on_debug_chat, ("chat" in enabled_logs)),
            ("log-connections", self.on_debug_connections, ("connection" in enabled_logs)),
            ("log-messages", self.on_debug_messages, ("message" in enabled_logs)),
            ("log-transfers", self.on_debug_transfers, ("transfer" in enabled_logs)),
            ("log-miscellaneous", self.on_debug_miscellaneous, ("miscellaneous" in enabled_logs))
        ):
            action = Gio.SimpleAction(name=action_name, state=GLib.Variant.new_boolean(state))
            action.connect("change-state", callback)
            self.add_action(action)

    def _set_accels_for_action(self, action, accels):

        if GTK_API_VERSION >= 4 and sys.platform == "darwin":
            # Use Command key instead of Ctrl in accelerators on macOS
            for i, accelerator in enumerate(accels):
                accels[i] = accelerator.replace("<Primary>", "<Meta>")

        self._instance.set_accels_for_action(action, accels)

    def _set_up_action_accels(self):

        for action_name, accelerators in (
            # Global accelerators
            ("app.connect", ["<Shift><Primary>c"]),
            ("app.disconnect", ["<Shift><Primary>d"]),
            ("app.away-accel", ["<Shift><Primary>a"]),
            ("app.wishlist", ["<Shift><Primary>w"]),
            ("app.confirm-quit", ["<Primary>q"]),
            ("app.force-quit", ["<Primary><Alt>q"]),
            ("app.quit", ["<Primary>q"]),  # Only used to show accelerator in menus
            ("app.rescan-shares", ["<Shift><Primary>r"]),
            ("app.keyboard-shortcuts", ["<Primary>question", "F1"]),
            ("app.preferences", ["<Primary>comma", "<Primary>p"]),

            # Window accelerators
            ("win.main-menu", ["F10"]),
            ("win.context-menu", ["<Shift>F10"]),
            ("win.change-focus-view", ["F6"]),
            ("win.show-log-pane", ["<Primary>l"]),
            ("win.reopen-closed-tab", ["<Primary><Shift>t"]),
            ("win.close-tab", ["<Primary>F4", "<Primary>w"]),
            ("win.cycle-tabs", ["<Control>Tab"]),
            ("win.cycle-tabs-reverse", ["<Control><Shift>Tab"]),

            # Other accelerators (logic defined elsewhere, actions only used for shortcuts dialog)
            ("accel.cut-clipboard", ["<Primary>x"]),
            ("accel.copy-clipboard", ["<Primary>c"]),
            ("accel.paste-clipboard", ["<Primary>v"]),
            ("accel.insert-emoji", ["<Control>period"]),
            ("accel.select-all", ["<Primary>a"]),
            ("accel.find", ["<Primary>f"]),
            ("accel.find-next-match", ["<Primary>g"]),
            ("accel.find-previous-match", ["<Shift><Primary>g"]),
            ("accel.refresh", ["<Primary>r", "F5"]),
            ("accel.remove", ["Delete"]),
            ("accel.toggle-row-expand", ["<Primary>backslash"]),
            ("accel.save", ["<Primary>s"]),
            ("accel.download-to", ["<Primary>Return"]),
            ("accel.file-properties", ["<Alt>Return"]),
            ("accel.back", ["BackSpace"]),
            ("accel.retry-transfer", ["r"]),
            ("accel.abort-transfer", ["t"])
        ):
            self._set_accels_for_action(action_name, accelerators)

        numpad_accels = []

        for num in range(1, 10):
            numpad_accels.append(f"<Alt>KP_{num}")
            self._set_accels_for_action(f"win.primary-tab-{num}", [f"<Primary>{num}", f"<Alt>{num}"])

        # Disable Alt+1-9 accelerators for numpad keys to avoid conflict with Alt codes
        self._set_accels_for_action("app.disabled", numpad_accels)

    def _update_user_status(self, *_args):

        status = core.users.login_status
        is_online = (status != UserStatus.OFFLINE)

        self.lookup_action("connect").set_enabled(not is_online)

        for action_name in ("disconnect", "soulseek-privileges", "away-accel",
                            "message-downloading-users", "message-buddies"):
            self.lookup_action(action_name).set_enabled(is_online)

        self.tray_icon.update()

    # Primary Menus #

    @staticmethod
    def _add_connection_section(menu):

        menu.add_items(
            ("=" + _("_Connect"), "app.connect"),
            ("=" + _("_Disconnect"), "app.disconnect"),
            ("#" + _("Soulseek _Privileges"), "app.soulseek-privileges"),
            ("", None)
        )

    @staticmethod
    def _add_preferences_item(menu):
        menu.add_items(("^" + _("_Preferences"), "app.preferences"))

    def _add_quit_item(self, menu):

        menu.add_items(
            ("", None),
            ("^" + _("_Quit"), "app.quit")
        )

    def _create_file_menu(self):

        from pynicotine.gtkgui.widgets.popupmenu import PopupMenu

        menu = PopupMenu(self)
        self._add_connection_section(menu)
        self._add_preferences_item(menu)
        self._add_quit_item(menu)

        return menu

    def _add_browse_shares_section(self, menu):

        menu.add_items(
            ("#" + _("Browse _Public Shares"), "app.browse-public-shares"),
            ("#" + _("Browse _Buddy Shares"), "app.browse-buddy-shares"),
            ("#" + _("Browse _Trusted Shares"), "app.browse-trusted-shares")
        )

    def _create_shares_menu(self):

        from pynicotine.gtkgui.widgets.popupmenu import PopupMenu

        menu = PopupMenu(self)
        menu.add_items(
            ("#" + _("_Rescan Shares"), "app.rescan-shares"),
            ("#" + _("Configure _Shares"), "app.configure-shares"),
            ("", None)
        )
        self._add_browse_shares_section(menu)

        return menu

    def _create_browse_shares_menu(self):

        from pynicotine.gtkgui.widgets.popupmenu import PopupMenu

        menu = PopupMenu(self)
        self._add_browse_shares_section(menu)

        return menu

    def _create_help_menu(self):

        from pynicotine.gtkgui.widgets.popupmenu import PopupMenu

        menu = PopupMenu(self)
        menu.add_items(
            ("#" + _("_Keyboard Shortcuts"), "app.keyboard-shortcuts"),
            ("#" + _("_Setup Assistant"), "app.setup-assistant"),
            ("#" + _("_Transfer Statistics"), "app.transfer-statistics"),
            ("", None)
        )
        if not self.isolated_mode:
            menu.add_items(
                ("#" + _("Report a _Bug"), "app.report-bug"),
                ("#" + _("Improve T_ranslations"), "app.improve-translations"),
                ("", None)
            )
        menu.add_items(
            ("^" + _("_About Nicotine+"), "app.about")
        )

        return menu

    def _set_up_menubar(self):

        from pynicotine.gtkgui.widgets.popupmenu import PopupMenu

        menu = PopupMenu(self)
        menu.add_items(
            (">" + _("_File"), self._create_file_menu()),
            (">" + _("_Shares"), self._create_shares_menu()),
            (">" + _("_Help"), self._create_help_menu())
        )

        menu.update_model()
        self._instance.set_menubar(menu.model)

    def create_hamburger_menu(self):

        from pynicotine.gtkgui.widgets.popupmenu import PopupMenu

        menu = PopupMenu(self)
        self._add_connection_section(menu)
        menu.add_items(
            ("#" + _("_Rescan Shares"), "app.rescan-shares"),
            (">" + _("_Browse Shares"), self._create_browse_shares_menu()),
            ("#" + _("Configure _Shares"), "app.configure-shares"),
            ("", None),
            (">" + _("_Help"), self._create_help_menu())
        )
        self._add_preferences_item(menu)
        self._add_quit_item(menu)

        menu.update_model()
        return menu

    # Notifications #

    def _show_notification(self, message, title=None, action=None, action_target=None, high_priority=False):

        if title is None:
            title = pynicotine.__application_name__

        title = title.strip()
        message = message.strip()

        try:
            if sys.platform == "win32":
                self.tray_icon.show_notification(
                    title=title, message=message, action=action, action_target=action_target,
                    high_priority=high_priority
                )
                return

            priority = Gio.NotificationPriority.HIGH if high_priority else Gio.NotificationPriority.NORMAL

            notification = Gio.Notification.new(title)
            notification.set_body(message)
            notification.set_priority(priority)

            # Fix notification icon in Snap package
            snap_name = os.environ.get("SNAP_NAME")

            if snap_name:
                notification.set_icon(Gio.ThemedIcon(name=f"snap.{snap_name}.{pynicotine.__application_id__}"))

            # Unity doesn't support default click actions, and replaces the notification with a dialog.
            # Disable actions to prevent this from happening.
            if action and os.environ.get("XDG_CURRENT_DESKTOP", "").lower() != "unity":
                if action_target:
                    notification.set_default_action_and_target(action, GLib.Variant.new_string(action_target))
                else:
                    notification.set_default_action(action)

            self._instance.send_notification(id=None, notification=notification)

            if config.sections["notifications"]["notification_popup_sound"]:
                Gdk.Display.get_default().beep()

        except Exception as error:
            log.add(_("Unable to show notification: %s"), error)

    def _show_chatroom_notification(self, room, message, title=None, high_priority=False):

        self._show_notification(
            message, title, action="app.chatroom-notification-activated", action_target=room,
            high_priority=high_priority
        )

        if high_priority:
            self.window.set_urgency_hint(True)

    def _show_download_notification(self, message, title=None, high_priority=False):

        self._show_notification(
            message, title, action="app.download-notification-activated",
            high_priority=high_priority
        )

    def _show_private_chat_notification(self, user, message, title=None):

        self._show_notification(
            message, title, action="app.private-chat-notification-activated", action_target=user,
            high_priority=True
        )
        self.window.set_urgency_hint(True)

    def _show_search_notification(self, search_token, message, title=None):

        self._show_notification(
            message, title, action="app.search-notification-activated", action_target=search_token,
            high_priority=True
        )

    # Core Events #

    def on_confirm_quit_response(self, dialog, response_id, _data):

        should_finish_uploads = dialog.get_option_value()

        if response_id == "quit":
            if should_finish_uploads:
                core.uploads.request_shutdown()
            else:
                core.quit()

        elif response_id == "run_background":
            self.window.hide()

    def on_confirm_quit(self):

        has_active_uploads = core.uploads.has_active_uploads()

        if not self.window.is_visible():
            # Never show confirmation dialog when main window is hidden
            core.quit()
            return

        from pynicotine.gtkgui.widgets.dialogs import OptionDialog

        if has_active_uploads:
            message = _("You are still uploading files. Do you really want to exit?")
            option_label = _("Wait for uploads to finish")
        else:
            message = _("Do you really want to exit?")
            option_label = None

        buttons = [
            ("cancel", _("_No")),
            ("quit", _("_Quit")),
            ("run_background", _("_Run in Background"))
        ]

        OptionDialog(
            parent=self.window,
            title=_("Quit Nicotine+"),
            message=message,
            buttons=buttons,
            option_label=option_label,
            callback=self.on_confirm_quit_response
        ).present()

    def on_shares_unavailable_response(self, _dialog, response_id, _data):
        core.shares.rescan_shares(force=(response_id == "force_rescan"))

    def on_shares_unavailable(self, shares):

        from pynicotine.gtkgui.widgets.dialogs import OptionDialog

        shares_list_message = ""

        for virtual_name, folder_path in shares:
            shares_list_message += f'• "{virtual_name}" {folder_path}\n'

        OptionDialog(
            parent=self.window,
            title=_("Shares Not Available"),
            message=_("Verify that external disks are mounted and folder permissions are correct."),
            long_message=shares_list_message,
            buttons=[
                ("cancel", _("_Cancel")),
                ("ok", _("_Retry")),
                ("force_rescan", _("_Force Rescan"))
            ],
            destructive_response_id="force_rescan",
            callback=self.on_shares_unavailable_response
        ).present()

    def on_invalid_password(self):
        self.on_fast_configure(invalid_password=True)

    def on_user_status(self, msg):
        if msg.user == core.users.login_username:
            self._update_user_status()

    # Actions #

    def on_connect(self, *_args):
        if core.users.login_status == UserStatus.OFFLINE:
            core.connect()

    def on_disconnect(self, *_args):
        if core.users.login_status != UserStatus.OFFLINE:
            core.disconnect()

    def on_soulseek_privileges(self, *_args):
        core.users.request_check_privileges(should_open_url=True)

    def on_preferences(self, *_args, page_id="network"):

        if self.preferences is None:
            from pynicotine.gtkgui.dialogs.preferences import Preferences
            self.preferences = Preferences(self)

        self.preferences.set_settings()
        self.preferences.set_active_page(page_id)
        self.preferences.present()

    def on_set_debug_level(self, action, state, level):

        if state.get_boolean():
            log.add_log_level(level)
        else:
            log.remove_log_level(level)

        action.set_state(state)

    def on_debug_downloads(self, action, state):
        self.on_set_debug_level(action, state, "download")

    def on_debug_uploads(self, action, state):
        self.on_set_debug_level(action, state, "upload")

    def on_debug_searches(self, action, state):
        self.on_set_debug_level(action, state, "search")

    def on_debug_chat(self, action, state):
        self.on_set_debug_level(action, state, "chat")

    def on_debug_connections(self, action, state):
        self.on_set_debug_level(action, state, "connection")

    def on_debug_messages(self, action, state):
        self.on_set_debug_level(action, state, "message")

    def on_debug_transfers(self, action, state):
        self.on_set_debug_level(action, state, "transfer")

    def on_debug_miscellaneous(self, action, state):
        self.on_set_debug_level(action, state, "miscellaneous")

    def on_fast_configure(self, *_args, invalid_password=False):

        if self.fast_configure is None:
            from pynicotine.gtkgui.dialogs.fastconfigure import FastConfigure
            self.fast_configure = FastConfigure(self)

        if invalid_password and self.fast_configure.is_visible():
            self.fast_configure.hide()

        self.fast_configure.invalid_password = invalid_password
        self.fast_configure.present()

    def on_keyboard_shortcuts(self, *_args):

        if self.shortcuts is None:
            from pynicotine.gtkgui.dialogs.shortcuts import Shortcuts
            self.shortcuts = Shortcuts(self)

        self.shortcuts.present()

    def on_transfer_statistics(self, *_args):

        if self.statistics is None:
            from pynicotine.gtkgui.dialogs.statistics import Statistics
            self.statistics = Statistics(self)

        self.statistics.present()

    @staticmethod
    def on_report_bug(*_args):
        open_uri(pynicotine.__issue_tracker_url__)

    @staticmethod
    def on_improve_translations(*_args):
        open_uri(pynicotine.__translations_url__)

    def on_wishlist(self, *_args):

        if self.wishlist is None:
            from pynicotine.gtkgui.dialogs.wishlist import WishList
            self.wishlist = WishList(self)

        self.wishlist.present()

    def on_about(self, *_args):

        if self.about is None:
            from pynicotine.gtkgui.dialogs.about import About
            self.about = About(self)

        self.about.present()

    def on_chatroom_notification_activated(self, _action, room_variant):

        room = room_variant.get_string()
        core.chatrooms.show_room(room)

        self.window.present()

    def on_private_chat_notification_activated(self, _action, user_variant):

        user = user_variant.get_string()
        core.privatechat.show_user(user)

        self.window.present()

    def on_search_notification_activated(self, _action, search_token_variant):

        search_token = int(search_token_variant.get_string())
        core.search.show_search(search_token)

        self.window.present()

    def on_downloads(self, *_args):
        self.window.change_main_page(self.window.downloads_page)
        self.window.present()

    def on_uploads(self, *_args):
        self.window.change_main_page(self.window.uploads_page)
        self.window.present()

    def on_private_chat(self, *_args):
        self.window.change_main_page(self.window.private_page)
        self.window.present()

    def on_chat_rooms(self, *_args):
        self.window.change_main_page(self.window.chatrooms_page)
        self.window.present()

    def on_searches(self, *_args):
        self.window.change_main_page(self.window.search_page)
        self.window.present()

    def on_message_users_response(self, dialog, _response_id, target):

        message = dialog.get_entry_value()

        if message:
            core.privatechat.send_message_users(target, message)

    def on_message_downloading_users(self, *_args):

        from pynicotine.gtkgui.widgets.dialogs import EntryDialog

        EntryDialog(
            parent=self.window,
            title=_("Message Downloading Users"),
            message=_("Send private message to all users who are downloading from you:"),
            action_button_label=_("_Send Message"),
            callback=self.on_message_users_response,
            callback_data="downloading",
            show_emoji_icon=True
        ).present()

    def on_message_buddies(self, *_args):

        from pynicotine.gtkgui.widgets.dialogs import EntryDialog

        EntryDialog(
            parent=self.window,
            title=_("Message Buddies"),
            message=_("Send private message to all online buddies:"),
            action_button_label=_("_Send Message"),
            callback=self.on_message_users_response,
            callback_data="buddies",
            show_emoji_icon=True
        ).present()

    def on_rescan_shares(self, *_args):
        core.shares.rescan_shares()

    def on_browse_public_shares(self, *_args):
        core.userbrowse.browse_local_shares(permission_level=PermissionLevel.PUBLIC, new_request=True)

    def on_browse_buddy_shares(self, *_args):
        core.userbrowse.browse_local_shares(permission_level=PermissionLevel.BUDDY, new_request=True)

    def on_browse_trusted_shares(self, *_args):
        core.userbrowse.browse_local_shares(permission_level=PermissionLevel.TRUSTED, new_request=True)

    def on_load_shares_from_disk_selected(self, selected_file_paths, _data):
        for file_path in selected_file_paths:
            core.userbrowse.load_shares_list_from_disk(file_path)

    def on_load_shares_from_disk(self, *_args):

        from pynicotine.gtkgui.widgets.filechooser import FileChooser

        FileChooser(
            parent=self.window,
            title=_("Select a Saved Shares List File"),
            callback=self.on_load_shares_from_disk_selected,
            initial_folder=core.userbrowse.create_user_shares_folder(),
            select_multiple=True
        ).present()

    def on_personal_profile(self, *_args):
        core.userinfo.show_user()

    def on_configure_shares(self, *_args):
        self.on_preferences(page_id="shares")

    def on_configure_searches(self, *_args):
        self.on_preferences(page_id="searches")

    def on_configure_chats(self, *_args):
        self.on_preferences(page_id="chats")

    def on_configure_downloads(self, *_args):
        self.on_preferences(page_id="downloads")

    def on_configure_uploads(self, *_args):
        self.on_preferences(page_id="uploads")

    def on_configure_ignored_users(self, *_args):
        self.on_preferences(page_id="ignored-users")

    def on_configure_account(self, *_args):
        self.on_preferences(page_id="network")

    def on_configure_user_profile(self, *_args):
        self.on_preferences(page_id="user-profile")

    def on_window_hide_unhide(self, *_args):

        if self.window.is_visible():
            self.window.hide()
            return

        self.window.present()

        # Workaround for broken window size when restoring maximized window from tray icon
        if sys.platform == "win32" and self.window.is_maximized():
            self.window.unmaximize()
            self.window.maximize()

    def on_away_accelerator(self, action, *_args):
        """Ctrl+H: Away/Online toggle."""

        current_time = time.monotonic()

        if (current_time - action.cooldown_time) >= 1:
            # Prevent rapid key-repeat toggling to avoid server ban
            self.on_away()
            action.cooldown_time = current_time

    def on_away(self, *_args):
        """Away/Online status button."""

        if core.users.login_status == UserStatus.OFFLINE:
            core.connect()
            return

        core.users.set_away_mode(core.users.login_status != UserStatus.AWAY, save_state=True)

    # Running #

    def _raise_exception(self, exc_value):
        raise exc_value

    def _show_critical_error_dialog_response(self, _dialog, response_id, data):

        loop, error = data

        if response_id == "copy_report_bug":
            from pynicotine.gtkgui.widgets import clipboard

            clipboard.copy_text(error)
            open_uri(pynicotine.__issue_tracker_url__)

            self._show_critical_error_dialog(error, loop)
            return

        loop.quit()

    def _show_critical_error_dialog(self, error, loop):

        from pynicotine.gtkgui.widgets.dialogs import OptionDialog

        OptionDialog(
            parent=self.window,
            title=_("Critical Error"),
            message=_("Nicotine+ has encountered a critical error and needs to exit. "
                      "Please copy the following message and include it in a bug report:"),
            long_message=error,
            buttons=[
                ("quit", _("_Quit Nicotine+")),
                ("copy_report_bug", _("_Copy & Report Bug"))
            ],
            callback=self._show_critical_error_dialog_response,
            callback_data=(loop, error)
        ).present()

    def _on_critical_error(self, exc_type, exc_value, exc_traceback):

        if self.ci_mode:
            core.quit()
            self._raise_exception(exc_value)
            return

        from traceback import format_tb

        # Check if exception occurred in a plugin
        if exc_traceback is not None:
            traceback = exc_traceback

            while traceback.tb_next:
                file_path = traceback.tb_frame.f_code.co_filename

                for plugin_name in core.pluginhandler.enabled_plugins:
                    plugin_path = core.pluginhandler.get_plugin_path(plugin_name)

                    if file_path.startswith(plugin_path):
                        core.pluginhandler.show_plugin_error(plugin_name, exc_value)
                        return

                traceback = traceback.tb_next

        # Show critical error dialog
        loop = GLib.MainLoop()
        gtk_version = f"{Gtk.get_major_version()}.{Gtk.get_minor_version()}.{Gtk.get_micro_version()}"
        error = (f"Nicotine+ Version: {pynicotine.__version__}\nGTK Version: {gtk_version}\n"
                 f"Python Version: {sys.version.split()[0]} ({sys.platform})\n\n"
                 f"Type: {exc_type}\nValue: {exc_value}\nTraceback: {''.join(format_tb(exc_traceback))}")
        self._show_critical_error_dialog(error, loop)

        # Keep dialog open if error occurs on startup
        loop.run()

        # Dialog was closed, quit
        sys.excepthook = None
        core.quit()

        # Process 'quit' event after slight delay in case thread event loop is stuck
        GLib.idle_add(lambda: events.process_thread_events() == -1, priority=GLib.PRIORITY_HIGH_IDLE)

        # Log exception in terminal
        self._raise_exception(exc_value)

    def on_critical_error(self, exc_type, exc_value, exc_traceback):

        if threading.current_thread() is threading.main_thread():
            self._on_critical_error(exc_type, exc_value, exc_traceback)
            return

        # Raise exception in the main thread
        GLib.idle_add(self._raise_exception, exc_value, priority=GLib.PRIORITY_HIGH_IDLE)

    def on_process_thread_events(self):
        return events.process_thread_events()

    def on_activate(self, *_args):

        if self.window:
            # Show the window of the running application instance
            self.window.present()
            return

        from pynicotine.gtkgui.mainwindow import MainWindow
        from pynicotine.gtkgui.widgets.theme import load_icons
        from pynicotine.gtkgui.widgets.trayicon import TrayIcon

        # Process thread events 10 times per second.
        # High priority to ensure there are no delays.
        GLib.timeout_add(100, self.on_process_thread_events, priority=GLib.PRIORITY_HIGH_IDLE)

        load_icons()

        self._set_up_actions()
        self._set_up_action_accels()
        self._set_up_menubar()

        self.tray_icon = TrayIcon(self)
        self.window = MainWindow(self)

        core.start()

        if config.sections["server"]["auto_connect_startup"]:
            core.connect()

        # Check command line option and config option
        start_hidden = (self.start_hidden or (self.tray_icon.available
                                              and config.sections["ui"]["trayicon"]
                                              and config.sections["ui"]["startup_hidden"]))

        if not start_hidden:
            self.window.present()

    def on_confirm_quit_request(self, *_args):
        core.confirm_quit()

    def on_force_quit_request(self, *_args):
        core.quit()

    def on_quit_request(self, *_args):

        if not core.uploads.has_active_uploads():
            core.quit()
            return

        core.confirm_quit()

    def on_shutdown(self, *_args):

        if self.about is not None:
            self.about.destroy()

        if self.fast_configure is not None:
            self.fast_configure.destroy()

        if self.preferences is not None:
            self.preferences.destroy()

        if self.file_properties is not None:
            self.file_properties.destroy()

        if self.shortcuts is not None:
            self.shortcuts.destroy()

        if self.statistics is not None:
            self.statistics.destroy()

        if self.wishlist is not None:
            self.wishlist.destroy()

        if self.spell_checker is not None:
            self.spell_checker.destroy()

        if self.window is not None:
            self.window.destroy()

        if self.tray_icon is not None:
            self.tray_icon.destroy()

        self.__dict__.clear()
