# COPYRIGHT (C) 2020-2023 Nicotine+ Contributors
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
import socket
import sys
import time

from operator import itemgetter

import gi
from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Pango

from pynicotine.config import config
from pynicotine.core import core
from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.popovers.searchfilterhelp import SearchFilterHelp
from pynicotine.gtkgui.widgets.filechooser import FileChooserButton
from pynicotine.gtkgui.widgets.filechooser import FileChooserSave
from pynicotine.gtkgui.widgets.filechooser import FolderChooser
from pynicotine.gtkgui.widgets.dialogs import Dialog
from pynicotine.gtkgui.widgets.dialogs import EntryDialog
from pynicotine.gtkgui.widgets.dialogs import MessageDialog
from pynicotine.gtkgui.widgets.dialogs import PluginSettingsDialog
from pynicotine.gtkgui.widgets.textview import TextView
from pynicotine.gtkgui.widgets.theme import USER_STATUS_ICON_NAMES
from pynicotine.gtkgui.widgets.theme import add_css_class
from pynicotine.gtkgui.widgets.theme import load_custom_icons
from pynicotine.gtkgui.widgets.theme import set_dark_mode
from pynicotine.gtkgui.widgets.theme import update_custom_css
from pynicotine.gtkgui.widgets.treeview import TreeView
from pynicotine.gtkgui.widgets.ui import UserInterface
from pynicotine.i18n import LANGUAGES
from pynicotine.slskmessages import UserStatus
from pynicotine.utils import open_file_path
from pynicotine.utils import open_uri
from pynicotine.utils import unescape


PAGE_IDS = [
    ("network", _("Network"), "network-wireless-symbolic"),
    ("user-interface", _("User Interface"), "view-grid-symbolic"),
    ("shares", _("Shares"), "folder-symbolic"),
    ("downloads", _("Downloads"), "document-save-symbolic"),
    ("uploads", _("Uploads"), "emblem-shared-symbolic"),
    ("searches", _("Searches"), "system-search-symbolic"),
    ("user-profile", _("User Profile"), "avatar-default-symbolic"),
    ("chats", _("Chats"), "insert-text-symbolic"),
    ("now-playing", _("Now Playing"), "folder-music-symbolic"),
    ("logging", _("Logging"), "folder-documents-symbolic"),
    ("banned-users", _("Banned Users"), "action-unavailable-symbolic"),
    ("ignored-users", _("Ignored Users"), "microphone-sensitivity-muted-symbolic"),
    ("plugins", _("Plugins"), "list-add-symbolic"),
    ("url-handlers", _("URL Handlers"), "insert-link-symbolic")]


class NetworkPage:

    def __init__(self, application):

        ui_template = UserInterface(scope=self, path="settings/network.ui")
        (
            self.Main,  # pylint: disable=invalid-name
            self.auto_away_spinner,
            self.auto_connect_startup_toggle,
            self.auto_reply_message_entry,
            self.check_port_status_label,
            self.current_port_label,
            self.first_port_spinner,
            self.last_port_spinner,
            self.network_interface_combobox,
            self.network_interface_label,
            self.soulseek_server_entry,
            self.upnp_toggle,
            self.username_entry
        ) = ui_template.widgets

        self.application = application
        self.portmap_required = False

        self.check_port_status_label.connect("activate-link", lambda x, url: open_uri(url))

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

    def set_settings(self):

        self.application.preferences.set_widgets_data(self.options)
        unknown_label = _("Unknown")

        # Listening port status
        if core.protothread.listenport:
            url = config.portchecker_url % str(core.protothread.listenport)
            port_status_text = _("Check Port Status")

            self.current_port_label.set_markup(_("<b>%(ip)s</b>, port %(port)s") % {
                "ip": core.user_ip_address or unknown_label,
                "port": core.protothread.listenport or unknown_label
            })
            self.check_port_status_label.set_markup(f"<a href='{url}' title='{url}'>{port_status_text}</a>")
            self.check_port_status_label.set_visible(True)
        else:
            self.current_port_label.set_markup(f"<b>{unknown_label}</b>")
            self.check_port_status_label.set_visible(False)

        # Network interfaces
        if sys.platform == "win32":
            for widget in (self.network_interface_combobox, self.network_interface_label):
                widget.get_parent().set_visible(False)
        else:
            self.network_interface_combobox.remove_all()
            self.network_interface_combobox.append_text("")

            try:
                for _i, interface in socket.if_nameindex():
                    self.network_interface_combobox.append_text(interface)

            except (AttributeError, OSError):
                pass

        # Special options
        server_hostname, server_port = config.sections["server"]["server"]
        self.soulseek_server_entry.set_text(f"{server_hostname}:{server_port}")

        first_port, last_port = config.sections["server"]["portrange"]
        self.first_port_spinner.set_value(first_port)
        self.last_port_spinner.set_value(last_port)

        self.portmap_required = False

    def get_settings(self):

        self.portmap_required = False

        try:
            server_addr = self.soulseek_server_entry.get_text().split(":")
            server_addr[1] = int(server_addr[1])
            server_addr = tuple(server_addr)

        except Exception:
            server_addr = config.defaults["server"]["server"]

        first_port = self.first_port_spinner.get_value_as_int()
        last_port = self.last_port_spinner.get_value_as_int()

        if first_port > last_port:
            first_port, last_port = last_port, first_port

        return {
            "server": {
                "server": server_addr,
                "login": self.username_entry.get_text(),
                "portrange": (first_port, last_port),
                "autoaway": self.auto_away_spinner.get_value_as_int(),
                "autoreply": self.auto_reply_message_entry.get_text(),
                "interface": self.network_interface_combobox.get_active_text(),
                "upnp": self.upnp_toggle.get_active(),
                "auto_connect_startup": self.auto_connect_startup_toggle.get_active()
            }
        }

    def on_change_password_response(self, dialog, _response_id, user_status):

        password = dialog.get_entry_value()

        if user_status != core.user_status:
            MessageDialog(
                parent=self.application.preferences,
                title=_("Password Change Rejected"),
                message=("Since your login status changed, your password has not been changed. Please try again.")
            ).show()
            return

        if not password:
            self.on_change_password()
            return

        if core.user_status == UserStatus.OFFLINE:
            config.sections["server"]["passw"] = password
            config.write_configuration()
            return

        core.request_change_password(password)

    def on_change_password(self, *_args):

        if core.user_status != UserStatus.OFFLINE:
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
            callback=self.on_change_password_response,
            callback_data=core.user_status
        ).show()

    def on_toggle_upnp(self, *_args):
        self.portmap_required = self.upnp_toggle.get_active()

    def on_default_server(self, *_args):
        server_address, server_port = config.defaults["server"]["server"]
        self.soulseek_server_entry.set_text(f"{server_address}:{server_port}")


