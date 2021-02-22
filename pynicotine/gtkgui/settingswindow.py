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
import sys
import time

from gi.repository import Gdk
from gi.repository import GObject
from gi.repository import Gtk

from pynicotine import slskmessages
from pynicotine.gtkgui.dialogs import choose_dir
from pynicotine.gtkgui.dialogs import combo_box_dialog
from pynicotine.gtkgui.dialogs import entry_dialog
from pynicotine.gtkgui.dialogs import save_file
from pynicotine.gtkgui.utils import FileChooserButton
from pynicotine.gtkgui.utils import initialise_columns
from pynicotine.gtkgui.utils import load_ui_elements
from pynicotine.gtkgui.utils import open_uri
from pynicotine.gtkgui.utils import update_widget_visuals
from pynicotine.logfacility import log
from pynicotine.utils import unescape


class BuildFrame:
    """ This class build the individual frames from the settings window """

    def __init__(self, window):

        self.frame = self.p.frame

        # Build the frame
        load_ui_elements(self, os.path.join(self.frame.gui_dir, "ui", "settings", window + ".ui"))


class ServerFrame(BuildFrame):

    def __init__(self, parent):

        self.p = parent

        BuildFrame.__init__(self, "server")

        self.needportmap = False

        self.options = {
            "server": {
                "server": None,
                "login": self.Login,
                "passw": self.Password,
                "portrange": None,
                "upnp": self.UseUPnP,
                "upnp_interval": self.UPnPInterval,
                "auto_connect_startup": self.AutoConnectStartup,
                "ctcpmsgs": self.ctcptogglebutton
            }
        }

    def set_settings(self, config):

        self.p.set_widgets_data(config, self.options)

        server = config["server"]

        if server["server"] is not None:
            self.Server.set_text("%s:%i" % (server["server"][0], server["server"][1]))

        if self.frame.np.waitport is None:
            self.CurrentPort.set_text(_("Client port is not set"))
        else:
            self.CurrentPort.set_markup(_("Client port is <b>%(port)s</b>") % {"port": self.frame.np.waitport})

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

    def get_settings(self):

        try:
            server = self.Server.get_text().split(":")
            server[1] = int(server[1])
            server = tuple(server)

        except Exception:
            server = self.frame.np.config.defaults["server"]["server"]

        firstport = min(self.FirstPort.get_value_as_int(), self.LastPort.get_value_as_int())
        lastport = max(self.FirstPort.get_value_as_int(), self.LastPort.get_value_as_int())
        portrange = (firstport, lastport)

        return {
            "server": {
                "server": server,
                "login": self.Login.get_text(),
                "passw": self.Password.get_text(),
                "portrange": portrange,
                "upnp": self.UseUPnP.get_active(),
                "upnp_interval": self.UPnPInterval.get_value_as_int(),
                "auto_connect_startup": self.AutoConnectStartup.get_active(),
                "ctcpmsgs": not self.ctcptogglebutton.get_active()
            }
        }

    def on_change_password(self, widget):
        self.frame.np.queue.put(slskmessages.ChangePassword(self.Password.get_text()))

    def on_modify_port(self, widget, *args):
        self.needportmap = True

    def on_check_port(self, widget):
        open_uri('='.join(['http://tools.slsknet.org/porttest.php?port', str(self.frame.np.waitport)]), self.p.SettingsWindow)

    def on_toggle_upnp(self, widget, *args):

        active = widget.get_active()
        self.needportmap = active

        self.UPnPIntervalL1.set_sensitive(active)
        self.UPnPInterval.set_sensitive(active)
        self.UPnPIntervalL2.set_sensitive(active)

    def on_modify_upnp_interval(self, widget, *args):
        self.needportmap = True


