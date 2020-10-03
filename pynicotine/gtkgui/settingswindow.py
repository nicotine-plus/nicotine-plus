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
from gettext import gettext as _

from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import GdkPixbuf
from gi.repository import GObject as gobject
from gi.repository import Gtk as gtk

import _thread
from pynicotine import slskmessages
from pynicotine.gtkgui.dirchooser import ChooseDir
from pynicotine.gtkgui.dialogs import ComboBoxDialog
from pynicotine.gtkgui.dialogs import EntryDialog
from pynicotine.gtkgui.utils import HumanSize
from pynicotine.gtkgui.utils import InitialiseColumns
from pynicotine.gtkgui.utils import OpenUri
from pynicotine.logfacility import log
from pynicotine.upnp import UPnPPortMapping
from pynicotine.utils import unescape


win32 = sys.platform.startswith("win")
if win32:
    pass
else:
    import pwd


class buildFrame:
    """ This class build the individual frames from the settings window """

    def __init__(self, window):

        self.frame = self.p.frame

        # Build the frame
        builder = gtk.Builder()

        builder.set_translation_domain('nicotine')
        builder.add_from_file(os.path.join(os.path.dirname(os.path.realpath(__file__)), "ui", "settings", window + ".ui"))

        self.__dict__[window] = builder.get_object(window)

        for i in builder.get_objects():
            try:
                self.__dict__[gtk.Buildable.get_name(i)] = i
            except TypeError:
                pass

        self.__dict__[window].remove(self.Main)
        self.__dict__[window].destroy()

        builder.connect_signals(self)