class DownloadsPage:

    def __init__(self, application):

        ui_template = UserInterface(scope=self, path="settings/downloads.ui")
        (
            self.Main,  # pylint: disable=invalid-name
            self.accept_sent_files_toggle,
            self.alt_speed_spinner,
            self.autoclear_downloads_toggle,
            self.download_double_click_combobox,
            self.download_folder_button,
            self.download_reverse_order_toggle,
            self.enable_username_subfolders_toggle,
            self.enable_filters_toggle,
            self.file_finished_command_entry,
            self.filter_list_container,
            self.filter_status_label,
            self.folder_finished_command_entry,
            self.incomplete_folder_button,
            self.received_folder_button,
            self.sent_files_permission_combobox,
            self.speed_spinner,
            self.use_alt_speed_limit_radio,
            self.use_speed_limit_radio,
            self.use_unlimited_speed_radio
        ) = ui_template.widgets

        self.application = application

        self.download_folder_button = FileChooserButton(
            self.download_folder_button, parent=application.preferences, chooser_type="folder"
        )
        self.incomplete_folder_button = FileChooserButton(
            self.incomplete_folder_button, parent=application.preferences, chooser_type="folder"
        )
        self.received_folder_button = FileChooserButton(
            self.received_folder_button, parent=application.preferences, chooser_type="folder"
        )

        self.filter_list_view = TreeView(
            application.window, parent=self.filter_list_container, multi_select=True,
            activate_row_callback=self.on_edit_filter,
            columns={
                "filter": {
                    "column_type": "text",
                    "title": _("Filter"),
                    "width": 150,
                    "expand_column": True,
                    "default_sort_column": "ascending"
                },
                "escaped": {
                    "column_type": "toggle",
                    "title": _("Escaped"),
                    "width": 0,
                    "toggle_callback": self.on_toggle_escaped
                }
            }
        )

        self.options = {
            "transfers": {
                "autoclear_downloads": self.autoclear_downloads_toggle,
                "reverseorder": self.download_reverse_order_toggle,
                "remotedownloads": self.accept_sent_files_toggle,
                "uploadallowed": self.sent_files_permission_combobox,
                "incompletedir": self.incomplete_folder_button,
                "downloaddir": self.download_folder_button,
                "uploaddir": self.received_folder_button,
                "downloadfilters": self.filter_list_view,
                "enablefilters": self.enable_filters_toggle,
                "downloadlimit": self.speed_spinner,
                "downloadlimitalt": self.alt_speed_spinner,
                "usernamesubfolders": self.enable_username_subfolders_toggle,
                "afterfinish": self.file_finished_command_entry,
                "afterfolder": self.folder_finished_command_entry,
                "download_doubleclick": self.download_double_click_combobox
            }
        }

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

    def get_settings(self):

        if self.use_speed_limit_radio.get_active():
            use_speed_limit = "primary"

        elif self.use_alt_speed_limit_radio.get_active():
            use_speed_limit = "alternative"

        else:
            use_speed_limit = "unlimited"

        download_filters = []

        for dfilter, iterator in self.filter_list_view.iterators.items():
            escaped = self.filter_list_view.get_row_value(iterator, "escaped")
            download_filters.append([dfilter, int(escaped)])

        download_filters.sort()

        return {
            "transfers": {
                "autoclear_downloads": self.autoclear_downloads_toggle.get_active(),
                "reverseorder": self.download_reverse_order_toggle.get_active(),
                "remotedownloads": self.accept_sent_files_toggle.get_active(),
                "uploadallowed": self.sent_files_permission_combobox.get_active(),
                "incompletedir": self.incomplete_folder_button.get_path(),
                "downloaddir": self.download_folder_button.get_path(),
                "uploaddir": self.received_folder_button.get_path(),
                "downloadfilters": download_filters,
                "enablefilters": self.enable_filters_toggle.get_active(),
                "use_download_speed_limit": use_speed_limit,
                "downloadlimit": self.speed_spinner.get_value_as_int(),
                "downloadlimitalt": self.alt_speed_spinner.get_value_as_int(),
                "usernamesubfolders": self.enable_username_subfolders_toggle.get_active(),
                "afterfinish": self.file_finished_command_entry.get_text(),
                "afterfolder": self.folder_finished_command_entry.get_text(),
                "download_doubleclick": self.download_double_click_combobox.get_active()
            }
        }

    def on_toggle_escaped(self, list_view, iterator):

        value = list_view.get_row_value(iterator, "escaped")
        list_view.set_row_value(iterator, "escaped", not value)

        self.on_verify_filter()

    def on_add_filter_response(self, dialog, _response_id, _data):

        dfilter = dialog.get_entry_value()
        escaped = dialog.get_option_value()

        iterator = self.filter_list_view.iterators.get(dfilter)

        if iterator is not None:
            self.filter_list_view.set_row_value(iterator, "filter", dfilter)
            self.filter_list_view.set_row_value(iterator, "escaped", escaped)
        else:
            self.filter_list_view.add_row([dfilter, escaped])

        self.on_verify_filter()

    def on_add_filter(self, *_args):

        EntryDialog(
            parent=self.application.preferences,
            title=_("Add Download Filter"),
            message=_("Enter a new download filter:"),
            callback=self.on_add_filter_response,
            option_value=True,
            option_label=_("Escape filter"),
            droplist=self.filter_list_view.iterators
        ).show()

    def on_edit_filter_response(self, dialog, _response_id, iterator):

        new_dfilter = dialog.get_entry_value()
        escaped = dialog.get_option_value()

        if new_dfilter in self.filter_list_view.iterators:
            self.filter_list_view.set_row_value(iterator, "filter", new_dfilter)
            self.filter_list_view.set_row_value(iterator, "escaped", escaped)
        else:
            self.filter_list_view.remove_row(iterator)
            self.filter_list_view.add_row([new_dfilter, escaped])

        self.on_verify_filter()

    def on_edit_filter(self, *_args):

        for iterator in self.filter_list_view.get_selected_rows():
            dfilter = self.filter_list_view.get_row_value(iterator, "filter")
            escaped = self.filter_list_view.get_row_value(iterator, "escaped")

            EntryDialog(
                parent=self.application.preferences,
                title=_("Edit Download Filter"),
                message=_("Modify the following download filter:"),
                callback=self.on_edit_filter_response,
                callback_data=iterator,
                default=dfilter,
                option_value=escaped,
                option_label=_("Escape filter")
            ).show()
            return

    def on_remove_filter(self, *_args):

        for iterator in reversed(self.filter_list_view.get_selected_rows()):
            self.filter_list_view.remove_row(iterator)

        self.on_verify_filter()

    def on_default_filters(self, *_args):

        self.filter_list_view.clear()

        for filter_row in config.defaults["transfers"]["downloadfilters"]:
            self.filter_list_view.add_row(filter_row, select_row=False)

        self.on_verify_filter()

    def on_verify_filter(self, *_args):

        failed = {}
        outfilter = "(\\\\("

        for dfilter, iterator in self.filter_list_view.iterators.items():
            dfilter = self.filter_list_view.get_row_value(iterator, "filter")
            escaped = self.filter_list_view.get_row_value(iterator, "escaped")

            if escaped:
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

    def __init__(self, application):

        ui_template = UserInterface(scope=self, path="settings/shares.ui")
        (
            self.Main,  # pylint: disable=invalid-name
            self.buddy_shares_trusted_only_toggle,
            self.rescan_on_startup_toggle,
            self.shares_list_container
        ) = ui_template.widgets

        self.application = application

        self.rescan_required = False
        self.shared_folders = []
        self.buddy_shared_folders = []

        self.shares_list_view = TreeView(
            application.window, parent=self.shares_list_container, multi_select=True,
            activate_row_callback=self.on_edit_shared_folder,
            columns={
                "virtual_name": {
                    "column_type": "text",
                    "title": _("Virtual Folder"),
                    "width": 65,
                    "expand_column": True,
                    "default_sort_column": "ascending"
                },
                "folder": {
                    "column_type": "text",
                    "title": _("Folder"),
                    "width": 150,
                    "expand_column": True
                },
                "buddy_only": {
                    "column_type": "toggle",
                    "title": _("Buddy-only"),
                    "width": 0,
                    "toggle_callback": self.on_toggle_folder_buddy_only
                }
            }
        )

        self.options = {
            "transfers": {
                "rescanonstartup": self.rescan_on_startup_toggle,
                "buddysharestrustedonly": self.buddy_shares_trusted_only_toggle
            }
        }

    def set_settings(self):

        self.shares_list_view.clear()

        self.application.preferences.set_widgets_data(self.options)

        self.shared_folders = config.sections["transfers"]["shared"][:]
        self.buddy_shared_folders = config.sections["transfers"]["buddyshared"][:]

        for virtual_name, folder_path, *_unused in self.buddy_shared_folders:
            is_buddy_only = True
            self.shares_list_view.add_row([str(virtual_name), str(folder_path), is_buddy_only], select_row=False)

        for virtual_name, folder_path, *_unused in self.shared_folders:
            is_buddy_only = False
            self.shares_list_view.add_row([str(virtual_name), str(folder_path), is_buddy_only], select_row=False)

        self.rescan_required = False

    def get_settings(self):

        return {
            "transfers": {
                "shared": self.shared_folders[:],
                "buddyshared": self.buddy_shared_folders[:],
                "rescanonstartup": self.rescan_on_startup_toggle.get_active(),
                "buddysharestrustedonly": self.buddy_shares_trusted_only_toggle.get_active()
            }
        }

    def _set_shared_folder_buddy_only(self, iterator, is_buddy_only):

        if is_buddy_only == self.shares_list_view.get_row_value(iterator, "buddy_only"):
            return

        self.rescan_required = True

        virtual_name = self.shares_list_view.get_row_value(iterator, "virtual_name")
        folder_path = self.shares_list_view.get_row_value(iterator, "folder")
        mapping = (virtual_name, folder_path)

        self.shares_list_view.set_row_value(iterator, "buddy_only", is_buddy_only)

        if is_buddy_only:
            self.shared_folders.remove(mapping)
            self.buddy_shared_folders.append(mapping)
            return

        self.buddy_shared_folders.remove(mapping)
        self.shared_folders.append(mapping)

    def on_add_shared_folder_selected(self, selected, _data):

        for folder_path in selected:
            if folder_path is None:
                continue

            if folder_path in (x[1] for x in self.shared_folders + self.buddy_shared_folders):
                continue

            self.rescan_required = True

            virtual_name = core.shares.get_normalized_virtual_name(
                os.path.basename(os.path.normpath(folder_path)),
                shared_folders=(self.shared_folders + self.buddy_shared_folders)
            )
            mapping = (virtual_name, folder_path)
            is_buddy_only = False

            self.shares_list_view.add_row([virtual_name, folder_path, is_buddy_only])
            self.shared_folders.append(mapping)

    def on_add_shared_folder(self, *_args):

        FolderChooser(
            parent=self.application.preferences,
            callback=self.on_add_shared_folder_selected,
            title=_("Add a Shared Folder"),
            select_multiple=True
        ).show()

    def on_edit_shared_folder_response(self, dialog, _response_id, iterator):

        virtual_name = dialog.get_entry_value()
        is_buddy_only = dialog.get_option_value()

        if not virtual_name:
            return

        self.rescan_required = True

        virtual_name = core.shares.get_normalized_virtual_name(
            virtual_name, shared_folders=(self.shared_folders + self.buddy_shared_folders)
        )
        old_virtual_name = self.shares_list_view.get_row_value(iterator, "virtual_name")
        folder_path = self.shares_list_view.get_row_value(iterator, "folder")

        old_mapping = (old_virtual_name, folder_path)
        new_mapping = (virtual_name, folder_path)

        if old_mapping in self.buddy_shared_folders:
            shared_folders = self.buddy_shared_folders
        else:
            shared_folders = self.shared_folders

        shared_folders.remove(old_mapping)
        shared_folders.append(new_mapping)

        self.shares_list_view.set_row_value(iterator, "virtual_name", virtual_name)
        self._set_shared_folder_buddy_only(iterator, is_buddy_only)

    def on_edit_shared_folder(self, *_args):

        for iterator in self.shares_list_view.get_selected_rows():
            virtual_name = self.shares_list_view.get_row_value(iterator, "virtual_name")
            folder_path = self.shares_list_view.get_row_value(iterator, "folder")
            is_buddy_only = self.shares_list_view.get_row_value(iterator, "buddy_only")

            EntryDialog(
                parent=self.application.preferences,
                title=_("Edit Shared Folder"),
                message=_("Enter new virtual name for '%(dir)s':") % {"dir": folder_path},
                default=virtual_name,
                option_value=is_buddy_only,
                option_label=_("Share with buddies only"),
                callback=self.on_edit_shared_folder_response,
                callback_data=iterator
            ).show()
            return

    def on_toggle_folder_buddy_only(self, list_view, iterator):
        self._set_shared_folder_buddy_only(iterator, is_buddy_only=not list_view.get_row_value(iterator, "buddy_only"))

    def on_remove_shared_folder(self, *_args):

        iterators = reversed(self.shares_list_view.get_selected_rows())

        for iterator in iterators:
            virtual_name = self.shares_list_view.get_row_value(iterator, "virtual_name")
            folder_path = self.shares_list_view.get_row_value(iterator, "folder")
            mapping = (virtual_name, folder_path)

            if mapping in self.buddy_shared_folders:
                self.buddy_shared_folders.remove(mapping)
            else:
                self.shared_folders.remove(mapping)

            self.shares_list_view.remove_row(iterator)

        if iterators:
            self.rescan_required = True