class DownloadsFrame(BuildFrame):

    def __init__(self, parent):

        self.p = parent

        BuildFrame.__init__(self, "downloads")

        self.needrescan = False

        self.IncompleteDir = FileChooserButton(
            self.IncompleteDir, parent.SettingsWindow, "folder"
        )
        self.DownloadDir = FileChooserButton(
            self.DownloadDir, parent.SettingsWindow, "folder", self.on_choose_download_dir
        )
        self.UploadDir = FileChooserButton(
            self.UploadDir, parent.SettingsWindow, "folder"
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
                "downloadlimit": self.DownloadSpeed
            }
        }

        self.filterlist = Gtk.ListStore(
            GObject.TYPE_STRING,
            GObject.TYPE_BOOLEAN
        )
        self.downloadfilters = []

        cols = initialise_columns(
            None,
            self.FilterView,
            ["filter", _("Filter"), 250, "text", None],
            ["escaped", _("Escaped"), 40, "toggle", None]
        )

        cols["filter"].set_sort_column_id(0)
        cols["escaped"].set_sort_column_id(1)
        renderers = cols["escaped"].get_cells()

        for render in renderers:
            render.connect('toggled', self.cell_toggle_callback, self.filterlist, 1)

        self.FilterView.set_model(self.filterlist)
        self.FilterView.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)

    def set_settings(self, config):

        self.p.set_widgets_data(config, self.options)

        self.UploadsAllowed.set_sensitive(self.RemoteDownloads.get_active())

        self.filtersiters = {}
        self.filterlist.clear()

        if config["transfers"]["downloadfilters"] != []:
            for dfilter in config["transfers"]["downloadfilters"]:
                dfilter, escaped = dfilter
                self.filtersiters[dfilter] = self.filterlist.append([dfilter, escaped])

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
                "downloadlimit": self.DownloadSpeed.get_value_as_int()
            }
        }

    def on_choose_download_dir(self):
        """
        Function called when the download directory is modified.
        """

        # Get the transfers section
        transfers = self.frame.np.config.sections["transfers"]

        # This function will be called upon creating the settings window,
        # so only force a scan if the user changes his donwload directory
        if self.ShareDownloadDir.get_active():
            if self.DownloadDir.get_path() != transfers["downloaddir"]:
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

    def on_add_filter(self, widget):

        response = combo_box_dialog(
            parent=self.Main.get_toplevel(),
            title=_('Add a Download Filter'),
            message=_('Enter a new download filter:'),
            option=True,
            optionvalue=True,
            optionmessage="Escape this filter?",
            droplist=list(self.filtersiters.keys())
        )

        if isinstance(response, list):

            dfilter = response[0]
            escaped = response[1]

            if dfilter in self.filtersiters:
                self.filterlist.set(self.filtersiters[dfilter], 0, dfilter, 1, escaped)
            else:
                self.filtersiters[dfilter] = self.filterlist.append([dfilter, escaped])

            self.on_verify_filter(self.VerifyFilters)

    def get_filter_list(self):

        self.downloadfilters = []

        df = sorted(self.filtersiters.keys())

        for dfilter in df:
            iterator = self.filtersiters[dfilter]
            dfilter = self.filterlist.get_value(iterator, 0)
            escaped = self.filterlist.get_value(iterator, 1)
            self.downloadfilters.append([dfilter, int(escaped)])

        return self.downloadfilters

    def on_edit_filter(self, widget):

        dfilter = self.get_selected_filter()

        if dfilter:

            iterator = self.filtersiters[dfilter]
            escapedvalue = self.filterlist.get_value(iterator, 1)

            response = combo_box_dialog(
                parent=self.Main.get_toplevel(),
                title=_('Edit a Download Filter'),
                message=_('Modify this download filter:'),
                default_text=dfilter,
                option=True,
                optionvalue=escapedvalue,
                optionmessage="Escape this filter?",
                droplist=list(self.filtersiters.keys())
            )

            if isinstance(response, list):

                new_dfilter, escaped = response

                if new_dfilter in self.filtersiters:
                    self.filterlist.set(self.filtersiters[new_dfilter], 0, new_dfilter, 1, escaped)
                else:
                    self.filtersiters[new_dfilter] = self.filterlist.append([new_dfilter, escaped])
                    del self.filtersiters[dfilter]
                    self.filterlist.remove(iterator)

                self.on_verify_filter(self.VerifyFilters)

    def _selected_filter(self, model, path, iterator, list):
        list.append(iterator)

    def get_selected_filter(self):

        iters = []
        self.FilterView.get_selection().selected_foreach(self._selected_filter, iters)

        if iters == []:
            return None

        dfilter = self.filterlist.get_value(iters[0], 0)

        return dfilter

    def on_remove_filter(self, widget):

        dfilter = self.get_selected_filter()

        if dfilter:

            iterator = self.filtersiters[dfilter]
            self.filterlist.remove(iterator)

            del self.filtersiters[dfilter]

            self.on_verify_filter(self.VerifyFilters)

    def on_default_filters(self, widget):

        self.filtersiters = {}
        self.filterlist.clear()

        defaults = self.frame.np.config.defaults

        for dfilter in defaults["transfers"]["downloadfilters"]:
            dfilter, escaped = dfilter
            self.filtersiters[dfilter] = self.filterlist.append([dfilter, escaped])

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

        if len(failed) >= 1:
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

        self.shareslist = Gtk.ListStore(
            str,
            str
        )

        self.shareddirs = []

        self.bshareslist = Gtk.ListStore(
            str,
            str
        )

        self.bshareddirs = []

        initialise_columns(
            None,
            self.Shares,
            ["virtual_folder", _("Virtual Folder"), 0, "text", None],
            ["folder", _("Folder"), 0, "text", None]
        )

        self.Shares.set_model(self.shareslist)
        self.Shares.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)

        initialise_columns(
            None,
            self.BuddyShares,
            ["virtual_folder", _("Virtual Folder"), 0, "text", None],
            ["folder", _("Folder"), 0, "text", None]
        )

        self.BuddyShares.set_model(self.bshareslist)
        self.BuddyShares.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)

        self.options = {
            "transfers": {
                "shared": self.Shares,
                "friendsonly": self.FriendsOnly,
                "rescanonstartup": self.RescanOnStartup,
                "buddyshared": self.BuddyShares,
                "enablebuddyshares": self.enableBuddyShares
            }
        }

    def set_settings(self, config):

        transfers = config["transfers"]
        self.shareslist.clear()
        self.bshareslist.clear()

        self.p.set_widgets_data(config, self.options)
        self.on_enabled_buddy_shares_toggled(self.enableBuddyShares)

        if transfers["shared"] is not None:

            for (virtual, actual, *unused) in transfers["shared"]:

                self.shareslist.append(
                    [
                        virtual,
                        actual
                    ]
                )

            self.shareddirs = transfers["shared"][:]

        if transfers["buddyshared"] is not None:

            for (virtual, actual, *unused) in transfers["buddyshared"]:
                self.bshareslist.append(
                    [
                        virtual,
                        actual
                    ]
                )

            self.bshareddirs = transfers["buddyshared"][:]

        self.needrescan = False

    def get_settings(self):

        # Buddy shares related menus are activated if needed
        buddies = self.enableBuddyShares.get_active()

        self.frame.rescan_buddy_action.set_enabled(buddies)
        self.frame.browse_buddy_shares_action.set_enabled(buddies)

        # Public shares related menus are deactivated if we only share with friends
        friendsonly = self.FriendsOnly.get_active()

        self.frame.rescan_public_action.set_enabled(not friendsonly)
        self.frame.browse_public_shares_action.set_enabled(not friendsonly)

        return {
            "transfers": {
                "shared": self.shareddirs[:],
                "rescanonstartup": self.RescanOnStartup.get_active(),
                "buddyshared": self.bshareddirs[:],
                "enablebuddyshares": buddies,
                "friendsonly": friendsonly
            }
        }

    def on_enabled_buddy_shares_toggled(self, widget):
        self.on_friends_only_toggled(widget)
        self.needrescan = True

    def on_friends_only_toggled(self, widget):

        friendsonly = self.FriendsOnly.get_active()

        if friendsonly:
            # If sharing only with friends, buddy shares are activated and should be locked
            self.enableBuddyShares.set_active(True)
            self.enableBuddyShares.set_sensitive(False)
        else:
            # If not let the buddy shares checkbox be selectable
            self.enableBuddyShares.set_sensitive(True)

        buddies = self.enableBuddyShares.get_active()

        if buddies:
            # If buddy shares are enabled let the friends only checkbox be selectable
            self.FriendsOnly.set_sensitive(True)
        else:
            # If not the friend only checkbox should be deactivated and locked
            self.FriendsOnly.set_active(False)
            self.FriendsOnly.set_sensitive(False)

        # Buddy shares are activated only if needed
        self.BuddyShares.set_sensitive(buddies)
        self.addBuddySharesButton.set_sensitive(buddies)
        self.removeBuddySharesButton.set_sensitive(buddies)
        self.renameBuddyVirtualsButton.set_sensitive(buddies)

    def add_shared_dir(self, folder, shareslist, shareddirs):

        if folder is None:
            return

        for directory in folder:

            # If the directory is already shared
            if directory in (x[1] for x in self.shareddirs + self.bshareddirs):

                dlg = Gtk.MessageDialog(
                    transient_for=self.Main.get_toplevel(),
                    flags=0,
                    type=Gtk.MessageType.WARNING,
                    buttons=Gtk.ButtonsType.OK,
                    text=_("Warning")
                )
                dlg.format_secondary_text(_("The chosen folder is already shared"))
                dlg.run()
                dlg.destroy()
                return

            virtual = combo_box_dialog(
                parent=self.Main.get_toplevel(),
                title=_("Virtual Name"),
                message=_("Enter virtual name for '%(dir)s':") % {'dir': directory}
            )

            # Remove slashes from share name to avoid path conflicts
            if virtual:
                virtual = virtual.replace('/', '_').replace('\\', '_')

            # If the virtual share name is not already used
            if not virtual or virtual in (x[0] for x in self.shareddirs + self.bshareddirs):

                dlg = Gtk.MessageDialog(
                    transient_for=self.Main.get_toplevel(),
                    flags=0,
                    type=Gtk.MessageType.WARNING,
                    buttons=Gtk.ButtonsType.OK,
                    text=_("Warning")
                )
                dlg.format_secondary_text(_("The chosen virtual name is either empty or already exists"))
                dlg.run()
                dlg.destroy()
                return

            shareslist.append(
                [
                    virtual,
                    directory
                ]
            )

            shareddirs.append((virtual, directory))
            self.needrescan = True

    def on_add_shared_dir(self, widget):

        folder = choose_dir(
            self.Main.get_toplevel(),
            title=_("Add a Shared Folder")
        )

        self.add_shared_dir(folder, self.shareslist, self.shareddirs)

    def on_add_shared_buddy_dir(self, widget):

        folder = choose_dir(
            self.Main.get_toplevel(),
            title=_("Add a Shared Buddy Folder")
        )

        self.add_shared_dir(folder, self.bshareslist, self.bshareddirs)

    def _remove_shared_dir(self, model, path, iterator, list):
        list.append(iterator)

    def on_rename_virtuals(self, widget):

        iters = []
        self.Shares.get_selection().selected_foreach(self._remove_shared_dir, iters)

        for iterator in iters:
            oldvirtual = self.shareslist.get_value(iterator, 0)
            directory = self.shareslist.get_value(iterator, 1)
            oldmapping = (oldvirtual, directory)

            virtual = combo_box_dialog(
                parent=self.Main.get_toplevel(),
                title=_("Virtual Name"),
                message=_("Enter new virtual name for '%(dir)s':") % {'dir': directory}
            )

            if virtual:
                # Remove slashes from share name to avoid path conflicts
                virtual = virtual.replace('/', '_').replace('\\', '_')

                newmapping = (virtual, directory)
                self.shareslist.set_value(iterator, 0, virtual)
                self.shareddirs.remove(oldmapping)
                self.shareddirs.append(newmapping)
                self.needrescan = True

    def on_rename_buddy_virtuals(self, widget):

        iters = []
        self.BuddyShares.get_selection().selected_foreach(self._remove_shared_dir, iters)

        for iterator in iters:
            oldvirtual = self.bshareslist.get_value(iterator, 0)
            directory = self.bshareslist.get_value(iterator, 1)
            oldmapping = (oldvirtual, directory)

            virtual = combo_box_dialog(
                parent=self.Main.get_toplevel(),
                title=_("Virtual Name"),
                message=_("Enter new virtual name for '%(dir)s':") % {'dir': directory}
            )

            if virtual:
                # Remove slashes from share name to avoid path conflicts
                virtual = virtual.replace('/', '_').replace('\\', '_')

                newmapping = (virtual, directory)
                self.bshareslist.set_value(iterator, 0, virtual)
                self.bshareslist.remove(oldmapping)
                self.bshareslist.append(newmapping)
                self.needrescan = True

    def on_remove_shared_dir(self, widget):
        iters = []
        self.Shares.get_selection().selected_foreach(self._remove_shared_dir, iters)

        for iterator in iters:
            virtual = self.shareslist.get_value(iterator, 0)
            actual = self.shareslist.get_value(iterator, 1)
            mapping = (virtual, actual)
            self.shareddirs.remove(mapping)
            self.shareslist.remove(iterator)

        if iters:
            self.needrescan = True

    def on_remove_shared_buddy_dir(self, widget):
        iters = []
        self.BuddyShares.get_selection().selected_foreach(self._remove_shared_dir, iters)

        for iterator in iters:
            virtual = self.bshareslist.get_value(iterator, 0)
            actual = self.bshareslist.get_value(iterator, 1)
            mapping = (virtual, actual)
            self.bshareddirs.remove(mapping)
            self.bshareslist.remove(iterator)

        if iters:
            self.needrescan = True


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
                "fifoqueue": self.FirstInFirstOut,
                "limitby": self.LimitTotalTransfers,
                "queuelimit": self.MaxUserQueue,
                "filelimit": self.MaxUserFiles,
                "friendsnolimits": self.FriendsNoLimits,
                "preferfriends": self.PreferFriends
            }
        }

    def set_settings(self, config):

        self.p.set_widgets_data(config, self.options)

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
        self.QueueBandwidthText2.set_sensitive(not sensitive)

    def on_limit_toggled(self, widget):

        sensitive = widget.get_active()

        for w in self.LimitSpeed, self.LimitPerTransfer, self.LimitTotalTransfers:
            w.set_sensitive(sensitive)