class ServerFrame(buildFrame):

    def __init__(self, parent):

        self.p = parent

        buildFrame.__init__(self, "server")

        self.options = {
            "server": {
                "server": None,
                "login": self.Login,
                "passw": self.Password,
                "portrange": None,
                "firewalled": self.DirectConnection,
                "upnp": self.UseUPnP,
                "ctcpmsgs": self.ctcptogglebutton
            }
        }

    def SetSettings(self, config):

        self.p.SetWidgetsData(config, self.options)

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

        if server["firewalled"] is not None:
            self.DirectConnection.set_active(not server["firewalled"])

        if server["ctcpmsgs"] is not None:
            self.ctcptogglebutton.set_active(not server["ctcpmsgs"])

        # We need to check if the frame has the upnppossible attribute
        # If UPnP port mapping is wanted, OnFirstConnect has been called
        # and the attribute is set.
        # Otherwise we need to check if we have the prerequisites for allowing it.
        # The initialization of the UPnPPortMapping object and the check
        # don't generate any unwanted network traffic.
        if not hasattr(self.frame, 'upnppossible'):

            # Initialiase a UPnPPortMapping object
            upnp = UPnPPortMapping()

            # Check if we can do a port mapping
            (self.frame.upnppossible, errors) = upnp.IsPossible()

        if self.frame.upnppossible:
            # If we can do a port mapping the field is active
            # if the config said so
            self.UseUPnP.set_active(server["upnp"])
            self.UseUPnP.set_sensitive(True)
            self.labelRequirementsUPnP.hide()
        else:
            # If we cant do a port mapping: highlight the requirements
            # & disable the choice
            self.UseUPnP.set_active(False)
            self.UseUPnP.set_sensitive(False)
            self.labelRequirementsUPnP.show()

    def GetSettings(self):

        try:
            server = self.Server.get_text().split(":")
            server[1] = int(server[1])
            server = tuple(server)
        except Exception:
            server = None

        if str(self.Login.get_text()) == "None":
            dlg = gtk.MessageDialog(
                transient_for=self.p.SettingsWindow,
                flags=0,
                type=gtk.MessageType.WARNING,
                buttons=gtk.ButtonsType.OK,
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
            dlg = gtk.MessageDialog(
                transient_for=self.p.SettingsWindow,
                flags=0,
                type=gtk.MessageType.WARNING,
                buttons=gtk.ButtonsType.OK,
                text=_("Warning: Invalid ports")
            )
            dlg.format_secondary_text(_("Client ports are invalid."))
            dlg.run()
            dlg.destroy()
            raise UserWarning

        firewalled = not self.DirectConnection.get_active()

        return {
            "server": {
                "server": server,
                "login": self.Login.get_text(),
                "passw": self.Password.get_text(),
                "portrange": portrange,
                "firewalled": firewalled,
                "upnp": self.UseUPnP.get_active(),
                "ctcpmsgs": not self.ctcptogglebutton.get_active(),
            }
        }

    def OnChangePassword(self, widget):
        self.frame.np.queue.put(slskmessages.ChangePassword(self.Password.get_text()))

    def OnCheckPort(self, widget):
        OpenUri('='.join(['http://tools.slsknet.org/porttest.php?port', str(self.frame.np.waitport)]), self.p.SettingsWindow)


class DownloadsFrame(buildFrame):

    def __init__(self, parent):

        self.p = parent

        buildFrame.__init__(self, "downloads")

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

        self.UploadsAllowed_List = gtk.ListStore(gobject.TYPE_STRING)
        self.UploadsAllowed.set_model(self.UploadsAllowed_List)

        self.UploadsAllowed_List.clear()
        self.alloweduserslist = [
            _("No one"),
            _("Everyone"),
            _("Users in list"),
            _("Trusted Users")
        ]

        for item in self.alloweduserslist:
            self.UploadsAllowed_List.append([item])

        self.filterlist = gtk.ListStore(
            gobject.TYPE_STRING,
            gobject.TYPE_BOOLEAN
        )
        self.downloadfilters = []

        cols = InitialiseColumns(
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
        self.FilterView.get_selection().set_mode(gtk.SelectionMode.MULTIPLE)

    def SetSettings(self, config):

        transfers = config["transfers"]

        self.p.SetWidgetsData(config, self.options)

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
                filter, escaped = dfilter
                self.filtersiters[filter] = self.filterlist.append([filter, escaped])

        self.OnEnableFiltersToggle(self.DownloadFilter)

        self.needrescan = False

    def GetSettings(self):

        if win32:
            place = "Windows"
            homedir = "C:\\windows"
        else:
            place = "Home"
            homedir = pwd.getpwuid(os.getuid())[5]

        if homedir == self.DownloadDir.get_file().get_path() and self.ShareDownloadDir.get_active():

            dlg = gtk.MessageDialog(
                transient_for=self.p.SettingsWindow,
                flags=0,
                type=gtk.MessageType.WARNING,
                buttons=gtk.ButtonsType.OK,
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
                "downloadfilters": self.GetFilterList(),
                "enablefilters": self.DownloadFilter.get_active(),
                "downloadlimit": self.DownloadSpeed.get_value_as_int()
            }
        }

    def GetNeedRescan(self):
        return self.needrescan

    def OnChooseDownloadDir(self, widget):
        """
        Function called when the download directory is modified.
        """

        # Get a gio.File object from gtk.FileChooser
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

    def OnRemoteDownloads(self, widget):

        sensitive = widget.get_active()

        self.UploadsAllowed.set_sensitive(sensitive)

    def OnShareDownloadDirToggled(self, widget):
        self.needrescan = True

    def OnEnableFiltersToggle(self, widget):

        sensitive = widget.get_active()

        self.VerifyFilters.set_sensitive(sensitive)
        self.VerifiedLabel.set_sensitive(sensitive)
        self.DefaultFilters.set_sensitive(sensitive)
        self.RemoveFilter.set_sensitive(sensitive)
        self.EditFilter.set_sensitive(sensitive)
        self.AddFilter.set_sensitive(sensitive)
        self.FilterView.set_sensitive(sensitive)

    def OnAddFilter(self, widget):

        response = ComboBoxDialog(
            parent=self.p.SettingsWindow,
            title=_('Add a download filter'),
            message=_('Enter a new download filter:'),
            option=True,
            optionvalue=True,
            optionmessage="Escape this filter?",
            droplist=list(self.filtersiters.keys())
        )

        if type(response) is list:

            filter = response[0]
            escaped = response[1]

            if filter in self.filtersiters:
                self.filterlist.set(self.filtersiters[filter], 0, filter, 1, escaped)
            else:
                self.filtersiters[filter] = self.filterlist.append([filter, escaped])

            self.OnVerifyFilter(self.VerifyFilters)

    def GetFilterList(self):

        self.downloadfilters = []

        df = list(self.filtersiters.keys())
        df.sort()

        for filter in df:
            iterator = self.filtersiters[filter]
            dfilter = self.filterlist.get_value(iterator, 0)
            escaped = self.filterlist.get_value(iterator, 1)
            self.downloadfilters.append([dfilter, int(escaped)])

        return self.downloadfilters

    def OnEditFilter(self, widget):

        dfilter = self.GetSelectedFilter()

        if dfilter:

            iterator = self.filtersiters[dfilter]
            escapedvalue = self.filterlist.get_value(iterator, 1)

            response = ComboBoxDialog(
                parent=self.p.SettingsWindow,
                title=_('Edit a download filter'),
                message=_('Modify this download filter:'),
                default_text=dfilter,
                option=True,
                optionvalue=escapedvalue,
                optionmessage="Escape this filter?",
                droplist=list(self.filtersiters.keys())
            )

            if type(response) is list:

                filter, escaped = response

                if filter in self.filtersiters:
                    self.filterlist.set(self.filtersiters[filter], 0, filter, 1, escaped)
                else:
                    self.filtersiters[filter] = self.filterlist.append([filter, escaped])
                    del self.filtersiters[dfilter]
                    self.filterlist.remove(iterator)

                self.OnVerifyFilter(self.VerifyFilters)

    def _SelectedFilter(self, model, path, iterator, list):
        list.append(iterator)

    def GetSelectedFilter(self):

        iters = []
        self.FilterView.get_selection().selected_foreach(self._SelectedFilter, iters)

        if iters == []:
            return None

        dfilter = self.filterlist.get_value(iters[0], 0)

        return dfilter

    def OnRemoveFilter(self, widget):

        dfilter = self.GetSelectedFilter()

        if dfilter:

            iterator = self.filtersiters[dfilter]
            self.filterlist.remove(iterator)

            del self.filtersiters[dfilter]

            self.OnVerifyFilter(self.VerifyFilters)

    def OnDefaultFilters(self, widget):

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
            filter, escaped = dfilter
            self.filtersiters[filter] = self.filterlist.append([filter, escaped])

        self.OnVerifyFilter(self.VerifyFilters)

    def OnVerifyFilter(self, widget):

        outfilter = "(\\\\("

        df = list(self.filtersiters.keys())
        df.sort()

        proccessedfilters = []
        failed = {}

        for filter in df:

            iterator = self.filtersiters[filter]
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

            for filter, error in failed.items():
                errors += "Filter: %(filter)s Error: %(error)s " % {
                    'filter': filter,
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

        self.OnVerifyFilter(self.VerifyFilters)


class SharesFrame(buildFrame):

    def __init__(self, parent):

        self.p = parent

        buildFrame.__init__(self, "shares")

        self.needrescan = False

        # last column is the raw byte/unicode object for the folder (not shown)
        self.shareslist = gtk.ListStore(
            gobject.TYPE_STRING, gobject.TYPE_STRING,
            gobject.TYPE_STRING, gobject.TYPE_STRING
        )

        self.shareddirs = []

        # last column is the raw byte/unicode object for the folder (not shown)
        self.bshareslist = gtk.ListStore(
            gobject.TYPE_STRING, gobject.TYPE_STRING,
            gobject.TYPE_STRING, gobject.TYPE_STRING
        )

        self.bshareddirs = []

        InitialiseColumns(
            self.Shares,
            [_("Virtual Directory"), 0, "text"],
            [_("Directory"), 0, "text"],
            [_("Size"), 0, "text"]
        )

        self.Shares.set_model(self.shareslist)
        self.Shares.get_selection().set_mode(gtk.SelectionMode.MULTIPLE)

        InitialiseColumns(
            self.BuddyShares,
            [_("Virtual Directory"), 0, "text"],
            [_("Directory"), 0, "text"],
            [_("Size"), 0, "text"]
        )

        self.BuddyShares.set_model(self.bshareslist)
        self.BuddyShares.get_selection().set_mode(gtk.SelectionMode.MULTIPLE)

        self.options = {
            "transfers": {
                "shared": self.Shares,
                "friendsonly": self.FriendsOnly,
                "rescanonstartup": self.RescanOnStartup,
                "buddyshared": self.BuddyShares,
                "enablebuddyshares": self.enableBuddyShares
            }
        }

    def SetSettings(self, config):

        transfers = config["transfers"]
        self.shareslist.clear()
        self.bshareslist.clear()

        self.p.SetWidgetsData(config, self.options)
        self.OnEnabledBuddySharesToggled(self.enableBuddyShares)

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
                _thread.start_new_thread(self.GetDirectorySize, (actual, self.shareslist))

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
                _thread.start_new_thread(self.GetDirectorySize, (actual, self.shareslist))

            self.bshareddirs = transfers["buddyshared"][:]

        self.needrescan = False

    def GetSettings(self):

        if win32:
            place = "Windows"
            homedir = "C:\\windows"
        else:
            place = "Home"
            homedir = pwd.getpwuid(os.getuid())[5]

        for share in self.shareddirs + self.bshareddirs:
            if homedir == share:
                dlg = gtk.MessageDialog(
                    transient_for=self.p.SettingsWindow,
                    flags=0,
                    type=gtk.MessageType.WARNING,
                    buttons=gtk.ButtonsType.OK,
                    text=_("Warning")
                )
                dlg.format_secondary_text(_("Security Risk: you should not share your %s directory!") % place)
                dlg.run()
                dlg.destroy()
                raise UserWarning

        # Buddy shares related menus are activated if needed
        buddies = self.enableBuddyShares.get_active()

        self.frame.rescan_buddy.set_sensitive(buddies)
        self.frame.browse_buddy_shares.set_sensitive(buddies)

        # Public shares related menus are deactivated if we only share with friends
        friendsonly = self.FriendsOnly.get_active()

        self.frame.rescan_public.set_sensitive(not friendsonly)
        self.frame.browse_public_shares.set_sensitive(not friendsonly)

        return {
            "transfers": {
                "shared": self.shareddirs[:],
                "rescanonstartup": self.RescanOnStartup.get_active(),
                "buddyshared": self.bshareddirs[:],
                "enablebuddyshares": buddies,
                "friendsonly": friendsonly
            }
        }

    def OnEnabledBuddySharesToggled(self, widget):
        self.OnFriendsOnlyToggled(widget)

    def OnFriendsOnlyToggled(self, widget):

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

    def GetNeedRescan(self):
        return self.needrescan

    def OnAddSharedDir(self, widget):

        dir1 = ChooseDir(
            self.Main.get_toplevel(),
            title=_("Add a shared directory")
        )

        if dir1 is not None:

            for directory in dir1:

                # If the directory is already shared
                if directory in [x[1] for x in self.shareddirs + self.bshareddirs]:

                    dlg = gtk.MessageDialog(
                        transient_for=self.p.SettingsWindow,
                        flags=0,
                        type=gtk.MessageType.WARNING,
                        buttons=gtk.ButtonsType.OK,
                        text=_("Warning")
                    )
                    dlg.format_secondary_text(_("The chosen directory is already shared"))
                    dlg.run()
                    dlg.destroy()
                    pass

                else:

                    virtual = ComboBoxDialog(
                        parent=self.p.SettingsWindow,
                        title=_("Virtual name"),
                        message=_("Enter virtual name for '%(dir)s':") % {'dir': directory}
                    )

                    # If the virtual share name is not already used
                    if virtual == '' or virtual is None or virtual in [x[0] for x in self.shareddirs + self.bshareddirs]:

                        dlg = gtk.MessageDialog(
                            transient_for=self.p.SettingsWindow,
                            flags=0,
                            type=gtk.MessageType.WARNING,
                            buttons=gtk.ButtonsType.OK,
                            text=_("Warning")
                        )
                        dlg.format_secondary_text(_("The chosen virtual name is either empty or already exists"))
                        dlg.run()
                        dlg.destroy()
                        pass

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
                        _thread.start_new_thread(self.GetDirectorySize, (directory, self.shareslist))

    def OnAddSharedBuddyDir(self, widget):

        dir1 = ChooseDir(
            self.Main.get_toplevel(),
            title=_("Add a shared buddy directory")
        )

        if dir1 is not None:

            for directory in dir1:

                # If the directory is already shared
                if directory in [x[1] for x in self.shareddirs + self.bshareddirs]:

                    dlg = gtk.MessageDialog(
                        transient_for=self.p.SettingsWindow,
                        flags=0,
                        type=gtk.MessageType.WARNING,
                        buttons=gtk.ButtonsType.OK,
                        text=_("Warning")
                    )
                    dlg.format_secondary_text(_("The chosen directory is already shared"))
                    dlg.run()
                    dlg.destroy()
                    pass

                else:

                    virtual = ComboBoxDialog(
                        parent=self.p.SettingsWindow,
                        title=_("Virtual name"),
                        message=_("Enter virtual name for '%(dir)s':") % {'dir': directory}
                    )

                    # If the virtual share name is not already used
                    if virtual == '' or virtual is None or virtual in [x[0] for x in self.shareddirs + self.bshareddirs]:

                        dlg = gtk.MessageDialog(
                            transient_for=self.p.SettingsWindow,
                            flags=0,
                            type=gtk.MessageType.WARNING,
                            buttons=gtk.ButtonsType.OK,
                            text=_("Warning")
                        )
                        dlg.format_secondary_text(_("The chosen virtual name is either empty or already exists"))
                        dlg.run()
                        dlg.destroy()
                        pass

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
                        _thread.start_new_thread(self.GetDirectorySize, (directory, self.bshareslist))

    def _RemoveSharedDir(self, model, path, iterator, list):
        list.append(iterator)

    def OnRenameVirtuals(self, widget):

        iters = []
        self.Shares.get_selection().selected_foreach(self._RemoveSharedDir, iters)

        for iterator in iters:
            oldvirtual = self.shareslist.get_value(iterator, 0)
            directory = self.shareslist.get_value(iterator, 3)
            oldmapping = (oldvirtual, directory)

            virtual = ComboBoxDialog(
                parent=self.p.SettingsWindow,
                title=_("Virtual name"),
                message=_("Enter new virtual name for '%(dir)s':") % {'dir': directory}
            )

            if virtual == '' or virtual is None:
                pass
            else:
                newmapping = (virtual, directory)
                self.shareslist.set_value(iterator, 0, virtual)
                self.shareddirs.remove(oldmapping)
                self.shareddirs.append(newmapping)
                self.needrescan = True

    def OnRenameBuddyVirtuals(self, widget):

        iters = []
        self.BuddyShares.get_selection().selected_foreach(self._RemoveSharedDir, iters)

        for iterator in iters:
            oldvirtual = self.bshareslist.get_value(iterator, 0)
            directory = self.bshareslist.get_value(iterator, 3)
            oldmapping = (oldvirtual, directory)

            virtual = ComboBoxDialog(
                parent=self.p.SettingsWindow,
                title=_("Virtual name"),
                message=_("Enter new virtual name for '%(dir)s':") % {'dir': directory}
            )

            if virtual == '' or virtual is None:
                pass
            else:
                newmapping = (virtual, directory)
                self.bshareslist.set_value(iterator, 0, virtual)
                self.bshareslist.remove(oldmapping)
                self.bshareslist.append(newmapping)
                self.needrescan = True

    def OnRemoveSharedDir(self, widget):
        iters = []
        self.Shares.get_selection().selected_foreach(self._RemoveSharedDir, iters)

        for iterator in iters:
            virtual = self.shareslist.get_value(iterator, 0)
            actual = self.shareslist.get_value(iterator, 3)
            mapping = (virtual, actual)
            self.shareddirs.remove(mapping)
            self.shareslist.remove(iterator)

        if iters:
            self.needrescan = True

    def OnRemoveSharedBuddyDir(self, widget):
        iters = []
        self.BuddyShares.get_selection().selected_foreach(self._RemoveSharedDir, iters)

        for iterator in iters:
            virtual = self.bshareslist.get_value(iterator, 0)
            actual = self.bshareslist.get_value(iterator, 3)
            mapping = (virtual, actual)
            self.bshareddirs.remove(mapping)
            self.bshareslist.remove(iterator)

        if iters:
            self.needrescan = True

    def GetDirectorySize(self, directory, liststore):

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
            HumanSize(total_size),
            liststore
        )

    def _updatedirstats(self, directory, humansize, liststore):

        iterator = liststore.get_iter_first()

        while iterator is not None:

            if directory == liststore.get_value(iterator, 3):

                liststore.set(iterator, 2, humansize)

                return

            iterator = liststore.iter_next(iterator)


class UploadsFrame(buildFrame):

    def __init__(self, parent):

        self.p = parent

        buildFrame.__init__(self, "uploads")

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

    def SetSettings(self, config):

        self.p.SetWidgetsData(config, self.options)

        self.OnQueueUseSlotsToggled(self.QueueUseSlots)

        self.OnLimitToggled(self.Limit)

    def GetSettings(self):

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

    def OnQueueUseSlotsToggled(self, widget):

        sensitive = widget.get_active()

        self.QueueSlots.set_sensitive(sensitive)

        self.QueueBandwidth.set_sensitive(not sensitive)
        self.QueueBandwidthText1.set_sensitive(not sensitive)
        self.QueueBandwidthText2.set_sensitive(not sensitive)

    def OnLimitToggled(self, widget):

        sensitive = widget.get_active()

        for w in self.LimitSpeed, self.LimitPerTransfer, self.LimitTotalTransfers:
            w.set_sensitive(sensitive)


class GeoBlockFrame(buildFrame):

    def __init__(self, parent):
        self.p = parent
        buildFrame.__init__(self, "geoblock")

        self.options = {
            "transfers": {
                "geoblock": self.GeoBlock,
                "geopanic": self.GeoPanic,
                "geoblockcc": self.GeoBlockCC
            }
        }

    def SetSettings(self, config):
        transfers = config["transfers"]
        self.p.SetWidgetsData(config, self.options)

        if transfers["geoblockcc"] is not None:
            self.GeoBlockCC.set_text(transfers["geoblockcc"][0])

        self.OnGeoBlockToggled(self.GeoBlock)

    def GetSettings(self):
        return {
            "transfers": {
                "geoblock": self.GeoBlock.get_active(),
                "geopanic": self.GeoPanic.get_active(),
                "geoblockcc": [self.GeoBlockCC.get_text().upper()]
            }
        }

    def OnGeoBlockToggled(self, widget):
        sensitive = widget.get_active()
        self.GeoPanic.set_sensitive(sensitive)
        self.GeoBlockCC.set_sensitive(sensitive)


class UserinfoFrame(buildFrame):

    def __init__(self, parent):

        self.p = parent

        buildFrame.__init__(self, "userinfo")

        self.options = {
            "userinfo": {
                "descr": None,
                "pic": self.ImageChooser
            }
        }

        def UpdateImagePreview(chooser):
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

        preview = gtk.Image()
        self.ImageChooser.set_preview_widget(preview)
        self.ImageChooser.connect('update-preview', UpdateImagePreview)

    def SetSettings(self, config):

        self.p.SetWidgetsData(config, self.options)

        userinfo = config["userinfo"]

        if userinfo["descr"] is not None:
            descr = unescape(userinfo["descr"])
            self.Description.get_buffer().set_text(descr)

        if userinfo["pic"]:
            self.ImageChooser.set_filename(userinfo["pic"])

    def GetSettings(self):

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

    def OnDefaultImage(self, widget):
        self.ImageChooser.unselect_all()


class IgnoreFrame(buildFrame):

    def __init__(self, parent):

        self.p = parent
        buildFrame.__init__(self, "ignore")

        self.options = {
            "server": {
                "ignorelist": self.IgnoredUsers,
                "ipignorelist": self.IgnoredIPs
            }
        }

        self.ignored_users = []
        self.ignorelist = gtk.ListStore(gobject.TYPE_STRING)
        column = gtk.TreeViewColumn(_("Users"), gtk.CellRendererText(), text=0)
        self.IgnoredUsers.append_column(column)
        self.IgnoredUsers.set_model(self.ignorelist)
        self.IgnoredUsers.get_selection().set_mode(gtk.SelectionMode.MULTIPLE)

        self.ignored_ips = {}
        self.ignored_ips_list = gtk.ListStore(str, str)
        cols = InitialiseColumns(
            self.IgnoredIPs,
            [_("Addresses"), -1, "text", self.frame.CellDataFunc],
            [_("Users"), -1, "text", self.frame.CellDataFunc]
        )
        cols[0].set_sort_column_id(0)
        cols[1].set_sort_column_id(1)

        self.IgnoredIPs.set_model(self.ignored_ips_list)
        self.IgnoredIPs.get_selection().set_mode(gtk.SelectionMode.MULTIPLE)

    def SetSettings(self, config):
        server = config["server"]

        self.ignorelist.clear()
        self.ignored_ips_list.clear()
        self.ignored_users = []
        self.ignored_ips = {}
        self.p.SetWidgetsData(config, self.options)

        if server["ignorelist"] is not None:
            self.ignored_users = server["ignorelist"][:]

        if server["ipignorelist"] is not None:
            self.ignored_ips = server["ipignorelist"].copy()
            for ip, user in self.ignored_ips.items():
                self.ignored_ips_list.append([ip, user])

    def GetSettings(self):
        return {
            "server": {
                "ignorelist": self.ignored_users[:],
                "ipignorelist": self.ignored_ips.copy()
            }
        }

    def _AppendItem(self, model, path, iterator, line):
        line.append(iterator)

    def OnAddIgnored(self, widget):

        user = EntryDialog(
            self.Main.get_toplevel(),
            _("Ignore user..."),
            _("User:")
        )

        if user and user not in self.ignored_users:
            self.ignored_users.append(user)
            self.ignorelist.append([user])

    def OnRemoveIgnored(self, widget):
        iters = []
        self.IgnoredUsers.get_selection().selected_foreach(self._AppendItem, iters)
        for iterator in iters:
            user = self.ignorelist.get_value(iterator, 0)
            self.ignored_users.remove(user)
            self.ignorelist.remove(iterator)

    def OnClearIgnored(self, widget):
        self.ignored_users = []
        self.ignorelist.clear()

    def OnAddIgnoredIP(self, widget):

        ip = EntryDialog(
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

    def OnRemoveIgnoredIP(self, widget):
        iters = []
        self.IgnoredIPs.get_selection().selected_foreach(self._AppendItem, iters)
        for iterator in iters:
            ip = self.ignored_ips_list.get_value(iterator, 0)
            del self.ignored_ips[ip]
            self.ignored_ips_list.remove(iterator)

    def OnClearIgnoredIP(self, widget):
        self.ignored_ips = {}
        self.ignored_ips_list.clear()


class BanFrame(buildFrame):

    def __init__(self, parent):
        self.p = parent
        buildFrame.__init__(self, "ban")

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
        self.banlist_model = gtk.ListStore(gobject.TYPE_STRING)
        column = gtk.TreeViewColumn(_("Users"), gtk.CellRendererText(), text=0)
        self.BannedList.append_column(column)
        self.BannedList.set_model(self.banlist_model)
        self.BannedList.get_selection().set_mode(gtk.SelectionMode.MULTIPLE)

        self.blocked_list = {}
        self.blocked_list_model = gtk.ListStore(str, str)
        cols = InitialiseColumns(
            self.BlockedList,
            [_("Addresses"), -1, "text", self.frame.CellDataFunc],
            [_("Users"), -1, "text", self.frame.CellDataFunc]
        )
        cols[0].set_sort_column_id(0)
        cols[1].set_sort_column_id(1)

        self.BlockedList.set_model(self.blocked_list_model)
        self.BlockedList.get_selection().set_mode(gtk.SelectionMode.MULTIPLE)

    def SetSettings(self, config):
        server = config["server"]
        transfers = config["transfers"]
        self.banlist_model.clear()
        self.blocked_list_model.clear()

        self.banlist = server["banlist"][:]
        self.p.SetWidgetsData(config, self.options)

        if server["ipblocklist"] is not None:
            self.blocked_list = server["ipblocklist"].copy()
            for blocked, user in server["ipblocklist"].items():
                self.blocked_list_model.append([blocked, user])

        if transfers["usecustomban"] is not None:
            self.UseCustomBan.set_active(transfers["usecustomban"])

        if transfers["customban"] is not None:
            self.CustomBan.set_text(transfers["customban"])

        self.OnUseCustomBanToggled(self.UseCustomBan)

    def GetSettings(self):
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

    def OnAddBanned(self, widget):

        user = EntryDialog(
            self.Main.get_toplevel(),
            _("Ban user..."),
            _("User:")
        )

        if user and user not in self.banlist:
            self.banlist.append(user)
            self.banlist_model.append([user])

    def _AppendItem(self, model, path, iterator, line):
        line.append(iterator)

    def OnRemoveBanned(self, widget):
        iters = []
        self.BannedList.get_selection().selected_foreach(self._AppendItem, iters)
        for iterator in iters:
            user = self.banlist_model.get_value(iterator, 0)
            self.banlist.remove(user)
            self.banlist_model.remove(iterator)

    def OnClearBanned(self, widget):
        self.banlist = []
        self.banlist_model.clear()

    def OnUseCustomBanToggled(self, widget):
        self.CustomBan.set_sensitive(widget.get_active())

    def OnAddBlocked(self, widget):

        ip = EntryDialog(
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

    def OnRemoveBlocked(self, widget):
        iters = []
        self.BlockedList.get_selection().selected_foreach(self._AppendItem, iters)
        for iterator in iters:
            ip = self.blocked_list_model.get_value(iterator, 0)
            del self.blocked_list[ip]
            self.blocked_list_model.remove(iterator)

    def OnClearBlocked(self, widget):
        self.blocked_list = {}
        self.blocked_list_model.clear()


class TTSFrame(buildFrame):

    def __init__(self, parent):

        self.p = parent

        buildFrame.__init__(self, "tts")

        # Combobox for text-to-speech readers
        self.TTSCommand_List = gtk.ListStore(gobject.TYPE_STRING)
        for executable in ["echo $ | festival --tts", "flite -t $"]:
            self.TTSCommand_List.append([executable])

        self.TTSCommand.set_model(self.TTSCommand_List)
        self.TTSCommand.set_entry_text_column(0)

        self.options = {
            "ui": {
                "speechenabled": self.TextToSpeech,
                "speechcommand": self.TTSCommand,
                "speechrooms": self.RoomMessage,
                "speechprivate": self.PrivateMessage
            }
        }

    def DefaultPrivate(self, widget):
        self.PrivateMessage.set_text("%(user)s told you.. %(message)s")

    def DefaultRooms(self, widget):
        self.RoomMessage.set_text("In %(room)s, %(user)s said %(message)s")

    def DefaultTTS(self, widget):
        self.TTSCommand.get_child().set_text("flite -t \"%s\"")

    def OnTextToSpeechToggled(self, widget):

        sensitive = self.TextToSpeech.get_active()

        self.TTSGrid.set_sensitive(sensitive)

    def SetSettings(self, config):

        ui = config["ui"]

        self.p.SetWidgetsData(config, self.options)

        for i in ["%(user)s", "%(message)s"]:

            if i not in ui["speechprivate"]:
                self.DefaultPrivate(None)

            if i not in ui["speechrooms"]:
                self.DefaultRooms(None)

        self.OnTextToSpeechToggled(self.TextToSpeech)

    def GetSettings(self):

        return {
            "ui": {
                "speechenabled": self.TextToSpeech.get_active(),
                "speechcommand": self.TTSCommand.get_child().get_text(),
                "speechrooms": self.RoomMessage.get_text(),
                "speechprivate": self.PrivateMessage.get_text()
            }
        }


class IconsFrame(buildFrame):

    def __init__(self, parent):

        self.p = parent

        buildFrame.__init__(self, "icons")

        self.options = {
            "ui": {
                "icontheme": self.ThemeDir,
                "trayicon": self.TrayiconCheck,
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

    def SetSettings(self, config):

        ui = config["ui"]

        self.p.SetWidgetsData(config, self.options)

        if ui["icontheme"]:
            self.ThemeDir.set_current_folder(ui["icontheme"])

        if ui["exitdialog"] is not None:

            exitdialog = int(ui["exitdialog"])

            if exitdialog == 1:
                self.DialogOnClose.set_active(True)
            elif exitdialog == 2:
                self.SendToTrayOnClose.set_active(True)
            elif exitdialog == 0:
                self.QuitOnClose.set_active(True)

    def OnDefaultTheme(self, widget):
        self.ThemeDir.unselect_all()

    def GetSettings(self):

        mainwindow_close = 0

        widgets = [self.QuitOnClose, self.DialogOnClose, self.SendToTrayOnClose]

        for i in widgets:
            if i.get_active():
                mainwindow_close = widgets.index(i)
                break

        if self.ThemeDir.get_file() is not None:
            icontheme = self.ThemeDir.get_file().get_path()
        else:
            icontheme = ""

        return {
            "ui": {
                "icontheme": icontheme,
                "trayicon": self.TrayiconCheck.get_active(),
                "exitdialog": mainwindow_close
            }
        }


class ColoursFrame(buildFrame):

    def __init__(self, parent):

        self.p = parent

        buildFrame.__init__(self, "colours")

        # Combobox for user names style
        self.UsernameStyle_List = gtk.ListStore(gobject.TYPE_STRING)
        for item in ["bold", "italic", "underline", "normal"]:
            self.UsernameStyle_List.append([item])

        self.UsernameStyle.set_model(self.UsernameStyle_List)

        cell = gtk.CellRendererText()
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

        self.PickRemote.connect("clicked", self.PickColour, self.Remote, self.Drawing_Remote)
        self.PickLocal.connect("clicked", self.PickColour, self.Local, self.Drawing_Local)
        self.PickMe.connect("clicked", self.PickColour, self.Me, self.Drawing_Me)
        self.PickHighlight.connect("clicked", self.PickColour, self.Highlight, self.Drawing_Highlight)
        self.PickImmediate.connect("clicked", self.PickColour, self.Immediate, self.Drawing_Immediate)
        self.PickQueue.connect("clicked", self.PickColour, self.Queue, self.Drawing_Queue)

        self.PickAway.connect("clicked", self.PickColour, self.AwayColor, self.Drawing_AwayColor)
        self.PickOnline.connect("clicked", self.PickColour, self.OnlineColor, self.Drawing_OnlineColor)
        self.PickOffline.connect("clicked", self.PickColour, self.OfflineColor, self.Drawing_OfflineColor)
        self.PickURL.connect("clicked", self.PickColour, self.URL, self.Drawing_URL)
        self.DefaultURL.connect("clicked", self.DefaultColour, self.URL)

        self.DefaultAway.connect("clicked", self.DefaultColour, self.AwayColor)
        self.DefaultOnline.connect("clicked", self.DefaultColour, self.OnlineColor)
        self.DefaultOffline.connect("clicked", self.DefaultColour, self.OfflineColor)

        self.PickBackground.connect("clicked", self.PickColour, self.BackgroundColor, self.Drawing_BackgroundColor)
        self.DefaultBackground.connect("clicked", self.DefaultColour, self.BackgroundColor)

        self.PickInput.connect("clicked", self.PickColour, self.InputColor, self.Drawing_InputColor)
        self.DefaultInput.connect("clicked", self.DefaultColour, self.InputColor)

        self.DefaultRemote.connect("clicked", self.DefaultColour, self.Remote)
        self.DefaultLocal.connect("clicked", self.DefaultColour, self.Local)
        self.DefaultMe.connect("clicked", self.DefaultColour, self.Me)
        self.DefaultHighlight.connect("clicked", self.DefaultColour, self.Highlight)
        self.DefaultImmediate.connect("clicked", self.DefaultColour, self.Immediate)
        self.DefaultQueue.connect("clicked", self.DefaultColour, self.Queue)

        self.DefaultColours.connect("clicked", self.OnDefaultColours)
        self.ClearAllColours.connect("clicked", self.OnClearAllColours)
        self.DisplayAwayColours.connect("toggled", self.ToggledAwayColours)

        self.PickHighlightTab.connect("clicked", self.PickColour, self.HighlightTab, self.Drawing_HighlightTab)
        self.PickDefaultTab.connect("clicked", self.PickColour, self.DefaultTab, self.Drawing_DefaultTab)
        self.PickChangedTab.connect("clicked", self.PickColour, self.ChangedTab, self.Drawing_ChangedTab)

        self.DefaultHighlightTab.connect("clicked", self.DefaultColour, self.HighlightTab)
        self.DefaultChangedTab.connect("clicked", self.DefaultColour, self.ChangedTab)
        self.ClearDefaultTab.connect("clicked", self.DefaultColour, self.DefaultTab)

        # To set needcolors flag
        self.Local.connect("changed", self.FontsColorsChanged)
        self.Remote.connect("changed", self.FontsColorsChanged)
        self.Me.connect("changed", self.FontsColorsChanged)
        self.Highlight.connect("changed", self.FontsColorsChanged)
        self.BackgroundColor.connect("changed", self.FontsColorsChanged)
        self.Immediate.connect("changed", self.FontsColorsChanged)
        self.Queue.connect("changed", self.FontsColorsChanged)
        self.AwayColor.connect("changed", self.FontsColorsChanged)
        self.OnlineColor.connect("changed", self.FontsColorsChanged)
        self.OfflineColor.connect("changed", self.FontsColorsChanged)
        self.UsernameStyle.connect("changed", self.FontsColorsChanged)
        self.InputColor.connect("changed", self.FontsColorsChanged)

    def SetSettings(self, config):

        self.settingup = 1

        self.p.SetWidgetsData(config, self.options)

        for option in self.colors:
            for key, value in self.colorsd.items():

                if option in value:

                    drawingarea = self.colorsd[key][option]

                    try:
                        colour = Gdk.color_parse(config[key][option])
                    except Exception:
                        colour = None

                    drawingarea.modify_bg(gtk.StateType.NORMAL, colour)
                    break

        self.ToggledAwayColours(self.DisplayAwayColours)
        self.settingup = 0
        self.needcolors = 0

    def GetSettings(self):

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

    def ToggledAwayColours(self, widget):

        sensitive = widget.get_active()

        self.AwayColor.set_sensitive(sensitive)
        self.PickAway.set_sensitive(sensitive)
        self.DefaultAway.set_sensitive(sensitive)

    def OnDefaultColours(self, widget):
        for option in self.colors:
            self.SetDefaultColor(option)

    def SetDefaultColor(self, option):

        defaults = self.frame.np.config.defaults

        for key, value in self.options.items():
            if option in value:
                widget = self.options[key][option]
                if type(widget) is gtk.Entry:
                    widget.set_text(defaults[key][option])
                elif type(widget) is gtk.SpinButton:
                    widget.set_value_as_int(defaults[key][option])
                elif type(widget) is gtk.CheckButton:
                    widget.set_active(defaults[key][option])
                elif type(widget) is gtk.ComboBox:
                    widget.get_child().set_text(defaults[key][option])

        for key, value in self.colorsd.items():

            if option in value:

                drawingarea = self.colorsd[key][option]

                try:
                    colour = Gdk.color_parse(defaults[key][option])
                except Exception:
                    colour = None

                drawingarea.modify_bg(gtk.StateFlags.NORMAL, colour)
                break

    def OnClearAllColours(self, button):

        for option in self.colors:
            for section, value in self.options.items():

                if option in value:

                    widget = self.options[section][option]
                    if type(widget) is gtk.Entry:
                        widget.set_text("")
                    elif type(widget) is gtk.SpinButton:
                        widget.set_value_as_int(0)
                    elif type(widget) is gtk.CheckButton:
                        widget.set_active(0)
                    elif type(widget) is gtk.ComboBox:
                        widget.get_child().set_text("")

            for section, value in self.colorsd.items():
                if option in value:
                    drawingarea = self.colorsd[section][option]
                    drawingarea.modify_bg(gtk.StateFlags.NORMAL, None)

    def FontsColorsChanged(self, widget):
        self.needcolors = 1

    def OnUsernameHotspotsToggled(self, widget):

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

    def PickColour(self, widget, entry):

        dlg = gtk.ColorChooserDialog(_("Pick a color, any color"))
        colourtext = entry.get_text()

        if colourtext is not None and colourtext != '':
            try:
                rgba = Gdk.RGBA()
                rgba.parse(colourtext)
            except Exception:
                dlg.destroy()
                return
            else:
                dlg.set_rgba(rgba)

        if dlg.run() == gtk.ResponseType.OK:

            rgba = dlg.get_rgba()
            colourtext = "#%02X%02X%02X" % (round(rgba.red * 255), round(rgba.green * 255), round(rgba.blue * 255))
            entry.set_text(colourtext)

            for section in self.options.keys():

                if section not in self.colorsd:
                    continue

                for key, value in self.options[section].items():

                    if key not in self.colorsd[section]:
                        continue

                    if entry is value:
                        drawingarea = self.colorsd[section][key]
                        drawingarea.modify_bg(gtk.StateFlags.NORMAL, rgba.to_color())
                        break

        dlg.destroy()

    def DefaultColour(self, widget, entry):

        for section in self.options:
            for key, value in self.options[section].items():
                if value is entry:
                    self.SetDefaultColor(key)
                    return

        entry.set_text("")


class NotebookFrame(buildFrame):

    def __init__(self, parent):

        self.p = parent

        buildFrame.__init__(self, "notebook")

        # Define options for each GtkComboBox using a liststore
        # The first element is the translated string,
        # the second is a GtkPositionType
        self.PosList = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
        self.PosList.append([_("Top"), "Top"])
        self.PosList.append([_("Bottom"), "Bottom"])
        self.PosList.append([_("Left"), "Left"])
        self.PosList.append([_("Right"), "Right"])

        cell = gtk.CellRendererText()

        self.MainPosition.set_model(self.PosList)
        self.MainPosition.pack_start(cell, True)
        self.MainPosition.add_attribute(cell, 'text', 0)

        self.ChatRoomsPosition.set_model(self.PosList)
        self.ChatRoomsPosition.pack_start(cell, True)
        self.ChatRoomsPosition.add_attribute(cell, 'text', 0)

        self.PrivateChatPosition.set_model(self.PosList)
        self.PrivateChatPosition.pack_start(cell, True)
        self.PrivateChatPosition.add_attribute(cell, 'text', 0)

        self.SearchPosition.set_model(self.PosList)
        self.SearchPosition.pack_start(cell, True)
        self.SearchPosition.add_attribute(cell, 'text', 0)

        self.UserInfoPosition.set_model(self.PosList)
        self.UserInfoPosition.pack_start(cell, True)
        self.UserInfoPosition.add_attribute(cell, 'text', 0)

        self.UserBrowsePosition.set_model(self.PosList)
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

    def SetSettings(self, config):

        self.p.SetWidgetsData(config, self.options)

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

    def GetSettings(self):

        # Get iters from GtkComboBox fields
        iter_Main = self.PosList.get_iter(self.MainPosition.get_active())
        iter_Rooms = self.PosList.get_iter(self.ChatRoomsPosition.get_active())
        iter_Private = self.PosList.get_iter(self.PrivateChatPosition.get_active())
        iter_Search = self.PosList.get_iter(self.SearchPosition.get_active())
        iter_Info = self.PosList.get_iter(self.UserInfoPosition.get_active())
        iter_Browse = self.PosList.get_iter(self.UserBrowsePosition.get_active())

        return {
            "ui": {
                "tabmain": self.PosList.get_value(iter_Main, 1),
                "tabrooms": self.PosList.get_value(iter_Rooms, 1),
                "tabprivate": self.PosList.get_value(iter_Private, 1),
                "tabsearch": self.PosList.get_value(iter_Search, 1),
                "tabinfo": self.PosList.get_value(iter_Info, 1),
                "tabbrowse": self.PosList.get_value(iter_Browse, 1),
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


class FontsFrame(buildFrame):

    def __init__(self, parent):

        self.p = parent

        buildFrame.__init__(self, "fonts")

        # Combobox for the decimal separator
        self.DecimalSep_List = gtk.ListStore(gobject.TYPE_STRING)
        self.DecimalSep.set_model(self.DecimalSep_List)

        cell2 = gtk.CellRendererText()
        self.DecimalSep.pack_start(cell2, True)
        self.DecimalSep.add_attribute(cell2, 'text', 0)

        for item in ["<None>", ",", ".", "<space>"]:
            self.DecimalSep_List.append([item])

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

        self.DefaultFont.connect("clicked", self.OnDefaultFont)
        self.SelectChatFont.connect("font-set", self.FontsColorsChanged)

        self.DefaultListFont.connect("clicked", self.OnDefaultListFont)
        self.SelectListFont.connect("font-set", self.FontsColorsChanged)

        self.DefaultSearchFont.connect("clicked", self.OnDefaultSearchFont)
        self.SelectSearchFont.connect("font-set", self.FontsColorsChanged)

        self.DefaultTransfersFont.connect("clicked", self.OnDefaultTransfersFont)
        self.SelectTransfersFont.connect("font-set", self.FontsColorsChanged)

        self.DefaultBrowserFont.connect("clicked", self.OnDefaultBrowserFont)
        self.SelectBrowserFont.connect("font-set", self.FontsColorsChanged)

        self.needcolors = 0

    def SetSettings(self, config):

        self.needcolors = 0

        self.p.SetWidgetsData(config, self.options)

    def GetSettings(self):

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

    def OnDefaultFont(self, widget):
        self.SelectChatFont.set_font_name("")
        self.needcolors = 1

    def OnDefaultBrowserFont(self, widget):
        self.SelectBrowserFont.set_font_name("")
        self.needcolors = 1

    def OnDefaultListFont(self, widget):
        self.SelectListFont.set_font_name("")
        self.needcolors = 1

    def OnDefaultSearchFont(self, widget):
        self.SelectSearchFont.set_font_name("")
        self.needcolors = 1

    def OnDefaultTransfersFont(self, widget):
        self.SelectTransfersFont.set_font_name("")
        self.needcolors = 1

    def FontsColorsChanged(self, widget):
        self.needcolors = 1


class LogFrame(buildFrame):

    def __init__(self, parent):

        self.p = parent

        buildFrame.__init__(self, "log")

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

    def SetSettings(self, config):

        self.p.SetWidgetsData(config, self.options)

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

    def GetSettings(self):

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

    def OnDefaultTimestamp(self, widget):
        defaults = self.frame.np.config.defaults
        self.LogFileFormat.set_text(defaults["logging"]["log_timestamp"])

    def OnRoomDefaultTimestamp(self, widget):
        defaults = self.frame.np.config.defaults
        self.ChatRoomFormat.set_text(defaults["logging"]["rooms_timestamp"])

    def OnPrivateDefaultTimestamp(self, widget):
        defaults = self.frame.np.config.defaults
        self.PrivateChatFormat.set_text(defaults["logging"]["private_timestamp"])


class SearchFrame(buildFrame):

    def __init__(self, parent):
        self.p = parent
        buildFrame.__init__(self, "search")
        self.options = {
            "searches": {
                "maxresults": self.MaxResults,
                "enablefilters": self.EnableFilters,
                "re_filter": self.RegexpFilters,
                "defilter": None,
                "distrib_timer": self.ToggleDistributed,
                "distrib_ignore": self.ToggleDistributedInterval,
                "reopen_tabs": self.ReopenTabs,
                "search_results": self.ToggleResults,
                "max_displayed_results": self.MaxDisplayedResults,
                "max_stored_results": self.MaxStoredResults,
                "min_search_chars": self.MinSearchChars,
                "remove_special_chars": self.RemoveSpecialChars
            }
        }

    def SetSettings(self, config):
        try:
            searches = config["searches"]
        except Exception:
            searches = None
        self.p.SetWidgetsData(config, self.options)

        if searches["defilter"] is not None:
            self.FilterIn.set_text(searches["defilter"][0])
            self.FilterOut.set_text(searches["defilter"][1])
            self.FilterSize.set_text(searches["defilter"][2])
            self.FilterBR.set_text(searches["defilter"][3])
            self.FilterFree.set_active(searches["defilter"][4])
            if(len(searches["defilter"]) > 5):
                self.FilterCC.set_text(searches["defilter"][5])

        self.OnEnableSearchResults(self.ToggleResults)

    def GetSettings(self):
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
                "distrib_timer": self.ToggleDistributed.get_active(),
                "distrib_ignore": self.ToggleDistributedInterval.get_value_as_int(),
                "reopen_tabs": self.ReopenTabs.get_active(),
                "search_results": self.ToggleResults.get_active(),
                "max_displayed_results": self.MaxDisplayedResults.get_value_as_int(),
                "max_stored_results": self.MaxStoredResults.get_value_as_int(),
                "min_search_chars": self.MinSearchChars.get_value_as_int(),
                "remove_special_chars": self.RemoveSpecialChars.get_active()
            }
        }

    def OnEnableFiltersToggled(self, widget):
        active = widget.get_active()
        for w in self.FilterIn, self.FilterOut, self.FilterSize, self.FilterBR, self.FilterFree:
            w.set_sensitive(active)

    def OnEnableSearchResults(self, widget):
        active = widget.get_active()
        for w in self.MinSearchCharsL1, self.MinSearchChars, self.MinSearchCharsL2, \
                self.MaxResults, self.MaxResultsL1, self.MaxResultsL2, \
                self.ToggleDistributed, self.ToggleDistributedInterval, self.secondsLabel:
            w.set_sensitive(active)


class AwayFrame(buildFrame):

    def __init__(self, parent):
        self.p = parent
        buildFrame.__init__(self, "away")
        self.options = {
            "server": {
                "autoaway": self.AutoAway,
                "autoreply": self.AutoReply
            }
        }

    def SetSettings(self, config):
        self.p.SetWidgetsData(config, self.options)

    def GetSettings(self):
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


class EventsFrame(buildFrame):

    def __init__(self, parent):

        self.p = parent

        buildFrame.__init__(self, "events")

        # Combobox for file manager
        self.FileManagerCombo_List = gtk.ListStore(gobject.TYPE_STRING)
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
            self.FileManagerCombo_List.append([executable])

        self.FileManagerCombo.set_model(self.FileManagerCombo_List)
        self.FileManagerCombo.set_entry_text_column(0)

        # Combobox for audio players
        self.audioPlayerCombo_List = gtk.ListStore(gobject.TYPE_STRING)
        for executable in [
            "amarok -a $",
            "audacious -e $",
            "exaile $",
            "rhythmbox $",
            "xmms2 add -f $"
        ]:
            self.audioPlayerCombo_List.append([executable])

        self.audioPlayerCombo.set_model(self.audioPlayerCombo_List)
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

    def SetSettings(self, config):

        self.p.SetWidgetsData(config, self.options)

    def GetSettings(self):

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


class UrlCatchFrame(buildFrame):

    def __init__(self, parent):

        self.p = parent

        buildFrame.__init__(self, "urlcatch")

        self.options = {
            "urls": {
                "urlcatching": self.URLCatching,
                "humanizeurls": self.HumanizeURLs,
                "protocols": None
            }
        }

        self.protocolmodel = gtk.ListStore(
            gobject.TYPE_STRING,
            gobject.TYPE_STRING
        )

        self.protocols = {}

        cols = InitialiseColumns(
            self.ProtocolHandlers,
            [_("Protocol"), -1, "text"],
            [_("Handler"), -1, "combo"]
        )

        cols[0].set_sort_column_id(0)
        cols[1].set_sort_column_id(1)

        self.ProtocolHandlers.set_model(self.protocolmodel)
        self.ProtocolHandlers.get_selection().connect("changed", self.OnSelect)

        renderers = cols[1].get_cells()
        for render in renderers:
            render.connect('edited', self.cell_edited_callback, self.ProtocolHandlers, 1)

        self.handlermodel = gtk.ListStore(gobject.TYPE_STRING)

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

        self.protomodel = gtk.ListStore(gobject.TYPE_STRING)
        for item in ["http", "https", "ftp", "sftp", "news", "irc"]:
            self.protomodel.append([item])

        self.ProtocolCombo.set_model(self.protomodel)
        self.ProtocolCombo.set_entry_text_column(0)

    def cell_edited_callback(self, widget, index, value, treeview, pos):
        store = treeview.get_model()
        iterator = store.get_iter(index)
        store.set(iterator, pos, value)

    def SetSettings(self, config):

        self.protocolmodel.clear()
        self.protocols.clear()
        self.p.SetWidgetsData(config, self.options)

        urls = config["urls"]

        if urls["protocols"] is not None:

            for key in urls["protocols"].keys():
                if urls["protocols"][key][-1:] == "&":
                    command = urls["protocols"][key][:-1].rstrip()
                else:
                    command = urls["protocols"][key]

                iterator = self.protocolmodel.append([key, command])
                self.protocols[key] = iterator

        self.OnURLCatchingToggled(self.URLCatching)
        selection = self.ProtocolHandlers.get_selection()
        selection.unselect_all()

        for key, iterator in self.protocols.items():
            if iterator is not None:
                selection.select_iter(iterator)
                break

    def GetSettings(self):

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

    def OnURLCatchingToggled(self, widget):

        self.HumanizeURLs.set_active(widget.get_active())
        act = self.URLCatching.get_active()

        self.RemoveHandler.set_sensitive(act)
        self.addButton.set_sensitive(act)
        self.HumanizeURLs.set_sensitive(act)
        self.ProtocolHandlers.set_sensitive(act)
        self.ProtocolCombo.set_sensitive(act)
        self.Handler.set_sensitive(act)

    def OnSelect(self, selection):

        model, iterator = selection.get_selected()

        if iterator is None:
            self.ProtocolCombo.get_child().set_text("")
        else:
            protocol = model.get_value(iterator, 0)
            handler = model.get_value(iterator, 1)
            self.ProtocolCombo.get_child().set_text(protocol)
            self.Handler.get_child().set_text(handler)

    def OnAdd(self, widget):

        protocol = self.ProtocolCombo.get_child().get_text()
        command = self.Handler.get_child().get_text()

        if protocol in self.protocols:
            iterator = self.protocols[protocol]
            if iterator is not None:
                self.protocolmodel.set(iterator, 1, command)
        else:
            iterator = self.protocolmodel.append([protocol, command])
            self.protocols[protocol] = iterator

    def OnRemove(self, widget):

        selection = self.ProtocolHandlers.get_selection()
        model, iterator = selection.get_selected()

        if iterator is not None:
            protocol = self.protocolmodel.get_value(iterator, 0)
            self.protocolmodel.remove(iterator)
            del self.protocols[protocol]


class CensorFrame(buildFrame):

    def __init__(self, parent):

        self.p = parent

        buildFrame.__init__(self, "censor")

        self.options = {
            "words": {
                "censorfill": self.CensorReplaceCombo,
                "censored": self.CensorList,
                "censorwords": self.CensorCheck
            }
        }

        self.censor_list_model = gtk.ListStore(gobject.TYPE_STRING)

        cols = InitialiseColumns(
            self.CensorList,
            [_("Pattern"), -1, "edit", self.frame.CellDataFunc]
        )

        cols[0].set_sort_column_id(0)

        self.CensorList.set_model(self.censor_list_model)

        # Combobox for the replacement letter
        self.CensorReplaceCombo_List = gtk.ListStore(gobject.TYPE_STRING)
        for letter in ["#", "$", "!", " ", "x", "*"]:
            self.CensorReplaceCombo_List.append([letter])

        self.CensorReplaceCombo.set_model(self.CensorReplaceCombo_List)

        cell = gtk.CellRendererText()
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

    def SetSettings(self, config):

        self.censor_list_model.clear()

        self.p.SetWidgetsData(config, self.options)

        self.OnCensorCheck(self.CensorCheck)

    def OnCensorCheck(self, widget):

        sensitive = widget.get_active()

        self.CensorList.set_sensitive(sensitive)
        self.RemoveCensor.set_sensitive(sensitive)
        self.AddCensor.set_sensitive(sensitive)
        self.ClearCensors.set_sensitive(sensitive)
        self.CensorReplaceCombo.set_sensitive(sensitive)

    def GetSettings(self):

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

    def OnAdd(self, widget):

        iterator = self.censor_list_model.append([""])

        selection = self.CensorList.get_selection()
        selection.unselect_all()
        selection.select_iter(iterator)

        col = self.CensorList.get_column(0)

        self.CensorList.set_cursor(self.censor_list_model.get_path(iterator), col, True)

    def OnRemove(self, widget):
        selection = self.CensorList.get_selection()
        iterator = selection.get_selected()[1]
        if iterator is not None:
            self.censor_list_model.remove(iterator)

    def OnClear(self, widget):
        self.censor_list_model.clear()


class AutoReplaceFrame(buildFrame):

    def __init__(self, parent):

        self.p = parent
        buildFrame.__init__(self, "autoreplace")

        self.options = {
            "words": {
                "autoreplaced": self.ReplacementList,
                "replacewords": self.ReplaceCheck
            }
        }

        self.replacelist = gtk.ListStore(
            gobject.TYPE_STRING,
            gobject.TYPE_STRING
        )

        cols = InitialiseColumns(
            self.ReplacementList,
            [_("Pattern"), 150, "edit", self.frame.CellDataFunc],
            [_("Replacement"), -1, "edit", self.frame.CellDataFunc]
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

    def SetSettings(self, config):
        self.replacelist.clear()
        self.p.SetWidgetsData(config, self.options)
        words = config["words"]
        if words["autoreplaced"] is not None:
            for word, replacement in words["autoreplaced"].items():
                self.replacelist.append([word, replacement])

        self.OnReplaceCheck(self.ReplaceCheck)

    def OnReplaceCheck(self, widget):
        sensitive = widget.get_active()
        self.ReplacementList.set_sensitive(sensitive)
        self.RemoveReplacement.set_sensitive(sensitive)
        self.AddReplacement.set_sensitive(sensitive)
        self.ClearReplacements.set_sensitive(sensitive)
        self.DefaultReplacements.set_sensitive(sensitive)

    def GetSettings(self):
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

    def OnAdd(self, widget):
        iterator = self.replacelist.append(["", ""])
        selection = self.ReplacementList.get_selection()
        selection.unselect_all()
        selection.select_iter(iterator)
        col = self.ReplacementList.get_column(0)

        self.ReplacementList.set_cursor(self.replacelist.get_path(iterator), col, True)

    def OnRemove(self, widget):
        selection = self.ReplacementList.get_selection()
        iterator = selection.get_selected()[1]
        if iterator is not None:
            self.replacelist.remove(iterator)

    def OnClear(self, widget):
        self.replacelist.clear()

    def OnDefaults(self, widget):

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


class CompletionFrame(buildFrame):

    def __init__(self, parent):

        self.p = parent
        buildFrame.__init__(self, "completion")

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

        self.CompletionTabCheck.connect("toggled", self.OnCompletionDropdownCheck)
        self.CompletionCycleCheck.connect("toggled", self.OnCompletionCycleCheck)
        self.CompletionDropdownCheck.connect("toggled", self.OnCompletionDropdownCheck)
        self.CharactersCompletion.connect("changed", self.OnCompletionChanged)
        self.CompleteAliasesCheck.connect("toggled", self.OnCompletionChanged)
        self.CompleteCommandsCheck.connect("toggled", self.OnCompletionChanged)
        self.CompleteUsersInRoomsCheck.connect("toggled", self.OnCompletionChanged)
        self.CompleteBuddiesCheck.connect("toggled", self.OnCompletionChanged)
        self.CompleteRoomNamesCheck.connect("toggled", self.OnCompletionChanged)

    def SetSettings(self, config):
        self.needcompletion = 0

        self.SpellCheck.set_sensitive(self.frame.gspell)

        self.p.SetWidgetsData(config, self.options)

    def OnCompletionChanged(self, widget):
        self.needcompletion = 1

    def OnCompletionDropdownCheck(self, widget):
        sensitive = self.CompletionTabCheck.get_active()
        self.needcompletion = 1

        self.CompletionCycleCheck.set_sensitive(sensitive)
        self.CompleteRoomNamesCheck.set_sensitive(sensitive)
        self.CompleteBuddiesCheck.set_sensitive(sensitive)
        self.CompleteUsersInRoomsCheck.set_sensitive(sensitive)
        self.CompleteCommandsCheck.set_sensitive(sensitive)
        self.CompleteAliasesCheck.set_sensitive(sensitive)
        self.CompletionDropdownCheck.set_sensitive(sensitive)

        self.OnCompletionCycleCheck(widget)

    def OnCompletionCycleCheck(self, widget):
        sensitive = (self.CompletionTabCheck.get_active() and not self.CompletionCycleCheck.get_active())
        self.CompletionDropdownCheck.set_sensitive(sensitive)
        self.CharactersCompletion.set_sensitive(sensitive)
        self.OneMatchCheck.set_sensitive(sensitive)

    def GetSettings(self):
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


class buildDialog(gtk.Dialog):
    """ Class used to build a custom dialog for the plugins """

    def __init__(self, parent):

        window = "PluginProperties"

        self.settings = parent.p

        # Build the window
        builder = gtk.Builder()

        builder.set_translation_domain('nicotine')
        builder.add_from_file(os.path.join(os.path.dirname(os.path.realpath(__file__)), "ui", "settings", "pluginproperties.ui"))

        self.PluginProperties = builder.get_object(window)

        for i in builder.get_objects():
            try:
                self.__dict__[gtk.Buildable.get_name(i)] = i
            except TypeError:
                pass

        builder.connect_signals(self)

        self.PluginProperties.set_transient_for(self.settings.SettingsWindow)
        self.tw = {}
        self.options = {}
        self.plugin = None

    def GenerateLabel(self, text):
        label = gtk.Label(text)
        label.set_line_wrap(True)
        return label

    def GenerateTreeView(self, name, description, value, c=0):

        self.tw["box%d" % c] = gtk.Box(False, 5)
        self.tw["box%d" % c].set_orientation(gtk.Orientation.VERTICAL)

        self.tw[name + "SW"] = gtk.ScrolledWindow()
        self.tw[name + "SW"].set_shadow_type(gtk.ShadowType.IN)
        self.tw[name + "SW"].set_policy(gtk.PolicyType.AUTOMATIC, gtk.PolicyType.AUTOMATIC)

        self.tw[name] = gtk.TreeView()
        self.tw[name].set_model(gtk.ListStore(gobject.TYPE_STRING))
        self.tw[name + "SW"].add(self.tw[name])

        self.tw["box%d" % c].pack_start(self.tw[name + "SW"], True, True, 5)

        cols = InitialiseColumns(self.tw[name], [description, 150, "edit"])

        try:
            self.settings.SetWidget(self.tw[name], value)
        except Exception:
            pass

        self.addButton = gtk.Button(_("Add"), gtk.STOCK_ADD)
        self.removeButton = gtk.Button(_("Remove"), gtk.STOCK_REMOVE)

        self.tw["vbox%d" % c] = gtk.Box(False, 5)
        self.tw["vbox%d" % c].pack_start(self.addButton, False, False, 0)
        self.tw["vbox%d" % c].pack_start(self.removeButton, False, False, 0)

        self.Main.pack_start(self.tw["box%d" % c], True, True, 0)
        self.Main.pack_start(self.tw["vbox%d" % c], False, False, 0)

        renderers = cols[0].get_cells()
        for render in renderers:
            render.connect('edited', self.cell_edited_callback, self.tw[name])

        self.addButton.connect("clicked", self.OnAdd, self.tw[name])
        self.removeButton.connect("clicked", self.OnRemove, self.tw[name])

    def cell_edited_callback(self, widget, index, value, treeview):
        store = treeview.get_model()
        iterator = store.get_iter(index)
        store.set(iterator, 0, value)

    def OnAdd(self, widget, treeview):

        iterator = treeview.get_model().append([""])
        col = treeview.get_column(0)

        treeview.set_cursor(treeview.get_model().get_path(iterator), col, True)

    def OnRemove(self, widget, treeview):
        selection = treeview.get_selection()
        iterator = selection.get_selected()[1]
        if iterator is not None:
            treeview.get_model().remove(iterator)

    def addOptions(self, plugin, options={}):

        for i in self.tw:
            self.tw[i].destroy()

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
            # and we can use self.settings.SetWidget and self.settings.GetWidgetData to set and get values
            #
            # Todo: gtk.ComboBox, and gtk.RadioButton

            value = self.settings.frame.np.config.sections["plugins"][plugin][name]

            if data["type"] in ("integer", "int", "float"):
                self.tw["box%d" % c] = gtk.Box(False, 5)
                self.tw["label%d" % c] = self.GenerateLabel(data["description"])
                self.tw["box%d" % c].pack_start(self.tw["label%d" % c], False, False, 0)

                self.tw[name] = gtk.SpinButton.new(gtk.Adjustment(0, 0, 99999, 1, 10, 0), 1, 2)
                self.settings.SetWidget(self.tw[name], self.settings.frame.np.config.sections["plugins"][plugin][name])
                self.tw["box%d" % c].pack_start(self.tw[name], False, False, 0)
                self.Main.pack_start(self.tw["box%d" % c], False, False, 0)
            elif data["type"] in ("bool",):
                self.tw["box%d" % c] = gtk.Box(False, 5)
                self.tw["label%d" % c] = self.GenerateLabel(data["description"])
                self.tw["box%d" % c].pack_start(self.tw["label%d" % c], False, False, 0)

                self.tw[name] = gtk.CheckButton()
                self.settings.SetWidget(self.tw[name], self.settings.frame.np.config.sections["plugins"][plugin][name])
                self.tw["box%d" % c].pack_start(self.tw[name], False, False, 0)
                self.Main.pack_start(self.tw["box%d" % c], False, False, 0)
            elif data['type'] in ('str', 'string', 'file'):
                self.tw["box%d" % c] = gtk.Box(False, 5)
                self.tw["label%d" % c] = self.GenerateLabel(data["description"])
                self.tw["box%d" % c].pack_start(self.tw["label%d" % c], False, False, 0)

                self.tw[name] = gtk.Entry()
                self.settings.SetWidget(self.tw[name], self.settings.frame.np.config.sections["plugins"][plugin][name])
                self.tw["box%d" % c].pack_start(self.tw[name], False, False, 0)
                self.Main.pack_start(self.tw["box%d" % c], False, False, 0)
            elif data['type'] in ('textview'):
                self.tw["box%d" % c] = gtk.Box(False, 5)
                self.tw["label%d" % c] = self.GenerateLabel(data["description"])
                self.tw["box%d" % c].pack_start(self.tw["label%d" % c], False, False, 0)

                self.tw[name] = gtk.TextView()
                self.settings.SetWidget(self.tw[name], self.settings.frame.np.config.sections["plugins"][plugin][name])

                self.tw["scrolledwindow%d" % c] = gtk.ScrolledWindow()
                self.tw["scrolledwindow%d" % c].set_min_content_height(100)
                self.tw["scrolledwindow%d" % c].set_min_content_width(400)
                self.tw["scrolledwindow%d" % c].set_shadow_type(gtk.ShadowType.IN)
                self.tw["scrolledwindow%d" % c].add(self.tw[name])

                self.tw["box%d" % c].pack_start(self.tw["scrolledwindow%d" % c], False, False, 0)
                self.Main.pack_start(self.tw["box%d" % c], False, False, 0)
            elif data["type"] in ("list string",):
                self.GenerateTreeView(name, data["description"], value, c)
            else:
                print("Unknown setting type '%s', data '%s'" % (name, data))

            c += 1

        self.PluginProperties.show_all()

    def OnCancel(self, widget):
        self.PluginProperties.hide()

    def OnOkay(self, widget):
        for name in self.options:
            value = self.settings.GetWidgetData(self.tw[name])
            if value is not None:
                self.settings.frame.np.config.sections["plugins"][self.plugin][name] = value
        self.PluginProperties.hide()
        self.settings.frame.np.pluginhandler.plugin_settings(self.settings.frame.np.pluginhandler.loaded_plugins[self.plugin].PLUGIN)

    def Show(self):
        self.PluginProperties.show()


class NotificationsFrame(buildFrame):

    def __init__(self, parent):

        self.p = parent

        buildFrame.__init__(self, "notifications")

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

    def SetSettings(self, config):

        if self.frame.notifications.notification_provider is not None:
            self.NotificationPopupSound.set_sensitive(True)
            self.NotificationPopupFile.set_sensitive(True)
            self.NotificationPopupFolder.set_sensitive(True)
            self.NotificationPopupPrivateMessage.set_sensitive(True)
            self.NotificationPopupChatroom.set_sensitive(True)
            self.NotificationPopupChatroomMention.set_sensitive(True)
        else:
            self.NotificationPopupSound.set_sensitive(False)
            self.NotificationPopupFile.set_sensitive(False)
            self.NotificationPopupFolder.set_sensitive(False)
            self.NotificationPopupPrivateMessage.set_sensitive(False)
            self.NotificationPopupChatroom.set_sensitive(False)
            self.NotificationPopupChatroomMention.set_sensitive(False)

        self.p.SetWidgetsData(config, self.options)

    def GetSettings(self):

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


class PluginFrame(buildFrame):

    def __init__(self, parent):

        self.p = parent
        buildFrame.__init__(self, "plugin")

        self.options = {
            "plugins": {
                "enable": self.PluginsEnable
            }
        }

        self.plugins_model = gtk.ListStore(
            gobject.TYPE_STRING,
            gobject.TYPE_BOOLEAN,
            gobject.TYPE_STRING
        )

        self.plugins = []
        self.pluginsiters = {}
        self.selected_plugin = None

        cols = InitialiseColumns(
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
        self.PluginTreeView.get_selection().connect("changed", self.OnSelectPlugin)

        self.dialog = buildDialog(self)

    def OnPluginProperties(self, widget):
        if self.selected_plugin is None:
            return

        self.dialog.addOptions(
            self.selected_plugin,
            self.frame.np.pluginhandler.get_plugin_settings(self.selected_plugin)
        )

        self.dialog.Show()

    def OnSelectPlugin(self, selection):

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

        self.CheckPropertiesButton(self.selected_plugin)

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

        self.CheckPropertiesButton(plugin)

    def CheckPropertiesButton(self, plugin):
        settings = self.frame.np.pluginhandler.get_plugin_settings(plugin)

        if settings is not None:
            self.PluginProperties.set_sensitive(True)
        else:
            self.PluginProperties.set_sensitive(False)

    def SetSettings(self, config):

        self.p.SetWidgetsData(config, self.options)
        self.OnPluginsEnable(None)
        self.pluginsiters = {}
        self.plugins_model.clear()
        plugins = self.frame.np.pluginhandler.list_installed_plugins()
        plugins.sort()

        for plugin in plugins:
            try:
                info = self.frame.np.pluginhandler.get_plugin_info(plugin)
            except IOError:
                continue
            enabled = (plugin in self.frame.np.pluginhandler.enabled_plugins)
            self.pluginsiters[filter] = self.plugins_model.append([info['Name'], enabled, plugin])

        return {}

    def OnPluginsEnable(self, widget):
        self.PluginList.set_sensitive(self.PluginsEnable.get_active())

        if not self.PluginsEnable.get_active():
            # Disable all plugins
            for plugin in self.frame.np.pluginhandler.enabled_plugins:
                self.frame.np.pluginhandler.disable_plugin(plugin)

            # Uncheck all checkboxes in GUI
            for plugin in self.plugins_model:
                self.plugins_model.set(plugin.iter, 1, False)

    def GetSettings(self):
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
        builder = gtk.Builder()

        builder.set_translation_domain('nicotine')
        builder.add_from_file(os.path.join(os.path.dirname(os.path.realpath(__file__)), "ui", "settings", "settingswindow.ui"))

        self.SettingsWindow = builder.get_object("SettingsWindow")

        for i in builder.get_objects():
            try:
                self.__dict__[gtk.Buildable.get_name(i)] = i
            except TypeError:
                pass

        builder.connect_signals(self)

        # Signal sent and catch by frame.py on close
        gobject.signal_new("settings-closed", gtk.Window, gobject.SignalFlags.RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_STRING,))

        # Connect the custom handlers
        self.SettingsWindow.set_transient_for(frame.MainWindow)
        self.SettingsWindow.connect("delete-event", self.OnDelete)

        # This is ?
        self.empty_label = gtk.Label.new("")
        self.empty_label.show()
        self.viewport1.add(self.empty_label)

        # Treeview of the settings
        self.tree = {}

        # Pages
        self.pages = p = {}
        self.handler_ids = {}

        # Model of the treeview
        model = gtk.TreeStore(str, str)

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

        p["Away Mode"] = AwayFrame(self)
        p["Ignore List"] = IgnoreFrame(self)
        p["Censor List"] = CensorFrame(self)
        p["Auto-Replace List"] = AutoReplaceFrame(self)
        p["URL Catching"] = UrlCatchFrame(self)
        p["Completion"] = CompletionFrame(self)

        # Title of the treeview
        column = gtk.TreeViewColumn(_("Categories"), gtk.CellRendererText(), text=0)

        # set the model on the treeview
        self.SettingsTreeview.set_model(model)
        self.SettingsTreeview.append_column(column)

        # Expand all
        self.SettingsTreeview.expand_all()

        # Connect the signal when a page/category is changed
        self.SettingsTreeview.get_selection().connect("changed", self.switch_page)

        # Set the cursor to the second element of the TreeViewColumn.
        self.SettingsTreeview.set_cursor((0, 0))

        self.UpdateColours()

    def ColourWidgets(self, widget):

        if type(widget) in (gtk.Entry, gtk.SpinButton):
            self.SetTextBG(widget)
        if type(widget) is gtk.TreeView:
            self.frame.ChangeListFont(widget, self.frame.np.config.sections["ui"]["listfont"])

    def UpdateColours(self):

        for widget in self.__dict__.values():
            self.ColourWidgets(widget)

        for name, page in self.pages.items():
            for widget in page.__dict__.values():
                self.ColourWidgets(widget)

    def SetTextBG(self, widget, bgcolor="", fgcolor=""):
        self.frame.SetTextBG(widget, bgcolor, fgcolor)

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

    def SwitchToPage(self, page):

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

    def OnApply(self, widget):
        self.SettingsWindow.emit("settings-closed", "apply")

    def OnOk(self, widget):
        self.SettingsWindow.emit("settings-closed", "ok")

    def OnCancel(self, widget):
        self.SettingsWindow.emit("settings-closed", "cancel")

    def OnDelete(self, widget, event):
        self.OnCancel(widget)
        widget.stop_emission_by_name("delete-event")
        return True

    def GetPosition(self, combobox, option):
        iterator = combobox.get_model().get_iter_first()
        while iterator is not None:
            word = combobox.get_model().get_value(iterator, 0)
            if word.lower() == option or word == option:
                combobox.set_active_iter(iterator)
                break
            iterator = combobox.get_model().iter_next(iterator)

    def SetWidgetsData(self, config, options):
        for section, keys in options.items():
            if section not in config:
                continue
            for key in keys:
                widget = options[section][key]
                if widget is None:
                    continue
                if config[section][key] is None:
                    self.ClearWidget(widget)
                else:
                    self.SetWidget(widget, config[section][key])

    def GetWidgetData(self, widget):

        if type(widget) is gtk.Entry:
            return widget.get_text()
        elif type(widget) is gtk.TextView:
            buffer = widget.get_buffer()
            start, end = buffer.get_bounds()
            return widget.get_buffer().get_text(start, end, True)
        elif type(widget) is gtk.SpinButton:
            return int(widget.get_value())
        elif type(widget) is gtk.CheckButton:
            return widget.get_active()
        elif type(widget) is gtk.RadioButton:
            return widget.get_active()
        elif type(widget) is gtk.ComboBox:
            return widget.get_model().get(widget.get_active_iter(), 0)[0]
        elif type(widget) is gtk.FontButton:
            widget.get_font()
        elif type(widget) is gtk.TreeView and widget.get_model().get_n_columns() == 1:
            wlist = []
            iterator = widget.get_model().get_iter_first()
            while iterator:
                word = widget.get_model().get_value(iterator, 0)
                if word is not None:
                    wlist.append(word)
                iterator = widget.get_model().iter_next(iterator)
            return wlist

    def ClearWidget(self, widget):
        if type(widget) is gtk.Entry:
            widget.set_text("")
        elif type(widget) is gtk.TextView:
            widget.get_buffer().set_text("")
        elif type(widget) is gtk.SpinButton:
            widget.set_value(0)
        elif type(widget) is gtk.CheckButton:
            widget.set_active(0)
        elif type(widget) is gtk.RadioButton:
            widget.set_active(0)
        elif type(widget) is gtk.ComboBox:
            self.GetPosition(widget, "")
        elif type(widget) is gtk.FontButton:
            widget.set_font("")

    def SetWidget(self, widget, value):

        if type(widget) is gtk.Entry:
            if type(value) in (int, str):
                widget.set_text(value)
        elif type(widget) is gtk.TextView:
            if type(value) in (int, str):
                widget.get_buffer().set_text(value)
        elif type(widget) is gtk.SpinButton:
            widget.set_value(int(value))
        elif type(widget) is gtk.CheckButton:
            widget.set_active(value)
        elif type(widget) is gtk.RadioButton:
            widget.set_active(value)
        elif type(widget) is gtk.ComboBox:
            if type(value) is str:
                self.GetPosition(widget, value)
            elif type(value) is int:
                widget.set_active(value)
        elif type(widget) is gtk.FontButton:
            widget.set_font(value)
        elif type(widget) is gtk.TreeView and type(value) is list and widget.get_model().get_n_columns() == 1:
            for item in value:
                widget.get_model().append([item])

    def InvalidSettings(self, domain, key):
        for name, page in self.pages.items():
            if domain in page.options:
                if key in page.options[domain]:
                    self.SwitchToPage(name)
                    break

    def SetSettings(self, config):
        for page in self.pages.values():
            page.SetSettings(config)

    def GetSettings(self):

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
                sub = page.GetSettings()
                for key, data in sub.items():
                    config[key].update(data)

            return self.pages["Shares"].GetNeedRescan(), (self.pages["Colours"].needcolors or self.pages["Fonts"].needcolors), self.pages["Completion"].needcompletion, config
        except UserWarning:
            return None
