# COPYRIGHT (C) 2020-2021 Nicotine+ Team
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
from gi.repository import GdkPixbuf
from gi.repository import GObject
from gi.repository import Gtk

from pynicotine.config import config
from pynicotine.gtkgui.utils import load_ui_elements
from pynicotine.gtkgui.utils import open_file_path
from pynicotine.gtkgui.utils import open_uri
from pynicotine.gtkgui.widgets.filechooser import FileChooserButton
from pynicotine.gtkgui.widgets.filechooser import choose_dir
from pynicotine.gtkgui.widgets.filechooser import save_file
from pynicotine.gtkgui.widgets.dialogs import dialog_hide
from pynicotine.gtkgui.widgets.dialogs import entry_dialog
from pynicotine.gtkgui.widgets.dialogs import generic_dialog
from pynicotine.gtkgui.widgets.dialogs import message_dialog
from pynicotine.gtkgui.widgets.dialogs import set_dialog_properties
from pynicotine.gtkgui.widgets.textview import append_line
from pynicotine.gtkgui.widgets.theme import update_widget_visuals
from pynicotine.gtkgui.widgets.treeview import initialise_columns
from pynicotine.logfacility import log
from pynicotine.utils import unescape


class BuildFrame:
    """ This class build the individual frames from the settings window """

    def __init__(self, window):

        self.frame = self.p.frame

        # Build the frame
        load_ui_elements(self, os.path.join(self.frame.gui_dir, "ui", "settings", window + ".ui"))


class NetworkFrame(BuildFrame):

    def __init__(self, parent):

        self.p = parent

        BuildFrame.__init__(self, "network")

        self.needportmap = False

        self.options = {
            "server": {
                "server": None,
                "login": self.Login,
                "portrange": None,
                "interface": self.Interface,
                "upnp": self.UseUPnP,
                "upnp_interval": self.UPnPInterval,
                "auto_connect_startup": self.AutoConnectStartup,
                "ctcpmsgs": self.ctcptogglebutton
            }
        }

    def set_settings(self):

        self.p.set_widgets_data(self.options)

        server = config.sections["server"]

        if server["server"] is not None:
            self.Server.set_text("%s:%i" % (server["server"][0], server["server"][1]))

        if self.frame.np.waitport is None:
            self.CurrentPort.set_text(_("Listening port is not set"))
        else:
            self.CurrentPort.set_markup(_("Active listening port is <b>%(port)s</b>") %
                                        {"port": self.frame.np.waitport})

        if self.frame.np.ipaddress is None:
            self.YourIP.set_text(_("Your IP address has not been retrieved from the server"))
        else:
            self.YourIP.set_markup(_("Your IP address is <b>%(ip)s</b>") % {"ip": self.frame.np.ipaddress})

        if server["portrange"] is not None:
            self.FirstPort.set_value(server["portrange"][0])
            self.LastPort.set_value(server["portrange"][1])

        if server["ctcpmsgs"] is not None:
            self.ctcptogglebutton.set_active(not server["ctcpmsgs"])

        self.needportmap = False

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

    def get_settings(self):

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
                "interface": self.Interface.get_active_text(),
                "upnp": self.UseUPnP.get_active(),
                "upnp_interval": self.UPnPInterval.get_value_as_int(),
                "auto_connect_startup": self.AutoConnectStartup.get_active(),
                "ctcpmsgs": not self.ctcptogglebutton.get_active()
            }
        }

    def on_change_password_response(self, dialog, response_id, data):

        password = dialog.get_response_value()
        dialog.destroy()

        if response_id != Gtk.ResponseType.OK:
            return

        if not password:
            self.on_change_password()
            return

        if not self.p.frame.np.logged_in:
            config.sections["server"]["passw"] = password
            config.write_configuration()
            return

        self.frame.np.request_change_password(password)

    def on_change_password(self, *args):

        if self.p.frame.np.logged_in:
            message = _("Enter a new password for your Soulseek account:")
        else:
            message = (_("You are currently disconnected from the server. If you are attempting to change "
                         "the password of an existing Soulseek account, you need to be logged into the account "
                         "in question.")
                       + "\n\n"
                       + _("Enter password to use when logging in:"))

        entry_dialog(
            parent=self.p.dialog,
            title=_("Change Password"),
            message=message,
            visibility=False,
            callback=self.on_change_password_response
        )

    def on_check_port(self, widget):
        open_uri('='.join(['http://tools.slsknet.org/porttest.php?port',
                 str(self.frame.np.waitport)]), self.p.dialog)

    def on_toggle_upnp(self, widget, *args):

        active = widget.get_active()
        self.needportmap = active

        self.UPnPIntervalL1.set_sensitive(active)
        self.UPnPInterval.set_sensitive(active)

    def on_modify_upnp_interval(self, widget, *args):
        self.needportmap = True


class DownloadsFrame(BuildFrame):

    def __init__(self, parent):

        self.p = parent

        BuildFrame.__init__(self, "downloads")

        self.needrescan = False

        self.IncompleteDir = FileChooserButton(
            self.IncompleteDir, parent.dialog, "folder"
        )
        self.DownloadDir = FileChooserButton(
            self.DownloadDir, parent.dialog, "folder", self.on_choose_download_dir
        )
        self.UploadDir = FileChooserButton(
            self.UploadDir, parent.dialog, "folder"
        )

        self.options = {
            "transfers": {
                "autoclear_downloads": self.AutoclearFinished,
                "lock": self.LockIncoming,
                "reverseorder": self.DownloadReverseOrder,
                "remotedownloads": self.RemoteDownloads,
                "uploadallowed": self.UploadsAllowed,
                "incompletedir": self.IncompleteDir,
                "downloaddir": self.DownloadDir,
                "sharedownloaddir": self.ShareDownloadDir,
                "uploaddir": self.UploadDir,
                "downloadfilters": self.FilterView,
                "enablefilters": self.DownloadFilter,
                "downloadlimit": self.DownloadSpeed,
                "downloadlimitalt": self.DownloadSpeedAlternative,
                "usernamesubfolders": self.UsernameSubfolders
            }
        }

        self.filterlist = Gtk.ListStore(
            str,
            bool
        )

        self.downloadfilters = []

        self.column_numbers = list(range(self.filterlist.get_n_columns()))
        cols = initialise_columns(
            None, self.FilterView,
            ["filter", _("Filter"), -1, "text", None],
            ["escaped", _("Escaped"), 40, "toggle", None]
        )

        cols["filter"].set_sort_column_id(0)
        cols["escaped"].set_sort_column_id(1)
        renderers = cols["escaped"].get_cells()

        for render in renderers:
            render.connect('toggled', self.cell_toggle_callback, self.filterlist, 1)

        self.FilterView.set_model(self.filterlist)

    def set_settings(self):

        self.p.set_widgets_data(self.options)

        self.UploadsAllowed.set_sensitive(self.RemoteDownloads.get_active())

        self.filtersiters = {}
        self.filterlist.clear()

        if config.sections["transfers"]["downloadfilters"]:
            for dfilter in config.sections["transfers"]["downloadfilters"]:
                dfilter, escaped = dfilter
                self.filtersiters[dfilter] = self.filterlist.insert_with_valuesv(
                    -1, self.column_numbers, [str(dfilter), bool(escaped)]
                )

        self.on_enable_filters_toggle(self.DownloadFilter)

        self.needrescan = False

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
                "incompletedir": self.IncompleteDir.get_path(),
                "downloaddir": self.DownloadDir.get_path(),
                "sharedownloaddir": self.ShareDownloadDir.get_active(),
                "uploaddir": self.UploadDir.get_path(),
                "downloadfilters": self.get_filter_list(),
                "enablefilters": self.DownloadFilter.get_active(),
                "downloadlimit": self.DownloadSpeed.get_value_as_int(),
                "downloadlimitalt": self.DownloadSpeedAlternative.get_value_as_int(),
                "usernamesubfolders": self.UsernameSubfolders.get_active()
            }
        }

    def on_choose_download_dir(self):

        # Get the transfers section
        transfers = config.sections["transfers"]

        # This function will be called upon creating the settings window,
        # so only force a scan if the user changes his donwload directory
        if self.ShareDownloadDir.get_active() and self.DownloadDir.get_path() != transfers["downloaddir"]:
            self.needrescan = True

    def on_remote_downloads(self, widget):

        sensitive = widget.get_active()

        self.UploadsAllowed.set_sensitive(sensitive)

    def on_share_download_dir_toggled(self, widget):
        self.needrescan = True

    def on_enable_filters_toggle(self, widget):

        sensitive = widget.get_active()

        self.VerifyFilters.set_sensitive(sensitive)
        self.VerifiedLabel.set_sensitive(sensitive)
        self.DefaultFilters.set_sensitive(sensitive)
        self.RemoveFilter.set_sensitive(sensitive)
        self.EditFilter.set_sensitive(sensitive)
        self.AddFilter.set_sensitive(sensitive)
        self.FilterView.set_sensitive(sensitive)

    def on_add_filter_response(self, dialog, response_id, data):

        dfilter = dialog.get_response_value()
        escaped = dialog.get_second_response_value()
        dialog.destroy()

        if response_id != Gtk.ResponseType.OK:
            return

        if dfilter in self.filtersiters:
            self.filterlist.set(self.filtersiters[dfilter], 0, dfilter, 1, escaped)
        else:
            self.filtersiters[dfilter] = self.filterlist.insert_with_valuesv(
                -1, self.column_numbers, [dfilter, escaped]
            )

        self.on_verify_filter(self.VerifyFilters)

    def on_add_filter(self, widget):

        entry_dialog(
            parent=self.p.dialog,
            title=_("Add Download Filter"),
            message=_("Enter a new download filter:"),
            callback=self.on_add_filter_response,
            option=True,
            optionvalue=True,
            optionmessage="Escape this filter?",
            droplist=list(self.filtersiters.keys())
        )

    def get_filter_list(self):

        self.downloadfilters = []

        df = sorted(self.filtersiters.keys())

        for dfilter in df:
            iterator = self.filtersiters[dfilter]
            dfilter = self.filterlist.get_value(iterator, 0)
            escaped = self.filterlist.get_value(iterator, 1)
            self.downloadfilters.append([dfilter, int(escaped)])

        return self.downloadfilters

    def on_edit_filter_response(self, dialog, response_id, data):

        new_dfilter = dialog.get_response_value()
        escaped = dialog.get_second_response_value()
        dialog.destroy()

        if response_id != Gtk.ResponseType.OK:
            return

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

        self.on_verify_filter(self.VerifyFilters)

    def on_edit_filter(self, widget):

        dfilter = self.get_selected_filter()

        if not dfilter:
            return

        iterator = self.filtersiters[dfilter]
        escapedvalue = self.filterlist.get_value(iterator, 1)

        entry_dialog(
            parent=self.p.dialog,
            title=_("Edit Download Filter"),
            message=_("Modify the following download filter:"),
            callback=self.on_edit_filter_response,
            default=dfilter,
            option=True,
            optionvalue=escapedvalue,
            optionmessage="Escape this filter?",
            droplist=list(self.filtersiters.keys())
        )

    def get_selected_filter(self):

        model, paths = self.FilterView.get_selection().get_selected_rows()

        for path in paths:
            iterator = model.get_iter(path)
            return model.get_value(iterator, 0)

        return None

    def on_remove_filter(self, widget):

        dfilter = self.get_selected_filter()

        if not dfilter:
            return

        iterator = self.filtersiters[dfilter]
        self.filterlist.remove(iterator)

        del self.filtersiters[dfilter]

        self.on_verify_filter(self.VerifyFilters)

    def on_default_filters(self, widget):

        self.filtersiters = {}
        self.filterlist.clear()

        for dfilter in config.defaults["transfers"]["downloadfilters"]:
            dfilter, escaped = dfilter
            self.filtersiters[dfilter] = self.filterlist.insert_with_valuesv(
                -1, self.column_numbers, [dfilter, escaped]
            )

        self.on_verify_filter(self.VerifyFilters)

    def on_verify_filter(self, widget):

        outfilter = "(\\\\("

        df = sorted(self.filtersiters.keys())

        proccessedfilters = []
        failed = {}

        for dfilter in df:

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
            except Exception as e:
                failed[dfilter] = e

            if filter is not df[-1]:
                outfilter += "|"

        outfilter += ")$)"

        try:
            re.compile(outfilter)

        except Exception as e:
            failed[outfilter] = e

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

    def cell_toggle_callback(self, widget, index, treeview, pos):

        iterator = self.filterlist.get_iter(index)
        value = self.filterlist.get_value(iterator, pos)

        self.filterlist.set(iterator, pos, not value)

        self.on_verify_filter(self.VerifyFilters)