class GeoBlockFrame(BuildFrame):

    def __init__(self, parent):
        self.p = parent
        BuildFrame.__init__(self, "geoblock")

        self.options = {
            "transfers": {
                "geoblock": self.GeoBlock,
                "geopanic": self.GeoPanic,
                "geoblockcc": self.GeoBlockCC
            }
        }

    def set_settings(self, config):
        transfers = config["transfers"]
        self.p.set_widgets_data(config, self.options)

        if transfers["geoblockcc"] is not None:
            self.GeoBlockCC.set_text(transfers["geoblockcc"][0])

        self.on_geo_block_toggled(self.GeoBlock)

    def get_settings(self):
        return {
            "transfers": {
                "geoblock": self.GeoBlock.get_active(),
                "geopanic": self.GeoPanic.get_active(),
                "geoblockcc": [self.GeoBlockCC.get_text().upper()]
            }
        }

    def on_geo_block_toggled(self, widget):
        sensitive = widget.get_active()
        self.GeoPanic.set_sensitive(sensitive)
        self.GeoBlockCC.set_sensitive(sensitive)


class UserInfoFrame(BuildFrame):

    def __init__(self, parent):

        self.p = parent

        BuildFrame.__init__(self, "userinfo")

        self.ImageChooser = FileChooserButton(self.ImageChooser, parent.SettingsWindow, "image")

        self.options = {
            "userinfo": {
                "descr": None,
                "pic": self.ImageChooser
            }
        }

    def set_settings(self, config):

        self.p.set_widgets_data(config, self.options)

        if config["userinfo"]["descr"] is not None:
            descr = unescape(config["userinfo"]["descr"])
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
        self.ignorelist = Gtk.ListStore(GObject.TYPE_STRING)
        column = Gtk.TreeViewColumn(_("Users"), Gtk.CellRendererText(), text=0)
        self.IgnoredUsers.append_column(column)
        self.IgnoredUsers.set_model(self.ignorelist)
        self.IgnoredUsers.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)

        self.ignored_ips = {}
        self.ignored_ips_list = Gtk.ListStore(str, str)
        cols = initialise_columns(
            None,
            self.IgnoredIPs,
            ["addresses", _("Addresses"), -1, "text", None],
            ["users", _("Users"), -1, "text", None]
        )
        cols["addresses"].set_sort_column_id(0)
        cols["users"].set_sort_column_id(1)

        self.IgnoredIPs.set_model(self.ignored_ips_list)
        self.IgnoredIPs.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)

    def set_settings(self, config):
        server = config["server"]

        self.ignorelist.clear()
        self.ignored_ips_list.clear()
        self.ignored_users = []
        self.ignored_ips = {}
        self.p.set_widgets_data(config, self.options)

        if server["ignorelist"] is not None:
            self.ignored_users = server["ignorelist"][:]

        if server["ipignorelist"] is not None:
            self.ignored_ips = server["ipignorelist"].copy()
            for ip, user in self.ignored_ips.items():
                self.ignored_ips_list.append([ip, user])

    def get_settings(self):
        return {
            "server": {
                "ignorelist": self.ignored_users[:],
                "ipignorelist": self.ignored_ips.copy()
            }
        }

    def _append_item(self, model, path, iterator, line):
        line.append(iterator)

    def on_add_ignored(self, widget):

        user = entry_dialog(
            self.Main.get_toplevel(),
            _("Ignore User..."),
            _("User:")
        )

        if user and user not in self.ignored_users:
            self.ignored_users.append(user)
            self.ignorelist.append([user])

    def on_remove_ignored(self, widget):
        iters = []
        self.IgnoredUsers.get_selection().selected_foreach(self._append_item, iters)
        for iterator in iters:
            user = self.ignorelist.get_value(iterator, 0)
            self.ignored_users.remove(user)
            self.ignorelist.remove(iterator)

    def on_clear_ignored(self, widget):
        self.ignored_users = []
        self.ignorelist.clear()

    def on_add_ignored_ip(self, widget):

        ip = entry_dialog(
            self.Main.get_toplevel(),
            _("Ignore IP Address..."),
            _("IP:") + " " + _("* is a wildcard")
        )

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
            self.ignored_ips_list.append([ip, ""])

    def on_remove_ignored_ip(self, widget):
        iters = []
        self.IgnoredIPs.get_selection().selected_foreach(self._append_item, iters)
        for iterator in iters:
            ip = self.ignored_ips_list.get_value(iterator, 0)
            del self.ignored_ips[ip]
            self.ignored_ips_list.remove(iterator)

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
        self.banlist_model = Gtk.ListStore(GObject.TYPE_STRING)
        column = Gtk.TreeViewColumn(_("Users"), Gtk.CellRendererText(), text=0)
        self.BannedList.append_column(column)
        self.BannedList.set_model(self.banlist_model)
        self.BannedList.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)

        self.blocked_list = {}
        self.blocked_list_model = Gtk.ListStore(str, str)
        cols = initialise_columns(
            None,
            self.BlockedList,
            ["addresses", _("Addresses"), -1, "text", None],
            ["users", _("Users"), -1, "text", None]
        )
        cols["addresses"].set_sort_column_id(0)
        cols["users"].set_sort_column_id(1)

        self.BlockedList.set_model(self.blocked_list_model)
        self.BlockedList.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)

    def set_settings(self, config):
        server = config["server"]
        transfers = config["transfers"]
        self.banlist_model.clear()
        self.blocked_list_model.clear()

        self.banlist = server["banlist"][:]
        self.p.set_widgets_data(config, self.options)

        if server["ipblocklist"] is not None:
            self.blocked_list = server["ipblocklist"].copy()
            for blocked, user in server["ipblocklist"].items():
                self.blocked_list_model.append([blocked, user])

        if transfers["usecustomban"] is not None:
            self.UseCustomBan.set_active(transfers["usecustomban"])

        if transfers["customban"] is not None:
            self.CustomBan.set_text(transfers["customban"])

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

    def on_add_banned(self, widget):

        user = entry_dialog(
            self.Main.get_toplevel(),
            _("Ban User..."),
            _("User:")
        )

        if user and user not in self.banlist:
            self.banlist.append(user)
            self.banlist_model.append([user])

    def _append_item(self, model, path, iterator, line):
        line.append(iterator)

    def on_remove_banned(self, widget):
        iters = []
        self.BannedList.get_selection().selected_foreach(self._append_item, iters)
        for iterator in iters:
            user = self.banlist_model.get_value(iterator, 0)
            self.banlist.remove(user)
            self.banlist_model.remove(iterator)

    def on_clear_banned(self, widget):
        self.banlist = []
        self.banlist_model.clear()

    def on_use_custom_ban_toggled(self, widget):
        self.CustomBan.set_sensitive(widget.get_active())

    def on_add_blocked(self, widget):

        ip = entry_dialog(
            self.Main.get_toplevel(),
            _("Block IP Address..."),
            _("IP:") + " " + _("* is a wildcard")
        )

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
            self.blocked_list_model.append([ip, ""])

    def on_remove_blocked(self, widget):
        iters = []
        self.BlockedList.get_selection().selected_foreach(self._append_item, iters)
        for iterator in iters:
            ip = self.blocked_list_model.get_value(iterator, 0)
            del self.blocked_list[ip]
            self.blocked_list_model.remove(iterator)

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
        defaults = self.frame.np.config.defaults
        self.PrivateMessage.set_text(defaults["ui"]["speechprivate"])

    def on_default_rooms(self, widget):
        defaults = self.frame.np.config.defaults
        self.RoomMessage.set_text(defaults["ui"]["speechrooms"])

    def on_default_tts(self, widget):
        defaults = self.frame.np.config.defaults
        self.TTSCommand.get_child().set_text(defaults["ui"]["speechcommand"])

    def on_text_to_speech_toggled(self, widget):

        sensitive = self.TextToSpeech.get_active()

        self.TTSGrid.set_sensitive(sensitive)

    def set_settings(self, config):

        ui = config["ui"]

        self.p.set_widgets_data(config, self.options)

        for i in ["%(user)s", "%(message)s"]:

            if i not in ui["speechprivate"]:
                self.default_private(None)

            if i not in ui["speechrooms"]:
                self.default_rooms(None)

        self.on_text_to_speech_toggled(self.TextToSpeech)

    def get_settings(self):

        return {
            "ui": {
                "speechenabled": self.TextToSpeech.get_active(),
                "speechcommand": self.TTSCommand.get_child().get_text(),
                "speechrooms": self.RoomMessage.get_text(),
                "speechprivate": self.PrivateMessage.get_text()
            }
        }


