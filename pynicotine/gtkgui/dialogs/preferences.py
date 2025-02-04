# COPYRIGHT (C) 2020-2024 Nicotine+ Contributors
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2016 Mutnick <muhing@yahoo.com>
# COPYRIGHT (C) 2008-2011 quinox <quinox@users.sf.net>
# COPYRIGHT (C) 2008 gallows <g4ll0ws@gmail.com>
# COPYRIGHT (C) 2006-2009 daelstorm <daelstorm@gmail.com>
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
import time

from operator import itemgetter

from gi.repository import Gdk
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Pango

import pynicotine
from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.application import GTK_MINOR_VERSION
from pynicotine.gtkgui.dialogs.pluginsettings import PluginSettings
from pynicotine.gtkgui.popovers.searchfilterhelp import SearchFilterHelp
from pynicotine.gtkgui.widgets import ui
from pynicotine.gtkgui.widgets.accelerator import Accelerator
from pynicotine.gtkgui.widgets.combobox import ComboBox
from pynicotine.gtkgui.widgets.dialogs import Dialog
from pynicotine.gtkgui.widgets.dialogs import EntryDialog
from pynicotine.gtkgui.widgets.dialogs import MessageDialog
from pynicotine.gtkgui.widgets.filechooser import FileChooserButton
from pynicotine.gtkgui.widgets.filechooser import FileChooserSave
from pynicotine.gtkgui.widgets.filechooser import FolderChooser
from pynicotine.gtkgui.widgets.textentry import SpellChecker
from pynicotine.gtkgui.widgets.textview import TextView
from pynicotine.gtkgui.widgets.theme import USER_STATUS_ICON_NAMES
from pynicotine.gtkgui.widgets.theme import add_css_class
from pynicotine.gtkgui.widgets.theme import load_custom_icons
from pynicotine.gtkgui.widgets.theme import set_dark_mode
from pynicotine.gtkgui.widgets.theme import update_custom_css
from pynicotine.gtkgui.widgets.treeview import TreeView
from pynicotine.i18n import LANGUAGES
from pynicotine.logfacility import log
from pynicotine.shares import PermissionLevel
from pynicotine.slskmessages import UserStatus
from pynicotine.slskproto import NetworkInterfaces
from pynicotine.utils import encode_path
from pynicotine.utils import open_folder_path
from pynicotine.utils import open_uri
from pynicotine.utils import unescape


class NetworkPage:

    def __init__(self, application):

        (
            self.auto_away_spinner,
            self.auto_connect_startup_toggle,
            self.auto_reply_message_entry,
            self.check_port_status_label,
            self.container,
            self.current_port_label,
            self.listen_port_spinner,
            self.network_interface_label,
            self.soulseek_server_entry,
            self.upnp_toggle,
            self.username_entry
        ) = self.widgets = ui.load(scope=self, path="settings/network.ui")

        self.application = application

        self.username_entry.set_max_length(core.users.USERNAME_MAX_LENGTH)
        self.check_port_status_label.connect("activate-link", self.on_activate_link)

        self.network_interface_combobox = ComboBox(
            container=self.network_interface_label.get_parent(), has_entry=True,
            label=self.network_interface_label
        )

        self.options = {
            "server": {
                "server": None,  # Special case in set_settings
                "login": self.username_entry,
                "portrange": None,  # Special case in set_settings
                "autoaway": self.auto_away_spinner,
                "autoreply": self.auto_reply_message_entry,
                "interface": self.network_interface_combobox,
                "upnp": self.upnp_toggle,
                "auto_connect_startup": self.auto_connect_startup_toggle
            }
        }

        for event_name, callback in (
            ("server-disconnect", self.update_port_label),
            ("server-login", self.update_port_label)
        ):
            events.connect(event_name, callback)

    def destroy(self):
        self.network_interface_combobox.destroy()
        self.__dict__.clear()

    def update_port_label(self, *_args):

        unknown_label = _("Unknown")

        if core.users.public_port:
            url = pynicotine.__port_checker_url__ % str(core.users.public_port)
            port_status_text = _("Check Port Status")

            self.current_port_label.set_markup(_("<b>%(ip)s</b>, port %(port)s") % {
                "ip": core.users.public_ip_address or unknown_label,
                "port": core.users.public_port or unknown_label
            })
            self.check_port_status_label.set_markup(f"<a href='{url}' title='{url}'>{port_status_text}</a>")
            self.check_port_status_label.set_visible(not self.application.isolated_mode)
        else:
            self.current_port_label.set_text(unknown_label)
            self.check_port_status_label.set_visible(False)

    def set_settings(self):

        # Network interfaces
        self.network_interface_combobox.freeze()
        self.network_interface_combobox.clear()
        self.network_interface_combobox.append("")

        for interface in NetworkInterfaces.get_interface_addresses():
            self.network_interface_combobox.append(interface)

        self.network_interface_combobox.unfreeze()

        self.application.preferences.set_widgets_data(self.options)

        # Listening port status
        self.update_port_label()

        # Special options
        server_hostname, server_port = config.sections["server"]["server"]
        self.soulseek_server_entry.set_text(f"{server_hostname}:{server_port}")

        listen_port, _unused_port = config.sections["server"]["portrange"]
        self.listen_port_spinner.set_value(listen_port)

    def get_settings(self):

        try:
            server_address, server_port = self.soulseek_server_entry.get_text().split(":")
            server_addr = (server_address.strip(), int(server_port.strip()))

        except ValueError:
            server_addr = config.defaults["server"]["server"]

        listen_port = self.listen_port_spinner.get_value_as_int()

        return {
            "server": {
                "server": server_addr,
                "login": self.username_entry.get_text(),
                "portrange": (listen_port, listen_port),
                "autoaway": self.auto_away_spinner.get_value_as_int(),
                "autoreply": self.auto_reply_message_entry.get_text(),
                "interface": self.network_interface_combobox.get_text(),
                "upnp": self.upnp_toggle.get_active(),
                "auto_connect_startup": self.auto_connect_startup_toggle.get_active()
            }
        }

    def on_activate_link(self, _label, url):
        open_uri(url)
        return True

    def on_change_password_response(self, dialog, _response_id, user_status):

        password = dialog.get_entry_value()

        if user_status != core.users.login_status:
            MessageDialog(
                parent=self.application.preferences,
                title=_("Password Change Rejected"),
                message=("Since your login status changed, your password has not been changed. Please try again.")
            ).present()
            return

        if not password:
            self.on_change_password()
            return

        if core.users.login_status == UserStatus.OFFLINE:
            config.sections["server"]["passw"] = password
            config.write_configuration()
            return

        core.users.request_change_password(password)

    def on_change_password(self, *_args):

        if core.users.login_status != UserStatus.OFFLINE:
            message = _("Enter a new password for your Soulseek account:")
        else:
            message = (_("You are currently logged out of the Soulseek network. If you want to change "
                         "the password of an existing Soulseek account, you need to be logged into that account.")
                       + "\n\n"
                       + _("Enter password to use when logging in:"))

        EntryDialog(
            parent=self.application.preferences,
            title=_("Change Password"),
            message=message,
            visibility=False,
            action_button_label=_("_Change"),
            callback=self.on_change_password_response,
            callback_data=core.users.login_status
        ).present()

    def on_default_server(self, *_args):
        server_address, server_port = config.defaults["server"]["server"]
        self.soulseek_server_entry.set_text(f"{server_address}:{server_port}")


class DownloadsPage:

    def __init__(self, application):

        (
            self.accept_sent_files_toggle,
            self.alt_speed_spinner,
            self.autoclear_downloads_toggle,
            self.container,
            self.download_double_click_label,
            self.download_folder_default_button,
            self.download_folder_label,
            self.enable_filters_toggle,
            self.enable_username_subfolders_toggle,
            self.file_finished_command_entry,
            self.filter_list_container,
            self.filter_status_label,
            self.folder_finished_command_entry,
            self.incomplete_folder_default_button,
            self.incomplete_folder_label,
            self.received_folder_default_button,
            self.received_folder_label,
            self.sent_files_permission_container,
            self.speed_spinner,
            self.use_alt_speed_limit_radio,
            self.use_speed_limit_radio,
            self.use_unlimited_speed_radio
        ) = self.widgets = ui.load(scope=self, path="settings/downloads.ui")

        self.application = application

        self.sent_files_permission_combobox = ComboBox(
            container=self.sent_files_permission_container,
            items=(
                (_("No one"), 0),
                (_("Everyone"), 1),
                (_("Buddies"), 2),
                (_("Trusted buddies"), 3)
            )
        )

        items = [
            (_("Nothing"), 0)
        ]
        if not self.application.isolated_mode:
            items += [
                (_("Open File"), 1),
                (_("Open in File Manager"), 2)
            ]
        items += [
            (_("Search"), 3),
            (_("Abort"), 4),
            (_("Remove"), 5),
            (_("Retry"), 6),
            (_("Browse Folder"), 7)
        ]
        self.download_double_click_combobox = ComboBox(
            container=self.download_double_click_label.get_parent(), label=self.download_double_click_label,
            items=items
        )

        self.download_folder_button = FileChooserButton(
            self.download_folder_label.get_parent(), window=application.preferences,
            label=self.download_folder_label, end_button=self.download_folder_default_button, chooser_type="folder",
            show_open_external_button=not self.application.isolated_mode
        )
        self.incomplete_folder_button = FileChooserButton(
            self.incomplete_folder_label.get_parent(), window=application.preferences,
            label=self.incomplete_folder_label, end_button=self.incomplete_folder_default_button, chooser_type="folder",
            show_open_external_button=not self.application.isolated_mode
        )
        self.received_folder_button = FileChooserButton(
            self.received_folder_label.get_parent(), window=application.preferences,
            label=self.received_folder_label, end_button=self.received_folder_default_button, chooser_type="folder",
            show_open_external_button=not self.application.isolated_mode
        )

        self.filter_syntax_description = _("<b>Syntax</b>: Case-insensitive. If enabled, Python regular expressions "
                                           "can be used, otherwise only wildcard * matches "
                                           "are supported.").replace("<b>", "").replace("</b>", "")
        self.filter_list_view = TreeView(
            application.window, parent=self.filter_list_container, multi_select=True,
            activate_row_callback=self.on_edit_filter,
            delete_accelerator_callback=self.on_remove_filter,
            columns={
                "filter": {
                    "column_type": "text",
                    "title": _("Filter"),
                    "width": 150,
                    "expand_column": True,
                    "default_sort_type": "ascending"
                },
                "regex": {
                    "column_type": "toggle",
                    "title": _("Regex"),
                    "width": 0,
                    "toggle_callback": self.on_toggle_regex
                }
            }
        )

        self.options = {
            "transfers": {
                "autoclear_downloads": self.autoclear_downloads_toggle,
                "remotedownloads": self.accept_sent_files_toggle,
                "uploadallowed": self.sent_files_permission_combobox,
                "incompletedir": self.incomplete_folder_button,
                "downloaddir": self.download_folder_button,
                "uploaddir": self.received_folder_button,
                "enablefilters": self.enable_filters_toggle,
                "downloadlimit": self.speed_spinner,
                "downloadlimitalt": self.alt_speed_spinner,
                "usernamesubfolders": self.enable_username_subfolders_toggle,
                "afterfinish": self.file_finished_command_entry,
                "afterfolder": self.folder_finished_command_entry,
                "download_doubleclick": self.download_double_click_combobox
            }
        }

    def destroy(self):

        self.download_folder_button.destroy()
        self.incomplete_folder_button.destroy()
        self.received_folder_button.destroy()
        self.filter_list_view.destroy()

        self.__dict__.clear()

    def set_settings(self):

        self.filter_list_view.clear()
        self.application.preferences.set_widgets_data(self.options)

        use_speed_limit = config.sections["transfers"]["use_download_speed_limit"]

        if use_speed_limit == "primary":
            self.use_speed_limit_radio.set_active(True)

        elif use_speed_limit == "alternative":
            self.use_alt_speed_limit_radio.set_active(True)

        else:
            self.use_unlimited_speed_radio.set_active(True)

        self.filter_list_view.freeze()

        for item in config.sections["transfers"]["downloadfilters"]:
            if not isinstance(item, list) or len(item) < 2:
                continue

            dfilter, escaped = item
            enable_regex = not escaped

            self.filter_list_view.add_row([dfilter, enable_regex], select_row=False)

        self.filter_list_view.unfreeze()

    def get_settings(self):

        if self.use_speed_limit_radio.get_active():
            use_speed_limit = "primary"

        elif self.use_alt_speed_limit_radio.get_active():
            use_speed_limit = "alternative"

        else:
            use_speed_limit = "unlimited"

        download_filters = []

        for dfilter, iterator in self.filter_list_view.iterators.items():
            enable_regex = self.filter_list_view.get_row_value(iterator, "regex")
            download_filters.append([dfilter, not enable_regex])

        return {
            "transfers": {
                "autoclear_downloads": self.autoclear_downloads_toggle.get_active(),
                "remotedownloads": self.accept_sent_files_toggle.get_active(),
                "uploadallowed": self.sent_files_permission_combobox.get_selected_id(),
                "incompletedir": self.incomplete_folder_button.get_path(),
                "downloaddir": self.download_folder_button.get_path(),
                "uploaddir": self.received_folder_button.get_path(),
                "downloadfilters": download_filters,
                "enablefilters": self.enable_filters_toggle.get_active(),
                "use_download_speed_limit": use_speed_limit,
                "downloadlimit": self.speed_spinner.get_value_as_int(),
                "downloadlimitalt": self.alt_speed_spinner.get_value_as_int(),
                "usernamesubfolders": self.enable_username_subfolders_toggle.get_active(),
                "afterfinish": self.file_finished_command_entry.get_text().strip(),
                "afterfolder": self.folder_finished_command_entry.get_text().strip(),
                "download_doubleclick": self.download_double_click_combobox.get_selected_id()
            }
        }

    def on_default_download_folder(self, *_args):
        self.download_folder_button.set_path(config.defaults["transfers"]["downloaddir"])

    def on_default_incomplete_folder(self, *_args):
        self.incomplete_folder_button.set_path(config.defaults["transfers"]["incompletedir"])

    def on_default_received_folder(self, *_args):
        self.received_folder_button.set_path(config.defaults["transfers"]["uploaddir"])

    def on_toggle_regex(self, list_view, iterator):

        value = list_view.get_row_value(iterator, "regex")
        list_view.set_row_value(iterator, "regex", not value)

        self.on_verify_filter()

    def on_add_filter_response(self, dialog, _response_id, _data):

        dfilter = dialog.get_entry_value()
        enable_regex = dialog.get_option_value()

        iterator = self.filter_list_view.iterators.get(dfilter)

        if iterator is not None:
            self.filter_list_view.set_row_value(iterator, "regex", enable_regex)
        else:
            self.filter_list_view.add_row([dfilter, enable_regex])

        self.on_verify_filter()

    def on_add_filter(self, *_args):

        EntryDialog(
            parent=self.application.preferences,
            title=_("Add Download Filter"),
            message=self.filter_syntax_description + "\n\n" + _("Enter a new download filter:"),
            action_button_label=_("_Add"),
            callback=self.on_add_filter_response,
            option_value=False,
            option_label=_("Enable regular expressions"),
            droplist=self.filter_list_view.iterators
        ).present()

    def on_edit_filter_response(self, dialog, _response_id, iterator):

        new_dfilter = dialog.get_entry_value()
        enable_regex = dialog.get_option_value()

        dfilter = self.filter_list_view.get_row_value(iterator, "filter")
        orig_iterator = self.filter_list_view.iterators[dfilter]

        self.filter_list_view.remove_row(orig_iterator)
        self.filter_list_view.add_row([new_dfilter, enable_regex])

        self.on_verify_filter()

    def on_edit_filter(self, *_args):

        for iterator in self.filter_list_view.get_selected_rows():
            dfilter = self.filter_list_view.get_row_value(iterator, "filter")
            enable_regex = self.filter_list_view.get_row_value(iterator, "regex")

            EntryDialog(
                parent=self.application.preferences,
                title=_("Edit Download Filter"),
                message=self.filter_syntax_description + "\n\n" + _("Modify the following download filter:"),
                action_button_label=_("_Edit"),
                callback=self.on_edit_filter_response,
                callback_data=iterator,
                default=dfilter,
                option_value=enable_regex,
                option_label=_("Enable regular expressions")
            ).present()
            return

    def on_remove_filter(self, *_args):

        for iterator in reversed(list(self.filter_list_view.get_selected_rows())):
            dfilter = self.filter_list_view.get_row_value(iterator, "filter")
            orig_iterator = self.filter_list_view.iterators[dfilter]

            self.filter_list_view.remove_row(orig_iterator)

        self.on_verify_filter()

    def on_default_filters(self, *_args):

        self.filter_list_view.clear()
        self.filter_list_view.freeze()

        for download_filter, escaped in config.defaults["transfers"]["downloadfilters"]:
            enable_regex = not escaped
            self.filter_list_view.add_row([download_filter, enable_regex], select_row=False)

        self.filter_list_view.unfreeze()
        self.on_verify_filter()

    def on_verify_filter(self, *_args):

        failed = {}
        outfilter = "(\\\\("

        for dfilter, iterator in self.filter_list_view.iterators.items():
            dfilter = self.filter_list_view.get_row_value(iterator, "filter")
            enable_regex = self.filter_list_view.get_row_value(iterator, "regex")

            if not enable_regex:
                dfilter = re.escape(dfilter)
                dfilter = dfilter.replace("\\*", ".*")

            try:
                re.compile("(" + dfilter + ")")
                outfilter += dfilter

                if dfilter != list(self.filter_list_view.iterators)[-1]:
                    outfilter += "|"

            except re.error as error:
                failed[dfilter] = error

        outfilter += ")$)"

        try:
            re.compile(outfilter)

        except re.error as error:
            failed[outfilter] = error

        if failed:
            errors = ""

            for dfilter, error in failed.items():
                errors += "Filter: %(filter)s Error: %(error)s " % {
                    "filter": dfilter,
                    "error": error
                }

            error = _("%(num)d Failed! %(error)s " % {
                "num": len(failed),
                "error": errors}
            )

            self.filter_status_label.set_text(error)
        else:
            self.filter_status_label.set_text(_("Filters Successful"))