class SharesFrame(BuildFrame):

    def __init__(self, parent):

        self.p = parent

        BuildFrame.__init__(self, "shares")

        self.needrescan = False
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
            None, self.Shares,
            ["virtual_folder", _("Virtual Folder"), 0, "text", None],
            ["folder", _("Folder"), -1, "text", None],
            ["buddies", _("Buddy-only"), 0, "toggle", None],
        )

        cols["virtual_folder"].set_sort_column_id(0)
        cols["folder"].set_sort_column_id(1)
        cols["buddies"].set_sort_column_id(2)

        for render in cols["buddies"].get_cells():
            render.connect('toggled', self.cell_toggle_callback, self.Shares)

        self.options = {
            "transfers": {
                "friendsonly": self.FriendsOnly,
                "rescanonstartup": self.RescanOnStartup,
                "enablebuddyshares": self.EnableBuddyShares,
                "buddysharestrustedonly": self.BuddySharesTrustedOnly
            }
        }

    def set_settings(self):

        transfers = config.sections["transfers"]
        self.shareslist.clear()

        self.p.set_widgets_data(self.options)
        self.on_enabled_buddy_shares_toggled(self.EnableBuddyShares)

        for (virtual, actual, *unused) in transfers["buddyshared"]:

            self.shareslist.insert_with_valuesv(-1, self.column_numbers, [
                str(virtual),
                str(actual),
                True
            ])

        for (virtual, actual, *unused) in transfers["shared"]:

            self.shareslist.insert_with_valuesv(-1, self.column_numbers, [
                str(virtual),
                str(actual),
                False
            ])

        self.shareddirs = transfers["shared"][:]
        self.bshareddirs = transfers["buddyshared"][:]

        self.needrescan = False

    def get_settings(self):

        # Public shares related menus are deactivated if we only share with friends
        friendsonly = self.FriendsOnly.get_active()

        self.frame.rescan_public_action.set_enabled(not friendsonly)
        self.frame.browse_public_shares_action.set_enabled(not friendsonly)

        # Buddy shares related menus are activated if needed
        buddies = self.EnableBuddyShares.get_active()

        self.frame.rescan_buddy_action.set_enabled(buddies)
        self.frame.browse_buddy_shares_action.set_enabled(buddies)

        return {
            "transfers": {
                "shared": self.shareddirs[:],
                "rescanonstartup": self.RescanOnStartup.get_active(),
                "buddyshared": self.bshareddirs[:],
                "enablebuddyshares": buddies,
                "friendsonly": friendsonly,
                "buddysharestrustedonly": self.BuddySharesTrustedOnly.get_active()
            }
        }

    def cell_toggle_callback(self, widget, index, treeview):

        store = treeview.get_model()
        iterator = store.get_iter(index)

        buddy = self.shareslist.get_value(iterator, 2)
        self.shareslist.set_value(iterator, 2, not buddy)

        virtual = self.shareslist.get_value(iterator, 0)
        directory = self.shareslist.get_value(iterator, 1)
        share = (virtual, directory)
        self.needrescan = True

        if buddy:
            self.bshareddirs.remove(share)
            self.shareddirs.append(share)
            return

        self.shareddirs.remove(share)
        self.bshareddirs.append(share)

    def on_enabled_buddy_shares_toggled(self, widget):

        buddies = widget.get_active()

        if not buddies:
            self.FriendsOnly.set_active(buddies)

        self.FriendsOnly.set_sensitive(buddies)
        self.BuddySharesTrustedOnly.set_sensitive(buddies)

        self.needrescan = True

    def on_friends_only_toggled(self, widget):
        self.needrescan = True

    def add_shared_dir_response(self, dialog, response_id, data):

        virtual = dialog.get_response_value()
        buddy = dialog.get_second_response_value()
        dialog.destroy()

        if response_id != Gtk.ResponseType.OK:
            return

        # Remove slashes from share name to avoid path conflicts
        if virtual:
            virtual = virtual.replace('/', '_').replace('\\', '_')

        # If the virtual share name is not already used
        if not virtual or virtual in (x[0] for x in self.shareddirs + self.bshareddirs):
            message_dialog(
                parent=self.p.dialog,
                title=_("Unable to Share Folder"),
                message=_("The chosen virtual name is either empty or already exists")
            )
            return

        directory = data

        self.shareslist.insert_with_valuesv(-1, self.column_numbers, [
            virtual,
            directory,
            buddy
        ])

        if buddy:
            shared_dirs = self.bshareddirs
        else:
            shared_dirs = self.shareddirs

        shared_dirs.append((virtual, directory))
        self.needrescan = True

    def add_shared_dir(self, folder):

        if folder is None:
            return

        # If the directory is already shared
        if folder in (x[1] for x in self.shareddirs + self.bshareddirs):
            message_dialog(
                parent=self.p.dialog,
                title=_("Unable to Share Folder"),
                message=_("The chosen folder is already shared.")
            )
            return

        entry_dialog(
            parent=self.p.dialog,
            title=_("Set Virtual Name"),
            message=_("Enter virtual name for '%(dir)s':") % {'dir': folder},
            option=True,
            optionmessage=_("Share with buddies only"),
            callback=self.add_shared_dir_response,
            callback_data=folder
        )

    def on_add_shared_dir_selected(self, selected, data):

        for folder in selected:
            self.add_shared_dir(folder)

    def on_add_shared_dir(self, *args):

        choose_dir(
            parent=self.p.dialog,
            callback=self.on_add_shared_dir_selected,
            title=_("Add a Shared Folder")
        )

    def rename_virtuals_response(self, dialog, response_id, iterator):

        virtual = dialog.get_response_value()
        dialog.destroy()

        if response_id != Gtk.ResponseType.OK:
            return

        if not virtual:
            return

        # Remove slashes from share name to avoid path conflicts
        virtual = virtual.replace('/', '_').replace('\\', '_')
        directory = self.shareslist.get_value(iterator, 1)
        oldvirtual = self.shareslist.get_value(iterator, 0)
        oldmapping = (oldvirtual, directory)
        newmapping = (virtual, directory)

        self.shareslist.set_value(iterator, 0, virtual)

        if oldmapping in self.bshareddirs:
            shared_dirs = self.bshareddirs
        else:
            shared_dirs = self.shareddirs

        shared_dirs.remove(oldmapping)
        shared_dirs.append(newmapping)

        self.needrescan = True

    def rename_virtuals(self):

        model, paths = self.Shares.get_selection().get_selected_rows()

        for path in reversed(paths):
            iterator = model.get_iter(path)
            folder = model.get_value(iterator, 1)

            entry_dialog(
                parent=self.p.dialog,
                title=_("Edit Virtual Name"),
                message=_("Enter new virtual name for '%(dir)s':") % {'dir': folder},
                callback=self.rename_virtuals_response,
                callback_data=iterator
            )

    def on_rename_virtuals(self, widget):
        self.rename_virtuals()

    def remove_shared_dir(self):

        model, paths = self.Shares.get_selection().get_selected_rows()

        for path in reversed(paths):
            iterator = model.get_iter(path)
            virtual = model.get_value(iterator, 0)
            actual = model.get_value(iterator, 1)
            mapping = (virtual, actual)

            if mapping in self.bshareddirs:
                self.bshareddirs.remove(mapping)
            else:
                self.shareddirs.remove(mapping)

            model.remove(iterator)

        if paths:
            self.needrescan = True

    def on_remove_shared_dir(self, widget):
        self.remove_shared_dir()


class UploadsFrame(BuildFrame):

    def __init__(self, parent):

        self.p = parent

        BuildFrame.__init__(self, "uploads")

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
                "preferfriends": self.PreferFriends
            }
        }

    def set_settings(self):

        self.p.set_widgets_data(self.options)

        self.on_queue_use_slots_toggled(self.QueueUseSlots)
        self.on_limit_toggled(self.Limit)

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
                "fifoqueue": self.FirstInFirstOut.get_active(),
                "limitby": self.LimitTotalTransfers.get_active(),
                "queuelimit": self.MaxUserQueue.get_value_as_int(),
                "filelimit": self.MaxUserFiles.get_value_as_int(),
                "friendsnolimits": self.FriendsNoLimits.get_active(),
                "preferfriends": self.PreferFriends.get_active()
            }
        }

    def on_queue_use_slots_toggled(self, widget):

        sensitive = widget.get_active()

        self.QueueSlots.set_sensitive(sensitive)

        self.QueueBandwidth.set_sensitive(not sensitive)
        self.QueueBandwidthText1.set_sensitive(not sensitive)

    def on_limit_toggled(self, widget):
        sensitive = widget.get_active()
        self.LimitSpeed.set_sensitive(sensitive)


class GeoBlockFrame(BuildFrame):

    def __init__(self, parent):
        self.p = parent
        BuildFrame.__init__(self, "geoblock")

        self.options = {
            "transfers": {
                "geoblock": self.GeoBlock,
                "geopanic": self.GeoPanic,
                "geoblockcc": self.GeoBlockCC,
                "usecustomgeoblock": self.UseCustomGeoBlock,
                "customgeoblock": self.CustomGeoBlock
            }
        }

    def set_settings(self):
        self.p.set_widgets_data(self.options)

        if config.sections["transfers"]["geoblockcc"] is not None:
            self.GeoBlockCC.set_text(config.sections["transfers"]["geoblockcc"][0])

    def get_settings(self):
        return {
            "transfers": {
                "geoblock": self.GeoBlock.get_active(),
                "geopanic": self.GeoPanic.get_active(),
                "geoblockcc": [self.GeoBlockCC.get_text().upper()],
                "usecustomgeoblock": self.UseCustomGeoBlock.get_active(),
                "customgeoblock": self.CustomGeoBlock.get_text()
            }
        }

    def on_use_custom_geo_block_toggled(self, widget):
        self.CustomGeoBlock.set_sensitive(widget.get_active())