class IconsFrame(BuildFrame):

    def __init__(self, parent):

        self.p = parent

        BuildFrame.__init__(self, "icons")

        self.ThemeDir = FileChooserButton(self.ThemeDir, parent.SettingsWindow, "folder")

        self.options = {
            "ui": {
                "icontheme": self.ThemeDir,
                "trayicon": self.TrayiconCheck,
                "startup_hidden": self.StartupHidden,
                "exitdialog": None
            }
        }

        self.N.set_from_pixbuf(self.frame.images["n"])
        self.Away.set_from_pixbuf(self.frame.images["away"])
        self.Online.set_from_pixbuf(self.frame.images["online"])
        self.Offline.set_from_pixbuf(self.frame.images["offline"])
        self.Hilite.set_from_pixbuf(self.frame.images["hilite"])
        self.Hilite3.set_from_pixbuf(self.frame.images["hilite3"])
        self.Trayicon_Away.set_from_pixbuf(self.frame.images["trayicon_away"])
        self.Trayicon_Connect.set_from_pixbuf(self.frame.images["trayicon_connect"])
        self.Trayicon_Disconnect.set_from_pixbuf(self.frame.images["trayicon_disconnect"])
        self.Trayicon_Msg.set_from_pixbuf(self.frame.images["trayicon_msg"])
        self.Notify.set_from_pixbuf(self.frame.images["notify"])

    def set_settings(self, config):

        self.p.set_widgets_data(config, self.options)

        if config["ui"]["exitdialog"] is not None:

            exitdialog = int(config["ui"]["exitdialog"])

            if exitdialog == 1:
                self.DialogOnClose.set_active(True)
            elif exitdialog == 2:
                self.SendToTrayOnClose.set_active(True)
            elif exitdialog == 0:
                self.QuitOnClose.set_active(True)

        if sys.platform == "darwin":
            # Tray icons don't work as expected on macOS
            self.hide_tray_icon_settings()
            return

        sensitive = self.TrayiconCheck.get_active()
        self.StartupHidden.set_sensitive(sensitive)

    def hide_tray_icon_settings(self):

        # Hide widgets
        self.TraySettings.hide()

        self.Trayicon_Label.hide()
        self.Trayicon_Away.hide()
        self.Trayicon_Away_Label.hide()
        self.Trayicon_Connect.hide()
        self.Trayicon_Online_Label.hide()
        self.Trayicon_Disconnect.hide()
        self.Trayicon_Offline_Label.hide()
        self.Trayicon_Msg.hide()
        self.Trayicon_Hilite_Label.hide()

        # Always exit on close, since there's no tray icon
        self.QuitOnClose.set_active(True)

    def on_default_theme(self, widget):

        self.ThemeDir.clear()

    def on_toggle_tray(self, widget):

        self.StartupHidden.set_sensitive(widget.get_active())

        if not widget.get_active() and self.StartupHidden.get_active():
            self.StartupHidden.set_active(widget.get_active())

    def get_settings(self):

        mainwindow_close = 0

        widgets = [self.QuitOnClose, self.DialogOnClose, self.SendToTrayOnClose]

        for i in widgets:
            if i.get_active():
                mainwindow_close = widgets.index(i)
                break

        return {
            "ui": {
                "icontheme": self.ThemeDir.get_path(),
                "trayicon": self.TrayiconCheck.get_active(),
                "startup_hidden": self.StartupHidden.get_active(),
                "exitdialog": mainwindow_close
            }
        }


class FontsColorsFrame(BuildFrame):

    def __init__(self, parent):

        self.p = parent

        BuildFrame.__init__(self, "fontscolors")

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
                "showaway": self.DisplayAwayColors,
                "urlcolor": self.EntryURL,
                "tab_default": self.EntryRegularTab,
                "tab_hilite": self.EntryHighlightTab,
                "tab_changed": self.EntryChangedTab,
                "dark_mode": self.DarkMode
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

    def set_settings(self, config):

        self.p.set_widgets_data(config, self.options)

        self.update_color_buttons(config)
        self.on_toggled_away_colors(self.DisplayAwayColors)
        self.needcolors = 0

    def get_settings(self):

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

                "chatlocal": self.EntryLocal.get_text(),
                "chatremote": self.EntryRemote.get_text(),
                "chatme": self.EntryMe.get_text(),
                "chathilite": self.EntryHighlight.get_text(),
                "urlcolor": self.EntryURL.get_text(),
                "textbg": self.EntryBackground.get_text(),
                "inputcolor": self.EntryInput.get_text(),
                "search": self.EntryImmediate.get_text(),
                "searchq": self.EntryQueue.get_text(),
                "showaway": self.DisplayAwayColors.get_active(),
                "useraway": self.EntryAway.get_text(),
                "useronline": self.EntryOnline.get_text(),
                "useroffline": self.EntryOffline.get_text(),
                "usernamehotspots": self.UsernameHotspots.get_active(),
                "tab_hilite": self.EntryHighlightTab.get_text(),
                "tab_default": self.EntryRegularTab.get_text(),
                "tab_changed": self.EntryChangedTab.get_text(),
                "dark_mode": self.DarkMode.get_active()
            }
        }

    """ Fonts """

    def on_default_font(self, widget):

        font_button = self.__dict__[Gtk.Buildable.get_name(widget).replace("Default", "Select")]
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

    def update_color_buttons(self, config):

        for section, color_ids in self.colorsd.items():
            for color_id in color_ids:
                self.update_color_button(config, color_id)

    def set_default_color(self, section, color_id):

        defaults = self.frame.np.config.defaults
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
        entry = self.__dict__[Gtk.Buildable.get_name(widget).replace("Pick", "Entry")]
        entry.set_text(color)

    def on_default_color(self, widget):

        entry = self.__dict__[Gtk.Buildable.get_name(widget).replace("Default", "Entry")]

        for section in self.options:
            for key, value in self.options[section].items():
                if value is entry:
                    self.set_default_color(section, key)
                    return

        entry.set_text("")

    def on_toggled_away_colors(self, widget):

        sensitive = widget.get_active()

        self.EntryAway.set_sensitive(sensitive)
        self.PickAway.set_sensitive(sensitive)
        self.DefaultAway.set_sensitive(sensitive)

    def on_username_hotspots_toggled(self, widget):

        sensitive = widget.get_active()
        display_away = self.DisplayAwayColors.get_active()

        self.DisplayAwayColors.set_sensitive(sensitive)

        self.EntryAway.set_sensitive(sensitive and display_away)
        self.EntryOnline.set_sensitive(sensitive)
        self.EntryOffline.set_sensitive(sensitive)

        self.DefaultAway.set_sensitive(sensitive and display_away)
        self.DefaultOnline.set_sensitive(sensitive)
        self.DefaultOffline.set_sensitive(sensitive)

        self.PickAway.set_sensitive(sensitive and display_away)
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

            color_button = self.__dict__[Gtk.Buildable.get_name(widget).replace("Entry", "Pick")]
            color_button.set_rgba(rgba)

        self.needcolors = 1


