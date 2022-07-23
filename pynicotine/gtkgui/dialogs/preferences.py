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
from pynicotine.gtkgui.widgets.dialogs import dialog_hide
from pynicotine.gtkgui.widgets.dialogs import dialog_show
from pynicotine.gtkgui.widgets.dialogs import EntryDialog
from pynicotine.gtkgui.widgets.dialogs import generic_dialog
from pynicotine.gtkgui.widgets.dialogs import MessageDialog
from pynicotine.gtkgui.widgets.dialogs import PluginSettingsDialog
from pynicotine.gtkgui.widgets.textview import TextView
from pynicotine.gtkgui.widgets.theme import load_custom_icons
from pynicotine.gtkgui.widgets.theme import set_dark_mode
from pynicotine.gtkgui.widgets.theme import set_global_font
from pynicotine.gtkgui.widgets.theme import update_widget_visuals
from pynicotine.gtkgui.widgets.treeview import initialise_columns
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

        if self.core.protothread.listenport is None:
            self.CurrentPort.set_text(_("Listening port is not set"))
        else:
            text = _("Public IP address is <b>%(ip)s</b> and active listening port is <b>%(port)s</b>") % {
                "ip": self.core.user_ip_address or _("unknown"),
                "port": self.core.protothread.listenport
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

        password = dialog.get_response_value()

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
         self.LockIncoming, self.Main, self.RemoteDownloads, self.UploadDir, self.UploadsAllowed,
         self.UsernameSubfolders, self.VerifiedLabel) = self.widgets

        self.preferences = preferences
        self.frame = preferences.frame

        self.incomplete_dir = FileChooserButton(self.IncompleteDir, preferences.dialog, "folder")
        self.download_dir = FileChooserButton(self.DownloadDir, preferences.dialog, "folder")
        self.upload_dir = FileChooserButton(self.UploadDir, preferences.dialog, "folder")

        self.options = {
            "transfers": {
                "autoclear_downloads": self.AutoclearFinished,
                "lock": self.LockIncoming,
                "reverseorder": self.DownloadReverseOrder,
                "remotedownloads": self.RemoteDownloads,
                "uploadallowed": self.UploadsAllowed,
                "incompletedir": self.incomplete_dir,
                "downloaddir": self.download_dir,
                "uploaddir": self.upload_dir,
                "downloadfilters": self.FilterView,
                "enablefilters": self.DownloadFilter,
                "downloadlimit": self.DownloadSpeed,
                "downloadlimitalt": self.DownloadSpeedAlternative,
                "usernamesubfolders": self.UsernameSubfolders,
                "afterfinish": self.AfterDownload,
                "afterfolder": self.AfterFolder,
                "download_doubleclick": self.DownloadDoubleClick
            }
        }

        self.filterlist = Gtk.ListStore(
            str,
            bool
        )

        self.filtersiters = {}
        self.downloadfilters = []

        self.column_numbers = list(range(self.filterlist.get_n_columns()))
        cols = initialise_columns(
            self.frame, None, self.FilterView,
            ["filter", _("Filter"), 1, "text", None],
            ["escaped", _("Escaped"), 40, "toggle", None]
        )

        cols["filter"].set_sort_column_id(0)
        cols["escaped"].set_sort_column_id(1)

        cols["filter"].set_expand(True)

        renderers = cols["escaped"].get_cells()

        for render in renderers:
            render.connect('toggled', self.cell_toggle_callback, self.filterlist, 1)

        self.FilterView.set_model(self.filterlist)

    def set_settings(self):

        self.preferences.set_widgets_data(self.options)

        self.filtersiters.clear()
        self.filterlist.clear()

        if config.sections["transfers"]["downloadfilters"]:
            for dfilter in config.sections["transfers"]["downloadfilters"]:
                dfilter, escaped = dfilter
                self.filtersiters[dfilter] = self.filterlist.insert_with_valuesv(
                    -1, self.column_numbers, [str(dfilter), bool(escaped)]
                )

    def get_settings(self):

        try:
            uploadallowed = self.UploadsAllowed.get_active()
        except Exception:
            uploadallowed = 0

        if not self.RemoteDownloads.get_active():
            uploadallowed = 0

        return {
            "transfers": {
                "autoclear_downloads": self.AutoclearFinished.get_active(),
                "lock": self.LockIncoming.get_active(),
                "reverseorder": self.DownloadReverseOrder.get_active(),
                "remotedownloads": self.RemoteDownloads.get_active(),
                "uploadallowed": uploadallowed,
                "incompletedir": self.incomplete_dir.get_path(),
                "downloaddir": self.download_dir.get_path(),
                "uploaddir": self.upload_dir.get_path(),
                "downloadfilters": self.get_filter_list(),
                "enablefilters": self.DownloadFilter.get_active(),
                "downloadlimit": self.DownloadSpeed.get_value_as_int(),
                "downloadlimitalt": self.DownloadSpeedAlternative.get_value_as_int(),
                "usernamesubfolders": self.UsernameSubfolders.get_active(),
                "afterfinish": self.AfterDownload.get_text(),
                "afterfolder": self.AfterFolder.get_text(),
                "download_doubleclick": self.DownloadDoubleClick.get_active()
            }
        }

    def on_add_filter_response(self, dialog, _response_id, _data):

        dfilter = dialog.get_response_value()
        escaped = dialog.get_second_response_value()

        if dfilter in self.filtersiters:
            self.filterlist.set(self.filtersiters[dfilter], 0, dfilter, 1, escaped)
        else:
            self.filtersiters[dfilter] = self.filterlist.insert_with_valuesv(
                -1, self.column_numbers, [dfilter, escaped]
            )

        self.on_verify_filter()

    def on_add_filter(self, *_args):

        EntryDialog(
            parent=self.preferences.dialog,
            title=_("Add Download Filter"),
            message=_("Enter a new download filter:"),
            callback=self.on_add_filter_response,
            option_value=True,
            option_label="Escape this filter?",
            droplist=list(self.filtersiters.keys())
        ).show()

    def get_filter_list(self):

        self.downloadfilters = []

        download_filters = sorted(self.filtersiters.keys())

        for dfilter in download_filters:
            iterator = self.filtersiters[dfilter]
            dfilter = self.filterlist.get_value(iterator, 0)
            escaped = self.filterlist.get_value(iterator, 1)
            self.downloadfilters.append([dfilter, int(escaped)])

        return self.downloadfilters

    def on_edit_filter_response(self, dialog, _response_id, _data):

        new_dfilter = dialog.get_response_value()
        escaped = dialog.get_second_response_value()

        dfilter = self.get_selected_filter()

        if not dfilter:
            return

        iterator = self.filtersiters[dfilter]

        if new_dfilter in self.filtersiters:
            self.filterlist.set(self.filtersiters[new_dfilter], 0, new_dfilter, 1, escaped)
        else:
            self.filtersiters[new_dfilter] = self.filterlist.insert_with_valuesv(
                -1, self.column_numbers, [new_dfilter, escaped]
            )
            del self.filtersiters[dfilter]
            self.filterlist.remove(iterator)

        self.on_verify_filter()

    def on_edit_filter(self, *_args):

        dfilter = self.get_selected_filter()

        if not dfilter:
            return

        iterator = self.filtersiters[dfilter]
        escapedvalue = self.filterlist.get_value(iterator, 1)

        EntryDialog(
            parent=self.preferences.dialog,
            title=_("Edit Download Filter"),
            message=_("Modify the following download filter:"),
            callback=self.on_edit_filter_response,
            default=dfilter,
            option_value=escapedvalue,
            option_label="Escape this filter?",
            droplist=list(self.filtersiters.keys())
        ).show()

    def get_selected_filter(self):

        model, paths = self.FilterView.get_selection().get_selected_rows()

        for path in paths:
            iterator = model.get_iter(path)
            return model.get_value(iterator, 0)

        return None

    def on_remove_filter(self, *_args):

        dfilter = self.get_selected_filter()

        if not dfilter:
            return

        iterator = self.filtersiters[dfilter]
        self.filterlist.remove(iterator)

        del self.filtersiters[dfilter]

        self.on_verify_filter()

    def on_default_filters(self, *_args):

        self.filtersiters = {}
        self.filterlist.clear()

        for dfilter in config.defaults["transfers"]["downloadfilters"]:
            dfilter, escaped = dfilter
            self.filtersiters[dfilter] = self.filterlist.insert_with_valuesv(
                -1, self.column_numbers, [dfilter, escaped]
            )

        self.on_verify_filter()

    def on_verify_filter(self, *_args):

        outfilter = "(\\\\("

        download_filters = sorted(self.filtersiters.keys())

        proccessedfilters = []
        failed = {}

        for dfilter in download_filters:

            iterator = self.filtersiters[dfilter]
            dfilter = self.filterlist.get_value(iterator, 0)
            escaped = self.filterlist.get_value(iterator, 1)

            if escaped:
                dfilter = re.escape(dfilter)
                dfilter = dfilter.replace("\\*", ".*")
            else:
                # Avoid "Nothing to repeat" error
                dfilter = dfilter.replace("*", "\\*").replace("+", "\\+")

            try:
                re.compile("(" + dfilter + ")")
                outfilter += dfilter
                proccessedfilters.append(dfilter)
            except Exception as error:
                failed[dfilter] = error

            if filter is not download_filters[-1]:
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

    def cell_toggle_callback(self, _widget, index, _treeview, pos):

        iterator = self.filterlist.get_iter(index)
        value = self.filterlist.get_value(iterator, pos)

        self.filterlist.set(iterator, pos, not value)

        self.on_verify_filter()