class UserInfoFrame(BuildFrame):

    def __init__(self, parent):

        self.p = parent

        BuildFrame.__init__(self, "userinfo")

        self.ImageChooser = FileChooserButton(self.ImageChooser, parent.dialog, "image")

        self.options = {
            "userinfo": {
                "descr": None,
                "pic": self.ImageChooser
            }
        }

    def set_settings(self):

        self.p.set_widgets_data(self.options)

        if config.sections["userinfo"]["descr"] is not None:
            descr = unescape(config.sections["userinfo"]["descr"])
            self.Description.get_buffer().set_text(descr)

    def get_settings(self):

        buffer = self.Description.get_buffer()

        start = buffer.get_start_iter()
        end = buffer.get_end_iter()

        descr = buffer.get_text(start, end, True).replace("; ", ", ").__repr__()

        return {
            "userinfo": {
                "descr": descr,
                "pic": self.ImageChooser.get_path()
            }
        }

    def on_default_image(self, widget):
        self.ImageChooser.clear()


class IgnoreListFrame(BuildFrame):

    def __init__(self, parent):

        self.p = parent
        BuildFrame.__init__(self, "ignore")

        self.options = {
            "server": {
                "ignorelist": self.IgnoredUsers,
                "ipignorelist": self.IgnoredIPs
            }
        }

        self.ignored_users = []
        self.ignorelist = Gtk.ListStore(str)

        self.user_column_numbers = list(range(self.ignorelist.get_n_columns()))
        initialise_columns(
            None, self.IgnoredUsers,
            ["users", _("Users"), -1, "text", None]
        )

        self.IgnoredUsers.set_model(self.ignorelist)

        self.ignored_ips = {}
        self.ignored_ips_list = Gtk.ListStore(str, str)

        self.ip_column_numbers = list(range(self.ignored_ips_list.get_n_columns()))
        cols = initialise_columns(
            None, self.IgnoredIPs,
            ["addresses", _("Addresses"), -1, "text", None],
            ["users", _("Users"), -1, "text", None]
        )
        cols["addresses"].set_sort_column_id(0)
        cols["users"].set_sort_column_id(1)

        self.IgnoredIPs.set_model(self.ignored_ips_list)

    def set_settings(self):
        server = config.sections["server"]

        self.ignorelist.clear()
        self.ignored_ips_list.clear()
        self.ignored_users = []
        self.ignored_ips = {}
        self.p.set_widgets_data(self.options)

        if server["ignorelist"] is not None:
            self.ignored_users = server["ignorelist"][:]

        if server["ipignorelist"] is not None:
            self.ignored_ips = server["ipignorelist"].copy()
            for ip, user in self.ignored_ips.items():
                self.ignored_ips_list.insert_with_valuesv(-1, self.ip_column_numbers, [
                    str(ip), str(user)
                ])

    def get_settings(self):
        return {
            "server": {
                "ignorelist": self.ignored_users[:],
                "ipignorelist": self.ignored_ips.copy()
            }
        }

    def on_add_ignored_response(self, dialog, response_id, data):

        user = dialog.get_response_value()
        dialog.destroy()

        if response_id != Gtk.ResponseType.OK:
            return

        if user and user not in self.ignored_users:
            self.ignored_users.append(user)
            self.ignorelist.insert_with_valuesv(-1, self.user_column_numbers, [str(user)])

    def on_add_ignored(self, widget):

        entry_dialog(
            parent=self.p.dialog,
            title=_("Ignore User"),
            message=_("Enter the name of a user you wish to ignore:"),
            callback=self.on_add_ignored_response
        )

    def on_remove_ignored(self, widget):

        model, paths = self.IgnoredUsers.get_selection().get_selected_rows()

        for path in reversed(paths):
            iterator = model.get_iter(path)
            user = model.get_value(iterator, 0)

            model.remove(iterator)
            self.ignored_users.remove(user)

    def on_clear_ignored(self, widget):
        self.ignored_users = []
        self.ignorelist.clear()

    def on_add_ignored_ip_response(self, dialog, response_id, data):

        ip = dialog.get_response_value()
        dialog.destroy()

        if response_id != Gtk.ResponseType.OK:
            return

        if ip is None or ip == "" or ip.count(".") != 3:
            return

        for chars in ip.split("."):

            if chars == "*":
                continue
            if not chars.isdigit():
                return

            try:
                if int(chars) > 255:
                    return
            except Exception:
                return

        if ip not in self.ignored_ips:
            self.ignored_ips[ip] = ""
            self.ignored_ips_list.insert_with_valuesv(-1, self.ip_column_numbers, [ip, ""])

    def on_add_ignored_ip(self, widget):

        entry_dialog(
            parent=self.p.dialog,
            title=_("Ignore IP Address"),
            message=_("Enter an IP address you wish to ignore:") + " " + _("* is a wildcard"),
            callback=self.on_add_ignored_ip_response
        )

    def on_remove_ignored_ip(self, widget):

        model, paths = self.IgnoredIPs.get_selection().get_selected_rows()

        for path in reversed(paths):
            iterator = model.get_iter(path)
            ip = model.get_value(iterator, 0)

            model.remove(iterator)
            del self.ignored_ips[ip]

    def on_clear_ignored_ip(self, widget):
        self.ignored_ips = {}
        self.ignored_ips_list.clear()


class BanListFrame(BuildFrame):

    def __init__(self, parent):

        self.p = parent
        BuildFrame.__init__(self, "ban")

        self.options = {
            "server": {
                "banlist": self.BannedList,
                "ipblocklist": self.BlockedList
            },
            "transfers": {
                "usecustomban": self.UseCustomBan,
                "customban": self.CustomBan
            }
        }

        self.banlist = []
        self.banlist_model = Gtk.ListStore(str)

        self.ban_column_numbers = list(range(self.banlist_model.get_n_columns()))
        initialise_columns(
            None, self.BannedList,
            ["users", _("Users"), -1, "text", None]
        )

        self.BannedList.set_model(self.banlist_model)

        self.blocked_list = {}
        self.blocked_list_model = Gtk.ListStore(str, str)

        self.block_column_numbers = list(range(self.blocked_list_model.get_n_columns()))
        cols = initialise_columns(
            None, self.BlockedList,
            ["addresses", _("Addresses"), -1, "text", None],
            ["users", _("Users"), -1, "text", None]
        )
        cols["addresses"].set_sort_column_id(0)
        cols["users"].set_sort_column_id(1)

        self.BlockedList.set_model(self.blocked_list_model)

    def set_settings(self):

        self.need_ip_block = False
        server = config.sections["server"]
        self.banlist_model.clear()
        self.blocked_list_model.clear()

        self.banlist = server["banlist"][:]
        self.p.set_widgets_data(self.options)

        if server["ipblocklist"] is not None:
            self.blocked_list = server["ipblocklist"].copy()
            for blocked, user in server["ipblocklist"].items():
                self.blocked_list_model.insert_with_valuesv(-1, self.block_column_numbers, [
                    str(blocked),
                    str(user)
                ])

        self.on_use_custom_ban_toggled(self.UseCustomBan)

    def get_settings(self):
        return {
            "server": {
                "banlist": self.banlist[:],
                "ipblocklist": self.blocked_list.copy()
            },
            "transfers": {
                "usecustomban": self.UseCustomBan.get_active(),
                "customban": self.CustomBan.get_text()
            }
        }

    def on_add_banned_response(self, dialog, response_id, data):

        user = dialog.get_response_value()
        dialog.destroy()

        if response_id != Gtk.ResponseType.OK:
            return

        if user and user not in self.banlist:
            self.banlist.append(user)
            self.banlist_model.insert_with_valuesv(-1, self.ban_column_numbers, [user])

    def on_add_banned(self, widget):

        entry_dialog(
            parent=self.p.dialog,
            title=_("Ban User"),
            message=_("Enter the name of a user you wish to ban:"),
            callback=self.on_add_banned_response
        )

    def on_remove_banned(self, widget):

        model, paths = self.BannedList.get_selection().get_selected_rows()

        for path in reversed(paths):
            iterator = model.get_iter(path)
            user = model.get_value(iterator, 0)

            model.remove(iterator)
            self.banlist.remove(user)

    def on_clear_banned(self, widget):
        self.banlist = []
        self.banlist_model.clear()

    def on_use_custom_ban_toggled(self, widget):
        self.CustomBan.set_sensitive(widget.get_active())

    def on_add_blocked_response(self, dialog, response_id, data):

        ip = dialog.get_response_value()
        dialog.destroy()

        if response_id != Gtk.ResponseType.OK:
            return

        if ip is None or ip == "" or ip.count(".") != 3:
            return

        for chars in ip.split("."):

            if chars == "*":
                continue
            if not chars.isdigit():
                return

            try:
                if int(chars) > 255:
                    return
            except Exception:
                return

        if ip not in self.blocked_list:
            self.blocked_list[ip] = ""
            self.blocked_list_model.insert_with_valuesv(-1, self.block_column_numbers, [ip, ""])
            self.need_ip_block = True

    def on_add_blocked(self, widget):

        entry_dialog(
            parent=self.p.dialog,
            title=_("Block IP Address"),
            message=_("Enter an IP address you wish to block:") + " " + _("* is a wildcard"),
            callback=self.on_add_blocked_response
        )

    def on_remove_blocked(self, widget):

        model, paths = self.BlockedList.get_selection().get_selected_rows()

        for path in reversed(paths):
            iterator = model.get_iter(path)
            ip = model.get_value(iterator, 0)

            self.blocked_list_model.remove(iterator)
            del self.blocked_list[ip]

    def on_clear_blocked(self, widget):
        self.blocked_list = {}
        self.blocked_list_model.clear()


class TextToSpeechFrame(BuildFrame):

    def __init__(self, parent):

        self.p = parent

        BuildFrame.__init__(self, "tts")

        self.options = {
            "ui": {
                "speechenabled": self.TextToSpeech,
                "speechcommand": self.TTSCommand,
                "speechrooms": self.RoomMessage,
                "speechprivate": self.PrivateMessage
            }
        }

    def on_default_private(self, widget):
        self.PrivateMessage.set_text(config.defaults["ui"]["speechprivate"])

    def on_default_rooms(self, widget):
        self.RoomMessage.set_text(config.defaults["ui"]["speechrooms"])

    def on_default_tts(self, widget):
        self.TTSCommand.get_child().set_text(config.defaults["ui"]["speechcommand"])

    def set_settings(self):

        self.p.set_widgets_data(self.options)

        for i in ("%(user)s", "%(message)s"):
            if i not in config.sections["ui"]["speechprivate"]:
                self.default_private(None)

            if i not in config.sections["ui"]["speechrooms"]:
                self.default_rooms(None)

    def get_settings(self):

        return {
            "ui": {
                "speechenabled": self.TextToSpeech.get_active(),
                "speechcommand": self.TTSCommand.get_child().get_text(),
                "speechrooms": self.RoomMessage.get_text(),
                "speechprivate": self.PrivateMessage.get_text()
            }
        }