class SharesPage:

    PERMISSION_LEVELS = {
        _("Public"): PermissionLevel.PUBLIC,
        _("Buddies"): PermissionLevel.BUDDY,
        _("Trusted buddies"): PermissionLevel.TRUSTED
    }

    def __init__(self, application):

        (
            self.container,
            self.rescan_on_startup_toggle,
            self.reveal_buddy_shares_toggle,
            self.reveal_trusted_shares_toggle,
            self.shares_list_container
        ) = self.widgets = ui.load(scope=self, path="settings/shares.ui")

        self.application = application

        self.last_parent_folder = None
        self.shared_folders = []
        self.buddy_shared_folders = []
        self.trusted_shared_folders = []

        self.shares_list_view = TreeView(
            application.window, parent=self.shares_list_container, multi_select=True,
            activate_row_callback=self.on_edit_shared_folder,
            delete_accelerator_callback=self.on_remove_shared_folder,
            columns={
                "virtual_name": {
                    "column_type": "text",
                    "title": _("Virtual Folder"),
                    "width": 65,
                    "expand_column": True,
                    "default_sort_type": "ascending"
                },
                "folder": {
                    "column_type": "text",
                    "title": _("Folder"),
                    "width": 150,
                    "expand_column": True
                },
                "accessible_to": {
                    "column_type": "text",
                    "title": _("Accessible To"),
                    "width": 0
                }
            }
        )

        self.options = {
            "transfers": {
                "rescanonstartup": self.rescan_on_startup_toggle,
                "reveal_buddy_shares": self.reveal_buddy_shares_toggle,
                "reveal_trusted_shares": self.reveal_trusted_shares_toggle
            }
        }

    def destroy(self):
        self.shares_list_view.destroy()
        self.__dict__.clear()

    def set_settings(self):

        self.shares_list_view.clear()
        self.shares_list_view.freeze()

        self.application.preferences.set_widgets_data(self.options)

        self.shared_folders = config.sections["transfers"]["shared"][:]
        self.buddy_shared_folders = config.sections["transfers"]["buddyshared"][:]
        self.trusted_shared_folders = config.sections["transfers"]["trustedshared"][:]

        for virtual_name, folder_path, *_unused in self.shared_folders:
            self.shares_list_view.add_row(
                [virtual_name, folder_path, _("Public")], select_row=False)

        for virtual_name, folder_path, *_unused in self.buddy_shared_folders:
            self.shares_list_view.add_row(
                [virtual_name, folder_path, _("Buddies")], select_row=False)

        for virtual_name, folder_path, *_unused in self.trusted_shared_folders:
            self.shares_list_view.add_row(
                [virtual_name, folder_path, _("Trusted")], select_row=False)

        self.shares_list_view.unfreeze()

    def get_settings(self):

        return {
            "transfers": {
                "shared": self.shared_folders[:],
                "buddyshared": self.buddy_shared_folders[:],
                "trustedshared": self.trusted_shared_folders[:],
                "rescanonstartup": self.rescan_on_startup_toggle.get_active(),
                "reveal_buddy_shares": self.reveal_buddy_shares_toggle.get_active(),
                "reveal_trusted_shares": self.reveal_trusted_shares_toggle.get_active()
            }
        }

    def on_add_shared_folder_selected(self, selected, _data):

        for folder_path in selected:
            virtual_name = core.shares.add_share(
                folder_path, share_groups=(self.shared_folders, self.buddy_shared_folders, self.trusted_shared_folders)
            )

            if not virtual_name:
                continue

            self.last_parent_folder = os.path.dirname(folder_path)
            self.shares_list_view.add_row([virtual_name, folder_path, _("Public")])

    def on_add_shared_folder(self, *_args):

        # By default, show parent folder of last added share as initial folder
        initial_folder = self.last_parent_folder

        # If present, show parent folder of selected share as initial folder
        for iterator in self.shares_list_view.get_selected_rows():
            initial_folder = os.path.dirname(self.shares_list_view.get_row_value(iterator, "folder"))
            break

        if initial_folder and not os.path.exists(encode_path(initial_folder)):
            initial_folder = None

        FolderChooser(
            parent=self.application.preferences,
            callback=self.on_add_shared_folder_selected,
            title=_("Add a Shared Folder"),
            initial_folder=initial_folder,
            select_multiple=True
        ).present()

    def on_edit_shared_folder_response(self, dialog, _response_id, iterator):

        new_virtual_name = dialog.get_entry_value()
        new_accessible_to = dialog.get_second_entry_value()
        new_accessible_to_short = new_accessible_to.replace(_("Trusted buddies"), _("Trusted"))

        virtual_name = self.shares_list_view.get_row_value(iterator, "virtual_name")
        accessible_to = self.shares_list_view.get_row_value(iterator, "accessible_to")

        if new_virtual_name == virtual_name and new_accessible_to_short == accessible_to:
            return

        folder_path = self.shares_list_view.get_row_value(iterator, "folder")
        permission_level = self.PERMISSION_LEVELS.get(new_accessible_to)
        orig_iterator = self.shares_list_view.iterators[virtual_name]

        self.shares_list_view.remove_row(orig_iterator)
        core.shares.remove_share(
            virtual_name, share_groups=(self.shared_folders, self.buddy_shared_folders, self.trusted_shared_folders)
        )
        new_virtual_name = core.shares.add_share(
            folder_path, permission_level=permission_level, virtual_name=new_virtual_name,
            share_groups=(self.shared_folders, self.buddy_shared_folders, self.trusted_shared_folders),
            validate_path=False
        )

        self.shares_list_view.add_row([new_virtual_name, folder_path, new_accessible_to_short])

    def on_edit_shared_folder(self, *_args):

        for iterator in self.shares_list_view.get_selected_rows():
            virtual_name = self.shares_list_view.get_row_value(iterator, "virtual_name")
            folder_path = self.shares_list_view.get_row_value(iterator, "folder")
            default_item = self.shares_list_view.get_row_value(iterator, "accessible_to")

            EntryDialog(
                parent=self.application.preferences,
                title=_("Edit Shared Folder"),
                message=_("Enter new virtual name for '%(dir)s':") % {"dir": folder_path},
                default=virtual_name,
                second_default=default_item.replace(_("Trusted"), _("Trusted buddies")),
                second_droplist=list(self.PERMISSION_LEVELS),
                use_second_entry=True,
                second_entry_editable=False,
                action_button_label=_("_Edit"),
                callback=self.on_edit_shared_folder_response,
                callback_data=iterator
            ).present()
            return

    def on_remove_shared_folder(self, *_args):

        for iterator in reversed(list(self.shares_list_view.get_selected_rows())):
            virtual_name = self.shares_list_view.get_row_value(iterator, "virtual_name")
            orig_iterator = self.shares_list_view.iterators[virtual_name]

            core.shares.remove_share(
                virtual_name, share_groups=(self.shared_folders, self.buddy_shared_folders, self.trusted_shared_folders)
            )
            self.shares_list_view.remove_row(orig_iterator)


class UploadsPage:

    def __init__(self, application):

        (
            self.alt_speed_spinner,
            self.autoclear_uploads_toggle,
            self.container,
            self.limit_total_transfers_radio,
            self.max_queued_files_spinner,
            self.max_queued_size_spinner,
            self.no_buddy_limits_toggle,
            self.prioritize_buddies_toggle,
            self.speed_spinner,
            self.upload_bandwidth_spinner,
            self.upload_double_click_label,
            self.upload_queue_type_label,
            self.upload_slots_spinner,
            self.use_alt_speed_limit_radio,
            self.use_speed_limit_radio,
            self.use_unlimited_speed_radio,
            self.use_upload_slots_bandwidth_radio,
            self.use_upload_slots_fixed_radio
        ) = self.widgets = ui.load(scope=self, path="settings/uploads.ui")

        self.application = application

        items = [
            (_("Nothing"), 0)
        ]
        if not self.application.isolated_mode:
            items += [
                (_("Open File"), 1),
                (_("Open in File Manager"), 2)
            ]
        items += [
            (_("Search"), 3),
            (_("Abort"), 4),
            (_("Remove"), 5),
            (_("Retry"), 6),
            (_("Browse Folder"), 7)
        ]
        self.upload_double_click_combobox = ComboBox(
            container=self.upload_double_click_label.get_parent(), label=self.upload_double_click_label,
            items=items
        )

        self.upload_queue_type_combobox = ComboBox(
            container=self.upload_queue_type_label.get_parent(), label=self.upload_queue_type_label,
            items=(
                (_("Round Robin"), 0),
                (_("First In, First Out"), 1)
            )
        )

        self.options = {
            "transfers": {
                "autoclear_uploads": self.autoclear_uploads_toggle,
                "uploadbandwidth": self.upload_bandwidth_spinner,
                "useupslots": self.use_upload_slots_fixed_radio,
                "uploadslots": self.upload_slots_spinner,
                "uploadlimit": self.speed_spinner,
                "uploadlimitalt": self.alt_speed_spinner,
                "fifoqueue": self.upload_queue_type_combobox,
                "limitby": self.limit_total_transfers_radio,
                "queuelimit": self.max_queued_size_spinner,
                "filelimit": self.max_queued_files_spinner,
                "friendsnolimits": self.no_buddy_limits_toggle,
                "preferfriends": self.prioritize_buddies_toggle,
                "upload_doubleclick": self.upload_double_click_combobox
            }
        }

    def destroy(self):

        self.upload_double_click_combobox.destroy()
        self.upload_queue_type_combobox.destroy()

        self.__dict__.clear()

    def set_settings(self):

        self.application.preferences.set_widgets_data(self.options)

        use_speed_limit = config.sections["transfers"]["use_upload_speed_limit"]

        if use_speed_limit == "primary":
            self.use_speed_limit_radio.set_active(True)

        elif use_speed_limit == "alternative":
            self.use_alt_speed_limit_radio.set_active(True)

        else:
            self.use_unlimited_speed_radio.set_active(True)

    def get_settings(self):

        if self.use_speed_limit_radio.get_active():
            use_speed_limit = "primary"

        elif self.use_alt_speed_limit_radio.get_active():
            use_speed_limit = "alternative"

        else:
            use_speed_limit = "unlimited"

        return {
            "transfers": {
                "autoclear_uploads": self.autoclear_uploads_toggle.get_active(),
                "uploadbandwidth": self.upload_bandwidth_spinner.get_value_as_int(),
                "useupslots": self.use_upload_slots_fixed_radio.get_active(),
                "uploadslots": self.upload_slots_spinner.get_value_as_int(),
                "use_upload_speed_limit": use_speed_limit,
                "uploadlimit": self.speed_spinner.get_value_as_int(),
                "uploadlimitalt": self.alt_speed_spinner.get_value_as_int(),
                "fifoqueue": bool(self.upload_queue_type_combobox.get_selected_id()),
                "limitby": self.limit_total_transfers_radio.get_active(),
                "queuelimit": self.max_queued_size_spinner.get_value_as_int(),
                "filelimit": self.max_queued_files_spinner.get_value_as_int(),
                "friendsnolimits": self.no_buddy_limits_toggle.get_active(),
                "preferfriends": self.prioritize_buddies_toggle.get_active(),
                "upload_doubleclick": self.upload_double_click_combobox.get_selected_id()
            }
        }


