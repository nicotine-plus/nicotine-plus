# COPYRIGHT (C) 2020 Nicotine+ Team
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

from gettext import gettext as _

from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import GdkPixbuf
from gi.repository import GObject
from gi.repository import Gtk

import _thread
from pynicotine import slskmessages
from pynicotine.gtkgui.dialogs import choose_dir
from pynicotine.gtkgui.dialogs import combo_box_dialog
from pynicotine.gtkgui.dialogs import entry_dialog
from pynicotine.gtkgui.dialogs import save_file
from pynicotine.gtkgui.utils import human_size
from pynicotine.gtkgui.utils import initialise_columns
from pynicotine.gtkgui.utils import load_ui_elements
from pynicotine.gtkgui.utils import open_uri
from pynicotine.gtkgui.utils import set_widget_fg_bg_css
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
                "ctcpmsgs": self.ctcptogglebutton
            }
        }

    def set_settings(self, config):

        self.p.set_widgets_data(config, self.options)

        server = config["server"]

        if server["server"] is not None:
            self.Server.set_text("%s:%i" % (server["server"][0], server["server"][1]))
        else:
            self.Server.set_text("server.slsknet.org:2242")

        if self.frame.np.waitport is None:
            self.CurrentPort.set_markup(_("Client port is not set"))
        else:
            self.CurrentPort.set_markup(_("Client port is <b>%(port)s</b>") % {"port": self.frame.np.waitport})

        if self.frame.np.ipaddress is None:
            self.YourIP.set_markup(_("Your IP address has not been retrieved from the server"))
        else:
            self.YourIP.set_markup(_("Your IP address is <b>%(ip)s</b>") % {"ip": self.frame.np.ipaddress})

        if server["login"] is not None:
            self.Login.set_text(server["login"])

        if server["passw"] is not None:
            self.Password.set_text(server["passw"])

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
            server = None

        if str(self.Login.get_text()) == "None":
            dlg = Gtk.MessageDialog(
                transient_for=self.p.SettingsWindow,
                flags=0,
                type=Gtk.MessageType.WARNING,
                buttons=Gtk.ButtonsType.OK,
                text=_("Warning: Bad Username")
            )
            dlg.format_secondary_text(_("Username 'None' is not a good one, please pick another."))
            dlg.run()
            dlg.destroy()
            raise UserWarning

        try:
            firstport = min(self.FirstPort.get_value_as_int(), self.LastPort.get_value_as_int())
            lastport = max(self.FirstPort.get_value_as_int(), self.LastPort.get_value_as_int())
            portrange = (firstport, lastport)
        except Exception:
            portrange = None
            dlg = Gtk.MessageDialog(
                transient_for=self.p.SettingsWindow,
                flags=0,
                type=Gtk.MessageType.WARNING,
                buttons=Gtk.ButtonsType.OK,
                text=_("Warning: Invalid ports")
            )
            dlg.format_secondary_text(_("Client ports are invalid."))
            dlg.run()
            dlg.destroy()
            raise UserWarning

        return {
            "server": {
                "server": server,
                "login": self.Login.get_text(),
                "passw": self.Password.get_text(),
                "portrange": portrange,
                "upnp": self.UseUPnP.get_active(),
                "upnp_interval": self.UPnPInterval.get_value_as_int(),
                "ctcpmsgs": not self.ctcptogglebutton.get_active(),
            }
        }

    def get_need_portmap(self):
        return self.needportmap

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

        self.options = {
            "transfers": {
                "lock": self.LockIncoming,
                "reverseorder": self.DownloadReverseOrder,
                "prioritize": self.DownloadChecksumsFirst,
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

        self.uploads_allowed__list = Gtk.ListStore(GObject.TYPE_STRING)
        self.UploadsAllowed.set_model(self.uploads_allowed__list)

        self.uploads_allowed__list.clear()
        self.alloweduserslist = [
            _("No one"),
            _("Everyone"),
            _("Users in list"),
            _("Trusted Users")
        ]

        for item in self.alloweduserslist:
            self.uploads_allowed__list.append([item])

        self.filterlist = Gtk.ListStore(
            GObject.TYPE_STRING,
            GObject.TYPE_BOOLEAN
        )
        self.downloadfilters = []

        cols = initialise_columns(
            self.FilterView,
            [_("Filter"), 250, "text"],
            [_("Escaped"), 40, "toggle"]
        )

        cols[0].set_sort_column_id(0)
        cols[1].set_sort_column_id(1)
        renderers = cols[1].get_cells()

        for render in renderers:
            render.connect('toggled', self.cell_toggle_callback, self.filterlist, 1)

        self.FilterView.set_model(self.filterlist)
        self.FilterView.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)

    def set_settings(self, config):

        transfers = config["transfers"]

        self.p.set_widgets_data(config, self.options)

        if transfers["uploadallowed"] is not None:
            self.UploadsAllowed.set_active(transfers["uploadallowed"])

        self.UploadsAllowed.set_sensitive(self.RemoteDownloads.get_active())

        if transfers["incompletedir"]:
            self.IncompleteDir.set_current_folder(transfers["incompletedir"])

        if transfers["downloaddir"]:
            self.DownloadDir.set_current_folder(transfers["downloaddir"])

        if transfers["uploaddir"]:
            self.UploadDir.set_current_folder(transfers["uploaddir"])

        self.filtersiters = {}
        self.filterlist.clear()

        if transfers["downloadfilters"] != []:
            for dfilter in transfers["downloadfilters"]:
                dfilter, escaped = dfilter
                self.filtersiters[dfilter] = self.filterlist.append([dfilter, escaped])

        self.on_enable_filters_toggle(self.DownloadFilter)

        self.needrescan = False

    def get_settings(self):

        place = _("home")
        homedir = os.path.expanduser('~')

        if homedir == self.DownloadDir.get_file().get_path() and self.ShareDownloadDir.get_active():

            dlg = Gtk.MessageDialog(
                transient_for=self.p.SettingsWindow,
                flags=0,
                type=Gtk.MessageType.WARNING,
                buttons=Gtk.ButtonsType.OK,
                text=_("Warning")
            )
            dlg.format_secondary_text(_("Security Risk: you should not share your %s directory!") % place)
            dlg.run()
            dlg.destroy()

            raise UserWarning

        try:
            uploadallowed = self.UploadsAllowed.get_active()
        except Exception:
            uploadallowed = 0

        if not self.RemoteDownloads.get_active():
            uploadallowed = 0

        return {
            "transfers": {
                "lock": self.LockIncoming.get_active(),
                "reverseorder": self.DownloadReverseOrder.get_active(),
                "prioritize": self.DownloadChecksumsFirst.get_active(),
                "remotedownloads": self.RemoteDownloads.get_active(),
                "uploadallowed": uploadallowed,
                "incompletedir": self.IncompleteDir.get_file().get_path(),
                "downloaddir": self.DownloadDir.get_file().get_path(),
                "sharedownloaddir": self.ShareDownloadDir.get_active(),
                "uploaddir": self.UploadDir.get_file().get_path(),
                "downloadfilters": self.get_filter_list(),
                "enablefilters": self.DownloadFilter.get_active(),
                "downloadlimit": self.DownloadSpeed.get_value_as_int()
            }
        }

    def get_need_rescan(self):
        return self.needrescan

    def on_choose_download_dir(self, widget):
        """
        Function called when the download directory is modified.
        """

        # Get a gio.File object from Gtk.FileChooser
        # Convert the gio.File to a string
        dir_disp = self.DownloadDir.get_file().get_path()

        if dir_disp is not None:

            # Get the transfers section
            transfers = self.frame.np.config.sections["transfers"]

            # This function will be called upon creating the settings window,
            # so only force a scan if the user changes his donwload directory
            if self.ShareDownloadDir.get_active():
                if dir_disp != transfers["downloaddir"]:
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
            parent=self.p.SettingsWindow,
            title=_('Add a download filter'),
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
                parent=self.p.SettingsWindow,
                title=_('Edit a download filter'),
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

        default_filters = [
            ["desktop.ini", 1],
            ["folder.jpg", 1],
            ["*.url", 1],
            ["thumbs.db", 1],
            ["albumart(_{........-....-....-....-............}_)?(_?(large|small))?\\.jpg", 0]
        ]

        for dfilter in default_filters:
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

            self.VerifiedLabel.set_markup("<span color=\"red\" weight=\"bold\">%s</span>" % error)
        else:
            self.VerifiedLabel.set_markup("<b>Filters Successful</b>")

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

        # last column is the raw byte/unicode object for the folder (not shown)
        self.shareslist = Gtk.ListStore(
            GObject.TYPE_STRING, GObject.TYPE_STRING,
            GObject.TYPE_STRING, GObject.TYPE_STRING
        )

        self.shareddirs = []

        # last column is the raw byte/unicode object for the folder (not shown)
        self.bshareslist = Gtk.ListStore(
            GObject.TYPE_STRING, GObject.TYPE_STRING,
            GObject.TYPE_STRING, GObject.TYPE_STRING
        )

        self.bshareddirs = []

        initialise_columns(
            self.Shares,
            [_("Virtual Directory"), 0, "text"],
            [_("Directory"), 0, "text"],
            [_("Size"), 0, "text"]
        )

        self.Shares.set_model(self.shareslist)
        self.Shares.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)

        initialise_columns(
            self.BuddyShares,
            [_("Virtual Directory"), 0, "text"],
            [_("Directory"), 0, "text"],
            [_("Size"), 0, "text"]
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

            for (virtual, actual) in transfers["shared"]:

                self.shareslist.append(
                    [
                        virtual,
                        actual,
                        "",
                        actual
                    ]
                )

                # Compute the directory size in the background
                _thread.start_new_thread(self.get_directory_size, (actual, self.shareslist))

            self.shareddirs = transfers["shared"][:]

        if transfers["buddyshared"] is not None:

            for (virtual, actual) in transfers["buddyshared"]:
                self.bshareslist.append(
                    [
                        virtual,
                        actual,
                        "",
                        actual
                    ]
                )

                # Compute the directory size in the background
                _thread.start_new_thread(self.get_directory_size, (actual, self.shareslist))

            self.bshareddirs = transfers["buddyshared"][:]

        self.needrescan = False

    def get_settings(self):

        place = _("home")
        homedir = os.path.expanduser('~')

        for share in self.shareddirs + self.bshareddirs:
            if homedir == share:
                dlg = Gtk.MessageDialog(
                    transient_for=self.p.SettingsWindow,
                    flags=0,
                    type=Gtk.MessageType.WARNING,
                    buttons=Gtk.ButtonsType.OK,
                    text=_("Warning")
                )
                dlg.format_secondary_text(_("Security Risk: you should not share your %s directory!") % place)
                dlg.run()
                dlg.destroy()
                raise UserWarning

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

        # Public shares are deactivated if we only share with friends
        self.Shares.set_sensitive(not (friendsonly and buddies))
        self.addSharesButton.set_sensitive(not (friendsonly and buddies))
        self.removeSharesButton.set_sensitive(not (friendsonly and buddies))
        self.renameVirtualsButton.set_sensitive(not (friendsonly and buddies))

        # Buddy shares are activated only if needed
        self.BuddyShares.set_sensitive(buddies)
        self.addBuddySharesButton.set_sensitive(buddies)
        self.removeBuddySharesButton.set_sensitive(buddies)
        self.renameBuddyVirtualsButton.set_sensitive(buddies)

    def get_need_rescan(self):
        return self.needrescan

    def on_add_shared_dir(self, widget):

        dir1 = choose_dir(
            self.Main.get_toplevel(),
            title=_("Add a shared directory")
        )

        if dir1 is not None:

            for directory in dir1:

                # If the directory is already shared
                if directory in (x[1] for x in self.shareddirs + self.bshareddirs):

                    dlg = Gtk.MessageDialog(
                        transient_for=self.p.SettingsWindow,
                        flags=0,
                        type=Gtk.MessageType.WARNING,
                        buttons=Gtk.ButtonsType.OK,
                        text=_("Warning")
                    )
                    dlg.format_secondary_text(_("The chosen directory is already shared"))
                    dlg.run()
                    dlg.destroy()

                else:

                    virtual = combo_box_dialog(
                        parent=self.p.SettingsWindow,
                        title=_("Virtual name"),
                        message=_("Enter virtual name for '%(dir)s':") % {'dir': directory}
                    )

                    # Remove slashes from share name to avoid path conflicts
                    virtual = virtual.replace('/', '_').replace('\\', '_')

                    # If the virtual share name is not already used
                    if not virtual or virtual in (x[0] for x in self.shareddirs + self.bshareddirs):

                        dlg = Gtk.MessageDialog(
                            transient_for=self.p.SettingsWindow,
                            flags=0,
                            type=Gtk.MessageType.WARNING,
                            buttons=Gtk.ButtonsType.OK,
                            text=_("Warning")
                        )
                        dlg.format_secondary_text(_("The chosen virtual name is either empty or already exists"))
                        dlg.run()
                        dlg.destroy()

                    else:

                        self.shareslist.append(
                            [
                                virtual,
                                directory,
                                "",
                                directory
                            ]
                        )

                        self.shareddirs.append((virtual, directory))
                        self.needrescan = True

                        # Compute the directory size in the background
                        _thread.start_new_thread(self.get_directory_size, (directory, self.shareslist))

    def on_add_shared_buddy_dir(self, widget):

        dir1 = choose_dir(
            self.Main.get_toplevel(),
            title=_("Add a shared buddy directory")
        )

        if dir1 is not None:

            for directory in dir1:

                # If the directory is already shared
                if directory in (x[1] for x in self.shareddirs + self.bshareddirs):

                    dlg = Gtk.MessageDialog(
                        transient_for=self.p.SettingsWindow,
                        flags=0,
                        type=Gtk.MessageType.WARNING,
                        buttons=Gtk.ButtonsType.OK,
                        text=_("Warning")
                    )
                    dlg.format_secondary_text(_("The chosen directory is already shared"))
                    dlg.run()
                    dlg.destroy()

                else:

                    virtual = combo_box_dialog(
                        parent=self.p.SettingsWindow,
                        title=_("Virtual name"),
                        message=_("Enter virtual name for '%(dir)s':") % {'dir': directory}
                    )

                    # Remove slashes from share name to avoid path conflicts
                    virtual = virtual.replace('/', '_').replace('\\', '_')

                    # If the virtual share name is not already used
                    if not virtual or virtual in (x[0] for x in self.shareddirs + self.bshareddirs):

                        dlg = Gtk.MessageDialog(
                            transient_for=self.p.SettingsWindow,
                            flags=0,
                            type=Gtk.MessageType.WARNING,
                            buttons=Gtk.ButtonsType.OK,
                            text=_("Warning")
                        )
                        dlg.format_secondary_text(_("The chosen virtual name is either empty or already exists"))
                        dlg.run()
                        dlg.destroy()

                    else:

                        self.bshareslist.append(
                            [
                                virtual,
                                directory,
                                "",
                                directory
                            ]
                        )

                        self.bshareddirs.append((virtual, directory))
                        self.needrescan = True

                        # Compute the directory size in the background
                        _thread.start_new_thread(self.get_directory_size, (directory, self.bshareslist))

    def _remove_shared_dir(self, model, path, iterator, list):
        list.append(iterator)

    def on_rename_virtuals(self, widget):

        iters = []
        self.Shares.get_selection().selected_foreach(self._remove_shared_dir, iters)

        for iterator in iters:
            oldvirtual = self.shareslist.get_value(iterator, 0)
            directory = self.shareslist.get_value(iterator, 3)
            oldmapping = (oldvirtual, directory)

            virtual = combo_box_dialog(
                parent=self.p.SettingsWindow,
                title=_("Virtual name"),
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
            directory = self.bshareslist.get_value(iterator, 3)
            oldmapping = (oldvirtual, directory)

            virtual = combo_box_dialog(
                parent=self.p.SettingsWindow,
                title=_("Virtual name"),
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
            actual = self.shareslist.get_value(iterator, 3)
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
            actual = self.bshareslist.get_value(iterator, 3)
            mapping = (virtual, actual)
            self.bshareddirs.remove(mapping)
            self.bshareslist.remove(iterator)

        if iters:
            self.needrescan = True

    def get_directory_size(self, directory, liststore):

        total_size = 0

        for dirpath, dirnames, filenames in os.walk(directory):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                try:
                    total_size += os.path.getsize(fp)
                except FileNotFoundError:
                    pass

        GLib.idle_add(
            self._updatedirstats,
            directory,
            human_size(total_size),
            liststore
        )

    def _updatedirstats(self, directory, human_size, liststore):

        iterator = liststore.get_iter_first()

        while iterator is not None:

            if directory == liststore.get_value(iterator, 3):

                liststore.set(iterator, 2, human_size)

                return

            iterator = liststore.iter_next(iterator)


class UploadsFrame(BuildFrame):

    def __init__(self, parent):

        self.p = parent

        BuildFrame.__init__(self, "uploads")

        self.options = {
            "transfers": {
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


class UserinfoFrame(BuildFrame):

    def __init__(self, parent):

        self.p = parent

        BuildFrame.__init__(self, "userinfo")

        self.options = {
            "userinfo": {
                "descr": None,
                "pic": self.ImageChooser
            }
        }

        def update_image_preview(chooser):
            path = chooser.get_preview_filename()

            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(path)

                maxwidth, maxheight = 300.0, 700.0
                width, height = pixbuf.get_width(), pixbuf.get_height()
                scale = min(maxwidth / width, maxheight / height)

                if scale < 1:
                    width, height = int(width * scale), int(height * scale)
                    pixbuf = pixbuf.scale_simple(width, height, GdkPixbuf.InterpType.BILINEAR)

                preview.set_from_pixbuf(pixbuf)
                chooser.set_preview_widget_active(True)
            except Exception:
                chooser.set_preview_widget_active(False)

        preview = Gtk.Image()
        self.ImageChooser.set_preview_widget(preview)
        self.ImageChooser.connect('update-preview', update_image_preview)

    def set_settings(self, config):

        self.p.set_widgets_data(config, self.options)

        userinfo = config["userinfo"]

        if userinfo["descr"] is not None:
            descr = unescape(userinfo["descr"])
            self.Description.get_buffer().set_text(descr)

        if userinfo["pic"]:
            self.ImageChooser.set_filename(userinfo["pic"])

    def get_settings(self):

        buffer = self.Description.get_buffer()

        start = buffer.get_start_iter()
        end = buffer.get_end_iter()

        descr = buffer.get_text(start, end, True).replace("; ", ", ").__repr__()

        if self.ImageChooser.get_filename() is not None:
            pic = self.ImageChooser.get_filename()
        else:
            pic = ""

        return {
            "userinfo": {
                "descr": descr,
                "pic": pic
            }
        }

    def on_default_image(self, widget):
        self.ImageChooser.unselect_all()


class IgnoreFrame(BuildFrame):

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
            self.IgnoredIPs,
            [_("Addresses"), -1, "text"],
            [_("Users"), -1, "text"]
        )
        cols[0].set_sort_column_id(0)
        cols[1].set_sort_column_id(1)

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
            _("Ignore user..."),
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


class BanFrame(BuildFrame):

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
            self.BlockedList,
            [_("Addresses"), -1, "text"],
            [_("Users"), -1, "text"]
        )
        cols[0].set_sort_column_id(0)
        cols[1].set_sort_column_id(1)

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
            _("Ban user..."),
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


class TTSFrame(BuildFrame):

    def __init__(self, parent):

        self.p = parent

        BuildFrame.__init__(self, "tts")

        # Combobox for text-to-speech readers
        self.tts_command_store = Gtk.ListStore(GObject.TYPE_STRING)
        for executable in ["echo $ | festival --tts", "flite -t $"]:
            self.tts_command_store.append([executable])

        self.TTSCommand.set_model(self.tts_command_store)
        self.TTSCommand.set_entry_text_column(0)

        self.options = {
            "ui": {
                "speechenabled": self.TextToSpeech,
                "speechcommand": self.TTSCommand,
                "speechrooms": self.RoomMessage,
                "speechprivate": self.PrivateMessage
            }
        }

    def on_default_private(self, widget):
        self.PrivateMessage.set_text("%(user)s told you.. %(message)s")

    def on_default_rooms(self, widget):
        self.RoomMessage.set_text("In %(room)s, %(user)s said %(message)s")

    def on_default_tts(self, widget):
        self.TTSCommand.get_child().set_text("flite -t \"%s\"")

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

        ui = config["ui"]

        self.p.set_widgets_data(config, self.options)

        if ui["icontheme"]:
            self.ThemeDir.set_current_folder(ui["icontheme"])

        if sys.platform == "darwin":
            # Tray icons don't work as expected on macOS
            self.hide_tray_icon_settings()
            return

        sensitive = self.TrayiconCheck.get_active()
        self.StartupHidden.set_sensitive(sensitive)

        if ui["exitdialog"] is not None:

            exitdialog = int(ui["exitdialog"])

            if exitdialog == 1:
                self.DialogOnClose.set_active(True)
            elif exitdialog == 2:
                self.SendToTrayOnClose.set_active(True)
            elif exitdialog == 0:
                self.QuitOnClose.set_active(True)

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

        """ Since the file chooser doesn't allow us to unselect a folder,
        we use this hack to identify a cleared state, and actually clear the theme path
        in the config later. """

        self.ThemeDir.unselect_all()
        self.ThemeDir.set_current_folder("   __invalid__   ")

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

        file_obj = self.ThemeDir.get_file()

        if file_obj is not None and not file_obj.get_path().endswith("   __invalid__   "):
            icontheme = file_obj.get_path()
        else:
            icontheme = ""

        return {
            "ui": {
                "icontheme": icontheme,
                "trayicon": self.TrayiconCheck.get_active(),
                "startup_hidden": self.StartupHidden.get_active(),
                "exitdialog": mainwindow_close
            }
        }


class ColoursFrame(BuildFrame):

    def __init__(self, parent):

        self.p = parent

        BuildFrame.__init__(self, "colours")

        # Combobox for user names style
        self.username_style_store = Gtk.ListStore(GObject.TYPE_STRING)
        for item in ("bold", "italic", "underline", "normal"):
            self.username_style_store.append([item])

        self.UsernameStyle.set_model(self.username_style_store)

        cell = Gtk.CellRendererText()
        self.UsernameStyle.pack_start(cell, True)
        self.UsernameStyle.add_attribute(cell, 'text', 0)

        self.needcolors = 0
        self.options = {
            "ui": {
                "chatlocal": self.Local,
                "chatremote": self.Remote,
                "chatme": self.Me,
                "chathilite": self.Highlight,
                "textbg": self.BackgroundColor,
                "inputcolor": self.InputColor,
                "search": self.Immediate,
                "searchq": self.Queue,
                "useraway": self.AwayColor,
                "useronline": self.OnlineColor,
                "useroffline": self.OfflineColor,
                "usernamehotspots": self.UsernameHotspots,
                "usernamestyle": self.UsernameStyle,
                "showaway": self.DisplayAwayColours,
                "urlcolor": self.URL,
                "tab_default": self.DefaultTab,
                "tab_hilite": self.HighlightTab,
                "tab_changed": self.ChangedTab,
                "dark_mode": self.DarkMode
            }
        }

        self.colorsd = {
            "ui": {
                "chatlocal": self.Drawing_Local,
                "chatremote": self.Drawing_Remote,
                "chatme": self.Drawing_Me,
                "chathilite": self.Drawing_Highlight,
                "textbg": self.Drawing_BackgroundColor,
                "inputcolor": self.Drawing_InputColor,
                "search": self.Drawing_Immediate,
                "searchq": self.Drawing_Queue,
                "useraway": self.Drawing_AwayColor,
                "useronline": self.Drawing_OnlineColor,
                "useroffline": self.Drawing_OfflineColor,
                "showaway": self.DisplayAwayColours,
                "urlcolor": self.Drawing_URL,
                "tab_default": self.Drawing_DefaultTab,
                "tab_hilite": self.Drawing_HighlightTab,
                "tab_changed": self.Drawing_ChangedTab
            }
        }

        self.colors = [
            "chatlocal",
            "chatremote",
            "urlcolor",
            "chatme",
            "chathilite",
            "textbg",
            "inputcolor",
            "search",
            "searchq",
            "useraway",
            "useronline",
            "useroffline",
            "tab_default",
            "tab_changed",
            "tab_hilite"
        ]

        self.PickRemote.connect("clicked", self.pick_colour, self.Remote, self.Drawing_Remote)
        self.PickLocal.connect("clicked", self.pick_colour, self.Local, self.Drawing_Local)
        self.PickMe.connect("clicked", self.pick_colour, self.Me, self.Drawing_Me)
        self.PickHighlight.connect("clicked", self.pick_colour, self.Highlight, self.Drawing_Highlight)
        self.PickImmediate.connect("clicked", self.pick_colour, self.Immediate, self.Drawing_Immediate)
        self.PickQueue.connect("clicked", self.pick_colour, self.Queue, self.Drawing_Queue)

        self.PickAway.connect("clicked", self.pick_colour, self.AwayColor, self.Drawing_AwayColor)
        self.PickOnline.connect("clicked", self.pick_colour, self.OnlineColor, self.Drawing_OnlineColor)
        self.PickOffline.connect("clicked", self.pick_colour, self.OfflineColor, self.Drawing_OfflineColor)
        self.PickURL.connect("clicked", self.pick_colour, self.URL, self.Drawing_URL)
        self.DefaultURL.connect("clicked", self.default_colour, self.URL)

        self.DefaultAway.connect("clicked", self.default_colour, self.AwayColor)
        self.DefaultOnline.connect("clicked", self.default_colour, self.OnlineColor)
        self.DefaultOffline.connect("clicked", self.default_colour, self.OfflineColor)

        self.PickBackground.connect("clicked", self.pick_colour, self.BackgroundColor, self.Drawing_BackgroundColor)
        self.DefaultBackground.connect("clicked", self.default_colour, self.BackgroundColor)

        self.PickInput.connect("clicked", self.pick_colour, self.InputColor, self.Drawing_InputColor)
        self.DefaultInput.connect("clicked", self.default_colour, self.InputColor)

        self.DefaultRemote.connect("clicked", self.default_colour, self.Remote)
        self.DefaultLocal.connect("clicked", self.default_colour, self.Local)
        self.DefaultMe.connect("clicked", self.default_colour, self.Me)
        self.DefaultHighlight.connect("clicked", self.default_colour, self.Highlight)
        self.DefaultImmediate.connect("clicked", self.default_colour, self.Immediate)
        self.DefaultQueue.connect("clicked", self.default_colour, self.Queue)

        self.DefaultColours.connect("clicked", self.on_default_colours)
        self.ClearAllColours.connect("clicked", self.on_clear_all_colours)
        self.DisplayAwayColours.connect("toggled", self.toggled_away_colours)

        self.PickHighlightTab.connect("clicked", self.pick_colour, self.HighlightTab, self.Drawing_HighlightTab)
        self.PickDefaultTab.connect("clicked", self.pick_colour, self.DefaultTab, self.Drawing_DefaultTab)
        self.PickChangedTab.connect("clicked", self.pick_colour, self.ChangedTab, self.Drawing_ChangedTab)

        self.DefaultHighlightTab.connect("clicked", self.default_colour, self.HighlightTab)
        self.DefaultChangedTab.connect("clicked", self.default_colour, self.ChangedTab)
        self.ClearDefaultTab.connect("clicked", self.default_colour, self.DefaultTab)

        # To set needcolors flag
        self.Local.connect("changed", self.fonts_colors_changed)
        self.Remote.connect("changed", self.fonts_colors_changed)
        self.Me.connect("changed", self.fonts_colors_changed)
        self.Highlight.connect("changed", self.fonts_colors_changed)
        self.BackgroundColor.connect("changed", self.fonts_colors_changed)
        self.Immediate.connect("changed", self.fonts_colors_changed)
        self.Queue.connect("changed", self.fonts_colors_changed)
        self.AwayColor.connect("changed", self.fonts_colors_changed)
        self.OnlineColor.connect("changed", self.fonts_colors_changed)
        self.OfflineColor.connect("changed", self.fonts_colors_changed)
        self.UsernameStyle.connect("changed", self.fonts_colors_changed)
        self.InputColor.connect("changed", self.fonts_colors_changed)

    def set_settings(self, config):

        self.settingup = 1

        self.p.set_widgets_data(config, self.options)

        for option in self.colors:
            for key, value in self.colorsd.items():

                if option in value:

                    drawingarea = self.colorsd[key][option]
                    set_widget_fg_bg_css(drawingarea, config[key][option])
                    break

        self.toggled_away_colours(self.DisplayAwayColours)
        self.settingup = 0
        self.needcolors = 0

    def get_settings(self):

        return {
            "ui": {
                "chatlocal": self.Local.get_text(),
                "chatremote": self.Remote.get_text(),
                "chatme": self.Me.get_text(),
                "chathilite": self.Highlight.get_text(),
                "urlcolor": self.URL.get_text(),
                "textbg": self.BackgroundColor.get_text(),
                "inputcolor": self.InputColor.get_text(),
                "search": self.Immediate.get_text(),
                "searchq": self.Queue.get_text(),
                "showaway": self.DisplayAwayColours.get_active(),
                "useraway": self.AwayColor.get_text(),
                "useronline": self.OnlineColor.get_text(),
                "useroffline": self.OfflineColor.get_text(),
                "usernamehotspots": self.UsernameHotspots.get_active(),
                "usernamestyle": self.UsernameStyle.get_model().get(self.UsernameStyle.get_active_iter(), 0)[0],
                "tab_hilite": self.HighlightTab.get_text(),
                "tab_default": self.DefaultTab.get_text(),
                "tab_changed": self.ChangedTab.get_text(),
                "dark_mode": self.DarkMode.get_active()
            }
        }

    def toggled_away_colours(self, widget):

        sensitive = widget.get_active()

        self.AwayColor.set_sensitive(sensitive)
        self.PickAway.set_sensitive(sensitive)
        self.DefaultAway.set_sensitive(sensitive)

    def on_default_colours(self, widget):
        for option in self.colors:
            self.set_default_color(option)

    def set_default_color(self, option):

        defaults = self.frame.np.config.defaults

        for key, value in self.options.items():
            if option in value:
                widget = self.options[key][option]

                if isinstance(widget, Gtk.SpinButton):
                    widget.set_value_as_int(defaults[key][option])

                elif isinstance(widget, Gtk.Entry):
                    widget.set_text(defaults[key][option])

                elif isinstance(widget, Gtk.CheckButton):
                    widget.set_active(defaults[key][option])

                elif isinstance(widget, Gtk.ComboBox):
                    widget.get_child().set_text(defaults[key][option])

        for key, value in self.colorsd.items():

            if option in value:

                drawingarea = self.colorsd[key][option]
                set_widget_fg_bg_css(drawingarea, defaults[key][option])
                break

    def on_clear_all_colours(self, button):

        for option in self.colors:
            for section, value in self.options.items():
                if option in value:
                    widget = self.options[section][option]

                    if isinstance(widget, Gtk.SpinButton):
                        widget.set_value_as_int(0)

                    elif isinstance(widget, Gtk.Entry):
                        widget.set_text("")

                    elif isinstance(widget, Gtk.CheckButton):
                        widget.set_active(0)

                    elif isinstance(widget, Gtk.ComboBox):
                        widget.get_child().set_text("")

            for section, value in self.colorsd.items():
                if option in value:
                    drawingarea = self.colorsd[section][option]
                    set_widget_fg_bg_css(drawingarea)

    def fonts_colors_changed(self, widget):
        self.needcolors = 1

    def on_username_hotspots_toggled(self, widget):

        sensitive = widget.get_active()

        self.AwayColor.set_sensitive(sensitive and self.DisplayAwayColours.get_active())
        self.OnlineColor.set_sensitive(sensitive)
        self.OfflineColor.set_sensitive(sensitive)

        self.DefaultAway.set_sensitive(sensitive)
        self.DefaultOnline.set_sensitive(sensitive)
        self.DefaultOffline.set_sensitive(sensitive)

        self.PickAway.set_sensitive(sensitive)
        self.PickOnline.set_sensitive(sensitive)
        self.PickOffline.set_sensitive(sensitive)

    def pick_colour(self, widget, entry, area):

        dlg = Gtk.ColorChooserDialog(_("Pick a color, any color"))
        color = entry.get_text()

        if color:
            try:
                rgba = Gdk.RGBA()
                rgba.parse(color)
            except Exception:
                dlg.destroy()
                return
            else:
                dlg.set_rgba(rgba)

        if dlg.run() == Gtk.ResponseType.OK:

            rgba = dlg.get_rgba()
            color = "#%02X%02X%02X" % (round(rgba.red * 255), round(rgba.green * 255), round(rgba.blue * 255))
            entry.set_text(color)

            for section in self.options.keys():

                if section not in self.colorsd:
                    continue

                for key, value in self.options[section].items():

                    if key not in self.colorsd[section]:
                        continue

                    if entry is value:
                        drawingarea = self.colorsd[section][key]
                        set_widget_fg_bg_css(drawingarea, bg_color=color)
                        break

        dlg.destroy()

    def default_colour(self, widget, entry):

        for section in self.options:
            for key, value in self.options[section].items():
                if value is entry:
                    self.set_default_color(key)
                    return

        entry.set_text("")


class NotebookFrame(BuildFrame):

    def __init__(self, parent):

        self.p = parent

        BuildFrame.__init__(self, "notebook")

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


class FontsFrame(BuildFrame):

    def __init__(self, parent):

        self.p = parent

        BuildFrame.__init__(self, "fonts")

        # Combobox for the decimal separator
        self.decimal_sep_store = Gtk.ListStore(GObject.TYPE_STRING)
        self.DecimalSep.set_model(self.decimal_sep_store)

        cell2 = Gtk.CellRendererText()
        self.DecimalSep.pack_start(cell2, True)
        self.DecimalSep.add_attribute(cell2, 'text', 0)

        for item in ["<None>", ",", ".", "<space>"]:
            self.decimal_sep_store.append([item])

        self.options = {
            "ui": {
                "chatfont": self.SelectChatFont,
                "listfont": self.SelectListFont,
                "searchfont": self.SelectSearchFont,
                "transfersfont": self.SelectTransfersFont,
                "browserfont": self.SelectBrowserFont,
                "decimalsep": self.DecimalSep
            }
        }

        self.DefaultFont.connect("clicked", self.on_default_font)
        self.SelectChatFont.connect("font-set", self.fonts_colors_changed)

        self.DefaultListFont.connect("clicked", self.on_default_list_font)
        self.SelectListFont.connect("font-set", self.fonts_colors_changed)

        self.DefaultSearchFont.connect("clicked", self.on_default_search_font)
        self.SelectSearchFont.connect("font-set", self.fonts_colors_changed)

        self.DefaultTransfersFont.connect("clicked", self.on_default_transfers_font)
        self.SelectTransfersFont.connect("font-set", self.fonts_colors_changed)

        self.DefaultBrowserFont.connect("clicked", self.on_default_browser_font)
        self.SelectBrowserFont.connect("font-set", self.fonts_colors_changed)

        self.needcolors = 0

    def set_settings(self, config):

        self.needcolors = 0

        self.p.set_widgets_data(config, self.options)

    def get_settings(self):

        return {
            "ui": {
                "decimalsep": self.DecimalSep.get_model().get(self.DecimalSep.get_active_iter(), 0)[0],
                "chatfont": self.SelectChatFont.get_font(),
                "listfont": self.SelectListFont.get_font(),
                "searchfont": self.SelectSearchFont.get_font(),
                "transfersfont": self.SelectTransfersFont.get_font(),
                "browserfont": self.SelectBrowserFont.get_font()
            }
        }

    def on_default_font(self, widget):
        self.SelectChatFont.set_font_name("")
        self.needcolors = 1

    def on_default_browser_font(self, widget):
        self.SelectBrowserFont.set_font_name("")
        self.needcolors = 1

    def on_default_list_font(self, widget):
        self.SelectListFont.set_font_name("")
        self.needcolors = 1

    def on_default_search_font(self, widget):
        self.SelectSearchFont.set_font_name("")
        self.needcolors = 1

    def on_default_transfers_font(self, widget):
        self.SelectTransfersFont.set_font_name("")
        self.needcolors = 1

    def fonts_colors_changed(self, widget):
        self.needcolors = 1


class LogFrame(BuildFrame):

    def __init__(self, parent):

        self.p = parent

        BuildFrame.__init__(self, "log")

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

        roomlogsdir = config["logging"]["roomlogsdir"]
        if roomlogsdir:
            if not os.path.exists(roomlogsdir):
                os.makedirs(roomlogsdir)

            self.RoomLogDir.set_current_folder(roomlogsdir)

        privatelogsdir = config["logging"]["privatelogsdir"]
        if privatelogsdir:
            if not os.path.exists(privatelogsdir):
                os.makedirs(privatelogsdir)

            self.PrivateLogDir.set_current_folder(privatelogsdir)

        transferslogsdir = config["logging"]["transferslogsdir"]
        if transferslogsdir:
            if not os.path.exists(transferslogsdir):
                os.makedirs(transferslogsdir)

            self.TransfersLogDir.set_current_folder(transferslogsdir)

        debuglogsdir = config["logging"]["debuglogsdir"]
        if debuglogsdir:
            if not os.path.exists(debuglogsdir):
                os.makedirs(debuglogsdir)

            self.DebugLogDir.set_current_folder(debuglogsdir)

    def get_settings(self):

        return {
            "logging": {
                "privatechat": self.LogPrivate.get_active(),
                "privatelogsdir": self.PrivateLogDir.get_file().get_path(),
                "chatrooms": self.LogRooms.get_active(),
                "roomlogsdir": self.RoomLogDir.get_file().get_path(),
                "transfers": self.LogTransfers.get_active(),
                "transferslogsdir": self.TransfersLogDir.get_file().get_path(),
                "debug_file_output": self.LogDebug.get_active(),
                "debuglogsdir": self.DebugLogDir.get_file().get_path(),
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


class SearchFrame(BuildFrame):

    def __init__(self, parent):
        self.p = parent
        BuildFrame.__init__(self, "search")
        self.options = {
            "searches": {
                "maxresults": self.MaxResults,
                "enablefilters": self.EnableFilters,
                "re_filter": self.RegexpFilters,
                "defilter": None,
                "reopen_tabs": self.ReopenTabs,
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
            self.FilterIn.set_text(searches["defilter"][0])
            self.FilterOut.set_text(searches["defilter"][1])
            self.FilterSize.set_text(searches["defilter"][2])
            self.FilterBR.set_text(searches["defilter"][3])
            self.FilterFree.set_active(searches["defilter"][4])
            if(len(searches["defilter"]) > 5):
                self.FilterCC.set_text(searches["defilter"][5])

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
                    self.FilterCC.get_text()
                ],
                "reopen_tabs": self.ReopenTabs.get_active(),
                "search_results": self.ToggleResults.get_active(),
                "max_displayed_results": self.MaxDisplayedResults.get_value_as_int(),
                "max_stored_results": self.MaxStoredResults.get_value_as_int(),
                "min_search_chars": self.MinSearchChars.get_value_as_int(),
                "remove_special_chars": self.RemoveSpecialChars.get_active()
            }
        }

    def on_enable_filters_toggled(self, widget):
        active = widget.get_active()
        for w in self.FilterIn, self.FilterOut, self.FilterSize, self.FilterBR, self.FilterFree:
            w.set_sensitive(active)

    def on_enable_search_results(self, widget):
        active = widget.get_active()
        for w in self.MinSearchCharsL1, self.MinSearchChars, self.MinSearchCharsL2, \
                self.MaxResults, self.MaxResultsL1, self.MaxResultsL2:
            w.set_sensitive(active)


class AwayFrame(BuildFrame):

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

        # Combobox for file manager
        self.file_manager_combo_store = Gtk.ListStore(GObject.TYPE_STRING)
        for executable in [
            "xdg-open $",
            "explorer $",
            "emelfm2 -1 $",
            "gentoo -1 $",
            "konqueror $",
            "krusader --left $",
            "nautilus --no-desktop $",
            "rox $",
            "thunar $",
            "xterm -e mc $"
        ]:
            self.file_manager_combo_store.append([executable])

        self.FileManagerCombo.set_model(self.file_manager_combo_store)
        self.FileManagerCombo.set_entry_text_column(0)

        # Combobox for audio players
        self.audio_player_combo_store = Gtk.ListStore(GObject.TYPE_STRING)
        for executable in [
            "amarok -a $",
            "audacious -e $",
            "exaile $",
            "rhythmbox $",
            "xmms2 add -f $"
        ]:
            self.audio_player_combo_store.append([executable])

        self.audioPlayerCombo.set_model(self.audio_player_combo_store)
        self.audioPlayerCombo.set_entry_text_column(0)

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


class UrlCatchFrame(BuildFrame):

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
            self.ProtocolHandlers,
            [_("Protocol"), -1, "text"],
            [_("Handler"), -1, "combo"]
        )

        cols[0].set_sort_column_id(0)
        cols[1].set_sort_column_id(1)

        self.ProtocolHandlers.set_model(self.protocolmodel)
        self.ProtocolHandlers.get_selection().connect("changed", self.on_select)

        renderers = cols[1].get_cells()
        for render in renderers:
            render.connect('edited', self.cell_edited_callback, self.ProtocolHandlers, 1)

        self.handlermodel = Gtk.ListStore(GObject.TYPE_STRING)

        for item in [
            "xdg-open $",
            "firefox $",
            "firefox -a firefox --remote \"openURL($,new-tab)\"",
            "opera $",
            "links -g $",
            "dillo $",
            "konqueror $",
            "\"c:\\Program Files\\Mozilla Firefox\\Firefox.exe\" $"
        ]:
            self.handlermodel.append([item])

        self.Handler.set_model(self.handlermodel)
        self.Handler.set_entry_text_column(0)

        renderers = cols[1].get_cells()
        for render in renderers:
            render.set_property("model", self.handlermodel)

        self.protomodel = Gtk.ListStore(GObject.TYPE_STRING)
        for item in ["http", "https", "ftp", "sftp", "news", "irc"]:
            self.protomodel.append([item])

        self.ProtocolCombo.set_model(self.protomodel)
        self.ProtocolCombo.set_entry_text_column(0)

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


class CensorFrame(BuildFrame):

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
            self.CensorList,
            [_("Pattern"), -1, "edit"]
        )

        cols[0].set_sort_column_id(0)

        self.CensorList.set_model(self.censor_list_model)

        # Combobox for the replacement letter
        self.censor_replace_combo_store = Gtk.ListStore(GObject.TYPE_STRING)
        for letter in ["#", "$", "!", " ", "x", "*"]:
            self.censor_replace_combo_store.append([letter])

        self.CensorReplaceCombo.set_model(self.censor_replace_combo_store)

        cell = Gtk.CellRendererText()
        self.CensorReplaceCombo.pack_start(cell, True)
        self.CensorReplaceCombo.add_attribute(cell, 'text', 0)

        renderers = cols[0].get_cells()
        for render in renderers:
            render.connect('edited', self.cell_edited_callback, self.CensorList, 0)

    def cell_edited_callback(self, widget, index, value, treeview, pos):

        store = treeview.get_model()
        iterator = store.get_iterator(index)

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
                "censorfill": self.CensorReplaceCombo.get_model().get(self.CensorReplaceCombo.get_active_iter(), 0)[0],
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


class AutoReplaceFrame(BuildFrame):

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
            self.ReplacementList,
            [_("Pattern"), 150, "edit"],
            [_("Replacement"), -1, "edit"]
        )
        cols[0].set_sort_column_id(0)
        cols[1].set_sort_column_id(1)

        self.ReplacementList.set_model(self.replacelist)

        for column in cols:
            renderers = column.get_cells()
            for render in renderers:
                render.connect('edited', self.cell_edited_callback, self.ReplacementList, cols.index(column))

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
                self.replacelist.append([word, replacement])

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
        defaults = {
            "teh ": "the ",
            "taht ": "that ",
            "tihng": "thing",
            "youre": "you're",
            "jsut": "just",
            "thier": "their",
            "tihs": "this"
        }

        for word, replacement in defaults.items():
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

        self.CompletionTabCheck.connect("toggled", self.on_completion_dropdown_check)
        self.CompletionCycleCheck.connect("toggled", self.on_completion_cycle_check)
        self.CompletionDropdownCheck.connect("toggled", self.on_completion_dropdown_check)
        self.CharactersCompletion.connect("changed", self.on_completion_changed)
        self.CompleteAliasesCheck.connect("toggled", self.on_completion_changed)
        self.CompleteCommandsCheck.connect("toggled", self.on_completion_changed)
        self.CompleteUsersInRoomsCheck.connect("toggled", self.on_completion_changed)
        self.CompleteBuddiesCheck.connect("toggled", self.on_completion_changed)
        self.CompleteRoomNamesCheck.connect("toggled", self.on_completion_changed)

    def set_settings(self, config):
        self.needcompletion = 0

        self.SpellCheck.set_sensitive(True if self.frame.spell_checker else False)

        self.p.set_widgets_data(config, self.options)

    def on_completion_changed(self, widget):
        self.needcompletion = 1

    def on_completion_dropdown_check(self, widget):
        sensitive = self.CompletionTabCheck.get_active()
        self.needcompletion = 1

        self.CompletionCycleCheck.set_sensitive(sensitive)
        self.CompleteRoomNamesCheck.set_sensitive(sensitive)
        self.CompleteBuddiesCheck.set_sensitive(sensitive)
        self.CompleteUsersInRoomsCheck.set_sensitive(sensitive)
        self.CompleteCommandsCheck.set_sensitive(sensitive)
        self.CompleteAliasesCheck.set_sensitive(sensitive)
        self.CompletionDropdownCheck.set_sensitive(sensitive)

        self.on_completion_cycle_check(widget)

    def on_completion_cycle_check(self, widget):
        sensitive = (self.CompletionTabCheck.get_active() and not self.CompletionCycleCheck.get_active())
        self.CompletionDropdownCheck.set_sensitive(sensitive)
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
        self.format_model = Gtk.ListStore(GObject.TYPE_STRING)

        self.default_format_list = [
            "$n",
            "$n ($f)",
            "$a - $t",
            "[$a] $t",
            "$a - $b - $t",
            "$a - $b - $t ($l/$r KBps) from $y $c"
        ]
        self.custom_format_list = []

        # Set the NPFormat model
        self.NPFormat.set_entry_text_column(0)
        self.NPFormat.set_model(self.format_model)

        # Suppy the information needed for the Now Playing class to return a song
        self.test_now_playing.connect(
            "clicked",
            self.p.frame.now_playing.display_now_playing,
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
        self.format_model.clear()

        for item in self.default_format_list:
            self.format_model.append([str(item)])

        if self.custom_format_list:
            for item in self.custom_format_list:
                self.format_model.append([str(item)])

        if config["players"]["npformat"] == "":
            # If there's no default format in the config: set the first of the list
            self.NPFormat.set_active(0)
        else:
            # If there's is a default format in the config: select the right item
            for (i, v) in enumerate(self.format_model):
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
        label.set_line_wrap(True)
        return label

    def generate_tree_view(self, name, description, value, c=0):

        self.tw["box%d" % c] = Gtk.Box(False, 5)
        self.tw["box%d" % c].set_orientation(Gtk.Orientation.VERTICAL)

        self.tw[name + "SW"] = Gtk.ScrolledWindow()
        self.tw[name + "SW"].set_shadow_type(Gtk.ShadowType.IN)
        self.tw[name + "SW"].set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        self.tw[name] = Gtk.TreeView()
        self.tw[name].set_model(Gtk.ListStore(GObject.TYPE_STRING))
        self.tw[name + "SW"].add(self.tw[name])

        self.tw["box%d" % c].pack_start(self.tw[name + "SW"], True, True, 5)

        cols = initialise_columns(self.tw[name], [description, 150, "edit"])

        try:
            self.settings.set_widget(self.tw[name], value)
        except Exception:
            pass

        self.add_button = Gtk.Button(_("Add"), Gtk.STOCK_ADD)
        self.remove_button = Gtk.Button(_("Remove"), Gtk.STOCK_REMOVE)

        self.tw["vbox%d" % c] = Gtk.Box(False, 5)
        self.tw["vbox%d" % c].pack_start(self.add_button, False, False, 0)
        self.tw["vbox%d" % c].pack_start(self.remove_button, False, False, 0)

        self.Main.pack_start(self.tw["box%d" % c], True, True, 0)
        self.Main.pack_start(self.tw["vbox%d" % c], False, False, 0)

        renderers = cols[0].get_cells()
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
                self.tw["box%d" % c].pack_start(self.tw["label%d" % c], False, False, 0)

                self.tw[name] = Gtk.SpinButton.new(Gtk.Adjustment(0, 0, 99999, 1, 10, 0), 1, 2)
                self.settings.set_widget(self.tw[name], self.settings.frame.np.config.sections["plugins"][plugin][name])
                self.tw["box%d" % c].pack_start(self.tw[name], False, False, 0)
                self.Main.pack_start(self.tw["box%d" % c], False, False, 0)
            elif data["type"] in ("bool",):
                self.tw["box%d" % c] = Gtk.Box(False, 5)
                self.tw["label%d" % c] = self.generate_label(data["description"])
                self.tw["box%d" % c].pack_start(self.tw["label%d" % c], False, False, 0)

                self.tw[name] = Gtk.CheckButton()
                self.settings.set_widget(self.tw[name], self.settings.frame.np.config.sections["plugins"][plugin][name])
                self.tw["box%d" % c].pack_start(self.tw[name], False, False, 0)
                self.Main.pack_start(self.tw["box%d" % c], False, False, 0)
            elif data['type'] in ('str', 'string', 'file'):
                self.tw["box%d" % c] = Gtk.Box(False, 5)
                self.tw["label%d" % c] = self.generate_label(data["description"])
                self.tw["box%d" % c].pack_start(self.tw["label%d" % c], False, False, 0)

                self.tw[name] = Gtk.Entry()
                self.settings.set_widget(self.tw[name], self.settings.frame.np.config.sections["plugins"][plugin][name])
                self.tw["box%d" % c].pack_start(self.tw[name], False, False, 0)
                self.Main.pack_start(self.tw["box%d" % c], False, False, 0)
            elif data['type'] in ('textview'):
                self.tw["box%d" % c] = Gtk.Box(False, 5)
                self.tw["label%d" % c] = self.generate_label(data["description"])
                self.tw["box%d" % c].pack_start(self.tw["label%d" % c], False, False, 0)

                self.tw[name] = Gtk.TextView()
                self.settings.set_widget(self.tw[name], self.settings.frame.np.config.sections["plugins"][plugin][name])

                self.tw["scrolledwindow%d" % c] = Gtk.ScrolledWindow()
                self.tw["scrolledwindow%d" % c].set_min_content_height(200)
                self.tw["scrolledwindow%d" % c].set_min_content_width(600)
                self.tw["scrolledwindow%d" % c].set_shadow_type(Gtk.ShadowType.IN)
                self.tw["scrolledwindow%d" % c].add(self.tw[name])

                self.tw["box%d" % c].pack_start(self.tw["scrolledwindow%d" % c], True, True, 0)
                self.Main.pack_start(self.tw["box%d" % c], True, True, 0)
            elif data["type"] in ("list string",):
                self.generate_tree_view(name, data["description"], value, c)
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


class NotificationsFrame(BuildFrame):

    def __init__(self, parent):

        self.p = parent

        BuildFrame.__init__(self, "notifications")

        self.options = {
            "notifications": {
                "notification_window_title": self.NotificationWindowTitle,
                "notification_tab_colors": self.NotificationTabColours,
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
                "notification_tab_colors": self.NotificationTabColours.get_active(),
                "notification_tab_icons": self.NotificationTabIcons.get_active(),
                "notification_popup_sound": self.NotificationPopupSound.get_active(),
                "notification_popup_file": self.NotificationPopupFile.get_active(),
                "notification_popup_folder": self.NotificationPopupFolder.get_active(),
                "notification_popup_private_message": self.NotificationPopupPrivateMessage.get_active(),
                "notification_popup_chatroom": self.NotificationPopupChatroom.get_active(),
                "notification_popup_chatroom_mention": self.NotificationPopupChatroomMention.get_active()
            }
        }


class PluginFrame(BuildFrame):

    def __init__(self, parent):

        self.p = parent
        BuildFrame.__init__(self, "plugin")

        self.options = {
            "plugins": {
                "enable": self.PluginsEnable
            }
        }

        self.plugins_model = Gtk.ListStore(
            GObject.TYPE_STRING,
            GObject.TYPE_BOOLEAN,
            GObject.TYPE_STRING
        )

        self.plugins = []
        self.pluginsiters = {}
        self.selected_plugin = None

        cols = initialise_columns(
            self.PluginTreeView,
            [_("Plugins"), 380, "text"],
            [_("Enabled"), -1, "toggle"]
        )

        cols[0].set_sort_column_id(0)
        cols[1].set_sort_column_id(1)

        renderers = cols[1].get_cells()
        for render in renderers:
            render.connect('toggled', self.cell_toggle_callback, self.PluginTreeView, 1)

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
        value = self.plugins_model.get_value(iterator, 1)
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
            enabled = (plugin in self.frame.np.pluginhandler.enabled_plugins)
            self.pluginsiters[filter] = self.plugins_model.append([info['Name'], enabled, plugin])

        return {}

    def on_plugins_enable(self, widget):
        self.PluginList.set_sensitive(self.PluginsEnable.get_active())

        if not self.PluginsEnable.get_active():
            # Disable all plugins
            for plugin in self.frame.np.pluginhandler.enabled_plugins.copy():
                self.frame.np.pluginhandler.disable_plugin(plugin)

            # Uncheck all checkboxes in GUI
            for plugin in self.plugins_model:
                self.plugins_model.set(plugin.iter, 1, False)

    def get_settings(self):
        return {
            "plugins": {
                "enable": self.PluginsEnable.get_active(),
                "enabled": list(self.frame.np.pluginhandler.enabled_plugins.keys())
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

        # This is ?
        self.empty_label = Gtk.Label.new("")
        self.empty_label.show()
        self.viewport1.add(self.empty_label)

        # Treeview of the settings
        self.tree = {}

        # Pages
        self.pages = p = {}
        self.handler_ids = {}

        # Model of the treeview
        model = Gtk.TreeStore(str, str)

        # Fill up the model
        self.tree["General"] = row = model.append(None, [_("General"), "General"])
        self.tree["Server"] = model.append(row, [_("Server"), "Server"])
        self.tree["Searches"] = model.append(row, [_("Searches"), "Searches"])
        self.tree["Notifications"] = model.append(row, [_("Notifications"), "Notifications"])
        self.tree["Plugins"] = model.append(row, [_("Plugins"), "Plugins"])
        self.tree["Text To Speech"] = model.append(row, [_("Text To Speech"), "Text To Speech"])
        self.tree["User Info"] = model.append(row, [_("User Info"), "User Info"])
        self.tree["Logging"] = model.append(row, [_("Logging"), "Logging"])

        self.tree["Transfers"] = row = model.append(None, [_("Transfers"), "Transfers"])
        self.tree["Shares"] = model.append(row, [_("Shares"), "Shares"])
        self.tree["Downloads"] = model.append(row, [_("Downloads"), "Downloads"])
        self.tree["Uploads"] = model.append(row, [_("Uploads"), "Uploads"])
        self.tree["Ban List"] = model.append(row, [_("Ban List"), "Ban List"])
        self.tree["Events"] = model.append(row, [_("Events"), "Events"])
        self.tree["Geo Block"] = model.append(row, [_("Geo Block"), "Geo Block"])

        self.tree["Interface"] = row = model.append(None, [_("Interface"), "Interface"])
        self.tree["Fonts"] = model.append(row, [_("Fonts"), "Fonts"])
        self.tree["Colours"] = model.append(row, [_("Colors"), "Colours"])
        self.tree["Icons"] = model.append(row, [_("Icons"), "Icons"])
        self.tree["Notebook Tabs"] = model.append(row, [_("Notebook Tabs"), "Notebook Tabs"])

        self.tree["Chat"] = row = model.append(None, [_("Chat"), "Chat"])
        self.tree["Now Playing"] = model.append(row, [_("Now Playing"), "Now Playing"])
        self.tree["Away Mode"] = model.append(row, [_("Away Mode"), "Away Mode"])
        self.tree["Ignore List"] = model.append(row, [_("Ignore List"), "Ignore List"])
        self.tree["Censor List"] = model.append(row, [_("Censor List"), "Censor List"])
        self.tree["Auto-Replace List"] = model.append(row, [_("Auto-Replace List"), "Auto-Replace List"])
        self.tree["URL Catching"] = model.append(row, [_("URL Catching"), "URL Catching"])
        self.tree["Completion"] = model.append(row, [_("Completion"), "Completion"])

        # Build individual categories
        p["Server"] = ServerFrame(self)
        p["Searches"] = SearchFrame(self)
        p["Notifications"] = NotificationsFrame(self)
        p["Plugins"] = PluginFrame(self)
        p["Text To Speech"] = TTSFrame(self)
        p["User Info"] = UserinfoFrame(self)
        p["Logging"] = LogFrame(self)

        p["Shares"] = SharesFrame(self)
        p["Downloads"] = DownloadsFrame(self)
        p["Uploads"] = UploadsFrame(self)
        p["Ban List"] = BanFrame(self)
        p["Events"] = EventsFrame(self)
        p["Geo Block"] = GeoBlockFrame(self)

        p["Fonts"] = FontsFrame(self)
        p["Colours"] = ColoursFrame(self)
        p["Icons"] = IconsFrame(self)
        p["Notebook Tabs"] = NotebookFrame(self)

        p["Now Playing"] = NowPlayingFrame(self)
        p["Away Mode"] = AwayFrame(self)
        p["Ignore List"] = IgnoreFrame(self)
        p["Censor List"] = CensorFrame(self)
        p["Auto-Replace List"] = AutoReplaceFrame(self)
        p["URL Catching"] = UrlCatchFrame(self)
        p["Completion"] = CompletionFrame(self)

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

        if page in self.pages:
            self.viewport1.add(self.pages[page].Main)
        else:
            self.viewport1.add(self.empty_label)

    def set_active_page(self, page):

        # Unminimize window
        self.SettingsWindow.deiconify()

        child = self.viewport1.get_child()

        if child:
            self.viewport1.remove(child)

        if self.tree[page] is None:
            self.viewport1.add(self.empty_label)
            return

        model = self.SettingsTreeview.get_model()
        sel = self.SettingsTreeview.get_selection()
        sel.unselect_all()
        path = model.get_path(self.tree[page])

        self.SettingsTreeview.expand_to_path(path)

        if path is not None:
            sel.select_path(path)

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
                widget.get_model().append([item])

    def invalid_settings(self, domain, key):

        for name, page in self.pages.items():
            if domain in page.options:
                if key in page.options[domain]:
                    self.set_active_page(name)
                    break

    def set_settings(self, config):

        for page in self.pages.values():
            page.set_settings(config)

    def get_settings(self):

        try:
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

            return self.pages["Server"].get_need_portmap(), self.pages["Shares"].get_need_rescan(), \
                (self.pages["Colours"].needcolors or self.pages["Fonts"].needcolors), self.pages["Completion"].needcompletion, config
        except UserWarning:
            return None

    def on_backup_config(self, *args):

        response = save_file(
            self.SettingsWindow.get_toplevel(),
            os.path.dirname(self.frame.np.config.filename),
            "config backup %s.tar.bz2" % (time.strftime("%Y-%m-%d %H_%M_%S")),
            title=_("Pick a filename for config backup")
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