class UserInterfaceFrame(BuildFrame):

    def __init__(self, parent):

        self.p = parent

        BuildFrame.__init__(self, "userinterface")

        # Define options for each GtkComboBox using a liststore
        # The first element is the translated string,
        # the second is a GtkPositionType
        self.pos_list = Gtk.ListStore(str, str)
        column_numbers = list(range(self.pos_list.get_n_columns()))

        for item in ([_("Top"), "Top"], [_("Bottom"), "Bottom"], [_("Left"), "Left"], [_("Right"), "Right"]):
            self.pos_list.insert_with_valuesv(-1, column_numbers, item)

        cell = Gtk.CellRendererText()

        self.MainPosition.set_model(self.pos_list)
        self.MainPosition.pack_start(cell, True)
        self.MainPosition.add_attribute(cell, 'text', 0)

        self.ChatRoomsPosition.set_model(self.pos_list)
        self.ChatRoomsPosition.pack_start(cell, True)
        self.ChatRoomsPosition.add_attribute(cell, 'text', 0)

        self.PrivateChatPosition.set_model(self.pos_list)
        self.PrivateChatPosition.pack_start(cell, True)
        self.PrivateChatPosition.add_attribute(cell, 'text', 0)

        self.SearchPosition.set_model(self.pos_list)
        self.SearchPosition.pack_start(cell, True)
        self.SearchPosition.add_attribute(cell, 'text', 0)

        self.UserInfoPosition.set_model(self.pos_list)
        self.UserInfoPosition.pack_start(cell, True)
        self.UserInfoPosition.add_attribute(cell, 'text', 0)

        self.UserBrowsePosition.set_model(self.pos_list)
        self.UserBrowsePosition.pack_start(cell, True)
        self.UserBrowsePosition.add_attribute(cell, 'text', 0)

        self.ThemeDir = FileChooserButton(self.ThemeDir, parent.dialog, "folder")

        liststore = Gtk.ListStore(GdkPixbuf.Pixbuf, str)
        column_numbers = list(range(liststore.get_n_columns()))
        self.IconView.set_model(liststore)

        for row in (
            [GObject.Value(GObject.TYPE_OBJECT, self.frame.images["online"]), _("Connected")],
            [GObject.Value(GObject.TYPE_OBJECT, self.frame.images["offline"]), _("Disconnected")],
            [GObject.Value(GObject.TYPE_OBJECT, self.frame.images["away"]), _("Away")],
            [GObject.Value(GObject.TYPE_OBJECT, self.frame.images["hilite"]), _("Highlight")],
            [GObject.Value(GObject.TYPE_OBJECT, self.frame.images["hilite3"]), _("Highlight")],
            [GObject.Value(GObject.TYPE_OBJECT, self.frame.images["n"]), _("Window")],
            [GObject.Value(GObject.TYPE_OBJECT, self.frame.images["notify"]), _("Notification")]
        ):
            liststore.insert_with_valuesv(-1, column_numbers, row)

        if sys.platform != "darwin" and Gtk.get_major_version() != 4:
            for row in (
                [GObject.Value(GObject.TYPE_OBJECT, self.frame.images["trayicon_connect"]),
                    _("Connected (Tray)")],
                [GObject.Value(GObject.TYPE_OBJECT, self.frame.images["trayicon_disconnect"]),
                    _("Disconnected (Tray)")],
                [GObject.Value(GObject.TYPE_OBJECT, self.frame.images["trayicon_away"]),
                    _("Away (Tray)")],
                [GObject.Value(GObject.TYPE_OBJECT, self.frame.images["trayicon_msg"]),
                    _("Message (Tray)")]
            ):
                liststore.insert_with_valuesv(-1, column_numbers, row)

        self.needcolors = 0
        self.options = {
            "ui": {
                "globalfont": self.SelectGlobalFont,
                "chatfont": self.SelectChatFont,
                "listfont": self.SelectListFont,
                "searchfont": self.SelectSearchFont,
                "transfersfont": self.SelectTransfersFont,
                "browserfont": self.SelectBrowserFont,
                "usernamestyle": self.UsernameStyle,
                "decimalsep": self.DecimalSep,

                "file_path_tooltips": self.FilePathTooltips,
                "reverse_file_paths": self.ReverseFilePaths,
                "private_search_results": self.ShowPrivateSearchResults,
                "private_shares": self.ShowPrivateShares,

                "tabmain": self.MainPosition,
                "tabrooms": self.ChatRoomsPosition,
                "tabprivate": self.PrivateChatPosition,
                "tabsearch": self.SearchPosition,
                "tabinfo": self.UserInfoPosition,
                "tabbrowse": self.UserBrowsePosition,
                "tab_select_previous": self.TabSelectPrevious,
                "tabclosers": self.TabClosers,
                "tab_status_icons": self.TabStatusIcons,

                "icontheme": self.ThemeDir,

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
                "exitdialog": self.CloseAction
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

        self.p.set_widgets_data(self.options)

        # Function to set the default iter from the value found in the config file
        def set_active_conf(model, path, iterator, data):
            if model.get_value(iterator, 1).lower() == data["cfg"].lower():
                data["combobox"].set_active_iter(iterator)

        # Override settings for the GtkComboBox defining ui positionning
        for opt in [
            "tabmain", "tabrooms", "tabprivate",
            "tabsearch", "tabinfo", "tabbrowse"
        ]:
            # Get the value in the config file
            config_val = config.sections["ui"][opt]

            # Iterate over entries to find which one should be active
            self.options["ui"][opt].get_model().foreach(set_active_conf, {
                "cfg": config_val,
                "combobox": self.options["ui"][opt]
            })

        self.update_color_buttons()
        self.needcolors = 0

    def get_settings(self):

        # Get iters from GtkComboBox fields
        iter_main = self.pos_list.get_iter(self.MainPosition.get_active())
        iter_rooms = self.pos_list.get_iter(self.ChatRoomsPosition.get_active())
        iter_private = self.pos_list.get_iter(self.PrivateChatPosition.get_active())
        iter_search = self.pos_list.get_iter(self.SearchPosition.get_active())
        iter_info = self.pos_list.get_iter(self.UserInfoPosition.get_active())
        iter_browse = self.pos_list.get_iter(self.UserBrowsePosition.get_active())

        return {
            "ui": {
                "globalfont": self.SelectGlobalFont.get_font(),
                "chatfont": self.SelectChatFont.get_font(),
                "listfont": self.SelectListFont.get_font(),
                "searchfont": self.SelectSearchFont.get_font(),
                "transfersfont": self.SelectTransfersFont.get_font(),
                "browserfont": self.SelectBrowserFont.get_font(),
                "usernamestyle": self.UsernameStyle.get_active_text(),
                "decimalsep": self.DecimalSep.get_active_text(),

                "file_path_tooltips": self.FilePathTooltips.get_active(),
                "reverse_file_paths": self.ReverseFilePaths.get_active(),
                "private_search_results": self.ShowPrivateSearchResults.get_active(),
                "private_shares": self.ShowPrivateShares.get_active(),

                "tabmain": self.pos_list.get_value(iter_main, 1),
                "tabrooms": self.pos_list.get_value(iter_rooms, 1),
                "tabprivate": self.pos_list.get_value(iter_private, 1),
                "tabsearch": self.pos_list.get_value(iter_search, 1),
                "tabinfo": self.pos_list.get_value(iter_info, 1),
                "tabbrowse": self.pos_list.get_value(iter_browse, 1),
                "tab_select_previous": self.TabSelectPrevious.get_active(),
                "tabclosers": self.TabClosers.get_active(),
                "tab_status_icons": self.TabStatusIcons.get_active(),

                "icontheme": self.ThemeDir.get_path(),

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
                "exitdialog": self.CloseAction.get_active()
            }
        }

    """ Icons """

    def on_default_theme(self, widget):
        self.ThemeDir.clear()

    """ Fonts """

    def on_default_font(self, widget):

        font_button = getattr(self, Gtk.Buildable.get_name(widget).replace("Default", "Select"))
        font_button.set_font_name("")

        self.needcolors = 1

    def on_fonts_changed(self, widget):
        self.needcolors = 1

    """ Colors """

    def update_color_button(self, config, color_id):

        for section, value in self.colorsd.items():
            if color_id in value:
                color_button = self.colorsd[section][color_id]
                rgba = Gdk.RGBA()

                rgba.parse(config[section][color_id])
                color_button.set_rgba(rgba)
                break

    def update_color_buttons(self):

        for section, color_ids in self.colorsd.items():
            for color_id in color_ids:
                self.update_color_button(config.sections, color_id)

    def set_default_color(self, section, color_id):

        defaults = config.defaults
        widget = self.options[section][color_id]

        if isinstance(widget, Gtk.Entry):
            widget.set_text(defaults[section][color_id])

        self.update_color_button(defaults, color_id)

    def clear_color(self, section, color_id):

        widget = self.options[section][color_id]

        if isinstance(widget, Gtk.Entry):
            widget.set_text("")

        color_button = self.colorsd[section][color_id]
        color_button.set_rgba(Gdk.RGBA())

    def on_color_set(self, widget):

        rgba = widget.get_rgba()
        color = "#%02X%02X%02X" % (round(rgba.red * 255), round(rgba.green * 255), round(rgba.blue * 255))
        entry = getattr(self, Gtk.Buildable.get_name(widget).replace("Pick", "Entry"))
        entry.set_text(color)

    def on_default_color(self, widget):

        entry = getattr(self, Gtk.Buildable.get_name(widget).replace("Default", "Entry"))

        for section in self.options:
            for key, value in self.options[section].items():
                if value is entry:
                    self.set_default_color(section, key)
                    return

        entry.set_text("")

    def on_username_hotspots_toggled(self, widget):

        sensitive = widget.get_active()

        self.EntryAway.set_sensitive(sensitive)
        self.EntryOnline.set_sensitive(sensitive)
        self.EntryOffline.set_sensitive(sensitive)

        self.DefaultAway.set_sensitive(sensitive)
        self.DefaultOnline.set_sensitive(sensitive)
        self.DefaultOffline.set_sensitive(sensitive)

        self.PickAway.set_sensitive(sensitive)
        self.PickOnline.set_sensitive(sensitive)
        self.PickOffline.set_sensitive(sensitive)

    def on_default_colors(self, widget):

        for section, color_ids in self.colorsd.items():
            for color_id in color_ids:
                self.set_default_color(section, color_id)

    def on_clear_colors(self, widget):

        for section, color_ids in self.colorsd.items():
            for color_id in color_ids:
                self.clear_color(section, color_id)

    def on_colors_changed(self, widget):

        if isinstance(widget, Gtk.Entry):
            rgba = Gdk.RGBA()
            rgba.parse(widget.get_text())

            color_button = getattr(self, Gtk.Buildable.get_name(widget).replace("Entry", "Pick"))
            color_button.set_rgba(rgba)

        self.needcolors = 1


class LoggingFrame(BuildFrame):

    def __init__(self, parent):

        self.p = parent

        BuildFrame.__init__(self, "log")

        self.PrivateLogDir = FileChooserButton(self.PrivateLogDir, parent.dialog, "folder")
        self.RoomLogDir = FileChooserButton(self.RoomLogDir, parent.dialog, "folder")
        self.TransfersLogDir = FileChooserButton(self.TransfersLogDir, parent.dialog, "folder")
        self.DebugLogDir = FileChooserButton(self.DebugLogDir, parent.dialog, "folder")

        self.options = {
            "logging": {
                "privatechat": self.LogPrivate,
                "privatelogsdir": self.PrivateLogDir,
                "chatrooms": self.LogRooms,
                "roomlogsdir": self.RoomLogDir,
                "transfers": self.LogTransfers,
                "transferslogsdir": self.TransfersLogDir,
                "debug_file_output": self.LogDebug,
                "debuglogsdir": self.DebugLogDir,
                "rooms_timestamp": self.ChatRoomFormat,
                "private_timestamp": self.PrivateChatFormat,
                "log_timestamp": self.LogFileFormat,
                "timestamps": self.ShowTimeStamps,
                "readroomlines": self.RoomLogLines,
                "readprivatelines": self.PrivateLogLines,
                "readroomlogs": self.ReadRoomLogs
            },
            "privatechat": {
                "store": self.ReopenPrivateChats
            }
        }

    def set_settings(self):
        self.p.set_widgets_data(self.options)

    def get_settings(self):

        return {
            "logging": {
                "privatechat": self.LogPrivate.get_active(),
                "privatelogsdir": self.PrivateLogDir.get_path(),
                "chatrooms": self.LogRooms.get_active(),
                "roomlogsdir": self.RoomLogDir.get_path(),
                "transfers": self.LogTransfers.get_active(),
                "transferslogsdir": self.TransfersLogDir.get_path(),
                "debug_file_output": self.LogDebug.get_active(),
                "debuglogsdir": self.DebugLogDir.get_path(),
                "readroomlogs": self.ReadRoomLogs.get_active(),
                "readroomlines": self.RoomLogLines.get_value_as_int(),
                "readprivatelines": self.PrivateLogLines.get_value_as_int(),
                "private_timestamp": self.PrivateChatFormat.get_text(),
                "rooms_timestamp": self.ChatRoomFormat.get_text(),
                "log_timestamp": self.LogFileFormat.get_text(),
                "timestamps": self.ShowTimeStamps.get_active()
            },
            "privatechat": {
                "store": self.ReopenPrivateChats.get_active()
            },
        }

    def on_default_timestamp(self, widget):
        self.LogFileFormat.set_text(config.defaults["logging"]["log_timestamp"])

    def on_room_default_timestamp(self, widget):
        self.ChatRoomFormat.set_text(config.defaults["logging"]["rooms_timestamp"])

    def on_private_default_timestamp(self, widget):
        self.PrivateChatFormat.set_text(config.defaults["logging"]["private_timestamp"])


class SearchesFrame(BuildFrame):

    def __init__(self, parent):

        self.p = parent
        BuildFrame.__init__(self, "search")
        load_ui_elements(self, os.path.join(self.frame.gui_dir, "ui", "popovers", "searchfilters.ui"))

        if Gtk.get_major_version() == 4:
            button = self.ShowSearchHelp.get_first_child()
            button.set_child(self.FilterHelpLabel)
        else:
            self.ShowSearchHelp.add(self.FilterHelpLabel)

        self.ShowSearchHelp.set_popover(self.AboutSearchFiltersPopover)

        self.options = {
            "searches": {
                "maxresults": self.MaxResults,
                "enablefilters": self.EnableFilters,
                "re_filter": self.RegexpFilters,
                "defilter": None,
                "search_results": self.ToggleResults,
                "max_displayed_results": self.MaxDisplayedResults,
                "min_search_chars": self.MinSearchChars,
                "remove_special_chars": self.RemoveSpecialChars,
                "enable_history": self.EnableSearchHistory
            }
        }

    def set_settings(self):

        try:
            searches = config.sections["searches"]
        except Exception:
            searches = None

        self.p.set_widgets_data(self.options)

        if searches["defilter"] is not None:
            self.FilterIn.set_text(str(searches["defilter"][0]))
            self.FilterOut.set_text(str(searches["defilter"][1]))
            self.FilterSize.set_text(str(searches["defilter"][2]))
            self.FilterBR.set_text(str(searches["defilter"][3]))
            self.FilterFree.set_active(searches["defilter"][4])

            if len(searches["defilter"]) > 5:
                self.FilterCC.set_text(str(searches["defilter"][5]))

            if len(searches["defilter"]) > 6:
                self.FilterType.set_text(str(searches["defilter"][6]))

        self.ClearSearchHistorySuccess.hide()
        self.ClearFilterHistorySuccess.hide()

        self.on_enable_filters_toggled(self.EnableFilters)
        self.on_enable_search_results(self.ToggleResults)

    def get_settings(self):

        return {
            "searches": {
                "maxresults": self.MaxResults.get_value_as_int(),
                "enablefilters": self.EnableFilters.get_active(),
                "re_filter": self.RegexpFilters.get_active(),
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
                "enable_history": self.EnableSearchHistory.get_active()
            }
        }

    def on_clear_search_history(self, widget):
        self.frame.searches.clear_search_history()
        self.ClearSearchHistorySuccess.show()

    def on_clear_filter_history(self, widget):
        self.frame.searches.clear_filter_history()
        self.ClearFilterHistorySuccess.show()

    def on_enable_filters_toggled(self, widget):
        active = widget.get_active()
        for w in (self.FilterIn, self.FilterOut, self.FilterType, self.FilterSize,
                  self.FilterBR, self.FilterCC, self.FilterFree):
            w.set_sensitive(active)

    def on_enable_search_results(self, widget):
        active = widget.get_active()
        for w in (self.MinSearchCharsL1, self.MinSearchChars,
                  self.MaxResults, self.MaxResultsL1):
            w.set_sensitive(active)


class AwayModeFrame(BuildFrame):

    def __init__(self, parent):
        self.p = parent
        BuildFrame.__init__(self, "away")
        self.options = {
            "server": {
                "autoaway": self.AutoAway,
                "autoreply": self.AutoReply
            }
        }

    def set_settings(self):
        self.p.set_widgets_data(self.options)

    def get_settings(self):
        try:
            autoaway = self.AutoAway.get_value_as_int()
        except Exception:
            autoaway = None
        return {
            "server": {
                "autoaway": autoaway,
                "autoreply": self.AutoReply.get_text()
            }
        }


class EventsFrame(BuildFrame):

    def __init__(self, parent):

        self.p = parent

        BuildFrame.__init__(self, "events")

        self.options = {
            "transfers": {
                "afterfinish": self.AfterDownload,
                "afterfolder": self.AfterFolder,
                "download_doubleclick": self.DownloadDoubleClick,
                "upload_doubleclick": self.UploadDoubleClick
            },
            "ui": {
                "filemanager": self.FileManagerCombo
            },
            "players": {
                "default": self.audioPlayerCombo
            }
        }

    def set_settings(self):
        self.p.set_widgets_data(self.options)

    def get_settings(self):

        return {
            "transfers": {
                "afterfinish": self.AfterDownload.get_text(),
                "afterfolder": self.AfterFolder.get_text(),
                "download_doubleclick": self.DownloadDoubleClick.get_active(),
                "upload_doubleclick": self.UploadDoubleClick.get_active()
            },
            "ui": {
                "filemanager": self.FileManagerCombo.get_child().get_text()
            },
            "players": {
                "default": self.audioPlayerCombo.get_child().get_text()
            }
        }


class UrlCatchingFrame(BuildFrame):

    def __init__(self, parent):

        self.p = parent

        BuildFrame.__init__(self, "urlcatch")

        self.options = {
            "urls": {
                "urlcatching": self.URLCatching,
                "humanizeurls": self.HumanizeURLs,
                "protocols": None
            }
        }

        self.protocolmodel = Gtk.ListStore(str, str)

        self.protocols = {}

        self.column_numbers = list(range(self.protocolmodel.get_n_columns()))
        cols = initialise_columns(
            None, self.ProtocolHandlers,
            ["protocol", _("Protocol"), -1, "text", None],
            ["handler", _("Handler"), -1, "combo", None]
        )

        cols["protocol"].set_sort_column_id(0)
        cols["handler"].set_sort_column_id(1)

        self.ProtocolHandlers.set_model(self.protocolmodel)

        renderers = cols["handler"].get_cells()
        for render in renderers:
            render.connect('edited', self.cell_edited_callback, self.ProtocolHandlers, 1)

    def cell_edited_callback(self, widget, index, value, treeview, pos):
        store = treeview.get_model()
        iterator = store.get_iter(index)
        store.set(iterator, pos, value)

    def set_settings(self):

        self.protocolmodel.clear()
        self.protocols.clear()
        self.p.set_widgets_data(self.options)

        urls = config.sections["urls"]

        if urls["protocols"] is not None:

            for key in urls["protocols"].keys():
                if urls["protocols"][key][-1:] == "&":
                    command = urls["protocols"][key][:-1].rstrip()
                else:
                    command = urls["protocols"][key]

                iterator = self.protocolmodel.insert_with_valuesv(-1, self.column_numbers, [
                    str(key), str(command)
                ])
                self.protocols[key] = iterator

        self.on_url_catching_toggled(self.URLCatching)
        selection = self.ProtocolHandlers.get_selection()
        selection.unselect_all()

        for key, iterator in self.protocols.items():
            if iterator is not None:
                selection.select_iter(iterator)
                break

    def get_settings(self):

        protocols = {}

        try:
            iterator = self.protocolmodel.get_iter_first()
            while iterator is not None:
                protocol = self.protocolmodel.get_value(iterator, 0)
                handler = self.protocolmodel.get_value(iterator, 1)
                protocols[protocol] = handler
                iterator = self.protocolmodel.iter_next(iterator)
        except Exception:
            pass

        return {
            "urls": {
                "urlcatching": self.URLCatching.get_active(),
                "humanizeurls": self.HumanizeURLs.get_active(),
                "protocols": protocols
            }
        }

    def on_url_catching_toggled(self, widget):

        self.HumanizeURLs.set_active(widget.get_active())
        act = self.URLCatching.get_active()

        self.ProtocolContainer.set_sensitive(act)

    def on_select(self, selection):

        model, iterator = selection.get_selected()

        if iterator is None:
            self.ProtocolCombo.get_child().set_text("")
            self.Handler.get_child().set_text("")
        else:
            protocol = model.get_value(iterator, 0)
            handler = model.get_value(iterator, 1)
            self.ProtocolCombo.get_child().set_text(protocol)
            self.Handler.get_child().set_text(handler)

    def on_add(self, widget):

        protocol = self.ProtocolCombo.get_child().get_text()
        command = self.Handler.get_child().get_text()

        self.ProtocolCombo.get_child().set_text("")
        self.Handler.get_child().set_text("")

        if protocol in self.protocols:
            iterator = self.protocols[protocol]
            if iterator is not None:
                self.protocolmodel.set(iterator, 1, command)
        else:
            iterator = self.protocolmodel.insert_with_valuesv(-1, self.column_numbers, [protocol, command])
            self.protocols[protocol] = iterator

    def on_remove(self, widget):

        selection = self.ProtocolHandlers.get_selection()
        model, iterator = selection.get_selected()

        if iterator is not None:
            protocol = self.protocolmodel.get_value(iterator, 0)
            self.protocolmodel.remove(iterator)
            del self.protocols[protocol]

    def on_clear(self, widget):
        self.protocolmodel.clear()


class CensorListFrame(BuildFrame):

    def __init__(self, parent):

        self.p = parent

        BuildFrame.__init__(self, "censor")

        self.options = {
            "words": {
                "censorfill": self.CensorReplaceCombo,
                "censored": self.CensorList,
                "censorwords": self.CensorCheck
            }
        }

        self.censor_list_model = Gtk.ListStore(str)

        cols = initialise_columns(
            None, self.CensorList,
            ["pattern", _("Pattern"), -1, "edit", None]
        )

        cols["pattern"].set_sort_column_id(0)

        self.CensorList.set_model(self.censor_list_model)

        renderers = cols["pattern"].get_cells()
        for render in renderers:
            render.connect('edited', self.cell_edited_callback, self.CensorList, 0)

    def cell_edited_callback(self, widget, index, value, treeview, pos):

        store = treeview.get_model()
        iterator = store.get_iter(index)

        if value != "" and not value.isspace() and len(value) > 2:
            store.set(iterator, pos, value)
        else:
            store.remove(iterator)

    def set_settings(self):

        self.censor_list_model.clear()

        self.p.set_widgets_data(self.options)

        self.on_censor_check(self.CensorCheck)

    def on_censor_check(self, widget):

        sensitive = widget.get_active()

        self.CensorList.set_sensitive(sensitive)
        self.RemoveCensor.set_sensitive(sensitive)
        self.AddCensor.set_sensitive(sensitive)
        self.ClearCensors.set_sensitive(sensitive)
        self.CensorReplaceCombo.set_sensitive(sensitive)

    def get_settings(self):

        censored = []

        try:
            iterator = self.censor_list_model.get_iter_first()
            while iterator is not None:
                word = self.censor_list_model.get_value(iterator, 0)
                censored.append(word)
                iterator = self.censor_list_model.iter_next(iterator)
        except Exception:
            pass

        return {
            "words": {
                "censorfill": self.CensorReplaceCombo.get_active_text(),
                "censored": censored,
                "censorwords": self.CensorCheck.get_active()
            }
        }

    def on_add_response(self, dialog, response_id, data):

        pattern = dialog.get_response_value()
        dialog.destroy()

        if response_id != Gtk.ResponseType.OK:
            return

        if pattern:
            self.censor_list_model.insert_with_valuesv(-1, [0], [pattern])

    def on_add(self, widget):

        entry_dialog(
            parent=self.p.dialog,
            title=_("Censor Pattern"),
            message=_("Enter a pattern you wish to censor. Add spaces around the pattern if you don't "
                      "wish to match strings inside words (may fail at the beginning and end of lines)."),
            callback=self.on_add_response
        )

    def on_remove(self, widget):
        selection = self.CensorList.get_selection()
        iterator = selection.get_selected()[1]
        if iterator is not None:
            self.censor_list_model.remove(iterator)

    def on_clear(self, widget):
        self.censor_list_model.clear()


class AutoReplaceListFrame(BuildFrame):

    def __init__(self, parent):

        self.p = parent
        BuildFrame.__init__(self, "autoreplace")

        self.options = {
            "words": {
                "autoreplaced": self.ReplacementList,
                "replacewords": self.ReplaceCheck
            }
        }

        self.replacelist = Gtk.ListStore(str, str)

        self.column_numbers = list(range(self.replacelist.get_n_columns()))
        cols = initialise_columns(
            None, self.ReplacementList,
            ["pattern", _("Pattern"), 150, "edit", None],
            ["replacement", _("Replacement"), -1, "edit", None]
        )
        cols["pattern"].set_sort_column_id(0)
        cols["replacement"].set_sort_column_id(1)

        self.ReplacementList.set_model(self.replacelist)

        pos = 0
        for (column_id, column) in cols.items():
            renderers = column.get_cells()
            for render in renderers:
                render.connect('edited', self.cell_edited_callback, self.ReplacementList, pos)

            pos += 1

    def cell_edited_callback(self, widget, index, value, treeview, pos):

        store = treeview.get_model()
        iterator = store.get_iter(index)
        store.set(iterator, pos, value)

    def set_settings(self):

        self.replacelist.clear()

        self.p.set_widgets_data(self.options)

        words = config.sections["words"]
        if words["autoreplaced"] is not None:
            for word, replacement in words["autoreplaced"].items():
                self.replacelist.insert_with_valuesv(-1, self.column_numbers, [
                    str(word),
                    str(replacement)
                ])

        self.on_replace_check(self.ReplaceCheck)

    def on_replace_check(self, widget):
        sensitive = widget.get_active()
        self.ReplacementsContainer.set_sensitive(sensitive)

    def get_settings(self):

        autoreplaced = {}
        try:
            iterator = self.replacelist.get_iter_first()
            while iterator is not None:
                word = self.replacelist.get_value(iterator, 0)
                replacement = self.replacelist.get_value(iterator, 1)
                autoreplaced[word] = replacement
                iterator = self.replacelist.iter_next(iterator)
        except Exception:
            autoreplaced.clear()

        return {
            "words": {
                "autoreplaced": autoreplaced,
                "replacewords": self.ReplaceCheck.get_active()
            }
        }

    def on_add(self, widget):

        iterator = self.replacelist.insert_with_valuesv(-1, self.column_numbers, ["", ""])
        selection = self.ReplacementList.get_selection()
        selection.unselect_all()
        selection.select_iter(iterator)
        col = self.ReplacementList.get_column(0)

        self.ReplacementList.set_cursor(self.replacelist.get_path(iterator), col, True)

    def on_remove(self, widget):

        selection = self.ReplacementList.get_selection()
        iterator = selection.get_selected()[1]
        if iterator is not None:
            self.replacelist.remove(iterator)

    def on_clear(self, widget):
        self.replacelist.clear()

    def on_defaults(self, widget):

        self.replacelist.clear()

        for word, replacement in config.defaults["words"]["autoreplaced"].items():
            self.replacelist.insert_with_valuesv(-1, self.column_numbers, [word, replacement])


class CompletionFrame(BuildFrame):

    def __init__(self, parent):

        self.p = parent
        BuildFrame.__init__(self, "completion")

        self.options = {
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
                "onematch": self.OneMatchCheck
            },
            "ui": {
                "spellcheck": self.SpellCheck
            }
        }

    def set_settings(self):
        self.needcompletion = 0

        try:
            gi.require_version('Gspell', '1')
            from gi.repository import Gspell  # noqa: F401

        except (ImportError, ValueError):
            self.SpellCheck.hide()

        self.p.set_widgets_data(self.options)

    def on_completion_changed(self, widget):
        self.needcompletion = 1

    def on_completion_tab_check(self, widget):
        sensitive = self.CompletionTabCheck.get_active()
        self.needcompletion = 1

        self.CompletionCycleCheck.set_sensitive(sensitive)
        self.CompleteRoomNamesCheck.set_sensitive(sensitive)
        self.CompleteBuddiesCheck.set_sensitive(sensitive)
        self.CompleteUsersInRoomsCheck.set_sensitive(sensitive)
        self.CompleteCommandsCheck.set_sensitive(sensitive)
        self.CompleteAliasesCheck.set_sensitive(sensitive)
        self.CompletionDropdownCheck.set_sensitive(sensitive)

        self.on_completion_dropdown_check(widget)

    def on_completion_dropdown_check(self, widget):
        sensitive = (self.CompletionTabCheck.get_active() and self.CompletionDropdownCheck.get_active())
        self.needcompletion = 1

        self.CharactersCompletion.set_sensitive(sensitive)
        self.OneMatchCheck.set_sensitive(sensitive)

    def get_settings(self):
        return {
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
                "onematch": self.OneMatchCheck.get_active()
            },
            "ui": {
                "spellcheck": self.SpellCheck.get_active()
            }
        }