class SharesFrame(UserInterface):

    def __init__(self, preferences):

        super().__init__("ui/settings/shares.ui")

        # pylint: disable=invalid-name
        self.BuddySharesTrustedOnly, self.Main, self.RescanOnStartup, self.Shares = self.widgets

        self.preferences = preferences
        self.frame = preferences.frame

        self.rescan_required = False
        self.shareddirs = []
        self.bshareddirs = []

        self.shareslist = Gtk.ListStore(
            str,
            str,
            bool
        )

        self.Shares.set_model(self.shareslist)
        self.column_numbers = list(range(self.shareslist.get_n_columns()))
        cols = initialise_columns(
            self.frame, None, self.Shares,
            ["virtual_folder", _("Virtual Folder"), 1, "text", None],
            ["folder", _("Folder"), 150, "text", None],
            ["buddies", _("Buddy-only"), 0, "toggle", None],
        )

        cols["virtual_folder"].set_sort_column_id(0)
        cols["folder"].set_sort_column_id(1)
        cols["buddies"].set_sort_column_id(2)

        cols["virtual_folder"].set_expand(True)
        cols["folder"].set_expand(True)

        for render in cols["buddies"].get_cells():
            render.connect('toggled', self.cell_toggle_callback, self.Shares)

        self.options = {
            "transfers": {
                "rescanonstartup": self.RescanOnStartup,
                "buddysharestrustedonly": self.BuddySharesTrustedOnly
            }
        }

    def set_settings(self):

        transfers = config.sections["transfers"]
        self.shareslist.clear()

        self.preferences.set_widgets_data(self.options)

        for virtual, folder, *_unused in transfers["buddyshared"]:

            self.shareslist.insert_with_valuesv(-1, self.column_numbers, [
                str(virtual),
                str(folder),
                True
            ])

        for virtual, folder, *_unused in transfers["shared"]:

            self.shareslist.insert_with_valuesv(-1, self.column_numbers, [
                str(virtual),
                str(folder),
                False
            ])

        self.shareddirs = transfers["shared"][:]
        self.bshareddirs = transfers["buddyshared"][:]

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

        if buddy_only == self.shareslist.get_value(iterator, 2):
            return

        virtual = self.shareslist.get_value(iterator, 0)
        directory = self.shareslist.get_value(iterator, 1)
        share = (virtual, directory)
        self.rescan_required = True

        self.shareslist.set_value(iterator, 2, buddy_only)

        if buddy_only:
            self.shareddirs.remove(share)
            self.bshareddirs.append(share)
            return

        self.bshareddirs.remove(share)
        self.shareddirs.append(share)

    def cell_toggle_callback(self, _widget, index, treeview):

        store = treeview.get_model()
        iterator = store.get_iter(index)

        buddy_only = not self.shareslist.get_value(iterator, 2)
        self.set_shared_dir_buddy_only(iterator, buddy_only)

    def add_shared_dir(self, folder):

        if folder is None:
            return

        # If the directory is already shared
        if folder in (x[1] for x in self.shareddirs + self.bshareddirs):
            return

        virtual = self.get_normalized_virtual_name(os.path.basename(os.path.normpath(folder)))
        iterator = self.shareslist.insert_with_valuesv(-1, self.column_numbers, [
            virtual,
            folder,
            False
        ])

        self.Shares.set_cursor(self.shareslist.get_path(iterator))
        self.Shares.grab_focus()

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

    def on_edit_shared_dir_response(self, dialog, _response_id, path):

        virtual = dialog.get_response_value()
        buddy_only = dialog.get_second_response_value()

        if not virtual:
            return

        virtual = self.get_normalized_virtual_name(virtual)
        iterator = self.shareslist.get_iter(path)
        folder = self.shareslist.get_value(iterator, 1)
        old_virtual = self.shareslist.get_value(iterator, 0)
        old_mapping = (old_virtual, folder)
        new_mapping = (virtual, folder)

        if old_mapping in self.bshareddirs:
            shared_dirs = self.bshareddirs
        else:
            shared_dirs = self.shareddirs

        shared_dirs.remove(old_mapping)
        shared_dirs.append(new_mapping)

        self.shareslist.set_value(iterator, 0, virtual)
        self.set_shared_dir_buddy_only(iterator, buddy_only)
        self.rescan_required = True

    def on_edit_shared_dir(self, *_args):

        model, paths = self.Shares.get_selection().get_selected_rows()

        for path in paths:
            iterator = model.get_iter(path)
            virtual_name = model.get_value(iterator, 0)
            folder = model.get_value(iterator, 1)
            buddy_only = model.get_value(iterator, 2)

            EntryDialog(
                parent=self.preferences.dialog,
                title=_("Edit Shared Folder"),
                message=_("Enter new virtual name for '%(dir)s':") % {'dir': folder},
                default=virtual_name,
                option_value=buddy_only,
                option_label="Share with buddies only?",
                callback=self.on_edit_shared_dir_response,
                callback_data=path
            ).show()
            return

    def on_remove_shared_dir(self, *_args):

        model, paths = self.Shares.get_selection().get_selected_rows()

        for path in reversed(paths):
            iterator = model.get_iter(path)
            virtual = model.get_value(iterator, 0)
            folder = model.get_value(iterator, 1)
            mapping = (virtual, folder)

            if mapping in self.bshareddirs:
                self.bshareddirs.remove(mapping)
            else:
                self.shareddirs.remove(mapping)

            model.remove(iterator)

        if paths:
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

        self.options = {
            "server": {
                "ignorelist": self.IgnoredUsers,
                "ipignorelist": self.IgnoredIPs
            }
        }

        self.ignored_users = []
        self.ignorelist = Gtk.ListStore(str)

        self.user_column_numbers = list(range(self.ignorelist.get_n_columns()))
        cols = initialise_columns(
            self.frame, None, self.IgnoredUsers,
            ["username", _("Username"), -1, "text", None]
        )
        cols["username"].set_sort_column_id(0)

        self.IgnoredUsers.set_model(self.ignorelist)

        self.ignored_ips = {}
        self.ignored_ips_list = Gtk.ListStore(str, str)

        self.ip_column_numbers = list(range(self.ignored_ips_list.get_n_columns()))
        cols = initialise_columns(
            self.frame, None, self.IgnoredIPs,
            ["ip_address", _("IP Address"), 20, "text", None],
            ["user", _("User"), -1, "text", None]
        )
        cols["ip_address"].set_sort_column_id(0)
        cols["user"].set_sort_column_id(1)

        cols["ip_address"].set_expand(True)

        self.IgnoredIPs.set_model(self.ignored_ips_list)

    def set_settings(self):
        server = config.sections["server"]

        self.ignorelist.clear()
        self.ignored_ips_list.clear()
        self.ignored_users = []
        self.ignored_ips = {}
        self.preferences.set_widgets_data(self.options)

        if server["ignorelist"] is not None:
            self.ignored_users = server["ignorelist"][:]

        if server["ipignorelist"] is not None:
            self.ignored_ips = server["ipignorelist"].copy()
            for ip_address, user in self.ignored_ips.items():
                self.ignored_ips_list.insert_with_valuesv(-1, self.ip_column_numbers, [
                    str(ip_address), str(user)
                ])

    def get_settings(self):
        return {
            "server": {
                "ignorelist": self.ignored_users[:],
                "ipignorelist": self.ignored_ips.copy()
            }
        }

    def on_add_ignored_response(self, dialog, _response_id, _data):

        user = dialog.get_response_value()

        if user and user not in self.ignored_users:
            self.ignored_users.append(user)
            self.ignorelist.insert_with_valuesv(-1, self.user_column_numbers, [str(user)])

    def on_add_ignored(self, *_args):

        EntryDialog(
            parent=self.preferences.dialog,
            title=_("Ignore User"),
            message=_("Enter the name of the user you want to ignore:"),
            callback=self.on_add_ignored_response
        ).show()

    def on_remove_ignored(self, *_args):

        model, paths = self.IgnoredUsers.get_selection().get_selected_rows()

        for path in reversed(paths):
            iterator = model.get_iter(path)
            user = model.get_value(iterator, 0)

            model.remove(iterator)
            self.ignored_users.remove(user)

    def on_add_ignored_ip_response(self, dialog, _response_id, _data):

        ip_address = dialog.get_response_value()

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
            self.ignored_ips_list.insert_with_valuesv(-1, self.ip_column_numbers, [ip_address, ""])

    def on_add_ignored_ip(self, *_args):

        EntryDialog(
            parent=self.preferences.dialog,
            title=_("Ignore IP Address"),
            message=_("Enter an IP address you want to ignore:") + " " + _("* is a wildcard"),
            callback=self.on_add_ignored_ip_response
        ).show()

    def on_remove_ignored_ip(self, *_args):

        model, paths = self.IgnoredIPs.get_selection().get_selected_rows()

        for path in reversed(paths):
            iterator = model.get_iter(path)
            ip_address = model.get_value(iterator, 0)

            model.remove(iterator)
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

        self.options = {
            "server": {
                "banlist": self.BannedList,
                "ipblocklist": self.BlockedList
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

        self.banlist = []
        self.banlist_model = Gtk.ListStore(str)

        self.ban_column_numbers = list(range(self.banlist_model.get_n_columns()))
        cols = initialise_columns(
            self.frame, None, self.BannedList,
            ["username", _("Username"), -1, "text", None]
        )
        cols["username"].set_sort_column_id(0)

        self.BannedList.set_model(self.banlist_model)

        self.blocked_list = {}
        self.blocked_list_model = Gtk.ListStore(str, str)

        self.block_column_numbers = list(range(self.blocked_list_model.get_n_columns()))
        cols = initialise_columns(
            self.frame, None, self.BlockedList,
            ["ip_address", _("IP Address"), 20, "text", None],
            ["user", _("User"), -1, "text", None]
        )
        cols["ip_address"].set_sort_column_id(0)
        cols["user"].set_sort_column_id(1)

        cols["ip_address"].set_expand(True)

        self.BlockedList.set_model(self.blocked_list_model)

    def set_settings(self):

        self.banlist_model.clear()
        self.blocked_list_model.clear()

        self.banlist = config.sections["server"]["banlist"][:]
        self.preferences.set_widgets_data(self.options)

        if config.sections["transfers"]["geoblockcc"] is not None:
            self.GeoBlockCC.set_text(config.sections["transfers"]["geoblockcc"][0])

        if config.sections["server"]["ipblocklist"] is not None:
            self.blocked_list = config.sections["server"]["ipblocklist"].copy()
            for blocked, user in config.sections["server"]["ipblocklist"].items():
                self.blocked_list_model.insert_with_valuesv(-1, self.block_column_numbers, [
                    str(blocked),
                    str(user)
                ])

        self.ip_block_required = False

    def get_settings(self):

        self.ip_block_required = False

        return {
            "server": {
                "banlist": self.banlist[:],
                "ipblocklist": self.blocked_list.copy()
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

        user = dialog.get_response_value()

        if user and user not in self.banlist:
            self.banlist.append(user)
            self.banlist_model.insert_with_valuesv(-1, self.ban_column_numbers, [user])

    def on_add_banned(self, *_args):

        EntryDialog(
            parent=self.preferences.dialog,
            title=_("Ban User"),
            message=_("Enter the name of the user you want to ban:"),
            callback=self.on_add_banned_response
        ).show()

    def on_remove_banned(self, *_args):

        model, paths = self.BannedList.get_selection().get_selected_rows()

        for path in reversed(paths):
            iterator = model.get_iter(path)
            user = model.get_value(iterator, 0)

            model.remove(iterator)
            self.banlist.remove(user)

    def on_add_blocked_response(self, dialog, _response_id, _data):

        ip_address = dialog.get_response_value()

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

        if ip_address not in self.blocked_list:
            self.blocked_list[ip_address] = ""
            self.blocked_list_model.insert_with_valuesv(-1, self.block_column_numbers, [ip_address, ""])
            self.ip_block_required = True

    def on_add_blocked(self, *_args):

        EntryDialog(
            parent=self.preferences.dialog,
            title=_("Block IP Address"),
            message=_("Enter an IP address you want to block:") + " " + _("* is a wildcard"),
            callback=self.on_add_blocked_response
        ).show()

    def on_remove_blocked(self, *_args):

        model, paths = self.BlockedList.get_selection().get_selected_rows()

        for path in reversed(paths):
            iterator = model.get_iter(path)
            ip_address = model.get_value(iterator, 0)

            self.blocked_list_model.remove(iterator)
            del self.blocked_list[ip_address]


class ChatsFrame(UserInterface):

    def __init__(self, preferences):

        super().__init__("ui/settings/chats.ui")

        # pylint: disable=invalid-name
        (self.CensorCheck, self.CensorList,
         self.CensorReplaceCombo, self.CharactersCompletion, self.ChatRoomFormat,
         self.CompleteAliasesCheck, self.CompleteBuddiesCheck, self.CompleteCommandsCheck, self.CompleteRoomNamesCheck,
         self.CompleteUsersInRoomsCheck, self.CompletionCycleCheck, self.CompletionDropdownCheck,
         self.CompletionTabCheck, self.Main, self.OneMatchCheck, self.PrivateChatFormat,
         self.PrivateLogLines, self.PrivateMessage, self.ReadRoomLogs,
         self.ReopenPrivateChats, self.ReplaceCheck, self.ReplacementList,
         self.RoomLogLines, self.RoomMessage, self.SpellCheck,
         self.TTSCommand, self.TextToSpeech) = self.widgets

        self.preferences = preferences
        self.frame = preferences.frame
        self.completion_required = False

        self.options = {
            "logging": {
                "readroomlines": self.RoomLogLines,
                "readprivatelines": self.PrivateLogLines,
                "readroomlogs": self.ReadRoomLogs,
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
                "censored": self.CensorList,
                "censorwords": self.CensorCheck,
                "censorfill": self.CensorReplaceCombo,
                "autoreplaced": self.ReplacementList,
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

        self.censor_list_model = Gtk.ListStore(str)

        cols = initialise_columns(
            self.frame, None, self.CensorList,
            ["pattern", _("Pattern"), -1, "edit", None]
        )
        cols["pattern"].set_sort_column_id(0)

        self.CensorList.set_model(self.censor_list_model)

        renderers = cols["pattern"].get_cells()
        for render in renderers:
            render.connect('edited', self.censor_cell_edited_callback, self.CensorList, 0)

        self.replace_list_model = Gtk.ListStore(str, str)

        self.column_numbers = list(range(self.replace_list_model.get_n_columns()))
        cols = initialise_columns(
            self.frame, None, self.ReplacementList,
            ["pattern", _("Pattern"), 50, "edit", None],
            ["replacement", _("Replacement"), -1, "edit", None]
        )
        cols["pattern"].set_sort_column_id(0)
        cols["replacement"].set_sort_column_id(1)

        cols["pattern"].set_expand(True)

        self.ReplacementList.set_model(self.replace_list_model)

        pos = 0
        for column in cols.values():
            renderers = column.get_cells()
            for render in renderers:
                render.connect('edited', self.replace_cell_edited_callback, self.ReplacementList, pos)

            pos += 1

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

    @staticmethod
    def censor_cell_edited_callback(_widget, index, value, treeview, pos):

        store = treeview.get_model()
        iterator = store.get_iter(index)

        if value != "" and not value.isspace() and len(value) > 2:
            store.set(iterator, pos, value)
        else:
            store.remove(iterator)

    @staticmethod
    def replace_cell_edited_callback(_widget, index, value, treeview, pos):

        store = treeview.get_model()
        iterator = store.get_iter(index)
        store.set(iterator, pos, value)

    def on_add_censored_response(self, dialog, _response_id, _data):

        pattern = dialog.get_response_value()

        if pattern:
            self.censor_list_model.insert_with_valuesv(-1, [0], [pattern])

    def on_add_censored(self, *_args):

        EntryDialog(
            parent=self.preferences.dialog,
            title=_("Censor Pattern"),
            message=_("Enter a pattern you want to censor. Add spaces around the pattern if you don't "
                      "want to match strings inside words (may fail at the beginning and end of lines)."),
            callback=self.on_add_censored_response
        ).show()

    def on_remove_censored(self, *_args):

        model, paths = self.CensorList.get_selection().get_selected_rows()

        for path in reversed(paths):
            iterator = model.get_iter(path)
            model.remove(iterator)

    def on_add_replacement(self, *_args):

        iterator = self.replace_list_model.insert_with_valuesv(-1, self.column_numbers, ["", ""])
        selection = self.ReplacementList.get_selection()
        selection.select_iter(iterator)
        col = self.ReplacementList.get_column(0)

        self.ReplacementList.set_cursor(self.replace_list_model.get_path(iterator), col, True)

    def on_remove_replacement(self, *_args):

        model, paths = self.ReplacementList.get_selection().get_selected_rows()

        for path in reversed(paths):
            iterator = model.get_iter(path)
            model.remove(iterator)

    def set_settings(self):

        self.censor_list_model.clear()
        self.replace_list_model.clear()

        self.preferences.set_widgets_data(self.options)

        try:
            gi.require_version('Gspell', '1')
            from gi.repository import Gspell  # noqa: F401; pylint:disable=unused-import

        except (ImportError, ValueError):
            self.SpellCheck.hide()

        for word, replacement in config.sections["words"]["autoreplaced"].items():
            self.replace_list_model.insert_with_valuesv(-1, self.column_numbers, [
                str(word),
                str(replacement)
            ])

        self.completion_required = False

    def get_settings(self):

        self.completion_required = False
        censored = []
        autoreplaced = {}

        iterator = self.censor_list_model.get_iter_first()

        while iterator is not None:
            word = self.censor_list_model.get_value(iterator, 0)
            censored.append(word)
            iterator = self.censor_list_model.iter_next(iterator)

        iterator = self.replace_list_model.get_iter_first()

        while iterator is not None:
            word = self.replace_list_model.get_value(iterator, 0)
            replacement = self.replace_list_model.get_value(iterator, 1)
            autoreplaced[word] = replacement
            iterator = self.replace_list_model.iter_next(iterator)

        return {
            "logging": {
                "readroomlogs": self.ReadRoomLogs.get_active(),
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
                "censored": censored,
                "censorwords": self.CensorCheck.get_active(),
                "censorfill": self.CensorReplaceCombo.get_active_id(),
                "autoreplaced": autoreplaced,
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
        (self.ClearFilterHistorySuccess,
         self.ClearSearchHistorySuccess, self.EnableFilters, self.EnableSearchHistory, self.FilterBR, self.FilterCC,
         self.FilterFree, self.FilterIn, self.FilterOut, self.FilterSize, self.FilterType,
         self.Main, self.MaxDisplayedResults, self.MaxResults, self.MinSearchChars,
         self.RemoveSpecialChars, self.ShowPrivateSearchResults, self.ShowSearchHelp, self.ToggleResults) = self.widgets

        self.preferences = preferences
        self.frame = preferences.frame
        self.search_required = False

        self.filter_help = UserInterface("ui/popovers/searchfilters.ui")
        self.filter_help.container, self.filter_help.popover = self.filter_help.widgets
        self.ShowSearchHelp.set_popover(self.filter_help.popover)

        if GTK_API_VERSION >= 4:
            # Scroll to the focused widget
            self.filter_help.container.get_child().set_scroll_to_focus(True)

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
                    self.FilterType.get_text()
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
        (self.FileManagerCombo, self.Handler, self.Main, self.ProtocolCombo, self.ProtocolHandlers,
         self.audioPlayerCombo) = self.widgets

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

        self.protocolmodel = Gtk.ListStore(str, str)
        self.protocols = {}

        self.column_numbers = list(range(self.protocolmodel.get_n_columns()))
        cols = initialise_columns(
            self.frame, None, self.ProtocolHandlers,
            ["protocol", _("Protocol"), 1, "text", None],
            ["command", _("Command"), -1, "edit", None]
        )

        cols["protocol"].set_sort_column_id(0)
        cols["command"].set_sort_column_id(1)

        cols["protocol"].set_expand(True)

        self.ProtocolHandlers.set_model(self.protocolmodel)

        renderers = cols["command"].get_cells()
        for render in renderers:
            render.connect('edited', self.cell_edited_callback, self.ProtocolHandlers, 1)

    def set_settings(self):

        self.protocolmodel.clear()
        self.protocols.clear()

        self.preferences.set_widgets_data(self.options)

        for key in config.sections["urls"]["protocols"].keys():
            if config.sections["urls"]["protocols"][key][-1:] == "&":
                command = config.sections["urls"]["protocols"][key][:-1].rstrip()
            else:
                command = config.sections["urls"]["protocols"][key]

            self.protocols[key] = self.protocolmodel.insert_with_valuesv(-1, self.column_numbers, [
                str(key), str(command)
            ])

    def get_settings(self):

        protocols = {}
        iterator = self.protocolmodel.get_iter_first()

        while iterator is not None:
            protocol = self.protocolmodel.get_value(iterator, 0)
            handler = self.protocolmodel.get_value(iterator, 1)
            protocols[protocol] = handler

            iterator = self.protocolmodel.iter_next(iterator)

        return {
            "urls": {
                "protocols": protocols
            },
            "ui": {
                "filemanager": self.FileManagerCombo.get_active_text()
            },
            "players": {
                "default": self.audioPlayerCombo.get_active_text()
            }
        }

    @staticmethod
    def cell_edited_callback(_widget, index, value, treeview, pos):

        store = treeview.get_model()
        iterator = store.get_iter(index)
        store.set(iterator, pos, value)

    def on_add(self, *_args):

        protocol = self.ProtocolCombo.get_active_text()
        command = self.Handler.get_active_text()

        self.ProtocolCombo.get_child().set_text("")
        self.Handler.get_child().set_text("")

        if protocol in self.protocols:
            self.protocolmodel.set(self.protocols[protocol], 1, command)
        else:
            self.protocols[protocol] = self.protocolmodel.insert_with_valuesv(
                -1, self.column_numbers, [protocol, command]
            )

    def on_remove(self, *_args):

        model, paths = self.ProtocolHandlers.get_selection().get_selected_rows()

        for path in reversed(paths):
            iterator = model.get_iter(path)
            protocol = self.protocolmodel.get_value(iterator, 0)

            model.remove(iterator)
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
                legend += _("Length")
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

        self.plugins_model = Gtk.ListStore(bool, str, str)
        self.plugins = []
        self.pluginsiters = {}
        self.selected_plugin = None
        self.descr_textview = TextView(self.PluginDescription)

        self.column_numbers = list(range(self.plugins_model.get_n_columns()))
        cols = initialise_columns(
            self.frame, None, self.PluginTreeView,
            ["enabled", _("Enabled"), 0, "toggle", None],
            ["plugin", _("Plugin"), -1, "text", None]
        )

        cols["enabled"].set_sort_column_id(0)
        cols["plugin"].set_sort_column_id(1)

        cols["enabled"].get_widget().hide()

        renderers = cols["enabled"].get_cells()

        for render in renderers:
            render.connect('toggled', self.cell_toggle_callback, self.PluginTreeView)

        self.PluginTreeView.set_model(self.plugins_model)

    def set_settings(self):

        self.preferences.set_widgets_data(self.options)

        self.on_plugins_enable()
        self.pluginsiters = {}
        self.plugins_model.clear()
        plugins = sorted(self.core.pluginhandler.list_installed_plugins())

        for plugin in plugins:
            try:
                info = self.core.pluginhandler.get_plugin_info(plugin)
            except OSError:
                continue

            enabled = (plugin in config.sections["plugins"]["enabled"])
            self.pluginsiters[filter] = self.plugins_model.insert_with_valuesv(
                -1, self.column_numbers, [enabled, info.get('Name', plugin), plugin]
            )

        return {}

    def get_enabled_plugins(self):

        enabled_plugins = []

        for plugin in self.plugins_model:
            enabled = self.plugins_model.get_value(plugin.iter, 0)

            if enabled:
                plugin_name = self.plugins_model.get_value(plugin.iter, 2)
                enabled_plugins.append(plugin_name)

        return enabled_plugins

    def get_settings(self):

        return {
            "plugins": {
                "enable": self.PluginsEnable.get_active(),
                "enabled": self.get_enabled_plugins()
            }
        }

    def check_properties_button(self, plugin):
        self.PluginProperties.set_sensitive(bool(self.core.pluginhandler.get_plugin_settings(plugin)))

    def on_select_plugin(self, selection):

        model, iterator = selection.get_selected()

        if iterator is None:
            self.selected_plugin = _("No Plugin Selected")
            info = {}
        else:
            self.selected_plugin = model.get_value(iterator, 2)
            info = self.core.pluginhandler.get_plugin_info(self.selected_plugin)

        self.PluginName.set_markup("<b>%(name)s</b>" % {"name": info.get("Name", self.selected_plugin)})
        self.PluginVersion.set_markup("<b>%(version)s</b>" % {"version": info.get("Version", '-')})
        self.PluginAuthor.set_markup("<b>%(author)s</b>" % {"author": ", ".join(info.get("Authors", '-'))})

        self.descr_textview.clear()
        self.descr_textview.append_line("%(description)s" % {
            "description": info.get("Description", '').replace(r'\n', '\n')})

        self.check_properties_button(self.selected_plugin)

    def cell_toggle_callback(self, _widget, index, _treeview):

        iterator = self.plugins_model.get_iter(index)
        plugin = self.plugins_model.get_value(iterator, 2)
        value = self.plugins_model.get_value(iterator, 0)
        self.plugins_model.set(iterator, 0, not value)

        if not value:
            self.core.pluginhandler.enable_plugin(plugin)
        else:
            self.core.pluginhandler.disable_plugin(plugin)

        self.check_properties_button(plugin)

    def on_plugins_enable(self, *_args):

        if self.PluginsEnable.get_active():
            # Enable all selected plugins
            for plugin in self.get_enabled_plugins():
                self.core.pluginhandler.enable_plugin(plugin)

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


class Preferences(UserInterface):

    def __init__(self, frame, core):

        super().__init__("ui/dialogs/preferences.ui")
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

        self.frame = frame
        self.core = core
        self.dialog = generic_dialog(
            parent=frame.window,
            content_box=self.container,
            buttons=[(self.cancel_button, Gtk.ResponseType.CANCEL),
                     (self.export_button, Gtk.ResponseType.HELP),
                     (self.apply_button, Gtk.ResponseType.APPLY),
                     (self.ok_button, Gtk.ResponseType.OK)],
            default_response=Gtk.ResponseType.OK,
            quit_callback=self.on_cancel,
            title=_("Preferences"),
            width=960,
            height=650
        )

        # Scroll to focused widgets
        if GTK_API_VERSION >= 4:
            self.viewport.set_scroll_to_focus(True)
        else:
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

        if isinstance(widget, Gtk.TreeView) and widget.get_model().get_n_columns() == 1:
            wlist = []
            iterator = widget.get_model().get_iter_first()

            while iterator:
                word = widget.get_model().get_value(iterator, 0)

                if word is not None:
                    wlist.append(word)

                iterator = widget.get_model().iter_next(iterator)

            return wlist

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

        elif isinstance(widget, Gtk.TreeView) and isinstance(value, list) and widget.get_model().get_n_columns() == 1:
            model = widget.get_model()
            column_numbers = list(range(model.get_n_columns()))

            for item in value:
                model.insert_with_valuesv(-1, column_numbers, [str(item)])

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

        self.hide()

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
        self.hide()

    def on_apply(self, *_args):
        self.update_settings()

    def on_ok(self, *_args):
        self.update_settings(settings_closed=True)

    def hide(self):

        # Scroll to the top
        self.content.get_vadjustment().set_value(0)

        dialog_hide(self.dialog)

    def show(self, *_args):
        dialog_show(self.dialog)
