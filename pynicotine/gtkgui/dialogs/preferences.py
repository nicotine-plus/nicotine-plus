# COPYRIGHT (C) 2020-2022 Nicotine+ Contributors
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2016 Mutnick <muhing@yahoo.com>
# COPYRIGHT (C) 2008-2011 Quinox <quinox@users.sf.net>
# COPYRIGHT (C) 2008 Gallows <g4ll0ws@gmail.com>
# COPYRIGHT (C) 2006-2009 Daelstorm <daelstorm@gmail.com>
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

import gi
from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Pango

from pynicotine.config import config
from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.widgets.filechooser import FileChooserButton
from pynicotine.gtkgui.widgets.filechooser import FileChooserSave
from pynicotine.gtkgui.widgets.filechooser import FolderChooser
from pynicotine.gtkgui.widgets.dialogs import Dialog
from pynicotine.gtkgui.widgets.dialogs import EntryDialog
from pynicotine.gtkgui.widgets.dialogs import MessageDialog
from pynicotine.gtkgui.widgets.dialogs import PluginSettingsDialog
from pynicotine.gtkgui.widgets.textview import TextView
from pynicotine.gtkgui.widgets.theme import load_custom_icons
from pynicotine.gtkgui.widgets.theme import set_dark_mode
from pynicotine.gtkgui.widgets.theme import set_global_font
from pynicotine.gtkgui.widgets.theme import update_widget_visuals
from pynicotine.gtkgui.widgets.treeview import TreeView
from pynicotine.gtkgui.widgets.ui import UserInterface
from pynicotine.utils import open_file_path
from pynicotine.utils import open_uri
from pynicotine.utils import unescape


class NetworkFrame(UserInterface):

    def __init__(self, preferences):

        super().__init__("ui/settings/network.ui")

        # pylint: disable=invalid-name
        (self.AutoAway, self.AutoConnectStartup, self.AutoReply, self.CheckPortLabel,
         self.CurrentPort, self.FirstPort, self.Interface, self.InterfaceLabel, self.LastPort, self.Login, self.Main,
         self.Server, self.UPnPInterval, self.UseUPnP, self.ctcptogglebutton) = self.widgets

        self.preferences = preferences
        self.frame = preferences.frame
        self.core = preferences.core
        self.portmap_required = False

        self.options = {
            "server": {
                "server": None,
                "login": self.Login,
                "portrange": None,
                "autoaway": self.AutoAway,
                "autoreply": self.AutoReply,
                "interface": self.Interface,
                "upnp": self.UseUPnP,
                "upnp_interval": self.UPnPInterval,
                "auto_connect_startup": self.AutoConnectStartup,
                "ctcpmsgs": self.ctcptogglebutton
            }
        }

    def set_settings(self):

        self.preferences.set_widgets_data(self.options)

        server = config.sections["server"]

        if server["server"] is not None:
            self.Server.set_text("%s:%i" % (server["server"][0], server["server"][1]))

        text = _("<b>%(ip)s</b>, port %(port)s") % {
            "ip": self.core.user_ip_address or _("Unknown"),
            "port": self.core.protothread.listenport or _("Unknown")
        }
        self.CurrentPort.set_markup(text)

        url = config.portchecker_url % str(self.core.protothread.listenport)
        text = "<a href='" + url + "' title='" + url + "'>" + _("Check Port Status") + "</a>"
        self.CheckPortLabel.set_markup(text)
        self.CheckPortLabel.connect("activate-link", lambda x, url: open_uri(url))

        if server["portrange"] is not None:
            self.FirstPort.set_value(server["portrange"][0])
            self.LastPort.set_value(server["portrange"][1])

        if server["ctcpmsgs"] is not None:
            self.ctcptogglebutton.set_active(not server["ctcpmsgs"])

        self.on_toggle_upnp(self.UseUPnP)

        if sys.platform not in ("linux", "darwin"):
            for widget in (self.InterfaceLabel, self.Interface):
                widget.get_parent().hide()

            return

        self.Interface.remove_all()
        self.Interface.append_text("")

        try:
            for _i, interface in socket.if_nameindex():
                self.Interface.append_text(interface)

        except (AttributeError, OSError):
            pass

        self.portmap_required = False

    def get_settings(self):

        self.portmap_required = False

        try:
            server = self.Server.get_text().split(":")
            server[1] = int(server[1])
            server = tuple(server)

        except Exception:
            server = config.defaults["server"]["server"]

        firstport = min(self.FirstPort.get_value_as_int(), self.LastPort.get_value_as_int())
        lastport = max(self.FirstPort.get_value_as_int(), self.LastPort.get_value_as_int())
        portrange = (firstport, lastport)

        return {
            "server": {
                "server": server,
                "login": self.Login.get_text(),
                "portrange": portrange,
                "autoaway": self.AutoAway.get_value_as_int(),
                "autoreply": self.AutoReply.get_text(),
                "interface": self.Interface.get_active_text(),
                "upnp": self.UseUPnP.get_active(),
                "upnp_interval": self.UPnPInterval.get_value_as_int(),
                "auto_connect_startup": self.AutoConnectStartup.get_active(),
                "ctcpmsgs": not self.ctcptogglebutton.get_active()
            }
        }

    def on_change_password_response(self, dialog, _response_id, logged_in):

        password = dialog.get_entry_value()

        if logged_in != self.core.logged_in:
            MessageDialog(
                parent=self.preferences.dialog,
                title=_("Password Change Rejected"),
                message=("Since your login status changed, your password has not been changed. Please try again.")
            ).show()
            return

        if not password:
            self.on_change_password()
            return

        if not self.core.logged_in:
            config.sections["server"]["passw"] = password
            config.write_configuration()
            return

        self.core.request_change_password(password)

    def on_change_password(self, *_args):

        if self.core.logged_in:
            message = _("Enter a new password for your Soulseek account:")
        else:
            message = (_("You are currently logged out of the Soulseek network. If you want to change "
                         "the password of an existing Soulseek account, you need to be logged into that account.")
                       + "\n\n"
                       + _("Enter password to use when logging in:"))

        EntryDialog(
            parent=self.preferences.dialog,
            title=_("Change Password"),
            message=message,
            visibility=False,
            callback=self.on_change_password_response,
            callback_data=self.core.logged_in
        ).show()

    def on_toggle_upnp(self, widget, *_args):
        self.portmap_required = widget.get_active()

    def on_modify_upnp_interval(self, *_args):
        self.portmap_required = True