class UploadsPage:

    def __init__(self, application):

        ui_template = UserInterface(scope=self, path="settings/uploads.ui")

        # pylint: disable=invalid-name
        (self.AutoclearFinished, self.FirstInFirstOut, self.FriendsNoLimits,
         self.LimitSpeed, self.LimitSpeedAlternative, self.LimitTotalTransfers, self.Main, self.MaxUserFiles,
         self.MaxUserQueue, self.PreferFriends, self.QueueBandwidth, self.QueueSlots, self.QueueUseBandwidth,
         self.QueueUseSlots, self.UnlimitedUploadSpeed, self.UploadDoubleClick, self.UseAltUploadSpeedLimit,
         self.UseUploadSpeedLimit) = ui_template.widgets

        self.application = application

        self.options = {
            "transfers": {
                "autoclear_uploads": self.AutoclearFinished,
                "uploadbandwidth": self.QueueBandwidth,
                "useupslots": self.QueueUseSlots,
                "uploadslots": self.QueueSlots,
                "uploadlimit": self.LimitSpeed,
                "uploadlimitalt": self.LimitSpeedAlternative,
                "fifoqueue": self.FirstInFirstOut,
                "limitby": self.LimitTotalTransfers,
                "queuelimit": self.MaxUserQueue,
                "filelimit": self.MaxUserFiles,
                "friendsnolimits": self.FriendsNoLimits,
                "preferfriends": self.PreferFriends,
                "upload_doubleclick": self.UploadDoubleClick
            }
        }

    def set_settings(self):

        self.application.preferences.set_widgets_data(self.options)

        use_speed_limit = config.sections["transfers"]["use_upload_speed_limit"]

        if use_speed_limit == "primary":
            self.UseUploadSpeedLimit.set_active(True)

        elif use_speed_limit == "alternative":
            self.UseAltUploadSpeedLimit.set_active(True)

        else:
            self.UnlimitedUploadSpeed.set_active(True)

    def get_settings(self):

        if self.UseUploadSpeedLimit.get_active():
            use_speed_limit = "primary"

        elif self.UseAltUploadSpeedLimit.get_active():
            use_speed_limit = "alternative"

        else:
            use_speed_limit = "unlimited"

        return {
            "transfers": {
                "autoclear_uploads": self.AutoclearFinished.get_active(),
                "uploadbandwidth": self.QueueBandwidth.get_value_as_int(),
                "useupslots": self.QueueUseSlots.get_active(),
                "uploadslots": self.QueueSlots.get_value_as_int(),
                "use_upload_speed_limit": use_speed_limit,
                "uploadlimit": self.LimitSpeed.get_value_as_int(),
                "uploadlimitalt": self.LimitSpeedAlternative.get_value_as_int(),
                "fifoqueue": bool(self.FirstInFirstOut.get_active()),
                "limitby": self.LimitTotalTransfers.get_active(),
                "queuelimit": self.MaxUserQueue.get_value_as_int(),
                "filelimit": self.MaxUserFiles.get_value_as_int(),
                "friendsnolimits": self.FriendsNoLimits.get_active(),
                "preferfriends": self.PreferFriends.get_active(),
                "upload_doubleclick": self.UploadDoubleClick.get_active()
            }
        }


class UserProfilePage:

    def __init__(self, application):

        ui_template = UserInterface(scope=self, path="settings/userinfo.ui")
        (
            self.Main,  # pylint: disable=invalid-name
            self.description_view_container,
            self.select_picture_button
        ) = ui_template.widgets

        self.application = application
        self.description_view = TextView(self.description_view_container, parse_urls=False)
        self.select_picture_button = FileChooserButton(
            self.select_picture_button, parent=application.preferences, chooser_type="image")

        self.options = {
            "userinfo": {
                "descr": self.description_view,
                "pic": self.select_picture_button
            }
        }

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

        ui_template = UserInterface(scope=self, path="settings/ignore.ui")
        (
            self.Main,  # pylint: disable=invalid-name
            self.ignored_ips_container,
            self.ignored_users_container
        ) = ui_template.widgets

        self.application = application

        self.ignored_users = []
        self.ignored_users_list_view = TreeView(
            application.window, parent=self.ignored_users_container, multi_select=True,
            columns={
                "username": {
                    "column_type": "text",
                    "title": _("Username"),
                    "default_sort_column": "ascending"
                }
            }
        )

        self.ignored_ips = {}
        self.ignored_ips_list_view = TreeView(
            application.window, parent=self.ignored_ips_container, multi_select=True,
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
                    "default_sort_column": "ascending"
                }
            }
        )

        self.options = {
            "server": {
                "ignorelist": self.ignored_users_list_view,
                "ipignorelist": self.ignored_ips_list_view
            }
        }

    def set_settings(self):

        self.ignored_users_list_view.clear()
        self.ignored_ips_list_view.clear()
        self.ignored_users.clear()
        self.ignored_ips.clear()

        self.application.preferences.set_widgets_data(self.options)

        self.ignored_users = config.sections["server"]["ignorelist"][:]
        self.ignored_ips = config.sections["server"]["ipignorelist"].copy()

    def get_settings(self):
        return {
            "server": {
                "ignorelist": self.ignored_users[:],
                "ipignorelist": self.ignored_ips.copy()
            }
        }

    def on_add_ignored_user_response(self, dialog, _response_id, _data):

        user = dialog.get_entry_value()

        if user and user not in self.ignored_users:
            self.ignored_users.append(user)
            self.ignored_users_list_view.add_row([str(user)])

    def on_add_ignored_user(self, *_args):

        EntryDialog(
            parent=self.application.preferences,
            title=_("Ignore User"),
            message=_("Enter the name of the user you want to ignore:"),
            callback=self.on_add_ignored_user_response
        ).show()

    def on_remove_ignored_user(self, *_args):

        for iterator in reversed(self.ignored_users_list_view.get_selected_rows()):
            user = self.ignored_users_list_view.get_row_value(iterator, "username")

            self.ignored_users_list_view.remove_row(iterator)
            self.ignored_users.remove(user)

    def on_add_ignored_ip_response(self, dialog, _response_id, _data):

        ip_address = dialog.get_entry_value()

        if not core.network_filter.is_ip_address(ip_address):
            return

        if ip_address not in self.ignored_ips:
            user = core.network_filter.get_online_username(ip_address) or ""
            self.ignored_ips[ip_address] = user
            self.ignored_ips_list_view.add_row([ip_address, user])

    def on_add_ignored_ip(self, *_args):

        EntryDialog(
            parent=self.application.preferences,
            title=_("Ignore IP Address"),
            message=_("Enter an IP address you want to ignore:") + " " + _("* is a wildcard"),
            callback=self.on_add_ignored_ip_response
        ).show()

    def on_remove_ignored_ip(self, *_args):

        for iterator in reversed(self.ignored_ips_list_view.get_selected_rows()):
            ip_address = self.ignored_ips_list_view.get_row_value(iterator, "ip_address")

            self.ignored_ips_list_view.remove_row(iterator)
            del self.ignored_ips[ip_address]