class UserProfilePage:

    def __init__(self, application):

        (
            self.container,
            self.description_view_container,
            self.reset_picture_button,
            self.select_picture_label
        ) = self.widgets = ui.load(scope=self, path="settings/userinfo.ui")

        self.application = application

        self.description_view = TextView(self.description_view_container, parse_urls=False)
        self.select_picture_button = FileChooserButton(
            self.select_picture_label.get_parent(), window=application.preferences, label=self.select_picture_label,
            end_button=self.reset_picture_button, chooser_type="image", is_flat=True,
            show_open_external_button=not self.application.isolated_mode
        )

        self.options = {
            "userinfo": {
                "descr": self.description_view,
                "pic": self.select_picture_button
            }
        }

    def destroy(self):

        self.description_view.destroy()
        self.select_picture_button.destroy()

        self.__dict__.clear()

    def set_settings(self):
        self.description_view.clear()
        self.application.preferences.set_widgets_data(self.options)

    def get_settings(self):

        return {
            "userinfo": {
                "descr": repr(self.description_view.get_text()),
                "pic": self.select_picture_button.get_path()
            }
        }

    def on_reset_picture(self, *_args):
        self.select_picture_button.clear()


class IgnoredUsersPage:

    def __init__(self, application):

        (
            self.container,
            self.ignored_ips_container,
            self.ignored_users_container
        ) = self.widgets = ui.load(scope=self, path="settings/ignore.ui")

        self.application = application
        self.added_users = set()
        self.added_ips = set()
        self.removed_users = set()
        self.removed_ips = set()

        self.ignored_users = []
        self.ignored_users_list_view = TreeView(
            application.window, parent=self.ignored_users_container, multi_select=True,
            delete_accelerator_callback=self.on_remove_ignored_user,
            columns={
                "username": {
                    "column_type": "text",
                    "title": _("Username"),
                    "default_sort_type": "ascending"
                }
            }
        )

        self.ignored_ips = {}
        self.ignored_ips_list_view = TreeView(
            application.window, parent=self.ignored_ips_container, multi_select=True,
            delete_accelerator_callback=self.on_remove_ignored_ip,
            columns={
                "ip_address": {
                    "column_type": "text",
                    "title": _("IP Address"),
                    "width": 50,
                    "expand_column": True
                },
                "user": {
                    "column_type": "text",
                    "title": _("User"),
                    "expand_column": True,
                    "default_sort_type": "ascending"
                }
            }
        )

        self.options = {
            "server": {
                "ignorelist": self.ignored_users_list_view,
                "ipignorelist": self.ignored_ips_list_view
            }
        }

    def destroy(self):

        self.ignored_users_list_view.destroy()
        self.ignored_ips_list_view.destroy()

        self.__dict__.clear()

    def set_settings(self):

        self.clear_changes()

        self.ignored_users_list_view.clear()
        self.ignored_ips_list_view.clear()
        self.ignored_users.clear()
        self.ignored_ips.clear()

        self.application.preferences.set_widgets_data(self.options)

        self.ignored_users = config.sections["server"]["ignorelist"][:]
        self.ignored_ips = config.sections["server"]["ipignorelist"].copy()

    def get_settings(self):
        return {}

    def clear_changes(self):

        self.added_users.clear()
        self.added_ips.clear()
        self.removed_users.clear()
        self.removed_ips.clear()

    def on_add_ignored_user_response(self, dialog, _response_id, _data):

        user = dialog.get_entry_value().strip()

        if user and user not in self.ignored_users:
            self.ignored_users.append(user)
            self.ignored_users_list_view.add_row([str(user)])

            self.added_users.add(user)
            self.removed_users.discard(user)

    def on_add_ignored_user(self, *_args):

        EntryDialog(
            parent=self.application.preferences,
            title=_("Ignore User"),
            message=_("Enter the name of the user you want to ignore:"),
            action_button_label=_("_Add"),
            callback=self.on_add_ignored_user_response
        ).present()

    def on_remove_ignored_user(self, *_args):

        for iterator in reversed(list(self.ignored_users_list_view.get_selected_rows())):
            user = self.ignored_users_list_view.get_row_value(iterator, "username")
            orig_iterator = self.ignored_users_list_view.iterators[user]

            self.ignored_users_list_view.remove_row(orig_iterator)
            self.ignored_users.remove(user)

            if user not in self.added_users:
                self.removed_users.add(user)

            self.added_users.discard(user)

    def on_add_ignored_ip_response(self, dialog, _response_id, _data):

        ip_address = dialog.get_entry_value().strip()

        if not core.network_filter.is_ip_address(ip_address):
            return

        if ip_address not in self.ignored_ips:
            user = core.network_filter.get_online_username(ip_address) or ""
            user_ip_pair = (user, ip_address)

            self.ignored_ips[ip_address] = user
            self.ignored_ips_list_view.add_row([ip_address, user])

            self.added_ips.add(user_ip_pair)
            self.removed_ips.discard(user_ip_pair)

    def on_add_ignored_ip(self, *_args):

        EntryDialog(
            parent=self.application.preferences,
            title=_("Ignore IP Address"),
            message=_("Enter an IP address you want to ignore:") + " " + _("* is a wildcard"),
            action_button_label=_("_Add"),
            callback=self.on_add_ignored_ip_response
        ).present()

    def on_remove_ignored_ip(self, *_args):

        for iterator in reversed(list(self.ignored_ips_list_view.get_selected_rows())):
            ip_address = self.ignored_ips_list_view.get_row_value(iterator, "ip_address")
            user = self.ignored_ips_list_view.get_row_value(iterator, "user")
            user_ip_pair = (user, ip_address)
            orig_iterator = self.ignored_ips_list_view.iterators[ip_address]

            self.ignored_ips_list_view.remove_row(orig_iterator)
            del self.ignored_ips[ip_address]

            if user_ip_pair not in self.added_ips:
                self.removed_ips.add(user_ip_pair)

            self.added_ips.discard(user_ip_pair)


class BannedUsersPage:

    def __init__(self, application):

        (
            self.ban_message_entry,
            self.ban_message_toggle,
            self.banned_ips_container,
            self.banned_users_container,
            self.container,
            self.geo_block_country_entry,
            self.geo_block_message_entry,
            self.geo_block_message_toggle,
            self.geo_block_toggle
        ) = self.widgets = ui.load(scope=self, path="settings/ban.ui")

        self.application = application
        self.added_users = set()
        self.added_ips = set()
        self.removed_users = set()
        self.removed_ips = set()

        self.banned_users = []
        self.banned_users_list_view = TreeView(
            application.window, parent=self.banned_users_container, multi_select=True,
            delete_accelerator_callback=self.on_remove_banned_user,
            columns={
                "username": {
                    "column_type": "text",
                    "title": _("Username"),
                    "default_sort_type": "ascending"
                }
            }
        )

        self.banned_ips = {}
        self.banned_ips_list_view = TreeView(
            application.window, parent=self.banned_ips_container, multi_select=True,
            delete_accelerator_callback=self.on_remove_banned_ip,
            columns={
                "ip_address": {
                    "column_type": "text",
                    "title": _("IP Address"),
                    "width": 50,
                    "expand_column": True
                },
                "user": {
                    "column_type": "text",
                    "title": _("User"),
                    "expand_column": True,
                    "default_sort_type": "ascending"
                }
            }
        )

        self.options = {
            "server": {
                "banlist": self.banned_users_list_view,
                "ipblocklist": self.banned_ips_list_view
            },
            "transfers": {
                "usecustomban": self.ban_message_toggle,
                "customban": self.ban_message_entry,
                "geoblock": self.geo_block_toggle,
                "geoblockcc": None,
                "usecustomgeoblock": self.geo_block_message_toggle,
                "customgeoblock": self.geo_block_message_entry
            }
        }

    def destroy(self):

        self.banned_users_list_view.destroy()
        self.banned_ips_list_view.destroy()

        self.__dict__.clear()

    def set_settings(self):

        self.clear_changes()

        self.banned_users_list_view.clear()
        self.banned_ips_list_view.clear()
        self.banned_users.clear()
        self.banned_ips.clear()

        self.application.preferences.set_widgets_data(self.options)

        self.banned_users = config.sections["server"]["banlist"][:]
        self.banned_ips = config.sections["server"]["ipblocklist"].copy()
        self.geo_block_country_entry.set_text(config.sections["transfers"]["geoblockcc"][0])

    def get_settings(self):

        return {
            "transfers": {
                "usecustomban": self.ban_message_toggle.get_active(),
                "customban": self.ban_message_entry.get_text(),
                "geoblock": self.geo_block_toggle.get_active(),
                "geoblockcc": [self.geo_block_country_entry.get_text().upper()],
                "usecustomgeoblock": self.geo_block_message_toggle.get_active(),
                "customgeoblock": self.geo_block_message_entry.get_text()
            }
        }

    def clear_changes(self):

        self.added_users.clear()
        self.added_ips.clear()
        self.removed_users.clear()
        self.removed_ips.clear()

    def on_add_banned_user_response(self, dialog, _response_id, _data):

        user = dialog.get_entry_value().strip()

        if user and user not in self.banned_users:
            self.banned_users.append(user)
            self.banned_users_list_view.add_row([user])

            self.added_users.add(user)
            self.removed_users.discard(user)

    def on_add_banned_user(self, *_args):

        EntryDialog(
            parent=self.application.preferences,
            title=_("Ban User"),
            message=_("Enter the name of the user you want to ban:"),
            action_button_label=_("_Add"),
            callback=self.on_add_banned_user_response
        ).present()

    def on_remove_banned_user(self, *_args):

        for iterator in reversed(list(self.banned_users_list_view.get_selected_rows())):
            user = self.banned_users_list_view.get_row_value(iterator, "username")
            orig_iterator = self.banned_users_list_view.iterators[user]

            self.banned_users_list_view.remove_row(orig_iterator)
            self.banned_users.remove(user)

            if user not in self.added_users:
                self.removed_users.add(user)

            self.added_users.discard(user)

    def on_add_banned_ip_response(self, dialog, _response_id, _data):

        ip_address = dialog.get_entry_value().strip()

        if not core.network_filter.is_ip_address(ip_address):
            return

        if ip_address not in self.banned_ips:
            user = core.network_filter.get_online_username(ip_address) or ""
            user_ip_pair = (user, ip_address)

            self.banned_ips[ip_address] = user
            self.banned_ips_list_view.add_row([ip_address, user])

            self.added_ips.add(user_ip_pair)
            self.removed_ips.discard(user_ip_pair)

    def on_add_banned_ip(self, *_args):

        EntryDialog(
            parent=self.application.preferences,
            title=_("Ban IP Address"),
            message=_("Enter an IP address you want to ban:") + " " + _("* is a wildcard"),
            action_button_label=_("_Add"),
            callback=self.on_add_banned_ip_response
        ).present()

    def on_remove_banned_ip(self, *_args):

        for iterator in reversed(list(self.banned_ips_list_view.get_selected_rows())):
            ip_address = self.banned_ips_list_view.get_row_value(iterator, "ip_address")
            user = self.banned_ips_list_view.get_row_value(iterator, "user")
            user_ip_pair = (user, ip_address)
            orig_iterator = self.banned_ips_list_view.iterators[ip_address]

            self.banned_ips_list_view.remove_row(orig_iterator)
            del self.banned_ips[ip_address]

            if user_ip_pair not in self.added_ips:
                self.removed_ips.add(user_ip_pair)

            self.added_ips.discard(user_ip_pair)


