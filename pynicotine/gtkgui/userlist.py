# COPYRIGHT (C) 2020 Nicotine+ Team
# COPYRIGHT (C) 2018 Mutnick <mutnick@techie.com>
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2009 Quinox <quinox@users.sf.net>
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
import time
from gettext import gettext as _

from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import GObject as gobject
from gi.repository import Gtk as gtk

from pynicotine import slskmessages
from pynicotine.gtkgui.dialogs import EntryDialog
from pynicotine.gtkgui.utils import Humanize
from pynicotine.gtkgui.utils import HumanSpeed
from pynicotine.gtkgui.utils import InitialiseColumns
from pynicotine.gtkgui.utils import PopupMenu
from pynicotine.gtkgui.utils import PressHeader
from pynicotine.gtkgui.utils import showCountryTooltip


class UserList:

    def __init__(self, frame):

        # Build the window
        self.frame = frame
        config = self.frame.np.config.sections

        builder = gtk.Builder()

        builder.set_translation_domain('nicotine')
        builder.add_from_file(os.path.join(os.path.dirname(os.path.realpath(__file__)), "ui", "buddylist.ui"))

        self.TempWindow = builder.get_object("TempWindow")

        for i in builder.get_objects():
            try:
                self.__dict__[gtk.Buildable.get_name(i)] = i
            except TypeError:
                pass

        self.TempWindow.remove(self.userlistvbox)
        self.TempWindow.destroy()

        builder.connect_signals(self)

        """ Columns """

        TARGETS = [('text/plain', 0, 1)]
        self.UserList.enable_model_drag_source(Gdk.ModifierType.BUTTON1_MASK, TARGETS, Gdk.DragAction.COPY)
        self.UserList.enable_model_drag_dest(TARGETS, Gdk.DragAction.COPY)
        self.UserList.connect("drag_data_get", self.buddylist_drag_data_get_data)
        self.UserList.connect("drag_data_received", self.DragUserToBuddylist)

        self.usersmodel = gtk.ListStore(
            gobject.TYPE_OBJECT,  # (0)  status icon
            gobject.TYPE_OBJECT,  # (1)  flag
            str,                  # (2)  username
            str,                  # (3)  hspeed
            str,                  # (4)  hfile count
            bool,                 # (5)  trusted
            bool,                 # (6)  notify
            bool,                 # (7)  privileged
            str,                  # (8)  hlast seen
            str,                  # (9)  comments
            gobject.TYPE_INT64,   # (10) status
            gobject.TYPE_UINT64,  # (11) speed
            gobject.TYPE_UINT64,  # (12) file count
            int,                  # (13) last seen
            str                   # (14) country
        )

        widths = self.frame.np.config.sections["columns"]["userlist_widths"]
        self.cols = cols = InitialiseColumns(
            self.UserList,
            [_("Status"), widths[0], "pixbuf"],
            [_("Country"), widths[1], "pixbuf"],
            [_("User"), widths[2], "text", self.CellDataFunc],
            [_("Speed"), widths[3], "number", self.CellDataFunc],
            [_("Files"), widths[4], "number", self.CellDataFunc],
            [_("Trusted"), widths[5], "toggle"],
            [_("Notify"), widths[6], "toggle"],
            [_("Privileged"), widths[7], "toggle"],
            [_("Last seen"), widths[8], "text", self.CellDataFunc],
            [_("Comments"), widths[9], "edit", self.CellDataFunc]
        )

        self.col_status, self.col_country, self.col_user, self.col_speed, self.col_files, self.col_trusted, self.col_notify, self.col_privileged, self.col_last_seen, self.col_comments = cols

        try:
            for i in range(len(cols)):

                parent = cols[i].get_widget().get_ancestor(gtk.Button)
                if parent:
                    parent.connect("button_press_event", PressHeader)

                # Read Show / Hide column settings from last session
                cols[i].set_visible(config["columns"]["userlist"][i])
        except IndexError:
            # Column count in config is probably incorrect (outdated?), don't crash
            pass

        self.col_status.set_sort_column_id(10)
        self.col_country.set_sort_column_id(14)
        self.col_user.set_sort_column_id(2)
        self.col_speed.set_sort_column_id(11)
        self.col_files.set_sort_column_id(12)
        self.col_trusted.set_sort_column_id(5)
        self.col_notify.set_sort_column_id(6)
        self.col_privileged.set_sort_column_id(7)
        self.col_last_seen.set_sort_column_id(13)
        self.col_comments.set_sort_column_id(9)

        self.col_status.get_widget().hide()
        self.col_country.get_widget().hide()

        if config["columns"]["hideflags"]:
            cols[1].set_visible(0)
            config["columns"]["userlist"][1] = 0

        for render in self.col_trusted.get_cells():
            render.connect('toggled', self.cell_toggle_callback, self.UserList, 5)

        for render in self.col_notify.get_cells():
            render.connect('toggled', self.cell_toggle_callback, self.UserList, 6)

        for render in self.col_privileged.get_cells():
            render.connect('toggled', self.cell_toggle_callback, self.UserList, 7)

        for render in self.col_comments.get_cells():
            render.connect('edited', self.cell_edited_callback, self.UserList, 9)

        self.UserList.set_model(self.usersmodel)

        """ Buddy list """

        for user in self.frame.np.config.sections["server"]["userlist"]:
            username, comment, notify, privileged, trusted, last_seen, country = user

            try:
                time_from_epoch = time.mktime(time.strptime(last_seen, "%m/%d/%Y %H:%M:%S"))
            except ValueError:
                last_seen = _("Never seen")
                time_from_epoch = 0

            row = [
                self.frame.GetStatusImage(0),
                self.frame.GetFlagImage(country),
                username,
                "",
                "",
                trusted,
                notify,
                privileged,
                last_seen,
                comment,
                0,
                0,
                0,
                time_from_epoch,
                country
            ]

            self.usersmodel.insert(0, row)

        self.usersmodel.set_sort_column_id(2, gtk.SortType.ASCENDING)

        """ Popup """

        self.Popup_Menu_PrivateRooms = PopupMenu(self.frame, False)
        self.popup_menu = popup = PopupMenu(frame)

        popup.setup(
            ("#" + _("Send _message"), popup.OnSendMessage),
            ("", None),
            ("#" + _("Show IP a_ddress"), popup.OnShowIPaddress),
            ("#" + _("Get user i_nfo"), popup.OnGetUserInfo),
            ("#" + _("Brow_se files"), popup.OnBrowseUser),
            ("#" + _("Gi_ve privileges"), popup.OnGivePrivileges),
            ("$" + _("_Ban this user"), popup.OnBanUser),
            ("$" + _("_Ignore this user"), popup.OnIgnoreUser),
            ("", None),
            ("$" + _("_Online notify"), self.OnNotify),
            ("$" + _("_Privileged"), self.OnPrivileged),
            ("$" + _("_Trusted"), self.OnTrusted),
            ("", None),
            ("#" + _("Edit _comments"), self.OnEditComments),
            ("#" + _("_Remove"), self.OnRemoveUser),
            (1, _("Private rooms"), self.Popup_Menu_PrivateRooms, popup.OnPrivateRooms)
        )

        items = self.popup_menu.get_children()
        self.Menu_SendMessage = items[0]
        self.Menu_ShowIPaddress = items[2]
        self.Menu_GetUserInfo = items[3]
        self.Menu_BrowseUser = items[4]
        self.Menu_GivePrivileges = items[5]
        self.Menu_BanUser = items[6]
        self.Menu_IgnoreUser = items[7]
        self.Menu_OnNotify = items[9]
        self.Menu_OnPrivileged = items[10]
        self.Menu_OnTrusted = items[11]
        self.Menu_EditComments = items[13]
        self.Menu_RemoveUser = items[14]
        self.Menu_PrivateRooms = items[15]

        self.UserList.connect("button_press_event", self.OnPopupMenu)

    def OnTooltip(self, widget, x, y, keyboard_mode, tooltip):
        return showCountryTooltip(widget, x, y, tooltip, 14, 'flag_')

    def OnAddUser(self, widget):

        text = self.AddUserEntry.get_text()
        if not text:
            return

        self.AddUserEntry.set_text("")
        self.AddToList(text)

    def UpdateColours(self):
        self.frame.SetTextBG(self.AddUserEntry)

    def buddylist_drag_data_get_data(self, treeview, context, selection, target_id, etime):

        treeselection = treeview.get_selection()
        model, iter = treeselection.get_selected()
        status, flag, user, speed, files, trusted, notify, privileged, lastseen, comments = model.get(iter, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9)

        selection.set(selection.get_target(), 8, user)

    def DragUserToBuddylist(self, treeview, context, x, y, selection, info, etime):

        user = selection.get_data()

        if user:
            self.AddToList(user)

    def OnSettingsBanIgnore(self, widget):
        self.frame.OnSettingsBanIgnore(widget)

    def CellDataFunc(self, column, cellrenderer, model, iter, dummy="dummy"):

        colour = self.frame.np.config.sections["ui"]["search"]

        if colour == "":
            colour = None

        cellrenderer.set_property("foreground", colour)

    def cell_toggle_callback(self, widget, index, treeview, pos):

        iter = self.usersmodel.get_iter(index)
        value = self.usersmodel.get_value(iter, pos)

        self.usersmodel.set(iter, pos, not value)

        self.SaveUserList()

    def cell_edited_callback(self, widget, index, value, treeview, pos):

        store = treeview.get_model()
        iter = store.get_iter(index)

        if pos == 9:
            self.SetComment(iter, store, value)

    def SetLastSeen(self, user, online=False):

        last_seen = ""
        time_from_epoch = 2147483647  # Gtk only allows range -2147483648 to 2147483647 in set()

        if not online:
            last_seen = time.strftime("%m/%d/%Y %H:%M:%S")
            time_from_epoch = time.mktime(time.strptime(last_seen, "%m/%d/%Y %H:%M:%S"))

        for i in self.usersmodel:
            if i[2] == user:
                self.usersmodel.set(i.iter, 8, last_seen)
                self.usersmodel.set(i.iter, 13, int(time_from_epoch))
                break

        if not online:
            self.SaveUserList()

    def SetComment(self, iter, store, comments=None):

        user = store.get_value(iter, 2)

        if comments is not None:

            for i in self.usersmodel:
                if i[2] == user:
                    self.usersmodel.set(iter, 9, comments)
                    break

            self.SaveUserList()

    def ConnClose(self):

        for i in self.usersmodel:
            self.usersmodel.set(
                i.iter,
                0, self.frame.GetStatusImage(0),
                3, "",
                4, "",
                10, 0,
                11, 0,
                12, 0
            )

            if self.usersmodel.get(i.iter, 8)[0] == "":
                user = i[2]
                self.SetLastSeen(user)

    def OnPopupMenu(self, widget, event):

        d = self.UserList.get_path_at_pos(int(event.x), int(event.y))

        if d:
            path, column, x, y = d
            model = self.UserList.get_model()
            iter = model.get_iter(path)
            user = model.get_value(iter, 2)
            status = model.get_value(iter, 10)

            if event.button != 3:
                if event.type == Gdk.EventType._2BUTTON_PRESS:
                    self.frame.privatechats.SendMessage(user, None, 1)
                    self.frame.ChangeMainPage(None, "private")
                return

            self.popup_menu.set_user(user)

            self.Menu_SendMessage.set_sensitive(status)
            self.Menu_ShowIPaddress.set_sensitive(status)
            self.Menu_GetUserInfo.set_sensitive(status)
            self.Menu_BrowseUser.set_sensitive(status)
            self.Menu_GivePrivileges.set_sensitive(status)
            self.Menu_PrivateRooms.set_sensitive(
                status or
                self.popup_menu.user != self.frame.np.config.sections["server"]["login"]
            )

            self.Menu_BanUser.set_active(user in self.frame.np.config.sections["server"]["banlist"])
            self.Menu_IgnoreUser.set_active(user in self.frame.np.config.sections["server"]["ignorelist"])
            self.Menu_OnNotify.set_active(model.get_value(iter, 6))
            self.Menu_OnPrivileged.set_active(model.get_value(iter, 7))
            self.Menu_OnTrusted.set_active(model.get_value(iter, 5))

            self.popup_menu.popup(None, None, None, None, event.button, event.time)

    def GetIter(self, user):

        iters = [i.iter for i in self.usersmodel if i[2] == user]

        if iters:
            return iters[0]
        else:
            return None

    def GetUserStatus(self, msg):

        user = msg.user
        status = msg.status
        iter = self.GetIter(user)

        if iter is None:
            return

        if status == int(self.usersmodel.get_value(iter, 10)):
            return

        notify = self.usersmodel.get_value(iter, 6)

        if notify:
            status_text = [_("User %s is offline"), _("User %s is away"), _("User %s is online")][status]
            self.frame.logMessage(status_text % user)
            self.frame.NewNotification(status_text % user)

        img = self.frame.GetStatusImage(status)
        self.usersmodel.set(
            iter,
            0, img,
            10, status
        )

        if status:  # online
            self.SetLastSeen(user, online=True)
        elif self.usersmodel.get(iter, 8)[0] == "":  # disconnected
            self.SetLastSeen(user)

    def GetUserStats(self, msg):

        user = msg.user
        iter = self.GetIter(user)

        if iter is None:
            return

        country = msg.country
        hspeed = HumanSpeed(msg.avgspeed)
        hfiles = Humanize(msg.files)

        self.usersmodel.set(
            iter,
            3, hspeed,
            4, hfiles,
            11, msg.avgspeed,
            12, msg.files
        )

        if country is not None and country != "":

            country = "flag_" + country
            self.SetUserFlag(user, country)

    def SetUserFlag(self, user, country):

        iter = self.GetIter(user)
        if iter is None:
            return

        if user not in [i[2] for i in self.usersmodel]:
            return

        self.usersmodel.set(
            iter,
            1, self.frame.GetFlagImage(country),
            14, country
        )

    def AddToList(self, user):

        if user in [i[2] for i in self.usersmodel]:
            return

        row = [self.frame.GetStatusImage(0), None, user, "", "", False, False, False, _("Never seen"), "", 0, 0, 0, 0, ""]
        self.usersmodel.append(row)

        self.SaveUserList()
        self.frame.np.queue.put(slskmessages.AddUser(user))
        self.frame.np.queue.put(slskmessages.GetPeerAddress(user))

        for widget in self.frame.BuddiesComboEntries:
            GLib.idle_add(widget.Append, user)

        if self.frame.np.config.sections["words"]["buddies"]:
            GLib.idle_add(self.frame.chatrooms.roomsctrl.UpdateCompletions)
            GLib.idle_add(self.frame.privatechats.UpdateCompletions)

    def OnEditComments(self, widget):

        user = self.popup_menu.get_user()

        for i in self.usersmodel:
            if i[2] == user:
                comments = i[9]
                break
        else:
            comments = ""

        comments = EntryDialog(self.frame.MainWindow, _("Edit comments") + "...", _("Comments") + ":", comments)

        if comments is not None:
            for i in self.usersmodel:
                if i[2] == user:
                    i[9] = comments
                    self.usersmodel.set(i.iter, 9, comments)
                    break

            self.SaveUserList()

    def SaveUserList(self):

        list = []

        for i in self.usersmodel:
            status_icon, flag, user, hspeed, hfile_count, trusted, notify, privileged, hlast_seen, comments, status, speed, file_count, last_seen, country = i
            list.append([user, comments, notify, privileged, trusted, hlast_seen, country])

        self.frame.np.config.sections["server"]["userlist"] = list
        self.frame.np.config.writeConfiguration()

    def saveColumns(self):

        columns = []
        widths = []
        for column in self.UserList.get_columns():
            columns.append(column.get_visible())
            widths.append(column.get_width())
        self.frame.np.config.sections["columns"]["userlist"] = columns
        self.frame.np.config.sections["columns"]["userlist_widths"] = widths

    def RemoveFromList(self, user):

        for i in self.usersmodel:
            if i[2] == user:
                self.usersmodel.remove(i.iter)
                break

        self.SaveUserList()

        for widget in self.frame.BuddiesComboEntries:
            GLib.idle_add(widget.Remove, user)

        if self.frame.np.config.sections["words"]["buddies"]:
            GLib.idle_add(self.frame.chatrooms.roomsctrl.UpdateCompletions)
            GLib.idle_add(self.frame.privatechats.UpdateCompletions)

    def OnRemoveUser(self, widget):
        self.RemoveFromList(self.popup_menu.get_user())

    def OnTrusted(self, widget):

        user = self.popup_menu.get_user()

        for i in self.usersmodel:
            if i[2] == user:
                self.usersmodel.set(i.iter, 5, widget.get_active())
                break

        self.SaveUserList()

    def OnNotify(self, widget):

        user = self.popup_menu.get_user()

        for i in self.usersmodel:
            if i[2] == user:
                self.usersmodel.set(i.iter, 6, widget.get_active())
                break

        self.SaveUserList()

    def OnPrivileged(self, widget):

        user = self.popup_menu.get_user()

        for i in self.usersmodel:
            if i[2] == user:
                self.usersmodel.set(i.iter, 7, widget.get_active())
                break

        self.SaveUserList()