class TabsFrame(BuildFrame):

    def __init__(self, parent):

        self.p = parent

        BuildFrame.__init__(self, "tabs")

        # Define options for each GtkComboBox using a liststore
        # The first element is the translated string,
        # the second is a GtkPositionType
        self.pos_list = Gtk.ListStore(GObject.TYPE_STRING, GObject.TYPE_STRING)
        self.pos_list.append([_("Top"), "Top"])
        self.pos_list.append([_("Bottom"), "Bottom"])
        self.pos_list.append([_("Left"), "Left"])
        self.pos_list.append([_("Right"), "Right"])

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

        self.options = {
            "ui": {
                "tabmain": self.MainPosition,
                "tabrooms": self.ChatRoomsPosition,
                "tabprivate": self.PrivateChatPosition,
                "tabsearch": self.SearchPosition,
                "tabinfo": self.UserInfoPosition,
                "tabbrowse": self.UserBrowsePosition,
                "labelmain": self.MainAngleSpin,
                "labelrooms": self.ChatRoomsAngleSpin,
                "labelprivate": self.PrivateChatAngleSpin,
                "labelsearch": self.SearchAngleSpin,
                "labelinfo": self.UserInfoAngleSpin,
                "labelbrowse": self.UserBrowseAngleSpin,
                "tab_select_previous": self.TabSelectPrevious,
                "tabclosers": self.TabClosers,
                "tab_reorderable": self.TabReorderable,
                "tab_status_icons": self.TabStatusIcons
            }
        }

    def set_settings(self, config):

        self.p.set_widgets_data(config, self.options)

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
            config_val = config["ui"][opt]

            # Iterate over entries to find which one should be active
            self.options["ui"][opt].get_model().foreach(set_active_conf, {
                "cfg": config_val,
                "combobox": self.options["ui"][opt]
            })

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
                "tabmain": self.pos_list.get_value(iter_main, 1),
                "tabrooms": self.pos_list.get_value(iter_rooms, 1),
                "tabprivate": self.pos_list.get_value(iter_private, 1),
                "tabsearch": self.pos_list.get_value(iter_search, 1),
                "tabinfo": self.pos_list.get_value(iter_info, 1),
                "tabbrowse": self.pos_list.get_value(iter_browse, 1),
                "labelmain": self.MainAngleSpin.get_value_as_int(),
                "labelrooms": self.ChatRoomsAngleSpin.get_value_as_int(),
                "labelprivate": self.PrivateChatAngleSpin.get_value_as_int(),
                "labelsearch": self.SearchAngleSpin.get_value_as_int(),
                "labelinfo": self.UserInfoAngleSpin.get_value_as_int(),
                "labelbrowse": self.UserBrowseAngleSpin.get_value_as_int(),
                "tab_select_previous": self.TabSelectPrevious.get_active(),
                "tabclosers": self.TabClosers.get_active(),
                "tab_reorderable": self.TabReorderable.get_active(),
                "tab_status_icons": self.TabStatusIcons.get_active()
            }
        }


class LoggingFrame(BuildFrame):

    def __init__(self, parent):

        self.p = parent

        BuildFrame.__init__(self, "log")

        self.PrivateLogDir = FileChooserButton(self.PrivateLogDir, parent.SettingsWindow, "folder")
        self.RoomLogDir = FileChooserButton(self.RoomLogDir, parent.SettingsWindow, "folder")
        self.TransfersLogDir = FileChooserButton(self.TransfersLogDir, parent.SettingsWindow, "folder")
        self.DebugLogDir = FileChooserButton(self.DebugLogDir, parent.SettingsWindow, "folder")

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

    def set_settings(self, config):
        self.p.set_widgets_data(config, self.options)

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
        defaults = self.frame.np.config.defaults
        self.LogFileFormat.set_text(defaults["logging"]["log_timestamp"])

    def on_room_default_timestamp(self, widget):
        defaults = self.frame.np.config.defaults
        self.ChatRoomFormat.set_text(defaults["logging"]["rooms_timestamp"])

    def on_private_default_timestamp(self, widget):
        defaults = self.frame.np.config.defaults
        self.PrivateChatFormat.set_text(defaults["logging"]["private_timestamp"])