class ChatsPage:

    def __init__(self, application):

        (
            self.auto_replace_words_toggle,
            self.censor_list_container,
            self.censor_text_patterns_toggle,
            self.complete_buddy_names_toggle,
            self.complete_commands_toggle,
            self.complete_room_names_toggle,
            self.complete_room_usernames_toggle,
            self.container,
            self.enable_completion_dropdown_toggle,
            self.enable_ctcp_toggle,
            self.enable_spell_checker_toggle,
            self.enable_tab_completion_toggle,
            self.enable_tts_toggle,
            self.format_codes_label,
            self.min_chars_dropdown_spinner,
            self.private_room_toggle,
            self.recent_private_messages_spinner,
            self.recent_room_messages_spinner,
            self.reopen_private_chats_toggle,
            self.replacement_list_container,
            self.timestamp_private_chat_entry,
            self.timestamp_room_entry,
            self.tts_command_label,
            self.tts_container,
            self.tts_private_message_entry,
            self.tts_room_message_entry,
        ) = self.widgets = ui.load(scope=self, path="settings/chats.ui")

        self.application = application

        format_codes_url = "https://docs.python.org/3/library/datetime.html#format-codes"
        format_codes_label = _("Format codes")

        self.format_codes_label.set_markup(
            f"<a href='{format_codes_url}' title='{format_codes_url}'>{format_codes_label}</a>")
        self.format_codes_label.connect("activate-link", self.on_activate_link)

        self.tts_command_combobox = ComboBox(
            container=self.tts_command_label.get_parent(), label=self.tts_command_label, has_entry=True,
            items=(
                ("flite -t $", None),
                ("echo $ | festival --tts", None)
            )
        )

        self.censored_patterns = []
        self.censor_list_view = TreeView(
            application.window, parent=self.censor_list_container, multi_select=True,
            activate_row_callback=self.on_edit_censored,
            delete_accelerator_callback=self.on_remove_censored,
            columns={
                "pattern": {
                    "column_type": "text",
                    "title": _("Pattern"),
                    "default_sort_type": "ascending"
                }
            }
        )

        self.replacements = {}
        self.replacement_list_view = TreeView(
            application.window, parent=self.replacement_list_container, multi_select=True,
            activate_row_callback=self.on_edit_replacement,
            delete_accelerator_callback=self.on_remove_replacement,
            columns={
                "pattern": {
                    "column_type": "text",
                    "title": _("Pattern"),
                    "width": 100,
                    "expand_column": True,
                    "default_sort_type": "ascending"
                },
                "replacement": {
                    "column_type": "text",
                    "title": _("Replacement"),
                    "expand_column": True
                }
            }
        )

        self.options = {
            "server": {
                "ctcpmsgs": None,  # Special case in set_settings
                "private_chatrooms": self.private_room_toggle
            },
            "logging": {
                "readroomlines": self.recent_room_messages_spinner,
                "readprivatelines": self.recent_private_messages_spinner,
                "rooms_timestamp": self.timestamp_room_entry,
                "private_timestamp": self.timestamp_private_chat_entry
            },
            "privatechat": {
                "store": self.reopen_private_chats_toggle
            },
            "words": {
                "tab": self.enable_tab_completion_toggle,
                "dropdown": self.enable_completion_dropdown_toggle,
                "characters": self.min_chars_dropdown_spinner,
                "roomnames": self.complete_room_names_toggle,
                "buddies": self.complete_buddy_names_toggle,
                "roomusers": self.complete_room_usernames_toggle,
                "commands": self.complete_commands_toggle,
                "censored": self.censor_list_view,
                "censorwords": self.censor_text_patterns_toggle,
                "autoreplaced": self.replacement_list_view,
                "replacewords": self.auto_replace_words_toggle
            },
            "ui": {
                "spellcheck": self.enable_spell_checker_toggle,
                "speechenabled": self.enable_tts_toggle,
                "speechcommand": self.tts_command_combobox,
                "speechrooms": self.tts_room_message_entry,
                "speechprivate": self.tts_private_message_entry
            }
        }

    def destroy(self):

        self.tts_command_combobox.destroy()
        self.censor_list_view.destroy()
        self.replacement_list_view.destroy()

        self.__dict__.clear()

    def set_settings(self):

        self.censor_list_view.clear()
        self.replacement_list_view.clear()
        self.censored_patterns.clear()
        self.replacements.clear()

        self.application.preferences.set_widgets_data(self.options)

        self.enable_spell_checker_toggle.get_parent().set_visible(SpellChecker.is_available())
        self.enable_ctcp_toggle.set_active(not config.sections["server"]["ctcpmsgs"])
        self.format_codes_label.set_visible(not self.application.isolated_mode)
        self.tts_container.set_margin_top(24 if self.application.isolated_mode else 0)

        self.censored_patterns = config.sections["words"]["censored"][:]
        self.replacements = config.sections["words"]["autoreplaced"].copy()

    def get_settings(self):

        return {
            "server": {
                "ctcpmsgs": not self.enable_ctcp_toggle.get_active(),
                "private_chatrooms": self.private_room_toggle.get_active()
            },
            "logging": {
                "readroomlines": self.recent_room_messages_spinner.get_value_as_int(),
                "readprivatelines": self.recent_private_messages_spinner.get_value_as_int(),
                "private_timestamp": self.timestamp_private_chat_entry.get_text(),
                "rooms_timestamp": self.timestamp_room_entry.get_text()
            },
            "privatechat": {
                "store": self.reopen_private_chats_toggle.get_active()
            },
            "words": {
                "tab": self.enable_tab_completion_toggle.get_active(),
                "dropdown": self.enable_completion_dropdown_toggle.get_active(),
                "characters": self.min_chars_dropdown_spinner.get_value_as_int(),
                "roomnames": self.complete_room_names_toggle.get_active(),
                "buddies": self.complete_buddy_names_toggle.get_active(),
                "roomusers": self.complete_room_usernames_toggle.get_active(),
                "commands": self.complete_commands_toggle.get_active(),
                "censored": self.censored_patterns[:],
                "censorwords": self.censor_text_patterns_toggle.get_active(),
                "autoreplaced": self.replacements.copy(),
                "replacewords": self.auto_replace_words_toggle.get_active()
            },
            "ui": {
                "spellcheck": self.enable_spell_checker_toggle.get_active(),
                "speechenabled": self.enable_tts_toggle.get_active(),
                "speechcommand": self.tts_command_combobox.get_text().strip(),
                "speechrooms": self.tts_room_message_entry.get_text(),
                "speechprivate": self.tts_private_message_entry.get_text()
            }
        }

    def on_activate_link(self, _label, url):
        open_uri(url)
        return True

    def on_default_tts_private_message(self, *_args):
        self.tts_private_message_entry.set_text(config.defaults["ui"]["speechprivate"])

    def on_default_tts_room_message(self, *_args):
        self.tts_room_message_entry.set_text(config.defaults["ui"]["speechrooms"])

    def on_default_timestamp_room(self, *_args):
        self.timestamp_room_entry.set_text(config.defaults["logging"]["rooms_timestamp"])

    def on_default_timestamp_private_chat(self, *_args):
        self.timestamp_private_chat_entry.set_text(config.defaults["logging"]["private_timestamp"])

    def on_add_censored_response(self, dialog, _response_id, _data):

        pattern = dialog.get_entry_value()

        if pattern and pattern not in self.censored_patterns:
            self.censored_patterns.append(pattern)
            self.censor_list_view.add_row([pattern])

    def on_add_censored(self, *_args):

        EntryDialog(
            parent=self.application.preferences,
            title=_("Censor Pattern"),
            message=_("Enter a pattern you want to censor. Add spaces around the pattern if you don't "
                      "want to match strings inside words (may fail at the beginning and end of lines)."),
            action_button_label=_("_Add"),
            callback=self.on_add_censored_response
        ).present()

    def on_edit_censored_response(self, dialog, _response_id, iterator):

        pattern = dialog.get_entry_value()

        if not pattern:
            return

        old_pattern = self.censor_list_view.get_row_value(iterator, "pattern")
        orig_iterator = self.censor_list_view.iterators[old_pattern]

        self.censor_list_view.remove_row(orig_iterator)
        self.censored_patterns.remove(old_pattern)

        self.censor_list_view.add_row([pattern])
        self.censored_patterns.append(pattern)

    def on_edit_censored(self, *_args):

        for iterator in self.censor_list_view.get_selected_rows():
            pattern = self.censor_list_view.get_row_value(iterator, "pattern")

            EntryDialog(
                parent=self.application.preferences,
                title=_("Edit Censored Pattern"),
                message=_("Enter a pattern you want to censor. Add spaces around the pattern if you don't "
                          "want to match strings inside words (may fail at the beginning and end of lines)."),
                action_button_label=_("_Edit"),
                callback=self.on_edit_censored_response,
                callback_data=iterator,
                default=pattern
            ).present()
            return

    def on_remove_censored(self, *_args):

        for iterator in reversed(list(self.censor_list_view.get_selected_rows())):
            censor = self.censor_list_view.get_row_value(iterator, "pattern")
            orig_iterator = self.censor_list_view.iterators[censor]

            self.censor_list_view.remove_row(orig_iterator)
            self.censored_patterns.remove(censor)

    def on_add_replacement_response(self, dialog, _response_id, _data):

        pattern = dialog.get_entry_value()
        replacement = dialog.get_second_entry_value()

        if not pattern or not replacement:
            return

        self.replacements[pattern] = replacement
        self.replacement_list_view.add_row([pattern, replacement])

    def on_add_replacement(self, *_args):

        EntryDialog(
            parent=self.application.preferences,
            title=_("Add Replacement"),
            message=_("Enter a text pattern and what to replace it with:"),
            action_button_label=_("_Add"),
            callback=self.on_add_replacement_response,
            use_second_entry=True
        ).present()

    def on_edit_replacement_response(self, dialog, _response_id, iterator):

        pattern = dialog.get_entry_value()
        replacement = dialog.get_second_entry_value()

        if not pattern or not replacement:
            return

        old_pattern = self.replacement_list_view.get_row_value(iterator, "pattern")
        orig_iterator = self.replacement_list_view.iterators[old_pattern]

        self.replacement_list_view.remove_row(orig_iterator)
        del self.replacements[old_pattern]

        self.replacements[pattern] = replacement
        self.replacement_list_view.add_row([pattern, replacement])

    def on_edit_replacement(self, *_args):

        for iterator in self.replacement_list_view.get_selected_rows():
            pattern = self.replacement_list_view.get_row_value(iterator, "pattern")
            replacement = self.replacement_list_view.get_row_value(iterator, "replacement")

            EntryDialog(
                parent=self.application.preferences,
                title=_("Edit Replacement"),
                message=_("Enter a text pattern and what to replace it with:"),
                action_button_label=_("_Edit"),
                callback=self.on_edit_replacement_response,
                callback_data=iterator,
                use_second_entry=True,
                default=pattern,
                second_default=replacement
            ).present()
            return

    def on_remove_replacement(self, *_args):

        for iterator in reversed(list(self.replacement_list_view.get_selected_rows())):
            replacement = self.replacement_list_view.get_row_value(iterator, "pattern")
            orig_iterator = self.replacement_list_view.iterators[replacement]

            self.replacement_list_view.remove_row(orig_iterator)
            del self.replacements[replacement]