class BannedUsersPage:

    def __init__(self, application):

        ui_template = UserInterface(scope=self, path="settings/ban.ui")
        (
            self.Main,  # pylint: disable=invalid-name
            self.ban_message_entry,
            self.ban_message_toggle,
            self.banned_ips_container,
            self.banned_users_container,
            self.geo_block_country_entry,
            self.geo_block_message_entry,
            self.geo_block_message_toggle,
            self.geo_block_toggle
        ) = ui_template.widgets

        self.application = application
        self.ip_ban_required = False

        self.banned_users = []
        self.banned_users_list_view = TreeView(
            application.window, parent=self.banned_users_container, multi_select=True,
            columns={
                "username": {
                    "column_type": "text",
                    "title": _("Username"),
                    "default_sort_column": "ascending"
                }
            }
        )

        self.banned_ips = {}
        self.banned_ips_list_view = TreeView(
            application.window, parent=self.banned_ips_container, multi_select=True,
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
                    "default_sort_column": "ascending"
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

    def set_settings(self):

        self.banned_users_list_view.clear()
        self.banned_ips_list_view.clear()
        self.banned_users.clear()
        self.banned_ips.clear()

        self.application.preferences.set_widgets_data(self.options)

        self.banned_users = config.sections["server"]["banlist"][:]
        self.banned_ips = config.sections["server"]["ipblocklist"].copy()
        self.geo_block_country_entry.set_text(config.sections["transfers"]["geoblockcc"][0])

        self.ip_ban_required = False

    def get_settings(self):

        self.ip_ban_required = False

        return {
            "server": {
                "banlist": self.banned_users[:],
                "ipblocklist": self.banned_ips.copy()
            },
            "transfers": {
                "usecustomban": self.ban_message_toggle.get_active(),
                "customban": self.ban_message_entry.get_text(),
                "geoblock": self.geo_block_toggle.get_active(),
                "geoblockcc": [self.geo_block_country_entry.get_text().upper()],
                "usecustomgeoblock": self.geo_block_message_toggle.get_active(),
                "customgeoblock": self.geo_block_message_entry.get_text()
            }
        }

    def on_add_banned_user_response(self, dialog, _response_id, _data):

        user = dialog.get_entry_value()

        if user and user not in self.banned_users:
            self.banned_users.append(user)
            self.banned_users_list_view.add_row([user])

    def on_add_banned_user(self, *_args):

        EntryDialog(
            parent=self.application.preferences,
            title=_("Ban User"),
            message=_("Enter the name of the user you want to ban:"),
            callback=self.on_add_banned_user_response
        ).show()

    def on_remove_banned_user(self, *_args):

        for iterator in reversed(self.banned_users_list_view.get_selected_rows()):
            user = self.banned_users_list_view.get_row_value(iterator, "username")

            self.banned_users_list_view.remove_row(iterator)
            self.banned_users.remove(user)

    def on_add_banned_ip_response(self, dialog, _response_id, _data):

        ip_address = dialog.get_entry_value()

        if not core.network_filter.is_ip_address(ip_address):
            return

        if ip_address not in self.banned_ips:
            user = core.network_filter.get_online_username(ip_address) or ""
            self.banned_ips[ip_address] = user
            self.banned_ips_list_view.add_row([ip_address, user])
            self.ip_ban_required = True

    def on_add_banned_ip(self, *_args):

        EntryDialog(
            parent=self.application.preferences,
            title=_("Ban IP Address"),
            message=_("Enter an IP address you want to ban:") + " " + _("* is a wildcard"),
            callback=self.on_add_banned_ip_response
        ).show()

    def on_remove_banned_ip(self, *_args):

        for iterator in reversed(self.banned_ips_list_view.get_selected_rows()):
            ip_address = self.banned_ips_list_view.get_row_value(iterator, "ip_address")

            self.banned_ips_list_view.remove_row(iterator)
            del self.banned_ips[ip_address]


class ChatsPage:

    def __init__(self, application):

        ui_template = UserInterface(scope=self, path="settings/chats.ui")

        # pylint: disable=invalid-name
        (self.CensorCheck, self.CensorList,
         self.CensorReplaceCombo, self.CharactersCompletion, self.ChatRoomFormat,
         self.CompleteBuddiesCheck, self.CompleteCommandsCheck, self.CompleteRoomNamesCheck,
         self.CompleteUsersInRoomsCheck, self.CompletionCycleCheck, self.CompletionDropdownCheck,
         self.CompletionTabCheck, self.Main, self.OneMatchCheck, self.PrivateChatFormat,
         self.PrivateLogLines, self.PrivateMessage,
         self.ReopenPrivateChats, self.ReplaceCheck, self.ReplacementList,
         self.RoomLogLines, self.RoomMessage, self.SpellCheck,
         self.TTSCommand, self.TextToSpeech, self.ctcp_toggle) = ui_template.widgets

        self.application = application
        self.completion_required = False

        self.censored_patterns = []
        self.censor_list_view = TreeView(
            application.window, parent=self.CensorList, multi_select=True, activate_row_callback=self.on_edit_censored,
            columns={
                "pattern": {
                    "column_type": "text",
                    "title": _("Pattern"),
                    "default_sort_column": "ascending"
                }
            }
        )

        self.replacements = {}
        self.replacement_list_view = TreeView(
            application.window, parent=self.ReplacementList, multi_select=True,
            activate_row_callback=self.on_edit_replacement,
            columns={
                "pattern": {
                    "column_type": "text",
                    "title": _("Pattern"),
                    "width": 100,
                    "expand_column": True,
                    "default_sort_column": "ascending"
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
                "ctcpmsgs": None  # Special case in set_settings
            },
            "logging": {
                "readroomlines": self.RoomLogLines,
                "readprivatelines": self.PrivateLogLines,
                "rooms_timestamp": self.ChatRoomFormat,
                "private_timestamp": self.PrivateChatFormat
            },
            "privatechat": {
                "store": self.ReopenPrivateChats
            },
            "words": {
                "tab": self.CompletionTabCheck,
                "cycle": self.CompletionCycleCheck,
                "dropdown": self.CompletionDropdownCheck,
                "characters": self.CharactersCompletion,
                "roomnames": self.CompleteRoomNamesCheck,
                "buddies": self.CompleteBuddiesCheck,
                "roomusers": self.CompleteUsersInRoomsCheck,
                "commands": self.CompleteCommandsCheck,
                "onematch": self.OneMatchCheck,
                "censored": self.censor_list_view,
                "censorwords": self.CensorCheck,
                "censorfill": self.CensorReplaceCombo,
                "autoreplaced": self.replacement_list_view,
                "replacewords": self.ReplaceCheck
            },
            "ui": {
                "spellcheck": self.SpellCheck,
                "speechenabled": self.TextToSpeech,
                "speechcommand": self.TTSCommand,
                "speechrooms": self.RoomMessage,
                "speechprivate": self.PrivateMessage
            }
        }

    def set_settings(self):

        self.censor_list_view.clear()
        self.replacement_list_view.clear()
        self.censored_patterns.clear()
        self.replacements.clear()

        self.application.preferences.set_widgets_data(self.options)

        try:
            gi.require_version("Gspell", "1")
            from gi.repository import Gspell  # noqa: F401; pylint:disable=unused-import

        except (ImportError, ValueError):
            self.SpellCheck.set_visible(False)

        self.ctcp_toggle.set_active(not config.sections["server"]["ctcpmsgs"])

        self.censored_patterns = config.sections["words"]["censored"][:]
        self.replacements = config.sections["words"]["autoreplaced"].copy()

        self.completion_required = False

    def get_settings(self):

        self.completion_required = False

        return {
            "server": {
                "ctcpmsgs": not self.ctcp_toggle.get_active()
            },
            "logging": {
                "readroomlines": self.RoomLogLines.get_value_as_int(),
                "readprivatelines": self.PrivateLogLines.get_value_as_int(),
                "private_timestamp": self.PrivateChatFormat.get_text(),
                "rooms_timestamp": self.ChatRoomFormat.get_text()
            },
            "privatechat": {
                "store": self.ReopenPrivateChats.get_active()
            },
            "words": {
                "tab": self.CompletionTabCheck.get_active(),
                "cycle": self.CompletionCycleCheck.get_active(),
                "dropdown": self.CompletionDropdownCheck.get_active(),
                "characters": self.CharactersCompletion.get_value_as_int(),
                "roomnames": self.CompleteRoomNamesCheck.get_active(),
                "buddies": self.CompleteBuddiesCheck.get_active(),
                "roomusers": self.CompleteUsersInRoomsCheck.get_active(),
                "commands": self.CompleteCommandsCheck.get_active(),
                "onematch": self.OneMatchCheck.get_active(),
                "censored": self.censored_patterns[:],
                "censorwords": self.CensorCheck.get_active(),
                "censorfill": self.CensorReplaceCombo.get_active_id(),
                "autoreplaced": self.replacements.copy(),
                "replacewords": self.ReplaceCheck.get_active()
            },
            "ui": {
                "spellcheck": self.SpellCheck.get_active(),
                "speechenabled": self.TextToSpeech.get_active(),
                "speechcommand": self.TTSCommand.get_active_text(),
                "speechrooms": self.RoomMessage.get_text(),
                "speechprivate": self.PrivateMessage.get_text()
            }
        }

    def on_completion_changed(self, *_args):
        self.completion_required = True

    def on_default_private(self, *_args):
        self.PrivateMessage.set_text(config.defaults["ui"]["speechprivate"])

    def on_default_rooms(self, *_args):
        self.RoomMessage.set_text(config.defaults["ui"]["speechrooms"])

    def on_room_default_timestamp(self, *_args):
        self.ChatRoomFormat.set_text(config.defaults["logging"]["rooms_timestamp"])

    def on_private_default_timestamp(self, *_args):
        self.PrivateChatFormat.set_text(config.defaults["logging"]["private_timestamp"])

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
            callback=self.on_add_censored_response
        ).show()

    def on_edit_censored_response(self, dialog, _response_id, iterator):

        pattern = dialog.get_entry_value()

        if not pattern:
            return

        old_pattern = self.censor_list_view.get_row_value(iterator, "pattern")
        self.censored_patterns.remove(old_pattern)

        self.censor_list_view.set_row_value(iterator, "pattern", pattern)
        self.censored_patterns.append(pattern)

    def on_edit_censored(self, *_args):

        for iterator in self.censor_list_view.get_selected_rows():
            pattern = self.censor_list_view.get_row_value(iterator, "pattern")

            EntryDialog(
                parent=self.application.preferences,
                title=_("Edit Censored Pattern"),
                message=_("Enter a pattern you want to censor. Add spaces around the pattern if you don't "
                          "want to match strings inside words (may fail at the beginning and end of lines)."),
                callback=self.on_edit_censored_response,
                callback_data=iterator,
                default=pattern
            ).show()
            return

    def on_remove_censored(self, *_args):

        for iterator in reversed(self.censor_list_view.get_selected_rows()):
            censor = self.censor_list_view.get_row_value(iterator, "pattern")

            self.censor_list_view.remove_row(iterator)
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
            message=_("Enter a text pattern and what to replace it with"),
            callback=self.on_add_replacement_response,
            use_second_entry=True
        ).show()

    def on_edit_replacement_response(self, dialog, _response_id, iterator):

        pattern = dialog.get_entry_value()
        replacement = dialog.get_second_entry_value()

        if not pattern or not replacement:
            return

        old_pattern = self.replacement_list_view.get_row_value(iterator, "pattern")
        del self.replacements[old_pattern]

        self.replacements[pattern] = replacement
        self.replacement_list_view.set_row_value(iterator, "pattern", pattern)
        self.replacement_list_view.set_row_value(iterator, "replacement", replacement)

    def on_edit_replacement(self, *_args):

        for iterator in self.replacement_list_view.get_selected_rows():
            pattern = self.replacement_list_view.get_row_value(iterator, "pattern")
            replacement = self.replacement_list_view.get_row_value(iterator, "replacement")

            EntryDialog(
                parent=self.application.preferences,
                title=_("Edit Replacement"),
                message=_("Enter a text pattern and what to replace it with:"),
                callback=self.on_edit_replacement_response,
                callback_data=iterator,
                use_second_entry=True,
                default=pattern,
                second_default=replacement
            ).show()
            return

    def on_remove_replacement(self, *_args):

        for iterator in reversed(self.replacement_list_view.get_selected_rows()):
            replacement = self.replacement_list_view.get_row_value(iterator, "pattern")

            self.replacement_list_view.remove_row(iterator)
            del self.replacements[replacement]