class NowPlayingFrame(BuildFrame):

    def __init__(self, parent):

        self.p = parent
        BuildFrame.__init__(self, "nowplaying")

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
            self.p.frame.np.now_playing.display_now_playing,
            self.set_now_playing_example,  # Callback to update the song displayed
            self.get_player,               # Callback to retrieve selected player
            self.get_command,              # Callback to retrieve command text
            self.get_format                # Callback to retrieve format text
        )

    def set_settings(self):

        self.p.set_widgets_data(self.options)

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
            for (i, v) in enumerate(self.NPFormat.get_model()):
                if v[0] == config.sections["players"]["npformat"]:
                    self.NPFormat.set_active(i)

    def get_player(self):

        if self.NP_lastfm.get_active():
            player = "lastfm"
        elif self.NP_mpris.get_active():
            player = "mpris"
        elif self.NP_other.get_active():
            player = "other"

        return player

    def get_command(self):
        return self.NPCommand.get_text()

    def get_format(self):
        return self.NPFormat.get_child().get_text()

    def set_player(self, player):

        if player == "lastfm":
            self.NP_lastfm.set_active(True)
        elif player == "other":
            self.NP_other.set_active(True)
        else:
            self.NP_mpris.set_active(True)

    def update_now_playing_info(self, widget=None):

        if self.NP_lastfm.get_active():
            self.player_replacers = ["$n", "$t", "$a", "$b"]
            self.player_input.set_text(_("Username;APIKEY:"))

        elif self.NP_mpris.get_active():
            self.player_replacers = ["$n", "$p", "$a", "$b", "$t", "$y", "$c", "$r", "$k", "$l", "$f"]
            self.player_input.set_text(_("Client name (e.g. amarok, audacious, exaile) or empty for auto:"))

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