class UserInterfacePage:

    def __init__(self, application):

        (
            self.buddy_list_position_label,
            self.chat_colored_usernames_toggle,
            self.chat_username_appearance_label,
            self.close_action_label,
            self.color_chat_action_button,
            self.color_chat_action_entry,
            self.color_chat_command_button,
            self.color_chat_command_entry,
            self.color_chat_highlighted_button,
            self.color_chat_highlighted_entry,
            self.color_chat_local_button,
            self.color_chat_local_entry,
            self.color_chat_remote_button,
            self.color_chat_remote_entry,
            self.color_input_background_button,
            self.color_input_background_entry,
            self.color_input_text_button,
            self.color_input_text_entry,
            self.color_list_text_button,
            self.color_list_text_entry,
            self.color_status_away_button,
            self.color_status_away_entry,
            self.color_status_offline_button,
            self.color_status_offline_entry,
            self.color_status_online_button,
            self.color_status_online_entry,
            self.color_tab_button,
            self.color_tab_changed_button,
            self.color_tab_changed_entry,
            self.color_tab_entry,
            self.color_tab_highlighted_button,
            self.color_tab_highlighted_entry,
            self.color_url_button,
            self.color_url_entry,
            self.container,
            self.dark_mode_toggle,
            self.exact_file_sizes_toggle,
            self.font_browse_button,
            self.font_browse_clear_button,
            self.font_chat_button,
            self.font_chat_clear_button,
            self.font_global_button,
            self.font_global_clear_button,
            self.font_list_button,
            self.font_list_clear_button,
            self.font_search_button,
            self.font_search_clear_button,
            self.font_text_view_button,
            self.font_text_view_clear_button,
            self.font_transfers_button,
            self.font_transfers_clear_button,
            self.header_bar_toggle,
            self.icon_theme_clear_button,
            self.icon_theme_label,
            self.icon_view,
            self.language_label,
            self.minimize_tray_startup_toggle,
            self.notification_chatroom_mention_toggle,
            self.notification_chatroom_toggle,
            self.notification_download_file_toggle,
            self.notification_download_folder_toggle,
            self.notification_private_message_toggle,
            self.notification_sounds_toggle,
            self.notification_window_title_toggle,
            self.notification_wish_toggle,
            self.reverse_file_paths_toggle,
            self.tab_close_buttons_toggle,
            self.tab_position_browse_label,
            self.tab_position_chatrooms_label,
            self.tab_position_main_label,
            self.tab_position_private_chat_label,
            self.tab_position_search_label,
            self.tab_position_userinfo_label,
            self.tab_restore_startup_toggle,
            self.tab_visible_browse_toggle,
            self.tab_visible_chatrooms_toggle,
            self.tab_visible_downloads_toggle,
            self.tab_visible_interests_toggle,
            self.tab_visible_private_chat_toggle,
            self.tab_visible_search_toggle,
            self.tab_visible_uploads_toggle,
            self.tab_visible_userinfo_toggle,
            self.tab_visible_userlist_toggle,
            self.tray_icon_toggle,
            self.tray_options_container
        ) = self.widgets = ui.load(scope=self, path="settings/userinterface.ui")

        self.application = application
        self.editing_color = False

        languages = [(_("System default"), "")]
        languages += [
            (language_name, language_code) for language_code, language_name in sorted(LANGUAGES, key=itemgetter(1))
        ]

        self.language_combobox = ComboBox(
            container=self.language_label.get_parent(), label=self.language_label,
            items=languages
        )

        self.close_action_combobox = ComboBox(
            container=self.close_action_label.get_parent(), label=self.close_action_label,
            items=(
                (_("Quit Nicotine+"), 0),
                (_("Show confirmation dialog"), 1),
                (_("Run in the background"), 2)
            )
        )

        self.chat_username_appearance_combobox = ComboBox(
            container=self.chat_username_appearance_label.get_parent(),
            label=self.chat_username_appearance_label,
            items=(
                (_("bold"), "bold"),
                (_("italic"), "italic"),
                (_("underline"), "underline"),
                (_("normal"), "normal")
            )
        )

        self.buddy_list_position_combobox = ComboBox(
            container=self.buddy_list_position_label.get_parent(), label=self.buddy_list_position_label,
            item_selected_callback=self.on_select_buddy_list_position,
            items=(
                (_("Separate Buddies tab"), "tab"),
                (_("Sidebar in Chat Rooms tab"), "chatrooms"),
                (_("Always visible sidebar"), "always")
            )
        )

        position_items = (
            (_("Top"), "Top"),
            (_("Bottom"), "Bottom"),
            (_("Left"), "Left"),
            (_("Right"), "Right")
        )

        self.tab_position_main_combobox = ComboBox(
            container=self.tab_position_main_label.get_parent(), label=self.tab_position_main_label,
            items=position_items)

        self.tab_position_search_combobox = ComboBox(
            container=self.tab_position_search_label.get_parent(), label=self.tab_position_search_label,
            items=position_items)

        self.tab_position_browse_combobox = ComboBox(
            container=self.tab_position_browse_label.get_parent(), label=self.tab_position_browse_label,
            items=position_items)

        self.tab_position_private_chat_combobox = ComboBox(
            container=self.tab_position_private_chat_label.get_parent(), label=self.tab_position_private_chat_label,
            items=position_items)

        self.tab_position_userinfo_combobox = ComboBox(
            container=self.tab_position_userinfo_label.get_parent(), label=self.tab_position_userinfo_label,
            items=position_items)

        self.tab_position_chatrooms_combobox = ComboBox(
            container=self.tab_position_chatrooms_label.get_parent(), label=self.tab_position_chatrooms_label,
            items=position_items)

        self.color_buttons = {
            "chatlocal": self.color_chat_local_button,
            "chatremote": self.color_chat_remote_button,
            "chatcommand": self.color_chat_command_button,
            "chatme": self.color_chat_action_button,
            "chathilite": self.color_chat_highlighted_button,
            "textbg": self.color_input_background_button,
            "inputcolor": self.color_input_text_button,
            "search": self.color_list_text_button,
            "useraway": self.color_status_away_button,
            "useronline": self.color_status_online_button,
            "useroffline": self.color_status_offline_button,
            "urlcolor": self.color_url_button,
            "tab_default": self.color_tab_button,
            "tab_hilite": self.color_tab_highlighted_button,
            "tab_changed": self.color_tab_changed_button
        }

        self.color_entries = {
            "chatlocal": self.color_chat_local_entry,
            "chatremote": self.color_chat_remote_entry,
            "chatcommand": self.color_chat_command_entry,
            "chatme": self.color_chat_action_entry,
            "chathilite": self.color_chat_highlighted_entry,
            "textbg": self.color_input_background_entry,
            "inputcolor": self.color_input_text_entry,
            "search": self.color_list_text_entry,
            "useraway": self.color_status_away_entry,
            "useronline": self.color_status_online_entry,
            "useroffline": self.color_status_offline_entry,
            "urlcolor": self.color_url_entry,
            "tab_default": self.color_tab_entry,
            "tab_hilite": self.color_tab_highlighted_entry,
            "tab_changed": self.color_tab_changed_entry
        }

        self.font_buttons = {
            "globalfont": self.font_global_button,
            "listfont": self.font_list_button,
            "textviewfont": self.font_text_view_button,
            "chatfont": self.font_chat_button,
            "searchfont": self.font_search_button,
            "transfersfont": self.font_transfers_button,
            "browserfont": self.font_browse_button
        }

        self.font_clear_buttons = {
            "globalfont": self.font_global_clear_button,
            "listfont": self.font_list_clear_button,
            "textviewfont": self.font_text_view_clear_button,
            "chatfont": self.font_chat_clear_button,
            "searchfont": self.font_search_clear_button,
            "transfersfont": self.font_transfers_clear_button,
            "browserfont": self.font_browse_clear_button
        }

        self.tab_position_comboboxes = {
            "tabmain": self.tab_position_main_combobox,
            "tabrooms": self.tab_position_chatrooms_combobox,
            "tabprivate": self.tab_position_private_chat_combobox,
            "tabsearch": self.tab_position_search_combobox,
            "tabinfo": self.tab_position_userinfo_combobox,
            "tabbrowse": self.tab_position_browse_combobox
        }

        self.tab_visible_toggles = {
            "search": self.tab_visible_search_toggle,
            "downloads": self.tab_visible_downloads_toggle,
            "uploads": self.tab_visible_uploads_toggle,
            "userbrowse": self.tab_visible_browse_toggle,
            "userinfo": self.tab_visible_userinfo_toggle,
            "private": self.tab_visible_private_chat_toggle,
            "userlist": self.tab_visible_userlist_toggle,
            "chatrooms": self.tab_visible_chatrooms_toggle,
            "interests": self.tab_visible_interests_toggle
        }

        rgba = Gdk.RGBA()
        rgba.red = rgba.green = rgba.blue = rgba.alpha = 0

        for color_id, button in self.color_buttons.items():
            button.set_rgba(rgba)
            button.connect("notify::rgba", self.on_color_button_changed, color_id)

        for color_id, entry in self.color_entries.items():
            entry.connect("icon-press", self.on_default_color, color_id)
            entry.connect("changed", self.on_color_entry_changed, color_id)

        for font_id, button in self.font_clear_buttons.items():
            button.connect("clicked", self.on_clear_font, font_id)

        if (GTK_API_VERSION, GTK_MINOR_VERSION) >= (4, 10):
            color_dialog = Gtk.ColorDialog()
            font_dialog = Gtk.FontDialog()

            for button in self.color_buttons.values():
                button.set_dialog(color_dialog)

            for button in self.font_buttons.values():
                button.set_dialog(font_dialog)
                button.set_level(Gtk.FontLevel.FONT)
        else:
            for button in self.color_buttons.values():
                button.set_use_alpha(True)

        icon_list = [
            (USER_STATUS_ICON_NAMES[UserStatus.ONLINE], _("Online"), 16, ("colored-icon", "user-status")),
            (USER_STATUS_ICON_NAMES[UserStatus.AWAY], _("Away"), 16, ("colored-icon", "user-status")),
            (USER_STATUS_ICON_NAMES[UserStatus.OFFLINE], _("Offline"), 16,
             ("colored-icon", "user-status")),
            ("nplus-tab-changed", _("Tab Changed"), 16, ("colored-icon", "notebook-tab-changed")),
            ("nplus-tab-highlight", _("Tab Highlight"), 16, ("colored-icon", "notebook-tab-highlight")),
            (pynicotine.__application_id__, _("Window"), 64, ())]

        if application.tray_icon.available:
            icon_list += [
                (f"{pynicotine.__application_id__}-connect", _("Online (Tray)"), 16, ()),
                (f"{pynicotine.__application_id__}-away", _("Away (Tray)"), 16, ()),
                (f"{pynicotine.__application_id__}-disconnect", _("Offline (Tray)"), 16, ()),
                (f"{pynicotine.__application_id__}-msg", _("Message (Tray)"), 16, ())]

        for icon_name, label, pixel_size, css_classes in icon_list:
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, valign=Gtk.Align.CENTER, spacing=6, visible=True)
            icon = Gtk.Image(icon_name=icon_name, pixel_size=pixel_size, visible=True)
            label = Gtk.Label(label=label, xalign=0.5, wrap=True, visible=True)

            for css_class in css_classes:
                add_css_class(icon, css_class)

            if GTK_API_VERSION >= 4:
                box.append(icon)   # pylint: disable=no-member
                box.append(label)  # pylint: disable=no-member
            else:
                box.add(icon)   # pylint: disable=no-member
                box.add(label)  # pylint: disable=no-member

            self.icon_view.insert(box, -1)

        self.icon_theme_button = FileChooserButton(
            self.icon_theme_label.get_parent(), window=application.preferences,
            label=self.icon_theme_label, end_button=self.icon_theme_clear_button, chooser_type="folder",
            show_open_external_button=not self.application.isolated_mode
        )

        self.options = {
            "notifications": {
                "notification_window_title": self.notification_window_title_toggle,
                "notification_popup_sound": self.notification_sounds_toggle,
                "notification_popup_file": self.notification_download_file_toggle,
                "notification_popup_folder": self.notification_download_folder_toggle,
                "notification_popup_private_message": self.notification_private_message_toggle,
                "notification_popup_chatroom": self.notification_chatroom_toggle,
                "notification_popup_chatroom_mention": self.notification_chatroom_mention_toggle,
                "notification_popup_wish": self.notification_wish_toggle
            },
            "ui": {
                "dark_mode": self.dark_mode_toggle,
                "exitdialog": self.close_action_combobox,
                "trayicon": self.tray_icon_toggle,
                "startup_hidden": self.minimize_tray_startup_toggle,
                "language": self.language_combobox,
                "reverse_file_paths": self.reverse_file_paths_toggle,
                "file_size_unit": self.exact_file_sizes_toggle,
                "tab_select_previous": self.tab_restore_startup_toggle,
                "tabclosers": self.tab_close_buttons_toggle,
                "icontheme": self.icon_theme_button,
                "chatlocal": self.color_chat_local_entry,
                "chatremote": self.color_chat_remote_entry,
                "chatcommand": self.color_chat_command_entry,
                "chatme": self.color_chat_action_entry,
                "chathilite": self.color_chat_highlighted_entry,
                "textbg": self.color_input_background_entry,
                "inputcolor": self.color_input_text_entry,
                "search": self.color_list_text_entry,
                "useraway": self.color_status_away_entry,
                "useronline": self.color_status_online_entry,
                "useroffline": self.color_status_offline_entry,
                "urlcolor": self.color_url_entry,
                "tab_default": self.color_tab_entry,
                "tab_hilite": self.color_tab_highlighted_entry,
                "tab_changed": self.color_tab_changed_entry,
                "usernamestyle": self.chat_username_appearance_combobox,
                "usernamehotspots": self.chat_colored_usernames_toggle,
                "buddylistinchatrooms": self.buddy_list_position_combobox,
                "header_bar": self.header_bar_toggle
            }
        }

        for dictionary in (
            self.font_buttons,
            self.tab_position_comboboxes
        ):
            self.options["ui"].update(dictionary)

    def destroy(self):

        self.language_combobox.destroy()
        self.close_action_combobox.destroy()
        self.chat_username_appearance_combobox.destroy()
        self.buddy_list_position_combobox.destroy()
        self.icon_theme_button.destroy()

        for combobox in self.tab_position_comboboxes.values():
            combobox.destroy()

        self.__dict__.clear()

    def set_settings(self):

        self.application.preferences.set_widgets_data(self.options)

        self.close_action_label.get_parent().set_visible(not self.application.isolated_mode)
        self.tray_options_container.set_visible(self.application.tray_icon.available)

        for page_id, enabled in config.sections["ui"]["modes_visible"].items():
            widget = self.tab_visible_toggles.get(page_id)

            if widget is not None:
                widget.set_active(enabled)

    def get_settings(self):

        enabled_tabs = {}

        for page_id, widget in self.tab_visible_toggles.items():
            enabled_tabs[page_id] = widget.get_active()

        return {
            "notifications": {
                "notification_window_title": self.notification_window_title_toggle.get_active(),
                "notification_popup_sound": self.notification_sounds_toggle.get_active(),
                "notification_popup_file": self.notification_download_file_toggle.get_active(),
                "notification_popup_folder": self.notification_download_folder_toggle.get_active(),
                "notification_popup_private_message": self.notification_private_message_toggle.get_active(),
                "notification_popup_chatroom": self.notification_chatroom_toggle.get_active(),
                "notification_popup_chatroom_mention": self.notification_chatroom_mention_toggle.get_active(),
                "notification_popup_wish": self.notification_wish_toggle.get_active()
            },
            "ui": {
                "dark_mode": self.dark_mode_toggle.get_active(),
                "exitdialog": self.close_action_combobox.get_selected_id(),
                "trayicon": self.tray_icon_toggle.get_active(),
                "startup_hidden": self.minimize_tray_startup_toggle.get_active(),
                "language": self.language_combobox.get_selected_id(),
                "globalfont": self.get_font(self.font_global_button),
                "listfont": self.get_font(self.font_list_button),
                "textviewfont": self.get_font(self.font_text_view_button),
                "chatfont": self.get_font(self.font_chat_button),
                "searchfont": self.get_font(self.font_search_button),
                "transfersfont": self.get_font(self.font_transfers_button),
                "browserfont": self.get_font(self.font_browse_button),
                "reverse_file_paths": self.reverse_file_paths_toggle.get_active(),
                "file_size_unit": "B" if self.exact_file_sizes_toggle.get_active() else "",
                "tabmain": self.tab_position_main_combobox.get_selected_id(),
                "tabrooms": self.tab_position_chatrooms_combobox.get_selected_id(),
                "tabprivate": self.tab_position_private_chat_combobox.get_selected_id(),
                "tabsearch": self.tab_position_search_combobox.get_selected_id(),
                "tabinfo": self.tab_position_userinfo_combobox.get_selected_id(),
                "tabbrowse": self.tab_position_browse_combobox.get_selected_id(),
                "modes_visible": enabled_tabs,
                "tab_select_previous": self.tab_restore_startup_toggle.get_active(),
                "tabclosers": self.tab_close_buttons_toggle.get_active(),
                "icontheme": self.icon_theme_button.get_path(),
                "chatlocal": self.color_chat_local_entry.get_text().strip(),
                "chatremote": self.color_chat_remote_entry.get_text().strip(),
                "chatcommand": self.color_chat_command_entry.get_text().strip(),
                "chatme": self.color_chat_action_entry.get_text().strip(),
                "chathilite": self.color_chat_highlighted_entry.get_text().strip(),
                "urlcolor": self.color_url_entry.get_text().strip(),
                "textbg": self.color_input_background_entry.get_text().strip(),
                "inputcolor": self.color_input_text_entry.get_text().strip(),
                "search": self.color_list_text_entry.get_text().strip(),
                "useraway": self.color_status_away_entry.get_text().strip(),
                "useronline": self.color_status_online_entry.get_text().strip(),
                "useroffline": self.color_status_offline_entry.get_text().strip(),
                "tab_hilite": self.color_tab_highlighted_entry.get_text().strip(),
                "tab_default": self.color_tab_entry.get_text().strip(),
                "tab_changed": self.color_tab_changed_entry.get_text().strip(),
                "usernamestyle": self.chat_username_appearance_combobox.get_selected_id(),
                "usernamehotspots": self.chat_colored_usernames_toggle.get_active(),
                "buddylistinchatrooms": self.buddy_list_position_combobox.get_selected_id(),
                "header_bar": self.header_bar_toggle.get_active()
            }
        }

    # Icons #

    def on_clear_icon_theme(self, *_args):
        self.icon_theme_button.clear()

    # Fonts #

    def get_font(self, button):

        if GTK_API_VERSION >= 4:
            font_desc = button.get_font_desc()
            return font_desc.to_string() if font_desc.get_family() else ""

        return button.get_font()

    def on_clear_font(self, _button, font_id):

        font_button = self.font_buttons[font_id]

        if GTK_API_VERSION >= 4:
            font_button.set_font_desc(Pango.FontDescription())
        else:
            font_button.set_font("")

    # Colors #

    def on_color_entry_changed(self, entry, color_id):

        self.editing_color = True

        rgba = Gdk.RGBA()
        color_hex = entry.get_text().strip()

        if color_hex:
            rgba.parse(color_hex)
        else:
            rgba.red = rgba.green = rgba.blue = rgba.alpha = 0

        color_button = self.color_buttons[color_id]
        color_button.set_rgba(rgba)

        self.editing_color = False

    def on_color_button_changed(self, button, _param, color_id):

        if self.editing_color:
            return

        rgba = button.get_rgba()

        if rgba.alpha <= 0:
            # Unset color if transparent
            color_hex = ""
        else:
            red_color = round(rgba.red * 255)
            green_color = round(rgba.green * 255)
            blue_color = round(rgba.blue * 255)
            color_hex = f"#{red_color:02X}{green_color:02X}{blue_color:02X}"

            if rgba.alpha < 1 and GTK_API_VERSION >= 4:
                alpha_value = round(rgba.alpha * 255)
                color_hex += f"{alpha_value:02X}"

        entry = self.color_entries[color_id]

        if entry.get_text() != color_hex:
            entry.set_text(color_hex)

    def on_default_color(self, entry, *args):

        if GTK_API_VERSION >= 4:
            _icon_pos, color_id = args
        else:
            _icon_pos, _event, color_id = args

        entry.set_text(config.defaults["ui"][color_id])

    # Tabs #

    def on_select_buddy_list_position(self, _combobox, selected_id):

        buddies_tab_active = (selected_id == "tab")

        self.tab_visible_userlist_toggle.set_active(buddies_tab_active)
        self.tab_visible_userlist_toggle.set_sensitive(buddies_tab_active)


