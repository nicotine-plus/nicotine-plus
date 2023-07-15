# COPYRIGHT (C) 2020-2023 Nicotine+ Contributors
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
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk

from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.logfacility import log
from pynicotine.slskmessages import UserStatus
from pynicotine.utils import open_uri

GTK_API_VERSION = Gtk.get_major_version()
GTK_MINOR_VERSION = Gtk.get_minor_version()
GTK_GUI_DIR = os.path.normpath(os.path.dirname(os.path.realpath(__file__)))
LIBADWAITA_API_VERSION = 0

if GTK_API_VERSION >= 4:
    try:
        if os.getenv("NICOTINE_LIBADWAITA") is None:
            os.environ["NICOTINE_LIBADWAITA"] = str(int(
                sys.platform in ("win32", "darwin") or os.environ.get("XDG_SESSION_DESKTOP") == "gnome"
            ))

        if os.getenv("NICOTINE_LIBADWAITA") == "1":
            gi.require_version("Adw", "1")

            from gi.repository import Adw  # pylint: disable=ungrouped-imports
            LIBADWAITA_API_VERSION = Adw.MAJOR_VERSION

    except (ImportError, ValueError):
        pass


class Application:

    def __init__(self, start_hidden, ci_mode, multi_instance):

        self._instance = Gtk.Application(application_id=config.application_id)
        GLib.set_application_name(config.application_name)
        GLib.set_prgname(config.application_id)

        if multi_instance:
            self._instance.set_flags(Gio.ApplicationFlags.NON_UNIQUE)

        self.start_hidden = start_hidden
        self.ci_mode = ci_mode

        self.window = None
        self.about = None
        self.fast_configure = None
        self.preferences = None
        self.file_properties = None
        self.shortcuts = None
        self.statistics = None
        self.wishlist = None
        self.tray_icon = None
        self.notifications = None
        self.spell_checker = None

        # Show errors in the GUI from here on
        sys.excepthook = self.on_critical_error

        self.connect("activate", self.on_activate)
        self.connect("shutdown", self.on_shutdown)

        for event_name, callback in (
            ("confirm-quit", self.on_confirm_quit),
            ("invalid-password", self.on_invalid_password),
            ("quit", self.on_quit),
            ("setup", self.on_fast_configure),
            ("shares-unavailable", self.on_shares_unavailable)
        ):
            events.connect(event_name, callback)

    def run(self):
        return self._instance.run()

    def connect(self, event_name, callback):
        self._instance.connect(event_name, callback)

    def add_action(self, action):
        self._instance.add_action(action)

    def lookup_action(self, action_name):
        return self._instance.lookup_action(action_name)

    def remove_action(self, action):
        self._instance.remove_action(action)

    def get_accels_for_action(self, action):
        return self._instance.get_accels_for_action(action)

    def set_accels_for_action(self, action, accels):

        if GTK_API_VERSION >= 4 and sys.platform == "darwin":
            # Use Command key instead of Ctrl in accelerators on macOS
            for i, accelerator in enumerate(accels):
                accels[i] = accelerator.replace("<Primary>", "<Meta>")

        self._instance.set_accels_for_action(action, accels)

    def add_window(self, window):
        self._instance.add_window(window)

    def set_menubar(self, model):
        self._instance.set_menubar(model)

    def send_notification(self, event_id, notification):
        self._instance.send_notification(event_id, notification)

    def init_spell_checker(self):

        try:
            gi.require_version("Gspell", "1")
            from gi.repository import Gspell
            self.spell_checker = Gspell.Checker()

        except (ImportError, ValueError):
            self.spell_checker = False

    def set_up_actions(self):

        # Regular actions

        for action_name, callback, parameter_type, is_enabled in (
            # General
            ("connect", self.on_connect, None, True),
            ("disconnect", self.on_disconnect, None, False),
            ("soulseek-privileges", self.on_soulseek_privileges, None, False),
            ("away", self.on_away, None, False),
            ("away-accel", self.on_away_accelerator, None, False),
            ("message-downloading-users", self.on_message_downloading_users, None, False),
            ("message-buddies", self.on_message_buddies, None, False),
            ("wishlist", self.on_wishlist, None, True),
            ("confirm-quit", self.on_confirm_quit_request, None, True),
            ("quit", self.on_quit_request, None, True),

            # Shares
            ("rescan-shares", self.on_rescan_shares, None, True),
            ("browse-public-shares", self.on_browse_public_shares, None, True),
            ("browse-buddy-shares", self.on_browse_buddy_shares, None, True),
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
            ("personal-profile", self.on_personal_profile, None, False),

            # Notifications
            ("chatroom-notification-activated", self.on_chatroom_notification_activated, "s", True),
            ("download-notification-activated", self.on_download_notification_activated, None, True),
            ("private-chat-notification-activated", self.on_private_chat_notification_activated, "s", True),
            ("search-notification-activated", self.on_search_notification_activated, "s", True),

            # Help
            ("keyboard-shortcuts", self.on_keyboard_shortcuts, None, True),
            ("setup-assistant", self.on_fast_configure, None, True),
            ("transfer-statistics", self.on_transfer_statistics, None, True),
            ("report-bug", self.on_report_bug, None, True),
            ("improve-translations", self.on_improve_translations, None, True),
            ("check-latest-version", self.on_check_latest_version, None, True),
            ("about", self.on_about, None, True)
        ):
            if parameter_type:
                parameter_type = GLib.VariantType(parameter_type)

            action = Gio.SimpleAction(name=action_name, parameter_type=parameter_type, enabled=is_enabled)
            action.connect("activate", callback)
            self.add_action(action)

        self.lookup_action("away-accel").cooldown_time = 0  # needed to prevent server ban

        # Stateful actions

        enabled_logs = config.sections["logging"]["debugmodes"]

        for action_name, callback, state in (
            # General
            ("prefer-dark-mode", self.on_prefer_dark_mode, config.sections["ui"]["dark_mode"]),

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
            action = Gio.SimpleAction(name=action_name, state=GLib.Variant("b", state))
            action.connect("change-state", callback)
            self.add_action(action)

    def set_up_action_accels(self):

        for action_name, accelerators in (
            # Global accelerators
            ("app.connect", ["<Shift><Primary>c"]),
            ("app.disconnect", ["<Shift><Primary>d"]),
            ("app.away-accel", ["<Primary>h"]),
            ("app.wishlist", ["<Shift><Primary>w"]),
            ("app.quit", ["<Primary><Alt>q"]),
            ("app.rescan-shares", ["<Shift><Primary>r"]),
            ("app.keyboard-shortcuts", ["<Primary>question", "F1"]),
            ("app.preferences", ["<Primary>comma", "<Primary>p"]),

            # Other accelerators (logic defined elsewhere, actions only used for shortcuts dialog)
            ("accel.cut-clipboard", ["<Primary>x"]),
            ("accel.copy-clipboard", ["<Primary>c"]),
            ("accel.paste-clipboard", ["<Primary>v"]),
            ("accel.insert-emoji", ["<Primary>period"]),
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
            self.set_accels_for_action(action_name, accelerators)

        if GTK_API_VERSION == 3 or sys.platform != "darwin":
            return

        # Built-in GTK shortcuts use Ctrl key on macOS, add shortcuts that use Command key
        for widget in (Gtk.Text, Gtk.TextView):
            for action_name, accelerator in (
                ("cut-clipboard", "<Meta>x"),
                ("copy-clipboard", "<Meta>c"),
                ("paste-clipboard", "<Meta>v"),
                ("selection.select-all", "<Meta>a"),
                ("misc.insert-emoji", "<Meta>period"),
                ("text.undo", "<Meta>z"),
                ("text.redo", "<Shift><Meta>u")
            ):
                widget.add_shortcut(
                    Gtk.Shortcut(
                        trigger=Gtk.ShortcutTrigger.parse_string(accelerator),
                        action=Gtk.NamedAction(action_name=action_name),
                    )
                )

    """ Core Events """

    def on_confirm_quit_response(self, dialog, response_id, _data):

        remember = dialog.get_option_value()

        if response_id == "quit":
            if remember:
                config.sections["ui"]["exitdialog"] = 0

            core.quit()

        elif response_id == "run_background":
            if remember:
                config.sections["ui"]["exitdialog"] = 2

            if self.window.is_visible():
                self.window.hide()

    def on_confirm_quit(self, remember=True):

        from pynicotine.gtkgui.widgets.dialogs import OptionDialog

        buttons = [
            ("cancel", _("_No")),
            ("quit", _("_Quit"))
        ]

        if self.window.is_visible():
            buttons.append(("run_background", _("_Run in Background")))

        OptionDialog(
            parent=self.window,
            title=_("Quit Nicotine+"),
            message=_("Do you really want to exit?"),
            buttons=buttons,
            option_label=_("Remember choice") if remember else None,
            callback=self.on_confirm_quit_response
        ).show()

    def on_quit(self):
        self._instance.quit()

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
        ).show()

    def on_invalid_password_response(self, *_args):
        self.on_preferences(page_id="network")

    def on_invalid_password(self):

        from pynicotine.gtkgui.widgets.dialogs import OptionDialog

        title = _("Invalid Password")
        msg = _("User %s already exists, and the password you entered is invalid. Please choose another username "
                "if this is your first time logging in.") % config.sections["server"]["login"]

        OptionDialog(
            parent=self.window,
            title=title,
            message=msg,
            buttons=[
                ("cancel", _("_Cancel")),
                ("ok", _("Change _Login Details"))
            ],
            callback=self.on_invalid_password_response
        ).show()

    """ Actions """

    def on_connect(self, *_args):
        core.connect()

    def on_disconnect(self, *_args):
        core.disconnect()

    def on_soulseek_privileges(self, *_args):

        import urllib.parse

        login = urllib.parse.quote(core.login_username)
        open_uri(config.privileges_url % login)
        core.request_check_privileges()

    def on_preferences(self, *_args, page_id="network"):

        if self.preferences is None:
            from pynicotine.gtkgui.dialogs.preferences import Preferences
            self.preferences = Preferences(self)

        self.preferences.set_settings()
        self.preferences.set_active_page(page_id)
        self.preferences.show()

    def on_chatroom_notification_activated(self, _action, room_variant):

        room = room_variant.get_string()
        core.chatrooms.show_room(room)

        self.window.show()

    def on_download_notification_activated(self, *_args):
        self.window.change_main_page(self.window.downloads_page)
        self.window.show()

    def on_private_chat_notification_activated(self, _action, user_variant):

        user = user_variant.get_string()
        core.privatechat.show_user(user)

        self.window.show()

    def on_search_notification_activated(self, _action, search_token_variant):

        search_token = int(search_token_variant.get_string())
        core.search.show_search(search_token)

        self.window.show()

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

    def on_fast_configure(self, *_args):

        if self.fast_configure is None:
            from pynicotine.gtkgui.dialogs.fastconfigure import FastConfigure
            self.fast_configure = FastConfigure(self)

        self.fast_configure.show()

    def on_keyboard_shortcuts(self, *_args):

        if self.shortcuts is None:
            from pynicotine.gtkgui.dialogs.shortcuts import Shortcuts
            self.shortcuts = Shortcuts(self)

        self.shortcuts.show()

    def on_transfer_statistics(self, *_args):

        if self.statistics is None:
            from pynicotine.gtkgui.dialogs.statistics import Statistics
            self.statistics = Statistics(self)

        self.statistics.show()

    @staticmethod
    def on_report_bug(*_args):
        open_uri(config.issue_tracker_url)

    @staticmethod
    def on_improve_translations(*_args):
        open_uri(config.translations_url)

    def on_check_latest_version(self, *_args):
        core.update_checker.check()

    def on_wishlist(self, *_args):

        if self.wishlist is None:
            from pynicotine.gtkgui.dialogs.wishlist import WishList
            self.wishlist = WishList(self)

        self.wishlist.show()

    def on_about(self, *_args):

        if self.about is None:
            from pynicotine.gtkgui.dialogs.about import About
            self.about = About(self)

        self.about.show()

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
            callback_data="downloading"
        ).show()

    def on_message_buddies(self, *_args):

        from pynicotine.gtkgui.widgets.dialogs import EntryDialog

        EntryDialog(
            parent=self.window,
            title=_("Message Buddies"),
            message=_("Send private message to all online buddies:"),
            action_button_label=_("_Send Message"),
            callback=self.on_message_users_response,
            callback_data="buddies"
        ).show()

    def on_rescan_shares(self, *_args):
        core.shares.rescan_shares()

    def on_browse_public_shares(self, *_args):
        core.userbrowse.browse_local_shares(share_type="public", new_request=True)

    def on_browse_buddy_shares(self, *_args):
        core.userbrowse.browse_local_shares(share_type="buddy", new_request=True)

    def on_load_shares_from_disk_selected(self, selected, _data):
        for filename in selected:
            core.userbrowse.load_shares_list_from_disk(filename)

    def on_load_shares_from_disk(self, *_args):

        from pynicotine.gtkgui.widgets.filechooser import FileChooser

        FileChooser(
            parent=self.window,
            title=_("Select a Saved Shares List File"),
            callback=self.on_load_shares_from_disk_selected,
            initial_folder=core.userbrowse.create_user_shares_folder(),
            select_multiple=True
        ).show()

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

    def on_personal_profile(self, *_args):
        core.userinfo.show_user(core.login_username)

    @staticmethod
    def on_prefer_dark_mode(action, *_args):

        from pynicotine.gtkgui.widgets.theme import set_dark_mode

        state = config.sections["ui"]["dark_mode"]
        set_dark_mode(not state)
        action.set_state(GLib.Variant("b", not state))

        config.sections["ui"]["dark_mode"] = not state

    def on_away_accelerator(self, action, *_args):
        """ Ctrl+H: Away/Online toggle """

        current_time = time.time()

        if (current_time - action.cooldown_time) >= 1:
            # Prevent rapid key-repeat toggling to avoid server ban
            self.on_away()
            action.cooldown_time = current_time

    def on_away(self, *_args):
        """ Away/Online status button """

        core.set_away_mode(core.user_status != UserStatus.AWAY, save_state=True)

    """ Running """

    def raise_exception(self, exc_value):
        raise exc_value

    def on_critical_error_response(self, _dialog, response_id, data):

        loop, error = data

        if response_id == "copy_report_bug":
            from pynicotine.gtkgui.widgets import clipboard

            clipboard.copy_text(error)
            open_uri(config.issue_tracker_url)

            self.show_critical_error_dialog(error, loop)
            return

        loop.quit()
        core.quit()

    def show_critical_error_dialog(self, error, loop):

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
            callback=self.on_critical_error_response,
            callback_data=(loop, error)
        ).show()

    def _on_critical_error(self, exc_type, exc_value, exc_traceback):

        if self.ci_mode:
            core.quit()
            self.raise_exception(exc_value)
            return

        from traceback import format_tb

        # Check if exception occurred in a plugin
        if core.pluginhandler is not None:
            traceback = exc_traceback

            while True:
                if not traceback.tb_next:
                    break

                filename = traceback.tb_frame.f_code.co_filename

                for plugin_name in core.pluginhandler.enabled_plugins:
                    path = core.pluginhandler.get_plugin_path(plugin_name)

                    if filename.startswith(path):
                        core.pluginhandler.show_plugin_error(
                            plugin_name, exc_type, exc_value, exc_traceback)
                        return

                traceback = traceback.tb_next

        # Show critical error dialog
        loop = GLib.MainLoop()
        error = (f"Nicotine+ Version: {config.version}\nGTK Version: {config.gtk_version}\n"
                 f"Python Version: {config.python_version} ({sys.platform})\n\n"
                 f"Type: {exc_type}\nValue: {exc_value}\nTraceback: {''.join(format_tb(exc_traceback))}")
        self.show_critical_error_dialog(error, loop)

        # Keep dialog open if error occurs on startup
        loop.run()
        self.raise_exception(exc_value)

    def on_critical_error(self, _exc_type, exc_value, _exc_traceback):

        if threading.current_thread() is threading.main_thread():
            self._on_critical_error(_exc_type, exc_value, _exc_traceback)
            return

        # Raise exception in the main thread
        GLib.idle_add(self.raise_exception, exc_value)

    def on_process_thread_events(self):
        events.process_thread_events()
        return not core.shutdown

    def on_activate(self, *_args):

        if self.window:
            # Show the window of the running application instance
            self.window.show()
            return

        from pynicotine.gtkgui.mainwindow import MainWindow
        from pynicotine.gtkgui.widgets.notifications import Notifications
        from pynicotine.gtkgui.widgets.theme import load_icons
        from pynicotine.gtkgui.widgets.trayicon import TrayIcon

        load_icons()

        self.set_up_actions()
        self.set_up_action_accels()

        self.tray_icon = TrayIcon(self)
        self.notifications = Notifications(self)
        self.window = MainWindow(self)

        core.start()

        if config.sections["server"]["auto_connect_startup"]:
            core.connect()

        # Check command line option and config option
        start_hidden = (self.start_hidden or (self.tray_icon.available
                                              and config.sections["ui"]["trayicon"]
                                              and config.sections["ui"]["startup_hidden"]))

        if not start_hidden:
            self.window.show()

        # Process thread events 20 times per second
        # High priority to ensure there are no delays
        GLib.timeout_add(50, self.on_process_thread_events, priority=GLib.PRIORITY_HIGH_IDLE)

    def on_shutdown(self, *_args):
        self.tray_icon.unload(is_shutdown=True)

    def on_confirm_quit_request(self, *_args):
        core.confirm_quit()

    def on_quit_request(self, *_args):
        core.quit()