class UserInterfacePage:

    def __init__(self, application):

        ui_template = UserInterface(scope=self, path="settings/userinterface.ui")

        # pylint: disable=invalid-name
        (self.ChatRoomsPosition, self.CloseAction, self.DarkMode,
         self.DefaultBrowserFont, self.DefaultChatFont, self.DefaultGlobalFont, self.DefaultListFont,
         self.DefaultSearchFont, self.DefaultTextViewFont, self.DefaultTheme, self.DefaultTransfersFont,
         self.EnableChatroomsTab, self.EnableDownloadsTab, self.EnableInterestsTab, self.EnablePrivateTab,
         self.EnableSearchTab, self.EnableUploadsTab, self.EnableUserBrowseTab, self.EnableUserInfoTab,
         self.EnableUserListTab, self.EntryAway, self.EntryBackground, self.EntryChangedTab, self.EntryCommand,
         self.EntryHighlight, self.EntryHighlightTab, self.EntryImmediate, self.EntryInput, self.EntryLocal,
         self.EntryMe, self.EntryOffline, self.EntryOnline, self.EntryQueue, self.EntryRegularTab, self.EntryRemote,
         self.EntryURL, self.ExactFileSizes, self.IconView, self.Language, self.Main, self.MainPosition,
         self.NotificationPopupChatroom, self.NotificationPopupChatroomMention, self.NotificationPopupFile,
         self.NotificationPopupFolder, self.NotificationPopupPrivateMessage, self.NotificationPopupSound,
         self.NotificationPopupWish, self.NotificationWindowTitle, self.PickAway,
         self.PickBackground, self.PickChangedTab, self.PickCommand, self.PickHighlight, self.PickHighlightTab,
         self.PickImmediate, self.PickInput, self.PickLocal, self.PickMe, self.PickOffline, self.PickOnline,
         self.PickQueue, self.PickRegularTab, self.PickRemote, self.PickURL, self.PrivateChatPosition,
         self.ReverseFilePaths, self.SearchPosition, self.SelectBrowserFont, self.SelectChatFont, self.SelectGlobalFont,
         self.SelectListFont, self.SelectSearchFont, self.SelectTextViewFont, self.SelectTransfersFont,
         self.StartupHidden, self.TabClosers, self.TabSelectPrevious, self.ThemeDir, self.TraySettings,
         self.TrayiconCheck, self.UserBrowsePosition, self.UserInfoPosition, self.UsernameHotspots,
         self.UsernameStyle) = ui_template.widgets

        self.application = application
        self.theme_required = False

        for language_code, language_name in sorted(LANGUAGES, key=itemgetter(1)):
            self.Language.append(language_code, language_name)

        self.theme_dir = FileChooserButton(self.ThemeDir, application.preferences, "folder")

        self.tabs = {
            "search": self.EnableSearchTab,
            "downloads": self.EnableDownloadsTab,
            "uploads": self.EnableUploadsTab,
            "userbrowse": self.EnableUserBrowseTab,
            "userinfo": self.EnableUserInfoTab,
            "private": self.EnablePrivateTab,
            "userlist": self.EnableUserListTab,
            "chatrooms": self.EnableChatroomsTab,
            "interests": self.EnableInterestsTab
        }

        # Tab positions
        for combobox in (self.MainPosition, self.ChatRoomsPosition, self.PrivateChatPosition,
                         self.SearchPosition, self.UserInfoPosition, self.UserBrowsePosition):
            combobox.append("Top", _("Top"))
            combobox.append("Bottom", _("Bottom"))
            combobox.append("Left", _("Left"))
            combobox.append("Right", _("Right"))

        # Icon preview
        icon_list = [
            (USER_STATUS_ICON_NAMES[UserStatus.ONLINE], _("Online"), 16, ("colored-icon", "user-status")),
            (USER_STATUS_ICON_NAMES[UserStatus.AWAY], _("Away"), 16, ("colored-icon", "user-status")),
            (USER_STATUS_ICON_NAMES[UserStatus.OFFLINE], _("Offline"), 16, ("colored-icon", "user-status")),
            ("nplus-tab-changed", _("Tab Changed"), 16, ("colored-icon", "notebook-tab-changed")),
            ("nplus-tab-highlight", _("Tab Highlight"), 16, ("colored-icon", "notebook-tab-highlight")),
            (config.application_id, _("Window"), 64, ())]

        if application.tray_icon.available:
            icon_list += [
                (f"{config.application_id}-connect", _("Online (Tray)"), 16, ()),
                (f"{config.application_id}-away", _("Away (Tray)"), 16, ()),
                (f"{config.application_id}-disconnect", _("Offline (Tray)"), 16, ()),
                (f"{config.application_id}-msg", _("Message (Tray)"), 16, ())]

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

            self.IconView.insert(box, -1)

        self.options = {
            "notifications": {
                "notification_window_title": self.NotificationWindowTitle,
                "notification_popup_sound": self.NotificationPopupSound,
                "notification_popup_file": self.NotificationPopupFile,
                "notification_popup_folder": self.NotificationPopupFolder,
                "notification_popup_private_message": self.NotificationPopupPrivateMessage,
                "notification_popup_chatroom": self.NotificationPopupChatroom,
                "notification_popup_chatroom_mention": self.NotificationPopupChatroomMention,
                "notification_popup_wish": self.NotificationPopupWish
            },
            "ui": {
                "language": self.Language,

                "globalfont": self.SelectGlobalFont,
                "listfont": self.SelectListFont,
                "textviewfont": self.SelectTextViewFont,
                "chatfont": self.SelectChatFont,
                "searchfont": self.SelectSearchFont,
                "transfersfont": self.SelectTransfersFont,
                "browserfont": self.SelectBrowserFont,
                "usernamestyle": self.UsernameStyle,

                "reverse_file_paths": self.ReverseFilePaths,
                "exact_file_sizes": self.ExactFileSizes,

                "tabmain": self.MainPosition,
                "tabrooms": self.ChatRoomsPosition,
                "tabprivate": self.PrivateChatPosition,
                "tabsearch": self.SearchPosition,
                "tabinfo": self.UserInfoPosition,
                "tabbrowse": self.UserBrowsePosition,
                "tab_select_previous": self.TabSelectPrevious,
                "tabclosers": self.TabClosers,

                "icontheme": self.theme_dir,

                "chatlocal": self.EntryLocal,
                "chatremote": self.EntryRemote,
                "chatcommand": self.EntryCommand,
                "chatme": self.EntryMe,
                "chathilite": self.EntryHighlight,
                "textbg": self.EntryBackground,
                "inputcolor": self.EntryInput,
                "search": self.EntryImmediate,
                "searchq": self.EntryQueue,
                "useraway": self.EntryAway,
                "useronline": self.EntryOnline,
                "useroffline": self.EntryOffline,
                "usernamehotspots": self.UsernameHotspots,
                "urlcolor": self.EntryURL,
                "tab_default": self.EntryRegularTab,
                "tab_hilite": self.EntryHighlightTab,
                "tab_changed": self.EntryChangedTab,
                "dark_mode": self.DarkMode,
                "exitdialog": self.CloseAction,
                "trayicon": self.TrayiconCheck,
                "startup_hidden": self.StartupHidden
            }
        }

        self.colorsd = {
            "ui": {
                "chatlocal": self.PickLocal,
                "chatremote": self.PickRemote,
                "chatcommand": self.PickCommand,
                "chatme": self.PickMe,
                "chathilite": self.PickHighlight,
                "textbg": self.PickBackground,
                "inputcolor": self.PickInput,
                "search": self.PickImmediate,
                "searchq": self.PickQueue,
                "useraway": self.PickAway,
                "useronline": self.PickOnline,
                "useroffline": self.PickOffline,
                "urlcolor": self.PickURL,
                "tab_default": self.PickRegularTab,
                "tab_hilite": self.PickHighlightTab,
                "tab_changed": self.PickChangedTab
            }
        }

    def set_settings(self):

        self.application.preferences.set_widgets_data(self.options)
        self.theme_required = False

        self.TraySettings.set_visible(self.application.tray_icon.available)

        for page_id, enabled in config.sections["ui"]["modes_visible"].items():
            widget = self.tabs.get(page_id)

            if widget is not None:
                widget.set_active(enabled)

        self.update_color_buttons()

    def get_settings(self):

        self.theme_required = False
        enabled_tabs = {}

        for page_id, widget in self.tabs.items():
            enabled_tabs[page_id] = widget.get_active()

        return {
            "notifications": {
                "notification_window_title": self.NotificationWindowTitle.get_active(),
                "notification_popup_sound": self.NotificationPopupSound.get_active(),
                "notification_popup_file": self.NotificationPopupFile.get_active(),
                "notification_popup_folder": self.NotificationPopupFolder.get_active(),
                "notification_popup_private_message": self.NotificationPopupPrivateMessage.get_active(),
                "notification_popup_chatroom": self.NotificationPopupChatroom.get_active(),
                "notification_popup_chatroom_mention": self.NotificationPopupChatroomMention.get_active(),
                "notification_popup_wish": self.NotificationPopupWish.get_active()
            },
            "ui": {
                "language": self.Language.get_active_id(),

                "globalfont": self.SelectGlobalFont.get_font(),
                "listfont": self.SelectListFont.get_font(),
                "textviewfont": self.SelectTextViewFont.get_font(),
                "chatfont": self.SelectChatFont.get_font(),
                "searchfont": self.SelectSearchFont.get_font(),
                "transfersfont": self.SelectTransfersFont.get_font(),
                "browserfont": self.SelectBrowserFont.get_font(),
                "usernamestyle": self.UsernameStyle.get_active_id(),

                "reverse_file_paths": self.ReverseFilePaths.get_active(),
                "exact_file_sizes": self.ExactFileSizes.get_active(),

                "tabmain": self.MainPosition.get_active_id(),
                "tabrooms": self.ChatRoomsPosition.get_active_id(),
                "tabprivate": self.PrivateChatPosition.get_active_id(),
                "tabsearch": self.SearchPosition.get_active_id(),
                "tabinfo": self.UserInfoPosition.get_active_id(),
                "tabbrowse": self.UserBrowsePosition.get_active_id(),
                "modes_visible": enabled_tabs,
                "tab_select_previous": self.TabSelectPrevious.get_active(),
                "tabclosers": self.TabClosers.get_active(),

                "icontheme": self.theme_dir.get_path(),

                "chatlocal": self.EntryLocal.get_text(),
                "chatremote": self.EntryRemote.get_text(),
                "chatcommand": self.EntryCommand.get_text(),
                "chatme": self.EntryMe.get_text(),
                "chathilite": self.EntryHighlight.get_text(),
                "urlcolor": self.EntryURL.get_text(),
                "textbg": self.EntryBackground.get_text(),
                "inputcolor": self.EntryInput.get_text(),
                "search": self.EntryImmediate.get_text(),
                "searchq": self.EntryQueue.get_text(),
                "useraway": self.EntryAway.get_text(),
                "useronline": self.EntryOnline.get_text(),
                "useroffline": self.EntryOffline.get_text(),
                "usernamehotspots": self.UsernameHotspots.get_active(),
                "tab_hilite": self.EntryHighlightTab.get_text(),
                "tab_default": self.EntryRegularTab.get_text(),
                "tab_changed": self.EntryChangedTab.get_text(),
                "dark_mode": self.DarkMode.get_active(),
                "exitdialog": self.CloseAction.get_active(),
                "trayicon": self.TrayiconCheck.get_active(),
                "startup_hidden": self.StartupHidden.get_active()
            }
        }

    """ Icons """

    def on_default_theme(self, *_args):
        self.theme_dir.clear()
        self.theme_required = True

    """ Fonts """

    def on_default_font(self, widget):

        font_button = getattr(self, Gtk.Buildable.get_name(widget).replace("Default", "Select"))
        font_button.set_font("")

        self.theme_required = True

    """ Colors """

    def on_theme_changed(self, *_args):
        self.theme_required = True

    def update_color_button(self, input_config, color_id):

        for section, value in self.colorsd.items():
            if color_id in value:
                color_button = value[color_id]
                rgba = Gdk.RGBA()

                rgba.parse(input_config[section][color_id])
                color_button.set_rgba(rgba)
                break

    def update_color_buttons(self):

        for color_ids in self.colorsd.values():
            for color_id in color_ids:
                self.update_color_button(config.sections, color_id)

    def set_default_color(self, section, color_id):

        defaults = config.defaults
        widget = self.options[section][color_id]

        if isinstance(widget, Gtk.Entry):
            widget.set_text(defaults[section][color_id])

        self.update_color_button(defaults, color_id)

    def on_color_set(self, widget):

        rgba = widget.get_rgba()
        red_color = round(rgba.red * 255)
        green_color = round(rgba.green * 255)
        blue_color = round(rgba.blue * 255)
        color_hex = f"#{red_color:02X}{green_color:02X}{blue_color:02X}"

        entry = getattr(self, Gtk.Buildable.get_name(widget).replace("Pick", "Entry"))
        entry.set_text(color_hex)

    def on_default_color(self, widget, *_args):

        entry = getattr(self, Gtk.Buildable.get_name(widget))

        for section, section_options in self.options.items():
            for key, value in section_options.items():
                if value is entry:
                    self.set_default_color(section, key)
                    return

        entry.set_text("")

    def on_colors_changed(self, widget):

        if isinstance(widget, Gtk.Entry):
            rgba = Gdk.RGBA()
            rgba.parse(widget.get_text())

            color_button = getattr(self, Gtk.Buildable.get_name(widget).replace("Entry", "Pick"))
            color_button.set_rgba(rgba)

        self.theme_required = True