class NotificationsFrame(BuildFrame):

    def __init__(self, parent):

        self.p = parent

        BuildFrame.__init__(self, "notifications")

        self.options = {
            "notifications": {
                "notification_window_title": self.NotificationWindowTitle,
                "notification_tab_colors": self.NotificationTabColors,
                "notification_tab_icons": self.NotificationTabIcons,
                "notification_popup_sound": self.NotificationPopupSound,
                "notification_popup_file": self.NotificationPopupFile,
                "notification_popup_folder": self.NotificationPopupFolder,
                "notification_popup_private_message": self.NotificationPopupPrivateMessage,
                "notification_popup_chatroom": self.NotificationPopupChatroom,
                "notification_popup_chatroom_mention": self.NotificationPopupChatroomMention
            },
            "ui": {
                "trayicon": self.TrayiconCheck,
                "startup_hidden": self.StartupHidden
            }
        }

    def set_settings(self):
        self.p.set_widgets_data(self.options)

        if sys.platform == "darwin" or Gtk.get_major_version() == 4:
            # Tray icons don't work as expected on macOS
            self.hide_tray_icon_settings()
            return

        sensitive = self.TrayiconCheck.get_active()
        self.StartupHidden.set_sensitive(sensitive)

    def hide_tray_icon_settings(self):

        # Hide widgets
        self.TraySettings.hide()

    def on_toggle_tray(self, widget):

        self.StartupHidden.set_sensitive(widget.get_active())

        if not widget.get_active() and self.StartupHidden.get_active():
            self.StartupHidden.set_active(widget.get_active())

    def get_settings(self):

        return {
            "notifications": {
                "notification_window_title": self.NotificationWindowTitle.get_active(),
                "notification_tab_colors": self.NotificationTabColors.get_active(),
                "notification_tab_icons": self.NotificationTabIcons.get_active(),
                "notification_popup_sound": self.NotificationPopupSound.get_active(),
                "notification_popup_file": self.NotificationPopupFile.get_active(),
                "notification_popup_folder": self.NotificationPopupFolder.get_active(),
                "notification_popup_private_message": self.NotificationPopupPrivateMessage.get_active(),
                "notification_popup_chatroom": self.NotificationPopupChatroom.get_active(),
                "notification_popup_chatroom_mention": self.NotificationPopupChatroomMention.get_active()
            },
            "ui": {
                "trayicon": self.TrayiconCheck.get_active(),
                "startup_hidden": self.StartupHidden.get_active()
            }
        }