class LoggingPage:

    def __init__(self, application):

        (
            self.chatroom_log_folder_default_button,
            self.chatroom_log_folder_label,
            self.container,
            self.debug_log_folder_default_button,
            self.debug_log_folder_label,
            self.folder_locations_container,
            self.format_codes_label,
            self.log_chatroom_toggle,
            self.log_debug_toggle,
            self.log_private_chat_toggle,
            self.log_timestamp_format_entry,
            self.log_transfer_toggle,
            self.private_chat_log_folder_default_button,
            self.private_chat_log_folder_label,
            self.transfer_log_folder_default_button,
            self.transfer_log_folder_label
        ) = self.widgets = ui.load(scope=self, path="settings/log.ui")

        self.application = application

        format_codes_url = "https://docs.python.org/3/library/datetime.html#format-codes"
        format_codes_label = _("Format codes")

        self.format_codes_label.set_markup(
            f"<a href='{format_codes_url}' title='{format_codes_url}'>{format_codes_label}</a>")
        self.format_codes_label.connect("activate-link", self.on_activate_link)

        self.private_chat_log_folder_button = FileChooserButton(
            self.private_chat_log_folder_label.get_parent(), window=application.preferences,
            label=self.private_chat_log_folder_label, end_button=self.private_chat_log_folder_default_button,
            chooser_type="folder", show_open_external_button=not self.application.isolated_mode
        )
        self.chatroom_log_folder_button = FileChooserButton(
            self.chatroom_log_folder_label.get_parent(), window=application.preferences,
            label=self.chatroom_log_folder_label, end_button=self.chatroom_log_folder_default_button,
            chooser_type="folder", show_open_external_button=not self.application.isolated_mode
        )
        self.transfer_log_folder_button = FileChooserButton(
            self.transfer_log_folder_label.get_parent(), window=application.preferences,
            label=self.transfer_log_folder_label, end_button=self.transfer_log_folder_default_button,
            chooser_type="folder", show_open_external_button=not self.application.isolated_mode
        )
        self.debug_log_folder_button = FileChooserButton(
            self.debug_log_folder_label.get_parent(), window=application.preferences,
            label=self.debug_log_folder_label, end_button=self.debug_log_folder_default_button,
            chooser_type="folder", show_open_external_button=not self.application.isolated_mode
        )

        self.options = {
            "logging": {
                "privatechat": self.log_private_chat_toggle,
                "privatelogsdir": self.private_chat_log_folder_button,
                "chatrooms": self.log_chatroom_toggle,
                "roomlogsdir": self.chatroom_log_folder_button,
                "transfers": self.log_transfer_toggle,
                "transferslogsdir": self.transfer_log_folder_button,
                "debug_file_output": self.log_debug_toggle,
                "debuglogsdir": self.debug_log_folder_button,
                "log_timestamp": self.log_timestamp_format_entry
            }
        }

    def destroy(self):

        self.private_chat_log_folder_button.destroy()
        self.chatroom_log_folder_button.destroy()
        self.transfer_log_folder_button.destroy()
        self.debug_log_folder_button.destroy()

        self.__dict__.clear()

    def set_settings(self):

        self.application.preferences.set_widgets_data(self.options)

        self.format_codes_label.set_visible(not self.application.isolated_mode)
        self.folder_locations_container.set_margin_top(24 if self.application.isolated_mode else 0)

    def get_settings(self):

        return {
            "logging": {
                "privatechat": self.log_private_chat_toggle.get_active(),
                "privatelogsdir": self.private_chat_log_folder_button.get_path(),
                "chatrooms": self.log_chatroom_toggle.get_active(),
                "roomlogsdir": self.chatroom_log_folder_button.get_path(),
                "transfers": self.log_transfer_toggle.get_active(),
                "transferslogsdir": self.transfer_log_folder_button.get_path(),
                "debug_file_output": self.log_debug_toggle.get_active(),
                "debuglogsdir": self.debug_log_folder_button.get_path(),
                "log_timestamp": self.log_timestamp_format_entry.get_text()
            }
        }

    def on_activate_link(self, _label, url):
        open_uri(url)
        return True

    def on_default_timestamp(self, *_args):
        self.log_timestamp_format_entry.set_text(config.defaults["logging"]["log_timestamp"])

    def on_default_private_chat_log_folder(self, *_args):
        self.private_chat_log_folder_button.set_path(config.defaults["logging"]["privatelogsdir"])

    def on_default_chatroom_log_folder(self, *_args):
        self.chatroom_log_folder_button.set_path(config.defaults["logging"]["roomlogsdir"])

    def on_default_transfer_log_folder(self, *_args):
        self.transfer_log_folder_button.set_path(config.defaults["logging"]["transferslogsdir"])

    def on_default_debug_log_folder(self, *_args):
        self.debug_log_folder_button.set_path(config.defaults["logging"]["debuglogsdir"])


class SearchesPage:

    def __init__(self, application):

        (
            self.clear_filter_history_icon,
            self.clear_filter_history_success_icon,
            self.clear_search_history_icon,
            self.clear_search_history_success_icon,
            self.container,
            self.enable_default_filters_toggle,
            self.enable_search_history_toggle,
            self.filter_bitrate_entry,
            self.filter_country_entry,
            self.filter_exclude_entry,
            self.filter_file_size_entry,
            self.filter_file_type_entry,
            self.filter_free_slot_toggle,
            self.filter_help_button,
            self.filter_include_entry,
            self.filter_length_entry,
            self.max_displayed_results_spinner,
            self.max_sent_results_spinner,
            self.min_search_term_length_spinner,
            self.repond_search_requests_toggle,
            self.show_private_results_toggle
        ) = self.widgets = ui.load(scope=self, path="settings/search.ui")

        self.application = application

        self.filter_help = SearchFilterHelp(application.preferences)
        self.filter_help.set_menu_button(self.filter_help_button)

        self.options = {
            "searches": {
                "maxresults": self.max_sent_results_spinner,
                "enablefilters": self.enable_default_filters_toggle,
                "defilter": None,
                "search_results": self.repond_search_requests_toggle,
                "max_displayed_results": self.max_displayed_results_spinner,
                "min_search_chars": self.min_search_term_length_spinner,
                "enable_history": self.enable_search_history_toggle,
                "private_search_results": self.show_private_results_toggle
            }
        }

    def destroy(self):
        self.filter_help.destroy()
        self.__dict__.clear()

    def set_settings(self):

        searches = config.sections["searches"]
        self.application.preferences.set_widgets_data(self.options)

        if searches["defilter"] is not None:
            num_filters = len(searches["defilter"])

            if num_filters > 0:
                self.filter_include_entry.set_text(str(searches["defilter"][0]))

            if num_filters > 1:
                self.filter_exclude_entry.set_text(str(searches["defilter"][1]))

            if num_filters > 2:
                self.filter_file_size_entry.set_text(str(searches["defilter"][2]))

            if num_filters > 3:
                self.filter_bitrate_entry.set_text(str(searches["defilter"][3]))

            if num_filters > 4:
                self.filter_free_slot_toggle.set_active(searches["defilter"][4])

            if num_filters > 5:
                self.filter_country_entry.set_text(str(searches["defilter"][5]))

            if num_filters > 6:
                self.filter_file_type_entry.set_text(str(searches["defilter"][6]))

            if num_filters > 7:
                self.filter_length_entry.set_text(str(searches["defilter"][7]))

        self.clear_search_history_icon.get_parent().set_visible_child(self.clear_search_history_icon)
        self.clear_filter_history_icon.get_parent().set_visible_child(self.clear_filter_history_icon)

    def get_settings(self):

        return {
            "searches": {
                "maxresults": self.max_sent_results_spinner.get_value_as_int(),
                "enablefilters": self.enable_default_filters_toggle.get_active(),
                "defilter": [
                    self.filter_include_entry.get_text().strip(),
                    self.filter_exclude_entry.get_text().strip(),
                    self.filter_file_size_entry.get_text().strip(),
                    self.filter_bitrate_entry.get_text().strip(),
                    self.filter_free_slot_toggle.get_active(),
                    self.filter_country_entry.get_text().strip(),
                    self.filter_file_type_entry.get_text().strip(),
                    self.filter_length_entry.get_text().strip()
                ],
                "search_results": self.repond_search_requests_toggle.get_active(),
                "max_displayed_results": self.max_displayed_results_spinner.get_value_as_int(),
                "min_search_chars": self.min_search_term_length_spinner.get_value_as_int(),
                "enable_history": self.enable_search_history_toggle.get_active(),
                "private_search_results": self.show_private_results_toggle.get_active()
            }
        }

    def on_clear_search_history(self, *_args):

        self.application.window.search.clear_search_history()

        stack = self.clear_search_history_success_icon.get_parent()
        stack.set_visible_child(self.clear_search_history_success_icon)

    def on_clear_filter_history(self, *_args):

        self.application.window.search.clear_filter_history()

        stack = self.clear_filter_history_success_icon.get_parent()
        stack.set_visible_child(self.clear_filter_history_success_icon)


class UrlHandlersPage:

    def __init__(self, application):

        (
            self.container,
            self.file_manager_label,
            self.protocol_list_container
        ) = self.widgets = ui.load(scope=self, path="settings/urlhandlers.ui")

        self.application = application

        self.file_manager_combobox = ComboBox(
            container=self.file_manager_label.get_parent(), label=self.file_manager_label, has_entry=True,
            items=(
                ("", None),
                ("xdg-open $", None),
                ("explorer $", None),
                ("nautilus $", None),
                ("nemo $", None),
                ("caja $", None),
                ("thunar $", None),
                ("dolphin $", None),
                ("konqueror $", None),
                ("krusader --left $", None),
                ("xterm -e mc $", None)
            )
        )

        self.options = {
            "urls": {
                "protocols": None
            },
            "ui": {
                "filemanager": self.file_manager_combobox
            }
        }

        self.default_protocols = [
            "http://",
            "https://",
            "audio",
            "image",
            "video",
            "document",
            "text",
            "archive",
            ".mp3",
            ".jpg",
            ".pdf"
        ]

        self.default_commands = [
            "xdg-open $",
            "firefox $",
            "firefox --new-tab $",
            "epiphany $",
            "chromium-browser $",
            "falkon $",
            "links -g $",
            "dillo $",
            "konqueror $",
            '"c:\\Program Files\\Mozilla Firefox\\Firefox.exe" $'
        ]

        self.protocols = {}
        self.protocol_list_view = TreeView(
            application.window, parent=self.protocol_list_container, multi_select=True,
            activate_row_callback=self.on_edit_handler,
            delete_accelerator_callback=self.on_remove_handler,
            columns={
                "protocol": {
                    "column_type": "text",
                    "title": _("Protocol"),
                    "width": 120,
                    "expand_column": True,
                    "iterator_key": True,
                    "default_sort_type": "ascending"
                },
                "command": {
                    "column_type": "text",
                    "title": _("Command"),
                    "expand_column": True
                }
            }
        )

    def destroy(self):

        self.file_manager_combobox.destroy()
        self.protocol_list_view.destroy()

        self.__dict__.clear()

    def set_settings(self):

        self.protocol_list_view.clear()
        self.protocol_list_view.freeze()
        self.protocols.clear()

        self.application.preferences.set_widgets_data(self.options)

        self.protocols = config.sections["urls"]["protocols"].copy()

        for protocol, command in self.protocols.items():
            self.protocol_list_view.add_row([str(protocol), str(command)], select_row=False)

        self.protocol_list_view.unfreeze()

    def get_settings(self):

        return {
            "urls": {
                "protocols": self.protocols.copy()
            },
            "ui": {
                "filemanager": self.file_manager_combobox.get_text().strip()
            }
        }

    def on_add_handler_response(self, dialog, _response_id, _data):

        protocol = dialog.get_entry_value().strip()
        command = dialog.get_second_entry_value().strip()

        if not protocol or not command:
            return

        if protocol.startswith("."):
            # Only keep last part of file extension (e.g. .tar.gz -> .gz)
            protocol = "." + protocol.rpartition(".")[-1]

        elif not protocol.endswith("://") and protocol not in self.default_protocols:
            protocol += "://"

        iterator = self.protocol_list_view.iterators.get(protocol)
        self.protocols[protocol] = command

        if iterator:
            self.protocol_list_view.set_row_value(iterator, "command", command)
            return

        self.protocol_list_view.add_row([protocol, command])

    def on_add_handler(self, *_args):

        EntryDialog(
            parent=self.application.preferences,
            title=_("Add URL Handler"),
            message=_("Enter the protocol and the command for the URL handler:"),
            action_button_label=_("_Add"),
            callback=self.on_add_handler_response,
            use_second_entry=True,
            droplist=self.default_protocols,
            second_droplist=self.default_commands
        ).present()

    def on_edit_handler_response(self, dialog, _response_id, iterator):

        command = dialog.get_entry_value().strip()

        if not command:
            return

        protocol = self.protocol_list_view.get_row_value(iterator, "protocol")

        self.protocols[protocol] = command
        self.protocol_list_view.set_row_value(iterator, "command", command)

    def on_edit_handler(self, *_args):

        for iterator in self.protocol_list_view.get_selected_rows():
            protocol = self.protocol_list_view.get_row_value(iterator, "protocol")
            command = self.protocol_list_view.get_row_value(iterator, "command")

            EntryDialog(
                parent=self.application.preferences,
                title=_("Edit Command"),
                message=_("Enter a new command for protocol %s:") % protocol,
                action_button_label=_("_Edit"),
                callback=self.on_edit_handler_response,
                callback_data=iterator,
                droplist=self.default_commands,
                default=command
            ).present()
            return

    def on_remove_handler(self, *_args):

        for iterator in reversed(list(self.protocol_list_view.get_selected_rows())):
            protocol = self.protocol_list_view.get_row_value(iterator, "protocol")
            orig_iterator = self.protocol_list_view.iterators[protocol]

            self.protocol_list_view.remove_row(orig_iterator)
            del self.protocols[protocol]

    def on_default_file_manager(self, *_args):
        default_file_manager = config.defaults["ui"]["filemanager"]
        self.file_manager_combobox.set_text(default_file_manager)