class SearchesFrame(BuildFrame):

    def __init__(self, parent):
        self.p = parent
        BuildFrame.__init__(self, "search")
        self.options = {
            "searches": {
                "maxresults": self.MaxResults,
                "enablefilters": self.EnableFilters,
                "re_filter": self.RegexpFilters,
                "defilter": None,
                "search_results": self.ToggleResults,
                "max_displayed_results": self.MaxDisplayedResults,
                "max_stored_results": self.MaxStoredResults,
                "min_search_chars": self.MinSearchChars,
                "remove_special_chars": self.RemoveSpecialChars
            }
        }

    def set_settings(self, config):
        try:
            searches = config["searches"]
        except Exception:
            searches = None

        self.p.set_widgets_data(config, self.options)

        if searches["defilter"] is not None:
            self.FilterIn.set_text(str(searches["defilter"][0]))
            self.FilterOut.set_text(str(searches["defilter"][1]))
            self.FilterSize.set_text(str(searches["defilter"][2]))
            self.FilterBR.set_text(str(searches["defilter"][3]))
            self.FilterFree.set_active(str(searches["defilter"][4]))

            if(len(searches["defilter"]) > 5):
                self.FilterCC.set_text(str(searches["defilter"][5]))

            if(len(searches["defilter"]) > 6):
                self.FilterType.set_text(str(searches["defilter"][6]))

        self.ClearSearchHistorySuccess.hide()
        self.ClearFilterHistorySuccess.hide()

        self.on_enable_search_results(self.ToggleResults)

    def get_settings(self):
        maxresults = self.MaxResults.get_value_as_int()
        return {
            "searches": {
                "maxresults": maxresults,
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
                "max_stored_results": self.MaxStoredResults.get_value_as_int(),
                "min_search_chars": self.MinSearchChars.get_value_as_int(),
                "remove_special_chars": self.RemoveSpecialChars.get_active()
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
        for w in self.FilterIn, self.FilterOut, self.FilterType, self.FilterSize, self.FilterBR, self.FilterCC, self.FilterFree:
            w.set_sensitive(active)

    def on_enable_search_results(self, widget):
        active = widget.get_active()
        for w in self.MinSearchCharsL1, self.MinSearchChars, self.MinSearchCharsL2, \
                self.MaxResults, self.MaxResultsL1, self.MaxResultsL2:
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

    def set_settings(self, config):
        self.p.set_widgets_data(config, self.options)

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

    def set_settings(self, config):
        self.p.set_widgets_data(config, self.options)

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

        self.protocolmodel = Gtk.ListStore(
            GObject.TYPE_STRING,
            GObject.TYPE_STRING
        )

        self.protocols = {}

        cols = initialise_columns(
            None,
            self.ProtocolHandlers,
            ["protocol", _("Protocol"), -1, "text", None],
            ["handler", _("Handler"), -1, "combo", None]
        )

        cols["protocol"].set_sort_column_id(0)
        cols["handler"].set_sort_column_id(1)

        self.ProtocolHandlers.set_model(self.protocolmodel)
        self.ProtocolHandlers.get_selection().connect("changed", self.on_select)

        renderers = cols["handler"].get_cells()
        for render in renderers:
            render.connect('edited', self.cell_edited_callback, self.ProtocolHandlers, 1)

    def cell_edited_callback(self, widget, index, value, treeview, pos):
        store = treeview.get_model()
        iterator = store.get_iter(index)
        store.set(iterator, pos, value)

    def set_settings(self, config):

        self.protocolmodel.clear()
        self.protocols.clear()
        self.p.set_widgets_data(config, self.options)

        urls = config["urls"]

        if urls["protocols"] is not None:

            for key in urls["protocols"].keys():
                if urls["protocols"][key][-1:] == "&":
                    command = urls["protocols"][key][:-1].rstrip()
                else:
                    command = urls["protocols"][key]

                iterator = self.protocolmodel.append([key, command])
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

        self.RemoveHandler.set_sensitive(act)
        self.addButton.set_sensitive(act)
        self.HumanizeURLs.set_sensitive(act)
        self.ProtocolHandlers.set_sensitive(act)
        self.ProtocolCombo.set_sensitive(act)
        self.Handler.set_sensitive(act)

    def on_select(self, selection):

        model, iterator = selection.get_selected()

        if iterator is None:
            self.ProtocolCombo.get_child().set_text("")
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
            iterator = self.protocolmodel.append([protocol, command])
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

        self.censor_list_model = Gtk.ListStore(GObject.TYPE_STRING)

        cols = initialise_columns(
            None,
            self.CensorList,
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

    def set_settings(self, config):

        self.censor_list_model.clear()

        self.p.set_widgets_data(config, self.options)

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

    def on_add(self, widget):

        iterator = self.censor_list_model.append([""])

        selection = self.CensorList.get_selection()
        selection.unselect_all()
        selection.select_iter(iterator)

        col = self.CensorList.get_column(0)

        self.CensorList.set_cursor(self.censor_list_model.get_path(iterator), col, True)

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

        self.replacelist = Gtk.ListStore(
            GObject.TYPE_STRING,
            GObject.TYPE_STRING
        )

        cols = initialise_columns(
            None,
            self.ReplacementList,
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

    def set_settings(self, config):
        self.replacelist.clear()
        self.p.set_widgets_data(config, self.options)
        words = config["words"]
        if words["autoreplaced"] is not None:
            for word, replacement in words["autoreplaced"].items():
                try:
                    self.replacelist.append([word, replacement])
                except TypeError:
                    # Invalid entry
                    continue

        self.on_replace_check(self.ReplaceCheck)

    def on_replace_check(self, widget):
        sensitive = widget.get_active()
        self.ReplacementList.set_sensitive(sensitive)
        self.RemoveReplacement.set_sensitive(sensitive)
        self.AddReplacement.set_sensitive(sensitive)
        self.ClearReplacements.set_sensitive(sensitive)
        self.DefaultReplacements.set_sensitive(sensitive)

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
        iterator = self.replacelist.append(["", ""])
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
        defaults = self.frame.np.config.defaults

        for word, replacement in defaults["words"]["autoreplaced"].items():
            self.replacelist.append([word, replacement])


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

    def set_settings(self, config):
        self.needcompletion = 0

        self.SpellCheck.set_sensitive(True if self.frame.spell_checker else False)

        self.p.set_widgets_data(config, self.options)

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

    def set_settings(self, config):

        self.p.set_widgets_data(config, self.options)

        # Save reference to format list for get_settings()
        self.custom_format_list = config["players"]["npformatlist"]

        # Update UI with saved player
        self.set_player(config["players"]["npplayer"])
        self.update_now_playing_info()

        # Add formats
        self.NPFormat.remove_all()

        for item in self.default_format_list:
            self.NPFormat.append_text(str(item))

        if self.custom_format_list:
            for item in self.custom_format_list:
                self.NPFormat.append_text(str(item))

        if config["players"]["npformat"] == "":
            # If there's no default format in the config: set the first of the list
            self.NPFormat.set_active(0)
        else:
            # If there's is a default format in the config: select the right item
            for (i, v) in enumerate(self.NPFormat.get_model()):
                if v[0] == config["players"]["npformat"]:
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
            self.player_input.set_text(_("Username;APIKEY :"))

        elif self.NP_mpris.get_active():
            self.player_replacers = ["$n", "$p", "$a", "$b", "$t", "$y", "$c", "$r", "$k", "$l", "$f"]
            self.player_input.set_text(_("Client name (e.g. amarok, audacious, exaile) or empty for auto:"))

        elif self.NP_other.get_active():
            self.player_replacers = ["$n"]
            self.player_input.set_text(_("Command :"))

        legend = ""

        for item in self.player_replacers:
            legend += item + "\t"

            if item == "$t":
                legend += _("Title")
            elif item == "$n":
                legend += _("Now Playing (typically \"%(artist)s - %(title)s\")") % {'artist': _("Artist"), 'title': _("Title")}
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

        self.Legend.set_text(legend)

    def set_now_playing_example(self, title):
        self.Example.set_text(title)

    def get_settings(self):

        npformat = self.get_format()

        if npformat and not npformat.isspace() and \
                npformat not in self.custom_format_list and \
                npformat not in self.default_format_list:
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
            }
        }

    def set_settings(self, config):
        self.p.set_widgets_data(config, self.options)

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
            }
        }