class LoggingPage:

    def __init__(self, application):

        ui_template = UserInterface(scope=self, path="settings/log.ui")
        (
            self.Main,  # pylint: disable=invalid-name
            self.chatroom_log_folder_button,
            self.debug_log_folder_button,
            self.log_chatroom_toggle,
            self.log_debug_toggle,
            self.log_private_chat_toggle,
            self.log_timestamp_format_entry,
            self.log_transfer_toggle,
            self.private_chat_log_folder_button,
            self.transfer_log_folder_button
        ) = ui_template.widgets

        self.application = application

        self.private_chat_log_folder_button = FileChooserButton(
            self.private_chat_log_folder_button, parent=application.preferences, chooser_type="folder"
        )
        self.chatroom_log_folder_button = FileChooserButton(
            self.chatroom_log_folder_button, parent=application.preferences, chooser_type="folder"
        )
        self.transfer_log_folder_button = FileChooserButton(
            self.transfer_log_folder_button, parent=application.preferences, chooser_type="folder"
        )
        self.debug_log_folder_button = FileChooserButton(
            self.debug_log_folder_button, parent=application.preferences, chooser_type="folder"
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

    def set_settings(self):
        self.application.preferences.set_widgets_data(self.options)

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

    def on_default_timestamp(self, *_args):
        self.log_timestamp_format_entry.set_text(config.defaults["logging"]["log_timestamp"])


class SearchesPage:

    def __init__(self, application):

        ui_template = UserInterface(scope=self, path="settings/search.ui")
        (
            self.Main,  # pylint: disable=invalid-name
            self.cleared_filter_history_icon,
            self.cleared_search_history_icon,
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
            self.remove_special_chars_toggle,
            self.repond_search_requests_toggle,
            self.show_private_results_toggle
        ) = ui_template.widgets

        self.application = application
        self.search_required = False

        self.filter_help = SearchFilterHelp(application.preferences)
        self.filter_help_button.set_popover(self.filter_help.widget)

        self.options = {
            "searches": {
                "maxresults": self.max_sent_results_spinner,
                "enablefilters": self.enable_default_filters_toggle,
                "defilter": None,
                "search_results": self.repond_search_requests_toggle,
                "max_displayed_results": self.max_displayed_results_spinner,
                "min_search_chars": self.min_search_term_length_spinner,
                "remove_special_chars": self.remove_special_chars_toggle,
                "enable_history": self.enable_search_history_toggle,
                "private_search_results": self.show_private_results_toggle
            }
        }

    def set_settings(self):

        searches = config.sections["searches"]
        self.application.preferences.set_widgets_data(self.options)
        self.search_required = False

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

        self.cleared_search_history_icon.set_visible(False)
        self.cleared_filter_history_icon.set_visible(False)

    def get_settings(self):

        self.search_required = False

        return {
            "searches": {
                "maxresults": self.max_sent_results_spinner.get_value_as_int(),
                "enablefilters": self.enable_default_filters_toggle.get_active(),
                "defilter": [
                    self.filter_include_entry.get_text(),
                    self.filter_exclude_entry.get_text(),
                    self.filter_file_size_entry.get_text(),
                    self.filter_bitrate_entry.get_text(),
                    self.filter_free_slot_toggle.get_active(),
                    self.filter_country_entry.get_text(),
                    self.filter_file_type_entry.get_text(),
                    self.filter_length_entry.get_text()
                ],
                "search_results": self.repond_search_requests_toggle.get_active(),
                "max_displayed_results": self.max_displayed_results_spinner.get_value_as_int(),
                "min_search_chars": self.min_search_term_length_spinner.get_value_as_int(),
                "remove_special_chars": self.remove_special_chars_toggle.get_active(),
                "enable_history": self.enable_search_history_toggle.get_active(),
                "private_search_results": self.show_private_results_toggle.get_active()
            }
        }

    def on_toggle_search_history(self, *_args):
        self.search_required = True

    def on_clear_search_history(self, *_args):
        self.application.window.search.clear_search_history()
        self.cleared_search_history_icon.set_visible(True)

    def on_clear_filter_history(self, *_args):
        self.application.window.search.clear_filter_history()
        self.cleared_filter_history_icon.set_visible(True)


class UrlHandlersPage:

    def __init__(self, application):

        ui_template = UserInterface(scope=self, path="settings/urlhandlers.ui")
        (
            self.Main,  # pylint: disable=invalid-name
            self.file_manager_combobox,
            self.media_player_combobox,
            self.protocol_list_container
        ) = ui_template.widgets

        self.application = application

        self.options = {
            "urls": {
                "protocols": None
            },
            "ui": {
                "filemanager": self.file_manager_combobox
            },
            "players": {
                "default": self.media_player_combobox
            }
        }

        self.default_protocols = [
            "http",
            "https",
            "ftp",
            "sftp",
            "news",
            "irc"
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
            columns={
                "protocol": {
                    "column_type": "text",
                    "title": _("Protocol"),
                    "width": 120,
                    "expand_column": True,
                    "iterator_key": True,
                    "default_sort_column": "ascending"
                },
                "command": {
                    "column_type": "text",
                    "title": _("Command"),
                    "expand_column": True
                }
            }
        )

    def set_settings(self):

        self.protocol_list_view.clear()
        self.protocols.clear()

        self.application.preferences.set_widgets_data(self.options)

        self.protocols = config.sections["urls"]["protocols"].copy()

        for protocol, command in self.protocols.items():
            if command[-1:] == "&":
                command = command[:-1].rstrip()

            self.protocol_list_view.add_row([str(protocol), str(command)], select_row=False)

    def get_settings(self):

        return {
            "urls": {
                "protocols": self.protocols.copy()
            },
            "ui": {
                "filemanager": self.file_manager_combobox.get_active_text()
            },
            "players": {
                "default": self.media_player_combobox.get_active_text()
            }
        }

    def on_add_handler_response(self, dialog, _response_id, _data):

        protocol = dialog.get_entry_value()
        command = dialog.get_second_entry_value()

        if not protocol or not command:
            return

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
            callback=self.on_add_handler_response,
            use_second_entry=True,
            droplist=self.default_protocols,
            second_droplist=self.default_commands
        ).show()

    def on_edit_handler_response(self, dialog, _response_id, iterator):

        command = dialog.get_entry_value()

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
                callback=self.on_edit_handler_response,
                callback_data=iterator,
                droplist=self.default_commands,
                default=command
            ).show()
            return

    def on_remove_handler(self, *_args):

        for iterator in reversed(self.protocol_list_view.get_selected_rows()):
            protocol = self.protocol_list_view.get_row_value(iterator, "protocol")

            self.protocol_list_view.remove_row(iterator)
            del self.protocols[protocol]

    def on_default_media_player(self, *_args):
        default_media_player = config.defaults["players"]["default"]
        self.media_player_combobox.get_child().set_text(default_media_player)

    def on_default_file_manager(self, *_args):
        default_file_manager = config.defaults["ui"]["filemanager"]
        self.file_manager_combobox.get_child().set_text(default_file_manager)