class NowPlayingPage:

    def __init__(self, application):

        (
            self.command_entry,
            self.command_label,
            self.container,
            self.format_help_label,
            self.format_message_label,
            self.lastfm_radio,
            self.listenbrainz_radio,
            self.mpris_radio,
            self.other_radio,
            self.output_label,
            self.test_configuration_button
        ) = self.widgets = ui.load(scope=self, path="settings/nowplaying.ui")

        self.application = application
        self.enable_mpris = (
            not self.application.isolated_mode
            and sys.platform not in {"win32", "darwin"}
            and "SNAP_NAME" not in os.environ
        )
        self.enable_other = not self.application.isolated_mode

        self.format_message_combobox = ComboBox(
            container=self.format_message_label.get_parent(), label=self.format_message_label,
            has_entry=True
        )

        self.options = {
            "players": {
                "npformat": self.format_message_combobox,
                "npothercommand": self.command_entry
            }
        }

        self.player_replacers = []

        # Default format list
        self.default_format_list = [
            "$n",
            "$n ($f)",
            "/me np: $n",
            "$a - $t",
            "[$a] $t",
            "$a - $b - $t",
            "$a - $b - $t ($l/$r KBps) from $y $c"
        ]
        self.custom_format_list = []

        # Supply the information needed for the Now Playing class to return a song
        self.test_configuration_button.connect(
            "clicked",
            core.now_playing.display_now_playing,
            self.set_now_playing_output,   # Callback to update the song displayed
            self.get_player,               # Callback to retrieve selected player
            self.get_command,              # Callback to retrieve command text
            self.get_format                # Callback to retrieve format text
        )

        self.mpris_radio.set_visible(self.enable_mpris)
        self.other_radio.set_visible(self.enable_other)

    def destroy(self):
        self.format_message_combobox.destroy()
        self.__dict__.clear()

    def set_settings(self):

        # Add formats
        self.format_message_combobox.freeze()
        self.format_message_combobox.clear()

        for item in self.default_format_list:
            self.format_message_combobox.append(str(item))

        if self.custom_format_list:
            for item in self.custom_format_list:
                self.format_message_combobox.append(str(item))

        self.format_message_combobox.unfreeze()

        self.application.preferences.set_widgets_data(self.options)

        # Save reference to format list for get_settings()
        self.custom_format_list = config.sections["players"]["npformatlist"]

        # Update UI with saved player
        self.set_player(config.sections["players"]["npplayer"])
        self.update_now_playing_info()

    def get_player(self):

        player = "lastfm"

        if self.enable_mpris and self.mpris_radio.get_active():
            player = "mpris"

        elif self.enable_other and self.other_radio.get_active():
            player = "other"

        elif self.listenbrainz_radio.get_active():
            player = "listenbrainz"

        return player

    def get_command(self):
        return self.command_entry.get_text().strip()

    def get_format(self):
        return self.format_message_combobox.get_text()

    def set_player(self, player):

        if player == "mpris" and self.enable_mpris:
            self.mpris_radio.set_active(True)

        elif player == "other" and self.enable_other:
            self.other_radio.set_active(True)

        elif player == "listenbrainz":
            self.listenbrainz_radio.set_active(True)

        else:
            self.lastfm_radio.set_active(True)

    def update_now_playing_info(self, *_args):

        if self.lastfm_radio.get_active():
            self.player_replacers = ["$n", "$t", "$a", "$b"]
            self.command_label.set_text(_("Username;APIKEY"))

        elif self.mpris_radio.get_active():
            self.player_replacers = ["$n", "$p", "$a", "$b", "$t", "$y", "$c", "$r", "$k", "$l", "$f"]
            self.command_label.set_text(_("Music player (e.g. amarok, audacious, exaile); leave empty to autodetect:"))

        elif self.listenbrainz_radio.get_active():
            self.player_replacers = ["$n", "$t", "$a", "$b"]
            self.command_label.set_text(_("Username: "))

        elif self.other_radio.get_active():
            self.player_replacers = ["$n"]
            self.command_label.set_text(_("Command:"))

        legend = ""

        for item in self.player_replacers:
            legend += item + "\t"

            if item == "$t":
                legend += _("Title")
            elif item == "$n":
                legend += _('Now Playing (typically "%(artist)s - %(title)s")') % {
                    "artist": _("Artist"), "title": _("Title")}
            elif item == "$l":
                legend += _("Duration")
            elif item == "$r":
                legend += _("Bitrate")
            elif item == "$c":
                legend += _("Comment")
            elif item == "$a":
                legend += _("Artist")
            elif item == "$b":
                legend += _("Album")
            elif item == "$k":
                legend += _("Track Number")
            elif item == "$y":
                legend += _("Year")
            elif item == "$f":
                legend += _("Filename (URI)")
            elif item == "$p":
                legend += _("Program")

            legend += "\n"

        self.format_help_label.set_text(legend[:-1])

    def set_now_playing_output(self, title):
        self.output_label.set_text(title)

    def get_settings(self):

        npformat = self.get_format()

        if (npformat and not npformat.isspace()
                and npformat not in self.custom_format_list
                and npformat not in self.default_format_list):
            self.custom_format_list.append(npformat)

        return {
            "players": {
                "npplayer": self.get_player(),
                "npothercommand": self.get_command(),
                "npformat": npformat,
                "npformatlist": self.custom_format_list
            }
        }


class PluginsPage:

    def __init__(self, application):

        (
            self.add_plugins_button,
            self.container,
            self.enable_plugins_toggle,
            self.plugin_authors_label,
            self.plugin_description_view_container,
            self.plugin_list_container,
            self.plugin_name_label,
            self.plugin_settings_button,
            self.plugin_version_label
        ) = self.widgets = ui.load(scope=self, path="settings/plugin.ui")

        self.application = application
        self.selected_plugin = None
        self.plugin_settings = None

        self.options = {
            "plugins": {
                "enable": self.enable_plugins_toggle
            }
        }

        self.plugin_description_view = TextView(self.plugin_description_view_container, editable=False,
                                                pixels_below_lines=2)
        self.plugin_list_view = TreeView(
            application.window, parent=self.plugin_list_container,
            activate_row_callback=self.on_row_activated, select_row_callback=self.on_select_plugin,
            columns={
                # Visible columns
                "enabled": {
                    "column_type": "toggle",
                    "title": _("Enabled"),
                    "width": 0,
                    "toggle_callback": self.on_plugin_toggle,
                    "hide_header": True
                },
                "plugin": {
                    "column_type": "text",
                    "title": _("Plugin"),
                    "default_sort_type": "ascending"
                },

                # Hidden data columns
                "plugin_id": {"data_type": GObject.TYPE_STRING, "iterator_key": True}
            }
        )
        self.add_plugins_button.set_visible(not self.application.isolated_mode)

    def destroy(self):

        self.plugin_description_view.destroy()
        self.plugin_list_view.destroy()

        if self.plugin_settings is not None:
            self.plugin_settings.destroy()

        self.__dict__.clear()

    def set_settings(self):

        self.plugin_list_view.clear()
        self.plugin_list_view.freeze()

        self.application.preferences.set_widgets_data(self.options)

        for plugin_id in core.pluginhandler.list_installed_plugins():
            try:
                info = core.pluginhandler.get_plugin_info(plugin_id)
            except OSError:
                continue

            plugin_name = info.get("Name", plugin_id)
            enabled = (plugin_id in config.sections["plugins"]["enabled"])
            self.plugin_list_view.add_row([enabled, plugin_name, plugin_id], select_row=False)

        self.plugin_list_view.unfreeze()

    def get_settings(self):

        return {
            "plugins": {
                "enable": self.enable_plugins_toggle.get_active()
            }
        }

    def check_plugin_settings_button(self, plugin):
        self.plugin_settings_button.set_sensitive(bool(core.pluginhandler.get_plugin_settings(plugin)))

    def on_select_plugin(self, list_view, iterator):

        if iterator is None:
            self.selected_plugin = _("No Plugin Selected")
            info = {}
        else:
            self.selected_plugin = list_view.get_row_value(iterator, "plugin_id")
            info = core.pluginhandler.get_plugin_info(self.selected_plugin)

        plugin_name = info.get("Name", self.selected_plugin)
        plugin_version = info.get("Version", "-")
        plugin_authors = ", ".join(info.get("Authors", "-"))
        plugin_description = info.get("Description", "").replace(r"\n", "\n")

        self.plugin_name_label.set_text(plugin_name)
        self.plugin_version_label.set_text(plugin_version)
        self.plugin_authors_label.set_text(plugin_authors)

        self.plugin_description_view.clear()
        self.plugin_description_view.append_line(plugin_description)
        self.plugin_description_view.place_cursor_at_line(0)

        self.check_plugin_settings_button(self.selected_plugin)

    def on_plugin_toggle(self, list_view, iterator):

        plugin_id = list_view.get_row_value(iterator, "plugin_id")
        enabled = core.pluginhandler.toggle_plugin(plugin_id)

        list_view.set_row_value(iterator, "enabled", enabled)
        self.check_plugin_settings_button(plugin_id)

    def on_enable_plugins(self, *_args):

        enabled_plugin_ids = config.sections["plugins"]["enabled"].copy()

        if self.enable_plugins_toggle.get_active():
            # Enable all selected plugins
            for plugin_id in enabled_plugin_ids:
                core.pluginhandler.enable_plugin(plugin_id)

            self.check_plugin_settings_button(self.selected_plugin)
            return

        # Disable all plugins
        for plugin in core.pluginhandler.enabled_plugins.copy():
            core.pluginhandler.disable_plugin(plugin)

        config.sections["plugins"]["enabled"] = enabled_plugin_ids
        self.plugin_settings_button.set_sensitive(False)

    def on_add_plugins(self, *_args):
        open_folder_path(core.pluginhandler.user_plugin_folder, create_folder=True)

    def on_plugin_settings(self, *_args):

        if self.selected_plugin is None:
            return

        settings = core.pluginhandler.get_plugin_settings(self.selected_plugin)

        if not settings:
            return

        if self.plugin_settings is None:
            self.plugin_settings = PluginSettings(self.application)

        self.plugin_settings.update_settings(plugin_id=self.selected_plugin, plugin_settings=settings)
        self.plugin_settings.present()

    def on_row_activated(self, _list_view, _iterator, column_id):
        if column_id == "plugin":
            self.on_plugin_settings()