class DownloadsFrame(UserInterface):

    def __init__(self, preferences):

        super().__init__("ui/settings/downloads.ui")

        # pylint: disable=invalid-name
        (self.AfterDownload, self.AfterFolder, self.AutoclearFinished,
         self.DownloadDir, self.DownloadDoubleClick, self.DownloadFilter, self.DownloadReverseOrder,
         self.DownloadSpeed, self.DownloadSpeedAlternative, self.FilterView, self.IncompleteDir,
         self.Main, self.RemoteDownloads, self.UploadDir, self.UploadsAllowed,
         self.UsernameSubfolders, self.VerifiedLabel) = self.widgets

        self.preferences = preferences
        self.frame = preferences.frame

        self.incomplete_dir = FileChooserButton(self.IncompleteDir, preferences.dialog, "folder")
        self.download_dir = FileChooserButton(self.DownloadDir, preferences.dialog, "folder")
        self.upload_dir = FileChooserButton(self.UploadDir, preferences.dialog, "folder")

        self.filter_list_view = TreeView(
            self.frame, parent=self.FilterView, multi_select=True, activate_row_callback=self.on_edit_filter,
            columns=[
                {"column_id": "filter", "column_type": "text", "title": _("Filter"), "sort_column": 0,
                 "width": 1, "expand_column": True},
                {"column_id": "escaped", "column_type": "toggle", "title": _("Escaped"), "width": 0,
                 "sort_column": 1, "toggle_callback": self.on_toggle_escaped}
            ]
        )

        self.options = {
            "transfers": {
                "autoclear_downloads": self.AutoclearFinished,
                "reverseorder": self.DownloadReverseOrder,
                "remotedownloads": self.RemoteDownloads,
                "uploadallowed": self.UploadsAllowed,
                "incompletedir": self.incomplete_dir,
                "downloaddir": self.download_dir,
                "uploaddir": self.upload_dir,
                "downloadfilters": self.filter_list_view,
                "enablefilters": self.DownloadFilter,
                "downloadlimit": self.DownloadSpeed,
                "downloadlimitalt": self.DownloadSpeedAlternative,
                "usernamesubfolders": self.UsernameSubfolders,
                "afterfinish": self.AfterDownload,
                "afterfolder": self.AfterFolder,
                "download_doubleclick": self.DownloadDoubleClick
            }
        }

    def set_settings(self):

        self.filter_list_view.clear()
        self.preferences.set_widgets_data(self.options)

    def get_settings(self):

        try:
            uploadallowed = self.UploadsAllowed.get_active()
        except Exception:
            uploadallowed = 0

        if not self.RemoteDownloads.get_active():
            uploadallowed = 0

        download_filters = []

        for dfilter, iterator in self.filter_list_view.iterators.items():
            escaped = self.filter_list_view.get_row_value(iterator, 1)
            download_filters.append([dfilter, int(escaped)])

        download_filters.sort()

        return {
            "transfers": {
                "autoclear_downloads": self.AutoclearFinished.get_active(),
                "reverseorder": self.DownloadReverseOrder.get_active(),
                "remotedownloads": self.RemoteDownloads.get_active(),
                "uploadallowed": uploadallowed,
                "incompletedir": self.incomplete_dir.get_path(),
                "downloaddir": self.download_dir.get_path(),
                "uploaddir": self.upload_dir.get_path(),
                "downloadfilters": download_filters,
                "enablefilters": self.DownloadFilter.get_active(),
                "downloadlimit": self.DownloadSpeed.get_value_as_int(),
                "downloadlimitalt": self.DownloadSpeedAlternative.get_value_as_int(),
                "usernamesubfolders": self.UsernameSubfolders.get_active(),
                "afterfinish": self.AfterDownload.get_text(),
                "afterfolder": self.AfterFolder.get_text(),
                "download_doubleclick": self.DownloadDoubleClick.get_active()
            }
        }

    def on_toggle_escaped(self, list_view, iterator):

        value = list_view.get_row_value(iterator, 1)
        list_view.set_row_value(iterator, 1, not value)

        self.on_verify_filter()

    def on_add_filter_response(self, dialog, _response_id, _data):

        dfilter = dialog.get_entry_value()
        escaped = dialog.get_option_value()

        iterator = self.filter_list_view.iterators.get(dfilter)

        if iterator is not None:
            self.filter_list_view.set_row_value(iterator, 0, dfilter)
            self.filter_list_view.set_row_value(iterator, 1, escaped)
        else:
            self.filter_list_view.add_row([dfilter, escaped])

        self.on_verify_filter()

    def on_add_filter(self, *_args):

        EntryDialog(
            parent=self.preferences.dialog,
            title=_("Add Download Filter"),
            message=_("Enter a new download filter:"),
            callback=self.on_add_filter_response,
            option_value=True,
            option_label="Escape this filter?",
            droplist=self.filter_list_view.iterators
        ).show()

    def on_edit_filter_response(self, dialog, _response_id, iterator):

        new_dfilter = dialog.get_entry_value()
        escaped = dialog.get_option_value()

        if new_dfilter in self.filter_list_view.iterators:
            self.filter_list_view.set_row_value(iterator, 0, new_dfilter)
            self.filter_list_view.set_row_value(iterator, 1, escaped)
        else:
            self.filter_list_view.remove_row(iterator)
            self.filter_list_view.add_row([new_dfilter, escaped])

        self.on_verify_filter()

    def on_edit_filter(self, *_args):

        for iterator in self.filter_list_view.get_selected_rows():
            dfilter = self.filter_list_view.get_row_value(iterator, 0)
            escaped = self.filter_list_view.get_row_value(iterator, 1)

            EntryDialog(
                parent=self.preferences.dialog,
                title=_("Edit Download Filter"),
                message=_("Modify the following download filter:"),
                callback=self.on_edit_filter_response,
                callback_data=iterator,
                default=dfilter,
                option_value=escaped,
                option_label="Escape this filter?",
                droplist=self.filter_list_view.iterators
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
            dfilter = self.filter_list_view.get_row_value(iterator, 0)
            escaped = self.filter_list_view.get_row_value(iterator, 1)

            if escaped:
                dfilter = re.escape(dfilter)
                dfilter = dfilter.replace("\\*", ".*")
            else:
                # Avoid "Nothing to repeat" error
                dfilter = dfilter.replace("*", "\\*").replace("+", "\\+")

            try:
                re.compile("(" + dfilter + ")")
                outfilter += dfilter

            except Exception as error:
                failed[dfilter] = error

            if filter is not list(self.filter_list_view.iterators)[-1]:
                outfilter += "|"

        outfilter += ")$)"

        try:
            re.compile(outfilter)

        except Exception as error:
            failed[outfilter] = error

        if failed:
            errors = ""

            for dfilter, error in failed.items():
                errors += "Filter: %(filter)s Error: %(error)s " % {
                    'filter': dfilter,
                    'error': error
                }

            error = _("%(num)d Failed! %(error)s " % {
                'num': len(failed),
                'error': errors}
            )

            self.VerifiedLabel.set_markup("<span foreground=\"#e04f5e\">%s</span>" % error)
        else:
            self.VerifiedLabel.set_text(_("Filters Successful"))


class SharesFrame(UserInterface):

    def __init__(self, preferences):

        super().__init__("ui/settings/shares.ui")

        # pylint: disable=invalid-name
        (self.BuddySharesTrustedOnly, self.Main, self.RescanOnStartup, self.Shares) = self.widgets

        self.preferences = preferences
        self.frame = preferences.frame

        self.rescan_required = False
        self.shareddirs = []
        self.bshareddirs = []

        self.shares_list_view = TreeView(
            self.frame, parent=self.Shares, multi_select=True, activate_row_callback=self.on_edit_shared_dir,
            columns=[
                {"column_id": "virtual_folder", "column_type": "text", "title": _("Virtual Folder"), "width": 1,
                 "sort_column": 0, "expand_column": True},
                {"column_id": "folder", "column_type": "text", "title": _("Folder"), "width": 150,
                 "sort_column": 1, "expand_column": True},
                {"column_id": "buddies", "column_type": "toggle", "title": _("Buddy-only"), "width": 0,
                 "sort_column": 2, "toggle_callback": self.cell_toggle_callback},
            ]
        )

        self.options = {
            "transfers": {
                "rescanonstartup": self.RescanOnStartup,
                "buddysharestrustedonly": self.BuddySharesTrustedOnly
            }
        }

    def set_settings(self):

        self.shares_list_view.clear()

        self.preferences.set_widgets_data(self.options)

        self.shareddirs = config.sections["transfers"]["shared"][:]
        self.bshareddirs = config.sections["transfers"]["buddyshared"][:]

        for virtual, folder, *_unused in self.bshareddirs:
            self.shares_list_view.add_row([str(virtual), str(folder), True], select_row=False)

        for virtual, folder, *_unused in self.shareddirs:
            self.shares_list_view.add_row([str(virtual), str(folder), False], select_row=False)

        self.rescan_required = False

    def get_settings(self):

        return {
            "transfers": {
                "shared": self.shareddirs[:],
                "buddyshared": self.bshareddirs[:],
                "rescanonstartup": self.RescanOnStartup.get_active(),
                "buddysharestrustedonly": self.BuddySharesTrustedOnly.get_active()
            }
        }

    def get_normalized_virtual_name(self, virtual_name):

        # Remove slashes from share name to avoid path conflicts
        virtual_name = virtual_name.replace('/', '_').replace('\\', '_')
        new_virtual_name = str(virtual_name)

        # Check if virtual share name is already in use
        counter = 1
        while new_virtual_name in (x[0] for x in self.shareddirs + self.bshareddirs):
            new_virtual_name = virtual_name + str(counter)
            counter += 1

        return new_virtual_name

    def set_shared_dir_buddy_only(self, iterator, buddy_only):

        if buddy_only == self.shares_list_view.get_row_value(iterator, 2):
            return

        virtual = self.shares_list_view.get_row_value(iterator, 0)
        directory = self.shares_list_view.get_row_value(iterator, 1)
        share = (virtual, directory)
        self.rescan_required = True

        self.shares_list_view.set_row_value(iterator, 2, buddy_only)

        if buddy_only:
            self.shareddirs.remove(share)
            self.bshareddirs.append(share)
            return

        self.bshareddirs.remove(share)
        self.shareddirs.append(share)

    def cell_toggle_callback(self, list_view, iterator):
        buddy_only = not list_view.get_row_value(iterator, 2)
        self.set_shared_dir_buddy_only(iterator, buddy_only)

    def add_shared_dir(self, folder):

        if folder is None:
            return

        # If the directory is already shared
        if folder in (x[1] for x in self.shareddirs + self.bshareddirs):
            return

        virtual = self.get_normalized_virtual_name(os.path.basename(os.path.normpath(folder)))

        self.shares_list_view.add_row([virtual, folder, False])
        self.shareddirs.append((virtual, folder))
        self.rescan_required = True

    def on_add_shared_dir_selected(self, selected, _data):

        for folder in selected:
            self.add_shared_dir(folder)

    def on_add_shared_dir(self, *_args):

        FolderChooser(
            parent=self.preferences.dialog,
            callback=self.on_add_shared_dir_selected,
            title=_("Add a Shared Folder"),
            multiple=True
        ).show()

    def on_edit_shared_dir_response(self, dialog, _response_id, iterator):

        virtual = dialog.get_entry_value()
        buddy_only = dialog.get_option_value()

        if not virtual:
            return

        virtual = self.get_normalized_virtual_name(virtual)
        folder = self.shares_list_view.get_row_value(iterator, 1)
        old_virtual = self.shares_list_view.get_row_value(iterator, 0)
        old_mapping = (old_virtual, folder)
        new_mapping = (virtual, folder)

        if old_mapping in self.bshareddirs:
            shared_dirs = self.bshareddirs
        else:
            shared_dirs = self.shareddirs

        shared_dirs.remove(old_mapping)
        shared_dirs.append(new_mapping)

        self.shares_list_view.set_row_value(iterator, 0, virtual)
        self.set_shared_dir_buddy_only(iterator, buddy_only)
        self.rescan_required = True

    def on_edit_shared_dir(self, *_args):

        for iterator in self.shares_list_view.get_selected_rows():
            virtual_name = self.shares_list_view.get_row_value(iterator, 0)
            folder = self.shares_list_view.get_row_value(iterator, 1)
            buddy_only = self.shares_list_view.get_row_value(iterator, 2)

            EntryDialog(
                parent=self.preferences.dialog,
                title=_("Edit Shared Folder"),
                message=_("Enter new virtual name for '%(dir)s':") % {'dir': folder},
                default=virtual_name,
                option_value=buddy_only,
                option_label="Share with buddies only?",
                callback=self.on_edit_shared_dir_response,
                callback_data=iterator
            ).show()
            return

    def on_remove_shared_dir(self, *_args):

        iterators = reversed(self.shares_list_view.get_selected_rows())

        for iterator in iterators:
            virtual = self.shares_list_view.get_row_value(iterator, 0)
            folder = self.shares_list_view.get_row_value(iterator, 1)
            mapping = (virtual, folder)

            if mapping in self.bshareddirs:
                self.bshareddirs.remove(mapping)
            else:
                self.shareddirs.remove(mapping)

            self.shares_list_view.remove_row(iterator)

        if iterators:
            self.rescan_required = True


class UploadsFrame(UserInterface):

    def __init__(self, preferences):

        super().__init__("ui/settings/uploads.ui")

        # pylint: disable=invalid-name
        (self.AutoclearFinished, self.FirstInFirstOut, self.FriendsNoLimits, self.Limit,
         self.LimitSpeed, self.LimitSpeedAlternative, self.LimitTotalTransfers, self.Main, self.MaxUserFiles,
         self.MaxUserQueue, self.PreferFriends, self.QueueBandwidth, self.QueueSlots, self.QueueUseBandwidth,
         self.QueueUseSlots, self.UploadDoubleClick) = self.widgets

        self.preferences = preferences
        self.frame = preferences.frame

        self.options = {
            "transfers": {
                "autoclear_uploads": self.AutoclearFinished,
                "uploadbandwidth": self.QueueBandwidth,
                "useupslots": self.QueueUseSlots,
                "uploadslots": self.QueueSlots,
                "uselimit": self.Limit,
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
        self.preferences.set_widgets_data(self.options)

    def get_settings(self):

        return {
            "transfers": {
                "autoclear_uploads": self.AutoclearFinished.get_active(),
                "uploadbandwidth": self.QueueBandwidth.get_value_as_int(),
                "useupslots": self.QueueUseSlots.get_active(),
                "uploadslots": self.QueueSlots.get_value_as_int(),
                "uselimit": self.Limit.get_active(),
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


class UserInfoFrame(UserInterface):

    def __init__(self, preferences):

        super().__init__("ui/settings/userinfo.ui")

        # pylint: disable=invalid-name
        self.Description, self.ImageChooser, self.Main = self.widgets

        self.preferences = preferences
        self.frame = preferences.frame

        self.image_chooser = FileChooserButton(self.ImageChooser, preferences.dialog, "image")

        self.options = {
            "userinfo": {
                "descr": None,
                "pic": self.image_chooser
            }
        }

    def set_settings(self):

        self.preferences.set_widgets_data(self.options)

        if config.sections["userinfo"]["descr"] is not None:
            descr = unescape(config.sections["userinfo"]["descr"])
            self.Description.get_buffer().set_text(descr)

    def get_settings(self):

        buffer = self.Description.get_buffer()

        start = buffer.get_start_iter()
        end = buffer.get_end_iter()

        descr = repr(buffer.get_text(start, end, True).replace("; ", ", "))

        return {
            "userinfo": {
                "descr": descr,
                "pic": self.image_chooser.get_path()
            }
        }

    def on_default_image(self, *_args):
        self.image_chooser.clear()


class IgnoredUsersFrame(UserInterface):

    def __init__(self, preferences):

        super().__init__("ui/settings/ignore.ui")

        # pylint: disable=invalid-name
        self.IgnoredIPs, self.IgnoredUsers, self.Main = self.widgets

        self.preferences = preferences
        self.frame = self.preferences.frame

        self.ignored_users = []
        self.ignored_users_list_view = TreeView(
            self.frame, parent=self.IgnoredUsers, multi_select=True,
            columns=[
                {"column_id": "username", "column_type": "text", "title": _("Username"), "sort_column": 0}
            ]
        )

        self.ignored_ips = {}
        self.ignored_ips_list_view = TreeView(
            self.frame, parent=self.IgnoredIPs, multi_select=True,
            columns=[
                {"column_id": "ip_address", "column_type": "text", "title": _("IP Address"), "sort_column": 0,
                 "width": 50, "expand_column": True},
                {"column_id": "user", "column_type": "text", "title": _("User"), "sort_column": 1,
                 "expand_column": True}
            ]
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

        self.preferences.set_widgets_data(self.options)

        self.ignored_users = config.sections["server"]["ignorelist"][:]
        self.ignored_ips = config.sections["server"]["ipignorelist"].copy()

    def get_settings(self):
        return {
            "server": {
                "ignorelist": self.ignored_users[:],
                "ipignorelist": self.ignored_ips.copy()
            }
        }

    def on_add_ignored_response(self, dialog, _response_id, _data):

        user = dialog.get_entry_value()

        if user and user not in self.ignored_users:
            self.ignored_users.append(user)
            self.ignored_users_list_view.add_row([str(user)])

    def on_add_ignored(self, *_args):

        EntryDialog(
            parent=self.preferences.dialog,
            title=_("Ignore User"),
            message=_("Enter the name of the user you want to ignore:"),
            callback=self.on_add_ignored_response
        ).show()

    def on_remove_ignored(self, *_args):

        for iterator in reversed(self.ignored_users_list_view.get_selected_rows()):
            user = self.ignored_users_list_view.get_row_value(iterator, 0)

            self.ignored_users_list_view.remove_row(iterator)
            self.ignored_users.remove(user)

    def on_add_ignored_ip_response(self, dialog, _response_id, _data):

        ip_address = dialog.get_entry_value()

        if ip_address is None or ip_address == "" or ip_address.count(".") != 3:
            return

        for chars in ip_address.split("."):

            if chars == "*":
                continue
            if not chars.isdigit():
                return

            try:
                if int(chars) > 255:
                    return
            except Exception:
                return

        if ip_address not in self.ignored_ips:
            self.ignored_ips[ip_address] = ""
            self.ignored_ips_list_view.add_row([ip_address, ""])

    def on_add_ignored_ip(self, *_args):

        EntryDialog(
            parent=self.preferences.dialog,
            title=_("Ignore IP Address"),
            message=_("Enter an IP address you want to ignore:") + " " + _("* is a wildcard"),
            callback=self.on_add_ignored_ip_response
        ).show()

    def on_remove_ignored_ip(self, *_args):

        for iterator in reversed(self.ignored_ips_list_view.get_selected_rows()):
            ip_address = self.ignored_ips_list_view.get_row_value(iterator, 0)

            self.ignored_ips_list_view.remove_row(iterator)
            del self.ignored_ips[ip_address]


class BannedUsersFrame(UserInterface):

    def __init__(self, preferences):

        super().__init__("ui/settings/ban.ui")

        # pylint: disable=invalid-name
        (self.BannedList, self.BlockedList, self.CustomBan, self.CustomGeoBlock, self.GeoBlock, self.GeoBlockCC,
         self.Main, self.UseCustomBan, self.UseCustomGeoBlock) = self.widgets

        self.preferences = preferences
        self.frame = preferences.frame
        self.ip_block_required = False

        self.banned_users = []
        self.banned_users_list_view = TreeView(
            self.frame, parent=self.BannedList, multi_select=True,
            columns=[
                {"column_id": "username", "column_type": "text", "title": _("Username"), "sort_column": 0}
            ]
        )

        self.banned_ips = {}
        self.banned_ips_list_view = TreeView(
            self.frame, parent=self.BlockedList, multi_select=True,
            columns=[
                {"column_id": "ip_address", "column_type": "text", "title": _("IP Address"), "sort_column": 0,
                 "width": 50, "expand_column": True},
                {"column_id": "user", "column_type": "text", "title": _("User"), "sort_column": 1,
                 "expand_column": True}
            ]
        )

        self.options = {
            "server": {
                "banlist": self.banned_users_list_view,
                "ipblocklist": self.banned_ips_list_view
            },
            "transfers": {
                "usecustomban": self.UseCustomBan,
                "customban": self.CustomBan,
                "geoblock": self.GeoBlock,
                "geoblockcc": self.GeoBlockCC,
                "usecustomgeoblock": self.UseCustomGeoBlock,
                "customgeoblock": self.CustomGeoBlock
            }
        }

    def set_settings(self):

        self.banned_users_list_view.clear()
        self.banned_ips_list_view.clear()
        self.banned_users.clear()
        self.banned_ips.clear()

        self.preferences.set_widgets_data(self.options)

        self.banned_users = config.sections["server"]["banlist"][:]
        self.banned_ips = config.sections["server"]["ipblocklist"].copy()
        self.GeoBlockCC.set_text(config.sections["transfers"]["geoblockcc"][0])

        self.ip_block_required = False

    def get_settings(self):

        self.ip_block_required = False

        return {
            "server": {
                "banlist": self.banned_users[:],
                "ipblocklist": self.banned_ips.copy()
            },
            "transfers": {
                "usecustomban": self.UseCustomBan.get_active(),
                "customban": self.CustomBan.get_text(),
                "geoblock": self.GeoBlock.get_active(),
                "geoblockcc": [self.GeoBlockCC.get_text().upper()],
                "usecustomgeoblock": self.UseCustomGeoBlock.get_active(),
                "customgeoblock": self.CustomGeoBlock.get_text()
            }
        }

    def on_add_banned_response(self, dialog, _response_id, _data):

        user = dialog.get_entry_value()

        if user and user not in self.banned_users:
            self.banned_users.append(user)
            self.banned_users_list_view.add_row([user])

    def on_add_banned(self, *_args):

        EntryDialog(
            parent=self.preferences.dialog,
            title=_("Ban User"),
            message=_("Enter the name of the user you want to ban:"),
            callback=self.on_add_banned_response
        ).show()

    def on_remove_banned(self, *_args):

        for iterator in reversed(self.banned_users_list_view.get_selected_rows()):
            user = self.banned_users_list_view.get_row_value(iterator, 0)

            self.banned_users_list_view.remove_row(iterator)
            self.banned_users.remove(user)

    def on_add_blocked_response(self, dialog, _response_id, _data):

        ip_address = dialog.get_entry_value()

        if ip_address is None or ip_address == "" or ip_address.count(".") != 3:
            return

        for chars in ip_address.split("."):

            if chars == "*":
                continue
            if not chars.isdigit():
                return

            try:
                if int(chars) > 255:
                    return
            except Exception:
                return

        if ip_address not in self.banned_ips:
            self.banned_ips[ip_address] = ""
            self.banned_ips_list_view.add_row([ip_address, ""])
            self.ip_block_required = True

    def on_add_blocked(self, *_args):

        EntryDialog(
            parent=self.preferences.dialog,
            title=_("Block IP Address"),
            message=_("Enter an IP address you want to block:") + " " + _("* is a wildcard"),
            callback=self.on_add_blocked_response
        ).show()

    def on_remove_blocked(self, *_args):

        for iterator in reversed(self.banned_ips_list_view.get_selected_rows()):
            ip_address = self.banned_ips_list_view.get_row_value(iterator, 0)

            self.banned_ips_list_view.remove_row(iterator)
            del self.banned_ips[ip_address]


class ChatsFrame(UserInterface):

    def __init__(self, preferences):

        super().__init__("ui/settings/chats.ui")

        # pylint: disable=invalid-name
        (self.CensorCheck, self.CensorList,
         self.CensorReplaceCombo, self.CharactersCompletion, self.ChatRoomFormat,
         self.CompleteAliasesCheck, self.CompleteBuddiesCheck, self.CompleteCommandsCheck, self.CompleteRoomNamesCheck,
         self.CompleteUsersInRoomsCheck, self.CompletionCycleCheck, self.CompletionDropdownCheck,
         self.CompletionTabCheck, self.Main, self.OneMatchCheck, self.PrivateChatFormat,
         self.PrivateLogLines, self.PrivateMessage,
         self.ReopenPrivateChats, self.ReplaceCheck, self.ReplacementList,
         self.RoomLogLines, self.RoomMessage, self.SpellCheck,
         self.TTSCommand, self.TextToSpeech) = self.widgets

        self.preferences = preferences
        self.frame = preferences.frame
        self.completion_required = False

        self.censored_patterns = []
        self.censor_list_view = TreeView(
            self.frame, parent=self.CensorList, multi_select=True, activate_row_callback=self.on_edit_censored,
            columns=[
                {"column_id": "pattern", "column_type": "text", "title": _("Pattern"), "sort_column": 0}
            ]
        )

        self.replacements = {}
        self.replacement_list_view = TreeView(
            self.frame, parent=self.ReplacementList, multi_select=True, activate_row_callback=self.on_edit_replacement,
            columns=[
                {"column_id": "pattern", "column_type": "text", "title": _("Pattern"), "sort_column": 0,
                 "width": 100, "expand_column": True},
                {"column_id": "replacement", "column_type": "text", "title": _("Replacement"), "sort_column": 1,
                 "expand_column": True}
            ]
        )

        self.options = {
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
                "aliases": self.CompleteAliasesCheck,
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

        self.preferences.set_widgets_data(self.options)

        try:
            gi.require_version('Gspell', '1')
            from gi.repository import Gspell  # noqa: F401; pylint:disable=unused-import

        except (ImportError, ValueError):
            self.SpellCheck.hide()

        self.censored_patterns = config.sections["words"]["censored"][:]
        self.replacements = config.sections["words"]["autoreplaced"].copy()

        self.completion_required = False

    def get_settings(self):

        self.completion_required = False

        return {
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
                "aliases": self.CompleteAliasesCheck.get_active(),
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
            parent=self.preferences.dialog,
            title=_("Censor Pattern"),
            message=_("Enter a pattern you want to censor. Add spaces around the pattern if you don't "
                      "want to match strings inside words (may fail at the beginning and end of lines)."),
            callback=self.on_add_censored_response
        ).show()

    def on_edit_censored_response(self, dialog, _response_id, iterator):

        pattern = dialog.get_entry_value()

        if not pattern:
            return

        old_pattern = self.censor_list_view.get_row_value(iterator, 0)
        self.censored_patterns.remove(old_pattern)

        self.censor_list_view.set_row_value(iterator, 0, pattern)
        self.censored_patterns.append(pattern)

    def on_edit_censored(self, *_args):

        for iterator in self.censor_list_view.get_selected_rows():
            pattern = self.censor_list_view.get_row_value(iterator, 0)

            EntryDialog(
                parent=self.preferences.dialog,
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
            censor = self.censor_list_view.get_row_value(iterator, 0)

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
            parent=self.preferences.dialog,
            title=_("Add Replacement"),
            message=_("Enter the text pattern and replacement, respectively:"),
            callback=self.on_add_replacement_response,
            use_second_entry=True
        ).show()

    def on_edit_replacement_response(self, dialog, _response_id, iterator):

        pattern = dialog.get_entry_value()
        replacement = dialog.get_second_entry_value()

        if not pattern or not replacement:
            return

        old_pattern = self.replacement_list_view.get_row_value(iterator, 0)
        del self.replacements[old_pattern]

        self.replacements[pattern] = replacement
        self.replacement_list_view.set_row_value(iterator, 0, pattern)
        self.replacement_list_view.set_row_value(iterator, 1, replacement)

    def on_edit_replacement(self, *_args):

        for iterator in self.replacement_list_view.get_selected_rows():
            pattern = self.replacement_list_view.get_row_value(iterator, 0)
            replacement = self.replacement_list_view.get_row_value(iterator, 1)

            EntryDialog(
                parent=self.preferences.dialog,
                title=_("Edit Replacement"),
                message=_("Enter the text pattern and replacement, respectively:"),
                callback=self.on_edit_replacement_response,
                callback_data=iterator,
                use_second_entry=True,
                default=pattern,
                second_default=replacement
            ).show()
            return

    def on_remove_replacement(self, *_args):

        for iterator in reversed(self.replacement_list_view.get_selected_rows()):
            replacement = self.replacement_list_view.get_row_value(iterator, 0)

            self.replacement_list_view.remove_row(iterator)
            del self.replacements[replacement]


class UserInterfaceFrame(UserInterface):

    def __init__(self, preferences):

        super().__init__("ui/settings/userinterface.ui")

        # pylint: disable=invalid-name
        (self.ChatRoomsPosition, self.CloseAction, self.DarkMode,
         self.DefaultBrowserFont, self.DefaultChatFont, self.DefaultGlobalFont, self.DefaultListFont,
         self.DefaultSearchFont, self.DefaultTheme, self.DefaultTransfersFont, self.EnableChatroomsTab,
         self.EnableDownloadsTab, self.EnableInterestsTab, self.EnablePrivateTab, self.EnableSearchTab,
         self.EnableUploadsTab, self.EnableUserBrowseTab, self.EnableUserInfoTab, self.EnableUserListTab,
         self.EntryAway, self.EntryBackground, self.EntryChangedTab, self.EntryHighlight, self.EntryHighlightTab,
         self.EntryImmediate, self.EntryInput, self.EntryLocal, self.EntryMe, self.EntryOffline, self.EntryOnline,
         self.EntryQueue, self.EntryRegularTab, self.EntryRemote, self.EntryURL, self.FilePathTooltips,
         self.IconView, self.Main, self.MainPosition,
         self.NotificationPopupChatroom, self.NotificationPopupChatroomMention, self.NotificationPopupFile,
         self.NotificationPopupFolder, self.NotificationPopupPrivateMessage, self.NotificationPopupSound,
         self.NotificationTabColors, self.NotificationWindowTitle, self.PickAway, self.PickBackground,
         self.PickChangedTab, self.PickHighlight, self.PickHighlightTab, self.PickImmediate, self.PickInput,
         self.PickLocal, self.PickMe, self.PickOffline, self.PickOnline, self.PickQueue, self.PickRegularTab,
         self.PickRemote, self.PickURL, self.PrivateChatPosition, self.ReverseFilePaths,
         self.SearchPosition, self.SelectBrowserFont, self.SelectChatFont, self.SelectGlobalFont, self.SelectListFont,
         self.SelectSearchFont, self.SelectTransfersFont, self.StartupHidden, self.TabClosers, self.TabSelectPrevious,
         self.TabStatusIcons, self.ThemeDir, self.TraySettings, self.TrayiconCheck,
         self.UserBrowsePosition, self.UserInfoPosition, self.UsernameHotspots,
         self.UsernameStyle) = self.widgets

        self.preferences = preferences
        self.frame = preferences.frame
        self.theme_required = False

        self.theme_dir = FileChooserButton(self.ThemeDir, preferences.dialog, "folder")

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
            ("nplus-status-online", _("Connected"), 16),
            ("nplus-status-offline", _("Disconnected"), 16),
            ("nplus-status-away", _("Away"), 16),
            ("nplus-hilite", _("Highlight"), 16),
            ("nplus-hilite3", _("Highlight"), 16),
            (config.application_id, _("Window"), 64)]

        if self.frame.tray_icon.available:
            icon_list += [
                (config.application_id + "-connect", _("Connected (Tray)"), 16),
                (config.application_id + "-disconnect", _("Disconnected (Tray)"), 16),
                (config.application_id + "-away", _("Away (Tray)"), 16),
                (config.application_id + "-msg", _("Message (Tray)"), 16)]

        for icon_name, label, pixel_size in icon_list:
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, valign=Gtk.Align.CENTER, spacing=6, visible=True)
            icon = Gtk.Image(icon_name=icon_name, pixel_size=pixel_size, visible=True)
            label = Gtk.Label(label=label, xalign=0.5, wrap=True, visible=True)

            if GTK_API_VERSION >= 4:
                box.append(icon)   # pylint: disable=no-member
                box.append(label)  # pylint: disable=no-member
            else:
                box.add(icon)   # pylint: disable=no-member
                box.add(label)  # pylint: disable=no-member

            self.IconView.insert(box, -1)

        self.options = {
            "notifications": {
                "notification_tab_colors": self.NotificationTabColors,
                "notification_window_title": self.NotificationWindowTitle,
                "notification_popup_sound": self.NotificationPopupSound,
                "notification_popup_file": self.NotificationPopupFile,
                "notification_popup_folder": self.NotificationPopupFolder,
                "notification_popup_private_message": self.NotificationPopupPrivateMessage,
                "notification_popup_chatroom": self.NotificationPopupChatroom,
                "notification_popup_chatroom_mention": self.NotificationPopupChatroomMention
            },
            "ui": {
                "globalfont": self.SelectGlobalFont,
                "chatfont": self.SelectChatFont,
                "listfont": self.SelectListFont,
                "searchfont": self.SelectSearchFont,
                "transfersfont": self.SelectTransfersFont,
                "browserfont": self.SelectBrowserFont,
                "usernamestyle": self.UsernameStyle,

                "file_path_tooltips": self.FilePathTooltips,
                "reverse_file_paths": self.ReverseFilePaths,

                "tabmain": self.MainPosition,
                "tabrooms": self.ChatRoomsPosition,
                "tabprivate": self.PrivateChatPosition,
                "tabsearch": self.SearchPosition,
                "tabinfo": self.UserInfoPosition,
                "tabbrowse": self.UserBrowsePosition,
                "tab_select_previous": self.TabSelectPrevious,
                "tabclosers": self.TabClosers,
                "tab_status_icons": self.TabStatusIcons,

                "icontheme": self.theme_dir,

                "chatlocal": self.EntryLocal,
                "chatremote": self.EntryRemote,
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

        self.preferences.set_widgets_data(self.options)
        self.theme_required = False

        self.TraySettings.set_visible(self.frame.tray_icon.available)

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
                "notification_tab_colors": self.NotificationTabColors.get_active(),
                "notification_window_title": self.NotificationWindowTitle.get_active(),
                "notification_popup_sound": self.NotificationPopupSound.get_active(),
                "notification_popup_file": self.NotificationPopupFile.get_active(),
                "notification_popup_folder": self.NotificationPopupFolder.get_active(),
                "notification_popup_private_message": self.NotificationPopupPrivateMessage.get_active(),
                "notification_popup_chatroom": self.NotificationPopupChatroom.get_active(),
                "notification_popup_chatroom_mention": self.NotificationPopupChatroomMention.get_active()
            },
            "ui": {
                "globalfont": self.SelectGlobalFont.get_font(),
                "chatfont": self.SelectChatFont.get_font(),
                "listfont": self.SelectListFont.get_font(),
                "searchfont": self.SelectSearchFont.get_font(),
                "transfersfont": self.SelectTransfersFont.get_font(),
                "browserfont": self.SelectBrowserFont.get_font(),
                "usernamestyle": self.UsernameStyle.get_active_id(),

                "file_path_tooltips": self.FilePathTooltips.get_active(),
                "reverse_file_paths": self.ReverseFilePaths.get_active(),

                "tabmain": self.MainPosition.get_active_id(),
                "tabrooms": self.ChatRoomsPosition.get_active_id(),
                "tabprivate": self.PrivateChatPosition.get_active_id(),
                "tabsearch": self.SearchPosition.get_active_id(),
                "tabinfo": self.UserInfoPosition.get_active_id(),
                "tabbrowse": self.UserBrowsePosition.get_active_id(),
                "modes_visible": enabled_tabs,
                "tab_select_previous": self.TabSelectPrevious.get_active(),
                "tabclosers": self.TabClosers.get_active(),
                "tab_status_icons": self.TabStatusIcons.get_active(),

                "icontheme": self.theme_dir.get_path(),

                "chatlocal": self.EntryLocal.get_text(),
                "chatremote": self.EntryRemote.get_text(),
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
        color = "#%02X%02X%02X" % (round(rgba.red * 255), round(rgba.green * 255), round(rgba.blue * 255))
        entry = getattr(self, Gtk.Buildable.get_name(widget).replace("Pick", "Entry"))
        entry.set_text(color)

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


class LoggingFrame(UserInterface):

    def __init__(self, preferences):

        super().__init__("ui/settings/log.ui")

        # pylint: disable=invalid-name
        (self.DebugLogDir, self.LogDebug, self.LogFileFormat,
         self.LogPrivate, self.LogRooms, self.LogTransfers, self.Main, self.PrivateLogDir,
         self.RoomLogDir, self.TransfersLogDir) = self.widgets

        self.preferences = preferences
        self.frame = preferences.frame

        self.private_log_dir = FileChooserButton(self.PrivateLogDir, preferences.dialog, "folder")
        self.room_log_dir = FileChooserButton(self.RoomLogDir, preferences.dialog, "folder")
        self.transfers_log_dir = FileChooserButton(self.TransfersLogDir, preferences.dialog, "folder")
        self.debug_log_dir = FileChooserButton(self.DebugLogDir, preferences.dialog, "folder")

        self.options = {
            "logging": {
                "privatechat": self.LogPrivate,
                "privatelogsdir": self.private_log_dir,
                "chatrooms": self.LogRooms,
                "roomlogsdir": self.room_log_dir,
                "transfers": self.LogTransfers,
                "transferslogsdir": self.transfers_log_dir,
                "debug_file_output": self.LogDebug,
                "debuglogsdir": self.debug_log_dir,
                "log_timestamp": self.LogFileFormat
            }
        }

    def set_settings(self):
        self.preferences.set_widgets_data(self.options)

    def get_settings(self):

        return {
            "logging": {
                "privatechat": self.LogPrivate.get_active(),
                "privatelogsdir": self.private_log_dir.get_path(),
                "chatrooms": self.LogRooms.get_active(),
                "roomlogsdir": self.room_log_dir.get_path(),
                "transfers": self.LogTransfers.get_active(),
                "transferslogsdir": self.transfers_log_dir.get_path(),
                "debug_file_output": self.LogDebug.get_active(),
                "debuglogsdir": self.debug_log_dir.get_path(),
                "log_timestamp": self.LogFileFormat.get_text()
            }
        }

    def on_default_timestamp(self, *_args):
        self.LogFileFormat.set_text(config.defaults["logging"]["log_timestamp"])


class SearchesFrame(UserInterface):

    def __init__(self, preferences):

        super().__init__("ui/settings/search.ui")

        # pylint: disable=invalid-name
        (self.ClearFilterHistorySuccess, self.ClearSearchHistorySuccess, self.EnableFilters, self.EnableSearchHistory,
         self.FilterBR, self.FilterCC, self.FilterFree, self.FilterIn, self.FilterLength, self.FilterOut,
         self.FilterSize, self.FilterType, self.Main, self.MaxDisplayedResults, self.MaxResults, self.MinSearchChars,
         self.RemoveSpecialChars, self.ShowPrivateSearchResults, self.ShowSearchHelp, self.ToggleResults) = self.widgets

        self.preferences = preferences
        self.frame = preferences.frame
        self.search_required = False

        self.filter_help = UserInterface("ui/popovers/searchfilters.ui")
        self.filter_help.popover, = self.filter_help.widgets
        self.ShowSearchHelp.set_popover(self.filter_help.popover)

        self.options = {
            "searches": {
                "maxresults": self.MaxResults,
                "enablefilters": self.EnableFilters,
                "defilter": None,
                "search_results": self.ToggleResults,
                "max_displayed_results": self.MaxDisplayedResults,
                "min_search_chars": self.MinSearchChars,
                "remove_special_chars": self.RemoveSpecialChars,
                "enable_history": self.EnableSearchHistory,
                "private_search_results": self.ShowPrivateSearchResults
            }
        }

    def set_settings(self):

        searches = config.sections["searches"]
        self.preferences.set_widgets_data(self.options)
        self.search_required = False

        if searches["defilter"] is not None:
            num_filters = len(searches["defilter"])

            if num_filters > 0:
                self.FilterIn.set_text(str(searches["defilter"][0]))

            if num_filters > 1:
                self.FilterOut.set_text(str(searches["defilter"][1]))

            if num_filters > 2:
                self.FilterSize.set_text(str(searches["defilter"][2]))

            if num_filters > 3:
                self.FilterBR.set_text(str(searches["defilter"][3]))

            if num_filters > 4:
                self.FilterFree.set_active(searches["defilter"][4])

            if num_filters > 5:
                self.FilterCC.set_text(str(searches["defilter"][5]))

            if num_filters > 6:
                self.FilterType.set_text(str(searches["defilter"][6]))

            if num_filters > 7:
                self.FilterLength.set_text(str(searches["defilter"][7]))

        self.ClearSearchHistorySuccess.hide()
        self.ClearFilterHistorySuccess.hide()

    def get_settings(self):

        self.search_required = False

        return {
            "searches": {
                "maxresults": self.MaxResults.get_value_as_int(),
                "enablefilters": self.EnableFilters.get_active(),
                "defilter": [
                    self.FilterIn.get_text(),
                    self.FilterOut.get_text(),
                    self.FilterSize.get_text(),
                    self.FilterBR.get_text(),
                    self.FilterFree.get_active(),
                    self.FilterCC.get_text(),
                    self.FilterType.get_text(),
                    self.FilterLength.get_text()
                ],
                "search_results": self.ToggleResults.get_active(),
                "max_displayed_results": self.MaxDisplayedResults.get_value_as_int(),
                "min_search_chars": self.MinSearchChars.get_value_as_int(),
                "remove_special_chars": self.RemoveSpecialChars.get_active(),
                "enable_history": self.EnableSearchHistory.get_active(),
                "private_search_results": self.ShowPrivateSearchResults.get_active()
            }
        }

    def on_toggle_search_history(self, *_args):
        self.search_required = True

    def on_clear_search_history(self, *_args):
        self.frame.search.clear_search_history()
        self.ClearSearchHistorySuccess.show()

    def on_clear_filter_history(self, *_args):
        self.frame.search.clear_filter_history()
        self.ClearFilterHistorySuccess.show()


class UrlHandlersFrame(UserInterface):

    def __init__(self, preferences):

        super().__init__("ui/settings/urlhandlers.ui")

        # pylint: disable=invalid-name
        (self.FileManagerCombo, self.Main, self.ProtocolHandlers, self.audioPlayerCombo) = self.widgets

        self.preferences = preferences
        self.frame = preferences.frame

        self.options = {
            "urls": {
                "protocols": None
            },
            "ui": {
                "filemanager": self.FileManagerCombo
            },
            "players": {
                "default": self.audioPlayerCombo
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
            "\"c:\\Program Files\\Mozilla Firefox\\Firefox.exe\" $"
        ]

        self.protocols = {}
        self.protocol_list_view = TreeView(
            self.frame, parent=self.ProtocolHandlers, multi_select=True, activate_row_callback=self.on_edit_handler,
            columns=[
                {"column_id": "protocol", "column_type": "text", "title": _("Protocol"), "sort_column": 0,
                 "width": 1, "expand_column": True, "iterator_key": True},
                {"column_id": "command", "column_type": "text", "title": _("Command"), "sort_column": 1,
                 "expand_column": True}
            ]
        )

    def set_settings(self):

        self.protocol_list_view.clear()
        self.protocols.clear()

        self.preferences.set_widgets_data(self.options)

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
                "filemanager": self.FileManagerCombo.get_active_text()
            },
            "players": {
                "default": self.audioPlayerCombo.get_active_text()
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
            self.protocol_list_view.set_row_value(iterator, 1, command)
            return

        self.protocol_list_view.add_row([protocol, command])

    def on_add_handler(self, *_args):

        EntryDialog(
            parent=self.preferences.dialog,
            title=_("Add URL Handler"),
            message=_("Enter the protocol and command for the URL hander, respectively:"),
            callback=self.on_add_handler_response,
            use_second_entry=True,
            droplist=self.default_protocols,
            second_droplist=self.default_commands
        ).show()

    def on_edit_handler_response(self, dialog, _response_id, iterator):

        command = dialog.get_entry_value()

        if not command:
            return

        protocol = self.protocol_list_view.get_row_value(iterator, 0)

        self.protocols[protocol] = command
        self.protocol_list_view.set_row_value(iterator, 1, command)

    def on_edit_handler(self, *_args):

        for iterator in self.protocol_list_view.get_selected_rows():
            protocol = self.protocol_list_view.get_row_value(iterator, 0)
            command = self.protocol_list_view.get_row_value(iterator, 1)

            EntryDialog(
                parent=self.preferences.dialog,
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
            protocol = self.protocol_list_view.get_row_value(iterator, 0)

            self.protocol_list_view.remove_row(iterator)
            del self.protocols[protocol]


class NowPlayingFrame(UserInterface):

    def __init__(self, preferences):

        super().__init__("ui/settings/nowplaying.ui")

        # pylint: disable=invalid-name
        (self.Example, self.Legend, self.Main, self.NPCommand, self.NPFormat, self.NP_lastfm, self.NP_listenbrainz,
         self.NP_mpris, self.NP_other, self.player_input, self.test_now_playing) = self.widgets

        self.preferences = preferences
        self.frame = preferences.frame
        self.core = preferences.core

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

        # Suppy the information needed for the Now Playing class to return a song
        self.test_now_playing.connect(
            "clicked",
            self.core.now_playing.display_now_playing,
            self.set_now_playing_example,  # Callback to update the song displayed
            self.get_player,               # Callback to retrieve selected player
            self.get_command,              # Callback to retrieve command text
            self.get_format                # Callback to retrieve format text
        )

    def set_settings(self):

        self.preferences.set_widgets_data(self.options)

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

        return player

    def get_command(self):
        return self.NPCommand.get_text()

    def get_format(self):
        return self.NPFormat.get_active_text()

    def set_player(self, player):

        if player == "lastfm":
            self.NP_lastfm.set_active(True)
        elif player == 'listenbrainz':
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
            self.player_input.set_text(_("Client name (e.g. amarok, audacious, exaile) or empty for auto:"))

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
                legend += _("Now Playing (typically \"%(artist)s - %(title)s\")") % {
                    'artist': _("Artist"), 'title': _("Title")}
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


class PluginsFrame(UserInterface):

    def __init__(self, preferences):

        super().__init__("ui/settings/plugin.ui")

        # pylint: disable=invalid-name
        (self.Main, self.PluginAuthor, self.PluginDescription, self.PluginName,
         self.PluginProperties, self.PluginTreeView, self.PluginVersion, self.PluginsEnable) = self.widgets

        self.preferences = preferences
        self.frame = preferences.frame
        self.core = preferences.core

        self.options = {
            "plugins": {
                "enable": self.PluginsEnable
            }
        }

        self.enabled_plugins = []
        self.selected_plugin = None
        self.descr_textview = TextView(self.PluginDescription)
        self.plugin_list_view = TreeView(
            self.frame, parent=self.PluginTreeView, search_column=1, always_select=True,
            select_row_callback=self.on_select_plugin,
            columns=[
                # Visible columns
                {"column_id": "enabled", "column_type": "toggle", "title": _("Enabled"), "width": 0,
                 "sort_column": 0, "toggle_callback": self.on_plugin_toggle, "hide_header": True},
                {"column_id": "plugin", "column_type": "text", "title": _("Plugin"), "sort_column": 1},

                # Hidden data columns
                {"column_id": "plugin_hidden", "data_type": str}
            ]
        )

    def set_settings(self):

        self.plugin_list_view.clear()

        self.preferences.set_widgets_data(self.options)

        for plugin_id in sorted(self.core.pluginhandler.list_installed_plugins()):
            try:
                info = self.core.pluginhandler.get_plugin_info(plugin_id)
            except OSError:
                continue

            plugin_name = info.get('Name', plugin_id)
            enabled = (plugin_id in config.sections["plugins"]["enabled"])
            self.plugin_list_view.add_row([enabled, plugin_name, plugin_id], select_row=False)

            if enabled:
                self.enabled_plugins.append(plugin_id)

    def get_settings(self):

        return {
            "plugins": {
                "enable": self.PluginsEnable.get_active(),
                "enabled": self.enabled_plugins[:]
            }
        }

    def check_properties_button(self, plugin):
        self.PluginProperties.set_sensitive(bool(self.core.pluginhandler.get_plugin_settings(plugin)))

    def on_select_plugin(self, list_view, iterator):

        if iterator is None:
            self.selected_plugin = _("No Plugin Selected")
            info = {}
        else:
            self.selected_plugin = list_view.get_row_value(iterator, 2)
            info = self.core.pluginhandler.get_plugin_info(self.selected_plugin)

        self.PluginName.set_markup("<b>%(name)s</b>" % {"name": info.get("Name", self.selected_plugin)})
        self.PluginVersion.set_markup("<b>%(version)s</b>" % {"version": info.get("Version", '-')})
        self.PluginAuthor.set_markup("<b>%(author)s</b>" % {"author": ", ".join(info.get("Authors", '-'))})

        self.descr_textview.clear()
        self.descr_textview.append_line("%(description)s" % {
            "description": info.get("Description", '').replace(r'\n', '\n')})

        self.check_properties_button(self.selected_plugin)

    def on_plugin_toggle(self, list_view, iterator):

        plugin_id = list_view.get_row_value(iterator, 2)
        value = list_view.get_row_value(iterator, 0)
        list_view.set_row_value(iterator, 0, not value)

        if not value:
            self.core.pluginhandler.enable_plugin(plugin_id)
            self.enabled_plugins.append(plugin_id)
        else:
            self.core.pluginhandler.disable_plugin(plugin_id)
            self.enabled_plugins.remove(plugin_id)

        self.check_properties_button(plugin_id)

    def on_plugins_enable(self, *_args):

        if self.PluginsEnable.get_active():
            # Enable all selected plugins
            for plugin_id in self.enabled_plugins:
                self.core.pluginhandler.enable_plugin(plugin_id)

            self.check_properties_button(self.selected_plugin)
            return

        # Disable all plugins
        for plugin in self.core.pluginhandler.enabled_plugins.copy():
            self.core.pluginhandler.disable_plugin(plugin)

        self.PluginProperties.set_sensitive(False)

    @staticmethod
    def on_add_plugins(*_args):
        open_file_path(config.plugin_dir, create_folder=True)

    def on_plugin_properties(self, *_args):

        if self.selected_plugin is None:
            return

        PluginSettingsDialog(
            self.frame,
            self.preferences,
            plugin_id=self.selected_plugin,
            plugin_settings=self.core.pluginhandler.get_plugin_settings(self.selected_plugin)
        ).show()


class Preferences(UserInterface, Dialog):

    def __init__(self, frame, core):

        self.frame = frame
        self.core = core

        UserInterface.__init__(self, "ui/dialogs/preferences.ui")
        (
            self.apply_button,
            self.cancel_button,
            self.container,
            self.content,
            self.export_button,
            self.ok_button,
            self.preferences_list,
            self.viewport
        ) = self.widgets

        Dialog.__init__(
            self,
            parent=frame.window,
            content_box=self.container,
            buttons=[(self.cancel_button, Gtk.ResponseType.CANCEL),
                     (self.export_button, Gtk.ResponseType.HELP),
                     (self.apply_button, Gtk.ResponseType.APPLY),
                     (self.ok_button, Gtk.ResponseType.OK)],
            default_response=Gtk.ResponseType.OK,
            close_callback=self.on_close,
            title=_("Preferences"),
            width=960,
            height=650,
            close_destroy=False
        )

        # Scroll to focused widgets
        if GTK_API_VERSION == 3:
            self.viewport.set_focus_vadjustment(self.content.get_vadjustment())

        self.dialog.get_style_context().add_class("preferences-border")

        self.pages = {}
        self.page_ids = [
            ("Network", _("Network"), "network-wireless-symbolic"),
            ("UserInterface", _("User Interface"), "view-grid-symbolic"),
            ("Shares", _("Shares"), "folder-symbolic"),
            ("Downloads", _("Downloads"), "document-save-symbolic"),
            ("Uploads", _("Uploads"), "emblem-shared-symbolic"),
            ("Searches", _("Searches"), "system-search-symbolic"),
            ("UserInfo", _("User Info"), "avatar-default-symbolic"),
            ("Chats", _("Chats"), "insert-text-symbolic"),
            ("NowPlaying", _("Now Playing"), "folder-music-symbolic"),
            ("Logging", _("Logging"), "folder-documents-symbolic"),
            ("BannedUsers", _("Banned Users"), "action-unavailable-symbolic"),
            ("IgnoredUsers", _("Ignored Users"), "microphone-sensitivity-muted-symbolic"),
            ("Plugins", _("Plugins"), "list-add-symbolic"),
            ("UrlHandlers", _("URL Handlers"), "insert-link-symbolic")]

        for _page_id, label, icon_name in self.page_ids:
            box = Gtk.Box(margin_top=8, margin_bottom=8, margin_start=12, margin_end=42, spacing=12, visible=True)
            icon = Gtk.Image(icon_name=icon_name, visible=True)
            label = Gtk.Label(label=label, xalign=0, visible=True)

            if GTK_API_VERSION >= 4:
                box.append(icon)   # pylint: disable=no-member
                box.append(label)  # pylint: disable=no-member
            else:
                box.add(icon)   # pylint: disable=no-member
                box.add(label)  # pylint: disable=no-member

            self.preferences_list.insert(box, -1)

        self.set_active_page("Network")
        self.update_visuals()

    def update_visuals(self, scope=None):

        if not scope:
            for page in self.pages.values():
                self.update_visuals(page)

            scope = self

        for widget in scope.__dict__.values():
            update_widget_visuals(widget)

    def set_active_page(self, page_id):

        if page_id is None:
            return

        for index, (n_page_id, _label, _icon_name) in enumerate(self.page_ids):
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

        if isinstance(widget, Gtk.TextView):
            buffer = widget.get_buffer()
            start, end = buffer.get_bounds()

            return widget.get_buffer().get_text(start, end, True)

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

        elif isinstance(widget, Gtk.TextView):
            widget.get_buffer().set_text("")

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

        elif isinstance(widget, Gtk.TextView):
            if isinstance(value, (str, int)):
                widget.get_buffer().set_text(value)

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
            portmap_required = self.pages["Network"].portmap_required

        except KeyError:
            portmap_required = False

        try:
            rescan_required = self.pages["Shares"].rescan_required

        except KeyError:
            rescan_required = False

        try:
            theme_required = self.pages["UserInterface"].theme_required

        except KeyError:
            theme_required = False

        try:
            completion_required = self.pages["Chats"].completion_required

        except KeyError:
            completion_required = False

        try:
            ip_block_required = self.pages["BannedUsers"].ip_block_required

        except KeyError:
            ip_block_required = False

        try:
            search_required = self.pages["Searches"].search_required

        except KeyError:
            search_required = False

        for page in self.pages.values():
            for key, data in page.get_settings().items():
                options[key].update(data)

        return (portmap_required, rescan_required, theme_required, completion_required,
                ip_block_required, search_required, options)

    def update_settings(self, settings_closed=False):

        (portmap_required, rescan_required, theme_required, completion_required,
            ip_block_required, search_required, options) = self.get_settings()

        for key, data in options.items():
            config.sections[key].update(data)

        if portmap_required:
            self.core.upnp.add_port_mapping()

        if theme_required:
            # Dark mode
            dark_mode_state = config.sections["ui"]["dark_mode"]
            set_dark_mode(dark_mode_state)
            self.frame.dark_mode_action.set_state(GLib.Variant("b", dark_mode_state))

            set_global_font(config.sections["ui"]["globalfont"])

            self.frame.chatrooms.update_visuals()
            self.frame.privatechat.update_visuals()
            self.frame.search.update_visuals()
            self.frame.downloads.update_visuals()
            self.frame.uploads.update_visuals()
            self.frame.userinfo.update_visuals()
            self.frame.userbrowse.update_visuals()
            self.frame.userlist.update_visuals()
            self.frame.interests.update_visuals()

            self.frame.update_visuals()
            self.update_visuals()

            # Icons
            load_custom_icons(update=True)
            self.frame.tray_icon.update_icon_theme()

        if completion_required:
            self.frame.update_completions()

        if ip_block_required:
            self.core.network_filter.close_blocked_ip_connections()

        if search_required:
            self.frame.search.populate_search_history()

        # UPnP
        if not config.sections["server"]["upnp"]:
            self.core.upnp.cancel_timer()

        # Chatrooms
        self.frame.chatrooms.toggle_chat_buttons()
        self.frame.privatechat.toggle_chat_buttons()

        # Transfers
        self.core.transfers.update_limits()
        self.core.transfers.update_download_filters()
        self.core.transfers.check_upload_queue()

        # Tray icon
        if not config.sections["ui"]["trayicon"] and self.frame.tray_icon.is_visible():
            self.frame.tray_icon.hide()

        elif config.sections["ui"]["trayicon"] and not self.frame.tray_icon.is_visible():
            self.frame.tray_icon.load()

        # Main notebook
        self.frame.set_tab_positions()
        self.frame.set_main_tabs_visibility()
        self.frame.notebook.set_tab_text_colors()

        for i in range(self.frame.notebook.get_n_pages()):
            page = self.frame.notebook.get_nth_page(i)
            self.frame.set_tab_expand(page)

        # Other notebooks
        for notebook in (self.frame.chatrooms, self.frame.privatechat, self.frame.userinfo,
                         self.frame.userbrowse, self.frame.search):
            notebook.set_tab_closers()
            notebook.set_tab_text_colors()

        # Update configuration
        config.write_configuration()

        if config.need_config():
            self.frame.setup()

        if not settings_closed:
            return

        if rescan_required:
            self.core.shares.rescan_shares()

        self.close()

        if not config.sections["ui"]["trayicon"]:
            self.frame.show()

    @staticmethod
    def on_back_up_config_response(selected, _data):
        config.write_config_backup(selected)

    def on_back_up_config(self, *_args):

        FileChooserSave(
            parent=self.dialog,
            callback=self.on_back_up_config_response,
            initial_folder=os.path.dirname(config.filename),
            initial_file="config backup %s.tar.bz2" % (time.strftime("%Y-%m-%d %H_%M_%S")),
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

        page_id, _label, _icon_name = self.page_ids[row.get_index()]
        old_page = self.viewport.get_child()

        if old_page:
            if GTK_API_VERSION >= 4:
                self.viewport.set_child(None)
            else:
                self.viewport.remove(old_page)

        if page_id not in self.pages:
            self.pages[page_id] = page = getattr(sys.modules[__name__], page_id + "Frame")(self)
            page.set_settings()

            for obj in page.widgets:
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

            self.update_visuals(page)

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