class BuildDialog(Gtk.Dialog):
    """ Class used to build a custom dialog for the plugins """

    def __init__(self, parent):

        self.settings = parent.p

        # Build the window
        load_ui_elements(self, os.path.join(self.settings.frame.gui_dir, "ui", "settings", "pluginproperties.ui"))
        self.PluginProperties.set_transient_for(self.settings.SettingsWindow)

        self.tw = {}
        self.options = {}
        self.plugin = None

    def generate_label(self, text):

        label = Gtk.Label(text)
        label.set_justify(Gtk.Justification.FILL)
        label.set_line_wrap(True)
        return label

    def generate_tree_view(self, name, description, value, c=0):

        self.tw["box%d" % c] = Gtk.Box(False, 5)
        self.tw["box%d" % c].set_orientation(Gtk.Orientation.VERTICAL)

        self.tw[name + "SW"] = Gtk.ScrolledWindow()
        self.tw[name + "SW"].set_hexpand(True)
        self.tw[name + "SW"].set_vexpand(True)
        self.tw[name + "SW"].set_min_content_height(200)
        self.tw[name + "SW"].set_min_content_width(350)
        self.tw[name + "SW"].set_shadow_type(Gtk.ShadowType.IN)
        self.tw[name + "SW"].set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        self.tw[name] = Gtk.TreeView()
        self.tw[name].set_model(Gtk.ListStore(GObject.TYPE_STRING))
        self.tw[name + "SW"].add(self.tw[name])

        self.tw["box%d" % c].add(self.tw[name + "SW"])

        cols = initialise_columns(
            None,
            self.tw[name],
            [description, description, 150, "edit", None]
        )

        try:
            self.settings.set_widget(self.tw[name], value)
        except Exception:
            pass

        self.add_button = Gtk.Button(_("Add"), Gtk.STOCK_ADD)
        self.remove_button = Gtk.Button(_("Remove"), Gtk.STOCK_REMOVE)

        self.tw["vbox%d" % c] = Gtk.Box(False, 5)
        self.tw["vbox%d" % c].add(self.add_button)
        self.tw["vbox%d" % c].add(self.remove_button)

        self.Main.add(self.tw["box%d" % c])
        self.Main.add(self.tw["vbox%d" % c])

        renderers = cols[description].get_cells()
        for render in renderers:
            render.connect('edited', self.cell_edited_callback, self.tw[name])

        self.add_button.connect("clicked", self.on_add, self.tw[name])
        self.remove_button.connect("clicked", self.on_remove, self.tw[name])

    def cell_edited_callback(self, widget, index, value, treeview):
        store = treeview.get_model()
        iterator = store.get_iter(index)
        store.set(iterator, 0, value)

    def on_add(self, widget, treeview):

        iterator = treeview.get_model().append([""])
        col = treeview.get_column(0)

        treeview.set_cursor(treeview.get_model().get_path(iterator), col, True)

    def on_remove(self, widget, treeview):
        selection = treeview.get_selection()
        iterator = selection.get_selected()[1]
        if iterator is not None:
            treeview.get_model().remove(iterator)

    def add_options(self, plugin, options=None):

        if options is None:
            options = {}

        self.options = options
        self.plugin = plugin

        c = 0

        for name, data in options.items():
            if plugin not in self.settings.frame.np.config.sections["plugins"] or name not in self.settings.frame.np.config.sections["plugins"][plugin]:
                if plugin not in self.settings.frame.np.config.sections["plugins"]:
                    print("No1 " + plugin + ", " + repr(list(self.settings.frame.np.config.sections["plugins"].keys())))
                elif name not in self.settings.frame.np.config.sections["plugins"][plugin]:
                    print("No2 " + name + ", " + repr(list(self.settings.frame.np.config.sections["plugins"][plugin].keys())))
                continue

            # We currently support SpinButtons, TreeView (one per plugin) and Checkboxes.
            # There's no reason more widgets cannot be added,
            # and we can use self.settings.set_widget and self.settings.get_widget_data to set and get values
            #
            # Todo: Gtk.ComboBox, and Gtk.RadioButton

            value = self.settings.frame.np.config.sections["plugins"][plugin][name]

            if data["type"] in ("integer", "int", "float"):
                self.tw["box%d" % c] = Gtk.Box(False, 5)
                self.tw["label%d" % c] = self.generate_label(data["description"])
                self.tw["box%d" % c].add(self.tw["label%d" % c])

                self.tw[name] = Gtk.SpinButton.new(Gtk.Adjustment(0, 0, 99999, 1, 10, 0), 1, 2)
                self.settings.set_widget(self.tw[name], self.settings.frame.np.config.sections["plugins"][plugin][name])
                self.tw["box%d" % c].add(self.tw[name])
                self.Main.add(self.tw["box%d" % c])

            elif data["type"] in ("bool",):
                self.tw["box%d" % c] = Gtk.Box(False, 5)
                self.tw["label%d" % c] = self.generate_label(data["description"])
                self.tw["box%d" % c].add(self.tw["label%d" % c])

                self.tw[name] = Gtk.CheckButton()
                self.settings.set_widget(self.tw[name], self.settings.frame.np.config.sections["plugins"][plugin][name])
                self.tw["box%d" % c].add(self.tw[name])
                self.Main.add(self.tw["box%d" % c])

            elif data["type"] in ("str", "string"):
                self.tw["box%d" % c] = Gtk.Box(False, 5)
                self.tw["label%d" % c] = self.generate_label(data["description"])
                self.tw["box%d" % c].add(self.tw["label%d" % c])

                self.tw[name] = Gtk.Entry()
                self.settings.set_widget(self.tw[name], self.settings.frame.np.config.sections["plugins"][plugin][name])
                self.tw["box%d" % c].add(self.tw[name])
                self.Main.add(self.tw["box%d" % c])

            elif data["type"] in ("textview"):
                self.tw["box%d" % c] = Gtk.Box(False, 5)
                self.tw["label%d" % c] = self.generate_label(data["description"])
                self.tw["box%d" % c].add(self.tw["label%d" % c])

                self.tw[name] = Gtk.TextView()
                self.settings.set_widget(self.tw[name], self.settings.frame.np.config.sections["plugins"][plugin][name])

                self.tw["scrolledwindow%d" % c] = Gtk.ScrolledWindow()
                self.tw["scrolledwindow%d" % c].set_hexpand(True)
                self.tw["scrolledwindow%d" % c].set_vexpand(True)
                self.tw["scrolledwindow%d" % c].set_min_content_height(200)
                self.tw["scrolledwindow%d" % c].set_min_content_width(600)
                self.tw["scrolledwindow%d" % c].set_shadow_type(Gtk.ShadowType.IN)
                self.tw["scrolledwindow%d" % c].add(self.tw[name])

                self.tw["box%d" % c].add(self.tw["scrolledwindow%d" % c])
                self.Main.add(self.tw["box%d" % c])

            elif data["type"] in ("list string",):
                self.generate_tree_view(name, data["description"], value, c)

            elif data["type"] in ("file",):
                self.tw["box%d" % c] = Gtk.Box(False, 5)
                self.tw["label%d" % c] = self.generate_label(data["description"])
                self.tw["box%d" % c].add(self.tw["label%d" % c])

                button_widget = Gtk.Button()
                button_widget.set_hexpand(True)

                try:
                    chooser = data["chooser"]
                except KeyError:
                    chooser = None

                self.tw[name] = FileChooserButton(button_widget, self.PluginProperties, chooser)
                self.settings.set_widget(self.tw[name], self.settings.frame.np.config.sections["plugins"][plugin][name])
                self.tw["box%d" % c].add(button_widget)
                self.Main.add(self.tw["box%d" % c])

            else:
                print("Unknown setting type '%s', data '%s'" % (name, data))

            c += 1

        self.PluginProperties.show_all()

    def on_cancel(self, widget):
        self.PluginProperties.destroy()

    def on_okay(self, widget):

        for name in self.options:
            value = self.settings.get_widget_data(self.tw[name])
            if value is not None:
                self.settings.frame.np.config.sections["plugins"][self.plugin][name] = value

        self.PluginProperties.destroy()
        self.settings.frame.np.pluginhandler.plugin_settings(self.plugin, self.settings.frame.np.pluginhandler.loaded_plugins[self.plugin].PLUGIN)

    def show(self):
        self.PluginProperties.show()