class Preferences(Dialog):

    def __init__(self, application):

        self.application = application

        (
            self.apply_button,
            self.cancel_button,
            self.container,
            self.content,
            self.export_button,
            self.ok_button,
            self.preferences_list,
            self.viewport
        ) = self.widgets = ui.load(scope=self, path="dialogs/preferences.ui")

        super().__init__(
            parent=application.window,
            modal=False,
            content_box=self.container,
            buttons_start=(self.cancel_button, self.export_button),
            buttons_end=(self.apply_button, self.ok_button),
            default_button=self.ok_button,
            close_callback=self.on_close,
            title=_("Preferences"),
            width=960,
            height=650,
            show_title_buttons=False
        )

        add_css_class(self.widget, "preferences-border")

        if GTK_API_VERSION == 3:
            # Scroll to focused widgets
            self.viewport.set_focus_vadjustment(self.content.get_vadjustment())

        self.pages = {}
        self.page_ids = [
            ("network", NetworkPage, _("Network"), "network-wireless-symbolic"),
            ("user-interface", UserInterfacePage, _("User Interface"), "view-grid-symbolic"),
            ("shares", SharesPage, _("Shares"), "folder-symbolic"),
            ("downloads", DownloadsPage, _("Downloads"), "folder-download-symbolic"),
            ("uploads", UploadsPage, _("Uploads"), "emblem-shared-symbolic"),
            ("searches", SearchesPage, _("Searches"), "system-search-symbolic"),
            ("user-profile", UserProfilePage, _("User Profile"), "avatar-default-symbolic"),
            ("chats", ChatsPage, _("Chats"), "insert-text-symbolic"),
            ("now-playing", NowPlayingPage, _("Now Playing"), "folder-music-symbolic"),
            ("logging", LoggingPage, _("Logging"), "folder-documents-symbolic"),
            ("banned-users", BannedUsersPage, _("Banned Users"), "action-unavailable-symbolic"),
            ("ignored-users", IgnoredUsersPage, _("Ignored Users"), "microphone-sensitivity-muted-symbolic"),
            ("url-handlers", UrlHandlersPage, _("URL Handlers"), "insert-link-symbolic"),
            ("plugins", PluginsPage, _("Plugins"), "application-x-addon-symbolic")
        ]

        for item in self.page_ids[:]:
            page_id, _page_class, label, icon_name = item

            if self.application.isolated_mode and page_id == "url-handlers":
                self.page_ids.remove(item)
                continue

            box = Gtk.Box(margin_top=8, margin_bottom=8, margin_start=12, margin_end=12, spacing=12, visible=True)
            icon = Gtk.Image(icon_name=icon_name, visible=True)
            label = Gtk.Label(label=label, xalign=0, visible=True)

            if GTK_API_VERSION >= 4:
                box.append(icon)   # pylint: disable=no-member
                box.append(label)  # pylint: disable=no-member
            else:
                box.add(icon)   # pylint: disable=no-member
                box.add(label)  # pylint: disable=no-member

            self.preferences_list.insert(box, -1)

        Accelerator("Tab", self.preferences_list, self.on_sidebar_tab_accelerator)
        Accelerator("<Shift>Tab", self.preferences_list, self.on_sidebar_shift_tab_accelerator)

    def destroy(self):

        for page in self.pages.values():
            page.destroy()

        super().destroy()

    def set_active_page(self, page_id):

        if page_id is None:
            return

        for index, (n_page_id, _page_class, _label, _icon_name) in enumerate(self.page_ids):
            if n_page_id != page_id:
                continue

            row = self.preferences_list.get_row_at_index(index)
            self.preferences_list.select_row(row)
            break

    def set_widgets_data(self, options):

        for section, keys in options.items():
            if section not in config.sections:
                continue

            for key in keys:
                widget = options[section][key]

                if widget is None:
                    continue

                self.set_widget(widget, config.sections[section][key])

    @staticmethod
    def set_widget(widget, value):

        if isinstance(widget, Gtk.SpinButton):
            try:
                widget.set_value(value)

            except TypeError:
                # Not a numerical value
                pass

        elif isinstance(widget, Gtk.Entry):
            if isinstance(value, (str, int)) and widget.get_text() != value:
                widget.set_text(value)

        elif isinstance(widget, TextView):
            if isinstance(value, str):
                widget.set_text(unescape(value))

        elif isinstance(widget, Gtk.Switch):
            widget.set_active(value)

        elif isinstance(widget, Gtk.CheckButton):
            try:
                # Radio button
                if isinstance(value, int) and value < len(widget.group_radios):
                    widget.group_radios[value].set_active(True)

            except (AttributeError, TypeError):
                # Regular check button
                widget.set_active(value)

        elif isinstance(widget, ComboBox):
            if widget.entry is not None:
                widget.set_text(value)
            else:
                widget.set_selected_id(value)

        elif isinstance(widget, Gtk.FontButton):
            widget.set_font(value)

        elif isinstance(widget, TreeView):
            widget.freeze()

            if isinstance(value, list):
                for item in value:
                    if isinstance(item, list):
                        row = item
                    else:
                        row = [item]

                    widget.add_row(row, select_row=False)

            elif isinstance(value, dict):
                for item1, item2 in value.items():
                    widget.add_row([str(item1), str(item2)], select_row=False)

            widget.unfreeze()

        elif isinstance(widget, FileChooserButton):
            widget.set_path(value)

        elif isinstance(widget, Gtk.FontDialogButton):
            widget.set_font_desc(Pango.FontDescription.from_string(value))

    def set_settings(self):

        for page in self.pages.values():
            page.set_settings()

    def get_settings(self):

        options = {
            "server": {},
            "transfers": {},
            "userinfo": {},
            "logging": {},
            "searches": {},
            "privatechat": {},
            "ui": {},
            "urls": {},
            "players": {},
            "words": {},
            "notifications": {},
            "plugins": {}
        }

        for page in self.pages.values():
            for key, data in page.get_settings().items():
                options[key].update(data)

        for section, key in (
            ("server", "login"),
            ("server", "portrange"),
            ("server", "interface"),
            ("server", "server")
        ):
            reconnect_required = self.has_option_changed(options, section, key)

            if reconnect_required:
                break

        portmap_changed = self.has_option_changed(options, "server", "upnp")
        portmap_required = None

        if portmap_changed:
            portmap_required = "add" if options["server"]["upnp"] else "remove"

        for section, key in (
            ("transfers", "shared"),
            ("transfers", "buddyshared"),
            ("transfers", "trustedshared")
        ):
            rescan_required = self.has_option_changed(options, section, key)

            if rescan_required:
                break

        for section, key in (
            ("transfers", "reveal_buddy_shares"),
            ("transfers", "reveal_trusted_shares")
        ):
            recompress_shares_required = self.has_option_changed(options, section, key)

            if recompress_shares_required:
                break

        for section, key in (
            ("userinfo", "descr"),
            ("userinfo", "pic")
        ):
            user_profile_required = self.has_option_changed(options, section, key)

            if user_profile_required:
                break

        for section, key in (
            ("words", "tab"),
            ("words", "dropdown"),
            ("words", "characters"),
            ("words", "roomnames"),
            ("words", "buddies"),
            ("words", "roomusers"),
            ("words", "commands")
        ):
            completion_required = self.has_option_changed(options, section, key)

            if completion_required:
                break

        private_room_required = self.has_option_changed(options, "server", "private_chatrooms")
        search_history_required = self.has_option_changed(options, "searches", "enable_history")

        return (
            reconnect_required,
            portmap_required,
            rescan_required,
            recompress_shares_required,
            user_profile_required,
            private_room_required,
            completion_required,
            search_history_required,
            options
        )

    def has_option_changed(self, options, section, key):

        if key not in options[section]:
            return False

        return options[section][key] != config.sections[section][key]

    def update_settings(self, settings_closed=False):

        (
            reconnect_required,
            portmap_required,
            rescan_required,
            recompress_shares_required,
            user_profile_required,
            private_room_required,
            completion_required,
            search_history_required,
            options
        ) = self.get_settings()

        for key, data in options.items():
            config.sections[key].update(data)

        banned_page = self.pages.get("banned-users")
        ignored_page = self.pages.get("ignored-users")

        if banned_page is not None:
            for username in banned_page.added_users:
                core.network_filter.ban_user(username)

            for username, ip_address in banned_page.added_ips:
                core.network_filter.ban_user_ip(username, ip_address)

            for username in banned_page.removed_users:
                core.network_filter.unban_user(username)

            for username, ip_address in banned_page.removed_ips:
                core.network_filter.unban_user_ip(username, ip_address)

            banned_page.clear_changes()

        if ignored_page is not None:
            for username in ignored_page.added_users:
                core.network_filter.ignore_user(username)

            for username, ip_address in ignored_page.added_ips:
                core.network_filter.ignore_user_ip(username, ip_address)

            for username in ignored_page.removed_users:
                core.network_filter.unignore_user(username)

            for username, ip_address in ignored_page.removed_ips:
                core.network_filter.unignore_user_ip(username, ip_address)

            ignored_page.clear_changes()

        if reconnect_required:
            core.reconnect()

        if portmap_required == "add":
            core.portmapper.add_port_mapping()

        elif portmap_required == "remove":
            core.portmapper.remove_port_mapping()

        if user_profile_required:
            core.userinfo.show_user(refresh=True, switch_page=False)

        if private_room_required:
            active = config.sections["server"]["private_chatrooms"]
            self.application.window.chatrooms.room_list.toggle_accept_private_room(active)

        if completion_required:
            core.chatrooms.update_completions()
            core.privatechat.update_completions()

        if search_history_required:
            self.application.window.search.populate_search_history()

        if recompress_shares_required and not rescan_required:
            core.shares.rescan_shares(init=True, rescan=False)

        # Dark mode
        dark_mode_state = config.sections["ui"]["dark_mode"]
        set_dark_mode(dark_mode_state)

        # Header bar
        header_bar_state = config.sections["ui"]["header_bar"]
        self.application.window.set_use_header_bar(header_bar_state)

        # Icons
        load_custom_icons(update=True)

        # Fonts and colors
        update_custom_css()

        # Chats
        self.application.window.chatrooms.update_widgets()
        self.application.window.privatechat.update_widgets()

        # Buddies
        self.application.window.buddies.set_buddy_list_position()

        # Transfers
        core.downloads.update_transfer_limits()
        core.downloads.update_download_filters()
        core.uploads.update_transfer_limits()

        # Logging
        log.update_folder_paths()

        # Tray icon
        if not config.sections["ui"]["trayicon"]:
            self.application.tray_icon.unload(is_shutdown=False)
        else:
            self.application.tray_icon.load()

        # Main notebook
        self.application.window.set_tab_positions()
        self.application.window.set_main_tabs_visibility()

        for tab in self.application.window.tabs.values():
            self.application.window.set_tab_expand(tab.page)

        # Other notebooks
        for notebook in (self.application.window.chatrooms, self.application.window.privatechat,
                         self.application.window.userinfo, self.application.window.userbrowse,
                         self.application.window.search):
            notebook.set_tab_closers()

        # Update configuration
        config.write_configuration()

        if not settings_closed:
            return

        self.close()

        if not config.sections["ui"]["trayicon"]:
            self.application.window.present()

        if rescan_required:
            core.shares.rescan_shares()

        if config.need_config():
            core.setup()

    @staticmethod
    def on_back_up_config_response(selected, _data):

        file_path = next(iter(selected), None)

        if file_path:
            config.write_config_backup(file_path)

    def on_back_up_config(self, *_args):

        current_date_time = time.strftime("%Y-%m-%d_%H-%M-%S")

        FileChooserSave(
            parent=self,
            callback=self.on_back_up_config_response,
            initial_folder=os.path.dirname(config.config_file_path),
            initial_file=f"config_backup_{current_date_time}.tar.bz2",
            title=_("Pick a File Name for Config Backup")
        ).present()

    def on_toggle_label_pressed(self, _controller, _num_p, _pos_x, _pos_y, toggle):
        toggle.emit("activate")

    def on_widget_scroll_event(self, _widget, event):
        """Prevent scrolling in GtkSpinButton and pass scroll event to container (GTK 3)"""

        self.content.event(event)
        return True

    def on_widget_scroll(self, _controller, _scroll_x, scroll_y):
        """Prevent scrolling in GtkSpinButton and emulate scrolling in the container (GTK 4)"""

        adjustment = self.content.get_vadjustment()
        value = adjustment.get_value()

        if scroll_y < 0:
            value -= adjustment.get_step_increment()
        else:
            value += adjustment.get_step_increment()

        adjustment.set_value(value)
        return True

    def on_switch_page(self, _listbox, row):

        if row is None:
            return

        page_id, page_class, _label, _icon_name = self.page_ids[row.get_index()]
        old_page = self.viewport.get_child()

        if old_page:
            if GTK_API_VERSION >= 4:
                self.viewport.set_child(None)
            else:
                self.viewport.remove(old_page)

        if page_id not in self.pages:
            self.pages[page_id] = page = page_class(self.application)
            page.set_settings()

            for obj in page.widgets:
                if isinstance(obj, Gtk.CheckButton):
                    if GTK_API_VERSION >= 4:
                        try:
                            check_button_label = list(obj)[-1]
                            check_button_label.set_wrap(True)   # pylint: disable=no-member
                        except AttributeError:
                            pass
                    else:
                        check_button_label = obj.get_child()
                        check_button_label.set_line_wrap(True)  # pylint: disable=no-member
                        obj.set_receives_default(True)

                elif isinstance(obj, Gtk.Switch):
                    switch_container = obj.get_parent()
                    switch_label = next(iter(switch_container))

                    if GTK_API_VERSION >= 4:
                        switch_label.gesture_click = Gtk.GestureClick()
                        switch_label.add_controller(switch_label.gesture_click)
                    else:
                        switch_label.set_has_window(True)
                        switch_label.gesture_click = Gtk.GestureMultiPress(widget=switch_label)

                    obj.set_receives_default(True)
                    switch_label.gesture_click.connect("released", self.on_toggle_label_pressed, obj)

                elif isinstance(obj, Gtk.SpinButton):
                    if GTK_API_VERSION >= 4:
                        scroll_controller = Gtk.EventControllerScroll(
                            flags=int(Gtk.EventControllerScrollFlags.VERTICAL)
                        )
                        scroll_controller.connect("scroll", self.on_widget_scroll)
                        obj.add_controller(scroll_controller)
                    else:
                        obj.connect("scroll-event", self.on_widget_scroll_event)

                elif (isinstance(obj, Gtk.FontButton)
                      or ((GTK_API_VERSION, GTK_MINOR_VERSION) >= (4, 10) and isinstance(obj, Gtk.FontDialogButton))):
                    if GTK_API_VERSION >= 4:
                        inner_button = next(iter(obj))
                        font_button_container = next(iter(inner_button))
                        font_button_label = next(iter(font_button_container))
                    else:
                        font_button_container = obj.get_child()
                        font_button_label = next(iter(font_button_container))

                    try:
                        font_button_label.set_ellipsize(Pango.EllipsizeMode.END)
                    except AttributeError:
                        pass

            page.container.set_margin_start(18)
            page.container.set_margin_end(18)
            page.container.set_margin_top(14)
            page.container.set_margin_bottom(18)

        if GTK_API_VERSION >= 4:
            self.viewport.set_child(self.pages[page_id].container)  # pylint: disable=no-member
        else:
            self.viewport.add(self.pages[page_id].container)        # pylint: disable=no-member

        # Scroll to the top
        self.content.get_vadjustment().set_value(0)

    def on_sidebar_tab_accelerator(self, *_args):
        """Tab - navigate to widget after preferences sidebar."""

        self.content.child_focus(Gtk.DirectionType.TAB_FORWARD)
        return True

    def on_sidebar_shift_tab_accelerator(self, *_args):
        """Shift+Tab - navigate to widget before preferences sidebar."""

        self.ok_button.grab_focus()
        return True

    def on_cancel(self, *_args):
        self.close()

    def on_apply(self, *_args):
        self.update_settings()

    def on_ok(self, *_args):
        self.update_settings(settings_closed=True)

    def on_close(self, *_args):
        self.content.get_vadjustment().set_value(0)