class NowPlayingPage:

    def __init__(self, application):

        ui_template = UserInterface(scope=self, path="settings/nowplaying.ui")

        # pylint: disable=invalid-name
        (self.Example, self.Legend, self.Main, self.NPCommand, self.NPFormat, self.NP_lastfm, self.NP_listenbrainz,
         self.NP_mpris, self.NP_other, self.player_input, self.test_now_playing) = ui_template.widgets

        self.application = application

        self.options = {
            "players": {
                "npothercommand": self.NPCommand
            }
        }

        self.player_replacers = []

        # Default format list
        self.default_format_list = [
            "$n",
            "$n ($f)",
            "$a - $t",
            "[$a] $t",
            "$a - $b - $t",
            "$a - $b - $t ($l/$r KBps) from $y $c"
        ]
        self.custom_format_list = []

        # Supply the information needed for the Now Playing class to return a song
        self.test_now_playing.connect(
            "clicked",
            core.now_playing.display_now_playing,
            self.set_now_playing_example,  # Callback to update the song displayed
            self.get_player,               # Callback to retrieve selected player
            self.get_command,              # Callback to retrieve command text
            self.get_format                # Callback to retrieve format text
        )

        self.NP_mpris.set_visible(sys.platform not in ("win32", "darwin"))

    def set_settings(self):

        self.application.preferences.set_widgets_data(self.options)

        # Save reference to format list for get_settings()
        self.custom_format_list = config.sections["players"]["npformatlist"]

        # Update UI with saved player
        self.set_player(config.sections["players"]["npplayer"])
        self.update_now_playing_info()

        # Add formats
        self.NPFormat.remove_all()

        for item in self.default_format_list:
            self.NPFormat.append_text(str(item))

        if self.custom_format_list:
            for item in self.custom_format_list:
                self.NPFormat.append_text(str(item))

        if config.sections["players"]["npformat"] == "":
            # If there's no default format in the config: set the first of the list
            self.NPFormat.set_active(0)
        else:
            # If there's is a default format in the config: select the right item
            for i, value in enumerate(self.NPFormat.get_model()):
                if value[0] == config.sections["players"]["npformat"]:
                    self.NPFormat.set_active(i)

    def get_player(self):

        if self.NP_lastfm.get_active():
            player = "lastfm"
        elif self.NP_mpris.get_active():
            player = "mpris"
        elif self.NP_listenbrainz.get_active():
            player = "listenbrainz"
        elif self.NP_other.get_active():
            player = "other"

        if sys.platform in ("win32", "darwin") and player == "mpris":
            player = "lastfm"

        return player

    def get_command(self):
        return self.NPCommand.get_text()

    def get_format(self):
        return self.NPFormat.get_active_text()

    def set_player(self, player):

        if sys.platform in ("win32", "darwin") and player == "mpris":
            player = "lastfm"

        if player == "lastfm":
            self.NP_lastfm.set_active(True)
        elif player == "listenbrainz":
            self.NP_listenbrainz.set_active(True)
        elif player == "other":
            self.NP_other.set_active(True)
        else:
            self.NP_mpris.set_active(True)

    def update_now_playing_info(self, *_args):

        if self.NP_lastfm.get_active():
            self.player_replacers = ["$n", "$t", "$a", "$b"]
            self.player_input.set_text(_("Username;APIKEY:"))

        elif self.NP_mpris.get_active():
            self.player_replacers = ["$n", "$p", "$a", "$b", "$t", "$y", "$c", "$r", "$k", "$l", "$f"]
            self.player_input.set_text(_("Music player (e.g. amarok, audacious, exaile); leave empty to autodetect:"))

        elif self.NP_listenbrainz.get_active():
            self.player_replacers = ["$n", "$t", "$a", "$b"]
            self.player_input.set_text(_("Username:"))

        elif self.NP_other.get_active():
            self.player_replacers = ["$n"]
            self.player_input.set_text(_("Command:"))

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

        self.Legend.set_text(legend[:-1])

    def set_now_playing_example(self, title):
        self.Example.set_text(title)

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

        ui_template = UserInterface(scope=self, path="settings/plugin.ui")
        (
            self.Main,  # pylint: disable=invalid-name
            self.enable_plugins_toggle,
            self.plugin_authors_label,
            self.plugin_description_view_container,
            self.plugin_list_container,
            self.plugin_name_label,
            self.plugin_settings_button,
            self.plugin_version_label
        ) = ui_template.widgets

        self.application = application
        self.selected_plugin = None

        self.options = {
            "plugins": {
                "enable": self.enable_plugins_toggle
            }
        }

        self.plugin_description_view = TextView(self.plugin_description_view_container, editable=False,
                                                pixels_below_lines=2)
        self.plugin_list_view = TreeView(
            application.window, parent=self.plugin_list_container, always_select=True,
            select_row_callback=self.on_select_plugin,
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
                    "default_sort_column": "ascending"
                },

                # Hidden data columns
                "plugin_id": {"data_type": str}
            }
        )

    def set_settings(self):

        self.plugin_list_view.clear()

        self.application.preferences.set_widgets_data(self.options)

        for plugin_id in sorted(core.pluginhandler.list_installed_plugins()):
            try:
                info = core.pluginhandler.get_plugin_info(plugin_id)
            except OSError:
                continue

            plugin_name = info.get("Name", plugin_id)
            enabled = (plugin_id in config.sections["plugins"]["enabled"])
            self.plugin_list_view.add_row([enabled, plugin_name, plugin_id], select_row=False)

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
        open_file_path(core.pluginhandler.user_plugin_folder, create_folder=True)

    def on_plugin_settings(self, *_args):

        if self.selected_plugin is None:
            return

        PluginSettingsDialog(
            self.application,
            plugin_id=self.selected_plugin,
            plugin_settings=core.pluginhandler.get_plugin_settings(self.selected_plugin)
        ).show()