class PluginsFrame(BuildFrame):

    def __init__(self, parent):

        self.p = parent
        BuildFrame.__init__(self, "plugin")

        self.options = {
            "plugins": {
                "enable": self.PluginsEnable
            }
        }

        self.plugins_model = Gtk.ListStore(
            GObject.TYPE_BOOLEAN,
            GObject.TYPE_STRING,
            GObject.TYPE_STRING
        )

        self.plugins = []
        self.pluginsiters = {}
        self.selected_plugin = None

        cols = initialise_columns(
            None,
            self.PluginTreeView,
            ["enabled", _("Enabled"), 0, "toggle", None],
            ["plugins", _("Plugins"), 380, "text", None]
        )

        cols["enabled"].set_sort_column_id(0)
        cols["plugins"].set_sort_column_id(1)

        renderers = cols["enabled"].get_cells()
        for render in renderers:
            column_pos = 0
            render.connect('toggled', self.cell_toggle_callback, self.PluginTreeView, column_pos)

        self.PluginTreeView.set_model(self.plugins_model)
        self.PluginTreeView.get_selection().connect("changed", self.on_select_plugin)

    def on_plugin_properties(self, widget):

        if self.selected_plugin is None:
            return

        dialog = BuildDialog(self)

        dialog.add_options(
            self.selected_plugin,
            self.frame.np.pluginhandler.get_plugin_settings(self.selected_plugin)
        )

        dialog.show()

    def on_select_plugin(self, selection):

        model, iterator = selection.get_selected()
        if iterator is None:
            self.selected_plugin = None
            return

        self.selected_plugin = model.get_value(iterator, 2)
        info = self.frame.np.pluginhandler.get_plugin_info(self.selected_plugin)

        self.PluginVersion.set_markup("<b>%(version)s</b>" % {"version": info['Version']})
        self.PluginName.set_markup("<b>%(name)s</b>" % {"name": info['Name']})
        self.PluginDescription.get_buffer().set_text("%(description)s" % {"description": info['Description'].replace(r'\n', "\n")})
        self.PluginAuthor.set_markup("<b>%(author)s</b>" % {"author": ", ".join(info['Authors'])})

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

    def set_settings(self, config):

        self.p.set_widgets_data(config, self.options)
        self.on_plugins_enable(None)
        self.pluginsiters = {}
        self.plugins_model.clear()
        plugins = sorted(self.frame.np.pluginhandler.list_installed_plugins())

        for plugin in plugins:
            try:
                info = self.frame.np.pluginhandler.get_plugin_info(plugin)
            except IOError:
                continue
            enabled = (plugin in config["plugins"]["enabled"])
            self.pluginsiters[filter] = self.plugins_model.append([enabled, info['Name'], plugin])

        return {}

    def get_enabled_plugins(self):

        enabled_plugins = []

        for plugin in self.plugins_model:
            enabled = self.plugins_model.get(plugin.iter, 0)[0]

            if enabled:
                plugin_name = self.plugins_model.get(plugin.iter, 2)[0]
                enabled_plugins.append(plugin_name)

        return enabled_plugins

    def on_plugins_enable(self, widget):
        self.PluginList.set_sensitive(self.PluginsEnable.get_active())

        if self.PluginsEnable.get_active():
            # Enable all selected plugins
            for plugin in self.get_enabled_plugins():
                self.frame.np.pluginhandler.enable_plugin(plugin)

        else:
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

        # Signal sent and catch by frame.py on update
        GObject.signal_new("settings-updated", Gtk.Window, GObject.SignalFlags.RUN_LAST, GObject.TYPE_NONE, (GObject.TYPE_STRING,))

        # Connect the custom handlers
        self.SettingsWindow.set_transient_for(frame.MainWindow)
        self.SettingsWindow.connect("delete-event", self.on_delete)
        self.SettingsWindow.connect("settings-updated", self.frame.on_settings_updated)

        # This is ?
        self.empty_label = Gtk.Label.new("")
        self.empty_label.show()
        self.viewport1.add(self.empty_label)

        # Treeview of the settings
        self.tree = {}

        # Pages
        self.pages = {}
        self.handler_ids = {}

        # Model of the treeview
        model = Gtk.TreeStore(str, str)

        # Fill up the model
        self.tree["General"] = row = model.append(None, [_("General"), "General"])
        self.tree["Server"] = model.append(row, [_("Server"), "Server"])
        self.tree["Searches"] = model.append(row, [_("Searches"), "Searches"])
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

        self.tree["Interface"] = row = model.append(None, [_("Interface"), "Interface"])
        self.tree["FontsColors"] = model.append(row, [_("Fonts & Colors"), "FontsColors"])
        self.tree["Icons"] = model.append(row, [_("Icons"), "Icons"])
        self.tree["Tabs"] = model.append(row, [_("Tabs"), "Tabs"])

        self.tree["Chat"] = row = model.append(None, [_("Chat"), "Chat"])
        self.tree["NowPlaying"] = model.append(row, [_("Now Playing"), "NowPlaying"])
        self.tree["AwayMode"] = model.append(row, [_("Away Mode"), "AwayMode"])
        self.tree["IgnoreList"] = model.append(row, [_("Ignore List"), "IgnoreList"])
        self.tree["CensorList"] = model.append(row, [_("Censor List"), "CensorList"])
        self.tree["AutoReplaceList"] = model.append(row, [_("Auto-Replace List"), "AutoReplaceList"])
        self.tree["UrlCatching"] = model.append(row, [_("URL Catching"), "UrlCatching"])
        self.tree["Completion"] = model.append(row, [_("Completion"), "Completion"])
        self.tree["TextToSpeech"] = model.append(row, [_("Text-to-Speech"), "TextToSpeech"])

        # Title of the treeview
        column = Gtk.TreeViewColumn(_("Categories"), Gtk.CellRendererText(), text=0)

        # set the model on the treeview
        self.SettingsTreeview.set_model(model)
        self.SettingsTreeview.append_column(column)

        # Expand all
        self.SettingsTreeview.expand_all()

        # Connect the signal when a page/category is changed
        self.SettingsTreeview.get_selection().connect("changed", self.switch_page)

        # Set the cursor to the second element of the TreeViewColumn.
        self.SettingsTreeview.set_cursor((0, 0))

        self.update_visuals()

    def update_visuals(self):

        for widget in self.__dict__.values():
            update_widget_visuals(widget)

        for name, page in self.pages.items():
            for widget in page.__dict__.values():
                update_widget_visuals(widget)

    def switch_page(self, widget):

        child = self.viewport1.get_child()

        if child:
            self.viewport1.remove(child)

        model, iterator = widget.get_selected()

        if iterator is None:
            self.viewport1.add(self.empty_label)
            return

        page = model.get_value(iterator, 1)

        if page not in self.pages:
            try:
                self.pages[page] = getattr(sys.modules[__name__], page + "Frame")(self)
            except AttributeError:
                return

            self.pages[page].set_settings(self.frame.np.config.sections)

        self.viewport1.add(self.pages[page].Main)

    def set_active_page(self, page):

        # Unminimize window
        self.SettingsWindow.deiconify()

        model = self.SettingsTreeview.get_model()
        sel = self.SettingsTreeview.get_selection()
        sel.unselect_all()
        path = model.get_path(self.tree[page])

        self.SettingsTreeview.expand_to_path(path)

        if path is not None:
            sel.select_path(path)

        self.switch_page(sel)

    def get_position(self, combobox, option):

        iterator = combobox.get_model().get_iter_first()

        while iterator is not None:
            word = combobox.get_model().get_value(iterator, 0)

            if word.lower() == option or word == option:
                combobox.set_active_iter(iterator)
                break

            iterator = combobox.get_model().iter_next(iterator)

    def set_widgets_data(self, config, options):

        for section, keys in options.items():
            if section not in config:
                continue

            for key in keys:
                widget = options[section][key]

                if widget is None:
                    continue

                if config[section][key] is None:
                    self.clear_widget(widget)
                else:
                    self.set_widget(widget, config[section][key])

    def get_widget_data(self, widget):

        if isinstance(widget, Gtk.SpinButton):
            return int(widget.get_value())

        elif isinstance(widget, Gtk.Entry):
            return widget.get_text()

        elif isinstance(widget, Gtk.TextView):
            buffer = widget.get_buffer()
            start, end = buffer.get_bounds()

            return widget.get_buffer().get_text(start, end, True)

        elif isinstance(widget, Gtk.CheckButton):
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
            self.get_position(widget, "")

        elif isinstance(widget, Gtk.FontButton):
            widget.set_font("")

    def set_widget(self, widget, value):

        if isinstance(widget, Gtk.SpinButton):
            widget.set_value(int(value))

        elif isinstance(widget, Gtk.Entry):
            if isinstance(value, (str, int)):
                widget.set_text(value)

        elif isinstance(widget, Gtk.TextView):
            if isinstance(value, (str, int)):
                widget.get_buffer().set_text(value)

        elif isinstance(widget, Gtk.CheckButton):
            widget.set_active(value)

        elif isinstance(widget, Gtk.ComboBox):
            if isinstance(value, str):
                self.get_position(widget, value)

            elif isinstance(value, int):
                widget.set_active(value)

        elif isinstance(widget, Gtk.FontButton):
            widget.set_font(value)

        elif isinstance(widget, Gtk.TreeView) and isinstance(value, list) and widget.get_model().get_n_columns() == 1:
            for item in value:
                try:
                    widget.get_model().append([item])
                except TypeError:
                    # Invalid input
                    continue

        elif isinstance(widget, FileChooserButton):
            widget.set_path(value)

    def set_settings(self, config):

        for page in self.pages.values():
            page.set_settings(config)

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
            need_portmap = self.pages["Server"].needportmap

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
            need_colors = self.pages["FontsColors"].needcolors

        except KeyError:
            need_colors = False

        try:
            need_completion = self.pages["Completion"].needcompletion

        except KeyError:
            need_completion = False

        return need_portmap, need_rescan, need_colors, need_completion, config

    def on_backup_config(self, *args):

        response = save_file(
            self.SettingsWindow.get_toplevel(),
            os.path.dirname(self.frame.np.config.filename),
            "config backup %s.tar.bz2" % (time.strftime("%Y-%m-%d %H_%M_%S")),
            title=_("Pick a File Name for Config Backup")
        )

        if not response:
            return

        error, message = self.frame.np.config.write_config_backup(response[0])

        if error:
            log.add(_("Error backing up config: %s"), message)
        else:
            log.add(_("Config backed up to: %s"), message)

    def on_apply(self, widget):
        self.SettingsWindow.emit("settings-updated", "apply")

    def on_ok(self, widget):
        self.SettingsWindow.hide()
        self.SettingsWindow.emit("settings-updated", "ok")

    def on_cancel(self, widget):
        self.SettingsWindow.hide()

    def on_delete(self, widget, event):
        self.on_cancel(widget)
        widget.stop_emission_by_name("delete-event")
        return True