class PluginsFrame(BuildFrame):

    """ Plugin preferences dialog """

    class PluginPreferencesDialog(Gtk.Dialog):
        """ Class used to build a custom dialog for the plugins """

        def __init__(self, parent, name):

            self.settings = parent.p

            # Build the window
            Gtk.Dialog.__init__(
                self,
                title=_("%s Properties") % name,
                modal=True,
                default_width=600,
                use_header_bar=config.sections["ui"]["header_bar"]
            )
            set_dialog_properties(self, self.settings.dialog)

            self.add_buttons(
                _("Cancel"), Gtk.ResponseType.CANCEL, _("OK"), Gtk.ResponseType.OK
            )

            self.set_default_response(Gtk.ResponseType.OK)
            self.connect("response", self.on_response)

            content_area = self.get_content_area()
            content_area.set_orientation(Gtk.Orientation.VERTICAL)
            content_area.set_margin_top(14)
            content_area.set_margin_bottom(14)
            content_area.set_margin_start(18)
            content_area.set_margin_end(18)
            content_area.set_spacing(12)

            self.tw = {}
            self.options = {}
            self.plugin = None

        def generate_label(self, text):

            label = Gtk.Label.new(text)
            label.set_hexpand(True)
            label.set_xalign(0)

            if Gtk.get_major_version() == 4:
                label.set_wrap(True)
            else:
                label.set_line_wrap(True)

            return label

        def generate_widget_container(self, description, vertical=False):

            container = Gtk.Box()
            container.set_spacing(12)

            if vertical:
                container.set_orientation(Gtk.Orientation.VERTICAL)

            label = self.generate_label(description)
            container.add(label)
            self.get_content_area().add(container)

            return container

        def generate_tree_view(self, name, description, value):

            container = Gtk.Box()
            container.set_spacing(6)

            scrolled_window = Gtk.ScrolledWindow()
            scrolled_window.set_hexpand(True)
            scrolled_window.set_vexpand(True)
            scrolled_window.set_min_content_height(200)
            scrolled_window.set_min_content_width(350)
            scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

            self.tw[name] = Gtk.TreeView()
            self.tw[name].set_model(Gtk.ListStore(str))

            if Gtk.get_major_version() == 4:
                scrolled_window.set_has_frame(True)
                scrolled_window.set_child(self.tw[name])
            else:
                scrolled_window.set_shadow_type(Gtk.ShadowType.IN)
                scrolled_window.add(self.tw[name])

            container.add(scrolled_window)

            cols = initialise_columns(
                None, self.tw[name],
                [description, description, 150, "edit", None]
            )

            try:
                self.settings.set_widget(self.tw[name], value)
            except Exception:
                pass

            self.add_button = Gtk.Button.new_with_label(_("Add"))
            self.remove_button = Gtk.Button.new_with_label(_("Remove"))

            box = Gtk.Box()
            box.set_spacing(6)

            box.add(self.add_button)
            box.add(self.remove_button)

            self.get_content_area().add(container)
            self.get_content_area().add(box)

            renderers = cols[description].get_cells()
            for render in renderers:
                render.connect('edited', self.cell_edited_callback, self.tw[name])

            self.add_button.connect("clicked", self.on_add, self.tw[name])
            self.remove_button.connect("clicked", self.on_remove, self.tw[name])

        def cell_edited_callback(self, widget, index, value, treeview):
            store = treeview.get_model()
            iterator = store.get_iter(index)
            store.set(iterator, 0, value)

        def add_options(self, plugin, options=None):

            if options is None:
                options = {}

            self.options = options
            self.plugin = plugin

            for name, data in options.items():
                if plugin not in config.sections["plugins"] or name not in config.sections["plugins"][plugin]:
                    if plugin not in config.sections["plugins"]:
                        print("No1 " + plugin + ", " + repr(list(config.sections["plugins"].keys())))
                    elif name not in config.sections["plugins"][plugin]:
                        print("No2 " + name + ", " + repr(list(config.sections["plugins"][plugin].keys())))
                    continue

                value = config.sections["plugins"][plugin][name]

                if data["type"] in ("integer", "int", "float"):
                    container = self.generate_widget_container(data["description"])

                    minimum = data.get("minimum") or 0
                    maximum = data.get("maximum") or 99999
                    stepsize = data.get("stepsize") or 1
                    decimals = 2

                    if data["type"] in ("integer", "int"):
                        decimals = 0

                    self.tw[name] = Gtk.SpinButton.new(
                        Gtk.Adjustment.new(0, minimum, maximum, stepsize, 10, 0),
                        1, decimals)
                    self.settings.set_widget(self.tw[name], config.sections["plugins"][plugin][name])

                    container.add(self.tw[name])

                elif data["type"] in ("bool",):
                    container = Gtk.Box()

                    self.tw[name] = Gtk.CheckButton.new_with_label(data["description"])
                    self.settings.set_widget(self.tw[name], config.sections["plugins"][plugin][name])

                    self.get_content_area().add(container)
                    container.add(self.tw[name])

                elif data["type"] in ("radio",):
                    container = self.generate_widget_container(data["description"])

                    vbox = Gtk.Box()
                    vbox.set_spacing(6)
                    vbox.set_orientation(Gtk.Orientation.VERTICAL)
                    container.add(vbox)

                    last_radio = None
                    group_radios = []

                    for label in data["options"]:
                        if Gtk.get_major_version() == 4:
                            radio = Gtk.CheckButton.new_with_label(label)
                        else:
                            radio = Gtk.RadioButton.new_with_label_from_widget(last_radio, label)

                        if not last_radio:
                            self.tw[name] = radio

                        elif Gtk.get_major_version() == 4:
                            radio.set_group(last_radio)

                        last_radio = radio
                        group_radios.append(radio)
                        vbox.add(radio)

                    self.tw[name].group_radios = group_radios
                    self.settings.set_widget(self.tw[name], config.sections["plugins"][plugin][name])

                elif data["type"] in ("dropdown",):
                    container = self.generate_widget_container(data["description"])

                    self.tw[name] = Gtk.ComboBoxText()

                    for label in data["options"]:
                        self.tw[name].append_text(label)

                    self.settings.set_widget(self.tw[name], config.sections["plugins"][plugin][name])

                    container.add(self.tw[name])

                elif data["type"] in ("str", "string"):
                    container = self.generate_widget_container(data["description"])

                    self.tw[name] = entry = Gtk.Entry()
                    entry.set_hexpand(True)
                    self.settings.set_widget(entry, config.sections["plugins"][plugin][name])

                    container.add(entry)

                elif data["type"] in ("textview"):
                    container = self.generate_widget_container(data["description"], vertical=True)

                    self.tw[name] = Gtk.TextView()
                    self.settings.set_widget(self.tw[name], config.sections["plugins"][plugin][name])

                    scrolled_window = Gtk.ScrolledWindow()
                    scrolled_window.set_hexpand(True)
                    scrolled_window.set_vexpand(True)
                    scrolled_window.set_min_content_height(200)
                    scrolled_window.set_min_content_width(600)

                    if Gtk.get_major_version() == 4:
                        scrolled_window.set_has_frame(True)

                        scrolled_window.set_child(self.tw[name])
                        container.append(scrolled_window)

                    else:
                        scrolled_window.set_shadow_type(Gtk.ShadowType.IN)

                        scrolled_window.add(self.tw[name])
                        container.add(scrolled_window)

                elif data["type"] in ("list string",):
                    self.generate_tree_view(name, data["description"], value)

                elif data["type"] in ("file",):
                    container = self.generate_widget_container(data["description"])

                    button_widget = Gtk.Button()
                    button_widget.set_hexpand(True)

                    try:
                        chooser = data["chooser"]
                    except KeyError:
                        chooser = None

                    self.tw[name] = FileChooserButton(button_widget, self, chooser)
                    self.settings.set_widget(self.tw[name], config.sections["plugins"][plugin][name])

                    container.add(button_widget)

                else:
                    print("Unknown setting type '%s', data '%s'" % (name, data))

            if Gtk.get_major_version() == 3:
                self.show_all()

        def on_add(self, widget, treeview):

            iterator = treeview.get_model().append([""])
            col = treeview.get_column(0)

            treeview.set_cursor(treeview.get_model().get_path(iterator), col, True)

        def on_remove(self, widget, treeview):
            selection = treeview.get_selection()
            iterator = selection.get_selected()[1]
            if iterator is not None:
                treeview.get_model().remove(iterator)

        def on_response(self, dialog, response_id):

            if response_id == Gtk.ResponseType.OK:
                for name in self.options:
                    value = self.settings.get_widget_data(self.tw[name])
                    if value is not None:
                        config.sections["plugins"][self.plugin][name] = value

                self.settings.frame.np.pluginhandler.plugin_settings(
                    self.plugin, self.settings.frame.np.pluginhandler.enabled_plugins[self.plugin])

            self.destroy()

    """ Initialize plugin list """

    def __init__(self, parent):

        self.p = parent
        BuildFrame.__init__(self, "plugin")

        self.options = {
            "plugins": {
                "enable": self.PluginsEnable
            }
        }

        self.plugins_model = Gtk.ListStore(bool, str, str)
        self.plugins = []
        self.pluginsiters = {}
        self.selected_plugin = None

        self.column_numbers = list(range(self.plugins_model.get_n_columns()))
        cols = initialise_columns(
            None, self.PluginTreeView,
            ["enabled", _("Enabled"), 0, "toggle", None],
            ["plugins", _("Plugins"), 380, "text", None]
        )

        cols["enabled"].set_sort_column_id(0)
        cols["plugins"].set_sort_column_id(1)

        renderers = cols["enabled"].get_cells()
        column_pos = 0

        for render in renderers:
            render.connect('toggled', self.cell_toggle_callback, self.PluginTreeView, column_pos)

        self.PluginTreeView.set_model(self.plugins_model)

    def on_add_plugins(self, widget):

        try:
            if not os.path.isdir(config.plugin_dir):
                os.makedirs(config.plugin_dir)

            open_file_path(config.plugin_dir)

        except Exception as e:
            log.add("Failed to open folder containing user plugins: %s", e)

    def on_plugin_properties(self, widget):

        if self.selected_plugin is None:
            return

        plugin_info = self.frame.np.pluginhandler.get_plugin_info(self.selected_plugin)
        dialog = self.PluginPreferencesDialog(self, plugin_info["Name"])

        dialog.add_options(
            self.selected_plugin,
            self.frame.np.pluginhandler.get_plugin_settings(self.selected_plugin)
        )

        dialog.present_with_time(Gdk.CURRENT_TIME)

    def on_select_plugin(self, selection):

        model, iterator = selection.get_selected()
        if iterator is None:
            self.selected_plugin = None
            self.check_properties_button(self.selected_plugin)
            return

        self.selected_plugin = model.get_value(iterator, 2)
        info = self.frame.np.pluginhandler.get_plugin_info(self.selected_plugin)

        self.PluginVersion.set_markup("<b>%(version)s</b>" % {"version": info['Version']})
        self.PluginName.set_markup("<b>%(name)s</b>" % {"name": info['Name']})
        self.PluginAuthor.set_markup("<b>%(author)s</b>" % {"author": ", ".join(info['Authors'])})

        self.PluginDescription.get_buffer().set_text("")
        append_line(self.PluginDescription,
                    "%(description)s" % {
                        "description": info['Description'].replace(r'\n', "\n")
                    },
                    showstamp=False,
                    scroll=False)

        self.check_properties_button(self.selected_plugin)

    def cell_toggle_callback(self, widget, index, treeview, pos):

        iterator = self.plugins_model.get_iter(index)
        plugin = self.plugins_model.get_value(iterator, 2)
        value = self.plugins_model.get_value(iterator, 0)
        self.plugins_model.set(iterator, pos, not value)

        if not value:
            if not self.frame.np.pluginhandler.enable_plugin(plugin):
                log.add(_('Could not enable plugin.'))
                return
        else:
            if not self.frame.np.pluginhandler.disable_plugin(plugin):
                log.add(_('Could not disable plugin.'))
                return

        self.check_properties_button(plugin)

    def check_properties_button(self, plugin):
        settings = self.frame.np.pluginhandler.get_plugin_settings(plugin)

        if settings is not None:
            self.PluginProperties.set_sensitive(True)
        else:
            self.PluginProperties.set_sensitive(False)

    def set_settings(self):

        self.p.set_widgets_data(self.options)
        self.on_plugins_enable(None)
        self.pluginsiters = {}
        self.plugins_model.clear()
        plugins = sorted(self.frame.np.pluginhandler.list_installed_plugins())

        for plugin in plugins:
            try:
                info = self.frame.np.pluginhandler.get_plugin_info(plugin)
            except IOError:
                continue
            enabled = (plugin in config.sections["plugins"]["enabled"])
            self.pluginsiters[filter] = self.plugins_model.insert_with_valuesv(
                -1, self.column_numbers, [enabled, info['Name'], plugin]
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

    def on_plugins_enable(self, *args):

        active = self.PluginsEnable.get_active()

        for widget in (self.PluginTreeView, self.PluginInfo):
            widget.set_sensitive(active)

        if active:
            # Enable all selected plugins
            for plugin in self.get_enabled_plugins():
                self.frame.np.pluginhandler.enable_plugin(plugin)

            return

        # Disable all plugins
        for plugin in self.frame.np.pluginhandler.enabled_plugins.copy():
            self.frame.np.pluginhandler.disable_plugin(plugin)

    def get_settings(self):

        return {
            "plugins": {
                "enable": self.PluginsEnable.get_active(),
                "enabled": self.get_enabled_plugins()
            }
        }


class Settings:

    def __init__(self, frame):

        self.frame = frame

        # Build the window
        load_ui_elements(self, os.path.join(self.frame.gui_dir, "ui", "settings", "settingswindow.ui"))

        self.dialog = dialog = generic_dialog(
            parent=frame.MainWindow,
            content_box=self.Main,
            quit_callback=self.on_delete,
            title=_("Preferences"),
            width=960,
            height=650
        )

        dialog.add_buttons(
            _("Cancel"), Gtk.ResponseType.CANCEL,
            _("Export"), Gtk.ResponseType.HELP,
            _("Apply"), Gtk.ResponseType.APPLY,
            _("OK"), Gtk.ResponseType.OK
        )

        dialog.set_default_response(Gtk.ResponseType.OK)
        dialog.connect("response", self.on_response)
        dialog.get_style_context().add_class("preferences")

        if Gtk.get_major_version() == 3:
            self.Main.child_set_property(self.SettingsList, "shrink", False)
            self.Main.child_set_property(self.ScrolledWindow, "shrink", False)
        else:
            self.Main.set_shrink_start_child(False)
            self.Main.set_shrink_end_child(False)

        # Signal sent and catch by frame.py on update
        GObject.signal_new("settings-updated", Gtk.Window, GObject.SignalFlags.RUN_LAST,
                           GObject.TYPE_NONE, (GObject.TYPE_STRING,))
        dialog.connect("settings-updated", self.frame.on_settings_updated)

        # Treeview of the settings
        self.tree = {}
        self.pages = {}

        # Model of the treeview
        model = Gtk.TreeStore(str, str)
        self.SettingsTreeview.set_model(model)

        self.tree["General"] = row = model.append(None, [_("General"), "General"])
        self.tree["Network"] = model.append(row, [_("Network"), "Network"])
        self.tree["Searches"] = model.append(row, [_("Searches"), "Searches"])
        self.tree["UserInterface"] = model.append(row, [_("User Interface"), "UserInterface"])
        self.tree["Notifications"] = model.append(row, [_("Notifications"), "Notifications"])
        self.tree["Plugins"] = model.append(row, [_("Plugins"), "Plugins"])
        self.tree["UserInfo"] = model.append(row, [_("User Info"), "UserInfo"])
        self.tree["Logging"] = model.append(row, [_("Logging"), "Logging"])

        self.tree["Transfers"] = row = model.append(None, [_("Transfers"), "Transfers"])
        self.tree["Shares"] = model.append(row, [_("Shares"), "Shares"])
        self.tree["Downloads"] = model.append(row, [_("Downloads"), "Downloads"])
        self.tree["Uploads"] = model.append(row, [_("Uploads"), "Uploads"])
        self.tree["BanList"] = model.append(row, [_("Ban List"), "BanList"])
        self.tree["Events"] = model.append(row, [_("Events"), "Events"])
        self.tree["GeoBlock"] = model.append(row, [_("Geo Block"), "GeoBlock"])

        self.tree["Chat"] = row = model.append(None, [_("Chat"), "Chat"])
        self.tree["NowPlaying"] = model.append(row, [_("Now Playing"), "NowPlaying"])
        self.tree["AwayMode"] = model.append(row, [_("Away Mode"), "AwayMode"])
        self.tree["IgnoreList"] = model.append(row, [_("Ignore List"), "IgnoreList"])
        self.tree["CensorList"] = model.append(row, [_("Censor List"), "CensorList"])
        self.tree["AutoReplaceList"] = model.append(row, [_("Auto-Replace List"), "AutoReplaceList"])
        self.tree["UrlCatching"] = model.append(row, [_("URL Catching"), "UrlCatching"])
        self.tree["Completion"] = model.append(row, [_("Completion"), "Completion"])
        self.tree["TextToSpeech"] = model.append(row, [_("Text-to-Speech"), "TextToSpeech"])

        initialise_columns(
            None, self.SettingsTreeview,
            ["categories", _("Categories"), -1, "text", None]
        )

        # Set the cursor to the second element of the TreeViewColumn.
        self.SettingsTreeview.expand_all()
        self.SettingsTreeview.set_cursor((0, 0))

        self.update_visuals()

    def update_visuals(self, scope=None):

        if not scope:
            for page in self.pages.values():
                self.update_visuals(page)

            scope = self

        for widget in list(scope.__dict__.values()):
            update_widget_visuals(widget)

    def set_active_page(self, page):

        model = self.SettingsTreeview.get_model()
        selection = self.SettingsTreeview.get_selection()
        selection.unselect_all()
        path = model.get_path(self.tree[page])

        self.SettingsTreeview.expand_to_path(path)

        if path is not None:
            selection.select_path(path)

        self.on_switch_page(selection)

    def set_combobox_value(self, combobox, option):

        # Attempt to match the value with an existing item
        iterator = combobox.get_model().get_iter_first()

        while iterator is not None:
            word = combobox.get_model().get_value(iterator, 0)

            if word.lower() == option or word == option:
                combobox.set_active_iter(iterator)
                break

            iterator = combobox.get_model().iter_next(iterator)

        # Custom value provided
        if combobox.get_has_entry():
            if Gtk.get_major_version() == 4:
                entry = combobox.get_child()
            else:
                entry = combobox.get_children()[0]

            entry.set_text(option)

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

    def get_widget_data(self, widget):

        if isinstance(widget, Gtk.SpinButton):
            if widget.get_digits() > 0:
                return widget.get_value()

            return widget.get_value_as_int()

        elif isinstance(widget, Gtk.Entry):
            return widget.get_text()

        elif isinstance(widget, Gtk.TextView):
            buffer = widget.get_buffer()
            start, end = buffer.get_bounds()

            return widget.get_buffer().get_text(start, end, True)

        elif isinstance(widget, Gtk.CheckButton):
            try:
                # Radio button
                for radio in widget.group_radios:
                    if radio.get_active():
                        return widget.group_radios.index(radio)

                return 0

            except (AttributeError, TypeError):
                # Regular check button
                return widget.get_active()

        elif isinstance(widget, Gtk.ComboBox):
            return widget.get_model().get(widget.get_active_iter(), 0)[0]

        elif isinstance(widget, Gtk.FontButton):
            widget.get_font()

        elif isinstance(widget, Gtk.TreeView) and widget.get_model().get_n_columns() == 1:
            wlist = []
            iterator = widget.get_model().get_iter_first()

            while iterator:
                word = widget.get_model().get_value(iterator, 0)

                if word is not None:
                    wlist.append(word)

                iterator = widget.get_model().iter_next(iterator)

            return wlist

        elif isinstance(widget, FileChooserButton):
            return widget.get_path()

    def clear_widget(self, widget):

        if isinstance(widget, Gtk.SpinButton):
            widget.set_value(0)

        elif isinstance(widget, Gtk.Entry):
            widget.set_text("")

        elif isinstance(widget, Gtk.TextView):
            widget.get_buffer().set_text("")

        elif isinstance(widget, Gtk.CheckButton):
            widget.set_active(0)

        elif isinstance(widget, Gtk.ComboBox):
            self.set_combobox_item(widget, "")

        elif isinstance(widget, Gtk.FontButton):
            widget.set_font("")

    def set_widget(self, widget, value):

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

        elif isinstance(widget, Gtk.ComboBox):
            if isinstance(value, str):
                self.set_combobox_value(widget, value)

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

        config = {
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
            sub = page.get_settings()
            for key, data in sub.items():
                config[key].update(data)

        try:
            need_portmap = self.pages["Network"].needportmap

        except KeyError:
            need_portmap = False

        try:
            need_rescan = self.pages["Shares"].needrescan

        except KeyError:
            need_rescan = False

        if not need_rescan:
            try:
                need_rescan = self.pages["Downloads"].needrescan

            except KeyError:
                need_rescan = False

        try:
            need_colors = self.pages["UserInterface"].needcolors

        except KeyError:
            need_colors = False

        try:
            need_completion = self.pages["Completion"].needcompletion

        except KeyError:
            need_completion = False

        try:
            need_ip_block = self.pages["BanList"].need_ip_block

        except KeyError:
            need_ip_block = False

        return need_portmap, need_rescan, need_colors, need_completion, need_ip_block, config

    def on_switch_page(self, selection):

        child = self.viewport1.get_child()

        if child:
            if Gtk.get_major_version() == 4:
                self.viewport1.set_child(None)
            else:
                self.viewport1.remove(child)

        model, iterator = selection.get_selected()

        if iterator is None:
            return

        page_id = model.get_value(iterator, 1)

        if page_id not in self.pages:
            if not hasattr(sys.modules[__name__], page_id + "Frame"):
                return

            self.pages[page_id] = page = getattr(sys.modules[__name__], page_id + "Frame")(self)
            page.set_settings()

            for obj in page.__dict__.values():
                if isinstance(obj, Gtk.CheckButton):
                    if Gtk.get_major_version() == 4:
                        obj.get_last_child().set_wrap(True)
                    else:
                        obj.get_children()[-1].set_line_wrap(True)

            page.Main.set_margin_start(18)
            page.Main.set_margin_end(18)
            page.Main.set_margin_top(14)
            page.Main.set_margin_bottom(18)

            self.update_visuals(page)

        if Gtk.get_major_version() == 4:
            self.viewport1.set_child(self.pages[page_id].Main)
        else:
            self.viewport1.add(self.pages[page_id].Main)

    def on_backup_config_response(self, selected, data):

        error, message = config.write_config_backup(selected)

        if error:
            log.add(_("Error backing up config: %s"), message)
        else:
            log.add(_("Config backed up to: %s"), message)

    def on_backup_config(self, *args):

        save_file(
            parent=self.frame.MainWindow,
            callback=self.on_backup_config_response,
            initialdir=os.path.dirname(config.filename),
            initialfile="config backup %s.tar.bz2" % (time.strftime("%Y-%m-%d %H_%M_%S")),
            title=_("Pick a File Name for Config Backup")
        )

    def on_response(self, dialog, response_id):

        if response_id == Gtk.ResponseType.OK:
            self.on_delete()
            self.dialog.emit("settings-updated", "ok")

        elif response_id == Gtk.ResponseType.APPLY:
            self.dialog.emit("settings-updated", "apply")

        elif response_id == Gtk.ResponseType.HELP:
            self.on_backup_config()

        else:
            self.on_delete()

    def on_delete(self, *args):
        dialog_hide(self.dialog)
        return True

    def show(self, *args):
        self.dialog.present_with_time(Gdk.CURRENT_TIME)