class Preferences(Dialog):

    def __init__(self, application):

        self.application = application

        ui_template = UserInterface(scope=self, path="dialogs/preferences.ui")
        (
            self.apply_button,
            self.cancel_button,
            self.container,
            self.content,
            self.export_button,
            self.ok_button,
            self.preferences_list,
            self.viewport
        ) = ui_template.widgets

        super().__init__(
            parent=application.window,
            content_box=self.container,
            buttons_start=(self.cancel_button, self.export_button),
            buttons_end=(self.apply_button, self.ok_button),
            default_button=self.ok_button,
            close_callback=self.on_close,
            title=_("Preferences"),
            width=960,
            height=650,
            close_destroy=False,
            show_title_buttons=False
        )

        add_css_class(self.widget, "preferences-border")

        if GTK_API_VERSION == 3:
            # Scroll to focused widgets
            self.viewport.set_focus_vadjustment(self.content.get_vadjustment())

        self.pages = {}

        for _page_id, label, icon_name in PAGE_IDS:
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

    def set_active_page(self, page_id):

        if page_id is None:
            return

        for index, (n_page_id, _label, _icon_name) in enumerate(PAGE_IDS):
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

                if config.sections[section][key] is None:
                    self.clear_widget(widget)
                else:
                    self.set_widget(widget, config.sections[section][key])

    @staticmethod
    def get_widget_data(widget):

        if isinstance(widget, Gtk.SpinButton):
            if widget.get_digits() > 0:
                return widget.get_value()

            return widget.get_value_as_int()

        if isinstance(widget, Gtk.Entry):
            return widget.get_text()

        if isinstance(widget, TextView):
            return repr(widget.get_text())

        if isinstance(widget, Gtk.CheckButton):
            try:
                # Radio button
                for radio in widget.group_radios:
                    if radio.get_active():
                        return widget.group_radios.index(radio)

                return 0

            except (AttributeError, TypeError):
                # Regular check button
                return widget.get_active()

        if isinstance(widget, Gtk.ComboBoxText):
            return widget.get_active_text()

        if isinstance(widget, Gtk.FontButton):
            return widget.get_font()

        if isinstance(widget, TreeView):
            return list(widget.iterators)

        if isinstance(widget, FileChooserButton):
            return widget.get_path()

        return None

    @staticmethod
    def clear_widget(widget):

        if isinstance(widget, Gtk.SpinButton):
            widget.set_value(0)

        elif isinstance(widget, Gtk.Entry):
            widget.set_text("")

        elif isinstance(widget, TextView):
            widget.clear()

        elif isinstance(widget, Gtk.CheckButton):
            widget.set_active(0)

        elif isinstance(widget, Gtk.ComboBoxText):
            widget.get_child().set_text("")

        elif isinstance(widget, Gtk.FontButton):
            widget.set_font("")

    @staticmethod
    def set_widget(widget, value):

        if isinstance(widget, Gtk.SpinButton):
            try:
                widget.set_value(value)

            except TypeError:
                # Not a numerical value
                pass

        elif isinstance(widget, Gtk.Entry):
            if isinstance(value, (str, int)):
                widget.set_text(value)

        elif isinstance(widget, TextView):
            if isinstance(value, str):
                widget.append_line(unescape(value))

        elif isinstance(widget, Gtk.CheckButton):
            try:
                # Radio button
                if isinstance(value, int) and value < len(widget.group_radios):
                    widget.group_radios[value].set_active(True)

            except (AttributeError, TypeError):
                # Regular check button
                widget.set_active(value)

        elif isinstance(widget, Gtk.ComboBoxText):
            if isinstance(value, str):
                if widget.get_has_entry():
                    widget.get_child().set_text(value)
                else:
                    widget.set_active_id(value)

            elif isinstance(value, int):
                widget.set_active(value)

            # If an invalid value was provided, select first item
            if not widget.get_has_entry() and widget.get_active() < 0:
                widget.set_active(0)

        elif isinstance(widget, Gtk.FontButton):
            widget.set_font(value)

        elif isinstance(widget, TreeView):
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

        elif isinstance(widget, FileChooserButton):
            widget.set_path(value)

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

        try:
            portmap_required = self.pages["network"].portmap_required

        except KeyError:
            portmap_required = False

        try:
            rescan_required = self.pages["shares"].rescan_required

        except KeyError:
            rescan_required = False

        try:
            theme_required = self.pages["user-interface"].theme_required

        except KeyError:
            theme_required = False

        try:
            completion_required = self.pages["chats"].completion_required

        except KeyError:
            completion_required = False

        try:
            ip_ban_required = self.pages["banned-users"].ip_ban_required

        except KeyError:
            ip_ban_required = False

        try:
            search_required = self.pages["searches"].search_required

        except KeyError:
            search_required = False

        for page in self.pages.values():
            for key, data in page.get_settings().items():
                options[key].update(data)

        return (portmap_required, rescan_required, theme_required, completion_required,
                ip_ban_required, search_required, options)

    def update_settings(self, settings_closed=False):

        (portmap_required, rescan_required, theme_required, completion_required,
            ip_ban_required, search_required, options) = self.get_settings()

        for key, data in options.items():
            config.sections[key].update(data)

        if portmap_required:
            core.protothread.upnp.add_port_mapping()
        else:
            core.protothread.upnp.cancel_timer()

        if theme_required:
            # Dark mode
            dark_mode_state = config.sections["ui"]["dark_mode"]
            set_dark_mode(dark_mode_state)
            self.application.lookup_action("prefer-dark-mode").set_state(GLib.Variant("b", dark_mode_state))

            # Icons
            load_custom_icons(update=True)
            self.application.tray_icon.update_icon_theme()

            # Fonts and colors
            update_custom_css()

            self.application.window.chatrooms.update_tags()
            self.application.window.privatechat.update_tags()

        if completion_required:
            core.chatrooms.update_completions()
            core.privatechat.update_completions()

        if ip_ban_required:
            core.network_filter.close_banned_ip_connections()

        if search_required:
            self.application.window.search.populate_search_history()

        # Chatrooms
        self.application.window.chatrooms.toggle_chat_buttons()
        self.application.window.privatechat.toggle_chat_buttons()

        # Transfers
        core.transfers.update_download_limits()
        core.transfers.update_download_filters()
        core.transfers.update_upload_limits()
        core.transfers.check_upload_queue()

        # Tray icon
        if not config.sections["ui"]["trayicon"] and self.application.tray_icon.is_visible():
            self.application.tray_icon.set_visible(False)

        elif config.sections["ui"]["trayicon"] and not self.application.tray_icon.is_visible():
            self.application.tray_icon.load()

        # Main notebook
        self.application.window.set_tab_positions()
        self.application.window.set_main_tabs_visibility()
        self.application.window.notebook.set_tab_text_colors()

        for i in range(self.application.window.notebook.get_n_pages()):
            page = self.application.window.notebook.get_nth_page(i)
            self.application.window.set_tab_expand(page)

        # Other notebooks
        for notebook in (self.application.window.chatrooms, self.application.window.privatechat,
                         self.application.window.userinfo, self.application.window.userbrowse,
                         self.application.window.search):
            notebook.set_tab_closers()
            notebook.set_tab_text_colors()

        # Update configuration
        config.write_configuration()

        if not settings_closed:
            return

        if rescan_required:
            core.shares.rescan_shares()

        self.close()

        if not config.sections["ui"]["trayicon"]:
            self.application.window.show()

        if config.need_config():
            core.setup()

    @staticmethod
    def on_back_up_config_response(selected, _data):
        config.write_config_backup(selected)

    def on_back_up_config(self, *_args):

        current_date_time = time.strftime("%Y-%m-%d_%H-%M-%S")

        FileChooserSave(
            parent=self,
            callback=self.on_back_up_config_response,
            initial_folder=os.path.dirname(config.filename),
            initial_file=f"config_backup_{current_date_time}.tar.bz2",
            title=_("Pick a File Name for Config Backup")
        ).show()

    def on_widget_scroll_event(self, _widget, event):
        """ Prevent scrolling in GtkComboBoxText and GtkSpinButton and pass scroll event
        to container (GTK 3) """

        self.content.event(event)
        return True

    def on_widget_scroll(self, _controller, _scroll_x, scroll_y):
        """ Prevent scrolling in GtkComboBoxText and GtkSpinButton and emulate scrolling
        in the container (GTK 4) """

        adjustment = self.content.get_vadjustment()
        value = adjustment.get_value()

        if scroll_y < 0:
            value -= adjustment.get_step_increment()
        else:
            value += adjustment.get_step_increment()

        adjustment.set_value(value)
        return True

    def on_switch_page(self, _listbox, row):

        page_id, _label, _icon_name = PAGE_IDS[row.get_index()]
        old_page = self.viewport.get_child()

        if old_page:
            if GTK_API_VERSION >= 4:
                self.viewport.set_child(None)
            else:
                self.viewport.remove(old_page)

        if page_id not in self.pages:
            class_name = page_id.title().replace("-", "") + "Page"
            self.pages[page_id] = page = getattr(sys.modules[__name__], class_name)(self.application)
            page.set_settings()

            for obj in page.__dict__.values():
                if isinstance(obj, Gtk.CheckButton):
                    if GTK_API_VERSION >= 4:
                        check_button_label = obj.get_last_child()
                    else:
                        check_button_label = obj.get_child()
                        obj.set_receives_default(True)

                    try:
                        check_button_label.set_property("wrap", True)
                    except AttributeError:
                        pass

                elif isinstance(obj, (Gtk.ComboBoxText, Gtk.SpinButton)):
                    if GTK_API_VERSION >= 4:
                        scroll_controller = Gtk.EventControllerScroll(flags=Gtk.EventControllerScrollFlags.VERTICAL)
                        scroll_controller.connect("scroll", self.on_widget_scroll)
                        obj.add_controller(scroll_controller)
                    else:
                        obj.connect("scroll-event", self.on_widget_scroll_event)

                    if isinstance(obj, Gtk.ComboBoxText):
                        for cell in obj.get_cells():
                            cell.set_property("ellipsize", Pango.EllipsizeMode.END)

                elif isinstance(obj, Gtk.FontButton):
                    if GTK_API_VERSION >= 4:
                        font_button_label = obj.get_first_child().get_first_child().get_first_child()
                    else:
                        font_button_label = obj.get_child().get_children()[0]

                    try:
                        font_button_label.set_ellipsize(Pango.EllipsizeMode.END)
                    except AttributeError:
                        pass

            page.Main.set_margin_start(18)
            page.Main.set_margin_end(18)
            page.Main.set_margin_top(14)
            page.Main.set_margin_bottom(18)

        self.viewport.set_property("child", self.pages[page_id].Main)

        # Scroll to the top
        self.content.get_vadjustment().set_value(0)

    def on_cancel(self, *_args):
        self.close()

    def on_apply(self, *_args):
        self.update_settings()

    def on_ok(self, *_args):
        self.update_settings(settings_closed=True)

    def on_close(self, *_args):
        self.content.get_vadjustment().set_value(0)
